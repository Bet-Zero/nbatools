"""Tests for the trust/status layer in the structured-result system.

Covers:
- ResultStatus and ResultReason enums
- current_through on results where determinable
- no_data vs no_match distinction in structured results
- NoResult reason propagation
- natural query path status metadata (current_through in METADATA)
- structured CLI path status metadata
- JSON export preserving trust/status metadata
- pretty output still working
- no regression in labeled raw output
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.format_output import (
    format_pretty_output,
    parse_labeled_sections,
    parse_metadata_block,
)
from nbatools.commands.freshness import (
    compute_current_through,
    compute_current_through_for_seasons,
    season_data_available,
)
from nbatools.commands.structured_results import (
    ComparisonResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    ResultReason,
    ResultStatus,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)

pytestmark = pytest.mark.output

# ---------------------------------------------------------------------------
# Unit: ResultStatus and ResultReason enums
# ---------------------------------------------------------------------------


class TestResultStatusEnum:
    def test_ok_value(self):
        assert ResultStatus.OK == "ok"
        assert ResultStatus.OK.value == "ok"

    def test_no_result_value(self):
        assert ResultStatus.NO_RESULT == "no_result"

    def test_error_value(self):
        assert ResultStatus.ERROR == "error"

    def test_str_serialization(self):
        assert str(ResultStatus.OK) == "ok"
        assert f"{ResultStatus.OK.value}" == "ok"

    def test_json_serializable(self):
        d = {"status": ResultStatus.OK.value}
        assert json.dumps(d) == '{"status": "ok"}'


class TestResultReasonEnum:
    def test_no_match(self):
        assert ResultReason.NO_MATCH == "no_match"

    def test_no_data(self):
        assert ResultReason.NO_DATA == "no_data"

    def test_unrouted(self):
        assert ResultReason.UNROUTED == "unrouted"

    def test_error(self):
        assert ResultReason.ERROR == "error"


# ---------------------------------------------------------------------------
# Unit: current_through from freshness module
# ---------------------------------------------------------------------------


class TestComputeCurrentThrough:
    @pytest.mark.needs_data
    def test_returns_date_for_known_season(self):
        ct = compute_current_through("2024-25", "Regular Season")
        assert ct is not None
        assert len(ct) == 10  # YYYY-MM-DD
        assert ct.startswith("202")

    def test_returns_none_for_nonexistent_season(self):
        ct = compute_current_through("2099-00", "Regular Season")
        assert ct is None

    @pytest.mark.needs_data
    def test_returns_date_for_current_season(self):
        ct = compute_current_through("2025-26", "Regular Season")
        assert ct is not None
        assert ct >= "2025-10-01"

    @pytest.mark.needs_data
    def test_multi_season_returns_latest(self):
        ct = compute_current_through_for_seasons(["2023-24", "2024-25"], "Regular Season")
        assert ct is not None
        ct_single = compute_current_through("2024-25", "Regular Season")
        assert ct == ct_single

    def test_multi_season_with_nonexistent(self):
        ct = compute_current_through_for_seasons(["2024-25", "2099-00"], "Regular Season")
        ct_single = compute_current_through("2024-25", "Regular Season")
        assert ct == ct_single

    def test_all_nonexistent_returns_none(self):
        ct = compute_current_through_for_seasons(["2099-00"], "Regular Season")
        assert ct is None


class TestSeasonDataAvailable:
    @pytest.mark.needs_data
    def test_known_season_available(self):
        assert season_data_available("2024-25", "Regular Season") is True

    def test_unknown_season_not_available(self):
        assert season_data_available("2099-00", "Regular Season") is False

    @pytest.mark.needs_data
    def test_player_stats_available(self):
        assert (
            season_data_available("2024-25", "Regular Season", dataset="player_game_stats") is True
        )

    @pytest.mark.needs_data
    def test_team_stats_available(self):
        assert season_data_available("2024-25", "Regular Season", dataset="team_game_stats") is True


# ---------------------------------------------------------------------------
# Unit: NoResult with reason distinction
# ---------------------------------------------------------------------------


class TestNoResultReasons:
    def test_default_reason_is_no_match(self):
        r = NoResult(query_class="summary")
        assert r.reason == "no_match"
        assert r.result_reason == "no_match"
        assert r.result_status == "no_result"

    def test_no_data_reason(self):
        r = NoResult(query_class="summary", reason="no_data")
        d = r.to_dict()
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"

    def test_unrouted_reason(self):
        r = NoResult(query_class="finder", reason="unrouted")
        d = r.to_dict()
        assert d["result_reason"] == "unrouted"

    def test_error_reason(self):
        r = NoResult(query_class="streak", reason="error")
        d = r.to_dict()
        assert d["result_reason"] == "error"

    def test_labeled_text_unchanged(self):
        r = NoResult(query_class="summary", reason="no_data")
        text = r.to_labeled_text()
        assert text.startswith("SUMMARY\n")
        assert "no matching games" in text

    def test_caveats_field_present(self):
        r = NoResult(query_class="summary", caveats=["test caveat"])
        d = r.to_dict()
        assert d["caveats"] == ["test caveat"]

    def test_current_through_on_no_result(self):
        r = NoResult(query_class="summary", current_through="2025-04-10")
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"


# ---------------------------------------------------------------------------
# Unit: Trust fields on result classes
# ---------------------------------------------------------------------------


class TestResultTrustFields:
    def test_summary_result_has_trust_fields(self):
        summary = pd.DataFrame([{"player_name": "X", "games": 10}])
        r = SummaryResult(
            summary=summary,
            current_through="2025-04-10",
            notes=["sample note"],
            caveats=["sample caveat"],
        )
        d = r.to_dict()
        assert d["result_status"] == "ok"
        assert d["current_through"] == "2025-04-10"
        assert d["notes"] == ["sample note"]
        assert d["caveats"] == ["sample caveat"]

    def test_summary_result_omits_none_current_through(self):
        summary = pd.DataFrame([{"player_name": "X", "games": 10}])
        r = SummaryResult(summary=summary)
        d = r.to_dict()
        assert "current_through" not in d

    def test_comparison_result_has_trust_fields(self):
        summary = pd.DataFrame([{"player_name": "A", "games": 5}])
        comp = pd.DataFrame([("games", 5, 5)], columns=["metric", "A", "B"])
        r = ComparisonResult(
            summary=summary,
            comparison=comp,
            current_through="2025-04-10",
        )
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"
        assert d["result_status"] == "ok"

    def test_split_summary_result_has_trust_fields(self):
        summary = pd.DataFrame([{"team_name": "BOS", "split": "home_away"}])
        split_comp = pd.DataFrame([{"bucket": "home", "games": 5}])
        r = SplitSummaryResult(
            summary=summary,
            split_comparison=split_comp,
            current_through="2025-04-10",
        )
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"
        assert d["caveats"] == []

    def test_finder_result_has_trust_fields(self):
        games = pd.DataFrame([{"rank": 1, "player_name": "X", "pts": 50}])
        r = FinderResult(games=games, current_through="2025-04-10")
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"
        assert d["result_status"] == "ok"

    def test_leaderboard_result_has_trust_fields(self):
        leaders = pd.DataFrame([{"rank": 1, "player_name": "X", "pts_avg": 30}])
        r = LeaderboardResult(leaders=leaders, current_through="2025-04-10")
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"

    def test_streak_result_has_trust_fields(self):
        streaks = pd.DataFrame([{"player_name": "X", "streak_length": 5}])
        r = StreakResult(streaks=streaks, current_through="2025-04-10")
        d = r.to_dict()
        assert d["current_through"] == "2025-04-10"

    def test_result_reason_present_when_none(self):
        """result_reason is always present in to_dict() for contract consistency."""
        summary = pd.DataFrame([{"player_name": "X", "games": 10}])
        r = SummaryResult(summary=summary)
        d = r.to_dict()
        assert d["result_reason"] is None

    def test_result_reason_included_when_set(self):
        summary = pd.DataFrame([{"player_name": "X", "games": 10}])
        r = SummaryResult(summary=summary, result_reason="partial_data")
        d = r.to_dict()
        assert d["result_reason"] == "partial_data"


# ---------------------------------------------------------------------------
# Integration: current_through on real command results
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestCurrentThroughOnCommands:
    def test_player_game_summary_has_current_through(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, SummaryResult)
        assert result.current_through is not None
        assert len(result.current_through) == 10

    def test_game_summary_has_current_through(self):
        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, SummaryResult)
        assert result.current_through is not None

    def test_player_compare_has_current_through(self):
        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2023-24",
            season_type="Regular Season",
        )
        assert isinstance(result, ComparisonResult)
        assert result.current_through is not None

    def test_team_compare_has_current_through(self):
        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="BOS",
            team_b="MIL",
            season="2024-25",
            season_type="Regular Season",
        )
        assert isinstance(result, ComparisonResult)
        assert result.current_through is not None

    def test_player_split_summary_has_current_through(self):
        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, SplitSummaryResult)
        assert result.current_through is not None

    def test_team_split_summary_has_current_through(self):
        from nbatools.commands.team_split_summary import build_result

        result = build_result(
            split="wins_losses",
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, SplitSummaryResult)
        assert result.current_through is not None

    def test_current_through_in_to_dict(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        d = result.to_dict()
        assert "current_through" in d
        assert d["current_through"] is not None
        assert d["result_status"] == "ok"


# ---------------------------------------------------------------------------
# Integration: no_data detection on invalid seasons
# ---------------------------------------------------------------------------


class TestNoDataDetection:
    def test_player_summary_no_data_for_missing_season(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"
        d = result.to_dict()
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"

    def test_game_summary_no_data_for_missing_season(self):
        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2099-00",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_player_compare_no_data_for_missing_season(self):
        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2099-00",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_team_compare_no_data_for_missing_season(self):
        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="BOS",
            team_b="MIL",
            season="2099-00",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_player_split_no_data_for_missing_season(self):
        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_team_split_no_data_for_missing_season(self):
        from nbatools.commands.team_split_summary import build_result

        result = build_result(
            split="wins_losses",
            season="2099-00",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    @pytest.mark.needs_data
    def test_no_match_vs_no_data_distinction(self):
        """no_match: data exists but filters match nothing. no_data: data doesn't exist."""
        from nbatools.commands.player_game_summary import build_result

        no_match = build_result(
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
        )
        assert isinstance(no_match, NoResult)
        assert no_match.reason == "no_match"

        no_data = build_result(
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(no_data, NoResult)
        assert no_data.reason == "no_data"

    def test_no_data_labeled_text_still_works(self):
        r = NoResult(query_class="summary", reason="no_data")
        text = r.to_labeled_text()
        assert "no matching games" in text


# ---------------------------------------------------------------------------
# Integration: natural query path status metadata
# ---------------------------------------------------------------------------


class TestNaturalQueryMetadata:
    @pytest.mark.needs_data
    def test_current_through_in_metadata_block(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("Jokic summary 2024-25", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        assert "METADATA" in sections
        meta = parse_metadata_block(sections["METADATA"])
        assert "current_through" in meta
        assert len(meta["current_through"]) == 10

    def test_metadata_still_has_route_and_query_class(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("Jokic summary 2024-25", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        meta = parse_metadata_block(sections["METADATA"])
        assert meta.get("route") == "player_game_summary"
        assert meta.get("query_class") == "summary"

    def test_pretty_output_still_works_with_trust_fields(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("Jokic summary 2024-25", pretty=True)
        output = buf.getvalue()
        assert 'Query: "Jokic summary 2024-25"' in output
        assert "Jokić" in output or "Jokic" in output

    @pytest.mark.needs_data
    def test_comparison_metadata_has_current_through(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("Jokic vs Embiid 2023-24", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        meta = parse_metadata_block(sections["METADATA"])
        assert "current_through" in meta


# ---------------------------------------------------------------------------
# Integration: JSON export preserving trust/status metadata
# ---------------------------------------------------------------------------


class TestJsonExportTrustMetadata:
    @pytest.mark.needs_data
    def test_json_export_includes_current_through(self):
        from nbatools.commands.natural_query import run

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        try:
            buf = StringIO()
            with redirect_stdout(buf):
                run("Jokic summary 2024-25", pretty=False, export_json_path=json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "current_through" in data["metadata"]
        finally:
            os.unlink(json_path)

    def test_json_export_preserves_query_class(self):
        from nbatools.commands.natural_query import run

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        try:
            buf = StringIO()
            with redirect_stdout(buf):
                run("Jokic summary 2024-25", pretty=False, export_json_path=json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert data["metadata"]["query_class"] == "summary"
        finally:
            os.unlink(json_path)


# ---------------------------------------------------------------------------
# Integration: Structured result to_dict trust contract
# ---------------------------------------------------------------------------


class TestToDictTrustContract:
    @pytest.mark.needs_data
    def test_player_summary_to_dict_contract(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            last_n=5,
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d
        assert isinstance(d["notes"], list)
        assert isinstance(d["caveats"], list)
        assert "summary" in d["sections"]

    def test_no_result_to_dict_contract(self):
        r = NoResult(query_class="summary", reason="no_data")
        d = r.to_dict()
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"
        assert d["sections"] == {}
        assert isinstance(d["notes"], list)
        assert isinstance(d["caveats"], list)

    def test_no_result_no_match_to_dict_contract(self):
        r = NoResult(query_class="finder", reason="no_match")
        d = r.to_dict()
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_match"


# ---------------------------------------------------------------------------
# Integration: labeled raw output still works
# ---------------------------------------------------------------------------


class TestLabeledRawOutputPreserved:
    @pytest.mark.needs_data
    def test_summary_labeled_text_unchanged(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            last_n=5,
        )
        text = result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "BY_SEASON" in sections

        df = pd.read_csv(StringIO(sections["SUMMARY"]))
        assert len(df) == 1
        assert df["player_name"].iloc[0] == "Nikola Jokić"

    @pytest.mark.needs_data
    def test_comparison_labeled_text_unchanged(self):
        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2023-24",
            season_type="Regular Season",
        )
        text = result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "COMPARISON" in sections

    def test_run_output_matches_build_result(self):
        """Verify run() still produces identical output to build_result().to_labeled_text()."""
        from nbatools.commands.player_game_summary import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                season="2024-25",
                player="Nikola Jokić",
                season_type="Regular Season",
                last_n=5,
            )
        run_output = buf.getvalue()

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            last_n=5,
        )
        assert result.to_labeled_text() == run_output


# ---------------------------------------------------------------------------
# Integration: Pretty output still works end-to-end
# ---------------------------------------------------------------------------


class TestPrettyOutputPreserved:
    def test_summary_pretty_output(self):
        summary = pd.DataFrame(
            [
                {
                    "player_name": "Test Player",
                    "season_start": "2024-25",
                    "season_end": "2024-25",
                    "season_type": "Regular Season",
                    "games": 10,
                    "wins": 7,
                    "losses": 3,
                    "win_pct": 0.7,
                    "pts_avg": 25.0,
                    "reb_avg": 10.0,
                    "ast_avg": 8.0,
                }
            ]
        )
        r = SummaryResult(
            summary=summary,
            current_through="2025-04-10",
            notes=["test_note"],
        )
        text = r.to_labeled_text()
        pretty = format_pretty_output(text, "test query")
        assert "Test Player" in pretty
        assert 'Query: "test query"' in pretty

    def test_comparison_pretty_output(self):
        summary = pd.DataFrame(
            [
                {"player_name": "A", "games": 5},
                {"player_name": "B", "games": 5},
            ]
        )
        comp = pd.DataFrame([("games", 5, 5)], columns=["metric", "A", "B"])
        r = ComparisonResult(
            summary=summary,
            comparison=comp,
            current_through="2025-04-10",
        )
        text = r.to_labeled_text()
        pretty = format_pretty_output(text, "compare")
        assert "A" in pretty
        assert "B" in pretty


# ---------------------------------------------------------------------------
# Integration: current_through on finder command results
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestCurrentThroughOnFinderCommands:
    def test_player_game_finder_has_current_through(self):
        from nbatools.commands.player_game_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            limit=5,
        )
        assert isinstance(result, FinderResult)
        assert result.current_through is not None
        assert len(result.current_through) == 10

    def test_game_finder_has_current_through(self):
        from nbatools.commands.game_finder import build_result

        result = build_result(
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
            limit=5,
        )
        assert isinstance(result, FinderResult)
        assert result.current_through is not None
        assert len(result.current_through) == 10

    def test_player_game_finder_to_dict_has_current_through(self):
        from nbatools.commands.player_game_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            limit=3,
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d
        assert d["current_through"] is not None

    def test_game_finder_to_dict_has_current_through(self):
        from nbatools.commands.game_finder import build_result

        result = build_result(
            season="2024-25",
            team="DEN",
            season_type="Regular Season",
            limit=3,
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d


# ---------------------------------------------------------------------------
# Integration: current_through on leaderboard command results
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestCurrentThroughOnLeaderboardCommands:
    def test_season_leaders_has_current_through(self):
        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, LeaderboardResult)
        assert result.current_through is not None
        assert len(result.current_through) == 10

    def test_season_team_leaders_has_current_through(self):
        from nbatools.commands.season_team_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, LeaderboardResult)
        assert result.current_through is not None

    def test_top_player_games_has_current_through(self):
        from nbatools.commands.top_player_games import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, LeaderboardResult)
        assert result.current_through is not None

    def test_top_team_games_has_current_through(self):
        from nbatools.commands.top_team_games import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, LeaderboardResult)
        assert result.current_through is not None

    def test_season_leaders_to_dict_has_current_through(self):
        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d
        assert isinstance(d["notes"], list)
        assert isinstance(d["caveats"], list)

    def test_season_leaders_date_window_has_caveat(self):
        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
            start_date="2025-01-01",
            end_date="2025-02-01",
        )
        assert isinstance(result, LeaderboardResult)
        assert len(result.caveats) >= 1
        assert any("game-log window" in c for c in result.caveats)

    def test_season_team_leaders_date_window_has_caveat(self):
        from nbatools.commands.season_team_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
            start_date="2025-01-01",
            end_date="2025-02-01",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("game-log window" in c for c in result.caveats)


# ---------------------------------------------------------------------------
# Integration: current_through on streak command results
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestCurrentThroughOnStreakCommands:
    def test_player_streak_finder_has_current_through(self):
        from nbatools.commands.player_streak_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            stat="pts",
            min_value=20,
        )
        assert isinstance(result, StreakResult)
        assert result.current_through is not None
        assert len(result.current_through) == 10

    def test_team_streak_finder_has_current_through(self):
        from nbatools.commands.team_streak_finder import build_result

        result = build_result(
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
            special_condition="wins",
        )
        assert isinstance(result, StreakResult)
        assert result.current_through is not None

    def test_player_streak_to_dict_has_current_through(self):
        from nbatools.commands.player_streak_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            stat="pts",
            min_value=15,
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d

    def test_team_streak_to_dict_has_current_through(self):
        from nbatools.commands.team_streak_finder import build_result

        result = build_result(
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
            special_condition="wins",
        )
        d = result.to_dict()
        assert d["result_status"] == "ok"
        assert "current_through" in d


# ---------------------------------------------------------------------------
# Integration: no_data detection on finder / leaderboard / streak
# ---------------------------------------------------------------------------


class TestNoDataDetectionFinderLeaderboardStreak:
    def test_player_game_finder_no_data(self):
        from nbatools.commands.player_game_finder import build_result

        result = build_result(
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"
        d = result.to_dict()
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_data"

    def test_game_finder_no_data(self):
        from nbatools.commands.game_finder import build_result

        result = build_result(
            season="2099-00",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    @pytest.mark.needs_data
    def test_player_game_finder_no_match(self):
        from nbatools.commands.player_game_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_match"

    @pytest.mark.needs_data
    def test_game_finder_no_match(self):
        from nbatools.commands.game_finder import build_result

        result = build_result(
            season="2024-25",
            team="ZZZZZ",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_match"

    def test_season_leaders_no_data(self):
        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2099-00",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_season_team_leaders_no_data(self):
        from nbatools.commands.season_team_leaders import build_result

        result = build_result(
            season="2099-00",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_top_player_games_no_data(self):
        from nbatools.commands.top_player_games import build_result

        result = build_result(
            season="2099-00",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_top_team_games_no_data(self):
        from nbatools.commands.top_team_games import build_result

        result = build_result(
            season="2099-00",
            stat="pts",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_player_streak_no_data(self):
        from nbatools.commands.player_streak_finder import build_result

        result = build_result(
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
            stat="pts",
            min_value=20,
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    def test_team_streak_no_data(self):
        from nbatools.commands.team_streak_finder import build_result

        result = build_result(
            season="2099-00",
            team="BOS",
            season_type="Regular Season",
            special_condition="wins",
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_data"

    @pytest.mark.needs_data
    def test_player_streak_no_match(self):
        from nbatools.commands.player_streak_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
            stat="pts",
            min_value=20,
        )
        assert isinstance(result, NoResult)
        assert result.reason == "no_match"

    @pytest.mark.needs_data
    def test_no_data_vs_no_match_finder(self):
        """Verify no_match and no_data are distinguished for finders."""
        from nbatools.commands.player_game_finder import build_result

        no_match = build_result(
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
        )
        assert isinstance(no_match, NoResult)
        assert no_match.reason == "no_match"

        no_data = build_result(
            season="2099-00",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(no_data, NoResult)
        assert no_data.reason == "no_data"


# ---------------------------------------------------------------------------
# Integration: metadata in raw output for finder / leaderboard / streak
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestMetadataInRawOutputFinderLeaderboardStreak:
    def test_finder_natural_query_has_metadata(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("show me Jokic games with 30 points 2024-25", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        assert "METADATA" in sections
        meta = parse_metadata_block(sections["METADATA"])
        assert "current_through" in meta
        assert meta.get("query_class") == "finder"

    def test_leaderboard_natural_query_has_metadata(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("top 5 scorers 2024-25", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        assert "METADATA" in sections
        meta = parse_metadata_block(sections["METADATA"])
        assert "current_through" in meta

    def test_streak_natural_query_has_metadata(self):
        from nbatools.commands.natural_query import run

        buf = StringIO()
        with redirect_stdout(buf):
            run("Jokic longest streak of 20+ points 2024-25", pretty=False)
        output = buf.getvalue()

        sections = parse_labeled_sections(output)
        assert "METADATA" in sections
        meta = parse_metadata_block(sections["METADATA"])
        assert "current_through" in meta


# ---------------------------------------------------------------------------
# Integration: JSON export with trust/status for finder / leaderboard / streak
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestJsonExportFinderLeaderboardStreak:
    def test_finder_json_export_has_metadata(self):
        from nbatools.commands.natural_query import run

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        try:
            buf = StringIO()
            with redirect_stdout(buf):
                run("Jokic 2024-25", pretty=False, export_json_path=json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "current_through" in data["metadata"]
        finally:
            os.unlink(json_path)

    def test_leaderboard_json_export_has_metadata(self):
        from nbatools.commands.natural_query import run

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        try:
            buf = StringIO()
            with redirect_stdout(buf):
                run("top 5 scorers 2024-25", pretty=False, export_json_path=json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "current_through" in data["metadata"]
        finally:
            os.unlink(json_path)


# ---------------------------------------------------------------------------
# Integration: pretty output still works for finder / leaderboard / streak
# ---------------------------------------------------------------------------


class TestPrettyOutputFinderLeaderboardStreak:
    def test_finder_pretty_output(self):
        games = pd.DataFrame(
            [{"rank": 1, "player_name": "Test", "pts": 50, "game_date": "2025-01-01"}]
        )
        r = FinderResult(games=games, current_through="2025-04-10")
        text = r.to_labeled_text()
        pretty = format_pretty_output(text, "test query")
        assert "Test" in pretty
        assert 'Query: "test query"' in pretty

    def test_leaderboard_pretty_output(self):
        leaders = pd.DataFrame(
            [{"rank": 1, "player_name": "Test", "pts_per_game": 30.0, "games_played": 50}]
        )
        r = LeaderboardResult(leaders=leaders, current_through="2025-04-10")
        text = r.to_labeled_text()
        pretty = format_pretty_output(text, "leaders query")
        assert "Test" in pretty

    def test_streak_pretty_output(self):
        streaks = pd.DataFrame(
            [
                {
                    "rank": 1,
                    "player_name": "Test",
                    "streak_length": 5,
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-10",
                }
            ]
        )
        r = StreakResult(streaks=streaks, current_through="2025-04-10")
        text = r.to_labeled_text()
        pretty = format_pretty_output(text, "streak query")
        assert "Test" in pretty


# ---------------------------------------------------------------------------
# Integration: labeled raw output preserved for finder / leaderboard / streak
# ---------------------------------------------------------------------------


@pytest.mark.needs_data
class TestLabeledRawOutputFinderLeaderboardStreak:
    def test_finder_labeled_text_unchanged(self):
        from nbatools.commands.player_game_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            limit=3,
        )
        text = result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "FINDER" in sections

        df = pd.read_csv(StringIO(sections["FINDER"]))
        assert len(df) <= 3
        assert "rank" in df.columns

    def test_leaderboard_labeled_text_unchanged(self):
        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
            limit=5,
        )
        text = result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "LEADERBOARD" in sections

        df = pd.read_csv(StringIO(sections["LEADERBOARD"]))
        assert len(df) <= 5
        assert "rank" in df.columns

    def test_streak_labeled_text_unchanged(self):
        from nbatools.commands.player_streak_finder import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            stat="pts",
            min_value=15,
        )
        text = result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "STREAK" in sections

    def test_run_output_matches_build_result_finder(self):
        from nbatools.commands.player_game_finder import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                season="2024-25",
                player="Nikola Jokić",
                season_type="Regular Season",
                limit=3,
            )
        run_output = buf.getvalue()

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            limit=3,
        )
        assert result.to_labeled_text() == run_output

    def test_run_output_matches_build_result_leaderboard(self):
        from nbatools.commands.season_leaders import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                season="2024-25",
                stat="pts",
                season_type="Regular Season",
                limit=5,
            )
        run_output = buf.getvalue()

        result = build_result(
            season="2024-25",
            stat="pts",
            season_type="Regular Season",
            limit=5,
        )
        assert result.to_labeled_text() == run_output
