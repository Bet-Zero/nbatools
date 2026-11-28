"""Two immutable releases share physical bytes and restore complete logical copies."""

import hashlib
import json

import pytest

from nbatools.commands.pipeline import generation_publication as pub
from nbatools.commands.pipeline.generation_refresh import (
    download_active_generation,
    prune_r2_generations,
)
from nbatools.data_source import (
    data_generation_context,
    data_glob,
    data_path,
    reset_data_source_cache,
)
from nbatools.generation_manifest import parse_generation_files
from tests.test_data_source import FakeR2Client as ReaderClient
from tests.test_data_source import _configure_r2
from tests.test_generation_publication import FakeR2Client, _write_valid_source
from tests.test_generation_refresh import FakeR2Client as PruneClient
from tools.cloud_backup import export_backup, restore_backup
from tools.plan_generation_reuse import plan

pytestmark = pytest.mark.engine
POINTER = "metadata/active_generation.json"
MANIFEST = "metadata/generation_manifest.json"
STABLE = "raw/unchanged.csv"
CHANGED = "raw/sample.csv"
ADDED = "raw/first-release.csv"


def _read_candidate(client, generation):
    return json.loads(client.objects[f"generations/{generation}/{MANIFEST}"])


def _source(root, version):
    _write_valid_source(root, version)
    (root / STABLE).write_text("value\noriginal\n")
    if version != "original":
        (root / ADDED).write_text("value\nfirst-addition\n")


def _plan(tmp_path, client, source, base, generation):
    base_raw = client.objects[f"generations/{base}/{MANIFEST}"]
    base_path = tmp_path / f"{base}.json"
    base_path.write_bytes(base_raw)
    local_root = tmp_path / f"local-{generation}"
    complete = pub.publish_local_generation(generation, source_dir=source, data_root=local_root)
    raw, receipt = plan(
        base_path,
        hashlib.sha256(base_raw).hexdigest(),
        local_root / "generations" / generation / MANIFEST,
        complete.manifest_sha256,
    )
    options = {
        "expected_base": base,
        "expected_base_manifest_sha256": receipt["base_manifest_sha256"],
        "expected_manifest_sha256": receipt["reuse_manifest_sha256"],
        "client": client,
        "bucket_name": "isolated",
    }
    return raw, receipt, options


def test_two_reused_releases_and_previous_standalone_reader(tmp_path, monkeypatch):
    source = tmp_path / "source"
    client = FakeR2Client()
    _source(source, "original")
    pub.publish_r2_generation("base", source_dir=source, client=client, bucket_name="isolated")
    original_pointer = client.objects[POINTER]
    pointers = {"base": original_pointer}

    for base, generation in (("base", "first"), ("first", "second")):
        _source(source, generation)
        raw, receipt, options = _plan(tmp_path, client, source, base, generation)
        before = dict(client.objects)
        client.put_order.clear()
        pub.upload_r2_candidate(generation, source_dir=source, reuse_unchanged=True, **options)
        assert client.objects[POINTER] == before[POINTER]
        assert all(client.objects[key] == value for key, value in before.items())
        assert len(client.put_order) == receipt["planned_candidate_puts"]
        assert (
            sum(len(client.objects[key]) for key in client.put_order)
            == receipt["planned_candidate_write_bytes"]
        )
        assert f"generations/{generation}/{STABLE}" not in client.objects
        assert client.objects[f"generations/{generation}/{MANIFEST}"] == raw
        manifest = _read_candidate(client, generation)
        entries = parse_generation_files(manifest, generation)
        assert entries[STABLE].storage_generation == "base"
        assert entries[CHANGED].storage_generation is None
        assert entries[ADDED].storage_generation == (None if generation == "first" else "first")
        assert (
            client.objects[f"generations/{generation}/{CHANGED}"]
            == f"value\n{generation}\n".encode()
        )

        client.put_order.clear()
        pub.activate_r2_candidate(generation, **options)
        assert client.put_order == [POINTER]
        pointers[generation] = client.objects[POINTER]
        folder = tmp_path / f"backup-{generation}"
        saved = export_backup(folder, generation, client=client, bucket="isolated")
        target = tmp_path / f"restored-{generation}"
        restored = restore_backup(folder / "generation.zip", saved, target)
        assert restored["manifest_sha256"] == receipt["reuse_manifest_sha256"]
        assert {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()} == {
            MANIFEST,
            *entries,
        }
        for relative, entry in entries.items():
            assert (target / relative).read_bytes() == client.objects[
                entry.object_key(generation, relative)
            ]
        fetched = tmp_path / f"refresh-{generation}"
        download_active_generation(fetched, client=client, bucket_name="isolated")
        assert (fetched / STABLE).read_bytes() == (target / STABLE).read_bytes()

    objects = dict(client.objects)
    reader = ReaderClient(objects)
    reset_data_source_cache()
    try:
        _configure_r2(monkeypatch, tmp_path, reader)
        for generation, pointer in pointers.items():
            objects[POINTER] = pointer
            with data_generation_context():
                assert data_path(STABLE).read_text() == "value\noriginal\n"
                assert (
                    data_path(CHANGED).read_text()
                    == f"value\n{generation if generation != 'base' else 'original'}\n"
                )
                assert STABLE.removeprefix("raw/") in {p.name for p in data_glob("raw/*.csv")}
        assert f"generations/base/{STABLE}" in reader.get_calls
        assert f"generations/second/{STABLE}" not in reader.get_calls
    finally:
        reset_data_source_cache()

    client.put_order.clear()
    assert (
        pub.rollback_r2_generation(client=client, bucket_name="isolated").generation_id == "first"
    )
    assert client.put_order == [POINTER]
    prune = PruneClient()
    for key, value in client.objects.items():
        prune.put(key, value)
    with pytest.raises(pub.GenerationPublicationError, match="reachability and retention"):
        prune_r2_generations(keep=2, client=prune, bucket_name="isolated")
    assert not prune.deleted


def test_corrupt_shared_bytes_fail_before_any_candidate_write(tmp_path):
    source = tmp_path / "source"
    client = FakeR2Client()
    _source(source, "original")
    pub.publish_r2_generation("base", source_dir=source, client=client, bucket_name="isolated")
    _source(source, "first")
    _, _, options = _plan(tmp_path, client, source, "base", "first")
    client.objects[f"generations/base/{STABLE}"] = b"value\nnot-base\n"
    client.put_order.clear()
    with pytest.raises(pub.GenerationValidationError, match="object checksum"):
        pub.upload_r2_candidate("first", source_dir=source, reuse_unchanged=True, **options)
    assert not client.put_order


@pytest.mark.parametrize("origin", ["../outside", "a/b", "legacy", "new", None])
def test_manifest_rejects_unsafe_origins(origin):
    record = dict(path=STABLE, size_bytes=3, sha256="a" * 64, storage_generation=origin)
    with pytest.raises(ValueError, match="storage generation"):
        parse_generation_files(dict(schema_version=2, generation_id="new", files=[record]), "new")
