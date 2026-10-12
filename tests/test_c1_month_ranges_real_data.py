"""C1: "Lakers record from January to March 2024" on real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_january_to_march_2024():
    import pandas as pd

    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[games["team_abbr"] == "LAL"]
    dates = pd.to_datetime(games["game_date"])
    games = games[(dates >= "2024-01-01") & (dates <= "2024-03-31")]
    summary = execute_natural_query("Lakers record from January to March 2024").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )
