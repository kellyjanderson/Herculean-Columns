from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from .backend import SliceFailure

_TIME = re.compile(r"(?:estimated printing time[^=]*=|total estimated time:)\s*([^\r\n;]+)", re.I)
_FILAMENT_MM = re.compile(r"filament used \[mm\]\s*=\s*([0-9.]+)", re.I)
_FILAMENT_G = re.compile(r"filament used \[g\]\s*=\s*([0-9.]+)", re.I)
_FILAMENT_CM3 = re.compile(r"filament used \[cm3\]\s*=\s*([0-9.]+)", re.I)
_FEATURE = re.compile(r"^;\s*(?:TYPE|FEATURE):\s*(.+)$", re.I)


def _seconds(value: str) -> float | None:
    total = 0.0
    found = False
    for amount, unit in re.findall(r"([0-9.]+)\s*([dhms])", value.lower()):
        found = True
        total += float(amount) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
    return total if found else None


def parse_gcode(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if len(raw) < 64 or not re.search(r"\b(?:G0|G1)\b", text) or not re.search(r"\bM(?:84|104|140)\b", text):
        raise SliceFailure("partial_gcode", "G-code lacks motion or terminal shutdown commands", evidence={"bytes": len(raw)})
    x = y = z = e = 0.0
    extrusion = travel = 0.0
    retractions = restarts = 0
    segment_lengths: list[float] = []
    active_feature = "unknown"
    feature_distance: dict[str, float] = {}
    for line in text.splitlines():
        feature = _FEATURE.match(line)
        if feature:
            active_feature = feature.group(1).strip()
        if not re.match(r"^G[01](?:\s|$)", line):
            if line.startswith("G92"):
                reset = dict(re.findall(r"\b([XYZE])(-?[0-9.]+)", line))
                x, y, z, e = (float(reset.get(key, current)) for key, current in (("X", x), ("Y", y), ("Z", z), ("E", e)))
            continue
        values = {key: float(value) for key, value in re.findall(r"\b([XYZE])(-?[0-9.]+)", line)}
        nx, ny, nz, ne = values.get("X", x), values.get("Y", y), values.get("Z", z), values.get("E", e)
        distance = math.dist((x, y, z), (nx, ny, nz))
        delta_e = ne - e
        if delta_e > 0:
            extrusion += distance
            segment_lengths.append(distance)
            feature_distance[active_feature] = feature_distance.get(active_feature, 0.0) + distance
            if e < 0 <= ne:
                restarts += 1
        elif delta_e < 0:
            retractions += 1
        else:
            travel += distance
        x, y, z, e = nx, ny, nz, ne
    time_match = _TIME.search(text)
    length_match = _FILAMENT_MM.search(text)
    mass_match = _FILAMENT_G.search(text)
    volume_match = _FILAMENT_CM3.search(text)
    short = {str(limit): sum(1 for value in segment_lengths if value < limit) for limit in (0.5, 1.0, 2.0)}
    return {
        "estimated_time_seconds": _seconds(time_match.group(1)) if time_match else None,
        "filament_length_mm": float(length_match.group(1)) if length_match else None,
        "filament_mass_g": float(mass_match.group(1)) if mass_match else None,
        "deposited_volume_mm3": float(volume_match.group(1)) * 1000 if volume_match else None,
        "extrusion_distance_mm": extrusion,
        "travel_distance_mm": travel,
        "retractions": retractions,
        "restarts": restarts,
        "feature_time_seconds": None,
        "feature_extrusion_distance_mm": feature_distance,
        "short_segment_distribution": {"total": len(segment_lengths), "counts_below_mm": short},
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
    }
