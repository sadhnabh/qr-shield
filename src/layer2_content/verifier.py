"""
verifier.py

End-to-end QR verification.

Pipeline:
1. Decode QR image
2. Parse payload
3. Verify merchant against fictional registry
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from src.qr_decoder.decode import decode_qr
from src.layer2_content.parser import parse_payload
from src.layer2_content.registry import exists, verify


@dataclass(frozen=True)
class VerificationResult:
    qr_detected: bool
    payload_valid: bool
    registry_match: bool
    payee_id: str
    merchant_name: str
    status: str
    reason: str


def verify_image(image_path: str | Path) -> VerificationResult:
    """
    Verify a QR image.
    """

    decoded = decode_qr(image_path)

    # QR not detected
    if not decoded["decoded"]:
        return VerificationResult(
            qr_detected=False,
            payload_valid=False,
            registry_match=False,
            payee_id="",
            merchant_name="",
            status="SUSPICIOUS",
            reason=decoded["error"],
        )

    # Parse payload
    info = parse_payload(decoded["payload"])

    if not info.is_valid_format:
        return VerificationResult(
            qr_detected=True,
            payload_valid=False,
            registry_match=False,
            payee_id=info.payee_address,
            merchant_name=info.payee_name,
            status="SUSPICIOUS",
            reason="Invalid UPI payload.",
        )

    # Unknown external UPI IDs are not fraudulent merely because QR Shield has
    # no registry record for them.
    if not exists(info.payee_address):
        return VerificationResult(
            qr_detected=True,
            payload_valid=True,
            registry_match=False,
            payee_id=info.payee_address,
            merchant_name=info.payee_name,
            status="UNVERIFIED",
            reason="Merchant not found in the QR Shield registry. Authenticity cannot be verified.",
        )

    # Registry verification
    registry_ok = verify(
        info.payee_address,
        info.payee_name,
    )

    if registry_ok:
        return VerificationResult(
            qr_detected=True,
            payload_valid=True,
            registry_match=True,
            payee_id=info.payee_address,
            merchant_name=info.payee_name,
            status="GENUINE",
            reason="Registry verification successful.",
        )

    return VerificationResult(
        qr_detected=True,
        payload_valid=True,
        registry_match=False,
        payee_id=info.payee_address,
        merchant_name=info.payee_name,
        status="SUSPICIOUS",
        reason="Merchant information does not match the trusted registry.",
    )


def pretty_print(result: VerificationResult) -> None:
    """
    Print verification result.
    """

    print()
    print("=" * 45)
    print("Verification Result")
    print("=" * 45)
    print(f"QR Detected    : {result.qr_detected}")
    print(f"Payload Valid  : {result.payload_valid}")
    print(f"Registry Match : {result.registry_match}")
    print(f"Payee ID       : {result.payee_id}")
    print(f"Merchant       : {result.merchant_name}")
    print(f"Status         : {result.status}")
    print(f"Reason         : {result.reason}")
    print("=" * 45)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="QR Verification")

    parser.add_argument(
        "image",
        nargs="?",
        default="data/genuine/genuine_seed42_00000.png",
        help="QR image",
    )

    args = parser.parse_args()

    result = verify_image(args.image)

    pretty_print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
