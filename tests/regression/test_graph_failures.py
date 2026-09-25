from __future__ import annotations

from dataclasses import dataclass

import pytest
from shapely.geometry import box

from herculean_columns import (
    EdgeKind,
    HerculeanConfig,
    HerculeanGenerator,
    MonotonicIdAllocator,
    NodeId,
    Orientation,
    StructuralGraph,
)
from herculean_columns.geometry import Vec3


@pytest.mark.regression
def test_retained_tapered_concern_ids_are_unique_across_orientations() -> None:
    @dataclass(frozen=True)
    class TaperedVolume:
        @property
        def bounds(self) -> tuple[float, float, float, float, float, float]:
            return (0.0, 0.0, 0.0, 24.0, 24.0, 20.0)

        @property
        def volume_mm3(self) -> float:
            return 7200.0

        def contains(self, point: Vec3, clearance_mm: float = 0.0) -> bool:
            x, y, z = point
            half = 12.0 - 0.25 * z
            return (
                clearance_mm <= z <= 20.0 - clearance_mm
                and 12.0 - half + clearance_mm <= x <= 12.0 + half - clearance_mm
                and 12.0 - half + clearance_mm <= y <= 12.0 + half - clearance_mm
            )

    config = HerculeanConfig(
        infill_percent=20.0,
        orientation_sample_pitch_mm=4.0,
        max_concerns_per_orientation=3,
    )
    result = HerculeanGenerator(config).generate(TaperedVolume())
    ids = [concern.id.value for concern in result.concerns]
    assert len(ids) == len(set(ids))
    assert ids == list(range(len(ids)))


@pytest.mark.regression
def test_pruning_does_not_allow_node_identity_overwrite() -> None:
    graph = StructuralGraph()
    first = graph.add_node((0.0, 0.0, 0.0))
    pruned = graph.add_node((1.0, 0.0, 0.0))
    third = graph.add_node((2.0, 0.0, 0.0))
    graph.remove_node(pruned)
    support = graph.add_node((1.0, 0.0, 1.0))
    assert first == NodeId(0)
    assert third == NodeId(2)
    assert support == NodeId(3)
    assert graph.nodes[third].xyz == (2.0, 0.0, 0.0)


@pytest.mark.regression
def test_concave_volume_rejects_out_of_domain_structural_chord() -> None:
    from herculean_columns import Layer, LayerStackVolume

    region = box(0.0, 0.0, 4.0, 10.0).union(box(0.0, 0.0, 10.0, 4.0))
    volume = LayerStackVolume((Layer(0.0, region), Layer(10.0, region)))
    graph = StructuralGraph()
    a = graph.add_node((2.0, 8.0, 5.0))
    b = graph.add_node((8.0, 2.0, 5.0))
    graph.add_edge(a, b, EdgeKind.STRUCTURAL)
    diagnostics = HerculeanGenerator(HerculeanConfig(infill_percent=10.0)).validate_graph(
        graph, volume, require_grounded=False
    )
    assert [item.code for item in diagnostics] == ["MEMBER_OUTSIDE_DOMAIN"]


@pytest.mark.regression
def test_upper_disconnected_region_cannot_create_fake_ground_anchor() -> None:
    @dataclass(frozen=True)
    class UpperOnlyVolume:
        @property
        def bounds(self) -> tuple[float, float, float, float, float, float]:
            return (0.0, 0.0, 0.0, 20.0, 20.0, 20.0)

        @property
        def volume_mm3(self) -> float:
            return 4000.0

        def contains(self, point: Vec3, clearance_mm: float = 0.0) -> bool:
            x, y, z = point
            return (
                clearance_mm <= x <= 20.0 - clearance_mm
                and clearance_mm <= y <= 20.0 - clearance_mm
                and 10.0 + clearance_mm <= z <= 20.0 - clearance_mm
            )

    config = HerculeanConfig(
        infill_percent=20.0,
        orientations=(Orientation(name="X", direction=(1.0, 0.0, 0.0)),),
        orientation_sample_pitch_mm=5.0,
    )
    result = HerculeanGenerator(config).generate(UpperOnlyVolume())
    assert not result.success
    assert result.graph is None
    assert "UNGROUNDED_NODE" in {item.code for item in result.diagnostics}


@pytest.mark.regression
def test_unresolved_nodes_never_escape_in_successful_result() -> None:
    class EmptyGroundVolume:
        bounds = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
        volume_mm3 = 1000.0

        def contains(self, point: Vec3, clearance_mm: float = 0.0) -> bool:
            return point[2] >= 5.0 + clearance_mm and all(
                clearance_mm <= value <= 10.0 - clearance_mm for value in point[:2]
            ) and point[2] <= 10.0 - clearance_mm

    config = HerculeanConfig(
        infill_percent=30.0,
        orientations=(Orientation(name="X", direction=(1.0, 0.0, 0.0)),),
        orientation_sample_pitch_mm=5.0,
    )
    result = HerculeanGenerator(config).generate(EmptyGroundVolume())
    assert result.success is False
    assert result.graph is None
    assert result.diagnostics


@pytest.mark.regression
def test_allocator_never_reuses_values() -> None:
    allocator = MonotonicIdAllocator(NodeId)
    assert [allocator.allocate().value for _ in range(4)] == [0, 1, 2, 3]
