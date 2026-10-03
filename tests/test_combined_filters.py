"""Combined filters: splits, summaries and records with several conditions.

"LeBron home/away splits in wins" picks the wins first and then splits them.
"Averages in games with 10+ rebounds and 5+ assists" keeps both conditions,
and "record when scoring 120 and allowing under 110" keeps both sides of the
score. Expected values come straight from the fixture's game CSVs, never from
the engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(kind: str, **match: str) -> list[dict[str, str]]:
    with (RAW / kind / "2025-26_regular_season.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows = [row for row in rows if all(row[key] == value for key, value in match.items())]
    return sorted(rows, key=lambda row: (row["game_date"], int(row["game_id"])), reverse=True)


def _lebron() -> list[dict[str, str]]:
    return _rows("player_game_stats", player_name="LeBron James")


def _lakers() -> list[dict[str, str]]:
    return _rows("team_game_stats", team_abbr="LAL")


def _home(row) -> bool:
    return row["is_home"] == "True"


def _won(row) -> bool:
    return row["wl"] == "W"


def _in_first_half_of_2026(row) -> bool:
    return "2026-01-01" <= row["game_date"] <= "2026-06-30"


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _buckets(result) -> dict[str, dict]:
    rows = result.result.to_dict()["sections"]["split_comparison"]
    return {row["bucket"]: row for row in rows}


def _assert_bucket(bucket: dict, rows: list[dict[str, str]]) -> None:
    assert bucket["games"] == len(rows)
    assert bucket["wins"] == sum(_won(row) for row in rows)
    assert bucket["losses"] == sum(not _won(row) for row in rows)
    assert bucket["pts_avg"] == pytest.approx(
        sum(int(row["pts"]) for row in rows) / len(rows), abs=1e-3
    )


def _assert_split(result, expected: dict[str, list[dict[str, str]]]) -> None:
    buckets = _buckets(result)
    assert set(buckets) == {name for name, rows in expected.items() if rows}
    for name, rows in expected.items():
        if rows:
            _assert_bucket(buckets[name], rows)


# -- splits apply every other filter before bucketing ------------------------


def test_home_away_split_uses_both_buckets():
    rows = _lebron()
    _assert_split(
        _run("LeBron home away splits"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_home_away_split_inside_wins():
    rows = [r for r in _lebron() if _won(r)]
    _assert_split(
        _run("LeBron home away split in wins"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_home_away_split_over_a_last_n_window():
    rows = _lebron()[:20]
    _assert_split(
        _run("LeBron home vs away splits last 20 games"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_home_away_split_when_scoring_30():
    rows = [r for r in _lebron() if int(r["pts"]) >= 30]
    _assert_split(
        _run("LeBron home away splits when scoring 30"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_home_away_split_with_two_stat_conditions():
    rows = [r for r in _lebron() if int(r["reb"]) >= 8 and int(r["ast"]) >= 8]
    _assert_split(
        _run("LeBron home away splits with 8+ rebounds and 8+ assists"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_wins_losses_split_inside_a_date_range():
    rows = [r for r in _lebron() if _in_first_half_of_2026(r)]
    _assert_split(
        _run("LeBron wins vs losses splits from January 1 2026 to June 30 2026"),
        {
            "wins": [r for r in rows if _won(r)],
            "losses": [r for r in rows if not _won(r)],
        },
    )


def test_team_home_away_split_over_a_last_n_window():
    rows = _lakers()[:10]
    _assert_split(
        _run("Lakers home vs away splits last 10 games"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


def test_team_wins_losses_split_on_the_road():
    rows = [r for r in _lakers() if not _home(r)]
    _assert_split(
        _run("Lakers road wins losses split"),
        {
            "wins": [r for r in rows if _won(r)],
            "losses": [r for r in rows if not _won(r)],
        },
    )


def test_team_wins_losses_split_at_home_inside_a_date_range():
    rows = [r for r in _lakers() if _home(r) and _in_first_half_of_2026(r)]
    _assert_split(
        _run("Lakers wins losses split at home from January 1 2026 to June 30 2026"),
        {
            "wins": [r for r in rows if _won(r)],
            "losses": [r for r in rows if not _won(r)],
        },
    )


def test_team_home_away_split_when_scoring_120():
    rows = [r for r in _lakers() if int(r["pts"]) >= 120]
    _assert_split(
        _run("Lakers home away splits when scoring 120"),
        {
            "home": [r for r in rows if _home(r)],
            "away": [r for r in rows if not _home(r)],
        },
    )


# -- summaries and records keep every stat condition --------------------------


def test_player_summary_keeps_both_stat_conditions():
    result = _run("LeBron averages in games with 10+ rebounds and 5+ assists")
    rows = [r for r in _lebron() if int(r["reb"]) >= 10 and int(r["ast"]) >= 5]

    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(rows)
    assert summary["pts_avg"] == pytest.approx(
        sum(int(r["pts"]) for r in rows) / len(rows), abs=1e-3
    )


def test_team_record_keeps_points_scored_and_allowed():
    result = _run("Lakers record when scoring 120 and allowing under 110")
    rows = [
        r for r in _lakers() if int(r["pts"]) >= 120 and int(r["pts"]) - int(r["plus_minus"]) < 110
    ]

    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(rows)
    assert summary["wins"] == sum(_won(r) for r in rows)
    assert summary["losses"] == sum(not _won(r) for r in rows)


# -- "scoring N" is a points threshold ---------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("when scoring 30", [("pts", 30.0)]),
        ("when scoring 25+ points", [("pts", 25.0)]),
        ("scoring 10 rebounds", [("reb", 10.0)]),
        ("when he scores 25+ points", [("pts", 25.0)]),
        ("drops 12 assists", [("ast", 12.0)]),
    ],
)
def test_scoring_n_is_a_threshold(text, expected):
    from nbatools.commands._parse_helpers import extract_threshold_conditions

    conditions = extract_threshold_conditions(text)
    assert [(c["stat"], c["min_value"]) for c in conditions] == expected


@pytest.mark.parametrize(
    "text",
    [
        "top scoring 5 games",
        "highest scoring 3 seasons",
        "scoring 30 games",
        "best scoring 10 players",
    ],
)
def test_scoring_n_is_not_a_threshold_when_it_counts_rows(text):
    from nbatools.commands._parse_helpers import extract_threshold_conditions

    assert extract_threshold_conditions(text) == []


# -- comparisons apply the same conditions to both sides ----------------------


def _compare_summary(result) -> list[dict]:
    return result.result.to_dict()["sections"]["summary"]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("LeBron vs Curry when scoring 30", lambda r: int(r["pts"]) >= 30),
        (
            "compare LeBron and Curry in games with 8+ rebounds and 5+ assists",
            lambda r: int(r["reb"]) >= 8 and int(r["ast"]) >= 5,
        ),
    ],
)
def test_player_comparison_applies_conditions_to_both_players(query, keep):
    result = _run(query)
    assert result.route == "player_compare"

    a, b = _compare_summary(result)
    for side, name in ((a, "LeBron James"), (b, "Stephen Curry")):
        rows = [r for r in _rows("player_game_stats", player_name=name) if keep(r)]
        assert side["games"] == len(rows)
        assert side["wins"] == sum(_won(r) for r in rows)


@pytest.mark.parametrize(
    ("query", "keep", "limit"),
    [
        ("Lakers vs Celtics when scoring 120", lambda r: int(r["pts"]) >= 120, None),
        (
            "compare Lakers and Celtics when scoring 120 and allowing under 110",
            lambda r: int(r["pts"]) >= 120 and int(r["pts"]) - int(r["plus_minus"]) < 110,
            None,
        ),
        ("compare the Lakers and the Celtics last 10 games", lambda r: True, 10),
    ],
)
def test_team_comparison_applies_conditions_to_both_teams(query, keep, limit):
    result = _run(query)
    assert result.route == "team_compare"

    a, b = _compare_summary(result)
    for side, abbr in ((a, "LAL"), (b, "BOS")):
        rows = [r for r in _rows("team_game_stats", team_abbr=abbr) if keep(r)][:limit]
        assert side["games"] == len(rows)
        assert side["wins"] == sum(_won(r) for r in rows)


def test_head_to_head_comparison_with_a_condition_is_not_answered_as_unfiltered():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron vs Curry head to head when scoring 30")
    assert result.result_status == "no_result"
    assert result.result_reason == "unsupported"


@pytest.mark.parametrize(
    "text",
    [
        "allowing under 110 2023-24",
        "allowing under 110 at home",
        "allowing under 110 points vs boston",
        "held opponents under 110 since march",
    ],
)
def test_points_allowed_threshold_ends_before_a_season_or_filter(text):
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions

    (condition,) = extract_opponent_points_allowed_conditions(text)
    assert condition["stat"] == "opponent_pts"
    assert condition["max_value"] < 110


def test_points_allowed_threshold_skips_other_stats():
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions

    assert extract_opponent_points_allowed_conditions("allowing under 110 rebounds") == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("games scoring 30 points and 5 assists", [("pts", 30.0), ("ast", 5.0)]),
        ("when scoring 120 and 30 assists", [("pts", 120.0), ("ast", 30.0)]),
        (
            "scores 30 points, 10 rebounds and 5 assists",
            [("pts", 30.0), ("reb", 10.0), ("ast", 5.0)],
        ),
    ],
)
def test_bare_stat_joined_to_a_scoring_verb_is_another_threshold(text, expected):
    from nbatools.commands._parse_helpers import extract_threshold_conditions

    conditions = extract_threshold_conditions(text)
    assert [(c["stat"], c["min_value"]) for c in conditions] == expected


def test_summary_keeps_a_bare_stat_joined_to_scoring():
    result = _run("Curry averages in games scoring 30 points and 5 assists")
    rows = [
        r
        for r in _rows("player_game_stats", player_name="Stephen Curry")
        if int(r["pts"]) >= 30 and int(r["ast"]) >= 5
    ]

    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(rows)
    assert summary["wins"] == sum(_won(r) for r in rows)


def test_team_record_keeps_a_bare_stat_joined_to_scoring():
    result = _run("Lakers record when scoring 120 and 30 assists")
    rows = [r for r in _lakers() if int(r["pts"]) >= 120 and int(r["ast"]) >= 30]

    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(rows)
