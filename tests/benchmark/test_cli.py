from __future__ import annotations

import json
from pathlib import Path

from herculean_columns.benchmark import cli


def test_orca_fallback_does_not_require_creality_gui_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "materialization.json"
    manifest.write_text(
        json.dumps({"requested_infill_percent": 5, "achieved_infill_percent": 5,
                    "configuration": {}, "structural_member_volume_mm3": 1,
                    "print_support_member_volume_mm3": 0}),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class Backend:
        def __init__(self, executable: Path) -> None:
            captured["executable"] = executable

    class Runner:
        def __init__(self, backend, profiles, output, *, fallback_evidence=None) -> None:
            captured["fallback_evidence"] = fallback_evidence

        def run(self, variants, *, timeout_seconds):
            captured["variant_count"] = len(variants)
            return tmp_path / "result"

    monkeypatch.setattr(cli, "OrcaSlicerBackend", Backend)
    monkeypatch.setattr(cli, "CrealityPrintBackend", lambda *_: (_ for _ in ()).throw(
        AssertionError("Creality identity must not be required for Orca fallback")
    ))
    monkeypatch.setattr(cli, "BenchmarkRunner", Runner)
    monkeypatch.setattr(
        "sys.argv",
        ["benchmark", "--source", str(tmp_path / "source.stl"),
         "--herculean", str(tmp_path / "body.stl"), "--materialization-manifest",
         str(manifest), "--infill-percent", "5", "--output", str(tmp_path / "out"),
         "--backend", "orca", "--fallback-from-creality-failure"],
    )

    assert cli.main() == 0
    assert captured["variant_count"] == 5
    assert captured["fallback_evidence"] == {
        "decision": "orca_after_creality_qualification_failure",
        "creality_gui_compatibility": "unverified",
    }
