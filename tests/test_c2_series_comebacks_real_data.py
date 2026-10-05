"""Series comebacks against the real 1996-97+ playoffs."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _rows(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    return result, result.result.to_dict()["sections"].get("leaderboard", [])


def test_2016_cavaliers_came_back_from_3_1_in_the_finals():
    result, rows = _rows("teams that came back from 3-1 down in the Finals")
    assert result.result_status == "ok", result.result_reason
    assert [(r["season"], r["team_abbr"], r["opponent_team_abbr"]) for r in rows] == [
        ("2015-16", "CLE", "GSW")
    ]


def test_warriors_blew_a_3_1_lead_in_2016():
    _, rows = _rows("Warriors blew a 3-1 lead")
    assert ("2015-16", "Finals", "CLE") in {
        (r["season"], r["playoff_round"], r["opponent_team_abbr"]) for r in rows
    }


def test_warriors_came_back_from_3_1_against_okc():
    _, rows = _rows("have the Warriors ever come back from 3-1")
    assert ("2015-16", "OKC") in {(r["season"], r["opponent_team_abbr"]) for r in rows}


def test_nobody_came_back_from_3_0():
    result, _ = _rows("teams that came back from 3-0 down")
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"
