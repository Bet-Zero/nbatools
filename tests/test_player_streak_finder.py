from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.player_streak_finder import (
    build_result as player_streak_finder_build_result,
)

pytestmark = pytest.mark.engine


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def test_player_streak_finder_returns_at_least_threshold_streaks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    pts_values = [15, 21, 25, 22, 20, 24, 19, 30]
    for idx, pts in enumerate(pts_values, start=1):
        rows.append(
            {
                "game_id": idx,
                "game_date": f"2099-10-{idx:02d}",
                "season": "2099-00",
                "season_type": "Regular Season",
                "player_id": 1,
                "player_name": "Streak Guy",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "opponent_team_name": "Beta",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "minutes": 35,
                "pts": pts,
                "reb": 5,
                "ast": 6,
                "stl": 1,
                "blk": 0,
                "fg3m": 2,
                "fg3a": 5,
                "tov": 2,
                "plus_minus": 8,
            }
        )

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)
    _write_csv(
        tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
        [{"game_id": row["game_id"], "team_id": row["team_id"], "wl": row["wl"]} for row in rows],
    )

    result = player_streak_finder_build_result(
        season="2099-00",
        season_type="Regular Season",
        player="Streak Guy",
        stat="pts",
        min_value=20,
        min_streak_length=5,
        longest=False,
    )
    df = result.streaks

    assert len(df) == 1
    assert int(df.iloc[0]["streak_length"]) == 5
    assert df.iloc[0]["start_date"] == "2099-10-02"
    assert df.iloc[0]["end_date"] == "2099-10-06"


def test_player_streak_finder_returns_longest_triple_double_streak(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    stat_rows = [
        (12, 11, 10),
        (14, 10, 12),
        (22, 9, 8),
        (20, 10, 10),
        (21, 12, 11),
        (18, 10, 10),
    ]
    for idx, (pts, reb, ast) in enumerate(stat_rows, start=1):
        rows.append(
            {
                "game_id": idx,
                "game_date": f"2099-11-{idx:02d}",
                "season": "2099-00",
                "season_type": "Regular Season",
                "player_id": 1,
                "player_name": "Triple Double Guy",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "opponent_team_name": "Beta",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "minutes": 35,
                "pts": pts,
                "reb": reb,
                "ast": ast,
                "stl": 1,
                "blk": 0,
                "fg3m": 1,
                "fg3a": 4,
                "tov": 3,
                "plus_minus": 6,
            }
        )

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)
    _write_csv(
        tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
        [{"game_id": row["game_id"], "team_id": row["team_id"], "wl": row["wl"]} for row in rows],
    )

    result = player_streak_finder_build_result(
        season="2099-00",
        season_type="Regular Season",
        player="Triple Double Guy",
        special_condition="triple_double",
        longest=True,
    )
    df = result.streaks

    assert len(df) == 1
    assert int(df.iloc[0]["streak_length"]) == 3
    assert df.iloc[0]["start_date"] == "2099-11-04"
    assert df.iloc[0]["end_date"] == "2099-11-06"
