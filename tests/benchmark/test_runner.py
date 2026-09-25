from __future__ import annotations

import json
from pathlib import Path

import pytest

from herculean_columns.benchmark.run import BenchmarkFailure, BenchmarkRunner, Variant
from herculean_columns.slicers import FakeSlicerBackend


def _profile_root(tmp_path: Path) -> Path:
    root = tmp_path / "profiles"; root.mkdir()
    for kind in ("machine", "process", "filament"):
        (root / f"{kind}.json").write_text(json.dumps({"type": kind, "from": "user", "name": f"HC-VIRTUAL-FDM-V1-{kind}"}), encoding="utf-8")
    (root / "profile.json").write_text(json.dumps({"profile_id": "HC-VIRTUAL-FDM-V1", "machine": "machine.json", "process": "process.json", "filament": "filament.json"}), encoding="utf-8")
    return root


def _variants(tmp_path: Path) -> list[Variant]:
    source = tmp_path / "source.stl"; source.write_bytes(b"source")
    body = tmp_path / "body.stl"; body.write_bytes(b"body")
    return [Variant("herculean", "rectilinear", body, 15, 12, {}, 20, 0), *(Variant(name, name, source, 15) for name in ("lightning", "rectilinear", "cubic", "gyroid"))]


def test_fake_cannot_enter_comparison_evidence(tmp_path: Path) -> None:
    runner = BenchmarkRunner(FakeSlicerBackend(), _profile_root(tmp_path), tmp_path / "out")
    with pytest.raises(BenchmarkFailure, match="Non-authoritative"):
        runner.run(_variants(tmp_path))


def test_handoff_keeps_requested_percentage_distinct(tmp_path: Path) -> None:
    variant = _variants(tmp_path)[0]
    assert variant.requested_percent == 15
    assert variant.slicer_infill_percent == 0


def test_exact_matrix_required(tmp_path: Path) -> None:
    runner = BenchmarkRunner(FakeSlicerBackend(), _profile_root(tmp_path), tmp_path / "out")
    with pytest.raises(BenchmarkFailure, match="exact five"):
        runner.run(_variants(tmp_path)[:-1])


def test_stale_content_addressed_destination_is_rejected(tmp_path: Path) -> None:
    class AuthoritativeFake(FakeSlicerBackend):
        def discover_identity(self):  # type: ignore[no-untyped-def]
            return super().discover_identity().__class__("fixture", "fixture", "0" * 64, "1", "fixture-1", True)
    runner = BenchmarkRunner(AuthoritativeFake(), _profile_root(tmp_path), tmp_path / "out")
    runner.run(_variants(tmp_path))
    with pytest.raises(BenchmarkFailure, match="stale artifact reuse"):
        runner.run(_variants(tmp_path))


def test_fallback_evidence_is_content_addressed_and_recorded(tmp_path: Path) -> None:
    class AuthoritativeFake(FakeSlicerBackend):
        def discover_identity(self):  # type: ignore[no-untyped-def]
            return super().discover_identity().__class__("fixture", "fixture", "0" * 64, "1", "fixture-1", True)

    evidence = {"decision": "orca_after_creality_qualification_failure", "creality_import_receipt": {"model_sha256": "a" * 64}}
    runner = BenchmarkRunner(AuthoritativeFake(), _profile_root(tmp_path), tmp_path / "out", fallback_evidence=evidence)
    result = runner.run(_variants(tmp_path))
    manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["fallback_evidence"] == evidence
