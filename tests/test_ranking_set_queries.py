"""Tests for expanded ranking/set-based query support.

Covers:
- Top-N / ranked-set support and parameterization
- Bottom-N / ascending semantics
- Rank phrasing and "best N" patterns
- Position-based subset filtering (among guards/centers/bigs/etc.)
- Historical + opponent-aware ranking
- Advanced metric ranking contexts
- Smart ascending for lower-is-better stats (def_rating, tov)
- Structured query parity (position kwarg)
- Trust/caveats for subset and filtered contexts
"""

from contextlib import redirect_stdout
from io import StringIO

import pandas as pd

from nbatools.commands.natural_query import (
    extract_position_filter,
    extract_top_n,
    parse_query,
    wants_ascending_leaderboard,
    wants_leaderboard,
    wants_team_leaderboard,
)
from nbatools.commands.season_leaders import (
    POSITION_GROUPS,
    _resolve_position_filter,
)
from nbatools.commands.season_leaders import (
    build_result as season_leaders_build_result,
)


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _write_csv(path, rows):
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


# ===========================================================================
# extract_top_n tests
# ===========================================================================


class TestExtractTopN:
    def test_top_10(self):
        assert extract_top_n("top 10 scorers") == 10

    def test_top_20(self):
        assert extract_top_n("top 20 scorers since 2020") == 20

    def test_top_5(self):
        assert extract_top_n("top 5 rebounders") == 5

    def test_no_top_n(self):
        assert extract_top_n("best scorers") is None

    def test_bottom_10(self):
        assert extract_top_n("bottom 10 turnover teams") == 10

    def test_bottom_5(self):
        assert extract_top_n("bottom 5 defensive teams") == 5

    def test_best_10(self):
        assert extract_top_n("best 10 scorers since 2021") == 10

    def test_worst_5(self):
        assert extract_top_n("worst 5 defensive teams") == 5


# ===========================================================================
# wants_ascending_leaderboard tests
# ===========================================================================


class TestWantsAscending:
    def test_lowest(self):
        assert wants_ascending_leaderboard("lowest turnover teams") is True

    def test_fewest(self):
        assert wants_ascending_leaderboard("fewest turnovers") is True

    def test_least(self):
        assert wants_ascending_leaderboard("least turnovers this season") is True

    def test_worst(self):
        assert wants_ascending_leaderboard("worst defensive rating") is True

    def test_bottom(self):
        assert wants_ascending_leaderboard("bottom 10 scorers") is True

    def test_top_not_ascending(self):
        assert wants_ascending_leaderboard("top 10 scorers") is False

    def test_best_not_ascending(self):
        assert wants_ascending_leaderboard("best scorers") is False


# ===========================================================================
# wants_leaderboard enhanced tests
# ===========================================================================


class TestWantsLeaderboard:
    def test_top_scorers(self):
        assert wants_leaderboard("top scorers this season") is True

    def test_best_efg(self):
        assert wants_leaderboard("best efg% this season") is True

    def test_lowest_turnovers(self):
        assert wants_leaderboard("lowest turnovers this season") is True

    def test_bottom_10_scorers(self):
        assert wants_leaderboard("bottom 10 scorers this season") is True

    def test_rank_players_by(self):
        assert wants_leaderboard("rank players by assists") is True

    def test_rank_by_net_rating(self):
        assert wants_leaderboard("rank by net rating") is True


# ===========================================================================
# wants_team_leaderboard enhanced tests
# ===========================================================================


class TestWantsTeamLeaderboard:
    def test_rank_teams_by_net_rating(self):
        assert wants_team_leaderboard("rank teams by net rating") is True

    def test_lowest_turnover_teams(self):
        assert wants_team_leaderboard("lowest turnover teams") is True

    def test_bottom_10_teams(self):
        assert wants_team_leaderboard("bottom 10 teams by scoring") is True

    def test_best_defensive_teams(self):
        assert wants_team_leaderboard("best defensive teams") is True

    def test_worst_offensive_teams(self):
        assert wants_team_leaderboard("worst offensive teams") is True


# ===========================================================================
# extract_position_filter tests
# ===========================================================================


class TestExtractPositionFilter:
    def test_among_guards(self):
        assert extract_position_filter("best ts% among guards this season") == "guards"

    def test_among_centers(self):
        assert extract_position_filter("top scorers among centers since 2020") == "centers"

    def test_among_big_men(self):
        assert extract_position_filter("top rebounders among big men since 2015") == "bigs"

    def test_among_bigs(self):
        assert extract_position_filter("best efg% among bigs last 3 seasons") == "bigs"

    def test_among_forwards(self):
        assert extract_position_filter("top scorers among forwards this season") == "forwards"

    def test_among_wings(self):
        assert extract_position_filter("best ts% among wings this season") == "wings"

    def test_by_guards(self):
        assert extract_position_filter("top scorers by guards") == "guards"

    def test_for_centers(self):
        assert extract_position_filter("best rebounding for centers") == "centers"

    def test_no_position(self):
        assert extract_position_filter("top scorers this season") is None

    def test_no_position_with_team(self):
        assert extract_position_filter("top scorers vs Lakers") is None


# ===========================================================================
# _resolve_position_filter tests
# ===========================================================================


class TestResolvePositionFilter:
    def test_guards(self):
        codes = _resolve_position_filter("guards")
        assert codes == {"G", "G-F"}

    def test_centers(self):
        codes = _resolve_position_filter("centers")
        assert codes == {"C", "C-F"}

    def test_bigs(self):
        codes = _resolve_position_filter("bigs")
        assert codes == {"C", "C-F", "F-C"}

    def test_forwards(self):
        codes = _resolve_position_filter("forwards")
        assert codes == {"F", "F-G", "F-C"}

    def test_wings(self):
        codes = _resolve_position_filter("wings")
        assert codes == {"F", "F-G", "G-F"}

    def test_none(self):
        assert _resolve_position_filter(None) is None

    def test_unknown(self):
        assert _resolve_position_filter("point guard") is None

    def test_position_groups_exist(self):
        assert len(POSITION_GROUPS) > 0


# ===========================================================================
# parse_query routing tests — top-N / rank / ascending
# ===========================================================================


class TestParseQueryTopN:
    def test_top_10_players_by_ast_since_2020(self):
        parsed = parse_query("top 10 players by assists since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["limit"] == 10
        assert parsed["route_kwargs"]["stat"] in ("ast", "ast_per_game")
        assert parsed["route_kwargs"]["ascending"] is False

    def test_top_20_scorers_vs_lakers_since_2018(self):
        parsed = parse_query("top 20 scorers vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["limit"] == 20
        assert parsed["route_kwargs"]["stat"] in ("pts", "pts_per_game")
        assert parsed["route_kwargs"]["opponent"] is not None

    def test_rank_teams_by_net_rating(self):
        parsed = parse_query("rank teams by net rating")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] in ("net_rating", "net")

    def test_lowest_turnover_teams_this_season(self):
        parsed = parse_query("lowest turnover teams this season")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_bottom_10_scorers(self):
        parsed = parse_query("bottom 10 scorers this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["limit"] == 10
        assert parsed["route_kwargs"]["ascending"] is True

    def test_best_efg_over_last_5_seasons(self):
        parsed = parse_query("best efg% over the last 5 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("efg_pct", "efg")
        assert parsed["route_kwargs"]["start_season"] is not None
        assert parsed["route_kwargs"]["end_season"] is not None

    def test_default_limit_is_10(self):
        parsed = parse_query("top scorers this season")
        assert parsed["route_kwargs"]["limit"] == 10

    def test_top_15_explicit(self):
        parsed = parse_query("top 15 rebounders this season")
        assert parsed["route_kwargs"]["limit"] == 15


# ===========================================================================
# parse_query routing tests — position subset filtering
# ===========================================================================


class TestParseQueryPositionFilter:
    def test_best_ts_among_centers(self):
        parsed = parse_query("best ts% among centers this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("ts_pct", "ts")
        assert parsed["route_kwargs"]["position"] == "centers"

    def test_top_scorers_among_guards_since_2021(self):
        parsed = parse_query("top scorers among guards since 2021")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("pts", "pts_per_game")
        assert parsed["route_kwargs"]["position"] == "guards"

    def test_top_rebounders_among_bigs(self):
        parsed = parse_query("top rebounders among big men since 2015")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["position"] == "bigs"

    def test_no_position_when_not_specified(self):
        parsed = parse_query("top scorers this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("position") is None


# ===========================================================================
# parse_query routing tests — historical + opponent ranking
# ===========================================================================


class TestParseQueryHistoricalOpponentRanking:
    def test_best_ast_pct_vs_lakers_since_2018(self):
        parsed = parse_query("best assist percentage vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("ast_pct", "ast")
        assert parsed["route_kwargs"]["opponent"] is not None
        assert parsed["route_kwargs"]["start_season"] is not None

    def test_most_steals_in_playoffs_since_2010(self):
        parsed = parse_query("most steals in playoffs since 2010")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("stl", "stl_per_game")
        assert parsed["route_kwargs"]["season_type"] == "Playoffs"
        assert parsed["route_kwargs"]["start_season"] is not None

    def test_best_efg_last_5_seasons(self):
        parsed = parse_query("best efg% over the last 5 seasons")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("efg_pct", "efg")
        assert parsed["route_kwargs"]["start_season"] is not None

    def test_highest_plus_minus_vs_celtics_since_2021(self):
        parsed = parse_query("highest plus minus vs Celtics since 2021")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["stat"] in ("plus_minus", "plus_minus_per_game")
        assert parsed["route_kwargs"]["opponent"] is not None
        assert parsed["route_kwargs"]["start_season"] is not None


# ===========================================================================
# parse_query — smart ascending for lower-is-better stats
# ===========================================================================


class TestSmartAscending:
    def test_best_defensive_teams_ascending(self):
        """'best defensive teams' → def_rating ascending (lower is better)."""
        parsed = parse_query("best defensive teams")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "def_rating"
        assert parsed["route_kwargs"]["ascending"] is True

    def test_worst_defensive_teams_descending(self):
        """'worst defensive teams' → def_rating descending (higher = worse)."""
        parsed = parse_query("worst defensive teams")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"]["stat"] == "def_rating"
        assert parsed["route_kwargs"]["ascending"] is False

    def test_lowest_turnovers_ascending(self):
        parsed = parse_query("lowest turnovers this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["ascending"] is True


# ===========================================================================
# build_result unit tests — position filtering
# ===========================================================================


class TestBuildResultPositionFiltering:
    def test_position_filter_restricts_players(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        game_rows = []
        # Guard player - 25 games, 20 ppg
        for gid in range(1, 26):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-10-{gid:02d}" if gid <= 28 else f"2099-11-{(gid - 28):02d}",
                    "player_id": 1,
                    "player_name": "Guard Guy",
                    "team_id": 100,
                    "team_abbr": "AAA",
                    "pts": 20,
                    "reb": 3,
                    "ast": 8,
                    "fgm": 8,
                    "fga": 16,
                    "fg3m": 2,
                    "fg3a": 5,
                    "ftm": 2,
                    "fta": 3,
                }
            )
        # Center player - 25 games, 25 ppg
        for gid in range(26, 51):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-11-{(gid - 25):02d}",
                    "player_id": 2,
                    "player_name": "Center Dude",
                    "team_id": 200,
                    "team_abbr": "BBB",
                    "pts": 25,
                    "reb": 12,
                    "ast": 2,
                    "fgm": 10,
                    "fga": 18,
                    "fg3m": 1,
                    "fg3a": 2,
                    "ftm": 4,
                    "fta": 5,
                }
            )

        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            game_rows,
        )

        # Roster data with positions
        roster_rows = [
            {
                "season": "2099-00",
                "team_id": 100,
                "team_abbr": "AAA",
                "player_id": 1,
                "player_name": "Guard Guy",
                "jersey_number": 1,
                "position": "G",
                "height": "6-3",
                "weight": 190,
                "birth_date": "1995-01-01",
                "experience_years": 5,
                "school": "U1",
                "stint": 1,
            },
            {
                "season": "2099-00",
                "team_id": 200,
                "team_abbr": "BBB",
                "player_id": 2,
                "player_name": "Center Dude",
                "jersey_number": 5,
                "position": "C",
                "height": "7-0",
                "weight": 260,
                "birth_date": "1996-01-01",
                "experience_years": 4,
                "school": "U2",
                "stint": 1,
            },
        ]
        _write_csv(tmp_path / "data/raw/rosters/2099-00.csv", roster_rows)

        # Without position filter — both players appear
        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
        )
        assert len(result.leaders) == 2

        # Filter to guards only
        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            position="guards",
        )
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["player_name"] == "Guard Guy"
        assert any("position group" in c for c in result.caveats)

        # Filter to centers only
        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            position="centers",
        )
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["player_name"] == "Center Dude"

    def test_position_filter_no_match_returns_no_result(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        game_rows = []
        for gid in range(1, 26):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-10-{gid:02d}",
                    "player_id": 1,
                    "player_name": "Guard Guy",
                    "team_id": 100,
                    "team_abbr": "AAA",
                    "pts": 20,
                    "reb": 3,
                    "ast": 8,
                    "fgm": 8,
                    "fga": 16,
                    "fg3m": 2,
                    "fg3a": 5,
                    "ftm": 2,
                    "fta": 3,
                }
            )

        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            game_rows,
        )

        roster_rows = [
            {
                "season": "2099-00",
                "team_id": 100,
                "team_abbr": "AAA",
                "player_id": 1,
                "player_name": "Guard Guy",
                "jersey_number": 1,
                "position": "G",
                "height": "6-3",
                "weight": 190,
                "birth_date": "1995-01-01",
                "experience_years": 5,
                "school": "U1",
                "stint": 1,
            },
        ]
        _write_csv(tmp_path / "data/raw/rosters/2099-00.csv", roster_rows)

        # Filter to centers when only guards exist
        from nbatools.commands.structured_results import NoResult

        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            position="centers",
        )
        assert isinstance(result, NoResult)

    def test_position_filter_with_opponent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        game_rows = []
        for gid in range(1, 26):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-10-{gid:02d}",
                    "player_id": 1,
                    "player_name": "Guard Guy",
                    "team_id": 100,
                    "team_abbr": "AAA",
                    "opponent_team_abbr": "LAL",
                    "pts": 20,
                    "reb": 3,
                    "ast": 8,
                    "fgm": 8,
                    "fga": 16,
                    "fg3m": 2,
                    "fg3a": 5,
                    "ftm": 2,
                    "fta": 3,
                }
            )
        for gid in range(26, 51):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-11-{(gid - 25):02d}",
                    "player_id": 2,
                    "player_name": "Center Dude",
                    "team_id": 200,
                    "team_abbr": "BBB",
                    "opponent_team_abbr": "LAL",
                    "pts": 25,
                    "reb": 12,
                    "ast": 2,
                    "fgm": 10,
                    "fga": 18,
                    "fg3m": 1,
                    "fg3a": 2,
                    "ftm": 4,
                    "fta": 5,
                }
            )

        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            game_rows,
        )

        roster_rows = [
            {
                "season": "2099-00",
                "team_id": 100,
                "team_abbr": "AAA",
                "player_id": 1,
                "player_name": "Guard Guy",
                "jersey_number": 1,
                "position": "G",
                "height": "6-3",
                "weight": 190,
                "birth_date": "1995-01-01",
                "experience_years": 5,
                "school": "U1",
                "stint": 1,
            },
            {
                "season": "2099-00",
                "team_id": 200,
                "team_abbr": "BBB",
                "player_id": 2,
                "player_name": "Center Dude",
                "jersey_number": 5,
                "position": "C",
                "height": "7-0",
                "weight": 260,
                "birth_date": "1996-01-01",
                "experience_years": 4,
                "school": "U2",
                "stint": 1,
            },
        ]
        _write_csv(tmp_path / "data/raw/rosters/2099-00.csv", roster_rows)

        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            opponent="LAL",
            position="guards",
        )
        assert len(result.leaders) == 1
        assert result.leaders.iloc[0]["player_name"] == "Guard Guy"
        assert any("position group" in c for c in result.caveats)
        assert any("vs LAL" in c for c in result.caveats)


# ===========================================================================
# build_result unit tests — ascending sort semantics
# ===========================================================================


class TestBuildResultAscending:
    def test_ascending_sort_returns_lowest_first(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        game_rows = []
        for gid in range(1, 26):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-10-{gid:02d}",
                    "player_id": 1,
                    "player_name": "High Scorer",
                    "team_id": 100,
                    "team_abbr": "AAA",
                    "pts": 30,
                    "reb": 5,
                    "ast": 5,
                    "fgm": 12,
                    "fga": 22,
                    "fg3m": 2,
                    "fg3a": 5,
                    "ftm": 4,
                    "fta": 5,
                }
            )
        for gid in range(26, 51):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-11-{(gid - 25):02d}",
                    "player_id": 2,
                    "player_name": "Low Scorer",
                    "team_id": 200,
                    "team_abbr": "BBB",
                    "pts": 5,
                    "reb": 2,
                    "ast": 1,
                    "fgm": 2,
                    "fga": 8,
                    "fg3m": 0,
                    "fg3a": 2,
                    "ftm": 1,
                    "fta": 2,
                }
            )

        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            game_rows,
        )

        result = season_leaders_build_result(
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            ascending=True,
        )
        assert result.leaders.iloc[0]["player_name"] == "Low Scorer"
        assert result.leaders.iloc[-1]["player_name"] == "High Scorer"


# ===========================================================================
# Service layer (query_service) tests
# ===========================================================================


class TestQueryServiceRanking:
    def test_structured_query_with_position(self, tmp_path, monkeypatch):
        """execute_structured_query passes position to season_leaders."""
        monkeypatch.chdir(tmp_path)

        game_rows = []
        for gid in range(1, 26):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-10-{gid:02d}",
                    "player_id": 1,
                    "player_name": "Guard Guy",
                    "team_id": 100,
                    "team_abbr": "AAA",
                    "pts": 20,
                    "reb": 3,
                    "ast": 8,
                    "fgm": 8,
                    "fga": 16,
                    "fg3m": 2,
                    "fg3a": 5,
                    "ftm": 2,
                    "fta": 3,
                }
            )
        for gid in range(26, 51):
            game_rows.append(
                {
                    "game_id": gid,
                    "game_date": f"2099-11-{(gid - 25):02d}",
                    "player_id": 2,
                    "player_name": "Center Dude",
                    "team_id": 200,
                    "team_abbr": "BBB",
                    "pts": 25,
                    "reb": 12,
                    "ast": 2,
                    "fgm": 10,
                    "fga": 18,
                    "fg3m": 1,
                    "fg3a": 2,
                    "ftm": 4,
                    "fta": 5,
                }
            )

        _write_csv(
            tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv",
            game_rows,
        )

        roster_rows = [
            {
                "season": "2099-00",
                "team_id": 100,
                "team_abbr": "AAA",
                "player_id": 1,
                "player_name": "Guard Guy",
                "jersey_number": 1,
                "position": "G",
                "height": "6-3",
                "weight": 190,
                "birth_date": "1995-01-01",
                "experience_years": 5,
                "school": "U1",
                "stint": 1,
            },
            {
                "season": "2099-00",
                "team_id": 200,
                "team_abbr": "BBB",
                "player_id": 2,
                "player_name": "Center Dude",
                "jersey_number": 5,
                "position": "C",
                "height": "7-0",
                "weight": 260,
                "birth_date": "1996-01-01",
                "experience_years": 4,
                "school": "U2",
                "stint": 1,
            },
        ]
        _write_csv(tmp_path / "data/raw/rosters/2099-00.csv", roster_rows)

        from nbatools.query_service import execute_structured_query

        qr = execute_structured_query(
            "season_leaders",
            season="2099-00",
            stat="pts",
            limit=10,
            min_games=1,
            position="guards",
        )
        assert qr.is_ok
        assert len(qr.result.leaders) == 1
        assert qr.result.leaders.iloc[0]["player_name"] == "Guard Guy"
        assert qr.metadata.get("position_filter") == "guards"

    def test_natural_query_with_position(self):
        """Natural query with position routes correctly."""
        parsed = parse_query("top scorers among guards this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"]["position"] == "guards"

    def test_natural_query_position_in_metadata(self):
        """Position filter appears in metadata."""
        parsed = parse_query("best ts% among centers this season")
        assert parsed.get("position_filter") == "centers"
