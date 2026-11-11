"""Requested totals summarize; a team's event board keeps the team; "who led" ranks.

Found by PR606's independent review. Expectations come from plain pandas over the
pinned v7 development rows, never from application output.
"""

import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands.natural_query import parse_query
from nbatools.development_data import development_snapshot
from tests.test_whole_rebound_correction import DATASET, V7, _unpack

pytestmark = [pytest.mark.served_seasons, pytest.mark.query]

PID = 1629023
STATS = ["pts", "reb", "ast", "stl", "blk"]


@pytest.fixture(scope="module")
def v7(tmp_path_factory):
    return _unpack(V7, tmp_path_factory.mktemp("totals-events-v7"))


@pytest.fixture(autouse=True)
def local(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")


def _answer(snapshot, query):
    with development_snapshot(*snapshot):
        body = natural_query_payload(query)
    assert body["result_status"] == "ok", body
    return body["result"]


@pytest.mark.parametrize(
    "query,stat",
    [
        ("PJ Washington defensive rebounds 2026-27 total", "dreb"),
        ("P.J. Washington total defensive rebounds in 2026-27", "dreb"),
        ("PJ Washington 2026-27 rebound totals", "reb"),
        ("what were P.J. Washington's total assists for 2026-27", "ast"),
    ],
)
def test_requested_player_total_is_the_season_aggregate(v7, query, stat):
    rows = pd.read_csv(v7[0] / DATASET)
    mine = rows[rows.player_id.eq(PID)]
    result = _answer(v7, query)
    (summary,) = result["sections"]["summary"]
    assert summary["games"] == len(mine) == 8
    assert summary[f"{stat}_sum"] == mine[stat].sum()
    assert "finder" not in result["sections"]


def test_requested_team_total_is_the_team_aggregate(v7):
    teams = pd.read_csv(v7[0] / "data/raw/team_game_stats/2026-27_regular_season.csv")
    dal = teams[teams.team_abbr.eq("DAL")]
    (summary,) = _answer(v7, "Mavericks total rebounds 2026-27")["sections"]["summary"]
    assert summary["games"] == len(dal) and summary["reb_sum"] == dal.reb.sum()


@pytest.mark.parametrize(
    "query",
    [
        "most total rebounds in 2026-27",
        "players with 25 points and 10 rebounds total",
        "Mavericks games with 130 total points",
        "LeBron and Davis combined total points",
        "total number of LeBron 30 point games",
    ],
)
def test_ranked_threshold_and_combined_totals_keep_other_readings(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert parsed["route"] not in {"player_game_summary", "game_summary"}


def _double_doubles(rows):
    return rows[(rows[STATS] >= 10).sum(axis=1) >= 2].groupby("player_id").size()


@pytest.mark.parametrize(
    "query,team",
    [
        ("most double doubles 2026-27 Mavericks", "DAL"),
        ("Who led the Mavericks in double-doubles in 2026-27", "DAL"),
        ("who led Dallas in double doubles during 2026-27", "DAL"),
        ("Spurs most double-doubles 2026-27", "SAS"),
        ("Who led the league in double-doubles in 2026-27", None),
    ],
)
def test_double_double_boards_keep_the_named_team(v7, query, team):
    rows = pd.read_csv(v7[0] / DATASET)
    population = rows[rows.team_abbr.eq(team)] if team else rows
    expected = _double_doubles(population)
    result = _answer(v7, query)
    assert result["metadata"].get("team") == team
    board = result["sections"]["leaderboard"]
    assert board and len(board) == min(10, len(expected))
    values = {r["player_id"]: r["double doubles"] for r in board}
    assert all(values[p] == expected[p] for p in values)
    ranked = [r["double doubles"] for r in board]
    assert ranked == sorted(expected.values, reverse=True)[: len(board)]
    if team:
        assert {r["team_abbr"] for r in board} == {team}


def test_opponent_is_not_read_as_the_players_team():
    parsed = parse_query("most double doubles against the Mavericks 2026-27")
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_occurrence_leaders"
    assert kwargs.get("opponent") == "DAL" and not kwargs.get("team")


@pytest.mark.parametrize(
    "query,season,stat,floor",
    [
        ("LeBron James 2015-16 points per game", "2015-16", "pts", None),
        ("Jokic 2023-24 assists", "2023-24", "ast", None),
        ("Lakers 2019-20 points", "2019-20", "pts", None),
        ("LeBron 2015-16 30 point games", "2015-16", "pts", 30.0),
        ("LeBron 30 points 2015-16", "2015-16", "pts", 30.0),
    ],
)
def test_season_closing_year_is_not_a_stat_floor(query, season, stat, floor):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("season"), kwargs.get("stat"), kwargs.get("min_value")) == (
        season,
        stat,
        floor,
    )


def test_season_before_stat_summary_keeps_every_game(v7):
    rows = pd.read_csv(v7[0] / DATASET)
    mine = rows[rows.player_id.eq(PID)]
    (summary,) = _answer(v7, "PJ Washington 2026-27 rebounds per game")["sections"]["summary"]
    assert summary["games"] == len(mine) and summary["reb_sum"] == mine.reb.sum()
