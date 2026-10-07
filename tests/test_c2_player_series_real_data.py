"""C2: a player's playoff series record against the real playoff rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_series_record_2016_to_2020():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron playoff series record from 2015-16 to 2019-20")
    assert result.result_status == "ok"
    summary = result.result.to_dict()["sections"]["summary"][0]
    # 2016: won 4 (title); 2017: won 3, lost Finals; 2018: won 3, lost Finals;
    # 2019: missed the playoffs; 2020: won 4 (title) with the Lakers.
    assert (summary["series_won"], summary["series_lost"]) == (14, 2)
    assert "Cleveland Cavaliers" in summary["team_name"]
    assert "Los Angeles Lakers" in summary["team_name"]


def test_lebron_finals_series_record():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron Finals series record")
    summary = result.result.to_dict()["sections"]["summary"][0]
    # 10 Finals from 2007 to 2020: 4 won (2012, 2013, 2016, 2020), 6 lost.
    assert (summary["series_won"], summary["series_lost"]) == (4, 6)
