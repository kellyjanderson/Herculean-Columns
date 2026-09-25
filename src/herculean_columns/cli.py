from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from shapely.geometry import box

from .config import HerculeanConfig
from .domain import Layer, LayerStackVolume
from .generator import HerculeanGenerator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and validate a Herculean structural graph")
    parser.add_argument("--infill-percent", type=float, required=True)
    parser.add_argument("--width-mm", type=float, default=20.0)
    parser.add_argument("--depth-mm", type=float, default=20.0)
    parser.add_argument("--height-mm", type=float, default=20.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if min(args.width_mm, args.depth_mm, args.height_mm) <= 0.0:
        build_parser().error("fixture dimensions must be positive")
    region = box(0.0, 0.0, args.width_mm, args.depth_mm)
    volume = LayerStackVolume((Layer(0.0, region), Layer(args.height_mm, region)))
    result = HerculeanGenerator(HerculeanConfig(infill_percent=args.infill_percent)).generate(volume)
    print(json.dumps(result.stable_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
