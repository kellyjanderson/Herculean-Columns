from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from herculean_columns.model import EdgeKind, StructuralGraph


def write_box(path: Path) -> Path:
    trimesh.creation.box((20.0, 20.0, 20.0)).export(path)
    return path


def write_concave_l(path: Path) -> Path:
    vertical = trimesh.creation.box((8.0, 20.0, 20.0), transform=trimesh.transformations.translation_matrix((-6.0, 0.0, 0.0)))
    horizontal = trimesh.creation.box((20.0, 8.0, 20.0), transform=trimesh.transformations.translation_matrix((0.0, -6.0, 0.0)))
    mesh = trimesh.boolean.union([vertical, horizontal], engine="manifold")
    assert isinstance(mesh, trimesh.Trimesh)
    mesh.export(path)
    return path


def write_tapered(path: Path) -> Path:
    sections = 32
    angles = np.linspace(0.0, np.pi * 2.0, sections, endpoint=False)
    lower = np.column_stack((10.0 * np.cos(angles), 10.0 * np.sin(angles), np.full(sections, -10.0)))
    upper = np.column_stack((7.0 * np.cos(angles), 7.0 * np.sin(angles), np.full(sections, 10.0)))
    vertices = np.vstack((lower, upper, [[0.0, 0.0, -10.0], [0.0, 0.0, 10.0]]))
    faces: list[tuple[int, int, int]] = []
    for index in range(sections):
        nxt = (index + 1) % sections
        faces.extend(((index, nxt, sections + nxt), (index, sections + nxt, sections + index), (2 * sections, nxt, index), (2 * sections + 1, sections + index, sections + nxt)))
    trimesh.Trimesh(vertices=vertices, faces=faces, process=True).export(path)
    return path


def anchored_graph(axis: str = "x") -> StructuralGraph:
    graph = StructuralGraph()
    if axis == "z":
        points = ((0.0, 0.0, -9.0), (0.0, 0.0, 9.0))
    else:
        points = ((-9.0, -6.0 if axis == "l" else 0.0, 0.0), (9.0, -6.0 if axis == "l" else 0.0, 0.0))
    a = graph.add_node(points[0], shell_anchor=True, grounded=True)
    b = graph.add_node(points[1], shell_anchor=True, grounded=True)
    graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    return graph
