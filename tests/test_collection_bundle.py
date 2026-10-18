import json
import zipfile

import pytest

from tools.collection_bundle import create, unpack


@pytest.fixture
def collection_requirement():
    return {
        "status": "collection_requirement_not_publication_approval",
        "base_generation": "current",
        "base_manifest_sha256": "a" * 64,
        "dataset": "raw/player_game_stats",
        "requested_nba_game_ids": ["0022500001"],
    }


def make_bundle(tmp_path, collection_requirement):
    root = tmp_path / "collection"
    (root / "sources").mkdir(parents=True)
    (root / "sources/game.json").write_text('{"gameId":"0022500001"}')
    (root / "acquisition.json").write_text(
        json.dumps(
            {
                "source": "NBA Stats",
                "captured_at": "2026-10-18T00:00:00Z",
                "parameters": {"GameID": "0022500001"},
            }
        )
    )
    output = tmp_path / "handoff.zip"
    result = create(root, collection_requirement, output)
    return output, result


def test_data_only_laptop_bundle_recovers_in_cloud_without_development(
    tmp_path, collection_requirement
):
    source, receipt = make_bundle(tmp_path, collection_requirement)
    destination = tmp_path / "cloud"
    result = unpack(source, collection_requirement, destination)
    assert result["sha256"] == receipt["sha256"]
    assert result["state"] == "unvalidated_staging_only"
    assert result["production_writes"] == 0
    assert (destination / "sources/game.json").is_file()


def test_changed_request_is_rejected_before_writes(tmp_path, collection_requirement):
    source, _ = make_bundle(tmp_path, collection_requirement)
    with pytest.raises(ValueError, match="original cloud request"):
        unpack(source, collection_requirement | {"base_generation": "other"}, tmp_path / "cloud")
    assert not (tmp_path / "cloud").exists()


@pytest.mark.parametrize(
    "member",
    ["../escape.json", "/absolute.json", "data/raw/.env", "sources/run.py", "sources\\evil.json"],
)
def test_unsafe_members_rejected_before_writes(tmp_path, collection_requirement, member):
    source, _ = make_bundle(tmp_path, collection_requirement)
    with zipfile.ZipFile(source) as original:
        contents = {name: original.read(name) for name in original.namelist()}
    manifest = json.loads(contents["collection-manifest.json"])
    import hashlib

    manifest["files"][member] = {"bytes": 2, "sha256": hashlib.sha256(b"{}").hexdigest()}
    contents[member] = b"{}"
    contents["collection-manifest.json"] = json.dumps(manifest).encode()
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    with pytest.raises(ValueError):
        unpack(evil, collection_requirement, tmp_path / "cloud")
    assert not (tmp_path / "cloud").exists()


def test_existing_data_never_overwritten(tmp_path, collection_requirement):
    source, _ = make_bundle(tmp_path, collection_requirement)
    target = tmp_path / "accepted"
    target.mkdir()
    marker = target / "keep.txt"
    marker.write_text("keep")
    with pytest.raises(ValueError):
        unpack(source, collection_requirement, target)
    assert marker.read_text() == "keep"


def test_modified_bytes_rejected(tmp_path, collection_requirement):
    source, _ = make_bundle(tmp_path, collection_requirement)
    with zipfile.ZipFile(source) as original:
        contents = {name: original.read(name) for name in original.namelist()}
    contents["sources/game.json"] = b"corruption"
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    with pytest.raises(ValueError):
        unpack(bad, collection_requirement, tmp_path / "cloud")
    assert not (tmp_path / "cloud").exists()
