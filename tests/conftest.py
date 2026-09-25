from __future__ import annotations

import pytest
from shapely.geometry import box

from herculean_columns import Layer, LayerStackVolume


@pytest.fixture
def box_volume() -> LayerStackVolume:
    region = box(0.0, 0.0, 20.0, 20.0)
    return LayerStackVolume((Layer(0.0, region), Layer(20.0, region)))
