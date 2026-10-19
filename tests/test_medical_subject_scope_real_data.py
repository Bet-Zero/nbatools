"""Real played/sample facts stay distinct from unqualified medical status."""

import csv
import hashlib
import json
from functools import wraps
from pathlib import Path

import pytest

from nbatools.commands import player_compare, team_record
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]
ROOT = Path(__file__).parent / "fixtures/medical_subject_scope"
SOURCE = json.loads((ROOT / "source_facts.json").read_text())
BASELINE = json.loads((ROOT / "baseline_and_compatibility.json").read_text())
CASES = {c["id"]: c for c in BASELINE["baselines"][-1]["cases"]}


def authenticate():
    assert (
        hashlib.sha256((ROOT / "source_facts.json").read_bytes()).hexdigest()
        == "a96da8646a6d5323f9d14b455c0ad89fdc1eb4285f0b9d47f41939c400e6e615"
    )
    assert (
        hashlib.sha256((ROOT / "route_consumer_contract.json").read_bytes()).hexdigest()
        == "d1f6aa6ff8fc53becf6601cdba908fe6c1f7bfe363b24d1a591a7f7a27324189"
    )
    for path, sha in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == sha
    control = SOURCE["qualified_played_control"]
    for kind, rows in [
        ("games", control["catalog_rows"]),
        ("team_game_stats", control["reciprocal_rows"]),
        ("player_game_stats", control["player_rows"]),
        ("player_game_availability", control["report_rows"]),
    ]:
        raw = list(csv.DictReader(data_path(f"raw/{kind}/2025-26_regular_season.csv").open()))
        assert all(row in raw for row in rows)
    assert {row["game_id"] for row in control["report_rows"]} == {"0022500338", "0022500823"}
    assert all(
        row["player_id"] == "1628401"
        and row["team_id"] == "1610612738"
        and row["participation_state"] == "played"
        for row in control["report_rows"]
    )


def assert_unavailable(result, route):
    assert result.route == route and result.result_status == "no_result", result.metadata
    assert result.result_reason == "filter_not_supported"
    assert not result.result.to_dict()["sections"] and not result.metadata.get("answer_phrase")
    assert not result.metadata.get("applied_filters")
    assert not result.metadata.get("with_player") and not result.metadata.get("without_player")
    assert "availability_status" in result.metadata["unsupported_filters"]
    assert result.metadata["unsupported_availability"]["condition"]


@pytest.mark.parametrize(
    "id",
    [
        "primary_team_medical",
        "prefix_team_medical",
        "team_healthy",
        "prefix_team_healthy",
        "team_questionable",
        "unknown_status_owner",
        "negative_medical",
        "injury_status",
    ],
)
def test_status_condition_never_returns_white_or_unfiltered_team_arithmetic(id, monkeypatch):
    authenticate()
    from nbatools.commands import _natural_query_execution as execution

    def forbidden(**kwargs):
        pytest.fail("Medical/status condition executed a reduced numerical request")

    monkeypatch.setitem(execution._get_build_result_map(), "team_record", forbidden)
    result = execute_natural_query(CASES[id]["query"])
    assert_unavailable(result, "team_record")
    assert result.metadata["team_context"]["team_id"] == 1610612738
    assert result.metadata["opponent_context"]["team_id"] == 1610612747
    assert result.metadata["season"] == "2025-26"
    assert result.metadata.get("player") is None and result.metadata.get("player_context") is None
    assert parse_query(CASES[id]["query"])["player"] is None
    assert result.query == CASES[id]["query"]


@pytest.mark.parametrize(
    "id",
    [
        "primary_comparison_medical",
        "prefix_comparison_medical",
        "comparison_healthy",
        "comparison_other_owner",
    ],
)
def test_unavailable_condition_keeps_both_actual_primary_comparison_identities(id):
    authenticate()
    result = execute_natural_query(CASES[id]["query"])
    assert_unavailable(result, "player_compare")
    assert parse_query(result.query)["player"] is None
    assert result.metadata["player"] == "Joel Embiid, Nikola Jokić"
    assert result.metadata["players_context"] == [
        {"player_id": 203954, "player_name": "Joel Embiid"},
        {"player_id": 203999, "player_name": "Nikola Jokić"},
    ]
    assert result.metadata["opponent_context"]["team_id"] == 1610612752
    assert result.metadata["season"] == "2023-24"


def test_player_primary_summary_target_survives_unavailable_status():
    authenticate()
    result = execute_natural_query(CASES["player_summary_medical"]["query"])
    assert_unavailable(result, "player_game_summary")
    assert result.metadata["player_context"]["player_id"] == 203954
    assert result.metadata["player"] == "Joel Embiid"


def test_empty_statistical_candidate_cannot_establish_medical_qualification():
    authenticate()
    result = execute_natural_query(
        "Boston record against Lakers in 2025-26 with under 0 points when Derrick White is medically cleared"
    )
    assert_unavailable(result, "team_record")
    assert result.metadata["team"] == "BOS" and result.metadata.get("player") is None


@pytest.mark.parametrize("id", ["team_played_positive", "team_unfiltered_positive"])
def test_qualified_played_and_unfiltered_team_samples_remain_original_source_games(id, monkeypatch):
    authenticate()
    captured = []
    compute = team_record._compute_record

    @wraps(compute)
    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    result = execute_natural_query(CASES[id]["query"])
    assert result.route == "team_record" and result.result_status == "ok", result.metadata
    body = result.result.to_dict()["sections"]
    assert body["summary"][0]["games"] == 2
    assert body["summary"][0]["wins"] == 2 and body["summary"][0]["losses"] == 0
    rows = captured[0].to_dict("records")
    assert captured
    expected = SOURCE["qualified_played_control"]["team_rows"]

    def key(r):
        return (
            int(r["game_id"]),
            str(r["game_date"])[:10],
            int(r["team_id"]),
            int(r["opponent_team_id"]),
        )

    assert {key(r) for r in rows} == {key(r) for r in expected}
    for stat in ("pts", "reb", "ast"):
        total = sum(int(r[stat]) for r in expected)
        assert (
            total
            == sum(r[stat] for r in rows)
            == SOURCE["qualified_played_control"]["totals"][stat]
        )
        assert body["summary"][0][stat + "_avg"] == total / 2
    assert not result.metadata.get("unsupported_availability")
    assert result.metadata.get("with_player") == (
        "Derrick White" if id == "team_played_positive" else None
    )


def test_unfiltered_comparison_keeps_independent_observed_samples(monkeypatch):
    authenticate()
    captured = []
    compute = player_compare.summarize_player

    @wraps(compute)
    def capture(frame, *args, **kwargs):
        captured.append(frame.copy())
        return compute(frame, *args, **kwargs)

    monkeypatch.setattr(player_compare, "summarize_player", capture)
    result = execute_natural_query(CASES["comparison_unfiltered_positive"]["query"])
    assert result.route == "player_compare" and result.result_status == "ok"
    raw = list(csv.DictReader(data_path("raw/player_game_stats/2023-24_regular_season.csv").open()))
    samples = SOURCE["unfiltered_comparison_control"]["samples"]
    assert all(r in raw for s in samples for r in s["selected_rows"])
    assert len(captured) == 2
    for frame, row, sample in zip(
        captured, result.result.to_dict()["sections"]["summary"], samples
    ):
        assert sorted(frame.game_id.astype(int)) == sorted(int(g) for g in sample["game_ids"])
        assert set(frame.player_id.astype(int)) == {int(sample["player_id"])}
        assert set(frame.opponent_team_id.astype(int)) == {1610612752}
        assert row["games"] == sample["games"]
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_sum"] == frame[stat].sum() == sample["totals"][stat]
    assert not result.metadata.get("unsupported_availability")
