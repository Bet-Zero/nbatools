"""Finite K12 delivery assertions reuse existing accepted numerical oracles.

This adapter checks delivered identity, basis, scope and answer values. Existing
source-key and independent-arithmetic evidence remains attached to its original
cases; identical qualified bytes are required here, without rebuilding it.
"""

import csv
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query
from tests.test_k04_ranking_real_data import verify_answer as _assert_ranking
from tests.test_k11_population_real_data import _assert_case as _assert_population

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "working/nba-tools-completion-program/k12-delivery-oracle.json"
ORACLE_SHA = "07c1f729b8751811ad63b00e0e2bb80928a5b6e932e2cddaf53c89066a89dbda"
IDS = (
    "K12-S1",
    "K12-R1",
    "K12-B1",
    "K12-C1",
    "K12-L1",
    "K12-X1",
    "K12-M1",
    "K12-Z1",
    "K12-E1",
    "K12-N1",
    "K12-H1",
)


CONTROLS = {
    "K12-R1-win-loss": (
        "K12-R1",
        "Celtics win-loss record against Knicks from 2023-11-01 to 2024-03-01",
    ),
}


@lru_cache(maxsize=1)
def _qualified_sources():
    raw = ORACLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORACLE_SHA
    oracle = json.loads(raw)
    # Independently qualified against all 60 inventory-matched player-game files.
    index = data_path("metadata/player_names.csv").read_bytes()
    assert hashlib.sha256(index).hexdigest() == (
        "f7097aaefe54b986ea5036e3c9ca5ca4c05a58266aa6cd0e2b4710e4cfe5f1b2"
    )
    for name, digest in oracle["reused_oracles"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    sources = {}
    for name, digest in oracle["source_hashes"].items():
        path = data_path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        with path.open() as stream:
            sources[name] = list(csv.DictReader(stream))
    return oracle, sources


def _bindings(oracle):
    cases = {}
    for frozen in oracle["cases"]:
        case = dict(frozen)
        if ref := frozen["reference"]:
            document = json.loads((ROOT / ref["file"]).read_text())
            entries = document if isinstance(document, list) else document["cases"]
            original = (
                entries[ref["id"]]
                if isinstance(entries, dict)
                else next(row for row in entries if row["id"] == ref["id"])
            )
            assert original["query"] == case["query"]
            case["original"] = original
        cases[case["id"]] = case
    for ident, (source, query) in CONTROLS.items():
        cases[ident] = dict(cases[source], query=query)
    return cases


@pytest.fixture
def qualified_oracle():
    return _qualified_sources()


def _values(actual, truth):
    for field, value in truth.items():
        assert actual[field] == pytest.approx(value, abs=0.00051), (field, actual, truth)


def _keys(rows):
    return sorted((int(row["game_id"]), int(row["team_id"]), int(row["player_id"])) for row in rows)


def _assert_case(result, case, sources):
    ident, meta = case["id"], result.metadata
    assert meta["query_text"] == case["query"]
    assert not meta.get("unsupported_filters")
    body = result.result.to_dict()
    sections = body["sections"]
    if ident == "K12-N1":
        assert meta["season"] == "2026-27"
        assert result.result_status == "no_result" and result.result_reason == "no_data"
        assert not sections and meta.get("primary_count") is None
        return
    original = case["original"]
    assert meta["season_type"] == "Regular Season"
    if ident == "K12-H1":
        assert result.result_status == "ok" and result.result_reason is None
        expected = original["expected"]
        summary = sections["summary"][0]
        assert summary["player_name"] == "Patrick Ewing"
        assert meta["player_context"]["player_id"] == 121
        assert (summary["season_start"], summary["season_end"]) == ("1996-97", "2001-02")
        _values(summary, {key: expected[key] for key in ("games", "wins", "losses")})
        _values(summary, {stat + "_sum": value for stat, value in expected["sums"].items()})
        _values(summary, {stat + "_avg": value for stat, value in expected["averages"].items()})
        assert _keys(sections["game_log"]) == sorted(map(tuple, expected["ids"]))
        assert any(
            "covers 1996-97 onward" in text and "earlier seasons are not in the data" in text
            for text in meta.get("notes", [])
        )
        return
    assert meta["season"] == "2023-24"
    if ident in ("K12-C1", "K12-Z1", "K12-E1"):
        expected_player = {"K12-C1": 1628973, "K12-Z1": 203999, "K12-E1": 1628973}[ident]
        assert meta["player_context"]["player_id"] == expected_player
    if ident == "K12-E1":
        assert result.result_status == "no_result" and result.result_reason == "no_match"
        assert not sections and meta.get("primary_count") is None
        return
    assert result.result_status == "ok" and result.result_reason is None
    if ident in ("K12-S1", "K12-R1"):
        assert len(sections["summary"]) == 1
        summary = sections["summary"][0]
        _values(summary, {key: original[key] for key in ("games", "wins", "losses")})
        _values(summary, {stat + "_avg": value for stat, value in original["means"].items()})
        if ident == "K12-S1":
            assert summary["player_name"] == "Stephen Curry"
            assert meta["player_context"]["player_id"] == 201939
            _values(summary, {stat + "_sum": value for stat, value in original["sums"].items()})
            assert _keys(sections["game_log"]) == sorted(map(tuple, original["expected_keys"]))
        else:
            assert meta["team"] == "BOS" and meta["opponent"] == "NYK"
            assert meta["start_date"] == "2023-11-01" and meta["end_date"] == "2024-03-01"
            assert summary["team_name"] == "Boston Celtics"
            assert meta["team_context"]["team_id"] == 1610612738
        return
    if ident == "K12-B1":
        _assert_ranking(original, result)
        return
    if ident == "K12-L1":
        _assert_population(result, original, sources)
        return
    if ident in ("K12-C1", "K12-Z1"):
        count = len(original["keys"])
        assert sections["count"] == [{"count": count}]
        assert meta["primary_count"] == count and "games" in meta["count_phrase"]
        return
    if ident == "K12-X1":
        assert meta["team"] == "DEN" and meta["opponent"] == "MIN"
        assert meta["stat"] == "pts" and meta["min_value"] == 110
        assert meta["split_type"] == "home_away"
        assert sections["summary"][0]["games_total"] == 2
        assert sections["summary"][0]["team_name"] == "Denver Nuggets"
        actual = {row["bucket"]: row for row in sections["split_comparison"]}
        assert actual.keys() == {"home", "away"}
        for bucket in original["buckets"]:
            _values(
                actual[bucket["bucket"]], {key: bucket[key] for key in ("games", "wins", "losses")}
            )
            _values(
                actual[bucket["bucket"]],
                {stat + "_avg": value for stat, value in bucket["means"].items()},
            )
        return
    assert ident == "K12-M1"
    assert len(sections["summary"]) == 2
    summaries = {row["player_name"]: row for row in sections["summary"]}
    comparisons = {row["metric"]: row for row in sections["comparison"]}
    names = {sample["name"] for sample in original["samples"]}
    assert summaries.keys() == names
    for sample in original["samples"]:
        actual = summaries[sample["name"]]
        assert {row["player_name"]: row["player_id"] for row in meta["players_context"]}[
            sample["name"]
        ] == sample["entity"]
        expected = {key: sample[key] for key in ("games", "wins", "losses")}
        expected.update({stat + "_avg": value for stat, value in sample["means"].items()})
        expected.update({stat + "_sum": value for stat, value in sample["sums"].items()})
        _values(actual, expected)
        for field, value in expected.items():
            assert set(comparisons[field]) == {"metric", *names}
            assert comparisons[field][sample["name"]] == pytest.approx(value, abs=0.00051)


@pytest.mark.parametrize("ident", (*IDS, *CONTROLS))
def test_k12_answer_delivery(qualified_oracle, ident):
    oracle, sources = qualified_oracle
    case = _bindings(oracle)[ident]
    _assert_case(execute_natural_query(case["query"]), case, sources)
