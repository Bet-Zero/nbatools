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
from tools.cloud_backup import export_backup, restore_backup


class ReadOnlyStore:
    def __init__(self, files):
        self.files = files

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.files[Key])}


def make_backup(tmp_path):
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
    output = tmp_path / "backup"
    receipt = export_backup(output, "backup-test", client=ReadOnlyStore(files), bucket="fixture")
    return output, receipt, files


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
