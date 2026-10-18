"""Discriminating ranking fixtures; synthetic rows are never NBA evidence."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands import player_game_finder, player_occurrence_leaders, season_leaders
from nbatools.data_source import reset_data_source_cache
from tests.test_leaderboard_filter_contracts import _make_player_game_rows

pytestmark = [pytest.mark.fixture_data, pytest.mark.engine]
SEASON = "2023-24"


def stage(tmp_path, monkeypatch, players):
    """Reuse an established complete box-score fixture schema with explicit cases."""
    template = _make_player_game_rows()[0]
    rows = []
    for ident, (name, games) in enumerate(players.items(), start=1):
        for day, changes in enumerate(games, start=1):
            rows.append(
                dict(
                    template,
                    player_id=ident,
                    player_name=name,
                    game_id=ident * 100 + day,
                    game_date=f"2024-01-{day:02d}",
                    season=SEASON,
                    team_name="Fixture Team",
                    opponent_team_name="Fixture Opponent",
                    **changes,
                )
            )
    destination = tmp_path / "data/raw/player_game_stats" / f"{SEASON}_regular_season.csv"
    destination.parent.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(destination, index=False)
    teams = destination.parent.parent / "team_game_stats" / destination.name
    teams.parent.mkdir()
    pd.DataFrame(
        [
            {"game_id": r["game_id"], "team_id": r["team_id"], "wl": "W", "plus_minus": 1}
            for r in rows
        ]
    ).to_csv(teams, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()


def records(result, section="leaderboard"):
    return result.to_dict()["sections"][section]


def test_total_and_per_game_can_reverse_rank(tmp_path, monkeypatch):
    # Alpha 80/2 =40; Beta 90/3 =30. Same raw rows, distinct requested basis.
    stage(
        tmp_path,
        monkeypatch,
        {"Alpha Example": [{"pts": 40}] * 2, "Beta Example": [{"pts": 30}] * 3},
    )
    total = records(
        season_leaders.build_result(season=SEASON, stat="pts_total", min_games=1, limit=2)
    )
    average = records(season_leaders.build_result(season=SEASON, stat="pts", min_games=1, limit=2))
    assert [(r["player_name"], r["pts_total"], r["games_played"]) for r in total] == [
        ("Beta Example", 90, 3),
        ("Alpha Example", 80, 2),
    ]
    assert [(r["player_name"], r["pts_per_game"], r["games_played"]) for r in average] == [
        ("Alpha Example", 40, 2),
        ("Beta Example", 30, 3),
    ]


@pytest.mark.parametrize(
    "made,attempts,stat", [("fg3m", "fg3a", "fg3_pct"), ("ftm", "fta", "ft_pct")]
)
def test_rates_use_total_ratio_and_inclusive_attempt_floor(
    tmp_path, monkeypatch, made, attempts, stat
):
    # Alpha's unweighted game mean .5 wrongly beats Beta .4; actual ratio .1
    # loses. Charlie .888... has only9attempts and is below explicit10floor.
    stage(
        tmp_path,
        monkeypatch,
        {
            "Alpha Example": [{made: 1, attempts: 1}, {made: 0, attempts: 9}],
            "Beta Example": [{made: 2, attempts: 5}, {made: 2, attempts: 5}],
            "Charlie Example": [{made: 8, attempts: 9}],
        },
    )
    result = season_leaders.build_result(
        season=SEASON, stat=stat, min_games=1, min_attempts=10, limit=3
    )
    rows = records(result)
    assert [r["player_name"] for r in rows] == ["Beta Example", "Alpha Example"]
    assert [r[stat] for r in rows] == pytest.approx([0.4, 0.1])
    assert [r[attempts + "_total"] for r in rows] == [10, 10]
    assert any("at least 10" in str(c) for c in result.to_dict()["caveats"])


def test_event_ties_use_games_then_name_and_exact_limit(tmp_path, monkeypatch):
    # Every player has2events. More total appearances ranks first, then name;
    # exactN means truncation at2 and sequential display positions1/2.
    stage(
        tmp_path,
        monkeypatch,
        {
            "Charlie Example": [{"pts": 40}, {"pts": 41}, {"pts": 0}],
            "Beta Example": [{"pts": 40}, {"pts": 41}, {"pts": 0}, {"pts": 0}],
            "Alpha Example": [{"pts": 40}, {"pts": 41}, {"pts": 0}],
        },
    )
    result = player_occurrence_leaders.build_result(
        season=SEASON, stat="pts", min_value=40, min_games=1, limit=2
    )
    rows = records(result)
    assert [(r["rank"], r["player_name"], r["games_played"]) for r in rows] == [
        (1, "Beta Example", 4),
        (2, "Alpha Example", 3),
    ]
    event = next(k for k in rows[0] if k.startswith("games_pts_"))
    assert [r[event] for r in rows] == [2, 2]


def test_named_player_top_games_and_last_games_are_distinct_samples(tmp_path, monkeypatch):
    stage(tmp_path, monkeypatch, {"Alpha Example": [{"pts": 50}, {"pts": 50}, {"pts": 10}]})
    top = records(
        player_game_finder.build_result(
            season=SEASON, player="Alpha Example", stat="pts", sort_by="stat", limit=2
        ),
        "finder",
    )
    last = records(
        player_game_finder.build_result(season=SEASON, player="Alpha Example", last_n=2, limit=2),
        "finder",
    )
    assert [(int(r["game_id"]), r["pts"]) for r in top] == [(102, 50), (101, 50)]
    assert [(int(r["game_id"]), r["pts"]) for r in last] == [(103, 10), (102, 50)]


@pytest.mark.parametrize(
    "qualifier", ["at least 40 appearances", "40 or more games played", "minimum of 40 games"]
)
def test_eligibility_span_is_not_a_second_ranking_metric(qualifier):
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(f"Top 5 players by total points in 2023-24 with {qualifier}")
    assert parsed["route"] == "season_leaders"
    kwargs = parsed["route_kwargs"]
    assert not kwargs.get("unsupported_filters")
    assert kwargs["min_games"] == 40
    assert kwargs["stat"] == "pts_total"
    assert kwargs["limit"] == 5


@pytest.mark.parametrize(
    "verb,stat", [("scoring", "points"), ("grabbing", "rebounds"), ("dishing", "assists")]
)
def test_ranked_event_floor_preserves_inclusive_zero(verb, stat):
    from nbatools.commands._occurrence_route_utils import extract_occurrence_event

    event = extract_occurrence_event(f"largest counts of games {verb} at least 0 {stat}")
    assert event["min_value"] == 0
    assert event.get("max_value") is None


def test_games_played_metric_is_not_erased_without_an_eligibility_floor():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query("Top 5 players by games played in 2023-24")
    assert parsed["route_kwargs"]["stat"] == "games_played"
    assert not parsed["route_kwargs"].get("unsupported_filters")


def test_rank_by_frequency_keeps_a_board_instead_of_counting_the_board():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(
        "Rank the first 3 players by how often they recorded at least 8 assists and zero turnovers in 2023-24."
    )
    assert parsed["route"] == "player_occurrence_leaders"
    assert parsed["count_intent"] is False
    assert parsed["route_kwargs"]["limit"] == 3
    assert parsed["route_kwargs"]["conditions"] == [
        {"stat": "ast", "min_value": 8, "max_value": None},
        {"stat": "tov", "min_value": None, "max_value": 0},
    ]


@pytest.mark.parametrize(
    "query,stat,minimum,limit",
    [
        (
            "For 2023-24, rank the leading 4 scorers by points per game, requiring 50 games played.",
            "pts",
            50,
            4,
        ),
        (
            "Among players who appeared in at least 50 games in 2023-24, which 4 accumulated the most points?",
            "pts_total",
            50,
            4,
        ),
        ("Rank 4 players by points per game in 2023-24 with at least 4 games played.", "pts", 4, 4),
    ],
)
def test_rank_population_and_eligibility_keep_separate_numbers(query, stat, minimum, limit):
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(query)
    assert parsed["route"] == "season_leaders"
    kwargs = parsed["route_kwargs"]
    assert not kwargs.get("unsupported_filters")
    assert (kwargs["stat"], kwargs["min_games"], kwargs["limit"]) == (stat, minimum, limit)


def test_explicit_player_population_beats_generic_team_shooting_alias():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(
        "With at least 250 three-point attempts in 2023-24, rank 3 players by three-point shooting percentage."
    )
    assert parsed["route"] == "season_leaders"
    kwargs = parsed["route_kwargs"]
    assert not kwargs.get("unsupported_filters")
    assert (kwargs["stat"], kwargs["attempt_stat"], kwargs["min_attempts"], kwargs["limit"]) == (
        "fg3_pct",
        "fg3a",
        250,
        3,
    )
