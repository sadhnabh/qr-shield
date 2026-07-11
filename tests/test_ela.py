import random

import pytest
from PIL import Image

from src.layer1_forensics.ela import analyze_ela, save_ela_heatmap


def test_ela_returns_normalized_score_and_matching_image_sizes():
    image = Image.new("RGB", (32, 24), (127, 160, 190))

    result = analyze_ela(image, jpeg_quality=90)

    assert 0.0 <= result.score <= 1.0
    assert result.mean_error >= 0.0
    assert 0 <= result.max_error <= 255
    assert result.difference.size == image.size
    assert result.heatmap.size == image.size


def test_irregular_high_frequency_image_has_more_error_than_flat_image():
    rng = random.Random(17)
    flat = Image.new("RGB", (64, 64), (128, 128, 128))
    noisy = Image.new("RGB", (64, 64))
    noisy.putdata(
        [
            (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            for _ in range(64 * 64)
        ]
    )

    flat_result = analyze_ela(flat, jpeg_quality=90)
    noisy_result = analyze_ela(noisy, jpeg_quality=90)

    assert noisy_result.mean_error > flat_result.mean_error


def test_ela_rejects_invalid_quality():
    with pytest.raises(ValueError, match="between 1 and 95"):
        analyze_ela(Image.new("RGB", (8, 8)), jpeg_quality=100)


def test_heatmap_save_refuses_to_overwrite(tmp_path):
    result = analyze_ela(Image.new("RGB", (16, 16), "white"))
    output = tmp_path / "heatmap.png"
    save_ela_heatmap(result, output)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        save_ela_heatmap(result, output)

