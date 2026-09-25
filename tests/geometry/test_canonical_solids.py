from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh

from herculean_columns import EdgeKind, HerculeanConfig, SolidMaterializer, StructuralGraph, admit_source
from tests.materialize.helpers import write_tapered


def _write(mesh: trimesh.Trimesh, path: Path) -> Path:
    path.write_bytes(mesh.export(file_type="stl"))
    return path


def _path(points: list[tuple[float, float, float]]) -> StructuralGraph:
    graph = StructuralGraph()
    nodes = [graph.add_node(point, shell_anchor=index in {0, len(points) - 1}, grounded=True) for index, point in enumerate(points)]
    for a, b in zip(nodes, nodes[1:]):
        graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    return graph


def _config() -> HerculeanConfig:
    return HerculeanConfig(
        infill_percent=8.0,
        member_radius_mm=0.6,
        junction_radius_mm=0.85,
        mesh_resolution_mm=1.0,
        budget_tolerance_percent=10.0,
    )


@pytest.mark.geometry
@pytest.mark.parametrize("fixture", ["convex_box", "concave_l", "tapered"])
def test_canonical_fixture_materializes_as_one_exterior_preserving_body(tmp_path: Path, fixture: str) -> None:
    if fixture == "convex_box":
        mesh = trimesh.creation.box((20.0, 20.0, 20.0))
        graph = _path([(-9.0, 0.0, 0.0), (0.0, 0.0, 0.0), (9.0, 0.0, 0.0)])
    elif fixture == "concave_l":
        horizontal = trimesh.creation.box((20.0, 8.0, 16.0), transform=trimesh.transformations.translation_matrix((0.0, -6.0, 0.0)))
        vertical = trimesh.creation.box((8.0, 12.0, 16.0), transform=trimesh.transformations.translation_matrix((-6.0, 4.0, 0.0)))
        mesh = trimesh.boolean.union([horizontal, vertical], engine="manifold")
        graph = _path([(9.0, -6.0, 0.0), (-6.0, -6.0, 0.0), (-6.0, 9.0, 0.0)])
    else:
        mesh = trimesh.load_mesh(write_tapered(tmp_path / "tapered-source.stl"), process=True)
        assert isinstance(mesh, trimesh.Trimesh)
        graph = _path([(0.0, 0.0, -9.0), (0.0, 0.0, 0.0), (0.0, 0.0, 9.0)])
    source_path = _write(mesh, tmp_path / f"{fixture}.stl")
    before = source_path.read_bytes()
    source = admit_source(source_path, units="mm")
    result = SolidMaterializer(_config()).materialize(source, graph)
    assert result.report.validation["component_count"] == 1
    assert result.body.is_watertight and result.body.is_winding_consistent
    assert result.body.volume > 0.0
    assert np.allclose(result.body.bounds, source.mesh.bounds, atol=_config().exterior_tolerance_mm)
    assert source_path.read_bytes() == before
    independently_recomputed = 100.0 * result.report.unioned_internal_volume_mm3 / result.report.legal_domain_volume_mm3
    assert result.report.achieved_infill_percent == pytest.approx(independently_recomputed)


@pytest.mark.geometry
def test_concave_escape_is_clipped_and_rejected_when_it_disconnects(tmp_path: Path) -> None:
    horizontal = trimesh.creation.box((20.0, 8.0, 16.0), transform=trimesh.transformations.translation_matrix((0.0, -6.0, 0.0)))
    vertical = trimesh.creation.box((8.0, 12.0, 16.0), transform=trimesh.transformations.translation_matrix((-6.0, 4.0, 0.0)))
    mesh = trimesh.boolean.union([horizontal, vertical], engine="manifold")
    source = admit_source(_write(mesh, tmp_path / "concave.stl"), units="mm")
    graph = _path([(9.0, -6.0, 0.0), (-6.0, 9.0, 0.0)])
    from herculean_columns import MaterializationError
    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(_config()).materialize(source, graph)
    assert raised.value.failure.code in {"DISCONNECTED_STRUTS", "MULTIPLE_OUTPUT_BODIES"}
