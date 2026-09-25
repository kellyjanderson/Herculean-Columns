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

    # Solid-materialization parameters.  These are explicit because the
    # required shell and legal domain must not depend on slicer defaults.
    line_width_mm: float = Field(default=0.45, gt=0.0)
    wall_count: int = Field(default=2, ge=1)
    top_bottom_thickness_mm: float = Field(default=0.8, gt=0.0)
    geometry_tolerance_mm: float = Field(default=0.05, gt=0.0)
    junction_radius_mm: float = Field(default=0.42, gt=0.0)
    strut_cross_section: str = Field(default="circular", pattern="^circular$")
    mesh_resolution_mm: float = Field(default=0.5, gt=0.0)
    exterior_tolerance_mm: float = Field(default=0.08, gt=0.0)

    @property
    def required_shell_thickness_mm(self) -> float:
        """Conservative isotropic shell used by the prototype solid boundary."""

        return max(
            self.line_width_mm * self.wall_count,
            self.top_bottom_thickness_mm,
        )

    @field_validator("junction_radius_mm")
    @classmethod
    def junction_overlaps_members(cls, value: float, info: object) -> float:
        # Cross-field ordering is intentionally checked in model validation by
        # the materializer as member_radius may not yet be available here.
        return value
    @field_validator("orientations")
    @classmethod
    def orientations_are_unique(cls, value: tuple[Orientation, ...]) -> tuple[Orientation, ...]:
        if not value:
            raise ValueError("at least one orientation is required")
        names = [orientation.name for orientation in value]
        if len(names) != len(set(names)):
            raise ValueError("orientation names must be unique")
        return value
