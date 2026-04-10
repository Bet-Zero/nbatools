from contextlib import redirect_stdout
from io import StringIO

import pandas as pd

from nbatools.commands.team_streak_finder import run as team_streak_finder_run


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def test_team_streak_finder_returns_at_least_threshold_streaks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    pts_values = [110, 121, 124, 122, 120, 126, 118, 130]
    for idx, pts in enumerate(pts_values, start=1):
        rows.append(
            {
                "game_id": idx,
                "game_date": f"2099-10-{idx:02d}",
                "season": "2099-00",
                "season_type": "Regular Season",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "opponent_team_name": "Beta",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "pts": pts,
                "reb": 45,
                "ast": 28,
                "stl": 8,
                "blk": 5,
                "fg3m": 14,
                "fg3a": 36,
                "tov": 12,
                "plus_minus": 9,
            }
        )

    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

    out = _capture_output(
        team_streak_finder_run,
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        stat="pts",
        min_value=120,
        min_streak_length=5,
        longest=False,
    )
    df = pd.read_csv(StringIO(out))

    assert len(df) == 1
    assert int(df.iloc[0]["streak_length"]) == 5
    assert df.iloc[0]["start_date"] == "2099-10-02"
    assert df.iloc[0]["end_date"] == "2099-10-06"


def test_team_streak_finder_returns_longest_winning_streak(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    wl_values = ["W", "W", "L", "W", "W", "W", "W", "L"]
    for idx, wl in enumerate(wl_values, start=1):
        rows.append(
            {
                "game_id": idx,
                "game_date": f"2099-11-{idx:02d}",
                "season": "2099-00",
                "season_type": "Regular Season",
                "team_id": 100,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "opponent_team_name": "Beta",
                "is_home": 1,
                "is_away": 0,
                "wl": wl,
                "pts": 118,
                "reb": 44,
                "ast": 27,
                "stl": 7,
                "blk": 4,
                "fg3m": 13,
                "fg3a": 34,
                "tov": 11,
                "plus_minus": 7,
            }
        )

    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

    out = _capture_output(
        team_streak_finder_run,
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        special_condition="wins",
        longest=True,
    )
    df = pd.read_csv(StringIO(out))

    assert len(df) == 1
    assert int(df.iloc[0]["streak_length"]) == 4
    assert df.iloc[0]["start_date"] == "2099-11-04"
    assert df.iloc[0]["end_date"] == "2099-11-07"
