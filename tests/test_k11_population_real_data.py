"""K11 player-game populations against independently frozen qualified raw rows.

The oracle was frozen before application baselining. No engine loader, roster
helper, parser or ranking helper supplies expected membership or values.
"""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = (
    Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program/k11-raw-oracle.json"
)
ORACLE_SHA = "b2491ba1ba5026bd0c7a853e1b44f7aa8c72adc71fbd8bbb077f26975cd77649"
IDS = (
    "K11-L1",
    "K11-L2",
    "K11-T1",
    "K11-T2",
    "K11-R1",
    "K11-R2",
    "K11-P1",
    "K11-P2",
    "K11-P3",
    "K11-C1",
)

CONTROLS = {
    "K11-R2-leading-season": ("K11-R2", "In 1998-99, rookies top 5 scoring performances"),
}


def _bindings(oracle):
    cases = {case["id"]: case for case in oracle["cases"]}
    for key, (source, query) in CONTROLS.items():
        cases[key] = dict(cases[source], query=query)
    return cases


def _qualified_sources():
    raw = ORACLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORACLE_SHA
    oracle = json.loads(raw)
    sources = {}
    for name, digest in oracle["source_hashes"].items():
        path = data_path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        with path.open() as stream:
            sources[name] = list(csv.DictReader(stream))
    return oracle, sources


@pytest.fixture
def qualified_oracle():
    return _qualified_sources()


def _sample(case, sources):
    season = case["season"]
    sample = [
        row
        for row in sources[f"raw/player_game_stats/{season}_regular_season.csv"]
        if (not case.get("team") or row["team_abbr"] == case["team"])
        and (not case.get("opponent") or row["opponent_team_abbr"] == case["opponent"])
    ]
    unknown = 0
    if case.get("position") or case.get("rookies"):
        roster = sources[f"raw/rosters/{season}.csv"]
        entries = {}
        for row in roster:
            assert row["season"] == season
            entries.setdefault(row["player_id"], []).append(row)
        unknown = sum(row["player_id"] not in entries for row in sample)
        sample = [
            row
            for row in sample
            if any(
                (not case.get("rookies") or float(entry["experience_years"]) == 0)
                and (not case.get("position") or entry["position"] in case["codes"])
                for entry in entries.get(row["player_id"], [])
            )
        ]
    assert len(sample) == case["expected"]["candidate_rows"]
    assert unknown == case["expected"]["unknown_rows"]
    return sorted(
        sample, key=lambda row: (float(row[case["metric"]]), row["game_date"]), reverse=True
    )


def _identity(row):
    return (
        str(row["game_id"]).zfill(10),
        int(row["player_id"]),
        row["player_name"],
        row["team_abbr"],
        row["opponent_team_abbr"],
        str(row["game_date"])[:10],
        float(row["pts"]),
        float(row["reb"]),
        float(row["ast"]),
    )


def _assert_rows(actual, expected, metric, *, boundary_rows=(), date_tiebreak=True):
    assert len(actual) == len(expected)
    assert [int(row["rank"]) for row in actual] == list(range(1, len(expected) + 1))

    def key(row):
        return float(row[metric]), str(row["game_date"])[:10] if date_tiebreak else ""

    assert [key(row) for row in actual] == [key(row) for row in expected]
    # Every row must match one exact qualified source identity and all values.
    # Only genuine equal-key boundary rows may substitute for a tied exemplar.
    allowed = {_identity(row) for row in [*expected, *boundary_rows]}
    identities = [_identity(row) for row in actual]
    assert len(identities) == len(set(identities))
    assert set(identities) <= allowed


def _assert_case(result, case, sources):
    assert result.result_status == "ok" and result.result_reason is None
    meta = result.metadata
    assert meta["route"] == (
        "top_player_games" if case["id"] in ("K11-L1", "K11-L2") else "player_game_finder"
    )
    assert meta["query_text"] == case["query"]
    assert meta["stat"] == case["metric"]
    assert meta["season"] == case["season"] and meta["season_type"] == "Regular Season"
    assert not meta.get("player") and not meta.get("unsupported_filters")
    assert meta.get("team") == case.get("team")
    assert meta.get("opponent") == case.get("opponent")
    body = result.result.to_dict()
    rows = body["sections"]["leaderboard" if meta["route"] == "top_player_games" else "finder"]
    _assert_rows(
        rows,
        case["expected"]["rows"],
        case["metric"],
        boundary_rows=case["expected"]["boundary_rows"],
        date_tiebreak=case["date_tiebreak"],
    )
    _assert_rows(
        rows,
        _sample(case, sources)[: case["limit"]],
        case["metric"],
        boundary_rows=case["expected"]["boundary_rows"],
        date_tiebreak=case["date_tiebreak"],
    )
    source_rows = {
        (str(row["game_id"]).zfill(10), int(row["player_id"])): row
        for row in sources[f"raw/player_game_stats/{case['season']}_regular_season.csv"]
    }
    for row in rows:
        source = source_rows[(str(row["game_id"]).zfill(10), int(row["player_id"]))]
        for name in ("team_name", "opponent_team_name"):
            assert row[name] == source[name]
    assert {row["season"] for row in rows} == {case["season"]}
    assert {row["season_type"] for row in rows} == {"Regular Season"}
    if unknown := case["expected"]["unknown_rows"]:
        caveats = body["caveats"]
        assert any(
            "Incomplete population" in text
            and f"{unknown} games" in text
            and "known" in text
            and "classification" in text
            for text in caveats
        )
        assert {row["population_scope"] for row in rows} == {
            "Incomplete population: known roster classifications only"
        }
    else:
        assert not any("Incomplete population" in text for text in body.get("caveats", []))
    filters = meta.get("applied_filters", [])
    if case.get("rookies"):
        assert any(f["kind"] == "position" and f["value"] == "Rookies" for f in filters)
    if case.get("position"):
        assert any(
            f["kind"] == "position" and case["position"].lower() in str(f["value"]).lower()
            for f in filters
        )


@pytest.mark.parametrize("ident", (*IDS, *CONTROLS))
def test_k11_population_source_case(qualified_oracle, ident):
    oracle, sources = qualified_oracle
    case = _bindings(oracle)[ident]
    _assert_case(execute_natural_query(case["query"]), case, sources)
