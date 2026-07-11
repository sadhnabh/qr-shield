"""Error Level Analysis (ELA) for QR-Shield images.

ELA resaves an image at a known JPEG quality and measures the per-pixel change.
Regions with different compression histories can produce different error levels.
The score here is an explainable image-wide baseline, not a fraud verdict by itself.
"""

from __future__ import annotations

import argparse
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageChops, ImageEnhance


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "ela"


@dataclass(frozen=True)
class ELAResult:
    """Computed ELA measurements and display-ready images."""

    score: float
    mean_error: float
    max_error: int
    difference: Image.Image
    heatmap: Image.Image


def _load_rgb(image_or_path: Image.Image | str | Path) -> Image.Image:
    """Load an input without retaining an open file handle."""
    if isinstance(image_or_path, Image.Image):
        return image_or_path.convert("RGB")
    with Image.open(image_or_path) as image:
        return image.convert("RGB")


def analyze_ela(
    image_or_path: Image.Image | str | Path,
    *,
    jpeg_quality: int = 90,
    heatmap_gain: float | None = None,
) -> ELAResult:
    """Recompress an image and return its ELA score and heatmap.

    Args:
        image_or_path: Pillow image or path to an image file.
        jpeg_quality: Known JPEG recompression quality in the range 1..95.
        heatmap_gain: Optional display multiplier. If omitted, the largest channel
            difference is scaled to 255. This changes visualization only, never
            the numerical score.

    Returns:
        An ``ELAResult`` whose score is mean absolute RGB error divided by 255.
    """
    if not 1 <= jpeg_quality <= 95:
        raise ValueError("jpeg_quality must be between 1 and 95")
    if heatmap_gain is not None and heatmap_gain <= 0:
        raise ValueError("heatmap_gain must be positive")

    original = _load_rgb(image_or_path)
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=jpeg_quality)
    buffer.seek(0)
    with Image.open(buffer) as encoded:
        recompressed = encoded.convert("RGB")

    difference = ImageChops.difference(original, recompressed)
    histogram = difference.histogram()
    channel_value_total = sum(
        count * (bin_index % 256) for bin_index, count in enumerate(histogram)
    )
    channel_count = original.width * original.height * 3
    mean_error = channel_value_total / channel_count
    max_error = max(channel_max for _, channel_max in difference.getextrema())
    score = mean_error / 255.0

    display_gain = heatmap_gain
    if display_gain is None:
        display_gain = 255.0 / max(1, max_error)
    heatmap = ImageEnhance.Brightness(difference).enhance(display_gain)

    return ELAResult(
        score=score,
        mean_error=mean_error,
        max_error=max_error,
        difference=difference,
        heatmap=heatmap,
    )


def save_ela_heatmap(
    result: ELAResult,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Save a heatmap, refusing replacement unless explicitly requested in code."""
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    result.heatmap.save(path, format="PNG", optimize=True)
    return path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments without reading or writing images."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+", help="input image paths")
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality 1..95")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Analyze images, save heatmaps, and print measurements."""
    args = parse_args(argv)
    outputs = [args.output_dir / f"{path.stem}_ela.png" for path in args.images]
    conflicts = [path for path in outputs if path.exists()]
    if conflicts:
        raise FileExistsError(f"Refusing to overwrite existing file: {conflicts[0]}")

    for image_path, output_path in zip(args.images, outputs):
        result = analyze_ela(image_path, jpeg_quality=args.quality)
        save_ela_heatmap(result, output_path)
        print(
            f"{image_path}: score={result.score:.6f}, "
            f"mean_error={result.mean_error:.4f}, max_error={result.max_error}, "
            f"heatmap={output_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

