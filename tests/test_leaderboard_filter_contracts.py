"""Result-level tests verifying leaderboard routes respect filter slots.

Phase A addendum item 14: slots detected by the parser (last_n, home_only,
away_only, wins_only, losses_only) must actually change engine output.
These tests assert on result **content**, not just parse state.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.season_leaders import build_result as season_leaders_build
from nbatools.commands.season_team_leaders import build_result as season_team_leaders_build
from nbatools.commands.structured_results import LeaderboardResult, NoResult
from nbatools.commands.top_player_games import build_result as top_player_games_build
from nbatools.commands.top_team_games import build_result as top_team_games_build

pytestmark = pytest.mark.engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _make_player_game_rows():
    """Create a dataset with two players and mixed home/away, win/loss games.

    Player A: 20 games total
      - Games 1-10: home, wins, 30 pts each (early dates)
      - Games 11-20: away, losses, 10 pts each (later dates)

    Player B: 20 games total
      - Games 1-10: away, losses, 20 pts each (early dates)
      - Games 11-20: home, wins, 20 pts each (later dates)
    """
    rows = []
    for i in range(1, 11):
        rows.append(
            {
                "game_id": i,
                "game_date": f"2099-10-{i:02d}",
                "player_id": 1,
                "player_name": "Player A",
                "team_id": 100,
                "team_abbr": "AAA",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "is_home": 1,
                "is_away": 0,
                "pts": 30,
                "reb": 10,
                "ast": 5,
                "fgm": 12,
                "fga": 20,
                "fg3m": 2,
                "fg3a": 5,
                "ftm": 4,
                "fta": 5,
                "stl": 1,
                "blk": 1,
                "tov": 2,
                "plus_minus": 10,
                "minutes": 36,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(11, 21):
        rows.append(
            {
                "game_id": i,
                "game_date": f"2099-11-{(i - 10):02d}",
                "player_id": 1,
                "player_name": "Player A",
                "team_id": 100,
                "team_abbr": "AAA",
                "opponent_team_id": 300,
                "opponent_team_abbr": "CCC",
                "is_home": 0,
                "is_away": 1,
                "pts": 10,
                "reb": 4,
                "ast": 3,
                "fgm": 4,
                "fga": 15,
                "fg3m": 1,
                "fg3a": 4,
                "ftm": 1,
                "fta": 2,
                "stl": 0,
                "blk": 0,
                "tov": 3,
                "plus_minus": -10,
                "minutes": 30,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(1, 11):
        rows.append(
            {
                "game_id": i + 100,
                "game_date": f"2099-10-{i:02d}",
                "player_id": 2,
                "player_name": "Player B",
                "team_id": 200,
                "team_abbr": "BBB",
                "opponent_team_id": 100,
                "opponent_team_abbr": "AAA",
                "is_home": 0,
                "is_away": 1,
                "pts": 20,
                "reb": 6,
                "ast": 4,
                "fgm": 8,
                "fga": 16,
                "fg3m": 2,
                "fg3a": 5,
                "ftm": 2,
                "fta": 3,
                "stl": 1,
                "blk": 1,
                "tov": 2,
                "plus_minus": -5,
                "minutes": 34,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(11, 21):
        rows.append(
            {
                "game_id": i + 100,
                "game_date": f"2099-11-{(i - 10):02d}",
                "player_id": 2,
                "player_name": "Player B",
                "team_id": 200,
                "team_abbr": "BBB",
                "opponent_team_id": 300,
                "opponent_team_abbr": "CCC",
                "is_home": 1,
                "is_away": 0,
                "pts": 20,
                "reb": 6,
                "ast": 4,
                "fgm": 8,
                "fga": 16,
                "fg3m": 2,
                "fg3a": 5,
                "ftm": 2,
                "fta": 3,
                "stl": 1,
                "blk": 1,
                "tov": 2,
                "plus_minus": 5,
                "minutes": 34,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    return rows


def _make_player_team_wl_rows():
    """Minimal team game stats with wl column for player-game merging.

    Matches the game_id / team_id layout of _make_player_game_rows() so
    the engine can derive wl for player game logs (real data lacks wl).
    """
    rows = []
    for i in range(1, 11):
        rows.append({"game_id": i, "team_id": 100, "wl": "W"})
    for i in range(11, 21):
        rows.append({"game_id": i, "team_id": 100, "wl": "L"})
    for i in range(1, 11):
        rows.append({"game_id": i + 100, "team_id": 200, "wl": "L"})
    for i in range(11, 21):
        rows.append({"game_id": i + 100, "team_id": 200, "wl": "W"})
    return rows


def _make_team_game_rows():
    """Create team game data with mixed home/away, win/loss games.

    Team AAA: 20 games
      - Games 1-10: home, wins, 110 pts
      - Games 11-20: away, losses, 90 pts

    Team BBB: 20 games
      - Games 1-10: away, losses, 95 pts
      - Games 11-20: home, wins, 105 pts
    """
    rows = []
    for i in range(1, 11):
        rows.append(
            {
                "game_id": i,
                "game_date": f"2099-10-{i:02d}",
                "team_id": 100,
                "team_name": "Team AAA",
                "team_abbr": "AAA",
                "opponent_team_id": 200,
                "opponent_team_abbr": "BBB",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "pts": 110,
                "reb": 45,
                "ast": 25,
                "fgm": 40,
                "fga": 85,
                "fg3m": 12,
                "fg3a": 30,
                "ftm": 18,
                "fta": 22,
                "stl": 8,
                "blk": 5,
                "tov": 12,
                "plus_minus": 15,
                "minutes": 240,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(11, 21):
        rows.append(
            {
                "game_id": i,
                "game_date": f"2099-11-{(i - 10):02d}",
                "team_id": 100,
                "team_name": "Team AAA",
                "team_abbr": "AAA",
                "opponent_team_id": 300,
                "opponent_team_abbr": "CCC",
                "is_home": 0,
                "is_away": 1,
                "wl": "L",
                "pts": 90,
                "reb": 38,
                "ast": 20,
                "fgm": 33,
                "fga": 85,
                "fg3m": 8,
                "fg3a": 25,
                "ftm": 16,
                "fta": 20,
                "stl": 6,
                "blk": 3,
                "tov": 15,
                "plus_minus": -10,
                "minutes": 240,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(1, 11):
        rows.append(
            {
                "game_id": i + 100,
                "game_date": f"2099-10-{i:02d}",
                "team_id": 200,
                "team_name": "Team BBB",
                "team_abbr": "BBB",
                "opponent_team_id": 100,
                "opponent_team_abbr": "AAA",
                "is_home": 0,
                "is_away": 1,
                "wl": "L",
                "pts": 95,
                "reb": 40,
                "ast": 22,
                "fgm": 35,
                "fga": 85,
                "fg3m": 10,
                "fg3a": 28,
                "ftm": 15,
                "fta": 20,
                "stl": 7,
                "blk": 4,
                "tov": 13,
                "plus_minus": -15,
                "minutes": 240,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    for i in range(11, 21):
        rows.append(
            {
                "game_id": i + 100,
                "game_date": f"2099-11-{(i - 10):02d}",
                "team_id": 200,
                "team_name": "Team BBB",
                "team_abbr": "BBB",
                "opponent_team_id": 300,
                "opponent_team_abbr": "CCC",
                "is_home": 1,
                "is_away": 0,
                "wl": "W",
                "pts": 105,
                "reb": 43,
                "ast": 24,
                "fgm": 38,
                "fga": 85,
                "fg3m": 11,
                "fg3a": 28,
                "ftm": 18,
                "fta": 22,
                "stl": 8,
                "blk": 5,
                "tov": 12,
                "plus_minus": 10,
                "minutes": 240,
                "season": "2099-00",
                "season_type": "Regular Season",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# season_leaders filter contract tests
# ---------------------------------------------------------------------------


class TestSeasonLeadersWinsOnly:
    """season_leaders with wins_only=True should only count win games."""

    def test_wins_only_changes_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_player_team_wl_rows(),
        )

        full = season_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        wins = season_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, wins_only=True
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(wins, LeaderboardResult)

        # Player A averages 20 ppg overall (30*10 + 10*10 = 400/20)
        # Player A averages 30 ppg in wins only (30*10 = 300/10)
        full_a = full.leaders[full.leaders["player_name"] == "Player A"]
        wins_a = wins.leaders[wins.leaders["player_name"] == "Player A"]

        assert abs(full_a.iloc[0]["pts_per_game"] - 20.0) < 0.01
        assert abs(wins_a.iloc[0]["pts_per_game"] - 30.0) < 0.01


class TestSeasonLeadersHomeOnly:
    """season_leaders with home_only=True should only count home games."""

    def test_home_only_changes_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )

        full = season_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        home = season_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, home_only=True
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(home, LeaderboardResult)

        # Player A: 20 ppg overall, 30 ppg at home
        full_a = full.leaders[full.leaders["player_name"] == "Player A"]
        home_a = home.leaders[home.leaders["player_name"] == "Player A"]

        assert abs(full_a.iloc[0]["pts_per_game"] - 20.0) < 0.01
        assert abs(home_a.iloc[0]["pts_per_game"] - 30.0) < 0.01


class TestSeasonLeadersLastN:
    """season_leaders with last_n should only use each player's N most recent games."""

    def test_last_n_changes_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )

        full = season_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        last5 = season_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1, last_n=5)

        assert isinstance(full, LeaderboardResult)
        assert isinstance(last5, LeaderboardResult)

        # Player A: 20 ppg overall; last 5 games are games 16-20 (all away, 10 pts)
        full_a = full.leaders[full.leaders["player_name"] == "Player A"]
        last5_a = last5.leaders[last5.leaders["player_name"] == "Player A"]

        assert abs(full_a.iloc[0]["pts_per_game"] - 20.0) < 0.01
        assert abs(last5_a.iloc[0]["pts_per_game"] - 10.0) < 0.01


class TestSeasonLeadersLossesOnly:
    """season_leaders with losses_only=True should only count loss games."""

    def test_losses_only_changes_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_player_team_wl_rows(),
        )

        full = season_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        losses = season_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, losses_only=True
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(losses, LeaderboardResult)

        # Player A: 20 ppg overall, 10 ppg in losses
        full_a = full.leaders[full.leaders["player_name"] == "Player A"]
        losses_a = losses.leaders[losses.leaders["player_name"] == "Player A"]

        assert abs(full_a.iloc[0]["pts_per_game"] - 20.0) < 0.01
        assert abs(losses_a.iloc[0]["pts_per_game"] - 10.0) < 0.01


class TestSeasonLeadersCaveats:
    """Filter caveats should appear in the result."""

    def test_filter_caveats_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_player_team_wl_rows(),
        )

        result = season_leaders_build(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            wins_only=True,
            home_only=True,
            last_n=10,
        )
        assert isinstance(result, LeaderboardResult)
        caveats_text = " ".join(result.caveats)
        assert "home games only" in caveats_text
        assert "wins only" in caveats_text
        assert "last 10 games" in caveats_text


class TestSeasonLeadersEmptySample:
    def test_filtered_empty_returns_no_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )

        result = season_leaders_build(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            start_date="2100-01-01",
        )

        assert isinstance(result, NoResult)
        assert result.result_reason == "no_match"
        assert result.notes == ["No games matched the specified filters"]


# ---------------------------------------------------------------------------
# season_team_leaders filter contract tests
# ---------------------------------------------------------------------------


class TestTeamLeadersLastN:
    """season_team_leaders with last_n should only use each team's N most recent games."""

    def test_last_n_changes_team_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        full = season_team_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        last5 = season_team_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, last_n=5
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(last5, LeaderboardResult)

        # Team AAA: 100 ppg overall (110*10 + 90*10 = 2000/20)
        # Team AAA last 5: 90 ppg (games 16-20 are all away losses at 90)
        full_aaa = full.leaders[full.leaders["team_abbr"] == "AAA"]
        last5_aaa = last5.leaders[last5.leaders["team_abbr"] == "AAA"]

        assert abs(full_aaa.iloc[0]["pts_per_game"] - 100.0) < 0.01
        assert abs(last5_aaa.iloc[0]["pts_per_game"] - 90.0) < 0.01


class TestTeamLeadersWinsOnly:
    """season_team_leaders with wins_only=True should only count win games."""

    def test_wins_only_changes_team_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        full = season_team_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        wins = season_team_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, wins_only=True
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(wins, LeaderboardResult)

        # Team AAA: 100 ppg overall, 110 ppg in wins only
        full_aaa = full.leaders[full.leaders["team_abbr"] == "AAA"]
        wins_aaa = wins.leaders[wins.leaders["team_abbr"] == "AAA"]

        assert abs(full_aaa.iloc[0]["pts_per_game"] - 100.0) < 0.01
        assert abs(wins_aaa.iloc[0]["pts_per_game"] - 110.0) < 0.01


class TestTeamLeadersLossesOnly:
    """season_team_leaders with losses_only=True should only count loss games."""

    def test_losses_only_changes_team_ppg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        full = season_team_leaders_build(season="2099-00", stat="pts", limit=10, min_games=1)
        losses = season_team_leaders_build(
            season="2099-00", stat="pts", limit=10, min_games=1, losses_only=True
        )

        assert isinstance(full, LeaderboardResult)
        assert isinstance(losses, LeaderboardResult)

        # Team AAA: 100 ppg overall, 90 ppg in losses only
        full_aaa = full.leaders[full.leaders["team_abbr"] == "AAA"]
        losses_aaa = losses.leaders[losses.leaders["team_abbr"] == "AAA"]

        assert abs(full_aaa.iloc[0]["pts_per_game"] - 100.0) < 0.01
        assert abs(losses_aaa.iloc[0]["pts_per_game"] - 90.0) < 0.01


class TestTeamLeadersEmptySample:
    def test_filtered_empty_returns_no_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        result = season_team_leaders_build(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            start_date="2100-01-01",
        )

        assert isinstance(result, NoResult)
        assert result.result_reason == "no_match"
        assert result.notes == ["No games matched the specified filters"]


# ---------------------------------------------------------------------------
# top_player_games filter contract tests
# ---------------------------------------------------------------------------


class TestTopPlayerGamesWinsOnly:
    """top_player_games with wins_only should only show games from wins."""

    def test_wins_only_changes_results(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_player_team_wl_rows(),
        )

        full = top_player_games_build(season="2099-00", stat="pts", limit=40)
        wins = top_player_games_build(season="2099-00", stat="pts", limit=40, wins_only=True)

        assert isinstance(full, LeaderboardResult)
        assert isinstance(wins, LeaderboardResult)

        # Full has 40 rows (all games); wins-only should have 20 (10 per player)
        assert len(full.leaders) == 40
        assert len(wins.leaders) == 20


class TestTopPlayerGamesLastN:
    """top_player_games with last_n should only consider the N most recent games."""

    def test_last_n_limits_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )

        # Last 10 games globally: games 111-120 (Player B, Nov) and 11-20 (Player A, Nov)
        # These are all 10-pt (Player A away losses) and 20-pt (Player B home wins)
        last10 = top_player_games_build(season="2099-00", stat="pts", limit=5, last_n=10)

        assert isinstance(last10, LeaderboardResult)
        # The top result in last 10 should be 20 pts (Player B), not 30 pts (Player A early)
        assert last10.leaders.iloc[0]["pts"] <= 20


class TestTopPlayerGamesEmptySample:
    def test_filtered_empty_returns_no_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            _make_player_game_rows(),
        )

        result = top_player_games_build(
            season="2099-00",
            stat="pts",
            limit=5,
            start_date="2100-01-01",
        )

        assert isinstance(result, NoResult)
        assert result.result_reason == "no_match"
        assert result.notes == ["No games matched the specified filters"]


# ---------------------------------------------------------------------------
# top_team_games filter contract tests
# ---------------------------------------------------------------------------


class TestTopTeamGamesHomeOnly:
    """top_team_games with home_only should only show home games."""

    def test_home_only_filters_team_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        home = top_team_games_build(season="2099-00", stat="pts", limit=5, home_only=True)

        assert isinstance(home, LeaderboardResult)
        for _, row in home.leaders.iterrows():
            assert row["is_home"] == 1


class TestTopTeamGamesEmptySample:
    def test_filtered_empty_returns_no_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_csv(
            tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv",
            _make_team_game_rows(),
        )

        result = top_team_games_build(
            season="2099-00",
            stat="pts",
            limit=5,
            start_date="2100-01-01",
        )

        assert isinstance(result, NoResult)
        assert result.result_reason == "no_match"
        assert result.notes == ["No games matched the specified filters"]
