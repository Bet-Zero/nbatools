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

import pytest

from nbatools.commands.structured_results import (
    ComparisonResult,
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
        qr = execute_natural_query("Jokic vs Embiid 2024-25")
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
        assert any("quarter" in note and "unfiltered" in note for note in qr.result.notes)

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
        assert any("half" in note and "unfiltered" in note for note in qr.result.notes)

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
        assert any("back_to_back" in note and "unfiltered" in note for note in qr.result.notes)

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
        assert any("rest" in note and "unfiltered" in note for note in qr.result.notes)

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
        assert any("one_possession" in note and "unfiltered" in note for note in qr.result.notes)

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
        assert any("national_tv" in note and "unfiltered" in note for note in qr.result.notes)

    def test_structured_query_accepts_role_filter_with_unfiltered_note(self):
        qr = execute_structured_query(
            "player_game_summary",
            season="1950-51",
            player="Nikola Jokić",
            role="bench",
        )
        assert qr.route == "player_game_summary"
        assert isinstance(qr.result, NoResult)
        assert qr.metadata["role"] == "bench"
        assert any("role" in note and "unfiltered" in note for note in qr.result.notes)

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

    def test_structured_query_accepts_lineup_summary_placeholder_route(self):
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
        assert any("lineup" in note and "placeholder" in note for note in qr.result.notes)

    def test_structured_query_accepts_lineup_leaderboard_placeholder_route(self):
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
        assert any("lineup" in note and "placeholder" in note for note in qr.result.notes)


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
