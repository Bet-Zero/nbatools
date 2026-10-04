from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GenerationPublicationError,
    GenerationValidationError,
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
        for item in Delete["Objects"]:
            self.objects.pop(item["Key"])
            self.deleted.append(item["Key"])
        return {}


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


def test_refresh_workflow_is_manual_and_keeps_r2_writes_behind_publish_mode() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/data-refresh.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    job = workflow["jobs"]["refresh"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert job["environment"] == "r2-publication"
    for step in job["steps"]:
        run = step.get("run", "")
        assert "${{" not in run
        if "--target r2" in run or "prune-generations" in run:
            assert step["if"] == "${{ inputs.mode == 'publish' }}"
        if "R2_SECRET_ACCESS_KEY" in step.get("env", {}):
            assert step["env"]["R2_SECRET_ACCESS_KEY"] == (
                "${{ secrets.R2_PUBLISH_SECRET_ACCESS_KEY }}"
            )
