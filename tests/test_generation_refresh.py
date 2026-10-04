from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GenerationConflictError,
    GenerationPublicationError,
    GenerationValidationError,
    publish_r2_generation,
)
from nbatools.commands.pipeline.generation_refresh import (
    changed_data_files,
    download_active_generation,
    prune_r2_generations,
)
from nbatools.data_source import ACTIVE_GENERATION_PATH

pytestmark = pytest.mark.engine

BUCKET = "test-bucket"


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeClientError(Exception):
    def __init__(self, code: str, status: int):
        self.response = {
            "Error": {"Code": code, "Message": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__(code)


class FakeR2Client:
    """An in-memory bucket with the calls refresh and pruning use."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.modified: dict[str, datetime] = {}
        self.deleted: list[str] = []
        self.fail_delete_keys: set[str] = set()
        self.on_delete = None

    def put(self, key: str, payload: bytes, modified: datetime | None = None) -> None:
        self.objects[key] = payload
        self.modified[key] = modified or datetime(2026, 7, 16, tzinfo=UTC)

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise FakeClientError("404", 404)
        payload = self.objects[Key]
        return {
            "ContentLength": len(payload),
            "LastModified": self.modified[Key],
            "ETag": f'"{hashlib.md5(payload, usedforsecurity=False).hexdigest()}"',
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        return {**self.head_object(Bucket=Bucket, Key=Key), "Body": FakeBody(self.objects[Key])}

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        prefix = kwargs["Prefix"]
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        if kwargs.get("Delimiter") == "/":
            prefixes = sorted({prefix + key[len(prefix) :].split("/")[0] + "/" for key in keys})
            return {"CommonPrefixes": [{"Prefix": p} for p in prefixes], "IsTruncated": False}
        # Two keys per page, so deletion has to loop.
        return {"Contents": [{"Key": key} for key in keys[:2]], "IsTruncated": len(keys) > 2}

    def delete_objects(self, *, Bucket: str, Delete: dict[str, Any]) -> dict[str, Any]:
        errors = []
        for item in Delete["Objects"]:
            if item["Key"] in self.fail_delete_keys:
                errors.append({"Key": item["Key"], "Code": "InternalError"})
                continue
            self.objects.pop(item["Key"])
            self.deleted.append(item["Key"])
        if self.on_delete is not None:
            self.on_delete()
        return {"Errors": errors} if errors else {}


def _publish(
    client: FakeR2Client,
    generation: str,
    files: dict[str, bytes],
    *,
    modified: datetime | None = None,
    previous: str | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    records = []
    for path, payload in files.items():
        client.put(f"generations/{generation}/{path}", payload, modified)
        records.append(
            {
                "path": path,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {"schema_version": 1, "generation_id": generation, "files": records}
    client.put(
        f"generations/{generation}/{GENERATION_MANIFEST_PATH}",
        json.dumps(manifest).encode(),
        modified,
    )
    if activate:
        client.put(
            ACTIVE_GENERATION_PATH.as_posix(),
            json.dumps(
                {
                    "schema_version": 1,
                    "generation_id": generation,
                    "previous_generation_id": previous,
                    "manifest_sha256": None,
                    "published_at": "2026-07-16T00:00:00+00:00",
                }
            ).encode(),
        )
    return manifest


SAMPLE = {
    "raw/games/2025-26_regular_season.csv": b"game_id\n1\n",
    "metadata/dataset_manifests/2025-26_regular_season.json": b"{}\n",
    "metadata/player_names.csv": b"player_id,player_name,season,first_seen\n",
}


def test_download_writes_every_source_file_and_returns_the_manifest(tmp_path: Path) -> None:
    client = FakeR2Client()
    manifest = _publish(client, "gen-a", SAMPLE)
    dest = tmp_path / "data"

    result = download_active_generation(dest, client=client, bucket_name=BUCKET)

    assert result.generation_id == "gen-a"
    assert result.manifest == manifest
    assert (dest / "raw/games/2025-26_regular_season.csv").read_bytes() == b"game_id\n1\n"
    # Publication derives the names list and manifest itself.
    assert not (dest / "metadata/player_names.csv").exists()
    assert result.file_count == 2


def test_download_refuses_a_file_that_does_not_match_the_manifest(tmp_path: Path) -> None:
    client = FakeR2Client()
    _publish(client, "gen-a", SAMPLE)
    client.objects["generations/gen-a/raw/games/2025-26_regular_season.csv"] = b"tampered\n"

    with pytest.raises(GenerationValidationError, match="does not match"):
        download_active_generation(tmp_path / "data", client=client, bucket_name=BUCKET)


def test_download_refuses_a_non_empty_target(tmp_path: Path) -> None:
    client = FakeR2Client()
    _publish(client, "gen-a", SAMPLE)
    dest = tmp_path / "data"
    dest.mkdir()
    (dest / "stale.csv").write_text("x\n")

    with pytest.raises(GenerationPublicationError, match="not empty"):
        download_active_generation(dest, client=client, bucket_name=BUCKET)


def test_only_game_data_changes_count_as_new_data(tmp_path: Path) -> None:
    client = FakeR2Client()
    manifest = _publish(client, "gen-a", SAMPLE)
    dest = tmp_path / "data"
    download_active_generation(dest, client=client, bucket_name=BUCKET)

    # A refresh that found no games still rewrites metadata timestamps.
    (dest / "metadata/dataset_manifests/2025-26_regular_season.json").write_text('{"at": 1}\n')
    (dest / "metadata/last_refresh.json").write_text("{}\n")
    assert changed_data_files(dest, manifest) == []

    (dest / "raw/games/2025-26_regular_season.csv").write_text("game_id\n1\n2\n")
    (dest / "processed/game_features").mkdir(parents=True)
    (dest / "processed/game_features/2026-27_regular_season.csv").write_text("x\n")
    assert changed_data_files(dest, manifest) == [
        "processed/game_features/2026-27_regular_season.csv",
        "raw/games/2025-26_regular_season.csv",
    ]

    (dest / "raw/games/2025-26_regular_season.csv").unlink()
    assert "raw/games/2025-26_regular_season.csv" in changed_data_files(dest, manifest)


def test_prune_keeps_the_newest_and_the_pointer_generations(tmp_path: Path) -> None:
    client = FakeR2Client()
    start = datetime(2026, 10, 1, tzinfo=UTC)
    for day, name in enumerate(["old-1", "old-2", "mid", "prev", "active"]):
        _publish(
            client,
            name,
            {"raw/a.csv": b"a\n", "raw/b.csv": b"b\n"},
            modified=start + timedelta(days=day),
            activate=False,
        )
    # The pointer keeps an older generation as its rollback target.
    _publish(
        client,
        "active",
        {"raw/a.csv": b"a\n", "raw/b.csv": b"b\n"},
        modified=start + timedelta(days=4),
        previous="old-1",
    )
    client.put("generations/uploading/raw/a.csv", b"a\n")  # no manifest yet

    result = prune_r2_generations(keep=2, client=client, bucket_name=BUCKET)

    assert sorted(result.kept) == ["active", "old-1", "prev"]
    assert sorted(result.deleted) == ["mid", "old-2"]
    assert result.ignored == ["uploading"]
    assert result.deleted_objects == 6
    assert not any(
        key.startswith(("generations/mid/", "generations/old-2/")) for key in client.objects
    )
    assert "generations/uploading/raw/a.csv" in client.objects


def test_prune_dry_run_deletes_nothing(tmp_path: Path) -> None:
    client = FakeR2Client()
    start = datetime(2026, 10, 1, tzinfo=UTC)
    for day, name in enumerate(["a", "b", "c"]):
        _publish(client, name, {"raw/a.csv": b"a\n"}, modified=start + timedelta(days=day))

    result = prune_r2_generations(keep=2, dry_run=True, client=client, bucket_name=BUCKET)

    assert result.deleted == ["a"]
    assert client.deleted == []


def test_prune_refuses_to_keep_fewer_than_two(tmp_path: Path) -> None:
    with pytest.raises(GenerationPublicationError, match="at least 2"):
        prune_r2_generations(keep=1, client=FakeR2Client(), bucket_name=BUCKET)


def _three_generations(client: FakeR2Client) -> None:
    start = datetime(2026, 10, 1, tzinfo=UTC)
    for day, name in enumerate(["a", "b", "c"]):
        _publish(
            client,
            name,
            {"raw/a.csv": b"a\n", "raw/b.csv": b"b\n", "raw/c.csv": b"c\n"},
            modified=start + timedelta(days=day),
        )


def test_prune_deletes_the_manifest_last() -> None:
    client = FakeR2Client()
    _three_generations(client)

    prune_r2_generations(keep=2, client=client, bucket_name=BUCKET)

    a_keys = [key for key in client.deleted if key.startswith("generations/a/")]
    assert a_keys[-1] == f"generations/a/{GENERATION_MANIFEST_PATH}"
    assert len(a_keys) == 4


def test_an_interrupted_prune_keeps_the_manifest_and_reports_failure() -> None:
    client = FakeR2Client()
    _three_generations(client)
    client.fail_delete_keys = {"generations/a/raw/c.csv"}

    with pytest.raises(GenerationPublicationError, match="refused to delete"):
        prune_r2_generations(keep=2, client=client, bucket_name=BUCKET)

    assert f"generations/a/{GENERATION_MANIFEST_PATH}" in client.objects


def test_prune_stops_when_the_pointer_moves() -> None:
    client = FakeR2Client()
    start = datetime(2026, 10, 1, tzinfo=UTC)
    for day, name in enumerate(["a", "b", "c", "d"]):
        _publish(client, name, {"raw/a.csv": b"a\n"}, modified=start + timedelta(days=day))

    def publish_elsewhere() -> None:
        # Another publisher re-activates "a" while "b" is being deleted.
        client.on_delete = None
        pointer = json.loads(client.objects[ACTIVE_GENERATION_PATH.as_posix()])
        pointer.update(generation_id="a", previous_generation_id="d")
        client.put(ACTIVE_GENERATION_PATH.as_posix(), json.dumps(pointer).encode())

    client.on_delete = publish_elsewhere

    with pytest.raises(GenerationConflictError, match="changed during pruning"):
        prune_r2_generations(keep=2, client=client, bucket_name=BUCKET)

    assert f"generations/a/{GENERATION_MANIFEST_PATH}" in client.objects
    assert "generations/a/raw/a.csv" in client.objects


def test_prune_refuses_without_an_active_pointer() -> None:
    client = FakeR2Client()
    client.put(f"generations/a/{GENERATION_MANIFEST_PATH}", b"{}")

    with pytest.raises(GenerationPublicationError, match="refusing to prune"):
        prune_r2_generations(keep=2, client=client, bucket_name=BUCKET)


def test_publication_refuses_a_base_the_pointer_has_moved_away_from(tmp_path: Path) -> None:
    client = FakeR2Client()
    _publish(client, "gen-a", SAMPLE)
    dest = tmp_path / "data"
    downloaded = download_active_generation(dest, client=client, bucket_name=BUCKET)
    _publish(client, "gen-b", SAMPLE)  # someone published or rolled back meanwhile

    with pytest.raises(GenerationConflictError, match="not gen-a"):
        publish_r2_generation(
            "gen-c",
            source_dir=dest,
            client=client,
            bucket_name=BUCKET,
            expected_base=downloaded.generation_id,
        )
    assert not any(key.startswith("generations/gen-c/") for key in client.objects)


def test_changed_files_ignores_hidden_parents_of_the_data_dir(tmp_path: Path) -> None:
    client = FakeR2Client()
    manifest = _publish(client, "gen-a", SAMPLE)
    dest = tmp_path / ".cache" / "data"
    download_active_generation(dest, client=client, bucket_name=BUCKET)

    assert changed_data_files(dest, manifest) == []
