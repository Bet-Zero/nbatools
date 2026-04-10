import pandas as pd

from nbatools.commands.player_compare import filter_player_games
from nbatools.commands.team_compare import filter_team_games


def test_player_compare_filter_respects_date_window_before_last_n():
    df = pd.DataFrame(
        [
            {
                "player_name": "Nikola Jokić",
                "team_abbr": "DEN",
                "team_name": "Denver Nuggets",
                "opponent_team_abbr": "LAL",
                "opponent_team_name": "Los Angeles Lakers",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "game_id": 1,
                "game_date": "2026-02-01",
            },
            {
                "player_name": "Nikola Jokić",
                "team_abbr": "DEN",
                "team_name": "Denver Nuggets",
                "opponent_team_abbr": "LAL",
                "opponent_team_name": "Los Angeles Lakers",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "game_id": 2,
                "game_date": "2026-03-10",
            },
            {
                "player_name": "Nikola Jokić",
                "team_abbr": "DEN",
                "team_name": "Denver Nuggets",
                "opponent_team_abbr": "PHX",
                "opponent_team_name": "Phoenix Suns",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "game_id": 3,
                "game_date": "2026-03-12",
            },
            {
                "player_name": "Nikola Jokić",
                "team_abbr": "DEN",
                "team_name": "Denver Nuggets",
                "opponent_team_abbr": "LAL",
                "opponent_team_name": "Los Angeles Lakers",
                "is_home": 0,
                "is_away": 1,
                "wl": "L",
                "game_id": 4,
                "game_date": "2026-03-14",
            },
        ]
    )

    out = filter_player_games(
        df,
        player="Nikola Jokić",
        opponent="LAL",
        start_date="2026-03-01",
        end_date="2026-03-31",
        last_n=1,
    )

    assert len(out) == 1
    assert int(out.iloc[0]["game_id"]) == 4


def test_team_compare_filter_respects_date_window_before_last_n():
    df = pd.DataFrame(
        [
            {
                "team_abbr": "BOS",
                "team_name": "Boston Celtics",
                "opponent_team_abbr": "MIL",
                "opponent_team_name": "Milwaukee Bucks",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "game_id": 1,
                "game_date": "2026-02-01",
            },
            {
                "team_abbr": "BOS",
                "team_name": "Boston Celtics",
                "opponent_team_abbr": "MIL",
                "opponent_team_name": "Milwaukee Bucks",
                "is_home": 0,
                "is_away": 1,
                "wl": "W",
                "game_id": 2,
                "game_date": "2026-03-02",
            },
            {
                "team_abbr": "BOS",
                "team_name": "Boston Celtics",
                "opponent_team_abbr": "MIL",
                "opponent_team_name": "Milwaukee Bucks",
                "is_home": 1,
                "is_away": 0,
                "wl": "L",
                "game_id": 3,
                "game_date": "2026-03-20",
            },
        ]
    )

    out = filter_team_games(
        df,
        team="BOS",
        opponent="MIL",
        start_date="2026-03-01",
        end_date="2026-03-31",
        last_n=1,
    )

    assert len(out) == 1
    assert int(out.iloc[0]["game_id"]) == 3
