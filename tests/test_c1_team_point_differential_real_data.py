"""C1: Lakers point differential and plus-minus board on real rows (2023-24)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_point_differential_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    opp = games[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp_abbr", "pts": "opp_pts"}
    )
    merged = games.merge(opp, on="game_id")
    merged = merged[(merged["team_abbr"] == "LAL") & (merged["opp_abbr"] != "LAL")]
    margin = (merged["pts"] - merged["opp_pts"]).mean()
    result = execute_natural_query("Lakers point differential in 2023-24")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["games"] == len(merged)
    assert row["plus_minus_avg"] == pytest.approx(margin, abs=1e-3)
    words = "outscoring opponents by" if margin > 0 else "outscored by"
    assert f"{words} {abs(margin):.1f} points per game" in result.metadata["answer_phrase"]


def test_lakers_best_plus_minus_board_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[rows["team_abbr"] == "LAL"]
    expected = rows.groupby("player_id")["plus_minus"].mean().sort_values(ascending=False)
    result = execute_natural_query("who has the best plus minus on the Lakers in 2023-24")
    board = result.result.to_dict()["sections"]["leaderboard"]
    assert result.route == "season_leaders"
    assert board[0]["plus_minus_per_game"] == pytest.approx(expected.iloc[0], abs=1e-3)
    assert [r["plus_minus_per_game"] for r in board] == sorted(
        (r["plus_minus_per_game"] for r in board), reverse=True
    )
