"""C1: "who led the Lakers in scoring over the Celtics" and "Lakers record in
Boston" on real rows (2023-24)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_scoring_over_the_celtics_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[(rows["team_abbr"] == "LAL") & (rows["opponent_team_abbr"] == "BOS")]
    expected = rows.groupby("player_id")["pts"].mean().sort_values(ascending=False)
    result = execute_natural_query("who led the Lakers in scoring over the Celtics in 2023-24")
    board = result.result.to_dict()["sections"]["leaderboard"]
    assert result.route == "season_leaders"
    assert board[0]["pts_per_game"] == pytest.approx(expected.iloc[0], abs=1e-3)


def test_lakers_record_in_boston_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[
        (games["team_abbr"] == "LAL")
        & (games["opponent_team_abbr"] == "BOS")
        & (games["is_home"].astype(int) == 0)
    ]
    summary = execute_natural_query("Lakers record in Boston in 2023-24").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )
