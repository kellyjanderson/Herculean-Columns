from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Sequence

from shapely.geometry import box

from .config import HerculeanConfig
from .domain import Layer, LayerStackVolume
from .generator import HerculeanGenerator
from .ids import NodeId
from .export import export_result
from .materialize import MaterializationError, SolidMaterializer, SourceAdmissionError, admit_source
from .model import EdgeKind, StructuralGraph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and validate a Herculean structural graph")
    parser.add_argument("--infill-percent", type=float, required=True)
    parser.add_argument("--width-mm", type=float, default=20.0)
    parser.add_argument("--depth-mm", type=float, default=20.0)
    parser.add_argument("--height-mm", type=float, default=20.0)
    return parser


def build_materialize_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize a Herculean graph as a printable STL")
    parser.add_argument("source", type=Path)
    parser.add_argument("graph", type=Path, help="HC-PS-010 stable graph JSON")
    parser.add_argument("config", type=Path, help="HerculeanConfig JSON")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-units", required=True, choices=("mm",))
    return parser


def _graph_from_json(path: Path) -> StructuralGraph:
    payload = json.loads(path.read_text(encoding="utf-8"))
    graph_payload = payload.get("graph", payload)
    graph = StructuralGraph()
    identities: dict[int, NodeId] = {}
    for item in sorted(graph_payload["nodes"], key=lambda value: value["id"]):
        identity = graph.add_node(tuple(item["xyz_mm"]), shell_anchor=bool(item.get("shell_anchor", False)), grounded=bool(item.get("grounded", False)))
        if identity.value != item["id"]:
            raise ValueError("graph node identities must be contiguous and monotonic")
        identities[item["id"]] = identity
    for item in sorted(graph_payload["edges"], key=lambda value: value["id"]):
        edge = graph.add_edge(identities[item["a"]], identities[item["b"]], EdgeKind(item["kind"]))
        if edge is None or edge.value != item["id"]:
            raise ValueError("graph edge identities must be contiguous and monotonic")
    return graph


def materialize_main(argv: Sequence[str]) -> int:
    args = build_materialize_parser().parse_args(argv)
    try:
        graph = _graph_from_json(args.graph)
        config = HerculeanConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
        source = admit_source(args.source, units=args.source_units)
        result = SolidMaterializer(config).materialize(source, graph)
        stl, manifest, preview = export_result(result, args.source, args.output_dir)
    except (MaterializationError, SourceAdmissionError, ValueError, OSError) as error:
        if isinstance(error, MaterializationError):
            payload = error.failure.model_dump(mode="json")
        elif isinstance(error, SourceAdmissionError):
            payload = {"code": error.code, "message": str(error)}
        else:
            payload = {"code": "INVALID_INPUT", "message": str(error)}
        print(json.dumps({"success": False, "diagnostic": payload}, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps({"success": True, "manifest": str(manifest), "stl": str(stl), "preview": str(preview)}, sort_keys=True, separators=(",", ":")))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "materialize":
        return materialize_main(arguments[1:])
    args = build_parser().parse_args(arguments)
    if min(args.width_mm, args.depth_mm, args.height_mm) <= 0.0:
        build_parser().error("fixture dimensions must be positive")
    region = box(0.0, 0.0, args.width_mm, args.depth_mm)
    volume = LayerStackVolume((Layer(0.0, region), Layer(args.height_mm, region)))
    result = HerculeanGenerator(HerculeanConfig(infill_percent=args.infill_percent)).generate(volume)
    print(json.dumps(result.stable_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
