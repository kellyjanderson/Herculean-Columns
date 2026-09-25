from __future__ import annotations

from math import sqrt
from typing import TypeAlias

Vec3: TypeAlias = tuple[float, float, float]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Vec3, factor: float) -> Vec3:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return sqrt(dot(a, a))


def unit(a: Vec3) -> Vec3:
    length = norm(a)
    if length <= 1e-12:
        raise ValueError("direction must be non-zero")
    return scale(a, 1.0 / length)


def distance(a: Vec3, b: Vec3) -> float:
    return norm(subtract(a, b))


def lerp(a: Vec3, b: Vec3, fraction: float) -> Vec3:
    return add(a, scale(subtract(b, a), fraction))


def orthonormal_basis(direction: Vec3) -> tuple[Vec3, Vec3, Vec3]:
    d = unit(direction)
    helper: Vec3 = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = unit(cross(d, helper))
    return u, unit(cross(d, u)), d


def bbox_corners(bounds: tuple[float, float, float, float, float, float]) -> list[Vec3]:
    x0, y0, z0, x1, y1, z1 = bounds
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
