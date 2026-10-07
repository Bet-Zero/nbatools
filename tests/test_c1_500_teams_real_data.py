"""C1: ".500 teams" opponents against the real standings and team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("Lakers record vs .500 teams in 2023-24", lambda pct: pct >= 0.5),
        ("Lakers record vs teams .500 or below in 2023-24", lambda pct: pct <= 0.5),
    ],
)
def test_lakers_record_against_a_500_bar(query, keep):
    import pandas as pd

    from nbatools.commands.data_utils import (
        load_latest_standings_snapshot,
        load_team_games_for_seasons,
    )
    from nbatools.query_service import execute_natural_query

    standings = load_latest_standings_snapshot("2023-24")
    pct = pd.to_numeric(standings["win_pct"], errors="coerce")
    opponents = set(standings.loc[pct.map(keep), "team_abbr"])
    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    mine = games[(games["team_abbr"] == "LAL") & games["opponent_team_abbr"].isin(opponents)]

    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((mine["wl"] == "W").sum()),
        int((mine["wl"] == "L").sum()),
    )
