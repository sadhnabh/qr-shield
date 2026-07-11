"""
QR Shield Fusion Engine

Combines registry verification and image forensics
into a final QR authenticity decision.

Outputs:
    • GENUINE
    • TAMPERED
    • UNVERIFIED
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusionResult:

    qr_detected: bool
    payload_valid: bool
    registry_match: bool

    ela_score: float
    fft_ratio: float
    finder_score: float

    fraud_score: float

    decision: str
    reason: str


def compute_fraud_score(
    *,
    qr_detected: bool,
    payload_valid: bool,
    merchant_exists: bool,
    registry_match: bool,
    ela_score: float,
    fft_ratio: float,
    finder_score: float,
) -> FusionResult:

    # --------------------------------------------------
    # QR not detected
    # --------------------------------------------------

    if not qr_detected:

        return FusionResult(
            qr_detected=False,
            payload_valid=False,
            registry_match=False,

            ela_score=round(ela_score, 6),
            fft_ratio=round(fft_ratio, 6),
            finder_score=round(finder_score, 6),

            fraud_score=1.000,

            decision="TAMPERED",

            reason="QR Code could not be detected.",
        )

    # --------------------------------------------------
    # Invalid payload
    # --------------------------------------------------

    if not payload_valid:

        return FusionResult(
            qr_detected=True,
            payload_valid=False,
            registry_match=False,

            ela_score=round(ela_score, 6),
            fft_ratio=round(fft_ratio, 6),
            finder_score=round(finder_score, 6),

            fraud_score=0.950,

            decision="TAMPERED",

            reason="Invalid payment payload.",
        )

    # --------------------------------------------------
    # Unknown merchant
    # --------------------------------------------------

    if not merchant_exists:

        return FusionResult(
            qr_detected=True,
            payload_valid=True,
            registry_match=False,

            ela_score=round(ela_score, 6),
            fft_ratio=round(fft_ratio, 6),
            finder_score=round(finder_score, 6),

            fraud_score=0.500,

            decision="UNVERIFIED",

            reason="Merchant not found in the QR Shield registry. Authenticity cannot be verified.",
        )

    # A known UPI ID paired with a different or missing merchant name is an
    # intentional identity mismatch, not an unknown merchant.
    if not registry_match:
        return FusionResult(
            qr_detected=True,
            payload_valid=True,
            registry_match=False,
            ela_score=round(ela_score, 6),
            fft_ratio=round(fft_ratio, 6),
            finder_score=round(finder_score, 6),
            fraud_score=0.950,
            decision="TAMPERED",
            reason="Merchant information does not match the trusted registry.",
        )

    # ==================================================
    # Registered QR: image forensics is supporting evidence, not a verdict
    # from a single compression/capture-sensitive measurement.
    # ==================================================

    anomalies = 0
    score = 0.0
    reasons = []

    # -------------------------
    # ELA
    # -------------------------

    if ela_score > 0.035:

        anomalies += 1
        score += 0.35

        reasons.append(
            "Image manipulation detected."
        )

    # -------------------------
    # FFT
    # High-frequency energy naturally changes with screenshots, JPEG encoding,
    # and camera noise, so it needs corroboration from another signal.
    # -------------------------

    if fft_ratio > 0.090:

        anomalies += 1
        score += 0.25

        reasons.append(
            "Abnormal frequency distribution."
        )

    # -------------------------
    # Finder Pattern
    # -------------------------

    if finder_score < 0.82:

        anomalies += 1
        score += 0.40

        reasons.append(
            "Finder pattern distortion detected."
        )

    score = min(score, 1.0)

    # ==================================================
    # Final Decision
    # ==================================================

    # A single feature can fail for an ordinary screenshot, JPEG compression,
    # light blur, or camera noise.  Require independent evidence or a high
    # combined risk score before marking a known, otherwise valid QR tampered.
    if anomalies >= 2 or score >= 0.70:

        decision = "TAMPERED"

        reason = " | ".join(reasons)

    else:

        decision = "GENUINE"

        reason = "All verification checks passed."

        score = min(score, 0.15)

    return FusionResult(

        qr_detected=True,

        payload_valid=True,

        registry_match=True,

        ela_score=round(ela_score, 6),

        fft_ratio=round(fft_ratio, 6),

        finder_score=round(finder_score, 6),

        fraud_score=round(score, 3),

        decision=decision,

        reason=reason,
    )


def print_result(result: FusionResult):

    print()
    print("=" * 60)
    print("QR SHIELD FINAL REPORT")
    print("=" * 60)

    print(f"QR Detected      : {result.qr_detected}")
    print(f"Payload Valid    : {result.payload_valid}")
    print(f"Registry Match   : {result.registry_match}")

    print()

    print(f"ELA Score        : {result.ela_score:.6f}")
    print(f"FFT Ratio        : {result.fft_ratio:.6f}")
    print(f"Finder Score     : {result.finder_score:.6f}")

    print()

    print(f"Fraud Score      : {result.fraud_score:.3f}")
    print(f"Decision         : {result.decision}")
    print(f"Reason           : {result.reason}")

    print("=" * 60)


def main():

    result = compute_fraud_score(

        qr_detected=True,

        payload_valid=True,

        merchant_exists=True,

        registry_match=True,

        ela_score=0.003,

        fft_ratio=0.041,

        finder_score=0.998,

    )

    print_result(result)


if __name__ == "__main__":
    main()
