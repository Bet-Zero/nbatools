"""C2 playoff series situations against the real 2015-16 playoff rows.

The 2016 Warriors: 4-1 over Houston and Portland (3-1 up before each game 5),
down 1-3 to Oklahoma City and won games 5-7, up 3-1 in the Finals and lost
games 5-7 to Cleveland.
"""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _record(query: str) -> tuple[int, int]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.metadata["route"] == "team_record", query
    assert result.result_status == "ok", (query, result.result_reason)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"]


def _warriors_series_games() -> list[tuple[int, int, int, str]]:
    """(game number, wins before, losses before, result) for each 2016 Warriors game."""
    rows = data_read_csv("raw/team_game_stats/2015-16_playoffs.csv", dtype={"game_id": str})
    gsw = rows[(rows["team_abbr"] == "GSW") & ~rows["game_id"].str.startswith("005")]
    out = []
    for _, series in gsw.sort_values("game_date").groupby("opponent_team_abbr", sort=False):
        wins = losses = 0
        for number, result in enumerate(series.sort_values("game_date")["wl"], start=1):
            out.append((number, wins, losses, result))
            wins += result == "W"
            losses += result == "L"
    return out


def _count(games, keep) -> tuple[int, int]:
    picked = [result for number, wins, losses, result in games if keep(number, wins, losses)]
    return picked.count("W"), picked.count("L")


def test_warriors_2016_series_situations_match_the_raw_rows():
    games = _warriors_series_games()
    assert len(games) == 24

    expected = {
        "Warriors record in game 7s in 2016": _count(games, lambda n, w, lo: n == 7),
        "Warriors record when up 3-1 in 2016": _count(games, lambda n, w, lo: (w, lo) == (3, 1)),
        "Warriors record when down 3-1 in 2016": _count(games, lambda n, w, lo: (w, lo) == (1, 3)),
        "Warriors record in elimination games in 2016": _count(
            games, lambda n, w, lo: lo == 3 and w < 4
        ),
        "Warriors record in closeout games in 2016": _count(
            games, lambda n, w, lo: w == 3 and lo < 4
        ),
    }
    # The history the rows must agree with.
    assert expected == {
        "Warriors record in game 7s in 2016": (1, 1),
        "Warriors record when up 3-1 in 2016": (2, 1),
        "Warriors record when down 3-1 in 2016": (1, 0),
        "Warriors record in elimination games in 2016": (3, 1),
        "Warriors record in closeout games in 2016": (3, 3),
    }
    for query, record in expected.items():
        assert _record(query) == record, query


def test_cavaliers_2016_title_was_their_only_game_7():
    assert _record("Cavaliers record in game 7s in 2016") == (1, 0)
