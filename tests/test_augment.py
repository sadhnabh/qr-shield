import random

from PIL import Image

from src.data_generation.augment import AugmentationConfig, apply_capture_augmentation


def test_augmentation_is_reproducible_and_adds_padding():
    image = Image.new("RGB", (20, 20), "white")
    config = AugmentationConfig(canvas_padding=5)

    first, first_params = apply_capture_augmentation(image, random.Random(7), config)
    second, second_params = apply_capture_augmentation(image, random.Random(7), config)

    assert first.size == (30, 30)
    assert first.tobytes() == second.tobytes()
    assert first_params == second_params

