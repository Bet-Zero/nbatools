from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.season_leaders import build_result as season_leaders_build_result

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


def test_season_leaders_dedupes_traded_player_and_keeps_latest_team(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []

    # Trade Guy: 24 total games, first 12 on AAA, last 12 on BBB.
    # This keeps him above the default per-game eligibility floor so the test
    # actually checks dedupe/latest-team behavior instead of getting filtered out.
    for game_id in range(1, 13):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-10-{game_id:02d}",
                "player_id": 1,
                "player_name": "Trade Guy",
                "team_id": 100,
                "team_abbr": "AAA",
                "pts": 28,
                "reb": 5,
                "ast": 2,
                "fgm": 10,
                "fga": 20,
                "fg3m": 2,
                "fg3a": 5,
                "ftm": 6,
                "fta": 7,
            }
        )

    for game_id in range(13, 25):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-11-{(game_id - 12):02d}",
                "player_id": 1,
                "player_name": "Trade Guy",
                "team_id": 200,
                "team_abbr": "BBB",
                "pts": 30,
                "reb": 5,
                "ast": 2,
                "fgm": 11,
                "fga": 21,
                "fg3m": 3,
                "fg3a": 6,
                "ftm": 5,
                "fta": 6,
            }
        )

    # Other Guy: enough games to be eligible, but lower scoring average.
    for game_id in range(25, 50):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-12-{(game_id - 24):02d}",
                "player_id": 2,
                "player_name": "Other Guy",
                "team_id": 300,
                "team_abbr": "CCC",
                "pts": 15,
                "reb": 4,
                "ast": 3,
                "fgm": 6,
                "fga": 14,
                "fg3m": 1,
                "fg3a": 4,
                "ftm": 2,
                "fta": 2,
            }
        )

    _write_csv(
        tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
        rows,
    )

    result = season_leaders_build_result(
        season="2099-00",
        stat="pts",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    trade_rows = df[df["player_id"] == 1]
    assert len(trade_rows) == 1
    assert trade_rows.iloc[0]["team_abbr"] == "BBB"


def test_season_leaders_default_min_games_filters_small_sample_per_game_leader(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    rows = []
    for game_id in range(1, 11):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-10-{game_id:02d}",
                "player_id": 1,
                "player_name": "Small Sample Star",
                "team_id": 100,
                "team_abbr": "AAA",
                "pts": 10,
                "reb": 5,
                "ast": 10,
                "fgm": 4,
                "fga": 10,
                "fg3m": 1,
                "fg3a": 3,
                "ftm": 1,
                "fta": 2,
            }
        )
    for game_id in range(11, 36):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-11-{(game_id - 10):02d}",
                "player_id": 2,
                "player_name": "Real Leader",
                "team_id": 200,
                "team_abbr": "BBB",
                "pts": 10,
                "reb": 5,
                "ast": 9,
                "fgm": 4,
                "fga": 10,
                "fg3m": 1,
                "fg3a": 3,
                "ftm": 1,
                "fta": 2,
            }
        )

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

    result = season_leaders_build_result(
        season="2099-00",
        stat="ast",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    assert "Small Sample Star" not in df["player_name"].tolist()
    assert df.iloc[0]["player_name"] == "Real Leader"


def test_season_leaders_percentage_guardrail_filters_low_attempt_outlier(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rows = []
    for game_id in range(1, 26):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-10-{game_id:02d}",
                "player_id": 1,
                "player_name": "Tiny Volume Guy",
                "team_id": 100,
                "team_abbr": "AAA",
                "pts": 4,
                "reb": 1,
                "ast": 1,
                "fgm": 2,
                "fga": 2,
                "fg3m": 0,
                "fg3a": 0,
                "ftm": 0,
                "fta": 0,
            }
        )
    for game_id in range(26, 51):
        rows.append(
            {
                "game_id": game_id,
                "game_date": f"2099-11-{(game_id - 25):02d}",
                "player_id": 2,
                "player_name": "Real Volume Guy",
                "team_id": 200,
                "team_abbr": "BBB",
                "pts": 20,
                "reb": 5,
                "ast": 3,
                "fgm": 8,
                "fga": 12,
                "fg3m": 1,
                "fg3a": 3,
                "ftm": 3,
                "fta": 4,
            }
        )

    _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

    result = season_leaders_build_result(
        season="2099-00",
        stat="ts_pct",
        limit=10,
        season_type="Regular Season",
        min_games=1,
        ascending=False,
    )
    df = result.leaders

    assert "Tiny Volume Guy" not in df["player_name"].tolist()
    assert df.iloc[0]["player_name"] == "Real Volume Guy"
