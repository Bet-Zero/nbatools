from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nbatools.commands.pipeline.sync_r2 import (
    R2CredentialError,
    load_r2_config,
    run_sync_r2,
)

pytestmark = pytest.mark.engine


VALID_ENV = {
    "R2_ACCOUNT_ID": "account-id",
    "R2_ACCESS_KEY_ID": "access-key-id",
    "R2_SECRET_ACCESS_KEY": "secret-access-key",
    "R2_BUCKET_NAME": "nbatools-data",
}


class FakeClientError(Exception):
    def __init__(self, code: str, message: str = "fake client error", status: int | None = None):
        http_status = status
        if http_status is None:
            http_status = int(code) if code.isdigit() else 400
        self.response = {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": http_status},
        }
        super().__init__(message)


class FakeR2Client:
    def __init__(
        self,
        *,
        remote_md5: dict[str, str] | None = None,
        fail_upload_keys: set[str] | None = None,
    ):
        self.remote_md5 = remote_md5 or {}
        self.fail_upload_keys = fail_upload_keys or set()
        self.uploaded: dict[str, bytes] = {}

    def head_object(self, *, Bucket: str, Key: str):
        if Key not in self.remote_md5:
            raise FakeClientError("404", "not found", 404)
        return {
            "ETag": f'"{self.remote_md5[Key]}"',
            "Metadata": {"nbatools-md5": self.remote_md5[Key]},
        }

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body,
        ContentLength: int,
        Metadata: dict[str, str],
    ):
        if Key in self.fail_upload_keys:
            raise FakeClientError("500", "upload failed", 500)
        body = Body.read()
        assert len(body) == ContentLength
        self.uploaded[Key] = body
        self.remote_md5[Key] = Metadata["nbatools-md5"]


def test_sync_r2_uploads_changed_files_and_skips_matching_files(tmp_path: Path):
    data_dir = tmp_path / "data"
    unchanged = data_dir / "raw" / "unchanged.csv"
    changed = data_dir / "processed" / "changed.csv"
    hidden = data_dir / ".DS_Store"
    unchanged.parent.mkdir(parents=True)
    changed.parent.mkdir(parents=True)
    unchanged.write_text("already synced\n")
    changed.write_text("new data\n")
    hidden.write_text("skip me\n")

    client = FakeR2Client(remote_md5={"raw/unchanged.csv": _md5(unchanged)})

    result = run_sync_r2(data_dir=data_dir, client=client, env=VALID_ENV, env_file=None)

    assert result.success
    assert result.total_files == 2
    assert result.synced_files == 1
    assert result.skipped_files == 1
    assert result.bytes_uploaded == changed.stat().st_size
    assert client.uploaded == {"processed/changed.csv": b"new data\n"}


def test_sync_r2_dry_run_reports_uploads_without_writing(tmp_path: Path):
    data_dir = tmp_path / "data"
    file_path = data_dir / "metadata" / "manifest.csv"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("season,current_through\n")
    client = FakeR2Client()

    result = run_sync_r2(
        data_dir=data_dir,
        dry_run=True,
        client=client,
        env=VALID_ENV,
        env_file=None,
    )

    assert result.success
    assert result.dry_run
    assert result.synced_files == 1
    assert result.bytes_uploaded == file_path.stat().st_size
    assert client.uploaded == {}


def test_sync_r2_records_partial_upload_failures(tmp_path: Path):
    data_dir = tmp_path / "data"
    ok_path = data_dir / "raw" / "ok.csv"
    fail_path = data_dir / "raw" / "fail.csv"
    ok_path.parent.mkdir(parents=True)
    ok_path.write_text("ok\n")
    fail_path.write_text("fail\n")
    client = FakeR2Client(fail_upload_keys={"raw/fail.csv"})

    result = run_sync_r2(data_dir=data_dir, client=client, env=VALID_ENV, env_file=None)

    assert not result.success
    assert result.synced_files == 2
    assert result.failed_files == 1
    assert result.failures[0].key == "raw/fail.csv"
    assert "Could not upload object" in result.failures[0].error
    assert client.uploaded == {"raw/ok.csv": b"ok\n"}


def test_load_r2_config_reports_missing_credentials():
    with pytest.raises(R2CredentialError) as excinfo:
        load_r2_config(env={}, env_file=None)

    message = str(excinfo.value)
    assert "Missing R2 environment variables" in message
    assert "R2_ACCOUNT_ID" in message
    assert "R2_SECRET_ACCESS_KEY" in message


def test_pipeline_sync_r2_cli_reports_missing_credentials_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from nbatools.cli_apps.pipeline import app

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["sync-r2", "--data-dir", str(data_dir)],
        env={"PATH": ""},
    )

    assert result.exit_code == 1
    assert "R2 sync failed: Missing R2 environment variables" in result.output
    assert "Traceback" not in result.output


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
