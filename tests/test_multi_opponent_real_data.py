"""Independent CSV oracle checks exact selected rows before answer arithmetic."""

import json
from pathlib import Path

import pytest

from nbatools.commands import team_record, team_split_summary
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_multi_opponent_subject_rows_and_labels(monkeypatch):
    oracle = json.loads(
        (Path(__file__).parent / "fixtures/multi_opponent/primary-oracle.json").read_text()
    )
    captured = []
    record = team_record._compute_record
    bucket = team_split_summary._summarize_bucket

    def capture_record(frame):
        captured.append(("all", frame.copy()))
        return record(frame)

    def capture_bucket(frame, name):
        captured.append((name, frame.copy()))
        return bucket(frame, name)

    monkeypatch.setattr(team_record, "_compute_record", capture_record)
    monkeypatch.setattr(team_split_summary, "_summarize_bucket", capture_bucket)
    for case in oracle["cases"]:
        queries = [case["query"]]
        if case["operation"] == "record":
            queries += [
                "What was New York’s away record against Miami and Washington in 2023-24?",
                "Against Miami and Washington, what was New York’s away record in 2023-24?",
            ]
        for query in queries:
            captured.clear()
            result = execute_natural_query(query)
            assert result.result_status == "ok", (query, result.metadata)
            meta = result.metadata
            assert meta["team"] == case["subject"]
            assert meta["team_context"]["team_id"] == case["subject_id"]
            assert meta["opponents"] == case["opponents"]
            assert meta["opponent"] == ", ".join(case["opponents"])
            assert not meta.get("opponent_context")
            assert {"label": "Opponent", "kind": "team", "value": meta["opponent"]} in meta[
                "applied_filters"
            ]
            sections = result.result.to_dict()["sections"]
            rows = sections.get("split_comparison", sections.get("summary"))
            assert len(rows) == len(case["buckets"])
            assert len(captured) >= len(rows)
            for row, expected, (name, frame) in zip(rows, case["buckets"], captured):
                assert name == expected["bucket"]
                assert (
                    sorted(
                        frame[["game_id", "team_id", "opponent_team_id"]]
                        .astype(int)
                        .values.tolist()
                    )
                    == expected["keys"]
                )
                assert set(frame.season) <= set(case["seasons"])
                for field in ("games", "wins", "losses"):
                    assert row[field] == expected[field]
                for stat in ("pts", "reb", "ast"):
                    assert int(frame[stat].sum()) == expected["sums"][stat]
                    assert row[stat + "_avg"] == pytest.approx(expected["means"][stat], abs=0.001)
