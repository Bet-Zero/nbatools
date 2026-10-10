"""C1: "Lakers record at Boston" against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_record_at_boston_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[
        (games["team_abbr"] == "LAL")
        & (games["opponent_team_abbr"] == "BOS")
        & (games["is_away"].astype(int) == 1)
    ]
    summary = execute_natural_query("Lakers record at Boston in 2023-24").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )
