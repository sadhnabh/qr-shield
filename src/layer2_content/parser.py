"""
QR Payload Parser

Parses the decoded QR payload and extracts useful payment fields.

This module does NOT verify authenticity.
It only converts a QR payload string into structured data.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class PaymentInfo:
    """
    Structured information extracted from a QR payload.
    """

    raw_payload: str
    scheme: str
    payee_address: str
    payee_name: str
    is_valid_format: bool

    def to_dict(self) -> dict:
        return {
            "raw_payload": self.raw_payload,
            "scheme": self.scheme,
            "payee_address": self.payee_address,
            "payee_name": self.payee_name,
            "is_valid_format": self.is_valid_format,
        }


def parse_payload(payload: str) -> PaymentInfo:
    """
    Parse a decoded QR payload.

    Example payload:

    upi://pay?pa=demo00000@qrshieldtest&pn=Blue+Banyan+Cafe
    """

    if not payload:
        return PaymentInfo(
            raw_payload="",
            scheme="",
            payee_address="",
            payee_name="",
            is_valid_format=False,
        )

    try:
        parsed = urlparse(payload)

        query = parse_qs(parsed.query)

        payee_address = query.get("pa", [""])[0]
        payee_name = query.get("pn", [""])[0]

        # A UPI address is sufficient to look up a registry entry.  ``pn`` is
        # optional in real UPI QR payloads: an unknown address without a name
        # must be UNVERIFIED, while a known address without its expected name
        # will fail registry verification and be TAMPERED.
        valid = (
            parsed.scheme.lower() == "upi"
            and parsed.netloc.lower() == "pay"
            and len(payee_address) > 0
        )

        return PaymentInfo(
            raw_payload=payload,
            scheme=parsed.scheme,
            payee_address=payee_address,
            payee_name=payee_name,
            is_valid_format=valid,
        )

    except Exception:

        return PaymentInfo(
            raw_payload=payload,
            scheme="",
            payee_address="",
            payee_name="",
            is_valid_format=False,
        )


def pretty_print(info: PaymentInfo) -> None:
    """
    Print parsed payment information.
    """

    print("\n========== Parsed QR Payload ==========")
    print(f"Format Valid : {info.is_valid_format}")
    print(f"Scheme       : {info.scheme}")
    print(f"Payee ID     : {info.payee_address}")
    print(f"Merchant     : {info.payee_name}")
    print("=======================================\n")


def main() -> int:
    """
    Small CLI for testing.

    Example:

    python -m src.layer2_content.parser
    """

    sample_payload = (
        "upi://pay?"
        "pa=demo00000@qrshieldtest"
        "&pn=Blue+Banyan+Cafe"
    )

    info = parse_payload(sample_payload)

    pretty_print(info)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
