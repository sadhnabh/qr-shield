import csv
import json
import random

import pytest
from PIL import Image

from src.data_generation.generate_tampered import (
    OVERLAY_PROFILES,
    apply_sticker_overlay,
    generate_tampered_qrs,
)


def test_clean_overlay_is_deterministic():
    base = Image.new("RGB", (80, 80), "white")
    sticker = Image.new("RGB", (40, 40), "black")

    first, first_params = apply_sticker_overlay(
        base,
        sticker,
        qr_origin=(20, 20),
        qr_size=(40, 40),
        rng=random.Random(5),
        profile=OVERLAY_PROFILES["clean"],
    )
    second, second_params = apply_sticker_overlay(
        base,
        sticker,
        qr_origin=(20, 20),
        qr_size=(40, 40),
        rng=random.Random(5),
        profile=OVERLAY_PROFILES["clean"],
    )

    assert first.tobytes() == second.tobytes()
    assert first_params == second_params


def test_batch_alternates_difficulty_and_logs_identities(tmp_path):
    output_dir = tmp_path / "tampered"
    manifest = tmp_path / "manifest.csv"

    paths = generate_tampered_qrs(2, output_dir, manifest, seed=23)

    assert [path.name.rsplit("_", 1)[-1] for path in paths] == [
        "clean.png",
        "obvious.png",
    ]
    assert all(path.exists() for path in paths)
    with manifest.open(encoding="utf-8", newline="") as handle:
        record = next(csv.DictReader(handle))
    parameters = json.loads(record["parameters"])
    assert record["generator"] == "tampered_qr"
    assert [sample["difficulty"] for sample in parameters["samples"]] == [
        "clean",
        "obvious",
    ]
    assert all(
        sample["genuine_id"] != sample["attacker_id"]
        for sample in parameters["samples"]
    )


def test_batch_rejects_unknown_difficulty(tmp_path):
    with pytest.raises(ValueError, match="unknown difficulties"):
        generate_tampered_qrs(
            1,
            tmp_path / "tampered",
            tmp_path / "manifest.csv",
            difficulties=("impossible",),
        )

