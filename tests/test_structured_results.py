"""Tests for the structured result layer.

Covers:
- SummaryResult / ComparisonResult / SplitSummaryResult / NoResult shapes
- to_labeled_text() reproduces the same labeled CSV sections
- to_dict() produces machine-readable dicts
- build_result() returns the correct type for each command
- Labeled text round-trips through format_output parse helpers
- Pretty output still works when derived from structured results
"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.format_output import (
    format_pretty_output,
    parse_labeled_sections,
)
from nbatools.commands.structured_results import (
    ComparisonResult,
    NoResult,
    SplitSummaryResult,
    SummaryResult,
)

pytestmark = pytest.mark.output

# ---------------------------------------------------------------------------
# Unit: NoResult
# ---------------------------------------------------------------------------


class TestNoResult:
    def test_labeled_text_shape(self):
        r = NoResult(query_class="summary")
        text = r.to_labeled_text()
        assert text.startswith("SUMMARY\n")
        assert "no matching games" in text

    def test_to_dict_shape(self):
        r = NoResult(query_class="summary", reason="no_match")
        d = r.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "no_result"
        assert d["result_reason"] == "no_match"
        assert d["sections"] == {}


# ---------------------------------------------------------------------------
# Unit: SummaryResult
# ---------------------------------------------------------------------------


class TestSummaryResult:
    @pytest.fixture
    def summary_result(self):
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
        by_season = pd.DataFrame(
            [
                {
                    "season": "2024-25",
                    "games": 10,
                    "wins": 7,
                    "losses": 3,
                    "pts_avg": 25.0,
                    "reb_avg": 10.0,
                    "ast_avg": 8.0,
                }
            ]
        )
        return SummaryResult(summary=summary, by_season=by_season)

    def test_labeled_text_has_both_sections(self, summary_result):
        text = summary_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "BY_SEASON" in sections

    def test_labeled_text_summary_is_csv(self, summary_result):
        text = summary_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["SUMMARY"]))
        assert len(df) == 1
        assert df["player_name"].iloc[0] == "Test Player"
        assert df["pts_avg"].iloc[0] == 25.0

    def test_labeled_text_by_season_is_csv(self, summary_result):
        text = summary_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["BY_SEASON"]))
        assert len(df) == 1
        assert df["season"].iloc[0] == "2024-25"

    def test_to_dict_shape(self, summary_result):
        d = summary_result.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"
        assert "summary" in d["sections"]
        assert "by_season" in d["sections"]
        assert len(d["sections"]["summary"]) == 1
        assert d["sections"]["summary"][0]["player_name"] == "Test Player"
        assert d["sections"]["summary"][0]["pts_avg"] == 25.0

    def test_to_dict_can_include_structured_game_log_without_labeled_output(self):
        summary = pd.DataFrame([{"player_name": "Test Player", "games": 2}])
        game_log = pd.DataFrame(
            [
                {
                    "game_date": "2024-10-25",
                    "game_id": "001",
                    "opponent_team_abbr": "LAL",
                    "wl": "W",
                    "minutes": 34.5,
                    "pts": 28,
                    "reb": 10,
                    "ast": 8,
                }
            ]
        )
        result = SummaryResult(summary=summary, game_log=game_log)

        d = result.to_dict()
        assert d["sections"]["game_log"] == [game_log.iloc[0].to_dict()]

        sections = parse_labeled_sections(result.to_labeled_text())
        assert "SUMMARY" in sections
        assert "GAME_LOG" not in sections

    def test_to_dict_handles_nan(self):
        summary = pd.DataFrame([{"player_name": "X", "pts_avg": float("nan")}])
        r = SummaryResult(summary=summary)
        d = r.to_dict()
        assert d["sections"]["summary"][0]["pts_avg"] is None

    def test_without_by_season(self):
        summary = pd.DataFrame([{"team_name": "BOS", "games": 5}])
        r = SummaryResult(summary=summary)
        text = r.to_labeled_text()
        assert "SUMMARY" in text
        assert "BY_SEASON" not in text
        d = r.to_dict()
        assert "by_season" not in d["sections"]

    def test_pretty_output_from_labeled_text(self, summary_result):
        text = summary_result.to_labeled_text()
        pretty = format_pretty_output(text, "test query")
        assert 'Query: "test query"' in pretty
        assert "Test Player" in pretty

    def test_metadata_preserved(self):
        summary = pd.DataFrame([{"player_name": "X", "games": 1}])
        r = SummaryResult(
            summary=summary,
            metadata={"route": "player_game_summary"},
            notes=["sample_advanced_metrics"],
        )
        d = r.to_dict()
        assert d["metadata"]["route"] == "player_game_summary"
        assert "sample_advanced_metrics" in d["notes"]


# ---------------------------------------------------------------------------
# Unit: ComparisonResult
# ---------------------------------------------------------------------------


class TestComparisonResult:
    @pytest.fixture
    def comparison_result(self):
        summary = pd.DataFrame(
            [
                {
                    "player_name": "Player A",
                    "games": 10,
                    "wins": 7,
                    "losses": 3,
                    "win_pct": 0.7,
                    "pts_avg": 25.0,
                },
                {
                    "player_name": "Player B",
                    "games": 10,
                    "wins": 5,
                    "losses": 5,
                    "win_pct": 0.5,
                    "pts_avg": 22.0,
                },
            ]
        )
        comparison = pd.DataFrame(
            [
                ("games", 10, 10),
                ("pts_avg", 25.0, 22.0),
                ("win_pct", 0.7, 0.5),
            ],
            columns=["metric", "Player A", "Player B"],
        )
        return ComparisonResult(summary=summary, comparison=comparison)

    def test_labeled_text_has_both_sections(self, comparison_result):
        text = comparison_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "COMPARISON" in sections

    def test_labeled_text_summary_has_two_rows(self, comparison_result):
        text = comparison_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["SUMMARY"]))
        assert len(df) == 2
        assert list(df["player_name"]) == ["Player A", "Player B"]

    def test_labeled_text_comparison_is_metric_table(self, comparison_result):
        text = comparison_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["COMPARISON"]))
        assert "metric" in df.columns
        assert "Player A" in df.columns
        assert "Player B" in df.columns
        assert len(df) == 3

    def test_to_dict_shape(self, comparison_result):
        d = comparison_result.to_dict()
        assert d["query_class"] == "comparison"
        assert d["result_status"] == "ok"
        assert len(d["sections"]["summary"]) == 2
        assert len(d["sections"]["comparison"]) == 3

    def test_pretty_output_from_labeled_text(self, comparison_result):
        text = comparison_result.to_labeled_text()
        pretty = format_pretty_output(text, "compare players")
        assert 'Query: "compare players"' in pretty
        assert "Player A" in pretty
        assert "Player B" in pretty


# ---------------------------------------------------------------------------
# Unit: SplitSummaryResult
# ---------------------------------------------------------------------------


class TestSplitSummaryResult:
    @pytest.fixture
    def split_result(self):
        summary = pd.DataFrame(
            [
                {
                    "player_name": "Test Player",
                    "season_start": "2024-25",
                    "season_end": "2024-25",
                    "season_type": "Regular Season",
                    "split": "home_away",
                    "games_total": 20,
                }
            ]
        )
        split_comparison = pd.DataFrame(
            [
                {
                    "bucket": "home",
                    "games": 12,
                    "wins": 10,
                    "losses": 2,
                    "win_pct": 0.833,
                    "pts_avg": 28.0,
                },
                {
                    "bucket": "away",
                    "games": 8,
                    "wins": 4,
                    "losses": 4,
                    "win_pct": 0.5,
                    "pts_avg": 22.0,
                },
            ]
        )
        return SplitSummaryResult(summary=summary, split_comparison=split_comparison)

    def test_labeled_text_has_both_sections(self, split_result):
        text = split_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        assert "SUMMARY" in sections
        assert "SPLIT_COMPARISON" in sections

    def test_labeled_text_summary_has_split_metadata(self, split_result):
        text = split_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["SUMMARY"]))
        assert df["split"].iloc[0] == "home_away"
        assert df["games_total"].iloc[0] == 20

    def test_labeled_text_split_comparison_has_buckets(self, split_result):
        text = split_result.to_labeled_text()
        sections = parse_labeled_sections(text)
        df = pd.read_csv(StringIO(sections["SPLIT_COMPARISON"]))
        assert len(df) == 2
        assert set(df["bucket"]) == {"home", "away"}

    def test_to_dict_shape(self, split_result):
        d = split_result.to_dict()
        assert d["query_class"] == "split_summary"
        assert d["result_status"] == "ok"
        assert len(d["sections"]["summary"]) == 1
        assert len(d["sections"]["split_comparison"]) == 2
        buckets = [r["bucket"] for r in d["sections"]["split_comparison"]]
        assert "home" in buckets
        assert "away" in buckets

    def test_pretty_output_from_labeled_text(self, split_result):
        text = split_result.to_labeled_text()
        pretty = format_pretty_output(text, "home vs away")
        assert 'Query: "home vs away"' in pretty
        assert "Test Player" in pretty
        assert "Home" in pretty


# ---------------------------------------------------------------------------
# Integration: build_result() returns correct types
# ---------------------------------------------------------------------------


class TestBuildResultPlayerGameSummary:
    @pytest.mark.needs_data
    def test_returns_summary_result(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, SummaryResult)
        assert not result.summary.empty
        assert "player_name" in result.summary.columns

    def test_returns_no_result_when_empty(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)

    @pytest.mark.needs_data
    def test_labeled_text_matches_run_output(self):
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
        assert isinstance(result, SummaryResult)
        assert result.to_labeled_text() == run_output

    @pytest.mark.needs_data
    def test_to_dict_has_summary_data(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            last_n=5,
        )
        d = result.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"
        assert len(d["sections"]["summary"]) == 1
        row = d["sections"]["summary"][0]
        assert row["player_name"] == "Nikola Jokić"
        assert row["games"] == 5


class TestBuildResultGameSummary:
    @pytest.mark.needs_data
    def test_returns_summary_result(self):
        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, SummaryResult)
        assert not result.summary.empty
        assert "team_name" in result.summary.columns

    def test_returns_no_result_when_empty(self):
        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2024-25",
            team="ZZZ",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)

    def test_to_dict_includes_team_game_log(self):
        from nbatools.commands.game_summary import build_result

        df = pd.DataFrame(
            [
                {
                    "game_id": "002",
                    "game_date": "2025-01-17",
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "team_id": 1610612738,
                    "team_abbr": "BOS",
                    "team_name": "Boston Celtics",
                    "opponent_team_id": 1610612747,
                    "opponent_team_abbr": "LAL",
                    "opponent_team_name": "Los Angeles Lakers",
                    "is_home": 0,
                    "is_away": 1,
                    "wl": "L",
                    "pts": 112,
                    "reb": 41,
                    "ast": 24,
                    "fg3m": 13,
                    "plus_minus": -5,
                },
                {
                    "game_id": "001",
                    "game_date": "2025-01-15",
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "team_id": 1610612738,
                    "team_abbr": "BOS",
                    "team_name": "Boston Celtics",
                    "opponent_team_id": 1610612748,
                    "opponent_team_abbr": "MIA",
                    "opponent_team_name": "Miami Heat",
                    "is_home": 1,
                    "is_away": 0,
                    "wl": "W",
                    "pts": 118,
                    "reb": 44,
                    "ast": 29,
                    "fg3m": 16,
                    "plus_minus": 8,
                },
            ]
        )

        result = build_result(season="2024-25", team="BOS", df=df)
        d = result.to_dict()

        assert list(d["sections"]) == ["summary", "by_season", "game_log"]
        first_game = d["sections"]["game_log"][0]
        assert first_game["game_date"] == "2025-01-15"
        assert first_game["team_abbr"] == "BOS"
        assert first_game["opponent_team_abbr"] == "MIA"
        assert first_game["opponent_pts"] == 110

    def test_to_dict_omits_game_log_for_unbounded_team_summary(self):
        from nbatools.commands.game_summary import build_result

        rows = []
        for index in range(6):
            rows.append(
                {
                    "game_id": f"00{index}",
                    "game_date": f"2025-01-{index + 1:02d}",
                    "season": "2024-25",
                    "season_type": "Regular Season",
                    "team_id": 1610612738,
                    "team_abbr": "BOS",
                    "team_name": "Boston Celtics",
                    "opponent_team_id": 1610612747,
                    "opponent_team_abbr": "LAL",
                    "opponent_team_name": "Los Angeles Lakers",
                    "is_home": index % 2,
                    "is_away": int(index % 2 == 0),
                    "wl": "W",
                    "pts": 110 + index,
                    "plus_minus": 5,
                }
            )
        df = pd.DataFrame(rows)

        result = build_result(season="2024-25", team="BOS", df=df)
        d = result.to_dict()

        assert "game_log" not in d["sections"]


class TestBuildResultPlayerCompare:
    @pytest.mark.needs_data
    def test_returns_comparison_result(self):
        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2023-24",
            season_type="Regular Season",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.summary) == 2
        assert "COMPARISON" in result.to_sections_dict()

    def test_labeled_text_matches_run_output(self):
        from nbatools.commands.player_compare import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                player_a="Nikola Jokić",
                player_b="Joel Embiid",
                season="2023-24",
                season_type="Regular Season",
            )
        run_output = buf.getvalue()

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2023-24",
            season_type="Regular Season",
        )
        assert result.to_labeled_text() == run_output


class TestBuildResultTeamCompare:
    @pytest.mark.needs_data
    def test_returns_comparison_result(self):
        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="BOS",
            team_b="MIL",
            season="2024-25",
            season_type="Regular Season",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.summary) == 2
        assert not result.comparison.empty

    def test_labeled_text_matches_run_output(self):
        from nbatools.commands.team_compare import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                team_a="BOS",
                team_b="MIL",
                season="2024-25",
                season_type="Regular Season",
            )
        run_output = buf.getvalue()

        result = build_result(
            team_a="BOS",
            team_b="MIL",
            season="2024-25",
            season_type="Regular Season",
        )
        assert result.to_labeled_text() == run_output


class TestBuildResultPlayerSplitSummary:
    @pytest.mark.needs_data
    def test_returns_split_summary_result(self):
        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, SplitSummaryResult)
        assert not result.summary.empty
        assert not result.split_comparison.empty
        assert set(result.split_comparison["bucket"]) == {"home", "away"}

    def test_returns_no_result_when_empty(self):
        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2024-25",
            player="Nonexistent Player XYZ",
            season_type="Regular Season",
        )
        assert isinstance(result, NoResult)

    def test_labeled_text_matches_run_output(self):
        from nbatools.commands.player_split_summary import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                split="home_away",
                season="2024-25",
                player="Nikola Jokić",
                season_type="Regular Season",
            )
        run_output = buf.getvalue()

        result = build_result(
            split="home_away",
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert result.to_labeled_text() == run_output


class TestBuildResultTeamSplitSummary:
    @pytest.mark.needs_data
    def test_returns_split_summary_result(self):
        from nbatools.commands.team_split_summary import build_result

        result = build_result(
            split="wins_losses",
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
        )
        assert isinstance(result, SplitSummaryResult)
        assert not result.summary.empty
        assert set(result.split_comparison["bucket"]) == {"wins", "losses"}

    def test_labeled_text_matches_run_output(self):
        from nbatools.commands.team_split_summary import build_result, run

        buf = StringIO()
        with redirect_stdout(buf):
            run(
                split="wins_losses",
                season="2024-25",
                team="BOS",
                season_type="Regular Season",
            )
        run_output = buf.getvalue()

        result = build_result(
            split="wins_losses",
            season="2024-25",
            team="BOS",
            season_type="Regular Season",
        )
        assert result.to_labeled_text() == run_output


# ---------------------------------------------------------------------------
# Integration: to_dict() round-trip guarantees
# ---------------------------------------------------------------------------


class TestToDictIntegration:
    @pytest.mark.needs_data
    @pytest.mark.engine
    def test_to_dict_has_normal_game_log_sample(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        assert isinstance(result, SummaryResult)

        d = result.to_dict()
        game_log = d["sections"]["game_log"]
        summary_row = d["sections"]["summary"][0]
        assert len(game_log) == summary_row["games"]
        assert {
            "game_date",
            "game_id",
            "opponent_team_abbr",
            "wl",
            "minutes",
            "pts",
            "reb",
            "ast",
        }.issubset(game_log[0])

    @pytest.mark.needs_data
    @pytest.mark.engine
    def test_to_dict_has_exact_last_n_game_log_sample(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
            last_n=5,
        )
        assert isinstance(result, SummaryResult)

        d = result.to_dict()
        game_log = d["sections"]["game_log"]
        assert len(game_log) == 5
        assert d["sections"]["summary"][0]["games"] == 5
        assert [row["game_date"] for row in game_log] == sorted(
            row["game_date"] for row in game_log
        )

    @pytest.mark.needs_data
    def test_player_summary_dict_has_by_season(self):
        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        d = result.to_dict()
        assert "by_season" in d["sections"]
        assert len(d["sections"]["by_season"]) >= 1

    @pytest.mark.needs_data
    def test_comparison_dict_has_metric_rows(self):
        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            season="2023-24",
            season_type="Regular Season",
        )
        d = result.to_dict()
        metrics = [r["metric"] for r in d["sections"]["comparison"]]
        assert "pts_avg" in metrics
        assert "win_pct" in metrics

    @pytest.mark.needs_data
    def test_split_dict_has_bucket_data(self):
        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2024-25",
            player="Nikola Jokić",
            season_type="Regular Season",
        )
        d = result.to_dict()
        buckets = [r["bucket"] for r in d["sections"]["split_comparison"]]
        assert "home" in buckets
        assert "away" in buckets

    def test_no_result_dict(self):
        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2024-25",
            team="ZZZ",
            season_type="Regular Season",
        )
        d = result.to_dict()
        assert d["result_status"] == "no_result"
        assert d["sections"] == {}
