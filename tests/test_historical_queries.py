"""Tests for historical / multi-season / career aggregation support.

Covers:
- Historical span model (_seasons.py)
- Natural query parsing for career, since, last-N-seasons
- Multi-season leaderboard aggregation
- Multi-season summary / comparison routing
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
from nbatools.commands.structured_results import LeaderboardResult, NoResult

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
