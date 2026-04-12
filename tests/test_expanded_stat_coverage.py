"""Tests for expanded stat coverage: STL, BLK, TOV, eFG%, TS%, plus_minus.

Covers:
- Parser/alias detection for new stats
- Finder stat threshold filtering
- Leaderboard ranking by new stats
- Summary/comparison inclusion of new stats
- Historical/opponent-filtered stat queries
- Ascending/descending detection for leaderboards
- Structured query parity
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._constants import STAT_ALIASES
from nbatools.commands.natural_query import (
    detect_player_leaderboard_stat,
    detect_stat,
    detect_team_leaderboard_stat,
    extract_min_value,
    extract_threshold_conditions,
    parse_query,
    wants_ascending_leaderboard,
    wants_leaderboard,
    wants_team_leaderboard,
)
from nbatools.commands.player_compare import build_result as compare_build_result
from nbatools.commands.player_game_finder import build_result as finder_build_result
from nbatools.commands.player_game_summary import build_result as summary_build_result
from nbatools.commands.season_leaders import build_result as leaders_build_result
from nbatools.commands.season_team_leaders import build_result as team_leaders_build_result
from nbatools.commands.structured_results import (
    ComparisonResult,
    FinderResult,
    LeaderboardResult,
    SummaryResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _make_player_rows(
    player_id: int,
    player_name: str,
    team_id: int,
    team_abbr: str,
    n_games: int,
    base_stats: dict,
    start_date: str = "2099-10-01",
    opponent_abbr: str = "OPP",
    opponent_name: str = "Opponents",
    season: str = "2099-00",
):
    """Generate n_games rows of player game stats with the given base stats."""
    rows = []
    for i in range(n_games):
        day = int(start_date.split("-")[2]) + i
        month = start_date.split("-")[1]
        year = start_date.split("-")[0]
        row = {
            "game_id": player_id * 1000 + i,
            "game_date": f"{year}-{month}-{day:02d}",
            "season": season,
            "season_type": "Regular Season",
            "player_id": player_id,
            "player_name": player_name,
            "team_id": team_id,
            "team_abbr": team_abbr,
            "team_name": f"Team {team_abbr}",
            "opponent_team_id": 999,
            "opponent_team_abbr": opponent_abbr,
            "opponent_team_name": opponent_name,
            "is_home": 1,
            "is_away": 0,
            "wl": "W",
            "starter_flag": 1,
            "start_position": "C",
            "minutes": 32.0,
            "pts": 20,
            "reb": 10,
            "ast": 5,
            "stl": 1,
            "blk": 1,
            "tov": 2,
            "pf": 2,
            "fgm": 8,
            "fga": 16,
            "fg3m": 2,
            "fg3a": 5,
            "ftm": 2,
            "fta": 3,
            "oreb": 3,
            "dreb": 7,
            "fg_pct": 0.500,
            "fg3_pct": 0.400,
            "ft_pct": 0.667,
            "plus_minus": 5,
        }
        row.update(base_stats)
        rows.append(row)
    return rows


def _team_rows_from_player_rows(player_rows: list[dict]) -> list[dict]:
    """Generate minimal team_game_stats rows from player rows for the data loader."""
    seen = set()
    team_rows = []
    for r in player_rows:
        key = (r["game_id"], r["team_id"])
        if key not in seen:
            seen.add(key)
            team_rows.append(
                {
                    "game_id": r["game_id"],
                    "game_date": r["game_date"],
                    "season": r.get("season", "2099-00"),
                    "season_type": r.get("season_type", "Regular Season"),
                    "team_id": r["team_id"],
                    "team_abbr": r["team_abbr"],
                    "team_name": r.get("team_name", f"Team {r['team_abbr']}"),
                    "opponent_team_id": r.get("opponent_team_id", 999),
                    "opponent_team_abbr": r.get("opponent_team_abbr", "OPP"),
                    "opponent_team_name": r.get("opponent_team_name", "Opponents"),
                    "is_home": r.get("is_home", 1),
                    "is_away": r.get("is_away", 0),
                    "wl": r.get("wl", "W"),
                    "pts": r.get("pts", 100),
                    "reb": r.get("reb", 45),
                    "ast": r.get("ast", 25),
                    "stl": r.get("stl", 8),
                    "blk": r.get("blk", 5),
                    "tov": r.get("tov", 12),
                    "pf": r.get("pf", 18),
                    "fgm": r.get("fgm", 38),
                    "fga": r.get("fga", 85),
                    "fg3m": r.get("fg3m", 12),
                    "fg3a": r.get("fg3a", 32),
                    "ftm": r.get("ftm", 12),
                    "fta": r.get("fta", 16),
                    "oreb": r.get("oreb", 10),
                    "dreb": r.get("dreb", 35),
                    "plus_minus": r.get("plus_minus", 5),
                    "minutes": r.get("minutes", 240),
                }
            )
    return team_rows


def _write_player_and_team_csvs(
    tmp_path,
    player_rows: list[dict],
    season: str = "2099-00",
    season_type_safe: str = "regular_season",
):
    """Write both player_game_stats and team_game_stats CSVs needed by the data loader."""
    _write_csv(
        tmp_path / f"data/raw/player_game_stats/{season}_{season_type_safe}.csv",
        player_rows,
    )
    team_rows = _team_rows_from_player_rows(player_rows)
    _write_csv(
        tmp_path / f"data/raw/team_game_stats/{season}_{season_type_safe}.csv",
        team_rows,
    )


def _make_team_rows(
    team_id: int,
    team_abbr: str,
    team_name: str,
    n_games: int,
    base_stats: dict,
    opponent_abbr: str = "OPP",
    opponent_name: str = "Opponents",
    season: str = "2099-00",
):
    rows = []
    for i in range(n_games):
        row = {
            "game_id": team_id * 1000 + i,
            "game_date": f"2099-10-{(i + 1):02d}",
            "season": season,
            "season_type": "Regular Season",
            "team_id": team_id,
            "team_abbr": team_abbr,
            "team_name": team_name,
            "opponent_team_id": 999,
            "opponent_team_abbr": opponent_abbr,
            "opponent_team_name": opponent_name,
            "is_home": 1,
            "is_away": 0,
            "wl": "W",
            "pts": 100,
            "reb": 45,
            "ast": 25,
            "stl": 8,
            "blk": 5,
            "tov": 12,
            "pf": 18,
            "fgm": 38,
            "fga": 85,
            "fg3m": 12,
            "fg3a": 32,
            "ftm": 12,
            "fta": 16,
            "oreb": 10,
            "dreb": 35,
            "fg_pct": 0.447,
            "fg3_pct": 0.375,
            "ft_pct": 0.750,
            "plus_minus": 8,
            "minutes": 240,
        }
        row.update(base_stats)
        rows.append(row)
    return rows


# ===========================================================================
# 1. Parser / Alias Detection Tests
# ===========================================================================


class TestStatAliases:
    """Test that STAT_ALIASES correctly maps new stat names."""

    def test_steals_aliases(self):
        assert STAT_ALIASES["steals"] == "stl"
        assert STAT_ALIASES["steal"] == "stl"
        assert STAT_ALIASES["stl"] == "stl"

    def test_blocks_aliases(self):
        assert STAT_ALIASES["blocks"] == "blk"
        assert STAT_ALIASES["block"] == "blk"
        assert STAT_ALIASES["blk"] == "blk"

    def test_turnovers_aliases(self):
        assert STAT_ALIASES["turnovers"] == "tov"
        assert STAT_ALIASES["turnover"] == "tov"
        assert STAT_ALIASES["tov"] == "tov"

    def test_efg_pct_aliases(self):
        assert STAT_ALIASES["efg%"] == "efg_pct"
        assert STAT_ALIASES["efg_pct"] == "efg_pct"
        assert STAT_ALIASES["effective field goal"] == "efg_pct"
        assert STAT_ALIASES["effective field goal %"] == "efg_pct"
        assert STAT_ALIASES["effective fg"] == "efg_pct"

    def test_ts_pct_aliases(self):
        assert STAT_ALIASES["ts%"] == "ts_pct"
        assert STAT_ALIASES["ts_pct"] == "ts_pct"
        assert STAT_ALIASES["true shooting"] == "ts_pct"
        assert STAT_ALIASES["true shooting %"] == "ts_pct"

    def test_plus_minus_aliases(self):
        assert STAT_ALIASES["plus_minus"] == "plus_minus"
        assert STAT_ALIASES["plus minus"] == "plus_minus"
        assert STAT_ALIASES["plus/minus"] == "plus_minus"
        assert STAT_ALIASES["+/-"] == "plus_minus"

    def test_detect_stat_steals(self):
        assert detect_stat("3+ steals games") == "stl"

    def test_detect_stat_blocks(self):
        assert detect_stat("2 blocks or more") == "blk"

    def test_detect_stat_turnovers(self):
        assert detect_stat("under 3 turnovers") == "tov"

    def test_detect_stat_efg(self):
        assert detect_stat("efg% over .600") == "efg_pct"

    def test_detect_stat_ts(self):
        assert detect_stat("ts% over .700") == "ts_pct"

    def test_detect_stat_plus_minus(self):
        assert detect_stat("plus minus above 10") == "plus_minus"

    def test_detect_stat_no_false_positive_on_stats(self):
        """'stats' should not falsely detect 'ts' as ts_pct."""
        # detect_stat uses substring matching; 'ts%' (4 chars) checked before 'ts_pct' (6 chars)
        # but neither should match inside 'career stats'
        result = detect_stat("career stats")
        # The substring 'ts' is not in STAT_ALIASES (removed for safety),
        # but 'ts%' or 'ts_pct' won't match inside 'stats'
        assert result != "ts_pct"


# ===========================================================================
# 2. Threshold Extraction Tests
# ===========================================================================


class TestThresholdExtraction:
    """Test threshold extraction for new stats including advanced stats."""

    def test_steals_n_plus(self):
        stat = detect_stat("jokic 3+ steals")
        min_val = extract_min_value("jokic 3+ steals", stat)
        assert stat == "stl"
        assert min_val == 3.0

    def test_blocks_n_plus(self):
        stat = detect_stat("embiid 2+ blocks")
        min_val = extract_min_value("embiid 2+ blocks", stat)
        assert stat == "blk"
        assert min_val == 2.0

    def test_turnovers_under(self):
        conditions = extract_threshold_conditions("celtics under 10 turnovers")
        assert len(conditions) == 1
        assert conditions[0]["stat"] == "tov"
        assert conditions[0]["max_value"] == pytest.approx(9.9999)

    def test_ts_pct_over_reverse_order(self):
        """'TS% over .700' — stat before operator (reverse pattern)."""
        conditions = extract_threshold_conditions("jokic games with ts% over .700")
        assert len(conditions) == 1
        assert conditions[0]["stat"] == "ts_pct"
        assert conditions[0]["min_value"] == pytest.approx(0.7001)

    def test_efg_pct_above_reverse_order(self):
        """'eFG% above .600' — stat before operator (reverse pattern)."""
        conditions = extract_threshold_conditions("teams with efg% above .600")
        assert len(conditions) == 1
        assert conditions[0]["stat"] == "efg_pct"
        assert conditions[0]["min_value"] == pytest.approx(0.6001)

    def test_plus_minus_over(self):
        conditions = extract_threshold_conditions("jokic games with plus minus over 10")
        assert len(conditions) == 1
        assert conditions[0]["stat"] == "plus_minus"
        assert conditions[0]["min_value"] == pytest.approx(10.0001)

    def test_efg_pct_below_reverse_order(self):
        conditions = extract_threshold_conditions("games with efg% below .400")
        assert len(conditions) == 1
        assert conditions[0]["stat"] == "efg_pct"
        assert conditions[0]["max_value"] == pytest.approx(0.3999)


# ===========================================================================
# 3. Leaderboard Detection Tests
# ===========================================================================


class TestLeaderboardDetection:
    """Test leaderboard stat detection and ascending/descending logic."""

    def test_leaders_in_steals(self):
        assert detect_player_leaderboard_stat("leaders in steals since 2020") == "stl"

    def test_most_blocks(self):
        assert detect_player_leaderboard_stat("most blocks this season") == "blk"

    def test_most_turnovers(self):
        assert detect_player_leaderboard_stat("most turnovers this season") == "tov"

    def test_plus_minus_leaders(self):
        assert detect_player_leaderboard_stat("best plus minus since 2021") == "plus_minus"

    def test_wants_leaderboard_steals(self):
        assert wants_leaderboard("leaders in steals since 2020")

    def test_wants_leaderboard_blocks(self):
        assert wants_leaderboard("most blocks this season")

    def test_wants_leaderboard_fewest_turnovers(self):
        assert wants_leaderboard("fewest turnovers this season")

    def test_ascending_fewest(self):
        assert wants_ascending_leaderboard("fewest turnovers this season") is True

    def test_ascending_lowest(self):
        assert wants_ascending_leaderboard("lowest turnovers per game") is True

    def test_ascending_worst(self):
        assert wants_ascending_leaderboard("worst plus minus") is True

    def test_not_ascending_most(self):
        assert wants_ascending_leaderboard("most steals this season") is False

    def test_not_ascending_best(self):
        assert wants_ascending_leaderboard("best efg% this season") is False

    def test_team_leaderboard_steals(self):
        assert detect_team_leaderboard_stat("most steals teams") == "stl"

    def test_team_leaderboard_blocks(self):
        assert detect_team_leaderboard_stat("most blocks teams") == "blk"

    def test_team_leaderboard_turnovers(self):
        assert detect_team_leaderboard_stat("lowest turnover teams") == "tov"

    def test_team_leaderboard_plus_minus(self):
        assert detect_team_leaderboard_stat("best plus minus teams") == "plus_minus"

    def test_wants_team_leaderboard_new_stats(self):
        assert wants_team_leaderboard("most steals teams this season")
        assert wants_team_leaderboard("lowest turnover teams this season")


# ===========================================================================
# 4. Natural Query Parse → Route Tests
# ===========================================================================


class TestNaturalQueryRouting:
    """Test that natural queries route correctly with new stats."""

    def test_parse_leaders_in_steals(self):
        parsed = parse_query("leaders in steals since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "stl"

    def test_parse_most_blocks(self):
        parsed = parse_query("most blocks this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "blk"

    def test_parse_fewest_turnovers_ascending(self):
        parsed = parse_query("fewest turnovers this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "tov"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_parse_best_plus_minus(self):
        parsed = parse_query("best plus minus this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "plus_minus"

    def test_parse_lowest_turnovers_team(self):
        parsed = parse_query("lowest turnover teams this season")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "tov"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_parse_most_steals_playoffs(self):
        parsed = parse_query("most steals in playoffs since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "stl"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_parse_best_efg_last_3_seasons(self):
        parsed = parse_query("best efg% last 3 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "efg_pct"
        assert parsed["route_kwargs"].get("start_season") is not None

    def test_finder_steals_threshold(self):
        parsed = parse_query("jokic games with 3+ steals")
        assert parsed["route"] in ("player_game_finder", "player_game_summary")
        assert parsed["route_kwargs"]["stat"] == "stl"
        assert parsed["route_kwargs"]["min_value"] == 3.0

    def test_finder_ts_pct_threshold(self):
        parsed = parse_query("jokic games with ts% over .700")
        assert parsed["route"] in ("player_game_finder", "player_game_summary")
        assert parsed["route_kwargs"]["stat"] == "ts_pct"
        assert parsed["route_kwargs"]["min_value"] == pytest.approx(0.7001)

    def test_finder_blocks_threshold(self):
        parsed = parse_query("embiid games with 2+ blocks since 2021")
        assert parsed["route"] in ("player_game_finder", "player_game_summary")
        assert parsed["route_kwargs"]["stat"] == "blk"
        assert parsed["route_kwargs"]["min_value"] == 2.0


# ===========================================================================
# 5. Leaderboard Build Result Tests (with data)
# ===========================================================================


class TestLeaderboardBuildResult:
    """Test that season_leaders.build_result works for new stats."""

    def test_leaders_steals(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Steal Guy", 100, "AAA", 25, {"stl": 3})
        rows += _make_player_rows(2, "Other Guy", 200, "BBB", 25, {"stl": 1})
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(season="2099-00", stat="stl", limit=5, min_games=1)
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Steal Guy"
        assert "stl_per_game" in result.leaders.columns

    def test_leaders_blocks(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Block Guy", 100, "AAA", 25, {"blk": 4})
        rows += _make_player_rows(2, "Other Guy", 200, "BBB", 25, {"blk": 1})
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(season="2099-00", stat="blk", limit=5, min_games=1)
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Block Guy"

    def test_leaders_turnovers_ascending(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Careful Guy", 100, "AAA", 25, {"tov": 1})
        rows += _make_player_rows(2, "Sloppy Guy", 200, "BBB", 25, {"tov": 5})
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(
            season="2099-00", stat="tov", limit=5, min_games=1, ascending=True
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Careful Guy"

    def test_leaders_plus_minus(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Impact Guy", 100, "AAA", 25, {"plus_minus": 15})
        rows += _make_player_rows(2, "Bench Guy", 200, "BBB", 25, {"plus_minus": -3})
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(season="2099-00", stat="plus_minus", limit=5, min_games=1)
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Impact Guy"
        assert "plus_minus_per_game" in result.leaders.columns

    def test_leaders_steals_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Steal King", 100, "AAA", 25, {"stl": 4}, opponent_abbr="LAL")
        rows += _make_player_rows(2, "Other", 200, "BBB", 25, {"stl": 2}, opponent_abbr="BOS")
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(
            season="2099-00", stat="stl", limit=5, min_games=1, opponent="LAL"
        )
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["player_name"] == "Steal King"

    def test_leaders_blocks_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows1 = _make_player_rows(1, "Block Boss", 100, "AAA", 25, {"blk": 3}, season="2098-99")
        rows2 = _make_player_rows(1, "Block Boss", 100, "AAA", 25, {"blk": 3}, season="2099-00")
        rows3 = _make_player_rows(2, "Other", 200, "BBB", 25, {"blk": 1}, season="2098-99")
        rows4 = _make_player_rows(2, "Other", 200, "BBB", 25, {"blk": 1}, season="2099-00")
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows1 + rows3
        )
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2 + rows4
        )

        result = leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="blk", limit=5, min_games=1
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Block Boss"


# ===========================================================================
# 6. Team Leaderboard Build Result Tests
# ===========================================================================


class TestTeamLeaderboardBuildResult:
    """Test that season_team_leaders.build_result works for new stats."""

    def test_team_leaders_steals(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_team_rows(100, "AAA", "Team A", 25, {"stl": 10})
        rows += _make_team_rows(200, "BBB", "Team B", 25, {"stl": 6})
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

        result = team_leaders_build_result(season="2099-00", stat="stl", limit=5, min_games=1)
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["team_abbr"] == "AAA"
        assert "stl_per_game" in result.leaders.columns

    def test_team_leaders_turnovers_ascending(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_team_rows(100, "AAA", "Team A", 25, {"tov": 8})
        rows += _make_team_rows(200, "BBB", "Team B", 25, {"tov": 15})
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

        result = team_leaders_build_result(
            season="2099-00", stat="tov", limit=5, min_games=1, ascending=True
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["team_abbr"] == "AAA"

    def test_team_leaders_plus_minus(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_team_rows(100, "AAA", "Team A", 25, {"plus_minus": 12})
        rows += _make_team_rows(200, "BBB", "Team B", 25, {"plus_minus": -5})
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

        result = team_leaders_build_result(
            season="2099-00", stat="plus_minus", limit=5, min_games=1
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["team_abbr"] == "AAA"

    def test_team_leaders_blocks_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_team_rows(100, "AAA", "Team A", 25, {"blk": 7}, opponent_abbr="LAL")
        rows += _make_team_rows(200, "BBB", "Team B", 25, {"blk": 4}, opponent_abbr="BOS")
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

        result = team_leaders_build_result(
            season="2099-00", stat="blk", limit=5, min_games=1, opponent="LAL"
        )
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["team_abbr"] == "AAA"


# ===========================================================================
# 7. Finder Stat Filtering Tests
# ===========================================================================


class TestFinderStatFiltering:
    """Test that player_game_finder supports filtering by new stats."""

    def test_finder_steals_threshold(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 20, {"stl": 1})
        # Add some high-steal games
        for i in range(5):
            rows.append(
                {**rows[0], "game_id": 9000 + i, "stl": 4, "game_date": f"2099-11-{(i + 1):02d}"}
            )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00", player="Test Player", stat="stl", min_value=3.0
        )
        assert isinstance(result, FinderResult)
        assert len(result.games) == 5

    def test_finder_blocks_threshold(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 20, {"blk": 0})
        for i in range(3):
            rows.append(
                {**rows[0], "game_id": 9000 + i, "blk": 3, "game_date": f"2099-11-{(i + 1):02d}"}
            )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00", player="Test Player", stat="blk", min_value=2.0
        )
        assert isinstance(result, FinderResult)
        assert len(result.games) == 3

    def test_finder_turnovers_max(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 20, {"tov": 5})
        for i in range(8):
            rows.append(
                {**rows[0], "game_id": 9000 + i, "tov": 1, "game_date": f"2099-11-{(i + 1):02d}"}
            )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00", player="Test Player", stat="tov", max_value=2.0
        )
        assert isinstance(result, FinderResult)
        assert len(result.games) == 8

    def test_finder_plus_minus(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 15, {"plus_minus": -5})
        for i in range(5):
            rows.append(
                {
                    **rows[0],
                    "game_id": 9000 + i,
                    "plus_minus": 15,
                    "game_date": f"2099-11-{(i + 1):02d}",
                }
            )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00", player="Test Player", stat="plus_minus", min_value=10.0
        )
        assert isinstance(result, FinderResult)
        assert len(result.games) == 5


# ===========================================================================
# 8. Summary/Comparison Stat Inclusion Tests
# ===========================================================================


class TestSummaryStatInclusion:
    """Test that summary and comparison outputs include new stats."""

    def test_summary_includes_new_stats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(
            1, "Test Player", 100, "AAA", 20, {"stl": 2, "blk": 1, "tov": 3, "plus_minus": 7}
        )
        _write_player_and_team_csvs(tmp_path, rows)

        result = summary_build_result(season="2099-00", player="Test Player")
        assert isinstance(result, SummaryResult)
        summary = result.summary
        assert "stl_avg" in summary
        assert "blk_avg" in summary
        assert "tov_avg" in summary
        assert "plus_minus_avg" in summary
        assert "efg_pct_avg" in summary
        assert "ts_pct_avg" in summary

    def test_comparison_includes_tov_avg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows_a = _make_player_rows(1, "Player A", 100, "AAA", 20, {"tov": 2})
        rows_b = _make_player_rows(2, "Player B", 200, "BBB", 20, {"tov": 4})
        _write_player_and_team_csvs(tmp_path, rows_a + rows_b)

        result = compare_build_result(player_a="Player A", player_b="Player B", season="2099-00")
        assert isinstance(result, ComparisonResult)
        assert "tov_avg" in result.summary.columns

    def test_comparison_includes_all_new_stats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows_a = _make_player_rows(
            1, "Player A", 100, "AAA", 20, {"stl": 2, "blk": 1, "tov": 3, "plus_minus": 5}
        )
        rows_b = _make_player_rows(
            2, "Player B", 200, "BBB", 20, {"stl": 1, "blk": 2, "tov": 4, "plus_minus": -2}
        )
        _write_player_and_team_csvs(tmp_path, rows_a + rows_b)

        result = compare_build_result(player_a="Player A", player_b="Player B", season="2099-00")
        assert isinstance(result, ComparisonResult)
        for col in ["stl_avg", "blk_avg", "tov_avg", "plus_minus_avg", "efg_pct_avg", "ts_pct_avg"]:
            assert col in result.summary.columns, f"Missing column {col}"


# ===========================================================================
# 9. Historical / Opponent-Filtered Stat Tests
# ===========================================================================


class TestHistoricalOpponentStats:
    """Test stats in historical spans and opponent-filtered contexts."""

    def test_leaders_steals_opponent_filtered(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Thief", 100, "AAA", 25, {"stl": 5}, opponent_abbr="LAL")
        rows += _make_player_rows(2, "Normal", 200, "BBB", 25, {"stl": 1}, opponent_abbr="BOS")
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(
            season="2099-00", stat="stl", limit=5, min_games=1, opponent="LAL"
        )
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["player_name"] == "Thief"
        assert "filtered to games vs LAL" in " ".join(result.caveats)

    def test_leaders_plus_minus_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows1 = _make_player_rows(1, "Star", 100, "AAA", 25, {"plus_minus": 10}, season="2098-99")
        rows2 = _make_player_rows(1, "Star", 100, "AAA", 25, {"plus_minus": 10}, season="2099-00")
        rows3 = _make_player_rows(2, "Bench", 200, "BBB", 25, {"plus_minus": -5}, season="2098-99")
        rows4 = _make_player_rows(2, "Bench", 200, "BBB", 25, {"plus_minus": -5}, season="2099-00")
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows1 + rows3
        )
        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2 + rows4
        )

        result = leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="plus_minus",
            limit=5,
            min_games=1,
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["player_name"] == "Star"

    def test_finder_steals_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 20, {"stl": 4}, opponent_abbr="LAL")
        rows += _make_player_rows(
            1,
            "Test Player",
            100,
            "AAA",
            10,
            {"stl": 0},
            opponent_abbr="BOS",
            start_date="2099-11-01",
        )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00",
            player="Test Player",
            stat="stl",
            min_value=3.0,
            opponent="LAL",
        )
        assert isinstance(result, FinderResult)
        assert len(result.games) == 20


# ===========================================================================
# 10. Structured Query Parity Tests
# ===========================================================================


class TestStructuredQueryParity:
    """Test that structured build_result calls work for all new stats."""

    def test_season_leaders_all_new_stats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(
            1, "Player", 100, "AAA", 25, {"stl": 2, "blk": 1, "tov": 3, "plus_minus": 8}
        )
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        for stat_key in ["stl", "blk", "tov", "plus_minus"]:
            result = leaders_build_result(season="2099-00", stat=stat_key, limit=5, min_games=1)
            assert isinstance(result, LeaderboardResult), f"Failed for stat={stat_key}"

    def test_team_leaders_all_new_stats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_team_rows(
            100, "AAA", "Team A", 25, {"stl": 8, "blk": 5, "tov": 12, "plus_minus": 6}
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows)

        for stat_key in ["stl", "blk", "tov", "plus_minus"]:
            result = team_leaders_build_result(
                season="2099-00", stat=stat_key, limit=5, min_games=1
            )
            assert isinstance(result, LeaderboardResult), f"Failed for stat={stat_key}"

    def test_finder_efg_pct_ts_pct(self, tmp_path, monkeypatch):
        """Test that efg_pct and ts_pct work as finder stats."""
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(
            1,
            "Test Player",
            100,
            "AAA",
            20,
            {
                "fgm": 10,
                "fga": 18,
                "fg3m": 3,
                "ftm": 4,
                "fta": 5,
                "pts": 27,
            },
        )
        _write_player_and_team_csvs(tmp_path, rows)

        result = finder_build_result(
            season="2099-00", player="Test Player", stat="efg_pct", min_value=0.5
        )
        assert isinstance(result, FinderResult)

    def test_summary_with_stat_filter_tov(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Test Player", 100, "AAA", 20, {"tov": 2})
        for i in range(5):
            rows.append(
                {**rows[0], "game_id": 9000 + i, "tov": 6, "game_date": f"2099-11-{(i + 1):02d}"}
            )
        _write_player_and_team_csvs(tmp_path, rows)

        result = summary_build_result(
            season="2099-00", player="Test Player", stat="tov", max_value=3.0
        )
        assert isinstance(result, SummaryResult)
        assert result.summary["games"].iloc[0] == 20


# ===========================================================================
# 11. Leaderboard Caveats Tests
# ===========================================================================


class TestLeaderboardCaveats:
    """Test that caveats are properly generated for filtered leaderboards."""

    def test_opponent_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_rows(1, "Player", 100, "AAA", 25, {"stl": 3}, opponent_abbr="LAL")
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = leaders_build_result(
            season="2099-00", stat="stl", limit=5, min_games=1, opponent="LAL"
        )
        assert isinstance(result, LeaderboardResult)
        assert any("LAL" in c for c in result.caveats)

    def test_multi_season_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows1 = _make_player_rows(1, "Player", 100, "AAA", 25, {"blk": 2}, season="2098-99")
        rows2 = _make_player_rows(1, "Player", 100, "AAA", 25, {"blk": 2}, season="2099-00")
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows1)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        result = leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="blk",
            limit=5,
            min_games=1,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("multi-season" in c for c in result.caveats)
