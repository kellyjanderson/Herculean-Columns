from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from herculean_columns.benchmark.compatibility import CompatibilityEvidenceError, create_creality_import_receipt, model_sha256, validate_creality_import_receipt
from herculean_columns.slicers import BackendIdentity


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


def test_receipt_rejects_identity_that_differs_from_installed_creality(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(_receipt(model)), encoding="utf-8")
    installed = BackendIdentity("creality-print", "/Applications/Creality Print.app", "b" * 64, "7.2.0", "Creality-01.10.00.00", True)

    with pytest.raises(CompatibilityEvidenceError, match="installed application"):
        validate_creality_import_receipt(receipt, model, installed)


def test_guided_receipt_requires_exact_hash_bound_human_confirmations(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    identity = BackendIdentity("creality-print", "/Applications/Creality Print.app", "a" * 64, "7.1.1.4472", "Creality-01.09.03.50", True)
    token = model_sha256(model)[:12]
    answers = iter(["fixture operator", f"IMPORT {token}", f"PREVIEW {token}"])

    parsed = create_creality_import_receipt(
        model,
        receipt,
        identity,
        prompt=lambda _: next(answers),
        now=lambda: datetime(2026, 9, 25, 19, 0, tzinfo=timezone.utc),
    )

    assert parsed.model_sha256 == model_sha256(model)
    assert parsed.observed_at == "2026-09-25T19:00:00+00:00"
    assert receipt.read_text(encoding="utf-8").endswith("\n")


def test_guided_receipt_writes_nothing_without_preview_confirmation(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    identity = BackendIdentity("creality-print", "/Applications/Creality Print.app", "a" * 64, "7.1.1.4472", "Creality-01.09.03.50", True)
    token = model_sha256(model)[:12]
    answers = iter(["fixture operator", f"IMPORT {token}", "no"])

    with pytest.raises(CompatibilityEvidenceError, match="Preview was not human-confirmed"):
        create_creality_import_receipt(model, receipt, identity, prompt=lambda _: next(answers))

    assert not receipt.exists()


def test_guided_receipt_refuses_to_overwrite_prior_evidence(tmp_path: Path) -> None:
    model = tmp_path / "model.stl"
    model.write_bytes(b"solid exact\nendsolid exact\n")
    receipt = tmp_path / "receipt.json"
    receipt.write_text("prior evidence\n", encoding="utf-8")
    identity = BackendIdentity("creality-print", "/Applications/Creality Print.app", "a" * 64, "7.1.1.4472", "Creality-01.09.03.50", True)

    with pytest.raises(CompatibilityEvidenceError, match="Refusing to overwrite"):
        create_creality_import_receipt(model, receipt, identity, prompt=lambda _: "unused")

    assert receipt.read_text(encoding="utf-8") == "prior evidence\n"
