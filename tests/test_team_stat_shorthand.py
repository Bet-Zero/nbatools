"""Explicit team noun predicates share ownership across existing consumers.

Oracles read the committed synthetic CSVs directly, before interpreting questions.
These tests establish software behavior, not facts about NBA players or seasons.
"""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
ROOT = Path("qa/fixtures/query_engine_sample/data/raw")


def raw_rows():
    teams = pd.read_csv(ROOT / "team_game_stats/2025-26_regular_season.csv")
    players = pd.read_csv(ROOT / "player_game_stats/2025-26_regular_season.csv")
    return teams, players


def ids(rows):
    return {int(r["game_id"]) for r in rows}


@pytest.mark.parametrize(
    ("wording", "stat", "predicate"),
    [
        ("110+ team points", "pts", lambda v: v >= 110),
        ("over 110 team points", "pts", lambda v: v > 110),
        ("under 110 team points", "pts", lambda v: v < 110),
        ("110 or fewer team points", "pts", lambda v: v <= 110),
        ("110 team points or less", "pts", lambda v: v <= 110),
        ("at least 25 team assists", "ast", lambda v: v >= 25),
        ("no more than 12 team turnovers", "tov", lambda v: v <= 12),
        ("15+ team threes", "fg3m", lambda v: v >= 15),
        ("over 24.5 team assists", "ast", lambda v: v > 24.5),
    ],
)
def test_player_finder_and_summary_keep_team_owned_threshold(wording, stat, predicate):
    teams, players = raw_rows()
    selected = teams.loc[predicate(teams[stat]), ["game_id", "team_id"]]
    expected = players.loc[players.player_name.eq("LeBron James")].merge(
        selected, on=["game_id", "team_id"], validate="one_to_one"
    )
    assert len(expected) > 0
    finder = execute_natural_query(f"LeBron James games in 2025-26 with {wording}")
    assert finder.result_status == "ok", finder.metadata
    expected_ids = set(expected.sort_values(stat if stat == "pts" else "game_id").game_id)
    # Default finder limit applies after selection; use its count plus a summary
    # game log to check the full population independently of ranking presentation.
    assert ids(finder.result.to_dict()["sections"]["finder"]) <= expected_ids
    summary = execute_natural_query(f"LeBron James average points in 2025-26 with {wording}")
    assert summary.result_status == "ok", summary.metadata
    sections = summary.result.to_dict()["sections"]
    assert ids(sections["game_log"]) == expected_ids
    assert sections["summary"][0]["games"] == len(expected)
    assert sections["summary"][0]["pts_sum"] == expected.pts.sum()
    assert sections["summary"][0]["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
    assert any(c["stat"] == f"team_{stat}" for c in summary.metadata["conditions"])


def test_mixed_player_team_opponent_ownership_through_http():
    teams, players = raw_rows()
    team = teams.loc[teams.team_abbr.eq("LAL") & teams.pts.ge(110)]
    opponent = teams[["game_id", "team_id", "pts"]].rename(
        columns={"team_id": "opponent_team_id", "pts": "opponent_pts"}
    )
    team = team.merge(opponent, on=["game_id", "opponent_team_id"], validate="one_to_one")
    team = team.loc[team.opponent_pts.lt(110)]
    expected = players.loc[players.player_name.eq("LeBron James") & players.pts.ge(25)].merge(
        team[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
    )
    response = TestClient(app).post(
        "/query",
        json={
            "query": "LeBron James average points in 2025-26 with 25 points and 110+ team points "
            "when opponents score under 110 points"
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result_status"] == "ok", body
    sections = body["result"]["sections"]
    assert ids(sections["game_log"]) == set(expected.game_id)
    assert sections["summary"][0]["pts_sum"] == expected.pts.sum()
    assert {c["stat"] for c in body["result"]["metadata"]["conditions"]} == {
        "pts",
        "team_pts",
        "opponent_pts",
    }


@pytest.mark.parametrize("operation", ["record", "average points"])
def test_team_consumers_preserve_both_sides_and_venue(operation):
    teams, _ = raw_rows()
    expected = teams.loc[teams.team_abbr.eq("LAL") & teams.is_home.eq(1) & teams.pts.le(110)]
    opponents = teams.loc[teams.pts.ge(100), ["game_id", "team_id"]].rename(
        columns={"team_id": "opponent_team_id"}
    )
    expected = expected.merge(opponents, on=["game_id", "opponent_team_id"], validate="one_to_one")
    answer = execute_natural_query(
        f"Lakers {operation} at home in 2025-26 with at most 110 team points "
        "and at least 100 opponent points"
    )
    assert answer.result_status == "ok", answer.metadata
    summary = answer.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == len(expected)
    assert summary["wins"] == expected.wl.eq("W").sum()
    assert summary["losses"] == expected.wl.eq("L").sum()
    assert summary["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


def test_two_team_noun_bounds_are_conjoined():
    teams, players = raw_rows()
    team_ids = teams.loc[teams.pts.ge(110) & teams.ast.le(25), ["game_id", "team_id"]]
    expected = players.loc[players.player_name.eq("LeBron James")].merge(
        team_ids, on=["game_id", "team_id"], validate="one_to_one"
    )
    result = execute_natural_query(
        "LeBron James average points in 2025-26 with 110+ team points and at most 25 team assists"
    )
    assert result.result_status == "ok", result.metadata
    assert ids(result.result.to_dict()["sections"]["game_log"]) == set(expected.game_id)


@pytest.mark.parametrize("suffix", ["from Davis", "and Curry", "and 2 days rest"])
def test_noun_stat_does_not_erase_unread_scope(suffix):
    result = execute_natural_query(f"Lakers record in 2025-26 with under 110 team points {suffix}")
    assert result.result_status != "ok", result.metadata


@pytest.mark.parametrize(
    ("wording", "floor", "ceiling"),
    [
        ("0 team turnovers", 0, 0),
        ("0+ team turnovers", 0, None),
    ],
)
def test_zero_noun_count_is_exact_unless_an_explicit_floor(wording, floor, ceiling):
    teams, players = raw_rows()
    teams = teams.loc[teams.tov.ge(floor)]
    if ceiling is not None:
        teams = teams.loc[teams.tov.le(ceiling)]
    expected = players.loc[players.player_name.eq("LeBron James")].merge(
        teams[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
    )
    answer = execute_natural_query(f"LeBron James average points in 2025-26 with {wording}")
    if expected.empty:
        assert answer.result_status == "no_result" and answer.result_reason == "no_match"
    else:
        assert answer.result_status == "ok", answer.metadata
        assert ids(answer.result.to_dict()["sections"]["game_log"]) == set(expected.game_id)
    assert any(
        c["stat"] == "team_tov" and c["max_value"] == ceiling for c in answer.metadata["conditions"]
    )


@pytest.mark.parametrize("operation", ["LeBron James average points", "Lakers average points"])
def test_same_stat_strict_conjunction_keeps_boundary(operation):
    teams, players = raw_rows()
    expected = teams.loc[teams.team_abbr.eq("LAL") & teams.pts.gt(110)]
    query = f"{operation} in 2025-26 with 110+ team points and over 110 team points"
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    if operation.startswith("LeBron"):
        expected = players.loc[players.player_name.eq("LeBron James")].merge(
            expected[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
        )
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == len(expected)
    assert summary["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)


def test_opponent_noun_and_team_noun_preserve_separate_rows():
    teams, players = raw_rows()
    ours = teams.loc[teams.ast.ge(20)]
    opposing = teams.loc[teams.ast.ge(20), ["game_id", "team_id"]].rename(
        columns={"team_id": "opponent_team_id"}
    )
    context = ours.merge(opposing, on=["game_id", "opponent_team_id"], validate="one_to_one")
    expected = players.loc[players.player_name.eq("Stephen Curry")].merge(
        context[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
    )
    result = execute_natural_query(
        "Stephen Curry average points with 20+ opponent assists and 20+ team assists in 2025-26"
    )
    assert result.result_status == "ok", result.metadata
    assert ids(result.result.to_dict()["sections"]["game_log"]) == set(expected.game_id)
    assert {c["stat"] for c in result.metadata["conditions"]} == {"opponent_ast", "team_ast"}


@pytest.mark.parametrize("opponents", ["BOS and DEN", "Celtics and Nuggets"])
def test_named_opponent_owner_survives_noun_context(opponents):
    teams, players = raw_rows()
    own = teams.loc[teams.team_abbr.eq("GSW") & teams.pts.ge(80)]
    opposing = teams.loc[
        teams.team_abbr.eq("BOS") & teams.ast.ge(20), ["game_id", "team_id"]
    ].rename(columns={"team_id": "opponent_team_id"})
    qualified = own.merge(opposing, on=["game_id", "opponent_team_id"], validate="one_to_one")
    expected = players.loc[players.player_name.eq("Stephen Curry")].merge(
        qualified[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
    )
    answer = execute_natural_query(
        f"Stephen Curry games vs {opponents} when BOS had at least 20 assists "
        "with 80+ team points in 2025-26"
    )
    assert answer.result_status == "ok", answer.metadata
    assert ids(answer.result.to_dict()["sections"]["finder"]) == set(expected.game_id)
    assert any(
        c["stat"] == "opponent_ast" and c.get("opponent_team") == "BOS"
        for c in answer.metadata["conditions"]
    )
