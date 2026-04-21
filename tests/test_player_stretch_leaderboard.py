from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.player_stretch_leaderboard import build_result

pytestmark = pytest.mark.engine


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _player_row(
    *,
    game_id: int,
    game_date: str,
    player_id: int,
    player_name: str,
    team_id: int,
    team_abbr: str,
    pts: int,
    fgm: int,
    fga: int,
    fg3m: int,
    fg3a: int,
    ftm: int,
    fta: int,
    oreb: int = 1,
    dreb: int = 4,
    reb: int = 5,
    ast: int = 5,
    stl: int = 1,
    blk: int = 0,
    tov: int = 2,
    pf: int = 2,
    plus_minus: int = 5,
    opponent_team_id: int = 99,
    opponent_team_abbr: str = "ZZZ",
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": team_id,
        "team_abbr": team_abbr,
        "team_name": team_abbr,
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_team_abbr,
        "opponent_team_name": opponent_team_abbr,
        "is_home": 1,
        "is_away": 0,
        "player_id": player_id,
        "player_name": player_name,
        "starter_flag": 1,
        "start_position": "G",
        "minutes": 35,
        "pts": pts,
        "fgm": fgm,
        "fga": fga,
        "fg_pct": round(fgm / fga, 3),
        "fg3m": fg3m,
        "fg3a": fg3a,
        "fg3_pct": round(fg3m / fg3a, 3) if fg3a else 0.0,
        "ftm": ftm,
        "fta": fta,
        "ft_pct": round(ftm / fta, 3) if fta else 0.0,
        "oreb": oreb,
        "dreb": dreb,
        "reb": reb,
        "ast": ast,
        "stl": stl,
        "blk": blk,
        "tov": tov,
        "pf": pf,
        "plus_minus": plus_minus,
        "comment": "",
    }


def test_build_result_ranks_highest_scoring_stretches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    player_rows = [
        _player_row(
            game_id=1,
            game_date="2099-10-01",
            player_id=1,
            player_name="Alpha Scorer",
            team_id=10,
            team_abbr="AAA",
            pts=20,
            fgm=7,
            fga=15,
            fg3m=2,
            fg3a=5,
            ftm=4,
            fta=5,
        ),
        _player_row(
            game_id=2,
            game_date="2099-10-03",
            player_id=1,
            player_name="Alpha Scorer",
            team_id=10,
            team_abbr="AAA",
            pts=24,
            fgm=8,
            fga=16,
            fg3m=3,
            fg3a=7,
            ftm=5,
            fta=6,
        ),
        _player_row(
            game_id=3,
            game_date="2099-10-05",
            player_id=1,
            player_name="Alpha Scorer",
            team_id=10,
            team_abbr="AAA",
            pts=26,
            fgm=9,
            fga=17,
            fg3m=4,
            fg3a=8,
            ftm=4,
            fta=5,
        ),
        _player_row(
            game_id=4,
            game_date="2099-10-07",
            player_id=2,
            player_name="Beta Bucket",
            team_id=20,
            team_abbr="BBB",
            pts=14,
            fgm=5,
            fga=14,
            fg3m=1,
            fg3a=4,
            ftm=3,
            fta=4,
        ),
        _player_row(
            game_id=5,
            game_date="2099-10-09",
            player_id=2,
            player_name="Beta Bucket",
            team_id=20,
            team_abbr="BBB",
            pts=16,
            fgm=6,
            fga=15,
            fg3m=1,
            fg3a=4,
            ftm=3,
            fta=4,
        ),
        _player_row(
            game_id=6,
            game_date="2099-10-11",
            player_id=2,
            player_name="Beta Bucket",
            team_id=20,
            team_abbr="BBB",
            pts=18,
            fgm=6,
            fga=16,
            fg3m=2,
            fg3a=5,
            ftm=4,
            fta=5,
        ),
    ]
    team_rows = [
        {"game_id": 1, "team_id": 10, "wl": "W"},
        {"game_id": 2, "team_id": 10, "wl": "W"},
        {"game_id": 3, "team_id": 10, "wl": "W"},
        {"game_id": 4, "team_id": 20, "wl": "L"},
        {"game_id": 5, "team_id": 20, "wl": "L"},
        {"game_id": 6, "team_id": 20, "wl": "W"},
    ]

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", player_rows)
    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", team_rows)

    result = build_result(
        season="2099-00",
        season_type="Regular Season",
        window_size=3,
        stretch_metric="pts",
        limit=5,
    )

    assert result.query_class == "leaderboard"
    leaders = result.leaders
    assert leaders.iloc[0]["player_name"] == "Alpha Scorer"
    assert leaders.iloc[0]["stretch_metric"] == "pts"
    assert leaders.iloc[0]["stretch_value"] == pytest.approx((20 + 24 + 26) / 3, rel=1e-3)


def test_build_result_computes_game_score_stretch_metric(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    player_rows = [
        _player_row(
            game_id=1,
            game_date="2099-10-01",
            player_id=1,
            player_name="All Around Ace",
            team_id=10,
            team_abbr="AAA",
            pts=22,
            fgm=8,
            fga=14,
            fg3m=2,
            fg3a=4,
            ftm=4,
            fta=4,
            reb=8,
            ast=9,
            stl=2,
            blk=1,
            tov=1,
            plus_minus=11,
        ),
        _player_row(
            game_id=2,
            game_date="2099-10-03",
            player_id=1,
            player_name="All Around Ace",
            team_id=10,
            team_abbr="AAA",
            pts=24,
            fgm=9,
            fga=15,
            fg3m=3,
            fg3a=5,
            ftm=3,
            fta=4,
            reb=7,
            ast=8,
            stl=2,
            blk=1,
            tov=2,
            plus_minus=10,
        ),
        _player_row(
            game_id=3,
            game_date="2099-10-05",
            player_id=1,
            player_name="All Around Ace",
            team_id=10,
            team_abbr="AAA",
            pts=26,
            fgm=10,
            fga=16,
            fg3m=3,
            fg3a=6,
            ftm=3,
            fta=4,
            reb=9,
            ast=10,
            stl=3,
            blk=2,
            tov=1,
            plus_minus=13,
        ),
    ]
    team_rows = [
        {"game_id": 1, "team_id": 10, "wl": "W"},
        {"game_id": 2, "team_id": 10, "wl": "W"},
        {"game_id": 3, "team_id": 10, "wl": "W"},
    ]

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", player_rows)
    _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", team_rows)

    result = build_result(
        season="2099-00",
        season_type="Regular Season",
        window_size=3,
        stretch_metric="game_score",
    )

    leaders = result.leaders
    assert leaders.iloc[0]["stretch_metric"] == "game_score"
    assert leaders.iloc[0]["games_in_window"] == 3
    assert leaders.iloc[0]["stretch_value"] > 0
