"""Source-frozen original matchup minutes use PDF seconds, not rounded CSV MIN."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
FIXTURE = Path(__file__).parent / "fixtures/qualified_original_minutes/source_and_baseline.json"
SOURCE = json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("case", SOURCE["obligations"][:7], ids=lambda c: c["id"])
def test_qualified_original_minutes_source_obligations(case):
    assert (
        hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        == "f95253c6d2bda90c8d9ff2c908d479f7a404bcdc0be62f3b4b7d2d5d1ecb26ad"
    )
    for path, sha in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == sha
    facts = SOURCE["source_games"][case["source_game_ref"]]
    for kind, key in [
        ("games", "catalog_rows"),
        ("team_game_stats", "team_rows"),
        ("player_game_stats", "target_positive_appearance_rows"),
        ("player_game_availability", "target_observation_rows"),
    ]:
        with data_path(f"raw/{kind}/{facts['season']}_regular_season.csv").open() as stream:
            raw = list(csv.DictReader(stream))
        for expected in facts[key]:
            assert expected in raw
    result = execute_natural_query(case["query"])
    assert result.route == "game_finder"
    assert result.result_status == case["expected_status"]
    assert result.result_reason == case["expected_reason"]
    assert result.metadata["player_context"]["player_id"] == case["player_id"]
    assert set(result.metadata["player_context"]) == {"player_id", "player_name"}
    assert result.metadata["stat"] is None and not result.metadata["threshold_conditions"]
    assert result.metadata["min_value"] is None and result.metadata["max_value"] is None
    assert not result.metadata["with_player"] and not result.metadata["without_player"]
    filters = result.metadata["applied_filters"]
    if case["desired_boolean"] is None:
        assert not result.metadata.get("answer_phrase")
        assert not result.result.to_dict()["sections"]
        assert not any(f["label"] == "Minutes check" for f in filters)
        return
    truth = case["desired_boolean"]
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith("Yes:" if truth else "No:")
    assert "2024-02-01" in phrase
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == case["original_team_game_id"]
    row = rows[0]
    assert not any(k in row for k in ("player_name", "player_id", "player"))
    own = next(r for r in facts["team_rows"] if r["team_abbr"] == result.metadata["team"])
    assert int(own["team_id"]) == row["team_id"]
    assert int(own["opponent_team_id"]) == row["opponent_team_id"]
    assert str(row["game_date"])[:10] == own["game_date"]
    assert [row[k] for k in ("pts", "reb", "ast")] == [int(own[k]) for k in ("pts", "reb", "ast")]
    time = next(
        (t for t in facts["pdf_elapsed_time_arithmetic"] if t["player_id"] == case["player_id"]),
        None,
    )
    if time:
        assert time["elapsed_seconds"] == 60 * time["minute_component"] + time["second_component"]
        assert abs(float(time["source_minutes_string"]) * 60 - time["elapsed_seconds"]) < 1e-8
        assert time["pdf_time"] in phrase
        observation = next(
            r for r in facts["target_observation_rows"] if int(r["player_id"]) == case["player_id"]
        )
        appearance = next(
            r
            for r in facts["target_positive_appearance_rows"]
            if int(r["player_id"]) == case["player_id"]
        )
        assert observation["team_id"] == appearance["team_id"]
        assert observation["game_date"] == appearance["game_date"] == own["game_date"]
    else:
        assert "did not play" in phrase and "played 0:" not in phrase
        assert not any(
            int(r["player_id"]) == case["player_id"]
            for r in facts["target_positive_appearance_rows"]
        )
    assert any(
        f["label"] == "Minutes check" and f["value"].startswith(result.metadata["player"])
        for f in filters
    )
    assert not any(f["label"] in ("Played check", "With player", "Without player") for f in filters)
    assert any("team-game totals" in c and "MM:SS" in c for c in result.result.caveats)


@pytest.mark.parametrize(
    "bound,truth",
    [
        ("over 36.6166 minutes", True),
        ("under 36.6167 minutes", True),
        ("at least 36.6167 minutes", False),
        ("at most 36.6166 minutes", False),
    ],
)
def test_report_second_near_decimal_bound_uses_operator_inclusivity(bound, truth):
    # Source above independently freezes Feb1 Tatum36:37 (2197 seconds).
    result = execute_natural_query(
        f"Did Tatum play {bound} in the Celtics last game against Lakers in 2023-24?"
    )
    assert result.result_status == "ok" and result.route == "game_finder"
    assert result.metadata["answer_phrase"].startswith("Yes:" if truth else "No:")
    assert "played 36:37" in result.metadata["answer_phrase"]
    assert result.metadata["player_context"]["player_id"] == 1628369
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == 22300684
    assert rows[0]["team_id"] == 1610612738 and rows[0]["opponent_team_id"] == 1610612747


@pytest.mark.parametrize(
    "query,minutes",
    [
        (
            "Did Jayson Tatum play at least 30 minutes in the Celtics last game against Lakers during the 2023-24 regular season?",
            True,
        ),
        (
            "For the Celtics latest meeting against Lakers during the 2023-24 regular season, did Tatum play at least 30 minutes?",
            True,
        ),
        (
            "Did Tatum play in the Celtics last game against Lakers during the 2023-24 regular season?",
            False,
        ),
        (
            "For the Celtics latest meeting against Lakers during the 2023-24 regular season, did both Tatum and Reaves play?",
            False,
        ),
    ],
)
def test_explicit_regular_season_original_scope_and_adjacent_played_source(query, minutes):
    result = execute_natural_query(query)
    assert result.result_status == "ok" and result.route == "game_finder"
    assert result.metadata["answer_phrase"].startswith("Yes:")
    assert "2024-02-01" in result.metadata["answer_phrase"]
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == 22300684
    assert rows[0]["team_id"] == 1610612738 and rows[0]["opponent_team_id"] == 1610612747
    if minutes:
        assert "played 36:37" in result.metadata["answer_phrase"]
        assert result.metadata["player_context"]["player_id"] == 1628369
    label = "Minutes check" if minutes else "Played check"
    assert any(f["label"] == label for f in result.metadata["applied_filters"])
