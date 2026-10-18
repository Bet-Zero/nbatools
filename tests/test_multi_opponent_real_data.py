"""Independent CSV oracle checks exact selected rows before answer arithmetic."""

import json
from pathlib import Path

import pytest

from nbatools.commands import player_compare, team_compare, team_record, team_split_summary
from nbatools.query_service import execute_natural_query, execute_structured_query

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


def test_comparison_opponent_union(monkeypatch):
    oracle = json.loads(
        (
            Path(__file__).parent / "fixtures/multi_opponent/comparison-primary-oracle.json"
        ).read_text()
    )
    captured = []
    for case in oracle["cases"]:
        captured.clear()
        player = case["kind"] == "player"
        module = player_compare if player else team_compare
        attr = "summarize_player" if player else "summarize_team"
        summarize = getattr(module, attr)

        def capture(frame, *args, **kwargs):
            captured.append(frame.copy())
            return summarize(frame, *args, **kwargs)

        monkeypatch.setattr(module, attr, capture)
        names = [sample["name"] for sample in case["summaries"]] if player else case["entities"]
        entities = {f"{case['kind']}_a": names[0], f"{case['kind']}_b": names[1]}
        results = [
            execute_natural_query(case["query"]),
            execute_structured_query(
                case["kind"] + "_compare",
                **entities,
                opponent=case["opponents"],
                season="2023-24",
            ),
        ]
        assert len(captured) == 4
        for result, frames in zip(results, (captured[:2], captured[2:])):
            assert result.result_status == "ok", result.metadata
            assert result.metadata["opponents"] == case["opponents"]
            assert result.metadata["opponent"] == ", ".join(case["opponents"])
            assert not result.metadata.get("opponent_context")
            if player:
                assert [c["player_id"] for c in result.metadata["players_context"]] == case[
                    "entities"
                ]
                assert result.metadata["team"] is None
            else:
                assert {c["team_abbr"] for c in result.metadata["teams_context"]} == set(
                    case["entities"]
                )
            rows = result.result.to_dict()["sections"]["summary"]
            assert len(rows) == len(case["summaries"])
            for row, frame, expected in zip(rows, frames, case["summaries"]):
                assert (
                    sorted(
                        frame[
                            ["game_id", "team_id", "opponent_team_id"]
                            + (["player_id"] if player else [])
                        ]
                        .astype(int)
                        .values.tolist()
                    )
                    == expected["keys"]
                )
                assert row["player_name" if player else "team_name"] == (
                    expected["name"] if player else expected["entity"]
                )
                for field in ("games", "wins", "losses"):
                    assert row[field] == expected[field]
                for stat in ("pts", "reb", "ast"):
                    assert int(frame[stat].sum()) == expected["sums"][stat]
                    assert row[stat + "_sum"] == expected["sums"][stat]
                    assert row[stat + "_avg"] == pytest.approx(
                        expected["sums"][stat] / expected["games"], abs=0.001
                    )


def test_head_to_head_opponent_intersection(monkeypatch):
    oracle = json.loads(
        (Path(__file__).parent / "fixtures/multi_opponent/head-to-head-oracle.json").read_text()
    )
    captured = []
    summarize = team_compare.summarize_team

    def capture(frame, *args, **kwargs):
        captured.append(frame.copy())
        return summarize(frame, *args, **kwargs)

    monkeypatch.setattr(team_compare, "summarize_team", capture)
    for case in oracle["cases"]:
        captured.clear()
        result = execute_structured_query(
            "team_compare",
            team_a="LAL",
            team_b="NYK",
            head_to_head=True,
            season="2023-24",
            opponent=case["opponent"],
        )
        if not case["paired_keys"]:
            assert result.result_status == "no_result" and result.result_reason == "no_match"
            assert captured == []
            continue
        assert result.result_status == "ok"
        assert len(captured) == 2
        actual = [
            key
            for frame in captured
            for key in frame[["game_id", "team_id", "opponent_team_id"]].astype(int).values.tolist()
        ]
        assert sorted(actual) == case["paired_keys"]
        rows = result.result.to_dict()["sections"]["summary"]
        assert len(rows) == 2
        for row, frame, expected in zip(rows, captured, case["summaries"]):
            assert row["team_name"] == expected["team"]
            assert (row["games"], row["wins"], row["losses"]) == (
                expected["games"],
                expected["wins"],
                expected["games"] - expected["wins"],
            )
            for stat in ("pts", "reb", "ast"):
                assert int(frame[stat].sum()) == row[stat + "_sum"] == expected["sums"][stat]
