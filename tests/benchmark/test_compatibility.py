from __future__ import annotations

import json
from pathlib import Path

import pytest

from herculean_columns.benchmark.compatibility import CompatibilityEvidenceError, model_sha256, validate_creality_import_receipt


def _receipt(model: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "model_sha256": model_sha256(model),
        "bundle_version": "7.1.1.4472",
        "engine_version": "Creality-01.09.03.50",
        "observer": "fixture operator",
        "observed_at": "2026-09-25T12:00:00-07:00",
        "import_succeeded": True,
        "preview_succeeded": True,
    }


def test_receipt_is_bound_to_exact_model(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(_receipt(model)), encoding="utf-8")
    model.write_bytes(b"solid changed\nendsolid changed\n")
    with pytest.raises(CompatibilityEvidenceError, match="exact model"):
        validate_creality_import_receipt(receipt, model)


@pytest.mark.parametrize("field", ["import_succeeded", "preview_succeeded"])
def test_receipt_rejects_unconfirmed_gui_observation(tmp_path: Path, field: str) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    values = _receipt(model)
    values[field] = False
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(values), encoding="utf-8")
    with pytest.raises(CompatibilityEvidenceError, match="both be human-confirmed"):
        validate_creality_import_receipt(receipt, model)


def test_valid_receipt_preserves_creality_identity(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(_receipt(model)), encoding="utf-8")
    parsed = validate_creality_import_receipt(receipt, model)
    assert parsed.bundle_version == "7.1.1.4472"
    assert parsed.engine_version == "Creality-01.09.03.50"
