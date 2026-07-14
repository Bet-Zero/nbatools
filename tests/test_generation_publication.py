from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from nbatools import data_source
from nbatools.commands.pipeline import generation_publication as publication
from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GenerationConflictError,
    GenerationPublicationError,
    GenerationValidationError,
    publish_local_generation,
    publish_r2_generation,
    rollback_local_generation,
    rollback_r2_generation,
)
from nbatools.data_source import ACTIVE_GENERATION_PATH, LOCAL_DATA_ROOT_ENV

pytestmark = pytest.mark.engine


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeClientError(Exception):
    def __init__(self, code: str, message: str, status: int):
        self.response = {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__(message)


class FakeR2Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}
        self.put_order: list[str] = []
        self.fail_put_keys: set[str] = set()
        self.pointer_conflict_payload: bytes | None = None
        self.put_race_objects: dict[str, tuple[bytes, dict[str, str]]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise FakeClientError("404", "not found", 404)
        payload = self.objects[Key]
        return {
            "ContentLength": len(payload),
            "Metadata": self.metadata.get(Key, {}),
            "ETag": f'"{_etag(payload)}"',
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        response = self.head_object(Bucket=Bucket, Key=Key)
        return {**response, "Body": FakeBody(self.objects[Key])}

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        key = kwargs["Key"]
        if key in self.fail_put_keys:
            raise FakeClientError("500", "injected upload failure", 500)
        if key == ACTIVE_GENERATION_PATH.as_posix() and self.pointer_conflict_payload is not None:
            self.objects[key] = self.pointer_conflict_payload
            self.metadata[key] = {}
            self.pointer_conflict_payload = None
        raced = self.put_race_objects.pop(key, None)
        if raced is not None:
            self.objects[key], self.metadata[key] = raced

        existing = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and existing is not None:
            raise FakeClientError("PreconditionFailed", "pointer already exists", 412)
        if "IfMatch" in kwargs:
            if existing is None or kwargs["IfMatch"] != f'"{_etag(existing)}"':
                raise FakeClientError("PreconditionFailed", "pointer changed", 412)

        body = kwargs["Body"]
        payload = body.read() if hasattr(body, "read") else bytes(body)
        assert kwargs["ContentLength"] == len(payload)
        self.objects[key] = payload
        self.metadata[key] = dict(kwargs.get("Metadata") or {})
        self.put_order.append(key)
        return {"ETag": f'"{_etag(payload)}"'}


def test_local_publication_validates_snapshot_and_atomically_switches_pointer(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")

    result = publish_local_generation(
        "local-one",
        source_dir=data_dir,
        data_root=data_dir,
    )

    pointer = _read_json(data_dir / ACTIVE_GENERATION_PATH)
    generation_dir = data_dir / "generations" / "local-one"
    manifest = _read_json(generation_dir / GENERATION_MANIFEST_PATH)
    assert result.generation_id == "local-one"
    assert result.previous_generation_id == "legacy"
    assert pointer["generation_id"] == "local-one"
    assert pointer["previous_generation_id"] == "legacy"
    assert pointer["manifest_sha256"] == _sha256(generation_dir / GENERATION_MANIFEST_PATH)
    assert (generation_dir / "raw" / "sample.csv").read_text() == "value\none\n"
    assert {item["path"] for item in manifest["files"]} == {
        "metadata/dataset_manifests/test_regular_season.json",
        "raw/sample.csv",
    }
    assert not (generation_dir / ACTIVE_GENERATION_PATH).exists()


def test_local_validation_failure_never_creates_generation_or_pointer(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "broken")
    receipt_path = data_dir / "metadata" / "dataset_manifests" / "test_regular_season.json"
    receipt = _read_json(receipt_path)
    receipt["datasets"][0]["file_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt))

    with pytest.raises(GenerationValidationError, match="checksum mismatch"):
        publish_local_generation(
            "local-broken",
            source_dir=data_dir,
            data_root=data_dir,
        )

    assert not (data_dir / ACTIVE_GENERATION_PATH).exists()
    generations = data_dir / "generations"
    assert not (generations / "local-broken").exists()
    assert not list(generations.glob(".staging-*"))


def test_local_pointer_failure_leaves_last_good_active_and_new_snapshot_inactive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)
    _write_valid_source(data_dir, "two")

    def fail_pointer(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise GenerationPublicationError("injected pointer failure")

    monkeypatch.setattr(publication, "_write_local_pointer_atomic", fail_pointer)

    with pytest.raises(GenerationPublicationError, match="injected pointer failure"):
        publish_local_generation("local-two", source_dir=data_dir, data_root=data_dir)

    assert _read_json(data_dir / ACTIVE_GENERATION_PATH)["generation_id"] == "local-one"
    assert (data_dir / "generations" / "local-two" / "raw" / "sample.csv").is_file()

    monkeypatch.undo()
    retried = publish_local_generation("local-two", source_dir=data_dir, data_root=data_dir)
    assert retried.generation_id == "local-two"
    assert _read_json(data_dir / ACTIVE_GENERATION_PATH)["generation_id"] == "local-two"


def test_local_pointer_compare_and_swap_rejects_concurrent_publisher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)
    _write_valid_source(data_dir, "two")
    original_build = publication._build_staged_generation

    def build_then_change_pointer(source: Path, staged: Path, generation: str) -> None:
        original_build(source, staged, generation)
        (data_dir / ACTIVE_GENERATION_PATH).write_bytes(_pointer_bytes("external", "local-one"))

    monkeypatch.setattr(publication, "_build_staged_generation", build_then_change_pointer)

    with pytest.raises(GenerationConflictError, match="pointer changed"):
        publish_local_generation("local-two", source_dir=data_dir, data_root=data_dir)

    assert _read_json(data_dir / ACTIVE_GENERATION_PATH)["generation_id"] == "external"
    assert (data_dir / "generations" / "local-two" / "raw" / "sample.csv").is_file()


def test_local_reader_stays_pinned_across_publication_and_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)
    monkeypatch.setenv(LOCAL_DATA_ROOT_ENV, str(tmp_path))
    data_source.reset_data_source_cache()

    with data_source.data_generation_context() as pinned:
        assert pinned == "local-one"
        assert data_source.data_read_text("raw/sample.csv") == "value\none\n"
        _write_valid_source(data_dir, "two")
        publish_local_generation("local-two", source_dir=data_dir, data_root=data_dir)
        assert data_source.data_read_text("raw/sample.csv") == "value\none\n"

    with data_source.data_generation_context() as current:
        assert current == "local-two"
        assert data_source.data_read_text("raw/sample.csv") == "value\ntwo\n"

    result = rollback_local_generation(data_root=data_dir)
    assert result.action == "rollback"
    assert result.generation_id == "local-one"
    with data_source.data_generation_context() as rolled_back:
        assert rolled_back == "local-one"
        assert data_source.data_read_text("raw/sample.csv") == "value\none\n"


def test_local_rollback_refuses_drifted_legacy_target(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)
    (data_dir / "raw" / "sample.csv").write_text("value\ndrifted\n")

    with pytest.raises(GenerationValidationError, match="checksum mismatch"):
        rollback_local_generation(data_root=data_dir)

    assert _read_json(data_dir / ACTIVE_GENERATION_PATH)["generation_id"] == "local-one"


def test_existing_generation_id_rejects_different_immutable_content(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)
    _write_valid_source(data_dir, "different")

    with pytest.raises(GenerationConflictError, match="different content"):
        publish_local_generation("local-one", source_dir=data_dir, data_root=data_dir)

    assert _read_json(data_dir / ACTIVE_GENERATION_PATH)["generation_id"] == "local-one"


def test_r2_publication_uploads_immutable_prefix_before_pointer(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    client = FakeR2Client()

    result = publish_r2_generation(
        "remote-one",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )

    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    pointer = json.loads(client.objects[pointer_key])
    assert result.previous_generation_id == "legacy"
    assert pointer["generation_id"] == "remote-one"
    assert pointer["previous_generation_id"] == "legacy"
    assert client.put_order[-1] == pointer_key
    assert set(client.objects) == {
        "generations/remote-one/metadata/dataset_manifests/test_regular_season.json",
        "generations/remote-one/metadata/generation_manifest.json",
        "generations/remote-one/raw/sample.csv",
        pointer_key,
    }


def test_r2_partial_upload_failure_keeps_pointer_and_retry_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "two")
    client = FakeR2Client()
    failing_key = "generations/remote-two/raw/sample.csv"
    client.fail_put_keys.add(failing_key)
    publication_times = iter(
        [
            "2026-07-14T10:00:00+00:00",
            "2026-07-14T10:01:00+00:00",
            "2026-07-14T10:02:00+00:00",
        ]
    )
    monkeypatch.setattr(publication, "_utc_now", lambda: next(publication_times))

    with pytest.raises(GenerationPublicationError, match="injected upload failure"):
        publish_r2_generation(
            "remote-two",
            source_dir=data_dir,
            client=client,
            bucket_name="test-bucket",
        )

    assert ACTIVE_GENERATION_PATH.as_posix() not in client.objects
    assert any(key.startswith("generations/remote-two/") for key in client.objects)

    client.fail_put_keys.clear()
    result = publish_r2_generation(
        "remote-two",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )
    assert result.generation_id == "remote-two"
    assert json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])["generation_id"] == (
        "remote-two"
    )


def test_r2_pointer_compare_and_swap_rejects_concurrent_publisher(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    client = FakeR2Client()
    publish_r2_generation(
        "remote-one",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )
    _write_valid_source(data_dir, "two")
    client.pointer_conflict_payload = _pointer_bytes("external", "remote-one")

    with pytest.raises(GenerationConflictError, match="pointer changed"):
        publish_r2_generation(
            "remote-two",
            source_dir=data_dir,
            client=client,
            bucket_name="test-bucket",
        )

    pointer = json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])
    assert pointer["generation_id"] == "external"
    assert "generations/remote-two/raw/sample.csv" in client.objects


def test_r2_immutable_object_conditional_write_rejects_racing_content(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    client = FakeR2Client()
    key = "generations/remote-race/raw/sample.csv"
    client.put_race_objects[key] = (
        b"different\n",
        {publication.SHA256_METADATA_KEY: hashlib.sha256(b"different\n").hexdigest()},
    )

    with pytest.raises(GenerationConflictError, match="conflicting write"):
        publish_r2_generation(
            "remote-race",
            source_dir=data_dir,
            client=client,
            bucket_name="test-bucket",
        )

    assert ACTIVE_GENERATION_PATH.as_posix() not in client.objects
    assert client.objects[key] == b"different\n"


def test_r2_rollback_reactivates_retained_previous_generation(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    client = FakeR2Client()
    _write_valid_source(data_dir, "one")
    publish_r2_generation(
        "remote-one",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )
    _write_valid_source(data_dir, "two")
    publish_r2_generation(
        "remote-two",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )

    result = rollback_r2_generation(client=client, bucket_name="test-bucket")

    pointer = json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])
    assert result.action == "rollback"
    assert result.generation_id == "remote-one"
    assert pointer["generation_id"] == "remote-one"
    assert pointer["previous_generation_id"] == "remote-two"
    assert "generations/remote-two/raw/sample.csv" in client.objects


def test_r2_rollback_refuses_unmanifested_legacy_target(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    client = FakeR2Client()
    _write_valid_source(data_dir, "one")
    publish_r2_generation(
        "remote-one",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )

    with pytest.raises(GenerationValidationError, match="bootstrap"):
        rollback_r2_generation(client=client, bucket_name="test-bucket")

    assert json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])["generation_id"] == (
        "remote-one"
    )


def test_r2_rollback_refuses_incomplete_retained_generation(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    client = FakeR2Client()
    _write_valid_source(data_dir, "one")
    publish_r2_generation(
        "remote-one",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )
    _write_valid_source(data_dir, "two")
    publish_r2_generation(
        "remote-two",
        source_dir=data_dir,
        client=client,
        bucket_name="test-bucket",
    )
    client.objects.pop("generations/remote-one/raw/sample.csv")
    client.metadata.pop("generations/remote-one/raw/sample.csv")

    with pytest.raises(GenerationValidationError, match="failed verification"):
        rollback_r2_generation(client=client, bucket_name="test-bucket")

    assert json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])["generation_id"] == (
        "remote-two"
    )


def test_pipeline_publish_and_rollback_local_generation_cli(tmp_path: Path) -> None:
    from nbatools.cli_apps.pipeline import app

    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    runner = CliRunner()

    published = runner.invoke(
        app,
        [
            "publish-generation",
            "--generation-id",
            "cli-one",
            "--data-dir",
            str(data_dir),
            "--target",
            "local",
        ],
    )
    rolled_back = runner.invoke(
        app,
        ["rollback-generation", "--data-dir", str(data_dir), "--target", "local"],
    )

    assert published.exit_code == 0
    assert "Generation publish: cli-one" in published.output
    assert rolled_back.exit_code == 0
    assert "Generation rollback: legacy" in rolled_back.output


def test_pipeline_r2_publication_reports_missing_credentials_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nbatools.cli_apps.pipeline import app

    data_dir = tmp_path / "data"
    _write_valid_source(data_dir, "one")
    monkeypatch.chdir(tmp_path)
    for key in (
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
    ):
        monkeypatch.delenv(key, raising=False)

    result = CliRunner().invoke(
        app,
        [
            "publish-generation",
            "--generation-id",
            "cli-r2",
            "--data-dir",
            str(data_dir),
            "--target",
            "r2",
        ],
    )

    assert result.exit_code == 1
    assert "Generation publication failed: Missing R2 environment variables" in result.output
    assert "Traceback" not in result.output


def _write_valid_source(data_dir: Path, value: str) -> None:
    data_path = data_dir / "raw" / "sample.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(f"value\n{value}\n")
    receipt = {
        "schema_version": 1,
        "season": "test",
        "season_type": "Regular Season",
        "generation_id": f"receipt-{value}",
        "generated_at": "2026-07-14T00:00:00",
        "validation_state": "passed",
        "validation_errors": [],
        "datasets": [
            {
                "name": "sample",
                "path": "data/raw/sample.csv",
                "required": True,
                "generation_id": f"receipt-{value}",
                "file_sha256": _sha256(data_path),
                "validation": {"state": "passed", "errors": []},
            }
        ],
    }
    receipt_path = data_dir / "metadata" / "dataset_manifests" / "test_regular_season.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def _pointer_bytes(generation: str, previous: str) -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "generation_id": generation,
            "previous_generation_id": previous,
            "manifest_sha256": None,
            "published_at": "2026-07-14T00:00:00+00:00",
        }
    ).encode()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _etag(payload: bytes) -> str:
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()
