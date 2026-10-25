"""K10 acceptance against the independently frozen, qualified playoff rows."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = (
    Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program/k10-raw-oracle.json"
)
ORACLE_SHA = "ced583f51b83150d76d3675146e4516fa2dd16916799340d250ea9c3c34b597d"
IDS = ("K10-G1", "K10-S1", "K10-A1", "K10-R1", "K10-Q1", "K10-F1", "K10-T1", "K10-T2")
ROUTES = dict(
    zip(
        IDS,
        (
            "team_record",
            "playoff_history",
            "playoff_appearances",
            "playoff_history",
            "team_record",
            "playoff_appearances",
            "playoff_history",
            "playoff_history",
        ),
        strict=True,
    )
)
ROUNDS = {1: "First Round", 2: "Second Round", 3: "Conference Finals", 4: "Finals"}
CONTROL_QUERIES = {
    "K10-F1-seattle": (
        "K10-F1",
        "How many times did Seattle make the playoffs between 2000-01 and 2004-05?",
    ),
    "K10-S1-postseason": ("K10-S1", "Golden State postseason series record in 2015-16"),
}


def _bindings(oracle):
    cases = {c["id"]: c for c in oracle["cases"]}
    for key, (original, query) in CONTROL_QUERIES.items():
        cases[key] = dict(cases[original], query=query, era_only=key == "K10-F1-seattle")
    return cases


def _qualified_sources():
    raw = ORACLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORACLE_SHA
    oracle, sources = json.loads(raw), {}
    for name, digest in oracle["source_hashes"].items():
        path = data_path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        with path.open() as stream:
            sources[name] = list(csv.DictReader(stream))
    return oracle, sources


@pytest.fixture
def qualified_oracle():
    return _qualified_sources()


def _sample(case, sources, expected):
    rows = [
        r
        for season in case["seasons"]
        for r in sources[f"raw/team_game_stats/{season}_playoffs.csv"]
        if int(r["team_id"]) == case["team_id"]
        and str(r["game_id"]).zfill(10) in expected["game_ids"]
    ]
    rows.sort(key=lambda r: (r["game_date"], r["game_id"]))
    assert [str(r["game_id"]).zfill(10) for r in rows] == expected["game_ids"]
    assert [
        [r["season"], str(r["game_id"]).zfill(10), int(r["team_id"])] for r in rows
    ] == expected["row_keys"]
    assert sum(r["wl"] == "W" for r in rows) == expected["wins"]
    assert sum(r["wl"] == "L" for r in rows) == expected["losses"]
    return rows


def _record(row, expected):
    for key in ("games", "wins", "losses"):
        assert row[key] == expected[key]
    assert row["win_pct"] == pytest.approx(expected["wins"] / expected["games"], abs=0.00051)


def _series(actual, expected):
    assert actual["playoff_round"] == ROUNDS[expected["round"]]
    assert actual["opponent_team_abbr"] == expected["opponent_team_abbr"]
    assert (actual["wins"], actual["losses"]) == (expected["wins"], expected["losses"])
    assert actual["result"] == ("Won" if expected["series_won"] else "Lost")
    for key in ("start_date", "end_date"):
        assert str(actual[key])[:10] == expected[key]


def _assert_case(result, case, sources):
    ident, expected = case["id"], case["expected"]
    assert result.result_status == "ok" and result.result_reason is None
    meta = result.metadata
    assert meta["route"] == ROUTES[ident]
    assert meta["query_text"] == case["query"]
    assert meta["season_type"] == "Playoffs"
    assert meta["team_context"]["team_id"] == case["team_id"]
    assert meta["team"] == (
        "SEA"
        if case.get("era_only")
        else "OKC"
        if ident == "K10-F1"
        else "LAL"
        if ident == "K10-T1"
        else "CLE"
        if ident == "K10-T2"
        else "GSW"
    )
    assert (
        not meta.get("unsupported_filters") and not meta.get("player") and not meta.get("opponent")
    )
    if len(case["seasons"]) == 1:
        assert meta["season"] == case["seasons"][0]
    else:
        assert (meta["start_season"], meta["end_season"]) == (
            case["seasons"][0],
            case["seasons"][-1],
        )
    body = result.result.to_dict()
    sections = body["sections"]
    assert len(sections["summary"]) == 1
    row = sections["summary"][0]
    source_names = {
        r["team_name"]
        for season in case["seasons"]
        for r in sources[f"raw/team_game_stats/{season}_playoffs.csv"]
        if int(r["team_id"]) == case["team_id"]
    }
    assert row["team_name"] in source_names
    if phrase := meta.get("answer_phrase"):
        assert phrase.startswith(f"The {row['team_name']} ")
    assert (row["season_start"], row["season_end"]) == (case["seasons"][0], case["seasons"][-1])
    if ident in ("K10-G1", "K10-R1", "K10-Q1"):
        _record(row, expected)
        sample = _sample(case, sources, expected)
        if ident != "K10-R1":
            for stat in ("pts", "reb", "ast", "fg3m", "stl", "blk", "tov"):
                assert row[stat + "_avg"] == pytest.approx(
                    sum(float(r[stat]) for r in sample) / len(sample), abs=0.00051
                )
        if ident == "K10-R1":
            assert len(sections["series"]) == 1
            _series(sections["series"][0], expected)
            assert (row["series_won"], row["series_lost"]) == (0, 1)
            assert "3-4 in those games" in meta["answer_phrase"]
        if ident == "K10-Q1":
            assert meta["series_situation"] == "elimination"
            assert any(
                f["kind"] == "situation" and "elimination" in f["value"]
                for f in meta["applied_filters"]
            )
    elif ident == "K10-S1":
        _record(row, case["game_record_control"])
        _sample(case, sources, case["game_record_control"])
        assert (row["series_won"], row["series_lost"]) == (
            expected["series_wins"],
            expected["series_losses"],
        )
        assert len(sections["series"]) == expected["series"]
        for actual, series in zip(sections["series"], expected["series_rows"], strict=True):
            _series(actual, series)
            _sample(case, sources, series)
        assert "3-1 in playoff series" in meta["answer_phrase"]
        assert "15-9 in games" in meta["answer_phrase"]
    elif ident in ("K10-A1", "K10-F1"):
        assert row["appearances"] == expected["appearances"]
        actual = sections["by_season"]
        assert [r["season"] for r in actual] == expected["appearance_seasons"]
        for shown, season in zip(actual, expected["season_rows"], strict=True):
            _record(shown, season)
            _sample(case, sources, season)
        assert f"playoffs {expected['appearances']} times" in meta["answer_phrase"]
        if ident == "K10-F1":
            assert row["team_name"] == "Seattle SuperSonics"
            if not case.get("era_only"):
                assert "Seattle SuperSonics" in " ".join(body.get("caveats") or [])
    else:
        assert row["titles"] == expected["titles"]
        finals = [r for r in sections["series"] if r["playoff_round"] == "Finals"]
        assert len(finals) == len(expected["finals_rows"])
        assert [r["season"] for r in finals if r["result"] == "Won"] == expected["title_seasons"]
        for actual, series in zip(finals, expected["finals_rows"], strict=True):
            _series(actual, series)
            _sample(case, sources, series)
            assert actual["season"] == series["season"]
        assert (
            f"{expected['titles']} {'title' if expected['titles'] == 1 else 'titles'}"
            in meta["answer_phrase"]
        )
        assert f"({', '.join(expected['title_seasons'])})" in meta["answer_phrase"]


@pytest.mark.parametrize("ident", [*IDS, *CONTROL_QUERIES])
def test_k10_bound_history(ident, qualified_oracle, monkeypatch):
    from nbatools.commands import playoff_history, team_record

    oracle, sources = qualified_oracle
    case = _bindings(oracle)[ident]
    # Observe the real selected sample at its aggregation boundary, without
    # replacing its calculation, source loader or filtering result.
    selected = []
    if case["id"] in ("K10-G1", "K10-S1", "K10-R1", "K10-Q1"):
        module = team_record if case["id"] in ("K10-G1", "K10-Q1") else playoff_history
        original = module._compute_record

        def observe(frame):
            selected.append(
                sorted(
                    (str(r.season), str(r.game_id).zfill(10), int(r.team_id))
                    for r in frame.itertuples()
                )
            )
            return original(frame)

        monkeypatch.setattr(module, "_compute_record", observe)
    result = execute_natural_query(case["query"])
    _assert_case(result, case, sources)
    if selected:
        expected = case.get("game_record_control", case["expected"])
        assert selected[0] == sorted(tuple(r) for r in expected["row_keys"])
