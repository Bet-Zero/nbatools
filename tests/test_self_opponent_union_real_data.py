"""Frozen reciprocal-source samples for explicit self-containing OR unions."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import team_record
from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(
    (Path(__file__).parent / "fixtures/self_opponent_union/primary.json").read_text()
)
NAMES = {"LAL": "Lakers", "BOS": "Celtics", "DEN": "Nuggets", "MIN": "Timberwolves"}


def _qualify(case):
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    teams = pd.read_csv(data_path("raw/team_game_stats/2023-24_regular_season.csv"))
    games = pd.read_csv(data_path("raw/games/2023-24_regular_season.csv"))
    assert (
        not teams.duplicated(["game_id", "team_id"]).any() and not games.game_id.duplicated().any()
    )
    assert not teams.team_id.eq(teams.opponent_team_id).any()
    selected = teams[
        teams.team_abbr.eq(case["subject"]) & teams.opponent_team_abbr.isin(case["opponents"])
    ]
    if case.get("away_only"):
        selected = selected[selected.is_away.eq(1)]
    assert set(selected.game_id) == {r["game_id"] for r in case["rows"]}
    for truth in case["rows"]:
        own = selected[selected.game_id.eq(truth["game_id"])].iloc[0]
        other = teams[
            teams.game_id.eq(truth["game_id"]) & teams.team_id.eq(truth["opponent_team_id"])
        ]
        game = games[games.game_id.eq(truth["game_id"])]
        assert len(other) == len(game) == 1
        other, game = other.iloc[0], game.iloc[0]
        assert other.opponent_team_id == truth["team_id"]
        assert {int(game.home_team_id), int(game.away_team_id)} == {
            truth["team_id"],
            truth["opponent_team_id"],
        }
        assert str(game.is_final).lower() in {"true", "1"} and game.game_date == truth["game_date"]
        for key, value in truth.items():
            assert (other.pts if key == "opponent_pts" else own[key]) == value


def _metadata(result, case, opponents):
    assert result.result_status == "ok", result.metadata
    m = result.metadata
    assert (
        m["team"] == case["subject"] and m["team_context"]["team_id"] == case["rows"][0]["team_id"]
    )
    assert m["opponents"] == opponents and m["opponent"] == ", ".join(opponents)
    assert not m.get("opponent_context") and not m.get("unsupported_filters")
    assert dict(label="Opponent", kind="team", value=", ".join(opponents)) in m["applied_filters"]


@pytest.mark.parametrize("case", ORACLE["cases"], ids=lambda c: c["case"])
@pytest.mark.parametrize("form", ["self_first", "self_last", "leading"])
@pytest.mark.parametrize("operation", ["record", "games"])
def test_self_member_union_matches_frozen_rows_and_keeps_full_scope(
    case, form, operation, monkeypatch
):
    _qualify(case)
    subject = case["subject"]
    other = next(t for t in case["opponents"] if t != subject)
    opponents = [other, subject] if form == "self_last" else [subject, other]
    names = " and ".join(NAMES[t] for t in opponents)
    query = f"{NAMES[subject]} {operation} against {names} in 2023-24"
    if form == "leading":
        query = f"Against {names}, what was {NAMES[subject]} {operation} in 2023-24?"
    captured = []
    original = team_record._compute_record

    def capture(frame):
        captured.append(frame.copy())
        return original(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    result = execute_natural_query(query)
    _metadata(result, case, opponents)
    sections = result.result.to_dict()["sections"]
    expected_ids = {r["game_id"] for r in case["rows"]}
    if operation == "record":
        assert captured and all(set(f.game_id) == expected_ids for f in captured)
        frame = captured[0]
        assert all(frame.team_abbr.eq(subject))
        for stat, total in case["expected"]["sums"].items():
            assert int(frame[stat].sum()) == total
        row = sections["summary"][0]
        for key in ["games", "wins", "losses"]:
            assert row[key] == case["expected"][key]
        for stat, value in case["expected"]["means"].items():
            assert row[stat + "_avg"] == pytest.approx(value, abs=0.001)
    else:
        rows = sections["finder"]
        truth = sorted(case["rows"], key=lambda r: (r["game_date"], r["game_id"]), reverse=True)
        assert [r["game_id"] for r in rows] == [r["game_id"] for r in truth]
        for row, frozen in zip(rows, truth):
            for key in [
                "team_abbr",
                "opponent_team_abbr",
                "pts",
                "reb",
                "ast",
                "wl",
            ]:
                assert row[key] == frozen[key]
            assert row["plus_minus"] == frozen["pts"] - frozen["opponent_pts"]


@pytest.mark.parametrize(
    "owner,floor,ids", [("Lakers", 110, {22300403, 22300684}), ("Celtics", 120, {22300403})]
)
def test_redundant_member_does_not_change_named_stat_owner(owner, floor, ids):
    case = ORACLE["cases"][0]
    _qualify(case)
    result = execute_natural_query(
        f"Lakers games against Celtics and Lakers when {owner} score at least {floor} in 2023-24"
    )
    _metadata(result, case, ["BOS", "LAL"])
    rows = result.result.to_dict()["sections"]["finder"]
    assert {r["game_id"] for r in rows} == ids
    m = result.metadata
    if owner == "Lakers":
        assert m["stat"] == "pts" and not m.get("conditions")
    else:
        assert m["conditions"] == [
            dict(stat="opponent_pts", min_value=120, max_value=None, opponent_team="BOS")
        ]


def test_explicit_player_team_scoring_uses_own_team_with_self_member():
    case = ORACLE["cases"][0]
    _qualify(case)
    path = data_path("raw/player_game_stats/2023-24_regular_season.csv")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "a455e553ceb0b4e74bd4caf37aca482c0a9aab193631b6f2b383b623f861d760"
    )
    players = pd.read_csv(path)
    assert not players.duplicated(["game_id", "player_id", "team_id"]).any()
    sample = players[
        players.player_id.eq(2544)
        & players.team_abbr.eq("LAL")
        & players.opponent_team_abbr.isin(["LAL", "BOS"])
    ]
    assert sample.game_id.tolist() == [22300403]
    assert sample[["pts", "reb", "ast"]].sum().tolist() == [16, 9, 8]
    result = execute_natural_query(
        "Lakers LeBron James games against Lakers and Celtics when Lakers score at least 110 in 2023-24"
    )
    _metadata(result, case, ["LAL", "BOS"])
    assert result.metadata["stat"] == "team_pts"
    assert result.metadata["conditions"] == [dict(stat="team_pts", min_value=110, max_value=None)]
    assert result.metadata["player_context"]["player_id"] == 2544
    sections = result.result.to_dict()["sections"]
    assert [row["game_id"] for row in sections["game_log"]] == [22300403]
    summary = sections["summary"][0]
    assert summary["games"] == 1
    assert [summary[stat + "_sum"] for stat in ["pts", "reb", "ast"]] == [16, 9, 8]


# Root froze these reciprocal-source controls before maker edits. They are
# revealed after independent review; primary.json remains author-known evidence.
REVEALED = json.loads(
    (Path(__file__).parent / "fixtures/self_opponent_union/revealed_controls.json").read_text()
)


@pytest.mark.parametrize(
    "index,query",
    [
        (0, "Knicks away record against Knicks and Heat in 2023-24"),
        (0, "Knicks away record against Heat and Knicks in 2023-24"),
        (0, "Against NYK and MIA, what was Knicks away record in 2023-24?"),
        (1, "Against Lakers and Warriors, what was Warriors record in 2023-24?"),
        (1, "Warriors record against Warriors and Lakers in 2023-24"),
        (1, "GSW record against LAL and GSW in 2023-24"),
    ],
)
def test_root_preimplementation_frozen_source_controls(index, query, monkeypatch):
    assert REVEALED["source_hashes"] == ORACLE["sources"]
    frozen = REVEALED["cases"][index]
    case = dict(
        subject=frozen["subject"],
        opponents=[frozen["subject"], frozen["opponent"]],
        away_only=" away " in frozen["query"],
        rows=[
            {
                **{
                    key: int(row[key])
                    for key in ["game_id", "team_id", "opponent_team_id", "pts", "reb", "ast"]
                },
                **{key: row[key] for key in ["game_date", "team_abbr", "opponent_team_abbr", "wl"]},
            }
            for row in frozen["rows"]
        ],
    )
    _qualify(case)
    captured = []
    original = team_record._compute_record

    def capture(frame):
        captured.append(frame.copy())
        return original(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    result = execute_natural_query(query)
    opponents = (
        [frozen["opponent"], frozen["subject"]]
        if query
        in [
            "Knicks away record against Heat and Knicks in 2023-24",
            "Against Lakers and Warriors, what was Warriors record in 2023-24?",
            "GSW record against LAL and GSW in 2023-24",
        ]
        else case["opponents"]
    )
    _metadata(result, case, opponents)
    assert captured and all(set(frame.game_id) == set(frozen["ids"]) for frame in captured)
    frame = captured[0]
    assert all(frame.team_abbr.eq(frozen["subject"]))
    if case["away_only"]:
        assert all(frame.is_away.eq(1))
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["games"] == len(frozen["ids"])
    for key in ["wins", "losses"]:
        assert row[key] == frozen[key]
    for stat, total in frozen["sums"].items():
        assert int(frame[stat].sum()) == total
        assert row[stat + "_avg"] == pytest.approx(total / len(frozen["ids"]), abs=0.001)
