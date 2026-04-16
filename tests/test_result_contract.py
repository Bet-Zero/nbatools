"""Tests for result/error contract consistency.

Validates that:
- All result classes produce consistent to_dict() structure
- result_reason is always present in to_dict() output
- NoResult correctly handles all reason codes
- ResultStatus and ResultReason enums cover expected values
- Query service returns structured results for all edge cases
- API envelope is consistent across result statuses
- Unsupported query combinations return structured NoResult
- Ambiguous entities return structured NoResult
- Empty-DF cases return NoResult instead of empty results
"""

import pandas as pd
import pytest

from nbatools.commands.structured_results import (
    ComparisonResult,
    CountResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    ResultReason,
    ResultStatus,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)
from nbatools.query_service import (
    QueryResult,
    execute_natural_query,
    execute_structured_query,
)

pytestmark = pytest.mark.output

# ===================================================================
# ResultStatus and ResultReason enum coverage
# ===================================================================


class TestResultEnums:
    """Result enums should contain all expected values."""

    def test_result_status_values(self):
        assert ResultStatus.OK == "ok"
        assert ResultStatus.NO_RESULT == "no_result"
        assert ResultStatus.ERROR == "error"

    def test_result_reason_values(self):
        assert ResultReason.NO_MATCH == "no_match"
        assert ResultReason.NO_DATA == "no_data"
        assert ResultReason.UNROUTED == "unrouted"
        assert ResultReason.AMBIGUOUS == "ambiguous"
        assert ResultReason.UNSUPPORTED == "unsupported"
        assert ResultReason.ERROR == "error"

    def test_result_reason_has_six_values(self):
        assert len(ResultReason) == 6


# ===================================================================
# to_dict() contract consistency across all result classes
# ===================================================================


class TestToDictContract:
    """Every result class's to_dict() must include a consistent set of fields."""

    REQUIRED_FIELDS = {
        "query_class",
        "result_status",
        "result_reason",
        "metadata",
        "notes",
        "caveats",
        "sections",
    }

    def _check_required_fields(self, d: dict):
        for field in self.REQUIRED_FIELDS:
            assert field in d, f"Missing required field: {field}"

    def test_summary_result_to_dict(self):
        r = SummaryResult(
            summary=pd.DataFrame({"pts_avg": [25.0]}),
            by_season=pd.DataFrame({"season": ["2024-25"], "pts_avg": [25.0]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"
        assert d["result_reason"] is None
        assert "summary" in d["sections"]
        assert "by_season" in d["sections"]

    def test_comparison_result_to_dict(self):
        r = ComparisonResult(
            summary=pd.DataFrame({"player_name": ["A", "B"]}),
            comparison=pd.DataFrame({"metric": ["pts_avg"], "A": [25], "B": [20]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "comparison"
        assert d["result_status"] == "ok"
        assert d["result_reason"] is None
        assert "summary" in d["sections"]
        assert "comparison" in d["sections"]

    def test_split_summary_result_to_dict(self):
        r = SplitSummaryResult(
            summary=pd.DataFrame({"pts_avg": [25.0]}),
            split_comparison=pd.DataFrame({"bucket": ["home", "away"], "pts_avg": [26, 24]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "split_summary"
        assert d["result_reason"] is None
        assert "summary" in d["sections"]
        assert "split_comparison" in d["sections"]

    def test_finder_result_to_dict(self):
        r = FinderResult(
            games=pd.DataFrame({"game_date": ["2025-01-01"], "pts": [30]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "finder"
        assert d["result_reason"] is None
        assert "finder" in d["sections"]

    def test_leaderboard_result_to_dict(self):
        r = LeaderboardResult(
            leaders=pd.DataFrame({"player_name": ["A"], "pts_avg": [30]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "leaderboard"
        assert d["result_reason"] is None
        assert "leaderboard" in d["sections"]

    def test_streak_result_to_dict(self):
        r = StreakResult(
            streaks=pd.DataFrame({"player_name": ["A"], "streak_length": [5]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "streak"
        assert d["result_reason"] is None
        assert "streak" in d["sections"]

    def test_count_result_to_dict(self):
        r = CountResult(
            count=42,
            games=pd.DataFrame({"game_date": ["2025-01-01"], "pts": [30]}),
        )
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "count"
        assert d["result_reason"] is None
        assert "count" in d["sections"]
        assert d["sections"]["count"] == [{"count": 42}]

    def test_no_result_to_dict(self):
        r = NoResult(query_class="summary", reason="no_match")
        d = r.to_dict()
        self._check_required_fields(d)
        assert d["query_class"] == "summary"
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_match"
        assert d["sections"] == {}


# ===================================================================
# NoResult reason codes
# ===================================================================


class TestNoResultReasonCodes:
    """NoResult should correctly handle all reason codes."""

    @pytest.mark.parametrize(
        "reason,expected_status",
        [
            ("no_match", "no_result"),
            ("no_data", "no_result"),
            ("unrouted", "no_result"),
            ("ambiguous", "no_result"),
            ("unsupported", "no_result"),
            ("error", "no_result"),
        ],
    )
    def test_reason_codes(self, reason, expected_status):
        r = NoResult(query_class="summary", reason=reason)
        assert r.result_reason == reason
        assert r.result_status == expected_status
        d = r.to_dict()
        assert d["result_reason"] == reason

    def test_reason_fallback_to_result_reason(self):
        """If result_reason is set explicitly, it takes precedence."""
        r = NoResult(query_class="summary", reason="no_match", result_reason="no_data")
        assert r.result_reason == "no_data"

    def test_reason_default_is_no_match(self):
        r = NoResult(query_class="summary")
        assert r.result_reason == "no_match"

    def test_no_result_with_notes(self):
        r = NoResult(
            query_class="summary",
            reason="unsupported",
            notes=["Cannot use this combination"],
        )
        d = r.to_dict()
        assert d["notes"] == ["Cannot use this combination"]

    def test_no_result_with_custom_status(self):
        r = NoResult(
            query_class="unknown",
            reason="unrouted",
            result_status="error",
        )
        assert r.result_status == "error"
        assert r.result_reason == "unrouted"


# ===================================================================
# Query service edge cases
# ===================================================================


class TestServiceEdgeCases:
    """Query service should return structured results for all edge cases."""

    def test_unrouted_query(self):
        qr = execute_natural_query("xyzzy flurble garbanzo")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason == "unrouted"

    def test_invalid_structured_route(self):
        qr = execute_structured_query("nonexistent_route")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason == "unsupported"
        assert qr.result_status == "no_result"

    def test_no_data_structured_query(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
        )
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason in ("no_data", "no_match")

    @pytest.mark.needs_data
    def test_unsupported_stat_top_player_games(self):
        qr = execute_structured_query(
            "top_player_games",
            season="2024-25",
            stat="xyzzy_stat",
            limit=5,
        )
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason == "unsupported"

    @pytest.mark.needs_data
    def test_unsupported_stat_top_team_games(self):
        qr = execute_structured_query(
            "top_team_games",
            season="2024-25",
            stat="xyzzy_stat",
            limit=5,
        )
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        assert qr.result_reason == "unsupported"

    def test_unsupported_mutual_exclusivity_finder(self):
        qr = execute_structured_query(
            "player_game_finder",
            season="2024-25",
            player="Nikola Jokić",
            home_only=True,
            away_only=True,
        )
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"

    def test_unsupported_mutual_exclusivity_game_finder(self):
        qr = execute_structured_query(
            "game_finder",
            season="2024-25",
            team="BOS",
            wins_only=True,
            losses_only=True,
        )
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"

    def test_unsupported_mutual_exclusivity_player_compare(self):
        qr = execute_structured_query(
            "player_compare",
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2024-25",
            home_only=True,
            away_only=True,
        )
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"

    def test_unsupported_mutual_exclusivity_team_compare(self):
        qr = execute_structured_query(
            "team_compare",
            team_a="BOS",
            team_b="LAL",
            season="2024-25",
            home_only=True,
            away_only=True,
        )
        assert isinstance(qr.result, NoResult)
        assert qr.result_reason == "unsupported"


# ===================================================================
# API envelope consistency
# ===================================================================


class TestAPIEnvelopeConsistency:
    """API envelope should be consistent across all result statuses."""

    ENVELOPE_FIELDS = {
        "ok",
        "query",
        "route",
        "result_status",
        "result_reason",
        "current_through",
        "notes",
        "caveats",
        "result",
    }

    def _make_qr(self, result, route=None, query="test"):
        return QueryResult(result=result, query=query, route=route)

    def _to_api_dict(self, qr: QueryResult) -> dict:
        """Simulate the API envelope conversion."""
        from nbatools.api import _query_result_to_response

        response = _query_result_to_response(qr)
        return response.model_dump()

    def test_ok_envelope(self):
        result = SummaryResult(summary=pd.DataFrame({"pts_avg": [25.0]}))
        d = self._to_api_dict(self._make_qr(result, route="player_game_summary"))
        for field in self.ENVELOPE_FIELDS:
            assert field in d, f"Missing envelope field: {field}"
        assert d["ok"] is True
        assert d["result_status"] == "ok"

    def test_no_result_envelope(self):
        result = NoResult(query_class="summary", reason="no_match")
        d = self._to_api_dict(self._make_qr(result))
        for field in self.ENVELOPE_FIELDS:
            assert field in d, f"Missing envelope field: {field}"
        assert d["ok"] is False
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_match"

    def test_unsupported_envelope(self):
        result = NoResult(
            query_class="finder",
            reason="unsupported",
            result_status="no_result",
            notes=["Cannot do this"],
        )
        d = self._to_api_dict(self._make_qr(result))
        assert d["ok"] is False
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "unsupported"
        assert d["notes"] == ["Cannot do this"]

    def test_ambiguous_envelope(self):
        result = NoResult(
            query_class="unknown",
            reason="ambiguous",
            result_status="no_result",
            notes=["Multiple players matched"],
        )
        d = self._to_api_dict(self._make_qr(result))
        assert d["ok"] is False
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "ambiguous"

    def test_error_envelope(self):
        result = NoResult(query_class="unknown", reason="error", result_status="error")
        d = self._to_api_dict(self._make_qr(result))
        assert d["ok"] is False
        assert d["result_status"] == "error"
        assert d["result_reason"] == "error"

    def test_result_payload_always_has_result_reason(self):
        """The result payload (inside the envelope) should always have result_reason."""
        ok_result = SummaryResult(summary=pd.DataFrame({"pts_avg": [25.0]}))
        d = self._to_api_dict(self._make_qr(ok_result))
        # result_reason should be present in the inner result
        assert "result_reason" in d["result"]

    def test_notes_and_caveats_always_lists(self):
        result = SummaryResult(summary=pd.DataFrame({"pts_avg": [25.0]}))
        d = self._to_api_dict(self._make_qr(result))
        assert isinstance(d["notes"], list)
        assert isinstance(d["caveats"], list)

    def test_no_data_envelope(self):
        result = NoResult(query_class="summary", reason="no_data")
        d = self._to_api_dict(self._make_qr(result))
        assert d["ok"] is False
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"


# ===================================================================
# Route family normalization
# ===================================================================


@pytest.mark.needs_data
class TestRouteFamilyNormalization:
    """Each route family should produce consistent result shapes."""

    def test_finder_ok_has_finder_section(self):
        qr = execute_structured_query(
            "player_game_finder",
            season="2024-25",
            player="Nikola Jokić",
            limit=5,
        )
        if qr.is_ok:
            d = qr.result.to_dict()
            assert "finder" in d["sections"]
            assert d["result_reason"] is None

    def test_leaderboard_ok_has_leaderboard_section(self):
        qr = execute_structured_query(
            "season_leaders",
            season="2024-25",
            stat="pts",
            limit=5,
        )
        if qr.is_ok:
            d = qr.result.to_dict()
            assert "leaderboard" in d["sections"]
            assert d["result_reason"] is None

    def test_summary_ok_has_summary_section(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="2024-25",
            player="Nikola Jokić",
        )
        if qr.is_ok:
            d = qr.result.to_dict()
            assert "summary" in d["sections"]
            assert d["result_reason"] is None

    def test_comparison_ok_has_comparison_section(self):
        qr = execute_structured_query(
            "player_compare",
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2024-25",
        )
        if qr.is_ok:
            d = qr.result.to_dict()
            assert "summary" in d["sections"]
            assert "comparison" in d["sections"]
            assert d["result_reason"] is None

    def test_split_ok_has_split_section(self):
        qr = execute_structured_query(
            "player_split_summary",
            season="2024-25",
            player="Nikola Jokić",
            split="home_away",
        )
        if qr.is_ok:
            d = qr.result.to_dict()
            assert "summary" in d["sections"]
            assert "split_comparison" in d["sections"]
            assert d["result_reason"] is None


# ===================================================================
# to_dict result_reason consistency across OK results
# ===================================================================


class TestResultReasonConsistencyOK:
    """OK results should always have result_reason=None in to_dict()."""

    def test_summary_ok_reason_none(self):
        r = SummaryResult(summary=pd.DataFrame({"x": [1]}))
        assert r.to_dict()["result_reason"] is None

    def test_comparison_ok_reason_none(self):
        r = ComparisonResult(
            summary=pd.DataFrame({"x": [1]}),
            comparison=pd.DataFrame({"x": [1]}),
        )
        assert r.to_dict()["result_reason"] is None

    def test_finder_ok_reason_none(self):
        r = FinderResult(games=pd.DataFrame({"x": [1]}))
        assert r.to_dict()["result_reason"] is None

    def test_leaderboard_ok_reason_none(self):
        r = LeaderboardResult(leaders=pd.DataFrame({"x": [1]}))
        assert r.to_dict()["result_reason"] is None

    def test_streak_ok_reason_none(self):
        r = StreakResult(streaks=pd.DataFrame({"x": [1]}))
        assert r.to_dict()["result_reason"] is None

    def test_split_ok_reason_none(self):
        r = SplitSummaryResult(
            summary=pd.DataFrame({"x": [1]}),
            split_comparison=pd.DataFrame({"x": [1]}),
        )
        assert r.to_dict()["result_reason"] is None

    def test_count_ok_reason_none(self):
        r = CountResult(count=5)
        assert r.to_dict()["result_reason"] is None


# ===================================================================
# reason_to_status policy
# ===================================================================


class TestReasonToStatusPolicy:
    """reason_to_status maps expected failures to no_result and system failures to error."""

    def test_expected_reasons_map_to_no_result(self):
        from nbatools.query_service import reason_to_status

        for reason in ("no_match", "no_data", "unsupported", "ambiguous"):
            assert reason_to_status(reason) == "no_result", f"{reason} should map to no_result"

    def test_system_reasons_map_to_error(self):
        from nbatools.query_service import reason_to_status

        for reason in ("unrouted", "error"):
            assert reason_to_status(reason) == "error", f"{reason} should map to error"

    def test_unknown_reason_maps_to_error(self):
        from nbatools.query_service import reason_to_status

        assert reason_to_status("something_else") == "error"


# ===================================================================
# no_data status consistency across entry points
# ===================================================================


class TestNoDataStatusConsistency:
    """no_data should produce no_result status regardless of entry point."""

    def test_no_data_natural_query_returns_no_result_status(self):
        """Natural query with missing data should be no_result, not error."""
        qr = execute_natural_query("Jokic summary 1950-51")
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        if qr.result_reason == "no_data":
            assert qr.result_status == "no_result"

    def test_no_data_structured_query_returns_no_result_status(self):
        """Structured query with missing data should be no_result, not error."""
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
        )
        assert isinstance(qr.result, NoResult)
        assert not qr.is_ok
        if qr.result_reason == "no_data":
            assert qr.result_status == "no_result"

    def test_no_data_api_envelope_ok_false(self):
        """no_data results should have ok=False in the API envelope."""
        from nbatools.api import _query_result_to_response

        result = NoResult(query_class="summary", reason="no_data")
        qr = QueryResult(result=result, query="test", route="player_game_summary")
        response = _query_result_to_response(qr)
        d = response.model_dump()
        assert d["ok"] is False
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"


# ===================================================================
# _REASON_DISPLAY completeness
# ===================================================================


class TestReasonDisplayCompleteness:
    """_REASON_DISPLAY should have entries for all canonical reason codes."""

    def test_all_canonical_reasons_have_display_text(self):
        from nbatools.commands.format_output import _REASON_DISPLAY

        for reason in ResultReason:
            assert reason.value in _REASON_DISPLAY, (
                f"Missing _REASON_DISPLAY entry for {reason.value!r}"
            )
