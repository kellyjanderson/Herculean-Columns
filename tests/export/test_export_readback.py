from __future__ import annotations

import json
from hashlib import sha256

import pytest

from herculean_columns.config import HerculeanConfig
from herculean_columns.export import export_result, readback_stl
from herculean_columns.materialize import SolidMaterializer, admit_source
from tests.materialize.helpers import anchored_graph, write_box


pytestmark = pytest.mark.export


def test_export_is_deterministic_and_independently_readable(tmp_path) -> None:
    source_path = write_box(tmp_path / "source.stl")
    source_hash = sha256(source_path.read_bytes()).hexdigest()
    result = SolidMaterializer(HerculeanConfig(infill_percent=10, budget_tolerance_percent=10, mesh_resolution_mm=1.0)).materialize(admit_source(source_path, units="mm"), anchored_graph())
    first = export_result(result, source_path, tmp_path / "a")
    second = export_result(result, source_path, tmp_path / "b")
    assert first[0].name == second[0].name
    assert sha256(first[0].read_bytes()).hexdigest() == sha256(second[0].read_bytes()).hexdigest()
    assert sha256(first[2].read_bytes()).hexdigest() == sha256(second[2].read_bytes()).hexdigest()
    manifest = json.loads(first[1].read_text())
    readback = readback_stl(str(first[0]))
    assert readback.volume_mm3 > 0 and readback.component_count == 1
    assert readback.watertight and readback.winding_consistent
    assert readback.bounds_mm == ((-10.0, -10.0, -10.0), (10.0, 10.0, 10.0))
    assert manifest["output"]["three_mf"]["produced"] is False
    assert sha256(source_path.read_bytes()).hexdigest() == source_hash
