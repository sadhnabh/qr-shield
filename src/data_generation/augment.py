"""Pillow-based augmentations for synthetic QR images.

The transforms model ordinary capture variation without using external images.
They deliberately remain mild so generated QR codes are usually still decodable.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

from PIL import Image, ImageEnhance


@dataclass(frozen=True)
class AugmentationConfig:
    """Ranges used to vary the appearance of a generated QR image."""

    rotation_degrees: float = 4.0
    brightness_min: float = 0.85
    brightness_max: float = 1.15
    canvas_padding: int = 36
    background_min: int = 220
    background_max: int = 255

    def validate(self) -> None:
        """Reject ranges that cannot produce a sensible image."""
        if self.rotation_degrees < 0:
            raise ValueError("rotation_degrees must be non-negative")
        if not 0 < self.brightness_min <= self.brightness_max:
            raise ValueError("brightness range must be positive and ordered")
        if self.canvas_padding < 0:
            raise ValueError("canvas_padding must be non-negative")
        if not 0 <= self.background_min <= self.background_max <= 255:
            raise ValueError("background range must be within 0..255")

    def to_dict(self) -> dict[str, float | int]:
        """Return JSON-serializable settings for the research manifest."""
        return asdict(self)


def apply_capture_augmentation(
    image: Image.Image,
    rng: random.Random,
    config: AugmentationConfig,
) -> tuple[Image.Image, dict[str, float | list[int]]]:
    """Apply a synthetic background, rotation, and brightness variation.

    Args:
        image: Base QR image generated in memory.
        rng: Seeded random-number generator owned by the calling run.
        config: Bounds controlling each transform.

    Returns:
        The augmented RGB image and the exact sampled values used for it.
    """
    config.validate()
    qr_image = image.convert("RGB")

    background = tuple(
        rng.randint(config.background_min, config.background_max) for _ in range(3)
    )
    brightness = rng.uniform(config.brightness_min, config.brightness_max)
    rotation = rng.uniform(-config.rotation_degrees, config.rotation_degrees)

    qr_image = ImageEnhance.Brightness(qr_image).enhance(brightness)
    qr_image = qr_image.rotate(
        rotation,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=background,
    )

    padding = config.canvas_padding
    canvas = Image.new(
        "RGB",
        (qr_image.width + 2 * padding, qr_image.height + 2 * padding),
        background,
    )
    canvas.paste(qr_image, (padding, padding))

    sampled = {
        "rotation_degrees": round(rotation, 4),
        "brightness_factor": round(brightness, 4),
        "background_rgb": list(background),
    }
    return canvas, sampled

