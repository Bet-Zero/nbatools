"""Stat ranges, two-digit seasons, "N total points" and a player's season totals.

These read wrong or not at all: "25-30 points" kept only the 30 floor (or
dropped the range), "15-16" and "2024–25" fell back to the default season,
"Mavericks games with 130 total points" dropped the 130, "players with a total
of 2000 points" did not parse and "how many times has LeBron scored 2000 points
in a season" counted single games. Expected values are read straight from the
fixture's box-score rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _players(season: str) -> pd.DataFrame:
    return pd.read_csv(RAW / "player_game_stats" / f"{season}_regular_season.csv")


def _teams(season: str) -> pd.DataFrame:
    return pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")


def _sections(query: str) -> dict:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_status, result.result_reason)
    return result.result.to_dict()["sections"]


def _finder_ids(query: str) -> set[int]:
    return {int(row["game_id"]) for row in _sections(query)["finder"]}


def _kwargs(query: str) -> dict:
    return parse_query(query)["route_kwargs"]


# ── ranges ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("query", "player", "stat", "low", "high"),
    [
        ("LeBron games with 25-30 points", "LeBron James", "pts", 25, 30),
        ("LeBron 25 to 30 points", "LeBron James", "pts", 25, 30),
        ("Luka 25-30 point games", "Luka Dončić", "pts", 25, 30),
        ("Luka games between 25-30 points", "Luka Dončić", "pts", 25, 30),
        ("Jokic games with 10–15 rebounds", "Nikola Jokić", "reb", 10, 15),
        ("Curry games with 5-7 threes", "Stephen Curry", "fg3m", 5, 7),
        # A two-digit pair after "with" is a range, not the 2015-16 season.
        ("LeBron games with 15-16 points", "LeBron James", "pts", 15, 16),
        # Not a season: an adjective game list, a pair no season has, a
        # "<stat> games" list.
        ("LeBron 21-22 point games", "LeBron James", "pts", 21, 22),
        ("LeBron 31-32 point games", "LeBron James", "pts", 31, 32),
        ("LeBron 5-10 assists games", "LeBron James", "ast", 5, 10),
    ],
)
def test_player_stat_range_is_both_bounds(query, player, stat, low, high):
    games = _players("2025-26")
    games = games[games["player_name"].eq(player) & games[stat].between(low, high)]
    rows = _sections(query)["finder"]
    # A game list shows its first 25 games, highest first.
    assert all(low <= row[stat] <= high for row in rows)
    assert {int(row["game_id"]) for row in rows} <= set(games["game_id"])
    assert len(rows) == min(len(games), 25)


def test_team_points_range():
    teams = _teams("2025-26")
    lal = teams[teams["team_abbr"].eq("LAL") & teams["pts"].between(110, 120)]
    assert _finder_ids("Lakers games with 110-120 points") == set(lal["game_id"])


def test_range_count_counts_the_range_games():
    games = _players("2025-26")
    luka = games[games["player_name"].eq("Luka Dončić") & games["pts"].between(25, 30)]
    sections = _sections("how many 25-30 point games does Luka have")
    assert sections["count"] == [{"count": len(luka)}]


def test_margin_range_stays_a_margin():
    kwargs = _kwargs("Lakers wins by 10-15 points")
    assert (kwargs["stat"], kwargs["min_value"], kwargs["max_value"]) == ("win_margin", 10, 15)


# ── two-digit and dashed seasons ────────────────────────────────────────


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("LeBron points 15-16", "2015-16"),
        ("Curry stats in 15-16", "2015-16"),
        ("Lakers record 09-10", "2009-10"),
        ("Lakers 15-16 record", "2015-16"),
        ("Celtics record in 99-00", "1999-00"),
        ("LeBron points 2024–25", "2024-25"),
        ("LeBron 2024/25 stats", "2024-25"),
        # "15-16 points" without "with" names the season, as "2015-16 points" does.
        ("LeBron 15-16 points", "2015-16"),
    ],
)
def test_short_and_dashed_seasons(query, season):
    assert _kwargs(query)["season"] == season


def test_range_beside_a_named_season():
    kwargs = _kwargs("Lakers 21-22 point games 2024-25")
    assert (kwargs["season"], kwargs["min_value"], kwargs["max_value"]) == ("2024-25", 21, 22)


def test_short_season_span():
    kwargs = _kwargs("LeBron from 15-16 to 17-18")
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2015-16", "2017-18")


def test_short_season_answers_like_the_full_season():
    short = _sections("LeBron stats 24-25")["summary"]
    full = _sections("LeBron stats 2024-25")["summary"]
    assert short == full


@pytest.mark.parametrize(
    "query",
    [
        # Records, not seasons.
        "Lakers went 15-16",
        "Lakers had a 15-16 record",
        "Lakers 10-11 in close games",
        # Makes and attempts.
        "LeBron 10/11 from the line",
        "LeBron 11-12 shooting",
        # Not consecutive, or before the data starts.
        "LeBron points 15-17",
        "Lakers record 85-86",
        "Lakers 45-46",
    ],
)
def test_pairs_that_are_not_seasons(query):
    try:
        kwargs = _kwargs(query)
    except ValueError:
        return
    assert kwargs.get("season") not in {"2015-16", "2015-17", "1985-86", "2010-11", "2011-12"}


# ── "N total points" in a game: both teams' combined score ─────────────


def _combined(season: str):
    teams = _teams(season)
    return teams.assign(total=2 * teams["pts"] - teams["plus_minus"])


def test_team_total_points_is_the_combined_score():
    kwargs = _kwargs("Mavericks games with 130 total points")
    assert (kwargs["team"], kwargs["stat"], kwargs["min_value"]) == ("DAL", "game_total_pts", 130)
    lal = _combined("2025-26")
    lal = lal[lal["team_abbr"].eq("LAL") & lal["total"].ge(230)]
    rows = _sections("Lakers games with 230 total points")["finder"]
    assert {int(r["game_id"]) for r in rows} == set(lal["game_id"])
    assert all(r["game_total_pts"] >= 230 for r in rows)
    assert _finder_ids("Lakers games with 230 combined points") == set(lal["game_id"])


def test_combined_score_ceiling():
    lal = _combined("2025-26")
    lal = lal[lal["team_abbr"].eq("LAL") & lal["total"].lt(180)]
    assert _finder_ids("Lakers games with under 180 total points") == set(lal["game_id"])


def test_combined_score_on_a_record():
    lal = _combined("2025-26")
    lal = lal[lal["team_abbr"].eq("LAL") & lal["total"].ge(240)]
    (summary,) = _sections("Lakers record in games with 240 total points")["summary"]
    assert (summary["wins"], summary["losses"]) == (
        int(lal["wl"].eq("W").sum()),
        int(lal["wl"].eq("L").sum()),
    )


def test_combined_score_count_sentence():
    lal = _combined("2025-26")
    lal = lal[lal["team_abbr"].eq("LAL") & lal["total"].gt(250)]
    result = execute_natural_query("how many Lakers games had over 250 total points")
    assert result.result.to_dict()["sections"]["count"] == [{"count": len(lal)}]
    assert "combined points" in result.metadata["count_phrase"]


def test_player_total_points_in_a_game_are_his_own():
    games = _players("2025-26")
    lebron = games[games["player_name"].eq("LeBron James") & games["pts"].ge(35)]
    assert _finder_ids("LeBron games with 35 total points") == set(lebron["game_id"])


# ── season totals ───────────────────────────────────────────────────────


def _season_totals(season: str, stat: str) -> pd.DataFrame:
    return _players(season).groupby("player_id", as_index=False)[stat].sum()


def test_a_total_of_is_a_season_total():
    totals = _season_totals("2024-25", "pts")
    expected = set(totals.loc[totals["pts"] >= 1000, "player_id"])
    rows = _sections("players with a total of 1000 points in 2024-25")["leaderboard"]
    assert {row["player_id"] for row in rows} == expected


def _lebron_seasons(line: float, seasons: list[str]) -> dict[str, int]:
    out = {}
    for season in seasons:
        games = _players(season)
        total = int(games.loc[games["player_name"].eq("LeBron James"), "pts"].sum())
        if total >= line:
            out[season] = total
    return out


@pytest.mark.parametrize(
    "query",
    [
        "LeBron seasons with 1000 points",
        "how many times has LeBron scored 1000 points in a season",
        "how many 1000 point seasons does LeBron have",
    ],
)
def test_named_player_seasons_over_a_total(query):
    expected = _lebron_seasons(1000, ["2023-24", "2024-25", "2025-26"])
    assert expected, "fixture should have LeBron seasons over 1000"
    sections = _sections(query)
    rows = sections["leaderboard"]
    assert {row["season"]: row["pts_total"] for row in rows} == expected
    assert {row["player_name"] for row in rows} == {"LeBron James"}
    if "count" in sections:
        assert sections["count"] == [{"count": len(expected)}]


def test_named_player_seasons_with_a_span():
    expected = _lebron_seasons(1000, ["2024-25", "2025-26"])
    rows = _sections("LeBron seasons with 1000 points since 2024-25")["leaderboard"]
    assert {row["season"]: row["pts_total"] for row in rows} == expected


def test_named_player_with_no_season_over_the_total():
    result = execute_natural_query("LeBron seasons with 1500 points")
    assert result.result.to_dict()["sections"].get("leaderboard", []) == []
    assert "has no seasons with 1,500+ points" in result.metadata["answer_phrase"]


def test_named_player_seasons_name_the_opponent():
    result = execute_natural_query("LeBron seasons with 280 points vs Celtics")
    assert result.result.to_dict()["sections"]["leaderboard"]
    assert "against the Boston Celtics" in result.metadata["answer_phrase"]


def test_named_player_game_threshold_is_unchanged():
    kwargs = _kwargs("LeBron 30 point games")
    assert parse_query("LeBron 30 point games")["route"] == "player_game_finder"
    assert kwargs["min_value"] == 30
