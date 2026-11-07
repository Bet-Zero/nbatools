"""C2 franchise identity against the real game rows.

Companion to ``test_c2_franchise_identity.py``. Expected values are taken from
the raw rows of the pinned generation by franchise ``team_id``, never from the
code under test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

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


# Independently frozen from retained NBA logs and two explicit game-day sources.
# The full82 population is retained; missing appearance rows never imply DNP.
ID44_EVIDENCE = Path(__file__).resolve().parents[1] / (
    "working/nba-tools-completion-program/source-evidence/id44-core-20261107"
)


def qualified_durant_population():
    raw = (ID44_EVIDENCE / "independent/source-qualified-oracle.json").read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "b67e76636d17184d310297da120d2409f03eb21260aae05606a0195651be626c"
    )
    oracle = json.loads(raw)
    team = _team_games("2007-08")
    team = team[pd.to_numeric(team["team_id"]) == OKC].copy()
    assert len(team) == team.game_id.nunique() == 82
    assert set(team.team_abbr) == {"SEA"}
    assert set(team.team_name) == {"Seattle SuperSonics"}
    actual = {int(r.game_id): (str(r.game_date)[:10], r.wl, int(r.pts)) for r in team.itertuples()}
    assert actual == {
        int(r["game_id"]): (r["game_date"], r["wl"], r["pts"]) for r in oracle["population"]
    }
    players = data_read_csv(
        "raw/player_game_stats/2007-08_regular_season.csv", dtype={"game_id": str}
    )
    played = players[pd.to_numeric(players.player_id).eq(201142)]
    assert len(played) == played.game_id.nunique() == 80
    assert pd.to_numeric(played.minutes).gt(0).all()
    assert set(pd.to_numeric(played.team_id)) == {OKC}
    assert set(played.team_abbr) == {"SEA"}
    assert {int(x) for x in played.game_id} == {
        int(x) for x in oracle["expected"]["with"]["game_ids"]
    }
    assert all(str(r.game_date)[:10] == actual[int(r.game_id)][0] for r in played.itertuples())
    return oracle


def assert_durant_record(result, expected, *, franchise=True):
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    payload = result.result.to_dict()
    summary = payload["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (
        len(expected["game_ids"]),
        expected["wins"],
        expected["losses"],
    )
    assert summary["team_name"] == "Seattle SuperSonics"
    assert summary["pts_avg"] == pytest.approx(
        expected["points"] / len(expected["game_ids"]), abs=0.001
    )
    selected = [int(r["game_id"]) for r in payload["sections"]["game_log"]]
    assert len(selected) == len(set(selected)) == len(expected["game_ids"])
    assert set(selected) == {int(x) for x in expected["game_ids"]}
    if franchise:
        assert any("Seattle SuperSonics" in c for c in result.result.caveats)


def test_thunder_record_without_durant_in_2007_08_is_seattle_games_he_missed():
    oracle = qualified_durant_population()
    # Explicit Traditional DND and Summary inactive rows establish same-game
    # Seattle association; expected absences are not the complement of a log.
    assert_durant_record(
        _query("Thunder record without Kevin Durant in 2007-08"), oracle["expected"]["without"]
    )


def test_thunder_record_with_durant_in_2007_08_keeps_his_seattle_games():
    oracle = qualified_durant_population()
    assert_durant_record(
        _query("Thunder record with Kevin Durant in 2007-08"), oracle["expected"]["with"]
    )


@pytest.mark.parametrize(
    "query",
    [
        "best record from 2000-01 to 2024-25",
        "which team has the most 120 point games from 2000-01 to 2024-25",
        "most playoff wins from 2000-01 to 2024-25",
    ],
)
def test_league_boards_show_one_row_per_franchise(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    rows = result.result.to_dict()["sections"]["leaderboard"]
    abbrs = [str(row.get("team_abbr")) for row in rows]
    for old, new in (("SEA", "OKC"), ("NJN", "BKN"), ("VAN", "MEM"), ("NOH", "NOP")):
        assert not (old in abbrs and new in abbrs), (query, abbrs)
