import math

from PIL import Image, ImageDraw

from src.data_generation.generate_qr import build_fictional_payload, create_qr_image
from src.layer1_forensics.freq_features import extract_frequency_features


def test_frequency_features_are_finite_for_generated_qr():
    payload, _ = build_fictional_payload(1, "Amber Kite Books")
    image = create_qr_image(payload)

    features = extract_frequency_features(image)

    assert len(features.to_vector()) == 5
    assert all(math.isfinite(value) for value in features.to_vector())
    assert 0 <= features.fft_high_frequency_ratio <= 1
    assert 0 <= features.dct_high_frequency_ratio <= 1
    assert 0 <= features.boundary_jump <= 1
    assert features.qr_detected == 1.0


def test_frequency_extraction_uses_fallback_when_qr_is_not_detected():
    image = Image.new("RGB", (96, 96), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 75, 75), fill="black")

    features = extract_frequency_features(image)

    assert features.qr_detected == 0.0
    assert all(math.isfinite(value) for value in features.to_vector())

