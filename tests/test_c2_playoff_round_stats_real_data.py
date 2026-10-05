"""Stats by playoff round against the real 1996-97+ playoffs."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _summary(query: str) -> dict:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", result.result_reason
    return result.result.to_dict()["sections"]["summary"][0]


def test_lebron_played_55_finals_games():
    # 2007, 2011-2018 and 2020 Finals: 4+6+5+7+5+6+7+5+4+6.
    summary = _summary("LeBron stats in the Finals")
    assert summary["games"] == 55


def test_jokic_2023_finals_line():
    summary = _summary("Jokic stats in the 2023 Finals")
    assert (summary["games"], summary["wins"], summary["losses"]) == (5, 4, 1)
    assert round(summary["pts_avg"], 1) == 30.2
    assert round(summary["reb_avg"], 1) == 14.0
