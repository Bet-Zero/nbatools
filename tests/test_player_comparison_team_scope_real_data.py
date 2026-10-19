"""Frozen raw identities/samples, not natural/structured agreement, are the oracle."""

import csv
import hashlib
import json
from functools import wraps
from pathlib import Path

import pytest

from nbatools.commands import player_compare
from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
FIXTURE = Path(__file__).parent / "fixtures/player_comparison_team_scope/source_and_baseline.json"
SOURCE = json.loads(FIXTURE.read_text())
PLAYERS = ["Luka Dončić", "Anthony Davis"]


def authenticate():
    assert (
        hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        == "4d77fb2982004cf073dbdc2865db2437cfc82f9a8f57d478b14f6ae19c460205"
    )
    for path, sha in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == sha
    for kind, rows in [
        ("games", SOURCE["full_catalog_rows"]),
        ("team_game_stats", SOURCE["full_reciprocal_team_rows"]),
        (
            "player_game_stats",
            [r for s in SOURCE["source_samples"] for r in s["selected_rows"]]
            + SOURCE["excluded_dallas_luka_control"]["selected_rows"],
        ),
    ]:
        with data_path(f"raw/{kind}/2024-25_regular_season.csv").open() as stream:
            raw = list(csv.DictReader(stream))
        assert all(row in raw for row in rows)


def labels(result, order=PLAYERS):
    m = result.metadata
    assert result.route == "player_compare" and result.result_status == "ok", m
    assert [p["player_name"] for p in m["players_context"]] == list(order)
    assert {p["player_id"] for p in m["players_context"]} == {1629029, 203076}
    assert m["team"] == "LAL" and m["team_context"]["team_id"] == 1610612747
    assert m["opponent"] == "GSW" and m["opponent_context"]["team_id"] == 1610612744
    assert m["season"] == "2024-25" and m["season_type"] == "Regular Season"
    assert not m["with_player"] and not m["without_player"] and not m["head_to_head_used"]
    assert {"label": "Playing for", "value": "LAL", "kind": "team"} in m["applied_filters"]
    assert {"label": "Opponent", "value": "GSW", "kind": "team"} in m["applied_filters"]
    assert not any("unsupported_boundary:" in n for n in m.get("notes") or [])


@pytest.mark.parametrize(
    "query,reverse",
    [
        (SOURCE["primary_query"], False),
        (
            "How did Luka Doncic and Anthony Davis compare for the Lakers against the Warriors in 2024-25?",
            False,
        ),
        ("Compare Anthony Davis and Luka Doncic for the Lakers against Warriors in 2024-25", True),
        (
            "Compare Luka Doncic and Anthony Davis while playing for the Lakers against Golden State in 2024-25",
            False,
        ),
        (
            "Compare Luka Doncic and Anthony Davis only in their games for the Lakers against the Warriors in 2024-25",
            False,
        ),
        (
            "For the Lakers in 2024-25, compare Luka Doncic and Anthony Davis against Golden State",
            False,
        ),
        ("Compare Luka Doncic with Anthony Davis for Lakers against Warriors in 2024-25", False),
    ],
)
def test_shared_team_source_samples_and_truthful_comparison(query, reverse, monkeypatch):
    authenticate()
    captured = []
    compute = player_compare.summarize_player

    @wraps(compute)
    def capture(frame, *args, **kwargs):
        captured.append(frame.copy())
        return compute(frame, *args, **kwargs)

    monkeypatch.setattr(player_compare, "summarize_player", capture)
    result = execute_natural_query(query)
    order = PLAYERS[::-1] if reverse else PLAYERS
    labels(result, order)
    assert len(captured) == 2
    expected_by_name = {s["player_name"]: s for s in SOURCE["source_samples"]}
    for row, frame, name in zip(result.result.to_dict()["sections"]["summary"], captured, order):
        expected = expected_by_name[name]
        assert row["player_name"] == name
        assert len(frame) == row["games"] == expected["games"]
        assert sorted(frame.game_id.astype(int)) == sorted(expected["game_ids"])
        assert set(frame.player_id.astype(int)) == {expected["player_id"]}
        assert set(frame.team_id.astype(int)) == {1610612747}
        assert set(frame.opponent_team_id.astype(int)) == {1610612744}
        expected_keys = {
            (
                int(r["game_id"]),
                r["game_date"],
                int(r["player_id"]),
                int(r["team_id"]),
                int(r["opponent_team_id"]),
            )
            for r in expected["selected_rows"]
        }
        actual_keys = {
            (
                int(r.game_id),
                str(r.game_date)[:10],
                int(r.player_id),
                int(r.team_id),
                int(r.opponent_team_id),
            )
            for r in frame.itertuples()
        }
        assert actual_keys == expected_keys
        assert row["wins"] == expected["wins"] and row["losses"] == expected["losses"]
        for stat in ("pts", "reb", "ast"):
            assert frame[stat].sum() == row[stat + "_sum"] == expected["totals"][stat]
            assert row[stat + "_avg"] == float(expected["means_3dp"][stat])


def test_whole_season_shared_team_filters_both_traded_players():
    authenticate()
    result = execute_natural_query("Compare Luka Doncic and Anthony Davis for Lakers in 2024-25")
    assert result.route == "player_compare" and result.result_status == "ok"
    for row in result.result.to_dict()["sections"]["summary"]:
        expected = next(
            s
            for s in SOURCE["whole_season_team_scope_controls"]
            if s["team"] == "LAL" and s["player_name"] == row["player_name"]
        )
        assert row["games"] == expected["games"]
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_sum"] == expected["totals"][stat]
            assert row[stat + "_avg"] == float(expected["means_3dp"][stat])


@pytest.mark.parametrize(
    "predicate,ids",
    [
        ("over 35.99999 points", [[], [22400644]]),
        ("under 36.00001 points", [[22401117], [22400408, 22400644]]),
        ("at most 0 points", [[], [22400408]]),
        ("under 0 points", [[], []]),
        ("between 0.1 and 0.9 points", [[], []]),
    ],
)
def test_exact_integer_count_source_cutoffs_partial_and_full_empty(predicate, ids, monkeypatch):
    authenticate()
    captured = []
    original = player_compare.filter_player_games

    @wraps(original)
    def capture(*args, **kwargs):
        frame = original(*args, **kwargs)
        captured.append(frame.copy())
        return frame

    monkeypatch.setattr(player_compare, "filter_player_games", capture)
    result = execute_natural_query(SOURCE["primary_query"] + " with " + predicate)
    assert len(captured) == 2
    assert [sorted(f.game_id.astype(int)) for f in captured] == ids
    if not any(ids):
        assert result.result_status == "no_result" and result.result_reason == "no_match"
        assert not result.result.to_dict()["sections"]
    else:
        labels(result)
        for row, selected, sample in zip(
            result.result.to_dict()["sections"]["summary"], ids, SOURCE["source_samples"]
        ):
            facts = [r for r in sample["selected_rows"] if int(r["game_id"]) in selected]
            assert row["games"] == len(facts)
            for stat in ("pts", "reb", "ast"):
                total = sum(int(r[stat]) for r in facts)
                assert row[stat + "_sum"] == total
                assert row[stat + "_avg"] == (round(total / len(facts), 3) if facts else None)
    values = [
        f["value"] for f in result.metadata["applied_filters"] if f["label"] == "Count filter"
    ]
    assert len(values) == 1
    if predicate != "at most 0 points":
        assert "integer execution:" in values[0]
    assert not result.metadata.get("with_player")


def test_existing_structured_sample_and_unfiltered_opponent_control():
    authenticate()
    scoped = execute_structured_query(
        "player_compare",
        player_a=PLAYERS[0],
        player_b=PLAYERS[1],
        season="2024-25",
        season_type="Regular Season",
        team="LAL",
        opponent="GSW",
    )
    labels(scoped)
    unscoped = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis against Warriors in 2024-25"
    )
    assert unscoped.route == "player_compare" and unscoped.result_status == "ok"
    assert unscoped.metadata["team"] is None
    assert not any(f["label"] == "Playing for" for f in unscoped.metadata["applied_filters"])
    for row, expected in zip(
        unscoped.result.to_dict()["sections"]["summary"], SOURCE["unfiltered_opponent_controls"]
    ):
        assert row["games"] == expected["games"]
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_sum"] == expected["totals"][stat]
