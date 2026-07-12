"""Synthetic neutral-game identity and puller contract tests."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.pipeline import pull_games, pull_schedule
from nbatools.commands.pipeline.game_identity import build_canonical_game_identity

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
