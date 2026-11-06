"""Boolean union before identity projection on retained qualified NBA rows."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands import query_boolean_parser as boolean
from nbatools.data_source import data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_poeltl_full_season_real_data import build_qualified_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
KEYS = ["game_id", "team_id", "player_id"]


def _keys(frame):
    return {tuple(map(int, row)) for row in frame[KEYS].itertuples(index=False, name=None)}


def _verify(raw, expression, question, selector, monkeypatch, *, scope=None):
    scope = scope or {}
    assert len(raw) > 0 and not raw.duplicated(KEYS).any()
    expected = raw.loc[selector(raw)]
    expected_keys = _keys(expected)
    expected_ids = set(map(int, expected.player_id))
    occurrences = {int(k): int(v) for k, v in expected.groupby("player_id").size().items()}
    observed = []
    original = boolean.evaluate_condition_tree_to_mask

    def capture(node, frame):
        # Capture only the outer call; recursive masks still use the real evaluator.
        nonlocal depth
        depth += 1
        try:
            mask = original(node, frame)
            if depth == 1:
                observed.append(frame.loc[mask].copy())
            return mask
        finally:
            depth -= 1

    depth = 0
    monkeypatch.setattr(boolean, "evaluate_condition_tree_to_mask", capture)
    natural = execute_natural_query(question)
    assert natural.result_status == "ok", natural.metadata
    assert natural.metadata["primary_count"] == len(expected_ids)
    assert "players" in natural.metadata["count_phrase"] or len(expected_ids) == 1
    assert _keys(observed.pop()) == expected_keys
    rows = natural.to_dict()["sections"].get("leaderboard", [])
    assert {int(r["player_id"]): int(r["matching_games"]) for r in rows} == occurrences
    structured = execute_structured_query(
        "player_occurrence_leaders", condition_expression=expression, limit=None, **scope
    )
    if expected.empty:
        assert structured.result_reason == "no_match"
    else:
        assert structured.result_status == "ok", structured.metadata
        assert {
            int(r["player_id"]): int(r["matching_games"])
            for r in structured.to_dict()["sections"]["leaderboard"]
        } == occurrences
    assert _keys(observed.pop()) == expected_keys
    http = TestClient(app).post("/query", json={"query": question})
    assert http.status_code == 200 and http.json()["result_status"] == "ok"
    assert http.json()["result"]["metadata"]["primary_count"] == len(expected_ids)
    assert _keys(observed.pop()) == expected_keys
    api = TestClient(app).post(
        "/structured-query",
        json={
            "route": "player_occurrence_leaders",
            "kwargs": dict(condition_expression=expression, limit=None, **scope),
        },
    )
    assert api.status_code == 200
    assert _keys(observed.pop()) == expected_keys
    if not expected.empty:
        assert {
            int(r["player_id"]): int(r["matching_games"])
            for r in api.json()["result"]["sections"]["leaderboard"]
        } == occurrences
    monkeypatch.setattr(boolean, "evaluate_condition_tree_to_mask", original)
    return dict(
        query=question,
        player_games=len(expected),
        nba_games=int(expected.game_id.nunique()),
        distinct_players=len(expected_ids),
        keys=sorted(expected_keys),
        player_ids=sorted(expected_ids),
        occurrences=occurrences,
        points_sum=int(expected.pts.sum()),
        assists_sum=int(expected.ast.sum()),
        answer=natural.metadata["count_phrase"],
    )


def _write(name, receipt, tmp_path):
    out = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "distinct-player-or"
    out.mkdir(parents=True, exist_ok=True)
    (out / (name + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")


def test_qualified_global_2023_example_oracle_and_all_consumers(tmp_path, monkeypatch):
    raw = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
    assert raw[["pts", "ast", "player_id"]].notna().all().all()
    left = raw.pts.gt(40)
    right = raw.ast.gt(12)
    receipt = _verify(
        raw,
        "over 40 points or over 12 assists",
        "How many different players had a game with over 40 points OR over 12 assists in 2023-24?",
        lambda r: r.pts.gt(40) | r.ast.gt(12),
        monkeypatch,
        scope=dict(season="2023-24"),
    )
    # Prospective raw selection is fixed before interpreting the question; no
    # total is guessed from named-player K03 subsets or application output.
    receipt["branches"] = dict(
        left=int(left.sum()),
        right=int(right.sum()),
        overlap=int((left & right).sum()),
        left_only=int((left & ~right).sum()),
        right_only=int((right & ~left).sum()),
    )
    assert receipt["branches"]["left_only"] > 0 and receipt["branches"]["right_only"] > 0
    assert receipt["player_games"] == int(left.sum() + right.sum() - (left & right).sum())
    _write("2023-global", receipt, tmp_path)


def test_retained_2022_complete_union_nested_and_scope(tmp_path, monkeypatch):
    root, teams, players = build_qualified_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        receipt = _verify(
            players,
            "over 40 points or over 12 assists",
            "How many distinct players had (over 40 points or over 12 assists) in 2022-23?",
            lambda r: r.pts.gt(40) | r.ast.gt(12),
            monkeypatch,
            scope=dict(season="2022-23"),
        )
        assert (receipt["player_games"], receipt["nba_games"], receipt["distinct_players"]) == (
            295,
            266,
            77,
        )
        assert (receipt["points_sum"], receipt["assists_sum"]) == (10051, 2676)
        gsw = players.loc[players.team_abbr.eq("GSW")]
        # Independent source-only selectors precede both application paths.
        scoped = _verify(
            gsw,
            "over 20 points or (over 6 assists and under 3 turnovers)",
            "How many different players for the Warriors had (over 20 points or (over 6 assists and under 3 turnovers)) in 2022-23?",
            lambda r: r.pts.gt(20) | (r.ast.gt(6) & r.tov.lt(3)),
            monkeypatch,
            scope=dict(season="2022-23", team="GSW"),
        )
        _write("2022-native", dict(league=receipt, warriors=scoped), tmp_path)
    finally:
        reset_data_source_cache()


def test_qualified_2022_pinned_rows_match_original_union(tmp_path, monkeypatch):
    evidence = (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/source-evidence/distinct-player-or-20261106"
    )
    original = json.loads((evidence / "author-original-oracle.json").read_text())
    raw = data_read_csv("raw/player_game_stats/2022-23_regular_season.csv")
    selected = raw.loc[raw.pts.gt(40) | raw.ast.gt(12)]
    assert _keys(selected) == set(map(tuple, original["keys"]))
    receipt = _verify(
        raw,
        "over 40 points or over 12 assists",
        "How many different players had a game with (over 40 points or over 12 assists) in 2022-23?",
        lambda r: r.pts.gt(40) | r.ast.gt(12),
        monkeypatch,
        scope=dict(season="2022-23"),
    )
    assert receipt["distinct_players"] == original["distinct_players"] == 77
    assert receipt["player_games"] == original["player_games"] == 295
    _write("2022-pinned-original-reconciliation", receipt, tmp_path)
