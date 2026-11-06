"""Independent raw-row owner/join oracles on the retained K03 population."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
EVIDENCE = Path(
    "working/nba-tools-completion-program/source-evidence/distinct-player-or-20261106/independent"
)
KEYS = ["game_id", "team_id", "player_id"]


@pytest.fixture(scope="module")
def retained_control(tmp_path_factory):
    root = tmp_path_factory.mktemp("owned-k03")
    subprocess.run(
        [
            sys.executable,
            str(EVIDENCE / "portable-source-replay.py"),
            "--repo",
            str(Path.cwd()),
            "--output",
            str(root),
        ],
        check=True,
        capture_output=True,
    )
    return root / "controlled"


@pytest.fixture
def owned_rows(retained_control, tmp_path, monkeypatch):
    root = tmp_path / "data-root"
    shutil.copytree(retained_control, root)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    p = pd.read_csv(root / "data/raw/player_game_stats/2025-26_regular_season.csv")
    t = pd.read_csv(root / "data/raw/team_game_stats/2025-26_regular_season.csv")
    # The oracle joins raw records independently of application context helpers.
    p = p.merge(
        t[["game_id", "team_id", "pts"]].rename(columns={"pts": "team_points"}),
        on=["game_id", "team_id"],
        validate="many_to_one",
    )
    p = p.merge(
        t[["game_id", "team_id", "pts"]].rename(
            columns={"team_id": "opponent_team_id", "pts": "opponent_points"}
        ),
        on=["game_id", "opponent_team_id"],
        validate="many_to_one",
    )
    yield p
    reset_data_source_cache()


def keys(rows):
    return {(int(r["game_id"]), r["team_abbr"], int(r["player_id"])) for r in rows}


CASES = [
    ("over 20 points and exactly 100 team points", lambda r: r.pts.gt(20) & r.team_points.eq(100)),
    (
        "(over 20 points or over 10 assists) with exactly 100 team points",
        lambda r: (r.pts.gt(20) | r.ast.gt(10)) & r.team_points.eq(100),
    ),
    (
        "(over 20 points or over 10 assists) when opponents scored under 100 points",
        lambda r: (r.pts.gt(20) | r.ast.gt(10)) & r.opponent_points.lt(100),
    ),
    (
        "(over 20 points and team points equal to 100) or (over 10 assists and exactly 90 opponent points)",
        lambda r: (
            (r.pts.gt(20) & r.team_points.eq(100)) | (r.ast.gt(10) & r.opponent_points.eq(90))
        ),
    ),
    (
        "over 20 points or (at least 100 team points and exactly 10 assists)",
        lambda r: r.pts.gt(20) | (r.team_points.ge(100) & r.ast.eq(10)),
    ),
    (
        "(over 100 team points or over 100 opponent points)",
        lambda r: r.team_points.gt(100) | r.opponent_points.gt(100),
    ),
    (
        "(at least 100 team points or under 100 opponent points)",
        lambda r: r.team_points.ge(100) | r.opponent_points.lt(100),
    ),
]


@pytest.mark.parametrize("expression,selector", CASES)
@pytest.mark.parametrize("distinct", [False, True])
def test_all_consumers_preserve_owned_tree_and_grain(owned_rows, expression, selector, distinct):
    expected = owned_rows.loc[selector(owned_rows)]
    prefix = "distinct players had" if distinct else "player games with"
    question = f"How many {prefix} {expression} in 2025-26?"
    result = execute_natural_query(question)
    assert result.result_status == "ok", result.to_dict()
    count = expected.player_id.nunique() if distinct else len(expected)
    assert result.metadata["primary_count"] == count
    natural = result.to_dict()
    route = "player_occurrence_leaders" if distinct else "player_game_finder"
    structured = execute_structured_query(
        route, season="2025-26", condition_expression=expression, limit=None
    )
    http = TestClient(app).post("/query", json={"query": question})
    assert http.status_code == 200 and http.json()["result_status"] == "ok"
    api = TestClient(app).post(
        "/structured-query",
        json={
            "route": route,
            "kwargs": {"season": "2025-26", "condition_expression": expression, "limit": None},
        },
    )
    assert api.status_code == 200
    documents = [natural, structured.to_dict(), http.json()["result"], api.json()["result"]]
    for document in documents:
        if distinct:
            rows = document["sections"].get("leaderboard", [])
            assert {
                int(r["player_id"]): int(r["matching_games"]) for r in rows
            } == expected.groupby("player_id").size().to_dict()
        else:
            assert keys(document["sections"].get("finder", [])) == keys(expected.to_dict("records"))
    if "exactly 100 team points" in expression:
        oracle = json.loads((EVIDENCE / "oracle.json").read_text())["cases"][
            "controlled_team_owned"
        ]
        assert {tuple(map(int, r)) for r in expected[KEYS].itertuples(index=False, name=None)} == {
            tuple(k) for k in oracle["selected_keys"]
        }
        assert len(expected) == 2 and expected.player_id.nunique() == 2


@pytest.mark.parametrize("distinct", [False, True])
def test_common_team_opponent_dates_and_venue_scope(owned_rows, distinct):
    expression = "(at least 90 team points or over 10 assists)"
    question = f"How many {'distinct players had' if distinct else 'player games with'} {expression} for Denver against Golden State at home from 2025-11-01 to 2025-11-03 in 2025-26?"
    expected = owned_rows.loc[
        owned_rows.team_abbr.eq("DEN")
        & owned_rows.opponent_team_abbr.eq("GSW")
        & owned_rows.is_home
        & owned_rows.game_date.between("2025-11-01", "2025-11-03")
    ]
    result = execute_natural_query(question)
    assert result.result_status == "ok", result.to_dict()
    assert result.metadata["primary_count"] == (
        expected.player_id.nunique() if distinct else len(expected)
    )


@pytest.mark.parametrize("distinct", [False, True])
@pytest.mark.parametrize(
    "damage",
    ["missing_join", "unknown_stat", "missing_team_file", "partial_season", "ambiguous_join"],
)
def test_unknown_owned_coverage_never_becomes_zero_or_partial(owned_rows, distinct, damage):
    root = Path(os.environ["NBATOOLS_DATA_ROOT"])
    path = root / "data/raw/team_game_stats/2025-26_regular_season.csv"
    if damage == "missing_team_file":
        path.unlink()
    else:
        raw = pd.read_csv(path)
        if damage == "missing_join":
            raw = raw[~(raw.game_id.eq(1) & raw.team_abbr.eq("GSW"))]
        elif damage == "ambiguous_join":
            raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
        elif damage == "unknown_stat":
            raw.loc[raw.game_id.eq(1) & raw.team_abbr.eq("GSW"), "pts"] = float("nan")
        raw.to_csv(path, index=False)
    (root / "data/raw/player_game_stats/2024-25_regular_season.csv").unlink(
        missing_ok=True
    ) if damage == "partial_season" else None
    reset_data_source_cache()
    scope = "from 2024-25 to 2025-26" if damage == "partial_season" else "in 2025-26"
    result = execute_natural_query(
        f"How many {'distinct players had' if distinct else 'player games with'} (over 0 points or under 90 opponent points) {scope}?"
    )
    assert result.result_status != "ok", result.to_dict()
    assert "primary_count" not in result.metadata


@pytest.mark.parametrize(
    "expression,stat,lower,upper",
    [
        ("above 100 team points", "team_pts", 100.0001, None),
        ("exactly zero team turnovers", "team_tov", 0, 0),
        ("no opponent assists", "opponent_ast", 0, 0),
        ("0+ opponent assists", "opponent_ast", 0, None),
        ("team points equal to 100", "team_pts", 100, 100),
    ],
)
def test_shared_bound_grammar_keeps_noun_ownership(expression, stat, lower, upper):
    from nbatools.commands.query_boolean_parser import parse_condition_text

    leaf = parse_condition_text(expression)
    assert (leaf.stat, leaf.min_value, leaf.max_value) == (stat, lower, upper)


def test_named_player_keeps_same_game_context(owned_rows):
    result = execute_natural_query(
        "How many games did Nikola Jokic have with (over 20 points or under 100 opponent points) in 2025-26?"
    )
    expected = owned_rows.loc[
        owned_rows.player_id.eq(203999)
        & (owned_rows.pts.gt(20) | owned_rows.opponent_points.lt(100))
    ]
    assert result.result_status == "ok", result.to_dict()
    assert result.metadata["primary_count"] == len(expected)
    assert keys(result.to_dict()["sections"]["finder"]) == keys(expected.to_dict("records"))
