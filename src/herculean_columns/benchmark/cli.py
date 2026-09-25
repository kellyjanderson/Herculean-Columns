from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ..slicers import CrealityPrintBackend, OrcaSlicerBackend
from .compatibility import CompatibilityEvidenceError, validate_creality_import_receipt
from .run import BenchmarkRunner, Variant


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the controlled five-variant FDM benchmark")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--herculean", type=Path, required=True)
    parser.add_argument("--materialization-manifest", type=Path, required=True)
    parser.add_argument("--infill-percent", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, default=Path("profiles/virtual-fdm"))
    parser.add_argument("--backend", choices=("creality", "orca"), default="creality")
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--creality-executable", type=Path, default=Path("/Applications/Creality Print.app/Contents/MacOS/CrealityPrint"), help="Creality executable used to verify fallback receipt identity")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--creality-import-receipt", type=Path, help="hash-bound human import/preview receipt required for a Creality-failure fallback")
    parser.add_argument("--fallback-from-creality-failure", action="store_true", help="record that Orca is selected after failed Creality qualification")
    return parser


def main() -> int:
    args = _parser().parse_args()
    manifest = json.loads(args.materialization_manifest.read_text(encoding="utf-8"))
    if float(manifest["requested_infill_percent"]) != args.infill_percent:
        raise SystemExit("materialization manifest requested percentage differs from benchmark request")
    executable = args.executable or Path("/Applications/Creality Print.app/Contents/MacOS/CrealityPrint" if args.backend == "creality" else "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer")
    backend = CrealityPrintBackend(executable) if args.backend == "creality" else OrcaSlicerBackend(executable)
    fallback_evidence: dict[str, object] | None = None
    if args.fallback_from_creality_failure:
        if args.backend != "orca" or args.creality_import_receipt is None:
            raise SystemExit("Creality-failure fallback requires Orca and --creality-import-receipt")
        try:
            creality_identity = CrealityPrintBackend(args.creality_executable).discover_identity()
            receipt = validate_creality_import_receipt(args.creality_import_receipt, args.herculean, creality_identity)
        except CompatibilityEvidenceError as exc:
            raise SystemExit(f"invalid Creality compatibility evidence: {exc}") from exc
        fallback_evidence = {"decision": "orca_after_creality_qualification_failure", "creality_import_receipt": asdict(receipt)}
    elif args.creality_import_receipt is not None:
        raise SystemExit("--creality-import-receipt is valid only with --fallback-from-creality-failure")
    common = {"requested_percent": args.infill_percent}
    variants = [
        Variant("herculean", "rectilinear", args.herculean, **common, achieved_herculean_percent=float(manifest["achieved_infill_percent"]), density_planning_configuration=manifest["configuration"], structural_volume_mm3=float(manifest["structural_member_volume_mm3"]), print_support_volume_mm3=float(manifest["print_support_member_volume_mm3"])),
        *(Variant(name, name, args.source, **common) for name in ("lightning", "rectilinear", "cubic", "gyroid")),
    ]
    result = BenchmarkRunner(backend, args.profiles, args.output, fallback_evidence=fallback_evidence).run(variants, timeout_seconds=args.timeout)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
