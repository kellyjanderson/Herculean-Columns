from __future__ import annotations

from pathlib import Path

import numpy as np

from ..export.readback import readback_stl


def inspect_pair(source: Path, output: Path, tolerance_mm: float) -> dict[str, object]:
    source_result = readback_stl(str(source))
    output_result = readback_stl(str(output))
    deviation = float(np.max(np.abs(np.asarray(source_result.bounds_mm) - np.asarray(output_result.bounds_mm))))
    return {
        "source": source_result.model_dump(mode="json"),
        "output": output_result.model_dump(mode="json"),
        "exterior_bounds_deviation_mm": deviation,
        "exterior_equivalent": deviation <= tolerance_mm,
        "valid": output_result.watertight and output_result.winding_consistent and output_result.component_count == 1 and deviation <= tolerance_mm,
    }
