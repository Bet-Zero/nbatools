"""Tests for explicit query-intent detection and routing.

Verifies that the engine correctly distinguishes:
- list/finder intent
- count intent
- summary intent
- leaderboard intent
- intent + historical spans (since, career, last N seasons)
- intent + opponent filters
- intent + season type (playoffs)

Tests cover:
1. Intent detection functions (wants_finder, wants_count, wants_summary, wants_leaderboard)
2. Parse state extraction (finder_intent, count_intent in parsed dict)
3. Route selection (explicit intent overrides defaults)
4. Count result semantics (CountResult with correct count)
5. Service/API compatibility (QueryResult envelope)
"""

import pytest

from nbatools.commands.natural_query import (
    _build_parse_state,
    parse_query,
    wants_count,
    wants_finder,
    wants_leaderboard,
    wants_summary,
    wants_team_leaderboard,
)
from nbatools.commands.structured_results import (
    CountResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)
from nbatools.query_service import (
    QueryResult,
    execute_natural_query,
)

pytestmark = pytest.mark.query

# ===================================================================
# Intent Detection Functions
# ===================================================================


class TestWantsFinder:
    """Test the wants_finder() detection function."""

    def test_show_me(self):
        assert wants_finder("show me jokic games with 30 points")

    def test_list(self):
        assert wants_finder("list celtics games vs bucks since 2021")

    def test_find(self):
        assert wants_finder("find playoff games where tatum had 40+")

    def test_give_me(self):
        assert wants_finder("give me jokic games over 25 points")

    def test_what_games(self):
        assert wants_finder("what games did jokic have 30+ points")

    def test_which_games(self):
        assert wants_finder("which games did tatum score 40+")

    def test_show_all(self):
        assert wants_finder("show all jokic 30 point games")

    def test_show_every(self):
        assert wants_finder("show every celtics win vs lakers")

    def test_show_games(self):
        assert wants_finder("show games where jokic had a triple double")

    def test_no_finder_intent(self):
        assert not wants_finder("jokic summary 2024-25")

    def test_no_finder_for_summary(self):
        assert not wants_finder("summarize jokic vs lakers")

    def test_no_finder_for_count(self):
        assert not wants_finder("how many games did jokic play")


class TestWantsCount:
    """Test the wants_count() detection function."""

    def test_how_many(self):
        assert wants_count("how many 40 point games has tatum had since 2020")

    def test_how_often(self):
        assert wants_count("how often has jokic recorded a triple double this season")

    def test_count(self):
        assert wants_count("count jokic triple-doubles in playoffs since 2021")

    def test_number_of(self):
        assert wants_count("number of celtics games vs bucks since 2022")

    def test_total_games(self):
        assert wants_count("total games with 15+ rebounds vs lakers")

    def test_total_number(self):
        assert wants_count("total number of 30 point games")

    def test_total_count(self):
        assert wants_count("total count of wins vs heat")

    def test_no_count_for_average_rate(self):
        # "how many points does X average" asks for a per-game rate,
        # not a count of games.
        assert not wants_count("how many points does jokic average")

    def test_no_count_for_list(self):
        assert not wants_count("show me jokic games")

    def test_no_count_for_summary(self):
        assert not wants_count("jokic career summary")


class TestWantsSummary:
    """Test summary detection (existing + new patterns)."""

    def test_summary(self):
        assert wants_summary("jokic summary 2024-25")

    def test_summarize(self):
        assert wants_summary("summarize jokic vs lakers since 2021")

    def test_average(self):
        assert wants_summary("jokic average 2024-25")

    def test_averages(self):
        assert wants_summary("jokic averages 2024-25")

    def test_career_summary(self):
        assert wants_summary("jokic career summary")

    def test_record(self):
        assert wants_summary("celtics record vs heat since 2020")

    def test_points_per_game(self):
        assert wants_summary("jokic points per game")

    def test_ppg_shorthand(self):
        assert wants_summary("jokic ppg")

    def test_rpg_shorthand(self):
        assert wants_summary("jokic rpg this season")

    def test_no_summary_for_finder(self):
        assert not wants_summary("show me jokic games with 30 points")


class TestWantsLeaderboard:
    """Test leaderboard detection including new 'rank' keyword."""

    def test_leaders_in(self):
        assert wants_leaderboard("leaders in ts% since 2020")

    def test_top_scorers(self):
        assert wants_leaderboard("top 20 scorers vs lakers since 2018")

    def test_rank(self):
        assert wants_leaderboard("rank players by net rating")

    def test_ranked(self):
        assert wants_leaderboard("ranked by ppg since 2020")

    def test_ranking(self):
        assert wants_leaderboard("ranking by ppg this season")

    def test_who_has_the_most(self):
        assert wants_leaderboard("who has the most ppg since 2020")

    def test_who_led(self):
        assert wants_leaderboard("who led the most in ppg")

    def test_season_leaders(self):
        assert wants_leaderboard("season leaders in ppg 2024-25")

    def test_highest_ts(self):
        assert wants_leaderboard("highest ts% 2024-25")

    def test_lowest_tov(self):
        assert wants_leaderboard("lowest tov pct 2024-25")


class TestWantsTeamLeaderboard:
    """Test team leaderboard detection including 'rank'."""

    def test_rank_teams(self):
        assert wants_team_leaderboard("rank teams by net rating")

    def test_ranked_teams(self):
        assert wants_team_leaderboard("ranked teams by pts")

    def test_best_teams(self):
        assert wants_team_leaderboard("best offensive teams 2024-25")

    def test_top_teams(self):
        assert wants_team_leaderboard("top 10 teams in scoring")


# ===================================================================
# Parse State Extraction
# ===================================================================


class TestParseStateIntents:
    """Verify that _build_parse_state produces correct intent flags."""

    def test_finder_intent_show_me(self):
        parsed = _build_parse_state("show me Jokic games with 30 points 2024-25")
        assert parsed["finder_intent"] is True
        assert parsed["count_intent"] is False

    def test_finder_intent_list(self):
        parsed = _build_parse_state("list Celtics games vs Bucks since 2021")
        assert parsed["finder_intent"] is True

    def test_count_intent_how_many(self):
        parsed = _build_parse_state("how many 40 point games has Jokic had since 2020")
        assert parsed["count_intent"] is True
        assert parsed["finder_intent"] is False

    def test_count_intent_count(self):
        parsed = _build_parse_state("count Jokic games over 25 points 2024-25")
        assert parsed["count_intent"] is True

    def test_no_explicit_intent(self):
        parsed = _build_parse_state("Jokic over 25 points 2024-25")
        assert parsed["finder_intent"] is False
        assert parsed["count_intent"] is False

    def test_summary_intent_preserved(self):
        parsed = _build_parse_state("Jokic career summary")
        assert parsed["summary_intent"] is True
        assert parsed["finder_intent"] is False

    def test_leaderboard_intent_rank(self):
        parsed = _build_parse_state("rank players by ppg 2024-25")
        assert parsed["leaderboard_intent"] is True


# ===================================================================
# Route Selection
# ===================================================================


class TestRouteSelection:
    """Verify that explicit intent correctly influences route selection."""

    def test_finder_intent_routes_to_finder(self):
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"

    def test_finder_intent_overrides_range_summary(self):
        """When both range_intent and finder_intent are present,
        finder_intent should win and route to finder, not summary."""
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"
        # Without finder_intent, range_intent would route to summary

    def test_count_intent_routes_to_finder(self):
        parsed = parse_query("how many 30 point games has Jokic had 2024-25")
        assert parsed["route"] == "player_game_finder"

    def test_count_intent_sets_no_limit(self):
        """Count queries should not limit results for accurate counting."""
        parsed = parse_query("how many 30 point games has Jokic had 2024-25")
        assert parsed["route_kwargs"].get("limit") is None

    def test_finder_intent_keeps_limit(self):
        """Regular finder intent should keep the default limit."""
        parsed = parse_query("show me Jokic games with 30 points 2024-25")
        assert parsed["route_kwargs"].get("limit") == 25

    def test_team_finder_intent(self):
        parsed = parse_query("list Celtics games vs Bucks 2024-25")
        assert parsed["route"] == "game_finder"

    def test_team_count_intent(self):
        parsed = parse_query("how many Celtics games vs Bucks 2024-25")
        assert parsed["route"] == "game_finder"
        assert parsed["route_kwargs"].get("limit") is None

    def test_summary_intent_still_routes_to_summary(self):
        """When summary is explicitly requested, it should still route to summary."""
        parsed = parse_query("summarize Jokic vs Lakers since 2021")
        assert parsed["route"] in ("player_game_summary", "player_compare")

    def test_leaderboard_rank_routes_correctly(self):
        parsed = parse_query("rank players by ppg 2024-25")
        assert parsed["route"] == "season_leaders"

    def test_points_per_game_routes_to_summary(self):
        parsed = parse_query("Shai points per game")
        assert parsed["route"] == "player_game_summary"
        assert parsed["player"] == "Shai Gilgeous-Alexander"

    def test_how_many_average_routes_to_summary(self):
        parsed = parse_query("how many points does Jokic average")
        assert parsed["route"] == "player_game_summary"

    def test_per_game_leaderboard_still_routes_to_leaders(self):
        # "per game" must not drag leaderboard questions into a
        # single-player summary.
        parsed = parse_query("who leads the NBA in points per game this season")
        assert parsed["route"] == "season_leaders"

    def test_last_game_is_one_game_window(self):
        parsed = parse_query("wemby blocks last game")
        assert parsed["route"] == "player_game_finder"
        assert parsed["route_kwargs"].get("last_n") == 1

    def test_team_when_player_scores_routes_to_summary(self):
        # "<team> when <player> scores N" is a record-shaped ask: the
        # threshold must apply and the answer is a summary, not a game list.
        parsed = parse_query("knicks when brunson scores 30")
        assert parsed["route"] == "player_game_summary"
        assert parsed["route_kwargs"].get("team") == "NYK"
        assert parsed["route_kwargs"].get("min_value") == 30.0

    def test_twenty_ten_combo_sets_both_thresholds(self):
        parsed = parse_query("wemby 20 10 games")
        conds = [(c["stat"], c["min_value"]) for c in parsed.get("conditions") or []]
        assert ("pts", 20.0) in conds
        assert ("reb", 10.0) in conds

    def test_last_n_games_does_not_become_combo(self):
        parsed = parse_query("luka last 10 games")
        assert not parsed.get("conditions")
        assert parsed["route"] == "player_game_summary"

    def test_team_3pt_shooting_ranks_by_fg3_pct(self):
        parsed = parse_query("best 3pt shooting team")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"].get("stat") == "fg3_pct"

    def test_player_3_point_percentage_stays_player_leaderboard(self):
        parsed = parse_query("Who has the best 3 point percentage this season?")
        assert parsed["route"] == "season_leaders"

    def test_rings_question_refuses(self):
        # Championship counts are not in the game-stats data; never answer
        # with a count of games.
        parsed = parse_query("how many rings does lebron have")
        assert parsed["route"] is None
        assert parsed["intent"] == "unsupported"

    def test_schedule_question_refuses(self):
        parsed = parse_query("when do the lakers play next")
        assert parsed["route"] is None
        assert parsed["intent"] == "unsupported"

    def test_when_did_player_score_still_answers(self):
        # Past-tense "when did" questions are answerable; only future
        # schedule shapes refuse.
        parsed = parse_query("when did jokic score 40")
        assert parsed["route"] == "player_game_finder"

    def test_this_year_playoffs_means_current_season(self):
        # Never silently substitute the previous completed playoffs for an
        # explicit current-season ask.
        parsed = parse_query("Jokic playoff stats this year")
        assert parsed["season"] == "2025-26"
        assert parsed["season_type"] == "Playoffs"

    def test_unanchored_playoffs_default_carries_note(self):
        parsed = parse_query("kyrie points in the playoffs")
        assert parsed["season"] == "2025-26"
        assert any("defaulted" in n for n in parsed.get("notes") or [])

    def test_fuzzy_day_window_sets_flag(self):
        parsed = parse_query("bron points last night")
        assert parsed["fuzzy_date_window"] is True
        parsed = parse_query("Jokic recent form")
        assert parsed["fuzzy_date_window"] is False

    def test_single_team_advanced_scalar_routes_to_team_leaders(self):
        # "wolves defensive rating" answers from the full team leaderboard
        # so the scalar arrives with its league rank.
        parsed = parse_query("wolves defensive rating")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"].get("stat") == "def_rating"
        # def_rating ranks ascending: lowest is best.
        assert parsed["route_kwargs"].get("ascending") is True

    def test_single_team_pace_routes_to_team_leaders(self):
        parsed = parse_query("kings pace this season")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["route_kwargs"].get("stat") == "pace"
        assert parsed["route_kwargs"].get("ascending") is False

    def test_windowed_team_advanced_scalar_still_refuses(self):
        parsed = parse_query("wolves defensive rating since January")
        assert parsed["route"] == "game_summary"
        assert "single_team_advanced_stat_summary" in (
            parsed["route_kwargs"].get("unsupported_filters") or []
        )

    def test_league_threshold_games_route(self):
        parsed = parse_query("who dropped 40 this week")
        assert parsed["route"] == "top_player_games"
        assert parsed["route_kwargs"].get("min_value") == 40.0
        assert parsed["route_kwargs"].get("stat") == "pts"

    def test_league_threshold_does_not_steal_leaderboards(self):
        parsed = parse_query("who leads the league in scoring")
        assert parsed["route"] == "season_leaders"

    def test_team_leading_scorer_routes_team_scoped(self):
        parsed = parse_query("lakers leading scorer")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("team") == "LAL"
        assert parsed["route_kwargs"].get("stat") == "pts"

    def test_team_leader_in_assists_sets_stat(self):
        parsed = parse_query("celtics leader in assists")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("team") == "BOS"
        assert parsed["route_kwargs"].get("stat") == "ast"

    def test_who_scores_most_for_team(self):
        parsed = parse_query("who scores the most for the celtics")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("team") == "BOS"

    def test_sophomore_leaders_filter_sophomores(self):
        parsed = parse_query("sophomore scoring leaders")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("sophomores_only") is True

    def test_best_player_on_team_refuses(self):
        parsed = parse_query("best player on the lakers")
        assert parsed["route"] is None
        assert parsed["route_kwargs"].get("unsupported_filters") == ["subjective_query"]

    def test_two_player_combined_refuses(self):
        parsed = parse_query("luka and kyrie combined points")
        assert parsed["route"] is None
        assert parsed["route_kwargs"].get("unsupported_filters") == ["multi_player_aggregate"]

    def test_rookie_leaderboard_routes_with_rookie_filter(self):
        parsed = parse_query("rookie scoring leaders")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("rookies_only") is True

    def test_top_rookies_routes_with_rookie_filter(self):
        parsed = parse_query("top rookies this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("rookies_only") is True

    def test_bench_leaderboard_routes_with_role(self):
        parsed = parse_query("most points off the bench")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("role") == "bench"

    def test_starter_leaderboard_routes_with_role(self):
        parsed = parse_query("top scorers among starters this season")
        assert parsed["route"] == "season_leaders"
        assert parsed["route_kwargs"].get("role") == "starter"

    def test_plain_leaderboard_has_no_role_or_rookie_filter(self):
        parsed = parse_query("top scorers this season")
        assert parsed["route_kwargs"].get("role") is None
        assert not parsed["route_kwargs"].get("rookies_only")

    def test_team_leaderboard_rank(self):
        parsed = parse_query("rank teams by net rating 2024-25")
        assert parsed["route"] == "season_team_leaders"

    def test_plain_player_query_defaults_to_finder(self):
        """Without explicit intent, a player + stat query should still default to finder."""
        parsed = parse_query("Jokic over 25 points 2024-25")
        assert parsed["route"] == "player_game_finder"


# ===================================================================
# Historical + Opponent Integration
# ===================================================================


class TestIntentWithHistorical:
    """Verify intents work with since-year, season ranges, last N, career, playoffs."""

    def test_finder_with_since(self):
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("start_season") is not None

    def test_count_with_since(self):
        parsed = parse_query("how many 40 point games has Jokic had since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("start_season") is not None

    def test_finder_with_last_n_seasons(self):
        parsed = parse_query("show me Jokic games with 25 points last 3 seasons")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("start_season") is not None

    def test_count_with_playoffs(self):
        parsed = parse_query("how many playoff games did Jokic have 25 points 2024-25")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True

    def test_leaderboard_with_since(self):
        parsed = parse_query("leaders in ts% since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed.get("start_season") is not None

    def test_leaderboard_rank_with_last_n(self):
        parsed = parse_query("rank teams by net rating last 3 seasons")
        assert parsed["route"] == "season_team_leaders"

    def test_summary_with_career(self):
        parsed = parse_query("Jokic career summary")
        assert parsed["route"] == "player_game_summary"


class TestIntentWithOpponent:
    """Verify intents work with opponent filters."""

    def test_finder_with_opponent(self):
        parsed = parse_query("show me Jokic games vs Lakers 2024-25")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("opponent") is not None

    def test_count_with_opponent(self):
        parsed = parse_query("how many games did Jokic have 30 points vs Lakers since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("opponent") is not None

    def test_team_finder_with_opponent(self):
        parsed = parse_query("list Celtics games vs Bucks since 2021")
        assert parsed["route"] == "game_finder"
        assert parsed.get("opponent") is not None

    def test_team_count_with_opponent(self):
        parsed = parse_query("how many Celtics games vs Heat since 2022")
        assert parsed["route"] == "game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("opponent") is not None

    def test_leaderboard_with_opponent(self):
        parsed = parse_query("top 20 scorers vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed.get("opponent") is not None


@pytest.mark.parametrize(
    "query",
    [
        "How often have the Lakers held opponents under 100 points this year?",
        "How often have the Lakers held them to under 100 points this year?",
        "How often have the Lakers limited opponents to under 100 points this year?",
        "How often have the Lakers kept the other team below 100 points this year?",
        "How often have the Lakers allowed under 100 points this year?",
        "Lakers gave up fewer than 100 points this year",
        "How often have the Lakers given up fewer than 100 points this year?",
        "Lakers opponents under 100 this year",
    ],
)
def test_opponent_points_allowed_phrasings_use_opponent_pts(query):
    parsed = parse_query(query)

    assert parsed["route"] == "game_finder"
    assert parsed["team"] == "LAL"
    assert parsed["stat"] == "opponent_pts"
    assert parsed["max_value"] == pytest.approx(99.9999)
    assert parsed["route_kwargs"]["stat"] == "opponent_pts"
    assert parsed["route_kwargs"]["max_value"] == pytest.approx(99.9999)


def test_team_finder_opponent_pts_filter_uses_opponent_score():
    import pandas as pd

    from nbatools.commands.game_finder import _apply_filters

    df = pd.DataFrame(
        [
            {
                "game_id": "win-low-opp",
                "game_date": "2026-01-01",
                "team_abbr": "LAL",
                "team_name": "Los Angeles Lakers",
                "pts": 116,
                "plus_minus": 17,
                "wl": "W",
                "is_home": 1,
                "is_away": 0,
            },
            {
                "game_id": "loss-low-own",
                "game_date": "2026-01-02",
                "team_abbr": "LAL",
                "team_name": "Los Angeles Lakers",
                "pts": 96,
                "plus_minus": -12,
                "wl": "L",
                "is_home": 0,
                "is_away": 1,
            },
        ]
    )

    filtered = _apply_filters(df, team="LAL", stat="opponent_pts", max_value=99.9999)

    assert filtered["game_id"].tolist() == ["win-low-opp"]
    assert filtered["opponent_pts"].tolist() == [99]


# ===================================================================
# CountResult Semantics
# ===================================================================


class TestCountResult:
    """Verify CountResult contract and serialization."""

    def test_count_result_to_dict(self):
        import pandas as pd

        games = pd.DataFrame(
            {"rank": [1, 2, 3], "game_date": ["2024-01-01", "2024-01-02", "2024-01-03"]}
        )
        cr = CountResult(count=3, games=games)
        d = cr.to_dict()
        assert d["query_class"] == "count"
        assert d["result_status"] == "ok"
        assert d["sections"]["count"] == [{"count": 3}]
        assert len(d["sections"]["finder"]) == 3

    def test_count_result_zero(self):
        cr = CountResult(count=0)
        d = cr.to_dict()
        assert d["query_class"] == "count"
        assert d["sections"]["count"] == [{"count": 0}]
        assert "finder" not in d["sections"]

    def test_count_result_labeled_text(self):
        import pandas as pd

        games = pd.DataFrame({"rank": [1], "game_date": ["2024-01-01"]})
        cr = CountResult(count=1, games=games)
        text = cr.to_labeled_text()
        assert "COUNT" in text
        assert "1" in text

    @pytest.mark.needs_data
    def test_bare_stat_count_sums_stat_not_games(self):
        # "how many threes did curry hit" asks for the number of threes,
        # not the number of games he played.
        qr = execute_natural_query("how many threes did curry hit")
        assert isinstance(qr.result, CountResult)
        games = qr.result.games
        assert qr.result.count == int(games["fg3m"].sum())

    @pytest.mark.needs_data
    def test_threshold_count_still_counts_games(self):
        qr = execute_natural_query("how many 30 point games has Jokic had 2024-25")
        assert isinstance(qr.result, CountResult)
        assert qr.result.count == len(qr.result.games)

    @pytest.mark.needs_data
    def test_team_advanced_scalar_answer_phrase(self):
        qr = execute_natural_query("celtics net rating")
        md = qr.metadata or {}
        phrase = md.get("answer_phrase") or ""
        assert "net rating" in phrase
        assert "of 30" in phrase
        assert "Celtics" in phrase

    @pytest.mark.needs_data
    def test_league_threshold_games_all_meet_threshold(self):
        qr = execute_natural_query("who scored 50+ points this season")
        assert isinstance(qr.result, LeaderboardResult)
        assert (qr.result.leaders["pts"] >= 50).all()

    @pytest.mark.needs_data
    def test_rookie_leaderboard_executes_with_caveat(self):
        qr = execute_natural_query("rookie scoring leaders")
        assert isinstance(qr.result, LeaderboardResult)
        assert any("rookies" in c for c in qr.result.caveats)

    @pytest.mark.needs_data
    def test_bench_leaderboard_executes_with_complete_live_role_coverage(self):
        qr = execute_natural_query("most points off the bench")
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.result.result_status == "ok"
        assert not qr.result.leaders.empty
        assert any(
            "filtered to bench games using trusted starter-role data" in note
            for note in qr.metadata["notes"]
        )

    @pytest.mark.needs_data
    def test_bench_leaderboard_refuses_without_role_coverage(self):
        # 2010-11 predates the trusted starter-role dataset.
        qr = execute_natural_query("most bench points in 2010-11")
        assert qr.result.result_status == "no_result"
        assert qr.result.result_reason == "filter_not_supported"

    def test_count_result_sections_dict(self):
        import pandas as pd

        games = pd.DataFrame({"rank": [1, 2], "game_date": ["2024-01-01", "2024-01-02"]})
        cr = CountResult(count=2, games=games)
        sections = cr.to_sections_dict()
        assert "COUNT" in sections
        assert "FINDER" in sections

    def test_count_result_trust_fields(self):
        cr = CountResult(
            count=5,
            result_status="ok",
            current_through="2025-04-10",
            notes=["test note"],
            caveats=["test caveat"],
        )
        d = cr.to_dict()
        assert d["result_status"] == "ok"
        assert d["current_through"] == "2025-04-10"
        assert "test note" in d["notes"]
        assert "test caveat" in d["caveats"]


# ===================================================================
# Service/API Compatibility (slow tests with real data)
# ===================================================================


@pytest.mark.slow
class TestExplicitIntentExecution:
    """Execute explicit intent queries through the service layer."""

    @pytest.mark.needs_data
    def test_finder_intent_returns_finder_result(self):
        qr = execute_natural_query("show me Jokic games with 25 points 2024-25")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, FinderResult)
        assert qr.is_ok
        assert qr.route == "player_game_finder"

    def test_count_intent_returns_count_result(self):
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, CountResult)
        assert qr.is_ok
        assert qr.result.count >= 0
        assert qr.metadata.get("query_class") == "count"

    def test_count_result_has_accurate_count(self):
        """Count result should report the total matching games, not a limited subset."""
        qr = execute_natural_query("how many games did Jokic have 10 points 2024-25")
        assert isinstance(qr.result, CountResult)
        # The count should be the actual number of matching games
        if qr.result.count > 0:
            assert len(qr.result.games) == qr.result.count

    def test_count_with_since(self):
        qr = execute_natural_query("how many 30 point games has Jokic had since 2022")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0
            assert qr.metadata.get("query_class") == "count"

    def test_count_with_opponent(self):
        qr = execute_natural_query("how many Celtics games vs Heat 2024-25")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0

    def test_count_zero_returns_ok(self):
        """A count of zero should return status ok with count=0, not an error."""
        qr = execute_natural_query("how many 100 point games has Jokic had 2024-25")
        assert isinstance(qr.result, CountResult)
        assert qr.result.count == 0
        assert qr.result.result_status == "ok"

    def test_finder_intent_overrides_range_to_summary(self):
        """'show me Jokic games with 30 points since 2020' should be finder, not summary."""
        qr = execute_natural_query("show me Jokic games with 30 points since 2020")
        assert isinstance(qr.result, (FinderResult, NoResult))
        assert qr.route == "player_game_finder"

    @pytest.mark.needs_data
    def test_summary_intent_returns_summary(self):
        qr = execute_natural_query("summarize Jokic 2024-25")
        assert isinstance(qr.result, SummaryResult)
        assert qr.route == "player_game_summary"

    def test_summary_with_opponent(self):
        qr = execute_natural_query("summarize Jokic vs Lakers 2024-25")
        assert isinstance(qr.result, (SummaryResult, NoResult))

    @pytest.mark.needs_data
    def test_leaderboard_rank(self):
        qr = execute_natural_query("top 5 scorers 2024-25")
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.route == "season_leaders"

    def test_leaderboard_with_opponent(self):
        qr = execute_natural_query("top 10 scorers vs Lakers 2024-25")
        assert isinstance(qr.result, (LeaderboardResult, NoResult))
        assert qr.route == "season_leaders"

    def test_count_result_to_dict_api_compatible(self):
        """CountResult.to_dict() should produce a valid dict for the API response."""
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        if isinstance(qr.result, CountResult):
            d = qr.result.to_dict()
            assert "query_class" in d
            assert "result_status" in d
            assert "sections" in d
            assert "count" in d["sections"]

    def test_team_list_intent(self):
        qr = execute_natural_query("list Celtics games 2024-25")
        assert isinstance(qr.result, (FinderResult, NoResult))
        assert qr.route == "game_finder"

    def test_team_count_intent(self):
        qr = execute_natural_query("how many Celtics wins 2024-25")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0

    def test_metadata_preserved_for_count(self):
        """Count results should still carry full metadata."""
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert qr.metadata.get("route") == "player_game_finder"
        assert qr.metadata.get("query_class") == "count"
        if qr.current_through:
            assert isinstance(qr.current_through, str)

    def test_result_status_for_count(self):
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert qr.result_status == "ok"
