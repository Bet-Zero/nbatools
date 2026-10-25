"""K09 controlled sequence witnesses; these rows are synthetic, not NBA evidence."""

import pandas as pd
import pytest

from nbatools.commands import player_streak_finder as player_streak
from nbatools.commands import player_stretch_leaderboard as player_stretch
from nbatools.commands import team_streak_finder as team_streak
from nbatools.commands import team_stretch_leaderboard as team_stretch

pytestmark = pytest.mark.engine


def _games(outcomes, *, points=None, homes=None, seasons=None):
    rows = []
    for i, outcome in enumerate(outcomes):
        season = seasons[i] if seasons else "2099-00"
        home = homes[i] if homes else 1
        rows.append(
            dict(
                game_id=100 + i,
                game_date=f"{season[:4]}-10-{i + 1:02d}",
                season=season,
                season_type="Regular Season",
                team_id=100,
                team_abbr="AAA",
                team_name="Alpha",
                opponent_team_id=200,
                opponent_team_abbr="BBB",
                opponent_team_name="Beta",
                is_home=home,
                is_away=1 - home,
                wl=outcome,
                pts=points[i] if points else 110,
                reb=40,
                ast=25,
                stl=7,
                blk=4,
                fg3m=12,
                fg3a=30,
                tov=10,
                plus_minus=9 if outcome == "W" else -9,
                player_id=1,
                player_name="Streak Guy",
                minutes=35,
                fgm=40,
                fga=80,
                oreb=8,
                dreb=32,
                fta=20,
                ftm=16,
                pf=18,
            )
        )
    return pd.DataFrame(rows)


def _build(monkeypatch, module, games, **kwargs):
    kind = "player" if module in (player_streak, player_stretch) else "team"
    monkeypatch.setattr(module, f"load_{kind}_games_for_seasons", lambda *a: games.copy())
    monkeypatch.setattr(module, "compute_current_through_for_seasons", lambda *a: "2100-10-09")
    return module.build_result(season_type="Regular Season", **kwargs)


def test_k09_distinct_maximal_runs_not_overlapping_windows(monkeypatch):
    result = _build(
        monkeypatch,
        team_streak,
        _games("WWWWWLWWW"),
        season="2099-00",
        team="AAA",
        special_condition="wins",
        min_streak_length=3,
    )
    rows = result.streaks
    assert list(rows.streak_length) == [5, 3]
    assert set(zip(rows.start_game_id, rows.end_game_id)) == {(100, 104), (106, 108)}


def test_k09_failed_and_missing_stats_break_runs(monkeypatch):
    games = _games("WWWWWWWW", points=[21, 24, None, 25, 29, 19, 31, 35])
    result = _build(
        monkeypatch,
        player_streak,
        games,
        season="2099-00",
        player="Streak Guy",
        stat="pts",
        min_value=20,
        min_streak_length=2,
    )
    assert list(result.streaks.streak_length) == [2, 2, 2]
    assert set(zip(result.streaks.start_game_id, result.streaks.end_game_id)) == {
        (100, 101),
        (103, 104),
        (106, 107),
    }


@pytest.mark.parametrize("home_only,length", [(False, 1), (True, 2)])
def test_k09_explicit_sample_filter_precedes_streak(monkeypatch, home_only, length):
    result = _build(
        monkeypatch,
        team_streak,
        _games("WLW", homes=[1, 0, 1]),
        season="2099-00",
        team="AAA",
        special_condition="wins",
        longest=True,
        home_only=home_only,
    )
    assert int(result.streaks.iloc[0].streak_length) == length


def test_k09_player_appearance_gap_is_not_failed_stat_or_health(monkeypatch):
    games = _games("WW", points=[21, 24])
    games.loc[1, ["game_id", "game_date"]] = [102, "2099-10-03"]
    result = _build(
        monkeypatch,
        player_streak,
        games,
        season="2099-00",
        player="Streak Guy",
        stat="pts",
        min_value=20,
        longest=True,
    )
    assert int(result.streaks.iloc[0].streak_length) == 2
    assert (result.streaks.iloc[0].start_game_id, result.streaks.iloc[0].end_game_id) == (100, 102)
    assert any("appear" in c or "missed games are skipped" in c for c in result.caveats)


def test_k09_selected_season_streak_and_team_window_have_distinct_boundaries(monkeypatch):
    games = _games("WWWW", seasons=["2099-00", "2099-00", "2100-01", "2100-01"])
    streak = _build(
        monkeypatch,
        team_streak,
        games,
        start_season="2099-00",
        end_season="2100-01",
        team="AAA",
        special_condition="wins",
        longest=True,
    )
    assert int(streak.streaks.iloc[0].streak_length) == 4
    assert any("across 2 seasons" in c for c in streak.caveats)
    window = _build(
        monkeypatch,
        team_stretch,
        games,
        start_season="2099-00",
        end_season="2100-01",
        team="AAA",
        window_size=3,
        stretch_metric="wins",
    )
    assert window.result_status == "no_result"
    assert window.reason == "no_match"


@pytest.mark.parametrize(
    "module,subject,metric,expected",
    [
        (team_stretch, {"team": "AAA"}, "wins", (3, 0)),
        (player_stretch, {"player": "Streak Guy"}, "pts", (131, 81)),
    ],
)
def test_k09_best_window_differs_from_last_window(monkeypatch, module, subject, metric, expected):
    games = _games("WWWLLL", points=[130, 131, 132, 80, 81, 82])
    kwargs = dict(season="2099-00", window_size=3, stretch_metric=metric, **subject)
    best = _build(monkeypatch, module, games, **kwargs).leaders.iloc[0]
    last = _build(monkeypatch, module, games, last_n=3, **kwargs).leaders.iloc[0]
    assert (best.stretch_value, last.stretch_value) == expected
    assert pd.Timestamp(best.window_start_date).date().isoformat() == "2099-10-01"
    assert pd.Timestamp(last.window_start_date).date().isoformat() == "2099-10-04"
