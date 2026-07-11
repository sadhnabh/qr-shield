"""FFT/DCT and QR-boundary discontinuity feature extraction."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from src.utils.image_io import ImageInput, load_gray


@dataclass(frozen=True)
class FrequencyFeatures:
    """Explainable frequency and boundary measurements for one image."""

    fft_high_frequency_ratio: float
    dct_high_frequency_ratio: float
    boundary_energy_ratio: float
    boundary_jump: float
    qr_detected: float

    def to_dict(self) -> dict[str, float]:
        """Return stable feature names for manifests and model input."""
        return asdict(self)

    def to_vector(self) -> list[float]:
        """Return features in their declared order for future classifiers."""
        values = self.to_dict()
        return [values[name] for name in values]


def _detect_qr_bounds(gray: np.ndarray) -> tuple[int, int, int, int, bool]:
    """Find an axis-aligned QR region, with a dark-pixel fallback."""
    detector = cv2.QRCodeDetector()
    detected, points = detector.detect(gray)
    if detected and points is not None:
        corners = np.asarray(points, dtype=np.float32).reshape(4, 2)
        x, y, width, height = cv2.boundingRect(corners)
        return x, y, width, height, True

    # The fallback permits feature extraction when tampering defeats QR detection.
    dark_y, dark_x = np.where(gray < 180)
    if dark_x.size == 0:
        return 0, 0, gray.shape[1], gray.shape[0], False
    x_min, x_max = int(dark_x.min()), int(dark_x.max())
    y_min, y_max = int(dark_y.min()), int(dark_y.max())
    return x_min, y_min, x_max - x_min + 1, y_max - y_min + 1, False


def _expanded_crop(
    gray: np.ndarray,
    bounds: tuple[int, int, int, int],
    padding_fraction: float = 0.05,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Crop around the QR while retaining pixels on both sides of its edge."""
    x, y, width, height = bounds
    padding = max(2, round(min(width, height) * padding_fraction))
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(gray.shape[1], x + width + padding)
    bottom = min(gray.shape[0], y + height + padding)
    crop = gray[top:bottom, left:right]
    relative_bounds = (x - left, y - top, width, height)
    return crop, relative_bounds


def _fft_high_frequency_ratio(gray: np.ndarray) -> float:
    """Measure spectral power outside the centered low-frequency disk."""
    normalized = gray.astype(np.float32) / 255.0
    normalized -= float(normalized.mean())
    power = np.abs(np.fft.fftshift(np.fft.fft2(normalized))) ** 2
    rows, columns = gray.shape
    yy, xx = np.ogrid[:rows, :columns]
    distance = np.sqrt((yy - rows / 2.0) ** 2 + (xx - columns / 2.0) ** 2)
    high_frequency = distance >= 0.25 * min(rows, columns)
    total = float(power.sum())
    return float(power[high_frequency].sum() / total) if total > 0 else 0.0


def _dct_high_frequency_ratio(gray: np.ndarray) -> float:
    """Measure DCT energy above a low-frequency triangular region."""
    normalized = gray.astype(np.float32) / 255.0
    normalized -= float(normalized.mean())
    coefficients = cv2.dct(normalized)
    energy = coefficients**2
    rows, columns = gray.shape
    yy, xx = np.ogrid[:rows, :columns]
    high_frequency = (yy / rows + xx / columns) >= 0.35
    total = float(energy.sum())
    return float(energy[high_frequency].sum() / total) if total > 0 else 0.0


def _boundary_features(
    crop: np.ndarray,
    bounds: tuple[int, int, int, int],
) -> tuple[float, float]:
    """Measure gradient energy and intensity jumps around the QR boundary."""
    x, y, width, height = bounds
    sobel_x = cv2.Sobel(crop, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(crop, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(sobel_x, sobel_y)
    band = max(1, round(min(width, height) * 0.025))

    boundary_mask = np.zeros(crop.shape, dtype=bool)
    interior_mask = np.zeros(crop.shape, dtype=bool)
    x_end = min(crop.shape[1], x + width)
    y_end = min(crop.shape[0], y + height)
    boundary_mask[max(0, y - band) : min(crop.shape[0], y + band), x:x_end] = True
    boundary_mask[max(0, y_end - band) : min(crop.shape[0], y_end + band), x:x_end] = True
    boundary_mask[y:y_end, max(0, x - band) : min(crop.shape[1], x + band)] = True
    boundary_mask[y:y_end, max(0, x_end - band) : min(crop.shape[1], x_end + band)] = True
    interior_mask[
        min(y_end, y + 2 * band) : max(y, y_end - 2 * band),
        min(x_end, x + 2 * band) : max(x, x_end - 2 * band),
    ] = True
    boundary_energy = float(gradient[boundary_mask].mean()) if boundary_mask.any() else 0.0
    interior_energy = float(gradient[interior_mask].mean()) if interior_mask.any() else 0.0
    energy_ratio = boundary_energy / max(interior_energy, 1e-6)

    jumps: list[float] = []
    if y - band >= 0 and y + band <= crop.shape[0]:
        outside = crop[y - band : y, x:x_end].astype(np.float32)
        inside = crop[y : y + band, x:x_end].astype(np.float32)
        jumps.append(float(np.abs(outside - inside).mean()))
    if y_end + band <= crop.shape[0] and y_end - band >= 0:
        inside = crop[y_end - band : y_end, x:x_end].astype(np.float32)
        outside = crop[y_end : y_end + band, x:x_end].astype(np.float32)
        jumps.append(float(np.abs(outside - inside).mean()))
    if x - band >= 0 and x + band <= crop.shape[1]:
        outside = crop[y:y_end, x - band : x].astype(np.float32)
        inside = crop[y:y_end, x : x + band].astype(np.float32)
        jumps.append(float(np.abs(outside - inside).mean()))
    if x_end + band <= crop.shape[1] and x_end - band >= 0:
        inside = crop[y:y_end, x_end - band : x_end].astype(np.float32)
        outside = crop[y:y_end, x_end : x_end + band].astype(np.float32)
        jumps.append(float(np.abs(outside - inside).mean()))
    boundary_jump = (sum(jumps) / len(jumps) / 255.0) if jumps else 0.0
    return energy_ratio, boundary_jump


def extract_frequency_features(image_or_path: ImageInput) -> FrequencyFeatures:
    """Extract FFT, DCT, and boundary features from an image."""
    gray = load_gray(image_or_path)
    if min(gray.shape) < 16:
        raise ValueError("image must be at least 16 pixels in each dimension")
    x, y, width, height, detected = _detect_qr_bounds(gray)
    crop, relative_bounds = _expanded_crop(gray, (x, y, width, height))
    boundary_energy_ratio, boundary_jump = _boundary_features(crop, relative_bounds)
    return FrequencyFeatures(
        fft_high_frequency_ratio=_fft_high_frequency_ratio(crop),
        dct_high_frequency_ratio=_dct_high_frequency_ratio(crop),
        boundary_energy_ratio=boundary_energy_ratio,
        boundary_jump=boundary_jump,
        qr_detected=float(detected),
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line inputs without analyzing images."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+", help="input image paths")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Print one JSON feature record per input image."""
    args = parse_args(argv)
    for path in args.images:
        features = extract_frequency_features(path)
        print(json.dumps({"image": str(path), **features.to_dict()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
