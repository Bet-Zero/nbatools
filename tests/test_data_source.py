from __future__ import annotations

from pathlib import Path

import pytest

from nbatools import data_source
from nbatools.data_source import (
    DATA_SOURCE_ENV,
    R2_CACHE_DIR_ENV,
    DataSourceError,
    data_exists,
    data_glob,
    data_path,
    data_read_csv,
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
        self.get_calls.append(Key)
        if self.fail_reads:
            raise FakeClientError("500", "network unavailable", 500)
        if Key not in self.objects:
            raise FakeClientError("404", "not found", 404)
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

    assert "Could not read R2 object raw/sample.csv" in str(excinfo.value)


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
