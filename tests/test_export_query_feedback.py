from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from nbatools import query_feedback_review
from nbatools.data_source import R2Config
from tools import export_query_feedback

pytestmark = pytest.mark.output


def test_local_fixture_export_creates_outputs_and_normalized_contract(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record(
            "wrong",
            query="Who leads the NBA in points per game this season?",
            feedback_type="wrong_answer",
            metadata={
                "route": "season_leaders",
                "unsupported_filters": [],
                "email": "user@example.com",
                "raw_result": [{"secret": "SHOULD_NOT_EXPORT"}],
            },
            raw_result=[{"secret": "SHOULD_NOT_EXPORT"}],
            ip="127.0.0.1",
        ),
        feedback_record(
            "copy",
            query="Why is this answer worded strangely?",
            feedback_type="confusing_answer",
        ),
        feedback_record(
            "smoke",
            query="Direct endpoint smoke safe payload",
            feedback_type="other",
            route="smoke",
            status="ok",
            reason="smoke",
        ),
    ]
    write_fixture_records(local_dir, records)

    run_dir = run_export(tmp_path, local_dir, "local_contract")

    expected_files = {
        "feedback_review.md",
        "feedback_records.csv",
        "feedback_records.jsonl",
        "summary.json",
        "triage_decisions_template.csv",
    }
    assert expected_files == {path.name for path in run_dir.iterdir()}

    csv_rows = read_csv(run_dir / "feedback_records.csv")
    assert len(csv_rows) == 2
    for field in [
        "query_normalized",
        "metadata_summary",
        "result_section_row_counts",
        "is_smoke",
        "group_id",
        "suggested_triage",
        "triage_modifiers",
    ]:
        assert field in csv_rows[0]

    jsonl_rows = read_jsonl(run_dir / "feedback_records.jsonl")
    assert len(jsonl_rows) == len(csv_rows)
    assert {row["id"] for row in jsonl_rows} == {"wrong", "copy"}

    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["source_mode"] == "local"
    assert summary["total_found"] == 3
    assert summary["total_exported"] == 2
    assert summary["excluded_smoke_count"] == 1
    assert summary["group_count"] == 2
    for key in [
        "feedback_review_md",
        "feedback_records_csv",
        "feedback_records_jsonl",
        "summary_json",
        "triage_decisions_template_csv",
    ]:
        assert key in summary["output_paths"]

    triage_rows = read_csv(run_dir / "triage_decisions_template.csv")
    assert len(triage_rows) == summary["group_count"]

    combined_output = "\n".join(path.read_text() for path in run_dir.iterdir())
    assert "SHOULD_NOT_EXPORT" not in combined_output
    assert "user@example.com" not in combined_output
    assert "127.0.0.1" not in combined_output
    assert "raw_result" not in combined_output


def test_smoke_records_are_included_only_when_requested(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record("normal", query="Jokic last 10 games"),
        feedback_record(
            "smoke",
            query="Direct endpoint smoke safe payload",
            feedback_type="other",
            route="smoke",
            status="ok",
            reason="smoke",
            user_note="Smoke test from endpoint",
        ),
    ]
    write_fixture_records(local_dir, records)

    default_run = run_export(tmp_path, local_dir, "smoke_default")
    default_summary = json.loads((default_run / "summary.json").read_text())
    assert default_summary["total_exported"] == 1
    assert default_summary["excluded_smoke_count"] == 1
    assert {row["id"] for row in read_jsonl(default_run / "feedback_records.jsonl")} == {"normal"}

    include_run = run_export(tmp_path, local_dir, "smoke_included", "--include-smoke")
    include_summary = json.loads((include_run / "summary.json").read_text())
    assert include_summary["total_exported"] == 2
    assert include_summary["excluded_smoke_count"] == 0
    smoke_row = {row["id"]: row for row in read_jsonl(include_run / "feedback_records.jsonl")}[
        "smoke"
    ]
    assert smoke_row["is_smoke"] is True
    assert smoke_row["suggested_triage"] == "no_action"


def test_grouping_uses_hash_then_fallback_and_duplicate_modifier(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record("hash_a", query="Duplicate demand A", query_normalized_hash="same_hash"),
        feedback_record(
            "hash_b",
            query="Different words but same stored hash",
            query_normalized_hash="same_hash",
        ),
        feedback_record(
            "fallback_a",
            query="Players with most personal fouls",
            query_normalized_hash=None,
            feedback_source="automatic",
            feedback_type="unsupported",
            status="no_result",
            reason="filter_not_supported",
            metadata={"unsupported_filters": ["personal_foul_leaderboard"]},
        ),
        feedback_record(
            "fallback_b",
            query=" players   with MOST personal fouls ",
            query_normalized_hash=None,
            feedback_source="automatic",
            feedback_type="unsupported",
            status="no_result",
            reason="filter_not_supported",
            metadata={"unsupported_filters": ["personal_foul_leaderboard"]},
        ),
    ]
    write_fixture_records(local_dir, records)

    run_dir = run_export(tmp_path, local_dir, "grouping")

    rows = {row["id"]: row for row in read_jsonl(run_dir / "feedback_records.jsonl")}
    assert rows["hash_a"]["group_id"] == rows["hash_b"]["group_id"]
    assert rows["fallback_a"]["group_id"] == rows["fallback_b"]["group_id"]
    assert rows["hash_a"]["group_id"] != rows["fallback_a"]["group_id"]
    assert "prioritize_review" in rows["hash_a"]["triage_modifiers"]
    assert json.loads((run_dir / "summary.json").read_text())["group_count"] == 2
    assert len(read_csv(run_dir / "triage_decisions_template.csv")) == 2


def test_suggested_triage_matches_documented_heuristics(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record(
            "parser",
            feedback_type="error",
            route=None,
            status="error",
            reason="unrouted",
        ),
        feedback_record(
            "unsupported",
            feedback_type="unsupported",
            status="no_result",
            reason="filter_not_supported",
        ),
        feedback_record(
            "data",
            feedback_type="no_result",
            status="no_result",
            reason="no_data",
        ),
        feedback_record("wrong", feedback_type="wrong_answer"),
        feedback_record("confusing", feedback_type="confusing_answer"),
        feedback_record("ui", feedback_type="ui_issue"),
        feedback_record(
            "perf",
            feedback_source="automatic",
            feedback_type="other",
            status="ok",
            elapsed_ms=8000,
        ),
        feedback_record(
            "smoke",
            query="Direct endpoint smoke safe payload",
            feedback_type="other",
            route="smoke",
            reason="smoke",
        ),
    ]
    write_fixture_records(local_dir, records)

    run_dir = run_export(tmp_path, local_dir, "triage", "--include-smoke")

    rows = {row["id"]: row for row in read_jsonl(run_dir / "feedback_records.jsonl")}
    assert rows["parser"]["suggested_triage"] == "parser_issue"
    assert rows["unsupported"]["suggested_triage"] == "unsupported_family"
    assert rows["data"]["suggested_triage"] == "data_issue"
    assert rows["wrong"]["suggested_triage"] == "raw_qa_case"
    assert rows["confusing"]["suggested_triage"] == "frontend_copy_case"
    assert rows["ui"]["suggested_triage"] == "visual_qa_case"
    assert rows["perf"]["suggested_triage"] == "performance_review"
    assert rows["smoke"]["suggested_triage"] == "no_action"


def test_date_filtering_supports_dates_and_iso_timestamps(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record("old", created_at="2026-05-17T23:59:59.000Z"),
        feedback_record("day", created_at="2026-05-18T12:00:00.000Z"),
        feedback_record("next", created_at="2026-05-19T00:00:00.000Z"),
    ]
    write_fixture_records(local_dir, records)

    date_run = run_export(
        tmp_path,
        local_dir,
        "date_only",
        "--since",
        "2026-05-18",
        "--until",
        "2026-05-18",
    )
    assert {row["id"] for row in read_jsonl(date_run / "feedback_records.jsonl")} == {"day"}

    iso_run = run_export(
        tmp_path,
        local_dir,
        "iso",
        "--since",
        "2026-05-18T12:00:00Z",
        "--until",
        "2026-05-19T00:00:00Z",
    )
    assert {row["id"] for row in read_jsonl(iso_run / "feedback_records.jsonl")} == {
        "day",
        "next",
    }


def test_source_type_status_and_route_filters_work_independently_and_together(
    tmp_path: Path,
):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record(
            "a",
            feedback_source="user_submitted",
            feedback_type="wrong_answer",
            status="ok",
            route="season_leaders",
        ),
        feedback_record(
            "b",
            feedback_source="automatic",
            feedback_type="unsupported",
            status="no_result",
            route="season_leaders",
        ),
        feedback_record(
            "c",
            feedback_source="user_submitted",
            feedback_type="ui_issue",
            status="error",
            route="player_game_summary",
        ),
        feedback_record(
            "d",
            feedback_source="automatic",
            feedback_type="other",
            status="ok",
            route="player_game_summary",
        ),
    ]
    write_fixture_records(local_dir, records)

    assert exported_ids(tmp_path, local_dir, "source", "--source", "automatic") == {"b", "d"}
    assert exported_ids(tmp_path, local_dir, "type", "--feedback-type", "ui_issue") == {"c"}
    assert exported_ids(tmp_path, local_dir, "status", "--status", "no_result") == {"b"}
    assert exported_ids(tmp_path, local_dir, "route", "--route", "player_game_summary") == {
        "c",
        "d",
    }
    assert exported_ids(
        tmp_path,
        local_dir,
        "combined",
        "--source",
        "user_submitted",
        "--feedback-type",
        "wrong_answer",
        "--status",
        "ok",
        "--route",
        "season_leaders",
    ) == {"a"}


def test_mocked_r2_mode_uses_only_read_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    record = feedback_record("r2_record")
    client = FakeR2Client(
        {"query_feedback/preview/2026/05/18/r2_record.json": json.dumps(record).encode("utf-8")}
    )

    def fake_load_r2_config(env=None):
        return R2Config(
            account_id="account",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name=(env or {})["R2_BUCKET_NAME"],
        )

    monkeypatch.setattr(query_feedback_review.data_source, "load_r2_config", fake_load_r2_config)
    monkeypatch.setattr(
        query_feedback_review.data_source, "create_r2_client", lambda config: client
    )

    run_dir = tmp_path / "exports" / "r2"
    exit_code = export_query_feedback.main(
        [
            "--bucket",
            "nbatools-data",
            "--prefix",
            "query_feedback/preview",
            "--output-dir",
            str(tmp_path / "exports"),
            "--run-id",
            "r2",
        ]
    )

    assert exit_code == 0
    assert (run_dir / "feedback_records.jsonl").exists()
    assert client.list_calls == [{"Bucket": "nbatools-data", "Prefix": "query_feedback/preview"}]
    assert client.get_calls == [
        {"Bucket": "nbatools-data", "Key": "query_feedback/preview/2026/05/18/r2_record.json"}
    ]
    assert client.mutation_calls == []


def feedback_record(record_id: str, **overrides: Any) -> dict[str, Any]:
    record = {
        "id": record_id,
        "created_at": "2026-05-18T12:00:00.000Z",
        "schema_version": 1,
        "feedback_source": "user_submitted",
        "feedback_type": "wrong_answer",
        "query": f"Query for {record_id}",
        "query_normalized_hash": f"hash_{record_id}",
        "source_page": "/",
        "environment": "preview",
        "deployment": {
            "vercel_url": "preview.example",
            "vercel_git_commit_sha": "abc123",
        },
        "route": "season_leaders",
        "status": "ok",
        "reason": None,
        "metadata": {"route": "season_leaders", "unsupported_filters": []},
        "result_shape": {
            "query_class": "leaderboard",
            "section_keys": ["leaderboard"],
            "section_row_counts": {"leaderboard": 3},
        },
        "notes": ["note"],
        "caveats": [],
        "user_note": None,
        "answer_text_preview": "Answer preview",
        "error_message": None,
        "elapsed_ms": 100,
        "review_status": "new",
        "triage_decision": None,
    }
    record.update(overrides)
    return record


def write_fixture_records(local_dir: Path, records: list[dict[str, Any]]) -> None:
    local_dir.mkdir(parents=True)
    for index, record in enumerate(records):
        (local_dir / f"{index:02d}_{record['id']}.json").write_text(json.dumps(record))


def run_export(tmp_path: Path, local_dir: Path, run_id: str, *extra_args: str) -> Path:
    output_dir = tmp_path / "exports"
    exit_code = export_query_feedback.main(
        [
            "--local-dir",
            str(local_dir),
            "--output-dir",
            str(output_dir),
            "--run-id",
            run_id,
            *extra_args,
        ]
    )
    assert exit_code == 0
    return output_dir / run_id


def exported_ids(tmp_path: Path, local_dir: Path, run_id: str, *args: str) -> set[str]:
    run_dir = run_export(tmp_path, local_dir, run_id, *args)
    return {row["id"] for row in read_jsonl(run_dir / "feedback_records.jsonl")}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeR2Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.list_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []
        self.mutation_calls: list[str] = []

    def list_objects_v2(self, **kwargs):
        self.list_calls.append(kwargs)
        prefix = kwargs.get("Prefix", "")
        return {
            "Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(prefix)],
            "IsTruncated": False,
        }

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"Body": FakeBody(self.objects[kwargs["Key"]])}

    def put_object(self, **kwargs):
        self.mutation_calls.append("put_object")
        raise AssertionError("exporter must not write R2 objects")

    def delete_object(self, **kwargs):
        self.mutation_calls.append("delete_object")
        raise AssertionError("exporter must not delete R2 objects")

    def copy_object(self, **kwargs):
        self.mutation_calls.append("copy_object")
        raise AssertionError("exporter must not copy R2 objects")
