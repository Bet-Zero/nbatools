"""C2 two-team stretches against the real regular-season rows.

"Lakers vs Celtics best 10 game stretch" ranks each team on its own games.
The expected windows are counted from the raw team game CSV with a plain loop.
"""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _best_wins(season: str, abbr: str, size: int) -> int:
    rows = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv", dtype={"game_id": str})
    games = rows[rows["team_abbr"] == abbr].sort_values(["game_date", "game_id"])
    results = list(games["wl"])
    return max(
        sum(r == "W" for r in results[start : start + size])
        for start in range(len(results) - size + 1)
    )


def test_versus_pair_best_stretch_counts_raw_games():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Lakers vs Celtics best 10 game stretch in 2007-08")
    assert result.metadata["route"] == "team_stretch_leaderboard"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    best = {row["team_abbr"]: row["wins"] for row in rows}
    assert best == {abbr: _best_wins("2007-08", abbr, 10) for abbr in ("LAL", "BOS")}
