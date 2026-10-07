"""C2 franchise identity against the real game rows.

Companion to ``test_c2_franchise_identity.py``. Expected values are taken from
the raw rows of the pinned generation by franchise ``team_id``, never from the
code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_exists, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

OKC, BKN, MEM = 1610612760, 1610612751, 1610612763


def _team_games(season: str, season_type: str = "regular_season") -> pd.DataFrame:
    path = f"raw/team_game_stats/{season}_{season_type}.csv"
    if not data_exists(path):
        return pd.DataFrame()
    return data_read_csv(path, dtype={"game_id": str})


def _query(text: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(text)
    assert result.result_status == "ok", (text, result.result_reason, result.metadata)
    return result


def test_the_seattle_rows_carry_the_thunder_franchise_id():
    games = _team_games("2005-06")
    seattle = games[games["team_abbr"] == "SEA"]
    assert not seattle.empty
    assert set(pd.to_numeric(seattle["team_id"])) == {OKC}


def test_nets_record_in_2002_03_finds_the_new_jersey_games():
    games = _team_games("2002-03")
    nets = games[pd.to_numeric(games["team_id"]) == BKN]
    wins, losses = int((nets["wl"] == "W").sum()), int((nets["wl"] == "L").sum())
    assert (wins, losses) == (49, 33)

    summary = _query("Nets record in 2002-03").result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (wins, losses)


def test_thunder_playoff_appearances_since_2000_include_seattle():
    seasons = [f"{y}-{str(y + 1)[-2:]}" for y in range(2000, 2025)]
    appeared = set()
    for season in seasons:
        games = _team_games(season, "playoffs")
        if games.empty:
            continue
        games = games[~games["game_id"].astype(str).str.zfill(10).str.startswith("005")]
        if (pd.to_numeric(games["team_id"]) == OKC).any():
            appeared.add(season)
    assert {"2001-02", "2004-05"} <= appeared  # the two Seattle appearances

    result = _query("Thunder playoff appearances from 2000-01 to 2024-25")
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["appearances"] == len(appeared)
    assert any("Seattle SuperSonics" in c for c in result.result.caveats)


def test_grizzlies_vs_thunder_meetings_in_2000_01_are_vancouver_vs_seattle():
    games = _team_games("2000-01")
    meetings = games[
        (pd.to_numeric(games["team_id"]) == MEM) & (pd.to_numeric(games["opponent_team_id"]) == OKC)
    ]
    assert len(meetings) >= 3

    summary = _query("Grizzlies record vs the Thunder in 2000-01").result.to_dict()["sections"][
        "summary"
    ][0]
    assert summary["wins"] + summary["losses"] == len(meetings)
    assert summary["wins"] == int((meetings["wl"] == "W").sum())


def test_thunder_record_without_durant_in_2007_08_is_seattle_games_he_missed():
    team = _team_games("2007-08")
    team = team[pd.to_numeric(team["team_id"]) == OKC]
    players = data_read_csv(
        "raw/player_game_stats/2007-08_regular_season.csv", dtype={"game_id": str}
    )
    played = set(players[pd.to_numeric(players["player_id"]) == 201142]["game_id"])
    missed = team[~team["game_id"].isin(played)]
    assert 0 < len(missed) < len(team)

    summary = _query("Thunder record without Kevin Durant in 2007-08").result.to_dict()["sections"][
        "summary"
    ][0]
    assert (summary["wins"], summary["losses"]) == (
        int((missed["wl"] == "W").sum()),
        int((missed["wl"] == "L").sum()),
    )
