import pytest

from nbatools.commands.natural_query import detect_opponent_quality, parse_query

pytestmark = pytest.mark.parser


def test_kobe_50_point_games_summary():
    parsed = parse_query("Kobe 50 point games summary in 2005-06")
    assert parsed["player"] == "Kobe Bryant"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] == 50.0
    assert parsed["season"] == "2005-06"
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "player_game_summary"


def test_boston_home_wins_vs_milwaukee_range():
    parsed = parse_query("Boston home wins vs Milwaukee from 2021-22 to 2023-24")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"
    assert parsed["start_season"] == "2021-22"
    assert parsed["end_season"] == "2023-24"
    assert parsed["season"] is None
    assert parsed["home_only"] is True
    assert parsed["wins_only"] is True
    assert parsed["route"] == "game_summary"


def test_playoff_player_finder():
    parsed = parse_query("Kobe playoff games in 2008-09")
    assert parsed["player"] == "Kobe Bryant"
    assert parsed["season"] == "2008-09"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["route"] == "player_game_finder"


def test_playoff_player_summary():
    parsed = parse_query("Kobe playoff summary in 2008-09")
    assert parsed["player"] == "Kobe Bryant"
    assert parsed["season"] == "2008-09"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["route"] == "player_game_summary"


def test_playoff_season_leaders():
    parsed = parse_query("season leaders in assists for 2023-24 playoffs")
    assert parsed["stat"] == "ast"
    assert parsed["season"] == "2023-24"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["route"] == "season_leaders"


def test_opponent_does_not_override_main_team():
    parsed = parse_query("Boston home wins vs Milwaukee from 2021-22 to 2023-24")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"


def test_dallas_opponent_for_player_summary():
    parsed = parse_query("Kobe 40 point games summary vs Dallas in 2005-06")
    assert parsed["player"] == "Kobe Bryant"
    assert parsed["opponent"] == "DAL"
    assert parsed["team"] is None
    assert parsed["min_value"] == 40.0
    assert parsed["route"] == "player_game_summary"


def test_lebron_alias_detected():
    parsed = parse_query("LeBron playoff summary in 2017-18")
    assert parsed["player"] == "LeBron James"
    assert parsed["season"] == "2017-18"
    assert parsed["season_type"] == "Playoffs"


def test_jokic_lakers_range_summary():
    parsed = parse_query("Jokic summary against Lakers from 2021-22 to 2023-24")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["opponent"] == "LAL"
    assert parsed["start_season"] == "2021-22"
    assert parsed["end_season"] == "2023-24"
    assert parsed["route"] == "player_game_summary"


def test_player_comparison_regular_season_route():
    parsed = parse_query("Kobe vs LeBron in 2005-06")
    assert parsed["player_a"] == "Kobe Bryant"
    assert parsed["player_b"] == "LeBron James"
    assert parsed["season"] == "2005-06"
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "player_compare"


def test_player_comparison_playoffs_route():
    parsed = parse_query("Kobe vs LeBron playoffs in 2008-09")
    assert parsed["player_a"] == "Kobe Bryant"
    assert parsed["player_b"] == "LeBron James"
    assert parsed["season"] == "2008-09"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["route"] == "player_compare"


def test_player_comparison_multiseason_route():
    parsed = parse_query("Jokic vs Embiid from 2021-22 to 2023-24")
    assert parsed["player_a"] == "Nikola Jokić"
    assert parsed["player_b"] == "Joel Embiid"
    assert parsed["start_season"] == "2021-22"
    assert parsed["end_season"] == "2023-24"
    assert parsed["season"] is None
    assert parsed["route"] == "player_compare"


def test_full_name_player_comparison_route():
    parsed = parse_query("LeBron James vs Kevin Durant comparison")
    assert parsed["route"] == "player_compare"
    assert parsed["player_a"] == "LeBron James"
    assert parsed["player_b"] == "Kevin Durant"


def test_compare_full_names_and_route():
    parsed = parse_query("Compare LeBron James and Kevin Durant")
    assert parsed["route"] == "player_compare"
    assert parsed["player_a"] == "LeBron James"
    assert parsed["player_b"] == "Kevin Durant"


def test_alias_player_comparison_still_routes():
    parsed = parse_query("LeBron vs Durant")
    assert parsed["route"] == "player_compare"
    assert parsed["player_a"] == "LeBron James"
    assert parsed["player_b"] == "Kevin Durant"


def test_player_game_log_vs_player_stays_finder():
    parsed = parse_query("Jokic game log vs Embiid")
    assert parsed["route"] == "player_game_finder"
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["opponent_player"] == "Joel Embiid"


def test_team_comparison_regular_season_route():
    parsed = parse_query("Celtics vs Bucks from 2021-22 to 2023-24")
    assert parsed["team_a"] == "BOS"
    assert parsed["team_b"] == "MIL"
    assert parsed["start_season"] == "2021-22"
    assert parsed["end_season"] == "2023-24"
    assert parsed["season"] is None
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "team_compare"


def test_team_comparison_playoffs_route():
    parsed = parse_query("Boston vs Milwaukee playoffs 2023-24")
    assert parsed["team_a"] == "BOS"
    assert parsed["team_b"] == "MIL"
    assert parsed["season"] == "2023-24"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["route"] == "team_compare"


def test_team_comparison_no_opponent_leak():
    parsed = parse_query("Celtics vs Bucks from 2021-22 to 2023-24")
    assert parsed["team_a"] == "BOS"
    assert parsed["team_b"] == "MIL"
    assert parsed["opponent"] is None


def test_recent_form_player_defaults_to_last_10_and_summary():
    parsed = parse_query("Jokic recent form")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["last_n"] == 10
    assert parsed["season"] == "2025-26"
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "player_game_summary"


def test_recent_form_team_defaults_to_last_10_and_summary():
    parsed = parse_query("Celtics recent form")
    assert parsed["team"] == "BOS"
    assert parsed["last_n"] == 10
    assert parsed["season"] == "2025-26"
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "game_summary"


def test_recent_form_player_comparison_defaults_to_last_10():
    parsed = parse_query("Jokic vs Embiid recent form")
    assert parsed["player_a"] == "Nikola Jokić"
    assert parsed["player_b"] == "Joel Embiid"
    assert parsed["last_n"] == 10
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_compare"


def test_last_n_player_summary_route():
    parsed = parse_query("LeBron last 8 games summary")
    assert parsed["player"] == "LeBron James"
    assert parsed["last_n"] == 8
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_summary"


def test_anthony_edwards_full_name_last_n_summary_route():
    parsed = parse_query("Anthony Edwards last 10 games summary")
    assert parsed["player"] == "Anthony Edwards"
    assert parsed["last_n"] == 10
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_summary"


def test_anthony_edwards_full_name_wins_losses_split_route():
    parsed = parse_query("How does Anthony Edwards shoot in wins versus losses?")
    assert parsed["player"] == "Anthony Edwards"
    assert parsed["split_type"] == "wins_losses"
    assert parsed["route"] == "player_split_summary"


def test_last_n_team_summary_route():
    parsed = parse_query("Celtics last 15 games summary")
    assert parsed["team"] == "BOS"
    assert parsed["last_n"] == 15
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "game_summary"


def test_recent_form_playoff_default_season():
    parsed = parse_query("LeBron recent form playoffs")
    assert parsed["player"] == "LeBron James"
    assert parsed["last_n"] == 10
    assert parsed["season"] == "2024-25"
    assert parsed["season_type"] == "Playoffs"


def test_player_split_home_away_route():
    parsed = parse_query("Jokic home vs away in 2025-26")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["split_type"] == "home_away"
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_split_summary"


def test_team_split_wins_losses_default_season_route():
    parsed = parse_query("Celtics wins vs losses")
    assert parsed["team"] == "BOS"
    assert parsed["split_type"] == "wins_losses"
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "team_split_summary"


def test_player_split_last_n_route():
    parsed = parse_query("Jokic home away split last 20 games")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["split_type"] == "home_away"
    assert parsed["last_n"] == 20
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_split_summary"


def test_team_split_explicit_season_route():
    parsed = parse_query("Boston wins losses split in 2025-26")
    assert parsed["team"] == "BOS"
    assert parsed["split_type"] == "wins_losses"
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "team_split_summary"


def test_team_record_road_last_season_relative_season():
    parsed = parse_query("Lakers road record last season")
    assert parsed["route"] == "team_record"
    assert parsed["team"] == "LAL"
    assert parsed["season"] == "2024-25"
    assert parsed["explicit_relative_season"] is True
    assert parsed["away_only"] is True


def test_team_record_away_last_season_relative_season():
    parsed = parse_query("Lakers away record last season")
    assert parsed["route"] == "team_record"
    assert parsed["season"] == "2024-25"
    assert parsed["away_only"] is True


def test_team_record_explicit_season_road_still_works():
    parsed = parse_query("Lakers 2024-25 road record")
    assert parsed["route"] == "team_record"
    assert parsed["season"] == "2024-25"
    assert parsed["explicit_relative_season"] is False
    assert parsed["away_only"] is True


def test_last_n_games_does_not_parse_as_last_season():
    parsed = parse_query("Anthony Edwards last 10 games summary")
    assert parsed["season"] == "2025-26"
    assert parsed["last_n"] == 10
    assert parsed["explicit_relative_season"] is False


def test_single_threshold_defaults_season_for_player_finder():
    parsed = parse_query("LeBron playoff games over 30 points vs Boston")
    assert parsed["player"] == "LeBron James"
    assert parsed["season"] == "2024-25"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["opponent"] == "BOS"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is not None
    assert parsed["route"] == "player_game_finder"


def test_single_threshold_defaults_season_for_team_finder():
    parsed = parse_query("Celtics wins vs Bucks over 120 points")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"
    assert parsed["wins_only"] is True
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is not None
    assert parsed["route"] == "game_finder"


def test_multi_condition_player_query_parses_route_conditions():
    parsed = parse_query("Jokic last 10 games over 25 points and over 10 rebounds")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["last_n"] == 10
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is not None
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 2
    assert parsed["extra_conditions"] == []
    assert parsed["route_kwargs"]["conditions"] == parsed["threshold_conditions"]
    assert parsed["route_kwargs"]["conditions"][1]["stat"] == "reb"
    assert parsed["route_kwargs"]["conditions"][1]["min_value"] is not None


def test_multi_condition_team_query_parses_route_conditions():
    parsed = parse_query("Celtics wins vs Bucks over 120 points and over 15 threes")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"
    assert parsed["wins_only"] is True
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["route"] == "game_finder"
    assert len(parsed["threshold_conditions"]) == 2
    assert parsed["extra_conditions"] == []
    assert parsed["route_kwargs"]["conditions"] == parsed["threshold_conditions"]
    assert parsed["route_kwargs"]["conditions"][1]["stat"] == "fg3m"


def test_compound_team_count_uses_route_conditions_without_duplicate_extras():
    parsed = parse_query("how many Celtics games with 120+ points and 15+ threes since 2022")

    assert parsed["route"] == "team_occurrence_leaders"
    assert parsed["team"] == "BOS"
    assert parsed["route_kwargs"]["conditions"] == [
        {"stat": "pts", "min_value": 120.0, "max_value": None},
        {"stat": "fg3m", "min_value": 15.0, "max_value": None},
    ]
    assert parsed["conditions"] == parsed["route_kwargs"]["conditions"]
    assert parsed["extra_conditions"] == []


def test_compact_player_finder_compound_binds_values_to_each_stat():
    parsed = parse_query("Jokic games with 30 points and 10 assists")

    assert parsed["route"] == "player_game_finder"
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] == 30.0
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 30.0
    assert parsed["route_kwargs"]["conditions"] == [
        {"stat": "pts", "min_value": 30.0, "max_value": None},
        {"stat": "ast", "min_value": 10.0, "max_value": None},
    ]
    assert parsed["extra_conditions"] == []


def test_single_stat_threshold_still_uses_scalar_route_kwargs():
    parsed = parse_query("Curry 5+ threes this season")

    assert parsed["route"] == "player_game_finder"
    assert parsed["stat"] == "fg3m"
    assert parsed["min_value"] == 5.0
    assert "conditions" not in parsed["route_kwargs"]
    assert parsed["extra_conditions"] == []


def test_compact_shorthand_is_not_expanded_to_compound_conditions():
    parsed = parse_query("Jokic 25/10/10")

    assert parsed["compound_occurrence_conditions"] is None
    assert "conditions" not in parsed["route_kwargs"]


def test_under_query_parses_max_value_for_player():
    parsed = parse_query("Jokic under 20 points")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is None
    assert parsed["max_value"] is not None
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 1


def test_team_allow_fewer_than_points_maps_to_opponent_points():
    parsed = parse_query("Knicks record when they allow fewer than 110 points")

    assert parsed["team"] == "NYK"
    assert parsed["route"] == "team_record"
    assert parsed["stat"] == "opponent_pts"
    assert parsed["min_value"] is None
    assert parsed["max_value"] == pytest.approx(109.9999)


def test_team_score_fewer_than_points_stays_team_points():
    parsed = parse_query("Knicks record when they score fewer than 110 points")

    assert parsed["team"] == "NYK"
    assert parsed["route"] == "team_record"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is None
    assert parsed["max_value"] == pytest.approx(109.9999)


def test_held_opponents_under_points_still_maps_to_opponent_points():
    parsed = parse_query("Lakers held opponents under 100 points")

    assert parsed["team"] == "LAL"
    assert parsed["route"] == "game_finder"
    assert parsed["stat"] == "opponent_pts"
    assert parsed["max_value"] == pytest.approx(99.9999)


def test_held_teams_under_points_record_maps_to_opponent_points():
    parsed = parse_query("Lakers record when they held teams under 100")

    assert parsed["team"] == "LAL"
    assert parsed["route"] == "team_record"
    assert parsed["stat"] == "opponent_pts"
    assert parsed["max_value"] == pytest.approx(99.9999)
    assert parsed["route_kwargs"]["stat"] == "opponent_pts"


def test_team_scored_under_points_stays_team_points():
    parsed = parse_query("Lakers record when they scored under 100")

    assert parsed["team"] == "LAL"
    assert parsed["route"] == "team_record"
    assert parsed["stat"] == "pts"
    assert parsed["max_value"] == pytest.approx(99.9999)
    assert parsed["route_kwargs"]["stat"] == "pts"


def test_points_allowed_team_leaderboard_uses_opponent_ppg():
    parsed = parse_query("Which team has allowed the fewest points per game this season?")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is True


def test_gave_up_fewest_points_team_leaderboard_uses_opponent_ppg():
    parsed = parse_query("Which team gave up the fewest points per game this season?")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is True


def test_gave_up_most_points_team_leaderboard_uses_opponent_ppg_descending():
    parsed = parse_query("Which team gave up the most points per game this season?")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is False


def test_most_points_allowed_team_leaderboard_uses_opponent_ppg_descending():
    parsed = parse_query("which teams allow the most points per game this season")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is False


def test_teams_allowing_fewest_points_team_leaderboard_uses_opponent_ppg():
    parsed = parse_query("teams allowing the fewest points this season")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is True


def test_opponent_ppg_leaders_route_to_team_leaderboard():
    parsed = parse_query("opponent PPG leaders this season")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["stat"] == "opponent_pts_per_game"
    assert parsed["route_kwargs"]["ascending"] is False


def test_team_scoring_fewest_points_leaderboard_stays_scoring_ppg():
    parsed = parse_query("Which team scores the fewest points per game this season?")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["ascending"] is True


def test_team_scoring_most_points_leaderboard_stays_scoring_ppg():
    parsed = parse_query("Which teams score the most points per game this season?")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["ascending"] is False


def test_bare_ppg_leaders_stays_player_leaderboard():
    parsed = parse_query("PPG leaders this season")

    assert parsed["route"] == "season_leaders"
    assert parsed["stat"] == "pts"
    assert parsed["route_kwargs"]["stat"] == "pts"


@pytest.mark.parametrize(
    ("query", "stat", "position"),
    [
        ("Which centers have the most rebounds this season?", "reb", "centers"),
        ("guard scoring leaders this season", "pts", "guards"),
        ("forwards FG% leaders this season", "fg_pct", "forwards"),
        ("point guard assist leaders this season", "ast", "guards"),
    ],
)
def test_position_prefix_leaderboards_set_position_filter(query, stat, position):
    parsed = parse_query(query)

    assert parsed["route"] == "season_leaders"
    assert parsed["stat"] == stat
    assert parsed["position_filter"] == position
    assert parsed["route_kwargs"]["position"] == position


@pytest.mark.parametrize(
    ("query", "stat", "position"),
    [
        (
            "What players have the best field goal percentage among guards?",
            "fg_pct",
            "guards",
        ),
        ("best ts% among centers this season", "ts_pct", "centers"),
        ("top scorers among guards since 2021", "pts", "guards"),
    ],
)
def test_among_position_leaderboards_set_position_filter(query, stat, position):
    parsed = parse_query(query)

    assert parsed["route"] == "season_leaders"
    assert parsed["stat"] == stat
    assert parsed["position_filter"] == position
    assert parsed["route_kwargs"]["position"] == position


def test_best_defensive_rating_stays_defensive_rating():
    parsed = parse_query("best defensive rating teams this season")

    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "def_rating"
    assert parsed["route_kwargs"]["ascending"] is True


@pytest.mark.parametrize(
    "query",
    [
        "Boston record when Tatum shoots under 40%",
        "Boston record when Tatum FG% under 40%",
        "Boston record when Tatum shoots under .400",
    ],
)
def test_clear_fg_percentage_thresholds_parse_to_zero_scale(query):
    parsed = parse_query(query)

    assert parsed["route"] == "player_game_summary"
    assert parsed["player"] == "Jayson Tatum"
    assert parsed["team"] == "BOS"
    assert parsed["stat"] == "fg_pct"
    assert parsed["min_value"] is None
    assert parsed["max_value"] == pytest.approx(0.3999)


def test_from_three_percentage_threshold_parses_to_fg3_pct():
    parsed = parse_query("Warriors record when Curry shoots over 40% from three")

    assert parsed["route"] == "player_game_summary"
    assert parsed["player"] == "Stephen Curry"
    assert parsed["team"] == "GSW"
    assert parsed["stat"] == "fg3_pct"
    assert parsed["min_value"] == pytest.approx(0.4001)
    assert parsed["max_value"] is None


def test_between_query_parses_min_and_max_for_player():
    parsed = parse_query("Jokic between 20 and 30 points")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] == 20.0
    assert parsed["max_value"] == 30.0
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 1


def test_mixed_over_and_under_conditions_parse():
    parsed = parse_query("Jokic last 10 games over 25 points and under 15 rebounds")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["last_n"] == 10
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is not None
    assert parsed["max_value"] is None
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 2
    assert parsed["extra_conditions"] == []
    assert parsed["route_kwargs"]["conditions"] == parsed["threshold_conditions"]
    assert parsed["route_kwargs"]["conditions"][1]["stat"] == "reb"
    assert parsed["route_kwargs"]["conditions"][1]["min_value"] is None
    assert parsed["route_kwargs"]["conditions"][1]["max_value"] is not None


def test_between_query_parses_for_team():
    parsed = parse_query("Celtics between 110 and 130 points vs Bucks")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] == 110.0
    assert parsed["max_value"] == 130.0
    assert parsed["route"] == "game_finder"


def test_parse_or_query_routes_to_player_game_finder():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Jokic over 25 points or over 10 rebounds")
    assert parsed["route"] == "player_game_finder"
    assert parsed["player"] == "Nikola Jokić"


def test_parse_between_or_query_routes_to_player_game_finder():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Jokic between 20 and 30 points or under 10 rebounds")
    assert parsed["route"] == "player_game_finder"
    assert parsed["player"] == "Nikola Jokić"


def test_parse_and_or_query_routes_to_player_game_finder():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Jokic over 25 points and over 10 rebounds or over 15 assists")
    assert parsed["route"] == "player_game_finder"
    assert parsed["player"] == "Nikola Jokić"


# ---------------------------------------------------------------------------
# Clutch context filter
# ---------------------------------------------------------------------------


def test_clutch_keyword_sets_slot():
    parsed = parse_query("Tatum clutch stats")
    assert parsed["clutch"] is True


def test_clutch_time_surface_form():
    parsed = parse_query("Lakers clutch time record")
    assert parsed["clutch"] is True


def test_in_the_clutch_surface_form():
    parsed = parse_query("Jokic in the clutch this season")
    assert parsed["clutch"] is True


def test_late_game_surface_form():
    parsed = parse_query("late-game scoring leaders")
    assert parsed["clutch"] is True


def test_late_game_no_hyphen_surface_form():
    parsed = parse_query("Curry late game stats")
    assert parsed["clutch"] is True


def test_no_clutch_when_absent():
    parsed = parse_query("Tatum scoring average")
    assert parsed["clutch"] is False


def test_clutch_note_appended():
    parsed = parse_query("Tatum clutch stats")
    assert parsed["clutch"] is True
    notes = parsed.get("notes", [])
    assert any("clutch" in n for n in notes)


# ---------------------------------------------------------------------------
# Quarter / half context filters
# ---------------------------------------------------------------------------


def test_fourth_quarter_numeric_surface_form():
    parsed = parse_query("LeBron 4th quarter scoring")
    assert parsed["quarter"] == "4"
    assert parsed["half"] is None


def test_fourth_quarter_word_surface_form():
    parsed = parse_query("LeBron fourth quarter scoring")
    assert parsed["quarter"] == "4"


def test_first_half_surface_form():
    parsed = parse_query("Celtics first half stats")
    assert parsed["half"] == "first"
    assert parsed["quarter"] is None


def test_second_half_surface_form():
    parsed = parse_query("Celtics second half stats")
    assert parsed["half"] == "second"


def test_overtime_surface_form_sets_ot_quarter():
    parsed = parse_query("Knicks overtime record")
    assert parsed["quarter"] == "OT"


def test_ot_surface_form_sets_ot_quarter():
    parsed = parse_query("Knicks OT record")
    assert parsed["quarter"] == "OT"


def test_supported_quarter_route_no_longer_appends_parser_note():
    parsed = parse_query("LeBron 4th quarter scoring")
    notes = parsed.get("notes", [])
    assert not any("quarter" in n and "unfiltered" in n for n in notes)


def test_unsupported_half_route_still_appends_parser_note():
    parsed = parse_query("Celtics first half stats")
    notes = parsed.get("notes", [])
    assert any(
        "half filter is not supported with current data" in n and "try removing this filter" in n
        for n in notes
    )


# ---------------------------------------------------------------------------
# Game-context filters
# ---------------------------------------------------------------------------


def test_back_to_back_surface_form_sets_flag():
    parsed = parse_query("Lakers on back-to-backs")
    assert parsed["back_to_back"] is True


def test_b2b_alias_sets_back_to_back_flag():
    parsed = parse_query("Lakers b2b record")
    assert parsed["back_to_back"] is True


def test_second_of_back_to_back_sets_back_to_back_flag():
    parsed = parse_query("Lakers second of a back-to-back record")
    assert parsed["back_to_back"] is True


def test_rest_advantage_surface_form_sets_rest_slot():
    parsed = parse_query("Jokic with rest advantage")
    assert parsed["rest_days"] == "advantage"


def test_rest_disadvantage_surface_form_sets_rest_slot():
    parsed = parse_query("Jokic with rest disadvantage")
    assert parsed["rest_days"] == "disadvantage"


def test_numeric_rest_days_surface_form_sets_rest_slot():
    parsed = parse_query("Jokic on 2 days rest")
    assert parsed["rest_days"] == 2


def test_one_possession_surface_form_sets_flag():
    parsed = parse_query("Celtics one-possession record")
    assert parsed["one_possession"] is True


def test_national_tv_surface_form_sets_flag():
    parsed = parse_query("Knicks on national TV record")
    assert parsed["nationally_televised"] is True


def test_nationally_televised_surface_form_sets_flag():
    parsed = parse_query("Knicks nationally televised record")
    assert parsed["nationally_televised"] is True


def test_back_to_back_note_appended():
    parsed = parse_query("Lakers on back-to-backs")
    notes = parsed.get("notes", [])
    assert any(
        "back_to_back filter is not supported with current data" in n
        and "try removing this filter" in n
        for n in notes
    )


def test_supported_rest_route_no_parse_time_unfiltered_note():
    parsed = parse_query("Jokic with rest advantage")
    notes = parsed.get("notes", [])
    assert not any("rest" in n and "unfiltered" in n for n in notes)


def test_supported_one_possession_route_no_parse_time_unfiltered_note():
    parsed = parse_query("Celtics one-possession record")
    notes = parsed.get("notes", [])
    assert not any("one_possession" in n and "unfiltered" in n for n in notes)


def test_supported_national_tv_route_no_parse_time_unfiltered_note():
    parsed = parse_query("Knicks on national TV record")
    notes = parsed.get("notes", [])
    assert not any("national_tv" in n and "unfiltered" in n for n in notes)


# ---------------------------------------------------------------------------
# Starter / bench role filter
# ---------------------------------------------------------------------------


def test_off_the_bench_surface_form_sets_bench_role():
    parsed = parse_query("Brunson off the bench")
    assert parsed["role"] == "bench"


def test_reserve_surface_form_sets_bench_role():
    parsed = parse_query("Brunson reserve stats")
    assert parsed["role"] == "bench"


def test_as_a_starter_surface_form_sets_starter_role():
    parsed = parse_query("LeBron as a starter stats")
    assert parsed["role"] == "starter"


def test_starting_surface_form_sets_starter_role():
    parsed = parse_query("LeBron starting stats")
    assert parsed["role"] == "starter"


def test_team_bench_scoring_does_not_set_role():
    parsed = parse_query("Celtics bench scoring")
    assert parsed["role"] is None


@pytest.mark.parametrize(
    ("query", "unsupported_filter"),
    [
        ("rookie scoring leaders this season", "rookie_leaderboard"),
        ("bench players scoring leaders this season", "role_leaderboard"),
        ("starter assist leaders this season", "role_leaderboard"),
        ("Celtics bench scoring this season", "team_bench_scoring"),
        ("personal fouls leaders this season", "personal_foul_leaderboard"),
        ("Celtics record against the East this season", "opponent_conference"),
    ],
)
def test_p2_boundary_queries_set_unsupported_filter(query, unsupported_filter):
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["unsupported_filters"] == [unsupported_filter]
    assert any("unsupported_boundary" in note for note in parsed.get("notes", []))


def test_role_note_not_appended_for_supported_role_route():
    parsed = parse_query("Brunson off the bench")
    notes = parsed.get("notes", [])
    assert not any("bench" in n and "unfiltered" in n for n in notes)


# ---------------------------------------------------------------------------
# Opponent-quality filters
# ---------------------------------------------------------------------------


def test_contenders_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic against contenders")
    assert parsed["opponent_quality"]["surface_term"] == "contenders"
    assert parsed["opponent_quality"]["definition"]["metric"] == "conference_rank"


def test_good_teams_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic against good teams")
    assert parsed["opponent_quality"]["surface_term"] == "good teams"


def test_top_teams_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic vs top teams")
    assert parsed["opponent_quality"]["surface_term"] == "top teams"


def test_playoff_teams_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic against playoff teams")
    assert parsed["opponent_quality"]["surface_term"] == "playoff teams"
    assert parsed["season_type"] == "Regular Season"


def test_postseason_teams_surface_form_maps_to_playoff_teams_slot():
    parsed = parse_query("Jokic against postseason teams")
    assert parsed["opponent_quality"]["surface_term"] == "playoff teams"
    assert parsed["season_type"] == "Regular Season"


def test_team_record_against_playoff_teams_stays_regular_season():
    parsed = parse_query("Celtics record against playoff teams")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "playoff teams"


def test_team_record_against_playoff_teams_explicit_regular_season():
    parsed = parse_query("Celtics record against playoff teams in the regular season")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "playoff teams"


def test_teams_that_made_playoffs_maps_to_playoff_teams_slot():
    parsed = parse_query("Celtics record against teams that made the playoffs")
    assert parsed["route"] == "team_record"
    assert parsed["opponent_quality"]["surface_term"] == "playoff teams"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"


def test_teams_that_qualified_for_playoffs_maps_to_playoff_teams_slot():
    parsed = parse_query("Celtics record against teams that qualified for the playoffs")
    assert parsed["route"] == "team_record"
    assert parsed["opponent_quality"]["surface_term"] == "playoff teams"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"


def test_player_summary_against_playoff_teams_this_season_stays_regular_season():
    parsed = parse_query("How has Jayson Tatum played against playoff teams this season?")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "playoff teams"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"


def test_actual_playoff_record_phrases_still_use_playoffs():
    parsed = parse_query("Celtics playoff record")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Playoffs"

    parsed = parse_query("Celtics record in the playoffs")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Playoffs"


def test_playoff_history_phrase_still_routes_to_playoff_history():
    parsed = parse_query("Lakers playoff history")
    assert parsed["route"] == "playoff_history"
    assert parsed["season_type"] == "Playoffs"


@pytest.mark.parametrize(
    ("query", "team_a", "team_b", "playoff_round"),
    [
        ("Heat Knicks playoff series record", "MIA", "NYK", None),
        ("Heat Knicks playoff history", "MIA", "NYK", None),
        ("Lakers Celtics playoff series record", "LAL", "BOS", None),
        ("Warriors Cavaliers Finals history", "GSW", "CLE", "04"),
    ],
)
def test_adjacent_playoff_team_phrasing_routes_to_matchup_history(
    query, team_a, team_b, playoff_round
):
    parsed = parse_query(query)
    assert parsed["route"] == "playoff_matchup_history"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["team_a"] == team_a
    assert parsed["team_b"] == team_b
    assert parsed["team"] is None
    assert parsed["route_kwargs"]["team_a"] == team_a
    assert parsed["route_kwargs"]["team_b"] == team_b
    assert parsed["route_kwargs"]["playoff_round"] == playoff_round


def test_explicit_vs_playoff_matchup_still_routes_to_matchup_history():
    parsed = parse_query("Heat vs Knicks playoff history")
    assert parsed["route"] == "playoff_matchup_history"
    assert parsed["team_a"] == "MIA"
    assert parsed["team_b"] == "NYK"


def test_single_team_playoff_series_record_vs_opponent_preserves_opponent_filter():
    parsed = parse_query("Lakers playoff series record vs Celtics")
    assert parsed["route"] == "playoff_history"
    assert parsed["team"] == "LAL"
    assert parsed["opponent"] == "BOS"
    assert parsed["team_a"] is None
    assert parsed["team_b"] is None


def test_adjacent_team_parsing_does_not_apply_without_playoff_context():
    parsed = parse_query("Heat Knicks record")
    assert parsed["team_a"] is None
    assert parsed["team_b"] is None
    assert parsed["route"] != "playoff_matchup_history"


@pytest.mark.parametrize(
    ("query", "team", "playoff_round"),
    [
        ("Bulls Finals record", "CHI", "04"),
        ("Warriors Finals record since 2015", "GSW", "04"),
        ("Celtics conference finals record", "BOS", "03"),
    ],
)
def test_single_team_playoff_round_records_are_unsupported_boundary(query, team, playoff_round):
    parsed = parse_query(query)
    assert parsed["route"] == "playoff_history"
    assert parsed["season_type"] == "Playoffs"
    assert parsed["team"] == team
    assert parsed["route_kwargs"]["team"] == team
    assert parsed["route_kwargs"]["playoff_round"] == playoff_round
    assert parsed["route_kwargs"]["unsupported_filters"] == ["single_team_playoff_round_record"]
    assert parsed["route"] != "team_record"
    assert any("single-team playoff round records" in note for note in parsed.get("notes", []))


def test_single_team_playoff_round_record_since_preserves_start_season():
    parsed = parse_query("Warriors Finals record since 2015")
    assert parsed["route_kwargs"]["start_season"] == "2015-16"
    assert parsed["route_kwargs"]["end_season"] == "2024-25"


def test_teams_over_point_five_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic against teams over .500")
    assert parsed["opponent_quality"]["surface_term"] == "teams over .500"
    assert parsed["opponent_quality"]["definition"]["operator"] == ">"


def test_top_ten_defenses_surface_form_sets_opponent_quality_slot():
    parsed = parse_query("Jokic against top-10 defenses")
    assert parsed["opponent_quality"]["surface_term"] == "top-10 defenses"
    assert parsed["opponent_quality"]["definition"]["metric"] == "def_rating_rank"


def test_top_defenses_shorthand_sets_top_ten_defenses_in_opponent_context():
    parsed = parse_query("Jokic against top defenses")
    assert parsed["opponent_quality"]["surface_term"] == "top-10 defenses"
    assert parsed["opponent_quality"]["definition"]["metric"] == "def_rating_rank"


def test_kd_ts_top_defenses_routes_to_summary_with_stat_and_quality():
    parsed = parse_query("KD TS% vs top defenses")
    assert parsed["route"] == "player_game_summary"
    assert parsed["player"] == "Kevin Durant"
    assert parsed["stat"] == "ts_pct"
    assert parsed["opponent_quality"]["surface_term"] == "top-10 defenses"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "top-10 defenses"


def test_kd_ts_top_10_defenses_still_preserves_quality():
    parsed = parse_query("KD TS% vs top 10 defenses")
    assert parsed["route"] == "player_game_summary"
    assert parsed["stat"] == "ts_pct"
    assert parsed["opponent_quality"]["surface_term"] == "top-10 defenses"


def test_top_defenses_without_opponent_context_does_not_set_opponent_quality():
    assert detect_opponent_quality("best defenses this season") is None
    assert detect_opponent_quality("top defenses this season") is None


def test_specific_opponent_does_not_set_opponent_quality():
    parsed = parse_query("Jokic vs Lakers")
    assert parsed["opponent_quality"] is None


def test_opponent_quality_definition_is_structured():
    parsed = parse_query("Jokic against contenders")
    definition = parsed["opponent_quality"]["definition"]
    assert definition["source"] == "standings_snapshots"
    assert definition["value"] == 6


# ---------------------------------------------------------------------------
# On/off query intent and routing
# ---------------------------------------------------------------------------


def test_jokic_on_off_routes_to_placeholder_route():
    parsed = parse_query("Jokic on/off")
    assert parsed["route"] == "player_on_off"
    assert parsed["intent"] == "on_off"
    assert parsed["lineup_members"] == ["Nikola Jokić"]
    assert parsed["presence_state"] == "both"


@pytest.mark.parametrize("query", ["Jokic on off", "Nikola Jokic on-off"])
def test_on_off_token_variants_route_to_placeholder_route(query):
    parsed = parse_query(query)
    assert parsed["route"] == "player_on_off"
    assert parsed["intent"] == "on_off"
    assert parsed["lineup_members"] == ["Nikola Jokić"]
    assert parsed["presence_state"] == "both"


def test_with_player_on_floor_sets_on_presence_state():
    parsed = parse_query("Nuggets with Jokic on the floor")
    assert parsed["route"] == "player_on_off"
    assert parsed["lineup_members"] == ["Nikola Jokić"]
    assert parsed["presence_state"] == "on"


def test_on_floor_versus_off_floor_routes_to_on_off_comparison():
    parsed = parse_query(
        "What is the Nuggets' net rating with Nikola Jokić on the floor versus off the floor?"
    )
    assert parsed["route"] == "player_on_off"
    assert parsed["intent"] == "on_off"
    assert parsed["team"] == "DEN"
    assert parsed["lineup_members"] == ["Nikola Jokić"]
    assert parsed["presence_state"] == "both"
    assert parsed["stat"] == "net_rating"


def test_without_player_on_floor_sets_off_presence_state():
    parsed = parse_query("Nuggets without Jokic on the floor")
    assert parsed["route"] == "player_on_off"
    assert parsed["lineup_members"] == ["Nikola Jokić"]
    assert parsed["presence_state"] == "off"


def test_player_on_court_sets_on_presence_state():
    parsed = parse_query("Jokic on court stats")
    assert parsed["route"] == "player_on_off"
    assert parsed["presence_state"] == "on"


def test_player_off_court_sets_off_presence_state():
    parsed = parse_query("Jokic off court stats")
    assert parsed["route"] == "player_on_off"
    assert parsed["presence_state"] == "off"


def test_player_sitting_sets_off_presence_state():
    parsed = parse_query("Jokic sitting")
    assert parsed["route"] == "player_on_off"
    assert parsed["presence_state"] == "off"


def test_on_off_query_does_not_set_without_player_absence_slot():
    parsed = parse_query("Nuggets without Jokic on the floor")
    assert parsed["without_player"] is None


def test_on_off_note_appended():
    parsed = parse_query("Jokic on/off")
    notes = parsed.get("notes", [])
    assert any("on_off" in n and "placeholder" in n for n in notes)


# ---------------------------------------------------------------------------
# Lineup query intent and routing
# ---------------------------------------------------------------------------


def test_best_five_man_lineups_route_to_leaderboard():
    parsed = parse_query("best 5-man lineups this season")
    assert parsed["route"] == "lineup_leaderboard"
    assert parsed["intent"] == "lineup"
    assert parsed["unit_size"] == 5


def test_three_man_units_capture_minimum_minutes():
    parsed = parse_query("3-man units with 200+ minutes")
    assert parsed["route"] == "lineup_leaderboard"
    assert parsed["unit_size"] == 3
    assert parsed["minute_minimum"] == 200


def test_two_man_combos_capture_unit_size():
    parsed = parse_query("top 2-man combos this season")
    assert parsed["route"] == "lineup_leaderboard"
    assert parsed["unit_size"] == 2


def test_lineup_with_two_players_routes_to_summary():
    parsed = parse_query("lineup with Tatum and Jaylen Brown")
    assert parsed["route"] == "lineup_summary"
    assert parsed["lineup_members"] == ["Jayson Tatum", "Jaylen Brown"]
    assert parsed["unit_size"] == 2


def test_together_phrase_routes_to_lineup_summary():
    parsed = parse_query("net rating with Tatum and Jaylen Brown together")
    assert parsed["route"] == "lineup_summary"
    assert parsed["lineup_members"] == ["Jayson Tatum", "Jaylen Brown"]


def test_lineup_parser_does_not_add_placeholder_note_after_source_backed_execution():
    parsed = parse_query("best 5-man lineups this season")
    notes = parsed.get("notes", [])
    assert not any("lineup" in n and "placeholder" in n for n in notes)


# ---------------------------------------------------------------------------
# Top single-game performance query intent and routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("most assists in a game this season", "ast"),
        ("most rebounds in a game this season", "reb"),
        ("single-game assist leaders this season", "ast"),
        ("highest assist games this season", "ast"),
        ("highest rebound games this season", "reb"),
        ("most rebounds by a player in a game this season", "reb"),
    ],
)
def test_non_scoring_single_game_top_performance_routes_to_top_player_games(query, stat):
    parsed = parse_query(query)
    assert parsed["route"] == "top_player_games"
    assert parsed["route_kwargs"]["stat"] == stat


@pytest.mark.parametrize(
    "query",
    [
        "assist leaders this season",
        "most assists this season",
        "Who leads the NBA in assists this season?",
    ],
)
def test_ordinary_assist_leaderboards_stay_season_leaders(query):
    parsed = parse_query(query)
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "ast"


# ---------------------------------------------------------------------------
# Stretch / rolling-window query intent and routing
# ---------------------------------------------------------------------------


def test_hottest_three_game_scoring_stretch_routes_to_stretch_leaderboard():
    parsed = parse_query("hottest 3-game scoring stretch this year")
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["intent"] == "leaderboard"
    assert parsed["window_size"] == 3
    assert parsed["stretch_metric"] == "pts"
    assert parsed["stretch_display_mode"] == "windows"
    assert parsed["route_kwargs"]["dedupe_players"] is False


def test_which_players_stretch_query_dedupes_to_best_player_windows():
    parsed = parse_query("which players have the hottest 3-game scoring stretch this year")
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["window_size"] == 3
    assert parsed["stretch_metric"] == "pts"
    assert parsed["stretch_display_mode"] == "players"
    assert parsed["route_kwargs"]["dedupe_players"] is True


def test_best_five_game_stretch_by_game_score_sets_metric_and_default_limit():
    parsed = parse_query("best 5-game stretch by Game Score")
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["window_size"] == 5
    assert parsed["stretch_metric"] == "game_score"
    assert parsed["route_kwargs"]["limit"] == 10


def test_most_efficient_rolling_stretch_defaults_to_true_shooting():
    parsed = parse_query("most efficient 10-game rolling stretch")
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["window_size"] == 10
    assert parsed["stretch_metric"] == "ts_pct"


def test_player_specific_stretch_query_preserves_subject():
    parsed = parse_query("Booker hottest 4-game scoring stretch")
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["player"] == "Devin Booker"
    assert parsed["window_size"] == 4
    assert parsed["stretch_display_mode"] == "named_player"


@pytest.mark.parametrize(
    "query",
    [
        "best 5-game team scoring stretch this season",
        "best team 5-game scoring stretch this season",
        "which teams have the best 5-game scoring stretch this season",
        "best 5-game scoring stretch by team",
        "best 5-game offensive stretch by a team",
    ],
)
def test_team_scoped_rolling_stretch_sets_unsupported_filter(query):
    parsed = parse_query(query)
    assert parsed["route"] == "player_stretch_leaderboard"
    assert parsed["route_kwargs"]["unsupported_filters"] == ["team_rolling_stretch"]
    assert any("team rolling-stretch" in note for note in parsed.get("notes", []))


@pytest.mark.parametrize(
    "query",
    [
        "Which players have the hottest 3-game scoring stretch this year?",
        "Jokic best 5-game rebounding stretch this season",
        "Booker hottest 4-game scoring stretch",
    ],
)
def test_player_rolling_stretch_queries_do_not_set_team_boundary(query):
    parsed = parse_query(query)
    assert parsed["route"] == "player_stretch_leaderboard"
    assert "unsupported_filters" not in parsed["route_kwargs"]
