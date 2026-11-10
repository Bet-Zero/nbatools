"""Retained authenticated 37-column schema and controlled corrupt-context checks."""

from pathlib import Path

import pandas as pd
import pytest

from tests.core1_k08_served_default_cases import _sample, player_team_context

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/tatum-20260201/acquired_data/canonical_selected"
)


@pytest.fixture
def frames():
    return [
        pd.read_csv(SOURCE / kind / "2025-26_regular_season.csv")
        for kind in ("player_game_stats", "team_game_stats", "games")
    ]


def test_actual_retained_raw_player_schema_gets_outcome_only_from_exact_team_fact(frames):
    players, teams, catalog = frames
    assert len(players.columns) == 37 and "wl" not in players
    original = players.copy(deep=True)
    joined = player_team_context(players, teams, catalog)
    pd.testing.assert_frame_equal(players, original)
    pd.testing.assert_frame_equal(joined[players.columns], players)
    assert joined.wl.value_counts().to_dict() == {"W": 12, "L": 12}
    for row in joined.itertuples():
        (team,) = teams.loc[
            teams.game_id.eq(row.game_id) & teams.team_id.eq(row.team_id)
        ].itertuples()
        assert row.wl == team.wl and row.game_date == team.game_date
    _sample(joined, player=True)  # No missing field is suppressed or filled with zero.


def test_untrusted_neutral_participants_keep_zero_zero_venue_without_losing_outcome(frames):
    players, teams, catalog = frames
    players[["is_home", "is_away"]] = 0
    teams[["is_home", "is_away"]] = 0
    catalog["home_away_designation_trusted"] = 0
    catalog["neutral_site"] = 1
    catalog[["home_team_id", "away_team_id"]] = float("nan")
    joined = player_team_context(players, teams, catalog)
    pd.testing.assert_frame_equal(joined[players.columns], players)
    assert joined.wl.value_counts().to_dict() == {"W": 12, "L": 12}
    assert joined.is_home.eq(0).all() and joined.is_away.eq(0).all()


@pytest.mark.parametrize(
    "damage",
    [
        "missing_team",
        "duplicate_team",
        "team_date",
        "opponent",
        "catalog_date",
        "nonfinal",
        "duplicate_player",
        "cross_side_player",
        "missing_stat",
    ],
)
def test_raw_player_context_cannot_hide_incomplete_or_conflicting_inputs(frames, damage):
    players, teams, catalog = frames
    if damage == "missing_team":
        teams = teams.iloc[1:].copy()
    elif damage == "duplicate_team":
        teams = pd.concat([teams, teams.iloc[:1]], ignore_index=True)
    elif damage == "team_date":
        teams.loc[0, "game_date"] = "2026-02-02"
    elif damage == "opponent":
        players.loc[0, "opponent_team_id"] = 999
    elif damage == "catalog_date":
        catalog.loc[0, "game_date"] = "2026-02-02"
    elif damage == "nonfinal":
        catalog.loc[0, "is_final"] = 0
    elif damage == "duplicate_player":
        players = pd.concat([players, players.iloc[:1]], ignore_index=True)
    elif damage == "cross_side_player":
        duplicate = players.iloc[:1].copy()
        other = teams.loc[teams.team_id.ne(duplicate.iloc[0].team_id)].iloc[0]
        for field in (
            "team_id",
            "team_abbr",
            "team_name",
            "opponent_team_id",
            "opponent_team_abbr",
            "opponent_team_name",
            "is_home",
            "is_away",
        ):
            duplicate[field] = other[field]
        players = pd.concat([players, duplicate], ignore_index=True)
    else:
        players = players.drop(columns="fg3a")
    with pytest.raises(AssertionError):
        player_team_context(players, teams, catalog)
