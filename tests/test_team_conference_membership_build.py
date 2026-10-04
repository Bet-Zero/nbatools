from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import build_team_conference_membership as membership
from nbatools.commands.pipeline.pull_standings_snapshots import normalize

pytestmark = pytest.mark.engine


def _write_season(data: Path, season: str, teams: list[tuple[int, str, str, str]]) -> None:
    standings = data / "raw" / "standings_snapshots" / f"{season}_regular_season.csv"
    stats = data / "raw" / "team_game_stats" / f"{season}_regular_season.csv"
    standings.parent.mkdir(parents=True, exist_ok=True)
    stats.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "snapshot_date": "2005-04-20",
                "team_id": team_id,
                "conference": conference,
                "division": division,
            }
            for team_id, _, conference, division in teams
        ]
    ).to_csv(standings, index=False)
    pd.DataFrame(
        [
            {"game_date": "2005-04-20", "team_id": team_id, "team_abbr": abbr}
            for team_id, abbr, _, _ in teams
        ]
    ).to_csv(stats, index=False)


def test_membership_comes_from_standings_with_the_seasons_own_abbreviations(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    _write_season(
        data,
        "2003-04",
        [
            (1610612760, "SEA", "West", "Pacific"),
            (1610612763, "MEM", "West", "Midwest"),
            (1610612740, "NOH", "East", "Central"),
        ],
    )
    existing = data / "raw" / "teams" / "team_conference_membership.csv"
    existing.parent.mkdir(parents=True)
    existing.write_text(
        "season,team_abbr,team_id,conference,division,source,coverage_trusted\n"
        "2024-25,BOS,1610612738,East,Atlantic,manual_current_nba_alignment_2026-05-17,true\n"
    )

    membership.run("2003-04", "Regular Season", data_dir=data)

    rows = pd.read_csv(existing)
    assert list(rows["season"]) == ["2003-04", "2003-04", "2003-04", "2024-25"]
    seattle = rows[rows["team_abbr"] == "SEA"].iloc[0]
    assert (seattle["conference"], seattle["division"]) == ("West", "Pacific")
    assert rows[rows["team_abbr"] == "MEM"].iloc[0]["division"] == "Midwest"
    assert set(rows[rows["season"] == "2003-04"]["source"]) == {membership.SOURCE}


def test_rerunning_a_season_replaces_only_that_seasons_rows(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _write_season(data, "2025-26", [(1610612738, "BOS", "East", "Atlantic")])
    _write_season(data, "2026-27", [(1610612738, "BOS", "East", "Atlantic")])
    membership.run("2025-26", "Regular Season", data_dir=data)
    membership.run("2026-27", "Regular Season", data_dir=data)
    membership.run("2026-27", "Regular Season", data_dir=data)

    rows = pd.read_csv(data / "raw" / "teams" / "team_conference_membership.csv")
    assert list(rows["season"]) == ["2025-26", "2026-27"]


def test_standings_without_conference_columns_leave_membership_alone(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _write_season(data, "1999-00", [(1610612738, "BOS", "East", "Atlantic")])
    standings = data / "raw" / "standings_snapshots" / "1999-00_regular_season.csv"
    pd.read_csv(standings).drop(columns=["conference", "division"]).to_csv(standings, index=False)

    membership.run("1999-00", "Regular Season", data_dir=data)

    assert not (data / "raw" / "teams" / "team_conference_membership.csv").exists()


def test_a_division_in_the_wrong_conference_is_refused(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _write_season(data, "2010-11", [(1610612738, "BOS", "West", "Atlantic")])

    with pytest.raises(ValueError, match="not a West division"):
        membership.run("2010-11", "Regular Season", data_dir=data)


def test_standings_pull_keeps_conference_and_division() -> None:
    raw = pd.DataFrame(
        [
            {
                "TeamID": 1610612738,
                "TeamAbbreviation": "BOS",
                "WINS": 61,
                "LOSSES": 21,
                "WinPCT": 0.744,
                "PlayoffRank": 2,
                "DivisionRank": 1,
                "ConferenceGamesBack": 3.0,
                "strCurrentStreak": "W 2",
                "Conference": "East",
                "Division": "Atlantic",
            }
        ]
    )

    out = normalize(raw, season="2024-25", season_type="Regular Season", snapshot_date="2025-04-13")

    assert out.loc[0, "conference"] == "East"
    assert out.loc[0, "division"] == "Atlantic"
