"""C1: "facing" reads the opponent filter against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_record_facing_the_celtics_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["team_abbr"] == "LAL") & (games["opponent_team_abbr"] == "BOS")]
    summary = execute_natural_query("Lakers record facing the Celtics in 2023-24").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )
