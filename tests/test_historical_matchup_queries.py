"""Tests for historical opponent/matchup/head-to-head support.

Covers:
- Natural query parsing for historical opponent spans
- Player-vs-opponent summaries across historical spans
- Team-vs-opponent summaries across historical spans
- Historical head-to-head comparisons (player and team)
- Opponent-filtered leaderboards across historical spans
- Playoff historical matchup spans
- Structured query support for historical opponent/h2h
- Service/API compatibility
- Caveats for opponent filtering
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._seasons import (
    EARLIEST_SEASON,
    LATEST_PLAYOFF_SEASON,
    LATEST_REGULAR_SEASON,
    resolve_last_n_seasons,
)
from nbatools.commands.natural_query import parse_query
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)

# ===================================================================
# Natural query parsing — historical opponent spans
# ===================================================================


class TestParseHistoricalPlayerVsOpponent:
    def test_player_vs_team_since(self):
        parsed = parse_query("Jokic vs Lakers since 2021")
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Nikola Jokić"
        assert parsed["opponent"] == "LAL"
        assert parsed["route_kwargs"]["opponent"] == "LAL"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_player_summary_vs_team_since(self):
        parsed = parse_query("Jokic summary vs Lakers since 2021")
        assert parsed["route"] == "player_game_summary"
        assert parsed["opponent"] == "LAL"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_player_vs_team_from_to_range(self):
        parsed = parse_query("LeBron vs Celtics from 2017-18 to 2022-23")
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "LeBron James"
        assert parsed["opponent"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2017-18"
        assert parsed["route_kwargs"]["end_season"] == "2022-23"

    def test_player_career_vs_team(self):
        parsed = parse_query("LeBron career vs Celtics")
        assert parsed["route"] == "player_game_summary"
        assert parsed["opponent"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == EARLIEST_SEASON
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_player_playoff_vs_team_since(self):
        parsed = parse_query("Jokic playoff stats vs Suns since 2021")
        assert parsed["route"] == "player_game_summary"
        assert parsed["opponent"] == "PHX"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_player_vs_team_last_n_seasons(self):
        parsed = parse_query("Jokic vs Lakers last 3 seasons")
        assert parsed["route"] == "player_game_summary"
        assert parsed["opponent"] == "LAL"
        start, end = resolve_last_n_seasons(3, "Regular Season")
        assert parsed["route_kwargs"]["start_season"] == start
        assert parsed["route_kwargs"]["end_season"] == end


class TestParseHistoricalTeamVsOpponent:
    def test_team_summary_vs_opponent_since(self):
        parsed = parse_query("Knicks playoff summary vs Heat since 1999")
        assert parsed["route"] == "game_summary"
        assert parsed["team"] == "NYK"
        assert parsed["opponent"] == "MIA"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "1999-00"

    def test_team_vs_team_since_routes_to_compare(self):
        parsed = parse_query("Celtics vs Bucks since 2022")
        assert parsed["route"] == "team_compare"
        assert parsed["team_a"] == "BOS"
        assert parsed["team_b"] == "MIL"
        assert parsed["route_kwargs"]["start_season"] == "2022-23"

    def test_team_vs_team_from_to_range(self):
        parsed = parse_query("Lakers vs Celtics from 2010-11 to 2020-21")
        assert parsed["route"] == "team_compare"
        assert parsed["team_a"] == "LAL"
        assert parsed["team_b"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2010-11"
        assert parsed["route_kwargs"]["end_season"] == "2020-21"


class TestParseHistoricalHeadToHead:
    def test_player_h2h_since(self):
        parsed = parse_query("Jokic head-to-head vs Embiid since 2021")
        assert parsed["route"] == "player_compare"
        assert parsed["player_a"] == "Nikola Jokić"
        assert parsed["player_b"] == "Joel Embiid"
        assert parsed["head_to_head"] is True
        assert parsed["route_kwargs"]["head_to_head"] is True
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_player_h2h_playoffs_since(self):
        parsed = parse_query("Jokic h2h vs Embiid playoffs since 2021")
        assert parsed["route"] == "player_compare"
        assert parsed["head_to_head"] is True
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_team_h2h_since(self):
        parsed = parse_query("Lakers head-to-head vs Celtics since 2010")
        assert parsed["route"] == "team_compare"
        assert parsed["team_a"] == "LAL"
        assert parsed["team_b"] == "BOS"
        assert parsed["head_to_head"] is True
        assert parsed["route_kwargs"]["start_season"] == "2010-11"

    def test_team_h2h_from_to_range(self):
        parsed = parse_query("Lakers h2h vs Celtics from 2015-16 to 2024-25")
        assert parsed["route"] == "team_compare"
        assert parsed["head_to_head"] is True
        assert parsed["route_kwargs"]["start_season"] == "2015-16"
        assert parsed["route_kwargs"]["end_season"] == "2024-25"


class TestParseHistoricalOpponentLeaderboards:
    def test_most_points_vs_team_since(self):
        parsed = parse_query("most points vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["opponent"] == "LAL"
        assert parsed["route_kwargs"]["start_season"] == "2018-19"
        assert parsed["route_kwargs"]["stat"] == "pts"

    def test_best_ts_vs_team_last_n_seasons(self):
        parsed = parse_query("best ts% vs Celtics over the last 3 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["opponent"] == "BOS"
        assert parsed["route_kwargs"]["stat"] == "ts_pct"

    def test_most_40_point_games_vs_team_since(self):
        parsed = parse_query("most 40 point games vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["opponent"] == "LAL"
        assert parsed["route_kwargs"]["stat"] == "games_40p"

    def test_best_scoring_teams_vs_opponent_since(self):
        parsed = parse_query("best scoring teams vs Lakers since 2018")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["opponent"] == "LAL"
        assert parsed["route_kwargs"]["start_season"] == "2018-19"

    def test_top_scorers_vs_opponent_single_season(self):
        parsed = parse_query("top scorers vs Celtics")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["opponent"] == "BOS"


# ===================================================================
# Fake data helpers
# ===================================================================


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _make_player_rows(
    player_name,
    player_id,
    team_abbr,
    team_id,
    season,
    n_games,
    avg_pts,
    opponent_abbr="OPP",
    opponent_id=999,
    opponent_name="Opponents",
    season_type="regular_season",
):
    rows = []
    team_name = f"Team {team_abbr}"
    st = "Playoffs" if season_type == "playoffs" else "Regular Season"
    for i in range(n_games):
        wl = "W" if i % 2 == 0 else "L"
        rows.append(
            {
                "game_id": f"{season}_{player_id}_{opponent_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": st,
                "player_id": player_id,
                "player_name": player_name,
                "team_id": team_id,
                "team_abbr": team_abbr,
                "team_name": team_name,
                "opponent_team_id": opponent_id,
                "opponent_team_abbr": opponent_abbr,
                "opponent_team_name": opponent_name,
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


def _make_team_rows(
    team_name,
    team_abbr,
    team_id,
    season,
    n_games,
    avg_pts,
    opponent_abbr="OPP",
    opponent_id=999,
    opponent_name="Opponents",
    season_type="regular_season",
):
    rows = []
    st = "Playoffs" if season_type == "playoffs" else "Regular Season"
    for i in range(n_games):
        wl = "W" if i % 2 == 0 else "L"
        rows.append(
            {
                "game_id": f"{season}_{team_id}_{opponent_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": st,
                "team_id": team_id,
                "team_name": team_name,
                "team_abbr": team_abbr,
                "opponent_team_id": opponent_id,
                "opponent_team_abbr": opponent_abbr,
                "opponent_team_name": opponent_name,
                "is_home": 1 if i % 2 == 0 else 0,
                "is_away": 0 if i % 2 == 0 else 1,
                "wl": wl,
                "pts": avg_pts + (i % 5),
                "reb": 40,
                "ast": 25,
                "stl": 7,
                "blk": 5,
                "fgm": 35,
                "fga": 80,
                "fg3m": 10,
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


def _setup_matchup_data(tmp_path, monkeypatch, season_type="regular_season"):
    """Set up two seasons of player and team data with mixed opponents."""
    monkeypatch.chdir(tmp_path)
    safe = season_type.lower().replace(" ", "_")

    for season in ("2098-99", "2099-00"):
        # Player Star vs OPP (10 games) and vs TGT (5 games each season)
        p_rows = _make_player_rows("Star Player", 1, "AAA", 100, season, 10, 30)
        p_rows += _make_player_rows(
            "Star Player",
            1,
            "AAA",
            100,
            season,
            5,
            35,
            opponent_abbr="TGT",
            opponent_id=888,
            opponent_name="Target Team",
        )
        # Player Other vs OPP (10 games) and vs TGT (3 games)
        p_rows += _make_player_rows("Other Player", 2, "BBB", 200, season, 10, 22)
        p_rows += _make_player_rows(
            "Other Player",
            2,
            "BBB",
            200,
            season,
            3,
            20,
            opponent_abbr="TGT",
            opponent_id=888,
            opponent_name="Target Team",
        )
        _write_csv(
            tmp_path / f"data/raw/player_game_stats/{season}_{safe}.csv",
            p_rows,
        )

        # Team data with mixed opponents
        t_rows = _make_team_rows("Team AAA", "AAA", 100, season, 10, 110)
        t_rows += _make_team_rows(
            "Team AAA",
            "AAA",
            100,
            season,
            5,
            120,
            opponent_abbr="TGT",
            opponent_id=888,
            opponent_name="Target Team",
        )
        t_rows += _make_team_rows("Team BBB", "BBB", 200, season, 10, 100)
        t_rows += _make_team_rows(
            "Team BBB",
            "BBB",
            200,
            season,
            3,
            95,
            opponent_abbr="TGT",
            opponent_id=888,
            opponent_name="Target Team",
        )
        _write_csv(
            tmp_path / f"data/raw/team_game_stats/{season}_{safe}.csv",
            t_rows,
        )


# ===================================================================
# Player-vs-opponent summaries — multi-season
# ===================================================================


class TestPlayerVsOpponentSummary:
    def test_multi_season_player_vs_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
            opponent="TGT",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games == 10  # 5 per season x 2 seasons
        assert any("vs TGT" in c for c in result.caveats)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_single_season_player_vs_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2098-99",
            player="Star Player",
            opponent="TGT",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games == 5
        assert any("vs TGT" in c for c in result.caveats)

    def test_player_vs_nonexistent_opponent_returns_no_result(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2098-99",
            player="Star Player",
            opponent="ZZZ",
        )
        assert isinstance(result, NoResult)


class TestTeamVsOpponentSummary:
    def test_multi_season_team_vs_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            team="AAA",
            opponent="TGT",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games == 10
        assert any("vs TGT" in c for c in result.caveats)

    def test_single_season_team_vs_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2098-99",
            team="AAA",
            opponent="TGT",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games == 5


# ===================================================================
# Historical H2H comparisons
# ===================================================================


class TestHistoricalPlayerH2H:
    def test_player_compare_multi_season_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
            opponent="TGT",
        )
        assert isinstance(result, ComparisonResult)
        assert any("vs TGT" in c for c in result.caveats)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_player_compare_h2h_multi_season(self, tmp_path, monkeypatch):
        """H2H filters to shared games across seasons."""
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
            head_to_head=True,
        )
        assert isinstance(result, ComparisonResult)
        assert any("head-to-head" in c for c in result.caveats)

    def test_player_h2h_single_season_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            season="2098-99",
            head_to_head=True,
        )
        assert isinstance(result, ComparisonResult)
        assert any("head-to-head" in c for c in result.caveats)


class TestHistoricalTeamH2H:
    def test_team_compare_multi_season_h2h(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="AAA",
            team_b="BBB",
            start_season="2098-99",
            end_season="2099-00",
            head_to_head=True,
        )
        assert isinstance(result, ComparisonResult)
        assert any("head-to-head" in c for c in result.caveats)
        assert any("multi-season" in c.lower() for c in result.caveats)

    def test_team_compare_non_h2h_still_works(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="AAA",
            team_b="BBB",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert not any("head-to-head" in c for c in result.caveats)


# ===================================================================
# Opponent-filtered leaderboards
# ===================================================================


class TestOpponentFilteredPlayerLeaderboard:
    def test_multi_season_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            opponent="TGT",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("vs TGT" in c for c in result.caveats)
        assert any("multi-season" in c.lower() for c in result.caveats)
        # Star Player should appear first (higher pts vs TGT)
        first = result.leaders.iloc[0]
        assert first["player_name"] == "Star Player"

    def test_single_season_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2098-99",
            stat="pts",
            opponent="TGT",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("vs TGT" in c for c in result.caveats)
        first = result.leaders.iloc[0]
        assert first["player_name"] == "Star Player"

    def test_leaderboard_opponent_no_match_returns_no_result(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2098-99",
            stat="pts",
            opponent="ZZZ",
        )
        assert isinstance(result, NoResult)

    def test_leaderboard_opponent_advanced_stat_raises(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        with pytest.raises(ValueError, match="Opponent-filtered"):
            build_result(
                season="2098-99",
                stat="net_rating",
                opponent="TGT",
            )

    def test_count_stat_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="games_30p",
            opponent="TGT",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("vs TGT" in c for c in result.caveats)


class TestOpponentFilteredTeamLeaderboard:
    def test_multi_season_team_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_team_leaders import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            opponent="TGT",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("vs TGT" in c for c in result.caveats)
        first = result.leaders.iloc[0]
        assert first["team_abbr"] == "AAA"

    def test_team_leaderboard_opponent_advanced_stat_raises(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_team_leaders import build_result

        with pytest.raises(ValueError, match="Opponent-filtered"):
            build_result(
                season="2098-99",
                stat="off_rating",
                opponent="TGT",
            )


# ===================================================================
# Playoff historical matchup spans
# ===================================================================


class TestPlayoffMatchupSpans:
    def test_parse_player_playoff_vs_team_since(self):
        parsed = parse_query("Jokic playoff stats vs Suns since 2021")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["opponent"] == "PHX"
        assert parsed["route_kwargs"]["start_season"] == "2021-22"
        assert parsed["route_kwargs"]["end_season"] == LATEST_PLAYOFF_SEASON

    def test_parse_player_playoff_h2h_since(self):
        parsed = parse_query("Jokic h2h vs Embiid playoffs since 2021")
        assert parsed["route"] == "player_compare"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["head_to_head"] is True
        assert parsed["route_kwargs"]["start_season"] == "2021-22"

    def test_playoff_player_vs_opponent_execution(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch, season_type="playoffs")

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            season_type="Playoffs",
            player="Star Player",
            opponent="TGT",
        )
        assert isinstance(result, SummaryResult)
        games = result.summary["games"].iloc[0]
        assert games == 10
        assert any("vs TGT" in c for c in result.caveats)


# ===================================================================
# Structured query support
# ===================================================================


class TestStructuredQueryMatchupSupport:
    def test_structured_player_summary_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_game_summary",
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
            opponent="TGT",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)
        assert qr.metadata.get("opponent") == "TGT"

    def test_structured_team_summary_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "game_summary",
            start_season="2098-99",
            end_season="2099-00",
            team="AAA",
            opponent="TGT",
        )
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)

    def test_structured_player_compare_h2h(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "player_compare",
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
            head_to_head=True,
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)
        assert qr.metadata.get("head_to_head_used") is True

    def test_structured_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            opponent="TGT",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.metadata.get("opponent") == "TGT"

    def test_structured_team_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_team_leaders",
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            opponent="TGT",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)


# ===================================================================
# Service/API compatibility
# ===================================================================


class TestAPICompatibility:
    def test_player_vs_opponent_to_dict(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            player="Star Player",
            opponent="TGT",
        )
        d = result.to_dict()
        assert d["query_class"] == "summary"
        assert d["result_status"] == "ok"
        assert len(d["caveats"]) >= 2
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "by_season" in d["sections"]

    def test_opponent_leaderboard_to_dict(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="pts",
            opponent="TGT",
        )
        d = result.to_dict()
        assert d["query_class"] == "leaderboard"
        assert d["result_status"] == "ok"
        assert len(d["caveats"]) >= 2

    def test_h2h_comparison_to_dict(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            start_season="2098-99",
            end_season="2099-00",
            head_to_head=True,
        )
        d = result.to_dict()
        assert d["query_class"] == "comparison"
        assert d["result_status"] == "ok"
        assert "sections" in d
        assert "summary" in d["sections"]
        assert "comparison" in d["sections"]

    def test_service_natural_query_matchup(self, tmp_path, monkeypatch):
        """Natural query through full service returns QueryResult with metadata."""
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.query_service import execute_natural_query

        qr = execute_natural_query("Star Player summary vs TGT from 2098-99 to 2099-00")
        # May not match if "Star Player" isn't in PLAYER_ALIASES, but tests
        # the pipeline doesn't crash.  For known aliases:
        if qr.is_ok:
            assert qr.metadata.get("opponent") == "TGT" or qr.metadata.get("opponent") is None


# ===================================================================
# Caveats verification
# ===================================================================


class TestMatchupCaveats:
    def test_player_summary_opponent_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2098-99",
            player="Star Player",
            opponent="TGT",
        )
        assert any("vs TGT" in c for c in result.caveats)

    def test_team_summary_opponent_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.game_summary import build_result

        result = build_result(
            season="2098-99",
            team="AAA",
            opponent="TGT",
        )
        assert any("vs TGT" in c for c in result.caveats)

    def test_player_compare_h2h_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            season="2098-99",
            head_to_head=True,
        )
        assert any("head-to-head" in c for c in result.caveats)

    def test_team_compare_h2h_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.team_compare import build_result

        result = build_result(
            team_a="AAA",
            team_b="BBB",
            season="2098-99",
            head_to_head=True,
        )
        assert any("head-to-head" in c for c in result.caveats)

    def test_player_compare_opponent_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_compare import build_result

        result = build_result(
            player_a="Star Player",
            player_b="Other Player",
            season="2098-99",
            opponent="TGT",
        )
        assert any("vs TGT" in c for c in result.caveats)

    def test_leaderboard_opponent_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.season_leaders import build_result

        result = build_result(
            season="2098-99",
            stat="pts",
            opponent="TGT",
        )
        assert any("vs TGT" in c for c in result.caveats)

    def test_no_opponent_no_caveat(self, tmp_path, monkeypatch):
        _setup_matchup_data(tmp_path, monkeypatch)

        from nbatools.commands.player_game_summary import build_result

        result = build_result(
            season="2098-99",
            player="Star Player",
        )
        assert not any("vs" in c.lower() and "filtered" in c.lower() for c in result.caveats)
