from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import trimesh

from ..materialize.pipeline import MaterializationResult


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _preview(result: MaterializationResult) -> bytes:
    low, high = result.body.bounds
    span = np.maximum(high - low, 1e-9)
    scale = min(300.0 / float(span[0]), 300.0 / float(span[2]))
    colors = ((result.shell, "#263238", "shell"), (result.structural, "#1769aa", "structural"), (result.support, "#e67e22", "support"), (result.junctions, "#7b1fa2", "junctions"))
    shapes: list[str] = []
    for panel, (mesh, color, label) in enumerate(colors):
        origin_x = 35.0 + (panel % 2) * 390.0
        origin_y = 360.0 + (panel // 2) * 390.0
        shapes.append(f'<rect x="{origin_x:.3f}" y="{origin_y-320:.3f}" width="330" height="330" fill="#fafafa" stroke="#cfd8dc"/><text x="{origin_x:.3f}" y="{origin_y-326:.3f}" font-family="sans-serif" font-size="16" fill="{color}">{label}</text>')
        if mesh.is_empty:
            continue
        edges = mesh.edges_unique
        stride = max(1, len(edges) // 3000)
        for a_index, b_index in edges[::stride]:
            a, b = mesh.vertices[int(a_index)], mesh.vertices[int(b_index)]
            x1 = origin_x + 15.0 + (float(a[0]) - low[0]) * scale
            y1 = origin_y - 15.0 - (float(a[2]) - low[2]) * scale
            x2 = origin_x + 15.0 + (float(b[0]) - low[0]) * scale
            y2 = origin_y - 15.0 - (float(b[2]) - low[2]) * scale
            shapes.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="{color}" stroke-width="0.7" stroke-opacity="0.55"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800"><rect width="800" height="800" fill="white"/>{"".join(shapes)}<text x="60" y="785" font-family="sans-serif" font-size="14">Deterministic XZ mesh projection; open STL for full surface inspection</text></svg>\n').encode()


def export_result(result: MaterializationResult, source_path: str | Path, output_dir: str | Path) -> tuple[Path, Path, Path]:
    source = Path(source_path).resolve()
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    identity = sha256((str(result.report.source["sha256"]) + result.report.graph_sha256 + result.report.configuration_sha256).encode()).hexdigest()[:16]
    stem = f"{source.stem}-herculean-{identity}"
    stl, manifest, preview = destination / f"{stem}.stl", destination / f"{stem}.manifest.json", destination / f"{stem}.preview.svg"
    if source in {stl, manifest, preview}:
        raise ValueError("output must not overwrite the source asset")
    existing = [path for path in (stl, manifest, preview) if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing artifact: {existing[0]}")
    stl.write_bytes(cast(bytes, result.body.export(file_type="stl")))
    preview.write_bytes(_preview(result))
    output = {
        "stl": str(stl), "stl_sha256": _hash(stl),
        "preview_svg": str(preview), "preview_sha256": _hash(preview),
        "three_mf": {"produced": False, "reason": "trimesh 5.1.0 has no 3MF exporter; units and provenance cannot be round-tripped"},
    }
    report = result.report.model_copy(update={"output": output})
    manifest.write_text(json.dumps(report.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return stl, manifest, preview
