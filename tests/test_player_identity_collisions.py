"""A player's name must reach that player, not a player whose alias it contains.

``apply_base_filters`` selects rows by the exact ``player_name`` entity
resolution returns, so a collision answers about someone else with real-looking
numbers. The reported cases were ``Karl-Anthony Towns`` -> Carmelo Anthony
("anthony" alias) and ``Nikola Jovic`` -> Nikola Jokić ("nikola" alias). The
same mechanism also mapped unpunctuated suffixes to the father
("Tim Hardaway Jr" -> Tim Hardaway).

Three data conditions are covered:

* a controlled name index shaped like the real 1996-97+ coverage (unit level);
* no season data at all (the curated canonical names still apply);
* the committed query fixture, end to end through the natural, structured and
  HTTP paths, with expected values computed straight from the fixture CSVs
  rather than from the engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nbatools.commands import entity_resolution
from nbatools.commands.entity_resolution import (
    extract_player_comparison_resolved,
    phrase_has_partial_nickname_player_typo,
    resolve_player,
    resolve_player_in_query,
)

# Real names from the 1996-97 onward player data, including both generations of
# shared-surname families that coexist inside that span.
COVERED_NAMES = {
    "Karl-Anthony Towns",
    "Carmelo Anthony",
    "Cole Anthony",
    "Anthony Black",
    "Anthony Davis",
    "Anthony Edwards",
    "Nikola Jokić",
    "Nikola Jović",
    "Nikola Vučević",
    "Tim Hardaway",
    "Tim Hardaway Jr.",
    "Gary Trent",
    "Gary Trent Jr.",
    "Jaren Jackson",
    "Jaren Jackson Jr.",
    "P.J. Tucker",
    "Shai Gilgeous-Alexander",
    "Stephen Curry",
    "Seth Curry",
    # Surnames that are also ordinary query words, and first names that are
    # also verbs: none of them may veto a neighbouring alias.
    "Todd Day",
    "Dionte Christmas",
    "Sean May",
    "World B. Free",
    "Will Barton",
    "Max Strus",
}


@pytest.fixture
def covered_index(monkeypatch, request):
    entity_resolution.reset_player_index()
    request.addfinalizer(entity_resolution.reset_player_index)
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "identity-test")
    monkeypatch.setattr(
        entity_resolution, "_read_player_names", lambda data_dir=None: set(COVERED_NAMES)
    )


@pytest.fixture
def empty_index(monkeypatch, request):
    entity_resolution.reset_player_index()
    request.addfinalizer(entity_resolution.reset_player_index)
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "identity-empty")
    monkeypatch.setattr(entity_resolution, "_read_player_names", lambda data_dir=None: set())


@pytest.mark.parser
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Karl-Anthony Towns last 10 games", "Karl-Anthony Towns"),
        ("karl anthony towns last 10 games", "Karl-Anthony Towns"),
        ("how many rebounds does karl anthony towns average", "Karl-Anthony Towns"),
        ("Carmelo Anthony career stats", "Carmelo Anthony"),
        ("melo career stats", "Carmelo Anthony"),
        ("Cole Anthony stats", "Cole Anthony"),
        ("anthony black assists this season", "Anthony Black"),
        ("Anthony Davis rebounds", "Anthony Davis"),
        ("Nikola Jovic stats", "Nikola Jović"),
        ("nikola jović last 5 games", "Nikola Jović"),
        ("Nikola Jokic stats", "Nikola Jokić"),
        ("nikola triple doubles", "Nikola Jokić"),
        ("Tim Hardaway Jr stats", "Tim Hardaway Jr."),
        ("tim hardaway jr. stats 2015-16", "Tim Hardaway Jr."),
        ("Tim Hardaway stats 1996-97", "Tim Hardaway"),
        ("gary trent jr 30 point games", "Gary Trent Jr."),
        ("Jaren Jackson Jr blocks", "Jaren Jackson Jr."),
        ("pj tucker corner threes", "P.J. Tucker"),
        ("shai gilgeous alexander points", "Shai Gilgeous-Alexander"),
        ("seth curry threes", "Seth Curry"),
        ("kat stats", "Karl-Anthony Towns"),
        # An alias next to a word that is also somebody's name is still the
        # alias (independent checker regressions on an earlier candidate).
        ("lebron christmas day games", "LeBron James"),
        ("luka christmas day games", "Luka Dončić"),
        ("luka free throws", "Luka Dončić"),
        ("giannis free throws made", "Giannis Antetokounmpo"),
        ("will curry score 30 tonight", "Stephen Curry"),
        ("max booker points", "Devin Booker"),
        ("luka tatum head to head", "Luka Dončić"),
        ("shai jokic mvp race", "Shai Gilgeous-Alexander"),
    ],
)
def test_names_in_queries_reach_their_own_player(covered_index, query, expected):
    result = resolve_player_in_query(query)
    assert result.is_confident, (query, result)
    assert result.resolved == expected


@pytest.mark.parser
@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("karl anthony towns", "Karl-Anthony Towns"),
        ("Karl-Anthony Towns", "Karl-Anthony Towns"),
        ("nikola jovic", "Nikola Jović"),
        ("tim hardaway jr", "Tim Hardaway Jr."),
        ("anthony black", "Anthony Black"),
        ("anthony", "Carmelo Anthony"),
        ("nikola", "Nikola Jokić"),
    ],
)
def test_name_fragments_reach_their_own_player(covered_index, phrase, expected):
    result = resolve_player(phrase)
    assert result.is_confident, (phrase, result)
    assert result.resolved == expected


@pytest.mark.parser
@pytest.mark.parametrize(
    ("query", "expected_a", "expected_b"),
    [
        ("Karl-Anthony Towns vs Carmelo Anthony", "Karl-Anthony Towns", "Carmelo Anthony"),
        ("karl anthony towns vs nikola jokic", "Karl-Anthony Towns", "Nikola Jokić"),
        ("nikola jovic vs nikola jokic", "Nikola Jović", "Nikola Jokić"),
        ("Tim Hardaway Jr vs Gary Trent Jr", "Tim Hardaway Jr.", "Gary Trent Jr."),
    ],
)
def test_comparison_sides_keep_their_own_players(covered_index, query, expected_a, expected_b):
    result_a, result_b = extract_player_comparison_resolved(query)
    assert (result_a.resolved, result_b.resolved) == (expected_a, expected_b)


@pytest.mark.parser
@pytest.mark.parametrize(
    "query",
    ["Karl-Anthony Towns last 10 games", "karl anthony towns stats"],
)
def test_curated_full_name_wins_without_season_data(empty_index, query):
    result = resolve_player_in_query(query)
    assert result.is_confident
    assert result.resolved == "Karl-Anthony Towns"
    assert resolve_player("karl anthony towns").resolved == "Karl-Anthony Towns"


@pytest.mark.parser
def test_season_tokens_are_not_name_typos(covered_index):
    assert not phrase_has_partial_nickname_player_typo("stephen curry 2025-26")
    assert not phrase_has_partial_nickname_player_typo("curry 2025-26")
    # A genuinely misspelled first name is still caught.
    assert phrase_has_partial_nickname_player_typo("stephn curry")


# ── End to end against the committed fixture ─────────────────────────

FIXTURE_STATS = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")
TOWNS_ID = "1626157"
JOVIC_ID = "1631107"
JOKIC_ID = "203999"


def _player_games(player_id: str, season: str) -> list[dict[str, str]]:
    """Independent expectation: the player's rows read straight from the CSV."""
    path = FIXTURE_STATS / f"{season}_regular_season.csv"
    with path.open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["player_id"] == player_id]
    return sorted(rows, key=lambda row: (row["game_date"], row["game_id"]))


def _expected_summary(rows: list[dict[str, str]]) -> dict[str, float]:
    return {
        "games": len(rows),
        "wins": sum(row["wl"] == "W" for row in rows),
        "pts_sum": float(sum(int(row["pts"]) for row in rows)),
        "reb_sum": float(sum(int(row["reb"]) for row in rows)),
        "pts_avg": round(sum(int(row["pts"]) for row in rows) / len(rows), 3),
    }


def _summary_rows(query_result) -> list[dict]:
    return query_result.result.to_dict()["sections"]["summary"]


def _assert_summary_matches(row: dict, name: str, expected: dict[str, float]) -> None:
    assert row["player_name"] == name
    assert row["games"] == expected["games"]
    assert row["wins"] == expected["wins"]
    assert row["pts_sum"] == expected["pts_sum"]
    assert row["reb_sum"] == expected["reb_sum"]
    assert row["pts_avg"] == pytest.approx(expected["pts_avg"], abs=0.001)


@pytest.mark.query
@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "name", "player_id", "season", "last_n"),
    [
        ("Karl-Anthony Towns last 10 games", "Karl-Anthony Towns", TOWNS_ID, "2025-26", 10),
        ("karl anthony towns stats 2024-25", "Karl-Anthony Towns", TOWNS_ID, "2024-25", None),
        ("Nikola Jovic last 5 games", "Nikola Jović", JOVIC_ID, "2025-26", 5),
        ("how did nikola jović play in 2023-24", "Nikola Jović", JOVIC_ID, "2023-24", None),
        ("Nikola Jokic last 5 games", "Nikola Jokić", JOKIC_ID, "2025-26", 5),
    ],
)
def test_named_summary_uses_that_players_rows(query, name, player_id, season, last_n):
    from nbatools.query_service import execute_natural_query

    entity_resolution.reset_player_index()
    result = execute_natural_query(query)

    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.metadata.get("player") == name
    rows = _player_games(player_id, season)
    if last_n is not None:
        rows = rows[-last_n:]
    (summary,) = _summary_rows(result)
    _assert_summary_matches(summary, name, _expected_summary(rows))


@pytest.mark.query
@pytest.mark.fixture_data
def test_natural_and_structured_requests_select_the_same_player_sample():
    from nbatools.query_service import execute_natural_query, execute_structured_query

    entity_resolution.reset_player_index()
    natural = execute_natural_query("karl anthony towns last 10 games")
    structured = execute_structured_query(
        "player_game_summary", player="Karl-Anthony Towns", season="2025-26", last_n=10
    )

    expected = _expected_summary(_player_games(TOWNS_ID, "2025-26")[-10:])
    (natural_row,) = _summary_rows(natural)
    (structured_row,) = _summary_rows(structured)
    _assert_summary_matches(natural_row, "Karl-Anthony Towns", expected)
    _assert_summary_matches(structured_row, "Karl-Anthony Towns", expected)


DONCIC_ID = "1629029"


@pytest.mark.query
@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "expected", "last_n"),
    [
        (
            "nikola jovic vs nikola jokic 2025-26",
            {"Nikola Jović": JOVIC_ID, "Nikola Jokić": JOKIC_ID},
            None,
        ),
        (
            "compare Nikola Jović and Nikola Jokic 2025-26",
            {"Nikola Jović": JOVIC_ID, "Nikola Jokić": JOKIC_ID},
            None,
        ),
        # Typed with the canonical diacritics: this lost its second player.
        (
            "Luka Dončić vs Nikola Jokić last 10 games",
            {"Luka Dončić": DONCIC_ID, "Nikola Jokić": JOKIC_ID},
            10,
        ),
        (
            "compare Karl-Anthony Towns and Nikola Jović 2025-26",
            {"Karl-Anthony Towns": TOWNS_ID, "Nikola Jović": JOVIC_ID},
            None,
        ),
    ],
)
def test_comparison_keeps_each_named_player(query, expected, last_n):
    from nbatools.query_service import execute_natural_query

    entity_resolution.reset_player_index()
    result = execute_natural_query(query)

    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.route == "player_compare"
    by_name = {row["player_name"]: row for row in _summary_rows(result)}
    assert set(by_name) == set(expected)
    for name, player_id in expected.items():
        rows = _player_games(player_id, "2025-26")
        if last_n is not None:
            rows = rows[-last_n:]
        _assert_summary_matches(by_name[name], name, _expected_summary(rows))


@pytest.mark.api
@pytest.mark.fixture_data
def test_http_answer_names_and_counts_the_requested_player():
    from fastapi.testclient import TestClient

    from nbatools.api import app

    entity_resolution.reset_player_index()
    response = TestClient(app).post("/query", json={"query": "Karl Anthony Towns last 10 games"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_status"] == "ok"
    (summary,) = payload["result"]["sections"]["summary"]
    _assert_summary_matches(
        summary,
        "Karl-Anthony Towns",
        _expected_summary(_player_games(TOWNS_ID, "2025-26")[-10:]),
    )
