from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from .geometry import Vec3


class VolumeAdapter(Protocol):
    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]: ...

    @property
    def volume_mm3(self) -> float: ...

    def contains(self, point: Vec3, clearance_mm: float = 0.0) -> bool: ...


@dataclass(frozen=True)
class Layer:
    z_mm: float
    region: BaseGeometry


class LayerStackVolume:
    """A deterministic piecewise-constant legal domain from horizontal layers."""

    def __init__(self, layers: Sequence[Layer]) -> None:
        self.layers = tuple(layers)
        if len(self.layers) < 2:
            raise ValueError("at least two layers are required")
        if any(b.z_mm <= a.z_mm for a, b in zip(self.layers, self.layers[1:])):
            raise ValueError("layers must be strictly increasing in Z")
        if any(layer.region.is_empty or not layer.region.is_valid for layer in self.layers):
            raise ValueError("layer regions must be non-empty and valid")
        min_x = min(layer.region.bounds[0] for layer in self.layers)
        min_y = min(layer.region.bounds[1] for layer in self.layers)
        max_x = max(layer.region.bounds[2] for layer in self.layers)
        max_y = max(layer.region.bounds[3] for layer in self.layers)
        self._bounds = (min_x, min_y, self.layers[0].z_mm, max_x, max_y, self.layers[-1].z_mm)

    @property
    def bounds(self) -> tuple[float, float, float, float, float, float]:
        return self._bounds

    @property
    def volume_mm3(self) -> float:
        return float(sum(
            (a.region.area + b.region.area) * 0.5 * (b.z_mm - a.z_mm)
            for a, b in zip(self.layers, self.layers[1:])
        ))

    def contains(self, point: Vec3, clearance_mm: float = 0.0) -> bool:
        x, y, z = point
        if (
            z < self.layers[0].z_mm + clearance_mm - 1e-9
            or z > self.layers[-1].z_mm - clearance_mm + 1e-9
        ):
            return False
        layer = min(self.layers, key=lambda candidate: abs(candidate.z_mm - z))
        legal = layer.region.buffer(-clearance_mm) if clearance_mm > 0.0 else layer.region
        return not legal.is_empty and legal.buffer(1e-9).covers(Point(x, y))
