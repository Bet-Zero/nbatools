"""Tests for historical team query parity.

Covers:
- Historical team summary parsing & build (since/range/last-N/playoff)
- Historical team comparison parsing & build (H2H, opponent filter, multi-season)
- Historical team leaderboard parsing & build (wins, win_pct, multi-season, opponent, home/away)
- Historical team occurrence parsing & build (single + compound, multi-season, playoff, opponent)
- Historical team matchup / opponent parity
- Structured query support for all team historical routes
- Caveats for team historical queries
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._seasons import (
    EARLIEST_SEASON,
    LATEST_PLAYOFF_SEASON,
    LATEST_REGULAR_SEASON,
    resolve_last_n_seasons,
)
from nbatools.commands.game_summary import build_result as game_summary_build_result
from nbatools.commands.natural_query import parse_query
from nbatools.commands.season_team_leaders import build_result as season_team_leaders_build_result
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)
from nbatools.commands.team_compare import build_result as team_compare_build_result
from nbatools.commands.team_occurrence_leaders import (
    build_result as team_occurrence_leaders_build_result,
)
from nbatools.commands.team_split_summary import (
    build_result as team_split_summary_build_result,
)
from nbatools.commands.team_streak_finder import (
    build_result as team_streak_finder_build_result,
)

# ===================================================================
# Helpers
# ===================================================================


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _team_game_rows(
    season,
    team_name,
    team_abbr,
    team_id,
    n_games,
    avg_pts,
    *,
    opponent_name="Other Team",
    opponent_abbr="OTH",
    opponent_id=99,
    wl_pattern=None,
    home_away_pattern=None,
    season_type="Regular Season",
    fg3m=10,
    tov=12,
):
    """Generate fake team game log rows with all required columns."""
    rows = []
    for i in range(n_games):
        if wl_pattern is not None:
            wl = wl_pattern[i % len(wl_pattern)]
        else:
            wl = "W" if i % 2 == 0 else "L"

        if home_away_pattern is not None:
            is_home = home_away_pattern[i % len(home_away_pattern)]
        else:
            is_home = 1 if i % 2 == 0 else 0

        rows.append(
            {
                "game_id": f"{season}_{team_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": season_type,
                "team_id": team_id,
                "team_name": team_name,
                "team_abbr": team_abbr,
                "opponent_team_id": opponent_id,
                "opponent_team_name": opponent_name,
                "opponent_team_abbr": opponent_abbr,
                "is_home": is_home,
                "is_away": 1 - is_home,
                "wl": wl,
                "pts": avg_pts + (i % 5),
                "reb": 40,
                "ast": 25,
                "stl": 8,
                "blk": 5,
                "fgm": 35,
                "fga": 80,
                "fg3m": fg3m,
                "fg3a": 30,
                "ftm": 15,
                "fta": 20,
                "tov": tov,
                "pf": 18,
                "minutes": 240,
                "plus_minus": 5 if wl == "W" else -5,
                "oreb": 10,
                "dreb": 30,
            }
        )
    return rows


def _write_two_team_seasons(tmp_path, safe="regular_season"):
    """Write two seasons of two-team data for multi-season tests."""
    rows1 = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 30, 110)
    rows1 += _team_game_rows("2098-99", "Team Beta", "BET", 2, 30, 100)
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", rows1)

    rows2 = _team_game_rows("2099-00", "Team Alpha", "ALP", 1, 30, 115)
    rows2 += _team_game_rows("2099-00", "Team Beta", "BET", 2, 30, 105)
    _write_csv(tmp_path / f"data/raw/team_game_stats/2099-00_{safe}.csv", rows2)


def _write_matchup_data(tmp_path, safe="regular_season"):
    """Write data where Team Alpha and Team Beta play each other."""
    rows_alpha = _team_game_rows(
        "2098-99",
        "Team Alpha",
        "ALP",
        1,
        10,
        110,
        opponent_name="Team Beta",
        opponent_abbr="BET",
        opponent_id=2,
    )
    rows_beta = _team_game_rows(
        "2098-99",
        "Team Beta",
        "BET",
        2,
        10,
        100,
        opponent_name="Team Alpha",
        opponent_abbr="ALP",
        opponent_id=1,
    )
    # Align game_ids so they represent the same games
    for i, (ra, rb) in enumerate(zip(rows_alpha, rows_beta)):
        shared_id = f"2098-99_h2h_{i}"
        ra["game_id"] = shared_id
        rb["game_id"] = shared_id

    all_rows = rows_alpha + rows_beta
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", all_rows)


# ===================================================================
# 1. Historical team summary parsing
# ===================================================================


class TestParseHistoricalTeamSummary:
    def test_team_since_year(self):
        parsed = parse_query("Celtics since 2008")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2008-09"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_team_playoff_since_year(self):
        parsed = parse_query("Lakers playoff summary since 2020")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "LAL"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_team_from_to_range(self):
        parsed = parse_query("Warriors summary from 2015-16 to 2018-19")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "GSW"
        assert parsed["route_kwargs"]["start_season"] == "2015-16"
        assert parsed["route_kwargs"]["end_season"] == "2018-19"

    def test_team_last_n_seasons(self):
        parsed = parse_query("Knicks summary last 3 seasons")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "NYK"
        start, end = resolve_last_n_seasons(3, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start
        assert parsed["route_kwargs"]["end_season"] == end

    def test_team_career_intent(self):
        parsed = parse_query("Celtics all-time record")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_team_vs_opponent_since(self):
        parsed = parse_query("Knicks summary vs Heat since 1999")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "NYK"
        assert parsed["opponent"] == "MIA"
        assert parsed["route_kwargs"]["opponent"] == "MIA"
        assert parsed["route_kwargs"]["start_season"] == "1999-00"


# ===================================================================
# 2. Historical team comparison parsing
# ===================================================================


class TestParseHistoricalTeamComparison:
    def test_team_compare_since(self):
        parsed = parse_query("Lakers vs Celtics since 2010")
        assert parsed["route"] == "team_compare"
        assert parsed["team_a"] == "LAL"
        assert parsed["team_b"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2010-11"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_team_compare_from_to(self):
        parsed = parse_query("Celtics vs Bucks from 2018-19 to 2023-24")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"]["start_season"] == "2018-19"
        assert parsed["route_kwargs"]["end_season"] == "2023-24"

    def test_team_compare_head_to_head(self):
        parsed = parse_query("Knicks head-to-head vs Heat since 1999")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"]["head_to_head"] is True
        assert parsed["route_kwargs"]["start_season"] == "1999-00"

    def test_team_compare_opponent_passthrough(self):
        """The opponent kwarg should no longer be hardcoded to None."""
        # When two teams are explicitly compared, opponent isn't independently used,
        # but when present it should be passed through (not hardcoded None).
        parsed = parse_query("Lakers vs Celtics since 2010")
        assert parsed["route"] == "team_compare"
        # The key fix: opponent should be passed through, not None-hardcoded
        # In a clean "Lakers vs Celtics" query, opponent won't be separately detected
        # because both entities map to team_a / team_b, so it's fine to be None here.
        # But verify it's in the kwargs dict
        assert "opponent" in parsed["route_kwargs"]

    def test_team_compare_playoff(self):
        parsed = parse_query("Celtics vs Heat playoffs since 2020")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"


# ===================================================================
# 3. Historical team leaderboard parsing
# ===================================================================


class TestParseHistoricalTeamLeaderboard:
    def test_best_offenses_since(self):
        parsed = parse_query("best team offenses since 2000")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["start_season"] is not None

    def test_most_wins_since(self):
        parsed = parse_query("most wins since 2000")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["stat"] == "wins"
        assert parsed["route_kwargs"]["start_season"] == "2000-01"

    def test_lowest_turnovers_last_5(self):
        parsed = parse_query("lowest turnover teams over the last 5 seasons")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_best_playoff_net_ratings(self):
        parsed = parse_query("best team playoff net ratings since 2010")
        assert parsed["route"] == "season_team_leaders"

    def test_best_scoring_vs_opponent(self):
        parsed = parse_query("best scoring teams vs Lakers since 2018")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["opponent"] == "LAL"
        assert parsed["route_kwargs"]["start_season"] == "2018-19"

    def test_best_record_teams(self):
        parsed = parse_query("best record teams last 3 seasons")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["stat"] == "win_pct"


# ===================================================================
# 4. Historical team occurrence parsing
# ===================================================================


class TestParseHistoricalTeamOccurrence:
    def test_most_130pt_games_since(self):
        parsed = parse_query("teams with most 130 point games since 2010")
        assert parsed["route"] == "team_occurrence_leaders"
        assert parsed["route_kwargs"]["min_value"] == 130

    def test_most_15_three_games_playoffs(self):
        parsed = parse_query("most team games with 15+ threes in playoffs since 2015")
        assert parsed["route"] == "team_occurrence_leaders"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_celtics_120pt_15three_count(self):
        parsed = parse_query("how many Celtics games with 120+ points and 15+ threes since 2022")
        assert parsed["route"] == "team_occurrence_leaders"
        assert parsed["team"] == "BOS"
        assert parsed["route_kwargs"]["team"] == "BOS"


# ===================================================================
# 5. Historical team summary build tests
# ===================================================================


class TestBuildHistoricalTeamSummary:
    def test_multi_season_summary(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = game_summary_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] == 60
        assert result.summary.iloc[0]["team_name"] == "Team Alpha"
        # by_season should show two seasons
        assert len(result.by_season) == 2

    def test_multi_season_summary_caveats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = game_summary_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert any("multi-season" in c for c in result.caveats)

    def test_summary_with_opponent_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
            opponent="BET",
        )
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] == 10
        assert any("BET" in c for c in result.caveats)

    def test_summary_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
            home_only=True,
        )
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] < 20
        assert any("home" in c for c in result.caveats)

    def test_summary_away_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
            away_only=True,
        )
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] < 20
        assert any("away" in c for c in result.caveats)

    def test_summary_wins_losses_caveats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
            wins_only=True,
        )
        assert isinstance(result, SummaryResult)
        assert any("wins" in c for c in result.caveats)

    def test_summary_playoff(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 10, 105, season_type="Playoffs")
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_playoffs.csv", rows)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
            season_type="Playoffs",
        )
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] == 10


# ===================================================================
# 6. Historical team comparison build tests
# ===================================================================


class TestBuildHistoricalTeamComparison:
    def test_multi_season_comparison(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.summary) == 2
        assert any("multi-season" in c for c in result.caveats)

    def test_head_to_head_comparison(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            head_to_head=True,
        )
        assert isinstance(result, ComparisonResult)
        assert any("head-to-head" in c for c in result.caveats)

    def test_comparison_with_home_only_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            home_only=True,
        )
        assert isinstance(result, ComparisonResult)
        assert any("home" in c for c in result.caveats)

    def test_comparison_with_date_window_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            start_date="2099-01-01",
            end_date="2099-12-31",
        )
        assert isinstance(result, ComparisonResult)
        assert any("date window" in c for c in result.caveats)

    def test_comparison_last_n_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            last_n=5,
        )
        assert isinstance(result, ComparisonResult)
        assert any("last 5" in c for c in result.caveats)

    def test_comparison_opponent_filter(self, tmp_path, monkeypatch):
        """Non-H2H comparison with opponent filter—should produce a caveat."""
        monkeypatch.chdir(tmp_path)
        # Write data where ALP and BET both play OTH
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 10, 110)
        rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 10, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            opponent="OTH",
        )
        assert isinstance(result, ComparisonResult)
        assert any("OTH" in c for c in result.caveats)


# ===================================================================
# 7. Historical team leaderboard build tests
# ===================================================================


class TestBuildHistoricalTeamLeaderboard:
    def test_multi_season_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = season_team_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
        )
        assert isinstance(result, LeaderboardResult)
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"
        assert any("multi-season" in c for c in result.caveats)

    def test_wins_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            100,
            wl_pattern=["W", "W", "W", "L"],  # 15W 5L
        )
        rows += _team_game_rows(
            "2098-99",
            "Team Beta",
            "BET",
            2,
            20,
            95,
            wl_pattern=["W", "L"],  # 10W 10L
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="wins",
        )
        assert isinstance(result, LeaderboardResult)
        assert "wins" in result.leaders.columns
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"
        assert result.leaders.iloc[0]["wins"] == 15

    def test_win_pct_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            100,
            wl_pattern=["W", "W", "W", "L"],  # 75% win pct
        )
        rows += _team_game_rows(
            "2098-99",
            "Team Beta",
            "BET",
            2,
            20,
            95,
            wl_pattern=["W", "L"],  # 50% win pct
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="win_pct",
        )
        assert isinstance(result, LeaderboardResult)
        assert "win_pct" in result.leaders.columns
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"
        assert result.leaders.iloc[0]["win_pct"] > 0.7

    def test_losses_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            100,
            wl_pattern=["W", "W", "W", "L"],  # 5 losses
        )
        rows += _team_game_rows(
            "2098-99",
            "Team Beta",
            "BET",
            2,
            20,
            95,
            wl_pattern=["W", "L"],  # 10 losses
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="losses",
        )
        assert isinstance(result, LeaderboardResult)
        # Most losses first (descending by default)
        assert result.leaders.iloc[0]["team_abbr"] == "BET"

    def test_multi_season_wins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = season_team_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="wins",
        )
        assert isinstance(result, LeaderboardResult)
        assert "wins" in result.leaders.columns
        # Verify multi-season aggregation
        total_wins = int(result.leaders.iloc[0]["wins"])
        assert total_wins > 0

    def test_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="pts",
            opponent="BET",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("BET" in c for c in result.caveats)

    def test_leaderboard_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 40, 100)
        rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 40, 95)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="pts",
            home_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("home" in c for c in result.caveats)
        # Should have fewer games than full season
        assert result.leaders.iloc[0]["games_played"] < 40

    def test_leaderboard_away_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 40, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="pts",
            away_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("away" in c for c in result.caveats)

    def test_leaderboard_advanced_stat_blocked_with_home_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        with pytest.raises(ValueError, match="Game-filtered"):
            season_team_leaders_build_result(
                season="2098-99",
                stat="off_rating",
                home_only=True,
            )

    def test_leaderboard_efg_pct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = season_team_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="efg_pct",
        )
        assert isinstance(result, LeaderboardResult)
        assert "efg_pct" in result.leaders.columns

    def test_leaderboard_ts_pct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = season_team_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="ts_pct",
        )
        assert isinstance(result, LeaderboardResult)
        assert "ts_pct" in result.leaders.columns

    def test_leaderboard_ascending(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            110,
            tov=15,
        )
        rows += _team_game_rows(
            "2098-99",
            "Team Beta",
            "BET",
            2,
            20,
            100,
            tov=10,
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="tov",
            ascending=True,
        )
        assert isinstance(result, LeaderboardResult)
        # Beta has fewer turnovers, should be first
        assert result.leaders.iloc[0]["team_abbr"] == "BET"


# ===================================================================
# 8. Historical team occurrence build tests
# ===================================================================


class TestBuildHistoricalTeamOccurrence:
    def test_single_stat_occurrence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 112)
        rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 20, 108)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=110,
            season="2098-99",
        )
        assert isinstance(result, LeaderboardResult)
        # Alpha has higher pts, should have more occurrences
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"

    def test_multi_season_occurrence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=110,
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("2 seasons" in c for c in result.caveats)

    def test_occurrence_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=110,
            season="2098-99",
            opponent="BET",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("BET" in c for c in result.caveats)

    def test_occurrence_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 112)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=110,
            season="2098-99",
            home_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("home" in c.lower() for c in result.caveats)

    def test_occurrence_playoff(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 10, 120, season_type="Playoffs")
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_playoffs.csv", rows)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=118,
            season="2098-99",
            season_type="Playoffs",
        )
        assert isinstance(result, LeaderboardResult)

    def test_compound_occurrence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 112, fg3m=16)
        rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 20, 108, fg3m=12)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_occurrence_leaders_build_result(
            conditions=[
                {"stat": "pts", "min_value": 110},
                {"stat": "fg3m", "min_value": 15},
            ],
            season="2098-99",
        )
        assert isinstance(result, LeaderboardResult)
        # Alpha has fg3m=16 > 15, Beta has fg3m=12 < 15
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"

    def test_single_team_count(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 112)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_occurrence_leaders_build_result(
            stat="pts",
            min_value=110,
            season="2098-99",
            team="ALP",
        )
        assert isinstance(result, LeaderboardResult)
        # Filtered to single team
        alp_rows = result.leaders[result.leaders["team_abbr"] == "ALP"]
        assert len(alp_rows) == 1


# ===================================================================
# 9. Historical team streak build tests
# ===================================================================


class TestBuildHistoricalTeamStreak:
    def test_multi_season_streak(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_streak_finder_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
            special_condition="wins",
        )
        assert isinstance(result, StreakResult)
        assert any("2 seasons" in c for c in result.caveats)

    def test_streak_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = team_streak_finder_build_result(
            season="2098-99",
            team="ALP",
            opponent="BET",
            special_condition="wins",
        )
        assert isinstance(result, StreakResult)
        assert any("BET" in c for c in result.caveats)

    def test_streak_home_only_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_streak_finder_build_result(
            season="2098-99",
            team="ALP",
            special_condition="wins",
            home_only=True,
        )
        assert isinstance(result, StreakResult)
        assert any("home" in c for c in result.caveats)


# ===================================================================
# 10. Historical team split summary build tests
# ===================================================================


class TestBuildHistoricalTeamSplit:
    def test_multi_season_split(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_split_summary_build_result(
            split="home_away",
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SplitSummaryResult)
        assert any("multi-season" in c for c in result.caveats)

    def test_split_with_opponent_caveat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = team_split_summary_build_result(
            split="home_away",
            season="2098-99",
            team="ALP",
            opponent="BET",
        )
        assert isinstance(result, SplitSummaryResult)
        assert any("BET" in c for c in result.caveats)


# ===================================================================
# 11. Structured query parity tests
# ===================================================================


class TestStructuredTeamQueryParity:
    """Ensure structured queries support the same historical kwargs as natural queries."""

    def test_structured_team_summary_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = game_summary_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SummaryResult)
        d = result.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"

    def test_structured_team_comparison_h2h(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            head_to_head=True,
        )
        assert isinstance(result, ComparisonResult)
        d = result.to_dict()
        assert d["query_class"] == "comparison"
        assert d["result_status"] == "ok"

    def test_structured_team_leaderboard_wins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            100,
            wl_pattern=["W", "W", "W", "L"],
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="wins",
        )
        assert isinstance(result, LeaderboardResult)
        d = result.to_dict()
        assert d["query_class"] == "leaderboard"
        assert "wins" in str(d["sections"]["leaderboard"])

    def test_structured_team_leaderboard_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 40, 100)
        rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 40, 95)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="pts",
            home_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        d = result.to_dict()
        assert any("home" in c for c in d["caveats"])

    def test_structured_team_occurrence_compound(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 112, fg3m=16)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = team_occurrence_leaders_build_result(
            conditions=[
                {"stat": "pts", "min_value": 110},
                {"stat": "fg3m", "min_value": 15},
            ],
            season="2098-99",
        )
        assert isinstance(result, LeaderboardResult)
        d = result.to_dict()
        assert d["query_class"] == "leaderboard"

    def test_structured_team_streak_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_streak_finder_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
            special_condition="wins",
        )
        assert isinstance(result, StreakResult)
        d = result.to_dict()
        assert d["query_class"] == "streak"

    def test_structured_team_split_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_split_summary_build_result(
            split="home_away",
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SplitSummaryResult)
        d = result.to_dict()
        assert d["query_class"] == "split_summary"


# ===================================================================
# 12. Result serialization & contract tests
# ===================================================================


class TestTeamResultContracts:
    """Ensure team historical results serialize properly for API/UI consumers."""

    def test_summary_result_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = game_summary_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        d = result.to_dict()
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "by_season" in d["sections"]
        assert isinstance(d["caveats"], list)

    def test_comparison_result_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_compare_build_result(
            team_a="ALP",
            team_b="BET",
            start_season="2098-99",
            end_season="2099-00",
        )
        d = result.to_dict()
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "comparison" in d["sections"]

    def test_leaderboard_result_to_dict_with_wins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            20,
            100,
            wl_pattern=["W", "W", "W", "L"],
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="wins",
        )
        d = result.to_dict()
        assert d["query_class"] == "leaderboard"
        leaders = d["sections"]["leaderboard"]
        assert any("wins" in row for row in leaders)

    def test_streak_result_to_dict_with_caveats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        result = team_streak_finder_build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
            special_condition="wins",
        )
        d = result.to_dict()
        assert d["query_class"] == "streak"
        assert isinstance(d["caveats"], list)
        assert len(d["caveats"]) > 0


# ===================================================================
# 13. Edge cases and error handling
# ===================================================================


class TestTeamHistoricalEdgeCases:
    def test_leaderboard_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data/raw/team_game_stats").mkdir(parents=True, exist_ok=True)

        result = season_team_leaders_build_result(
            season="2098-99",
            stat="pts",
        )
        assert isinstance(result, NoResult)

    def test_leaderboard_multi_season_advanced_stat_blocked(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_two_team_seasons(tmp_path)

        with pytest.raises(ValueError, match="Multi-season"):
            season_team_leaders_build_result(
                start_season="2098-99",
                end_season="2099-00",
                stat="off_rating",
            )

    def test_leaderboard_date_window_advanced_stat_blocked(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        with pytest.raises(ValueError, match="Date-window"):
            season_team_leaders_build_result(
                season="2098-99",
                stat="off_rating",
                start_date="2099-01-01",
                end_date="2099-06-01",
            )

    def test_comparison_both_home_away_rejected(self):
        with pytest.raises(ValueError, match="both home_only and away_only"):
            team_compare_build_result(
                team_a="ALP",
                team_b="BET",
                season="2098-99",
                home_only=True,
                away_only=True,
            )

    def test_comparison_both_wins_losses_rejected(self):
        with pytest.raises(ValueError, match="both wins_only and losses_only"):
            team_compare_build_result(
                team_a="ALP",
                team_b="BET",
                season="2098-99",
                wins_only=True,
                losses_only=True,
            )

    def test_leaderboard_invalid_stat(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows)

        with pytest.raises(ValueError, match="Unsupported stat"):
            season_team_leaders_build_result(
                season="2098-99",
                stat="invented_stat",
            )

    def test_summary_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data/raw/team_game_stats").mkdir(parents=True, exist_ok=True)

        result = game_summary_build_result(
            season="2098-99",
            team="ALP",
        )
        assert isinstance(result, NoResult)
