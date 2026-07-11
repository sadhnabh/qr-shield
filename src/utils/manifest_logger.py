"""Append-only CSV logging for synthetic dataset-generation runs."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


FIELDNAMES = ("timestamp_utc", "generator", "count", "parameters", "output_dir")


def log_generation_run(
    manifest_path: Path,
    *,
    generator: str,
    count: int,
    parameters: Mapping[str, Any],
    output_dir: Path,
) -> None:
    """Append one generation-run record, creating the CSV header if needed."""
    if count < 1:
        raise ValueError("count must be at least 1")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not manifest_path.exists() or manifest_path.stat().st_size == 0
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generator": generator,
        "count": count,
        "parameters": json.dumps(parameters, sort_keys=True, separators=(",", ":")),
        "output_dir": output_dir.as_posix(),
    }

    with manifest_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if needs_header:
            writer.writeheader()
        writer.writerow(record)

