from __future__ import annotations

import trimesh
import pytest

from herculean_columns.materialize import SourceAdmissionError, admit_source
from tests.materialize.helpers import write_box


pytestmark = pytest.mark.geometry


def test_unknown_units_are_rejected(tmp_path) -> None:
    source = write_box(tmp_path / "box.stl")
    with pytest.raises(SourceAdmissionError, match="declared explicitly") as caught:
        admit_source(source, units=None)
    assert caught.value.code == "UNKNOWN_UNITS"


def test_non_watertight_source_is_rejected_without_mutation(tmp_path) -> None:
    source = tmp_path / "open.stl"
    mesh = trimesh.creation.box((10, 10, 10))
    mesh.update_faces(range(len(mesh.faces) - 1))
    mesh.export(source)
    before = source.read_bytes()
    with pytest.raises(SourceAdmissionError) as caught:
        admit_source(source, units="mm")
    assert caught.value.code == "NON_WATERTIGHT_SOURCE"
    assert source.read_bytes() == before


def test_valid_stl_records_identity_and_normalization(tmp_path) -> None:
    source = write_box(tmp_path / "box.stl")
    admitted = admit_source(source, units="mm")
    assert admitted.watertight and admitted.winding_consistent
    assert admitted.component_count == 1
    assert admitted.volume_mm3 == pytest.approx(8000.0)
    assert admitted.normalizations == ("merge-identical-stl-vertices",)
