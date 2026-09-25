from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class CompatibilityEvidenceError(ValueError):
    """Raised when manual Creality compatibility evidence is absent or unsafe."""


@dataclass(frozen=True)
class CrealityImportReceipt:
    model_sha256: str
    bundle_version: str
    engine_version: str
    observer: str
    observed_at: str
    import_succeeded: bool
    preview_succeeded: bool


def model_sha256(model: Path) -> str:
    return hashlib.sha256(model.read_bytes()).hexdigest()


def validate_creality_import_receipt(receipt_path: Path, model: Path) -> CrealityImportReceipt:
    """Validate human-observed GUI evidence without driving or trusting GUI state."""
    try:
        raw = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompatibilityEvidenceError("Creality import receipt is missing or invalid JSON") from exc
    if raw.get("schema_version") != 1:
        raise CompatibilityEvidenceError("Creality import receipt must use schema_version 1")
    expected_hash = model_sha256(model)
    if raw.get("model_sha256") != expected_hash:
        raise CompatibilityEvidenceError("Creality import receipt does not identify the exact model")
    required_text = ("bundle_version", "engine_version", "observer", "observed_at")
    if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required_text):
        raise CompatibilityEvidenceError("Creality import receipt is missing identity or observer fields")
    if raw.get("import_succeeded") is not True or raw.get("preview_succeeded") is not True:
        raise CompatibilityEvidenceError("Creality import and preview must both be human-confirmed")
    return CrealityImportReceipt(
        model_sha256=expected_hash,
        bundle_version=raw["bundle_version"],
        engine_version=raw["engine_version"],
        observer=raw["observer"],
        observed_at=raw["observed_at"],
        import_succeeded=True,
        preview_succeeded=True,
    )
