from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from herculean_columns.fixtures import FIXTURES, fixture_mesh


pytestmark = pytest.mark.geometry


def test_all_named_fixtures_are_single_watertight_parametric_bodies() -> None:
    assert {item.fixture_id for item in FIXTURES} == {"convex-box", "concave-l", "tapered-coupon", "three-point-bending-bar", "torsion-keyed-prism", "shell-indentation-coupon"}
    for definition in FIXTURES:
        mesh = fixture_mesh(definition)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume
        assert np.allclose(np.ptp(mesh.bounds, axis=0), definition.dimensions_mm, atol=0.001)


def test_deliberately_changed_dimensions_are_rejected_by_contract() -> None:
    definition = FIXTURES[0]
    changed = replace(definition, dimensions_mm=(21.0, 20.0, 20.0))
    assert not np.allclose(np.ptp(fixture_mesh(changed).bounds, axis=0), changed.dimensions_mm, atol=0.001)


def test_labels_are_absent_from_critical_geometry() -> None:
    assert all(definition.label is None for definition in FIXTURES)
