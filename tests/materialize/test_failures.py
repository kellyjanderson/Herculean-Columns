from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from herculean_columns import (
    EdgeKind,
    HerculeanConfig,
    MaterializationError,
    SolidMaterializer,
    SourceAdmissionError,
    StructuralGraph,
    admit_source,
)
from herculean_columns.materialize import FailureDetail


def _write(mesh: trimesh.Trimesh, path: Path) -> Path:
    path.write_bytes(mesh.export(file_type="stl"))
    return path


def _line_graph(a: tuple[float, float, float], b: tuple[float, float, float]) -> StructuralGraph:
    graph = StructuralGraph()
    first = graph.add_node(a, shell_anchor=True, grounded=True)
    second = graph.add_node(b, shell_anchor=True, grounded=True)
    graph.add_edge(first, second, EdgeKind.STRUCTURAL)
    return graph


@pytest.mark.materialize
def test_non_watertight_source_is_rejected(tmp_path: Path) -> None:
    mesh = trimesh.creation.box((10.0, 10.0, 10.0))
    mesh.update_faces(range(len(mesh.faces) - 1))
    with pytest.raises(SourceAdmissionError) as raised:
        admit_source(_write(mesh, tmp_path / "open.stl"), units="mm")
    assert raised.value.code == "NON_WATERTIGHT_SOURCE"


@pytest.mark.materialize
def test_unknown_units_are_rejected(tmp_path: Path) -> None:
    path = _write(trimesh.creation.box((10.0, 10.0, 10.0)), tmp_path / "box.stl")
    with pytest.raises(SourceAdmissionError) as raised:
        admit_source(path, units=None)
    assert raised.value.code == "UNKNOWN_UNITS"


@pytest.mark.materialize
def test_boolean_failure_is_structured(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((12.0, 12.0, 12.0)), tmp_path / "box.stl"), units="mm")

    def fail(_name: str, _meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
        raise MaterializationError(FailureDetail(code="BOOLEAN_FAILURE", message="injected"))

    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(HerculeanConfig(infill_percent=10), boolean=fail).materialize(
            source, _line_graph((-5.0, 0.0, 0.0), (5.0, 0.0, 0.0))
        )
    assert raised.value.failure.code == "BOOLEAN_FAILURE"


@pytest.mark.materialize
def test_zero_overlap_junction_is_rejected(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((12.0, 12.0, 12.0)), tmp_path / "box.stl"), units="mm")
    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(HerculeanConfig(infill_percent=10, member_radius_mm=0.5, junction_radius_mm=0.5)).materialize(
            source, _line_graph((-5.0, 0.0, 0.0), (5.0, 0.0, 0.0))
        )
    assert raised.value.failure.code == "ZERO_THICKNESS_JUNCTION"


@pytest.mark.materialize
def test_disconnected_graph_is_rejected_before_export(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((12.0, 12.0, 12.0)), tmp_path / "box.stl"), units="mm")
    graph = _line_graph((-5.0, -2.0, 0.0), (5.0, -2.0, 0.0))
    c = graph.add_node((-5.0, 2.0, 0.0))
    d = graph.add_node((5.0, 2.0, 0.0))
    graph.add_edge(c, d, EdgeKind.STRUCTURAL)
    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(HerculeanConfig(infill_percent=10, mesh_resolution_mm=1.0)).materialize(source, graph)
    assert raised.value.failure.code in {"DISCONNECTED_MEMBERS", "DISCONNECTED_STRUTS"}


@pytest.mark.materialize
def test_exterior_deviation_is_structured(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((12.0, 12.0, 12.0)), tmp_path / "box.stl"), units="mm")
    materializer = SolidMaterializer(HerculeanConfig(infill_percent=10))
    moved = source.mesh.copy()
    moved.apply_translation((1.0, 0.0, 0.0))
    graph = _line_graph((-5.0, 0.0, 0.0), (5.0, 0.0, 0.0))
    with pytest.raises(MaterializationError) as raised:
        materializer._validate(source, graph, source.mesh, source.mesh, moved)
    assert raised.value.failure.code == "EXTERIOR_DEVIATION"


@pytest.mark.materialize
def test_thin_source_cannot_hide_required_shell(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((20.0, 20.0, 1.0)), tmp_path / "thin.stl"), units="mm")
    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(HerculeanConfig(infill_percent=10)).materialize(source, _line_graph((-9.0, 0.0, 0.0), (9.0, 0.0, 0.0)))
    assert raised.value.failure.code == "THIN_FEATURE"


@pytest.mark.materialize
def test_union_volume_outside_density_tolerance_is_rejected(tmp_path: Path) -> None:
    source = admit_source(_write(trimesh.creation.box((20.0, 20.0, 20.0)), tmp_path / "box.stl"), units="mm")
    with pytest.raises(MaterializationError) as raised:
        SolidMaterializer(HerculeanConfig(infill_percent=25, budget_tolerance_percent=0.25, mesh_resolution_mm=1.0)).materialize(source, _line_graph((-9.0, 0.0, 0.0), (9.0, 0.0, 0.0)))
    assert raised.value.failure.code == "DENSITY_BUDGET_MISS"
