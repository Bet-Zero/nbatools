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

import pandas as pd
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
        entity_resolution,
        "_read_identity_rows",
        lambda: ([pd.DataFrame({"player_name": sorted(COVERED_NAMES)})], None),
    )


@pytest.fixture
def empty_index(monkeypatch, request):
    entity_resolution.reset_player_index()
    request.addfinalizer(entity_resolution.reset_player_index)
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "identity-empty")
    monkeypatch.setattr(entity_resolution, "_read_identity_rows", lambda: ([], None))


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


@pytest.fixture
def identity_snapshot_files():
    root = FIXTURE_STATS.parents[1]
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_admitted_queries_keep_own_identity_and_sample_on_generation_rollover(
    tmp_path, monkeypatch, identity_snapshot_files
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from nbatools import query_service
    from nbatools.admission_control import AdmissionController
    from nbatools.data_source import ACTIVE_GENERATION_PATH, reset_data_source_cache
    from tests.test_data_source import FakeR2Client, _configure_r2, published_generation_objects

    old_ledger = b"player_id,player_name,season,first_seen\n1626157,Karl-Anthony Towns,2025-26,0\n"
    new_ledger = (
        b"player_id,player_name,season,first_seen\n"
        b"1626157,Karl Anthony Towns,2025-26,0\n"
        b"99999,Karl Anthony Towns,2025-26,1\n"
    )
    ledger = "metadata/player_names.csv"
    stats = "raw/player_game_stats/2025-26_regular_season.csv"
    original = pd.read_csv(FIXTURE_STATS / "2025-26_regular_season.csv", dtype={"game_id": str})
    changed = original.copy()
    primary = changed["player_id"] == int(TOWNS_ID)
    changed.loc[primary, "player_name"] = "Karl Anthony Towns"
    addition = changed.loc[primary].head(1).assign(player_id=99999, pts=200)
    new_stats = pd.concat([changed, addition], ignore_index=True).to_csv(index=False).encode()
    old, _ = published_generation_objects("old", identity_snapshot_files | {ledger: old_ledger})
    new, _ = published_generation_objects(
        "new", identity_snapshot_files | {ledger: new_ledger, stats: new_stats}
    )
    pointer = ACTIVE_GENERATION_PATH.as_posix()
    client = FakeR2Client(new | old)
    _configure_r2(monkeypatch, tmp_path, client)
    monkeypatch.setattr(entity_resolution, "_MAX_CACHED_PLAYER_IDENTITIES", 1)
    entity_resolution.reset_player_index()
    old_pinned = Event()
    new_finished = Event()
    observed = {}
    original_natural = query_service._execute_natural_query_in_generation
    original_structured = query_service._execute_structured_query_in_generation

    def read_identity():
        return (
            entity_resolution.player_ids_for_name("Karl-Anthony Towns"),
            entity_resolution.canonical_player_names_by_id()[TOWNS_ID],
        )

    def pause_old(query):
        bundle = entity_resolution._get_player_identity()
        observed["old_before"] = read_identity()
        old_pinned.set()
        assert new_finished.wait(8)
        answer = original_natural(query)
        assert entity_resolution._get_player_identity() is bundle
        observed["old_after"] = read_identity()
        return answer

    def inspect_new(route, **kwargs):
        observed["new"] = read_identity()
        return original_structured(route, **kwargs)

    monkeypatch.setattr(query_service, "_execute_natural_query_in_generation", pause_old)
    monkeypatch.setattr(query_service, "_execute_structured_query_in_generation", inspect_new)
    controller = AdmissionController(max_concurrent_queries=2)
    query = "Karl-Anthony Towns stats in 2025-26"
    try:
        with ThreadPoolExecutor(max_workers=1) as callers:
            old_answer = callers.submit(
                controller.run_query,
                "old-client",
                lambda: query_service.execute_natural_query(query),
            )
            try:
                assert old_pinned.wait(8)
                client.objects[pointer] = new[pointer]
                new_answer = controller.run_query(
                    "new-client",
                    lambda: query_service.execute_structured_query(
                        "player_game_summary", player="Karl-Anthony Towns", season="2025-26"
                    ),
                )
            finally:
                new_finished.set()
            old_result = old_answer.result(timeout=8)
        expected = _expected_summary(_player_games(TOWNS_ID, "2025-26"))
        _assert_summary_matches(_summary_rows(old_result)[0], "Karl-Anthony Towns", expected)
        _assert_summary_matches(_summary_rows(new_answer)[0], "Karl Anthony Towns", expected)
        assert observed == {
            "old_before": (frozenset({TOWNS_ID}), "Karl-Anthony Towns"),
            "new": (frozenset({TOWNS_ID, "99999"}), "Karl Anthony Towns"),
            "old_after": (frozenset({TOWNS_ID}), "Karl-Anthony Towns"),
        }
        assert any("More than one player" in note for note in new_answer.result.notes)
        assert not any("More than one player" in note for note in old_result.result.notes)
    finally:
        controller._executor.shutdown(wait=True)
        entity_resolution.reset_player_index()
        reset_data_source_cache()


@pytest.mark.parametrize("declared_ledger", [True, False])
def test_required_identity_integrity_reaches_natural_and_structured_consumers(
    tmp_path, monkeypatch, identity_snapshot_files, declared_ledger
):
    from nbatools.data_source import DataSourceError, reset_data_source_cache
    from nbatools.query_service import execute_natural_query, execute_structured_query
    from tests.test_data_source import FakeR2Client, _configure_r2, published_generation_objects

    season = "raw/player_game_stats/2025-26_regular_season.csv"
    sources = dict(identity_snapshot_files)
    if declared_ledger:
        sources["metadata/player_names.csv"] = (
            b"player_id,player_name,season,first_seen\n1626157,Karl-Anthony Towns,2025-26,0\n"
        )
    objects, _ = published_generation_objects("identity", sources)
    objects[f"generations/identity/{season}"] = b"corrupt season object"
    if declared_ledger:
        objects.pop("generations/identity/metadata/player_names.csv")
    _configure_r2(monkeypatch, tmp_path, FakeR2Client(objects))
    entity_resolution.reset_player_index()

    try:
        with pytest.raises(DataSourceError):
            execute_natural_query("Karl-Anthony Towns stats in 2025-26")
        with pytest.raises(DataSourceError):
            execute_structured_query(
                "player_game_summary", player="Karl-Anthony Towns", season="2025-26"
            )
    finally:
        entity_resolution.reset_player_index()
        reset_data_source_cache()


def test_failed_concurrent_identity_build_publishes_nothing_and_recovers(tmp_path, monkeypatch):
    from concurrent.futures import Future, ThreadPoolExecutor
    from threading import Event

    from nbatools.data_source import DataSourceError, reset_data_source_cache
    from tests.test_data_source import (
        FakeBody,
        FakeR2Client,
        _configure_r2,
        published_generation_objects,
    )

    builder_entered = Event()
    waiter_entered = Event()
    data = b"player_id,player_name,season,first_seen\n2229,Mike James,2025-26,0\n"
    ledger = "metadata/player_names.csv"
    key = f"generations/identity/{ledger}"

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiter_entered.set()
            return super().result(timeout)

    class OneCorruptReadClient(FakeR2Client):
        attempts = 0

        def get_object(self, *, Bucket, Key):
            if Key == key:
                self.attempts += 1
                if self.attempts == 1:
                    builder_entered.set()
                    assert waiter_entered.wait(8)
                    # Preserve length so the authenticated digest is the check
                    # that prevents a plausible but incorrect identity.
                    return {"Body": FakeBody(data.replace(b"2229", b"2228"))}
            return super().get_object(Bucket=Bucket, Key=Key)

    objects, _ = published_generation_objects("identity", {ledger: data})
    client = OneCorruptReadClient(objects)
    _configure_r2(monkeypatch, tmp_path, client)
    monkeypatch.setattr(entity_resolution, "Future", ObservedFuture)
    entity_resolution.reset_player_index()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(entity_resolution.player_ids_for_name, "Mike James")
            assert builder_entered.wait(8)
            second = pool.submit(entity_resolution.player_ids_for_name, "Mike James")
            for pending in (first, second):
                with pytest.raises(DataSourceError, match="published digest"):
                    pending.result(timeout=8)
        assert client.attempts == 1
        assert entity_resolution.player_ids_for_name("Mike James") == {"2229"}
        assert entity_resolution.canonical_player_names_by_id()["2229"] == "Mike James"
        assert client.attempts == 2
    finally:
        entity_resolution.reset_player_index()
        reset_data_source_cache()
