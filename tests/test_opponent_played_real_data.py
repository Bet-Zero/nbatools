"""Opponent played predicates use frozen same-game identity and source evidence."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(
    (Path(__file__).parent / "fixtures/opponent_played/source_oracle.json").read_text()
)


@pytest.mark.parametrize("case", ORACLE["primary_cases"])
@pytest.mark.parametrize("consumer", ["natural", "when_plays", "structured"])
def test_opponent_played_has_qualified_same_game_membership(case, consumer):
    season = case["query"].split()[-1]
    for path, digest in ORACLE["sources"].items():
        if season in path:
            assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    report = pd.read_csv(data_path(f"raw/player_game_availability/{season}_regular_season.csv"))
    players = pd.read_csv(data_path(f"raw/player_game_stats/{season}_regular_season.csv"))
    teams = pd.read_csv(data_path(f"raw/team_game_stats/{season}_regular_season.csv"))
    selected = teams.loc[
        teams.team_id.eq(case["subject_id"]) & teams.opponent_team_id.eq(case["predicate_side_id"])
    ]
    assert sorted(selected.game_id.astype(int)) == case["candidate_game_ids"]
    for fact in case["observations"]:
        source = report.loc[
            report.game_id.eq(fact["game_id"]) & report.player_id.eq(fact["player_id"])
        ]
        assert len(source) == 1
        row = source.iloc[0]
        for key in ("team_id", "participation_state", "source_sha256", "game_date"):
            assert row[key] == fact[key]
        subject = selected.loc[selected.game_id.eq(fact["game_id"])].iloc[0]
        assert subject.game_date == fact["game_date"] and subject.opponent_team_id == row.team_id
        positive = players.loc[
            players.game_id.eq(fact["game_id"])
            & players.player_id.eq(fact["player_id"])
            & pd.to_numeric(players.minutes, errors="coerce").gt(0)
        ]
        if fact["participation_state"] == "played":
            assert len(positive) == 1
            assert positive.iloc[0].team_id == row.team_id
            assert positive.iloc[0].game_date == row.game_date
        else:
            assert positive.empty
    if consumer == "structured":
        result = execute_structured_query(
            "team_record", team="LAL", opponent="BOS", with_player="Jayson Tatum", season=season
        )
    else:
        query = (
            case["query"]
            if consumer == "natural"
            else case["query"].replace("with Jayson Tatum playing", "when Jayson Tatum plays")
        )
        result = execute_natural_query(query)
    assert result.route == "team_record"
    meta = result.metadata
    assert meta["team_context"]["team_id"] == case["subject_id"]
    assert meta["opponent_context"]["team_id"] == case["predicate_side_id"]
    assert meta["with_player"] == "Jayson Tatum" and not meta["without_player"]
    sections = result.result.to_dict()["sections"]
    expected = case["expected"]
    if not expected["games"]:
        assert result.result_status == "no_result" and result.result_reason == "no_match"
        assert not sections
        return
    assert result.result_status == "ok"
    rows = sections["game_log"]
    assert sorted(int(row["game_id"]) for row in rows) == expected["game_ids"]
    assert all(
        row["team_id"] == case["subject_id"]
        and row["opponent_team_id"] == case["predicate_side_id"]
        for row in rows
    )
    summary = sections["summary"][0]
    for key in ("games", "wins", "losses"):
        assert summary[key] == expected[key]
    for stat, total in expected["sums"].items():
        assert sum(row[stat] for row in rows) == total
        assert summary[stat + "_avg"] == pytest.approx(expected["means"][stat])


def test_additional_qualified_clause_returns_source_proven_conjunction_empty():
    """Promote the exact natural obligation, retaining its historical baseline."""
    obligation = json.loads(
        (
            Path(__file__).parent / "fixtures/opponent_played/additional_clause_obligation.json"
        ).read_text()
    )
    report = pd.read_csv(data_path("raw/player_game_availability/2023-24_regular_season.csv"))
    for fact in obligation["independent_source_rows"]:
        row = report.loc[
            report.game_id.eq(fact["game_id"]) & report.player_id.eq(fact["player_id"])
        ].iloc[0]
        for key, value in fact.items():
            assert row[key] == value
    structured = execute_structured_query(
        "team_record",
        team="LAL",
        opponent="BOS",
        with_player="Jayson Tatum and Gabe Vincent",
        season="2023-24",
    )
    assert structured.result_status == "no_result" and structured.result_reason == "no_match"
    assert not structured.result.to_dict()["sections"]
    for query in [
        obligation["query"],
        obligation["query"].replace(
            "playing while Gabe Vincent plays", "playing, Gabe Vincent plays"
        ),
        obligation["query"].replace("playing while Gabe Vincent plays", ", Gabe Vincent playing"),
    ]:
        natural = execute_natural_query(query)
        assert natural.result_status == "no_result" and natural.result_reason == "no_match"
        assert not natural.result.to_dict()["sections"]
        assert natural.metadata["with_player"] == "Jayson Tatum and Gabe Vincent"
        assert not natural.metadata["unsupported_filters"]


@pytest.mark.parametrize(
    "mode,season,game,wins,totals",
    [
        ("with", "2023-24", 22300684, 1, (114, 52, 30)),
        ("without", "2025-26", 22500338, 0, (105, 35, 15)),
    ],
)
def test_understood_road_setting_is_not_an_unresolved_second_player(
    mode, season, game, wins, totals
):
    result = execute_natural_query(
        f"Lakers record against Celtics {mode} Tatum and on the road in {season}"
    )
    assert result.result_status == "ok", result.metadata
    rows = result.result.to_dict()["sections"]["game_log"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == game
    assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
    assert rows[0]["is_away"] == 1
    assert tuple(rows[0][stat] for stat in ("pts", "reb", "ast")) == totals
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == 1 and summary["wins"] == wins
