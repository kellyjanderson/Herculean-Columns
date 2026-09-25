from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import cast

import trimesh

from ..config import HerculeanConfig
from ..export import export_result
from ..inspection import inspect_pair
from ..materialize import SolidMaterializer, admit_source
from .definitions import FIXTURES, fixture_graph, fixture_mesh


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def generate(destination: Path) -> dict[str, object]:
    destination.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for definition in FIXTURES:
        fixture_dir = destination / definition.fixture_id
        fixture_dir.mkdir()
        source = fixture_dir / "source.stl"
        source.write_bytes(cast(bytes, fixture_mesh(definition).export(file_type="stl")))
        percentages = (5.0, 10.0, 15.0) if definition.fixture_id == "convex-box" else (10.0,)
        variants: list[dict[str, object]] = []
        for percent in percentages:
            config = HerculeanConfig(infill_percent=percent, budget_tolerance_percent=100.0, mesh_resolution_mm=1.0)
            result = SolidMaterializer(config).materialize(admit_source(source, units="mm"), fixture_graph(definition, percent))
            stl, manifest, preview = export_result(result, source, fixture_dir)
            exported = json.loads(manifest.read_text(encoding="utf-8"))
            exported["source"]["path"] = "source.stl"
            exported["output"]["stl"] = stl.name
            exported["output"]["preview_svg"] = preview.name
            manifest.write_text(json.dumps(exported, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            inspection = inspect_pair(source, stl, definition.acceptance_tolerance_mm)
            variants.append({"infill_percent": percent, "achieved_infill_percent": result.report.achieved_infill_percent, "configuration_sha256": result.report.configuration_sha256, "stl": stl.name, "manifest": manifest.name, "preview": preview.name, "inspection": inspection})
        fixture_manifest = {
            "schema_version": 1,
            "fixture_id": definition.fixture_id,
            "dimensions_mm": definition.dimensions_mm,
            "purpose": definition.purpose,
            "physical_setup": definition.physical_setup,
            "critical_surfaces": definition.critical_surfaces,
            "label": definition.label,
            "build_orientation": definition.build_orientation,
            "expected_component_count": definition.expected_component_count,
            "expected_graph_properties": definition.expected_graph_properties,
            "acceptance_tolerance_mm": definition.acceptance_tolerance_mm,
            "provenance": {"generator": "herculean_columns.fixtures.corpus", "source_kind": "parametric", "units": "mm"},
            "variants": variants,
        }
        _write_json(fixture_dir / "fixture.json", fixture_manifest)
        reports.append(fixture_manifest)
    hashes = {str(path.relative_to(destination)): sha256(path.read_bytes()).hexdigest() for path in sorted(destination.rglob("*")) if path.is_file()}
    _write_json(destination / "hashes.json", {"schema_version": 1, "sha256": hashes})
    _write_json(destination / "geometry-report.json", {"schema_version": 1, "fixtures": reports})
    return {"fixtures": len(reports), "files": len(hashes) + 2, "hashes": hashes}


def regenerate_and_validate(committed: Path) -> dict[str, object]:
    expected = cast(dict[str, str], json.loads((committed / "hashes.json").read_text(encoding="utf-8"))["sha256"])
    committed_actual = {
        str(path.relative_to(committed)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(committed.rglob("*"))
        if path.is_file() and path.name not in {"hashes.json", "geometry-report.json"}
    }
    if committed_actual != expected:
        raise ValueError("fixture corpus differs: committed artifact hashes do not match hashes.json")
    with tempfile.TemporaryDirectory(prefix="hc-fixtures-") as raw:
        candidate = Path(raw) / "generated"
        report = generate(candidate)
        actual = cast(dict[str, str], report["hashes"])
        if expected != actual:
            missing = sorted(set(expected) - set(actual)); extra = sorted(set(actual) - set(expected))
            changed = sorted(key for key in set(expected) & set(actual) if expected[key] != actual[key])
            raise ValueError(f"fixture corpus differs: missing={missing}, extra={extra}, changed={changed}")
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or validate the deterministic HC fixture corpus")
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    report = generate(args.path) if args.command == "generate" else regenerate_and_validate(args.path)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
