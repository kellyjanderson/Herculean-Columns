from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from herculean_columns.slicers import CrealityPrintBackend, FakeSlicerBackend, ProfileBundle, SliceFailure, SliceRequest
from herculean_columns.slicers.gcode import parse_gcode


def _profiles(tmp_path: Path) -> ProfileBundle:
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {}
    for kind in ("machine", "process", "filament"):
        path = tmp_path / f"{kind}.json"
        path.write_text(json.dumps({"type": kind, "from": "user", "name": f"HC-VIRTUAL-FDM-V1-{kind}"}), encoding="utf-8")
        paths[kind] = path
    return ProfileBundle(paths["machine"], paths["process"], paths["filament"], "HC-VIRTUAL-FDM-V1", {kind: hashlib.sha256(path.read_bytes()).hexdigest() for kind, path in paths.items()})


def test_missing_executable_is_structured(tmp_path: Path) -> None:
    with pytest.raises(SliceFailure, match="Executable not found") as caught:
        CrealityPrintBackend(tmp_path / "missing").discover_identity()
    assert caught.value.code == "missing_executable"


def test_unsupported_version_is_structured(tmp_path: Path) -> None:
    executable = tmp_path / "slicer"
    executable.write_text("#!/bin/sh\necho Alien-9:\n", encoding="utf-8"); executable.chmod(0o755)
    with pytest.raises(SliceFailure) as caught:
        CrealityPrintBackend(executable).discover_identity()
    assert caught.value.code == "unsupported_version"


def test_profile_drift_and_fallback_are_rejected(tmp_path: Path) -> None:
    profiles = _profiles(tmp_path)
    profiles.machine.write_text("{}", encoding="utf-8")
    backend = CrealityPrintBackend(tmp_path / "unused")
    with pytest.raises(SliceFailure) as caught:
        backend.validate_profiles(profiles)
    assert caught.value.code == "profile_drift"


def test_profile_fallback_is_rejected(tmp_path: Path) -> None:
    profiles = _profiles(tmp_path)
    profiles.machine.write_text(json.dumps({"type": "machine", "from": "system", "name": "System default"}), encoding="utf-8")
    profiles = ProfileBundle(profiles.machine, profiles.process, profiles.filament, profiles.profile_id, {**profiles.hashes, "machine": hashlib.sha256(profiles.machine.read_bytes()).hexdigest()})
    with pytest.raises(SliceFailure) as caught:
        CrealityPrintBackend(tmp_path / "unused").validate_profiles(profiles)
    assert caught.value.code == "profile_fallback"


def test_fake_is_always_non_authoritative(tmp_path: Path) -> None:
    profiles = _profiles(tmp_path)
    model = tmp_path / "model.stl"; model.write_bytes(b"solid fake\nendsolid fake\n")
    result = FakeSlicerBackend().slice(SliceRequest(model, tmp_path / "out", tmp_path / "data", profiles, "gyroid", 15))
    assert result.identity.authoritative is False
    assert "NON_AUTHORITATIVE_FAKE" in result.warnings


def test_partial_gcode_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "partial.gcode"; path.write_text("G1 X1 E1\n", encoding="utf-8")
    with pytest.raises(SliceFailure) as caught:
        parse_gcode(path)
    assert caught.value.code == "partial_gcode"


def test_unavailable_metrics_are_none_not_zero(tmp_path: Path) -> None:
    path = tmp_path / "valid.gcode"
    path.write_text("; enough metadata padding for parser validation xxxxxxxxxxxxx\nG1 X0 Y0 E0\nG1 X10 Y0 E1\nM104 S0\nM84\n", encoding="utf-8")
    metrics = parse_gcode(path)
    assert metrics["filament_mass_g"] is None
    assert metrics["estimated_time_seconds"] is None


def test_timeout_is_structured_and_logs_are_retained(tmp_path: Path) -> None:
    executable = tmp_path / "slicer"
    executable.write_text("#!/bin/sh\ncase \"$1\" in --help) echo Creality-01.09.03.50:;; *) sleep 2;; esac\n", encoding="utf-8"); executable.chmod(0o755)
    profiles = _profiles(tmp_path / "profiles")
    model = tmp_path / "model.stl"; model.write_bytes(b"solid fake\nendsolid fake\n")
    output = tmp_path / "out"
    with pytest.raises(SliceFailure) as caught:
        CrealityPrintBackend(executable).slice(SliceRequest(model, output, tmp_path / "data", profiles, "gyroid", 15, timeout_seconds=0.05))
    assert caught.value.code == "timeout"
    assert (output / "stdout.log").is_file()
