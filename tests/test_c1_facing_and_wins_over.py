"""C1: "facing" and "wins over winning teams" read the opponent filter.

"Lakers record facing winning teams" / "facing the Celtics" read no filter
(the full season, 47-13); "how many wins do the Lakers have over winning
teams" counted every win (47). They read as "against". Expected values come
from the fixture's team rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _games() -> pd.DataFrame:
    return pd.read_csv(RAW / "2025-26_regular_season.csv")


def _winning() -> set:
    records = _games().groupby("team_abbr")["wl"].value_counts().unstack(fill_value=0)
    return set(records[records["W"] > records["L"]].index)


def _record(query: str) -> tuple[int, int]:
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"]


def _lakers_vs(opponents: set) -> tuple[int, int]:
    games = _games()
    games = games[(games["team_abbr"] == "LAL") & games["opponent_team_abbr"].isin(opponents)]
    return int((games["wl"] == "W").sum()), int((games["wl"] == "L").sum())


@pytest.mark.parametrize(
    ("query", "opponents"),
    [
        ("Lakers record facing winning teams", None),
        ("Lakers record facing teams over .500", None),
        ("Lakers record facing the Celtics", {"BOS"}),
        ("Lakers record when facing the Celtics", {"BOS"}),
    ],
)
def test_facing_is_an_opponent_filter(query, opponents):
    assert _record(query) == _lakers_vs(opponents or _winning())


def test_wins_over_winning_teams_count():
    wins, _ = _lakers_vs(_winning())
    result = execute_natural_query("how many wins do the Lakers have over winning teams")
    assert result.result.to_dict()["sections"]["count"] == [{"count": wins}]


def test_facing_elimination_stays_a_series_situation():
    # "facing elimination" is the series situation, not an opponent: the
    # Nuggets' two elimination games in the fixture's playoffs.
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Nuggets record when facing elimination")
    assert parsed.get("series_situation") == "elimination"
    assert parsed.get("season_type") == "Playoffs"
    assert _record("Nuggets record when facing elimination") == (1, 1)
