from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
import numpy as np
import trimesh

from herculean_columns import (
    EdgeKind,
    HerculeanConfig,
    SolidMaterializer,
    StructuralGraph,
    admit_source,
    export_result,
    readback_stl,
)


def _materialized(tmp_path: Path):  # type: ignore[no-untyped-def]
    source_path = tmp_path / "source.stl"
    source_path.write_bytes(trimesh.creation.box((16.0, 16.0, 16.0)).export(file_type="stl"))
    graph = StructuralGraph()
    a = graph.add_node((-7.0, 0.0, 0.0), shell_anchor=True, grounded=True)
    b = graph.add_node((7.0, 0.0, 0.0), shell_anchor=True, grounded=True)
    graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    config = HerculeanConfig(infill_percent=8, budget_tolerance_percent=10, member_radius_mm=0.6, junction_radius_mm=0.85, mesh_resolution_mm=1.0)
    return source_path, SolidMaterializer(config).materialize(admit_source(source_path, units="mm"), graph)


@pytest.mark.export
def test_stl_manifest_preview_and_independent_readback_are_bound(tmp_path: Path) -> None:
    source, result = _materialized(tmp_path)
    before = source.read_bytes()
    stl, manifest, preview = export_result(result, source, tmp_path / "out")
    evidence = readback_stl(str(stl))
    report = json.loads(manifest.read_text())
    assert evidence.volume_mm3 > 0.0
    assert evidence.component_count == 1
    assert evidence.watertight and evidence.winding_consistent
    assert np.allclose(evidence.bounds_mm, result.body.bounds, atol=1e-6)
    assert report["output"]["stl_sha256"] == sha256(stl.read_bytes()).hexdigest()
    assert report["output"]["preview_sha256"] == sha256(preview.read_bytes()).hexdigest()
    assert report["output"]["three_mf"]["produced"] is False
    assert source.read_bytes() == before


@pytest.mark.export
def test_deterministic_inputs_have_stable_artifact_hashes(tmp_path: Path) -> None:
    source, first = _materialized(tmp_path)
    one = export_result(first, source, tmp_path / "one")
    source_two = admit_source(source, units="mm")
    graph = StructuralGraph()
    a = graph.add_node((-7.0, 0.0, 0.0), shell_anchor=True, grounded=True)
    b = graph.add_node((7.0, 0.0, 0.0), shell_anchor=True, grounded=True)
    graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    config = HerculeanConfig(infill_percent=8, budget_tolerance_percent=10, member_radius_mm=0.6, junction_radius_mm=0.85, mesh_resolution_mm=1.0)
    second = SolidMaterializer(config).materialize(source_two, graph)
    two = export_result(second, source, tmp_path / "two")
    assert sha256(one[0].read_bytes()).hexdigest() == sha256(two[0].read_bytes()).hexdigest()
    assert sha256(one[2].read_bytes()).hexdigest() == sha256(two[2].read_bytes()).hexdigest()
