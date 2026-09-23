"""
Herculean Columns v0.2 — orientation-agnostic sparse structural infill.

Architecture
============
Stage 1: structural concern synthesis
    * Treat several 3-D directions symmetrically; printer Z is irrelevant.
    * For each direction, cast sparse virtual "vertical" rays through the part.
    * Long interior spans become structural concerns.
    * Find cross-orientation near-intersections and move concerns through shared
      mutual nodes, producing an irregular 3-D structural graph.

Stage 2: printability solver
    * Introduce the real print/build direction (currently +Z).
    * Walk graph nodes bottom-up and identify nodes that are not constructively
      supported by an already-supported node through a printable-angle edge.
    * Reuse lower graph nodes where possible; otherwise add the shortest legal
      support member available inside the part.

Stage 3: slicer handoff
    * Intersect 3-D graph edges with horizontal layer slabs.
    * Return ordinary XY extrusion-centerline strokes to the host slicer.

This is a research prototype, not a production infill implementation.
The important design point is that *structural topology is decided before
print-orientation support is considered*.

Dependencies:
    pip install shapely

The host slicer can supply a custom VolumeAdapter.  LayerStackVolume is a
convenience adapter for slicers which already expose per-layer Shapely regions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, cos, hypot, pi, sin, sqrt, tan
from typing import Iterable, Iterator, Protocol, Sequence

from shapely.geometry import GeometryCollection, LineString, MultiLineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def vadd(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vmul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return sqrt(dot(a, a))


def unit(a: Vec3) -> Vec3:
    n = norm(a)
    if n <= 1e-12:
        raise ValueError("zero-length direction")
    return vmul(a, 1.0 / n)


def distance(a: Vec3, b: Vec3) -> float:
    return norm(vsub(a, b))


def lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def orthonormal_basis(direction: Vec3) -> tuple[Vec3, Vec3, Vec3]:
    """Return (u, v, d), with u/v spanning the plane normal to d."""
    d = unit(direction)
    helper = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = unit(cross(d, helper))
    v = unit(cross(d, u))
    return u, v, d


# ---------------------------------------------------------------------------
# Host geometry abstraction
# ---------------------------------------------------------------------------

class VolumeAdapter(Protocol):
    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]: ...

    def contains(self, p: Vec3) -> bool: ...


@dataclass(frozen=True)
class Layer:
    z: float
    region: BaseGeometry


class LayerStackVolume:
    """Approximate 3-D occupancy from slicer-generated horizontal polygons."""

    def __init__(self, layers: Sequence[Layer]):
        self.layers = list(layers)
        if not self.layers:
            raise ValueError("at least one layer is required")
        for a, b in zip(self.layers, self.layers[1:]):
            if b.z <= a.z:
                raise ValueError("layers must be strictly increasing in Z")

        nonempty = [x for x in self.layers if not x.region.is_empty]
        if not nonempty:
            raise ValueError("all layers are empty")
        minx = min(x.region.bounds[0] for x in nonempty)
        miny = min(x.region.bounds[1] for x in nonempty)
        maxx = max(x.region.bounds[2] for x in nonempty)
        maxy = max(x.region.bounds[3] for x in nonempty)
        self._bounds = (minx, miny, self.layers[0].z, maxx, maxy, self.layers[-1].z)

    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]:
        return self._bounds

    def contains(self, p: Vec3) -> bool:
        x, y, z = p
        if z < self.layers[0].z or z > self.layers[-1].z:
            return False
        layer = min(self.layers, key=lambda L: abs(L.z - z))
        return layer.region.buffer(1e-8).covers(Point(x, y))


# ---------------------------------------------------------------------------
# Structural model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Orientation:
    name: str
    direction: Vec3


@dataclass(frozen=True)
class Concern:
    id: int
    orientation: str
    a: Vec3
    b: Vec3
    score: float

    @property
    def length(self) -> float:
        return distance(self.a, self.b)


@dataclass
class GraphNode:
    id: int
    xyz: Vec3
    shell_anchor: bool = False
    concerns: set[int] = field(default_factory=set)
    print_supported: bool = False


@dataclass(frozen=True)
class GraphEdge:
    a: int
    b: int
    kind: str  # structural | print_support
    concerns: tuple[int, ...] = ()


@dataclass
class StructuralGraph:
    nodes: dict[int, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, xyz: Vec3, *, shell_anchor: bool = False, concerns: Iterable[int] = ()) -> int:
        nid = len(self.nodes)
        self.nodes[nid] = GraphNode(nid, xyz, shell_anchor, set(concerns))
        return nid

    def add_edge(self, a: int, b: int, kind: str, concerns: Iterable[int] = ()) -> None:
        if a == b:
            return
        key = (min(a, b), max(a, b), kind)
        for e in self.edges:
            if (min(e.a, e.b), max(e.a, e.b), e.kind) == key:
                return
        self.edges.append(GraphEdge(a, b, kind, tuple(sorted(set(concerns)))))

    def incident(self, nid: int) -> Iterator[GraphEdge]:
        for e in self.edges:
            if e.a == nid or e.b == nid:
                yield e


@dataclass(frozen=True)
class LayerStroke:
    layer_index: int
    z: float
    a: Vec2
    b: Vec2
    kind: str
    edge_index: int


@dataclass
class HerculeanConfig:
    layer_height: float = 0.20
    line_width: float = 0.45

    # Stage 1: orientation-agnostic concern discovery.
    orientations: tuple[Orientation, ...] = (
        Orientation("X", (1, 0, 0)),
        Orientation("Y", (0, 1, 0)),
        Orientation("Z", (0, 0, 1)),
        Orientation("XY+", (1, 1, 0)),
        Orientation("XY-", (1, -1, 0)),
        Orientation("XZ+", (1, 0, 1)),
        Orientation("YZ+", (0, 1, 1)),
    )
    orientation_sample_pitch: float = 10.0
    ray_step: float = 1.0
    min_concern_span: float = 12.0
    max_concerns_per_orientation: int = 64

    # Stage 1b: cross-cutting concern -> mutual node synthesis.
    node_merge_radius: float = 3.0
    max_node_detour_ratio: float = 1.18
    shared_node_cluster_radius: float = 4.0

    # Stage 2: actual print orientation.
    max_angle_from_vertical_deg: float = 45.0
    support_search_radius: float = 20.0
    support_probe_step: float = 0.75
    build_plate_epsilon: float = 0.45

    # Stage 3: layer strokes.
    vertical_stroke_length: float = 0.50


@dataclass
class HerculeanResult:
    concerns: list[Concern]
    graph_before_support: StructuralGraph
    graph: StructuralGraph
    strokes: list[LayerStroke]

    @property
    def structural_edge_count(self) -> int:
        return sum(e.kind == "structural" for e in self.graph.edges)

    @property
    def print_support_edge_count(self) -> int:
        return sum(e.kind == "print_support" for e in self.graph.edges)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class HerculeanColumns:
    def __init__(self, config: HerculeanConfig | None = None):
        self.cfg = config or HerculeanConfig()

    def generate(self, volume: VolumeAdapter, layers: Sequence[Layer]) -> HerculeanResult:
        concerns = self.analyze_orientations(volume)
        structural = self.build_structural_graph(concerns)
        before = self._copy_graph(structural)
        self.solve_print_support(structural, volume)
        strokes = self.graph_to_layer_strokes(structural, layers)
        return HerculeanResult(concerns, before, structural, strokes)

    # ----------------------- Stage 1: concerns -----------------------

    def analyze_orientations(self, volume: VolumeAdapter) -> list[Concern]:
        all_concerns: list[Concern] = []
        next_id = 0
        for orientation in self.cfg.orientations:
            found = self._scan_orientation(volume, orientation, next_id)
            found.sort(key=lambda c: c.score, reverse=True)
            found = found[: self.cfg.max_concerns_per_orientation]
            all_concerns.extend(found)
            next_id += len(found)
        return all_concerns

    def _scan_orientation(self, volume: VolumeAdapter, orientation: Orientation, first_id: int) -> list[Concern]:
        u, v, d = orthonormal_basis(orientation.direction)
        corners = self._bbox_corners(volume.bounds)
        pu = [dot(c, u) for c in corners]
        pv = [dot(c, v) for c in corners]
        pd = [dot(c, d) for c in corners]
        u0, u1 = min(pu), max(pu)
        v0, v1 = min(pv), max(pv)
        d0, d1 = min(pd), max(pd)

        pitch = self.cfg.orientation_sample_pitch
        ray_step = self.cfg.ray_step
        out: list[Concern] = []
        cid = first_id

        uu = u0 + pitch * 0.5
        while uu <= u1 + 1e-9:
            vv = v0 + pitch * 0.5
            while vv <= v1 + 1e-9:
                origin = vadd(vmul(u, uu), vmul(v, vv))
                samples: list[tuple[float, bool]] = []
                t = d0
                while t <= d1 + ray_step * 0.5:
                    p = vadd(origin, vmul(d, t))
                    samples.append((t, volume.contains(p)))
                    t += ray_step

                intervals = self._inside_intervals(samples)
                for ta, tb in intervals:
                    length = tb - ta
                    if length < self.cfg.min_concern_span:
                        continue
                    a = vadd(origin, vmul(d, ta))
                    b = vadd(origin, vmul(d, tb))
                    # Long spans are more valuable, but mildly normalize by
                    # sampling pitch so denser analysis doesn't inflate score.
                    score = length / max(pitch, 1e-9)
                    out.append(Concern(cid, orientation.name, a, b, score))
                    cid += 1
                vv += pitch
            uu += pitch
        return out

    @staticmethod
    def _inside_intervals(samples: Sequence[tuple[float, bool]]) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        start: float | None = None
        last_t: float | None = None
        for t, inside in samples:
            if inside and start is None:
                start = t
            if not inside and start is not None:
                out.append((start, last_t if last_t is not None else t))
                start = None
            if inside:
                last_t = t
        if start is not None and last_t is not None:
            out.append((start, last_t))
        return out

    # ---------------- Stage 1b: shared mutual nodes -----------------

    def build_structural_graph(self, concerns: Sequence[Concern]) -> StructuralGraph:
        graph = StructuralGraph()
        endpoints: dict[int, tuple[int, int]] = {}

        # Concern endpoints are shell anchors by construction: they are the
        # entry/exit boundaries of an interior ray interval.
        for c in concerns:
            endpoints[c.id] = (
                graph.add_node(c.a, shell_anchor=True, concerns=[c.id]),
                graph.add_node(c.b, shell_anchor=True, concerns=[c.id]),
            )

        # Candidate shared nodes are near-intersections of concerns from
        # different orientations.  Cluster them so several cross-cutting
        # concerns can intentionally converge on one node.
        candidates: list[tuple[Vec3, set[int]]] = []
        for i, a in enumerate(concerns):
            for b in concerns[i + 1 :]:
                if a.orientation == b.orientation:
                    continue
                pa, pb, sep = self._closest_points_on_segments(a.a, a.b, b.a, b.b)
                if sep > self.cfg.node_merge_radius:
                    continue
                p = vmul(vadd(pa, pb), 0.5)
                candidates.append((p, {a.id, b.id}))

        clusters = self._cluster_shared_candidates(candidates)
        shared_nodes: list[tuple[int, set[int]]] = []
        for p, ids in clusters:
            nid = graph.add_node(p, concerns=ids)
            shared_nodes.append((nid, ids))

        # Route each concern through the most useful mutual node associated
        # with it, provided the detour is modest.  This is the explicit
        # "cross-cutting concerns -> mutual nodes" pass.
        for c in concerns:
            a_id, b_id = endpoints[c.id]
            best: tuple[float, int] | None = None
            direct = c.length
            for nid, ids in shared_nodes:
                if c.id not in ids:
                    continue
                p = graph.nodes[nid].xyz
                detour = distance(c.a, p) + distance(p, c.b)
                ratio = detour / max(direct, 1e-9)
                if ratio <= self.cfg.max_node_detour_ratio and (best is None or detour < best[0]):
                    best = (detour, nid)

            if best is None:
                graph.add_edge(a_id, b_id, "structural", [c.id])
            else:
                nid = best[1]
                graph.add_edge(a_id, nid, "structural", [c.id])
                graph.add_edge(nid, b_id, "structural", [c.id])

        self._prune_unused_shared_nodes(graph)
        return graph

    def _cluster_shared_candidates(self, candidates: Sequence[tuple[Vec3, set[int]]]) -> list[tuple[Vec3, set[int]]]:
        groups: list[list[tuple[Vec3, set[int]]]] = []
        r = self.cfg.shared_node_cluster_radius
        for cand in candidates:
            p, _ = cand
            for group in groups:
                center = self._mean_point([x[0] for x in group])
                if distance(p, center) <= r:
                    group.append(cand)
                    break
            else:
                groups.append([cand])

        out: list[tuple[Vec3, set[int]]] = []
        for group in groups:
            point = self._mean_point([x[0] for x in group])
            ids: set[int] = set()
            for _, cids in group:
                ids |= cids
            out.append((point, ids))
        return out

    # ------------------- Stage 2: print support ---------------------

    def solve_print_support(self, graph: StructuralGraph, volume: VolumeAdapter) -> None:
        """Make the structural graph printable in +Z without changing Stage 1."""
        zmin = volume.bounds[2]
        angle = self.cfg.max_angle_from_vertical_deg * pi / 180.0
        tan_limit = tan(angle)

        # Work bottom-up.  Shell anchors count as initially supported only if
        # they have material vertically below them to the lower volume region;
        # being attached to a high side/top shell is not automatically enough.
        ordered = sorted(graph.nodes.values(), key=lambda n: n.xyz[2])
        supported_ids: set[int] = set()

        for node in ordered:
            if node.xyz[2] <= zmin + self.cfg.build_plate_epsilon:
                node.print_supported = True
                supported_ids.add(node.id)
                continue

            # Existing structural edge to an already-supported lower node?
            supported_by_existing = False
            for e in graph.incident(node.id):
                other_id = e.b if e.a == node.id else e.a
                if other_id not in supported_ids:
                    continue
                other = graph.nodes[other_id]
                if other.xyz[2] >= node.xyz[2] - 1e-9:
                    continue
                if self._printable_edge(other.xyz, node.xyz, tan_limit):
                    supported_by_existing = True
                    break

            if supported_by_existing:
                node.print_supported = True
                supported_ids.add(node.id)
                continue

            # Reuse nearest lower supported node inside the printable cone.
            target_id = self._best_support_target(node, graph, supported_ids, volume, tan_limit)
            if target_id is not None:
                graph.add_edge(target_id, node.id, "print_support")
                node.print_supported = True
                supported_ids.add(node.id)
                continue

            # Fallback: create the shortest vertical-ish support anchor beneath
            # this node that remains in the model.
            anchor = self._find_support_anchor_below(node.xyz, volume)
            if anchor is not None and distance(anchor, node.xyz) > 1e-6:
                aid = graph.add_node(anchor, shell_anchor=True)
                graph.nodes[aid].print_supported = True
                supported_ids.add(aid)
                graph.add_edge(aid, node.id, "print_support")
                node.print_supported = True
                supported_ids.add(node.id)

    def _best_support_target(
        self,
        node: GraphNode,
        graph: StructuralGraph,
        supported_ids: set[int],
        volume: VolumeAdapter,
        tan_limit: float,
    ) -> int | None:
        best: tuple[float, int] | None = None
        for sid in supported_ids:
            s = graph.nodes[sid]
            dz = node.xyz[2] - s.xyz[2]
            if dz <= 1e-9:
                continue
            lateral = hypot(node.xyz[0] - s.xyz[0], node.xyz[1] - s.xyz[1])
            if lateral > min(self.cfg.support_search_radius, dz * tan_limit):
                continue
            if not self._segment_inside_volume(s.xyz, node.xyz, volume):
                continue
            cost = distance(s.xyz, node.xyz)
            if best is None or cost < best[0]:
                best = (cost, sid)
        return None if best is None else best[1]

    def _find_support_anchor_below(self, p: Vec3, volume: VolumeAdapter) -> Vec3 | None:
        zmin = volume.bounds[2]
        z = p[2] - self.cfg.support_probe_step
        last_inside: Vec3 | None = None
        while z >= zmin:
            q = (p[0], p[1], z)
            if volume.contains(q):
                last_inside = q
            else:
                break
            z -= self.cfg.support_probe_step
        return last_inside

    # --------------------- Stage 3: slicing -------------------------

    def graph_to_layer_strokes(self, graph: StructuralGraph, layers: Sequence[Layer]) -> list[LayerStroke]:
        out: list[LayerStroke] = []
        half = self.cfg.layer_height * 0.5
        for ei, edge in enumerate(graph.edges):
            a3 = graph.nodes[edge.a].xyz
            b3 = graph.nodes[edge.b].xyz
            zlo, zhi = sorted((a3[2], b3[2]))

            for li, layer in enumerate(layers):
                slab_lo, slab_hi = layer.z - half, layer.z + half
                lo, hi = max(zlo, slab_lo), min(zhi, slab_hi)

                if abs(a3[2] - b3[2]) < 1e-9:
                    if abs(layer.z - a3[2]) > half + 1e-9:
                        continue
                    p0, p1 = a3, b3
                else:
                    if hi < lo:
                        continue
                    p0 = self._point_on_segment_at_z(a3, b3, lo)
                    p1 = self._point_on_segment_at_z(a3, b3, hi)

                a = (p0[0], p0[1])
                b = (p1[0], p1[1])
                if hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
                    d = self.cfg.vertical_stroke_length * 0.5
                    a, b = ((p0[0] - d, p0[1]), (p0[0] + d, p0[1])) if not (li & 1) else ((p0[0], p0[1] - d), (p0[0], p0[1] + d))

                clipped = LineString([a, b]).intersection(layer.region)
                for seg in self._line_parts(clipped):
                    if seg.length > 1e-6:
                        coords = list(seg.coords)
                        out.append(LayerStroke(li, layer.z, tuple(coords[0]), tuple(coords[-1]), edge.kind, ei))
        return out

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _segment_inside_volume(self, a: Vec3, b: Vec3, volume: VolumeAdapter) -> bool:
        steps = max(2, int(ceil(distance(a, b) / self.cfg.support_probe_step)) + 1)
        for i in range(steps):
            p = lerp(a, b, i / (steps - 1))
            if not volume.contains(p):
                # endpoints may lie exactly on a sampled shell boundary
                if i not in (0, steps - 1):
                    return False
        return True

    @staticmethod
    def _printable_edge(lower: Vec3, upper: Vec3, tan_limit: float) -> bool:
        dz = upper[2] - lower[2]
        if dz <= 1e-9:
            return False
        lateral = hypot(upper[0] - lower[0], upper[1] - lower[1])
        return lateral <= dz * tan_limit + 1e-9

    @staticmethod
    def _closest_points_on_segments(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> tuple[Vec3, Vec3, float]:
        """Closest points on two 3-D segments; standard clamped formulation."""
        d1 = vsub(q1, p1)
        d2 = vsub(q2, p2)
        r = vsub(p1, p2)
        a = dot(d1, d1)
        e = dot(d2, d2)
        f = dot(d2, r)
        eps = 1e-12

        if a <= eps and e <= eps:
            return p1, p2, distance(p1, p2)
        if a <= eps:
            s = 0.0
            t = min(1.0, max(0.0, f / e))
        else:
            c = dot(d1, r)
            if e <= eps:
                t = 0.0
                s = min(1.0, max(0.0, -c / a))
            else:
                b = dot(d1, d2)
                denom = a * e - b * b
                s = 0.0 if abs(denom) <= eps else min(1.0, max(0.0, (b * f - c * e) / denom))
                t = (b * s + f) / e
                if t < 0.0:
                    t = 0.0
                    s = min(1.0, max(0.0, -c / a))
                elif t > 1.0:
                    t = 1.0
                    s = min(1.0, max(0.0, (b - c) / a))

        c1 = vadd(p1, vmul(d1, s))
        c2 = vadd(p2, vmul(d2, t))
        return c1, c2, distance(c1, c2)

    @staticmethod
    def _bbox_corners(bounds: tuple[float, float, float, float, float, float]) -> list[Vec3]:
        x0, y0, z0, x1, y1, z1 = bounds
        return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]

    @staticmethod
    def _mean_point(points: Sequence[Vec3]) -> Vec3:
        n = len(points)
        return (
            sum(p[0] for p in points) / n,
            sum(p[1] for p in points) / n,
            sum(p[2] for p in points) / n,
        )

    @staticmethod
    def _point_on_segment_at_z(a: Vec3, b: Vec3, z: float) -> Vec3:
        dz = b[2] - a[2]
        if abs(dz) < 1e-12:
            return a
        t = min(1.0, max(0.0, (z - a[2]) / dz))
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z)

    @staticmethod
    def _line_parts(geom: BaseGeometry) -> list[LineString]:
        if geom.is_empty:
            return []
        if isinstance(geom, LineString):
            return [geom]
        if isinstance(geom, MultiLineString):
            return list(geom.geoms)
        if isinstance(geom, GeometryCollection):
            return [g for g in geom.geoms if isinstance(g, LineString) and not g.is_empty]
        return []

    @staticmethod
    def _copy_graph(graph: StructuralGraph) -> StructuralGraph:
        g = StructuralGraph()
        for nid, n in graph.nodes.items():
            g.nodes[nid] = GraphNode(n.id, n.xyz, n.shell_anchor, set(n.concerns), n.print_supported)
        g.edges = list(graph.edges)
        return g

    @staticmethod
    def _prune_unused_shared_nodes(graph: StructuralGraph) -> None:
        used = {e.a for e in graph.edges} | {e.b for e in graph.edges}
        for nid in list(graph.nodes):
            if nid not in used and not graph.nodes[nid].shell_anchor:
                del graph.nodes[nid]


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def strokes_by_layer(result: HerculeanResult) -> dict[int, list[LayerStroke]]:
    grouped: dict[int, list[LayerStroke]] = {}
    for s in result.strokes:
        grouped.setdefault(s.layer_index, []).append(s)
    return grouped


def default_layers_for_prism(width: float, depth: float, height: float, layer_height: float) -> list[Layer]:
    """Tiny demo helper; real slicers should provide their own legal regions."""
    region = Polygon([(0, 0), (width, 0), (width, depth), (0, depth)])
    count = int(round(height / layer_height)) + 1
    return [Layer(i * layer_height, region) for i in range(count)]


if __name__ == "__main__":
    layers = default_layers_for_prism(60, 40, 20, 0.20)
    volume = LayerStackVolume(layers)
    cfg = HerculeanConfig(
        layer_height=0.20,
        orientation_sample_pitch=12.0,
        ray_step=1.0,
        min_concern_span=14.0,
        max_concerns_per_orientation=18,
    )
    result = HerculeanColumns(cfg).generate(volume, layers)
    print(f"concerns:             {len(result.concerns)}")
    print(f"nodes before support: {len(result.graph_before_support.nodes)}")
    print(f"structural edges:     {result.structural_edge_count}")
    print(f"print support edges:  {result.print_support_edge_count}")
    print(f"layer strokes:        {len(result.strokes)}")
