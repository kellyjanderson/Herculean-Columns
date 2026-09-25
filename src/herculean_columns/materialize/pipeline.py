from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from typing import Callable, cast

import numpy as np
import manifold3d  # type: ignore[import-not-found]
import trimesh

from ..config import HerculeanConfig
from ..model import EdgeKind, StructuralGraph
from .report import FailureDetail, MaterializationReport
from .source import AdmittedSource


class MaterializationError(RuntimeError):
    def __init__(self, failure: FailureDetail) -> None:
        super().__init__(failure.message)
        self.failure = failure


@dataclass(frozen=True)
class MaterializationResult:
    body: trimesh.Trimesh
    shell: trimesh.Trimesh
    structural: trimesh.Trimesh
    support: trimesh.Trimesh
    junctions: trimesh.Trimesh
    legal_domain: trimesh.Trimesh
    report: MaterializationReport


BooleanOperation = Callable[[list[trimesh.Trimesh]], trimesh.Trimesh]


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256(payload).hexdigest()


def _boolean(name: str, meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    try:
        operation = getattr(trimesh.boolean, name)
        result = operation(meshes, engine="manifold", check_volume=True)
    except Exception as exc:
        raise MaterializationError(
            FailureDetail(code="BOOLEAN_FAILURE", message=f"{name} boolean failed: {exc}")
        ) from exc
    if not isinstance(result, trimesh.Trimesh) or result.is_empty:
        raise MaterializationError(
            FailureDetail(code="BOOLEAN_FAILURE", message=f"{name} boolean returned empty geometry")
        )
    return result


def _cylinder_between(a: np.ndarray, b: np.ndarray, radius: float) -> trimesh.Trimesh:
    vector = b - a
    length = float(np.linalg.norm(vector))
    if length <= 1e-9:
        raise MaterializationError(
            FailureDetail(code="ZERO_LENGTH_MEMBER", message="member endpoints coincide")
        )
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=24)
    direction = vector / length
    transform = trimesh.geometry.align_vectors([0.0, 0.0, 1.0], direction)  # type: ignore[no-untyped-call]
    if transform is None:
        transform = np.eye(4)
    transform[:3, 3] = (a + b) * 0.5
    mesh.apply_transform(transform)
    return cast(trimesh.Trimesh, mesh)


def _empty() -> trimesh.Trimesh:
    return trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=int))


def _mesh_components(mesh: trimesh.Trimesh) -> int:
    converted = manifold3d.Manifold(manifold3d.Mesh64(np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.uint64)))
    return sum(1 for component in converted.decompose() if component.volume() > 0.0)


class SolidMaterializer:
    def __init__(
        self,
        config: HerculeanConfig,
        *,
        boolean: Callable[[str, list[trimesh.Trimesh]], trimesh.Trimesh] = _boolean,
    ) -> None:
        self.config = config
        def guarded(name: str, meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
            try:
                return boolean(name, meshes)
            except MaterializationError:
                raise
            except Exception as exc:
                raise MaterializationError(FailureDetail(code="BOOLEAN_FAILURE", message=f"{name} boolean failed: {exc}")) from exc
        self.boolean = guarded

    def materialize(self, source: AdmittedSource, graph: StructuralGraph) -> MaterializationResult:
        if self.config.junction_radius_mm <= self.config.member_radius_mm:
            raise MaterializationError(
                FailureDetail(
                    code="ZERO_THICKNESS_JUNCTION",
                    message="junction radius must exceed member radius to provide real overlap",
                )
            )
        if not graph.edges:
            raise MaterializationError(FailureDetail(code="EMPTY_GRAPH", message="graph has no members"))
        shell_t = self.config.required_shell_thickness_mm
        if min(np.ptp(source.mesh.bounds, axis=0)) <= 2.0 * shell_t + self.config.geometry_tolerance_mm:
            raise MaterializationError(
                FailureDetail(code="THIN_FEATURE", message="source cannot contain the required shell")
            )

        legal = self._inset(source.mesh, shell_t)
        # Build the shell against a slightly deeper inset so the legal domain
        # and shell overlap by a real, resolution-scaled band.  This avoids a
        # coplanar-only attachment while preserving the source exterior.
        overlap = max(self.config.geometry_tolerance_mm, self.config.mesh_resolution_mm * 0.51)
        shell_inner = self._inset(source.mesh, shell_t + overlap)
        shell = self.boolean("difference", [source.mesh.copy(), shell_inner])
        structural_parts: list[trimesh.Trimesh] = []
        support_parts: list[trimesh.Trimesh] = []
        junction_parts: list[trimesh.Trimesh] = []
        for node in sorted(graph.nodes.values(), key=lambda item: item.id.value):
            junction = trimesh.creation.icosphere(subdivisions=2, radius=self.config.junction_radius_mm)
            junction.apply_translation(node.xyz)
            junction_parts.append(junction)
        for edge in sorted(graph.edges.values(), key=lambda item: item.id.value):
            a = np.asarray(graph.nodes[edge.a].xyz, dtype=float)
            b = np.asarray(graph.nodes[edge.b].xyz, dtype=float)
            part = _cylinder_between(a, b, self.config.member_radius_mm)
            (structural_parts if edge.kind == EdgeKind.STRUCTURAL else support_parts).append(part)

        junctions_raw = self.boolean("union", junction_parts)
        structural_raw = self.boolean("union", structural_parts + junction_parts)
        structural = self.boolean("intersection", [structural_raw, legal.copy()])
        if support_parts:
            support_raw = self.boolean("union", support_parts + junction_parts)
            support_clipped = self.boolean("intersection", [support_raw, legal.copy()])
            support = self.boolean("difference", [support_clipped, structural.copy()])
            internal = self.boolean("union", [structural.copy(), support_clipped])
        else:
            support = _empty()
            internal = structural.copy()
        junctions = self.boolean("intersection", [junctions_raw, legal.copy()])
        body = self.boolean("union", [shell.copy(), internal.copy()])
        self._validate(source, graph, legal, internal, body)

        graph_dict = graph.stable_dict()
        config_dict = self.config.model_dump(mode="json")
        legal_volume = float(legal.volume)
        structural_volume = float(structural.volume)
        support_volume = 0.0 if support.is_empty else float(support.volume)
        internal_volume = float(internal.volume)
        achieved = 100.0 * internal_volume / legal_volume
        deviation = abs(achieved - self.config.infill_percent)
        if deviation > self.config.budget_tolerance_percent:
            raise MaterializationError(
                FailureDetail(
                    code="DENSITY_BUDGET_MISS",
                    message="unioned internal volume is outside configured density tolerance",
                    details={"requested_percent": self.config.infill_percent, "achieved_percent": achieved, "deviation_percent": deviation, "tolerance_percent": self.config.budget_tolerance_percent},
                )
            )
        report = MaterializationReport(
            success=True,
            source={
                "path": str(source.path),
                "sha256": source.content_sha256,
                "bytes": source.byte_count,
                "units": source.units,
                "bounds_mm": source.bounds_mm,
                "volume_mm3": source.volume_mm3,
                "component_count": source.component_count,
                "watertight": source.watertight,
                "winding_consistent": source.winding_consistent,
                "normalizations": source.normalizations,
            },
            graph_sha256=_canonical_hash(graph_dict),
            configuration=config_dict,
            configuration_sha256=_canonical_hash(config_dict),
            tool_versions={"trimesh": version("trimesh"), "manifold3d": version("manifold3d")},
            shell_thickness_mm=shell_t,
            legal_domain_volume_mm3=legal_volume,
            source_volume_mm3=source.volume_mm3,
            shell_volume_mm3=float(shell.volume),
            structural_member_volume_mm3=structural_volume,
            print_support_member_volume_mm3=support_volume,
            unioned_internal_volume_mm3=internal_volume,
            requested_infill_percent=self.config.infill_percent,
            achieved_infill_percent=achieved,
            absolute_deviation_percent=deviation,
            validation={
                "positive_volume": float(body.volume) > 0.0,
                "component_count": _mesh_components(body),
                "watertight": bool(body.is_watertight),
                "winding_consistent": bool(body.is_winding_consistent),
                "bounds_mm": np.asarray(body.bounds).tolist(),
                "exterior_bounds_deviation_mm": float(np.max(np.abs(body.bounds - source.mesh.bounds))),
                "graph_component_count": self._graph_components(graph),
            },
        )
        return MaterializationResult(body, shell, structural, support, junctions, legal, report)

    def _inset(self, mesh: trimesh.Trimesh, thickness: float) -> trimesh.Trimesh:
        try:
            # Manifold's level-set constructor keeps the result closed and
            # manifold while trimesh supplies signed-distance queries for an
            # arbitrary concave admitted source.
            proximity = trimesh.proximity.ProximityQuery(mesh)  # type: ignore[no-untyped-call]
            def signed_distance(x: float, y: float, z: float) -> float:
                return float(proximity.signed_distance([[x, y, z]])[0])  # type: ignore[no-untyped-call]
            generated = manifold3d.Manifold.level_set(
                signed_distance,
                tuple(float(value) for value in mesh.bounds.reshape(-1)),
                self.config.mesh_resolution_mm,
                level=thickness,
                tolerance=self.config.geometry_tolerance_mm,
            )
            if generated.is_empty():
                raise ValueError("erosion removed the entire legal domain")
            result = generated.to_mesh64()
            return trimesh.Trimesh(vertices=np.asarray(result.vert_properties)[:, :3], faces=np.asarray(result.tri_verts), process=False)
        except Exception as exc:
            raise MaterializationError(
                FailureDetail(code="LEGAL_DOMAIN_FAILURE", message=f"cannot derive closed legal domain: {exc}")
            ) from exc

    def _validate(
        self,
        source: AdmittedSource,
        graph: StructuralGraph,
        legal: trimesh.Trimesh,
        internal: trimesh.Trimesh,
        body: trimesh.Trimesh,
    ) -> None:
        failures: list[FailureDetail] = []
        if body.is_empty or body.volume <= 0.0:
            failures.append(FailureDetail(code="EMPTY_OUTPUT", message="output is empty or non-positive"))
        if not body.is_watertight or not body.is_winding_consistent or not body.is_volume:
            failures.append(FailureDetail(code="NONMANIFOLD_OUTPUT", message="output is not watertight and consistently wound"))
        components = _mesh_components(body)
        if components != 1:
            failures.append(FailureDetail(code="MULTIPLE_OUTPUT_BODIES", message=f"output has {components} bodies"))
        deviation = float(np.max(np.abs(body.bounds - source.mesh.bounds)))
        if deviation > self.config.exterior_tolerance_mm:
            failures.append(
                FailureDetail(code="EXTERIOR_DEVIATION", message="output bounds deviate from source", details={"deviation_mm": deviation})
            )
        if self._graph_components(graph) != 1:
            failures.append(FailureDetail(code="DISCONNECTED_MEMBERS", message="graph contains disconnected member components"))
        if _mesh_components(internal) > 1:
            failures.append(FailureDetail(code="DISCONNECTED_STRUTS", message="clipped internal solid is disconnected"))
        if legal.is_empty or not legal.is_watertight:
            failures.append(FailureDetail(code="INVALID_LEGAL_DOMAIN", message="legal infill domain is not closed"))
        if failures:
            raise MaterializationError(failures[0])

    @staticmethod
    def _graph_components(graph: StructuralGraph) -> int:
        pending = set(graph.nodes)
        count = 0
        while pending:
            count += 1
            stack = [pending.pop()]
            while stack:
                current = stack.pop()
                for edge in graph.incident(current):
                    other = edge.b if edge.a == current else edge.a
                    if other in pending:
                        pending.remove(other)
                        stack.append(other)
        return count
