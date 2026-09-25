from __future__ import annotations

from dataclasses import dataclass
from math import ceil, hypot, pi, tan
from typing import Sequence

from .config import HerculeanConfig, Orientation
from .domain import VolumeAdapter
from .geometry import (
    Vec3,
    add,
    bbox_corners,
    distance,
    dot,
    lerp,
    orthonormal_basis,
    scale,
)
from .ids import ConcernId, MonotonicIdAllocator, NodeId
from .model import (
    Concern,
    DensityReport,
    Diagnostic,
    EdgeKind,
    EndpointQuality,
    GenerationResult,
    StructuralGraph,
)


@dataclass(frozen=True)
class _RawConcern:
    orientation: str
    a: Vec3
    b: Vec3
    score: float
    endpoint_quality: EndpointQuality

    @property
    def length_mm(self) -> float:
        return distance(self.a, self.b)


class HerculeanGenerator:
    def __init__(self, config: HerculeanConfig) -> None:
        self.config = config

    def generate(self, volume: VolumeAdapter) -> GenerationResult:
        raw = self._scan_all(volume)
        selected = self._plan_density(raw, volume.volume_mm3)
        concern_ids = MonotonicIdAllocator(ConcernId)
        concerns = tuple(
            Concern(
                id=concern_ids.allocate(),
                orientation=item.orientation,
                a=item.a,
                b=item.b,
                score=item.score,
                endpoint_quality=item.endpoint_quality,
            )
            for item in selected
        )
        if not concerns:
            return GenerationResult(
                success=False,
                concerns=(),
                graph=None,
                diagnostics=(Diagnostic(code="NO_AFFORDABLE_CONCERNS", message="density budget selected no legal concern"),),
                density=None,
            )

        graph = StructuralGraph()
        for concern in concerns:
            a = graph.add_node(concern.a, shell_anchor=True, concerns=(concern.id,))
            b = graph.add_node(concern.b, shell_anchor=True, concerns=(concern.id,))
            graph.add_edge(a, b, EdgeKind.STRUCTURAL, (concern.id,))

        diagnostics = self.validate_graph(graph, volume, require_grounded=False)
        if diagnostics:
            return GenerationResult(False, concerns, None, tuple(diagnostics), None)

        support_diagnostics = self._ground_graph(graph, volume)
        diagnostics = support_diagnostics + self.validate_graph(graph, volume, require_grounded=True)
        if diagnostics:
            return GenerationResult(False, concerns, None, tuple(self._deduplicate(diagnostics)), None)

        density = self._density_report(graph, volume.volume_mm3)
        return GenerationResult(True, concerns, graph, (), density)

    def _scan_all(self, volume: VolumeAdapter) -> list[_RawConcern]:
        by_orientation: list[_RawConcern] = []
        for orientation in self.config.orientations:
            found = self._scan_orientation(volume, orientation)
            found.sort(key=lambda item: (-item.score, item.a, item.b))
            by_orientation.extend(found[: self.config.max_concerns_per_orientation])
        return sorted(by_orientation, key=lambda item: (-item.score, item.orientation, item.a, item.b))

    def _scan_orientation(self, volume: VolumeAdapter, orientation: Orientation) -> list[_RawConcern]:
        u, v, direction = orthonormal_basis(orientation.direction)
        corners = bbox_corners(volume.bounds)
        projected_u = [dot(corner, u) for corner in corners]
        projected_v = [dot(corner, v) for corner in corners]
        projected_d = [dot(corner, direction) for corner in corners]
        u0, u1 = min(projected_u), max(projected_u)
        v0, v1 = min(projected_v), max(projected_v)
        d0, d1 = min(projected_d), max(projected_d)
        pitch = self.config.orientation_sample_pitch_mm
        step = self.config.ray_step_mm
        found: list[_RawConcern] = []

        ray_u = u0 + pitch * 0.5
        while ray_u <= u1 + 1e-9:
            ray_v = v0 + pitch * 0.5
            while ray_v <= v1 + 1e-9:
                origin = add(scale(u, ray_u), scale(v, ray_v))
                samples: list[tuple[float, bool]] = []
                position = d0 - step
                while position <= d1 + step + 1e-9:
                    samples.append((position, volume.contains(add(origin, scale(direction, position)))))
                    position += step
                for start, end, quality in self._inside_intervals(samples, origin, direction, volume):
                    boundary_a = add(origin, scale(direction, start))
                    boundary_b = add(origin, scale(direction, end))
                    # Inset until the configured radius fits. For oblique rays,
                    # moving one radius along the ray is not necessarily one
                    # radius away from the crossed domain face.
                    a = self._inset_endpoint(boundary_a, boundary_b, volume)
                    b = self._inset_endpoint(boundary_b, boundary_a, volume)
                    if a is None or b is None:
                        continue
                    length = distance(a, b)
                    if length + 1e-9 < self.config.min_concern_span_mm:
                        continue
                    found.append(
                        _RawConcern(
                            orientation=orientation.name,
                            a=a,
                            b=b,
                            score=length / pitch,
                            endpoint_quality=quality,
                        )
                    )
                ray_v += pitch
            ray_u += pitch
        return found

    def _inset_endpoint(self, boundary: Vec3, toward: Vec3, volume: VolumeAdapter) -> Vec3 | None:
        span = distance(boundary, toward)
        increment = min(self.config.member_radius_mm / 4.0, self.config.containment_step_mm)
        inset = increment
        while inset < span * 0.5:
            candidate = lerp(boundary, toward, inset / span)
            if volume.contains(candidate, self.config.member_radius_mm):
                return candidate
            inset += increment
        return None

    def _inside_intervals(
        self,
        samples: Sequence[tuple[float, bool]],
        origin: Vec3,
        direction: Vec3,
        volume: VolumeAdapter,
    ) -> list[tuple[float, float, EndpointQuality]]:
        intervals: list[tuple[float, float, EndpointQuality]] = []
        start: float | None = None
        start_quality = EndpointQuality.APPROXIMATE
        previous_t: float | None = None
        previous_inside = False
        for current_t, current_inside in samples:
            if current_inside and not previous_inside:
                if previous_t is None:
                    start = current_t
                    start_quality = EndpointQuality.APPROXIMATE
                else:
                    start = self._refine_boundary(previous_t, current_t, origin, direction, volume)
                    start_quality = EndpointQuality.REFINED
            elif previous_inside and not current_inside and start is not None and previous_t is not None:
                end = self._refine_boundary(current_t, previous_t, origin, direction, volume)
                quality = start_quality if start_quality == EndpointQuality.APPROXIMATE else EndpointQuality.REFINED
                intervals.append((start, end, quality))
                start = None
            previous_t = current_t
            previous_inside = current_inside
        if start is not None and previous_t is not None:
            intervals.append((start, previous_t, EndpointQuality.APPROXIMATE))
        return intervals

    def _refine_boundary(
        self,
        outside_t: float,
        inside_t: float,
        origin: Vec3,
        direction: Vec3,
        volume: VolumeAdapter,
    ) -> float:
        outside = outside_t
        inside = inside_t
        while abs(inside - outside) > self.config.boundary_tolerance_mm:
            middle = (inside + outside) * 0.5
            if volume.contains(add(origin, scale(direction, middle))):
                inside = middle
            else:
                outside = middle
        return inside

    def _plan_density(self, candidates: Sequence[_RawConcern], volume_mm3: float) -> list[_RawConcern]:
        target = volume_mm3 * self.config.infill_percent / 100.0
        structural_budget = target * (1.0 - self.config.support_reserve_fraction)
        area = pi * self.config.member_radius_mm**2
        selected: list[_RawConcern] = []
        used = 0.0
        for candidate in candidates:
            cost = area * candidate.length_mm
            if used + cost <= structural_budget + 1e-9:
                selected.append(candidate)
                used += cost
        if not selected and candidates:
            selected.append(candidates[0])
        return selected

    def _ground_graph(self, graph: StructuralGraph, volume: VolumeAdapter) -> list[Diagnostic]:
        z_min = volume.bounds[2]
        grounding_height = z_min + self.config.member_radius_mm + self.config.build_plate_epsilon_mm
        for node in graph.nodes.values():
            node.grounded = node.xyz[2] <= grounding_height

        angle_limit = tan(self.config.max_angle_from_vertical_deg * pi / 180.0)
        diagnostics: list[Diagnostic] = []
        for node in sorted(tuple(graph.nodes.values()), key=lambda item: (item.xyz[2], item.id.value)):
            if node.grounded:
                continue
            target = self._best_grounded_target(node.id, graph, volume, angle_limit)
            if target is not None:
                graph.add_edge(target, node.id, EdgeKind.PRINT_SUPPORT)
                node.grounded = True
                continue
            anchor = self._ground_anchor_below(node.xyz, volume)
            if anchor is None:
                diagnostics.append(
                    Diagnostic(
                        code="UNGROUNDED_NODE",
                        message="no continuous legal path reaches the build plate",
                        entity_type="node",
                        entity_id=node.id.value,
                    )
                )
                continue
            anchor_id = graph.add_node(anchor, shell_anchor=True, grounded=True)
            graph.add_edge(anchor_id, node.id, EdgeKind.PRINT_SUPPORT)
            node.grounded = True
        return diagnostics

    def _best_grounded_target(
        self,
        node_id: NodeId,
        graph: StructuralGraph,
        volume: VolumeAdapter,
        angle_limit: float,
    ) -> NodeId | None:
        node = graph.nodes[node_id]
        options: list[tuple[float, int, NodeId]] = []
        for candidate in graph.nodes.values():
            if not candidate.grounded or candidate.xyz[2] >= node.xyz[2] - 1e-9:
                continue
            dz = node.xyz[2] - candidate.xyz[2]
            lateral = hypot(node.xyz[0] - candidate.xyz[0], node.xyz[1] - candidate.xyz[1])
            if lateral > min(self.config.support_search_radius_mm, dz * angle_limit) + 1e-9:
                continue
            if self._swept_segment_inside(candidate.xyz, node.xyz, volume):
                options.append((distance(candidate.xyz, node.xyz), candidate.id.value, candidate.id))
        return min(options)[2] if options else None

    def _ground_anchor_below(self, point: Vec3, volume: VolumeAdapter) -> Vec3 | None:
        z_min = volume.bounds[2] + self.config.member_radius_mm
        step = self.config.containment_step_mm
        z = point[2]
        while z > z_min:
            z = max(z_min, z - step)
            if not volume.contains((point[0], point[1], z), self.config.member_radius_mm):
                return None
        anchor = (point[0], point[1], z_min)
        return anchor if self._swept_segment_inside(anchor, point, volume) else None

    def _swept_segment_inside(self, a: Vec3, b: Vec3, volume: VolumeAdapter) -> bool:
        steps = max(2, int(ceil(distance(a, b) / self.config.containment_step_mm)) + 1)
        return all(
            volume.contains(lerp(a, b, index / (steps - 1)), self.config.member_radius_mm)
            for index in range(steps)
        )

    def validate_graph(
        self,
        graph: StructuralGraph,
        volume: VolumeAdapter,
        *,
        require_grounded: bool,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for edge in sorted(graph.edges.values(), key=lambda item: item.id.value):
            if not self._swept_segment_inside(graph.nodes[edge.a].xyz, graph.nodes[edge.b].xyz, volume):
                diagnostics.append(
                    Diagnostic(
                        code="MEMBER_OUTSIDE_DOMAIN",
                        message="edge centerline or configured radius leaves the legal domain",
                        entity_type="edge",
                        entity_id=edge.id.value,
                    )
                )
        if require_grounded:
            reachable = self._reachable_from_ground(graph)
            for node in sorted(graph.nodes.values(), key=lambda item: item.id.value):
                if node.id not in reachable or not node.grounded:
                    diagnostics.append(
                        Diagnostic(
                            code="UNSUPPORTED_NODE",
                            message="node has no proven path to a grounded printable component",
                            entity_type="node",
                            entity_id=node.id.value,
                        )
                    )
        return diagnostics

    @staticmethod
    def _reachable_from_ground(graph: StructuralGraph) -> set[NodeId]:
        reached = {node.id for node in graph.nodes.values() if node.grounded}
        pending = list(reached)
        while pending:
            current = pending.pop()
            for edge in graph.incident(current):
                other = edge.b if edge.a == current else edge.a
                if other not in reached:
                    reached.add(other)
                    pending.append(other)
        return reached

    def _density_report(self, graph: StructuralGraph, volume_mm3: float) -> DensityReport:
        area = pi * self.config.member_radius_mm**2
        structural = 0.0
        support = 0.0
        for edge in graph.edges.values():
            estimated = area * distance(graph.nodes[edge.a].xyz, graph.nodes[edge.b].xyz)
            if edge.kind == EdgeKind.STRUCTURAL:
                structural += estimated
            else:
                support += estimated
        target = volume_mm3 * self.config.infill_percent / 100.0
        achieved = 100.0 * (structural + support) / volume_mm3
        deviation = abs(achieved - self.config.infill_percent)
        return DensityReport(
            requested_percent=self.config.infill_percent,
            achieved_planned_percent=achieved,
            absolute_deviation_percent=deviation,
            legal_domain_volume_mm3=volume_mm3,
            target_internal_volume_mm3=target,
            structural_volume_estimate_mm3=structural,
            support_volume_estimate_mm3=support,
            support_reserve_volume_mm3=target * self.config.support_reserve_fraction,
            exact_request_feasible=deviation <= self.config.budget_tolerance_percent,
        )

    @staticmethod
    def _deduplicate(diagnostics: Sequence[Diagnostic]) -> list[Diagnostic]:
        found: dict[tuple[str, str | None, int | None], Diagnostic] = {}
        for item in diagnostics:
            found[(item.code, item.entity_type, item.entity_id)] = item
        return list(found.values())
