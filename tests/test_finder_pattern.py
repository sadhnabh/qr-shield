import numpy as np

from src.data_generation.generate_qr import build_fictional_payload, create_qr_image
from src.layer1_forensics.finder_pattern import (
    FinderCandidate,
    analyze_finder_geometry,
    finder_triangle_features,
    quadrilateral_features,
)


def test_perfect_square_has_zero_geometry_error():
    corners = np.asarray([(0, 0), (10, 0), (10, 10), (0, 10)], dtype=np.float32)

    angle, opposite, diagonal = quadrilateral_features(corners)

    assert angle < 1e-8
    assert opposite == 0.0
    assert diagonal == 0.0


def test_perfect_finder_triangle_has_zero_error():
    candidates = [
        FinderCandidate((0.0, 0.0), 100.0),
        FinderCandidate((10.0, 0.0), 100.0),
        FinderCandidate((0.0, 10.0), 100.0),
    ]

    leg, pythagorean, size = finder_triangle_features(candidates)

    assert leg < 1e-8
    assert pythagorean < 1e-8
    assert size == 0.0


def test_generated_qr_has_detectable_outer_and_finder_geometry():
    payload, _ = build_fictional_payload(2, "Copper Cloud Crafts")
    image = create_qr_image(payload)

    result = analyze_finder_geometry(image)

    assert result.qr_detected == 1.0
    assert result.finder_count >= 3
    assert len(result.finder_centers) == 3
    assert 0 <= result.irregularity_score <= 1

