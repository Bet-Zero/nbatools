"""Two natural played predicates consume independently frozen report facts."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(
    (Path(__file__).parent / "fixtures/qualified_played_pair/source_oracle.json").read_text()
)


@pytest.mark.parametrize("case", ORACLE["cases"], ids=["qualified-empty", "both-played"])
def test_natural_played_pair_source_identity_sample_numbers_and_labels(case):
    for path, expected_hash in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == expected_hash
    report = pd.read_csv(data_path("raw/player_game_availability/2023-24_regular_season.csv"))
    players = pd.read_csv(data_path("raw/player_game_stats/2023-24_regular_season.csv"))
    teams = pd.read_csv(data_path("raw/team_game_stats/2023-24_regular_season.csv"))
    sample = teams.loc[teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)]
    assert sorted(sample.game_id.astype(int)) == case["candidate_game_ids"]
    for fact in case["source_observations"]:
        actual = report.loc[
            report.game_id.eq(int(fact["game_id"])) & report.player_id.eq(int(fact["player_id"]))
        ]
        assert len(actual) == 1
        row = actual.iloc[0]
        for key in ["team_id", "player_id"]:
            assert int(row[key]) == int(fact[key])
        for key in [
            "player_name",
            "game_date",
            "participation_state",
            "source",
            "source_sha256",
            "coverage_scope",
        ]:
            assert row[key] == fact[key]
        if fact["source_minutes"]:
            assert row.source_minutes == pytest.approx(float(fact["source_minutes"]))
        else:
            assert pd.isna(row.source_minutes)
        assert ("" if pd.isna(row.source_comment) else row.source_comment) == fact["source_comment"]
        assert (
            hashlib.sha256(
                data_path(
                    "raw/player_game_availability_sources/" + fact["source_sha256"] + ".pdf"
                ).read_bytes()
            ).hexdigest()
            == fact["source_sha256"]
        )
        positive = players.loc[
            players.game_id.eq(int(fact["game_id"]))
            & players.player_id.eq(int(fact["player_id"]))
            & players.minutes.gt(0)
        ]
        assert len(positive) == (1 if fact["participation_state"] == "played" else 0)
        if not positive.empty:
            assert positive.iloc[0].team_id == row.team_id
            assert positive.iloc[0].game_date == row.game_date
    for fact in ORACLE["candidate_team_rows"]:
        row = sample.loc[sample.game_id.eq(int(fact["game_id"]))].iloc[0]
        for key in ["pts", "reb", "ast"]:
            assert row[key] == float(fact[key])
        assert row.game_date == fact["game_date"] and row.wl == fact["wl"]
    first, second = case["names"]
    clauses = [
        f"with {first} playing while {second} plays",
        f"when {first} plays and {second} plays",
        f"with {first} playing, {second} plays",
        f"with {first}, {second} playing",
        f"with {first} and {second} both playing",
        f"with {second} playing while {first} plays",
    ]
    results = [
        execute_natural_query(f"Lakers record against Celtics {clause} in 2023-24")
        for clause in clauses
    ]
    results.append(
        execute_structured_query(
            "team_record",
            team="LAL",
            opponent="BOS",
            with_player=" and ".join(case["names"]),
            season="2023-24",
        )
    )
    expected = case["expected"]
    for result in results:
        assert result.route == "team_record"
        assert result.metadata["player"] is None
        assert result.metadata["team_context"]["team_id"] == 1610612747
        assert result.metadata["opponent_context"]["team_id"] == 1610612738
        assert result.metadata["with_player"] in [f"{first} and {second}", f"{second} and {first}"]
        assert not result.metadata["without_player"] and not result.metadata["unsupported_filters"]
        assert {
            "label": "With player",
            "value": result.metadata["with_player"],
            "kind": "player",
        } in result.metadata["applied_filters"]
        sections = result.result.to_dict()["sections"]
        if not expected["games"]:
            assert result.result_status == "no_result" and result.result_reason == "no_match"
            assert not sections
            continue
        assert result.result_status == "ok"
        rows = sections["game_log"]
        assert sorted(int(row["game_id"]) for row in rows) == expected["game_ids"]
        assert all(
            row["team_id"] == 1610612747 and row["opponent_team_id"] == 1610612738 for row in rows
        )
        summary = sections["summary"][0]
        for key in ["games", "wins", "losses"]:
            assert summary[key] == expected[key]
        for stat, total in expected["sums"].items():
            assert sum(row[stat] for row in rows) == total
            assert summary[stat + "_avg"] == pytest.approx(total / expected["games"])
