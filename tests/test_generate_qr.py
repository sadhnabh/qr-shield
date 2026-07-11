import csv
import json

import pytest

from src.data_generation.generate_qr import (
    build_fictional_payload,
    generate_genuine_qrs,
)


def test_payload_contains_only_fictional_identity():
    payload, fictional_id = build_fictional_payload(3, "Amber Kite Books")

    assert payload.startswith("upi://pay?")
    assert fictional_id == "demo00003@qrshieldtest"
    assert "Amber+Kite+Books" in payload


def test_generation_writes_images_and_one_manifest_record(tmp_path):
    output_dir = tmp_path / "genuine"
    manifest = tmp_path / "manifest.csv"

    paths = generate_genuine_qrs(2, output_dir, manifest, seed=11)

    assert len(paths) == 2
    assert all(path.exists() for path in paths)
    with manifest.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert len(records) == 1
    assert records[0]["generator"] == "genuine_qr"
    assert records[0]["count"] == "2"
    assert json.loads(records[0]["parameters"])["seed"] == 11


def test_generation_refuses_to_overwrite_existing_batch(tmp_path):
    output_dir = tmp_path / "genuine"
    manifest = tmp_path / "manifest.csv"
    generate_genuine_qrs(1, output_dir, manifest, seed=9)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        generate_genuine_qrs(1, output_dir, manifest, seed=9)

