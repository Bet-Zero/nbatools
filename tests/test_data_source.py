from __future__ import annotations

import hashlib
import json
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic

import pytest

from nbatools import data_source
from nbatools.admission_control import _QUERY_WORK_DEADLINE, QueryWorkExpired
from nbatools.data_source import (
    ACTIVE_GENERATION_PATH,
    DATA_GENERATION_ENV,
    DATA_SOURCE_ENV,
    LOCAL_DATA_ROOT_ENV,
    R2_CACHE_DIR_ENV,
    DataSourceError,
    data_exists,
    data_generation_context,
    data_glob,
    data_path,
    data_prefetch,
    data_read_csv,
    data_source_cache_key,
    reset_data_source_cache,
)

pytestmark = pytest.mark.engine


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeClientError(Exception):
    def __init__(self, code: str, message: str = "fake client error", status: int = 400):
        self.response = {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__(message)


class FakeR2Client:
    def __init__(self, objects: dict[str, bytes], fail_reads: bool = False):
        self.objects = objects
        self.fail_reads = fail_reads
        self.get_calls: list[str] = []
        self.head_calls: list[str] = []

    def head_object(self, *, Bucket: str, Key: str):
        self.head_calls.append(Key)
        if self.fail_reads:
            raise FakeClientError("500", "network unavailable", 500)
        if Key not in self.objects:
            raise FakeClientError("404", "not found", 404)
        return {}

    def get_object(self, *, Bucket: str, Key: str):
        if self.fail_reads:
            raise FakeClientError("500", "network unavailable", 500)
        if Key not in self.objects:
            raise FakeClientError("404", "not found", 404)
        self.get_calls.append(Key)
        return {"Body": FakeBody(self.objects[Key])}

    def list_objects_v2(self, **kwargs):
        prefix = kwargs.get("Prefix", "")
        contents = [{"Key": key} for key in sorted(self.objects) if key.startswith(prefix)]
        return {"Contents": contents, "IsTruncated": False}


@pytest.fixture(autouse=True)
def _reset_data_source(monkeypatch: pytest.MonkeyPatch):
    reset_data_source_cache()
    monkeypatch.delenv(DATA_SOURCE_ENV, raising=False)
    monkeypatch.delenv(R2_CACHE_DIR_ENV, raising=False)
    monkeypatch.delenv(DATA_GENERATION_ENV, raising=False)
    monkeypatch.delenv(LOCAL_DATA_ROOT_ENV, raising=False)
    yield
    reset_data_source_cache()


def test_local_data_source_reads_from_default_data_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "raw" / "sample.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("name,value\nJokic,1\n")

    assert data_exists("raw/sample.csv")
    assert data_path("data/raw/sample.csv") == Path("data/raw/sample.csv")

    df = data_read_csv("raw/sample.csv")

    assert df.to_dict("records") == [{"name": "Jokic", "value": 1}]


def test_r2_data_source_downloads_and_caches_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client = FakeR2Client({"raw/sample.csv": b"name,value\nJokic,1\n"})
    _configure_r2(monkeypatch, tmp_path, client)

    first = data_read_csv("data/raw/sample.csv")
    second = data_read_csv("raw/sample.csv")

    assert first.equals(second)
    assert client.get_calls == ["raw/sample.csv"]
    assert data_exists("raw/sample.csv")
    assert data_glob("raw/*.csv") == [Path("data/raw/sample.csv")]


def test_r2_cache_identity_keeps_accounts_separate(tmp_path, monkeypatch):
    first = FakeR2Client({"raw/sample.csv": b"name,value\nOne,1\n"})
    second = FakeR2Client({"raw/sample.csv": b"name,value\nTwo,2\n"})
    _configure_r2(monkeypatch, tmp_path, first)
    monkeypatch.setattr(
        data_source,
        "create_r2_client",
        lambda config: first if config.account_id == "account-id" else second,
    )
    first_key = data_source_cache_key()
    assert data_read_csv("raw/sample.csv")["value"].tolist() == [1]

    monkeypatch.setenv("R2_ACCOUNT_ID", "different-account")
    assert first_key != data_source_cache_key()
    assert data_read_csv("raw/sample.csv")["value"].tolist() == [2]


def test_r2_generation_switch_reloads_same_logical_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    client = FakeR2Client(
        {
            pointer_key: b'{"generation_id":"generation-one"}',
            "generations/generation-one/raw/sample.csv": b"name,value\nJokic,1\n",
            "generations/generation-two/raw/sample.csv": b"name,value\nJokic,2\n",
        }
    )
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context() as first_generation:
        first_key = data_source_cache_key()
        first = data_read_csv("raw/sample.csv")
        client.objects[pointer_key] = b'{"generation_id":"generation-two"}'
        still_first = data_read_csv("raw/sample.csv")

    with data_generation_context() as second_generation:
        second_key = data_source_cache_key()
        second = data_read_csv("raw/sample.csv")

    assert first_generation == "generation-one"
    assert second_generation == "generation-two"
    assert first_key != second_key
    assert first["value"].tolist() == [1]
    assert still_first["value"].tolist() == [1]
    assert second["value"].tolist() == [2]
    assert client.get_calls == [
        pointer_key,
        "generations/generation-one/raw/sample.csv",
        pointer_key,
        "generations/generation-two/raw/sample.csv",
    ]


def _generation_objects(generation: str, files: dict[str, bytes], *, manifest: bool = True):
    prefix = f"generations/{generation}/"
    objects = {ACTIVE_GENERATION_PATH.as_posix(): f'{{"generation_id":"{generation}"}}'.encode()}
    objects.update({prefix + path: body for path, body in files.items()})
    if manifest:
        document = {"generation_id": generation, "files": [{"path": path} for path in files]}
        objects[prefix + "metadata/generation_manifest.json"] = json.dumps(document).encode()
    return objects


def published_generation_objects(generation, files):
    prefix = f"generations/{generation}/"
    manifest = json.dumps(
        dict(
            schema_version=1,
            generation_id=generation,
            files=[
                dict(path=path, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                for path, raw in files.items()
            ],
        )
    ).encode()
    digest = hashlib.sha256(manifest).hexdigest()
    objects = {prefix + path: raw for path, raw in files.items()}
    objects[prefix + data_source.GENERATION_MANIFEST_PATH.as_posix()] = manifest
    objects[ACTIVE_GENERATION_PATH.as_posix()] = json.dumps(
        dict(generation_id=generation, manifest_sha256=digest)
    ).encode()
    return objects, digest


def test_published_reads_use_pointer_digest_and_only_manifested_bytes(tmp_path, monkeypatch):
    objects, _ = published_generation_objects("published", {"raw/sample.csv": b"valid"})
    prefix = "generations/published/"
    objects[prefix + "raw/unlisted.csv"] = b"unlisted"
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)
    with data_generation_context():
        assert data_glob("raw/*.csv") == [Path("data/raw/sample.csv")]
        assert data_exists("raw/sample.csv") and not data_exists("raw/unlisted.csv")
        with pytest.raises(FileNotFoundError, match="absent from the generation manifest"):
            data_path("raw/unlisted.csv")
        del objects[prefix + "raw/sample.csv"]
        with pytest.raises(DataSourceError, match="Missing published R2 data object"):
            data_path("raw/sample.csv")
        # A same-length change must fail before the file reaches any consumer.
        objects[prefix + "raw/sample.csv"] = b"wrong"
        with pytest.raises(DataSourceError, match="checksum"):
            data_path("raw/sample.csv")
        objects[prefix + "raw/sample.csv"] = b"valid"
        assert data_path("raw/sample.csv").read_bytes() == b"valid"
    assert not client.head_calls
    assert client.get_calls.count(prefix + "metadata/generation_manifest.json") == 1


@pytest.mark.parametrize("first_read", ["valid", "expired", "corrupt", "waiter-expired"])
def test_overlapping_verified_reads_share_only_the_exact_download(
    tmp_path, monkeypatch, first_read
):
    path = "raw/shared.csv"
    key = "generations/published/" + path
    other = "raw/independent.csv"
    objects, _ = published_generation_objects("published", {path: b"valid", other: b"other"})
    downloading = Event()
    waiting = Event()
    finish = Event()

    class BlockingClient(FakeR2Client):
        def get_object(self, *, Bucket, Key):
            response = super().get_object(Bucket=Bucket, Key=Key)
            if Key == key and not downloading.is_set():
                downloading.set()
                assert finish.wait(5)
                if first_read == "expired":
                    raise QueryWorkExpired("The first reader exhausted its budget")
                if first_read == "corrupt":
                    return {"Body": FakeBody(b"wrong")}
            return response

    class ObservedDownload(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout=timeout)

    client = BlockingClient(objects)
    _configure_managed_cache(monkeypatch, tmp_path, client)
    with data_generation_context():
        assert data_exists(path)  # Warm the manifest separately from the object.
    monkeypatch.setattr(data_source, "Future", ObservedDownload)

    def read(relative):
        with data_generation_context():
            return data_path(relative).read_bytes()

    def wait_for_shared():
        if first_read != "waiter-expired":
            return read(path)
        with data_generation_context():
            token = _QUERY_WORK_DEADLINE.set(monotonic() + 0.25)
            try:
                return data_path(path).read_bytes()
            finally:
                _QUERY_WORK_DEADLINE.reset(token)

    with ThreadPoolExecutor(max_workers=3) as pool:
        leader = pool.submit(read, path)
        try:
            assert downloading.wait(5)
            waiter = pool.submit(wait_for_shared)
            assert waiting.wait(5)
            assert pool.submit(read, other).result(timeout=2) == b"other"
            assert client.get_calls.count(key) == 1
            if first_read == "waiter-expired":
                with pytest.raises(QueryWorkExpired):
                    waiter.result(timeout=2)
                assert not leader.done()
        finally:
            finish.set()
        if first_read == "expired":
            with pytest.raises(QueryWorkExpired):
                leader.result(timeout=5)
            assert waiter.result(timeout=5) == b"valid"
        elif first_read == "corrupt":
            for pending in (leader, waiter):
                with pytest.raises(DataSourceError, match="checksum"):
                    pending.result(timeout=5)
        else:
            assert leader.result(timeout=5) == b"valid"
            if first_read == "valid":
                assert waiter.result(timeout=5) == b"valid"

    assert read(path) == b"valid"
    assert client.get_calls.count(key) == (2 if first_read in {"expired", "corrupt"} else 1)


def test_hosted_cache_retires_a_generation_only_after_the_last_reader(tmp_path, monkeypatch):
    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    path = "raw/sample.csv"
    old, _ = published_generation_objects("old", {path: b"value\n1\n"})
    latest, _ = published_generation_objects("latest", {path: b"value\n2\n"})
    objects = old | {key: value for key, value in latest.items() if key != pointer_key}
    client = FakeR2Client(objects)
    _configure_managed_cache(monkeypatch, tmp_path, client)

    old_pinned = Event()
    finish_old = Event()

    def read_old():
        with data_generation_context() as generation:
            assert generation == "old"
            cached = data_path(path)
            old_pinned.set()
            assert finish_old.wait(5)
            assert cached.read_bytes() == b"value\n1\n"
            assert data_path(path) == cached
            return cached

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(read_old)
        try:
            assert old_pinned.wait(5)
            objects[pointer_key] = latest[pointer_key]
            with data_generation_context() as generation:
                assert generation == "latest"
                newest_path = data_path(path)
                assert newest_path.read_bytes() == b"value\n2\n"
                finish_old.set()
                retired_path = pending.result(timeout=5)
                assert not retired_path.exists()
                assert newest_path.exists()
        finally:
            finish_old.set()

    objects[pointer_key] = old[pointer_key]
    with data_generation_context() as generation:
        assert generation == "old"
        assert data_path(path).read_bytes() == b"value\n1\n"
        assert not newest_path.exists()
    assert client.get_calls.count(f"generations/old/{path}") == 2


def test_delayed_reader_keeps_the_newer_observed_cache(tmp_path, monkeypatch):
    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    path = "raw/sample.csv"
    old, _ = published_generation_objects("old", {path: b"old"})
    latest, _ = published_generation_objects("latest", {path: b"latest"})
    objects = old | {key: value for key, value in latest.items() if key != pointer_key}
    client = FakeR2Client(objects)
    _configure_managed_cache(monkeypatch, tmp_path, client)

    observed = Event()
    resume = Event()
    pin_cache = data_source._R2DataSource.pin_cache

    def pause_before_pin(source, generation):
        if generation.id == "old":
            observed.set()
            assert resume.wait(5)
        return pin_cache(source, generation)

    def read_old():
        with data_generation_context() as generation:
            assert generation == "old"
            return data_path(path).read_bytes()

    monkeypatch.setattr(data_source._R2DataSource, "pin_cache", pause_before_pin)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(read_old)
        try:
            assert observed.wait(5)
            objects[pointer_key] = latest[pointer_key]
            with data_generation_context():
                newest_path = data_path(path)
        finally:
            resume.set()
        assert pending.result(timeout=5) == b"old"

    assert newest_path.read_bytes() == b"latest"
    with data_generation_context():
        assert data_path(path) == newest_path
    assert client.get_calls.count(f"generations/latest/{path}") == 1


@pytest.mark.served_seasons
def test_freshness_keeps_one_cache_and_refresh_log_during_rollover(tmp_path, monkeypatch):
    from nbatools.commands import _seasons
    from nbatools.vercel_functions import freshness_response

    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    path = "raw/games/2023-24_regular_season.csv"
    log = "metadata/last_refresh.json"
    old, _ = published_generation_objects(
        "fresh-old",
        {
            path: b"game_date,is_final\n2024-04-11,1\n",
            log: b'{"success":true,"timestamp":"2024-04-11T13:00:00"}',
        },
    )
    latest, _ = published_generation_objects(
        "fresh-new",
        {
            path: b"game_date,is_final\n2024-04-12,1\n",
            log: b'{"success":true,"timestamp":"2024-04-12T13:00:00"}',
        },
    )
    objects = old | {key: value for key, value in latest.items() if key != pointer_key}
    _configure_managed_cache(monkeypatch, tmp_path, FakeR2Client(objects))
    monkeypatch.setattr(_seasons, "_LATEST_SERVED_CACHE", {})
    with data_generation_context():
        old_path = data_path(path)

    started = Event()
    resume = Event()
    read_csv = data_source.pd.read_csv

    def pause_before_open(path, *args, **kwargs):
        if path == old_path and not started.is_set():
            started.set()
            assert resume.wait(5)
        return read_csv(path, *args, **kwargs)

    monkeypatch.setattr(data_source.pd, "read_csv", pause_before_open)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(freshness_response)
        try:
            assert started.wait(5)
            objects[pointer_key] = latest[pointer_key]
            with data_generation_context():
                assert data_path(path).read_bytes() == latest[f"generations/fresh-new/{path}"]
        finally:
            resume.set()
        status, result = pending.result(timeout=5)

    assert status == 200
    assert result["seasons"][0]["season"] == "2023-24"
    assert result["last_refresh_at"] == "2024-04-11T13:00:00"
    assert not old_path.exists()


def test_explicit_r2_cache_remains_available_across_requests(tmp_path, monkeypatch):
    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    path = "raw/sample.csv"
    old, _ = published_generation_objects("old", {path: b"same"})
    latest, _ = published_generation_objects("latest", {path: b"same"})
    objects = old | {key: value for key, value in latest.items() if key != pointer_key}
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)
    monkeypatch.setenv("VERCEL", "1")

    with data_generation_context():
        original_path = data_path(path)

    objects[pointer_key] = latest[pointer_key]
    with data_generation_context(), pytest.raises(DataSourceError, match="Missing published"):
        del objects[f"generations/latest/{path}"]
        data_path(path)
    assert original_path.read_bytes() == b"same"


def test_published_reads_fail_closed_on_wrong_manifest(tmp_path, monkeypatch):
    objects, _ = published_generation_objects("published", {"raw/sample.csv": b"valid"})
    key = "generations/published/metadata/generation_manifest.json"
    objects[key] += b" "
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)
    with data_generation_context(), pytest.raises(DataSourceError, match="checksum"):
        data_exists("raw/sample.csv")
    assert client.get_calls == [ACTIVE_GENERATION_PATH.as_posix(), key]


def test_r2_exists_answers_from_the_generation_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = FakeR2Client(_generation_objects("gen-a", {"raw/games/2025-26_playoffs.csv": b"x"}))
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        for _ in range(5):
            assert data_exists("data/raw/games/2025-26_playoffs.csv")
            assert not data_exists("raw/pbp/2025-26_playoffs.csv")

    # One HEAD for the unlisted path, none for the listed one, one manifest GET.
    assert client.head_calls == ["generations/gen-a/raw/pbp/2025-26_playoffs.csv"]
    assert client.get_calls.count("generations/gen-a/metadata/generation_manifest.json") == 1


def test_r2_exists_without_manifest_remembers_head_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = FakeR2Client(_generation_objects("gen-a", {"raw/sample.csv": b"x"}, manifest=False))
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        for _ in range(3):
            assert data_exists("raw/sample.csv")
            assert not data_exists("raw/missing.csv")

    assert sorted(client.head_calls) == [
        "generations/gen-a/raw/missing.csv",
        "generations/gen-a/raw/sample.csv",
    ]


def test_r2_exists_follows_a_generation_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    objects = _generation_objects("gen-a", {"raw/old.csv": b"x"})
    objects.update(_generation_objects("gen-b", {"raw/new.csv": b"y"}))
    objects[ACTIVE_GENERATION_PATH.as_posix()] = b'{"generation_id":"gen-a"}'
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        assert data_exists("raw/old.csv")
        assert not data_exists("raw/new.csv")
    client.objects[ACTIVE_GENERATION_PATH.as_posix()] = b'{"generation_id":"gen-b"}'
    with data_generation_context():
        assert data_exists("raw/new.csv")
        assert not data_exists("raw/old.csv")


def test_r2_legacy_layout_is_not_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client = FakeR2Client({})
    _configure_r2(monkeypatch, tmp_path, client)

    assert not data_exists("raw/sample.csv")
    client.objects["raw/sample.csv"] = b"x"
    assert data_exists("raw/sample.csv")


def test_r2_exists_reads_a_malformed_manifest_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    objects = _generation_objects("gen-a", {"raw/sample.csv": b"x"}, manifest=False)
    manifest_key = "generations/gen-a/metadata/generation_manifest.json"
    objects[manifest_key] = b'{"files": ["raw/sample.csv"]}'
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        for _ in range(3):
            assert data_exists("raw/sample.csv")

    assert client.get_calls.count(manifest_key) == 1
    assert client.head_calls == ["generations/gen-a/raw/sample.csv"]


def test_r2_exists_does_not_remember_a_failed_manifest_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = FakeR2Client(_generation_objects("gen-a", {"raw/sample.csv": b"x"}))
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        client.fail_reads = True
        with pytest.raises(DataSourceError):
            data_exists("raw/sample.csv")
        client.fail_reads = False
        assert data_exists("raw/sample.csv")
        assert data_exists("raw/sample.csv")

    assert client.get_calls.count("generations/gen-a/metadata/generation_manifest.json") == 1


def test_r2_download_never_exposes_a_partial_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    client = FakeR2Client({"raw/sample.csv": b"name,value\nJokic,1\n"})
    _configure_r2(monkeypatch, tmp_path, client)
    cache_file = tmp_path / "cache" / "nbatools-data" / "legacy" / "raw" / "sample.csv"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"name,value\nJokic,1\n")
    replaced: list[tuple[str, str]] = []
    real_replace = data_source.os.replace

    def spy_replace(src, dst):
        # At the moment of the swap the reader-visible file is still complete.
        assert cache_file.read_bytes() == b"name,value\nJokic,1\n"
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(data_source.os, "replace", spy_replace)

    assert data_read_csv("raw/sample.csv")["value"].tolist() == [1]
    assert replaced and replaced[0][1] == str(cache_file)
    assert [p.name for p in cache_file.parent.iterdir()] == ["sample.csv"]


def test_r2_prefetch_fetches_in_the_pinned_generation_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    objects = _generation_objects(
        "gen-a",
        {f"raw/player_game_stats/{season}_regular_season.csv": b"v\n1\n" for season in "abc"},
    )
    objects[pointer_key] = b'{"generation_id":"gen-a"}'
    objects["generations/gen-b/raw/player_game_stats/a_regular_season.csv"] = b"v\n2\n"
    client = FakeR2Client(objects)
    _configure_r2(monkeypatch, tmp_path, client)
    paths = [f"data/raw/player_game_stats/{season}_regular_season.csv" for season in "abcz"]

    with data_generation_context():
        # The pointer moves mid-request; the prefetch still reads gen-a.
        client.objects[pointer_key] = b'{"generation_id":"gen-b"}'
        client.get_calls.clear()
        data_prefetch(paths)
        fetched = sorted(client.get_calls)
        values = [data_read_csv(path)["v"].tolist() for path in paths[:3]]

    assert fetched == [
        f"generations/gen-a/raw/player_game_stats/{season}_regular_season.csv" for season in "abc"
    ]
    assert values == [[1], [1], [1]]
    # The reads came from the prefetched files; the missing one was skipped.
    assert sorted(client.get_calls) == fetched
    with data_generation_context(), pytest.raises(FileNotFoundError):
        data_read_csv(paths[3])


def test_frame_cache_key_changes_with_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from nbatools.commands.data_utils import load_latest_standings_snapshot

    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    client = FakeR2Client(
        {
            pointer_key: b'{"generation_id":"standings-one"}',
            "generations/standings-one/raw/standings_snapshots/2099-00_regular_season.csv": (
                b"team_id,snapshot_date,wins\n1,2099-01-01,10\n"
            ),
            "generations/standings-two/raw/standings_snapshots/2099-00_regular_season.csv": (
                b"team_id,snapshot_date,wins\n1,2099-01-02,11\n"
            ),
        }
    )
    _configure_r2(monkeypatch, tmp_path, client)

    with data_generation_context():
        first = load_latest_standings_snapshot("2099-00")
    client.objects[pointer_key] = b'{"generation_id":"standings-two"}'
    with data_generation_context():
        second = load_latest_standings_snapshot("2099-00")

    assert first["wins"].tolist() == [10]
    assert second["wins"].tolist() == [11]


def test_local_request_does_not_mix_generations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(LOCAL_DATA_ROOT_ENV, str(tmp_path))
    pointer = tmp_path / "data" / ACTIVE_GENERATION_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"generation_id":"local-one"}')
    for generation, value in (("local-one", 1), ("local-two", 2)):
        path = tmp_path / "data" / "generations" / generation / "raw" / "sample.csv"
        path.parent.mkdir(parents=True)
        path.write_text(f"name,value\nJokic,{value}\n")
    reset_data_source_cache()

    with data_generation_context():
        assert data_glob("raw/*.csv") == [Path("data/raw/sample.csv")]
        first = data_read_csv("raw/sample.csv")
        pointer.write_text('{"generation_id":"local-two"}')
        still_first = data_read_csv("raw/sample.csv")

    with data_generation_context():
        second = data_read_csv("raw/sample.csv")

    assert first["value"].tolist() == [1]
    assert still_first["value"].tolist() == [1]
    assert second["value"].tolist() == [2]


@pytest.mark.parametrize(
    "payload, message",
    [
        ("not-json", "not valid JSON"),
        ('{"generation_id":"../escape"}', "Invalid data generation identifier"),
    ],
)
def test_invalid_local_generation_pointer_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: str,
    message: str,
) -> None:
    monkeypatch.setenv(LOCAL_DATA_ROOT_ENV, str(tmp_path))
    pointer = tmp_path / "data" / ACTIVE_GENERATION_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_text(payload)
    reset_data_source_cache()

    with pytest.raises(DataSourceError, match=message):
        with data_generation_context():
            pass


def test_r2_data_source_raises_without_silent_local_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    local_path = tmp_path / "data" / "raw" / "sample.csv"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("name,value\nlocal,1\n")
    client = FakeR2Client({"raw/sample.csv": b"name,value\nremote,2\n"}, fail_reads=True)
    _configure_r2(monkeypatch, tmp_path, client)

    with pytest.raises(DataSourceError) as excinfo:
        data_path("raw/sample.csv")

    assert "Could not read active generation pointer" in str(excinfo.value)


def test_player_advanced_team_context_loader_reads_from_r2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from nbatools.commands.player_advanced_metrics import load_team_games_for_seasons

    client = FakeR2Client(
        {
            "raw/team_game_stats/2099-00_regular_season.csv": (
                b"game_id,team_id,team_abbr,team_name,opponent_team_id,"
                b"opponent_team_abbr,minutes,fgm,fga,fta,tov,reb,wl\n"
                b"G1,100,AAA,A Team,200,BBB,240,40,85,20,12,50,W\n"
            )
        }
    )
    _configure_r2(monkeypatch, tmp_path, client)

    df = load_team_games_for_seasons(["2099-00"], "Regular Season")

    assert df.to_dict("records") == [
        {
            "game_id": "G1",
            "team_id": 100,
            "team_abbr": "AAA",
            "team_name": "A Team",
            "opponent_team_id": 200,
            "opponent_team_abbr": "BBB",
            "minutes": 240,
            "fgm": 40,
            "fga": 85,
            "fta": 20,
            "tov": 12,
            "reb": 50,
            "wl": "W",
            "season": "2099-00",
            "season_type": "Regular Season",
        }
    ]
    assert client.get_calls == ["raw/team_game_stats/2099-00_regular_season.csv"]


def _configure_r2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    client: FakeR2Client,
) -> None:
    monkeypatch.setenv(DATA_SOURCE_ENV, "r2")
    monkeypatch.setenv(R2_CACHE_DIR_ENV, str(tmp_path / "cache"))
    monkeypatch.setenv("R2_ACCOUNT_ID", "account-id")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "access-key-id")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret-access-key")
    monkeypatch.setenv("R2_BUCKET_NAME", "nbatools-data")
    monkeypatch.setattr(data_source, "create_r2_client", lambda config, **_: client)
    reset_data_source_cache()


def _configure_managed_cache(monkeypatch, tmp_path, client):
    _configure_r2(monkeypatch, tmp_path, client)
    monkeypatch.delenv(R2_CACHE_DIR_ENV)
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setattr(data_source.tempfile, "gettempdir", lambda: str(tmp_path))


def test_query_transport_bounds_connect_and_header_waits_only_inside_query(monkeypatch):
    from time import monotonic

    from nbatools.admission_control import AdmissionController

    clients = {}

    def create_client(config, *, query_io_timeout=None):
        return clients.setdefault(query_io_timeout, FakeR2Client({}))

    monkeypatch.setattr(data_source, "create_r2_client", create_client)
    source = data_source._R2DataSource(data_source.R2Config("id", "key", "secret", "bucket"))
    controller = AdmissionController()
    try:
        assert source._request_client() is clients[None]
        assert (
            controller.run_query("budget-9", source._request_client, deadline=monotonic() + 9)
            is clients[4]
        )
        assert (
            controller.run_query("budget-3", source._request_client, deadline=monotonic() + 3)
            is clients[1]
        )
        assert (
            controller.run_query("budget-1", source._request_client, deadline=monotonic() + 1)
            is clients[0.25]
        )
        assert source._request_client() is clients[None]
    finally:
        controller._executor.shutdown(wait=True)


def test_query_stream_preserves_eof_validation_and_closes_socket():
    from io import BytesIO

    from nbatools.admission_control import AdmissionController

    class CheckedStream(BytesIO):
        eof_reads = 0

        def set_socket_timeout(self, seconds):
            assert not self.closed and seconds > 0

        def read(self, length=-1):
            content = super().read(length)
            if not content:
                self.eof_reads += 1
            return content

    expected = b"x" * (2 * 128 * 1024 + 17)
    stream = CheckedStream(expected)
    controller = AdmissionController()
    try:
        assert (
            controller.run_query(
                "stream",
                lambda: data_source._read_r2_body({"Body": stream, "ContentLength": len(expected)}),
            )
            == expected
        )
        assert stream.eof_reads == 1 and stream.closed
    finally:
        controller._executor.shutdown(wait=True)
