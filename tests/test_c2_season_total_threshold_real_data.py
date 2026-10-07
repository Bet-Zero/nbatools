"""C2: players over a season total, against the real player game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _over(season: str, stat: str, line: float) -> dict[int, int]:
    from nbatools.commands.data_utils import load_player_games_for_seasons

    games = load_player_games_for_seasons([season], "Regular Season")
    totals = games.groupby("player_id")[stat].sum()
    return {int(pid): int(value) for pid, value in totals[totals >= line].items()}


def test_players_with_2000_points_in_2023_24():
    from nbatools.query_service import execute_natural_query

    expected = _over("2023-24", "pts", 2000)
    result = execute_natural_query("how many players scored 2000 points in 2023-24")
    sections = result.result.to_dict()["sections"]
    assert sections["count"] == [{"count": len(expected)}]
    rows = {row["player_id"]: row["pts_total"] for row in sections["leaderboard"]}
    assert rows == expected
    # Luka Dončić led the league with 2,370 points.
    top = sections["leaderboard"][0]
    assert (top["player_name"], top["pts_total"]) == ("Luka Dončić", 2370)


def test_players_with_500_assists_in_2023_24():
    from nbatools.query_service import execute_natural_query

    expected = _over("2023-24", "ast", 500)
    result = execute_natural_query("players with 500 assists in 2023-24")
    rows = {row["player_id"] for row in result.result.to_dict()["sections"]["leaderboard"]}
    assert rows == set(expected)
