import pytest

from nbatools.commands.natural_query import parse_query

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


def test_multi_condition_player_query_parses_extra_conditions():
    parsed = parse_query("Jokic last 10 games over 25 points and over 10 rebounds")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["last_n"] == 10
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is not None
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 2
    assert len(parsed["extra_conditions"]) == 1
    assert parsed["extra_conditions"][0]["stat"] == "reb"
    assert parsed["extra_conditions"][0]["min_value"] is not None


def test_multi_condition_team_query_parses_extra_conditions():
    parsed = parse_query("Celtics wins vs Bucks over 120 points and over 15 threes")
    assert parsed["team"] == "BOS"
    assert parsed["opponent"] == "MIL"
    assert parsed["wins_only"] is True
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["route"] == "game_finder"
    assert len(parsed["threshold_conditions"]) == 2
    assert len(parsed["extra_conditions"]) == 1
    assert parsed["extra_conditions"][0]["stat"] == "fg3m"


def test_under_query_parses_max_value_for_player():
    parsed = parse_query("Jokic under 20 points")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["season"] == "2025-26"
    assert parsed["stat"] == "pts"
    assert parsed["min_value"] is None
    assert parsed["max_value"] is not None
    assert parsed["route"] == "player_game_finder"
    assert len(parsed["threshold_conditions"]) == 1


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
    assert len(parsed["extra_conditions"]) == 1
    assert parsed["extra_conditions"][0]["stat"] == "reb"
    assert parsed["extra_conditions"][0]["min_value"] is None
    assert parsed["extra_conditions"][0]["max_value"] is not None


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


def test_quarter_note_appended():
    parsed = parse_query("LeBron 4th quarter scoring")
    notes = parsed.get("notes", [])
    assert any("quarter" in n and "unfiltered" in n for n in notes)


def test_half_note_appended():
    parsed = parse_query("Celtics first half stats")
    notes = parsed.get("notes", [])
    assert any("half" in n and "unfiltered" in n for n in notes)
