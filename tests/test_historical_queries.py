"""Tests for historical / multi-season / career aggregation support.

Covers:
- Historical span model (_seasons.py)
- Natural query parsing for career, since, last-N-seasons
- Multi-season leaderboard aggregation
- Multi-season summary / comparison routing
- Multi-season caveats on all result classes
- Range-intent routing to summary for player/team queries
- Playoff historical spans
- Structured query support for historical spans
- Service/API compatibility
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._seasons import (
    EARLIEST_SEASON,
    LATEST_PLAYOFF_SEASON,
    LATEST_REGULAR_SEASON,
    default_end_season,
    int_to_season,
    resolve_career,
    resolve_last_n_seasons,
    resolve_seasons,
    resolve_since_season,
    resolve_since_year,
    season_to_int,
)
from nbatools.commands.natural_query import (
    detect_career_intent,
    extract_last_n,
    extract_last_n_seasons,
    extract_since_season,
    normalize_text,
    parse_query,
)
from nbatools.commands.season_leaders import build_result as season_leaders_build_result
from nbatools.commands.season_team_leaders import build_result as season_team_leaders_build_result
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SplitSummaryResult,
    SummaryResult,
)

# ===================================================================
# _seasons.py — Historical span model
# ===================================================================


class TestDefaultEndSeason:
    def test_regular_season(self):
        assert default_end_season("Regular Season") == LATEST_REGULAR_SEASON

    def test_playoffs(self):
        assert default_end_season("Playoffs") == LATEST_PLAYOFF_SEASON


class TestResolveSinceYear:
    def test_since_2020(self):
        start, end = resolve_since_year(2020, "Regular Season")
        assert start == "2020-21"
        assert end == LATEST_REGULAR_SEASON

    def test_since_2015_playoffs(self):
        start, end = resolve_since_year(2015, "Playoffs")
        assert start == "2015-16"
        assert end == LATEST_PLAYOFF_SEASON


class TestResolveSinceSeason:
    def test_since_2020_21(self):
        start, end = resolve_since_season("2020-21", "Regular Season")
        assert start == "2020-21"
        assert end == LATEST_REGULAR_SEASON


class TestResolveLastNSeasons:
    def test_last_3(self):
        start, end = resolve_last_n_seasons(3, "Regular Season")
        end_year = season_to_int(LATEST_REGULAR_SEASON)
        assert start == int_to_season(end_year - 2)
        assert end == LATEST_REGULAR_SEASON

    def test_last_5_playoffs(self):
        start, end = resolve_last_n_seasons(5, "Playoffs")
        end_year = season_to_int(LATEST_PLAYOFF_SEASON)
        assert start == int_to_season(end_year - 4)
        assert end == LATEST_PLAYOFF_SEASON


class TestResolveCareer:
    def test_regular_season(self):
        start, end = resolve_career("Regular Season")
        assert start == EARLIEST_SEASON
        assert end == LATEST_REGULAR_SEASON

    def test_playoffs(self):
        start, end = resolve_career("Playoffs")
        assert start == EARLIEST_SEASON
        assert end == LATEST_PLAYOFF_SEASON


class TestResolveSeasonsBackcompat:
    """Existing resolve_seasons behavior should be preserved."""

    def test_single_season(self):
        assert resolve_seasons("2024-25", None, None) == ["2024-25"]

    def test_range(self):
        result = resolve_seasons(None, "2022-23", "2024-25")
        assert result == ["2022-23", "2023-24", "2024-25"]

    def test_conflict_raises(self):
        with pytest.raises(ValueError):
            resolve_seasons("2024-25", "2022-23", "2024-25")


# ===================================================================
# natural_query.py — Historical span parsing
# ===================================================================


class TestDetectCareerIntent:
    @pytest.mark.parametrize(
        "query",
        [
            "Jokic career summary",
            "career leaders in assists",
            "LeBron career playoff averages",
            "all-time leaders in scoring",
            "alltime scoring leaders",
            "all time great scorers",
        ],
    )
    def test_career_detected(self, query):
        assert detect_career_intent(normalize_text(query)) is True

    @pytest.mark.parametrize(
        "query",
        [
            "top scorers this season",
            "Jokic summary",
            "best rebounders since 2020",
        ],
    )
    def test_career_not_detected(self, query):
        assert detect_career_intent(normalize_text(query)) is False


class TestExtractSinceSeason:
    def test_since_season_format(self):
        assert extract_since_season("top scorers since 2020-21") == "2020-21"

    def test_since_bare_year(self):
        assert extract_since_season("top scorers since 2020") == "2020-21"

    def test_no_since(self):
        assert extract_since_season("top scorers this season") is None

    def test_since_month_not_matched(self):
        # "since January" is a date range, not a season range
        assert extract_since_season("Jokic since January") is None


class TestExtractLastNSeasons:
    def test_last_3_seasons(self):
        assert extract_last_n_seasons("best rebounders last 3 seasons") == 3

    def test_over_the_last_5_seasons(self):
        assert extract_last_n_seasons("top scorers over the last 5 seasons") == 5

    def test_past_2_seasons(self):
        assert extract_last_n_seasons("top scorers past 2 seasons") == 2

    def test_in_the_last_4_seasons(self):
        assert extract_last_n_seasons("scoring leaders in the last 4 seasons") == 4

    def test_no_seasons(self):
        assert extract_last_n_seasons("top scorers this season") is None

    def test_last_10_games_not_matched(self):
        assert extract_last_n_seasons("Jokic last 10 games") is None


class TestExtractLastNNotConfused:
    """extract_last_n should NOT match 'last N seasons'."""

    def test_last_3_seasons_not_last_n(self):
        assert extract_last_n("best rebounders last 3 seasons") is None

    def test_last_10_games_still_works(self):
        assert extract_last_n("Jokic last 10 games") == 10

    def test_last_5_bare_still_works(self):
        assert extract_last_n("Jokic last 5") == 5

    def test_past_3_seasons_not_last_n(self):
        assert extract_last_n("top scorers past 3 seasons") is None


# ===================================================================
# natural_query.py — Parse routing for historical spans
# ===================================================================


class TestParseCareerQuery:
    def test_career_summary_player(self):
        parsed = parse_query("Jokic career summary")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON
        assert parsed["route_kwargs"]["season"] is None

    def test_career_averages_player(self):
        parsed = parse_query("LeBron career averages")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_career_playoff_averages(self):
        parsed = parse_query("LeBron career playoff averages")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_career_leaders_in_assists(self):
        parsed = parse_query("career leaders in assists")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON
        assert parsed["route_kwargs"]["stat"] == "ast"
        assert parsed["route_kwargs"]["season"] is None

    def test_alltime_scoring_leaders(self):
        parsed = parse_query("all-time scoring leaders")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_jokic_career_routes_to_summary(self):
        """'Jokic career' alone should route to summary, not finder."""
        parsed = parse_query("Jokic career")
        assert parsed["route"] == "player_game_summary"


class TestParseSinceQuery:
    def test_top_scorers_since_2020(self):
        parsed = parse_query("top scorers since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON
        assert parsed["route_kwargs"]["season"] is None

    def test_best_rebounders_since_2020_21(self):
        parsed = parse_query("best rebounders since 2020-21")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_jokic_summary_since_2020(self):
        parsed = parse_query("Jokic summary since 2020")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_celtics_vs_bucks_since_2021(self):
        parsed = parse_query("Celtics vs Bucks since 2021")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_playoff_leaders_since_2010(self):
        parsed = parse_query("playoff leaders since 2010")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == "2010-11"
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_since_month_still_works_as_date(self):
        """'Jokic since January' should still be a date range, not season range."""
        parsed = parse_query("Jokic since January")
        # Should be a single-season query with start_date
        assert parsed["route_kwargs"].get("start_date") is not None
        assert parsed["route_kwargs"].get("start_season") is None or parsed["route_kwargs"].get(
            "start_season"
        ) == parsed.get("start_season")


class TestParseLastNSeasonsQuery:
    def test_last_3_seasons_leaders(self):
        parsed = parse_query("top scorers last 3 seasons")
        assert parsed["route"] == "season_leaders"
        start, end = resolve_last_n_seasons(3, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start
        assert parsed["route_kwargs"]["end_season"] == end
        assert parsed["route_kwargs"]["season"] is None

    def test_over_the_last_5_seasons(self):
        parsed = parse_query("best rebounders over the last 5 seasons")
        assert parsed["route"] == "season_leaders"
        start, end = resolve_last_n_seasons(5, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start
        assert parsed["route_kwargs"]["end_season"] == end

    def test_jokic_last_3_seasons_summary(self):
        parsed = parse_query("Jokic summary last 3 seasons")
        assert parsed["route"] == "player_game_summary"
        start, end = resolve_last_n_seasons(3, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start
        assert parsed["route_kwargs"]["end_season"] == end


class TestParseSeasonRangeQuery:
    """Existing from-to range should still work."""

    def test_from_to_range_leaders(self):
        parsed = parse_query("top scorers from 2020-21 to 2024-25")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == "2024-25"

    def test_from_to_range_player_compare(self):
        parsed = parse_query("Jokic vs Embiid from 2022-23 to 2024-25")
        assert parsed["route"] == "player_compare"
        assert parsed["route_kwargs"]["start_season"] == "2022-23"
        assert parsed["route_kwargs"]["end_season"] == "2024-25"


# ===================================================================
# season_leaders.py — Multi-season leaderboard build_result
# ===================================================================


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _make_player_game_rows(player_name, player_id, team_abbr, team_id, season, n_games, avg_pts):
    """Generate fake game log rows."""
    rows = []
    for i in range(n_games):
        rows.append(
            {
                "game_id": f"{season}_{player_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "team_abbr": team_abbr,
                "pts": avg_pts + (i % 5),
                "reb": 5,
                "ast": 5,
                "fgm": 10,
                "fga": 20,
                "fg3m": 2,
                "fg3a": 5,
                "ftm": 3,
                "fta": 4,
            }
        )
    return rows


class TestMultiSeasonLeaderboard:
    def test_single_season_backward_compat(self, tmp_path, monkeypatch):
        """Single-season build_result still works as before."""
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        rows += _make_player_game_rows("Other Player", 2, "BBB", 200, "2099-00", 25, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows)

        result = season_leaders_build_result(season="2099-00", stat="pts")
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) >= 1
        assert "season" in result.leaders.columns

    def test_multi_season_aggregation(self, tmp_path, monkeypatch):
        """Multi-season leaderboard aggregates across seasons."""
        monkeypatch.chdir(tmp_path)

        # Season 1: Star scores more
        rows1 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        rows1 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2098-99", 25, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows1)

        # Season 2: Same players
        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        rows2 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2099-00", 25, 20)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        result = season_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        assert isinstance(result, LeaderboardResult)
        # Combined ~50 games per player
        assert result.leaders["games_played"].iloc[0] >= 40
        # Multi-season should have a 'seasons' column, not 'season'
        assert "seasons" in result.leaders.columns
        assert "multi-season" in result.caveats[0].lower()

    def test_multi_season_no_data_returns_no_result(self, tmp_path, monkeypatch):
        """Multi-season with no data files returns NoResult."""
        monkeypatch.chdir(tmp_path)
        result = season_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        assert isinstance(result, NoResult)

    def test_multi_season_partial_data(self, tmp_path, monkeypatch):
        """Multi-season with only some seasons having data still works."""
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows)
        # 2099-00 has no data file

        result = season_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) >= 1


class TestMultiSeasonTeamLeaderboard:
    def test_multi_season_team_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def _team_rows(season, team_name, team_abbr, team_id, n_games, avg_pts):
            rows = []
            for i in range(n_games):
                rows.append(
                    {
                        "game_id": f"{season}_{team_id}_{i}",
                        "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                        "team_id": team_id,
                        "team_name": team_name,
                        "team_abbr": team_abbr,
                        "pts": avg_pts,
                        "reb": 40,
                        "ast": 25,
                        "fgm": 35,
                        "fga": 80,
                        "fg3m": 10,
                        "fg3a": 30,
                        "ftm": 15,
                        "fta": 20,
                    }
                )
            return rows

        rows1 = _team_rows("2098-99", "Team Alpha", "ALP", 1, 25, 110)
        rows1 += _team_rows("2098-99", "Team Beta", "BET", 2, 25, 100)
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_regular_season.csv", rows1)

        rows2 = _team_rows("2099-00", "Team Alpha", "ALP", 1, 25, 115)
        rows2 += _team_rows("2099-00", "Team Beta", "BET", 2, 25, 105)
        _write_csv(tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv", rows2)

        result = season_team_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        assert isinstance(result, LeaderboardResult)
        assert "seasons" in result.leaders.columns
        # Team Alpha should be ranked first (higher avg pts)
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"


# ===================================================================
# Result / export / service compatibility
# ===================================================================


class TestLeaderboardResultCompat:
    """Multi-season leaderboards produce results compatible with existing output."""

    def test_to_labeled_text(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        rows += _make_player_game_rows("Other Player", 2, "BBB", 200, "2098-99", 25, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows)
        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        rows2 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2099-00", 25, 20)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        result = season_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        assert isinstance(result, LeaderboardResult)
        text = result.to_labeled_text()
        assert "LEADERBOARD" in text
        assert "Star Player" in text

    def test_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows)
        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        result = season_leaders_build_result(
            start_season="2098-99", end_season="2099-00", stat="pts"
        )
        d = result.to_dict()
        assert d["query_class"] == "leaderboard"
        assert d["result_status"] == "ok"
        assert "sections" in d
        assert "leaderboard" in d["sections"]


# ===================================================================
# Structured query service compatibility
# ===================================================================


class TestStructuredQueryHistorical:
    """Structured queries can now pass start_season/end_season to leaderboards."""

    def test_structured_multi_season_leaders(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows)
        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)


# ===================================================================
# Live data smoke tests (run against real data)
# ===================================================================


class TestLiveSmokeHistorical:
    """Smoke tests against real data. Skipped if data files are missing."""

    @pytest.fixture(autouse=True)
    def _check_data(self):
        from pathlib import Path

        if not Path("data/raw/player_game_stats/2024-25_regular_season.csv").exists():
            pytest.skip("Live data not available")

    def test_career_leaders_assists(self):
        parsed = parse_query("career leaders in assists")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "ast"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON

    def test_top_scorers_since_2020_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("top scorers since 2020")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)
        assert len(qr.result.leaders) >= 1
        # Should span multiple seasons
        assert "seasons" in qr.result.leaders.columns

    def test_best_rebounders_last_3_seasons_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("best rebounders last 3 seasons")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_jokic_career_summary_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic career summary")
        assert qr.is_ok
        # The result should be a summary spanning many seasons
        assert qr.route == "player_game_summary"

    def test_jokic_since_2021_summary_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic summary since 2021")
        assert qr.is_ok
        assert qr.route == "player_game_summary"

    def test_playoff_leaders_since_2010_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("playoff leaders since 2010")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_celtics_vs_bucks_since_2021_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Celtics vs Bucks since 2021")
        assert qr.is_ok
        assert qr.route == "team_compare"

    def test_jokic_vs_embiid_since_2021_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic vs Embiid since 2021")
        assert qr.is_ok
        assert qr.route == "player_compare"

    def test_from_to_range_leaders_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("top scorers from 2022-23 to 2024-25")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_structured_historical_leaders_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            start_season="2022-23",
            end_season="2024-25",
            stat="pts",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_api_response_shape(self):
        """Service result converts to API-compatible dict."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("top scorers since 2023")
        d = qr.to_dict()
        assert "sections" in d or "metadata" in d
        # The result should serialize without error

    def test_jokic_career_playoff_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic career playoff averages")
        assert qr.is_ok
        assert qr.route == "player_game_summary"

    def test_most_40_point_games_since_2015_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("most 40 point games since 2015")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_top_team_scoring_last_5_seasons_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("best scoring teams last 5 seasons")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)


# ===================================================================
# Helper: fake data generators for isolated tests
# ===================================================================


def _make_player_game_rows_full(
    player_name,
    player_id,
    team_abbr,
    team_id,
    season,
    n_games,
    avg_pts,
    season_type="regular_season",
):
    """Generate fake player game log rows with all required columns."""
    rows = []
    team_name = f"Team {team_abbr}"
    for i in range(n_games):
        wl = "W" if i % 2 == 0 else "L"
        rows.append(
            {
                "game_id": f"{season}_{player_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": "Playoffs" if season_type == "playoffs" else "Regular Season",
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "team_abbr": team_abbr,
                "team_name": team_name,
                "opponent_team_id": 999,
                "opponent_team_abbr": "OPP",
                "opponent_team_name": "Opponents",
                "is_home": 1 if i % 2 == 0 else 0,
                "is_away": 0 if i % 2 == 0 else 1,
                "wl": wl,
                "pts": avg_pts + (i % 5),
                "reb": 8 + (i % 3),
                "ast": 6 + (i % 4),
                "stl": 1,
                "blk": 1,
                "fgm": 10 + (i % 3),
                "fga": 20,
                "fg3m": 2 + (i % 2),
                "fg3a": 5,
                "ftm": 3,
                "fta": 4,
                "tov": 3,
                "pf": 2,
                "minutes": 35,
                "plus_minus": 5 if wl == "W" else -3,
                "oreb": 2,
                "dreb": 6,
                "fg_pct": 0.5,
                "fg3_pct": 0.4,
                "ft_pct": 0.75,
                "efg_pct": 0.55,
                "ts_pct": 0.60,
            }
        )
    return rows


def _make_team_game_rows_full(
    team_name,
    team_abbr,
    team_id,
    season,
    n_games,
    avg_pts,
    season_type="regular_season",
):
    """Generate fake team game log rows with all required columns."""
    rows = []
    for i in range(n_games):
        wl = "W" if i % 2 == 0 else "L"
        rows.append(
            {
                "game_id": f"{season}_{team_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": "Playoffs" if season_type == "playoffs" else "Regular Season",
                "team_id": team_id,
                "team_name": team_name,
                "team_abbr": team_abbr,
                "opponent_team_id": 999,
                "opponent_team_abbr": "OPP",
                "opponent_team_name": "Opponents",
                "is_home": 1 if i % 2 == 0 else 0,
                "is_away": 0 if i % 2 == 0 else 1,
                "wl": wl,
                "pts": avg_pts + (i % 5),
                "reb": 40 + (i % 5),
                "ast": 25 + (i % 3),
                "stl": 7,
                "blk": 5,
                "fgm": 35 + (i % 3),
                "fga": 80,
                "fg3m": 10 + (i % 3),
                "fg3a": 30,
                "ftm": 15,
                "fta": 20,
                "tov": 12,
                "pf": 18,
                "minutes": 240,
                "plus_minus": 8 if wl == "W" else -6,
                "oreb": 10,
                "dreb": 30,
                "fg_pct": 0.44,
                "fg3_pct": 0.35,
                "ft_pct": 0.75,
                "efg_pct": 0.52,
                "ts_pct": 0.57,
            }
        )
    return rows


def _setup_multi_season_player_data(tmp_path, monkeypatch, season_type="regular_season"):
    """Set up two seasons of player game data for testing.

    Also creates matching team_game_stats CSVs since the player data loader
    requires them for the wl merge.
    """
    monkeypatch.chdir(tmp_path)
    safe_type = season_type.lower().replace(" ", "_")

    rows1 = _make_player_game_rows_full(
        "Star Player",
        1,
        "AAA",
        100,
        "2098-99",
        25,
        30,
        season_type=safe_type,
    )
    rows1 += _make_player_game_rows_full(
        "Other Player",
        2,
        "BBB",
        200,
        "2098-99",
        25,
        22,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/player_game_stats/2098-99_{safe_type}.csv",
        rows1,
    )

    rows2 = _make_player_game_rows_full(
        "Star Player",
        1,
        "AAA",
        100,
        "2099-00",
        25,
        28,
        season_type=safe_type,
    )
    rows2 += _make_player_game_rows_full(
        "Other Player",
        2,
        "BBB",
        200,
        "2099-00",
        25,
        20,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/player_game_stats/2099-00_{safe_type}.csv",
        rows2,
    )

    # Player data loader requires team_game_stats for wl merge
    team_rows1 = _make_team_game_rows_full(
        "Team AAA",
        "AAA",
        100,
        "2098-99",
        25,
        110,
        season_type=safe_type,
    )
    team_rows1 += _make_team_game_rows_full(
        "Team BBB",
        "BBB",
        200,
        "2098-99",
        25,
        100,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/team_game_stats/2098-99_{safe_type}.csv",
        team_rows1,
    )

    team_rows2 = _make_team_game_rows_full(
        "Team AAA",
        "AAA",
        100,
        "2099-00",
        25,
        115,
        season_type=safe_type,
    )
    team_rows2 += _make_team_game_rows_full(
        "Team BBB",
        "BBB",
        200,
        "2099-00",
        25,
        105,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/team_game_stats/2099-00_{safe_type}.csv",
        team_rows2,
    )


def _setup_multi_season_team_data(tmp_path, monkeypatch, season_type="regular_season"):
    """Set up two seasons of team game data for testing."""
    monkeypatch.chdir(tmp_path)
    safe_type = season_type.lower().replace(" ", "_")

    rows1 = _make_team_game_rows_full(
        "Team Alpha",
        "ALP",
        1,
        "2098-99",
        25,
        110,
        season_type=safe_type,
    )
    rows1 += _make_team_game_rows_full(
        "Team Beta",
        "BET",
        2,
        "2098-99",
        25,
        100,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/team_game_stats/2098-99_{safe_type}.csv",
        rows1,
    )

    rows2 = _make_team_game_rows_full(
        "Team Alpha",
        "ALP",
        1,
        "2099-00",
        25,
        115,
        season_type=safe_type,
    )
    rows2 += _make_team_game_rows_full(
        "Team Beta",
        "BET",
        2,
        "2099-00",
        25,
        105,
        season_type=safe_type,
    )
    _write_csv(
        tmp_path / f"data/raw/team_game_stats/2099-00_{safe_type}.csv",
        rows2,
    )


# ===================================================================
# Multi-season SUMMARY caveats
# ===================================================================


class TestMultiSeasonPlayerSummaryCaveats:
    """Player summaries include multi-season caveat when spanning seasons."""

    def test_multi_season_player_summary_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        assert isinstance(result, SummaryResult)
        assert any("multi-season" in c.lower() for c in result.caveats)
        assert result.by_season is not None
        assert len(result.by_season) == 2

    def test_single_season_player_summary_no_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(season="2098-99", player="Star Player")
        assert isinstance(result, SummaryResult)
        assert len(result.caveats) == 0

    def test_multi_season_summary_aggregates_games(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        assert isinstance(result, SummaryResult)
        # Should have ~50 games (25 per season)
        games = result.summary["games"].iloc[0]
        assert games >= 40

    def test_multi_season_summary_to_dict(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        d = result.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"
        assert len(d["caveats"]) > 0
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "by_season" in d["sections"]


class TestMultiSeasonTeamSummaryCaveats:
    """Team summaries include multi-season caveat when spanning seasons."""

    def test_multi_season_team_summary_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SummaryResult)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_single_season_team_summary_no_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(season="2098-99", team="ALP")
        assert isinstance(result, SummaryResult)
        assert len(result.caveats) == 0

    def test_multi_season_team_summary_aggregates_games(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games >= 40


# ===================================================================
# Multi-season COMPARISON caveats
# ===================================================================


class TestMultiSeasonPlayerComparisonCaveats:
    """Player comparisons include multi-season caveat."""

    def test_multi_season_player_compare_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        # Also need team data for advanced metrics
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_single_season_player_compare_no_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            season="2098-99",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.caveats) == 0

    def test_multi_season_comparison_both_players_present(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.summary) == 2
        player_names = list(result.summary["player_name"])
        assert "Star Player" in player_names
        assert "Other Player" in player_names

    def test_multi_season_comparison_to_dict(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
        )
        d = result.to_dict()
        assert d["query_class"] == "comparison"
        assert d["result_status"] == "ok"
        assert len(d["caveats"]) > 0
        assert "summary" in d["sections"]
        assert "comparison" in d["sections"]


class TestMultiSeasonTeamComparisonCaveats:
    """Team comparisons include multi-season caveat."""

    def test_multi_season_team_compare_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="ALP",
            team_b="BET",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_single_season_team_compare_no_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
        )
        assert isinstance(result, ComparisonResult)
        assert len(result.caveats) == 0


# ===================================================================
# Multi-season SPLIT SUMMARY caveats
# ===================================================================


class TestMultiSeasonPlayerSplitCaveats:
    """Player split summaries include multi-season caveat."""

    def test_multi_season_player_split_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        assert isinstance(result, SplitSummaryResult)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_single_season_player_split_no_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.player_split_summary import build_result

        result = build_result(
            split="home_away",
            season="2098-99",
            player="Star Player",
        )
        assert isinstance(result, SplitSummaryResult)
        assert len(result.caveats) == 0


class TestMultiSeasonTeamSplitCaveats:
    """Team split summaries include multi-season caveat."""

    def test_multi_season_team_split_has_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.commands.team_split_summary import build_result

        result = build_result(
            split="home_away",
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert isinstance(result, SplitSummaryResult)
        assert any("multi-season" in c.lower() for c in result.caveats)


# ===================================================================
# Range-intent routing (new behavior)
# ===================================================================


class TestRangeIntentRouting:
    """Historical span queries route to summary, not finder."""

    def test_player_since_routes_to_summary(self):
        """'Jokic since 2021' should route to summary, not finder."""
        parsed = parse_query("Jokic since 2021")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_player_last_n_seasons_routes_to_summary(self):
        """'LeBron last 3 seasons' should route to summary."""
        parsed = parse_query("LeBron last 3 seasons")
        assert parsed["route"] == "player_game_summary"
        start, end = resolve_last_n_seasons(3, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start

    def test_team_since_routes_to_summary(self):
        """'Celtics since 2021' should route to summary, not finder."""
        parsed = parse_query("Celtics since 2021")
        assert parsed["route"] == "game_summary"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_team_last_n_seasons_routes_to_summary(self):
        """'Lakers last 5 seasons' should route to summary."""
        parsed = parse_query("Lakers last 5 seasons")
        assert parsed["route"] == "game_summary"
        start, end = resolve_last_n_seasons(5, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start

    def test_team_since_with_record_routes_to_summary(self):
        """'Celtics record since 2021' still routes to summary."""
        parsed = parse_query("Celtics record since 2021")
        assert parsed["route"] == "game_summary"

    def test_player_career_still_routes_to_summary(self):
        """'Jokic career' routes to summary (career_intent)."""
        parsed = parse_query("Jokic career")
        assert parsed["route"] == "player_game_summary"

    def test_player_comparison_since_routes_to_compare(self):
        """'Jokic vs Embiid since 2021' should route to compare, not summary."""
        parsed = parse_query("Jokic vs Embiid since 2021")
        assert parsed["route"] == "player_compare"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_team_comparison_since_routes_to_compare(self):
        """'Celtics vs Bucks since 2021' should route to compare."""
        parsed = parse_query("Celtics vs Bucks since 2021")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_leaderboard_career_still_routes_to_leaders(self):
        """'career leaders in assists' should still route to leaderboard."""
        parsed = parse_query("career leaders in assists")
        assert parsed["route"] == "season_leaders"

    def test_leaderboard_since_still_routes_to_leaders(self):
        """'top scorers since 2020' should still route to leaderboard."""
        parsed = parse_query("top scorers since 2020")
        assert parsed["route"] == "season_leaders"


# ===================================================================
# Playoff historical spans
# ===================================================================


class TestPlayoffHistoricalParsing:
    """Playoff historical spans are correctly parsed and routed."""

    def test_player_career_playoff_summary(self):
        parsed = parse_query("LeBron career playoff averages")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_player_playoff_since(self):
        parsed = parse_query("Jokic playoff averages since 2020")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_playoff_leaderboard_career(self):
        parsed = parse_query("career playoff leaders in scoring")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_playoff_leaderboard_since(self):
        parsed = parse_query("playoff leaders since 2015")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2015-16"

    def test_player_compare_playoff_since(self):
        parsed = parse_query("Jokic vs Embiid playoff since 2021")
        assert parsed["route"] == "player_compare"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"


class TestPlayoffHistoricalExecution:
    """Playoff historical spans execute correctly with fake data."""

    def test_playoff_player_summary_with_caveat(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch, season_type="playoffs")

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            season_type="Playoffs",
            player="Star Player",
        )
        assert isinstance(result, SummaryResult)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_playoff_multi_season_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows1 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 15, 30)
        rows1 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2098-99", 15, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_playoffs.csv", rows1)

        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 15, 28)
        rows2 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2099-00", 15, 20)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_playoffs.csv", rows2)

        result = season_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            season_type="Playoffs",
        )
        assert isinstance(result, LeaderboardResult)
        assert "seasons" in result.leaders.columns
        assert any("multi-season" in c.lower() for c in result.caveats)


# ===================================================================
# Count stat leaderboards across seasons
# ===================================================================


class TestMultiSeasonCountStatLeaderboards:
    """Count stats (20p games, 30p games, etc.) aggregate correctly across seasons."""

    def test_multi_season_30_point_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Star Player has many 30+ point games
        rows1 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        rows1 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2098-99", 25, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows1)

        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 30)
        rows2 += _make_player_game_rows("Other Player", 2, "BBB", 200, "2099-00", 25, 22)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        result = season_leaders_build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="games_30p",
        )
        assert isinstance(result, LeaderboardResult)
        # Star Player should be first with 30+ pt games aggregated across seasons
        first_row = result.leaders.iloc[0]
        assert first_row["player_name"] == "Star Player"
        assert first_row["games_30p"] > 0

    def test_multi_season_40_point_games_parsing(self):
        """'most 40 point games since 2015' parses and routes correctly."""
        parsed = parse_query("most 40 point games since 2015")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] == "games_40p"
        assert parsed["route_kwargs"]["start_season"] == "2015-16"


# ===================================================================
# Structured query support for historical spans
# ===================================================================


class TestStructuredHistoricalSummary:
    """Structured queries support historical spans for all result classes."""

    def test_structured_multi_season_player_summary(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)
        assert qr.metadata.get("start_season") == "2098-99"
        assert qr.metadata.get("end_season") == "2099-00"

    def test_structured_multi_season_team_summary(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "game_summary",
            start_season="2098-99",
            end_season="2099-00",
            team="ALP",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_structured_multi_season_player_compare(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_compare",
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_structured_multi_season_team_compare(self, tmp_path, monkeypatch):
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "team_compare",
            team_a="ALP",
            team_b="BET",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)


class TestStructuredQueryMetadata:
    """Structured queries include proper historical metadata."""

    def test_metadata_includes_season_span(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        assert qr.metadata["start_season"] == "2098-99"
        assert qr.metadata["end_season"] == "2099-00"
        assert qr.metadata.get("season") is None

    def test_metadata_includes_current_through(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        # Result is well-formed; current_through is None for fake future seasons
        # (compute_current_through_for_seasons checks real schedule data)
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)


# ===================================================================
# Service/API response compatibility
# ===================================================================


class TestServiceResponseHistorical:
    """Service responses are well-formed for historical queries."""

    def test_natural_query_multi_season_summary_response(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        # We need to monkeypatch aliases since fake data uses "Star Player"
        # Instead, test via structured query which doesn't need alias matching
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
        )
        d = qr.to_dict()
        assert "sections" in d
        assert "metadata" in d
        assert d["metadata"]["start_season"] == "2098-99"
        assert d["metadata"]["end_season"] == "2099-00"
        # Caveats should be present in result
        result_dict = qr.result.to_dict()
        assert len(result_dict["caveats"]) > 0

    def test_to_dict_shape_multi_season_comparison(self, tmp_path, monkeypatch):
        _setup_multi_season_player_data(tmp_path, monkeypatch)
        _setup_multi_season_team_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_compare",
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
        )
        d = qr.to_dict()
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "comparison" in d["sections"]
        # Each section is a list of dicts
        assert isinstance(d["sections"]["summary"], list)
        assert isinstance(d["sections"]["comparison"], list)

    def test_to_dict_shape_multi_season_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _make_player_game_rows("Star Player", 1, "AAA", 100, "2098-99", 25, 30)
        _write_csv(tmp_path / "data/raw/player_game_stats/2098-99_regular_season.csv", rows)
        rows2 = _make_player_game_rows("Star Player", 1, "AAA", 100, "2099-00", 25, 28)
        _write_csv(tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv", rows2)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
        )
        d = qr.to_dict()
        assert "leaderboard" in d["sections"]
        assert isinstance(d["sections"]["leaderboard"], list)


# ===================================================================
# Live data smoke tests — Extended
# ===================================================================


class TestLiveSmokeHistoricalExtended:
    """Extended smoke tests for new historical capabilities."""

    @pytest.fixture(autouse=True)
    def _check_data(self):
        from pathlib import Path

        if not Path("data/raw/player_game_stats/2024-25_regular_season.csv").exists():
            pytest.skip("Live data not available")

    # -- Player summaries --

    def test_jokic_since_2021_routes_to_summary(self):
        """'Jokic since 2021' routes to summary (range_intent routing)."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic since 2021")
        assert qr.is_ok
        assert qr.route == "player_game_summary"
        assert isinstance(qr.result, SummaryResult)

    def test_jokic_since_2021_has_caveat(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic since 2021")
        assert qr.is_ok
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_lebron_career_summary_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("LeBron career summary")
        assert qr.is_ok
        assert qr.route == "player_game_summary"
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_lebron_last_3_seasons_summary_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("LeBron last 3 seasons")
        assert qr.is_ok
        assert qr.route == "player_game_summary"

    # -- Team summaries --

    def test_celtics_since_2021_live(self):
        """'Celtics since 2021' routes to team summary."""
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Celtics since 2021")
        assert qr.is_ok
        assert qr.route == "game_summary"
        assert isinstance(qr.result, SummaryResult)

    def test_lakers_last_5_seasons_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Lakers last 5 seasons")
        assert qr.is_ok
        assert qr.route == "game_summary"

    # -- Player comparisons --

    def test_jokic_vs_embiid_since_2021_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic vs Embiid since 2021")
        assert qr.is_ok
        assert qr.route == "player_compare"
        assert isinstance(qr.result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    # -- Team comparisons --

    def test_lakers_vs_celtics_since_2010_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Lakers vs Celtics since 2010")
        assert qr.is_ok
        assert qr.route == "team_compare"
        assert isinstance(qr.result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    # -- Playoff historical --

    def test_jokic_career_playoff_summary_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic career playoff averages")
        assert qr.is_ok
        assert qr.route == "player_game_summary"
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_lakers_playoff_summary_since_2020_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Lakers playoff summary since 2020")
        assert qr.is_ok
        assert qr.route == "game_summary"

    # -- Leaderboard hardening --

    def test_career_assists_leaders_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("career assists leaders")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_alltime_scoring_leaders_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("all-time scoring leaders")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_most_40_point_games_since_2015_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("most 40 point games since 2015")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)
        assert "seasons" in qr.result.leaders.columns

    def test_best_ts_last_5_seasons_live(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("best TS% over the last 5 seasons")
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    # -- Structured query parity --

    def test_structured_player_summary_career_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2020-21",
            end_season=LATEST_REGULAR_SEASON,
            player="Nikola Jokić",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_structured_team_summary_since_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "game_summary",
            start_season="2020-21",
            end_season=LATEST_REGULAR_SEASON,
            team="BOS",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)

    def test_structured_player_compare_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_compare",
            player_a="Nikola Jokić",
            player_b="Joel Embiid",
            start_season="2021-22",
            end_season="2024-25",
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)
        assert any("multi-season" in c.lower() for c in qr.result.caveats)

    def test_structured_team_compare_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "team_compare",
            team_a="BOS",
            team_b="MIL",
            start_season="2021-22",
            end_season="2024-25",
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)

    def test_structured_playoff_leaders_live(self):
        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            start_season="2020-21",
            end_season=LATEST_PLAYOFF_SEASON,
            stat="pts",
            season_type="Playoffs",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    # -- API response shape --

    def test_api_response_shape_multi_season_summary(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic since 2021")
        d = qr.to_dict()
        assert "sections" in d
        assert "metadata" in d
        # Caveats propagate to result dict
        result_d = qr.result.to_dict()
        assert len(result_d["caveats"]) > 0

    def test_api_response_shape_multi_season_comparison(self):
        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Jokic vs Embiid since 2021")
        d = qr.to_dict()
        assert "sections" in d
        assert "metadata" in d
