"""C2: "best three point shooters", "best free throw shooters".

"best three point shooters" ranked points (and refused as unclear), "best 3pt
shooters" / "best free throw shooters" had no metric, and "Lakers best three
point shooters" fell to a game list. The shooting percentage is ranked, with
the board's attempt floor; a bare "best shooters" stays unread (3P%, FG% and
TS% are all fair readings).
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("best three point shooters", "fg3_pct"),
        ("best 3pt shooters", "fg3_pct"),
        ("best 3 point shooters this season", "fg3_pct"),
        ("best free throw shooters", "ft_pct"),
        ("best ft shooters in 2024-25", "ft_pct"),
    ],
)
def test_shooters_rank_the_shooting_percentage(query, stat):
    parsed = parse_query(query)
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == stat
    assert not parsed["route_kwargs"].get("unsupported_filters")
    rows = execute_natural_query(query).result.to_dict()["sections"]["leaderboard"]
    values = [row[stat] for row in rows]
    assert values == sorted(values, reverse=True)


@pytest.mark.parametrize(
    ("query", "stat", "descending"),
    [
        ("Lakers best three point shooters", "fg3_pct", True),
        ("best three point shooters on the Lakers", "fg3_pct", True),
        ("Lakers best 3 point percentage", "fg3_pct", True),
        ("Celtics best free throw shooters", "ft_pct", True),
        ("Lakers worst free throw shooters", "ft_pct", False),
    ],
)
def test_team_shooters_rank_the_teams_players(query, stat, descending):
    parsed = parse_query(query)
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == stat
    rows = execute_natural_query(query).result.to_dict()["sections"]["leaderboard"]
    team = parsed["route_kwargs"]["team"]
    assert rows and all(row["team_abbr"] == team for row in rows)
    values = [row[stat] for row in rows]
    assert values == sorted(values, reverse=descending)


def test_bare_best_shooters_is_not_guessed():
    try:
        parsed = parse_query("best shooters")
    except ValueError:
        return
    assert parsed["route_kwargs"].get("stat") not in ("fg3_pct", "ft_pct", "pts")
