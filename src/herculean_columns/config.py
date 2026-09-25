from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .geometry import Vec3, norm


class Orientation(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    direction: Vec3

    @field_validator("direction")
    @classmethod
    def nonzero_direction(cls, value: Vec3) -> Vec3:
        if norm(value) <= 1e-12:
            raise ValueError("orientation direction must be non-zero")
        return value


DEFAULT_ORIENTATIONS = (
    Orientation(name="X", direction=(1.0, 0.0, 0.0)),
    Orientation(name="Y", direction=(0.0, 1.0, 0.0)),
    Orientation(name="Z", direction=(0.0, 0.0, 1.0)),
    Orientation(name="XY+", direction=(1.0, 1.0, 0.0)),
    Orientation(name="XY-", direction=(1.0, -1.0, 0.0)),
)


class HerculeanConfig(BaseModel):
    """All distances are millimetres and density inputs are percent."""

    model_config = ConfigDict(frozen=True)

    infill_percent: float = Field(gt=0.0, le=100.0)
    member_radius_mm: float = Field(default=0.30, gt=0.0)
    orientation_sample_pitch_mm: float = Field(default=8.0, gt=0.0)
    ray_step_mm: float = Field(default=0.75, gt=0.0)
    boundary_tolerance_mm: float = Field(default=0.01, gt=0.0)
    containment_step_mm: float = Field(default=0.25, gt=0.0)
    min_concern_span_mm: float = Field(default=4.0, gt=0.0)
    max_concerns_per_orientation: int = Field(default=64, ge=1)
    support_reserve_fraction: float = Field(default=0.15, ge=0.0, lt=1.0)
    budget_tolerance_percent: float = Field(default=0.25, ge=0.0)
    build_plate_epsilon_mm: float = Field(default=0.45, ge=0.0)
    support_search_radius_mm: float = Field(default=20.0, gt=0.0)
    max_angle_from_vertical_deg: float = Field(default=45.0, gt=0.0, lt=90.0)
    orientations: tuple[Orientation, ...] = DEFAULT_ORIENTATIONS

    @field_validator("orientations")
    @classmethod
    def orientations_are_unique(cls, value: tuple[Orientation, ...]) -> tuple[Orientation, ...]:
        if not value:
            raise ValueError("at least one orientation is required")
        names = [orientation.name for orientation in value]
        if len(names) != len(set(names)):
            raise ValueError("orientation names must be unique")
        return value
