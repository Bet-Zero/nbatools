"""Exact bounds selected independently from the committed synthetic game rows."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
ROOT = Path("qa/fixtures/query_engine_sample/data/raw")


def _players():
    return pd.read_csv(ROOT / "player_game_stats/2025-26_regular_season.csv")


def _ids(rows):
    return {int(r["game_id"]) for r in rows}


@pytest.mark.parametrize(
    "clause",
    [
        "exactly 20 points",
        "points equal to 20",
        "points equals 20",
        "points = 20",
    ],
)
def test_player_equality_list_count_summary_and_http(clause):
    raw = _players()
    expected = raw.loc[raw.player_name.eq("LeBron James") & raw.pts.eq(20)]
    assert len(expected) == 3
    assert len(raw.loc[raw.player_name.eq("LeBron James") & raw.pts.ge(20)]) > 3
    question = f"How many LeBron James games with {clause} in 2025-26?"
    count = execute_natural_query(question)
    assert count.result_status == "ok", count.metadata
    assert count.metadata["primary_count"] == 3
    assert "exactly 20 points" in count.metadata["count_phrase"]
    assert any(f["value"] == "exactly 20" for f in count.metadata["applied_filters"])
    assert _ids(count.to_dict()["sections"]["finder"]) == set(expected.game_id)
    summary = execute_natural_query(f"LeBron James average assists with {clause} in 2025-26")
    assert summary.result_status == "ok", summary.metadata
    sections = summary.to_dict()["sections"]
    assert _ids(sections["game_log"]) == set(expected.game_id)
    assert sections["summary"][0]["ast_avg"] == pytest.approx(expected.ast.mean(), abs=0.001)
    structured = execute_structured_query(
        "player_game_summary",
        player="LeBron James",
        season="2025-26",
        stat="pts",
        min_value=20,
        max_value=20,
    )
    assert _ids(structured.to_dict()["sections"]["game_log"]) == set(expected.game_id)
    http = TestClient(app).post("/query", json={"query": question})
    assert http.status_code == 200 and http.json()["result_status"] == "ok"
    assert http.json()["result"]["metadata"]["primary_count"] == 3


def test_equality_before_rank_and_split():
    raw = _players()
    expected = raw.loc[raw.player_name.eq("LeBron James") & raw.pts.eq(20)]
    ranked = execute_natural_query(
        "LeBron James top 2 games by assists with exactly 20 points in 2025-26"
    )
    assert ranked.result_status == "ok", ranked.metadata
    rows = ranked.to_dict()["sections"]["finder"]
    assert [r["ast"] for r in rows] == sorted(expected.ast, reverse=True)[:2]
    assert _ids(rows) <= set(expected.game_id)
    split = execute_natural_query(
        "LeBron James average assists by season with exactly 20 points in 2025-26"
    )
    assert split.result_status == "ok", split.metadata
    rows = split.to_dict()["sections"]["by_season"]
    assert len(rows) == 1 and rows[0]["games"] == 3
    assert rows[0]["ast_avg"] == pytest.approx(expected.ast.mean(), abs=0.001)


@pytest.mark.parametrize(
    "clause",
    ["exactly 110 team points", "team points equal to 110", "the team scored exactly 110 points"],
)
def test_team_owner_is_preserved(clause):
    teams = pd.read_csv(ROOT / "team_game_stats/2025-26_regular_season.csv")
    selected = teams.loc[teams.pts.eq(110), ["game_id", "team_id"]]
    expected = (
        _players()
        .loc[lambda r: r.player_name.eq("LeBron James")]
        .merge(selected, on=["game_id", "team_id"])
    )
    assert len(expected) > 0
    join = "when" if clause.startswith("the team") else "with"
    result = execute_natural_query(f"LeBron James average assists in 2025-26 {join} {clause}")
    assert result.result_status == "ok", result.metadata
    assert _ids(result.to_dict()["sections"]["game_log"]) == set(expected.game_id)
    assert any(
        c["stat"] == "team_pts" and c["min_value"] == c["max_value"] == 110
        for c in result.metadata["conditions"]
    )


@pytest.mark.parametrize("clause", ["exactly 0 turnovers", "turnovers equal to 0"])
def test_explicit_zero_is_equality(clause):
    expected = _players().loc[lambda r: r.player_name.eq("LeBron James") & r.tov.eq(0)]
    result = execute_natural_query(f"How many LeBron James games with {clause} in 2025-26?")
    assert result.result_status == "ok", result.metadata
    assert result.metadata["primary_count"] == len(expected)
    assert _ids(result.to_dict()["sections"]["finder"]) == set(expected.game_id)


@pytest.mark.parametrize(
    "clause",
    [
        "not exactly 20 points",
        "points not equal to 20",
        "exactly 20+ points",
        "exactly 20 points or more",
        "points = 20+",
        "points equal to 20 or more",
        "points = 20 or fewer",
        "!= 20 points",
        "points != 20",
        "points >= 20",
        "points == 20",
    ],
)
def test_unimplemented_or_contradictory_operators_withhold_answer(clause):
    result = execute_natural_query(f"How many LeBron James games with {clause} in 2025-26?")
    assert result.result_status != "ok"
    assert "primary_count" not in result.metadata


def test_compound_equality_does_not_hide_other_inclusive_bound():
    expected = _players().loc[
        lambda r: r.player_name.eq("LeBron James") & r.pts.eq(20) & r.ast.ge(5)
    ]
    result = execute_natural_query(
        "How many LeBron James games with exactly 20 points and 5 assists or more in 2025-26?"
    )
    assert result.result_status == "ok", result.metadata
    assert result.metadata["primary_count"] == len(expected)


def test_negated_owned_verbal_equality_cannot_become_own_score():
    result = execute_natural_query(
        "Celtics record when opponents do not score exactly 102 points in 2025-26"
    )
    assert result.result_status != "ok"
    assert "primary_count" not in result.metadata


def test_opponent_count_answer_keeps_equality_label():
    teams = pd.read_csv(ROOT / "team_game_stats/2025-26_regular_season.csv")
    opponents = teams.loc[teams.pts.eq(100), ["game_id", "team_id"]].rename(
        columns={"team_id": "opponent_team_id"}
    )
    expected = teams.loc[teams.team_abbr.eq("LAL")].merge(
        opponents, on=["game_id", "opponent_team_id"]
    )
    answer = execute_natural_query(
        "How many Lakers games with exactly 100 opponent points in 2025-26?"
    )
    assert answer.result_status == "ok", answer.metadata
    assert answer.metadata["primary_count"] == len(expected)
    assert "allowed exactly 100 points" in answer.metadata["count_phrase"]
    assert "or fewer" not in answer.metadata["count_phrase"]


@pytest.mark.parametrize("modifier", ["once", "ever", "actually", "even once"])
def test_negated_governor_modifiers_are_not_discarded(modifier):
    result = execute_natural_query(
        f"Celtics record when opponents never {modifier} scored exactly 102 points in 2025-26"
    )
    assert result.result_status != "ok"
    assert "primary_count" not in result.metadata


def test_opponent_verbal_equality_preserves_owner():
    teams = pd.read_csv(ROOT / "team_game_stats/2025-26_regular_season.csv")
    expected = teams.loc[teams.team_abbr.eq("LAL")].merge(
        teams.loc[teams.pts.eq(100), ["game_id", "team_id"]].rename(
            columns={"team_id": "opponent_team_id"}
        ),
        on=["game_id", "opponent_team_id"],
    )
    for clause in (
        "opponents score exactly 100 points",
        "opponents scored exactly 100 points",
        "opponents score exactly 100",
    ):
        answer = execute_natural_query(f"How many Lakers games when {clause} in 2025-26?")
        assert answer.result_status == "ok", answer.metadata
        assert answer.metadata["primary_count"] == len(expected)
        assert "allowed exactly 100 points" in answer.metadata["count_phrase"]


@pytest.mark.parametrize("owner", ["team", "opponent"])
def test_conflicting_owned_equality_does_not_discard_trailing_floor(owner):
    result = execute_natural_query(
        f"Celtics record with exactly 102 {owner} points or more in 2025-26"
    )
    assert result.result_status != "ok"
    assert "primary_count" not in result.metadata


@pytest.mark.parametrize("suffix", ["points", ""])
@pytest.mark.parametrize("verb", ["holding", "held", "limiting"])
def test_defensive_governor_preserves_equality_owner(verb, suffix):
    teams = pd.read_csv(ROOT / "team_game_stats/2025-26_regular_season.csv")
    expected = teams.loc[teams.team_abbr.eq("BOS")].merge(
        teams.loc[teams.pts.eq(102), ["game_id", "team_id"]].rename(
            columns={"team_id": "opponent_team_id"}
        ),
        on=["game_id", "opponent_team_id"],
    )
    answer = execute_natural_query(
        f"Celtics record when {verb} opponents to exactly 102 {suffix} in 2025-26"
    )
    assert answer.result_status == "ok", answer.metadata
    row = answer.to_dict()["sections"]["summary"][0]
    assert row["games"] == len(expected)
    assert row["wins"] == int(expected.wl.eq("W").sum())
    assert row["losses"] == int(expected.wl.eq("L").sum())
