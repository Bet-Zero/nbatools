"""Stat ranges, two-digit seasons, "N total points" and season totals on real rows.

Expected values are counted straight from the published raw box-score files,
not from another engine path.
"""

from __future__ import annotations

import pytest

from nbatools.data_source import data_exists, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _players(season: str):
    return data_read_csv(f"data/raw/player_game_stats/{season}_regular_season.csv")


def _teams(season: str):
    return data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")


def _answer(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _sections(query: str) -> dict:
    return _answer(query).result.to_dict()["sections"]


@pytest.mark.parametrize(
    "query",
    [
        "how many games did LeBron score 25-30 points in 2015-16",
        "how many games did LeBron score 25 to 30 points in 15-16",
        "how many 25-30 point games did LeBron have in 2015–16",
    ],
)
def test_lebron_25_to_30_point_games(query):
    games = _players("2015-16")
    lebron = games[games["player_name"].eq("LeBron James") & games["pts"].between(25, 30)]
    assert len(lebron) > 0
    assert _sections(query)["count"] == [{"count": len(lebron)}]


def test_curry_short_season_summary():
    games = _players("2015-16")
    curry = games[games["player_name"].eq("Stephen Curry")]
    result = _answer("Curry stats 15-16")
    assert result.metadata.get("season") == "2015-16"
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(curry)
    assert summary["pts_avg"] == pytest.approx(curry["pts"].mean(), abs=0.05)


def test_mavericks_combined_score_games():
    teams = _teams("2023-24")
    # Both teams' rows of the same game, summed: independent of plus-minus.
    combined = teams.groupby("game_id")["pts"].sum()
    dal = teams[teams["team_abbr"].eq("DAL")]
    dal = dal[dal["game_id"].map(combined).ge(250)]
    assert 0 < len(dal) <= 25
    rows = _sections("Mavericks games with 250 total points in 2023-24")["finder"]
    assert {int(r["game_id"]) for r in rows} == {int(g) for g in dal["game_id"]}


def test_combined_score_count_from_both_team_rows():
    teams = _teams("2023-24")
    # Both teams' rows of the same game, summed. Plus-minus is missing on some
    # real rows, so it is not used for the expectation.
    pairs = teams.groupby("game_id")["pts"].sum()
    lal = teams[teams["team_abbr"].eq("LAL")]
    expected = set(lal["game_id"][lal["game_id"].map(pairs).lt(210)])
    assert expected
    sections = _sections("how many Lakers games had under 210 total points in 2023-24")
    assert sections["count"] == [{"count": len(expected)}]


def test_players_with_a_total_of_2000_points():
    games = _players("2022-23")
    totals = games.groupby("player_id")["pts"].sum()
    expected = {int(p) for p in totals[totals >= 2000].index}
    assert expected
    rows = _sections("players with a total of 2000 points in 2022-23")["leaderboard"]
    assert {int(r["player_id"]) for r in rows} == expected


def test_lebron_2000_point_seasons():
    expected = {}
    for start in range(2003, 2027):
        season = f"{start}-{str(start + 1)[-2:]}"
        path = f"data/raw/player_game_stats/{season}_regular_season.csv"
        if not data_exists(path):
            continue
        games = data_read_csv(path)
        total = int(games.loc[games["player_name"].eq("LeBron James"), "pts"].sum())
        if total >= 2000:
            expected[season] = total
    assert expected
    sections = _sections("how many times has LeBron scored 2000 points in a season")
    assert sections["count"] == [{"count": len(expected)}]
    assert {r["season"]: int(r["pts_total"]) for r in sections["leaderboard"]} == expected
