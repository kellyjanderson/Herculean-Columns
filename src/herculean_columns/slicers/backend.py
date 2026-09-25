from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol


FailureCode = Literal[
    "missing_executable", "unsupported_version", "profile_drift", "profile_fallback",
    "timeout", "partial_gcode", "stale_artifact", "unsupported_pattern", "parse_error",
    "process_failed", "metric_omission",
]


class SliceFailure(RuntimeError):
    def __init__(self, code: FailureCode, message: str, *, evidence: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.evidence = evidence or {}


@dataclass(frozen=True)
class BackendIdentity:
    backend: str
    executable: str
    executable_sha256: str
    bundle_version: str | None
    engine_version: str
    authoritative: bool


@dataclass(frozen=True)
class BackendCapabilities:
    patterns: tuple[str, ...]
    isolated_data_directory: bool
    gcode_export: bool
    settings_export: bool


@dataclass(frozen=True)
class ProfileBundle:
    machine: Path
    process: Path
    filament: Path
    profile_id: str
    hashes: dict[str, str]


@dataclass(frozen=True)
class SliceRequest:
    model: Path
    output_dir: Path
    data_dir: Path
    profiles: ProfileBundle
    pattern: str
    slicer_infill_percent: float
    requested_herculean_percent: float | None = None
    timeout_seconds: float = 180.0


@dataclass(frozen=True)
class SliceResult:
    identity: BackendIdentity
    request: SliceRequest
    gcode: Path
    settings: Path
    stdout_log: Path
    stderr_log: Path
    metrics: dict[str, object]
    warnings: tuple[str, ...] = field(default_factory=tuple)


class SlicerBackend(Protocol):
    def discover_identity(self) -> BackendIdentity: ...
    def discover_capabilities(self) -> BackendCapabilities: ...
    def validate_profiles(self, profiles: ProfileBundle) -> None: ...
    def slice(self, request: SliceRequest) -> SliceResult: ...
