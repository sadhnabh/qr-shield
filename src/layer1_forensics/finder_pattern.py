"""QR outer-corner and finder-pattern geometry consistency checks."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from src.utils.image_io import ImageInput, load_bgr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "finder_geometry"


@dataclass(frozen=True)
class FinderCandidate:
    """Center and area of one nested square finder-pattern candidate."""

    center: tuple[float, float]
    area: float


@dataclass(frozen=True)
class FinderGeometryResult:
    """Geometry measurements used as future classifier features."""

    qr_detected: float
    finder_count: int
    quadrilateral_angle_error: float
    opposite_side_error: float
    diagonal_error: float
    finder_leg_ratio_error: float
    finder_pythagorean_error: float
    finder_size_variation: float
    irregularity_score: float
    qr_corners: tuple[tuple[float, float], ...]
    finder_centers: tuple[tuple[float, float], ...]

    def feature_dict(self) -> dict[str, float | int]:
        """Return numerical model features without drawing metadata."""
        values = asdict(self)
        values.pop("qr_corners")
        values.pop("finder_centers")
        return values


def quadrilateral_features(corners: np.ndarray) -> tuple[float, float, float]:
    """Return angle, opposite-side, and diagonal errors for four ordered corners."""
    points = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    sides = [float(np.linalg.norm(points[(i + 1) % 4] - points[i])) for i in range(4)]
    if min(sides) <= 1e-6:
        return 1.0, 1.0, 1.0

    cosines: list[float] = []
    for index in range(4):
        previous = points[(index - 1) % 4] - points[index]
        following = points[(index + 1) % 4] - points[index]
        cosine = abs(float(np.dot(previous, following))) / (
            float(np.linalg.norm(previous) * np.linalg.norm(following)) + 1e-9
        )
        cosines.append(cosine)
    angle_error = float(np.mean(cosines))
    opposite_error = 0.5 * (
        abs(sides[0] - sides[2]) / max(sides[0], sides[2])
        + abs(sides[1] - sides[3]) / max(sides[1], sides[3])
    )
    diagonal_a = float(np.linalg.norm(points[2] - points[0]))
    diagonal_b = float(np.linalg.norm(points[3] - points[1]))
    diagonal_error = abs(diagonal_a - diagonal_b) / max(diagonal_a, diagonal_b, 1e-9)
    return angle_error, opposite_error, diagonal_error


def finder_triangle_features(
    candidates: Sequence[FinderCandidate],
) -> tuple[float, float, float]:
    """Measure isosceles-right triangle and finder-size consistency errors."""
    if len(candidates) != 3:
        return 1.0, 1.0, 1.0
    centers = [np.asarray(candidate.center, dtype=np.float64) for candidate in candidates]
    distances = sorted(
        float(np.linalg.norm(centers[first] - centers[second]))
        for first, second in ((0, 1), (0, 2), (1, 2))
    )
    if distances[1] <= 1e-6 or distances[2] <= 1e-6:
        return 1.0, 1.0, 1.0
    leg_ratio_error = abs(distances[0] - distances[1]) / distances[1]
    pythagorean_error = abs(
        distances[2] ** 2 - distances[0] ** 2 - distances[1] ** 2
    ) / (distances[2] ** 2)
    areas = np.asarray([candidate.area for candidate in candidates], dtype=np.float64)
    size_variation = float(areas.std() / max(float(areas.mean()), 1e-9))
    return leg_ratio_error, pythagorean_error, size_variation


def _nested_depth(hierarchy: np.ndarray, contour_index: int) -> int:
    """Count successive first-child contours in an OpenCV hierarchy."""
    depth = 0
    child = int(hierarchy[contour_index][2])
    while child >= 0:
        depth += 1
        child = int(hierarchy[child][2])
    return depth


def _find_candidates(gray: np.ndarray) -> list[FinderCandidate]:
    """Locate nested, approximately square black/white finder structures."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    contours, hierarchy_raw = cv2.findContours(
        binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy_raw is None:
        return []
    hierarchy = hierarchy_raw[0]
    minimum_area = gray.shape[0] * gray.shape[1] * 0.0004
    raw: list[FinderCandidate] = []
    for index, contour in enumerate(contours):
        area = float(cv2.contourArea(contour))
        # With binary inversion, a standard finder often appears as three nested
        # contour levels (outer contour plus two successive children).
        if area < minimum_area or _nested_depth(hierarchy, index) < 2:
            continue
        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.08 * perimeter, True)
        if len(approximation) != 4 or not cv2.isContourConvex(approximation):
            continue
        x, y, width, height = cv2.boundingRect(approximation)
        aspect_ratio = width / max(height, 1)
        if not 0.65 <= aspect_ratio <= 1.35:
            continue
        moments = cv2.moments(contour)
        if abs(moments["m00"]) <= 1e-9:
            continue
        center = (
            float(moments["m10"] / moments["m00"]),
            float(moments["m01"] / moments["m00"]),
        )
        raw.append(FinderCandidate(center=center, area=area))

    # Nested contours can describe the same finder. Keep its largest outer square.
    candidates: list[FinderCandidate] = []
    for candidate in sorted(raw, key=lambda item: item.area, reverse=True):
        duplicate = any(
            np.linalg.norm(
                np.asarray(candidate.center) - np.asarray(existing.center)
            )
            < 0.08 * np.sqrt(existing.area)
            for existing in candidates
        )
        if not duplicate:
            candidates.append(candidate)
    return candidates


def _best_finder_triplet(candidates: Sequence[FinderCandidate]) -> list[FinderCandidate]:
    """Choose the three candidates closest to expected finder geometry."""
    if len(candidates) <= 3:
        return list(candidates)
    best: tuple[float, tuple[FinderCandidate, ...]] | None = None
    for triplet in itertools.combinations(candidates[:10], 3):
        errors = finder_triangle_features(triplet)
        cost = sum(errors)
        if best is None or cost < best[0]:
            best = (cost, triplet)
    return list(best[1]) if best is not None else []


def analyze_finder_geometry(image_or_path: ImageInput) -> FinderGeometryResult:
    """Analyze outer QR geometry and the three nested finder patterns."""
    bgr = load_bgr(image_or_path)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    detector = cv2.QRCodeDetector()
    detected, points = detector.detect(gray)
    if detected and points is not None:
        corners_array = np.asarray(points, dtype=np.float32).reshape(4, 2)
        angle_error, opposite_error, diagonal_error = quadrilateral_features(
            corners_array
        )
        corners = tuple(tuple(map(float, point)) for point in corners_array)
    else:
        angle_error = opposite_error = diagonal_error = 1.0
        corners = ()

    all_candidates = _find_candidates(gray)
    selected = _best_finder_triplet(all_candidates)
    leg_error, pythagorean_error, size_variation = finder_triangle_features(selected)
    count_error = min(1.0, abs(len(all_candidates) - 3) / 3.0)
    quadrilateral_error = (angle_error + opposite_error + diagonal_error) / 3.0
    finder_error = (leg_error + pythagorean_error + min(size_variation, 1.0)) / 3.0
    irregularity = min(
        1.0,
        0.35 * quadrilateral_error
        + 0.50 * finder_error
        + 0.15 * count_error,
    )
    return FinderGeometryResult(
        qr_detected=float(bool(detected)),
        finder_count=len(all_candidates),
        quadrilateral_angle_error=angle_error,
        opposite_side_error=opposite_error,
        diagonal_error=diagonal_error,
        finder_leg_ratio_error=leg_error,
        finder_pythagorean_error=pythagorean_error,
        finder_size_variation=size_variation,
        irregularity_score=irregularity,
        qr_corners=corners,
        finder_centers=tuple(candidate.center for candidate in selected),
    )


def draw_geometry_overlay(
    image_or_path: ImageInput,
    result: FinderGeometryResult,
) -> np.ndarray:
    """Draw detected outer corners and finder centers for human validation."""
    output = load_bgr(image_or_path)
    if result.qr_corners:
        corners = np.asarray(result.qr_corners, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(output, [corners], True, (0, 200, 0), 3)
    for index, center in enumerate(result.finder_centers, start=1):
        point = tuple(round(value) for value in center)
        cv2.circle(output, point, 8, (0, 0, 255), 2)
        cv2.putText(
            output,
            f"F{index}",
            (point[0] + 8, point[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return output


def save_geometry_overlay(
    overlay: np.ndarray,
    output_path: str | Path,
) -> Path:
    """Save a validation overlay without replacing an existing file."""
    path = Path(output_path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), overlay):
        raise OSError(f"Could not write geometry overlay: {path}")
    return path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI inputs without analyzing images."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+", help="input image paths")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Print geometry features and save visual validation overlays."""
    args = parse_args(argv)
    outputs = [args.output_dir / f"{path.stem}_geometry.png" for path in args.images]
    conflicts = [path for path in outputs if path.exists()]
    if conflicts:
        raise FileExistsError(f"Refusing to overwrite existing file: {conflicts[0]}")
    for image_path, output_path in zip(args.images, outputs):
        result = analyze_finder_geometry(image_path)
        overlay = draw_geometry_overlay(image_path, result)
        save_geometry_overlay(overlay, output_path)
        print(
            json.dumps(
                {
                    "image": str(image_path),
                    **result.feature_dict(),
                    "overlay": str(output_path),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
