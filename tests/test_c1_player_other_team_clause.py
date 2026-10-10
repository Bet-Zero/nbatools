"""C1: a clause about another team on a player's games is his opponent's.

"LeBron top scoring games when the Celtics made 15 threes" read the Celtics
as LeBron's team (no games). The named team, when it is not his team in the
latest season, is the opponent and its number an opponent bound. Expected
values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _games(player: str, opp: str) -> pd.DataFrame:
    players = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    teams = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    other = teams[["game_id", "team_abbr", "pts", "fg3m"]].rename(
        columns={"team_abbr": "opponent_team_abbr", "pts": "opp_pts", "fg3m": "opp_fg3m"}
    )
    rows = players[players["player_name"] == player].merge(
        other, on=["game_id", "opponent_team_abbr"]
    )
    return rows[rows["opponent_team_abbr"] == opp]


def test_top_scoring_games_when_the_opponent_made_15_threes():
    games = _games("LeBron James", "BOS")
    games = games[games["opp_fg3m"] >= 15]
    rows = execute_natural_query(
        "LeBron top scoring games when the Celtics made 15 threes"
    ).result.to_dict()["sections"]["finder"]
    assert [r["pts"] for r in rows] == games["pts"].nlargest(len(rows)).tolist()
    assert len(rows) == min(5, len(games))


def test_points_when_the_opponent_scored_120():
    games = _games("LeBron James", "BOS")
    games = games[games["opp_pts"] >= 120]
    summary = execute_natural_query("LeBron points when the Celtics scored 120").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert summary["games"] == len(games)
    assert summary["pts_avg"] == pytest.approx(games["pts"].mean(), abs=0.01)


@pytest.mark.parametrize(
    ("query", "team", "opponent"),
    [
        ("LeBron games when the Lakers scored 120", "LAL", None),
        ("LeBron games vs Boston when the Lakers score 120", "LAL", "BOS"),
        ("LeBron games when the Celtics scored 120", None, "BOS"),
        # His team named outside the clause stays his team.
        ("LeBron stats with the Celtics when the Celtics scored 120", "BOS", None),
        ("LeBron games for the Heat when the Heat scored 120", "MIA", None),
        ("LeBron Heat games when the Heat scored 120", "MIA", None),
    ],
)
def test_whose_team_the_clause_names(query, team, opponent):
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("team"), kwargs.get("opponent")) == (team, opponent)
