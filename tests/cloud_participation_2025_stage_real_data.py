"""Rebase the accepted 2025-26 LAL/BOS participation stage onto the live base.

No NBA collection and no publication. The three remaining accepted packages
(LAL and BOS 2025-26 participation, reported-rest reasons) were qualified on
``availability-lebron-season-v1-20261031``. The live generation is that base
plus exactly the published ``historical-participation-v1`` overlay. This test
proves that, proves the remaining packages read and write none of the paths that
publication changed, composes them on their reviewed base with every original
check, and then rebuilds and accepts the same stage on real live-base bytes.
"""

import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.cloud_composed_participation_stage_real_data import (
    BASE as OLD,
)
from tests.cloud_composed_participation_stage_real_data import (
    MANIFEST as OLD_MANIFEST,
)
from tests.cloud_composed_participation_stage_real_data import (
    PACKAGES,
    _baseline,
    _documents,
    _sha,
    verify_composed_root,
)
from tests.cloud_core1_k08_lal_default_real_data import (
    accepted_inputs,
    verify_original_defaults,
)
from tools.availability_overlay import verify_append
from tools.compose_participation_overlays import compose_overlays

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
NEW = "availability-historical-participation-v1-20261114"
NEW_MANIFEST = "be0940172453b76cd81f636d3f27c8bd3e0f428dcb35be5c1b01c4aa6af74a58"
NEW_FILES = 852
PUBLISHED = PACKAGES[2]  # k08-direct-dependencies, live as historical-participation-v1
REMAINING = [PACKAGES[0], PACKAGES[1], PACKAGES[3]]
OVERLAY_FILES = 328


def _pin(monkeypatch, generation):
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", generation)
    reset_data_source_cache()
    clear_frame_cache()


def _published_overlay():
    path, digest = PUBLISHED
    assert _sha(path.read_bytes()) == digest
    with ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith("/validation.json"))
        return {item["path"]: item for item in json.loads(archive.read(name))["overlay_files"]}


def _key(entry):
    return entry["sha256"], entry["size_bytes"]


def test_rebase_2025_participation_onto_live_historical_base(tmp_path, monkeypatch):
    transport = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    assert not transport.exists() or not any(transport.iterdir())
    diagnostics = transport.parent / "participation-2025-stage"
    assert not diagnostics.exists()
    diagnostics.mkdir(parents=True)
    candidate = os.environ["VALIDATION_SHA"]
    docs, oracles, records = _documents()
    remaining_docs = [docs[0], docs[1], docs[3]]

    # 1. Compose the three remaining packages on their own reviewed base.
    _pin(monkeypatch, OLD)
    old_root = tmp_path / "old/data"
    old_root.mkdir(parents=True)
    old_manifest, _ = _baseline(old_root, docs)
    old_overlay = tmp_path / "old-overlay"
    composed = compose_overlays(
        REMAINING,
        old_root,
        old_overlay,
        base_generation=OLD,
        base_manifest_sha256=OLD_MANIFEST,
        candidate_sha=candidate,
    )
    assert len(composed["overlay_files"]) == OVERLAY_FILES

    # 2. The live base is exactly the reviewed base plus the published package.
    _pin(monkeypatch, NEW)
    with data_generation_context() as generation:
        assert generation == NEW
        new_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
    assert _sha(new_raw) == NEW_MANIFEST
    new_manifest = json.loads(new_raw)
    assert new_manifest["generation_id"] == NEW and len(new_manifest["files"]) == NEW_FILES
    old_entries = {row["path"]: row for row in old_manifest["files"]}
    new_entries = {row["path"]: row for row in new_manifest["files"]}
    assert len(old_entries) == len(old_manifest["files"])
    assert len(new_entries) == len(new_manifest["files"])
    assert old_entries.keys() <= new_entries.keys()
    published = _published_overlay()
    changed = {
        path
        for path, entry in new_entries.items()
        if path not in old_entries or _key(old_entries[path]) != _key(entry)
    }
    assert changed == set(published)
    for path in changed:
        assert _key(new_entries[path]) == _key(published[path])

    # 3. Nothing the remaining stage reads or writes was touched by that package.
    touched = {item["path"] for item in composed["overlay_files"]}
    touched |= set(composed["base_file_hashes"])
    for doc in remaining_docs:
        for bound in [doc, *doc.get("season_stage_validations", [])]:
            touched |= set(bound.get("base_file_hashes", {}))
        touched |= {item["path"] for item in doc["overlay_files"]}
    assert not touched & changed
    for path, digest in composed["base_file_hashes"].items():
        assert new_entries[path]["sha256"] == old_entries[path]["sha256"] == digest

    # 4. Rebuild the dependency root from real live-base bytes. It includes the
    # published 2023-24/2024-25 tables the original composition carried itself.
    root = tmp_path / "stage/data"
    root.mkdir(parents=True)
    required = set(composed["base_file_hashes"])
    for doc in docs:
        for bound in [doc, *doc.get("season_stage_validations", [])]:
            required |= set(bound.get("base_file_hashes", {}))
        required |= {item["path"] for item in doc["overlay_files"]}
    required &= new_entries.keys()
    with data_generation_context() as generation:
        assert generation == NEW
        for path in sorted(required):
            body = data_path("data/" + path).read_bytes()
            assert (_sha(body), len(body)) == _key(new_entries[path])
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / "metadata/generation_manifest.json").write_bytes(new_raw)
    before = {path: (root / path).read_bytes() for path in required}

    # 5. Apply the stage; every changed table is an exact append on live bytes
    # or a creation of a path the live base does not have.
    for path, bound in composed["append_only"].items():
        assert bound["base_sha256"] == new_entries[path]["sha256"]
        assert bound["base_size_bytes"] == new_entries[path]["size_bytes"]
        verify_append(path, before[path], (old_overlay / path).read_bytes(), bound)
    for path in composed["manifest_absent_creations"]:
        assert path not in new_entries
    output = tmp_path / "overlay"
    for item in composed["overlay_files"]:
        path = item["path"]
        assert path.startswith("raw/")
        assert path not in new_entries or path in composed["append_only"]
        body = (old_overlay / path).read_bytes()
        assert (_sha(body), len(body)) == _key(item)
        for target in (output / path, root / path):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    validation = dict(
        composed,
        candidate_sha=candidate,
        base_generation=NEW,
        base_manifest_sha256=NEW_MANIFEST,
        base_file_hashes={
            p: new_entries[p]["sha256"] for p in sorted(composed["base_file_hashes"])
        },
        rebased_from=dict(
            base_generation=OLD,
            base_manifest_sha256=OLD_MANIFEST,
            published_package="historical-participation-v1",
            published_overlay_paths=sorted(changed),
            stage_paths_disjoint_from_published=True,
        ),
    )
    (output / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    shutil.copytree(output, diagnostics / "overlay")

    # 6. The full original consumer acceptance, then the original IDs 16/18/35.
    changed_stage = {item["path"] for item in validation["overlay_files"]}
    verify_composed_root(
        root, diagnostics, validation, oracles, records, before, changed_stage, monkeypatch
    )
    _, _, coverage = accepted_inputs()
    receipt = dict(
        candidate_sha=candidate,
        base_generation=NEW,
        base_manifest_sha256=NEW_MANIFEST,
        classification="original16_18_35_exact_default_channels_on_rebased_stage",
        answers=[],
        accepted_original_ids=[],
        consumer_acceptance="pending",
        nba_source_requests=0,
        production_writes=0,
    )
    defaults = diagnostics / "core1-k08-lal-default"
    defaults.mkdir()

    def persist():
        (defaults / "acceptance.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")

    verify_original_defaults(root, coverage, validation, receipt, persist, monkeypatch)
    assert receipt["accepted_original_ids"] == [16, 18, 35]

    # 7. Only after every consumer passes, export the exact publisher transport.
    for item in validation["overlay_files"]:
        target = transport / item["path"]
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (output / item["path"]).read_bytes()
        assert _sha(raw) == item["sha256"]
        target.write_bytes(raw)
    (transport / "validation.json").write_bytes((output / "validation.json").read_bytes())
