from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, cast

import numpy as np
import trimesh

from ..model import EdgeKind, StructuralGraph


@dataclass(frozen=True)
class FixtureDefinition:
    fixture_id: str
    dimensions_mm: tuple[float, float, float]
    purpose: str
    physical_setup: str
    critical_surfaces: tuple[str, ...]
    build_orientation: tuple[float, float, float]
    expected_graph_properties: tuple[str, ...]
    acceptance_tolerance_mm: float = 0.08
    expected_component_count: int = 1
    label: str | None = None


FIXTURES = (
    FixtureDefinition("convex-box", (20.0, 20.0, 20.0), "containment, grounding, roof support, and compression", "compress between parallel platens on the Z faces", ("z_min", "z_max"), (0.0, 0.0, 1.0), ("single grounded component", "no escaped swept members")),
    FixtureDefinition("concave-l", (24.0, 24.0, 20.0), "illegal-chord and clipping-discontinuity detection", "inspect the re-entrant corner and compress on Z faces", ("z_min", "z_max", "reentrant_corner"), (0.0, 0.0, 1.0), ("no chord crosses the missing quadrant", "single grounded component")),
    FixtureDefinition("tapered-coupon", (20.0, 20.0, 24.0), "variable cross-section and identity stability", "compress between the parallel end faces", ("z_min", "z_max"), (0.0, 0.0, 1.0), ("stable monotonic identities", "members remain inside taper")),
    FixtureDefinition("three-point-bending-bar", (80.0, 12.0, 10.0), "repeatable three-point bending", "support at X=-30/+30 mm and load at X=0 on the top face", ("z_max", "support_lines"), (0.0, 0.0, 1.0), ("shell anchors span the bar", "single grounded component")),
    FixtureDefinition("torsion-keyed-prism", (50.0, 16.0, 19.0), "torsional coupling", "clamp the keyed X end faces and apply axial torque", ("x_min", "x_max", "key_flats"), (0.0, 0.0, 1.0), ("axial structural continuity", "single grounded component")),
    FixtureDefinition("shell-indentation-coupon", (36.0, 36.0, 12.0), "local shell-collapse resistance", "indent the center of the top face while supporting the perimeter", ("z_max_center", "bottom_perimeter"), (0.0, 0.0, 1.0), ("center-to-shell load path", "single grounded component")),
)


def _box(size: tuple[float, float, float]) -> trimesh.Trimesh:
    return cast(trimesh.Trimesh, trimesh.creation.box(extents=size))


def _concave_l() -> trimesh.Trimesh:
    a = _box((8.0, 24.0, 20.0)); a.apply_translation((-8.0, 0.0, 0.0))
    b = _box((24.0, 8.0, 20.0)); b.apply_translation((0.0, -8.0, 0.0))
    result = trimesh.boolean.union([a, b], engine="manifold")
    assert isinstance(result, trimesh.Trimesh)
    return result


def _taper() -> trimesh.Trimesh:
    angles = np.linspace(0.0, 2.0 * np.pi, 32, endpoint=False)
    lower = np.column_stack((10.0 * np.cos(angles), 10.0 * np.sin(angles), np.full(32, -12.0)))
    upper = np.column_stack((7.0 * np.cos(angles), 7.0 * np.sin(angles), np.full(32, 12.0)))
    vertices = np.vstack((lower, upper, [[0.0, 0.0, -12.0], [0.0, 0.0, 12.0]]))
    faces: list[tuple[int, int, int]] = []
    for i in range(32):
        n = (i + 1) % 32
        faces.extend(((i, n, 32 + n), (i, 32 + n, 32 + i), (64, n, i), (65, 32 + i, 32 + n)))
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=True)


def _torsion() -> trimesh.Trimesh:
    body = _box((50.0, 16.0, 16.0))
    key = _box((6.0, 4.0, 3.0)); key.apply_translation((-22.0, 0.0, 9.5))
    result = trimesh.boolean.union([body, key], engine="manifold")
    assert isinstance(result, trimesh.Trimesh)
    return result


_BUILDERS: dict[str, Callable[[], trimesh.Trimesh]] = {
    "convex-box": lambda: _box((20.0, 20.0, 20.0)),
    "concave-l": _concave_l,
    "tapered-coupon": _taper,
    "three-point-bending-bar": lambda: _box((80.0, 12.0, 10.0)),
    "torsion-keyed-prism": _torsion,
    "shell-indentation-coupon": lambda: _box((36.0, 36.0, 12.0)),
}


def fixture_mesh(definition: FixtureDefinition) -> trimesh.Trimesh:
    mesh = _BUILDERS[definition.fixture_id]()
    mesh.metadata["units"] = "mm"
    return mesh


def fixture_graph(definition: FixtureDefinition, infill_percent: float = 10.0) -> StructuralGraph:
    low, high = fixture_mesh(definition).bounds
    margin = 1.0
    graph = StructuralGraph()
    if definition.fixture_id == "convex-box":
        center = graph.add_node((0.0, 0.0, 0.0), grounded=True)
        bottom = graph.add_node((0.0, 0.0, low[2] + margin), shell_anchor=True, grounded=True)
        top = graph.add_node((0.0, 0.0, high[2] - margin), shell_anchor=True, grounded=True)
        graph.add_edge(bottom, center, EdgeKind.STRUCTURAL)
        graph.add_edge(center, top, EdgeKind.STRUCTURAL)
        if infill_percent >= 10.0:
            left = graph.add_node((low[0] + margin, 0.0, 0.0), shell_anchor=True, grounded=True)
            right = graph.add_node((high[0] - margin, 0.0, 0.0), shell_anchor=True, grounded=True)
            graph.add_edge(left, center, EdgeKind.STRUCTURAL)
            graph.add_edge(center, right, EdgeKind.STRUCTURAL)
        if infill_percent >= 15.0:
            front = graph.add_node((0.0, low[1] + margin, 0.0), shell_anchor=True, grounded=True)
            back = graph.add_node((0.0, high[1] - margin, 0.0), shell_anchor=True, grounded=True)
            graph.add_edge(front, center, EdgeKind.STRUCTURAL)
            graph.add_edge(center, back, EdgeKind.STRUCTURAL)
        return graph
    if definition.fixture_id == "concave-l":
        points = ((-8.0, -11.0, low[2] + margin), (-8.0, -11.0, high[2] - margin))
    elif definition.fixture_id in {"three-point-bending-bar", "torsion-keyed-prism"}:
        points = ((low[0] + margin, 0.0, low[2] + margin), (high[0] - margin, 0.0, low[2] + margin))
    else:
        points = ((0.0, 0.0, low[2] + margin), (0.0, 0.0, high[2] - margin))
    a = graph.add_node(points[0], shell_anchor=True, grounded=True)
    b = graph.add_node(points[1], shell_anchor=True, grounded=True)
    graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    return graph
