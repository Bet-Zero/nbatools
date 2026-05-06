from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from nbatools.commands.data_utils import (
    load_player_game_period_stats_for_seasons,
    load_team_game_period_stats_for_seasons,
)
from nbatools.commands.pipeline.pull_game_period_stats import build_period_backfill
from nbatools.commands.pipeline.pull_game_period_stats import run as pull_game_period_stats_run
from nbatools.commands.pipeline.validate_raw import (
    validate_player_game_period_stats_df,
    validate_team_game_period_stats_df,
)
from nbatools.commands.player_game_finder import build_result as build_player_finder_result
from nbatools.commands.team_record import build_team_record_result

pytestmark = [pytest.mark.engine, pytest.mark.query]


def _player_game_row(
    *,
    game_id: int,
    game_date: str,
    team_id: int,
    team_abbr: str,
    team_name: str,
    opponent_team_id: int,
    opponent_team_abbr: str,
    opponent_team_name: str,
    player_id: int,
    player_name: str,
    wl: str,
    pts: int,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": team_id,
        "team_abbr": team_abbr,
        "team_name": team_name,
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_team_abbr,
        "opponent_team_name": opponent_team_name,
        "is_home": 1 if team_id == 1 else 0,
        "is_away": 0 if team_id == 1 else 1,
        "player_id": player_id,
        "player_name": player_name,
        "starter_flag": 1 if team_id == 1 else 0,
        "start_position": "G" if team_id == 1 else "",
        "minutes": 32,
        "pts": pts,
        "fgm": 9,
        "fga": 18,
        "fg_pct": 0.5,
        "fg3m": 3,
        "fg3a": 7,
        "fg3_pct": 0.429,
        "ftm": 2,
        "fta": 2,
        "ft_pct": 1.0,
        "oreb": 1,
        "dreb": 5,
        "reb": 6,
        "ast": 7,
        "stl": 1,
        "blk": 0,
        "tov": 2,
        "pf": 2,
        "plus_minus": 6 if wl == "W" else -4,
        "comment": "",
        "wl": wl,
    }


def _team_game_row(
    *,
    game_id: int,
    game_date: str,
    team_id: int,
    team_abbr: str,
    team_name: str,
    opponent_team_id: int,
    opponent_team_abbr: str,
    opponent_team_name: str,
    wl: str,
    pts: int,
    plus_minus: int,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": team_id,
        "team_abbr": team_abbr,
        "team_name": team_name,
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_team_abbr,
        "opponent_team_name": opponent_team_name,
        "is_home": 1 if team_id == 1 else 0,
        "is_away": 0 if team_id == 1 else 1,
        "wl": wl,
        "minutes": 240,
        "pts": pts,
        "fgm": 40,
        "fga": 85,
        "fg_pct": 0.471,
        "fg3m": 12,
        "fg3a": 31,
        "fg3_pct": 0.387,
        "ftm": 18,
        "fta": 22,
        "ft_pct": 0.818,
        "oreb": 10,
        "dreb": 32,
        "reb": 42,
        "ast": 24,
        "stl": 7,
        "blk": 4,
        "tov": 12,
        "pf": 19,
        "plus_minus": plus_minus,
    }


def _player_period_row(
    *,
    game_id: int,
    game_date: str,
    player_id: int,
    player_name: str,
    pts: int,
    period_family: str = "quarter",
    period_value: str = "4",
    source_start_period: int = 4,
    source_end_period: int = 4,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "period_family": period_family,
        "period_value": period_value,
        "source_start_period": source_start_period,
        "source_end_period": source_end_period,
        "team_id": 1,
        "team_abbr": "AAA",
        "team_name": "Alpha",
        "opponent_team_id": 2,
        "opponent_team_abbr": "BBB",
        "opponent_team_name": "Beta",
        "is_home": 1,
        "is_away": 0,
        "wl": "W",
        "player_id": player_id,
        "player_name": player_name,
        "minutes": 9,
        "pts": pts,
        "fgm": 3,
        "fga": 6,
        "fg_pct": 0.5,
        "fg3m": 1,
        "fg3a": 2,
        "fg3_pct": 0.5,
        "ftm": 1,
        "fta": 1,
        "ft_pct": 1.0,
        "oreb": 0,
        "dreb": 2,
        "reb": 2,
        "ast": 2,
        "stl": 0,
        "blk": 0,
        "tov": 1,
        "pf": 1,
        "plus_minus": 2,
        "comment": "",
        "usg_pct": 0.24,
        "ast_pct": 0.18,
        "reb_pct": 0.09,
        "tov_pct": 0.11,
        "efg_pct": 0.583,
        "ts_pct": 0.612,
    }


def _team_period_row(
    *,
    game_id: int,
    game_date: str,
    pts: int,
    wl: str,
    plus_minus: int,
    period_family: str = "half",
    period_value: str = "first",
    source_start_period: int = 1,
    source_end_period: int = 2,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "period_family": period_family,
        "period_value": period_value,
        "source_start_period": source_start_period,
        "source_end_period": source_end_period,
        "team_id": 1,
        "team_abbr": "AAA",
        "team_name": "Alpha",
        "opponent_team_id": 2,
        "opponent_team_abbr": "BBB",
        "opponent_team_name": "Beta",
        "is_home": 1,
        "is_away": 0,
        "wl": wl,
        "minutes": 120,
        "pts": pts,
        "fgm": 20,
        "fga": 44,
        "fg_pct": 0.455,
        "fg3m": 6,
        "fg3a": 16,
        "fg3_pct": 0.375,
        "ftm": 9,
        "fta": 10,
        "ft_pct": 0.9,
        "oreb": 5,
        "dreb": 16,
        "reb": 21,
        "ast": 13,
        "stl": 3,
        "blk": 2,
        "tov": 6,
        "pf": 9,
        "plus_minus": plus_minus,
        "efg_pct": 0.523,
        "ts_pct": 0.566,
    }


def _write_period_query_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_player_period_file: bool = True,
    include_team_period_file: bool = True,
) -> None:
    monkeypatch.chdir(tmp_path)

    player_rows = [
        _player_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            player_id=10,
            player_name="Period Star",
            wl="W",
            pts=30,
        ),
        _player_game_row(
            game_id=2,
            game_date="2099-10-03",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            player_id=10,
            player_name="Period Star",
            wl="W",
            pts=24,
        ),
        _player_game_row(
            game_id=3,
            game_date="2099-10-05",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            player_id=10,
            player_name="Period Star",
            wl="L",
            pts=18,
        ),
    ]

    team_rows = [
        _team_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            wl="W",
            pts=108,
            plus_minus=8,
        ),
        _team_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=2,
            team_abbr="BBB",
            team_name="Beta",
            opponent_team_id=1,
            opponent_team_abbr="AAA",
            opponent_team_name="Alpha",
            wl="L",
            pts=100,
            plus_minus=-8,
        ),
        _team_game_row(
            game_id=2,
            game_date="2099-10-03",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            wl="W",
            pts=102,
            plus_minus=2,
        ),
        _team_game_row(
            game_id=2,
            game_date="2099-10-03",
            team_id=2,
            team_abbr="BBB",
            team_name="Beta",
            opponent_team_id=1,
            opponent_team_abbr="AAA",
            opponent_team_name="Alpha",
            wl="L",
            pts=100,
            plus_minus=-2,
        ),
        _team_game_row(
            game_id=3,
            game_date="2099-10-05",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            wl="L",
            pts=96,
            plus_minus=-6,
        ),
        _team_game_row(
            game_id=3,
            game_date="2099-10-05",
            team_id=2,
            team_abbr="BBB",
            team_name="Beta",
            opponent_team_id=1,
            opponent_team_abbr="AAA",
            opponent_team_name="Alpha",
            wl="W",
            pts=102,
            plus_minus=6,
        ),
    ]

    player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
    team_path = tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv"
    player_path.parent.mkdir(parents=True, exist_ok=True)
    team_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(player_rows).to_csv(player_path, index=False)
    pd.DataFrame(team_rows).to_csv(team_path, index=False)

    if include_player_period_file:
        player_period_path = (
            tmp_path / "data/raw/player_game_period_stats/2099-00_regular_season.csv"
        )
        player_period_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                _player_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    player_id=10,
                    player_name="Period Star",
                    pts=12,
                ),
                _player_period_row(
                    game_id=2,
                    game_date="2099-10-03",
                    player_id=10,
                    player_name="Period Star",
                    pts=4,
                ),
                _player_period_row(
                    game_id=3,
                    game_date="2099-10-05",
                    player_id=10,
                    player_name="Period Star",
                    pts=9,
                ),
            ]
        ).to_csv(player_period_path, index=False)

    if include_team_period_file:
        team_period_path = tmp_path / "data/raw/team_game_period_stats/2099-00_regular_season.csv"
        team_period_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                _team_period_row(game_id=1, game_date="2099-10-01", pts=55, wl="W", plus_minus=5),
                _team_period_row(game_id=2, game_date="2099-10-03", pts=50, wl="T", plus_minus=0),
                _team_period_row(game_id=3, game_date="2099-10-05", pts=48, wl="L", plus_minus=-3),
            ]
        ).to_csv(team_period_path, index=False)


def _write_period_builder_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    games_path = tmp_path / "data/raw/games/2099-00_regular_season.csv"
    games_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"game_id": 1}]).to_csv(games_path, index=False)

    player_rows = [
        _player_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            player_id=10,
            player_name="Period Star",
            wl="W",
            pts=22,
        ),
        _player_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=2,
            team_abbr="BBB",
            team_name="Beta",
            opponent_team_id=1,
            opponent_team_abbr="AAA",
            opponent_team_name="Alpha",
            player_id=20,
            player_name="Other Star",
            wl="L",
            pts=18,
        ),
    ]
    team_rows = [
        _team_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            wl="W",
            pts=108,
            plus_minus=8,
        ),
        _team_game_row(
            game_id=1,
            game_date="2099-10-01",
            team_id=2,
            team_abbr="BBB",
            team_name="Beta",
            opponent_team_id=1,
            opponent_team_abbr="AAA",
            opponent_team_name="Alpha",
            wl="L",
            pts=100,
            plus_minus=-8,
        ),
    ]

    player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
    team_path = tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv"
    player_path.parent.mkdir(parents=True, exist_ok=True)
    team_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(player_rows).to_csv(player_path, index=False)
    pd.DataFrame(team_rows).to_csv(team_path, index=False)


def _traditional_player_rows(
    *, game_id: int, pts: int, minutes: str = "PT9M00.00S"
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 1,
                "personId": 10,
                "comment": "",
                "minutes": minutes,
                "points": pts,
                "fieldGoalsMade": 3,
                "fieldGoalsAttempted": 6,
                "fieldGoalsPercentage": 0.5,
                "threePointersMade": 1,
                "threePointersAttempted": 2,
                "threePointersPercentage": 0.5,
                "freeThrowsMade": 1,
                "freeThrowsAttempted": 1,
                "freeThrowsPercentage": 1.0,
                "reboundsOffensive": 0,
                "reboundsDefensive": 2,
                "reboundsTotal": 2,
                "assists": 2,
                "steals": 0,
                "blocks": 0,
                "turnovers": 1,
                "foulsPersonal": 1,
                "plusMinusPoints": 2,
            },
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 2,
                "personId": 20,
                "comment": "",
                "minutes": minutes,
                "points": 5,
                "fieldGoalsMade": 2,
                "fieldGoalsAttempted": 5,
                "fieldGoalsPercentage": 0.4,
                "threePointersMade": 0,
                "threePointersAttempted": 1,
                "threePointersPercentage": 0.0,
                "freeThrowsMade": 1,
                "freeThrowsAttempted": 2,
                "freeThrowsPercentage": 0.5,
                "reboundsOffensive": 1,
                "reboundsDefensive": 1,
                "reboundsTotal": 2,
                "assists": 1,
                "steals": 0,
                "blocks": 0,
                "turnovers": 1,
                "foulsPersonal": 1,
                "plusMinusPoints": -2,
            },
        ]
    )


def _traditional_team_rows(*, game_id: int, pts: int, minutes: str = "PT60M00.00S") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 1,
                "minutes": minutes,
                "points": pts,
                "fieldGoalsMade": 20,
                "fieldGoalsAttempted": 44,
                "fieldGoalsPercentage": 0.455,
                "threePointersMade": 6,
                "threePointersAttempted": 16,
                "threePointersPercentage": 0.375,
                "freeThrowsMade": 9,
                "freeThrowsAttempted": 10,
                "freeThrowsPercentage": 0.9,
                "reboundsOffensive": 5,
                "reboundsDefensive": 16,
                "reboundsTotal": 21,
                "assists": 13,
                "steals": 3,
                "blocks": 2,
                "turnovers": 6,
                "foulsPersonal": 9,
                "plusMinusPoints": 5,
            },
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 2,
                "minutes": minutes,
                "points": 50,
                "fieldGoalsMade": 18,
                "fieldGoalsAttempted": 42,
                "fieldGoalsPercentage": 0.429,
                "threePointersMade": 5,
                "threePointersAttempted": 15,
                "threePointersPercentage": 0.333,
                "freeThrowsMade": 9,
                "freeThrowsAttempted": 11,
                "freeThrowsPercentage": 0.818,
                "reboundsOffensive": 4,
                "reboundsDefensive": 15,
                "reboundsTotal": 19,
                "assists": 10,
                "steals": 2,
                "blocks": 1,
                "turnovers": 7,
                "foulsPersonal": 10,
                "plusMinusPoints": -5,
            },
        ]
    )


def _advanced_player_rows(*, game_id: int, usg_pct: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 1,
                "personId": 10,
                "usagePercentage": usg_pct,
                "assistPercentage": 0.18,
                "reboundPercentage": 0.09,
                "turnoverRatio": 0.11,
            },
            {
                "gameId": str(game_id).zfill(10),
                "teamId": 2,
                "personId": 20,
                "usagePercentage": 0.22,
                "assistPercentage": 0.12,
                "reboundPercentage": 0.08,
                "turnoverRatio": 0.10,
            },
        ]
    )


def test_player_finder_period_filter_uses_period_dataset(tmp_path, monkeypatch):
    _write_period_query_fixture(tmp_path, monkeypatch)

    result = build_player_finder_result(
        season="2099-00",
        season_type="Regular Season",
        player="Period Star",
        quarter="4",
    )

    assert list(result.games["pts"]) == [9, 4, 12]
    assert result.notes == []


def test_player_finder_period_filter_falls_back_when_dataset_missing(tmp_path, monkeypatch):
    _write_period_query_fixture(
        tmp_path,
        monkeypatch,
        include_player_period_file=False,
    )

    result = build_player_finder_result(
        season="2099-00",
        season_type="Regular Season",
        player="Period Star",
        quarter="4",
    )

    assert list(result.games["pts"]) == [18, 24, 30]
    assert any("quarter" in note and "unfiltered" in note for note in result.notes)


def test_team_record_period_filter_uses_period_dataset_and_excludes_ties(tmp_path, monkeypatch):
    _write_period_query_fixture(tmp_path, monkeypatch)

    result = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        half="first",
    )

    row = result.summary.iloc[0]
    assert int(row["games"]) == 2
    assert int(row["wins"]) == 1
    assert int(row["losses"]) == 1
    assert result.notes == []
    assert any("tied period windows excluded" in caveat for caveat in result.caveats)


def test_team_record_period_filter_falls_back_when_dataset_missing(tmp_path, monkeypatch):
    _write_period_query_fixture(
        tmp_path,
        monkeypatch,
        include_team_period_file=False,
    )

    result = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        half="first",
    )

    row = result.summary.iloc[0]
    assert int(row["games"]) == 3
    assert any("half" in note and "unfiltered" in note for note in result.notes)


def test_load_player_period_stats_requires_all_requested_seasons(tmp_path, monkeypatch):
    _write_period_query_fixture(tmp_path, monkeypatch)

    with pytest.raises(FileNotFoundError):
        load_player_game_period_stats_for_seasons(["2099-00", "2100-01"], "Regular Season")


def test_load_team_period_stats_requires_all_requested_seasons(tmp_path, monkeypatch):
    _write_period_query_fixture(tmp_path, monkeypatch)

    with pytest.raises(FileNotFoundError):
        load_team_game_period_stats_for_seasons(["2099-00", "2100-01"], "Regular Season")


def test_validate_player_period_stats_rejects_bad_window_descriptor():
    df = pd.DataFrame(
        [
            {
                **_player_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    player_id=10,
                    player_name="Period Star",
                    pts=12,
                ),
                "period_value": "5",
            }
        ]
    )

    with pytest.raises(ValueError, match="unsupported period_family/period_value"):
        validate_player_game_period_stats_df(df)


def test_validate_team_period_stats_rejects_wl_mismatch():
    df = pd.DataFrame(
        [
            {
                **_team_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    pts=55,
                    wl="L",
                    plus_minus=5,
                )
            }
        ]
    )

    with pytest.raises(ValueError, match="wl mismatch"):
        validate_team_game_period_stats_df(df)


def test_build_period_backfill_merges_player_advanced_fields(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    def fake_traditional(game_id, *, start_period, end_period):
        del start_period, end_period
        return _traditional_player_rows(game_id=game_id, pts=12), _traditional_team_rows(
            game_id=game_id,
            pts=55,
        )

    def fake_advanced(game_id, *, start_period, end_period):
        del start_period, end_period
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        player_df, team_df = build_period_backfill("2099-00", "Regular Season")

    assert {"quarter", "half", "overtime"} == set(player_df["period_family"])
    assert {"quarter", "half", "overtime"} == set(team_df["period_family"])
    assert player_df.loc[player_df["player_id"] == 10, "usg_pct"].eq(0.25).all()
    assert player_df["ts_pct"].notna().all()


def test_build_period_backfill_derives_player_wl_from_team_context_when_missing(
    tmp_path, monkeypatch
):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
    player_context = pd.read_csv(player_path).drop(columns=["wl"])
    player_context.to_csv(player_path, index=False)

    def fake_traditional(game_id, *, start_period, end_period):
        del start_period, end_period
        return _traditional_player_rows(game_id=game_id, pts=12), _traditional_team_rows(
            game_id=game_id,
            pts=55,
        )

    def fake_advanced(game_id, *, start_period, end_period):
        del start_period, end_period
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        player_df, _team_df = build_period_backfill("2099-00", "Regular Season")

    assert player_df.loc[player_df["player_id"] == 10, "wl"].eq("W").all()
    assert player_df.loc[player_df["player_id"] == 20, "wl"].eq("L").all()


def test_build_period_backfill_drops_unmatched_dnp_rows(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    def fake_traditional(game_id, *, start_period, end_period):
        del start_period, end_period
        dnp_row = pd.DataFrame(
            [
                {
                    "gameId": str(game_id).zfill(10),
                    "teamId": 1,
                    "personId": 999,
                    "comment": "DNP - Coach's Decision",
                    "minutes": "",
                    "points": 0,
                    "fieldGoalsMade": 0,
                    "fieldGoalsAttempted": 0,
                    "fieldGoalsPercentage": 0.0,
                    "threePointersMade": 0,
                    "threePointersAttempted": 0,
                    "threePointersPercentage": 0.0,
                    "freeThrowsMade": 0,
                    "freeThrowsAttempted": 0,
                    "freeThrowsPercentage": 0.0,
                    "reboundsOffensive": 0,
                    "reboundsDefensive": 0,
                    "reboundsTotal": 0,
                    "assists": 0,
                    "steals": 0,
                    "blocks": 0,
                    "turnovers": 0,
                    "foulsPersonal": 0,
                    "plusMinusPoints": 0,
                }
            ]
        )
        player_rows = pd.concat(
            [_traditional_player_rows(game_id=game_id, pts=12), dnp_row],
            ignore_index=True,
        )
        return player_rows, _traditional_team_rows(game_id=game_id, pts=55)

    def fake_advanced(game_id, *, start_period, end_period):
        del start_period, end_period
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        player_df, _team_df = build_period_backfill("2099-00", "Regular Season")

    assert 999 not in set(player_df["player_id"])


def test_build_period_backfill_rejects_unmatched_playing_rows(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    def fake_traditional(game_id, *, start_period, end_period):
        del start_period, end_period
        missing_player_row = pd.DataFrame(
            [
                {
                    "gameId": str(game_id).zfill(10),
                    "teamId": 1,
                    "personId": 999,
                    "comment": "",
                    "minutes": "PT1M00.00S",
                    "points": 2,
                    "fieldGoalsMade": 1,
                    "fieldGoalsAttempted": 1,
                    "fieldGoalsPercentage": 1.0,
                    "threePointersMade": 0,
                    "threePointersAttempted": 0,
                    "threePointersPercentage": 0.0,
                    "freeThrowsMade": 0,
                    "freeThrowsAttempted": 0,
                    "freeThrowsPercentage": 0.0,
                    "reboundsOffensive": 0,
                    "reboundsDefensive": 1,
                    "reboundsTotal": 1,
                    "assists": 0,
                    "steals": 0,
                    "blocks": 0,
                    "turnovers": 0,
                    "foulsPersonal": 0,
                    "plusMinusPoints": 1,
                }
            ]
        )
        player_rows = pd.concat(
            [_traditional_player_rows(game_id=game_id, pts=12), missing_player_row],
            ignore_index=True,
        )
        return player_rows, _traditional_team_rows(game_id=game_id, pts=55)

    def fake_advanced(game_id, *, start_period, end_period):
        del start_period, end_period
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        with pytest.raises(ValueError, match="joined back to player_game_stats context"):
            build_period_backfill("2099-00", "Regular Season")


def test_build_period_backfill_skips_inactive_overtime_window(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    def fake_traditional(game_id, *, start_period, end_period):
        if start_period == 5:
            return _traditional_player_rows(
                game_id=game_id,
                pts=0,
                minutes="PT0M00.00S",
            ), pd.DataFrame(
                [
                    {
                        "gameId": str(game_id).zfill(10),
                        "teamId": 1,
                        "minutes": "PT0M00.00S",
                        "points": 0,
                        "fieldGoalsMade": 0,
                        "fieldGoalsAttempted": 0,
                        "fieldGoalsPercentage": 0.0,
                        "threePointersMade": 0,
                        "threePointersAttempted": 0,
                        "threePointersPercentage": 0.0,
                        "freeThrowsMade": 0,
                        "freeThrowsAttempted": 0,
                        "freeThrowsPercentage": 0.0,
                        "reboundsOffensive": 0,
                        "reboundsDefensive": 0,
                        "reboundsTotal": 0,
                        "assists": 0,
                        "steals": 0,
                        "blocks": 0,
                        "turnovers": 0,
                        "foulsPersonal": 0,
                        "plusMinusPoints": 0,
                    },
                    {
                        "gameId": str(game_id).zfill(10),
                        "teamId": 2,
                        "minutes": "PT0M00.00S",
                        "points": 0,
                        "fieldGoalsMade": 0,
                        "fieldGoalsAttempted": 0,
                        "fieldGoalsPercentage": 0.0,
                        "threePointersMade": 0,
                        "threePointersAttempted": 0,
                        "threePointersPercentage": 0.0,
                        "freeThrowsMade": 0,
                        "freeThrowsAttempted": 0,
                        "freeThrowsPercentage": 0.0,
                        "reboundsOffensive": 0,
                        "reboundsDefensive": 0,
                        "reboundsTotal": 0,
                        "assists": 0,
                        "steals": 0,
                        "blocks": 0,
                        "turnovers": 0,
                        "foulsPersonal": 0,
                        "plusMinusPoints": 0,
                    },
                ]
            )
        return _traditional_player_rows(game_id=game_id, pts=12), _traditional_team_rows(
            game_id=game_id,
            pts=55,
        )

    def fake_advanced(game_id, *, start_period, end_period):
        del start_period, end_period
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        player_df, team_df = build_period_backfill("2099-00", "Regular Season")

    assert "overtime" not in set(player_df["period_family"])
    assert "overtime" not in set(team_df["period_family"])


def test_build_period_backfill_retries_deferred_windows_within_same_run(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "nbatools.commands.pipeline.pull_game_period_stats.WINDOW_PASS_SLEEP_SECONDS",
        0.0,
    )

    advanced_call_counts: dict[tuple[int, int, int], int] = {}

    def fake_traditional(game_id, *, start_period, end_period):
        return _traditional_player_rows(game_id=game_id, pts=12), _traditional_team_rows(
            game_id=game_id,
            pts=55,
        )

    def fake_advanced(game_id, *, start_period, end_period):
        key = (int(game_id), start_period, end_period)
        advanced_call_counts[key] = advanced_call_counts.get(key, 0) + 1
        if key == (1, 3, 4) and advanced_call_counts[key] == 1:
            raise RuntimeError("transient advanced timeout")
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        player_df, team_df = build_period_backfill("2099-00", "Regular Season")

    assert advanced_call_counts[(1, 3, 4)] == 2
    assert {"quarter", "half", "overtime"} == set(player_df["period_family"])
    assert {"quarter", "half", "overtime"} == set(team_df["period_family"])


def test_pull_game_period_stats_run_resumes_from_partial_cache(tmp_path, monkeypatch):
    _write_period_builder_fixture(tmp_path, monkeypatch)

    player_partial_path = (
        tmp_path / "data/raw/player_game_period_stats/2099-00_regular_season.partial.csv"
    )
    team_partial_path = (
        tmp_path / "data/raw/team_game_period_stats/2099-00_regular_season.partial.csv"
    )
    progress_path = (
        tmp_path / "data/raw/player_game_period_stats/2099-00_regular_season.windows.partial.csv"
    )
    player_partial_path.parent.mkdir(parents=True, exist_ok=True)
    team_partial_path.parent.mkdir(parents=True, exist_ok=True)

    cached_player = pd.DataFrame(
        [
            {
                **_player_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    player_id=10,
                    player_name="Period Star",
                    pts=12,
                    period_family="quarter",
                    period_value="1",
                    source_start_period=1,
                    source_end_period=1,
                )
            },
            {
                **_player_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    player_id=20,
                    player_name="Bench Wing",
                    pts=8,
                    period_family="quarter",
                    period_value="1",
                    source_start_period=1,
                    source_end_period=1,
                ),
                "team_id": 2,
                "team_abbr": "BBB",
                "team_name": "Beta",
                "opponent_team_id": 1,
                "opponent_team_abbr": "AAA",
                "opponent_team_name": "Alpha",
                "is_home": 0,
                "is_away": 1,
                "wl": "L",
                "plus_minus": -2,
            },
        ]
    )
    cached_team = pd.DataFrame(
        [
            _team_period_row(
                game_id=1,
                game_date="2099-10-01",
                pts=55,
                wl="W",
                plus_minus=5,
                period_family="quarter",
                period_value="1",
                source_start_period=1,
                source_end_period=1,
            ),
            {
                **_team_period_row(
                    game_id=1,
                    game_date="2099-10-01",
                    pts=49,
                    wl="L",
                    plus_minus=-5,
                    period_family="quarter",
                    period_value="1",
                    source_start_period=1,
                    source_end_period=1,
                ),
                "team_id": 2,
                "team_abbr": "BBB",
                "team_name": "Beta",
                "opponent_team_id": 1,
                "opponent_team_abbr": "AAA",
                "opponent_team_name": "Alpha",
                "is_home": 0,
                "is_away": 1,
            },
        ]
    )
    cached_player.to_csv(player_partial_path, index=False)
    cached_team.to_csv(team_partial_path, index=False)
    pd.DataFrame(
        [
            {
                "game_id": 1,
                "period_family": "quarter",
                "period_value": "1",
                "has_activity": True,
            }
        ]
    ).to_csv(progress_path, index=False)

    seen_traditional_calls: list[tuple[int, int, int]] = []
    seen_advanced_calls: list[tuple[int, int, int]] = []

    def fake_traditional(game_id, *, start_period, end_period):
        seen_traditional_calls.append((int(game_id), start_period, end_period))
        return _traditional_player_rows(game_id=game_id, pts=12), _traditional_team_rows(
            game_id=game_id,
            pts=55,
        )

    def fake_advanced(game_id, *, start_period, end_period):
        seen_advanced_calls.append((int(game_id), start_period, end_period))
        return _advanced_player_rows(game_id=game_id, usg_pct=0.25)

    with (
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_traditional_period_rows_for_game",
            side_effect=fake_traditional,
        ),
        patch(
            "nbatools.commands.pipeline.pull_game_period_stats.fetch_advanced_period_rows_for_game",
            side_effect=fake_advanced,
        ),
    ):
        pull_game_period_stats_run("2099-00", "Regular Season")

    assert (1, 1, 1) not in seen_traditional_calls
    assert (1, 1, 1) not in seen_advanced_calls
    assert len(seen_traditional_calls) == len(seen_advanced_calls)

    player_out = pd.read_csv(
        tmp_path / "data/raw/player_game_period_stats/2099-00_regular_season.csv"
    )
    team_out = pd.read_csv(tmp_path / "data/raw/team_game_period_stats/2099-00_regular_season.csv")

    assert set(player_out["period_family"]) == {"quarter", "half", "overtime"}
    assert set(team_out["period_family"]) == {"quarter", "half", "overtime"}
    assert not player_partial_path.exists()
    assert not team_partial_path.exists()
    assert not progress_path.exists()
