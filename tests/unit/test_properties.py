from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from herculean_columns import HerculeanConfig, HerculeanGenerator


@pytest.mark.unit
@given(st.floats(min_value=2.0, max_value=40.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_successful_generation_has_unique_stable_ids_and_no_unsupported_nodes(
    box_volume: object, percentage: float
) -> None:
    generator = HerculeanGenerator(HerculeanConfig(infill_percent=percentage))
    result = generator.generate(box_volume)  # type: ignore[arg-type]
    assert result.success
    assert result.graph is not None
    node_ids = [item.value for item in result.graph.nodes]
    edge_ids = [item.value for item in result.graph.edges]
    concern_ids = [item.id.value for item in result.concerns]
    assert len(node_ids) == len(set(node_ids))
    assert len(edge_ids) == len(set(edge_ids))
    assert len(concern_ids) == len(set(concern_ids))
    assert all(node.grounded for node in result.graph.nodes.values())


@pytest.mark.unit
def test_generation_and_serialization_are_deterministic(box_volume: object) -> None:
    config = HerculeanConfig(infill_percent=15.0)
    first = HerculeanGenerator(config).generate(box_volume)  # type: ignore[arg-type]
    second = HerculeanGenerator(config).generate(box_volume)  # type: ignore[arg-type]
    assert first.stable_dict() == second.stable_dict()
    assert json.dumps(first.stable_dict(), sort_keys=True) == json.dumps(second.stable_dict(), sort_keys=True)


@pytest.mark.unit
def test_successful_edges_are_swept_member_contained(box_volume: object) -> None:
    generator = HerculeanGenerator(HerculeanConfig(infill_percent=20.0))
    result = generator.generate(box_volume)  # type: ignore[arg-type]
    assert result.success and result.graph is not None
    assert generator.validate_graph(result.graph, box_volume, require_grounded=True) == []  # type: ignore[arg-type]


@pytest.mark.unit
def test_density_response_is_monotonic_and_reports_budget_and_support(box_volume: object) -> None:
    percentages = (2.0, 5.0, 10.0, 20.0, 40.0)
    results = [
        HerculeanGenerator(HerculeanConfig(infill_percent=value)).generate(box_volume)  # type: ignore[arg-type]
        for value in percentages
    ]
    assert all(result.success and result.density is not None for result in results)
    structural = [result.density.structural_volume_estimate_mm3 for result in results if result.density]
    assert structural == sorted(structural)
    for requested, result in zip(percentages, results):
        assert result.density is not None
        assert result.density.requested_percent == requested
        assert result.density.support_volume_estimate_mm3 >= 0.0
        assert result.density.support_reserve_volume_mm3 > 0.0
        assert result.density.absolute_deviation_percent == pytest.approx(
            abs(result.density.achieved_planned_percent - requested)
        )
        assert result.density.measurement_kind == "non-unioned centerline planning estimate"
