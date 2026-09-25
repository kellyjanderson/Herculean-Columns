from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from ..slicers import ProfileBundle, SliceFailure, SliceRequest, SlicerBackend


class BenchmarkFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class Variant:
    name: str
    pattern: str
    model: Path
    requested_percent: float
    achieved_herculean_percent: float | None = None
    density_planning_configuration: dict[str, object] | None = None
    structural_volume_mm3: float | None = None
    print_support_volume_mm3: float | None = None

    @property
    def slicer_infill_percent(self) -> float:
        return 0.0 if self.name == "herculean" else self.requested_percent


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_profiles(root: Path) -> ProfileBundle:
    descriptor = json.loads((root / "profile.json").read_text(encoding="utf-8"))
    paths = {key: root / descriptor[key] for key in ("machine", "process", "filament")}
    return ProfileBundle(paths["machine"], paths["process"], paths["filament"], descriptor["profile_id"], {key: _sha(path) for key, path in paths.items()})


class BenchmarkRunner:
    def __init__(self, backend: SlicerBackend, profile_root: Path, output_root: Path, *, fallback_evidence: dict[str, object] | None = None) -> None:
        self.backend = backend
        self.base_profiles = load_profiles(profile_root)
        self.output_root = output_root
        self.fallback_evidence = fallback_evidence

    def _variant_profiles(self, variant: Variant, work: Path) -> ProfileBundle:
        profile_dir = work / "profiles"
        profile_dir.mkdir(parents=True)
        machine = profile_dir / "machine.json"; shutil.copy2(self.base_profiles.machine, machine)
        filament = profile_dir / "filament.json"; shutil.copy2(self.base_profiles.filament, filament)
        process = profile_dir / "process.json"
        values = json.loads(self.base_profiles.process.read_text(encoding="utf-8"))
        values["sparse_infill_pattern"] = variant.pattern
        values["sparse_infill_density"] = f"{variant.slicer_infill_percent:g}%"
        values["name"] = f"{self.base_profiles.profile_id} {variant.name} {variant.slicer_infill_percent:g}"
        process.write_text(json.dumps(values, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        paths = {"machine": machine, "process": process, "filament": filament}
        return ProfileBundle(machine, process, filament, self.base_profiles.profile_id, {key: _sha(path) for key, path in paths.items()})

    def run(self, variants: list[Variant], *, timeout_seconds: float = 180.0) -> Path:
        if {v.name for v in variants} != {"herculean", "lightning", "rectilinear", "cubic", "gyroid"}:
            raise BenchmarkFailure("The exact five-variant matrix is required")
        if any(v.name == "herculean" and v.slicer_infill_percent != 0 for v in variants):
            raise BenchmarkFailure("Herculean downstream slicer infill must remain zero")
        identity = self.backend.discover_identity()
        if not identity.authoritative:
            raise BenchmarkFailure("Non-authoritative backend cannot create comparison evidence")
        input_identity = [{"name": v.name, "model_sha256": _sha(v.model), "requested_percent": v.requested_percent, "slicer_infill_percent": v.slicer_infill_percent} for v in variants]
        run_key = hashlib.sha256(json.dumps({"backend": asdict(identity), "profiles": self.base_profiles.hashes, "variants": input_identity, "fallback_evidence": self.fallback_evidence}, sort_keys=True).encode()).hexdigest()
        final = self.output_root / run_key
        if final.exists():
            raise BenchmarkFailure(f"stale artifact reuse refused: {final}")
        staging = self.output_root / f".{run_key}.partial"
        if staging.exists():
            raise BenchmarkFailure(f"partial run exists: {staging}")
        staging.mkdir(parents=True)
        records: list[dict[str, object]] = []
        try:
            for variant in variants:
                variant_dir = staging / variant.name
                profiles = self._variant_profiles(variant, variant_dir)
                result = self.backend.slice(SliceRequest(variant.model, variant_dir / "artifacts", variant_dir / "data", profiles, variant.pattern, variant.slicer_infill_percent, variant.requested_percent if variant.name == "herculean" else None, timeout_seconds))
                metrics = dict(result.metrics)
                required = ("estimated_time_seconds", "filament_length_mm", "filament_mass_g", "deposited_volume_mm3", "extrusion_distance_mm", "travel_distance_mm", "retractions", "restarts", "feature_time_seconds", "short_segment_distribution", "artifact_sha256")
                if any(key not in metrics for key in required):
                    raise SliceFailure("metric_omission", f"Backend omitted normalized metrics for {variant.name}")
                metrics.update({"variant": variant.name, "pattern": variant.pattern, "requested_herculean_percent": variant.requested_percent if variant.name == "herculean" else None, "achieved_herculean_percent": variant.achieved_herculean_percent, "slicer_infill_percent": variant.slicer_infill_percent, "density_planning_configuration": variant.density_planning_configuration, "structural_volume_mm3": variant.structural_volume_mm3, "print_support_volume_mm3": variant.print_support_volume_mm3, "authoritative": result.identity.authoritative, "warnings": list(result.warnings), "model_sha256": _sha(variant.model), "profile_hashes": profiles.hashes})
                if variant.name == "herculean" and metrics["requested_herculean_percent"] == metrics["slicer_infill_percent"]:
                    raise BenchmarkFailure("slicer infill overwrote Herculean requested percentage")
                (variant_dir / "metrics.json").write_text(json.dumps(metrics, sort_keys=True, indent=2) + "\n", encoding="utf-8")
                records.append(metrics)
            manifest = {"schema_version": 1, "run_id": run_key, "backend": asdict(identity), "base_profile_hashes": self.base_profiles.hashes, "fallback_evidence": self.fallback_evidence, "variants": records}
            (staging / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            with (staging / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["variant", "pattern", "requested_herculean_percent", "achieved_herculean_percent", "slicer_infill_percent", "estimated_time_seconds", "filament_length_mm", "filament_mass_g", "deposited_volume_mm3", "extrusion_distance_mm", "travel_distance_mm", "retractions", "restarts", "artifact_sha256"])
                writer.writeheader(); writer.writerows({key: item.get(key) for key in writer.fieldnames} for item in records)
            staging.rename(final)
            return final
        except BaseException:
            raise
