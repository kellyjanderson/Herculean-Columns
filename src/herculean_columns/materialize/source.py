from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import manifold3d  # type: ignore[import-not-found]
import trimesh


class SourceAdmissionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AdmittedSource:
    path: Path
    mesh: trimesh.Trimesh
    units: str
    content_sha256: str
    byte_count: int
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    volume_mm3: float
    component_count: int
    watertight: bool
    winding_consistent: bool
    normalizations: tuple[str, ...]


def _single_mesh(loaded: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
    if isinstance(loaded, trimesh.Trimesh):
        return loaded
    geometries = tuple(loaded.geometry.values())
    if not geometries:
        raise SourceAdmissionError("EMPTY_SOURCE", "source contains no mesh geometry")
    return cast(trimesh.Trimesh, trimesh.util.concatenate(geometries))


def admit_source(path: str | Path, *, units: str | None) -> AdmittedSource:
    source = Path(path).resolve()
    if units is None or units.strip().lower() not in {"mm", "millimeter", "millimetre"}:
        raise SourceAdmissionError(
            "UNKNOWN_UNITS", "source units must be declared explicitly as millimetres"
        )
    if not source.is_file():
        raise SourceAdmissionError("SOURCE_NOT_FOUND", f"source does not exist: {source}")
    payload = source.read_bytes()
    try:
        mesh = _single_mesh(cast(trimesh.Trimesh | trimesh.Scene, trimesh.load(source, force=None, process=False)))
    except Exception as exc:
        raise SourceAdmissionError("SOURCE_READ_FAILED", str(exc)) from exc
    if len(mesh.faces) == 0 or len(mesh.vertices) == 0:
        raise SourceAdmissionError("EMPTY_SOURCE", "source mesh is empty")
    # STL stores independent triangle records.  Merging numerically identical
    # vertices is representation normalization on the in-memory copy, not a
    # geometric repair and never changes the admitted source bytes.
    mesh.merge_vertices()
    normalizations = ("merge-identical-stl-vertices",) if source.suffix.lower() == ".stl" else ()
    if not mesh.is_watertight:
        raise SourceAdmissionError("NON_WATERTIGHT_SOURCE", "source mesh is not watertight")
    if not mesh.is_winding_consistent:
        raise SourceAdmissionError("INCONSISTENT_WINDING", "source winding is inconsistent")
    if not mesh.is_volume:
        raise SourceAdmissionError("SELF_INTERSECTION_INDICATOR", "source does not bound a valid positive volume")
    if not np.isfinite(mesh.vertices).all():
        raise SourceAdmissionError("NONFINITE_SOURCE", "source contains non-finite coordinates")
    volume = float(mesh.volume)
    if volume <= 0.0:
        raise SourceAdmissionError("ORIENTATION_AMBIGUITY", "source has non-positive signed volume")
    components = _component_count(mesh)
    if components != 1:
        raise SourceAdmissionError(
            "MULTIPLE_SOURCE_BODIES", f"source must contain one body, found {components}"
        )
    bounds = np.asarray(mesh.bounds, dtype=float)
    return AdmittedSource(
        path=source,
        mesh=mesh,
        units="mm",
        content_sha256=sha256(payload).hexdigest(),
        byte_count=len(payload),
        bounds_mm=(tuple(bounds[0]), tuple(bounds[1])),
        volume_mm3=volume,
        component_count=components,
        watertight=True,
        winding_consistent=True,
        normalizations=normalizations,
    )
def _component_count(mesh: trimesh.Trimesh) -> int:
    converted = manifold3d.Manifold(manifold3d.Mesh64(np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.uint64)))
    return sum(1 for component in converted.decompose() if component.volume() > 0.0)
