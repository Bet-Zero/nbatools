from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nbatools.commands.pipeline import generation_publication
from nbatools.recovery_drill import run_safe_recovery_drill

pytestmark = pytest.mark.engine


def test_safe_recovery_drill_is_network_free_and_proves_recovery_invariants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_real_client(*args, **kwargs):
        del args, kwargs
        raise AssertionError("real R2 client must not be created by the safe drill")

    monkeypatch.setattr(generation_publication, "create_r2_client", reject_real_client)

    receipt = run_safe_recovery_drill()
    document = receipt.to_dict()

    assert document["status"] == "passed"
    assert document["mode"] == "temporary_local_and_in_memory_r2"
    assert document["network_access"] is False
    assert document["real_credentials_loaded"] is False
    assert document["production_mutation"] is False
    assert document["recovered_generations"] == {
        "local": "drill-local-one",
        "in_memory_r2": "drill-r2-one",
    }
    assert set(document["measurements_ms"]) == {
        "local_restore",
        "local_rollback",
        "in_memory_r2_restore",
        "in_memory_r2_rollback",
    }
    assert all(value >= 0 for value in document["measurements_ms"].values())
    assert len(document["checks"]) == 10


def test_pipeline_recovery_drill_writes_matching_receipt(tmp_path: Path) -> None:
    from nbatools.cli_apps.pipeline import app

    output = tmp_path / "evidence" / "recovery.json"
    result = CliRunner().invoke(app, ["recovery-drill", "--output", str(output)])

    assert result.exit_code == 0, result.output
    written = json.loads(output.read_text())
    printed = json.loads(result.output)
    assert written == printed
    assert written["status"] == "passed"
    assert written["production_mutation"] is False
