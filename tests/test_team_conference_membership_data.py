from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.data_utils import (
    get_team_conference_map,
    get_teams_by_conference,
    load_team_conference_membership,
)

pytestmark = [pytest.mark.engine, pytest.mark.needs_data]

MEMBERSHIP_PATH = Path("data/raw/teams/team_conference_membership.csv")
SUPPORTED_SEASONS = ("2024-25", "2025-26")
REQUIRED_COLUMNS = {
    "season",
    "team_abbr",
    "team_id",
    "conference",
    "division",
    "source",
    "coverage_trusted",
}
EXPECTED_DIVISIONS = {"Atlantic", "Central", "Southeast", "Northwest", "Pacific", "Southwest"}


def _load_raw_membership() -> pd.DataFrame:
    return pd.read_csv(MEMBERSHIP_PATH)


def _trusted_mask(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip().str.lower()
    return values.isin({"1", "true", "yes"})


def _trusted_membership(df: pd.DataFrame, season: str) -> pd.DataFrame:
    return df.loc[df["season"].eq(season) & _trusted_mask(df["coverage_trusted"])].copy()


def test_team_conference_membership_file_contract():
    assert MEMBERSHIP_PATH.exists()
    df = _load_raw_membership()

    assert REQUIRED_COLUMNS.issubset(df.columns)
    assert not df.duplicated(subset=["season", "team_abbr"]).any()
    assert set(df["conference"]) <= {"East", "West"}
    assert df["conference"].notna().all()
    assert df["division"].fillna("").astype(str).str.strip().ne("").all()
    assert df["source"].fillna("").astype(str).str.strip().str.contains("manual").all()

    trust_values = set(df["coverage_trusted"].fillna("").astype(str).str.lower())
    assert trust_values <= {"true", "false", "1", "0"}


@pytest.mark.parametrize("season", SUPPORTED_SEASONS)
def test_trusted_season_has_complete_balanced_membership(season: str):
    df = _trusted_membership(_load_raw_membership(), season)

    assert len(df) == 30
    assert df["team_abbr"].nunique() == 30
    assert df["team_id"].notna().all()
    assert df["conference"].notna().all()
    assert df["conference"].value_counts().to_dict() == {"East": 15, "West": 15}
    assert set(df["conference"]) == {"East", "West"}

    division_counts = df["division"].value_counts().to_dict()
    assert set(df["division"]) == EXPECTED_DIVISIONS
    assert division_counts == {division: 5 for division in EXPECTED_DIVISIONS}


@pytest.mark.parametrize("season", SUPPORTED_SEASONS)
def test_membership_abbreviations_match_team_game_stats(season: str):
    membership = _trusted_membership(_load_raw_membership(), season)
    stats = pd.read_csv(
        Path(f"data/raw/team_game_stats/{season}_regular_season.csv"),
        usecols=["team_id", "team_abbr", "opponent_team_id", "opponent_team_abbr"],
    )

    membership_abbrs = set(membership["team_abbr"])
    team_abbrs = set(stats["team_abbr"])
    opponent_abbrs = set(stats["opponent_team_abbr"])
    assert membership_abbrs == team_abbrs
    assert membership_abbrs == opponent_abbrs

    team_identity_counts = stats.groupby("team_abbr")["team_id"].nunique()
    opponent_identity_counts = stats.groupby("opponent_team_abbr")["opponent_team_id"].nunique()
    assert team_identity_counts.eq(1).all()
    assert opponent_identity_counts.eq(1).all()

    stats_team_ids = (
        stats[["team_abbr", "team_id"]]
        .drop_duplicates()
        .set_index("team_abbr")["team_id"]
        .astype(int)
        .to_dict()
    )
    membership_team_ids = membership.set_index("team_abbr")["team_id"].astype(int).to_dict()
    assert membership_team_ids == stats_team_ids


def test_load_team_conference_membership_normalizes_contract_values():
    df = load_team_conference_membership()

    assert set(SUPPORTED_SEASONS) <= set(df["season"])
    assert set(df["coverage_trusted"]) == {1}
    assert set(df["conference"]) == {"East", "West"}


@pytest.mark.parametrize("season", SUPPORTED_SEASONS)
def test_get_team_conference_map_returns_trusted_maps(season: str):
    mapping = get_team_conference_map(season)

    assert len(mapping) == 30
    assert mapping["BOS"] == "East"
    assert mapping["LAL"] == "West"


@pytest.mark.parametrize("season", SUPPORTED_SEASONS)
@pytest.mark.parametrize("conference", ("East", "West"))
def test_get_teams_by_conference_returns_balanced_team_lists(season: str, conference: str):
    teams = get_teams_by_conference(season, conference)

    assert len(teams) == 15
    assert teams == sorted(teams)


def test_unknown_season_has_no_trusted_conference_coverage():
    assert get_team_conference_map("2099-00") == {}
    assert get_teams_by_conference("2099-00", "East") == []


def test_require_trusted_coverage_rejects_unknown_season():
    with pytest.raises(ValueError, match="Missing trusted team-conference coverage"):
        get_teams_by_conference("2099-00", "East", require_trusted_coverage=True)


def test_get_teams_by_conference_rejects_unknown_conference():
    with pytest.raises(ValueError, match="Unsupported conference"):
        get_teams_by_conference("2025-26", "Central")
