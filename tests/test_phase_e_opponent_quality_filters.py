import pytest

from nbatools.commands.data_utils import resolve_opponent_quality_teams
from nbatools.commands.natural_query import parse_query
from nbatools.commands.player_game_summary import build_result as build_player_summary_result
from nbatools.commands.structured_results import NoResult
from nbatools.commands.team_record import build_team_record_result
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query


def test_opponent_quality_propagates_to_route_kwargs():
    parsed = parse_query("Jokic against contenders")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "contenders"


def test_top_ten_defenses_propagates_to_team_record_route_kwargs():
    parsed = parse_query("Lakers record against top-10 defenses")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "top-10 defenses"


def test_playoff_team_quality_phrases_propagate_without_playoff_season_type():
    parsed = parse_query("Celtics record against teams that made the playoffs")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "playoff teams"


@pytest.mark.parametrize(
    ("query", "expected_route"),
    [
        ("top scorers against contenders this season", "season_leaders"),
        (
            "players with most assists against playoff teams this season",
            "season_team_leaders",
        ),
    ],
)
def test_unsupported_opponent_quality_routes_fail_closed(query, expected_route):
    qr = execute_natural_query(query)

    assert qr.route == expected_route
    assert isinstance(qr.result, NoResult)
    assert qr.result_status == "no_result"
    assert qr.result_reason == "filter_not_supported"
    assert qr.metadata["unsupported_filters"] == ["opponent_quality"]
    assert any("opponent_quality" in note for note in qr.result.notes)


@pytest.mark.parametrize(
    ("query", "surface_term"),
    [
        ("Thunder record vs top 10 teams", "top 10 teams"),
        ("Celtics record vs top 5 teams", "top 5 teams"),
        ("Bucks record against losing teams", "losing teams"),
        ("Timberwolves record vs top seeded teams", "top seeded teams"),
        ("Suns record vs bad teams", "bad teams"),
        ("Knicks record against teams under .500", "teams under .500"),
        ("Lakers record against non-playoff teams", "non-playoff teams"),
    ],
)
def test_team_record_opponent_quality_phrases_propagate(query, surface_term):
    parsed = parse_query(query)

    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == surface_term


@pytest.mark.parametrize(
    ("query", "conference", "surface_term"),
    [
        ("Mavericks record against West playoff teams", "West", "playoff teams"),
        ("Mavericks record against Western Conference playoff teams", "West", "playoff teams"),
        ("Mavericks record against East top 10 teams", "East", "top 10 teams"),
    ],
)
def test_team_record_compound_conference_quality_phrases_propagate(query, conference, surface_term):
    parsed = parse_query(query)

    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["season_type"] == "Regular Season"
    assert parsed["route_kwargs"]["opponent_conference"] == conference
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == surface_term


@pytest.mark.needs_data
def test_natural_query_filters_player_summary_against_contenders():
    query = "Jokic against contenders 2024-25"
    parsed = parse_query(query)
    qr = execute_natural_query(query)

    assert qr.route == "player_game_summary"
    assert qr.is_ok

    resolved = resolve_opponent_quality_teams(
        parsed["opponent_quality"],
        ["2024-25"],
        "Regular Season",
    )
    expected = build_player_summary_result(
        season="2024-25",
        player=parsed["player"],
        opponent=resolved,
    )

    actual_games = int(qr.result.summary.iloc[0]["games"])
    filtered_games = int(expected.summary.iloc[0]["games"])
    baseline_games = int(
        build_player_summary_result(season="2024-25", player=parsed["player"]).summary.iloc[0][
            "games"
        ]
    )

    assert actual_games == filtered_games
    assert actual_games < baseline_games
    assert not any("opponent_quality" in note for note in qr.result.notes)
    quality_filters = [
        f for f in qr.metadata.get("applied_filters", []) if f.get("kind") == "quality"
    ]
    assert quality_filters == [
        {"label": "Opponent quality", "value": "contenders", "kind": "quality"}
    ]


@pytest.mark.needs_data
def test_natural_query_filters_team_record_against_top_ten_defenses():
    query = "Lakers record against top-10 defenses 2024-25"
    parsed = parse_query(query)
    qr = execute_natural_query(query)

    assert qr.route == "team_record"
    assert qr.is_ok

    resolved = resolve_opponent_quality_teams(
        parsed["opponent_quality"],
        ["2024-25"],
        "Regular Season",
    )
    expected = build_team_record_result(
        season="2024-25",
        team=parsed["team"],
        opponent=resolved,
    )

    actual_row = qr.result.summary.iloc[0]
    expected_row = expected.summary.iloc[0]
    baseline_games = int(
        build_team_record_result(season="2024-25", team=parsed["team"]).summary.iloc[0]["games"]
    )

    assert int(actual_row["games"]) == int(expected_row["games"])
    assert int(actual_row["wins"]) == int(expected_row["wins"])
    assert int(actual_row["losses"]) == int(expected_row["losses"])
    assert int(actual_row["games"]) < baseline_games
    assert not any("opponent_quality" in note for note in qr.result.notes)
    quality_filters = [
        f for f in qr.metadata.get("applied_filters", []) if f.get("kind") == "quality"
    ]
    assert quality_filters == [
        {"label": "Opponent quality", "value": "top-10 defenses", "kind": "quality"}
    ]


@pytest.mark.needs_data
@pytest.mark.parametrize(
    ("query", "surface_term", "games", "wins", "losses"),
    [
        ("Thunder record vs top 10 teams", "top 10 teams", 28, 18, 10),
        ("Celtics record vs top 5 teams", "top 5 teams", 10, 2, 8),
        ("Bucks record against losing teams", "losing teams", 28, 18, 10),
        ("Timberwolves record vs top seeded teams", "top seeded teams", 29, 14, 15),
        ("Suns record vs bad teams", "bad teams", 27, 23, 4),
        ("Lakers record against playoff teams", "playoff teams", 53, 27, 26),
        ("Nuggets record vs winning teams", "winning teams", 49, 29, 20),
        ("Knicks record against teams over .500", "teams over .500", 52, 29, 23),
    ],
)
def test_natural_query_filters_team_record_opponent_quality_samples(
    query, surface_term, games, wins, losses
):
    qr = execute_natural_query(query)

    assert qr.route == "team_record"
    assert qr.is_ok
    assert {
        "label": "Opponent quality",
        "value": surface_term,
        "kind": "quality",
    } in qr.metadata["applied_filters"]

    row = qr.result.summary.iloc[0]
    assert int(row["games"]) == games
    assert int(row["wins"]) == wins
    assert int(row["losses"]) == losses
    assert int(row["games"]) < 82


@pytest.mark.needs_data
def test_natural_query_intersects_team_record_conference_and_opponent_quality():
    query = "Mavericks record against West playoff teams"
    qr = execute_natural_query(query)

    assert qr.route == "team_record"
    assert qr.is_ok
    applied_filters = qr.metadata["applied_filters"]
    assert {
        "label": "Opponent conference",
        "value": "West",
        "kind": "conference",
    } in applied_filters
    assert {
        "label": "Opponent quality",
        "value": "playoff teams",
        "kind": "quality",
    } in applied_filters
    assert qr.metadata["opponent_team_abbrs"] == [
        "DEN",
        "GSW",
        "HOU",
        "LAC",
        "LAL",
        "MIN",
        "OKC",
        "PHX",
        "POR",
        "SAS",
    ]

    row = qr.result.summary.iloc[0]
    assert int(row["games"]) == 36
    assert int(row["wins"]) == 9
    assert int(row["losses"]) == 27
