"""Tests for advanced metric query/filter/ranking support.

Covers:
- metric_registry validity and guardrails
- stat alias expansion (_constants.py)
- leaderboard routing for advanced metrics (natural query)
- leaderboard ranking by advanced metrics (season_leaders)
- summary/comparison inclusion (tov_pct added)
- finder/filter support for advanced metrics
- blocked/guardrailed invalid contexts
- structured query support via season_leaders
- service/API compatibility
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN
from nbatools.commands.metric_registry import (
    GAME_LOG_DERIVABLE,
    METRIC_REGISTRY,
    SEASON_ADVANCED_ONLY,
    MetricGrain,
    MetricSource,
    blocked_leaderboard_reason,
    is_metric_valid_for_context,
    leaderboard_grain,
    metric_caveat,
)
from nbatools.commands.natural_query import (
    detect_player_leaderboard_stat,
    detect_stat,
    detect_team_leaderboard_stat,
    extract_threshold_conditions,
    parse_query,
    wants_ascending_leaderboard,
    wants_leaderboard,
)
from nbatools.commands.player_advanced_metrics import (
    compute_sample_advanced_metrics,
    compute_sample_tov_pct,
)

pytestmark = pytest.mark.engine

# ── metric_registry ──────────────────────────────────────────────────


class TestMetricRegistry:
    """Ensure the metric capability map is coherent."""

    def test_all_metrics_have_valid_grains(self) -> None:
        for name, desc in METRIC_REGISTRY.items():
            assert desc.valid_grains, f"{name} has no valid grains"

    def test_box_score_metrics_valid_everywhere(self) -> None:
        for name, desc in METRIC_REGISTRY.items():
            if desc.source == MetricSource.BOX_SCORE:
                assert MetricGrain.GAME in desc.valid_grains
                assert MetricGrain.SEASON in desc.valid_grains
                assert MetricGrain.MULTI_SEASON in desc.valid_grains

    def test_season_advanced_only_not_multi_season(self) -> None:
        for name in SEASON_ADVANCED_ONLY:
            desc = METRIC_REGISTRY[name]
            assert MetricGrain.MULTI_SEASON not in desc.valid_grains, (
                f"{name} should not be valid at multi-season"
            )

    def test_game_log_derived_valid_at_sample_and_multi(self) -> None:
        for name, desc in METRIC_REGISTRY.items():
            if desc.source == MetricSource.GAME_LOG_DERIVED:
                assert MetricGrain.FILTERED_SAMPLE in desc.valid_grains
                assert MetricGrain.MULTI_SEASON in desc.valid_grains

    def test_usg_pct_player_only(self) -> None:
        desc = METRIC_REGISTRY["usg_pct"]
        assert desc.player is True
        assert desc.team is False

    def test_pace_team_only(self) -> None:
        desc = METRIC_REGISTRY["pace"]
        assert desc.player is False
        assert desc.team is True

    def test_off_rating_season_only(self) -> None:
        assert is_metric_valid_for_context("off_rating", grain=MetricGrain.SEASON, is_player=True)
        assert not is_metric_valid_for_context(
            "off_rating", grain=MetricGrain.MULTI_SEASON, is_player=True
        )

    def test_def_rating_lower_is_better(self) -> None:
        assert METRIC_REGISTRY["def_rating"].higher_is_better is False

    def test_tov_pct_lower_is_better(self) -> None:
        assert METRIC_REGISTRY["tov_pct"].higher_is_better is False


class TestBlockedLeaderboard:
    """blocked_leaderboard_reason should catch invalid metric/context combos."""

    def test_off_rating_blocked_multi_season(self) -> None:
        reason = blocked_leaderboard_reason("off_rating", multi_season=True)
        assert reason is not None
        assert "multi-season" in reason

    def test_off_rating_blocked_date_window(self) -> None:
        reason = blocked_leaderboard_reason("off_rating", date_window=True)
        assert reason is not None

    def test_usg_pct_allowed_multi_season(self) -> None:
        reason = blocked_leaderboard_reason("usg_pct", multi_season=True)
        assert reason is None

    def test_usg_pct_allowed_opponent_filtered(self) -> None:
        reason = blocked_leaderboard_reason("usg_pct", opponent_filtered=True)
        assert reason is None

    def test_pace_blocked_for_player(self) -> None:
        reason = blocked_leaderboard_reason("pace", is_player=True)
        assert reason is not None

    def test_efg_pct_allowed_everywhere(self) -> None:
        for multi, date_win, opp in [
            (True, False, False),
            (False, True, False),
            (False, False, True),
            (True, True, True),
        ]:
            reason = blocked_leaderboard_reason(
                "efg_pct",
                multi_season=multi,
                date_window=date_win,
                opponent_filtered=opp,
            )
            assert reason is None, f"efg_pct should be allowed everywhere, got: {reason}"

    def test_unknown_metric(self) -> None:
        reason = blocked_leaderboard_reason("fake_stat", is_player=True)
        assert reason is not None


class TestMetricCaveat:
    def test_usg_pct_sample_caveat(self) -> None:
        caveat = metric_caveat("usg_pct", grain=MetricGrain.FILTERED_SAMPLE)
        assert caveat is not None
        assert "recomputed" in caveat

    def test_efg_pct_no_caveat_at_season(self) -> None:
        assert metric_caveat("efg_pct", grain=MetricGrain.SEASON) is None


class TestLeaderboardGrain:
    def test_single_season(self) -> None:
        assert (
            leaderboard_grain(multi_season=False, date_window=False, opponent_filtered=False)
            == MetricGrain.SEASON
        )

    def test_multi_season(self) -> None:
        assert (
            leaderboard_grain(multi_season=True, date_window=False, opponent_filtered=False)
            == MetricGrain.MULTI_SEASON
        )

    def test_date_window(self) -> None:
        assert (
            leaderboard_grain(multi_season=False, date_window=True, opponent_filtered=False)
            == MetricGrain.FILTERED_SAMPLE
        )

    def test_opponent(self) -> None:
        assert (
            leaderboard_grain(multi_season=False, date_window=False, opponent_filtered=True)
            == MetricGrain.FILTERED_SAMPLE
        )


# ── STAT_ALIASES ─────────────────────────────────────────────────────


class TestStatAliases:
    """Ensure advanced metrics are properly aliased."""

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("usage rate", "usg_pct"),
            ("usage", "usg_pct"),
            ("usg%", "usg_pct"),
            ("usg_pct", "usg_pct"),
            ("assist percentage", "ast_pct"),
            ("ast%", "ast_pct"),
            ("rebound percentage", "reb_pct"),
            ("reb%", "reb_pct"),
            ("turnover percentage", "tov_pct"),
            ("turnover rate", "tov_pct"),
            ("tov%", "tov_pct"),
            ("offensive rating", "off_rating"),
            ("defensive rating", "def_rating"),
            ("net rating", "net_rating"),
            ("pace", "pace"),
            ("fg%", "fg_pct"),
            ("fg_pct", "fg_pct"),
            ("ft%", "ft_pct"),
            ("3pt%", "fg3_pct"),
        ],
    )
    def test_alias_mapping(self, alias: str, canonical: str) -> None:
        assert STAT_ALIASES.get(alias) == canonical, (
            f"STAT_ALIASES[{alias!r}] should be {canonical!r}"
        )


class TestStatPattern:
    """STAT_PATTERN regex should match advanced metric phrases."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "usage rate",
            "usage",
            "usg%",
            "assist percentage",
            "ast%",
            "rebound percentage",
            "reb%",
            "turnover percentage",
            "tov%",
            "turnover rate",
            "offensive rating",
            "defensive rating",
            "net rating",
            "pace",
            "fg_pct",
            "fg3_pct",
            "ft_pct",
        ],
    )
    def test_pattern_matches(self, phrase: str) -> None:
        assert re.search(STAT_PATTERN, phrase, re.IGNORECASE), (
            f"STAT_PATTERN should match {phrase!r}"
        )


# ── Natural query routing ───────────────────────────────────────────


class TestNaturalQueryAdvancedMetricRouting:
    """Test NQ parser routes advanced metric leaderboard queries correctly."""

    def test_highest_usage_rate_routes_to_season_leaders(self) -> None:
        parsed = parse_query("highest usage rate this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "usg_pct"

    def test_best_assist_percentage_multi_season(self) -> None:
        parsed = parse_query("best assist percentage last 3 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "ast_pct"

    def test_lowest_turnover_percentage(self) -> None:
        parsed = parse_query("lowest turnover percentage this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "tov_pct"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_best_rebound_percentage_playoffs(self) -> None:
        parsed = parse_query("best rebound percentage in playoffs since 2015")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "reb_pct"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_net_rating_teams(self) -> None:
        parsed = parse_query("best net rating teams")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "net_rating"

    def test_fastest_teams(self) -> None:
        parsed = parse_query("fastest teams this season")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "pace"

    def test_best_defense_teams(self) -> None:
        parsed = parse_query("best defense teams")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "def_rating"

    def test_off_rating_blocked_multi_season_team(self) -> None:
        """Team off_rating should fall back to pts for multi-season."""
        parsed = parse_query("best offensive teams last 3 seasons")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "pts"
        notes = parsed.get("notes", [])
        assert any("stat_fallback" in n for n in notes)

    def test_usg_pct_allowed_multi_season_player(self) -> None:
        """Player USG% should NOT fall back for multi-season — it's game-log-derivable."""
        parsed = parse_query("highest usage rate last 3 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "usg_pct"
        notes = parsed.get("notes", [])
        assert not any("stat_fallback" in n for n in notes)


class TestNaturalQueryThresholdParsing:
    """Test threshold extraction for advanced metric filter conditions."""

    def test_ts_pct_over_threshold(self) -> None:
        conditions = extract_threshold_conditions("ts% over .700")
        assert len(conditions) >= 1
        matching = [c for c in conditions if c["stat"] == "ts_pct"]
        assert matching
        assert matching[0]["min_value"] > 0.700

    def test_usage_rate_over_threshold(self) -> None:
        conditions = extract_threshold_conditions("usage rate over 30")
        assert len(conditions) >= 1
        matching = [c for c in conditions if c["stat"] == "usg_pct"]
        assert matching

    def test_tov_pct_under_threshold(self) -> None:
        conditions = extract_threshold_conditions("tov% under 10")
        assert len(conditions) >= 1
        matching = [c for c in conditions if c["stat"] == "tov_pct"]
        assert matching
        assert matching[0]["max_value"] is not None


class TestDetectStats:
    """detect_stat and leaderboard stat detection for advanced metrics."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("usage rate", "usg_pct"),
            ("ast%", "ast_pct"),
            ("reb%", "reb_pct"),
            ("tov%", "tov_pct"),
        ],
    )
    def test_detect_stat_advanced(self, text: str, expected: str) -> None:
        assert detect_stat(text) == expected

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("usage rate", "usg_pct"),
            ("usage", "usg_pct"),
            ("usg%", "usg_pct"),
            ("assist percentage", "ast_pct"),
            ("rebound percentage", "reb_pct"),
            ("turnover percentage", "tov_pct"),
            ("offensive rating", "off_rating"),
            ("net rating", "net_rating"),
        ],
    )
    def test_detect_player_leaderboard_stat(self, text: str, expected: str) -> None:
        result = detect_player_leaderboard_stat(text)
        assert result == expected, f"Expected {expected}, got {result} for '{text}'"

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("best defense", "def_rating"),
            ("best net rating teams", "net_rating"),
            ("defensive rating", "def_rating"),
            ("pace", "pace"),
        ],
    )
    def test_detect_team_leaderboard_stat(self, text: str, expected: str) -> None:
        result = detect_team_leaderboard_stat(text)
        assert result == expected


# ── Player advanced metrics computation ──────────────────────────────


class TestTovPctComputation:
    """Turnover percentage computation from sample data."""

    def test_basic_tov_pct(self) -> None:
        df = pd.DataFrame(
            {
                "fga": [10, 15],
                "fta": [5, 8],
                "tov": [3, 4],
            }
        )
        result = compute_sample_tov_pct(df)
        assert result is not None
        # TOV% = 100 * 7 / (25 + 0.44*13 + 7) = 100 * 7 / 37.72 ≈ 18.559
        assert 18.0 < result < 19.5

    def test_empty_returns_none(self) -> None:
        df = pd.DataFrame(columns=["fga", "fta", "tov"])
        assert compute_sample_tov_pct(df) is None


class TestSampleAdvancedMetricsIncludesTovPct:
    """compute_sample_advanced_metrics should include tov_pct_avg."""

    def test_includes_tov_pct_avg(self) -> None:
        df = pd.DataFrame(
            {
                "fga": [10],
                "fta": [5],
                "tov": [3],
                "minutes": [30],
                "ast": [5],
                "fgm": [4],
                "reb": [7],
                "team_fga": [80],
                "team_fta": [20],
                "team_tov": [15],
                "team_minutes": [240],
                "team_fgm": [35],
                "team_reb": [40],
                "opp_reb": [38],
            }
        )
        metrics = compute_sample_advanced_metrics(df)
        assert "tov_pct_avg" in metrics
        assert metrics["tov_pct_avg"] is not None


# ── Season leaders ALLOWED_STATS ─────────────────────────────────────


class TestSeasonLeadersAllowedStats:
    """season_leaders.py should accept advanced metric stat names."""

    def test_usg_pct_in_allowed(self) -> None:
        from nbatools.commands.season_leaders import ALLOWED_STATS

        assert "usg_pct" in ALLOWED_STATS or "usg%" in ALLOWED_STATS

    def test_ast_pct_in_allowed(self) -> None:
        from nbatools.commands.season_leaders import ALLOWED_STATS

        assert "ast_pct" in ALLOWED_STATS or "ast%" in ALLOWED_STATS

    def test_reb_pct_in_allowed(self) -> None:
        from nbatools.commands.season_leaders import ALLOWED_STATS

        assert "reb_pct" in ALLOWED_STATS or "reb%" in ALLOWED_STATS

    def test_tov_pct_in_allowed(self) -> None:
        from nbatools.commands.season_leaders import ALLOWED_STATS

        assert "tov_pct" in ALLOWED_STATS or "tov%" in ALLOWED_STATS


class TestSeasonLeadersGuardrails:
    """Season leaders should block season-advanced-only stats in multi/date/opp context."""

    def test_off_rating_blocked_multi_season(self) -> None:
        from nbatools.commands.season_leaders import DATE_WINDOW_UNSUPPORTED_ADVANCED

        assert "off_rating" in DATE_WINDOW_UNSUPPORTED_ADVANCED

    def test_def_rating_blocked_multi_season(self) -> None:
        from nbatools.commands.season_leaders import DATE_WINDOW_UNSUPPORTED_ADVANCED

        assert "def_rating" in DATE_WINDOW_UNSUPPORTED_ADVANCED

    def test_net_rating_blocked_multi_season(self) -> None:
        from nbatools.commands.season_leaders import DATE_WINDOW_UNSUPPORTED_ADVANCED

        assert "net_rating" in DATE_WINDOW_UNSUPPORTED_ADVANCED

    def test_usg_pct_not_blocked(self) -> None:
        from nbatools.commands.season_leaders import DATE_WINDOW_UNSUPPORTED_ADVANCED

        assert "usg_pct" not in DATE_WINDOW_UNSUPPORTED_ADVANCED

    def test_tov_pct_not_blocked(self) -> None:
        from nbatools.commands.season_leaders import DATE_WINDOW_UNSUPPORTED_ADVANCED

        assert "tov_pct" not in DATE_WINDOW_UNSUPPORTED_ADVANCED


# ── Finder ALLOWED_STATS ────────────────────────────────────────────


class TestFinderAllowedStats:
    """Finder modules should accept advanced metric stat names."""

    def test_player_finder_tov_pct(self) -> None:
        from nbatools.commands.player_game_finder import ALLOWED_STATS

        assert "tov_pct" in ALLOWED_STATS

    def test_player_finder_usg_pct(self) -> None:
        from nbatools.commands.player_game_finder import ALLOWED_STATS

        assert "usg_pct" in ALLOWED_STATS

    def test_team_finder_fg_pct(self) -> None:
        from nbatools.commands.game_finder import ALLOWED_STATS

        assert "fg_pct" in ALLOWED_STATS

    def test_team_finder_fg3_pct(self) -> None:
        from nbatools.commands.game_finder import ALLOWED_STATS

        assert "fg3_pct" in ALLOWED_STATS

    def test_team_finder_ft_pct(self) -> None:
        from nbatools.commands.game_finder import ALLOWED_STATS

        assert "ft_pct" in ALLOWED_STATS


# ── data_utils percentage columns ───────────────────────────────────


class TestAddAdvancedPctColumns:
    """add_advanced_pct_columns should compute new pct columns."""

    def test_tov_pct_computed(self) -> None:
        from nbatools.commands.data_utils import add_advanced_pct_columns

        df = pd.DataFrame(
            {
                "fgm": [5],
                "fga": [10],
                "fg3m": [2],
                "fg3a": [5],
                "ftm": [3],
                "fta": [4],
                "pts": [15],
                "tov": [3],
            }
        )
        result = add_advanced_pct_columns(df)
        assert "tov_pct" in result.columns
        assert result["tov_pct"].iloc[0] > 0

    def test_fg_pct_computed(self) -> None:
        from nbatools.commands.data_utils import add_advanced_pct_columns

        df = pd.DataFrame(
            {
                "fgm": [5],
                "fga": [10],
                "fg3m": [2],
                "fg3a": [5],
                "ftm": [3],
                "fta": [4],
                "pts": [15],
                "tov": [3],
            }
        )
        result = add_advanced_pct_columns(df)
        assert "fg_pct" in result.columns
        assert abs(result["fg_pct"].iloc[0] - 0.5) < 0.001


# ── Game-log derivable sets ──────────────────────────────────────────


class TestDerivedSets:
    """Ensure the convenience sets in metric_registry are correct."""

    def test_season_advanced_only_includes_off_rating(self) -> None:
        assert "off_rating" in SEASON_ADVANCED_ONLY

    def test_season_advanced_only_includes_pace(self) -> None:
        assert "pace" in SEASON_ADVANCED_ONLY

    def test_game_log_derivable_includes_usg(self) -> None:
        assert "usg_pct" in GAME_LOG_DERIVABLE

    def test_game_log_derivable_includes_ts(self) -> None:
        assert "ts_pct" in GAME_LOG_DERIVABLE

    def test_game_log_derivable_excludes_off_rating(self) -> None:
        assert "off_rating" not in GAME_LOG_DERIVABLE


# ── Integration: wants_leaderboard detection ─────────────────────────


class TestWantsLeaderboardAdvanced:
    """wants_leaderboard should detect advanced metric leaderboard intent."""

    def test_highest_usage_rate(self) -> None:
        assert wants_leaderboard("highest usage rate this season")

    def test_best_assist_percentage(self) -> None:
        assert wants_leaderboard("best assist percentage last season")

    def test_lowest_turnover_percentage(self) -> None:
        assert wants_leaderboard("lowest turnover percentage this season")

    def test_best_rebound_percentage(self) -> None:
        assert wants_leaderboard("best rebound percentage in playoffs")


class TestWantsAscendingLeaderboard:
    """Ascending sort detection for 'lowest', 'worst' etc."""

    def test_lowest(self) -> None:
        assert wants_ascending_leaderboard("lowest turnover percentage")

    def test_worst(self) -> None:
        assert wants_ascending_leaderboard("worst defensive rating teams")

    def test_best_not_ascending(self) -> None:
        assert not wants_ascending_leaderboard("best usage rate")
