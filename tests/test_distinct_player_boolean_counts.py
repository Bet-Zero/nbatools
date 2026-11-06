"""Controlled K03 union/projection and independent committed-fixture scopes."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_k03_find_count_contract import population as population

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv")


@pytest.mark.parametrize("subject", ["different players", "distinct players", "players"])
@pytest.mark.parametrize(
    "expression", ["(over 20 points or over 10 assists)", "over 20 points or over 10 assists"]
)
def test_controlled_union_then_player_projection(population, subject, expression):
    query = f"How many {subject} had a game with {expression} in 2025-26?"
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert result.metadata["primary_count"] == 3
    rows = result.to_dict()["sections"]["leaderboard"]
    assert {r["player_id"]: r["matching_games"] for r in rows} == {
        population["A"]: 2,
        population["B"]: 1,
        population["C"]: 1,
    }
    assert sum(r["matching_games"] for r in rows) == 4
    assert "3 distinct players" in result.metadata["count_phrase"]
    assert any(
        f["kind"] == "boolean" and "or" in f["value"] for f in result.metadata["applied_filters"]
    )
    structured = execute_structured_query(
        "player_occurrence_leaders", season="2025-26", condition_expression=expression, limit=None
    )
    assert structured.result_status == "ok"
    assert {
        r["player_id"]: r["matching_games"] for r in structured.to_dict()["sections"]["leaderboard"]
    } == {population["A"]: 2, population["B"]: 1, population["C"]: 1}


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(over 20 points or over 10 assists) and under 1 turnovers", {"A": 1, "B": 1}),
        ("over 20 points or (over 10 assists and under 1 turnovers)", {"A": 2, "B": 1, "C": 1}),
        ("(over 10 assists and exactly 1 turnovers) or over 100 points", {}),
    ],
)
def test_nested_predicates_stay_in_the_same_game(population, expression, expected):
    result = execute_natural_query(f"How many distinct players had {expression} in 2025-26?")
    assert result.result_status == "ok", result.metadata
    assert result.metadata["primary_count"] == len(expected)
    actual = {
        r["player_id"]: r["matching_games"]
        for r in result.to_dict()["sections"].get("leaderboard", [])
    }
    assert actual == {population[k]: v for k, v in expected.items()}


def test_player_game_and_unique_game_grains_are_not_distinct_players(population):
    result = execute_natural_query(
        "How many player games with (over 20 points or over 10 assists) in 2025-26?"
    )
    assert result.result_status == "ok"
    rows = result.to_dict()["sections"]["finder"]
    assert result.metadata["primary_count"] == 4
    assert len({r["game_id"] for r in rows}) == 3
    assert len({r["player_id"] for r in rows}) == 3
    assert "4 matching player-games" in result.metadata["count_phrase"]
    # This separate global projection is not advertised by the existing engine.
    unsupported = execute_natural_query(
        "How many unique NBA games had players with (over 20 points or over 10 assists) in 2025-26?"
    )
    assert unsupported.result_status != "ok"
    assert "primary_count" not in unsupported.metadata


@pytest.mark.parametrize(
    ("scope", "selector"),
    [
        ("for the Lakers", lambda r: r.team_abbr.eq("LAL")),
        ("at home", lambda r: r.is_home.eq(1)),
        (
            "against Boston in November 2025",
            lambda r: (
                r.opponent_team_abbr.eq("BOS") & r.game_date.between("2025-11-01", "2025-11-30")
            ),
        ),
        ("on the road in losses", lambda r: r.is_away.eq(1) & r.wl.eq("L")),
    ],
)
def test_common_scope_and_http_keep_exact_ids(scope, selector):
    raw = pd.read_csv(RAW)
    expected = raw.loc[selector(raw) & (raw.pts.gt(20) | raw.ast.gt(10))]
    query = f"How many different players had a game with (over 20 points or over 10 assists) {scope} in 2025-26?"
    response = TestClient(app).post("/query", json={"query": query})
    assert response.status_code == 200
    body = response.json()
    assert body["result_status"] == "ok", body
    assert body["result"]["metadata"]["primary_count"] == expected.player_id.nunique()
    rows = body["result"]["sections"].get("leaderboard", [])
    assert {int(r["player_id"]): r["matching_games"] for r in rows} == expected.groupby(
        "player_id"
    ).size().to_dict()


def test_team_player_subject_uses_the_same_boolean_engine():
    raw = pd.read_csv(RAW)
    expected = raw.loc[raw.team_abbr.eq("LAL") & (raw.pts.gt(20) | raw.ast.gt(10))]
    result = execute_natural_query(
        "How many Lakers players had a game with (over 20 points or over 10 assists) in 2025-26?"
    )
    assert result.result_status == "ok", result.metadata
    assert result.metadata["primary_count"] == expected.player_id.nunique()
    assert {r["player_id"] for r in result.to_dict()["sections"]["leaderboard"]} == set(
        expected.player_id
    )


@pytest.mark.parametrize(
    "clause",
    [
        "(over 20 points or over 10 assists) while injured",
        "(over 20 points against Boston or over 10 assists against Phoenix)",
        "(over 20 points or over 10 assists) before Christmas",
        "(over 20 team points or over 10 assists)",
        "(over 20 points or over 10 opponent assists)",
    ],
)
def test_unread_scopes_and_owners_never_become_partial_answers(clause):
    result = execute_natural_query(
        f"How many different players had a game with {clause} in 2025-26?"
    )
    assert result.result_status != "ok"
    assert "primary_count" not in result.metadata


def test_identity_projection_does_not_group_alias_spellings(population):
    import os

    from nbatools.data_source import reset_data_source_cache

    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2025-26_regular_season.csv"
    )
    raw = pd.read_csv(path)
    raw.loc[raw.game_id.eq(1) & raw.player_id.eq(population["A"]), "player_name"] = (
        "Alternate fixture spelling"
    )
    raw.to_csv(path, index=False)
    reset_data_source_cache()
    answer = execute_natural_query(
        "How many different players had (over 20 points or over 10 assists) in 2025-26?"
    )
    assert answer.result_status == "ok", answer.metadata
    assert answer.metadata["primary_count"] == 3
    rows = answer.to_dict()["sections"]["leaderboard"]
    assert {r["player_id"]: r["matching_games"] for r in rows}[population["A"]] == 2


@pytest.mark.parametrize(
    "damage", ["missing_source", "missing_branch_column", "unknown_branch_value"]
)
def test_unavailable_predicate_is_not_a_qualified_zero(population, damage):
    import os

    from nbatools.data_source import reset_data_source_cache

    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2025-26_regular_season.csv"
    )
    if damage == "missing_source":
        path.unlink()
    else:
        raw = pd.read_csv(path)
        if damage == "missing_branch_column":
            raw = raw.drop(columns="ast")
        else:
            raw.loc[0, "ast"] = float("nan")
        raw.to_csv(path, index=False)
    reset_data_source_cache()
    answer = execute_natural_query(
        "How many different players had (over 20 points or over 10 assists) in 2025-26?"
    )
    assert answer.result_status != "ok"
    assert "primary_count" not in answer.metadata


def test_shared_bare_threshold_and_zero_vocabulary(population):
    answer = execute_natural_query(
        "How many different players had (20 points or 10 assists) and zero turnovers in 2025-26?"
    )
    assert answer.result_status == "ok", answer.metadata
    assert answer.metadata["primary_count"] == 3
    assert {r["player_id"] for r in answer.to_dict()["sections"]["leaderboard"]} == set(
        population.values()
    )


def test_missing_requested_season_never_returns_partial_union(population):
    answer = execute_structured_query(
        "player_occurrence_leaders",
        start_season="2021-22",
        end_season="2025-26",
        condition_expression="over 20 points or over 10 assists",
        limit=None,
    )
    assert answer.result_status != "ok"
    assert answer.result_reason == "no_data"


@pytest.mark.parametrize(
    "wording",
    ["Boston or Phoenix", "Boston or against Phoenix", "Boston, Phoenix", "Boston and Phoenix"],
)
def test_common_opponent_list_cannot_become_subject_team(wording):
    raw = pd.read_csv(RAW)
    expected = raw.loc[
        raw.opponent_team_abbr.isin(["BOS", "PHX"]) & (raw.pts.gt(20) | raw.ast.gt(10))
    ]
    answer = execute_natural_query(
        f"How many distinct players had (over 20 points or over 10 assists) in 2025-26 against {wording}?"
    )
    assert answer.result_status == "ok", answer.metadata
    assert answer.metadata["primary_count"] == expected.player_id.nunique()
    assert answer.metadata["team"] is None
    assert set(answer.metadata["opponents"]) == {"BOS", "PHX"}
    assert {
        r["player_id"]: r["matching_games"] for r in answer.to_dict()["sections"]["leaderboard"]
    } == expected.groupby("player_id").size().to_dict()


def test_common_team_and_opponent_union_are_separate_filters():
    raw = pd.read_csv(RAW)
    expected = raw.loc[
        raw.team_abbr.eq("LAL")
        & raw.opponent_team_abbr.isin(["BOS", "PHX"])
        & (raw.pts.gt(20) | raw.ast.gt(10))
    ]
    answer = execute_natural_query(
        "How many Lakers players had (over 20 points or over 10 assists) in 2025-26 against Boston or against Phoenix?"
    )
    assert answer.result_status == "ok", answer.metadata
    assert answer.metadata["team"] == "LAL"
    assert answer.metadata["primary_count"] == expected.player_id.nunique()


@pytest.mark.parametrize(
    "scope", ["at home or on the road", "against Boston or against UnknownClub"]
)
def test_unrepresented_outer_scope_or_withholds(scope):
    answer = execute_natural_query(
        f"How many distinct players had (over 20 points or over 10 assists) in 2025-26 {scope}?"
    )
    assert answer.result_status != "ok"
    assert "primary_count" not in answer.metadata
