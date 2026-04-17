"""Tests for structured-first orchestration paths.

Verifies that natural_query.run() and CLI query execution use
build_result() directly instead of capturing stdout, and that
the render/export helpers produce correct output from structured
result objects.
"""

import json
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.cli_apps.queries import _run_and_handle_exports
from nbatools.commands.format_output import (
    METADATA_LABEL,
    format_pretty_from_result,
    format_pretty_output,
    parse_labeled_sections,
    write_csv_from_result,
    write_json_from_result,
)
from nbatools.commands._natural_query_execution import (
    _apply_extra_conditions_to_result,
    _combine_or_results,
    _execute_build_result,
    _get_build_result_map,
)
from nbatools.commands.natural_query import (
    run as natural_query_run,
)
from nbatools.commands.structured_results import (
    ComparisonResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)
from nbatools.commands.top_player_games import run as top_player_games_run


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Build result map
# ---------------------------------------------------------------------------


class TestBuildResultMap:
    """Verify the structured-first build_result map is complete."""

    def test_all_routes_have_build_result(self):
        brmap = _get_build_result_map()
        expected_routes = {
            "top_player_games",
            "top_team_games",
            "season_leaders",
            "season_team_leaders",
            "player_game_summary",
            "game_summary",
            "player_game_finder",
            "game_finder",
            "player_compare",
            "team_compare",
            "team_record",
            "team_matchup_record",
            "team_record_leaderboard",
            "player_split_summary",
            "team_split_summary",
            "player_streak_finder",
            "team_streak_finder",
            "player_occurrence_leaders",
            "team_occurrence_leaders",
            "playoff_history",
            "playoff_appearances",
            "playoff_matchup_history",
            "playoff_round_record",
            "record_by_decade",
            "record_by_decade_leaderboard",
            "matchup_by_decade",
        }
        assert expected_routes == set(brmap.keys())

    def test_build_result_callables_are_not_run(self):
        brmap = _get_build_result_map()
        # Record routes use named functions rather than the build_result alias
        record_names = {
            "build_team_record_result",
            "build_matchup_record_result",
            "build_record_leaderboard_result",
            "build_playoff_history_result",
            "build_playoff_appearances_result",
            "build_playoff_matchup_history_result",
            "build_playoff_round_record_result",
            "build_record_by_decade_result",
            "build_record_by_decade_leaderboard_result",
            "build_matchup_by_decade_result",
        }
        for route, fn in brmap.items():
            assert fn.__name__ in ("build_result", *record_names), (
                f"{route} maps to {fn.__name__}, expected build_result or a record builder"
            )


# ---------------------------------------------------------------------------
# _execute_build_result: structured-first execution
# ---------------------------------------------------------------------------


class TestExecuteBuildResult:
    """Verify _execute_build_result returns typed result objects."""

    @pytest.mark.needs_data
    def test_finder_result(self):
        result = _execute_build_result(
            "player_game_finder",
            {
                "season": "2005-06",
                "player": "Kobe Bryant",
                "stat": "pts",
                "min_value": 60,
                "season_type": "Regular Season",
                "start_season": None,
                "end_season": None,
                "team": None,
                "opponent": None,
                "home_only": False,
                "away_only": False,
                "wins_only": False,
                "losses_only": False,
                "max_value": None,
                "start_date": None,
                "end_date": None,
                "limit": 25,
                "sort_by": "stat",
                "ascending": False,
                "last_n": None,
            },
        )
        assert isinstance(result, FinderResult)
        assert not result.games.empty
        assert "Kobe Bryant" in result.games["player_name"].values

    @pytest.mark.needs_data
    def test_leaderboard_result(self):
        result = _execute_build_result(
            "top_player_games",
            {
                "season": "2005-06",
                "stat": "pts",
                "limit": 5,
                "season_type": "Regular Season",
                "ascending": False,
            },
        )
        assert isinstance(result, LeaderboardResult)
        assert not result.leaders.empty
        assert len(result.leaders) == 5

    @pytest.mark.needs_data
    def test_summary_result(self):
        result = _execute_build_result(
            "player_game_summary",
            {
                "season": "2005-06",
                "player": "Kobe Bryant",
                "season_type": "Regular Season",
                "start_season": None,
                "end_season": None,
                "team": None,
                "opponent": None,
                "home_only": False,
                "away_only": False,
                "wins_only": False,
                "losses_only": False,
                "stat": None,
                "min_value": None,
                "max_value": None,
                "last_n": None,
                "start_date": None,
                "end_date": None,
            },
        )
        assert isinstance(result, SummaryResult)
        assert not result.summary.empty

    def test_no_result_on_impossible_filter(self):
        result = _execute_build_result(
            "player_game_finder",
            {
                "season": "2005-06",
                "player": "Kobe Bryant",
                "stat": "pts",
                "min_value": 200,
                "season_type": "Regular Season",
                "start_season": None,
                "end_season": None,
                "team": None,
                "opponent": None,
                "home_only": False,
                "away_only": False,
                "wins_only": False,
                "losses_only": False,
                "max_value": None,
                "start_date": None,
                "end_date": None,
                "limit": 25,
                "sort_by": "stat",
                "ascending": False,
                "last_n": None,
            },
        )
        assert isinstance(result, NoResult)

    def test_extra_conditions_applied(self):
        result = _execute_build_result(
            "player_game_finder",
            {
                "season": "2005-06",
                "player": "Kobe Bryant",
                "stat": "pts",
                "min_value": 40,
                "season_type": "Regular Season",
                "start_season": None,
                "end_season": None,
                "team": None,
                "opponent": None,
                "home_only": False,
                "away_only": False,
                "wins_only": False,
                "losses_only": False,
                "max_value": None,
                "start_date": None,
                "end_date": None,
                "limit": 25,
                "sort_by": "stat",
                "ascending": False,
                "last_n": None,
            },
            extra_conditions=[{"stat": "reb", "min_value": 10, "max_value": None}],
        )
        if isinstance(result, FinderResult):
            assert (result.games["reb"] >= 10).all()
        else:
            assert isinstance(result, NoResult)


# ---------------------------------------------------------------------------
# _apply_extra_conditions_to_result
# ---------------------------------------------------------------------------


class TestApplyExtraConditionsToResult:
    """Verify DataFrame-level extra condition filtering."""

    def test_filters_finder_games(self):
        df = pd.DataFrame({"game_id": [1, 2, 3], "pts": [30, 25, 40], "reb": [5, 12, 8]})
        result = FinderResult(games=df)
        filtered = _apply_extra_conditions_to_result(
            result, [{"stat": "pts", "min_value": 28, "max_value": None}]
        )
        assert isinstance(filtered, FinderResult)
        assert len(filtered.games) == 2
        assert set(filtered.games["pts"].tolist()) == {30, 40}

    def test_returns_no_result_when_empty(self):
        df = pd.DataFrame({"game_id": [1], "pts": [10]})
        result = FinderResult(games=df)
        filtered = _apply_extra_conditions_to_result(
            result, [{"stat": "pts", "min_value": 50, "max_value": None}]
        )
        assert isinstance(filtered, NoResult)

    def test_returns_no_result_for_missing_stat(self):
        df = pd.DataFrame({"game_id": [1], "pts": [10]})
        result = FinderResult(games=df)
        filtered = _apply_extra_conditions_to_result(
            result, [{"stat": "nonexistent", "min_value": 1, "max_value": None}]
        )
        assert isinstance(filtered, NoResult)

    def test_no_conditions_passthrough(self):
        df = pd.DataFrame({"game_id": [1, 2], "pts": [30, 25]})
        result = FinderResult(games=df)
        filtered = _apply_extra_conditions_to_result(result, [])
        assert isinstance(filtered, FinderResult)
        assert len(filtered.games) == 2

    def test_no_result_passthrough(self):
        result = NoResult(query_class="finder")
        filtered = _apply_extra_conditions_to_result(
            result, [{"stat": "pts", "min_value": 10, "max_value": None}]
        )
        assert isinstance(filtered, NoResult)

    def test_summary_skipped(self):
        result = SummaryResult(summary=pd.DataFrame({"games": [10]}))
        filtered = _apply_extra_conditions_to_result(
            result, [{"stat": "pts", "min_value": 10, "max_value": None}]
        )
        assert isinstance(filtered, SummaryResult)


# ---------------------------------------------------------------------------
# _combine_or_results
# ---------------------------------------------------------------------------


class TestCombineOrResults:
    """Verify structured OR-query combining."""

    def test_combines_two_finder_results(self):
        df1 = pd.DataFrame({"game_id": [1, 2], "player_id": [100, 100], "pts": [30, 25]})
        df2 = pd.DataFrame({"game_id": [2, 3], "player_id": [100, 100], "pts": [25, 40]})
        r1 = FinderResult(games=df1)
        r2 = FinderResult(games=df2)
        combined = _combine_or_results([r1, r2])
        assert isinstance(combined, FinderResult)
        # Game 2 should be deduped
        assert len(combined.games) == 3

    def test_all_no_results(self):
        r1 = NoResult(query_class="finder")
        r2 = NoResult(query_class="finder")
        combined = _combine_or_results([r1, r2])
        assert isinstance(combined, NoResult)

    def test_mixed_results_skips_no_result(self):
        df = pd.DataFrame({"game_id": [1], "pts": [30]})
        r1 = FinderResult(games=df)
        r2 = NoResult(query_class="finder")
        combined = _combine_or_results([r1, r2])
        assert isinstance(combined, FinderResult)
        assert len(combined.games) == 1


# ---------------------------------------------------------------------------
# format_pretty_from_result
# ---------------------------------------------------------------------------


class TestFormatPrettyFromResult:
    """Verify structured result pretty formatting."""

    def test_finder_result_pretty(self):
        df = pd.DataFrame(
            {
                "rank": [1],
                "game_date": ["2006-01-22"],
                "player_name": ["Kobe Bryant"],
                "team_abbr": ["LAL"],
                "opponent_team_abbr": ["TOR"],
                "pts": [81],
            }
        )
        result = FinderResult(games=df)
        pretty = format_pretty_from_result(result, "Kobe over 80 points")
        assert "Kobe over 80 points" in pretty
        assert "Kobe Bryant" in pretty

    def test_summary_result_pretty(self):
        df = pd.DataFrame(
            {
                "player_name": ["Kobe Bryant"],
                "season_start": ["2005-06"],
                "season_end": ["2005-06"],
                "season_type": ["Regular Season"],
                "games": [80],
                "wins": [45],
                "losses": [35],
                "win_pct": [0.563],
                "pts_avg": [35.4],
                "reb_avg": [5.3],
                "ast_avg": [4.5],
            }
        )
        result = SummaryResult(summary=df)
        pretty = format_pretty_from_result(result, "Kobe 2005-06 summary")
        assert "Kobe Bryant" in pretty
        assert "Games:" in pretty

    def test_no_result_pretty(self):
        result = NoResult(query_class="finder", reason="no_match")
        pretty = format_pretty_from_result(result, "impossible query")
        assert "No matching games" in pretty

    def test_leaderboard_result_pretty(self):
        df = pd.DataFrame(
            {
                "rank": [1, 2],
                "player_name": ["Player A", "Player B"],
                "pts": [30, 28],
            }
        )
        result = LeaderboardResult(leaders=df)
        pretty = format_pretty_from_result(result, "top scorers")
        assert "Player A" in pretty


# ---------------------------------------------------------------------------
# write_csv_from_result
# ---------------------------------------------------------------------------


class TestWriteCsvFromResult:
    """Verify CSV export directly from structured results."""

    def test_finder_csv(self, tmp_path):
        df = pd.DataFrame({"rank": [1, 2], "player_name": ["A", "B"], "pts": [30, 25]})
        result = FinderResult(games=df)
        path = tmp_path / "out.csv"
        write_csv_from_result(result, str(path))
        text = path.read_text(encoding="utf-8")
        assert "player_name" in text
        assert "A" in text
        assert "B" in text

    def test_leaderboard_csv(self, tmp_path):
        df = pd.DataFrame({"rank": [1], "player_name": ["X"], "pts": [50]})
        result = LeaderboardResult(leaders=df)
        path = tmp_path / "out.csv"
        write_csv_from_result(result, str(path))
        text = path.read_text(encoding="utf-8")
        assert "player_name" in text

    def test_summary_csv(self, tmp_path):
        df = pd.DataFrame({"player_name": ["Test"], "games": [10], "pts_avg": [20.0]})
        result = SummaryResult(summary=df)
        path = tmp_path / "out.csv"
        write_csv_from_result(result, str(path))
        text = path.read_text(encoding="utf-8")
        assert "SUMMARY" in text
        assert "player_name" in text

    def test_no_result_csv(self, tmp_path):
        result = NoResult(query_class="finder")
        path = tmp_path / "out.csv"
        write_csv_from_result(result, str(path))
        text = path.read_text(encoding="utf-8")
        assert "no matching games" in text

    def test_comparison_csv(self, tmp_path):
        summary = pd.DataFrame({"player_name": ["A", "B"], "games": [10, 10]})
        comparison = pd.DataFrame({"metric": ["pts_avg"], "A": [25.0], "B": [22.0]})
        result = ComparisonResult(summary=summary, comparison=comparison)
        path = tmp_path / "out.csv"
        write_csv_from_result(result, str(path))
        text = path.read_text(encoding="utf-8")
        assert "SUMMARY" in text
        assert "COMPARISON" in text


# ---------------------------------------------------------------------------
# write_json_from_result
# ---------------------------------------------------------------------------


class TestWriteJsonFromResult:
    """Verify JSON export directly from structured results."""

    def test_finder_json(self, tmp_path):
        df = pd.DataFrame({"rank": [1, 2], "player_name": ["A", "B"], "pts": [30, 25]})
        result = FinderResult(games=df)
        path = tmp_path / "out.json"
        metadata = {"route": "player_game_finder", "query_class": "finder"}
        write_json_from_result(result, str(path), metadata)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "finder" in payload
        assert isinstance(payload["finder"], list)
        assert len(payload["finder"]) == 2

    def test_summary_json(self, tmp_path):
        df = pd.DataFrame({"player_name": ["Test"], "games": [10], "pts_avg": [20.0]})
        result = SummaryResult(summary=df)
        path = tmp_path / "out.json"
        write_json_from_result(result, str(path))
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "summary" in payload

    def test_no_result_json(self, tmp_path):
        result = NoResult(query_class="finder", reason="no_match")
        path = tmp_path / "out.json"
        metadata = {"route": "player_game_finder", "result_status": "no_result"}
        write_json_from_result(result, str(path), metadata)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "no_result" in payload
        assert "metadata" in payload

    def test_json_handles_timestamps(self, tmp_path):
        df = pd.DataFrame(
            {
                "rank": [1],
                "player_name": ["Test"],
                "game_date": pd.to_datetime(["2006-01-22"]),
                "pts": [50],
            }
        )
        result = FinderResult(games=df)
        path = tmp_path / "out.json"
        write_json_from_result(result, str(path))
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "finder" in payload


# ---------------------------------------------------------------------------
# Natural query structured-first path: integration tests
# ---------------------------------------------------------------------------


class TestNaturalQueryStructuredFirst:
    """Verify natural query routes use structured-first execution."""

    @pytest.mark.needs_data
    def test_finder_pretty_output_parity(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points in 2005-06",
            pretty=True,
        )
        assert "Kobe Bryant" in out
        assert "81" in out  # Kobe's 81-point game

    @pytest.mark.needs_data
    def test_finder_raw_output_has_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points in 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "FINDER" in sections

    @pytest.mark.needs_data
    def test_summary_pretty_output(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant summary 2005-06",
            pretty=True,
        )
        assert "Kobe Bryant" in out
        assert "Games:" in out

    @pytest.mark.needs_data
    def test_summary_raw_output_has_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant summary 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "SUMMARY" in sections

    @pytest.mark.needs_data
    def test_leaderboard_pretty_output(self):
        out = _capture_output(
            natural_query_run,
            query="top 5 scoring games in 2005-06",
            pretty=True,
        )
        assert "Kobe Bryant" in out

    @pytest.mark.needs_data
    def test_leaderboard_raw_output_has_label(self):
        out = _capture_output(
            natural_query_run,
            query="top 5 scoring games in 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert "LEADERBOARD" in sections

    @pytest.mark.needs_data
    def test_no_result_pretty_output(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=True,
        )
        assert "No matching games" in out

    def test_no_result_raw_output(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert "NO_RESULT" in sections


# ---------------------------------------------------------------------------
# Natural query export from structured results
# ---------------------------------------------------------------------------


class TestNaturalQueryExports:
    """Verify exports work directly from structured results."""

    @pytest.mark.needs_data
    def test_csv_export_finder(self, tmp_path):
        csv_path = tmp_path / "export.csv"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points in 2005-06",
            pretty=False,
            export_csv_path=str(csv_path),
        )
        assert csv_path.exists()
        text = csv_path.read_text(encoding="utf-8")
        assert "player_name" in text
        assert "Kobe Bryant" in text

    @pytest.mark.needs_data
    def test_json_export_finder(self, tmp_path):
        json_path = tmp_path / "export.json"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points in 2005-06",
            pretty=False,
            export_json_path=str(json_path),
        )
        assert json_path.exists()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "finder" in payload

    def test_txt_export_summary(self, tmp_path):
        txt_path = tmp_path / "export.txt"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant summary 2005-06",
            pretty=True,
            export_txt_path=str(txt_path),
        )
        assert txt_path.exists()
        text = txt_path.read_text(encoding="utf-8")
        assert "Kobe Bryant" in text

    def test_csv_export_no_result(self, tmp_path):
        csv_path = tmp_path / "no_match.csv"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=False,
            export_csv_path=str(csv_path),
        )
        assert csv_path.exists()
        text = csv_path.read_text(encoding="utf-8")
        assert "no matching games" in text

    def test_json_export_no_result(self, tmp_path):
        json_path = tmp_path / "no_match.json"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=False,
            export_json_path=str(json_path),
        )
        assert json_path.exists()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert "no_result" in payload


# ---------------------------------------------------------------------------
# CLI structured query path exports
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestCLIQueryStructuredExports:
    """Verify CLI query commands export directly from structured results."""

    def test_cli_csv_export(self, tmp_path):
        csv_path = tmp_path / "top.csv"
        _capture_output(
            _run_and_handle_exports,
            top_player_games_run,
            "2005-06",
            "pts",
            5,
            "Regular Season",
            False,
            csv=str(csv_path),
        )
        assert csv_path.exists()
        text = csv_path.read_text(encoding="utf-8")
        assert "player_name" in text

    def test_cli_json_export(self, tmp_path):
        json_path = tmp_path / "top.json"
        _capture_output(
            _run_and_handle_exports,
            top_player_games_run,
            "2005-06",
            "pts",
            5,
            "Regular Season",
            False,
            json_path=str(json_path),
        )
        assert json_path.exists()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "leaderboard" in payload

    def test_cli_output_has_metadata(self):
        out = _capture_output(
            _run_and_handle_exports,
            top_player_games_run,
            "2005-06",
            "pts",
            5,
            "Regular Season",
            False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "LEADERBOARD" in sections


# ---------------------------------------------------------------------------
# Grouped boolean structured-first paths
# ---------------------------------------------------------------------------


class TestGroupedBooleanStructuredFirst:
    """Verify grouped boolean queries use structured-first execution."""

    @pytest.mark.needs_data
    def test_grouped_boolean_player_summary(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic summary (over 25 points and over 10 rebounds) or over 15 assists",
            pretty=True,
        )
        assert "Nikola Jokić" in out
        assert "Games:" in out

    def test_grouped_boolean_finder(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic games (over 25 points and over 10 rebounds) or over 15 assists",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections

    @pytest.mark.needs_data
    def test_grouped_boolean_player_split(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists",
            pretty=True,
        )
        assert "Nikola Jokić" in out


# ---------------------------------------------------------------------------
# OR query structured-first paths
# ---------------------------------------------------------------------------


class TestOrQueryStructuredFirst:
    """Verify OR queries use structured-first execution."""

    def test_or_finder_query(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points or over 20 rebounds in 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections

    def test_or_query_pretty(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 60 points or over 20 rebounds in 2005-06",
            pretty=True,
        )
        assert "Kobe Bryant" in out


# ---------------------------------------------------------------------------
# Pretty output parity: structured vs text rendering
# ---------------------------------------------------------------------------


class TestPrettyOutputParity:
    """Verify format_pretty_from_result matches format_pretty_output."""

    def test_finder_pretty_parity(self):
        df = pd.DataFrame(
            {
                "rank": [1, 2],
                "game_date": ["2006-01-22", "2006-03-28"],
                "player_name": ["Kobe Bryant", "Kobe Bryant"],
                "team_abbr": ["LAL", "LAL"],
                "opponent_team_abbr": ["TOR", "WAS"],
                "pts": [81, 60],
            }
        )
        result = FinderResult(games=df)
        query = "Kobe over 50 points"

        text_pretty = format_pretty_output(result.to_labeled_text(), query)
        result_pretty = format_pretty_from_result(result, query)
        assert text_pretty == result_pretty

    def test_no_result_pretty_parity(self):
        result = NoResult(query_class="finder", reason="no_match")
        query = "impossible query"

        result_pretty = format_pretty_from_result(result, query)
        assert "No matching games" in result_pretty
