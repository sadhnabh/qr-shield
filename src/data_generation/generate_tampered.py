"""
Generate Tampered QR Codes for QR Shield

Creates visually tampered QR codes with fraudulent payloads.
"""

from __future__ import annotations

import argparse
import io
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageDraw
import qrcode
from qrcode.constants import ERROR_CORRECT_Q

from src.data_generation.generate_qr import build_decodable_payload
from src.layer2_content.registry import REGISTRY
from src.qr_decoder.decode import decode_qr

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "tampered"

# QR generation parameters - kept as named constants since finder_damage()
# needs to derive pixel coordinates from these, not hardcode them.
QR_BOX_SIZE = 10
QR_BORDER = 4

# ---------------------------------------------------------
# QR Generator
# ---------------------------------------------------------

def create_qr(payload: str) -> Image.Image:

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_Q,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )

    qr.add_data(payload)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white",
    ).convert("RGB")


# ---------------------------------------------------------
# Attack 1
# Gaussian Noise
# ---------------------------------------------------------

def add_noise(image: Image.Image) -> Image.Image:

    arr = np.array(image).astype(np.float32)

    noise = np.random.normal(0, 6, arr.shape)

    arr += noise

    arr = np.clip(arr, 0, 255)

    return Image.fromarray(arr.astype(np.uint8))


# ---------------------------------------------------------
# Attack 2
# Blur
# ---------------------------------------------------------

def blur(image: Image.Image) -> Image.Image:

    return image.filter(ImageFilter.GaussianBlur(radius=0.6))


# ---------------------------------------------------------
# Attack 3
# JPEG Compression
# ---------------------------------------------------------

def jpeg_compress(image: Image.Image) -> Image.Image:

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=55)
    buffer.seek(0)
    with Image.open(buffer) as img:
        compressed = img.convert("RGB")
    return compressed


# ---------------------------------------------------------
# Attack 4
# Rotate
# ---------------------------------------------------------

def rotate(image: Image.Image) -> Image.Image:

    angle = random.uniform(-2, 2)

    rotated = image.rotate(
        angle,
        expand=True,
        fillcolor="white",
    )

    return rotated.resize(image.size)


# ---------------------------------------------------------
# Attack 5
# Random Rectangle Damage
# ---------------------------------------------------------

def erase_block(image: Image.Image) -> Image.Image:

    img = image.copy()

    draw = ImageDraw.Draw(img)

    w, h = img.size

    x = random.randint(w // 4, w // 2)
    y = random.randint(h // 4, h // 2)

    # A small local blemish leaves QR error correction room to preserve
    # payload readability.  This dataset models payload fraud, not destruction.
    draw.rectangle((x, y, x + 14, y + 14), fill="white")

    return img


# ---------------------------------------------------------
# Attack 6
# Finder Pattern Damage
# ---------------------------------------------------------

def finder_damage(image: Image.Image) -> Image.Image:
    """
    Adds a small visible blemish to the top-left finder pattern without
    erasing it.  The finder remains detectable, so this is a visual-tamper
    simulation rather than a QR-destruction attack.
    """

    img = image.copy()

    draw = ImageDraw.Draw(img)

    offset = QR_BORDER * QR_BOX_SIZE          # top-left corner of finder pattern
    draw.rectangle(
        (
            offset + 2 * QR_BOX_SIZE,
            offset + 2 * QR_BOX_SIZE,
            offset + 2 * QR_BOX_SIZE + 8,
            offset + 2 * QR_BOX_SIZE + 8,
        ),
        fill=(110, 110, 110),
    )

    return img


# ---------------------------------------------------------
# Attack 7
# Random Scratch
# ---------------------------------------------------------

def add_scratch(image: Image.Image) -> Image.Image:

    img = image.copy()

    draw = ImageDraw.Draw(img)

    w, h = img.size

    draw.line(
        (
            random.randint(0, w),
            random.randint(0, h),
            random.randint(0, w),
            random.randint(0, h),
        ),
        fill="black",
        width=2,
    )

    return img


# ---------------------------------------------------------
# Apply Visual Attack
# ---------------------------------------------------------

def apply_visual_attack(image: Image.Image, attack: int) -> Image.Image:

    if attack == 0:
        image = add_noise(image)
        image = jpeg_compress(image)

    elif attack == 1:
        image = blur(image)
        image = add_noise(image)

    elif attack == 2:
        image = jpeg_compress(image)
        image = rotate(image)

    elif attack == 3:
        image = erase_block(image)
        image = add_noise(image)

    elif attack == 4:
        image = finder_damage(image)
        image = blur(image)

    elif attack == 5:
        image = add_scratch(image)
        image = jpeg_compress(image)

    elif attack == 6:
        image = rotate(image)
        image = add_noise(image)

    else:
        image = add_noise(image)
        image = blur(image)
        image = jpeg_compress(image)
        image = add_scratch(image)

    return image


def _save_if_decodable(image: Image.Image, filename: Path) -> bool:
    """Persist only tampered samples that the production decoder can read."""
    image.save(filename, optimize=True)
    if decode_qr(filename)["decoded"]:
        return True
    filename.unlink(missing_ok=True)
    return False


def build_mismatched_payload(registry: list, payload_attack: int) -> tuple[str, str]:
    """Build a syntactically valid QR payload with a registry-only mismatch.

    Both values always come from the local fictional registry.  The payee ID and
    merchant name deliberately belong to different registry records, so a QR
    that remains decodable will fail ``registry.verify`` and be classified as
    ``TAMPERED`` by the detection pipeline.

    Args:
        registry: Available fictional ``RegistryRecord`` entries.
        payload_attack: Selects whether to start from the payee or merchant of
            the first selected record.  It changes the generation path only;
            both paths produce a mismatch.

    Returns:
        The payload and a short human-readable description of the mismatch.
    """
    if len(registry) < 2:
        raise ValueError("At least two registry entries are required for a mismatch.")
    if payload_attack not in (0, 1):
        raise ValueError("payload_attack must be 0 or 1")

    first = random.choice(registry)
    second = random.choice(registry)
    while second.payee_id == first.payee_id:
        second = random.choice(registry)

    if payload_attack == 0:
        # A valid UPI ID paired with another registered merchant's name.
        payee, name = first.payee_id, second.merchant_name
        description = "registered UPI paired with different registered merchant"
    else:
        # The same intentional mismatch, chosen from the merchant-first path.
        payee, name = second.payee_id, first.merchant_name
        description = "registered merchant paired with different registered UPI"

    payload = build_decodable_payload({"pa": payee, "pn": name})
    return payload, description


# ---------------------------------------------------------
# Generate Dataset
# ---------------------------------------------------------

def generate(count: int) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove previous generated images
    for file in OUTPUT_DIR.glob("tampered_*.png"):
        file.unlink()

    registry = list(REGISTRY.values())

    if len(registry) < 2:
        raise ValueError(
            "generate_tampered.py requires at least 2 registry entries "
            f"to build mismatched payloads; found {len(registry)}."
        )

    generated = 0

    while generated < count:

        # ---------------------------------
        # Registry-only payload mismatch
        # ---------------------------------

        payload_attack = random.randint(0, 1)
        payload, mismatch_description = build_mismatched_payload(
            registry,
            payload_attack,
        )

        filename = OUTPUT_DIR / f"tampered_{generated:05d}.png"
        for _ in range(20):
            image = create_qr(payload)
            visual_attack = random.randint(0, 7)
            image = apply_visual_attack(image, visual_attack)
            if _save_if_decodable(image, filename):
                break
        else:
            raise RuntimeError("Could not create a decodable tampered QR sample.")

        print(
            f"{filename.name:<20}"
            f" | Payload Attack: {payload_attack} ({mismatch_description})"
            f" | Visual Attack: {visual_attack}"
        )

        generated += 1


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Generate Tampered QR Dataset"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=500,
        help="Number of tampered QR codes to generate",
    )

    args = parser.parse_args()

    generate(args.count)

    print()
    print("=" * 60)
    print(f"Generated {args.count} tampered QR codes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
