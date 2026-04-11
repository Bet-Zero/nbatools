from contextlib import redirect_stdout
from io import StringIO

import pandas as pd

from nbatools.commands.season_team_leaders import (
    build_result as season_team_leaders_build_result,
)


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def test_team_leaders_computes_fg3m_per_game_from_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    for game_id in range(1, 21):
        rows.append(
            {
                "game_id": game_id,
                "team_id": 1,
                "team_name": "Alpha",
                "team_abbr": "ALP",
                "pts": 100,
                "reb": 40,
                "ast": 25,
                "fgm": 35,
                "fga": 80,
                "fg3m": 15,
                "fg3a": 40,
                "ftm": 15,
                "fta": 20,
            }
        )
    for game_id in range(21, 41):
        rows.append(
            {
                "game_id": game_id,
                "team_id": 2,
                "team_name": "Beta",
                "team_abbr": "BET",
                "pts": 100,
                "reb": 40,
                "ast": 25,
                "fgm": 35,
                "fga": 80,
                "fg3m": 10,
                "fg3a": 30,
                "ftm": 15,
                "fta": 20,
            }
        )

    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

    result = season_team_leaders_build_result(
        season="2099-00",
        stat="fg3m",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    assert df.iloc[0]["team_name"] == "Alpha"
    assert df.iloc[0]["fg3m_per_game"] == 15


def test_team_leaders_uses_latest_advanced_row(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    _write_csv(
        tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
        [
            {
                "game_id": 1,
                "team_id": 1,
                "team_name": "Alpha",
                "team_abbr": "ALP",
                "pts": 100,
                "reb": 40,
                "ast": 25,
                "fgm": 35,
                "fga": 80,
                "fg3m": 10,
                "fg3a": 30,
                "ftm": 20,
                "fta": 25,
            },
            {
                "game_id": 2,
                "team_id": 2,
                "team_name": "Beta",
                "team_abbr": "BET",
                "pts": 100,
                "reb": 40,
                "ast": 25,
                "fgm": 35,
                "fga": 80,
                "fg3m": 10,
                "fg3a": 30,
                "ftm": 20,
                "fta": 25,
            },
        ],
    )

    _write_csv(
        tmp_path / "data/raw/team_season_advanced/2099-00_regular_season.csv",
        [
            {
                "team_id": 1,
                "team_name": "Alpha",
                "team_abbr": "ALP",
                "games_played": 20,
                "off_rating": 110.0,
                "as_of_date": "2099-11-01",
            },
            {
                "team_id": 1,
                "team_name": "Alpha",
                "team_abbr": "ALP",
                "games_played": 20,
                "off_rating": 120.0,
                "as_of_date": "2099-12-01",
            },
            {
                "team_id": 2,
                "team_name": "Beta",
                "team_abbr": "BET",
                "games_played": 20,
                "off_rating": 115.0,
                "as_of_date": "2099-12-01",
            },
        ],
    )

    result = season_team_leaders_build_result(
        season="2099-00",
        stat="off_rating",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    assert df.iloc[0]["team_name"] == "Alpha"
    assert df.iloc[0]["off_rating"] == 120.0


def test_team_leaders_computes_efg_pct_from_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    for game_id in range(1, 21):
        rows.append(
            {
                "game_id": game_id,
                "team_id": 1,
                "team_name": "Alpha",
                "team_abbr": "ALP",
                "pts": 110,
                "reb": 40,
                "ast": 25,
                "fgm": 40,
                "fga": 80,
                "fg3m": 10,
                "fg3a": 30,
                "ftm": 20,
                "fta": 25,
            }
        )
    for game_id in range(21, 41):
        rows.append(
            {
                "game_id": game_id,
                "team_id": 2,
                "team_name": "Beta",
                "team_abbr": "BET",
                "pts": 110,
                "reb": 40,
                "ast": 25,
                "fgm": 35,
                "fga": 80,
                "fg3m": 5,
                "fg3a": 20,
                "ftm": 20,
                "fta": 25,
            }
        )

    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

    result = season_team_leaders_build_result(
        season="2099-00",
        stat="efg_pct",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    assert df.iloc[0]["team_name"] == "Alpha"
