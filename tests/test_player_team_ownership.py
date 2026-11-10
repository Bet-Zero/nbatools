"""Full person spans own internal team words; explicit separate teams survive."""

import asyncio

import httpx
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands import entity_resolution as er
from nbatools.commands._matchup_utils import (
    detect_opponent,
    detect_team_in_text,
    detect_team_resolved,
    detect_unresolved_availability_player,
)
from nbatools.commands.natural_query import parse_query
from nbatools.development_data import development_snapshot
from nbatools.query_service import _build_applied_filters, execute_structured_query
from tests.test_player_period_dependencies import source_oracle, unpack
from tools.development_query import create_app

pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


@pytest.fixture
def known_names(monkeypatch, request):
    # Controlled identity-index fixture; these are no NBA statistical claims.
    names = {
        "P.J. Washington",
        "Orlando Robinson",
        "Allan Houston",
        "Brandon Boston Jr.",
        "Duane Washington Jr.",
        "TyTy Washington Jr.",
        "David Robinson",
    }
    er.reset_player_index()
    request.addfinalizer(er.reset_player_index)
    monkeypatch.setattr(er, "data_source_cache_key", lambda: "controlled-team-owned-names")
    monkeypatch.setattr(er, "_read_player_names", lambda data_dir=None: names)


@pytest.mark.parametrize(
    "name",
    [
        "P.J. Washington",
        "PJ Washington",
        "Orlando Robinson",
        "Allan Houston",
        "Brandon Boston Jr.",
        "Duane Washington Jr.",
        "TyTy Washington Jr.",
    ],
)
def test_explicit_known_person_owns_entire_name_before_team_or_short_alias(known_names, name):
    expected = "P.J. Washington" if name == "PJ Washington" else name
    q = f"{name} rebounds in 2024-25"
    parsed = parse_query(q)
    assert parsed["player"] == expected
    assert parsed["team"] is parsed["opponent"] is None
    assert er.resolve_player_in_query(name).resolved == expected
    assert detect_team_in_text(q.lower()) is None
    assert detect_team_resolved(q.lower()).resolved is None
    assert er.resolve_team_in_query(q).resolved is None


@pytest.mark.parametrize(
    "name,team,opponent",
    [
        ("P.J. Washington", "DAL", "WAS"),
        ("Orlando Robinson", "MIA", "ORL"),
        ("Allan Houston", "NYK", "HOU"),
        ("Brandon Boston Jr.", "LAC", "BOS"),
    ],
)
def test_independent_team_and_opponent_clauses_keep_all_entities(known_names, name, team, opponent):
    for join in ("against", "vs", "versus"):
        p = parse_query(f"{name} games for {team} {join} {opponent} in 2024-25")
        assert (p["player"], p["team"], p["opponent"]) == (name, team, opponent)
    p = parse_query(f"{name} games for Washington against Dallas in 2024-25")
    assert (p["player"], p["team"], p["opponent"]) == (name, "WAS", "DAL")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Washington Wizards", "WAS"),
        ("WAS", "WAS"),
        ("Boston Celtics", "BOS"),
        ("BOS", "BOS"),
        ("Orlando Magic", "ORL"),
        ("ORL", "ORL"),
        ("Houston Rockets", "HOU"),
        ("HOU", "HOU"),
    ],
)
def test_team_names_and_abbreviations_still_mean_the_team(known_names, text, expected):
    p = parse_query(f"{text} record in 2024-25")
    assert p["team"] == expected and p["player"] is None
    assert er.resolve_team(text).resolved == expected


def test_person_opponent_comparisons_and_initials_in_presence_retain_roles(known_names):
    p = parse_query("Jokic games vs P.J. Washington in 2024-25")
    assert (p["player"], p["opponent_player"], p["opponent"], p["team"]) == (
        "Nikola Jokić",
        "P.J. Washington",
        None,
        None,
    )
    p = parse_query("compare Allan Houston and P.J. Washington points in 2024-25")
    assert (p["player_a"], p["player_b"], p["team_a"], p["team_b"]) == (
        "Allan Houston",
        "P.J. Washington",
        None,
        None,
    )
    for mode in ("with", "without"):
        p = parse_query(f"Orlando Robinson games {mode} P.J. Washington in 2024-25")
        assert p["player"] == "Orlando Robinson" and p[mode + "_player"] == "P.J. Washington"
        assert p["team"] is None
        unresolved = detect_unresolved_availability_player(
            f"games {mode} q.j. unindexed in 2024-25", mode=mode
        )
        assert unresolved == "q.j. unindexed"


def test_offsets_survive_periods_accents_whitespace_and_multiple_person_mentions(known_names):
    q = "P.J. Wáshington\tgames against the Washington Wizards, at home"
    masked = er.mask_player_owned_team_words(q)
    assert len(masked) == len(q) and masked.index("Washington Wizards") == q.index(
        "Washington Wizards"
    )
    opponent, remaining = detect_opponent(q.lower())
    assert opponent == "WAS" and "p.j. washington" in remaining and "at home" in remaining
    remainder = er.mask_player_owned_team_words("Orlando Robinson and Allan Houston against Boston")
    assert " ".join(remainder.split()) == "and against Boston"
    # An absence actor in parsed input is not the team's primary player.
    for scope in (
        {"player": "P.J. Washington", "team": "DAL", "without_player": "P.J. Washington"},
        {"team": "DAL", "membership_player": "P.J. Washington"},
        {"team": "DAL"},
    ):
        assert not any(
            f["label"] == "Playing for"
            for f in _build_applied_filters(scope, route_kwargs={"team": "DAL"})
        )


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    return unpack(tmp_path_factory.mktemp("ownership-qualified-v6"))


@pytest.fixture(autouse=True)
def local(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")


@pytest.mark.parametrize(
    "query,window,rebounds",
    [
        (
            "How many rebounds did P.J. Washington get in first halves on 2026-11-04?",
            {"half": "first"},
            4,
        ),
        (
            "How many rebounds did PJ Washington get in first halves vs Spurs on 2026-11-04?",
            {"half": "first", "opponent": "SAS"},
            4,
        ),
        (
            "How many rebounds did P.J. Washington get in second quarters for DAL on 2026-11-04?",
            {"quarter": "2", "team": "DAL"},
            1,
        ),
    ],
)
def test_scorer_qualified_player_rebounds_natural_structured_http(
    qualified, query, window, rebounds
):
    expected = next(
        row
        for row in source_oracle()["selected_rows"]
        if row["player_id"] == 1629023 and row["window"] == ("h1" if "half" in window else "q2")
    )
    assert expected["reb"] == rebounds  # Accepted independent raw/book source oracle.
    with development_snapshot(*qualified):
        natural = natural_query_payload(query)
        structured = execute_structured_query(
            "player_game_finder",
            player="P.J. Washington",
            season="2026-27",
            start_date="2026-11-04",
            end_date="2026-11-04",
            stat="reb",
            **window,
        )
        assert structured.result_status == "ok"
        assert [
            f for f in structured.metadata.get("applied_filters", []) if f["label"] == "Playing for"
        ] == (
            [{"label": "Playing for", "value": window["team"], "kind": "team"}]
            if window.get("team")
            else []
        )
        rows = structured.result.to_dict()["sections"]["finder"]
        assert len(rows) == 1 and (rows[0]["game_id"], rows[0]["player_id"], rows[0]["reb"]) == (
            expected["game_id"],
            expected["player_id"],
            rebounds,
        )
    assert natural["result_status"] == "ok" and natural["result"]["sections"]["count"] == [
        {"count": rebounds}
    ]
    meta = natural["result"]["metadata"]
    assert meta["player"] == "P.J. Washington" and meta["team"] == window.get("team")
    assert meta["opponent"] == window.get("opponent")
    assert [f for f in meta.get("applied_filters", []) if f["label"] == "Playing for"] == (
        [{"label": "Playing for", "value": window["team"], "kind": "team"}]
        if window.get("team")
        else []
    )
    assert meta["data_quality"]["manifest_sha256"] == qualified[1]
    assert meta["data_quality"]["production_accepted"] is False

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(*qualified)), base_url="http://127.0.0.1"
        ) as client:
            r = await client.post("/query", json={"query": query})
            assert r.status_code == 200
            body = r.json()
            assert body["result_status"] == "ok" and body["result"]["sections"]["count"] == [
                {"count": rebounds}
            ]
            assert body["result"]["metadata"] == meta

    asyncio.run(request())


def test_explicit_conflicting_team_is_preserved_as_qualified_empty_not_ignored(qualified):
    query = "How many rebounds did P.J. Washington get in first halves for WAS on 2026-11-04?"
    with development_snapshot(*qualified):
        body = natural_query_payload(query)
        assert body["result_status"] == "ok" and body["result"]["sections"]["count"] == [
            {"count": 0}
        ]
        assert body["result"]["metadata"]["team"] == "WAS"
        assert body["result"]["metadata"]["player"] == "P.J. Washington"
        assert {"label": "Playing for", "value": "WAS", "kind": "team"} in body["result"][
            "metadata"
        ]["applied_filters"]
        structured = execute_structured_query(
            "player_game_finder",
            player="P.J. Washington",
            team="WAS",
            season="2026-27",
            start_date="2026-11-04",
            end_date="2026-11-04",
            stat="reb",
            half="first",
        )
        assert structured.result_status == "no_result" and structured.result_reason == "no_match"
        assert {"label": "Playing for", "value": "WAS", "kind": "team"} in structured.metadata[
            "applied_filters"
        ]
