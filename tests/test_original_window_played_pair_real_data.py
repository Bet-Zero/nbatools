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
SOURCE_IDENTITIES = {
    "Jayson Tatum": (1628369, 1610612738),
    "Anthony Davis": (203076, 1610612747),
    "Austin Reaves": (1630559, 1610612747),
    "LeBron James": (2544, 1610612747),
}


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
            player_id, team_id = SOURCE_IDENTITIES[name]
            observation = report.loc[
                report.game_id.eq(game.game_id) & report.player_id.eq(player_id)
            ]
            assert len(observation) == 1
            fact = observation.iloc[0]
            assert fact.player_id == player_id and fact.player_name == name
            assert fact.team_id == team_id
            assert team_id == (game.opponent_team_id if name == "Jayson Tatum" else game.team_id)
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
                & players.player_id.eq(player_id)
                & players.minutes.gt(0)
            ]
            assert len(appearances) == int(fact.participation_state == "played")
            if len(appearances):
                appearance = appearances.iloc[0]
                assert appearance.player_id == fact.player_id == player_id
                assert appearance.player_name == fact.player_name == name
                assert appearance.team_id == fact.team_id == team_id
                assert appearance.game_date == fact.game_date
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


@pytest.mark.parametrize(
    "last_n,expected_ids,expected_totals",
    [
        (None, [22300403, 22300684], [229, 95, 54]),
        (1, [22300684], [114, 52, 30]),
    ],
)
def test_unset_scope_keeps_accepted_record_sample(last_n, expected_ids, expected_totals):
    teams = pd.read_csv(data_path("raw/team_game_stats/2023-24_regular_season.csv"))
    assert (
        hashlib.sha256(
            data_path("raw/team_game_stats/2023-24_regular_season.csv").read_bytes()
        ).hexdigest()
        == ORACLE["source_hashes"]["raw/team_game_stats/2023-24_regular_season.csv"]
    )
    candidates = teams.loc[
        teams.team_id.eq(1610612747) & teams.opponent_team_id.eq(1610612738)
    ].sort_values(["game_date", "game_id"], ascending=False)
    selected = candidates if last_n is None else candidates.head(last_n)
    assert sorted(selected.game_id.astype(int)) == expected_ids
    assert [int(selected[stat].sum()) for stat in ["pts", "reb", "ast"]] == expected_totals
    for scope in [None, "qualifying"]:
        result = execute_structured_query(
            "team_record",
            team="LAL",
            opponent="BOS",
            season="2023-24",
            last_n=last_n,
            last_n_scope=scope,
        )
        assert result.result_status == "ok"
        sections = result.result.to_dict()["sections"]
        if last_n:
            assert sorted(int(row["game_id"]) for row in sections["game_log"]) == expected_ids
        else:
            assert "game_log" not in sections
        summary = sections["summary"][0]
        assert summary["games"] == len(expected_ids)
        assert summary["wins"] == int(selected.wl.eq("W").sum())
        assert summary["losses"] == int(selected.wl.eq("L").sum())
        for stat, total in zip(["pts", "reb", "ast"], expected_totals):
            if last_n:
                assert sum(row[stat] for row in sections["game_log"]) == total
            assert summary[stat + "_avg"] == total / len(expected_ids)


REVEALED_PATH = (
    Path(__file__).parent / "fixtures/original_window_played_pair/revealed_controls.json"
)
REVEALED = json.loads(REVEALED_PATH.read_text())


@pytest.mark.parametrize("case", REVEALED["cases"], ids=["opposite-subject", "other-season"])
@pytest.mark.parametrize("scope", ["original_window", "qualifying"])
def test_root_preimplementation_temporal_controls_now_revealed(case, scope):
    """Root froze these temporal expectations before implementation.

    These are retained revealed temporal controls, not newly unfamiliar entities:
    the entities were prior PR522 controls. Neither the engine nor maker supplied
    their independently frozen original-versus-qualifying expectations.
    """
    assert (
        hashlib.sha256(REVEALED_PATH.read_bytes()).hexdigest()
        == "396ae52b7f88efdeb6d7a731b6a1bc30f3d0785ee91f3ffeb42f34dbca3c15ce"
    )
    for path, digest in REVEALED["source_hashes"].items():
        if case["season"] in path or path.endswith(".pdf"):
            assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    suffix = case["season"] + "_regular_season.csv"
    teams = pd.read_csv(data_path("raw/team_game_stats/" + suffix))
    players = pd.read_csv(data_path("raw/player_game_stats/" + suffix))
    report = pd.read_csv(data_path("raw/player_game_availability/" + suffix))
    candidates = teams.loc[
        teams.team_abbr.eq(case["subject"]) & teams.opponent_team_abbr.eq(case["opponent"])
    ].sort_values(["game_date", "game_id"], ascending=False)
    assert sorted(candidates.game_id.astype(int)) == sorted(
        int(row["game_id"]) for row in case["candidate_rows"]
    )
    subject_id = int(case["candidate_rows"][0]["team_id"])
    opponent_id = int(case["candidate_rows"][0]["opponent_team_id"])
    by_id = {int(row["game_id"]): row for row in case["candidate_rows"]}
    fact_lookup = {(int(row["game_id"]), int(row["player_id"])): row for row in case["facts"]}
    played_ids = []
    for game in candidates.itertuples():
        frozen = by_id[int(game.game_id)]
        assert game.team_id == subject_id and game.opponent_team_id == opponent_id
        assert game.game_date == frozen["game_date"] and game.wl == frozen["wl"]
        for stat in ["pts", "reb", "ast"]:
            assert getattr(game, stat) == float(frozen[stat])
        reciprocal = teams.loc[teams.game_id.eq(game.game_id) & teams.team_id.eq(opponent_id)]
        assert len(reciprocal) == 1 and reciprocal.iloc[0].opponent_team_id == subject_id
        assert reciprocal.iloc[0].game_date == game.game_date
        states = []
        for player_id, name in case["players"]:
            frozen_fact = fact_lookup[(int(game.game_id), player_id)]
            actual = report.loc[report.game_id.eq(game.game_id) & report.player_id.eq(player_id)]
            assert len(actual) == 1
            row = actual.iloc[0]
            assert row.player_id == int(frozen_fact["player_id"]) == player_id
            assert row.player_name == frozen_fact["player_name"] == name
            assert row.team_id == int(frozen_fact["team_id"]) and row.team_id in {
                subject_id,
                opponent_id,
            }
            assert row.game_date == frozen_fact["game_date"] == game.game_date
            for key in ["participation_state", "source", "source_sha256", "coverage_scope"]:
                assert row[key] == frozen_fact[key]
            assert ("" if pd.isna(row.source_comment) else row.source_comment) == frozen_fact[
                "source_comment"
            ]
            assert row.coverage_scope == "listed_player_rows_only"
            assert (
                hashlib.sha256(
                    data_path(
                        "raw/player_game_availability_sources/" + row.source_sha256 + ".pdf"
                    ).read_bytes()
                ).hexdigest()
                == row.source_sha256
            )
            appearance = players.loc[
                players.game_id.eq(game.game_id)
                & players.player_id.eq(player_id)
                & players.minutes.gt(0)
            ]
            assert len(appearance) == int(row.participation_state == "played")
            if len(appearance):
                assert appearance.iloc[0].player_id == row.player_id == player_id
                assert appearance.iloc[0].team_id == row.team_id
                assert appearance.iloc[0].game_date == row.game_date
                assert appearance.iloc[0].player_name == name
                assert row.source_minutes == pytest.approx(float(frozen_fact["source_minutes"]))
            else:
                assert row.participation_state == "did_not_play" and pd.isna(row.source_minutes)
            states.append(row.participation_state == "played")
        if all(states):
            played_ids.append(int(game.game_id))
    latest_original = int(candidates.iloc[0].game_id)
    independently_selected = [latest_original] if latest_original in played_ids else []
    if scope == "qualifying":
        independently_selected = played_ids[:1]
    expected = case["window_last1_ids" if scope == "original_window" else "qualifying_last1_ids"]
    assert independently_selected == expected
    selected = candidates.loc[candidates.game_id.isin(expected)]
    first, second = [player[1] for player in case["players"]]
    phrase = (
        "among their last meeting"
        if scope == "original_window"
        else "in their last qualifying meeting"
    )
    results = [
        execute_natural_query(
            f"{case['subject']} record against {case['opponent']} {phrase} with {first} playing while {second} plays in {case['season']}"
        ),
        execute_structured_query(
            "team_record",
            team=case["subject"],
            opponent=case["opponent"],
            season=case["season"],
            with_player=f"{first} and {second}",
            last_n=1,
            last_n_scope=scope,
        ),
    ]
    for result in results:
        assert result.route == "team_record" and result.metadata["player"] is None
        assert result.metadata["last_n_scope"] == scope and result.metadata["last_n"] == 1
        assert result.metadata["with_player"] == f"{first} and {second}"
        assert result.metadata["team_context"]["team_id"] == subject_id
        assert result.metadata["opponent_context"]["team_id"] == opponent_id
        assert not result.metadata["without_player"] and not result.metadata["unsupported_filters"]
        assert {
            "kind": "player",
            "label": "With player",
            "value": f"{first} and {second}",
        } in result.metadata["applied_filters"]
        label = next(
            f["value"]
            for f in result.metadata["applied_filters"]
            if f["label"] == "Sample selection"
        )
        assert label == (
            "Select the last 1 original matchup game before checking both played predicates"
            if scope == "original_window"
            else "Select the last 1 games matching the conditions"
        )
        sections = result.result.to_dict()["sections"]
        if not expected:
            assert result.result_reason == "no_match" and result.result_status == "no_result"
            assert not sections
            continue
        assert result.result_status == "ok"
        rows = sections["game_log"]
        assert [int(row["game_id"]) for row in rows] == expected
        assert rows[0]["game_date"] == selected.game_date.iloc[0]
        assert rows[0]["team_id"] == subject_id and rows[0]["opponent_team_id"] == opponent_id
        summary = sections["summary"][0]
        assert summary["games"] == len(expected)
        assert summary["wins"] == int(selected.wl.eq("W").sum())
        assert summary["losses"] == int(selected.wl.eq("L").sum())
        for stat in ["pts", "reb", "ast"]:
            assert sum(row[stat] for row in rows) == selected[stat].sum()
            assert summary[stat + "_avg"] == selected[stat].mean()


@pytest.mark.parametrize("scope", [None, "qualifying", "window"])
def test_legacy_played_pair_windows_and_native_bare_last_n_keep_christmas(scope):
    # Frozen preimplementation helper oracle, checked against actual source facts
    # above: participation cohort excludes Feb1 (AD explicitly DNP) before N.
    expected = ORACLE["helper_order_oracles"][0]["latest_qualifying"]
    assert expected["game_ids"] == [22300403]
    assert expected["sums"] == {"pts": 115, "reb": 43, "ast": 24}
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    teams = pd.read_csv(data_path("raw/team_game_stats/2023-24_regular_season.csv"))
    report = pd.read_csv(data_path("raw/player_game_availability/2023-24_regular_season.csv"))
    appearances = pd.read_csv(data_path("raw/player_game_stats/2023-24_regular_season.csv"))
    qualified_ids = []
    for game_id, date in [(22300403, "2023-12-25"), (22300684, "2024-02-01")]:
        states = []
        for name in ["Jayson Tatum", "Anthony Davis", "LeBron James"]:
            player_id, team_id = SOURCE_IDENTITIES[name]
            fact = report.loc[report.game_id.eq(game_id) & report.player_id.eq(player_id)]
            assert len(fact) == 1
            row = fact.iloc[0]
            assert row.player_id == player_id and row.team_id == team_id
            assert row.player_name == name and row.game_date == date
            assert row.coverage_scope == "listed_player_rows_only"
            should_play = game_id == 22300403 or name == "Jayson Tatum"
            assert row.participation_state == ("played" if should_play else "did_not_play")
            positive = appearances.loc[
                appearances.game_id.eq(game_id)
                & appearances.player_id.eq(player_id)
                & appearances.minutes.gt(0)
            ]
            assert len(positive) == int(should_play)
            if len(positive):
                assert positive.iloc[0].player_id == row.player_id == player_id
                assert positive.iloc[0].team_id == row.team_id == team_id
                assert positive.iloc[0].game_date == row.game_date == date
            states.append(should_play)
        if all(states):
            qualified_ids.append(game_id)
    assert qualified_ids == expected["game_ids"]
    source = teams.loc[teams.team_id.eq(1610612747) & teams.game_id.eq(22300403)]
    assert len(source) == 1 and source.iloc[0].opponent_team_id == 1610612738
    assert source.iloc[0].game_date == "2023-12-25" and source.iloc[0].wl == "L"
    results = [
        (
            execute_structured_query(
                "team_record",
                team="LAL",
                opponent="BOS",
                season="2023-24",
                with_player="Jayson Tatum and Anthony Davis",
                last_n=1,
                last_n_scope=scope,
            ),
            "Jayson Tatum and Anthony Davis",
            scope,
        )
    ]
    if scope is None:
        results.append(
            (
                execute_natural_query(
                    "Lakers record against Celtics with LeBron James and Anthony Davis last 1 game in 2023-24"
                ),
                "LeBron James and Anthony Davis",
                "qualifying",
            )
        )
    for result, pair, expected_scope in results:
        assert result.result_status == "ok" and result.route == "team_record"
        assert result.metadata["with_player"] == pair
        assert result.metadata["last_n_scope"] == expected_scope
        assert {"kind": "player", "label": "With player", "value": pair} in result.metadata[
            "applied_filters"
        ]
        sections = result.result.to_dict()["sections"]
        assert [int(row["game_id"]) for row in sections["game_log"]] == expected["game_ids"]
        summary = sections["summary"][0]
        assert summary["games"] == 1 and summary["wins"] == 0 and summary["losses"] == 1
        for stat, total in expected["sums"].items():
            assert sections["game_log"][0][stat] == source.iloc[0][stat] == total
            assert summary[stat + "_avg"] == total
