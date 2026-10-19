"""Known Yes/No derives from canonical raw rows and retained official source bytes."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE_PATH = Path(__file__).parent / "fixtures/latest_original_both/source_and_baseline.json"
ORACLE = json.loads(ORACLE_PATH.read_text())


@pytest.mark.parametrize("which", [0, 1], ids=["known-false", "known-true"])
def test_latest_original_both_from_qualified_official_facts(which):
    assert (
        hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest()
        == "8f0de7f0086aab457a62d957dd287fc4fd1212264aa9c6b201ad201e11e4cc44"
    )
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        return pd.read_csv(data_path(f"raw/{kind}/2023-24_regular_season.csv"))

    teams, games, players, observations = (
        raw(k)
        for k in ("team_game_stats", "games", "player_game_stats", "player_game_availability")
    )
    candidates = teams.loc[
        teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)
    ].sort_values(["game_date", "game_id"], ascending=False)
    assert candidates.game_id.astype(int).tolist() == [22300684, 22300403]
    original = candidates.iloc[0]
    assert original.game_date == "2024-02-01"
    schedule = games.loc[games.game_id.eq(original.game_id)]
    assert len(schedule) == 1 and schedule.iloc[0].game_date == original.game_date
    reciprocal = teams.loc[teams.game_id.eq(original.game_id) & teams.team_id.eq(1610612738)]
    assert len(reciprocal) == 1 and reciprocal.iloc[0].opponent_team_id == original.team_id
    assert reciprocal.iloc[0].game_date == original.game_date
    case = ORACLE["cases"][which]
    states = []
    for player_id, name in case["players"]:
        expected_side = 1610612738 if player_id == 1628369 else 1610612747
        rows = observations.loc[
            observations.game_id.eq(original.game_id) & observations.player_id.eq(player_id)
        ]
        assert len(rows) == 1
        fact = rows.iloc[0]
        assert fact.player_id == player_id and fact.player_name == name
        assert fact.team_id == expected_side and fact.game_date == original.game_date
        assert fact.coverage_scope == "listed_player_rows_only"
        assert fact.source == "nba_official_finalbox:20240201_LALBOS"
        assert (
            fact.source_sha256 == "98f2dbbf9db7b64a99a19e80721196ec788632c5ba0bae881c70bcd3799cfda4"
        )
        appearances = players.loc[
            players.game_id.eq(original.game_id)
            & players.player_id.eq(player_id)
            & players.minutes.gt(0)
        ]
        if player_id == 203076:
            assert fact.participation_state == "did_not_play" and fact.source_comment
            assert appearances.empty
        else:
            assert fact.participation_state == "played" and len(appearances) == 1
            appearance = appearances.iloc[0]
            assert appearance.player_id == fact.player_id == player_id
            assert appearance.team_id == fact.team_id == expected_side
            assert appearance.game_date == fact.game_date
        states.append(fact.participation_state == "played")
    truth = all(states)
    assert truth is case["desired"]["truth"]
    queries = [
        case["query"],
        f"Did both {case['players'][1][1]} and Jayson Tatum play in the Lakers latest original game against Boston in 2023-24?",
    ]
    for query in queries:
        result = execute_natural_query(query)
        assert result.result_status == "ok" and result.route == "game_finder"
        assert (
            result.metadata["player"] is None
            and result.metadata["team"] == "LAL"
            and result.metadata["opponent"] == "BOS"
        )
        assert result.metadata["season"] == "2023-24" and result.metadata["last_n"] == 1
        assert result.metadata["last_n_scope"] == "window"
        assert not result.metadata["with_player"] and not result.metadata["without_player"]
        assert not result.metadata["unsupported_filters"]
        request = next(
            json.loads(n.split(":", 1)[1])
            for n in result.metadata["notes"]
            if n.startswith("yes_no_last_game:")
        )
        assert request["event"] == "played_pair"
        assert set(request["players"]) == {name for _pid, name in case["players"]}
        phrase = result.metadata["answer_phrase"]
        assert phrase.startswith("Yes:" if truth else "No:") and "2024-02-01" in phrase
        assert all(name in phrase for _pid, name in case["players"])
        rows = result.result.to_dict()["sections"]["finder"]
        assert len(rows) == 1 and int(rows[0]["game_id"]) == 22300684
        assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
        assert str(rows[0]["game_date"])[:10] == "2024-02-01"
        assert [rows[0][stat] for stat in ("pts", "reb", "ast")] == [114, 52, 30]
        filters = result.metadata["applied_filters"]
        assert not any(f["label"] in ("With player", "Without player") for f in filters)
        assert any(
            f["label"] == "Played check"
            and all(name in f["value"] for _pid, name in case["players"])
            for f in filters
        )
        assert any(
            f["label"] == "Sample selection"
            and "original" in f["value"]
            and "before checking" in f["value"]
            for f in filters
        )
