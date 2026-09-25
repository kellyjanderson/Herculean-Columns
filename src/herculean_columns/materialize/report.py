from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FailureDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None
    details: dict[str, object] = Field(default_factory=dict)


class MaterializationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    success: bool
    source: dict[str, object]
    graph_sha256: str
    configuration: dict[str, object]
    configuration_sha256: str
    tool_versions: dict[str, str]
    shell_thickness_mm: float
    legal_domain_volume_mm3: float
    source_volume_mm3: float
    shell_volume_mm3: float
    structural_member_volume_mm3: float
    print_support_member_volume_mm3: float
    unioned_internal_volume_mm3: float
    requested_infill_percent: float
    achieved_infill_percent: float
    absolute_deviation_percent: float
    output: dict[str, object] | None = None
    validation: dict[str, object] = Field(default_factory=dict)
    failures: tuple[FailureDetail, ...] = ()
