from __future__ import annotations

from pathlib import Path

import pytest

from nbatools import data_source
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

    def head_object(self, *, Bucket: str, Key: str):
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
    monkeypatch.setattr(data_source, "create_r2_client", lambda config: client)
    reset_data_source_cache()
