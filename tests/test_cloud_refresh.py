"""Freshness failure containment, separate from real NBA source acceptance."""

import json
import subprocess

import pytest

from tools.cloud_refresh import plan, prepare


def test_plan_is_offline_and_contains_canonical_stages():
    result = plan("2025-26")
    stages = result["stages"]
    assert (
        stages.index("pull_games")
        < stages.index("validate_raw")
        < stages.index("build_game_features")
        < stages.index("update_manifest")
    )
    assert result["automatic_refresh"] is False and result["production_publication"] is False
    with pytest.raises(ValueError):
        plan("2025-27")


@pytest.mark.parametrize("failure", ["timeout", "failed", "skipped", "partial"])
def test_failed_refresh_preserves_backup_and_never_prepares_candidate(
    tmp_path, monkeypatch, failure
):
    from tests.test_cloud_backup import make_backup

    output, receipt, _ = make_backup(tmp_path)
    archive = output / "generation.zip"
    original = archive.read_bytes()
    work = tmp_path / "refresh"

    def pipeline(args, *, cwd, env, **kwargs):
        assert cwd == work
        assert env["DATA_SOURCE"] == "local"
        assert not any(k.startswith("R2_") or k == "NBATOOLS_DATA_GENERATION" for k in env)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 1)
        stages = [{"name": name, "status": "success"} for name in plan("2025-26")["stages"]]
        if failure == "partial":
            stages = stages[:-1]
        else:
            stages[0]["status"] = failure
        (cwd / "pipeline-result.json").write_text(json.dumps({"stages": stages}))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("tools.cloud_refresh.subprocess.run", pipeline)
    result = prepare(archive, output / "backup-receipt.json", work, season="2025-26")
    assert result["state"] == "failed" and result["candidate"] is None
    assert archive.read_bytes() == original
    assert not (work / "candidate").exists()
    assert json.loads((work / "refresh-attempt.json").read_text())["production_writes"] == 0
