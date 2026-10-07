"""A2: a year closing the question names its season, on the real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_record_2024_is_2023_24():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Lakers record 2024")
    assert result.result_status == "ok"
    summary = result.result.to_dict()["sections"]["summary"][0]
    # 2023-24 regular season: 47-35.
    assert (summary["wins"], summary["losses"]) == (47, 35)


def test_lebron_stats_2016_is_2015_16():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron stats 2016")
    assert result.result_status == "ok"
    summary = result.result.to_dict()["sections"]["summary"][0]
    # 2015-16 regular season: 76 games, 25.3 points per game.
    assert summary["games"] == 76
    assert round(summary["pts_avg"], 1) == 25.3
