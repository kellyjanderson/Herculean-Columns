from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from herculean_columns import HerculeanConfig, Orientation


@pytest.mark.unit
@pytest.mark.parametrize("value", [0.0, -1.0, 100.1])
def test_infill_percentage_boundaries_reject_invalid_values(value: float) -> None:
    with pytest.raises(ValidationError):
        HerculeanConfig(infill_percent=value)


@pytest.mark.unit
@pytest.mark.parametrize("value", [0.01, 1.0, 50.0, 100.0])
def test_infill_percentage_accepts_declared_range(value: float) -> None:
    assert HerculeanConfig(infill_percent=value).infill_percent == value


@pytest.mark.unit
def test_units_and_stable_configuration_serialization() -> None:
    config = HerculeanConfig(infill_percent=12.5, member_radius_mm=0.4)
    encoded = config.model_dump_json()
    assert json.loads(encoded)["member_radius_mm"] == 0.4
    assert encoded == config.model_dump_json()


@pytest.mark.unit
def test_duplicate_orientation_names_are_rejected() -> None:
    duplicate = Orientation(name="X", direction=(1.0, 0.0, 0.0))
    with pytest.raises(ValidationError):
        HerculeanConfig(infill_percent=10.0, orientations=(duplicate, duplicate))
