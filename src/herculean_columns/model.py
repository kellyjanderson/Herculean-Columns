from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Iterator

from pydantic import BaseModel, ConfigDict, Field

from .geometry import Vec3, distance
from .ids import ConcernId, EdgeId, MonotonicIdAllocator, NodeId


class EndpointQuality(StrEnum):
    REFINED = "refined"
    APPROXIMATE = "approximate"


class EdgeKind(StrEnum):
    STRUCTURAL = "structural"
    PRINT_SUPPORT = "print_support"


@dataclass(frozen=True)
class Concern:
    id: ConcernId
    orientation: str
    a: Vec3
    b: Vec3
    score: float
    endpoint_quality: EndpointQuality

    @property
    def length_mm(self) -> float:
        return distance(self.a, self.b)


@dataclass
class GraphNode:
    id: NodeId
    xyz: Vec3
    shell_anchor: bool = False
    grounded: bool = False
    concerns: set[ConcernId] = field(default_factory=set)


@dataclass(frozen=True)
class GraphEdge:
    id: EdgeId
    a: NodeId
    b: NodeId
    kind: EdgeKind
    concerns: tuple[ConcernId, ...] = ()


@dataclass
class StructuralGraph:
    nodes: dict[NodeId, GraphNode] = field(default_factory=dict)
    edges: dict[EdgeId, GraphEdge] = field(default_factory=dict)
    _node_ids: MonotonicIdAllocator[NodeId] = field(
        default_factory=lambda: MonotonicIdAllocator(NodeId), repr=False
    )
    _edge_ids: MonotonicIdAllocator[EdgeId] = field(
        default_factory=lambda: MonotonicIdAllocator(EdgeId), repr=False
    )

    def add_node(
        self,
        xyz: Vec3,
        *,
        shell_anchor: bool = False,
        grounded: bool = False,
        concerns: Iterable[ConcernId] = (),
    ) -> NodeId:
        node_id = self._node_ids.allocate()
        self.nodes[node_id] = GraphNode(node_id, xyz, shell_anchor, grounded, set(concerns))
        return node_id

    def add_edge(
        self,
        a: NodeId,
        b: NodeId,
        kind: EdgeKind,
        concerns: Iterable[ConcernId] = (),
    ) -> EdgeId | None:
        if a == b:
            return None
        if a not in self.nodes or b not in self.nodes:
            raise ValueError("edge endpoints must exist")
        pair = frozenset((a, b))
        for edge in self.edges.values():
            if edge.kind == kind and frozenset((edge.a, edge.b)) == pair:
                return edge.id
        edge_id = self._edge_ids.allocate()
        ordered_concerns = tuple(sorted(set(concerns), key=lambda identity: identity.value))
        self.edges[edge_id] = GraphEdge(edge_id, a, b, kind, ordered_concerns)
        return edge_id

    def remove_node(self, node_id: NodeId) -> None:
        if any(edge.a == node_id or edge.b == node_id for edge in self.edges.values()):
            raise ValueError("cannot remove an incident node")
        del self.nodes[node_id]

    def incident(self, node_id: NodeId) -> Iterator[GraphEdge]:
        return (edge for edge in self.edges.values() if edge.a == node_id or edge.b == node_id)

    def stable_dict(self) -> dict[str, object]:
        return {
            "nodes": [
                {
                    "id": node.id.value,
                    "xyz_mm": list(node.xyz),
                    "shell_anchor": node.shell_anchor,
                    "grounded": node.grounded,
                    "concerns": sorted(identity.value for identity in node.concerns),
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.id.value)
            ],
            "edges": [
                {
                    "id": edge.id.value,
                    "a": edge.a.value,
                    "b": edge.b.value,
                    "kind": edge.kind.value,
                    "concerns": [identity.value for identity in edge.concerns],
                }
                for edge in sorted(self.edges.values(), key=lambda item: item.id.value)
            ],
        }


class Diagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None
    details: dict[str, object] = Field(default_factory=dict)


class DensityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_percent: float
    achieved_planned_percent: float
    absolute_deviation_percent: float
    legal_domain_volume_mm3: float
    target_internal_volume_mm3: float
    structural_volume_estimate_mm3: float
    support_volume_estimate_mm3: float
    support_reserve_volume_mm3: float
    exact_request_feasible: bool
    measurement_kind: str = "non-unioned centerline planning estimate"


@dataclass(frozen=True)
class GenerationResult:
    success: bool
    concerns: tuple[Concern, ...]
    graph: StructuralGraph | None
    diagnostics: tuple[Diagnostic, ...]
    density: DensityReport | None

    def __post_init__(self) -> None:
        if self.success and (self.graph is None or self.diagnostics):
            raise ValueError("successful results require a graph and no diagnostics")
        if not self.success and self.graph is not None:
            raise ValueError("failed results cannot expose a downstream graph")

    def stable_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "concerns": [
                {
                    "id": concern.id.value,
                    "orientation": concern.orientation,
                    "a_mm": list(concern.a),
                    "b_mm": list(concern.b),
                    "score": concern.score,
                    "endpoint_quality": concern.endpoint_quality.value,
                }
                for concern in self.concerns
            ],
            "graph": None if self.graph is None else self.graph.stable_dict(),
            "diagnostics": [item.model_dump(mode="json") for item in self.diagnostics],
            "density": None if self.density is None else self.density.model_dump(mode="json"),
        }
