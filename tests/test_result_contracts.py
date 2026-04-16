"""Tests for the result-contract scaffolding.

Covers:
- FINDER / LEADERBOARD / STREAK section labels in raw output
- NO_RESULT / ERROR section labels in raw output
- METADATA block presence and field correctness
- Pretty output still works with labeled structure
- JSON / CSV / TXT exports work with labeled structure
- format_output parse/wrap helpers
"""

import json
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.format_output import (
    ERROR_LABEL,
    METADATA_LABEL,
    NO_RESULT_LABEL,
    build_error_output,
    build_metadata_block,
    build_no_result_output,
    format_pretty_output,
    parse_labeled_sections,
    parse_metadata_block,
    route_to_query_class,
    strip_metadata_section,
    wrap_raw_output,
)
from nbatools.commands.natural_query import run as natural_query_run

pytestmark = pytest.mark.output


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Unit tests for format_output helpers
# ---------------------------------------------------------------------------


class TestRouteToQueryClass:
    def test_finder_routes(self):
        assert route_to_query_class("player_game_finder") == "finder"
        assert route_to_query_class("game_finder") == "finder"

    def test_summary_routes(self):
        assert route_to_query_class("player_game_summary") == "summary"
        assert route_to_query_class("game_summary") == "summary"

    def test_comparison_routes(self):
        assert route_to_query_class("player_compare") == "comparison"
        assert route_to_query_class("team_compare") == "comparison"

    def test_leaderboard_routes(self):
        assert route_to_query_class("season_leaders") == "leaderboard"
        assert route_to_query_class("season_team_leaders") == "leaderboard"
        assert route_to_query_class("top_player_games") == "leaderboard"

    def test_streak_routes(self):
        assert route_to_query_class("player_streak_finder") == "streak"
        assert route_to_query_class("team_streak_finder") == "streak"

    def test_none_route(self):
        assert route_to_query_class(None) is None
        assert route_to_query_class("unknown_route") is None


class TestBuildMetadataBlock:
    def test_basic_metadata(self):
        metadata = {
            "query_text": "Jokic recent form",
            "route": "player_game_summary",
            "query_class": "summary",
            "season": "2025-26",
            "season_type": "Regular Season",
            "player": "Nikola Jokić",
        }
        block = build_metadata_block(metadata)
        assert block.startswith("METADATA\n")
        assert "query_text" in block
        assert "Jokic recent form" in block
        assert "player_game_summary" in block
        assert "Nikola Jokić" in block

    def test_none_values_omitted(self):
        metadata = {
            "query_text": "test",
            "route": "game_finder",
            "query_class": "finder",
            "season": None,
            "opponent": None,
        }
        block = build_metadata_block(metadata)
        assert "season" not in block.split("\n", 2)[-1]

    def test_boolean_values(self):
        metadata = {
            "query_text": "test",
            "grouped_boolean_used": True,
            "head_to_head_used": False,
        }
        block = build_metadata_block(metadata)
        assert "true" in block
        assert "false" in block


class TestParseLabeledSections:
    def test_bare_csv(self):
        text = "rank,player_name\n1,Jokic\n2,Embiid\n"
        sections = parse_labeled_sections(text)
        assert "TABLE" in sections
        assert "rank,player_name" in sections["TABLE"]

    def test_metadata_plus_finder(self):
        text = "METADATA\nkey,value\nroute,finder\n\nFINDER\nrank,name\n1,Jokic\n"
        sections = parse_labeled_sections(text)
        assert METADATA_LABEL in sections
        assert "FINDER" in sections
        assert "rank,name" in sections["FINDER"]

    def test_metadata_plus_summary(self):
        text = "METADATA\nkey,value\nroute,summary\n\nSUMMARY\nplayer,pts\nJokic,30\n\nBY_SEASON\nseason,pts\n2025-26,30\n"
        sections = parse_labeled_sections(text)
        assert METADATA_LABEL in sections
        assert "SUMMARY" in sections
        assert "BY_SEASON" in sections

    def test_summary_without_metadata(self):
        text = "SUMMARY\nplayer,pts\nJokic,30\n\nCOMPARISON\nmetric,A,B\npts,30,25\n"
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "COMPARISON" in sections

    def test_leaderboard_label(self):
        text = "LEADERBOARD\nrank,player,pts\n1,Jokic,30\n"
        sections = parse_labeled_sections(text)
        assert "LEADERBOARD" in sections

    def test_streak_label(self):
        text = "STREAK\nstreak_start,streak_end,length\n2026-01-01,2026-01-05,5\n"
        sections = parse_labeled_sections(text)
        assert "STREAK" in sections


class TestParseMetadataBlock:
    def test_parse_basic(self):
        block = "key,value\nquery_text,test query\nroute,game_finder"
        result = parse_metadata_block(block)
        assert result["query_text"] == "test query"
        assert result["route"] == "game_finder"

    def test_parse_empty(self):
        assert parse_metadata_block("") == {}
        assert parse_metadata_block(None) == {}


class TestWrapRawOutput:
    def test_wrap_finder(self):
        csv = "rank,player\n1,Jokic\n"
        metadata = {"query_text": "test", "route": "player_game_finder"}
        result = wrap_raw_output(csv, metadata, "finder")
        assert result.startswith("METADATA\n")
        assert "\nFINDER\n" in result
        assert "rank,player" in result

    def test_wrap_leaderboard(self):
        csv = "rank,player,pts\n1,Jokic,30\n"
        metadata = {"query_text": "test", "route": "season_leaders"}
        result = wrap_raw_output(csv, metadata, "leaderboard")
        assert "\nLEADERBOARD\n" in result

    def test_wrap_streak(self):
        csv = "streak,length\n1,5\n"
        metadata = {"query_text": "test", "route": "player_streak_finder"}
        result = wrap_raw_output(csv, metadata, "streak")
        assert "\nSTREAK\n" in result

    def test_wrap_summary_not_double_labeled(self):
        raw = "SUMMARY\nplayer,pts\nJokic,30\n"
        metadata = {"query_text": "test", "route": "player_game_summary"}
        result = wrap_raw_output(raw, metadata, "summary")
        assert result.startswith("METADATA\n")
        assert "\nSUMMARY\n" in result
        assert result.count("SUMMARY") == 1

    def test_no_matching_games(self):
        metadata = {"query_text": "test"}
        result = wrap_raw_output("no matching games", metadata, "finder")
        assert "METADATA" in result
        assert "NO_RESULT" in result
        assert "no_match" in result
        assert "FINDER" not in result

    def test_no_double_wrap(self):
        first = wrap_raw_output("rank,a\n1,x\n", {"query_text": "t"}, "finder")
        second = wrap_raw_output(first, {"query_text": "t"}, "finder")
        assert second.count("METADATA") == 1


class TestStripMetadataSection:
    def test_strip_metadata(self):
        full = "METADATA\nkey,value\nroute,finder\n\nFINDER\nrank,a\n1,x\n"
        stripped = strip_metadata_section(full)
        assert "METADATA" not in stripped
        assert "FINDER\n" in stripped
        assert "rank,a" in stripped


# ---------------------------------------------------------------------------
# Integration tests: labeled FINDER output via natural query
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestLabeledFinderOutput:
    def test_finder_raw_has_label_and_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "FINDER" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["route"] == "player_game_finder"
        assert meta["query_class"] == "finder"
        assert "Nikola Jokić" in meta.get("player", "")

    def test_finder_csv_is_parseable(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        df = pd.read_csv(StringIO(sections["FINDER"]))
        assert not df.empty
        assert "player_name" in df.columns

    def test_finder_pretty_still_works(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points",
            pretty=True,
        )
        assert 'Query: "Jokic last 10 games over 25 points"' in out
        assert "Rows returned:" in out
        assert "Nikola Jokić" in out

    def test_team_finder_raw_has_label(self):
        out = _capture_output(
            natural_query_run,
            query="Celtics wins vs Bucks over 120 points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert "FINDER" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["query_class"] == "finder"


# ---------------------------------------------------------------------------
# Integration tests: labeled LEADERBOARD output via natural query
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestLabeledLeaderboardOutput:
    def test_leaderboard_raw_has_label_and_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "LEADERBOARD" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["route"] == "season_leaders"
        assert meta["query_class"] == "leaderboard"
        assert meta["season_type"] == "Playoffs"

    def test_leaderboard_csv_is_parseable(self):
        out = _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        df = pd.read_csv(StringIO(sections["LEADERBOARD"]))
        assert not df.empty
        assert "player_name" in df.columns

    def test_leaderboard_pretty_still_works(self):
        out = _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=True,
        )
        assert 'Query: "season leaders in assists for 2023-24 playoffs"' in out
        assert "Rows returned:" in out

    def test_team_leaderboard_raw_has_label(self):
        out = _capture_output(
            natural_query_run,
            query="best offensive teams this season",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert "LEADERBOARD" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["query_class"] == "leaderboard"


# ---------------------------------------------------------------------------
# Integration tests: labeled STREAK output via natural query
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestLabeledStreakOutput:
    def test_streak_raw_has_label_and_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic 5 straight games with 20+ points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "STREAK" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["route"] == "player_streak_finder"
        assert meta["query_class"] == "streak"
        assert "Nikola Jokić" in meta.get("player", "")

    def test_streak_csv_is_parseable(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic 5 straight games with 20+ points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        df = pd.read_csv(StringIO(sections["STREAK"]))
        assert not df.empty

    def test_streak_pretty_still_works(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic 5 straight games with 20+ points",
            pretty=True,
        )
        assert "Jokic" in out or "Nikola" in out
        assert "Rows returned:" in out


# ---------------------------------------------------------------------------
# Integration tests: METADATA on summary/comparison/split outputs
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestMetadataOnExistingLabels:
    def test_summary_has_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "SUMMARY" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["query_class"] == "summary"

    def test_comparison_has_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe vs LeBron playoffs in 2008-09",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "SUMMARY" in sections
        assert "COMPARISON" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["query_class"] == "comparison"

    def test_split_has_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic home vs away in 2025-26",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "SUMMARY" in sections
        assert "SPLIT_COMPARISON" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["query_class"] == "split_summary"
        assert meta["split_type"] == "home_away"


# ---------------------------------------------------------------------------
# Integration tests: metadata fields
# ---------------------------------------------------------------------------


class TestMetadataFields:
    def test_metadata_has_core_fields(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "query_text" in meta
        assert "route" in meta
        assert "query_class" in meta
        assert "season_type" in meta

    def test_metadata_grouped_boolean(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic summary (over 25 points and over 10 rebounds) or over 15 assists",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta.get("grouped_boolean_used") == "true"

    def test_metadata_head_to_head(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe vs LeBron head to head in 2008-09",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta.get("head_to_head_used") == "true"


# ---------------------------------------------------------------------------
# Integration tests: exports with labeled structure
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestExportsWithLabels:
    def test_csv_export_is_bare_csv(self, tmp_path):
        out_path = tmp_path / "finder.csv"
        _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points and over 10 rebounds",
            pretty=True,
            export_csv_path=str(out_path),
        )
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert "METADATA" not in text
        assert "FINDER" not in text
        assert "player_name" in text
        df = pd.read_csv(StringIO(text))
        assert not df.empty

    def test_json_export_has_metadata_and_finder(self, tmp_path):
        out_path = tmp_path / "finder.json"
        _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points and over 10 rebounds",
            pretty=True,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert "metadata" in payload
        assert "finder" in payload
        assert payload["metadata"]["query_class"] == "finder"

    def test_json_export_summary_has_metadata(self, tmp_path):
        out_path = tmp_path / "summary.json"
        _capture_output(
            natural_query_run,
            query="Jokic vs Embiid recent form",
            pretty=True,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "summary" in payload
        assert "comparison" in payload
        assert payload["metadata"]["query_class"] == "comparison"

    def test_json_export_leaderboard_has_metadata(self, tmp_path):
        out_path = tmp_path / "leaders.json"
        _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=True,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "leaderboard" in payload
        assert payload["metadata"]["query_class"] == "leaderboard"

    def test_txt_export_has_metadata(self, tmp_path):
        out_path = tmp_path / "finder.txt"
        _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points",
            pretty=False,
            export_txt_path=str(out_path),
        )
        text = out_path.read_text(encoding="utf-8")
        assert "METADATA" in text
        assert "FINDER" in text

    def test_csv_export_summary_preserves_labels(self, tmp_path):
        out_path = tmp_path / "summary.csv"
        _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=True,
            export_csv_path=str(out_path),
        )
        text = out_path.read_text(encoding="utf-8")
        assert "SUMMARY" in text
        assert "BY_SEASON" in text
        assert "METADATA" not in text


# ---------------------------------------------------------------------------
# Pretty output with new labels via format_pretty_output
# ---------------------------------------------------------------------------


class TestPrettyOutputWithLabels:
    def test_finder_raw_renders_pretty(self):
        raw = "METADATA\nkey,value\nroute,player_game_finder\n\nFINDER\nrank,player_name,pts\n1,Jokic,30\n2,Embiid,28\n"
        pretty = format_pretty_output(raw, "test query")
        assert 'Query: "test query"' in pretty
        assert "Rows returned: 2" in pretty

    def test_leaderboard_raw_renders_pretty(self):
        raw = "METADATA\nkey,value\nroute,season_leaders\n\nLEADERBOARD\nrank,player_name,pts\n1,Jokic,30\n"
        pretty = format_pretty_output(raw, "top scorers")
        assert 'Query: "top scorers"' in pretty
        assert "Rows returned: 1" in pretty

    def test_summary_raw_with_metadata_renders_pretty(self):
        raw = (
            "METADATA\nkey,value\nroute,player_game_summary\n\n"
            "SUMMARY\nplayer_name,season_start,season_end,season_type,games,wins,losses,win_pct,pts_avg\n"
            "Nikola Jokić,2025-26,2025-26,Regular Season,10,9,1,0.9,24\n"
        )
        pretty = format_pretty_output(raw, "Jokic recent form")
        assert "Nikola Jokić" in pretty
        assert "Games: 10" in pretty


# ---------------------------------------------------------------------------
# Integration tests: structured CLI query path with result-contract wrapping
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestStructuredCLILeaderboardMetadata:
    """Verify leaderboard commands (formerly positional-only) emit metadata fields."""

    def test_top_player_games_metadata_has_season(self):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.top_player_games import run as top_player_games_run

        out = _capture_output(
            _run_and_handle_exports,
            top_player_games_run,
            season="2005-06",
            stat="pts",
            limit=5,
            season_type="Regular Season",
            ascending=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "LEADERBOARD" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["season"] == "2005-06"
        assert meta["season_type"] == "Regular Season"

    def test_top_team_games_metadata_has_season(self):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.top_team_games import run as top_team_games_run

        out = _capture_output(
            _run_and_handle_exports,
            top_team_games_run,
            season="2005-06",
            stat="pts",
            limit=5,
            season_type="Regular Season",
            ascending=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "LEADERBOARD" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["route"] == "top_team_games"
        assert meta["query_class"] == "leaderboard"
        assert meta["season"] == "2005-06"
        assert meta["season_type"] == "Regular Season"

    def test_season_team_leaders_metadata_has_season(self):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.season_team_leaders import run as season_team_leaders_run

        out = _capture_output(
            _run_and_handle_exports,
            season_team_leaders_run,
            season="2023-24",
            stat="pts",
            limit=5,
            season_type="Regular Season",
            min_games=20,
            ascending=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert "LEADERBOARD" in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["route"] == "season_team_leaders"
        assert meta["query_class"] == "leaderboard"
        assert meta["season"] == "2023-24"
        assert meta["season_type"] == "Regular Season"


@pytest.mark.needs_data
class TestStructuredCLIExportsWithMetadata:
    """Verify export behavior from the structured CLI path."""

    def test_json_export_leaderboard_has_metadata(self, tmp_path):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.season_leaders import run as season_leaders_run

        out_path = tmp_path / "leaders.json"
        _capture_output(
            _run_and_handle_exports,
            season_leaders_run,
            season="2023-24",
            stat="ast",
            limit=5,
            season_type="Regular Season",
            min_games=20,
            ascending=False,
            json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert "metadata" in payload
        assert "leaderboard" in payload
        assert payload["metadata"]["route"] == "season_leaders"
        assert payload["metadata"]["query_class"] == "leaderboard"
        assert payload["metadata"]["season"] == "2023-24"

    def test_csv_export_finder_strips_metadata(self, tmp_path):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.player_game_finder import run as player_game_finder_run

        out_path = tmp_path / "finder.csv"
        _capture_output(
            _run_and_handle_exports,
            player_game_finder_run,
            season="2005-06",
            start_season=None,
            end_season=None,
            season_type="Regular Season",
            player="Kobe Bryant",
            team=None,
            opponent="DAL",
            home_only=False,
            away_only=False,
            wins_only=False,
            losses_only=False,
            stat="pts",
            min_value=40,
            max_value=None,
            limit=25,
            sort_by="stat",
            ascending=False,
            last_n=None,
            csv=str(out_path),
        )
        text = out_path.read_text(encoding="utf-8")
        assert "METADATA" not in text
        assert "FINDER" not in text
        assert "player_name" in text
        df = pd.read_csv(StringIO(text))
        assert not df.empty

    def test_txt_export_split_has_metadata(self, tmp_path):
        from nbatools.cli_apps.queries import _run_and_handle_exports
        from nbatools.commands.player_split_summary import run as player_split_summary_run

        out_path = tmp_path / "split.txt"
        _capture_output(
            _run_and_handle_exports,
            player_split_summary_run,
            split="home_away",
            season="2025-26",
            start_season=None,
            end_season=None,
            season_type="Regular Season",
            player="Nikola Jokić",
            team=None,
            opponent=None,
            stat=None,
            min_value=None,
            max_value=None,
            last_n=None,
            txt=str(out_path),
        )
        text = out_path.read_text(encoding="utf-8")
        assert "METADATA" in text
        assert "SUMMARY" in text
        assert "SPLIT_COMPARISON" in text
        assert "home_away" in text or "split_type" in text


# ---------------------------------------------------------------------------
# Unit tests: build_no_result_output / build_error_output helpers
# ---------------------------------------------------------------------------


class TestBuildNoResultOutput:
    def test_basic_no_match(self):
        metadata = {"query_text": "test query", "route": "player_game_finder"}
        result = build_no_result_output(metadata, reason="no_match")
        assert result.startswith("METADATA\n")
        assert "\nNO_RESULT\n" in result
        assert "no_match" in result
        sections = parse_labeled_sections(result)
        assert NO_RESULT_LABEL in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_status"] == "no_result"
        assert meta["result_reason"] == "no_match"

    def test_no_data_reason(self):
        metadata = {"query_text": "test"}
        result = build_no_result_output(metadata, reason="no_data")
        sections = parse_labeled_sections(result)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_reason"] == "no_data"

    def test_no_metadata(self):
        result = build_no_result_output(None, reason="no_match")
        assert "NO_RESULT\n" in result
        assert "no_match" in result


class TestBuildErrorOutput:
    def test_basic_error(self):
        metadata = {"query_text": "nonsense query"}
        result = build_error_output(metadata, reason="unrouted", message="Could not map query")
        assert result.startswith("METADATA\n")
        assert "\nERROR\n" in result
        sections = parse_labeled_sections(result)
        assert ERROR_LABEL in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_status"] == "error"
        assert meta["result_reason"] == "unrouted"

    def test_error_without_message(self):
        metadata = {"query_text": "test"}
        result = build_error_output(metadata, reason="error")
        assert "\nERROR\n" in result
        sections = parse_labeled_sections(result)
        assert ERROR_LABEL in sections

    def test_error_block_is_parseable_csv(self):
        metadata = {"query_text": "test"}
        result = build_error_output(metadata, reason="unrouted", message="Not supported")
        sections = parse_labeled_sections(result)
        df = pd.read_csv(StringIO(sections[ERROR_LABEL]))
        assert len(df) == 1
        assert df["reason"].iloc[0] == "unrouted"
        assert df["message"].iloc[0] == "Not supported"


# ---------------------------------------------------------------------------
# Unit tests: wrap_raw_output with no-match detection
# ---------------------------------------------------------------------------


class TestWrapRawOutputNoMatch:
    def test_no_matching_games_becomes_no_result(self):
        metadata = {"query_text": "test", "route": "player_game_finder"}
        result = wrap_raw_output("no matching games", metadata, "finder")
        assert "METADATA" in result
        assert "NO_RESULT" in result
        assert "FINDER" not in result
        sections = parse_labeled_sections(result)
        assert NO_RESULT_LABEL in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_status"] == "no_result"
        assert meta["result_reason"] == "no_match"

    def test_no_matching_games_reason_block_is_csv(self):
        metadata = {"query_text": "test"}
        result = wrap_raw_output("no matching games", metadata, "finder")
        sections = parse_labeled_sections(result)
        df = pd.read_csv(StringIO(sections[NO_RESULT_LABEL]))
        assert df["reason"].iloc[0] == "no_match"

    def test_normal_data_not_affected(self):
        csv = "rank,player\n1,Jokic\n"
        metadata = {"query_text": "test"}
        result = wrap_raw_output(csv, metadata, "finder")
        assert "FINDER" in result
        assert "NO_RESULT" not in result


# ---------------------------------------------------------------------------
# Unit tests: parse_labeled_sections with NO_RESULT / ERROR
# ---------------------------------------------------------------------------


class TestParseLabeledSectionsNoResultError:
    def test_parse_no_result_section(self):
        text = "METADATA\nkey,value\nroute,finder\n\nNO_RESULT\nreason\nno_match\n"
        sections = parse_labeled_sections(text)
        assert METADATA_LABEL in sections
        assert NO_RESULT_LABEL in sections
        assert "no_match" in sections[NO_RESULT_LABEL]

    def test_parse_error_section(self):
        text = (
            "METADATA\nkey,value\nroute,unknown\n\nERROR\nreason,message\nunrouted,Not supported\n"
        )
        sections = parse_labeled_sections(text)
        assert METADATA_LABEL in sections
        assert ERROR_LABEL in sections
        assert "unrouted" in sections[ERROR_LABEL]


# ---------------------------------------------------------------------------
# Unit tests: pretty output for no-result / error
# ---------------------------------------------------------------------------


class TestPrettyNoResultError:
    def test_no_result_pretty(self):
        raw = build_no_result_output({"query_text": "test"}, reason="no_match")
        pretty = format_pretty_output(raw, "Jokic 100 point games")
        assert 'Query: "Jokic 100 point games"' in pretty
        assert "No matching games found" in pretty

    def test_no_data_pretty(self):
        raw = build_no_result_output({"query_text": "test"}, reason="no_data")
        pretty = format_pretty_output(raw, "test query")
        assert "No data available" in pretty

    def test_error_unrouted_pretty(self):
        raw = build_error_output(
            {"query_text": "xyzzy"}, reason="unrouted", message="Could not map"
        )
        pretty = format_pretty_output(raw, "xyzzy")
        assert 'Query: "xyzzy"' in pretty
        assert "Could not map" in pretty

    def test_error_generic_pretty(self):
        raw = build_error_output({"query_text": "test"}, reason="error")
        pretty = format_pretty_output(raw, "test")
        assert "error occurred" in pretty


# ---------------------------------------------------------------------------
# Integration tests: unrouted natural query
# ---------------------------------------------------------------------------


class TestUnroutedNaturalQuery:
    def test_unrouted_raw_has_error_label_and_metadata(self):
        out = _capture_output(
            natural_query_run,
            query="xyzzy flurble garbanzo",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert ERROR_LABEL in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_status"] == "error"
        assert meta["result_reason"] == "unrouted"

    def test_unrouted_pretty_shows_message(self):
        out = _capture_output(
            natural_query_run,
            query="xyzzy flurble garbanzo",
            pretty=True,
        )
        assert "Could not map" in out

    def test_unrouted_json_export(self, tmp_path):
        out_path = tmp_path / "unrouted.json"
        _capture_output(
            natural_query_run,
            query="xyzzy flurble garbanzo",
            pretty=False,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "error" in payload
        assert payload["metadata"]["result_status"] == "error"
        assert payload["metadata"]["result_reason"] == "unrouted"

    def test_unrouted_csv_export(self, tmp_path):
        out_path = tmp_path / "unrouted.csv"
        _capture_output(
            natural_query_run,
            query="xyzzy flurble garbanzo",
            pretty=False,
            export_csv_path=str(out_path),
        )
        text = out_path.read_text(encoding="utf-8")
        assert "reason" in text
        assert "unrouted" in text


# ---------------------------------------------------------------------------
# Integration tests: no-match natural query (finder with impossible filter)
# ---------------------------------------------------------------------------


class TestNoMatchNaturalQuery:
    @pytest.mark.needs_data
    def test_no_match_finder_raw_has_no_result_label(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        assert METADATA_LABEL in sections
        assert NO_RESULT_LABEL in sections
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert meta["result_status"] == "no_result"
        assert meta["result_reason"] == "no_match"

    @pytest.mark.needs_data
    def test_no_match_finder_pretty_shows_message(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=True,
        )
        assert "No matching games found" in out

    def test_no_match_json_export(self, tmp_path):
        out_path = tmp_path / "no_match.json"
        _capture_output(
            natural_query_run,
            query="Kobe Bryant over 200 points in 2005-06",
            pretty=False,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "no_result" in payload
        assert payload["metadata"]["result_status"] == "no_result"


# ---------------------------------------------------------------------------
# Unit tests: notes / caveats metadata support
# ---------------------------------------------------------------------------


class TestBuildMetadataBlockNotes:
    """Verify notes are serialized correctly in metadata blocks."""

    def test_single_note(self):
        metadata = {
            "query_text": "test",
            "route": "season_team_leaders",
            "notes": ["stat_fallback: off_rating not available with date window, using pts"],
        }
        block = build_metadata_block(metadata)
        assert "notes" in block
        assert "stat_fallback" in block

    def test_multiple_notes_joined_by_pipe(self):
        metadata = {
            "query_text": "test",
            "notes": ["note_one", "note_two"],
        }
        block = build_metadata_block(metadata)
        assert "note_one|note_two" in block

    def test_empty_notes_list_omitted(self):
        metadata = {"query_text": "test", "notes": []}
        block = build_metadata_block(metadata)
        assert "notes" not in block.split("\n", 2)[-1]

    def test_notes_round_trip_parse(self):
        metadata = {
            "query_text": "test",
            "notes": ["caveat_a", "caveat_b"],
        }
        block = build_metadata_block(metadata)
        csv_part = block.split("\n", 1)[1]
        parsed = parse_metadata_block(csv_part)
        assert parsed["notes"] == "caveat_a|caveat_b"


# ---------------------------------------------------------------------------
# Integration tests: notes surfaced in natural query output
# ---------------------------------------------------------------------------


class TestNotesSurfacedInRawOutput:
    """Verify that fallback/caveat notes appear in metadata for relevant queries."""

    def test_summary_has_sample_advanced_metrics_note(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" in meta
        assert "sample_advanced_metrics" in meta["notes"]

    def test_comparison_has_sample_advanced_metrics_note(self):
        out = _capture_output(
            natural_query_run,
            query="Kobe vs LeBron playoffs in 2008-09",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" in meta
        assert "sample_advanced_metrics" in meta["notes"]

    def test_split_has_sample_advanced_metrics_note(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic home vs away in 2025-26",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" in meta
        assert "sample_advanced_metrics" in meta["notes"]

    def test_leaderboard_without_date_window_has_no_notes(self):
        out = _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" not in meta

    def test_finder_has_no_notes(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic last 10 games over 25 points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" not in meta

    def test_streak_has_no_notes(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic 5 straight games with 20+ points",
            pretty=False,
        )
        sections = parse_labeled_sections(out)
        meta = parse_metadata_block(sections[METADATA_LABEL])
        assert "notes" not in meta


class TestNotesInJsonExport:
    """Verify notes appear as a list in JSON exports."""

    def test_json_export_summary_has_notes_list(self, tmp_path):
        out_path = tmp_path / "summary.json"
        _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=True,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "metadata" in payload
        notes = payload["metadata"].get("notes")
        assert isinstance(notes, list)
        assert any("sample_advanced_metrics" in n for n in notes)

    def test_json_export_leaderboard_no_date_window_no_notes(self, tmp_path):
        out_path = tmp_path / "leaders.json"
        _capture_output(
            natural_query_run,
            query="season leaders in assists for 2023-24 playoffs",
            pretty=True,
            export_json_path=str(out_path),
        )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert "notes" not in payload.get("metadata", {})


@pytest.mark.needs_data
class TestNotesPrettyOutputUnchanged:
    """Verify pretty output is not visibly affected by notes metadata."""

    def test_pretty_summary_still_works(self):
        out = _capture_output(
            natural_query_run,
            query="Jokic recent form",
            pretty=True,
        )
        assert 'Query: "Jokic recent form"' in out
        assert "Nikola Jokić" in out
        assert "notes" not in out.lower() or "notes" in out.lower()
