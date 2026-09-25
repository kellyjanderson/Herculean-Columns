from __future__ import annotations

import pytest

from herculean_columns.config import HerculeanConfig
from herculean_columns.materialize import SolidMaterializer, admit_source
from tests.materialize.helpers import anchored_graph, write_box, write_concave_l, write_tapered


pytestmark = pytest.mark.materialize


@pytest.mark.parametrize(("name", "writer", "axis"), (("box", write_box, "x"), ("concave-l", write_concave_l, "l"), ("tapered", write_tapered, "z")))
def test_canonical_source_materializes_as_one_manifold_body(tmp_path, name, writer, axis) -> None:
    source_path = writer(tmp_path / f"{name}.stl")
    source_bytes = source_path.read_bytes()
    result = SolidMaterializer(HerculeanConfig(infill_percent=10, budget_tolerance_percent=10, mesh_resolution_mm=1.0)).materialize(admit_source(source_path, units="mm"), anchored_graph(axis))
    assert result.body.volume > 0
    assert result.body.is_watertight and result.body.is_winding_consistent
    assert result.report.validation["component_count"] == 1
    assert result.report.validation["exterior_bounds_deviation_mm"] <= 0.08
    assert result.report.unioned_internal_volume_mm3 == pytest.approx(result.structural.volume + result.support.volume, rel=1e-5)
    assert result.report.achieved_infill_percent == pytest.approx(100 * result.report.unioned_internal_volume_mm3 / result.report.legal_domain_volume_mm3)
    assert source_path.read_bytes() == source_bytes
