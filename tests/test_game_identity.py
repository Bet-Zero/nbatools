"""Synthetic neutral-game identity and puller contract tests."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.pipeline import build_game_features, pull_games, pull_schedule
from nbatools.commands.pipeline.game_identity import (
    apply_canonical_home_away_flags,
    build_canonical_game_identity,
)

pytestmark = pytest.mark.engine


@pytest.fixture
def normalized_game_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": 1,
                "game_date": "2026-01-01",
                "matchup": "AAA vs. BBB",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "Team A",
            },
            {
                "game_id": 1,
                "game_date": "2026-01-01",
                "matchup": "BBB @ AAA",
                "team_id": 200,
                "team_abbr": "BBB",
                "team_name": "Team B",
            },
            {
                "game_id": 2,
                "game_date": "2026-01-02",
                "matchup": "CCC @ DDD",
                "team_id": 300,
                "team_abbr": "CCC",
                "team_name": "Team C",
            },
            {
                "game_id": 2,
                "game_date": "2026-01-02",
                "matchup": "DDD @ CCC",
                "team_id": 400,
                "team_abbr": "DDD",
                "team_name": "Team D",
            },
        ]
    )


def test_canonical_identity_keeps_neutral_game_without_inventing_home_team(
    normalized_game_rows: pd.DataFrame,
) -> None:
    games = build_canonical_game_identity(normalized_game_rows)
    standard = games.set_index("game_id").loc[1]
    neutral = games.set_index("game_id").loc[2]

    assert games["game_id"].tolist() == [1, 2]
    assert standard["home_team_id"] == 100
    assert standard["away_team_id"] == 200
    assert standard["home_away_designation_trusted"] == 1
    assert neutral["team_a_id"] == 300
    assert neutral["team_b_id"] == 400
    assert neutral["site_type"] == "neutral"
    assert neutral["neutral_site"] == 1
    assert neutral["home_away_designation_trusted"] == 0
    assert pd.isna(neutral["home_team_id"])
    assert pd.isna(neutral["away_team_id"])


def test_canonical_identity_requires_two_distinct_participants(
    normalized_game_rows: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="exactly two distinct team rows"):
        build_canonical_game_identity(normalized_game_rows.iloc[[0]])


def test_relative_flags_do_not_label_neutral_participants_away(
    normalized_game_rows: pd.DataFrame,
) -> None:
    flagged = apply_canonical_home_away_flags(normalized_game_rows)

    assert flagged.loc[flagged["game_id"].eq(1), "is_home"].tolist() == [1, 0]
    assert flagged.loc[flagged["game_id"].eq(1), "is_away"].tolist() == [0, 1]
    assert flagged.loc[flagged["game_id"].eq(2), "is_home"].eq(0).all()
    assert flagged.loc[flagged["game_id"].eq(2), "is_away"].eq(0).all()


def test_player_rows_share_neutral_relative_flag_contract(
    normalized_game_rows: pd.DataFrame,
) -> None:
    players = pd.concat(
        [
            normalized_game_rows.assign(player_id=lambda frame: frame["team_id"] + 1),
            normalized_game_rows.assign(player_id=lambda frame: frame["team_id"] + 2),
        ],
        ignore_index=True,
    )

    flagged = apply_canonical_home_away_flags(players)

    assert flagged.loc[flagged["game_id"].eq(2), "is_home"].eq(0).all()
    assert flagged.loc[flagged["game_id"].eq(2), "is_away"].eq(0).all()


def test_game_features_preserve_neutral_game_key_without_inventing_roles(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    games_path = tmp_path / "data/raw/games/2025-26_regular_season.csv"
    features_path = tmp_path / "data/processed/team_game_features/2025-26_regular_season.csv"
    games_path.parent.mkdir(parents=True, exist_ok=True)
    features_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "game_id": 1,
                "game_date": "2026-01-01",
                "season": "2025-26",
                "season_type": "Regular Season",
                "home_team_id": 100,
                "away_team_id": 200,
            },
            {
                "game_id": 2,
                "game_date": "2026-01-02",
                "season": "2025-26",
                "season_type": "Regular Season",
                "home_team_id": pd.NA,
                "away_team_id": pd.NA,
            },
        ]
    ).to_csv(games_path, index=False)
    rows = []
    for game_id, teams, flags in (
        (1, (100, 200), ((1, 0), (0, 1))),
        (2, (300, 400), ((0, 0), (0, 0))),
    ):
        for team_id, (is_home, is_away) in zip(teams, flags):
            rows.append(
                {
                    "game_id": game_id,
                    "team_id": team_id,
                    "is_home": is_home,
                    "is_away": is_away,
                    "days_rest": 2,
                    "is_back_to_back": 0,
                    "pts_last_5": 110,
                    "fg3m_last_5": 12,
                    "fg3_pct_last_5": 0.36,
                    "reb_last_5": 44,
                    "tov_last_5": 13,
                }
            )
    pd.DataFrame(rows).to_csv(features_path, index=False)

    build_game_features.run("2025-26", "Regular Season")

    output = pd.read_csv(
        tmp_path / "data/processed/game_features/2025-26_regular_season.csv"
    ).set_index("game_id")
    assert list(output.index) == [1, 2]
    assert output.loc[1, "home_team_id"] == 100
    assert output.loc[1, "away_team_id"] == 200
    assert pd.isna(output.loc[2, "home_team_id"])
    assert pd.isna(output.loc[2, "away_team_id"])
    assert pd.isna(output.loc[2, "home_pts_last_5"])
    assert pd.isna(output.loc[2, "away_pts_last_5"])


@pytest.mark.parametrize(
    ("module", "fetch_name", "relative_path"),
    [
        (pull_games, "fetch_games", "data/raw/games/2025-26_regular_season.csv"),
        (pull_schedule, "fetch_schedule", "data/raw/schedule/2025-26_regular_season.csv"),
    ],
)
def test_pullers_share_participant_complete_identity_contract(
    tmp_path,
    monkeypatch,
    normalized_game_rows: pd.DataFrame,
    module,
    fetch_name: str,
    relative_path: str,
) -> None:
    upstream = normalized_game_rows.rename(
        columns={
            "game_id": "GAME_ID",
            "game_date": "GAME_DATE",
            "matchup": "MATCHUP",
            "team_id": "TEAM_ID",
            "team_abbr": "TEAM_ABBREVIATION",
            "team_name": "TEAM_NAME",
        }
    )
    monkeypatch.setattr(module, fetch_name, lambda season, season_type: upstream)
    monkeypatch.chdir(tmp_path)

    module.run("2025-26", "Regular Season")

    output = pd.read_csv(tmp_path / relative_path)
    neutral = output.set_index("game_id").loc[2]
    assert output["game_id"].tolist() == [1, 2]
    assert neutral["team_a_id"] == 300
    assert neutral["team_b_id"] == 400
    assert neutral["site_type"] == "neutral"
    assert neutral["home_away_designation_trusted"] == 0
    assert pd.isna(neutral["home_team_id"])
    assert pd.isna(neutral["away_team_id"])
