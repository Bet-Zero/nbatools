"""Pair questions that used to drop a team or a filter.

"Lakers and Nuggets series history" is their playoff matchup history,
"Lakers and Celtics leading scorers" ranks both rosters, "LeBron vs Curry
against winning teams" compares both players against the bar, and "the best
teams" is an opponent-quality term. Expected values come from the fixture.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


@pytest.mark.parametrize(
    "query",
    [
        "Lakers and Nuggets series history",
        "Lakers vs Nuggets series history",
        "Lakers and Nuggets playoff history",
    ],
)
def test_pair_series_history_is_their_playoff_history(query):
    expected = _run("Lakers Nuggets playoff history")
    result = _run(query)
    assert result.route == "playoff_matchup_history"
    assert result.result.to_dict()["sections"] == expected.result.to_dict()["sections"]


def test_pair_series_record_stays_the_season_series():
    assert _run("Lakers and Celtics series record").route == "team_matchup_record"


def test_pair_leading_scorers_rank_both_rosters():
    rows = _csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    totals: dict[str, list[int]] = {}
    for row in rows:
        if row["team_abbr"] in {"LAL", "BOS"}:
            totals.setdefault(row["player_name"], []).append(int(row["pts"]))
    expected = sorted(totals, key=lambda name: -sum(totals[name]) / len(totals[name]))[:3]

    result = _run("Lakers and Celtics leading scorers")
    leaders = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_abbr"] for row in leaders} == {"LAL", "BOS"}
    assert [row["player_name"] for row in leaders[:3]] == expected
    assert result.metadata["team"] == "LAL, BOS"


def _winning(season: str) -> set[str]:
    rows = _csv(RAW / "standings_snapshots" / f"{season}_regular_season.csv")
    return {r["team_id"] for r in rows if float(r["win_pct"]) >= 0.5}


@pytest.mark.parametrize(
    "query",
    ["LeBron vs Curry against winning teams", "compare LeBron and Curry vs winning teams"],
)
def test_player_pair_against_winning_teams(query):
    rows = _csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    winning = _winning("2025-26")
    lebron, curry = _run(query).result.to_dict()["sections"]["summary"]
    for side, name in ((lebron, "LeBron James"), (curry, "Stephen Curry")):
        games = [r for r in rows if r["player_name"] == name and r["opponent_team_id"] in winning]
        assert side["games"] == len(games)


@pytest.mark.parametrize(
    "query", ["LeBron vs Curry against the Celtics", "compare LeBron and Curry vs the Celtics"]
)
def test_player_pair_against_a_team(query):
    rows = _csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    result = _run(query)
    assert result.route == "player_compare"
    lebron, curry = result.result.to_dict()["sections"]["summary"]
    for side, name in ((lebron, "LeBron James"), (curry, "Stephen Curry")):
        games = [r for r in rows if r["player_name"] == name and r["opponent_team_abbr"] == "BOS"]
        assert side["games"] == len(games)


def test_the_best_teams_is_opponent_quality():
    result = _run("Lakers record vs the best teams")
    kinds = {f["kind"] for f in result.metadata["applied_filters"]}
    assert "quality" in kinds


def test_player_pair_typo_still_refuses():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("lebron vs cury against winning teams")
    assert result.result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "opponent"),
    [
        ("LeBron vs Curry's Warriors", "GSW"),
        ("LeBron vs Steph's Warriors", "GSW"),
        ("Curry vs LeBron's Lakers", "LAL"),
    ],
)
def test_possessive_team_after_vs_is_the_opponent(query, opponent):
    result = _run(query)
    assert result.route == "player_game_finder"
    assert result.result_status == "ok"
    assert opponent in str(result.metadata.get("opponent_team_abbrs") or result.metadata)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers and Nuggets playoff record",
        "Lakers vs Nuggets in the playoffs record",
        "Lakers vs Nuggets postseason record",
    ],
)
def test_pair_playoff_record_covers_every_meeting(query):
    result = _run(query)
    assert result.route == "playoff_matchup_history"
    notes = " ".join(result.metadata.get("notes") or [])
    assert "defaulted to the" not in notes
    lakers = result.result.to_dict()["sections"]["summary"][0]
    assert (lakers["wins"], lakers["losses"]) == (5, 1)
    # The season chip reads metadata, so it must show the window that ran.
    assert result.metadata.get("season") is None
    assert result.metadata.get("start_season") == "1996-97"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers vs Nuggets playoff record this postseason",
        "Lakers vs Nuggets playoff record these playoffs",
        "Lakers vs Nuggets playoff record 2026",
    ],
)
def test_pair_playoff_record_keeps_a_named_window(query):
    result = _run(query)
    assert result.route == "playoff_matchup_history"
    assert result.metadata.get("season") == "2025-26"
    assert not result.metadata.get("start_season")
