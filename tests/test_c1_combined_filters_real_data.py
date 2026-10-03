"""C1 combined filters against the real 1996-97+ game rows.

Companion to ``test_combined_filters.py`` (fixture). Expected values are
counted from the raw game rows of the pinned generation with plain pandas
filters, never from the code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASON = "2023-24"


def _games(kind: str, column: str, value: str) -> pd.DataFrame:
    frame = data_read_csv(f"raw/{kind}/{SEASON}_regular_season.csv", dtype={"game_id": str})
    frame = frame[frame[column] == value].copy()
    if kind == "player_game_stats":
        # Player rows may omit the game result and venue; take them from the
        # player's team row for the same game.
        teams = data_read_csv(
            f"raw/team_game_stats/{SEASON}_regular_season.csv", dtype={"game_id": str}
        )[["game_id", "team_id", "wl", "is_home"]]
        frame = frame.drop(columns=["wl", "is_home"], errors="ignore").merge(
            teams, on=["game_id", "team_id"], how="left"
        )
    for stat in ("pts", "reb", "ast", "plus_minus"):
        if stat in frame.columns:
            frame[stat] = pd.to_numeric(frame[stat], errors="coerce")
    frame["home"] = frame["is_home"].astype(str).str.lower().isin({"1", "true", "1.0"})
    frame["won"] = frame["wl"].eq("W")
    return frame


def _lebron() -> pd.DataFrame:
    return _games("player_game_stats", "player_name", "LeBron James")


def _curry() -> pd.DataFrame:
    return _games("player_game_stats", "player_name", "Stephen Curry")


def _team(abbr: str) -> pd.DataFrame:
    games = _games("team_game_stats", "team_abbr", abbr)
    every = data_read_csv(
        f"raw/team_game_stats/{SEASON}_regular_season.csv", dtype={"game_id": str}
    )
    opponent = every[every["team_abbr"] != abbr][["game_id", "team_abbr", "pts"]]
    opponent = opponent.rename(columns={"team_abbr": "opponent_team_abbr", "pts": "opp_pts"})
    games = games.merge(opponent, on=["game_id", "opponent_team_abbr"], how="left")
    games["opp_pts"] = pd.to_numeric(games["opp_pts"], errors="coerce")
    return games


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _sections(result) -> dict:
    return result.result.to_dict()["sections"]


def _assert_rows(row: dict, games: pd.DataFrame) -> None:
    assert row["games"] == len(games)
    assert row["wins"] == int(games["won"].sum())
    assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


def test_home_away_split_inside_wins():
    games = _lebron()
    games = games[games["won"]]
    buckets = {
        row["bucket"]: row
        for row in _sections(_run(f"LeBron home away split in wins {SEASON}"))["split_comparison"]
    }
    _assert_rows(buckets["home"], games[games["home"]])
    _assert_rows(buckets["away"], games[~games["home"]])


def test_home_away_split_when_scoring_30():
    games = _lebron()
    games = games[games["pts"] >= 30]
    buckets = {
        row["bucket"]: row
        for row in _sections(_run(f"LeBron home away splits when scoring 30 {SEASON}"))[
            "split_comparison"
        ]
    }
    _assert_rows(buckets["home"], games[games["home"]])
    _assert_rows(buckets["away"], games[~games["home"]])


def test_summary_keeps_both_stat_conditions():
    games = _lebron()
    games = games[(games["reb"] >= 8) & (games["ast"] >= 8)]
    (summary,) = _sections(
        _run(f"LeBron averages in games with 8+ rebounds and 8+ assists {SEASON}")
    )["summary"]
    _assert_rows(summary, games)


def test_team_record_keeps_points_scored_and_allowed():
    games = _team("LAL")
    games = games[(games["pts"] >= 120) & (games["opp_pts"] < 110)]
    (summary,) = _sections(_run(f"Lakers record when scoring 120 and allowing under 110 {SEASON}"))[
        "summary"
    ]
    assert summary["games"] == len(games)
    assert summary["wins"] == int(games["won"].sum())


def test_player_comparison_applies_the_condition_to_both_players():
    result = _run(f"LeBron vs Curry when scoring 30 {SEASON}")
    assert result.route == "player_compare"
    a, b = _sections(result)["summary"]
    for side, games in ((a, _lebron()), (b, _curry())):
        _assert_rows(side, games[games["pts"] >= 30])


def test_team_comparison_with_two_conditions():
    result = _run(f"compare Lakers and Celtics when scoring 120 and allowing under 110 {SEASON}")
    assert result.route == "team_compare"
    a, b = _sections(result)["summary"]
    for side, abbr in ((a, "LAL"), (b, "BOS")):
        games = _team(abbr)
        games = games[(games["pts"] >= 120) & (games["opp_pts"] < 110)]
        _assert_rows(side, games)


def test_bare_stat_joined_to_scoring_is_kept():
    games = _curry()
    games = games[(games["pts"] >= 30) & (games["ast"] >= 5)]
    (summary,) = _sections(
        _run(f"Curry averages in games scoring 30 points and 5 assists {SEASON}")
    )["summary"]
    _assert_rows(summary, games)
