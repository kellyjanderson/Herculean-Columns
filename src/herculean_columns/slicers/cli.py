from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import subprocess
import time
from pathlib import Path

from .backend import BackendCapabilities, BackendIdentity, ProfileBundle, SliceFailure, SliceRequest, SliceResult
from .gcode import parse_gcode


class CliSlicerBackend:
    backend_name = "cli"
    version_prefix = ""
    supported_engine = re.compile(r".+")

    def __init__(self, executable: str | Path) -> None:
        self.executable = Path(executable)

    def discover_identity(self) -> BackendIdentity:
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise SliceFailure("missing_executable", f"Executable not found: {self.executable}")
        try:
            completed = subprocess.run([self.executable, "--help"], capture_output=True, text=True, timeout=20, check=False)
        except subprocess.TimeoutExpired as exc:
            raise SliceFailure("timeout", "Version discovery timed out") from exc
        output = completed.stdout + completed.stderr
        first = next((line.strip().rstrip(":") for line in output.splitlines() if self.version_prefix in line), "")
        if not first or not self.supported_engine.fullmatch(first):
            raise SliceFailure("unsupported_version", f"Unsupported engine identity: {first or 'unknown'}")
        bundle = None
        # Bundle executables live at App.app/Contents/MacOS/name; Info.plist is
        # a sibling of MacOS under Contents.
        plist = self.executable.parents[1] / "Info.plist"
        if plist.exists():
            with plist.open("rb") as stream:
                info = plistlib.load(stream)
            bundle = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "unknown")
        return BackendIdentity(self.backend_name, str(self.executable), hashlib.sha256(self.executable.read_bytes()).hexdigest(), bundle, first, True)

    def discover_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(("lightning", "rectilinear", "cubic", "gyroid"), True, True, True)

    def validate_profiles(self, profiles: ProfileBundle) -> None:
        actual = {key: hashlib.sha256(getattr(profiles, key).read_bytes()).hexdigest() for key in ("machine", "process", "filament")}
        if actual != profiles.hashes:
            raise SliceFailure("profile_drift", "Checked-in profile hash mismatch", evidence={"expected": profiles.hashes, "actual": actual})
        for path, expected in ((profiles.machine, "machine"), (profiles.process, "process"), (profiles.filament, "filament")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("type") != expected or data.get("from") != "user" or data.get("name", "").startswith("System"):
                raise SliceFailure("profile_fallback", f"Invalid isolated {expected} profile: {path}")

    def slice(self, request: SliceRequest) -> SliceResult:
        identity = self.discover_identity()
        self.validate_profiles(request.profiles)
        if request.pattern not in self.discover_capabilities().patterns:
            raise SliceFailure("unsupported_pattern", request.pattern)
        before = request.model.stat()
        request.output_dir.mkdir(parents=True, exist_ok=False)
        request.data_dir.mkdir(parents=True, exist_ok=True)
        stdout_log, stderr_log = request.output_dir / "stdout.log", request.output_dir / "stderr.log"
        exported_settings = request.output_dir / "applied-settings.json"
        cmd = [str(self.executable), "--datadir", str(request.data_dir), "--load-settings", f"{request.profiles.machine};{request.profiles.process}", "--load-filaments", str(request.profiles.filament), "--outputdir", str(request.output_dir), "--export-settings", str(exported_settings), "--arrange", "1", "--ensure-on-bed", "--slice", "0", str(request.model)]
        started = time.time_ns()
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=request.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            timeout_stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            timeout_stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout_log.write_text(timeout_stdout, encoding="utf-8")
            stderr_log.write_text(timeout_stderr, encoding="utf-8")
            raise SliceFailure("timeout", "Slicer exceeded bounded execution", evidence={"command": cmd, "timeout_seconds": request.timeout_seconds}) from exc
        stdout_log.write_text(completed.stdout, encoding="utf-8")
        stderr_log.write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise SliceFailure("process_failed", f"Slicer exited {completed.returncode}", evidence={"command": cmd, "returncode": completed.returncode, "stdout": str(stdout_log), "stderr": str(stderr_log)})
        gcodes = sorted(request.output_dir.glob("*.gcode"))
        if len(gcodes) != 1:
            raise SliceFailure("partial_gcode", f"Expected one G-code artifact, found {len(gcodes)}")
        gcode = gcodes[0]
        if gcode.stat().st_mtime_ns < started:
            raise SliceFailure("stale_artifact", f"Output predates invocation: {gcode}")
        after = request.model.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise SliceFailure("stale_artifact", "Input model changed during slicing")
        if not exported_settings.is_file():
            raise SliceFailure("profile_fallback", "Slicer did not export applied settings")
        try:
            applied = json.loads(exported_settings.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise SliceFailure("parse_error", "Applied settings are not valid JSON") from exc
        expected_density = f"{request.slicer_infill_percent:g}%"
        checks = {
            "profile": request.profiles.profile_id in str(applied.get("print_settings_id", "")),
            "density": applied.get("sparse_infill_density") == expected_density,
            "pattern": applied.get("sparse_infill_pattern") == request.pattern,
            "support": applied.get("enable_support") == "0",
        }
        if not all(checks.values()):
            raise SliceFailure("profile_fallback", "Applied settings do not match the requested profile", evidence={"checks": checks, "expected_density": expected_density})
        metrics = parse_gcode(gcode)
        warnings = tuple(line for line in (completed.stdout + completed.stderr).splitlines() if "warn" in line.lower())
        return SliceResult(identity, request, gcode, exported_settings, stdout_log, stderr_log, metrics, warnings)


class CrealityPrintBackend(CliSlicerBackend):
    backend_name = "creality-print"
    version_prefix = "Creality-"
    supported_engine = re.compile(r"Creality-01\..+")


class OrcaSlicerBackend(CliSlicerBackend):
    backend_name = "orca-slicer"
    version_prefix = "OrcaSlicer-"
    supported_engine = re.compile(r"OrcaSlicer-2\..+")
