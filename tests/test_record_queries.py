"""Tests for record-oriented and matchup-history queries.

Covers:
1. Historical team record queries (single team, multi-season, home/away, playoff)
2. Historical team-vs-team matchup record queries
3. Record leaderboard / ranking queries
4. Contextual sample record queries (record when scoring 120+, etc.)
5. Player record routing (confirm player queries still route to existing routes)
6. Natural query parsing (record intent detection)
7. Structured query parity (team_record, team_matchup_record, team_record_leaderboard)
8. Service/API compatibility
9. Trust/status/caveats for record queries
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._seasons import (
    LATEST_REGULAR_SEASON,
)
from nbatools.commands.natural_query import (
    detect_record_intent,
    parse_query,
)
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)
from nbatools.commands.team_record import (
    build_matchup_record_result,
    build_record_leaderboard_result,
    build_team_record_result,
)

pytestmark = pytest.mark.engine

# ===================================================================
# Helpers
# ===================================================================


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _team_game_rows(
    season,
    team_name,
    team_abbr,
    team_id,
    n_games,
    avg_pts,
    *,
    opponent_name="Other Team",
    opponent_abbr="OTH",
    opponent_id=99,
    wl_pattern=None,
    home_away_pattern=None,
    season_type="Regular Season",
    fg3m=10,
    tov=12,
):
    """Generate fake team game log rows."""
    rows = []
    for i in range(n_games):
        if wl_pattern is not None:
            wl = wl_pattern[i % len(wl_pattern)]
        else:
            wl = "W" if i % 2 == 0 else "L"

        if home_away_pattern is not None:
            is_home = home_away_pattern[i % len(home_away_pattern)]
        else:
            is_home = 1 if i % 2 == 0 else 0

        rows.append(
            {
                "game_id": f"{season}_{team_id}_{opponent_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": season,
                "season_type": season_type,
                "team_id": team_id,
                "team_name": team_name,
                "team_abbr": team_abbr,
                "opponent_team_id": opponent_id,
                "opponent_team_name": opponent_name,
                "opponent_team_abbr": opponent_abbr,
                "is_home": is_home,
                "is_away": 1 - is_home,
                "wl": wl,
                "pts": avg_pts + (i % 5),
                "reb": 40,
                "ast": 25,
                "stl": 8,
                "blk": 5,
                "fgm": 35,
                "fga": 80,
                "fg3m": fg3m,
                "fg3a": 30,
                "ftm": 15,
                "fta": 20,
                "tov": tov,
                "pf": 18,
                "minutes": 240,
                "plus_minus": 5 if wl == "W" else -5,
                "oreb": 10,
                "dreb": 30,
                "efg_pct": 0.55,
                "ts_pct": 0.60,
            }
        )
    return rows


def _write_single_season(tmp_path, safe="regular_season"):
    """Write one season of data with two teams."""
    rows = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 110, wl_pattern=["W", "W", "L"])
    rows += _team_game_rows("2098-99", "Team Beta", "BET", 2, 20, 100, wl_pattern=["W", "L", "L"])
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", rows)


def _write_multi_season(tmp_path, safe="regular_season"):
    """Write two seasons of data with three teams."""
    rows1 = _team_game_rows("2098-99", "Team Alpha", "ALP", 1, 20, 110, wl_pattern=["W", "W", "L"])
    rows1 += _team_game_rows("2098-99", "Team Beta", "BET", 2, 20, 100, wl_pattern=["W", "L", "L"])
    rows1 += _team_game_rows(
        "2098-99", "Team Gamma", "GAM", 3, 20, 105, wl_pattern=["W", "W", "W", "L"]
    )
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", rows1)

    rows2 = _team_game_rows("2099-00", "Team Alpha", "ALP", 1, 20, 115, wl_pattern=["W", "W", "L"])
    rows2 += _team_game_rows("2099-00", "Team Beta", "BET", 2, 20, 105, wl_pattern=["W", "L", "L"])
    rows2 += _team_game_rows(
        "2099-00", "Team Gamma", "GAM", 3, 20, 108, wl_pattern=["W", "W", "W", "L"]
    )
    _write_csv(tmp_path / f"data/raw/team_game_stats/2099-00_{safe}.csv", rows2)


def _write_matchup_data(tmp_path, safe="regular_season"):
    """Write data where Team Alpha and Team Beta play each other."""
    rows_alpha = _team_game_rows(
        "2098-99",
        "Team Alpha",
        "ALP",
        1,
        10,
        110,
        opponent_name="Team Beta",
        opponent_abbr="BET",
        opponent_id=2,
        wl_pattern=["W", "W", "W", "L"],
    )
    rows_beta = _team_game_rows(
        "2098-99",
        "Team Beta",
        "BET",
        2,
        10,
        100,
        opponent_name="Team Alpha",
        opponent_abbr="ALP",
        opponent_id=1,
        wl_pattern=["L", "L", "L", "W"],
    )
    # Align game_ids
    for i, (ra, rb) in enumerate(zip(rows_alpha, rows_beta)):
        shared_id = f"2098-99_h2h_{i}"
        ra["game_id"] = shared_id
        rb["game_id"] = shared_id

    # Also add some non-matchup games
    rows_alpha_other = _team_game_rows(
        "2098-99", "Team Alpha", "ALP", 1, 5, 108, wl_pattern=["W", "L"]
    )
    rows_beta_other = _team_game_rows(
        "2098-99", "Team Beta", "BET", 2, 5, 95, wl_pattern=["L", "W"]
    )

    all_rows = rows_alpha + rows_beta + rows_alpha_other + rows_beta_other
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", all_rows)


def _write_matchup_multi_season(tmp_path, safe="regular_season"):
    """Write matchup data across two seasons."""
    # Season 1
    rows_a1 = _team_game_rows(
        "2098-99",
        "Team Alpha",
        "ALP",
        1,
        5,
        110,
        opponent_name="Team Beta",
        opponent_abbr="BET",
        opponent_id=2,
        wl_pattern=["W", "W", "L"],
    )
    rows_b1 = _team_game_rows(
        "2098-99",
        "Team Beta",
        "BET",
        2,
        5,
        100,
        opponent_name="Team Alpha",
        opponent_abbr="ALP",
        opponent_id=1,
        wl_pattern=["L", "L", "W"],
    )
    for i, (ra, rb) in enumerate(zip(rows_a1, rows_b1)):
        shared_id = f"2098-99_h2h_{i}"
        ra["game_id"] = shared_id
        rb["game_id"] = shared_id

    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", rows_a1 + rows_b1)

    # Season 2
    rows_a2 = _team_game_rows(
        "2099-00",
        "Team Alpha",
        "ALP",
        1,
        5,
        115,
        opponent_name="Team Beta",
        opponent_abbr="BET",
        opponent_id=2,
        wl_pattern=["W", "W", "W", "L"],
    )
    rows_b2 = _team_game_rows(
        "2099-00",
        "Team Beta",
        "BET",
        2,
        5,
        105,
        opponent_name="Team Alpha",
        opponent_abbr="ALP",
        opponent_id=1,
        wl_pattern=["L", "L", "L", "W"],
    )
    for i, (ra, rb) in enumerate(zip(rows_a2, rows_b2)):
        shared_id = f"2099-00_h2h_{i}"
        ra["game_id"] = shared_id
        rb["game_id"] = shared_id

    _write_csv(tmp_path / f"data/raw/team_game_stats/2099-00_{safe}.csv", rows_a2 + rows_b2)


def _write_contextual_data(tmp_path, safe="regular_season"):
    """Write data with varying scores for contextual sample queries."""
    rows = []
    for i in range(20):
        pts = 120 + i if i < 8 else 100 + i  # 8 games with 120+
        wl = "W" if pts >= 120 else ("W" if i % 3 == 0 else "L")
        opp_abbr = "BET" if i < 10 else "OTH"
        opp_name = "Team Beta" if i < 10 else "Other Team"
        opp_id = 2 if i < 10 else 99
        rows.append(
            {
                "game_id": f"2098-99_1_{opp_id}_{i}",
                "game_date": f"2099-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "season": "2098-99",
                "season_type": "Regular Season",
                "team_id": 1,
                "team_name": "Team Alpha",
                "team_abbr": "ALP",
                "opponent_team_id": opp_id,
                "opponent_team_name": opp_name,
                "opponent_team_abbr": opp_abbr,
                "is_home": 1 if i % 2 == 0 else 0,
                "is_away": 0 if i % 2 == 0 else 1,
                "wl": wl,
                "pts": pts,
                "reb": 40,
                "ast": 25,
                "stl": 8,
                "blk": 5,
                "fgm": 35,
                "fga": 80,
                "fg3m": 15 if pts >= 120 else 8,
                "fg3a": 30,
                "ftm": 15,
                "fta": 20,
                "tov": 12,
                "pf": 18,
                "minutes": 240,
                "plus_minus": 5 if wl == "W" else -5,
                "oreb": 10,
                "dreb": 30,
                "efg_pct": 0.55,
                "ts_pct": 0.60,
            }
        )
    _write_csv(tmp_path / f"data/raw/team_game_stats/2098-99_{safe}.csv", rows)


# ===================================================================
# 1. detect_record_intent unit tests
# ===================================================================


class TestDetectRecordIntent:
    def test_best_record(self):
        assert detect_record_intent("best record since 2015") is True

    def test_worst_record(self):
        assert detect_record_intent("worst record since 2020") is True

    def test_most_wins(self):
        assert detect_record_intent("most wins since 2010") is True

    def test_most_home_wins(self):
        assert detect_record_intent("most home wins over the last 10 seasons") is True

    def test_most_away_wins(self):
        assert detect_record_intent("most away wins since 2015") is True

    def test_most_losses(self):
        assert detect_record_intent("most losses since 2020") is True

    def test_fewest_losses(self):
        assert detect_record_intent("fewest losses since 2020") is True

    def test_winning_percentage(self):
        assert detect_record_intent("highest winning percentage since 2018") is True

    def test_home_record(self):
        assert detect_record_intent("home record since 2020") is True

    def test_away_record(self):
        assert detect_record_intent("away record since 2020") is True

    def test_playoff_record(self):
        assert detect_record_intent("playoff record since 2015") is True

    def test_all_time_record(self):
        assert detect_record_intent("all-time record") is True

    def test_matchup_record(self):
        assert detect_record_intent("matchup record since 2020") is True

    def test_best_playoff_record(self):
        assert detect_record_intent("best playoff record since 2015") is True

    def test_best_home_record(self):
        assert detect_record_intent("best home record over the last 5 seasons") is True

    def test_worst_away_record(self):
        assert detect_record_intent("worst away record since 2020") is True

    def test_no_record_intent_on_stats(self):
        assert detect_record_intent("best offense since 2020") is False

    def test_no_record_intent_on_scoring(self):
        assert detect_record_intent("best scoring teams this season") is False

    def test_no_record_intent_on_averages(self):
        assert detect_record_intent("Celtics averages since 2020") is False


# ===================================================================
# 2. Natural query parsing — record routing
# ===================================================================


class TestParseRecordSingleTeam:
    def test_team_record_since(self):
        parsed = parse_query("Celtics record since 2020")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2020-21"
        assert parsed["route_kwargs"]["end_season"] == LATEST_REGULAR_SEASON

    def test_team_playoff_record_since(self):
        parsed = parse_query("Lakers playoff record since 2015")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "LAL"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] == "2015-16"

    def test_team_home_record(self):
        parsed = parse_query("Celtics home record since 2022")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["home_only"] is True
        assert parsed["route_kwargs"]["away_only"] is False

    def test_team_away_record(self):
        parsed = parse_query("Nets away record since 2020")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["away_only"] is True
        assert parsed["route_kwargs"]["home_only"] is False

    def test_team_record_vs_opponent(self):
        parsed = parse_query("Celtics record vs Bucks since 2020")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "BOS"
        assert parsed["route_kwargs"]["opponent"] == "MIL"

    def test_team_playoff_record_vs_opponent(self):
        parsed = parse_query("Knicks playoff record vs Heat since 1999")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "NYK"
        assert parsed["route_kwargs"]["opponent"] == "MIA"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"


class TestParseRecordMatchup:
    def test_team_vs_team_record(self):
        parsed = parse_query("Lakers vs Celtics all-time record")
        assert parsed["route"] == "team_matchup_record"
        assert parsed["route_kwargs"]["team_a"] == "LAL"
        assert parsed["route_kwargs"]["team_b"] == "BOS"

    def test_team_vs_team_record_since(self):
        parsed = parse_query("Lakers vs Celtics record since 2010")
        assert parsed["route"] == "team_matchup_record"
        assert parsed["route_kwargs"]["team_a"] == "LAL"
        assert parsed["route_kwargs"]["team_b"] == "BOS"
        assert parsed["route_kwargs"]["start_season"] == "2010-11"

    def test_team_vs_team_home_record(self):
        parsed = parse_query("Warriors home record vs Nuggets since 2018")
        # This routes to team_record with opponent filter (single team + opponent)
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "GSW"
        assert parsed["route_kwargs"]["opponent"] == "DEN"
        assert parsed["route_kwargs"]["home_only"] is True

    def test_team_vs_team_playoff_record(self):
        parsed = parse_query("Celtics vs Heat playoff record since 2020")
        # Playoff matchup queries now route to the dedicated playoff_matchup_history route
        assert parsed["route"] == "playoff_matchup_history"


class TestParseRecordLeaderboard:
    def test_best_record_since(self):
        parsed = parse_query("best record since 2015")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["start_season"] == "2015-16"
        assert parsed["route_kwargs"]["stat"] == "win_pct"

    def test_most_wins_since(self):
        parsed = parse_query("most wins since 2010")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["stat"] == "wins"

    def test_best_playoff_record_since(self):
        parsed = parse_query("teams with the best playoff record since 2010")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    def test_most_home_wins(self):
        parsed = parse_query("most home wins over the last 10 seasons")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["home_only"] is True
        assert parsed["route_kwargs"]["stat"] == "wins"

    def test_highest_winning_percentage(self):
        parsed = parse_query("highest winning percentage since 2018")
        assert parsed["route"] == "team_record_leaderboard"

    def test_worst_away_record(self):
        parsed = parse_query("worst away record since 2020")
        assert parsed["route"] == "team_record_leaderboard"
        assert parsed["route_kwargs"]["away_only"] is True
        assert parsed["route_kwargs"]["ascending"] is True


class TestParseRecordContextual:
    @pytest.mark.xfail(reason="contextual 'when scoring 120+' parsing not yet supported")
    def test_record_when_scoring_threshold(self):
        parsed = parse_query("Celtics record when scoring 120+ since 2022")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"]["team"] == "BOS"
        # Threshold should be captured as stat/min_value
        assert parsed["route_kwargs"]["stat"] == "pts"
        assert parsed["route_kwargs"]["min_value"] is not None


class TestParsePlayerRecordRouting:
    """Verify player record queries still route to existing routes."""

    def test_player_record_routes_to_summary(self):
        parsed = parse_query("Jokic record 2024-25")
        assert parsed["route"] == "player_game_summary"

    def test_player_record_vs_team(self):
        parsed = parse_query("LeBron record vs Celtics since 2010")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["opponent"] == "BOS"

    def test_player_record_playoffs(self):
        parsed = parse_query("LeBron playoff record vs Celtics since 2010")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"


class TestParseNoRegressions:
    """Verify that non-record queries are unaffected."""

    def test_team_averages_still_route_to_summary(self):
        parsed = parse_query("Celtics averages since 2020")
        assert parsed["route"] == "game_summary"

    def test_team_summary_still_works(self):
        parsed = parse_query("Celtics summary since 2020")
        assert parsed["route"] == "game_summary"

    def test_stat_leaderboard_unaffected(self):
        parsed = parse_query("best offense since 2020")
        assert parsed["route"] == "season_team_leaders"

    def test_player_summary_unaffected(self):
        parsed = parse_query("Jokic summary 2024-25")
        assert parsed["route"] == "player_game_summary"

    def test_player_leaderboard_unaffected(self):
        parsed = parse_query("top 5 scorers 2024-25")
        assert parsed["route"] == "season_leaders"

    def test_team_compare_without_record_unaffected(self):
        parsed = parse_query("Lakers vs Celtics since 2020")
        assert parsed["route"] == "team_compare"


# ===================================================================
# 3. build_team_record_result — execution tests
# ===================================================================


class TestBuildTeamRecordResult:
    def test_basic_record(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99")
        assert isinstance(result, SummaryResult)
        s = result.summary
        assert len(s) == 1
        assert s.iloc[0]["wins"] > 0
        assert s.iloc[0]["losses"] > 0
        assert s.iloc[0]["win_pct"] is not None
        assert s.iloc[0]["games"] == 20

    def test_record_has_by_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_team_record_result(team="ALP", start_season="2098-99", end_season="2099-00")
        assert isinstance(result, SummaryResult)
        assert result.by_season is not None
        assert len(result.by_season) == 2

    def test_record_has_caveats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_team_record_result(team="ALP", start_season="2098-99", end_season="2099-00")
        assert any("multi-season" in c for c in result.caveats)

    def test_record_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99", home_only=True)
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] < 20
        assert any("home" in c for c in result.caveats)

    def test_record_away_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99", away_only=True)
        assert isinstance(result, SummaryResult)
        assert any("away" in c for c in result.caveats)

    def test_record_vs_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99", opponent="BET")
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] == 10
        assert any("vs" in c.lower() for c in result.caveats)

    def test_record_with_stat_threshold(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_contextual_data(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99", stat="pts", min_value=120)
        assert isinstance(result, SummaryResult)
        assert result.summary.iloc[0]["games"] == 8
        assert any("pts" in c for c in result.caveats)

    def test_record_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = build_team_record_result(team="ALP", season="2098-99")
        assert isinstance(result, NoResult)

    def test_record_no_matching_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="XYZ", season="2098-99")
        assert isinstance(result, NoResult)

    def test_record_playoff_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            10,
            110,
            season_type="Playoffs",
            wl_pattern=["W", "W", "W", "L"],
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_playoffs.csv", rows)

        result = build_team_record_result(team="ALP", season="2098-99", season_type="Playoffs")
        assert isinstance(result, SummaryResult)
        # 10 games, pattern [W,W,W,L] -> 8W 2L (approximately)
        assert result.summary.iloc[0]["wins"] > result.summary.iloc[0]["losses"]

    def test_record_result_status(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99")
        assert result.result_status == "ok"

    def test_record_current_through(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99")
        # current_through may be None for future seasons, but should not error
        assert isinstance(result, SummaryResult)

    def test_record_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99")
        d = result.to_dict()
        assert "sections" in d
        assert "summary" in d["sections"]


# ===================================================================
# 4. build_matchup_record_result — execution tests
# ===================================================================


class TestBuildMatchupRecordResult:
    def test_basic_matchup(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        assert isinstance(result, ComparisonResult)
        assert len(result.summary) == 2
        # Team Alpha has more wins vs Beta (pattern [W,W,W,L])
        alp_row = result.summary[result.summary["team_name"] == "Team Alpha"]
        bet_row = result.summary[result.summary["team_name"] == "Team Beta"]
        assert int(alp_row.iloc[0]["wins"]) > int(bet_row.iloc[0]["wins"])

    def test_matchup_comparison_df(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        assert isinstance(result, ComparisonResult)
        comp = result.comparison
        assert "metric" in comp.columns
        metrics = set(comp["metric"].tolist())
        assert "wins" in metrics
        assert "losses" in metrics
        assert "win_pct" in metrics

    def test_matchup_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_multi_season(tmp_path)

        result = build_matchup_record_result(
            team_a="ALP",
            team_b="BET",
            start_season="2098-99",
            end_season="2099-00",
        )
        assert isinstance(result, ComparisonResult)
        assert any("multi-season" in c for c in result.caveats)

    def test_matchup_caveats(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        assert any("matchup record" in c.lower() for c in result.caveats)

    def test_matchup_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(
            team_a="ALP",
            team_b="BET",
            season="2098-99",
            home_only=True,
        )
        assert isinstance(result, ComparisonResult)
        # Home games for ALP only — fewer games
        assert result.summary.iloc[0]["games"] <= 10

    def test_matchup_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        assert isinstance(result, NoResult)

    def test_matchup_no_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        # ALP vs BET never play each other in single_season data
        result = build_matchup_record_result(team_a="ALP", team_b="XYZ", season="2098-99")
        assert isinstance(result, (ComparisonResult, NoResult))

    def test_matchup_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        d = result.to_dict()
        assert "sections" in d

    def test_matchup_result_status(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        assert result.result_status == "ok"


# ===================================================================
# 5. build_record_leaderboard_result — execution tests
# ===================================================================


class TestBuildRecordLeaderboardResult:
    def test_basic_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        assert isinstance(result, LeaderboardResult)
        leaders = result.leaders
        assert len(leaders) == 3  # Three teams
        assert "rank" in leaders.columns
        assert "wins" in leaders.columns
        assert "losses" in leaders.columns
        assert "win_pct" in leaders.columns

    def test_leaderboard_ordered_by_win_pct(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        leaders = result.leaders
        pcts = leaders["win_pct"].tolist()
        assert pcts == sorted(pcts, reverse=True)

    def test_leaderboard_ordered_by_wins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="wins"
        )
        leaders = result.leaders
        wins = leaders["wins"].tolist()
        assert wins == sorted(wins, reverse=True)

    def test_leaderboard_ascending(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
            ascending=True,
        )
        leaders = result.leaders
        pcts = leaders["win_pct"].tolist()
        assert pcts == sorted(pcts)

    def test_leaderboard_limit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
            limit=2,
        )
        assert len(result.leaders) == 2

    def test_leaderboard_home_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
            home_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("home" in c for c in result.caveats)

    def test_leaderboard_away_only(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
            away_only=True,
        )
        assert isinstance(result, LeaderboardResult)
        assert any("away" in c for c in result.caveats)

    def test_leaderboard_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
            opponent="ALP",
        )
        assert isinstance(result, LeaderboardResult)
        assert any("vs" in c.lower() for c in result.caveats)

    def test_leaderboard_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = build_record_leaderboard_result(season="2098-99", stat="win_pct")
        assert isinstance(result, NoResult)

    def test_leaderboard_caveats_multi_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        assert any("multi-season" in c for c in result.caveats)

    def test_leaderboard_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        d = result.to_dict()
        assert "sections" in d

    def test_leaderboard_result_status(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        assert result.result_status == "ok"

    def test_leaderboard_single_season(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_record_leaderboard_result(season="2098-99", stat="win_pct")
        assert isinstance(result, LeaderboardResult)
        assert len(result.leaders) == 2

    def test_leaderboard_playoff(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rows = _team_game_rows(
            "2098-99",
            "Team Alpha",
            "ALP",
            1,
            10,
            110,
            season_type="Playoffs",
            wl_pattern=["W", "W", "W", "L"],
        )
        rows += _team_game_rows(
            "2098-99",
            "Team Beta",
            "BET",
            2,
            10,
            100,
            season_type="Playoffs",
            wl_pattern=["W", "L", "L", "L"],
        )
        _write_csv(tmp_path / "data/raw/team_game_stats/2098-99_playoffs.csv", rows)

        result = build_record_leaderboard_result(
            season="2098-99", stat="win_pct", season_type="Playoffs"
        )
        assert isinstance(result, LeaderboardResult)
        # ALP should be ranked first
        assert result.leaders.iloc[0]["team_abbr"] == "ALP"


# ===================================================================
# 6. Structured query parity
# ===================================================================


class TestStructuredQueryParity:
    def test_team_record_in_valid_routes(self):
        from nbatools.query_service import VALID_ROUTES

        assert "team_record" in VALID_ROUTES
        assert "team_matchup_record" in VALID_ROUTES
        assert "team_record_leaderboard" in VALID_ROUTES

    def test_execute_structured_team_record(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query("team_record", team="ALP", season="2098-99")
        assert qr.is_ok
        assert isinstance(qr.result, SummaryResult)
        assert qr.route == "team_record"

    def test_execute_structured_matchup_record(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "team_matchup_record", team_a="ALP", team_b="BET", season="2098-99"
        )
        assert qr.is_ok
        assert isinstance(qr.result, ComparisonResult)

    def test_execute_structured_record_leaderboard(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "team_record_leaderboard",
            start_season="2098-99",
            end_season="2099-00",
            stat="win_pct",
        )
        assert qr.is_ok
        assert isinstance(qr.result, LeaderboardResult)

    def test_structured_query_no_data(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query("team_record", team="ALP", season="2098-99")
        assert not qr.is_ok
        assert isinstance(qr.result, NoResult)


# ===================================================================
# 7. Service / API compatibility
# ===================================================================


class TestServiceAPICompatibility:
    def test_natural_query_returns_query_result(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        from nbatools.query_service import QueryResult, execute_natural_query

        # Use a team record query that would fail to match real data
        # but should still return QueryResult
        qr = execute_natural_query("Team Alpha record 2098-99")
        assert isinstance(qr, QueryResult)

    def test_natural_query_team_record_metadata(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        from nbatools.query_service import execute_natural_query

        # This might not match because "Team Alpha" isn't in TEAM_ALIASES,
        # so test with BOS which is.
        # We can't test with real alias since data doesn't have BOS.
        # Instead test that query does not crash.
        qr = execute_natural_query("best record 2098-99")
        assert qr is not None
        assert qr.metadata.get("route") == "team_record_leaderboard"

    def test_query_result_to_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query("team_record", team="ALP", season="2098-99")
        d = qr.to_dict()
        assert isinstance(d, dict)

    def test_route_to_query_class_mapping(self):
        from nbatools.commands.format_output import route_to_query_class

        assert route_to_query_class("team_record") == "summary"
        assert route_to_query_class("team_matchup_record") == "comparison"
        assert route_to_query_class("team_record_leaderboard") == "leaderboard"


# ===================================================================
# 8. Error / edge case handling
# ===================================================================


class TestRecordEdgeCases:
    def test_home_and_away_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        with pytest.raises(ValueError, match="home_only.*away_only"):
            build_team_record_result(team="ALP", season="2098-99", home_only=True, away_only=True)

    def test_matchup_home_and_away_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        with pytest.raises(ValueError, match="home_only.*away_only"):
            build_matchup_record_result(
                team_a="ALP",
                team_b="BET",
                season="2098-99",
                home_only=True,
                away_only=True,
            )

    def test_leaderboard_invalid_limit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        with pytest.raises(ValueError, match="limit"):
            build_record_leaderboard_result(season="2098-99", stat="win_pct", limit=0)

    def test_leaderboard_home_and_away_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        with pytest.raises(ValueError, match="home_only.*away_only"):
            build_record_leaderboard_result(
                season="2098-99", stat="win_pct", home_only=True, away_only=True
            )


# ===================================================================
# 9. Record result serialization
# ===================================================================


class TestRecordResultSerialization:
    def test_record_to_labeled_text(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_single_season(tmp_path)

        result = build_team_record_result(team="ALP", season="2098-99")
        text = result.to_labeled_text()
        assert "SUMMARY" in text
        assert "wins" in text.lower() or "win" in text.lower()

    def test_matchup_to_labeled_text(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_matchup_data(tmp_path)

        result = build_matchup_record_result(team_a="ALP", team_b="BET", season="2098-99")
        text = result.to_labeled_text()
        assert "SUMMARY" in text
        assert "COMPARISON" in text

    def test_leaderboard_to_labeled_text(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_multi_season(tmp_path)

        result = build_record_leaderboard_result(
            start_season="2098-99", end_season="2099-00", stat="win_pct"
        )
        text = result.to_labeled_text()
        assert "LEADERBOARD" in text
        assert "win_pct" in text.lower()
