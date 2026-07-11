"""QR decoder with diagnostic preprocessing fallbacks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except (ImportError, OSError):
    # pyzbar requires the native zbar library, which is optional on Windows.
    pyzbar_decode = None


DEBUG_ROOT = Path(".test-tmp") / "qr_decoder_debug"


def _resize(image: np.ndarray, scale: float) -> np.ndarray:
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _preprocessed_images(image: np.ndarray):
    """Build and name every representation used by the decoders."""
    height, width = image.shape[:2]
    if max(height, width) > 1200:
        image = _resize(image, 1200 / max(height, width))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    equalized = cv2.equalizeHist(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    smallest_side = min(gray.shape)
    if smallest_side >= 3:
        block_size = min(31, smallest_side if smallest_side % 2 else smallest_side - 1)
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 5
        )
    else:
        adaptive = gray.copy()

    resized_2x = _resize(gray, 2.0)
    resized_3x = _resize(gray, 3.0)
    _, resized_2x_otsu = cv2.threshold(
        resized_2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    _, resized_3x_otsu = cv2.threshold(
        resized_3x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    resized_2x_adaptive = cv2.adaptiveThreshold(
        resized_2x, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
    )
    resized_3x_adaptive = cv2.adaptiveThreshold(
        resized_3x, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
    )
    sharpened = cv2.addWeighted(
        clahe, 1.5, cv2.GaussianBlur(clahe, (0, 0), 1.0), -0.5, 0
    )

    return (
        ("original", image),
        ("grayscale", gray),
        ("adaptive_threshold", adaptive),
        ("otsu_threshold", otsu),
        ("histogram_equalization", equalized),
        ("clahe", clahe),
        ("resize_2x", resized_2x),
        ("resize_3x", resized_3x),
        ("sharpen", sharpened),
        ("denoise", denoised),
        ("resize_2x_otsu_threshold", resized_2x_otsu),
        ("resize_3x_otsu_threshold", resized_3x_otsu),
        ("resize_2x_adaptive_threshold", resized_2x_adaptive),
        ("resize_3x_adaptive_threshold", resized_3x_adaptive),
    )


def _rectified_candidates(candidates):
    """Add perspective-corrected variants when OpenCV can find QR corners."""
    rectified = []
    for step, image in candidates[:6]:
        try:
            detected, points = cv2.QRCodeDetector().detect(image)
        except cv2.error:
            detected, points = False, None
        if not detected or points is None:
            print(f"[qr_decoder] rectify {step}: no QR corners")
            continue
        source = points.reshape(4, 2).astype("float32")
        size = 720
        destination = np.array(
            ((0, 0), (size - 1, 0), (size - 1, size - 1), (0, size - 1)),
            dtype="float32",
        )
        warped = cv2.warpPerspective(
            image, cv2.getPerspectiveTransform(source, destination), (size, size),
            borderMode=cv2.BORDER_CONSTANT, borderValue=255,
        )
        rectified.append((
            f"{step}_perspective_rectified",
            cv2.copyMakeBorder(warped, 32, 32, 32, 32, cv2.BORDER_CONSTANT, value=255),
        ))
        print(f"[qr_decoder] rectify {step}: saved candidate")
    return tuple(rectified)


def _save_debug_images(image_path: Path, candidates) -> Path:
    """Persist all decoder inputs for visual inspection of a failing upload."""
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", image_path.stem)
    debug_dir = DEBUG_ROOT / safe_stem
    debug_dir.mkdir(parents=True, exist_ok=True)
    for index, (step, candidate) in enumerate(candidates):
        filename = f"{index:02d}_{step}.png"
        if not cv2.imwrite(str(debug_dir / filename), candidate):
            print(f"[qr_decoder] debug image {step}: FAILED to save")
    print(f"[qr_decoder] preprocessing images saved to: {debug_dir.resolve()}")
    return debug_dir


def _decode_with_opencv(image: np.ndarray) -> str:
    try:
        payload, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
        return payload or ""
    except cv2.error:
        return ""


def _decode_multi_with_opencv(image: np.ndarray) -> str:
    try:
        detected, payloads, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(image)
    except (cv2.error, ValueError):
        return ""
    return next((payload for payload in payloads if payload), "") if detected else ""


def _decode_with_pyzbar(image: np.ndarray) -> str:
    if pyzbar_decode is None:
        return ""
    try:
        symbols = pyzbar_decode(image)
    except Exception:
        return ""
    for symbol in symbols:
        if getattr(symbol, "type", "") == "QRCODE":
            return symbol.data.decode("utf-8", errors="replace")
    return ""


def _run_decoder(name: str, decoder, candidates) -> str:
    """Run a decoder over every candidate and log each success or failure."""
    first_payload = ""
    for step, candidate in candidates:
        payload = decoder(candidate)
        if payload:
            print(f"[qr_decoder] {name} {step}: SUCCESS ({payload!r})")
            first_payload = first_payload or payload
        else:
            print(f"[qr_decoder] {name} {step}: failed")
    return first_payload


def _success(payload: str) -> dict:
    parsed = urlparse(payload)
    params = parse_qs(parsed.query)
    return {
        "decoded": True,
        "payload": payload,
        "upi_id": params.get("pa", [None])[0],
        "merchant": params.get("pn", [None])[0],
        "error": None,
    }


def decode_qr(image_path: str | Path) -> dict:
    """Decode a QR upload only after exhaustively trying every decoder path."""
    image_path = Path(image_path)
    if not image_path.exists():
        return {"decoded": False, "payload": None, "upi_id": None, "merchant": None,
                "error": f"Image not found: {image_path}"}

    image = cv2.imread(str(image_path))
    if image is None:
        return {"decoded": False, "payload": None, "upi_id": None, "merchant": None,
                "error": "Unable to read image."}

    candidates = _preprocessed_images(image)
    candidates += _rectified_candidates(candidates)
    _save_debug_images(image_path, candidates)

    payloads = (
        _run_decoder("OpenCV detectAndDecode", _decode_with_opencv, candidates),
        _run_decoder("OpenCV detectAndDecodeMulti", _decode_multi_with_opencv, candidates),
        _run_decoder("pyzbar", _decode_with_pyzbar, candidates),
    )
    for payload in payloads:
        if payload:
            return _success(payload)
    return {"decoded": False, "payload": None, "upi_id": None, "merchant": None,
            "error": "QR code not detected after all decoder attempts"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode a QR image with diagnostic logging.")
    parser.add_argument("image", nargs="?", default="data/genuine/genuine_seed42_00000.png")
    args = parser.parse_args()
    result = decode_qr(args.image)
    print("\n========== QR Decode Result ==========")
    print(f"Decoded   : {result['decoded']}")
    print(f"Payload   : {result['payload']}")
    print(f"UPI ID    : {result['upi_id']}")
    print(f"Merchant  : {result['merchant']}")
    print(f"Error     : {result['error']}")
    print("======================================\n")


if __name__ == "__main__":
    main()
