"""Tests for real-world UI query failure fixes.

Covers six categories of failures identified from manual usage:
1. Player-vs-player-as-opponent routing
2. Season-high / single-game queries
3. Stat phrase expansion (fg%, 3pt%, "field goal percentage", etc.)
4. With/without player filtering
5. Distinct entity count queries
6. Entity resolution (Bronny James)
"""

import pytest

from nbatools.commands._constants import STAT_ALIASES
from nbatools.commands._leaderboard_utils import (
    LEADERBOARD_STAT_ALIASES,
    TEAM_LEADERBOARD_STAT_ALIASES,
)
from nbatools.commands._matchup_utils import (
    detect_opponent_player,
    detect_without_player,
    extract_player_vs_player_as_opponent,
)
from nbatools.commands._parse_helpers import (
    detect_distinct_player_count,
    detect_distinct_team_count,
    detect_season_high_intent,
    wants_leaderboard,
)
from nbatools.commands.entity_resolution import resolve_player
from nbatools.commands.natural_query import _build_parse_state, parse_query
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query


def _is_triple_double(row: dict) -> bool:
    return sum(1 for stat in ("pts", "reb", "ast", "stl", "blk") if (row.get(stat) or 0) >= 10) >= 3


# ---------------------------------------------------------------------------
# 1. Player-vs-player-as-opponent
# ---------------------------------------------------------------------------


class TestPlayerVsPlayerAsOpponent:
    """'LeBron stats vs Kevin Durant' should NOT be a comparison —
    it should be LeBron's summary filtered to games where KD played."""

    def test_detect_opponent_player_basic(self):
        opp, cleaned = detect_opponent_player("stats vs Kevin Durant")
        assert opp == "Kevin Durant"

    def test_detect_opponent_player_against(self):
        opp, cleaned = detect_opponent_player("averages against Stephen Curry")
        assert opp == "Stephen Curry"

    def test_detect_opponent_player_none_when_team(self):
        opp, cleaned = detect_opponent_player("games vs Lakers")
        assert opp is None

    def test_extract_player_vs_player_as_opponent(self):
        result = extract_player_vs_player_as_opponent("LeBron James stats vs Kevin Durant")
        assert result is not None
        player_a, opponent = result
        assert player_a == "LeBron James"
        assert opponent == "Kevin Durant"

    def test_extract_comparison_not_opponent_when_direct_vs(self):
        """'LeBron vs KD' (no context words) should remain a comparison,
        not be treated as opponent filtering."""
        result = extract_player_vs_player_as_opponent("LeBron James vs Kevin Durant")
        # No context words → (None, None), meaning no opponent-filter intent
        assert result is None or result == (None, None)

    def test_route_lebron_stats_vs_kd(self):
        parsed = parse_query("LeBron stats vs Kevin Durant")
        # May route to finder or summary; key behavior is opponent_player is set
        assert parsed["route"] in ("player_game_finder", "player_game_summary")
        assert parsed["player"] == "LeBron James"
        assert parsed.get("opponent_player") == "Kevin Durant"

    def test_route_jokic_averages_against_curry(self):
        parsed = parse_query("Jokic averages against Stephen Curry")
        assert parsed["route"] == "player_game_summary"
        assert "joki" in parsed["player"].lower()
        assert parsed.get("opponent_player") == "Stephen Curry"


# ---------------------------------------------------------------------------
# 2. Season-high / single-game queries
# ---------------------------------------------------------------------------


class TestSeasonHighQueries:
    """'Cade Cunningham season high' should route to finder, not leaderboard.
    'highest scoring games this season' should route to top player games."""

    def test_detect_season_high_intent_basic(self):
        assert detect_season_high_intent("Cade Cunningham season high") is True

    def test_detect_season_high_intent_best_game(self):
        assert detect_season_high_intent("LeBron best game this season") is True

    def test_detect_season_high_intent_highest_scoring(self):
        assert detect_season_high_intent("highest scoring games this season") is True

    def test_detect_season_high_intent_negative(self):
        assert detect_season_high_intent("most points this season") is False

    def test_wants_leaderboard_excludes_season_high(self):
        assert wants_leaderboard("Cade Cunningham season high") is False

    def test_wants_leaderboard_excludes_highest_scoring_games(self):
        assert wants_leaderboard("highest scoring games this season") is False

    def test_route_player_season_high(self):
        parsed = parse_query("Cade Cunningham season high")
        # Should route to finder (top games), not leaderboard
        assert parsed["route"] == "player_game_finder"
        assert parsed["player"] == "Cade Cunningham"

    def test_route_highest_scoring_games(self):
        parsed = parse_query("highest scoring games this season")
        # Should route to top_player_games, not ppg leaderboard
        assert parsed["route"] == "top_player_games"

    def test_route_biggest_scoring_games(self):
        parsed = parse_query("biggest scoring games this season")
        assert parsed["route"] == "top_player_games"
        assert parsed["route_kwargs"]["stat"] == "pts"

    def test_route_most_dominant_plus_minus_games(self):
        parsed = parse_query("most dominant games by plus-minus this season")
        assert parsed["route"] == "top_player_games"
        assert parsed["route_kwargs"]["stat"] == "plus_minus"


class TestTopPerformanceAndTeamStretchBoundaries:
    """Regression coverage for raw answer QA AQ-006/AQ-008 boundaries."""

    @pytest.mark.needs_data
    def test_single_game_assist_leaders_execute_as_top_performances(self):
        qr = execute_natural_query("What were the most assists in a game this season?")

        assert qr.route == "top_player_games"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "ast"

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows
        assert rows[0]["ast"] == 23
        assert rows[0]["player_name"] == "Ryan Nembhard"
        assert "ast_per_game" not in rows[0]

    @pytest.mark.needs_data
    def test_single_game_rebound_leaders_execute_as_top_performances(self):
        qr = execute_natural_query("What were the most rebounds in a game this season?")

        assert qr.route == "top_player_games"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "reb"

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows
        assert rows[0]["reb"] == 25
        assert rows[0]["player_name"] == "Scottie Barnes"
        assert "reb_per_game" not in rows[0]

    @pytest.mark.needs_data
    def test_team_scoped_rolling_stretch_returns_unsupported_not_player_rows(self):
        qr = execute_natural_query("best 5-game team scoring stretch this season")

        assert qr.route == "player_stretch_leaderboard"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["team_rolling_stretch"]
        assert qr.to_dict()["sections"] == {}
        notes = qr.metadata.get("notes", []) + qr.result.notes
        assert any("team rolling-stretch leaderboards" in note for note in notes)

    @pytest.mark.needs_data
    def test_player_rolling_stretch_still_returns_rows(self):
        qr = execute_natural_query(
            "Which players have the hottest 3-game scoring stretch this year?"
        )

        assert qr.route == "player_stretch_leaderboard"
        assert qr.result.result_status == "ok"
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows
        assert rows[0]["window_size"] == 3


class TestP2BoundaryRoutingCleanup:
    """Regression coverage for Raw Query Answer QA Wave 7A boundaries."""

    @pytest.mark.needs_data
    def test_center_rebound_leaders_execute_with_position_filter(self):
        qr = execute_natural_query("Which centers have the most rebounds this season?")

        assert qr.route == "season_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "reb"
        assert qr.metadata["position_filter"] == "centers"
        assert {
            "label": "Position",
            "value": "centers",
            "kind": "position",
        } in qr.metadata["applied_filters"]

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows

    @pytest.mark.needs_data
    def test_guards_fg_percentage_leaders_execute_with_position_filter(self):
        qr = execute_natural_query("What players have the best field goal percentage among guards?")

        assert qr.route == "season_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "fg_pct"
        assert qr.metadata["position_filter"] == "guards"
        assert {
            "label": "Position",
            "value": "guards",
            "kind": "position",
        } in qr.metadata["applied_filters"]

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows

    @pytest.mark.needs_data
    def test_full_name_lebron_durant_comparison_executes_as_comparison(self):
        qr = execute_natural_query("LeBron James vs Kevin Durant comparison")

        assert qr.route == "player_compare"
        assert qr.result.result_status == "ok"
        sections = qr.to_dict()["sections"]
        assert set(sections) == {"summary", "comparison"}
        assert {row["player_name"] for row in sections["summary"]} == {
            "LeBron James",
            "Kevin Durant",
        }

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "route", "unsupported_filter"),
        [
            ("rookie scoring leaders this season", "season_leaders", "rookie_leaderboard"),
            (
                "bench players scoring leaders this season",
                "season_leaders",
                "role_leaderboard",
            ),
            ("starter assist leaders this season", "season_leaders", "role_leaderboard"),
            ("Celtics bench scoring this season", "game_finder", "team_bench_scoring"),
            (
                "personal fouls leaders this season",
                "season_leaders",
                "personal_foul_leaderboard",
            ),
            (
                "players with most personal fouls this season",
                "season_leaders",
                "personal_foul_leaderboard",
            ),
        ],
    )
    def test_unsupported_boundary_queries_return_no_result(self, query, route, unsupported_filter):
        qr = execute_natural_query(query)

        assert qr.route == route
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == [unsupported_filter]
        assert qr.to_dict()["sections"] == {}

    @pytest.mark.parametrize(
        ("query", "route", "unsupported_filter"),
        [
            ("Celtcs record this season", "team_record_leaderboard", "unresolved_team"),
            ("Lakeers record this season", "team_record_leaderboard", "unresolved_team"),
            (
                "Who leads the NBA in pionts per game this season?",
                "season_leaders",
                "unresolved_stat",
            ),
            ("top scorers in Marhc", "season_leaders", "unresolved_date"),
            (
                "best offensive teams since the trade deadline",
                "season_team_leaders",
                "unsupported_date_anchor",
            ),
            (
                "Bookr hottest 4-game scoring stretch",
                "player_stretch_leaderboard",
                "unresolved_player",
            ),
        ],
    )
    def test_public_query_bad_fragment_guards_return_no_result(
        self,
        query,
        route,
        unsupported_filter,
    ):
        qr = execute_natural_query(query)

        assert qr.route == route
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == [unsupported_filter]
        assert qr.to_dict()["sections"] == {}

    @pytest.mark.needs_data
    def test_opponent_conference_team_record_filter_returns_supported_result(self):
        qr = execute_natural_query("Celtics record against the East this season")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "BOS"
        assert qr.metadata["opponent_conference"] == "East"
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert {
            "label": "Opponent conference",
            "value": "East",
            "kind": "conference",
        } in qr.metadata["applied_filters"]
        assert set(qr.to_dict()["sections"]) >= {"summary", "by_season"}

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "stat"),
        [
            ("Warriors net rating this season", "net_rating"),
            ("Warriors offensive rating this season", "off_rating"),
            ("Warriors defensive rating this season", "def_rating"),
            ("Warriors pace this season", "pace"),
        ],
    )
    def test_single_team_advanced_stat_summaries_return_unsupported_boundary(self, query, stat):
        qr = execute_natural_query(query)

        assert qr.route == "game_summary"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["team"] == "GSW"
        assert qr.metadata["stat"] == stat
        assert qr.metadata["unsupported_filters"] == ["single_team_advanced_stat_summary"]
        assert qr.to_dict()["sections"] == {}
        notes = qr.metadata.get("notes", []) + qr.result.notes
        assert any("single-team advanced-stat summaries" in note for note in notes)

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "stat"),
        [
            ("Who averages the most turnovers per game this season?", "tov"),
            ("Who leads the league in steals this season?", "stl"),
            ("Who leads the league in blocks this season?", "blk"),
        ],
    )
    def test_supported_turnover_steal_block_leaderboards_still_execute(self, query, stat):
        qr = execute_natural_query(query)

        assert qr.route == "season_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == stat
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert qr.to_dict()["sections"]["leaderboard"]

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "stat"),
        [
            ("What teams have the best net rating this year?", "net_rating"),
            ("What team has the highest offensive rating this season?", "off_rating"),
            ("best defensive rating teams this season", "def_rating"),
            ("team pace leaders this season", "pace"),
            ("fastest pace teams this season", "pace"),
        ],
    )
    def test_league_wide_team_advanced_leaderboards_still_execute(self, query, stat):
        qr = execute_natural_query(query)

        assert qr.route == "season_team_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == stat
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert qr.to_dict()["sections"]["leaderboard"]

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "route", "metadata_key", "metadata_value"),
        [
            ("Malik Monk off the bench this season", "player_game_summary", "role", "bench"),
            ("Nikola Jokic as a starter this season", "player_game_summary", "role", "starter"),
            (
                "top scorers among guards since 2021",
                "season_leaders",
                "position_filter",
                "guards",
            ),
            (
                "Jayson Tatum vs Jaylen Brown last 10 games",
                "player_compare",
                "query_class",
                "comparison",
            ),
            (
                "Celtics record against playoff teams last season",
                "team_record",
                "query_class",
                "summary",
            ),
        ],
    )
    def test_nearby_supported_queries_still_execute(
        self, query, route, metadata_key, metadata_value
    ):
        qr = execute_natural_query(query)

        assert qr.route == route
        assert qr.result.result_status == "ok"
        assert qr.metadata[metadata_key] == metadata_value
        assert qr.to_dict()["sections"]


class TestPlayoffRoutingBoundaries:
    @pytest.mark.needs_data
    def test_best_second_round_hyphenated_since_routes_to_round_record(self):
        qr = execute_natural_query("best second-round record since 2010")

        assert qr.route == "playoff_round_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season_type"] == "Playoffs"
        assert qr.metadata["start_season"] == "2010-11"
        assert qr.metadata["end_season"] == "2024-25"

        sections = qr.to_dict()["sections"]
        assert set(sections) == {"leaderboard"}
        assert sections["leaderboard"]
        assert {row["round"] for row in sections["leaderboard"][:3]} == {"Second Round"}

    @pytest.mark.needs_data
    def test_lakers_celtics_playoff_matchup_history_phrase_executes(self):
        qr = execute_natural_query("Lakers Celtics playoff matchup history")

        assert qr.route == "playoff_matchup_history"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season_type"] == "Playoffs"

        sections = qr.to_dict()["sections"]
        assert set(sections) == {"summary", "comparison"}
        assert {row["team_name"] for row in sections["summary"]} == {
            "Los Angeles Lakers",
            "Boston Celtics",
        }
        assert sections["comparison"]

    @pytest.mark.needs_data
    def test_adjacent_heat_knicks_series_record_matches_vs_family(self):
        adjacent = execute_natural_query("Heat Knicks playoff series record")
        explicit = execute_natural_query("Heat vs Knicks playoff history")

        assert adjacent.route == "playoff_matchup_history"
        assert adjacent.result.result_status == "ok"
        assert explicit.route == "playoff_matchup_history"
        assert explicit.result.result_status == "ok"

        adjacent_sections = adjacent.to_dict()["sections"]
        explicit_sections = explicit.to_dict()["sections"]
        assert set(adjacent_sections) == {"summary", "comparison"}
        assert len(adjacent_sections["summary"]) == len(explicit_sections["summary"]) == 2
        assert len(adjacent_sections["comparison"]) == len(explicit_sections["comparison"]) == 6
        assert {row["team_name"] for row in adjacent_sections["summary"]} == {
            "Miami Heat",
            "New York Knicks",
        }

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "team", "start_season"),
        [
            ("Warriors Finals record since 2015", "GSW", "2015-16"),
            ("Celtics conference finals record", "BOS", None),
            ("Bulls Finals record", "CHI", None),
        ],
    )
    def test_single_team_round_records_return_unsupported_not_team_record(
        self, query, team, start_season
    ):
        qr = execute_natural_query(query)

        assert qr.route == "playoff_history"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["season_type"] == "Playoffs"
        assert qr.metadata["team"] == team
        assert qr.metadata["unsupported_filters"] == ["single_team_playoff_round_record"]
        assert qr.to_dict()["sections"] == {}
        if start_season is not None:
            assert qr.metadata["start_season"] == start_season
        notes = qr.metadata.get("notes", []) + qr.result.notes
        assert any("single-team playoff round records" in note for note in notes)


# ---------------------------------------------------------------------------
# 3. Stat phrase expansion
# ---------------------------------------------------------------------------


class TestStatPhraseExpansion:
    """Various percentage stat phrasings should resolve correctly."""

    def test_normalize_3_point_percentage(self):
        assert STAT_ALIASES.get("3 point percentage") == "fg3_pct"

    def test_normalize_3_point_pct_hyphen(self):
        assert STAT_ALIASES.get("3-point percentage") == "fg3_pct"

    def test_normalize_3_point_percent(self):
        assert STAT_ALIASES.get("3 point %") == "fg3_pct"

    def test_leaderboard_field_goal_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("field goal percentage") == "fg_pct"

    def test_leaderboard_fg_pct(self):
        assert LEADERBOARD_STAT_ALIASES.get("fg%") == "fg_pct"

    def test_leaderboard_3pt_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("3 point percentage") == "fg3_pct"

    def test_leaderboard_three_point_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("three point percentage") == "fg3_pct"

    def test_leaderboard_free_throw_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("free throw percentage") == "ft_pct"

    def test_team_leaderboard_3pt(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("best team 3 point percentage") == "fg3_pct"

    def test_team_leaderboard_fg_pct(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("team fg%") == "fg_pct"

    def test_team_leaderboard_ft_pct(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("team ft%") == "ft_pct"

    def test_route_3pt_percentage_leaders(self):
        parsed = parse_query("best 3 point percentage")
        assert parsed["route"] in ("season_leaders", "player_occurrence_leaders")
        assert parsed["stat"] == "fg3_pct"

    def test_route_best_team_3pt_pct(self):
        parsed = parse_query("best team 3 point percentage")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["stat"] == "fg3_pct"

    def test_route_hottest_from_three_recently(self):
        parsed = parse_query("hottest from three lately")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "fg3_pct"
        assert parsed["route_kwargs"]["last_n"] == 10

    def test_route_hottest_from_3_recently(self):
        parsed = parse_query("hottest from 3 lately")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "fg3_pct"
        assert parsed["route_kwargs"]["last_n"] == 10

    def test_route_best_shot_blocker_last_10(self):
        parsed = parse_query("best shot blocker last 10 games")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "blk"
        assert parsed["route_kwargs"]["last_n"] == 10

    def test_route_best_shooting_against_top_10_defenses(self):
        parsed = parse_query("best shooting vs top 10 defenses")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "fg_pct"
        assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "top-10 defenses"

    def test_route_context_only_boundary_fragment_with_fallback_note(self):
        parsed = parse_query("in clutch time")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "pts"
        assert any("boundary_fragment" in note for note in parsed.get("notes", []))

    def test_route_opponent_quality_boundary_fragment_with_fallback_note(self):
        parsed = parse_query("against winning teams")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "pts"
        assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "winning teams"
        assert any("boundary_fragment" in note for note in parsed.get("notes", []))

    def test_route_best_rim_protector_past_month(self):
        parsed = parse_query("best rim protector over the past month")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "blk"

    def test_route_best_offensive_rebounder_lately(self):
        parsed = parse_query("best offensive rebounder lately")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "oreb"


# ---------------------------------------------------------------------------
# 4. With/without player
# ---------------------------------------------------------------------------


class TestWithoutPlayer:
    """'Lakers record without LeBron' should filter out games LeBron played."""

    def test_detect_without_player_basic(self):
        player, cleaned = detect_without_player("lakers record without lebron james")
        assert player == "LeBron James"

    def test_detect_without_player_no_match(self):
        player, cleaned = detect_without_player("lakers record")
        assert player is None

    def test_detect_without_player_strips_from_text(self):
        player, cleaned = detect_without_player("lakers record without steph curry")
        # "Steph Curry" may be resolved to "Stephen Curry"
        assert player in ("Steph Curry", "Stephen Curry")
        assert "without" not in cleaned.lower()
        assert "curry" not in cleaned.lower()

    def test_detect_without_player_does_not_play_form(self):
        player, cleaned = detect_without_player(
            "what is the knicks record when jalen brunson doesn't play"
        )
        assert player == "Jalen Brunson"
        assert "brunson" not in cleaned.lower()

    def test_route_team_without_player(self):
        parsed = parse_query("Lakers record without LeBron James")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed.get("without_player") == "LeBron James"

    def test_route_team_record_with_player_presence(self):
        parsed = parse_query("Lakers record with Luka")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed["player"] is None
        assert parsed.get("with_player") == "Luka Dončić"
        assert parsed["route_kwargs"]["with_player"] == "Luka Dončić"

    def test_route_team_record_with_player_presence_full_name(self):
        parsed = parse_query("Lakers record with Austin Reaves")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed["player"] is None
        assert parsed.get("with_player") == "Austin Reaves"
        assert parsed["route_kwargs"]["with_player"] == "Austin Reaves"

    def test_route_team_record_when_player_does_not_play(self):
        parsed = parse_query("What is the Knicks' record when Jalen Brunson doesn't play?")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "NYK"
        assert parsed["player"] is None
        assert parsed.get("without_player") == "Jalen Brunson"

    def test_route_team_wins_without_player(self):
        parsed = parse_query("Warriors wins without Stephen Curry")
        assert parsed["team"] == "GSW"
        assert parsed.get("without_player") == "Stephen Curry"

    def test_route_full_name_player_without_teammate(self):
        parsed = parse_query(
            "How has Tyrese Maxey played when Joel Embiid didn't play this season?"
        )
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Tyrese Maxey"
        assert parsed["without_player"] == "Joel Embiid"

    def test_summary_when_other_player_is_out_resolves_primary_player(self):
        parsed = parse_query("How does Jamal Murray score when Nikola Jokić is out?")
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Jamal Murray"
        assert parsed["without_player"] == "Nikola Jokić"
        assert parsed["stat"] == "pts"

    @pytest.mark.parametrize(
        "query",
        [
            "What is the Lakers' record when LeBron James and Anthony Davis both play?",
            "Lakers record when LeBron and AD both play",
            "Lakers record when LeBron and AD are both out",
            "Lakers record with LeBron and AD",
            "Lakers record without LeBron and AD",
            "Lakers record with Reaves without Luka",
        ],
    )
    def test_multi_player_availability_record_sets_unsupported_filter(self, query):
        parsed = parse_query(query)
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed["route_kwargs"]["unsupported_filters"] == ["multi_player_availability"]
        assert any("unsupported_boundary" in note for note in parsed.get("notes", []))

    def test_unresolved_availability_player_sets_unsupported_filter(self):
        parsed = parse_query("Lakers record without Luk")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed["route_kwargs"]["unresolved_availability_player"] == "luk"
        assert parsed["route_kwargs"]["unsupported_filters"] == ["unresolved_player_availability"]

    @pytest.mark.needs_data
    def test_multi_player_availability_record_returns_unsupported_not_unfiltered(self):
        qr = execute_natural_query(
            "What is the Lakers record when LeBron James and Anthony Davis both play?"
        )

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["multi_player_availability"]
        assert qr.to_dict()["sections"] == {}
        notes = qr.metadata.get("notes", []) + qr.result.notes
        assert any("multi-player availability" in note for note in notes)

    @pytest.mark.needs_data
    def test_single_player_availability_record_still_executes_with_filter(self):
        qr = execute_natural_query("Lakers record without LeBron")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert {
            "label": "Without player",
            "value": "LeBron James",
            "kind": "player",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["games"] < 82
        assert summary["wins"] + summary["losses"] == summary["games"]
        assert len(sections["game_log"]) == summary["games"]

    @pytest.mark.needs_data
    def test_single_player_presence_record_executes_with_team_subject(self):
        qr = execute_natural_query("Lakers record with Luka")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["with_player"] == "Luka Dončić"
        assert qr.metadata["player"] is None
        assert {
            "label": "With player",
            "value": "Luka Dončić",
            "kind": "player",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["team_name"] == "Los Angeles Lakers"
        assert summary["games"] == 64
        assert summary["wins"] == 43
        assert summary["losses"] == 21
        assert len(sections["game_log"]) == summary["games"]

    @pytest.mark.needs_data
    def test_single_player_presence_record_for_reaves_executes_with_team_subject(self):
        qr = execute_natural_query("Lakers record with Reaves")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["with_player"] == "Austin Reaves"
        assert qr.metadata["player"] is None
        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["team_name"] == "Los Angeles Lakers"
        assert summary["games"] == 51
        assert summary["wins"] == 36
        assert summary["losses"] == 15
        assert len(sections["game_log"]) == summary["games"]

    @pytest.mark.needs_data
    def test_mixed_presence_absence_record_returns_unsupported_not_player_summary(self):
        qr = execute_natural_query("Lakers record with Reaves without Luka")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["multi_player_availability"]
        assert qr.to_dict()["sections"] == {}

    @pytest.mark.needs_data
    def test_unresolved_availability_player_does_not_return_broad_team_record(self):
        qr = execute_natural_query("Lakers record without Luk")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["unresolved_player_availability"]
        assert qr.metadata["unresolved_availability_player"] == "luk"
        assert qr.to_dict()["sections"] == {}

    @pytest.mark.needs_data
    def test_record_without_player_wrong_team_returns_no_match(self):
        qr = execute_natural_query("Celtics record when Giannis out")
        assert qr.route == "team_record"
        assert qr.result.result_reason == "no_match"
        assert qr.result.notes == ["No games matched the specified filters"]

    @pytest.mark.needs_data
    def test_record_when_player_does_not_play_answers_team_record_with_game_log(self):
        qr = execute_natural_query("What is the Knicks' record when Jalen Brunson doesn't play?")
        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["without_player"] == "Jalen Brunson"

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["team_name"] == "New York Knicks"
        assert summary["wins"] == 3
        assert summary["losses"] == 5
        assert len(sections["game_log"]) == 8
        assert all(row["team_abbr"] == "NYK" for row in sections["game_log"])

    @pytest.mark.needs_data
    def test_record_when_player_special_event_filters_summary_and_game_log(self):
        query = "What is Denver's record when Nikola Jokić has a triple-double?"
        parsed = parse_query(query)
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["special_event"] == "triple_double"
        assert parsed["occurrence_event"] == {"special_event": "triple_double"}

        qr = execute_natural_query(query)
        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team_context"]["team_abbr"] == "DEN"
        assert qr.metadata["occurrence_event"] == {"special_event": "triple_double"}
        assert {
            "label": "Special Event",
            "value": "Triple Double",
            "kind": "special_event",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        game_log = sections["game_log"]

        assert summary["games"] == 34
        assert summary["wins"] == 24
        assert summary["losses"] == 10
        assert (summary["games"], summary["wins"], summary["losses"]) != (65, 43, 22)
        assert summary["games"] == len(game_log)
        assert summary["wins"] == sum(1 for row in game_log if row["wl"] == "W")
        assert summary["losses"] == sum(1 for row in game_log if row["wl"] == "L")
        assert all(_is_triple_double(row) for row in game_log)

    @pytest.mark.needs_data
    def test_possessive_jokic_triple_double_record_ignores_auxiliary_was(self):
        query = "What was Jokic's record in games with a triple-double?"
        parsed = parse_query(query)
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Nikola Jokić"
        assert parsed["team"] is None
        assert parsed["route_kwargs"]["team"] is None
        assert parsed["route_kwargs"]["special_event"] == "triple_double"

        qr = execute_natural_query(query)
        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] is None
        assert qr.metadata.get("team_context") is None
        assert qr.metadata["occurrence_event"] == {"special_event": "triple_double"}
        assert {
            "label": "Special Event",
            "value": "Triple Double",
            "kind": "special_event",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        game_log = sections["game_log"]
        assert summary["games"] == 34
        assert summary["wins"] == 24
        assert summary["losses"] == 10
        assert len(game_log) == 34
        assert all(_is_triple_double(row) for row in game_log)

    @pytest.mark.needs_data
    def test_curry_last_20_from_three_preserves_summary_stat_context(self):
        query = "Curry last 20 games from three"
        parsed = parse_query(query)
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Stephen Curry"
        assert parsed["last_n"] == 20
        assert parsed["stat"] == "fg3m"
        assert parsed["route_kwargs"]["stat"] == "fg3m"
        assert parsed["route_kwargs"]["min_value"] is None
        assert parsed["route_kwargs"]["max_value"] is None

        qr = execute_natural_query(query)
        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "fg3m"
        assert qr.metadata["min_value"] is None
        assert qr.metadata["max_value"] is None
        assert {
            "label": "Last N games",
            "value": "20",
            "kind": "window",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["games"] == 20
        assert summary["fg3m_avg"] == pytest.approx(4.05)
        assert summary["fg3m_sum"] == 81
        assert len(sections["game_log"]) == 20

    @pytest.mark.needs_data
    def test_lakers_record_holding_opponents_under_100_uses_filtered_sample(self):
        qr = execute_natural_query(
            "What is the Lakers record when they held opponents under 100 points?"
        )

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert {
            "label": "OPP PTS max",
            "value": "99.9999",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["games"] == 7
        assert summary["wins"] == 7
        assert summary["losses"] == 0
        assert (summary["games"], summary["wins"], summary["losses"]) != (82, 53, 29)

        by_season = sections["by_season"][0]
        assert by_season["games"] == summary["games"]
        assert by_season["wins"] == summary["wins"]
        assert by_season["losses"] == summary["losses"]

    @pytest.mark.needs_data
    def test_lakers_record_holding_teams_under_100_matches_opponents_alias(self):
        held_teams = execute_natural_query(
            "What was the Lakers record when they held teams to under 100 points?"
        )
        held_opponents = execute_natural_query(
            "What is the Lakers record when they held opponents under 100 points?"
        )

        assert held_teams.route == "team_record"
        assert held_teams.result.result_status == "ok"
        assert held_teams.metadata["stat"] == "opponent_pts"
        assert {
            "label": "OPP PTS max",
            "value": "99.9999",
            "kind": "threshold",
        } in held_teams.metadata["applied_filters"]

        teams_summary = held_teams.to_dict()["sections"]["summary"][0]
        opponents_summary = held_opponents.to_dict()["sections"]["summary"][0]
        assert teams_summary["games"] == opponents_summary["games"] == 7
        assert teams_summary["wins"] == opponents_summary["wins"] == 7
        assert teams_summary["losses"] == opponents_summary["losses"] == 0

    @pytest.mark.needs_data
    def test_knicks_record_allowing_under_110_uses_opponent_points(self):
        qr = execute_natural_query(
            "What is the Knicks record when they allow fewer than 110 points?"
        )

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert {
            "label": "OPP PTS max",
            "value": "109.9999",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 35
        assert summary["wins"] == 32
        assert summary["losses"] == 3
        assert (summary["games"], summary["wins"], summary["losses"]) != (26, 8, 18)

    @pytest.mark.needs_data
    def test_celtics_record_scoring_over_120_uses_filtered_sample(self):
        qr = execute_natural_query("What is the Celtics record when they score over 120 points?")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert any(
            item["kind"] == "threshold" and item["label"] == "pts min"
            for item in qr.metadata["applied_filters"]
        )

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert 0 < summary["games"] < 82
        assert summary["wins"] + summary["losses"] == summary["games"]

        by_season = sections["by_season"][0]
        assert by_season["games"] == summary["games"]
        assert by_season["wins"] + by_season["losses"] == by_season["games"]

    @pytest.mark.needs_data
    def test_points_allowed_leaderboard_ranks_opponent_ppg(self):
        qr = execute_natural_query("Which team has allowed the fewest points per game this season?")

        assert qr.route == "season_team_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "opponent_pts_per_game"
        assert qr.metadata["ascending"] is True

        top_row = qr.to_dict()["sections"]["leaderboard"][0]
        assert top_row["team_abbr"] == "BOS"
        assert top_row["team_name"] == "Boston Celtics"
        assert top_row["opponent_pts_per_game"] == pytest.approx(107.159, abs=0.001)
        assert top_row["team_abbr"] != "BKN"

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        "query",
        [
            "Which team gave up the fewest points per game?",
            "teams allowing the fewest points",
        ],
    )
    def test_wave5_defensive_fewest_aliases_rank_opponent_ppg(self, query):
        qr = execute_natural_query(query)

        assert qr.route == "season_team_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "opponent_pts_per_game"
        assert qr.metadata["ascending"] is True

        top_row = qr.to_dict()["sections"]["leaderboard"][0]
        assert top_row["team_abbr"] == "BOS"
        assert top_row["team_name"] == "Boston Celtics"
        assert top_row["opponent_pts_per_game"] == pytest.approx(107.159, abs=0.001)
        assert top_row["team_abbr"] != "BKN"

    @pytest.mark.needs_data
    def test_most_points_allowed_leaderboard_ranks_highest_opponent_ppg(self):
        qr = execute_natural_query("which teams allow the most points per game this season")

        assert qr.route == "season_team_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "opponent_pts_per_game"
        assert qr.metadata["ascending"] is False

        top_row = qr.to_dict()["sections"]["leaderboard"][0]
        assert top_row["team_abbr"] == "UTA"
        assert top_row["team_name"] == "Utah Jazz"
        assert top_row["opponent_pts_per_game"] == pytest.approx(126.012, abs=0.001)
        assert "player_name" not in top_row
        assert top_row["team_abbr"] != "DEN"

    @pytest.mark.needs_data
    def test_opponent_ppg_leaders_use_team_leaderboard_rows(self):
        qr = execute_natural_query("opponent PPG leaders this season")

        assert qr.route == "season_team_leaders"
        assert qr.result.result_status == "ok"
        assert qr.metadata["stat"] == "opponent_pts_per_game"

        top_row = qr.to_dict()["sections"]["leaderboard"][0]
        assert top_row["team_abbr"] == "UTA"
        assert top_row["opponent_pts_per_game"] == pytest.approx(126.012, abs=0.001)
        assert "player_name" not in top_row

    @pytest.mark.needs_data
    def test_tatum_under_40_fg_record_uses_percentage_filter(self):
        qr = execute_natural_query("What's Boston's record when Jayson Tatum shoots under 40%?")

        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert any(
            item["kind"] == "threshold"
            and item["label"] == "fg_pct max"
            and float(item["value"]) == pytest.approx(0.3999)
            for item in qr.metadata["applied_filters"]
        )

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 6
        assert summary["wins"] == 4
        assert summary["losses"] == 2
        assert (summary["games"], summary["wins"], summary["losses"]) != (16, 13, 3)

    @pytest.mark.needs_data
    def test_record_leaderboard_without_player_returns_no_match(self):
        qr = execute_natural_query("best record without Stephen Curry")
        assert qr.route == "team_record_leaderboard"
        assert qr.result.result_reason == "no_match"
        assert qr.result.notes == ["No games matched the specified filters"]

    @pytest.mark.needs_data
    def test_or_more_threshold_does_not_trigger_top_level_or(self):
        qr = execute_natural_query("How often has Stephen Curry made 5 or more threes this year?")
        notes = qr.metadata.get("notes", []) + getattr(qr.result, "notes", [])
        assert qr.route in {"player_game_finder", "player_occurrence_leaders"}
        assert not any("Top-level OR" in note for note in notes)

    def test_unsupported_boundary_note_for_semantic_fallback(self):
        parsed = parse_query("Which scorers have the biggest drop-off against top-10 defenses?")
        assert parsed["route"] == "season_leaders"
        assert any("unsupported_boundary" in note for note in parsed.get("notes", []))

    def test_unsupported_boundary_note_for_above_point_six_hundred_record_bucket(self):
        parsed = parse_query("best record vs teams above .600")
        assert parsed["route"] == "team_record_leaderboard"
        assert any("unsupported_boundary" in note for note in parsed.get("notes", []))

    @pytest.mark.parametrize(
        "query",
        [
            "Who has the most ___ since becoming a starter?",
            "What is ___ record in overtime games this season?",
        ],
    )
    def test_placeholder_templates_fail_cleanly(self, query):
        parsed = parse_query(query)
        assert parsed["route"] is None
        assert parsed["intent"] == "unsupported"
        assert parsed["entity_ambiguity"]["source"] == "placeholder_template"
        assert any("placeholder templates" in note for note in parsed.get("notes", []))

        qr = execute_natural_query(query)
        assert qr.route is None
        assert qr.result.result_status == "no_result"


class TestDateFilterDropPrevention:
    @pytest.mark.needs_data
    def test_specific_date_top_scorer_uses_game_level_date_filtered_result(self):
        qr = execute_natural_query("Who scored the most points on January 1 2026?")

        assert qr.route == "top_player_games"
        assert qr.result.result_status == "ok"
        assert qr.metadata["start_date"] == "2026-01-01"
        assert qr.metadata["end_date"] == "2026-01-01"
        assert {
            "label": "Date range",
            "value": "2026-01-01 – 2026-01-01",
            "kind": "date",
        } in qr.metadata["applied_filters"]

        rows = qr.to_dict()["sections"]["leaderboard"]
        assert rows
        assert all(str(row["game_date"]).startswith("2026-01-01") for row in rows)
        assert rows[0]["player_name"] == "Kawhi Leonard"
        assert rows[0]["pts"] == 45
        assert "pts_per_game" not in rows[0]

    @pytest.mark.needs_data
    def test_team_record_since_explicit_calendar_date_uses_current_data_window(self):
        qr = execute_natural_query("Celtics road record since January 1")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "BOS"
        assert {"label": "Location", "value": "Away", "kind": "location"} in qr.metadata[
            "applied_filters"
        ]
        assert qr.metadata["start_date"] == "2026-01-01"
        assert qr.metadata["end_date"] == "2026-04-12"
        assert {
            "label": "Date range",
            "value": "2026-01-01 – 2026-04-12",
            "kind": "date",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 24
        assert summary["wins"] == 16
        assert summary["losses"] == 8

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        ("query", "expected_start", "expected_end", "away_only"),
        [
            ("What is the Knicks road record this season?", None, None, True),
            ("Thunder record since All-Star break", "2026-02-16", None, False),
            ("Warriors record in March", "2026-03-01", "2026-03-31", False),
            ("Knicks record in March", "2026-03-01", "2026-03-31", False),
        ],
    )
    def test_team_record_location_and_date_guardrails(
        self,
        query,
        expected_start,
        expected_end,
        away_only,
    ):
        qr = execute_natural_query(query)

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["start_date"] == expected_start
        assert qr.metadata["end_date"] == expected_end
        location_filter_present = {
            "label": "Location",
            "value": "Away",
            "kind": "location",
        } in qr.metadata["applied_filters"]
        assert location_filter_present is away_only
        assert qr.to_dict()["sections"]["summary"]

    @pytest.mark.needs_data
    def test_working_date_window_cases_still_preserve_date_filters(self):
        march = execute_natural_query("top scorers in March")
        assert march.route == "season_leaders"
        assert march.result.result_status == "ok"
        assert {
            "label": "Date range",
            "value": "2026-03-01 – 2026-03-31",
            "kind": "date",
        } in march.metadata["applied_filters"]
        assert march.to_dict()["sections"]["leaderboard"]

        all_star = execute_natural_query("Jokic since All-Star break")
        assert all_star.route == "player_game_finder"
        assert all_star.result.result_status == "ok"
        assert {
            "label": "Date range",
            "value": "2026-02-16",
            "kind": "date",
        } in all_star.metadata["applied_filters"]
        assert all_star.to_dict()["sections"]["finder"]

        offensive = execute_natural_query("best offensive teams since January")
        assert offensive.route == "season_team_leaders"
        assert offensive.result.result_status == "ok"
        assert offensive.metadata["start_date"] == "2026-01-01"
        assert offensive.metadata["end_date"] is None
        assert {
            "label": "Date range",
            "value": "2026-01-01",
            "kind": "date",
        } in offensive.metadata["applied_filters"]
        assert offensive.to_dict()["sections"]["leaderboard"]

        last_night = execute_natural_query("Who scored the most points last night?")
        assert last_night.route == "season_leaders"
        assert last_night.result.result_status == "no_result"
        assert last_night.result.result_reason == "no_match"
        assert {
            "label": "Date range",
            "value": "2026-04-11 – 2026-04-11",
            "kind": "date",
        } in last_night.metadata["applied_filters"]
        assert last_night.to_dict()["sections"] == {}


# ---------------------------------------------------------------------------
# 5. Opponent-quality playoff-team semantics
# ---------------------------------------------------------------------------


class TestOpponentQualityPlayoffTeamSemantics:
    @pytest.mark.needs_data
    def test_celtics_record_against_playoff_teams_uses_regular_season_quality_sample(self):
        qr = execute_natural_query("What is the Celtics' record against playoff teams?")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season_type"] == "Regular Season"
        assert {
            "label": "Opponent quality",
            "value": "playoff teams",
            "kind": "quality",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["season_type"] == "Regular Season"
        assert summary["games"] == 54
        assert summary["wins"] == 33
        assert summary["losses"] == 21
        assert (summary["games"], summary["wins"], summary["losses"]) != (11, 6, 5)

    @pytest.mark.needs_data
    def test_tatum_against_playoff_teams_uses_regular_season_quality_sample(self):
        qr = execute_natural_query("How has Jayson Tatum played against playoff teams this season?")

        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season_type"] == "Regular Season"
        assert {
            "label": "Opponent quality",
            "value": "playoff teams",
            "kind": "quality",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["season_type"] == "Regular Season"
        assert summary["games"] == 12
        assert summary["games"] != 8

    @pytest.mark.needs_data
    def test_actual_playoff_record_phrase_still_uses_playoff_games(self):
        qr = execute_natural_query("What is the Celtics playoff record?")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season_type"] == "Playoffs"

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["season_type"] == "Playoffs"
        assert summary["games"] == 11
        assert summary["wins"] == 6
        assert summary["losses"] == 5


class TestRawQueryAnswerWave5Coverage:
    @pytest.mark.needs_data
    def test_anthony_edwards_last_10_summary_returns_expected_player_and_window(self):
        qr = execute_natural_query("Anthony Edwards last 10 games summary")

        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["player"] == "Anthony Edwards"
        assert {"label": "Last N games", "value": "10", "kind": "window"} in qr.metadata[
            "applied_filters"
        ]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["player_name"] == "Anthony Edwards"
        assert summary["games"] == 10
        assert len(sections["game_log"]) == 10

    @pytest.mark.needs_data
    def test_anthony_edwards_wins_losses_split_returns_split_buckets(self):
        qr = execute_natural_query("How does Anthony Edwards shoot in wins versus losses?")

        assert qr.route == "player_split_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["player"] == "Anthony Edwards"

        sections = qr.to_dict()["sections"]
        assert sections["summary"][0]["player_name"] == "Anthony Edwards"
        assert sections["summary"][0]["games_total"] == 61
        assert {row["bucket"] for row in sections["split_comparison"]} == {"wins", "losses"}

    @pytest.mark.needs_data
    def test_lakers_road_record_last_season_preserves_relative_season_and_location(self):
        qr = execute_natural_query("Lakers road record last season")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season"] == "2024-25"
        assert qr.metadata["explicit_relative_season"] is True
        assert {"label": "Location", "value": "Away", "kind": "location"} in qr.metadata[
            "applied_filters"
        ]
        assert {"label": "Season", "value": "2024-25", "kind": "season"} in qr.metadata[
            "applied_filters"
        ]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["season_start"] == "2024-25"
        assert summary["games"] == 41
        assert summary["wins"] == 19
        assert summary["losses"] == 22

    @pytest.mark.needs_data
    def test_how_did_lakers_do_road_last_season_returns_team_record(self):
        qr = execute_natural_query("How did the Lakers do on the road last season?")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "LAL"
        assert qr.metadata["season"] == "2024-25"
        assert qr.metadata["explicit_relative_season"] is True
        assert {"label": "Location", "value": "Away", "kind": "location"} in qr.metadata[
            "applied_filters"
        ]
        assert {"label": "Season", "value": "2024-25", "kind": "season"} in qr.metadata[
            "applied_filters"
        ]

        sections = qr.to_dict()["sections"]
        assert set(sections) >= {"summary", "by_season"}
        summary = sections["summary"][0]
        assert summary["games"] == 41
        assert summary["wins"] == 19
        assert summary["losses"] == 22

    @pytest.mark.needs_data
    def test_kd_ts_top_defenses_summary_preserves_stat_and_quality_filter(self):
        qr = execute_natural_query("KD TS% vs top defenses")

        assert qr.route == "player_game_summary"
        assert qr.result.result_status == "ok"
        assert qr.metadata["player"] == "Kevin Durant"
        assert qr.metadata["stat"] == "ts_pct"
        assert qr.metadata["opponent_quality"]["surface_term"] == "top-10 defenses"
        assert {
            "label": "Opponent quality",
            "value": "top-10 defenses",
            "kind": "quality",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        summary = sections["summary"][0]
        assert summary["player_name"] == "Kevin Durant"
        assert summary["games"] == 23
        assert len(sections["game_log"]) == 23


# ---------------------------------------------------------------------------
# 6. Distinct entity count
# ---------------------------------------------------------------------------


class TestDistinctEntityCount:
    """'How many players scored 40+' should count distinct players."""

    def test_detect_distinct_player_count_basic(self):
        assert detect_distinct_player_count("how many players scored 40 points") is True

    def test_detect_distinct_player_count_number_of(self):
        assert detect_distinct_player_count("number of players with 10 assists") is True

    def test_detect_distinct_player_count_negative(self):
        assert detect_distinct_player_count("LeBron 40 point games") is False

    def test_detect_distinct_team_count(self):
        assert detect_distinct_team_count("how many teams scored 130 points") is True

    def test_route_how_many_players(self):
        parsed = parse_query("how many players scored 40 points this season")
        assert parsed["route"] == "player_occurrence_leaders"


# ---------------------------------------------------------------------------
# 7. Entity resolution: Bronny James
# ---------------------------------------------------------------------------


class TestBronnyJamesResolution:
    """'Bronny James' and 'Bronny' should resolve confidently."""

    def test_resolve_bronny_james_full(self):
        r = resolve_player("Bronny James")
        assert r.is_confident
        assert r.resolved == "Bronny James"

    def test_resolve_bronny_nickname(self):
        r = resolve_player("Bronny")
        assert r.is_confident
        assert r.resolved == "Bronny James"

    def test_route_bronny_stats(self):
        parsed = parse_query("Bronny James stats")
        assert parsed["player"] == "Bronny James"


# ---------------------------------------------------------------------------
# 8. Build-parse-state integration: new keys present
# ---------------------------------------------------------------------------


class TestBuildParseStateNewKeys:
    """Verify _build_parse_state returns the new detection keys."""

    def test_season_high_intent_key(self):
        state = _build_parse_state("LeBron season high")
        assert "season_high_intent" in state

    def test_distinct_player_count_key(self):
        state = _build_parse_state("how many players scored 40")
        assert "distinct_player_count" in state
        assert state["distinct_player_count"] is True

    def test_opponent_player_key(self):
        state = _build_parse_state("LeBron stats vs Kevin Durant")
        assert "opponent_player" in state

    def test_without_player_key(self):
        state = _build_parse_state("Lakers record without LeBron")
        assert "without_player" in state
