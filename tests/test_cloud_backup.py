"""Offline corruption/bounds checks; fixtures here are never NBA acceptance."""

import hashlib
import io
import json
import zipfile

import pytest

from nbatools.commands.pipeline.generation_publication import (
    GenerationValidationError,
    _build_staged_generation,
)
from tools import cloud_backup
from tools.cloud_backup import (
    candidate_backup_preflight,
    export_backup,
    export_reconciled_candidate_backup,
    restore_backup,
)


class ReadOnlyStore:
    def __init__(self, files):
        self.files = files
        self.reads = []

    def get_object(self, *, Bucket, Key):
        self.reads.append(Key)
        return {"Body": io.BytesIO(self.files[Key])}


def make_backup(tmp_path, *, register=None):
    source = tmp_path / "source"
    sample = source / "raw/sample.csv"
    sample.parent.mkdir(parents=True)
    sample.write_text("value\n42\n")
    receipt = {
        "schema_version": 1,
        "season": "test",
        "season_type": "Regular Season",
        "generation_id": "receipt-test",
        "generated_at": "2026-07-14T00:00:00",
        "validation_state": "passed",
        "validation_errors": [],
        "datasets": [
            {
                "name": "sample",
                "path": "data/raw/sample.csv",
                "required": True,
                "generation_id": "receipt-test",
                "file_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
                "validation": {"state": "passed", "errors": []},
            }
        ],
    }
    path = source / "metadata/dataset_manifests/test_regular_season.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt))
    stage = tmp_path / "stage"
    _build_staged_generation(source, stage, "backup-test")
    manifest = stage / "metadata/generation_manifest.json"
    files = {
        "generations/backup-test/" + p.relative_to(stage).as_posix(): p.read_bytes()
        for p in stage.rglob("*")
        if p.is_file()
    }
    files["metadata/active_generation.json"] = json.dumps(
        {
            "generation_id": "backup-test",
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        }
    ).encode()
    if register is not None:
        register(hashlib.sha256(manifest.read_bytes()).hexdigest())
    output = tmp_path / "backup"
    receipt = export_backup(output, "backup-test", client=ReadOnlyStore(files), bucket="fixture")
    return output, receipt, files


def test_exact_qualified_backup_and_restore_verify_bytes_without_source_replay(
    tmp_path, monkeypatch
):
    registry = tmp_path / "approved.json"
    monkeypatch.setattr(cloud_backup, "REGISTRY", registry)
    monkeypatch.setattr(
        cloud_backup,
        "validate_staged_generation",
        lambda *args: pytest.fail("Source qualification replayed for an approved manifest"),
    )

    def register(manifest_sha):
        registry.write_text(
            json.dumps(
                {
                    "packages": {
                        "fixture": {
                            "generation_id": "backup-test",
                            "operations": ["activate_candidate"],
                            "activation": {"manifest_sha256": manifest_sha},
                        }
                    },
                }
            )
        )
        assert not cloud_backup.qualified_activation_manifest("backup-test", "0" * 64)
        assert not cloud_backup.qualified_activation_manifest("another-generation", manifest_sha)

    output, receipt, _ = make_backup(tmp_path, register=register)
    assert receipt["source_qualification_reused"]
    archive = output / "generation.zip"
    restored = restore_backup(archive, receipt, tmp_path / "restore")
    assert restored["source_qualification_reused"]
    with zipfile.ZipFile(archive) as zipped:
        entries = {name: zipped.read(name) for name in zipped.namelist()}
    entries["raw/sample.csv"] = b"value\n43\n"
    with zipfile.ZipFile(archive, "w") as zipped:
        for key, value in entries.items():
            zipped.writestr(key, value)
    receipt["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    receipt["archive_bytes"] = archive.stat().st_size
    with pytest.raises(ValueError, match="differs from the qualified manifest"):
        restore_backup(archive, receipt, tmp_path / "corrupt")


def test_byte_exact_export_and_offline_restore(tmp_path):
    output, receipt, files = make_backup(tmp_path)
    target = tmp_path / "restore"
    result = restore_backup(output / "generation.zip", receipt, target)
    assert result["production_writes"] == 0
    for key, value in files.items():
        if key.startswith("generations/backup-test/"):
            assert (target / key.removeprefix("generations/backup-test/")).read_bytes() == value
    with pytest.raises(ValueError, match="must not exist"):
        restore_backup(output / "generation.zip", receipt, target)


@pytest.mark.parametrize(
    ("pointer_patch", "error"),
    [
        ({}, None),
        ({"published_at": "2026-11-28T12:00:00Z"}, "independently verified activation"),
        ({"previous_generation_id": "later"}, "independently verified activation"),
        ({"schema_version": True}, "independently verified activation"),
        ({"schema_version": 1.0}, "independently verified activation"),
    ],
)
def test_reconciled_backup_requires_the_exact_verified_pointer(tmp_path, pointer_patch, error):
    _, ordinary_receipt, files = make_backup(tmp_path)
    pointer_key = "metadata/active_generation.json"
    pointer = json.loads(files[pointer_key]) | {
        "schema_version": 1,
        "previous_generation_id": "base",
        "published_at": "2026-11-27T12:00:00Z",
    }
    verified = {
        "publication_state": "candidate_activated_historical_verified",
        "generation_id": "backup-test",
        "base_generation": "base",
        "prepared_manifest_sha256": pointer["manifest_sha256"],
        "file_count": ordinary_receipt["files"],
        "total_bytes": ordinary_receipt["data_bytes"],
        "verified_pointer": pointer,
        "reconciliation": {
            "status": "exact_candidate_active",
            "observed_pointer": pointer,
            "production_writes": 0,
        },
    }
    evidence = tmp_path / "reconciliation.json"
    evidence.write_text(json.dumps(verified))
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    store = ReadOnlyStore(files)
    files[pointer_key] = json.dumps(pointer | pointer_patch).encode()
    output = tmp_path / "reconciled-backup"
    kwargs = {"expected_receipt_sha256": digest, "client": store, "bucket": "fixture"}
    if error:
        with pytest.raises(ValueError, match=error):
            export_reconciled_candidate_backup(output, evidence, **kwargs)
        assert store.reads == [
            pointer_key,
            "generations/backup-test/metadata/generation_manifest.json",
        ]
        assert not (output / "generation.zip").exists()
        assert not (output / "backup-receipt.json").exists()
    else:
        receipt = export_reconciled_candidate_backup(output, evidence, **kwargs)
        assert receipt["verified_pointer"] == pointer
        assert receipt["reconciliation_receipt_sha256"] == digest
        assert json.loads((output / "backup-receipt.json").read_text()) == receipt
        assert receipt["r2_writes"] == 0
        restore = restore_backup(output / "generation.zip", receipt, tmp_path / "restore")
        assert restore["manifest_sha256"] == pointer["manifest_sha256"]
        assert restore["archive_sha256"] == receipt["archive_sha256"]
        assert restore["verified_pointer"] == pointer
        assert restore["reconciliation_receipt_sha256"] == digest
        tampered = receipt | {"verified_pointer": pointer | {"manifest_sha256": "0" * 64}}
        with pytest.raises(ValueError, match="pointer differs from the backup identity"):
            restore_backup(output / "generation.zip", tampered, tmp_path / "tampered-restore")
        store.reads.clear()
        evidence.write_text(json.dumps(verified | {"base_generation": "different"}))
        with pytest.raises(ValueError, match="differs from the reviewed bytes"):
            export_reconciled_candidate_backup(tmp_path / "other-backup", evidence, **kwargs)
        assert not store.reads


def test_candidate_preflight_measures_exact_zip_without_active_pointer(tmp_path, monkeypatch):
    output, receipt, files = make_backup(tmp_path)
    del files["metadata/active_generation.json"]
    generation = receipt["generation_id"]
    manifest = files[f"generations/{generation}/metadata/generation_manifest.json"]
    store = ReadOnlyStore(files)
    proof = candidate_backup_preflight(
        store, "fixture", generation, receipt["manifest_sha256"], manifest
    )
    assert proof == {
        "generation_id": generation,
        "manifest_sha256": receipt["manifest_sha256"],
        "files": receipt["files"],
        "data_bytes": receipt["data_bytes"],
        "archive_bytes": (output / "generation.zip").stat().st_size,
        "r2_writes": 0,
    }

    monkeypatch.setattr(cloud_backup, "MAX_ARCHIVE", proof["archive_bytes"] - 1)
    with pytest.raises(ValueError, match="Compressed candidate backup exceeds"):
        candidate_backup_preflight(
            store, "fixture", generation, receipt["manifest_sha256"], manifest
        )

    monkeypatch.setattr(cloud_backup, "MAX_ARCHIVE", proof["archive_bytes"])
    files[f"generations/{generation}/raw/sample.csv"] = b"value\n43\n"
    with pytest.raises(ValueError, match="backup object differs"):
        candidate_backup_preflight(
            store, "fixture", generation, receipt["manifest_sha256"], manifest
        )


@pytest.mark.parametrize(
    "defect", ["corrupt_archive", "traversal", "duplicate", "corrupt_manifest", "corrupt_data"]
)
def test_restore_fails_closed(tmp_path, defect):
    output, receipt, _ = make_backup(tmp_path)
    archive = output / "generation.zip"
    if defect == "corrupt_archive":
        archive.write_bytes(archive.read_bytes() + b"corruption")
    else:
        with zipfile.ZipFile(archive) as zipped:
            entries = {name: zipped.read(name) for name in zipped.namelist()}
        if defect == "traversal":
            entries["raw/../../outside"] = b"bad"
        elif defect == "corrupt_manifest":
            entries["metadata/generation_manifest.json"] += b" "
        elif defect == "corrupt_data":
            entries["raw/sample.csv"] = b"value\n43\n"
        with zipfile.ZipFile(archive, "w") as zipped:
            for key, value in entries.items():
                zipped.writestr(key, value)
            if defect == "duplicate":
                with pytest.warns(UserWarning):
                    zipped.writestr("raw/sample.csv", b"duplicate")
        receipt["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        receipt["archive_bytes"] = archive.stat().st_size
    with pytest.raises((ValueError, GenerationValidationError)):
        restore_backup(archive, receipt, tmp_path / "restore")
    assert not (tmp_path / "outside").exists()
