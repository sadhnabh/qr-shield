"""
QR Shield Detection Pipeline

Workflow
--------
1. Decode QR
2. Parse Payload
3. Registry Check
4. Image Forensics (registered & verified QRs only)
5. Final Decision
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.qr_decoder.decode import decode_qr
from src.layer2_content.parser import parse_payload
from src.layer2_content.registry import exists, verify
from src.layer1_forensics.ela import analyze_ela
from src.layer1_forensics.freq_features import extract_frequency_features
from src.layer1_forensics.finder_pattern import analyze_finder_geometry
from src.fusion.fusion_engine import compute_fraud_score


def detect(image_path: str | Path):

    image_path = Path(image_path)

    if not image_path.exists():
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
        }

    print("\n" + "=" * 60)
    print("QR SHIELD DETECTION")
    print("=" * 60)

    # Decode and parse before running any forensic feature.  A valid external
    # UPI QR must be UNVERIFIED regardless of image characteristics.
    decoded = decode_qr(image_path)
    payload = parse_payload(decoded["payload"] if decoded["decoded"] else "")

    # ----------------------------------------------------
    # Default Feature Values
    # ----------------------------------------------------

    ela_score = 0.0
    fft_ratio = 0.0
    dct_ratio = 0.0
    boundary_energy = 0.0
    boundary_jump = 0.0
    finder_score = 1.0

    # ----------------------------------------------------
    # Registry Check
    # ----------------------------------------------------

    merchant_exists = bool(payload.is_valid_format and exists(payload.payee_address))
    registry_match = bool(
        merchant_exists and verify(payload.payee_address, payload.payee_name)
    )

    if decoded["decoded"] and payload.is_valid_format and registry_match:

            # ------------------------------------------------
            # Image Forensics
            # ------------------------------------------------

        try:
            ela = analyze_ela(image_path)
            freq = extract_frequency_features(image_path)
            geometry = analyze_finder_geometry(image_path)
            ela_score = ela.score
            fft_ratio = freq.fft_high_frequency_ratio
            dct_ratio = freq.dct_high_frequency_ratio
            boundary_energy = freq.boundary_energy_ratio
            boundary_jump = freq.boundary_jump
            finder_score = 1.0 - geometry.irregularity_score
        except Exception:
            # A feature extractor error is not image evidence of tampering.
            # Keep neutral values and allow the content verification result.
            pass

    fusion = compute_fraud_score(
        qr_detected=decoded["decoded"],
        payload_valid=payload.is_valid_format,
        merchant_exists=merchant_exists,
        registry_match=registry_match,
        ela_score=ela_score,
        fft_ratio=fft_ratio,
        finder_score=finder_score,
    )
    decision = fusion.decision
    fraud_score = fusion.fraud_score
    reason = fusion.reason

# ==========================
# END OF PART 1
# ==========================
    # ----------------------------------------------------
    # Terminal Report
    # ----------------------------------------------------

    print()

    print("Merchant :", payload.payee_name)
    print("UPI      :", payload.payee_address)

    print()

    print("Exists   :", merchant_exists)
    print("Verified :", registry_match)

    print()

    print("ELA      :", round(ela_score, 6))
    print("FFT      :", round(fft_ratio, 6))
    print("Finder   :", round(finder_score, 6))

    print()

    print("Decision :", decision)
    print("Reason   :", reason)

    print("=" * 60)

    # ----------------------------------------------------
    # API Response
    # ----------------------------------------------------

    return {

        "success": True,

        "decision": decision,

        "fraud_score": fraud_score,

        "reason": reason,

        "merchant": payload.payee_name,

        "upi": payload.payee_address,

        "payload": payload.raw_payload,

        "registry_verified": registry_match,

        "qr_detected": decoded["decoded"],

        "payload_valid": payload.is_valid_format,

        "ela_score": round(ela_score, 6),

        "fft_ratio": round(fft_ratio, 6),

        "dct_ratio": round(dct_ratio, 6),

        "boundary_energy": round(boundary_energy, 6),

        "boundary_jump": round(boundary_jump, 6),

        "finder_score": round(finder_score, 6),
    }


# ----------------------------------------------------
# Main
# ----------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="QR Shield Detection"
    )

    parser.add_argument(
        "image",
        type=Path,
        help="QR Image",
    )

    args = parser.parse_args()

    result = detect(args.image)

    print(result)


if __name__ == "__main__":
    main()
