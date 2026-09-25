from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..slicers import BackendIdentity, CrealityPrintBackend, SliceFailure


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


def validate_creality_import_receipt(
    receipt_path: Path,
    model: Path,
    expected_identity: BackendIdentity | None = None,
) -> CrealityImportReceipt:
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
    try:
        datetime.fromisoformat(raw["observed_at"])
    except ValueError as exc:
        raise CompatibilityEvidenceError("Creality import receipt has an invalid observation time") from exc
    if raw.get("import_succeeded") is not True or raw.get("preview_succeeded") is not True:
        raise CompatibilityEvidenceError("Creality import and preview must both be human-confirmed")
    if expected_identity is not None and (
        raw["bundle_version"] != expected_identity.bundle_version
        or raw["engine_version"] != expected_identity.engine_version
    ):
        raise CompatibilityEvidenceError("Creality import receipt identity does not match the installed application")
    return CrealityImportReceipt(
        model_sha256=expected_hash,
        bundle_version=raw["bundle_version"],
        engine_version=raw["engine_version"],
        observer=raw["observer"],
        observed_at=raw["observed_at"],
        import_succeeded=True,
        preview_succeeded=True,
    )


def create_creality_import_receipt(
    model: Path,
    destination: Path,
    identity: BackendIdentity,
    *,
    prompt: Callable[[str], str] = input,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> CrealityImportReceipt:
    """Guide a person through evidence capture without launching or driving the GUI."""
    if identity.backend != "creality-print" or not identity.bundle_version:
        raise CompatibilityEvidenceError("Receipt creation requires a discovered Creality Print identity")
    if destination.exists():
        raise CompatibilityEvidenceError("Refusing to overwrite an existing Creality import receipt")
    digest = model_sha256(model)
    token = digest[:12]
    observer = prompt("Observer name: ").strip()
    if not observer:
        raise CompatibilityEvidenceError("Observer name is required")
    imported = prompt(
        f"Manually import {model.resolve()} (SHA-256 {digest}) in Creality Print, then type IMPORT {token}: "
    ).strip()
    if imported != f"IMPORT {token}":
        raise CompatibilityEvidenceError("Exact-model import was not human-confirmed")
    previewed = prompt(
        f"Manually enter Preview for that model, then type PREVIEW {token}: "
    ).strip()
    if previewed != f"PREVIEW {token}":
        raise CompatibilityEvidenceError("Preview was not human-confirmed")
    observed_at = now().astimezone(timezone.utc).isoformat()
    raw = {
        "schema_version": 1,
        "model_sha256": digest,
        "bundle_version": identity.bundle_version,
        "engine_version": identity.engine_version,
        "observer": observer,
        "observed_at": observed_at,
        "import_succeeded": True,
        "preview_succeeded": True,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(raw, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise CompatibilityEvidenceError("Refusing to overwrite an existing Creality import receipt") from exc
    return validate_creality_import_receipt(destination, model)


def receipt_main() -> int:
    """Interactive entry point; intentionally never opens Creality Print."""
    import argparse

    parser = argparse.ArgumentParser(description="Capture a human-observed Creality import/Preview receipt")
    parser.add_argument("model", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument(
        "--creality-executable",
        type=Path,
        default=Path("/Applications/Creality Print.app/Contents/MacOS/CrealityPrint"),
    )
    args = parser.parse_args()
    try:
        identity = CrealityPrintBackend(args.creality_executable).discover_identity()
        receipt = create_creality_import_receipt(args.model, args.receipt, identity)
    except (CompatibilityEvidenceError, SliceFailure) as exc:
        parser.exit(2, f"receipt not created: {exc}\n")
    print(f"Validated receipt for {receipt.model_sha256}: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(receipt_main())
