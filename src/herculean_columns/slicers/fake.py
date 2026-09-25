from __future__ import annotations

import hashlib
import json

from .backend import BackendCapabilities, BackendIdentity, ProfileBundle, SliceFailure, SliceRequest, SliceResult


class FakeSlicerBackend:
    def discover_identity(self) -> BackendIdentity:
        return BackendIdentity("fake", "<deterministic-fake>", hashlib.sha256(b"fake-v1").hexdigest(), "1", "fake-1", False)

    def discover_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(("lightning", "rectilinear", "cubic", "gyroid"), True, True, True)

    def validate_profiles(self, profiles: ProfileBundle) -> None:
        if set(profiles.hashes) != {"machine", "process", "filament"}:
            raise SliceFailure("profile_drift", "Incomplete fake profile identity")

    def slice(self, request: SliceRequest) -> SliceResult:
        request.output_dir.mkdir(parents=True, exist_ok=False)
        request.data_dir.mkdir(parents=True, exist_ok=True)
        gcode = request.output_dir / "fake.gcode"
        gcode.write_text("; NON-AUTHORITATIVE FAKE\n; filament used [mm] = 10\nG1 X0 Y0 E0\nG1 X1 Y0 E1\nM84\n", encoding="utf-8")
        settings = request.output_dir / "applied-settings.json"
        settings.write_text(json.dumps({"profile_id": request.profiles.profile_id, "sparse_infill_density": request.slicer_infill_percent}), encoding="utf-8")
        stdout = request.output_dir / "stdout.log"; stdout.write_text("deterministic fake\n", encoding="utf-8")
        stderr = request.output_dir / "stderr.log"; stderr.write_text("", encoding="utf-8")
        metrics: dict[str, object] = {"estimated_time_seconds": 1.0, "filament_length_mm": 10.0, "filament_mass_g": None, "deposited_volume_mm3": None, "extrusion_distance_mm": 1.0, "travel_distance_mm": 0.0, "retractions": 0, "restarts": 0, "feature_time_seconds": None, "short_segment_distribution": {"total": 1, "counts_below_mm": {"0.5": 0, "1.0": 0, "2.0": 1}}, "artifact_sha256": hashlib.sha256(gcode.read_bytes()).hexdigest()}
        return SliceResult(self.discover_identity(), request, gcode, settings, stdout, stderr, metrics, ("NON_AUTHORITATIVE_FAKE",))
