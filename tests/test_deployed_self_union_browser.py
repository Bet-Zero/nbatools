"""Explicit self-containing opponent unions through the deployed interface."""

import hashlib
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table
from tests.test_self_opponent_union_real_data import ORACLE, _qualify

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-ClijrUhz.js"
FOLDER = "self-union-browser"
PLAYER_HASH = "a455e553ceb0b4e74bd4caf37aca482c0a9aab193631b6f2b383b623f861d760"
PLAYER = dict(
    game_id=22300403,
    player_id=2544,
    team_id=1610612747,
    opponent_team_id=1610612738,
    team_abbr="LAL",
    opponent_team_abbr="BOS",
    pts=16,
    reb=9,
    ast=8,
    wl="L",
)


def _cases():
    assert ORACLE["generation"] == "availability-opening-s4-v1-20261017"
    assert ORACLE["manifest"] == "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
    _qualify(ORACLE["cases"][0])  # Hashes, full team sample, reciprocal sides, dates and finality.
    path = data_path("raw/player_game_stats/2023-24_regular_season.csv")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PLAYER_HASH
    players = pd.read_csv(path)
    assert not players.duplicated(["game_id", "player_id", "team_id"]).any()
    selected = players[
        players.player_id.eq(2544)
        & players.team_abbr.eq("LAL")
        & players.opponent_team_abbr.isin(["LAL", "BOS"])
    ]
    assert selected.game_id.tolist() == [PLAYER["game_id"]]
    assert selected.iloc[0].player_name == "LeBron James"
    team_game = next(
        row for row in ORACLE["cases"][0]["rows"] if row["game_id"] == PLAYER["game_id"]
    )
    for key, value in PLAYER.items():
        assert (team_game["wl"] if key == "wl" else selected.iloc[0][key]) == value
    assert selected.iloc[0].game_date == team_game["game_date"]
    common = dict(forbidden=["No Matching Results", "undefined", "NaN", "Infinity"])
    return [
        dict(
            id="self-union-record",
            query="Lakers record against Lakers and Celtics in 2023-24",
            text=["Lakers are 1-1", "LAL, BOS", "50% win rate"],
            **common,
        ),
        dict(
            id="self-union-own-finder",
            query="Lakers games against Celtics and Lakers when Lakers score at least 110 in 2023-24",
            text=["BOS, LAL", "110+ PTS"],
            **common,
        ),
        dict(
            id="self-union-player-team",
            query="Lakers LeBron James games against Lakers and Celtics when Lakers score at least 110 in 2023-24",
            text=[
                "LeBron James",
                "16 points, 9 rebounds and 8 assists",
                "LAL, BOS",
                "110+ TEAM PTS",
            ],
            **common,
        ),
    ]


def _record(item, metadata, sections):
    assert item["payload"]["route"] == "team_record"
    assert set(sections) == {"summary", "by_season"}
    assert metadata["stat"] is None and not metadata.get("conditions")
    assert not metadata.get("player_context") and metadata["player"] is None
    expected = ORACLE["cases"][0]["expected"]
    assert len(sections["summary"]) == len(sections["by_season"]) == 1
    for row in (sections["summary"][0], sections["by_season"][0]):
        for key in ["games", "wins", "losses"]:
            assert row[key] == expected[key]
        for key, value in expected["means"].items():
            assert row[key + "_avg"] == value
        assert row["win_pct"] == 0.5
    assert sections["summary"][0]["team_name"] == "Los Angeles Lakers"
    assert sections["by_season"][0]["season"] == "2023-24"
    table = _table(item, "Team record")
    assert len(table["rows"]) == 1
    cells = dict(zip(table["headers"], table["rows"][0]))
    assert cells["Team"] == "LALLos Angeles Lakers"
    assert cells["W-L"] == "1-1" and int(cells["Games"]) == 2
    assert cells["Win %"] == "50.0%" and float(cells["PPG"]) == 114.5


def _finder(item, metadata, sections):
    assert item["payload"]["route"] == "game_finder"
    assert set(sections) == {"finder"}
    assert metadata["stat"] == "pts" and metadata["min_value"] == 110
    assert metadata["max_value"] is None and not metadata.get("conditions")
    assert not metadata.get("player_context") and metadata["player"] is None
    assert any(
        f["label"] == "pts min" and float(f["value"]) == 110 for f in metadata["applied_filters"]
    )
    expected = sorted(ORACLE["cases"][0]["rows"], key=lambda row: row["pts"], reverse=True)
    rows = sections["finder"]
    assert [row["game_id"] for row in rows] == [row["game_id"] for row in expected]
    table = _table(item, "Game log")
    assert len(table["rows"]) == 2
    for actual, frozen, displayed in zip(rows, expected, table["rows"]):
        assert (
            datetime.fromisoformat(str(actual["game_date"]).replace("Z", "+00:00"))
            .date()
            .isoformat()
            == frozen["game_date"]
        )
        for key in ["team_abbr", "opponent_team_abbr", "pts", "reb", "ast", "wl"]:
            assert actual[key] == frozen[key]
        assert actual["plus_minus"] == frozen["pts"] - frozen["opponent_pts"]
        cells = dict(zip(table["headers"], displayed))
        day = date.fromisoformat(frozen["game_date"])
        assert cells["Date"] == f"{day:%b} {day.day}"
        assert cells["Team"] == "LALLos Angeles Lakers" and cells["Opp"] == "BOSBoston Celtics"
        assert (
            cells["Score"] == f"{frozen['pts']}-{frozen['opponent_pts']}"
            and cells["W/L"] == frozen["wl"]
        )
        for stat in ["pts", "reb", "ast"]:
            assert float(cells[stat.upper()]) == frozen[stat]


def _player(item, metadata, sections):
    assert item["payload"]["route"] == "player_game_summary"
    assert set(sections) == {"summary", "by_season", "game_log"}
    assert metadata["player"] == "LeBron James" and metadata["player_context"]["player_id"] == 2544
    condition = dict(stat="team_pts", min_value=110, max_value=None)
    assert (
        metadata["stat"] == "team_pts"
        and metadata["min_value"] == 110
        and metadata["max_value"] is None
    )
    assert metadata["conditions"] == metadata["threshold_conditions"] == [condition]
    assert any(
        f["label"] == "team_pts min" and float(f["value"]) == 110
        for f in metadata["applied_filters"]
    )
    rows = sections["game_log"]
    assert len(rows) == 1
    assert (
        datetime.fromisoformat(str(rows[0]["game_date"]).replace("Z", "+00:00")).date().isoformat()
        == "2023-12-25"
    )
    for key, value in PLAYER.items():
        assert rows[0][key] == value
    summary = sections["summary"][0]
    assert len(sections["summary"]) == 1 and summary["games"] == 1
    assert summary["player_name"] == "LeBron James"
    assert len(sections["by_season"]) == 1 and sections["by_season"][0]["season"] == "2023-24"
    assert summary["wins"] == 0 and summary["losses"] == 1
    for stat in ["pts", "reb", "ast"]:
        assert summary[stat + "_sum"] == summary[stat + "_avg"] == PLAYER[stat]
    table = _table(item, "Game log")
    assert len(table["rows"]) == 1
    cells = dict(zip(table["headers"], table["rows"][0]))
    assert cells["Date"] == "Dec 25"
    assert cells["TM"] == "LALLos Angeles Lakers" and cells["Opp"] == "BOSBoston Celtics"
    assert cells["W/L"] == "L"
    for stat in ["pts", "reb", "ast"]:
        assert float(cells[stat.upper()]) == PLAYER[stat]
    footers = {row[0]: dict(zip(table["headers"], row)) for row in table["footers"]}
    assert set(footers) == {"Average", "Total"}
    for label in footers:
        for stat in ["pts", "reb", "ast"]:
            assert float(footers[label][stat.upper()]) == PLAYER[stat]


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"] and not item["missing"]
        assert not item["forbidden"] and not item["grainErrors"]
        assert all(value in item["text"] for value in case["text"])
        assert not any(value in item["text"] for value in case["forbidden"])
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert (
                ready["ready"] is True
                and ready["status"] == "ready"
                and ready["immutable_generation"] is True
            )
            assert ready["active_generation"] == ORACLE["generation"] and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        payload = item["payload"]
        assert payload["result_status"] == "ok" and payload["result_reason"] is None
        metadata, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert metadata["team"] == "LAL" and metadata["team_context"] == dict(
            team_id=1610612747, team_abbr="LAL", team_name="Lakers"
        )
        assert metadata["season"] == "2023-24" and metadata["season_type"] == "Regular Season"
        opponents = ["BOS", "LAL"] if item["id"] == "self-union-own-finder" else ["LAL", "BOS"]
        assert metadata["opponents"] == opponents and metadata["opponent"] == ", ".join(opponents)
        assert not metadata.get("opponent_context") and not metadata.get("unsupported_filters")
        assert (
            dict(label="Opponent", kind="team", value=", ".join(opponents))
            in metadata["applied_filters"]
        )
        if item["id"] == "self-union-record":
            _record(item, metadata, sections)
        elif item["id"] == "self-union-own-finder":
            _finder(item, metadata, sections)
        else:
            _player(item, metadata, sections)
    assert seen == {(viewport, ident) for viewport in ["desktop", "mobile"] for ident in by_id}


def test_deployed_self_union_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
