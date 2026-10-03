"""Last-N game samples: time windows, qualifying games and meetings.

"How many 30 point games in his last 10 games" takes the 10 most recent games
and counts the 30 point games among them (window). "His last 5 games where he
scored 30" keeps the 30 point games and returns the 5 most recent of them
(qualifying). Opponent, home/away and teammate availability always choose the
games in play first, so "last 3 meetings with the Warriors" is the last 3
games against Golden State. Expected values come straight from the fixture's
game CSVs, never from the engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(
    kind: str,
    *,
    player: str | None = None,
    team: str | None = None,
    opponent: str | None = None,
    season: str = "2025-26",
) -> list[dict[str, str]]:
    with (RAW / kind / f"{season}_regular_season.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if player:
        rows = [row for row in rows if row["player_name"] == player]
    if team:
        rows = [row for row in rows if row["team_abbr"] == team]
    if opponent:
        rows = [row for row in rows if row["opponent_team_abbr"] == opponent]
    return sorted(rows, key=lambda row: (row["game_date"], int(row["game_id"])), reverse=True)


def _player(name: str, **kwargs) -> list[dict[str, str]]:
    return _rows("player_game_stats", player=name, **kwargs)


def _team(abbr: str, **kwargs) -> list[dict[str, str]]:
    return _rows("team_game_stats", team=abbr, **kwargs)


def _ids(rows) -> list[int]:
    return sorted(int(row["game_id"]) for row in rows)


def _triple_double(row: dict[str, str]) -> bool:
    return sum(float(row[stat]) >= 10 for stat in ("pts", "reb", "ast", "stl", "blk")) >= 3


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _game_ids(result) -> list[int]:
    sections = result.result.to_dict()["sections"]
    rows = sections.get("finder") or sections.get("game_log") or []
    return sorted(int(row["game_id"]) for row in rows)


def _count(result) -> int:
    (row,) = result.result.to_dict()["sections"]["count"]
    return row["count"]


# -- window: conditions are measured inside the N most recent games --------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "how many times has LeBron scored 30 in his last 10 games",
            lambda: [r for r in _player("LeBron James")[:10] if int(r["pts"]) >= 30],
        ),
        (
            "how many of his last 10 games did LeBron score 25",
            lambda: [r for r in _player("LeBron James")[:10] if int(r["pts"]) >= 25],
        ),
        (
            "how many triple doubles has Jokic had in his last 20 games",
            lambda: [r for r in _player("Nikola Jokić")[:20] if _triple_double(r)],
        ),
        (
            "how many times have the Lakers scored 120 in their last 10 games",
            lambda: [r for r in _team("LAL")[:10] if int(r["pts"]) >= 120],
        ),
        (
            "how many times has Curry made 5 threes over his last 15 games",
            lambda: [r for r in _player("Stephen Curry")[:15] if int(r["fg3m"]) >= 5],
        ),
    ],
)
def test_count_inside_a_last_n_window(query, expected):
    result = _run(query)
    rows = expected()
    assert _count(result) == len(rows)
    assert _game_ids(result) == _ids(rows)


def test_window_with_no_qualifying_game_is_a_zero_count():
    result = _run("how many times has LeBron scored 50 in his last 10 games")

    assert _count(result) == 0
    assert result.metadata["count_phrase"] == (
        "LeBron James has had 0 games with 50+ points in his last 10 games."
    )


def test_window_count_phrase_names_the_window_and_the_team():
    result = _run("how many times have the Lakers scored 120 in their last 10 games")
    expected = sum(int(r["pts"]) >= 120 for r in _team("LAL")[:10])

    assert result.metadata["count_phrase"] == (
        f"The Los Angeles Lakers have had {expected} games with 120+ points in their last 10 games."
    )


def test_condition_listed_before_a_bare_window_is_measured_inside_it():
    result = _run("LeBron 30 point games in his last 10 games")
    expected = [r for r in _player("LeBron James")[:10] if int(r["pts"]) >= 30]

    assert result.route == "player_game_finder"
    assert _game_ids(result) == _ids(expected)


def test_outcome_inside_a_window_summarises_the_wins_among_those_games():
    result = _run("LeBron stats in wins over his last 10 games")
    expected = [r for r in _player("LeBron James")[:10] if r["wl"] == "W"]

    assert result.route == "player_game_summary"
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(expected)
    assert _game_ids(result) == _ids(expected)


# -- qualifying: the condition picks the games, then the N most recent ------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "LeBron last 5 games where he scored 30",
            lambda: [r for r in _player("LeBron James") if int(r["pts"]) >= 30][:5],
        ),
        (
            "LeBron last 10 wins",
            lambda: [r for r in _player("LeBron James") if r["wl"] == "W"][:10],
        ),
        (
            "Lakers last 5 games scoring 120+",
            lambda: [r for r in _team("LAL") if int(r["pts"]) >= 120][:5],
        ),
        # Special events are conditions too: the last 3 triple-doubles, not
        # the triple-doubles among his last 3 games.
        (
            "Jokic last 3 triple doubles",
            lambda: [r for r in _player("Nikola Jokić") if _triple_double(r)][:3],
        ),
    ],
)
def test_last_n_qualifying_games(query, expected):
    assert _game_ids(_run(query)) == _ids(expected())


# -- meetings: the opponent chooses the games in play -----------------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "LeBron last 3 meetings with the Warriors",
            lambda: _player("LeBron James", opponent="GSW")[:3],
        ),
        ("LeBron last 3 games vs Warriors", lambda: _player("LeBron James", opponent="GSW")[:3]),
        ("Lakers last 3 meetings with the Warriors", lambda: _team("LAL", opponent="GSW")[:3]),
        ("Lakers last meeting with the Celtics", lambda: _team("LAL", opponent="BOS")[:1]),
        (
            "Lakers record in their last 4 meetings against Denver",
            lambda: _team("LAL", opponent="DEN")[:4],
        ),
        (
            "how many times has LeBron scored 25 in his last 5 games against the Celtics",
            lambda: [r for r in _player("LeBron James", opponent="BOS")[:5] if int(r["pts"]) >= 25],
        ),
    ],
)
def test_last_n_meetings_select_games_against_that_opponent(query, expected):
    result = _run(query)
    rows = expected()
    assert result.metadata["opponent"] in {"GSW", "BOS", "DEN"}
    assert _game_ids(result) == _ids(rows)


# -- wording: every recent-sample phrase keeps its window -------------------


@pytest.mark.parametrize(
    ("query", "rows"),
    [
        ("LeBron last ten games", lambda: _player("LeBron James")[:10]),
        ("LeBron previous 5 games", lambda: _player("LeBron James")[:5]),
        ("LeBron's 5 most recent games", lambda: _player("LeBron James")[:5]),
        ("LeBron over his past five games", lambda: _player("LeBron James")[:5]),
        ("Lakers record last five games", lambda: _team("LAL")[:5]),
        ("Celtics record over their previous 8 games", lambda: _team("BOS")[:8]),
        ("Knicks record in their prior twelve games", lambda: _team("NYK")[:12]),
    ],
)
def test_recent_sample_wording_keeps_its_window(query, rows):
    result = _run(query)
    (summary,) = result.result.to_dict()["sections"]["summary"]
    expected = rows()
    assert summary["games"] == len(expected)
    assert _game_ids(result) == _ids(expected)


def test_record_window_caveat_counts_games_in_the_window():
    from nbatools.query_service import execute_structured_query

    result = execute_structured_query(
        "team_record",
        team="LAL",
        season="2025-26",
        last_n=10,
        wins_only=True,
        last_n_scope="window",
    )
    expected = [r for r in _team("LAL")[:10] if r["wl"] == "W"]

    assert _game_ids(result) == _ids(expected)
    assert "last 10 games (played 10)" in result.result.to_dict()["caveats"]


# -- no season named: the window reaches back into last season --------------


def _team_both_seasons(abbr: str) -> list[dict[str, str]]:
    return _team(abbr) + _team(abbr, season="2024-25")


def test_last_n_without_a_season_fills_from_the_prior_season():
    result = _run("Knicks record last 70 games")
    expected = _team_both_seasons("NYK")[:70]
    (summary,) = result.result.to_dict()["sections"]["summary"]

    assert len(_team("NYK")) < 70
    assert summary["games"] == 70
    assert _game_ids(result) == _ids(expected)
    assert (
        "multi-season record aggregated from game logs across 2024-25 to 2025-26"
        in result.result.to_dict()["caveats"]
    )


def test_window_inside_the_current_season_has_no_multi_season_caveat():
    result = _run("Knicks record last 10 games")
    caveats = result.result.to_dict()["caveats"]

    assert _game_ids(result) == _ids(_team("NYK")[:10])
    assert not any(c.startswith("multi-season") for c in caveats)


@pytest.mark.parametrize(
    "query",
    ["Knicks record last 70 games this season", "Knicks record last 70 games 2025-26"],
)
def test_named_season_keeps_the_window_inside_it(query):
    result = _run(query)

    assert _game_ids(result) == _ids(_team("NYK"))
    assert "last 70 games (played 60)" in result.result.to_dict()["caveats"]


# -- review findings: more window wordings ----------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "how many 30 point games did LeBron have in the past ten games",
        "how many of LeBron's last 10 games did he score 30",
        "of LeBron's last 10 games how many did he score 30",
        "LeBron's last ten games how many 30 point games",
    ],
)
def test_window_wordings_count_inside_the_window(query):
    result = _run(query)
    expected = [r for r in _player("LeBron James")[:10] if int(r["pts"]) >= 30]

    assert _count(result) == len(expected)
    assert _game_ids(result) == _ids(expected)


def test_possessive_team_window_counts_wins_inside_it():
    result = _run("how many of the Lakers' last 10 games were wins")
    expected = [r for r in _team("LAL")[:10] if r["wl"] == "W"]

    assert _count(result) == len(expected)
    assert _game_ids(result) == _ids(expected)


def test_qualifying_count_wording_does_not_claim_a_window():
    from nbatools.query_service import _count_context

    assert (
        _count_context({}, player=True, last_n=5, last_n_scope="qualifying")
        == "(limited to the 5 most recent)"
    )
    assert _count_context({}, player=True, last_n=5, last_n_scope="window") == (
        "in his last 5 games"
    )


# -- "his last 10 wins" is the sample when another condition is counted ------


def _player_two_seasons(name: str) -> list[dict[str, str]]:
    return _player(name) + _player(name, season="2024-25")


@pytest.mark.parametrize(
    "query",
    [
        "how many of LeBron's last 10 wins did he score 30",
        "how many of his last 10 wins did LeBron score 30",
    ],
)
def test_condition_counted_inside_the_last_n_wins(query):
    result = _run(query)
    wins = [r for r in _player_two_seasons("LeBron James") if r["wl"] == "W"][:10]
    expected = [r for r in wins if int(r["pts"]) >= 30]

    assert _count(result) == len(expected)
    assert _game_ids(result) == _ids(expected)
    assert result.metadata["count_phrase"].endswith("in his last 10 wins.")


def test_last_n_losses_alone_are_the_answer():
    result = _run("Lakers last 5 losses how many")
    expected = [r for r in _team("LAL") + _team("LAL", season="2024-25") if r["wl"] == "L"][:5]

    assert _game_ids(result) == _ids(expected)
