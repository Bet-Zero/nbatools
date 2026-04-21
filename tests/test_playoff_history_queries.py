"""Tests for playoff history, era-bucket, and round-specific queries.

Covers:
- Era-bucket / by-decade queries
- Playoff appearance queries
- Playoff round-specific record queries
- Playoff matchup history queries
- By-decade leaderboard queries
- Structured query support
- Service/API compatibility
"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.engine

# ---------------------------------------------------------------------------
# Unit tests for playoff_history module internals
# ---------------------------------------------------------------------------


class TestPlayoffRoundExtraction(unittest.TestCase):
    """Test round extraction from game_ids."""

    def test_extract_round_first_round(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        assert extract_playoff_round("0042300111") == "01"

    def test_extract_round_second_round(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        assert extract_playoff_round("0042300211") == "02"

    def test_extract_round_conference_finals(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        assert extract_playoff_round("0042300311") == "03"

    def test_extract_round_finals(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        assert extract_playoff_round("0042300411") == "04"

    def test_extract_round_old_format_returns_none(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        # Old format (pre-2001) has "00" at positions 6-7
        assert extract_playoff_round("0049600001") is None

    def test_extract_round_short_id(self):
        from nbatools.commands.playoff_history import extract_playoff_round

        assert extract_playoff_round("00423") is None


class TestRoundCodeToLabel(unittest.TestCase):
    def test_all_codes(self):
        from nbatools.commands.playoff_history import round_code_to_label

        assert round_code_to_label("01") == "First Round"
        assert round_code_to_label("02") == "Second Round"
        assert round_code_to_label("03") == "Conference Finals"
        assert round_code_to_label("04") == "Finals"


class TestResolveRoundFilter(unittest.TestCase):
    def test_finals(self):
        from nbatools.commands.playoff_history import resolve_round_filter

        assert resolve_round_filter("finals") == "04"
        assert resolve_round_filter("nba finals") == "04"
        assert resolve_round_filter("the finals") == "04"
        assert resolve_round_filter("championship") == "04"

    def test_conference_finals(self):
        from nbatools.commands.playoff_history import resolve_round_filter

        assert resolve_round_filter("conference finals") == "03"
        assert resolve_round_filter("conf finals") == "03"

    def test_second_round(self):
        from nbatools.commands.playoff_history import resolve_round_filter

        assert resolve_round_filter("second round") == "02"
        assert resolve_round_filter("2nd round") == "02"
        assert resolve_round_filter("semifinals") == "02"

    def test_first_round(self):
        from nbatools.commands.playoff_history import resolve_round_filter

        assert resolve_round_filter("first round") == "01"
        assert resolve_round_filter("1st round") == "01"

    def test_no_match(self):
        from nbatools.commands.playoff_history import resolve_round_filter

        assert resolve_round_filter("random text") is None


class TestSeasonToDecade(unittest.TestCase):
    def test_various_decades(self):
        from nbatools.commands.playoff_history import season_to_decade

        assert season_to_decade("1999-00") == "1990s"
        assert season_to_decade("2003-04") == "2000s"
        assert season_to_decade("2019-20") == "2010s"
        assert season_to_decade("2023-24") == "2020s"

    def test_decade_boundary(self):
        from nbatools.commands.playoff_history import season_to_decade

        assert season_to_decade("2009-10") == "2000s"
        assert season_to_decade("2010-11") == "2010s"


class TestHasRoundData(unittest.TestCase):
    def test_modern_season(self):
        from nbatools.commands.playoff_history import _has_round_data

        assert _has_round_data(["2023-24"]) is True
        assert _has_round_data(["2001-02"]) is True

    def test_old_season(self):
        from nbatools.commands.playoff_history import _has_round_data

        assert _has_round_data(["1999-00"]) is False

    def test_mixed_seasons(self):
        from nbatools.commands.playoff_history import _has_round_data

        assert _has_round_data(["1999-00", "2005-06"]) is True


# ---------------------------------------------------------------------------
# Natural query intent detection tests
# ---------------------------------------------------------------------------


class TestPlayoffIntentDetection(unittest.TestCase):
    """Test new intent detection functions."""

    def test_detect_by_decade_intent(self):
        from nbatools.commands.natural_query import detect_by_decade_intent

        assert detect_by_decade_intent("lakers vs celtics by decade") is True
        assert detect_by_decade_intent("most wins by decade since 1980") is True
        assert detect_by_decade_intent("lakers playoff record") is False

    def test_detect_playoff_appearance_intent(self):
        from nbatools.commands.natural_query import detect_playoff_appearance_intent

        assert detect_playoff_appearance_intent("most finals appearances since 2000") is True
        assert detect_playoff_appearance_intent("lakers playoff appearances since 1990") is True
        assert detect_playoff_appearance_intent("conference finals appearances since 2000") is True
        assert detect_playoff_appearance_intent("second round appearances") is True
        assert detect_playoff_appearance_intent("lakers playoff record") is False

    def test_detect_playoff_history_intent(self):
        from nbatools.commands.natural_query import detect_playoff_history_intent

        assert detect_playoff_history_intent("lakers playoff history") is True
        assert detect_playoff_history_intent("celtics postseason history") is True
        assert detect_playoff_history_intent("knicks playoff series vs heat") is True
        assert detect_playoff_history_intent("lakers career averages") is False

    def test_detect_playoff_round_filter(self):
        from nbatools.commands.natural_query import detect_playoff_round_filter

        assert detect_playoff_round_filter("best finals record since 1980") == "04"
        assert detect_playoff_round_filter("most conference finals appearances since 2000") == "03"
        assert detect_playoff_round_filter("second round appearances") == "02"
        assert detect_playoff_round_filter("first round record") == "01"
        assert detect_playoff_round_filter("lakers playoff record") is None

    def test_detect_by_round_intent(self):
        from nbatools.commands.natural_query import detect_by_round_intent

        assert detect_by_round_intent("celtics vs bucks playoff history by round") is True
        assert detect_by_round_intent("celtics vs bucks playoff history") is False


# ---------------------------------------------------------------------------
# Natural query routing tests
# ---------------------------------------------------------------------------


class TestPlayoffHistoryRouting(unittest.TestCase):
    """Test that playoff/decade queries route to the correct route."""

    def _parse(self, query: str) -> dict:
        from nbatools.commands.natural_query import parse_query

        return parse_query(query)

    def test_by_decade_team_routes(self):
        """'Lakers by decade' → record_by_decade."""
        result = self._parse("lakers playoff summary by decade")
        assert result["route"] in ("record_by_decade", "playoff_history"), result["route"]

    def test_by_decade_matchup_routes(self):
        """'Lakers vs Celtics by decade' → matchup_by_decade."""
        result = self._parse("lakers vs celtics by decade")
        assert result["route"] == "matchup_by_decade", result["route"]

    def test_playoffs_appearance_leaderboard_routes(self):
        """'Most finals appearances since 2000' → playoff_appearances."""
        result = self._parse("most finals appearances since 2000")
        assert result["route"] == "playoff_appearances", result["route"]

    def test_team_playoff_appearances_routes(self):
        """'Lakers playoff appearances since 1990' → playoff_appearances."""
        result = self._parse("lakers playoff appearances since 1990")
        assert result["route"] == "playoff_appearances", result["route"]

    def test_team_finals_appearances_routes(self):
        """'Lakers finals appearances by decade' → playoff_appearances."""
        result = self._parse("lakers finals appearances since 2000")
        assert result["route"] == "playoff_appearances", result["route"]

    def test_playoff_history_routes(self):
        """'Celtics playoff history' → playoff_history."""
        result = self._parse("celtics playoff history since 2000")
        assert result["route"] == "playoff_history", result["route"]

    def test_playoff_matchup_history_routes(self):
        """'Knicks playoff history vs Heat' → playoff_matchup_history."""
        result = self._parse("knicks vs heat playoff history since 1999")
        assert result["route"] == "playoff_matchup_history", result["route"]

    def test_playoff_series_matchup_routes(self):
        """'Lakers playoff series record vs Celtics' → playoff_matchup_history."""
        result = self._parse("lakers vs celtics playoff series since 2000")
        assert result["route"] == "playoff_matchup_history", result["route"]

    def test_by_round_matchup_routes(self):
        """'Celtics vs Bucks playoff history by round' → playoff_matchup_history."""
        result = self._parse("celtics vs bucks playoff history by round since 2000")
        assert result["route"] == "playoff_matchup_history", result["route"]
        assert result["route_kwargs"].get("by_round") is True

    def test_best_finals_record_routes(self):
        """'Best finals record since 1980' → playoff_round_record."""
        result = self._parse("best finals record since 1980")
        assert result["route"] == "playoff_round_record", result["route"]

    def test_record_by_decade_leaderboard_routes(self):
        """'Most wins by decade since 1980' → record_by_decade_leaderboard."""
        result = self._parse("most wins by decade since 1980")
        assert result["route"] == "record_by_decade_leaderboard", result["route"]

    def test_best_playoff_record_by_decade_routes(self):
        """'Best playoff record by decade since 1980'."""
        result = self._parse("best playoff record by decade since 1980")
        assert result["route"] == "record_by_decade_leaderboard", result["route"]

    def test_conference_finals_appearances_routes(self):
        """'Most conference finals appearances since 2000' → playoff_appearances."""
        result = self._parse("most conference finals appearances since 2000")
        assert result["route"] == "playoff_appearances", result["route"]
        assert result["route_kwargs"].get("playoff_round") == "03"


# ---------------------------------------------------------------------------
# Build-result integration tests (require data files)
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestPlayoffHistoryBuildResult(unittest.TestCase):
    """Integration tests for playoff history build functions.

    These require actual data files to be present.
    """

    def test_build_playoff_history_result(self):
        """Build a single-team playoff history summary."""
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="BOS",
            start_season="2020-21",
            end_season="2024-25",
        )
        # Should return SummaryResult
        assert result.query_class == "summary", f"Expected summary, got {result.query_class}"
        assert result.result_status == "ok"
        assert not result.summary.empty
        assert "team_name" in result.summary.columns
        assert "wins" in result.summary.columns
        assert "losses" in result.summary.columns
        # Should have by_season breakdown
        assert result.by_season is not None
        assert not result.by_season.empty

    def test_build_playoff_history_by_round(self):
        """Build a team playoff history filtered to Finals."""
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="BOS",
            start_season="2020-21",
            end_season="2024-25",
            playoff_round="04",
        )
        if result.result_status == "ok":
            assert "playoff_round" in result.summary.columns
            assert result.summary["playoff_round"].iloc[0] == "Finals"

    def test_build_playoff_history_by_decade(self):
        """Build a team playoff history by decade."""
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="LAL",
            start_season="2001-02",
            end_season="2024-25",
            by_decade=True,
        )
        assert result.result_status == "ok"
        # by_season field should contain decade breakdown
        assert result.by_season is not None
        if not result.by_season.empty:
            assert "decade" in result.by_season.columns

    def test_build_playoff_history_vs_opponent(self):
        """Build playoff history filtered by opponent."""
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="BOS",
            start_season="2001-02",
            end_season="2024-25",
            opponent="MIA",
        )
        if result.result_status == "ok":
            assert "wins" in result.summary.columns

    def test_build_playoff_history_no_match(self):
        """Build playoff history for a team/span with no data."""
        from nbatools.commands.playoff_history import build_playoff_history_result
        from nbatools.commands.structured_results import NoResult

        result = build_playoff_history_result(
            team="FAKE",
            start_season="2020-21",
            end_season="2024-25",
        )
        assert isinstance(result, NoResult)


@pytest.mark.needs_data
class TestPlayoffAppearancesBuildResult(unittest.TestCase):
    """Integration tests for playoff appearances."""

    def test_appearances_leaderboard(self):
        """Build a leaderboard of most playoff appearances."""
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            start_season="2010-11",
            end_season="2024-25",
            limit=10,
        )
        assert result.query_class == "leaderboard"
        assert result.result_status == "ok"
        assert not result.leaders.empty
        assert "appearances" in result.leaders.columns
        assert "rank" in result.leaders.columns
        assert len(result.leaders) <= 10

    def test_finals_appearances_leaderboard(self):
        """Build a leaderboard of most Finals appearances."""
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="04",
            limit=10,
        )
        assert result.query_class == "leaderboard"
        assert result.result_status == "ok"
        if not result.leaders.empty:
            assert "appearances" in result.leaders.columns
            assert result.leaders["round"].iloc[0] == "Finals"

    def test_conference_finals_appearances(self):
        """Build a leaderboard of most conference finals appearances."""
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="03",
            limit=10,
        )
        assert result.result_status == "ok"

    def test_single_team_appearances(self):
        """Build appearances count for a single team."""
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            team="BOS",
            start_season="2010-11",
            end_season="2024-25",
        )
        # Should return SummaryResult for single team
        assert result.query_class == "summary"
        assert result.result_status == "ok"
        assert "appearances" in result.summary.columns

    def test_single_team_finals_appearances(self):
        """Build Finals appearances for a single team."""
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            team="BOS",
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="04",
        )
        if result.result_status == "ok":
            assert result.query_class == "summary"
            assert "appearances" in result.summary.columns


@pytest.mark.needs_data
class TestRecordByDecadeBuildResult(unittest.TestCase):
    """Integration tests for record-by-decade."""

    def test_team_record_by_decade(self):
        """Build a team record by decade (playoffs)."""
        from nbatools.commands.playoff_history import build_record_by_decade_result

        result = build_record_by_decade_result(
            team="LAL",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Playoffs",
        )
        assert result.result_status == "ok"
        assert result.query_class == "summary"
        assert result.by_season is not None
        if not result.by_season.empty:
            assert "decade" in result.by_season.columns

    def test_team_record_by_decade_regular_season(self):
        """Build a team record by decade (regular season)."""
        from nbatools.commands.playoff_history import build_record_by_decade_result

        result = build_record_by_decade_result(
            team="BOS",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Regular Season",
        )
        assert result.result_status == "ok"
        assert result.by_season is not None
        if not result.by_season.empty:
            assert "decade" in result.by_season.columns
            assert "wins" in result.by_season.columns

    def test_record_by_decade_leaderboard(self):
        """Build a record leaderboard by decade."""
        from nbatools.commands.playoff_history import (
            build_record_by_decade_leaderboard_result,
        )

        result = build_record_by_decade_leaderboard_result(
            start_season="2001-02",
            end_season="2024-25",
            season_type="Regular Season",
            stat="wins",
            limit=5,
        )
        assert result.result_status == "ok"
        assert result.query_class == "leaderboard"
        assert not result.leaders.empty
        assert "decade" in result.leaders.columns
        assert "wins" in result.leaders.columns

    def test_record_by_decade_leaderboard_playoffs(self):
        """Build a playoff record leaderboard by decade."""
        from nbatools.commands.playoff_history import (
            build_record_by_decade_leaderboard_result,
        )

        result = build_record_by_decade_leaderboard_result(
            start_season="2001-02",
            end_season="2024-25",
            season_type="Playoffs",
            stat="wins",
            limit=5,
        )
        assert result.result_status == "ok"
        assert "decade" in result.leaders.columns


@pytest.mark.needs_data
class TestMatchupByDecadeBuildResult(unittest.TestCase):
    """Integration tests for matchup-by-decade."""

    def test_matchup_by_decade_regular(self):
        """Build a matchup record by decade."""
        from nbatools.commands.playoff_history import build_matchup_by_decade_result

        result = build_matchup_by_decade_result(
            team_a="LAL",
            team_b="BOS",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Regular Season",
        )
        assert result.result_status == "ok"
        assert result.query_class == "comparison"
        assert not result.summary.empty
        assert not result.comparison.empty
        assert "decade" in result.comparison.columns

    def test_matchup_by_decade_playoffs(self):
        """Build a playoff matchup record by decade."""
        from nbatools.commands.playoff_history import build_matchup_by_decade_result

        result = build_matchup_by_decade_result(
            team_a="BOS",
            team_b="MIA",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Playoffs",
        )
        if result.result_status == "ok":
            assert result.query_class == "comparison"
            assert "decade" in result.comparison.columns


@pytest.mark.needs_data
class TestPlayoffMatchupHistoryBuildResult(unittest.TestCase):
    """Integration tests for playoff matchup history."""

    def test_playoff_matchup_history(self):
        """Build playoff matchup history between two teams."""
        from nbatools.commands.playoff_history import (
            build_playoff_matchup_history_result,
        )

        result = build_playoff_matchup_history_result(
            team_a="BOS",
            team_b="MIA",
            start_season="2001-02",
            end_season="2024-25",
        )
        if result.result_status == "ok":
            assert result.query_class == "comparison"
            assert not result.summary.empty
            # Comparison should show season-level breakdown
            assert not result.comparison.empty

    def test_playoff_matchup_by_round(self):
        """Build playoff matchup history by round."""
        from nbatools.commands.playoff_history import (
            build_playoff_matchup_history_result,
        )

        result = build_playoff_matchup_history_result(
            team_a="BOS",
            team_b="MIA",
            start_season="2001-02",
            end_season="2024-25",
            by_round=True,
        )
        if result.result_status == "ok":
            assert result.query_class == "comparison"
            if not result.comparison.empty:
                assert "round" in result.comparison.columns

    def test_playoff_matchup_no_match(self):
        """Playoff matchup with no historical playoff games."""
        from nbatools.commands.playoff_history import (
            build_playoff_matchup_history_result,
        )
        from nbatools.commands.structured_results import NoResult

        result = build_playoff_matchup_history_result(
            team_a="FAKE1",
            team_b="FAKE2",
            start_season="2020-21",
            end_season="2024-25",
        )
        assert isinstance(result, NoResult)


@pytest.mark.needs_data
class TestPlayoffRoundRecordBuildResult(unittest.TestCase):
    """Integration tests for round-specific record leaderboard."""

    def test_best_finals_record(self):
        """Build 'best finals record' leaderboard."""
        from nbatools.commands.playoff_history import (
            build_playoff_round_record_result,
        )

        result = build_playoff_round_record_result(
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="04",
            stat="win_pct",
            limit=10,
        )
        assert result.result_status == "ok"
        if result.query_class == "leaderboard":
            assert not result.leaders.empty
            assert "round" in result.leaders.columns
            assert result.leaders["round"].iloc[0] == "Finals"

    def test_most_conf_finals_wins(self):
        """Build 'most conference finals wins' leaderboard."""
        from nbatools.commands.playoff_history import (
            build_playoff_round_record_result,
        )

        result = build_playoff_round_record_result(
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="03",
            stat="wins",
            limit=10,
        )
        assert result.result_status == "ok"

    def test_no_round_all_playoffs(self):
        """Build leaderboard for all rounds (no round filter)."""
        from nbatools.commands.playoff_history import (
            build_playoff_round_record_result,
        )

        result = build_playoff_round_record_result(
            start_season="2010-11",
            end_season="2024-25",
            stat="wins",
            limit=10,
        )
        assert result.result_status == "ok"


# ---------------------------------------------------------------------------
# Query service integration tests
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestPlayoffHistoryQueryService(unittest.TestCase):
    """Test that the query service properly handles new routes."""

    def test_structured_playoff_history(self):
        """Structured query for playoff_history route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "playoff_history",
            team="BOS",
            start_season="2020-21",
            end_season="2024-25",
        )
        assert qr.is_ok

    def test_structured_playoff_appearances(self):
        """Structured query for playoff_appearances route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "playoff_appearances",
            start_season="2010-11",
            end_season="2024-25",
            limit=10,
        )
        assert qr.is_ok

    def test_structured_playoff_appearances_finals(self):
        """Structured query for finals appearances."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "playoff_appearances",
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="04",
            limit=10,
        )
        assert qr.is_ok

    def test_structured_record_by_decade(self):
        """Structured query for record_by_decade route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "record_by_decade",
            team="LAL",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Regular Season",
        )
        assert qr.is_ok

    def test_structured_matchup_by_decade(self):
        """Structured query for matchup_by_decade route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "matchup_by_decade",
            team_a="LAL",
            team_b="BOS",
            start_season="2001-02",
            end_season="2024-25",
        )
        assert qr.is_ok

    def test_structured_playoff_matchup_history(self):
        """Structured query for playoff_matchup_history route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "playoff_matchup_history",
            team_a="BOS",
            team_b="MIA",
            start_season="2001-02",
            end_season="2024-25",
        )
        # May be no_result if no matchups exist, but should not error
        assert qr.result_status in ("ok", "no_result")

    def test_structured_playoff_round_record(self):
        """Structured query for playoff_round_record route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "playoff_round_record",
            start_season="2001-02",
            end_season="2024-25",
            playoff_round="04",
            stat="wins",
            limit=10,
        )
        assert qr.is_ok

    def test_structured_record_by_decade_leaderboard(self):
        """Structured query for record_by_decade_leaderboard route."""
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "record_by_decade_leaderboard",
            start_season="2001-02",
            end_season="2024-25",
            season_type="Regular Season",
            stat="wins",
            limit=5,
        )
        assert qr.is_ok

    def test_valid_routes_include_new(self):
        """Verify new routes are in VALID_ROUTES."""
        from nbatools.query_service import VALID_ROUTES

        assert "playoff_history" in VALID_ROUTES
        assert "playoff_appearances" in VALID_ROUTES
        assert "playoff_matchup_history" in VALID_ROUTES
        assert "playoff_round_record" in VALID_ROUTES
        assert "record_by_decade" in VALID_ROUTES
        assert "record_by_decade_leaderboard" in VALID_ROUTES
        assert "matchup_by_decade" in VALID_ROUTES


# ---------------------------------------------------------------------------
# Natural query -> result integration tests
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestPlayoffHistoryNaturalQueryEndToEnd(unittest.TestCase):
    """End-to-end tests: natural query → query service → result."""

    def test_celtics_playoff_history(self):
        """'Celtics playoff history since 2015' returns valid result."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("celtics playoff history since 2015")
        assert qr.route == "playoff_history", f"Expected playoff_history, got {qr.route}"
        assert qr.result_status in ("ok", "no_result")

    def test_most_finals_appearances(self):
        """'Most finals appearances since 2000' returns leaderboard."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("most finals appearances since 2000")
        assert qr.route == "playoff_appearances", f"Expected playoff_appearances, got {qr.route}"
        if qr.is_ok:
            d = qr.to_dict()
            assert d.get("query_class") in ("leaderboard", "summary")

    def test_lakers_vs_celtics_by_decade(self):
        """'Lakers vs Celtics by decade' returns comparison."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("lakers vs celtics by decade")
        assert qr.route == "matchup_by_decade", f"Expected matchup_by_decade, got {qr.route}"
        if qr.is_ok:
            d = qr.to_dict()
            assert d.get("query_class") == "comparison"

    def test_best_finals_record(self):
        """'Best finals record since 2001' returns leaderboard."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("best finals record since 2001")
        assert qr.route == "playoff_round_record", f"Expected playoff_round_record, got {qr.route}"

    def test_most_wins_by_decade(self):
        """'Most wins by decade since 2000' returns by-decade leaderboard."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("most wins by decade since 2000")
        assert qr.route == "record_by_decade_leaderboard", (
            f"Expected record_by_decade_leaderboard, got {qr.route}"
        )

    def test_conference_finals_appearances(self):
        """'Most conference finals appearances since 2000' returns leaderboard."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("most conference finals appearances since 2000")
        assert qr.route == "playoff_appearances", f"Expected playoff_appearances, got {qr.route}"

    def test_team_playoff_appearances(self):
        """'Celtics playoff appearances since 2010' returns summary."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("celtics playoff appearances since 2010")
        assert qr.route == "playoff_appearances", f"Expected playoff_appearances, got {qr.route}"

    def test_knicks_playoff_summary_by_decade(self):
        """'Knicks playoff summary by decade' returns summary."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("knicks playoff summary by decade")
        assert qr.route in ("playoff_history", "record_by_decade"), (
            f"Expected playoff_history or record_by_decade, got {qr.route}"
        )


# ---------------------------------------------------------------------------
# Result contract tests
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestPlayoffHistoryResultContracts(unittest.TestCase):
    """Verify result objects have proper trust/status/caveat fields."""

    def test_playoff_history_result_contract(self):
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="BOS",
            start_season="2020-21",
            end_season="2024-25",
        )
        d = result.to_dict()
        assert "query_class" in d
        assert "result_status" in d
        assert "notes" in d
        assert "caveats" in d
        assert "sections" in d
        assert "metadata" in d

    def test_playoff_appearances_result_contract(self):
        from nbatools.commands.playoff_history import build_playoff_appearances_result

        result = build_playoff_appearances_result(
            start_season="2010-11",
            end_season="2024-25",
        )
        d = result.to_dict()
        assert "query_class" in d
        assert "result_status" in d
        assert d["query_class"] == "leaderboard"
        # current_through should be present
        assert "current_through" in d or result.current_through is not None

    def test_round_data_caveat_for_old_seasons(self):
        """Verify caveat is added when seasons lack round data."""
        from nbatools.commands.playoff_history import build_playoff_history_result

        result = build_playoff_history_result(
            team="LAL",
            start_season="1996-97",
            end_season="2005-06",
            playoff_round="04",
        )
        # Should include a caveat about round data limitation
        if result.result_status == "ok":
            assert any("round data" in c for c in result.caveats), (
                f"Expected round data caveat, got: {result.caveats}"
            )


# ---------------------------------------------------------------------------
# Route-to-query-class mapping tests
# ---------------------------------------------------------------------------


class TestRouteToQueryClassMapping(unittest.TestCase):
    """Verify route_to_query_class includes new routes."""

    def test_new_route_mappings(self):
        from nbatools.commands.format_output import route_to_query_class

        assert route_to_query_class("playoff_history") == "summary"
        assert route_to_query_class("playoff_appearances") == "leaderboard"
        assert route_to_query_class("playoff_matchup_history") == "comparison"
        assert route_to_query_class("playoff_round_record") == "leaderboard"
        assert route_to_query_class("record_by_decade") == "summary"
        assert route_to_query_class("record_by_decade_leaderboard") == "leaderboard"
        assert route_to_query_class("matchup_by_decade") == "comparison"


if __name__ == "__main__":
    unittest.main()
