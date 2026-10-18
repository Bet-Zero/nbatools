"""Finite K01 identity/scope acceptance with independently frozen raw populations."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import team_record
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
HISTORY = json.loads(Path(__file__).with_name("k01_historical_expected.json").read_text())["cases"]
EWING_SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(1996, 2002)]
CASES = [
    ("A1_plain", "Nikola Jokic stats in 2023-24", 203999, ["2023-24"], None),
    ("A1_accent", "Nikola Jokić stats in 2023-24", 203999, ["2023-24"], None),
    ("A1_alias", "Joker's 2023-24 averages", 203999, ["2023-24"], None),
    ("A2", "Nikola Jovic stats in 2024-25", 1631107, ["2024-25"], None),
    ("B1", "Marcus Williams Spurs stats in 2007-08", 201173, ["2007-08"], "SAS"),
    ("B1_collision", "Marcus Williams stats in 2007-08", 200766, ["2007-08"], None),
    ("C1_old", "Bobby Portis stats in 2024-25", 1626171, ["2024-25"], None),
    ("C1_new", "Bobby Portis Jr. stats in 2024-25", 1626171, ["2024-25"], None),
    (
        "C1_union",
        "Bobby Portis stats from 2023-24 through 2024-25",
        1626171,
        ["2023-24", "2024-25"],
        None,
    ),
    ("D1", "Thunder record from 2007-08 through 2008-09", None, ["2007-08", "2008-09"], None),
    ("D1_era", "Seattle SuperSonics record in 2007-08", None, ["2007-08"], None),
    ("D1_wording", "What record did the Sonics finish with in 2007-08?", None, ["2007-08"], None),
    ("E1", "Patrick Ewing career stats", 121, EWING_SEASONS, None),
    ("E1_season", "Patrick Ewing stats in 1996-97", 121, ["1996-97"], None),
]
FROZEN = {
    (203999, "2023-24"): (
        79,
        [2085, 976, 708],
        "d9b737266eff8066eacc7a15917a273e348992626f9e6cf78d80bde352384a71",
    ),
    (1631107, "2024-25"): (
        46,
        [494, 180, 131],
        "982a6efdd890b8d789690016f92ca487606888001329938f06b1c3e0a01bc202",
    ),
    (1626171, "2023-24"): (
        82,
        [1130, 607, 104],
        "2c187e487b0e11b00fb2a1eec398664ab864a6156d9d0ef27dde915a4e70bacf",
    ),
    (1626171, "2024-25"): (
        49,
        [680, 411, 104],
        "6e1add83e579938e581df7366c4f2c8b425adec7b2cb121f3854efc1557d4c4e",
    ),
}


def _keys(frame, player):
    columns = ["game_id", "team_id"] + (["player_id"] if player else [])
    assert not frame.duplicated(columns).any()
    return frame[columns].astype(int).sort_values(columns).values.tolist()


@pytest.mark.parametrize("ident,query,player,seasons,team", CASES, ids=[c[0] for c in CASES])
def test_k01_identity_and_covered_scope(ident, query, player, seasons, team, monkeypatch):
    frames = []
    results = []
    for season in seasons:
        # Required files are read unconditionally: no missing-season skip oracle.
        teams = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv")
        assert not teams.empty and not teams.duplicated(["game_id", "team_id"]).any()
        if player is None:
            rows = teams.loc[teams.team_id.eq(1610612760)].copy()
        else:
            raw = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
            rows = raw.loc[raw.player_id.eq(player)].copy()
            if team:
                rows = rows.loc[rows.team_abbr.eq(team)]
            joined = rows.merge(
                teams[["game_id", "team_id", "wl"]],
                on=["game_id", "team_id"],
                validate="many_to_one",
            )
            assert len(joined) == len(rows)
            results.extend(joined.wl.tolist())
            if (player, season) in FROZEN:
                count, sums, digest = FROZEN[player, season]
                assert len(rows) == count
                assert rows[["pts", "reb", "ast"]].sum().tolist() == sums
                assert (
                    hashlib.sha256(
                        json.dumps(_keys(rows, True), separators=(",", ":")).encode()
                    ).hexdigest()
                    == digest
                )
        assert not rows.empty
        frames.append(rows)
    expected = pd.concat(frames, ignore_index=True)
    historical_key = {
        "B1": "K01-B1",
        "D1": "K01-D1",
        "D1_era": "K01-D1-2007-08",
        "D1_wording": "K01-D1-2007-08",
        "E1": "K01-E1",
        "E1_season": "K01-E1-1996-97",
    }.get(ident)
    if historical_key:
        frozen = HISTORY[historical_key]["expected"]
        assert _keys(expected, player is not None) == frozen["ids"]
        for stat in ("pts", "reb", "ast"):
            assert expected[stat].sum() == frozen["sums"][stat]
    captured = []
    original = team_record._compute_record

    def record(frame):
        captured.append(frame.copy())
        return original(frame)

    monkeypatch.setattr(team_record, "_compute_record", record)
    response = execute_natural_query(query)
    payload = response.to_dict()
    assert response.result_status == "ok", payload
    sections = payload["sections"]
    assert len(sections["summary"]) == 1
    row = sections["summary"][0]
    assert row["games"] == len(expected)
    assert row["season_start"] == seasons[0] and row["season_end"] == seasons[-1]
    assert row["season_type"] == "Regular Season"
    actual = pd.DataFrame(sections["game_log"]) if player else captured[-1]
    assert _keys(actual, player is not None) == _keys(expected, player is not None)
    for stat in ("pts", "reb", "ast"):
        assert row[f"{stat}_avg"] == pytest.approx(expected[stat].mean(), abs=0.00051)
        if player:
            assert row[f"{stat}_sum"] == expected[stat].sum()
    wl = pd.Series(results) if player else expected.wl
    assert row["wins"] == int(wl.eq("W").sum())
    assert row["losses"] == int(wl.eq("L").sum())
    if ident == "B1_collision":
        assert any(
            "More than one player is named Marcus Williams" in n
            for n in response.metadata.get("notes", [])
        )
    if ident == "D1":
        assert any("Seattle SuperSonics" in n for n in payload["caveats"])
    notes = response.metadata.get("notes", [])
    if ident == "E1":
        assert any(
            "covers 1996-97 onward" in n and "earlier seasons are not in the data" in n
            for n in notes
        )
    else:
        assert not any("career_span:" in n for n in notes)
