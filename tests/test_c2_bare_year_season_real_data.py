"""C2 lone years against the real regular-season rows."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lone_year_record_counts_the_season_that_ended_in_it():
    from nbatools.query_service import execute_natural_query

    rows = data_read_csv("raw/team_game_stats/2015-16_regular_season.csv", dtype={"game_id": str})
    gsw = rows[rows["team_abbr"] == "GSW"]
    wins, losses = int((gsw["wl"] == "W").sum()), int((gsw["wl"] == "L").sum())

    result = execute_natural_query("Warriors record in 2016")
    assert result.metadata["route"] == "team_record"
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (wins, losses) == (73, 9)
