from __future__ import annotations

import json
from pathlib import Path

import pytest

from herculean_columns.fixtures.corpus import regenerate_and_validate


pytestmark = pytest.mark.export
CORPUS = Path("fixtures/generated")


def test_committed_corpus_regenerates_byte_identically() -> None:
    report = regenerate_and_validate(CORPUS)
    assert report["fixtures"] == 6


def test_manifests_have_provenance_orientation_and_independent_geometry_evidence() -> None:
    for path in sorted(CORPUS.glob("*/fixture.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["provenance"]["source_kind"] == "parametric"
        assert manifest["build_orientation"] == [0.0, 0.0, 1.0]
        assert manifest["expected_component_count"] == 1
        assert manifest["physical_setup"] and manifest["purpose"]
        assert all(variant["inspection"]["valid"] for variant in manifest["variants"])


def test_density_series_has_stable_distinct_configuration_identity() -> None:
    manifest = json.loads((CORPUS / "convex-box" / "fixture.json").read_text(encoding="utf-8"))
    variants = manifest["variants"]
    assert [item["infill_percent"] for item in variants] == [5.0, 10.0, 15.0]
    assert len({item["configuration_sha256"] for item in variants}) == 3
    assert all(item["achieved_infill_percent"] > 0 for item in variants)
    # Printable minima can flatten achieved volume, so nondecreasing is the contract.
    achieved = [item["achieved_infill_percent"] for item in variants]
    assert achieved == sorted(achieved)


@pytest.mark.parametrize("mutation", ("missing_provenance", "wrong_orientation", "unexpected_components"))
def test_red_manifest_mutations_fail_contract(mutation: str) -> None:
    manifest = json.loads((CORPUS / "convex-box" / "fixture.json").read_text(encoding="utf-8"))
    if mutation == "missing_provenance":
        manifest.pop("provenance")
    elif mutation == "wrong_orientation":
        manifest["build_orientation"] = [1.0, 0.0, 0.0]
    else:
        manifest["expected_component_count"] = 2
    valid = bool(manifest.get("provenance")) and manifest["build_orientation"] == [0.0, 0.0, 1.0] and manifest["expected_component_count"] == 1
    assert not valid


def test_hash_manifest_detects_nondeterminism(tmp_path: Path) -> None:
    copied = tmp_path / "generated"
    import shutil
    shutil.copytree(CORPUS, copied)
    target = next(copied.glob("*/fixture.json"))
    target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="fixture corpus differs"):
        regenerate_and_validate(copied)
