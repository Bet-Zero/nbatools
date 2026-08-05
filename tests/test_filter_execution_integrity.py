"""Every displayed filter badge must correspond to filtering that actually ran.

These tests exist because the rest of the suite asserts on *parser* output --
"did we detect the word 'guards'" -- which passes just as happily when the route
receiving that filter has no code to apply it. That blind spot shipped several
filters that were detected, badged as applied, and then silently ignored:
position groups outside season_leaders, last-N windows on the record family,
and triple-double filters on team records.

The invariant here is deliberately behavioural rather than structural, so it
keeps holding as routes are added: for a query carrying a filter, the engine
must either refuse it honestly, or return data that actually differs from the
same query without the filter. Returning the unfiltered answer while showing a
badge is the one outcome that is never acceptable.
"""

from __future__ import annotations

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data, pytest.mark.slow]


def _fingerprint(result) -> str:
    """Stable fingerprint of the data a query actually returned."""
    if result is None:
        return "NONE"
    parts: list[str] = []
    for attr in ("games", "leaders", "streaks", "summary", "splits", "comparison"):
        frame = getattr(result, attr, None)
        if frame is None or not hasattr(frame, "to_csv"):
            continue
        parts.append(f"{attr}:{frame.shape}:{frame.to_csv(index=False)}")
    return "||".join(parts) or f"type={type(result).__name__}"


def _run(query: str):
    executed = execute_natural_query(query)
    metadata = executed.metadata or {}
    badges = [
        (badge.get("label"), str(badge.get("value")))
        for badge in (metadata.get("applied_filters") or [])
    ]
    return executed, badges, _fingerprint(executed.result)


# (filtered query, unfiltered control, badge label the filter would display)
FILTER_PAIRS = [
    # position groups: only season_leaders applies `position`
    (
        "best 10 game stretch by guards in 2023-24",
        "best 10 game stretch in 2023-24",
        "Position",
    ),
    ("most triple doubles among centers in 2023-24", "most triple doubles in 2023-24", "Position"),
    ("highest scoring games by guards in 2023-24", "highest scoring games in 2023-24", "Position"),
    ("Lakers record by guards in 2023-24", "Lakers record in 2023-24", "Position"),
    (
        "team points leaders among centers in 2023-24",
        "team points leaders in 2023-24",
        "Position",
    ),
    # last-N windows: the record / decade / playoff family has no last_n parameter
    ("Lakers record last 10 games in 2023-24", "Lakers record in 2023-24", "Last N games"),
    ("Lakers vs Celtics record last 10 games", "Lakers vs Celtics record", "Last N games"),
    ("best record last 10 games in 2023-24", "best record in 2023-24", "Last N games"),
    ("Lakers playoff history last 5 games", "Lakers playoff history", "Last N games"),
    ("Lakers record by decade last 10 games", "Lakers record by decade", "Last N games"),
    (
        "which team had the most 120 point games in the last 10 games in 2023-24",
        "which team had the most 120 point games in 2023-24",
        "Last N games",
    ),
    # triple-double / double-double filters outside the routes that count them
    ("Lakers record in triple doubles in 2023-24", "Lakers record in 2023-24", "Special Event"),
    (
        "Jokic home vs away splits for triple doubles in 2023-24",
        "Jokic home vs away splits in 2023-24",
        "Special Event",
    ),
    ("team triple double leaders in 2023-24", "team points leaders in 2023-24", "Special Event"),
    # whole-game teammate availability outside team records
    (
        "Jokic averages with Jamal Murray in 2023-24",
        "Jokic averages in 2023-24",
        "With player",
    ),
]


@pytest.mark.parametrize(("filtered_query", "control_query", "badge_label"), FILTER_PAIRS)
def test_filter_either_changes_the_answer_or_is_refused(
    filtered_query: str, control_query: str, badge_label: str
) -> None:
    filtered, badges, filtered_fingerprint = _run(filtered_query)
    _control, _control_badges, control_fingerprint = _run(control_query)

    if filtered.result_status == "no_result":
        # Honest refusal: the engine must not also advertise the filter as applied.
        assert not any(label == badge_label for label, _ in badges), (
            f"{filtered_query!r} refused but still displays a {badge_label!r} badge"
        )
        return

    assert filtered_fingerprint != control_fingerprint, (
        f"{filtered_query!r} returned byte-identical data to the unfiltered control "
        f"{control_query!r} while displaying badges {badges}. The filter was detected "
        f"but never executed."
    )


def test_position_filter_actually_restricts_the_leaderboard() -> None:
    """The route that does support positions must really apply them."""
    executed, _badges, _fp = _run("which centers have the most rebounds in 2023-24")

    assert executed.result_status == "ok"
    names = set(executed.result.leaders["player_name"])
    # Guards must not appear on a centers-only board.
    assert not names & {"Luka Dončić", "James Harden", "Josh Giddey", "Trae Young"}


@pytest.mark.parametrize(
    "query",
    [
        "Jokic longest triple-double streak",
        "most triple doubles in 2023-24",
        "Jokic triple doubles in 2023-24",
    ],
)
def test_routes_that_do_consume_special_events_are_not_blocked(query: str) -> None:
    """Gating an unexecuted filter must not block the routes that execute it.

    Triple-double support is reached three different ways (special_event kwarg,
    occurrence counting, and special_condition on the streak finders); a gate
    that only knows one of them silently breaks the others.
    """
    executed, _badges, _fp = _run(query)

    assert executed.result_status == "ok", f"{query!r} was refused but is a supported query"


def test_explicit_month_year_uses_the_requested_year() -> None:
    """An explicit calendar year must win over the current-season default."""
    executed, badges, _fp = _run("Lakers record in January 2024")

    assert executed.result_status == "ok"
    assert ("Date range", "2024-01-01 – 2024-01-31") in badges
    assert (executed.metadata or {}).get("season") == "2023-24"


def test_month_year_queries_for_different_years_differ() -> None:
    _executed_a, _badges_a, january_2024 = _run("Lakers record in January 2024")
    _executed_b, _badges_b, january_2023 = _run("Lakers record in January 2023")

    assert january_2024 != january_2023


def test_games_played_minimum_is_not_read_as_a_stat_threshold() -> None:
    """'at least 50 games' is a sample-size floor, not a 50-point cutoff."""
    executed, badges, _fp = _run("points leaders with at least 50 games in 2023-24")

    assert executed.result_status == "ok"
    assert not any(label == "pts min" for label, _ in badges)

    leaders = executed.result.leaders
    assert (leaders["games_played"] >= 50).all()
    # ...and it must still be a leaderboard: descending, not the bottom of the league.
    assert leaders["pts_per_game"].iloc[0] > 25


def test_at_least_does_not_flip_leaderboard_sort() -> None:
    """The 'least' inside 'at least' must not turn a leaderboard upside down."""
    executed, _badges, _fp = _run("points leaders with at least 50 games in 2023-24")
    points = executed.result.leaders["pts_per_game"].tolist()

    assert points == sorted(points, reverse=True)


def test_explicit_ascending_language_still_sorts_ascending() -> None:
    executed, _badges, _fp = _run("fewest turnovers in 2023-24")
    turnovers = executed.result.leaders["tov_per_game"].tolist()

    assert turnovers == sorted(turnovers)
