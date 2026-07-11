"""
registry.py

QR Shield Merchant Registry

Contains fictional merchants used for
generating and verifying genuine QR codes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryRecord:
    payee_id: str
    merchant_name: str


# -------------------------------------------------------
# Merchant Name Pool
# -------------------------------------------------------

ADJECTIVES = [
    "Blue","Amber","Copper","Ivory","Maple","Silver","Teal","Velvet",
    "Golden","Royal","Crystal","Urban","Prime","Bright","Happy","Lucky",
    "Fresh","Green","Rapid","Smart"
]

NOUNS = [
    "Cafe","Bakery","Books","Crafts","Mart","Stationery","Studio",
    "Foods","Store","Electronics","Boutique","Pharmacy","Kitchen",
    "Fashion","Corner","Market","Services","Solutions","Hub","Center",
    "Traders","Collections","Emporium","World","Point"
]


# -------------------------------------------------------
# Build Registry
# -------------------------------------------------------

REGISTRY: dict[str, RegistryRecord] = {}

merchant_index = 0

for adjective in ADJECTIVES:
    for noun in NOUNS:

        merchant_name = f"{adjective} {noun}"

        upi = f"demo{merchant_index:05d}@qrshieldtest"

        REGISTRY[upi] = RegistryRecord(
            payee_id=upi,
            merchant_name=merchant_name,
        )

        merchant_index += 1

        if merchant_index == 500:
            break

    if merchant_index == 500:
        break


# -------------------------------------------------------
# Registry Helpers
# -------------------------------------------------------

def lookup(payee_id: str) -> RegistryRecord | None:
    return REGISTRY.get(payee_id)


def exists(payee_id: str) -> bool:
    return payee_id in REGISTRY


def verify(payee_id: str, merchant_name: str) -> bool:

    record = lookup(payee_id)

    if record is None:
        return False

    return (
        record.merchant_name.strip().lower()
        ==
        merchant_name.strip().lower()
    )


def registry_size() -> int:
    return len(REGISTRY)


if __name__ == "__main__":

    print("Registry Size:", registry_size())

    print()

    for record in list(REGISTRY.values())[:20]:
        print(record)