"""C2: rookie and position game lists, checked on the real player rows and rosters."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _season_rows(season, keep):
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.data_source import data_read_csv

    roster = data_read_csv(Path(f"data/raw/rosters/{season}.csv"))
    ids = set(roster.loc[keep(roster), "player_id"].astype(int))
    rows = load_player_games_for_seasons([season], "Regular Season")
    return rows[rows["player_id"].astype(int).isin(ids)]


@pytest.mark.parametrize("season", ["1998-99", "2023-24"])
def test_rookie_scoring_games(season):
    from nbatools.query_service import execute_natural_query

    rows = _season_rows(season, lambda roster: roster["experience_years"] == 0)
    top = sorted(rows["pts"], reverse=True)[:5]
    listed = execute_natural_query(f"top 5 scoring games by rookies in {season}").result.to_dict()[
        "sections"
    ]["finder"]
    assert [row["pts"] for row in listed] == top
    assert {row["season"] for row in listed} == {season}


def test_center_rebounding_games_in_2023_24():
    from nbatools.query_service import execute_natural_query

    rows = _season_rows("2023-24", lambda roster: roster["position"].isin(["C", "C-F"]))
    top = sorted(rows["reb"], reverse=True)[:5]
    listed = execute_natural_query("top 5 rebounding games by centers in 2023-24").result.to_dict()[
        "sections"
    ]["finder"]
    assert [row["reb"] for row in listed] == top
