import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.parser


def _assert_route_kwargs(parsed: dict, expected: dict) -> None:
    route_kwargs = parsed["route_kwargs"]
    for key, value in expected.items():
        assert route_kwargs.get(key) == value


def _assert_no_unsupported_filters(parsed: dict) -> None:
    assert "unsupported_filters" not in parsed["route_kwargs"]


@pytest.mark.parametrize(
    "case",
    [
        {
            "query": "Celtics record against the East this season",
            "route": "team_record",
            "fields": {
                "team": "BOS",
                "opponent_conference": "East",
                "opponent_conference_geography_boundary": False,
            },
            "route_kwargs": {"team": "BOS", "opponent_conference": "East"},
            "no_unsupported_filters": True,
        },
        {
            "query": "Celtics conference finals record",
            "route": "playoff_history",
            "fields": {"team": "BOS", "season_type": "Playoffs"},
            "route_kwargs": {
                "team": "BOS",
                "playoff_round": "03",
                "unsupported_filters": ["single_team_playoff_round_record"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "Celtics record against east coast teams",
            "route": "team_record",
            "fields": {
                "team": "BOS",
                "opponent_conference": None,
                "opponent_conference_geography_boundary": True,
            },
            "route_kwargs": {
                "team": "BOS",
                "unsupported_filters": ["opponent_conference"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "Celtics record vs Atlantic Division",
            "route": "team_record",
            "fields": {
                "team": "BOS",
                "opponent_conference": None,
                "opponent_division": "Atlantic",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "BOS",
                "opponent_division": "Atlantic",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "Lakers record against Pacific Division",
            "route": "team_record",
            "fields": {
                "team": "LAL",
                "opponent_division": "Pacific",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "LAL",
                "opponent_division": "Pacific",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "Knicks record vs Central Division",
            "route": "team_record",
            "fields": {
                "team": "NYK",
                "opponent_division": "Central",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "NYK",
                "opponent_division": "Central",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "record against Northwest Division teams",
            "route": "team_record_leaderboard",
            "fields": {
                "team": None,
                "opponent_conference": None,
                "opponent_division": "Northwest",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "opponent_division": "Northwest",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "team records vs Pacific Division",
            "route": "team_record_leaderboard",
            "fields": {
                "team": None,
                "opponent_division": "Pacific",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "opponent_division": "Pacific",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "Lakers record against Western Conference Pacific Division teams",
            "route": "team_record",
            "fields": {
                "team": "LAL",
                "opponent_conference": None,
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "LAL",
                "unsupported_filters": ["opponent_division"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "Celtics conference finals record vs Atlantic Division",
            "route": "playoff_history",
            "fields": {
                "team": "BOS",
                "season_type": "Playoffs",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "BOS",
                "playoff_round": "03",
                "unsupported_filters": ["single_team_playoff_round_record"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "Celtics playoff record vs Atlantic Division",
            "route": "team_record",
            "fields": {
                "team": "BOS",
                "season_type": "Playoffs",
                "opponent_division_boundary": True,
            },
            "route_kwargs": {
                "team": "BOS",
                "season_type": "Playoffs",
                "unsupported_filters": ["opponent_division"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "most conference finals appearances",
            "route": "playoff_appearances",
            "fields": {"season_type": "Playoffs"},
            "route_kwargs": {"playoff_round": "03"},
            "no_unsupported_filters": True,
        },
        {
            "query": "Lakers record since 2010",
            "route": "team_record",
            "fields": {"team": "LAL", "start_season": "2010-11"},
            "route_kwargs": {"team": "LAL", "start_season": "2010-11"},
            "no_unsupported_filters": True,
        },
        {
            "query": "Warriors vs Lakers record this season",
            "route": "team_matchup_record",
            "fields": {"team_a": "GSW", "team_b": "LAL"},
            "route_kwargs": {"team_a": "GSW", "team_b": "LAL"},
            "no_unsupported_filters": True,
        },
        {
            "query": "Celtics vs Bucks comparison this season",
            "route": "team_compare",
            "fields": {"team_a": "BOS", "team_b": "MIL"},
            "route_kwargs": {"team_a": "BOS", "team_b": "MIL", "head_to_head": False},
            "no_unsupported_filters": True,
        },
        {
            "query": "LeBron James vs Kevin Durant comparison",
            "route": "player_compare",
            "fields": {"player_a": "LeBron James", "player_b": "Kevin Durant"},
            "route_kwargs": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "head_to_head": False,
            },
            "absent_fields": ["opponent_player"],
            "no_unsupported_filters": True,
        },
        {
            "query": "LeBron vs KD",
            "route": "player_compare",
            "fields": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "bare_player_vs_player": True,
            },
            "route_kwargs": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "head_to_head": False,
                "ambiguous_intent": "bare_player_vs_player",
            },
            "absent_fields": ["opponent_player"],
            "no_unsupported_filters": True,
        },
        {
            "query": "LeBron James vs Kevin Durant",
            "route": "player_compare",
            "fields": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "bare_player_vs_player": True,
            },
            "route_kwargs": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "head_to_head": False,
                "ambiguous_intent": "bare_player_vs_player",
            },
            "absent_fields": ["opponent_player"],
            "no_unsupported_filters": True,
        },
        {
            "query": "Jokic vs Embiid",
            "route": "player_compare",
            "fields": {
                "player_a": "Nikola Jokić",
                "player_b": "Joel Embiid",
                "bare_player_vs_player": True,
            },
            "route_kwargs": {
                "player_a": "Nikola Jokić",
                "player_b": "Joel Embiid",
                "head_to_head": False,
                "ambiguous_intent": "bare_player_vs_player",
            },
            "absent_fields": ["opponent_player"],
            "no_unsupported_filters": True,
        },
        {
            "query": "How do LeBron James and Kevin Durant compare this season?",
            "route": "player_compare",
            "fields": {
                "player": None,
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "season": "2025-26",
            },
            "route_kwargs": {
                "player_a": "LeBron James",
                "player_b": "Kevin Durant",
                "season": "2025-26",
                "head_to_head": False,
            },
            "absent_fields": ["opponent_player"],
            "no_unsupported_filters": True,
        },
        {
            "query": "LeBron stats vs Kevin Durant",
            "route": "player_game_finder",
            "fields": {"player": "LeBron James", "opponent_player": "Kevin Durant"},
            "route_kwargs": {
                "player": "LeBron James",
                "opponent_player": "Kevin Durant",
            },
            "absent_fields": ["player_a", "player_b"],
            "no_unsupported_filters": True,
        },
        {
            "query": "Jokic game log vs Embiid",
            "route": "player_game_finder",
            "fields": {"player": "Nikola Jokić", "opponent_player": "Joel Embiid"},
            "route_kwargs": {
                "player": "Nikola Jokić",
                "opponent_player": "Joel Embiid",
            },
            "absent_fields": ["player_a", "player_b"],
            "no_unsupported_filters": True,
        },
        {
            "query": "What were the most assists in a game this season?",
            "route": "top_player_games",
            "fields": {"stat": "ast"},
            "route_kwargs": {"stat": "ast"},
            "note_contains": "season_high",
            "no_unsupported_filters": True,
        },
        {
            "query": "Who leads the NBA in assists this season?",
            "route": "season_leaders",
            "fields": {"stat": "ast"},
            "route_kwargs": {"stat": "ast"},
            "note_not_contains": "season_high",
            "no_unsupported_filters": True,
        },
        {
            "query": "Nuggets net rating with Nikola Jokic on the floor versus off the floor",
            "route": "player_on_off",
            "fields": {
                "team": "DEN",
                "lineup_members": ["Nikola Jokić"],
                "presence_state": "both",
                "stat": "net_rating",
                "without_player": None,
            },
            "route_kwargs": {
                "team": "DEN",
                "lineup_members": ["Nikola Jokić"],
                "presence_state": "both",
            },
            "note_contains": "on_off",
            "no_unsupported_filters": True,
        },
        {
            "query": "Lakers record without LeBron",
            "route": "team_record",
            "fields": {"team": "LAL", "without_player": "LeBron James"},
            "route_kwargs": {"team": "LAL", "without_player": "LeBron James"},
            "no_unsupported_filters": True,
        },
        {
            "query": "best 5-game team scoring stretch this season",
            "route": "player_stretch_leaderboard",
            "fields": {"window_size": 5, "stretch_metric": "pts"},
            "route_kwargs": {
                "window_size": 5,
                "stretch_metric": "pts",
                "unsupported_filters": ["team_rolling_stretch"],
            },
            "note_contains": "unsupported_boundary",
        },
        {
            "query": "Jokic best 5-game rebounding stretch this season",
            "route": "player_stretch_leaderboard",
            "fields": {
                "player": "Nikola Jokić",
                "window_size": 5,
                "stretch_metric": "reb",
            },
            "route_kwargs": {
                "player": "Nikola Jokić",
                "window_size": 5,
                "stretch_metric": "reb",
            },
            "no_unsupported_filters": True,
        },
        {
            "query": "Warriors net rating this season",
            "route": "season_team_leaders",
            "fields": {"team": "GSW", "stat": "net_rating"},
            "route_kwargs": {
                "stat": "net_rating",
                "limit": 30,
            },
            "note_contains": "single_team_advanced_stat",
        },
        {
            "query": "best net rating teams this season",
            "route": "season_team_leaders",
            "fields": {"stat": "net_rating"},
            "route_kwargs": {"stat": "net_rating"},
            "no_unsupported_filters": True,
        },
    ],
    ids=lambda case: case["query"],
)
def test_route_priority_collision_snapshot(case):
    parsed = parse_query(case["query"])

    assert parsed["route"] == case["route"]
    for key, value in case.get("fields", {}).items():
        assert parsed.get(key) == value
    for key in case.get("absent_fields", []):
        assert parsed.get(key) is None

    _assert_route_kwargs(parsed, case.get("route_kwargs", {}))
    if case.get("no_unsupported_filters"):
        _assert_no_unsupported_filters(parsed)

    notes = parsed.get("notes", [])
    if note_substring := case.get("note_contains"):
        assert any(note_substring in note for note in notes)
    if note_substring := case.get("note_not_contains"):
        assert not any(note_substring in note for note in notes)
