"""Original-window versus qualifying played samples from unchanged official sources."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE_PATH = (
    Path(__file__).parent / "fixtures/original_window_played_pair/source_and_baseline.json"
)
ORACLE = json.loads(ORACLE_PATH.read_text())


@pytest.mark.parametrize(
    "which,scope",
    [(0, "original_window"), (0, "qualifying"), (1, "original_window")],
    ids=["qualified-empty-original", "latest-qualifying", "positive-original"],
)
def test_original_and_qualifying_windows_keep_source_order_identity_and_numbers(which, scope):
    assert (
        hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest()
        == "572c17fd53172c1f8dfcc2b53f782a0943dfc06e50bfc58209851d361f4e3f6b"
    )
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest

    def raw(kind):
        return pd.read_csv(data_path(f"raw/{kind}/2023-24_regular_season.csv"))

    teams, players, report = (
        raw("team_game_stats"),
        raw("player_game_stats"),
        raw("player_game_availability"),
    )
    candidates = teams.loc[
        teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)
    ].sort_values(["game_date", "game_id"], ascending=False)
    assert candidates.game_id.astype(int).tolist() == [22300684, 22300403]
    case = ORACLE["helper_order_oracles"][which]
    names = case["names"].split(" and ")
    # Independently qualify each named same-game side/date and its source PDF;
    # no engine-selected rows are used to derive expected membership or totals.
    selected = []
    for game in candidates.itertuples():
        played = []
        for name in names:
            observation = report.loc[report.game_id.eq(game.game_id) & report.player_name.eq(name)]
            assert len(observation) == 1
            fact = observation.iloc[0]
            assert fact.team_id in [game.team_id, game.opponent_team_id]
            assert fact.game_date == game.game_date
            assert fact.coverage_scope == "listed_player_rows_only"
            assert (
                hashlib.sha256(
                    data_path(
                        "raw/player_game_availability_sources/" + fact.source_sha256 + ".pdf"
                    ).read_bytes()
                ).hexdigest()
                == fact.source_sha256
            )
            appearances = players.loc[
                players.game_id.eq(game.game_id)
                & players.player_name.eq(name)
                & players.minutes.gt(0)
            ]
            assert len(appearances) == int(fact.participation_state == "played")
            if len(appearances):
                assert appearances.iloc[0].team_id == fact.team_id
                assert appearances.iloc[0].game_date == fact.game_date
            else:
                assert fact.participation_state == "did_not_play" and fact.source_comment
            played.append(fact.participation_state == "played")
        if all(played):
            selected.append(int(game.game_id))
        if scope == "original_window" or selected:
            break
    expected = case[
        "qualified_inside_original_window" if scope == "original_window" else "latest_qualifying"
    ]
    assert selected == expected["game_ids"]
    source_rows = candidates.loc[candidates.game_id.isin(selected)]
    assert len(source_rows) == expected["games"]
    assert int(source_rows.wl.eq("W").sum()) == expected["wins"]
    for stat, total in expected["sums"].items():
        assert source_rows[stat].sum() == total
    scopes = (
        [
            "within their last 1 game",
            "among their last 1 game",
            "of their last 1 game",
            "within their last game",
            "among their last meeting",
            "in their last 1 original game",
        ]
        if scope == "original_window"
        else ["in their last 1 qualifying game", "in their last qualifying meeting"]
    )
    results = [
        execute_natural_query(
            f"Lakers record against Celtics {phrase} with {names[0]} playing while {names[1]} plays in 2023-24"
        )
        for phrase in scopes
    ]
    results.append(
        execute_natural_query(
            f"Lakers record against Celtics with {names[1]} playing while {names[0]} plays {scopes[0]} in 2023-24"
        )
    )
    results.append(
        execute_structured_query(
            "team_record",
            team="LAL",
            opponent="BOS",
            season="2023-24",
            with_player=case["names"],
            last_n=1,
            last_n_scope=scope,
        )
    )
    for result in results:
        assert result.route == "team_record"
        assert result.metadata["last_n_scope"] == scope
        assert result.metadata["with_player"] in [case["names"], " and ".join(reversed(names))]
        assert result.metadata["team_context"]["team_id"] == 1610612747
        assert result.metadata["opponent_context"]["team_id"] == 1610612738
        assert result.metadata["player"] is None and not result.metadata["unsupported_filters"]
        assert {
            "label": "With player",
            "value": result.metadata["with_player"],
            "kind": "player",
        } in result.metadata["applied_filters"]
        selection = next(
            f["value"]
            for f in result.metadata["applied_filters"]
            if f["label"] == "Sample selection"
        )
        assert ("before checking both played" in selection) == (scope == "original_window")
        sections = result.result.to_dict()["sections"]
        if not expected["games"]:
            assert result.result_status == "no_result" and result.result_reason == "no_match"
            assert not sections
            assert any("selected 1" in note for note in result.result.to_dict()["notes"])
            continue
        assert result.result_status == "ok"
        rows = sections["game_log"]
        assert [int(row["game_id"]) for row in rows] == expected["game_ids"]
        summary = sections["summary"][0]
        for key in ["games", "wins", "losses"]:
            assert summary[key] == expected[key]
        for stat, total in expected["sums"].items():
            assert sum(row[stat] for row in rows) == total == summary[stat + "_avg"]
        assert rows[0]["game_date"] == source_rows.game_date.iloc[0]
        assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
