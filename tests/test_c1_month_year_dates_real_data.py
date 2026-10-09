"""C1: month-and-year dates against the real team rows."""

from __future__ import annotations

import pandas as pd
import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_record_from_january_2024_to_march_2024():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[games["team_abbr"] == "LAL"]
    day = pd.to_datetime(games["game_date"])
    games = games[(day >= "2024-01-01") & (day <= "2024-03-31")]
    summary = execute_natural_query("Lakers record from Jan. 2024 to Mar. 2024").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )
