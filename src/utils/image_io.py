"""Small image-loading helpers shared by computer-vision modules."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ImageInput = Image.Image | np.ndarray | str | Path


def load_bgr(image_or_path: ImageInput) -> np.ndarray:
    """Return a copied three-channel BGR image from common input types."""
    if isinstance(image_or_path, np.ndarray):
        array = image_or_path.copy()
        if array.ndim == 2:
            return cv2.cvtColor(array, cv2.COLOR_GRAY2BGR)
        if array.ndim == 3 and array.shape[2] == 3:
            return array
        if array.ndim == 3 and array.shape[2] == 4:
            return cv2.cvtColor(array, cv2.COLOR_BGRA2BGR)
        raise ValueError("NumPy image must be grayscale, BGR, or BGRA")

    if isinstance(image_or_path, Image.Image):
        rgb = np.asarray(image_or_path.convert("RGB"))
    else:
        with Image.open(image_or_path) as image:
            rgb = np.asarray(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def load_gray(image_or_path: ImageInput) -> np.ndarray:
    """Return an 8-bit grayscale image."""
    return cv2.cvtColor(load_bgr(image_or_path), cv2.COLOR_BGR2GRAY)

