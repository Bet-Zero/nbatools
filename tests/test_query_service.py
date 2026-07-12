"""Tests for the query service layer.

Validates that:
- Natural queries execute and return structured QueryResult objects
- Structured queries execute and return structured QueryResult objects
- CLI rendering via render_query_result produces correct output
- Trust/status metadata is preserved
- No-result/error distinctions are preserved
- Export semantics match pre-refactor behavior
"""

import json
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

import nbatools.commands._natural_query_execution as natural_execution
import nbatools.query_service as query_service
from nbatools.commands.data_utils import get_teams_by_conference, get_teams_by_division
from nbatools.commands.structured_results import (
    ComparisonResult,
    CountResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)
from nbatools.query_service import (
    QueryResult,
    execute_natural_query,
    execute_structured_query,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


def _patch_identity_contexts(monkeypatch) -> None:
    player_contexts = {
        "Nikola Jokić": {"player_id": 203999, "player_name": "Nikola Jokić"},
        "Joel Embiid": {"player_id": 203954, "player_name": "Joel Embiid"},
    }
    team_contexts = {
        "BOS": {"team_id": 1610612738, "team_abbr": "BOS", "team_name": "Celtics"},
        "DEN": {"team_id": 1610612743, "team_abbr": "DEN", "team_name": "Nuggets"},
        "LAL": {"team_id": 1610612747, "team_abbr": "LAL", "team_name": "Lakers"},
        "PHX": {"team_id": 1610612756, "team_abbr": "PHX", "team_name": "Suns"},
    }

    monkeypatch.setattr(
        query_service,
        "_resolve_player_context",
        lambda value: player_contexts.get(value),
    )
    monkeypatch.setattr(
        query_service,
        "_resolve_team_context",
        lambda value: team_contexts.get(value),
    )


@pytest.mark.query
class TestCountFinalizerParity:
    def test_strict_threshold_copy_is_deduplicated_and_human_readable(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        games = pd.DataFrame(
            [
                {"game_id": 1, "player_name": "Nikola Jokić", "pts": 31},
                {"game_id": 2, "player_name": "Nikola Jokić", "pts": 40},
            ]
        )
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: FinderResult(games=games),
        )

        qr = execute_natural_query("How many games did Jokic score over 30 points in 2024-25?")

        assert isinstance(qr.result, CountResult)
        assert qr.metadata["count_phrase"] == (
            "Nikola Jokić has had 2 games with over 30 points in the 2024-25 regular season."
        )
        assert qr.metadata["threshold_conditions"] == [
            {
                "stat": "pts",
                "min_value": 30.0001,
                "max_value": None,
                "text": "score over 30",
            }
        ]
        assert qr.metadata["applied_filters"] == [
            {"label": "pts min", "value": "30 (exclusive)", "kind": "threshold"}
        ]

    def test_strict_under_threshold_copy_hides_storage_epsilon(self):
        phrase = query_service._build_count_phrase(
            3,
            {
                "conditions": [
                    {"stat": "ast", "min_value": None, "max_value": 9.9999},
                ]
            },
            {
                "player": "Nikola Jokić",
                "season": "2024-25",
                "season_type": "Regular Season",
            },
        )
        assert "3 games with under 10 assists" in phrase
        assert "9.9999" not in phrase

    def test_team_count_phrase_uses_plural_verb(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        games = pd.DataFrame([{"game_id": 1, "team_abbr": "BOS", "wl": "W"}])
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: FinderResult(games=games),
        )

        qr = execute_natural_query("How many Celtics wins this season")

        assert qr.metadata["count_phrase"] == "The Celtics have recorded 1 game this season."

    def test_standard_or_and_grouped_paths_share_the_count_overlay(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        games = pd.DataFrame(
            [
                {"game_id": 1, "player_id": 2544, "pts": 25, "ast": 5},
                {"game_id": 2, "player_id": 2544, "pts": 18, "ast": 12},
            ]
        )

        def finder_result():
            return FinderResult(games=games.copy())

        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: finder_result(),
        )
        monkeypatch.setattr(
            query_service,
            "_execute_or_query_build_result",
            lambda query: (finder_result(), query_service.parse_query(query)),
        )
        monkeypatch.setattr(
            query_service,
            "_execute_grouped_boolean_build_result",
            lambda condition_text, parsed: finder_result(),
        )

        queries = [
            "How many LeBron games over 20 points in 2024-25?",
            "How many LeBron games over 20 points or over 10 assists in 2024-25?",
            "How many LeBron games (over 20 points or over 10 assists) in 2024-25?",
        ]
        results = [execute_natural_query(query) for query in queries]

        for qr in results:
            assert isinstance(qr.result, CountResult)
            assert qr.result.count == 2
            assert qr.metadata["query_class"] == "count"
            assert qr.metadata["primary_count"] == 2
            assert qr.metadata["count_phrase"]
            assert qr.to_dict()["sections"]["count"] == [{"count": 2}]

    @pytest.mark.parametrize("path", ["or", "grouped"])
    def test_boolean_count_paths_preserve_negative_reasons(self, monkeypatch, path):
        negative = NoResult(
            query_class="finder",
            reason="no_data",
            result_status="no_result",
            result_reason="no_data",
            notes=["coverage unavailable"],
        )
        if path == "or":
            query = "How many LeBron games over 20 points or over 10 assists in 2024-25?"
            monkeypatch.setattr(
                query_service,
                "_execute_or_query_build_result",
                lambda raw_query: (negative, query_service.parse_query(raw_query)),
            )
        else:
            query = "How many LeBron games (over 20 points or over 10 assists) in 2024-25?"
            monkeypatch.setattr(
                query_service,
                "_execute_grouped_boolean_build_result",
                lambda condition_text, parsed: negative,
            )

        qr = execute_natural_query(query)

        assert isinstance(qr.result, NoResult)
        assert qr.result.query_class == "count"
        assert qr.result_reason == "no_data"
        assert qr.metadata["query_class"] == "count"
        assert "primary_count" not in qr.metadata
        assert "count_phrase" not in qr.metadata

    def test_or_clauses_inherit_the_full_query_season(self, monkeypatch):
        seen_seasons = []

        def fake_execute(route, kwargs, extra_conditions=None):
            seen_seasons.append(kwargs["season"])
            return FinderResult(
                games=pd.DataFrame([{"game_id": len(seen_seasons), "player_id": 2544}])
            )

        monkeypatch.setattr(natural_execution, "_execute_build_result", fake_execute)

        result, parsed = query_service._execute_or_query_build_result(
            "How many LeBron games over 20 points or over 10 assists in 2024-25?"
        )

        assert seen_seasons == ["2024-25", "2024-25"]
        assert parsed["season"] == "2024-25"
        assert len(result.games) == 2

    def test_grouped_or_evaluates_against_an_unfiltered_base(self, monkeypatch):
        parsed = query_service.parse_query(
            "How many LeBron games (over 20 points or over 10 assists) in 2024-25?"
        )
        condition_text = query_service._extract_grouped_condition_text(
            parsed["normalized_query"],
            player=parsed["player"],
        )
        games = pd.DataFrame(
            [
                {"game_id": 1, "player_id": 2544, "pts": 25, "ast": 5},
                {"game_id": 2, "player_id": 2544, "pts": 18, "ast": 12},
                {"game_id": 3, "player_id": 2544, "pts": 18, "ast": 5},
            ]
        )

        def fake_execute(route, kwargs, extra_conditions=None):
            assert kwargs["conditions"] is None
            return FinderResult(games=games)

        monkeypatch.setattr(natural_execution, "_execute_build_result", fake_execute)

        result = query_service._execute_grouped_boolean_build_result(condition_text, parsed)

        assert result.games["game_id"].tolist() == [1, 2]

    @pytest.mark.needs_data
    def test_top_level_and_grouped_or_are_result_equivalent(self):
        top_level = execute_natural_query(
            "How many games did LeBron James have over 20 points or over 10 assists in 2024-25?"
        )
        grouped = execute_natural_query(
            "How many games did LeBron James have (over 20 points or over 10 assists) in 2024-25?"
        )

        assert isinstance(top_level.result, CountResult)
        assert isinstance(grouped.result, CountResult)
        assert top_level.result.count == grouped.result.count
        assert set(top_level.result.games["game_id"]) == set(grouped.result.games["game_id"])
        assert top_level.metadata["count_phrase"] == grouped.metadata["count_phrase"]


class TestCountNegativeFinalization:
    @pytest.mark.parametrize(
        ("reason", "status"),
        [
            ("filter_not_supported", "no_result"),
            ("no_data", "no_result"),
            ("unsupported", "no_result"),
            ("ambiguous", "no_result"),
            ("unrouted", "error"),
            ("error", "error"),
        ],
    )
    def test_negative_reasons_never_become_zero(self, monkeypatch, reason, status):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: NoResult(
                query_class="finder",
                reason=reason,
                result_status=status,
                result_reason=reason,
                current_through="2025-04-10",
                metadata={"coverage": "missing"},
                notes=["requested filter was not executed"],
                caveats=["coverage caveat"],
            ),
        )

        qr = execute_natural_query("how many 30 point games has Jokic had 2024-25")
        payload = qr.to_dict()

        assert isinstance(qr.result, NoResult)
        assert qr.result.query_class == "count"
        assert qr.result_status == status
        assert qr.result_reason == reason
        assert qr.result.current_through == "2025-04-10"
        assert qr.result.metadata == {"coverage": "missing"}
        assert qr.result.notes == ["requested filter was not executed"]
        assert qr.result.caveats == ["coverage caveat"]
        assert payload["sections"] == {}
        assert qr.metadata["query_class"] == "count"
        assert "primary_count" not in qr.metadata
        assert "count_phrase" not in qr.metadata

    def test_explicit_no_match_becomes_trusted_zero(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: NoResult(
                query_class="finder",
                reason="no_match",
                current_through="2025-04-10",
                metadata={"coverage": "complete"},
                notes=["fully evaluated"],
                caveats=["sample caveat"],
            ),
        )

        qr = execute_natural_query("how many 100 point games has Jokic had 2024-25")
        payload = qr.to_dict()

        assert isinstance(qr.result, CountResult)
        assert qr.result.count == 0
        assert qr.result_status == "ok"
        assert qr.result.current_through == "2025-04-10"
        assert qr.result.metadata == {"coverage": "complete"}
        assert qr.result.notes == ["fully evaluated"]
        assert qr.result.caveats == ["sample caveat"]
        assert payload["sections"]["count"] == [{"count": 0}]
        assert qr.metadata["primary_count"] == 0
        assert "count_phrase" in qr.metadata

    @pytest.mark.parametrize(
        "result",
        [
            FinderResult(
                games=pd.DataFrame([{"player_name": "Nikola Jokić"}]),
                result_status="no_result",
                result_reason="filter_not_supported",
            ),
            LeaderboardResult(
                leaders=pd.DataFrame([{"player_name": "Nikola Jokić", "games": 25}]),
                result_status="no_result",
                result_reason="filter_not_supported",
            ),
            CountResult(
                count=25,
                result_status="no_result",
                result_reason="filter_not_supported",
            ),
        ],
    )
    def test_negative_row_bearing_results_do_not_expose_broad_counts(self, monkeypatch, result):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: result,
        )

        qr = execute_natural_query("how many 30 point games has Jokic had 2024-25")

        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "filter_not_supported"
        assert qr.to_dict()["sections"] == {}
        assert "primary_count" not in qr.metadata

    def test_negative_count_raw_cli_has_no_count_section(self, monkeypatch):
        from nbatools.commands.natural_query import render_query_result

        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=["clutch coverage is unavailable"],
            ),
        )

        query = "how many clutch games has Jokic had 2024-25"
        qr = execute_natural_query(query)
        output = _capture(render_query_result, qr, query, pretty=False)

        assert "NO_RESULT" in output
        assert "filter_not_supported" in output
        assert "\nCOUNT\n" not in output

    def test_exact_coverage_failure_survives_shared_cli_envelope(self, monkeypatch):
        from nbatools.commands.natural_query import render_query_result

        detail = (
            "player_game_period_stats coverage incomplete; requested_keys=3; "
            "covered_keys=2; window=quarter:4; "
            "missing_keys=[game_id=3, team_id=1, player_id=10]"
        )
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: NoResult(
                query_class="finder",
                reason="filter_not_supported",
                notes=[detail],
            ),
        )

        qr = execute_structured_query(
            "player_game_finder",
            season="2099-00",
            player="Period Star",
            quarter="4",
        )
        output = _capture(render_query_result, qr, qr.query, pretty=False)

        assert qr.result_status == "no_result"
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.notes == [detail]
        assert detail in output
        assert "NO_RESULT" in output


class TestLeaderboardCountEntityGrain:
    def _parsed_player_appearance_query(self):
        from nbatools.commands.natural_query import parse_query

        parsed = parse_query("How many Finals appearances does LeBron have?")
        parsed["route_kwargs"].pop("unsupported_filters", None)
        return parsed

    def test_player_appearance_boundary_refuses_before_execution(self):
        qr = execute_natural_query("How many Finals appearances does LeBron have?")

        assert qr.route == "playoff_appearances"
        assert isinstance(qr.result, NoResult)
        assert qr.result.query_class == "count"
        assert qr.result_status == "no_result"
        assert qr.result_reason == "filter_not_supported"
        assert qr.to_dict()["sections"] == {}
        assert qr.metadata["unsupported_filters"] == ["player_playoff_appearances"]
        assert "primary_count" not in qr.metadata
        assert "count_phrase" not in qr.metadata

    def test_player_appearance_raw_cli_has_no_count_or_leaderboard(self):
        from nbatools.commands.natural_query import render_query_result

        query = "How many Finals appearances does LeBron have?"
        qr = execute_natural_query(query)
        output = _capture(render_query_result, qr, query, pretty=False)

        assert "NO_RESULT" in output
        assert "filter_not_supported" in output
        assert "\nCOUNT\n" not in output
        assert "\nLEADERBOARD\n" not in output

    def test_wrong_grain_leaderboard_cannot_become_player_zero(self, monkeypatch):
        parsed = self._parsed_player_appearance_query()
        monkeypatch.setattr(query_service, "parse_query", lambda _query: parsed)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: LeaderboardResult(
                leaders=pd.DataFrame(
                    [{"rank": 1, "team_abbr": "LAL", "team_name": "Lakers", "appearances": 10}]
                )
            ),
        )

        qr = execute_natural_query("How many Finals appearances does LeBron have?")

        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "filter_not_supported"
        assert qr.to_dict()["sections"] == {}
        assert "primary_count" not in qr.metadata

    def test_missing_player_row_remains_no_match(self, monkeypatch):
        parsed = self._parsed_player_appearance_query()
        monkeypatch.setattr(query_service, "parse_query", lambda _query: parsed)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: LeaderboardResult(
                leaders=pd.DataFrame(
                    [{"rank": 1, "player_name": "Stephen Curry", "appearances": 6}]
                )
            ),
        )

        qr = execute_natural_query("How many Finals appearances does LeBron have?")

        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "no_match"
        assert qr.to_dict()["sections"] == {}

    def test_matching_player_grain_preserves_real_count(self, monkeypatch):
        parsed = self._parsed_player_appearance_query()
        monkeypatch.setattr(query_service, "parse_query", lambda _query: parsed)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: LeaderboardResult(
                leaders=pd.DataFrame(
                    [{"rank": 1, "player_name": "LeBron James", "appearances": 10}]
                )
            ),
        )

        qr = execute_natural_query("How many Finals appearances does LeBron have?")

        assert isinstance(qr.result, CountResult)
        assert qr.result.count == 10
        assert qr.metadata["primary_count"] == 10


# ===================================================================
# Natural query execution through the service layer
# ===================================================================


@pytest.mark.slow
class TestNaturalQueryExecution:
    """execute_natural_query should parse, route, and return typed results."""

    @pytest.mark.needs_data
    def test_player_summary_returns_summary_result(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, SummaryResult)
        assert qr.is_ok
        assert qr.route == "player_game_summary"
        assert qr.result_status == "ok"

    @pytest.mark.needs_data
    def test_team_summary_returns_summary_result(self):
        qr = execute_natural_query("Celtics summary 2024-25")
        assert isinstance(qr.result, SummaryResult)
        assert qr.is_ok
        assert qr.route == "game_summary"

    @pytest.mark.needs_data
    def test_player_compare_returns_comparison_result(self):
        qr = execute_natural_query("Jokic vs Embiid recent form")
        assert isinstance(qr.result, ComparisonResult)
        assert qr.is_ok
        assert qr.route == "player_compare"

    @pytest.mark.needs_data
    def test_team_compare_returns_comparison_result(self):
        qr = execute_natural_query("Celtics vs Lakers 2024-25")
        assert isinstance(qr.result, ComparisonResult)
        assert qr.is_ok
        assert qr.route == "team_compare"

    @pytest.mark.needs_data
    def test_player_finder_returns_finder_result(self):
        qr = execute_natural_query("Jokic over 25 points 2024-25")
        assert isinstance(qr.result, FinderResult)
        assert qr.is_ok
        assert qr.route == "player_game_finder"

    @pytest.mark.needs_data
    def test_team_finder_returns_finder_result(self):
        qr = execute_natural_query("Celtics over 120 points 2024-25")
        assert isinstance(qr.result, FinderResult)
        assert qr.is_ok
        assert qr.route == "game_finder"

    @pytest.mark.needs_data
    def test_player_split_returns_split_summary_result(self):
        qr = execute_natural_query("Jokic home vs away 2024-25")
        assert isinstance(qr.result, SplitSummaryResult)
        assert qr.is_ok
        assert qr.route == "player_split_summary"

    @pytest.mark.needs_data
    def test_team_split_returns_split_summary_result(self):
        qr = execute_natural_query("Celtics wins vs losses 2024-25")
        assert isinstance(qr.result, SplitSummaryResult)
        assert qr.is_ok
        assert qr.route == "team_split_summary"

    @pytest.mark.needs_data
    def test_season_leaders_returns_leaderboard_result(self):
        qr = execute_natural_query("top 5 scorers 2024-25")
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.is_ok
        assert qr.route == "season_leaders"

    def test_player_streak_returns_streak_result(self):
        qr = execute_natural_query("Jokic 5 straight games with 20+ points")
        assert isinstance(qr.result, (StreakResult, NoResult))
        assert qr.route == "player_streak_finder"

    @pytest.mark.needs_data
    def test_or_query_returns_finder_result(self):
        qr = execute_natural_query("Jokic over 30 points or over 10 assists 2024-25")
        assert isinstance(qr.result, FinderResult)
        assert qr.is_ok

    def test_grouped_boolean_returns_result(self):
        qr = execute_natural_query("Jokic summary (over 25 points and over 10 rebounds) 2024-25")
        assert isinstance(qr, QueryResult)
        # Should return a SummaryResult or NoResult depending on data
        assert isinstance(qr.result, (SummaryResult, NoResult))


# ===================================================================
# Structured query execution through the service layer
# ===================================================================


class TestStructuredQueryExecution:
    """execute_structured_query should call build_result and return results."""

    @pytest.mark.needs_data
    def test_player_game_summary(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="2024-25",
            player="Nikola Jokić",
        )
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, SummaryResult)
        assert qr.route == "player_game_summary"
        assert qr.metadata["route"] == "player_game_summary"
        assert qr.metadata["query_class"] == "summary"

    @pytest.mark.needs_data
    def test_game_summary(self):
        qr = execute_structured_query(
            "game_summary",
            season="2024-25",
            team="BOS",
        )
        assert isinstance(qr.result, SummaryResult)
        assert qr.route == "game_summary"

    @pytest.mark.needs_data
    def test_season_leaders(self):
        qr = execute_structured_query(
            "season_leaders",
            season="2024-25",
            stat="pts",
            limit=5,
        )
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.route == "season_leaders"

    @pytest.mark.needs_data
    def test_player_compare(self):
        qr = execute_structured_query(
            "player_compare",
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2024-25",
        )
        assert isinstance(qr.result, ComparisonResult)
        assert qr.route == "player_compare"

    def test_player_game_finder(self):
        qr = execute_structured_query(
            "player_game_finder",
            season="2024-25",
            player="Nikola Jokić",
            stat="pts",
            min_value=25,
            limit=10,
            sort_by="game_date",
            ascending=False,
        )
        assert isinstance(qr.result, (FinderResult, NoResult))
        assert qr.route == "player_game_finder"

    @pytest.mark.needs_data
    def test_top_player_games(self):
        qr = execute_structured_query(
            "top_player_games",
            season="2005-06",
            stat="pts",
            limit=5,
        )
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.route == "top_player_games"
        # Kobe's 81-point game should be in 2005-06
        if qr.is_ok:
            leaders_df = qr.result.leaders
            assert "Kobe Bryant" in leaders_df["player_name"].values

    def test_invalid_route_returns_unsupported(self):
        qr = execute_structured_query("nonexistent_route", season="2024-25")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason == "unsupported"
        assert qr.result_status == "no_result"

    def test_no_data_returns_no_result(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
        )
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason in ("no_data", "no_match")

    def test_structured_query_accepts_quarter_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
            quarter="4",
        )
        assert qr.route == "player_game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["quarter"] == "4"
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.result_status == "no_result"

    def test_structured_query_accepts_half_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "game_summary",
            season="1950-51",
            team="BOS",
            half="first",
        )
        assert qr.route == "game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["half"] == "first"
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.result_status == "no_result"

    def test_structured_query_accepts_back_to_back_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "game_summary",
            season="1950-51",
            team="BOS",
            back_to_back=True,
        )
        assert qr.route == "game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["back_to_back"] is True
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.result_status == "no_result"

    def test_structured_query_accepts_rest_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
            rest_days="advantage",
        )
        assert qr.route == "player_game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["rest_days"] == "advantage"
        assert any(
            "rest filter is not supported with current data" in note
            and "try removing this filter" in note
            for note in qr.result.notes
        )

    def test_structured_query_accepts_one_possession_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "game_summary",
            season="1950-51",
            team="BOS",
            one_possession=True,
        )
        assert qr.route == "game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["one_possession"] is True
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.result_status == "no_result"

    def test_structured_query_accepts_national_tv_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "game_summary",
            season="1950-51",
            team="BOS",
            nationally_televised=True,
        )
        assert qr.route == "game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["nationally_televised"] is True
        assert qr.result_reason == "filter_not_supported"
        assert qr.result.result_status == "no_result"

    def test_structured_query_accepts_role_filter_in_metadata(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
            role="bench",
        )
        assert qr.route == "player_game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["role"] == "bench"
        assert not any("role" in note and "unfiltered" in note for note in qr.result.notes)

    def test_structured_query_accepts_on_off_placeholder_route(self):
        qr = execute_structured_query(
            "player_on_off",
            season="1950-51",
            player="Nikola Jokić",
            lineup_members=["Nikola Jokić"],
            presence_state="both",
        )
        assert qr.route == "player_on_off"
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"
        assert qr.metadata["lineup_members"] == ["Nikola Jokić"]
        assert qr.metadata["presence_state"] == "both"
        assert any("on_off" in note and "placeholder" in note for note in qr.result.notes)

    def test_structured_query_accepts_lineup_summary_route_without_coverage(self):
        qr = execute_structured_query(
            "lineup_summary",
            season="1950-51",
            lineup_members=["Jayson Tatum", "Jaylen Brown"],
            unit_size=2,
        )
        assert qr.route == "lineup_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"
        assert qr.metadata["lineup_members"] == ["Jayson Tatum", "Jaylen Brown"]
        assert qr.metadata["unit_size"] == 2
        assert any("lineup" in note and "coverage" in note for note in qr.result.notes)

    def test_structured_query_accepts_lineup_leaderboard_route_without_coverage(self):
        qr = execute_structured_query(
            "lineup_leaderboard",
            season="1950-51",
            unit_size=5,
            minute_minimum=200,
        )
        assert qr.route == "lineup_leaderboard"
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"
        assert qr.metadata["unit_size"] == 5
        assert qr.metadata["minute_minimum"] == 200
        assert any("lineup" in note and "coverage" in note for note in qr.result.notes)

    def test_structured_query_accepts_player_stretch_leaderboard_route(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        player_rows = [
            {
                "game_id": 1,
                "season": "2099-00",
                "season_type": "Regular Season",
                "game_date": "2099-10-01",
                "team_id": 1,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 2,
                "opponent_team_abbr": "BBB",
                "opponent_team_name": "Beta",
                "is_home": 1,
                "is_away": 0,
                "player_id": 10,
                "player_name": "Stretch Star",
                "starter_flag": 1,
                "start_position": "G",
                "minutes": 35,
                "pts": 20,
                "fgm": 7,
                "fga": 15,
                "fg_pct": 0.467,
                "fg3m": 2,
                "fg3a": 6,
                "fg3_pct": 0.333,
                "ftm": 4,
                "fta": 5,
                "ft_pct": 0.8,
                "oreb": 1,
                "dreb": 4,
                "reb": 5,
                "ast": 6,
                "stl": 1,
                "blk": 0,
                "tov": 2,
                "pf": 2,
                "plus_minus": 8,
                "comment": "",
            },
            {
                "game_id": 2,
                "season": "2099-00",
                "season_type": "Regular Season",
                "game_date": "2099-10-03",
                "team_id": 1,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 3,
                "opponent_team_abbr": "CCC",
                "opponent_team_name": "Gamma",
                "is_home": 0,
                "is_away": 1,
                "player_id": 10,
                "player_name": "Stretch Star",
                "starter_flag": 1,
                "start_position": "G",
                "minutes": 34,
                "pts": 24,
                "fgm": 8,
                "fga": 16,
                "fg_pct": 0.5,
                "fg3m": 3,
                "fg3a": 7,
                "fg3_pct": 0.429,
                "ftm": 5,
                "fta": 6,
                "ft_pct": 0.833,
                "oreb": 1,
                "dreb": 5,
                "reb": 6,
                "ast": 7,
                "stl": 2,
                "blk": 1,
                "tov": 2,
                "pf": 2,
                "plus_minus": 10,
                "comment": "",
            },
            {
                "game_id": 3,
                "season": "2099-00",
                "season_type": "Regular Season",
                "game_date": "2099-10-05",
                "team_id": 1,
                "team_abbr": "AAA",
                "team_name": "Alpha",
                "opponent_team_id": 4,
                "opponent_team_abbr": "DDD",
                "opponent_team_name": "Delta",
                "is_home": 1,
                "is_away": 0,
                "player_id": 10,
                "player_name": "Stretch Star",
                "starter_flag": 1,
                "start_position": "G",
                "minutes": 36,
                "pts": 26,
                "fgm": 9,
                "fga": 17,
                "fg_pct": 0.529,
                "fg3m": 4,
                "fg3a": 8,
                "fg3_pct": 0.5,
                "ftm": 4,
                "fta": 5,
                "ft_pct": 0.8,
                "oreb": 2,
                "dreb": 4,
                "reb": 6,
                "ast": 8,
                "stl": 1,
                "blk": 1,
                "tov": 1,
                "pf": 2,
                "plus_minus": 12,
                "comment": "",
            },
        ]
        team_rows = [
            {"game_id": 1, "team_id": 1, "wl": "W"},
            {"game_id": 2, "team_id": 1, "wl": "W"},
            {"game_id": 3, "team_id": 1, "wl": "W"},
        ]

        player_df = pd.DataFrame(player_rows)
        team_df = pd.DataFrame(team_rows)
        player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
        team_path = tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv"
        player_path.parent.mkdir(parents=True, exist_ok=True)
        team_path.parent.mkdir(parents=True, exist_ok=True)
        player_df.to_csv(player_path, index=False)
        team_df.to_csv(team_path, index=False)

        qr = execute_structured_query(
            "player_stretch_leaderboard",
            season="2099-00",
            window_size=3,
            stretch_metric="pts",
        )

        assert qr.route == "player_stretch_leaderboard"
        assert qr.metadata["window_size"] == 3
        assert qr.metadata["stretch_metric"] == "pts"
        assert qr.result.query_class == "leaderboard"
        assert qr.result.result_status == "ok"


# ===================================================================
# Metadata preservation
# ===================================================================


class TestMetadataPreservation:
    """Query metadata should be populated correctly."""

    def test_natural_query_metadata_has_core_fields(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        assert "query_text" in qr.metadata
        assert qr.metadata["query_text"] == "Jokic summary 2024-25"
        assert qr.metadata["route"] == "player_game_summary"
        assert qr.metadata["query_class"] == "summary"

    def test_structured_query_metadata_has_core_fields(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="2024-25",
            player="Nikola Jokić",
        )
        assert qr.metadata["route"] == "player_game_summary"
        assert qr.metadata["query_class"] == "summary"
        assert qr.metadata["season"] == "2024-25"
        assert qr.metadata["player"] == "Nikola Jokić"

    def test_natural_player_finder_metadata_preserves_threshold_context(self, monkeypatch):
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: FinderResult(
                games=pd.DataFrame([{"player_name": "Nikola Jokić", "pts": 28}])
            ),
        )

        qr = execute_natural_query("Jokic games with 25+ points and 10+ rebounds 2024-25")

        assert qr.metadata["route"] == "player_game_finder"
        assert qr.metadata["query_class"] == "finder"
        assert qr.metadata["player"] == "Nikola Jokić"
        assert qr.metadata["stat"] == "pts"
        assert qr.metadata["min_value"] == 25.0
        assert qr.metadata["sort_by"] == "stat"
        assert qr.metadata["ranked_intent"] is False
        assert qr.metadata["threshold_conditions"] == [
            {
                "stat": "pts",
                "min_value": 25.0,
                "max_value": None,
                "text": "25+ points",
            },
            {
                "stat": "reb",
                "min_value": 10.0,
                "max_value": None,
                "text": "10+ rebounds",
            },
        ]
        assert qr.metadata["conditions"] == [
            {
                "stat": "pts",
                "min_value": 25.0,
                "max_value": None,
                "text": "25+ points",
            },
            {
                "stat": "reb",
                "min_value": 10.0,
                "max_value": None,
                "text": "10+ rebounds",
            },
        ]
        assert qr.metadata["extra_conditions"] == []
        assert qr.metadata["applied_filters"] == [
            {
                "label": "pts min",
                "value": "25.0",
                "kind": "threshold",
            },
            {
                "label": "reb min",
                "value": "10.0",
                "kind": "threshold",
            },
        ]

    def test_compound_team_count_consumes_conditions_without_extra_filtering(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)

        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "team_occurrence_leaders"
            assert kwargs["conditions"] == [
                {"stat": "pts", "min_value": 120.0, "max_value": None},
                {"stat": "fg3m", "min_value": 15.0, "max_value": None},
            ]
            assert extra_conditions == []
            return LeaderboardResult(
                leaders=pd.DataFrame(
                    [
                        {
                            "rank": 1,
                            "team_abbr": "BOS",
                            "team_name": "Boston Celtics",
                            "games_played": 200,
                            "games_pts_120+_fg3m_15+": 125,
                        }
                    ]
                )
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query(
            "how many Celtics games with 120+ points and 15+ threes since 2022"
        )

        assert qr.metadata["primary_count"] == 125
        assert qr.metadata["extra_conditions"] == []
        assert "15+ threes" in qr.metadata["count_phrase"]
        assert {
            "label": "pts min",
            "value": "120.0",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]
        assert {
            "label": "fg3m min",
            "value": "15.0",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]

    def test_compact_player_finder_passes_compound_conditions_to_execution(self, monkeypatch):
        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "player_game_finder"
            assert kwargs["stat"] == "pts"
            assert kwargs["min_value"] == 30.0
            assert kwargs["conditions"] == [
                {"stat": "pts", "min_value": 30.0, "max_value": None},
                {"stat": "ast", "min_value": 10.0, "max_value": None},
            ]
            assert extra_conditions == []
            return FinderResult(
                games=pd.DataFrame([{"player_name": "Nikola Jokić", "pts": 30, "ast": 10}])
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query("Jokic games with 30 points and 10 assists")

        assert qr.metadata["route"] == "player_game_finder"
        assert qr.metadata["stat"] == "pts"
        assert qr.metadata["min_value"] == 30.0
        assert {
            "label": "pts min",
            "value": "30.0",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]
        assert {
            "label": "ast min",
            "value": "10.0",
            "kind": "threshold",
        } in qr.metadata["applied_filters"]

    def test_how_often_player_special_event_gets_count_phrase(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)

        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "player_game_finder"
            assert kwargs["special_event"] == "triple_double"
            assert kwargs["limit"] is None
            return FinderResult(
                games=pd.DataFrame(
                    [
                        {"player_name": "Nikola Jokić", "wl": "W"},
                        {"player_name": "Nikola Jokić", "wl": "W"},
                    ]
                )
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query(
            "How often has Nikola Jokić recorded a triple-double this season?"
        )

        assert qr.metadata["query_class"] == "count"
        assert qr.metadata["primary_count"] == 2
        assert (
            qr.metadata["count_phrase"] == "Nikola Jokić has recorded 2 triple-doubles this season."
        )

    def test_record_when_player_special_event_metadata_exposes_filter(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)

        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "player_game_summary"
            assert kwargs["special_event"] == "triple_double"
            return SummaryResult(
                summary=pd.DataFrame(
                    [
                        {
                            "player_name": "Nikola Jokić",
                            "games": 34,
                            "wins": 24,
                            "losses": 10,
                        }
                    ]
                )
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query("What is Denver's record when Nikola Jokić has a triple-double?")

        assert qr.metadata["route"] == "player_game_summary"
        assert qr.metadata["occurrence_event"] == {"special_event": "triple_double"}
        assert {
            "label": "Special Event",
            "value": "Triple Double",
            "kind": "special_event",
        } in qr.metadata["applied_filters"]

    def test_specific_calendar_date_top_scorer_preserves_date_filter(self, monkeypatch):
        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "top_player_games"
            assert kwargs["start_date"] == "2026-01-01"
            assert kwargs["end_date"] == "2026-01-01"
            return LeaderboardResult(
                leaders=pd.DataFrame(
                    [
                        {
                            "rank": 1,
                            "player_name": "Kawhi Leonard",
                            "game_date": "2026-01-01",
                            "pts": 45,
                        }
                    ]
                )
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query("Who scored the most points on January 1 2026?")

        assert qr.route == "top_player_games"
        assert qr.metadata["start_date"] == "2026-01-01"
        assert qr.metadata["end_date"] == "2026-01-01"
        assert {
            "label": "Date range",
            "value": "2026-01-01 – 2026-01-01",
            "kind": "date",
        } in qr.metadata["applied_filters"]
        assert qr.to_dict()["sections"]["leaderboard"][0]["pts"] == 45

    def test_team_opponent_points_count_phrase_includes_record(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)

        def fake_execute(route, kwargs, extra_conditions=None):
            assert route == "game_finder"
            assert kwargs["stat"] == "opponent_pts"
            assert kwargs["limit"] is None
            return FinderResult(
                games=pd.DataFrame(
                    [
                        {"team_abbr": "LAL", "opponent_pts": 99, "wl": "W"},
                        {"team_abbr": "LAL", "opponent_pts": 92, "wl": "W"},
                        {"team_abbr": "LAL", "opponent_pts": 95, "wl": "L"},
                    ]
                )
            )

        monkeypatch.setattr(query_service, "_execute_build_result", fake_execute)

        qr = execute_natural_query(
            "How often have the Lakers held opponents under 100 points this year?"
        )

        assert qr.metadata["primary_count"] == 3
        assert (
            qr.metadata["count_phrase"]
            == "The Lakers have held opponents under 100 points 3 times this season, going 2-1."
        )

    def test_game_summary_answer_phrase_uses_filtered_record(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs, extra_conditions=None: SummaryResult(
                summary=pd.DataFrame(
                    [
                        {
                            "team_name": "Suns",
                            "games": 18,
                            "wins": 8,
                            "losses": 10,
                            "pts_avg": 103.778,
                        }
                    ]
                )
            ),
        )

        qr = execute_natural_query("How do the Suns perform when Devin Booker didn't play?")

        assert qr.metadata["record"] == "8-10"
        assert qr.metadata["primary_count"] == 18
        assert (
            qr.metadata["answer_phrase"]
            == "The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG."
        )

    def test_structured_player_finder_metadata_preserves_sort_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: FinderResult(
                games=pd.DataFrame([{"player_name": "Nikola Jokić", "pts": 28}])
            ),
        )

        qr = execute_structured_query(
            "player_game_finder",
            season="2024-25",
            player="Nikola Jokić",
            stat="pts",
            min_value=25,
            sort_by="stat",
        )

        assert qr.metadata["route"] == "player_game_finder"
        assert qr.metadata["query_class"] == "finder"
        assert qr.metadata["stat"] == "pts"
        assert qr.metadata["min_value"] == 25
        assert qr.metadata["sort_by"] == "stat"
        assert qr.metadata["ranked_intent"] is True

    def test_structured_player_metadata_has_player_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: SummaryResult(query_class="summary"),
        )
        qr = execute_structured_query(
            "player_game_summary",
            season="2024-25",
            player="Nikola Jokić",
        )
        assert qr.metadata["player"] == "Nikola Jokić"
        assert qr.metadata["player_context"] == {
            "player_id": 203999,
            "player_name": "Nikola Jokić",
        }

    def test_structured_team_metadata_has_team_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: SummaryResult(query_class="summary"),
        )
        qr = execute_structured_query(
            "game_summary",
            season="2024-25",
            team="BOS",
        )
        assert qr.metadata["team"] == "BOS"
        assert qr.metadata["team_context"]["team_id"] == 1610612738
        assert qr.metadata["team_context"]["team_abbr"] == "BOS"
        assert "Celtics" in qr.metadata["team_context"]["team_name"]

    def test_structured_opponent_metadata_has_opponent_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: SummaryResult(query_class="summary"),
        )
        qr = execute_structured_query(
            "player_game_summary",
            season="2024-25",
            player="Nikola Jokić",
            opponent="LAL",
        )
        assert qr.metadata["opponent"] == "LAL"
        assert qr.metadata["opponent_context"] == {
            "team_id": 1610612747,
            "team_abbr": "LAL",
            "team_name": "Lakers",
        }

    def test_structured_player_comparison_metadata_has_players_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: ComparisonResult(query_class="comparison"),
        )
        qr = execute_structured_query(
            "player_compare",
            season="2024-25",
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
        )
        assert qr.metadata["player"] == "Nikola Jokić, Joel Embiid"
        assert qr.metadata["players_context"] == [
            {"player_id": 203999, "player_name": "Nikola Jokić"},
            {"player_id": 203954, "player_name": "Joel Embiid"},
        ]
        assert "player_context" not in qr.metadata

    def test_structured_team_comparison_metadata_has_teams_context(self, monkeypatch):
        _patch_identity_contexts(monkeypatch)
        monkeypatch.setattr(
            query_service,
            "_execute_build_result",
            lambda route, kwargs: ComparisonResult(query_class="comparison"),
        )
        qr = execute_structured_query(
            "team_compare",
            season="2024-25",
            team_a="BOS",
            team_b="LAL",
        )
        assert qr.metadata["team"] == "BOS, LAL"
        assert qr.metadata["teams_context"] == [
            {"team_id": 1610612738, "team_abbr": "BOS", "team_name": "Celtics"},
            {"team_id": 1610612747, "team_abbr": "LAL", "team_name": "Lakers"},
        ]
        assert "team_context" not in qr.metadata

    @pytest.mark.needs_data
    def test_current_through_present(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        # current_through should be on the result or in metadata
        assert qr.current_through is not None

    def test_notes_present_for_summary(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        meta = qr.metadata
        # Player summary queries should have sample_advanced_metrics note
        notes = meta.get("notes", [])
        assert any("sample_advanced_metrics" in n for n in notes)

    @pytest.mark.query
    def test_unsupported_concept_never_reaches_route_execution(self, monkeypatch):
        def fail_if_executed(*args, **kwargs):
            pytest.fail("unsupported concept reached route execution")

        monkeypatch.setattr(query_service, "_execute_build_result", fail_if_executed)
        qr = execute_natural_query("Who's been the best shot creator in clutch time this season?")

        assert qr.route is None
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["unsupported_concept"]
        assert qr.to_dict()["sections"] == {}
        notes = qr.metadata.get("notes", [])
        assert any("unsupported_boundary" in note for note in notes)

    @pytest.mark.needs_data
    @pytest.mark.parametrize(
        "query",
        [
            "Jokic salary and contract",
            "How many games did LeBron and Curry both play?",
        ],
    )
    def test_a01_audit_reproductions_fail_closed(self, query):
        qr = execute_natural_query(query)

        assert qr.route is None
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["unsupported_concept"]
        assert qr.to_dict()["sections"] == {}


# ===================================================================
# No-result and error distinctions
# ===================================================================


class TestNoResultAndError:
    """No-result and error cases should be distinctly represented."""

    def test_unrouted_query_returns_no_result_with_error_status(self):
        qr = execute_natural_query("xyzzy flurble garbanzo")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_status == "error"
        assert qr.result_reason == "unrouted"

    def test_no_data_returns_no_result(self):
        qr = execute_natural_query("Jokic summary 1950-51")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason in ("no_data", "no_match")

    def test_no_result_preserves_metadata(self):
        qr = execute_natural_query("xyzzy flurble garbanzo")
        assert qr.metadata["query_text"] == "xyzzy flurble garbanzo"


# ===================================================================
# QueryResult envelope
# ===================================================================


class TestQueryResultEnvelope:
    """QueryResult should provide a clean envelope API."""

    def test_to_dict_includes_metadata(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        d = qr.to_dict()
        assert "metadata" in d

    def test_to_dict_includes_sections(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        d = qr.to_dict()
        if qr.is_ok:
            assert "sections" in d
            assert "summary" in d["sections"]

    @pytest.mark.needs_data
    def test_is_ok_true_for_valid_result(self):
        qr = execute_natural_query("Jokic summary 2024-25")
        assert qr.is_ok is True

    def test_is_ok_false_for_no_result(self):
        qr = execute_natural_query("xyzzy flurble garbanzo")
        assert qr.is_ok is False


# ===================================================================
# CLI rendering through the service
# ===================================================================


class TestCLIRenderingThroughService:
    """The run() function should call the service and still produce correct output."""

    @pytest.mark.needs_data
    def test_natural_query_pretty_output(self):
        from nbatools.commands.natural_query import run as natural_query_run

        out = _capture(natural_query_run, "Jokic summary 2024-25", pretty=True)
        assert "Nikola Jokić" in out
        assert "Games:" in out

    @pytest.mark.needs_data
    def test_natural_query_raw_output(self):
        from nbatools.commands.natural_query import run as natural_query_run

        out = _capture(natural_query_run, "Jokic summary 2024-25", pretty=False)
        assert "METADATA" in out
        assert "SUMMARY" in out
        assert "player_game_summary" in out

    def test_unrouted_natural_query_reports_error(self):
        from nbatools.commands.natural_query import run as natural_query_run

        out = _capture(natural_query_run, "xyzzy flurble garbanzo", pretty=False)
        assert "ERROR" in out
        assert "unrouted" in out


# ===================================================================
# Export parity
# ===================================================================


@pytest.mark.slow
@pytest.mark.needs_data
class TestExportParity:
    """Exports should produce the same semantics after refactoring."""

    def test_natural_query_csv_export(self, tmp_path):
        from nbatools.commands.natural_query import run as natural_query_run

        csv_path = tmp_path / "test.csv"
        _capture(
            natural_query_run,
            "Jokic summary 2024-25",
            pretty=False,
            export_csv_path=str(csv_path),
        )
        assert csv_path.exists()
        text = csv_path.read_text()
        assert "SUMMARY" in text

    def test_natural_query_json_export(self, tmp_path):
        from nbatools.commands.natural_query import run as natural_query_run

        json_path = tmp_path / "test.json"
        _capture(
            natural_query_run,
            "Jokic summary 2024-25",
            pretty=False,
            export_json_path=str(json_path),
        )
        assert json_path.exists()
        payload = json.loads(json_path.read_text())
        assert "metadata" in payload
        assert "summary" in payload

    def test_natural_query_txt_export(self, tmp_path):
        from nbatools.commands.natural_query import run as natural_query_run

        txt_path = tmp_path / "test.txt"
        _capture(
            natural_query_run,
            "Jokic summary 2024-25",
            pretty=True,
            export_txt_path=str(txt_path),
        )
        assert txt_path.exists()
        text = txt_path.read_text()
        assert "Nikola Jokić" in text

    def test_structured_query_csv_export(self, tmp_path):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.season_leaders import run as season_leaders_run

        csv_path = tmp_path / "leaders.csv"
        _capture(
            _run_and_handle_exports,
            season_leaders_run,
            season="2024-25",
            stat="pts",
            limit=5,
            season_type="Regular Season",
            min_games=1,
            ascending=False,
            csv=str(csv_path),
        )
        assert csv_path.exists()
        text = csv_path.read_text()
        assert "player_name" in text

    def test_structured_query_json_export(self, tmp_path):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.season_leaders import run as season_leaders_run

        json_path = tmp_path / "leaders.json"
        _capture(
            _run_and_handle_exports,
            season_leaders_run,
            season="2024-25",
            stat="pts",
            limit=5,
            season_type="Regular Season",
            min_games=1,
            ascending=False,
            json_path=str(json_path),
        )
        assert json_path.exists()
        payload = json.loads(json_path.read_text())
        assert "metadata" in payload
        assert "leaderboard" in payload


# ===================================================================
# Opponent-conference team records
# ===================================================================


@pytest.mark.needs_data
class TestOpponentConferenceTeamRecords:
    def test_celtics_current_season_record_against_east(self):
        qr = execute_natural_query("Celtics record against the East this season")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "BOS"
        assert qr.metadata["season"] == "2025-26"
        assert qr.metadata["opponent_conference"] == "East"
        assert len(qr.metadata["opponent_team_abbrs"]) == 15
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert {
            "label": "Opponent conference",
            "value": "East",
            "kind": "conference",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        assert set(sections) >= {"summary", "by_season"}
        assert sections["summary"][0]["games"] == 52
        assert sections["summary"][0]["wins"] == 36
        assert sections["summary"][0]["losses"] == 16

    def test_lakers_default_season_record_against_west(self):
        qr = execute_natural_query("Lakers record against the West")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "LAL"
        assert qr.metadata["season"] == "2025-26"
        assert qr.metadata["opponent_conference"] == "West"
        assert len(qr.metadata["opponent_team_abbrs"]) == 15
        assert {
            "label": "Opponent conference",
            "value": "West",
            "kind": "conference",
        } in qr.metadata["applied_filters"]

        sections = qr.to_dict()["sections"]
        assert set(sections) >= {"summary", "by_season"}
        assert sections["summary"][0]["games"] == 52
        assert sections["summary"][0]["wins"] == 33
        assert sections["summary"][0]["losses"] == 19

    def test_lakers_road_record_against_west_last_season_composes_filters(self):
        qr = execute_natural_query("Lakers road record against West last season")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "LAL"
        assert qr.metadata["season"] == "2024-25"
        assert qr.metadata["explicit_relative_season"] is True
        assert qr.metadata["opponent_conference"] == "West"
        assert {"label": "Location", "value": "Away", "kind": "location"} in qr.metadata[
            "applied_filters"
        ]
        assert {
            "label": "Opponent conference",
            "value": "West",
            "kind": "conference",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 26
        assert summary["wins"] == 14
        assert summary["losses"] == 12

    def test_knicks_record_against_eastern_conference_since_january_1_composes_date(self):
        qr = execute_natural_query("Knicks record against Eastern Conference teams since January 1")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "NYK"
        assert qr.metadata["opponent_conference"] == "East"
        assert qr.metadata["start_date"] == "2026-01-01"
        assert {
            "label": "Opponent conference",
            "value": "East",
            "kind": "conference",
        } in qr.metadata["applied_filters"]
        assert {
            "label": "Date range",
            "value": "2026-01-01 – 2026-04-12",
            "kind": "date",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 26
        assert summary["wins"] == 17
        assert summary["losses"] == 9

    def test_east_coast_teams_remains_unsupported_without_broad_record(self):
        qr = execute_natural_query("Celtics record against east coast teams")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["unsupported_filters"] == ["opponent_conference"]
        assert qr.to_dict()["sections"] == {}

    def test_missing_conference_coverage_returns_no_result_without_broad_record(self):
        qr = execute_natural_query("Celtics record against the East in 2023-24")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["opponent_conference"] == "East"
        assert qr.metadata["unsupported_filters"] == ["conference_coverage"]
        assert qr.to_dict()["sections"] == {}

    def test_missing_conference_membership_file_uses_coverage_guardrail(self, monkeypatch):
        import nbatools.commands._natural_query_execution as execution

        def missing_membership_file(*args, **kwargs):
            raise FileNotFoundError(
                "Missing team conference membership file: "
                "data/raw/teams/team_conference_membership.csv"
            )

        monkeypatch.setattr(execution, "get_teams_by_conference", missing_membership_file)

        qr = execute_natural_query("Celtics record against the East this season")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["opponent_conference"] == "East"
        assert qr.metadata["unsupported_filters"] == ["conference_coverage"]
        assert qr.to_dict()["sections"] == {}

    def test_conference_record_matches_explicit_opponent_list(self):
        natural = execute_natural_query("Celtics record against the East this season")
        explicit = execute_structured_query(
            "team_record",
            team="BOS",
            season="2025-26",
            season_type="Regular Season",
            opponent=get_teams_by_conference("2025-26", "East"),
        )

        assert natural.to_dict()["sections"]["summary"] == explicit.to_dict()["sections"]["summary"]
        assert (
            natural.to_dict()["sections"]["by_season"]
            == explicit.to_dict()["sections"]["by_season"]
        )


# ===================================================================
# Opponent-division team records
# ===================================================================


@pytest.mark.needs_data
class TestOpponentDivisionTeamRecords:
    def test_celtics_current_season_record_against_atlantic(self):
        qr = execute_natural_query("Celtics record vs Atlantic Division")

        assert qr.route == "team_record"
        assert qr.result.result_status == "ok"
        assert qr.metadata["team"] == "BOS"
        assert qr.metadata["season"] == "2025-26"
        assert qr.metadata["opponent_division"] == "Atlantic"
        assert len(qr.metadata["opponent_team_abbrs"]) == 5
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert {
            "label": "Opponent division",
            "value": "Atlantic",
            "kind": "division",
        } in qr.metadata["applied_filters"]

        summary = qr.to_dict()["sections"]["summary"][0]
        assert summary["games"] == 16
        assert summary["wins"] == 10
        assert summary["losses"] == 6

    def test_division_record_matches_explicit_opponent_list(self):
        natural = execute_natural_query("Lakers record against Pacific Division")
        explicit = execute_structured_query(
            "team_record",
            team="LAL",
            season="2025-26",
            season_type="Regular Season",
            opponent=get_teams_by_division("2025-26", "Pacific"),
        )

        assert natural.to_dict()["sections"]["summary"] == explicit.to_dict()["sections"]["summary"]
        assert (
            natural.to_dict()["sections"]["by_season"]
            == explicit.to_dict()["sections"]["by_season"]
        )

    def test_missing_division_coverage_returns_no_result_without_broad_record(self):
        qr = execute_natural_query("Celtics record vs Atlantic Division in 2023-24")

        assert qr.route == "team_record"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["opponent_division"] == "Atlantic"
        assert qr.metadata["unsupported_filters"] == ["division_coverage"]
        assert qr.to_dict()["sections"] == {}


@pytest.mark.needs_data
class TestOpponentDivisionTeamRecordLeaderboards:
    def test_current_season_record_leaderboard_against_northwest(self):
        qr = execute_natural_query("record against Northwest Division teams")

        assert qr.route == "team_record_leaderboard"
        assert qr.result.result_status == "ok"
        assert qr.metadata["season"] == "2025-26"
        assert qr.metadata["season_type"] == "Regular Season"
        assert qr.metadata["opponent_division"] == "Northwest"
        assert qr.metadata["opponent_team_abbrs"] == ["DEN", "MIN", "OKC", "POR", "UTA"]
        assert (
            "unsupported_filters" not in qr.metadata or qr.metadata["unsupported_filters"] is None
        )
        assert {
            "label": "Opponent division",
            "value": "Northwest",
            "kind": "division",
        } in qr.metadata["applied_filters"]

        leaderboard = qr.to_dict()["sections"]["leaderboard"]
        assert len(leaderboard) == 10
        assert leaderboard[0]["team_abbr"] == "DET"
        assert leaderboard[0]["wins"] == 8
        assert leaderboard[0]["losses"] == 2
        assert leaderboard[0]["win_pct"] == 0.8

    def test_division_record_leaderboard_matches_explicit_opponent_list(self):
        natural = execute_natural_query("team records vs Pacific Division")
        explicit = execute_structured_query(
            "team_record_leaderboard",
            season="2025-26",
            season_type="Regular Season",
            stat="win_pct",
            opponent=get_teams_by_division("2025-26", "Pacific"),
            limit=10,
            ascending=False,
        )

        assert (
            natural.to_dict()["sections"]["leaderboard"]
            == explicit.to_dict()["sections"]["leaderboard"]
        )

    def test_playoff_division_record_leaderboard_stays_unsupported(self):
        qr = execute_natural_query("playoff record against Northwest Division teams")

        assert qr.route == "team_record_leaderboard"
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"
        assert qr.metadata["season_type"] == "Playoffs"
        assert qr.metadata["opponent_division"] == "Northwest"
        assert qr.metadata["unsupported_filters"] == ["opponent_division"]
        assert qr.to_dict()["sections"] == {}


# ===================================================================
# Service entry points via __init__
# ===================================================================


class TestPublicAPI:
    """The query service should be importable from nbatools."""

    def test_import_from_package(self):
        from nbatools import QueryResult, execute_natural_query, execute_structured_query

        assert callable(execute_natural_query)
        assert callable(execute_structured_query)
        assert QueryResult is not None

    def test_result_types_importable_from_service(self):
        from nbatools.query_service import (
            ResultStatus,
            SummaryResult,
        )

        assert SummaryResult is not None
        assert ResultStatus.OK == "ok"


# ===================================================================
# render_query_result
# ===================================================================


class TestRenderQueryResult:
    """render_query_result should produce correct console and export output."""

    @pytest.mark.needs_data
    def test_render_pretty(self):
        from nbatools.commands.natural_query import render_query_result

        qr = execute_natural_query("Jokic summary 2024-25")
        out = _capture(render_query_result, qr, "Jokic summary 2024-25", pretty=True)
        assert "Nikola Jokić" in out
        assert "Games:" in out

    @pytest.mark.needs_data
    def test_render_raw(self):
        from nbatools.commands.natural_query import render_query_result

        qr = execute_natural_query("Jokic summary 2024-25")
        out = _capture(render_query_result, qr, "Jokic summary 2024-25", pretty=False)
        assert "METADATA" in out
        assert "SUMMARY" in out

    def test_render_with_exports(self, tmp_path):
        from nbatools.commands.natural_query import render_query_result

        csv_path = tmp_path / "r.csv"
        json_path = tmp_path / "r.json"
        txt_path = tmp_path / "r.txt"

        qr = execute_natural_query("Jokic summary 2024-25")
        _capture(
            render_query_result,
            qr,
            "Jokic summary 2024-25",
            pretty=True,
            export_csv_path=str(csv_path),
            export_json_path=str(json_path),
            export_txt_path=str(txt_path),
        )
        assert csv_path.exists()
        assert json_path.exists()
        assert txt_path.exists()

    def test_render_no_result(self):
        from nbatools.commands.natural_query import render_query_result

        qr = execute_natural_query("razzmatazz furblequop")
        out = _capture(render_query_result, qr, "razzmatazz furblequop", pretty=False)
        assert "ERROR" in out or "NO_RESULT" in out
