"""B1: a stated shot-attempt minimum on team shooting-rate leaderboards.

"teams with the best 3 point percentage minimum 2000 attempts" refused as an
unsupported concept: only the player board read the qualifier. The team board
now keeps teams that reached the stated minimum (season total or per game),
in place of its default attempt floor, and says so in a caveat. A minimum on a
non-rate team stat still refuses rather than being dropped.

Expected values come from the raw fixture team game rows, not the engine.
Fixture: 60 regular-season games per team, 2025-26 the current season.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

_RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _season_totals() -> pd.DataFrame:
    games = pd.read_csv(_RAW / "2025-26_regular_season.csv")
    totals = games.groupby("team_abbr")[["fg3m", "fg3a", "ftm", "fta"]].sum()
    totals["games"] = games.groupby("team_abbr").size()
    totals["fg3_pct"] = totals["fg3m"] / totals["fg3a"]
    totals["ft_pct"] = totals["ftm"] / totals["fta"]
    return totals


def _expected(rate: str, attempts: str, minimum: float, per_game: bool) -> list[str]:
    totals = _season_totals()
    volume = totals[attempts] / (totals["games"] if per_game else 1)
    qualified = totals[volume >= minimum].sort_values(rate, ascending=False)
    return list(qualified.index)


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "rate", "attempts", "minimum", "per_game", "caveat"),
    [
        (
            "teams with the best 3 point percentage minimum 1500 attempts",
            "fg3_pct",
            "fg3a",
            1500,
            False,
            "qualified: at least 1500 three-point attempts",
        ),
        (
            "best team free throw percentage with at least 1450 attempts",
            "ft_pct",
            "fta",
            1450,
            False,
            "qualified: at least 1450 free-throw attempts",
        ),
        (
            "team 3 point percentage leaders minimum 26 attempts per game",
            "fg3_pct",
            "fg3a",
            26,
            True,
            "qualified: at least 26 three-point attempts per game",
        ),
    ],
)
def test_team_rate_board_keeps_teams_over_the_stated_minimum(
    query, rate, attempts, minimum, per_game, caveat
):
    expected = _expected(rate, attempts, minimum, per_game)
    # The fixture must discriminate: some teams in, some out.
    assert 0 < len(expected) < len(_season_totals())
    data = execute_natural_query(query).to_dict()
    assert data["result_status"] == "ok"
    assert data["metadata"]["route"] == "season_team_leaders"
    assert [row["team_abbr"] for row in data["sections"]["leaderboard"]] == expected
    assert caveat in data["caveats"]


@pytest.mark.fixture_data
def test_a_minimum_no_team_meets_is_an_empty_answer_not_a_refusal():
    data = execute_natural_query(
        "teams with the best 3 point percentage minimum 2000 attempts"
    ).to_dict()
    assert data["result_status"] == "no_result"
    assert data["result_reason"] == "no_match"


def test_the_qualifier_reaches_the_team_route():
    kwargs = parse_query("best team 3 point percentage minimum 300 three point attempts")[
        "route_kwargs"
    ]
    assert (kwargs["min_attempts"], kwargs["attempt_stat"]) == (300, "fg3a")
    assert not kwargs.get("unsupported_filters")


def test_a_minimum_on_a_non_rate_team_stat_still_refuses():
    kwargs = parse_query("teams with the most points minimum 1000 attempts")["route_kwargs"]
    assert "min_attempts" not in kwargs
    assert kwargs.get("unsupported_filters")
