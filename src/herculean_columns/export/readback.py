from __future__ import annotations

from pydantic import BaseModel, ConfigDict
import manifold3d  # type: ignore[import-not-found]
import numpy as np
import trimesh
from trimesh import Trimesh


class ReadbackEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    volume_mm3: float
    component_count: int
    watertight: bool
    winding_consistent: bool
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]


def _components(mesh: Trimesh) -> int:
    converted = manifold3d.Manifold(manifold3d.Mesh64(np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.uint64)))
    return sum(1 for component in converted.decompose() if component.volume() > 0.0)


def readback_stl(path: str) -> ReadbackEvidence:
    loaded = trimesh.load_mesh(path, file_type="stl", process=False)
    if not isinstance(loaded, Trimesh):
        raise ValueError("STL readback did not produce one triangle mesh")
    loaded.merge_vertices()
    return ReadbackEvidence(
        volume_mm3=float(loaded.volume), component_count=_components(loaded),
        watertight=bool(loaded.is_watertight), winding_consistent=bool(loaded.is_winding_consistent),
        bounds_mm=((float(loaded.bounds[0, 0]), float(loaded.bounds[0, 1]), float(loaded.bounds[0, 2])), (float(loaded.bounds[1, 0]), float(loaded.bounds[1, 1]), float(loaded.bounds[1, 2]))),
    )
