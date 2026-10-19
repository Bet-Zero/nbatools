"""Scalar Yes/DNP No/unknown derives from frozen canonical source facts."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
PATH = Path(__file__).parent / "fixtures/qualified_scalar_played/source_and_baseline.json"
ORACLE = json.loads(PATH.read_text())


@pytest.mark.parametrize(
    "index",
    range(7),
    ids=[
        "tatum-positive",
        "davis-explicit-dnp",
        "tatum-explicit-dnp",
        "tatum-unknown",
        "curry-unknown",
        "davis-membership-unknown",
        "basic-lebron-positive",
    ],
)
def test_scalar_participation_from_original_game_and_qualified_sources(index):
    assert (
        hashlib.sha256(PATH.read_bytes()).hexdigest()
        == "1d55567df1bd2cd8ea400b1d24ac0da1e5de22fe7c917c566c4c0984fbb3ddd1"
    )
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    case = ORACLE["cases"][index]
    season = case["season"]

    def raw(kind):
        with data_path(f"raw/{kind}/{season}_regular_season.csv").open() as f:
            return list(csv.DictReader(f))

    team_rows, player_rows, observations = (
        raw(k) for k in ("team_game_stats", "player_game_stats", "player_game_availability")
    )
    original = case["selected_original_team_row"]
    candidates = sorted(
        [
            r
            for r in team_rows
            if r["team_id"] == original["team_id"]
            and (not case["opponent"] or r["opponent_team_id"] == original["opponent_team_id"])
        ],
        key=lambda r: (r["game_date"], int(r["game_id"])),
        reverse=True,
    )
    assert [int(r["game_id"]) for r in candidates] == case["original_candidate_game_ids"]
    assert candidates[0] == original
    player = case["canonical_player"]
    gid, pid, day = int(original["game_id"]), player["player_id"], original["game_date"]
    facts = [r for r in observations if int(r["game_id"]) == gid and int(r["player_id"]) == pid]
    positive = [
        r
        for r in player_rows
        if int(r["game_id"]) == gid and int(r["player_id"]) == pid and float(r["minutes"]) > 0
    ]
    assert facts == case["report_observation_rows"]
    assert positive == case["positive_appearance_rows"]
    for row in [*facts, *positive]:
        assert int(row["player_id"]) == pid and row["player_name"] == player["player_name"]
        assert row["game_date"] == day
        assert row["team_id"] in (original["team_id"], original["opponent_team_id"])
    for fact in facts:
        assert fact["coverage_scope"] == "listed_player_rows_only"
        pdf = data_path("raw/player_game_availability_sources/" + fact["source_sha256"] + ".pdf")
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == fact["source_sha256"]
    truth = case["desired_boolean"]
    if truth is True:
        assert len(positive) == 1
        assert not facts or facts[0]["participation_state"] == "played"
    elif truth is False:
        assert not positive and len(facts) == 1
        assert facts[0]["participation_state"] == "did_not_play" and facts[0]["source_comment"]
    else:
        assert not positive and not facts
    queries = [case["query"]]
    if index == 5:
        queries.append("Did AD play last game in 2025-26?")
    for query in queries:
        result = execute_natural_query(query)
        assert result.route == "game_finder" and result.metadata["intent"] == "finder"
        assert result.metadata["player"] == player["player_name"]
        assert result.metadata["player_context"] == player
        assert result.metadata["stat"] is None
        assert result.metadata["min_value"] is None and result.metadata["max_value"] is None
        assert not result.metadata["threshold_conditions"]
        assert not result.metadata["with_player"] and not result.metadata["without_player"]
        filters = result.metadata.get("applied_filters") or []
        if truth is None:
            assert result.result_status == "no_result" and result.result_reason not in (
                "no_match",
                "error",
            )
            assert not result.metadata.get("answer_phrase")
            assert not result.result.to_dict()["sections"]
            assert not any(f["label"] == "Played check" for f in filters)
            if query.startswith("Did AD"):
                assert result.metadata["team"] is None and not result.metadata.get("team_context")
            continue
        assert result.result_status == "ok"
        phrase = result.metadata["answer_phrase"]
        assert phrase.startswith(f"{'Yes' if truth else 'No'}: {player['player_name']} ")
        assert day in phrase
        assert {
            "label": "Played check",
            "value": player["player_name"] + " played",
            "kind": "player",
        } in filters
        assert any(
            f["label"] == "Sample selection" and "original team game" in f["value"] for f in filters
        )
        rows = result.result.to_dict()["sections"]["finder"]
        assert len(rows) == 1 and int(rows[0]["game_id"]) == gid
        assert str(rows[0]["game_date"])[:10] == day
        assert rows[0]["team_id"] == int(original["team_id"])
        assert rows[0]["opponent_team_id"] == int(original["opponent_team_id"])
        assert rows[0]["wl"] == original["wl"]
        assert [rows[0][k] for k in ("pts", "reb", "ast")] == [
            int(original[k]) for k in ("pts", "reb", "ast")
        ]
        assert not any(k in rows[0] for k in ("player_id", "player_name", "player"))
        assert any(
            "team-game totals" in c and "not the checked player's statistics" in c
            for c in result.result.caveats
        )
        if truth:
            for stat, word in [("pts", "points"), ("reb", "rebounds"), ("ast", "assists")]:
                assert f"{float(positive[0][stat]):g} {word}" in phrase
        else:
            assert ": 0 points" not in phrase and "his last game was" not in phrase


@pytest.mark.parametrize(
    "predicate,truth",
    [
        ("at least 30 minutes", True),
        ("fewer than 30 minutes", False),
        ("at least 40 minutes or score at least 20 points", True),
        ("at least 40 minutes or score at least 30 points", False),
        ("at least 40 minutes or win", True),
        ("at least 40 minutes or lose", False),
        ("at least 30 minutes and score at least 20 points", True),
        ("at least 30 minutes and score at least 30 points", False),
        ("at least 30 minutes and win", True),
        ("at least 30 minutes and lose", False),
    ],
)
def test_source_qualified_legacy_minutes_checks_keep_statistical_contract(predicate, truth):
    path = "raw/player_game_stats/2023-24_regular_season.csv"
    assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == ORACLE["source_hashes"][path]
    with data_path(path).open() as stream:
        raw = list(csv.DictReader(stream))
    rows = sorted(
        [r for r in raw if int(r["player_id"]) == 2544],
        key=lambda r: (r["game_date"], int(r["game_id"])),
    )
    source = rows[-1]
    assert source == ORACLE["cases"][6]["positive_appearance_rows"][0]
    assert int(source["game_id"]) == 22301195 and source["game_date"] == "2024-04-14"
    assert int(source["team_id"]) == 1610612747
    assert [float(source[k]) for k in ("minutes", "pts", "reb", "ast")] == [38, 28, 11, 17]
    team_path = "raw/team_game_stats/2023-24_regular_season.csv"
    assert (
        hashlib.sha256(data_path(team_path).read_bytes()).hexdigest()
        == ORACLE["source_hashes"][team_path]
    )
    with data_path(team_path).open() as stream:
        teams = list(csv.DictReader(stream))
    own = next(
        r for r in teams if r["game_id"] == source["game_id"] and r["team_id"] == source["team_id"]
    )
    other = next(
        r
        for r in teams
        if r["game_id"] == source["game_id"] and r["team_id"] == source["opponent_team_id"]
    )
    assert own == ORACLE["cases"][6]["selected_original_team_row"]
    assert own["game_date"] == other["game_date"] == source["game_date"]
    assert (
        own["opponent_team_id"] == other["team_id"] and other["opponent_team_id"] == own["team_id"]
    )
    assert own["wl"] == "W" and float(own["pts"]) > float(other["pts"])
    result = execute_natural_query(f"Did LeBron play {predicate} last game in 2023-24?")
    assert result.result_status == "ok" and result.route == "player_game_finder"
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith("Yes:" if truth else "No:")
    assert "38 minutes" in phrase and source["game_date"] in phrase
    actual = result.result.to_dict()["sections"]["finder"]
    assert len(actual) == 1 and int(actual[0]["game_id"]) == 22301195
    assert int(actual[0]["player_id"]) == 2544
    assert actual[0]["team_abbr"] == own["team_abbr"] == "LAL"
    assert actual[0]["opponent_team_abbr"] == other["team_abbr"] == "NOP"
    assert actual[0]["wl"] == own["wl"]
    assert str(actual[0]["game_date"])[:10] == source["game_date"]
    assert [actual[0][k] for k in ("minutes", "pts", "reb", "ast")] == [38, 28, 11, 17]
    assert not any(f["label"] == "Played check" for f in result.metadata["applied_filters"])
