"""C1: team games ranked by the opponent's number.

"Lakers games with the most opponent turnovers" ranked the Lakers' own
turnovers; "fewest opponent rebounds" ranked the Lakers' rebounds highest
first. The opponent's stat ranks, in the asked direction, and a bound on
the team's own stat stays a condition. Expected values come from the
fixture's team rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _lakers() -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    other = games[["game_id", "team_abbr", "tov", "reb"]].rename(
        columns={"team_abbr": "opp", "tov": "opp_tov", "reb": "opp_reb"}
    )
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    return lakers[lakers["opp"] != "LAL"]


def _values(query: str, column: str, games: pd.DataFrame) -> list:
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    by_date = dict(zip(games["game_date"], games[column], strict=True))
    return [by_date[str(r["game_date"])[:10]] for r in rows]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers games with the most opponent turnovers",
        "Lakers games where opponents had the most turnovers",
        "Lakers games where they forced the most turnovers",
    ],
)
def test_most_opponent_turnovers(query):
    games = _lakers()
    values = _values(query, "opp_tov", games)
    assert values == sorted(games["opp_tov"], reverse=True)[: len(values)]


def test_top_5_by_opponent_turnovers():
    games = _lakers()
    values = _values("Lakers top 5 games by opponent turnovers", "opp_tov", games)
    assert values == sorted(games["opp_tov"], reverse=True)[:5]


def test_fewest_opponent_rebounds_ranks_from_the_bottom():
    games = _lakers()
    values = _values("Lakers games with the fewest opponent rebounds", "opp_reb", games)
    assert values == sorted(games["opp_reb"])[: len(values)]


def test_a_bound_on_the_teams_own_stat_stays():
    games = _lakers()
    games = games[games["pts"] >= 120]
    values = _values("Lakers most opponent turnovers with 120 points", "opp_tov", games)
    assert values == sorted(games["opp_tov"], reverse=True)


def test_at_least_n_opponent_turnovers_is_a_bound():
    games = _lakers()
    result = execute_natural_query("how many Lakers games had at least 15 opponent turnovers")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((games["opp_tov"] >= 15).sum())}
    ]


def test_the_opponent_forcing_turnovers_ranks_the_teams_own():
    games = _lakers()
    values = _values("Lakers games where the opponent forced the most turnovers", "tov", games)
    assert values == sorted(games["tov"], reverse=True)[: len(values)]


def test_a_bound_after_an_opponent_had_ranking_stays():
    games = _lakers()
    games = games[games["pts"] >= 120]
    values = _values(
        "Lakers games where opponents had the most turnovers with 120 points", "opp_tov", games
    )
    assert values == sorted(games["opp_tov"], reverse=True)


def test_the_ranked_opponent_number_is_shown():
    rows = execute_natural_query("Lakers games with the most opponent turnovers").result.to_dict()[
        "sections"
    ]["finder"]
    assert all("opponent_tov" in r for r in rows)
