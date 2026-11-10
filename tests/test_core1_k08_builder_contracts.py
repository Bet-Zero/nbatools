"""Native route schemas on retained source rows; not new original-case NBA proof."""

import pandas as pd
import pytest

from nbatools.commands import game_finder, game_summary, player_game_summary, team_record
from tests.core1_k08_served_default_cases import (
    STATS,
    _sample,
    assert_summary_metrics,
    player_team_context,
)
from tests.test_core1_k08_raw_player_context import SOURCE


@pytest.fixture
def native(monkeypatch):
    players, teams, catalog = [
        pd.read_csv(SOURCE / k / "2025-26_regular_season.csv")
        for k in ("player_game_stats", "team_game_stats", "games")
    ]
    players = player_team_context(players, teams, catalog)
    monkeypatch.setattr(team_record, "load_team_games_for_seasons", lambda *a, **k: teams.copy())
    monkeypatch.setattr(game_finder, "load_team_games_for_seasons", lambda *a, **k: teams.copy())
    monkeypatch.setattr(
        player_game_summary, "load_team_games_for_seasons", lambda *a, **k: teams.copy()
    )
    for module in (team_record, game_finder, game_summary, player_game_summary):
        monkeypatch.setattr(
            module, "compute_current_through_for_seasons", lambda *a, **k: "2026-02-01"
        )
    return players, teams


@pytest.mark.parametrize("route", ["team_record", "game_summary", "player_game_summary"])
def test_native_builder_publishes_the_frozen_route_specific_required_metrics(native, route):
    players, teams = native
    if route == "team_record":
        expected = teams.loc[teams.team_abbr.eq("BOS")]
        result = team_record.build_team_record_result(team="BOS", season="2025-26", last_n=1)
    elif route == "game_summary":
        expected = teams.loc[teams.team_abbr.eq("BOS")]
        result = game_summary.build_result(
            team="BOS", season="2025-26", df=expected.copy(), player_df=players.copy()
        )
    else:
        expected = players.loc[players.player_name.eq("Jaylen Brown")]
        result = player_game_summary.build_result(
            player="Jaylen Brown", season="2025-26", df=expected.copy()
        )
    assert result.result_status == "ok"
    sections = result.to_dict()["sections"]
    oracle = _sample(expected, player=route == "player_game_summary")
    assert_summary_metrics(sections["summary"][0], oracle, route)
    assert len(sections["game_log"]) == len(expected) == 1
    for stat in STATS:
        assert stat in sections["game_log"][0]
        assert sections["game_log"][0][stat] == oracle["rows"][0][stat]
    if route == "team_record":
        assert "fgm_avg" not in sections["summary"][0]
        assert not any(k.endswith("_sum") for k in sections["summary"][0])


def test_native_team_finder_keeps_all_required_row_metrics_without_inventing_numeric_team_key(
    native,
):
    _, teams = native
    result = game_finder.build_result(team="BOS", season="2025-26", limit=82)
    assert result.result_status == "ok"
    (row,) = result.to_dict()["sections"]["finder"]
    expected = teams.loc[teams.team_abbr.eq("BOS")].iloc[0]
    assert row["team_abbr"] == "BOS" and "team_id" not in row
    for stat in STATS:
        assert row[stat] == expected[stat]


def test_native_qualified_empty_summary_has_no_metric_or_row_claim(native):
    players, teams = native
    result = game_summary.build_result(
        team="BOS",
        season="2025-26",
        df=teams.loc[teams.team_abbr.eq("BOS") & teams.pts.ge(200)].copy(),
        player_df=players.copy(),
        stat="pts",
        min_value=200,
    )
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert result.to_dict()["sections"] == {}
