"""
Generate Genuine QR Codes for QR Shield
"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlencode

import cv2
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_Q

from src.layer2_content.registry import REGISTRY


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "genuine"

PAYLOAD_VARIANTS = (
    ("pa", "pn"),
    ("pa", "pn", "tr"),
    ("pa", "pn", "cu"),
    ("pa", "pn", "am"),
    ("pa", "pn", "tn"),
    ("pn", "pa"),
    ("pn", "pa", "tr"),
    ("pn", "pa", "cu"),
    ("pn", "pa", "am"),
    ("pn", "pa", "tn"),
)


def create_qr(payload: str):

    qr = qrcode.QRCode(
        version=None,
        # Q remains resilient to ordinary synthetic capture variation while
        # avoiding OpenCV decode failures seen with some denser H-level codes.
        error_correction=ERROR_CORRECT_Q,
        box_size=10,
        border=4,
    )

    qr.add_data(payload)
    qr.make(fit=True)

    return qr.make_image(
        fill_color="black",
        back_color="white",
    ).convert("RGB")


def qr_decodes(image) -> bool:

    detector = cv2.QRCodeDetector()

    payload, _, _ = detector.detectAndDecode(
        cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    )

    return bool(payload)


def build_decodable_payload(fields: dict[str, str]) -> str:

    last_payload = ""

    for order in PAYLOAD_VARIANTS:

        ordered_pairs = [
            (field, fields[field])
            for field in order
            if field in fields
        ]

        last_payload = "upi://pay?" + urlencode(ordered_pairs)

        if qr_decodes(create_qr(last_payload)):
            return last_payload

    return last_payload


def generate_genuine_qrs(count: int):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    registry_items = list(REGISTRY.values())

    if count > len(registry_items):
        raise ValueError(
            f"Registry contains only {len(registry_items)} merchants."
        )

    for i in range(count):

        merchant = registry_items[i]

        payload = build_decodable_payload(
            {
                "pa": merchant.payee_id,
                "pn": merchant.merchant_name,
            }
        )

        image = create_qr(payload)

        filename = OUTPUT_DIR / f"genuine_{i:05d}.png"

        image.save(filename)

        print(
            f"Generated: {filename.name} -> "
            f"{merchant.merchant_name} "
            f"({merchant.payee_id})"
        )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--count",
        type=int,
        default=500,
    )

    args = parser.parse_args()

    generate_genuine_qrs(args.count)


if __name__ == "__main__":
    main()
