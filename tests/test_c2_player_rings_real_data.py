"""Player rings against the real 1996-97+ playoffs."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _leaders(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", result.result_reason
    return result, result.result.leaders


def test_lebron_has_four_rings():
    result, board = _leaders("how many rings does lebron have")
    row = board.iloc[0]
    assert (row["player_name"], int(row["titles"])) == ("LeBron James", 4)
    assert row["title_seasons"] == "2011-12, 2012-13, 2015-16, 2019-20"
    assert row["title_teams"] == "MIA, MIA, CLE, LAL"
    assert "LeBron James won 4 titles" in result.metadata["answer_phrase"]


def test_jokic_has_one_ring():
    _, board = _leaders("how many titles has Jokic won")
    row = board.iloc[0]
    assert (int(row["titles"]), row["title_seasons"]) == (1, "2022-23")


def test_most_rings_since_1996_is_five():
    _, board = _leaders("who has the most rings")
    top = board[board["titles"] == board["titles"].max()]
    assert int(top["titles"].iloc[0]) == 5
    assert {"Tim Duncan", "Kobe Bryant", "Derek Fisher"} <= set(top["player_name"])
