"""Controlled roles/coverage, not NBA membership or season evidence."""

import copy

import pandas as pd
import pytest

from nbatools.commands import _team_appearances as appearances
from nbatools.commands.pipeline.team_appearance_coverage import (
    qualify_retained_appearances,
    validate_complete_appearance_proof,
)
from tests.test_qualified_played_pair import pair_sample as _pair_sample
from tests.test_structured_participation import run
from tests.test_structured_participation import source as _source

source = _source
pair_sample = _pair_sample
pytestmark = pytest.mark.engine


@pytest.mark.parametrize(
    "tail",
    [
        "Stephen Curry or LeBron James",
        "Stephen Curry unless LeBron James plays",
        "Stephen Curry during the first quarter",
        "Stephen Curry and LeBron James and Kevin Durant",
    ],
)
def test_unread_player_clause_cannot_clear_an_existing_boundary(tail):
    from nbatools.commands._team_participation_query import apply_team_participation_scope

    parsed = {
        "route": "team_record",
        "route_kwargs": {"unsupported_filters": ["unresolved_player_availability"]},
    }
    out = apply_team_participation_scope(f"Cavaliers record without {tail} in 2024-25", parsed)
    assert "unresolved_player_availability" in out["route_kwargs"]["unsupported_filters"]


def test_complete_name_clause_can_resolve_globally_without_presumed_membership():
    from nbatools.commands._team_participation_query import apply_team_participation_scope

    parsed = {
        "route": "team_record",
        "route_kwargs": {"unsupported_filters": ["unresolved_player_availability"]},
    }
    out = apply_team_participation_scope(
        "Cavaliers record without Stephen Curry in 2024-25", parsed
    )
    assert out["route_kwargs"]["without_player"] == "Stephen Curry"
    assert "unsupported_filters" not in out["route_kwargs"]


def test_single_catalog_surname_does_not_override_unresolved_team_context(monkeypatch):
    from types import SimpleNamespace

    from nbatools.commands import _team_participation_query as scope

    monkeypatch.setattr(
        scope,
        "resolve_player",
        lambda _: SimpleNamespace(resolved="John Smith", source="last_name"),
    )
    parsed = {
        "route": "team_record",
        "route_kwargs": {"unsupported_filters": ["unresolved_player_availability"]},
    }
    out = scope.apply_team_participation_scope("Cavaliers record without Smith in 2024-25", parsed)
    assert out["route_kwargs"]["unsupported_filters"] == ["unresolved_player_availability"]


def test_actual_unless_query_does_not_enable_an_unread_condition():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(
        "Cavaliers record without Stephen Curry unless LeBron James plays in 2024-25"
    )
    assert parsed["route"] == "team_record"
    assert "unread_participation_clause" in parsed["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize("window", [None, "qualifying", "window", "original_window"])
def test_new_mixed_scope_does_not_hide_unknown_behind_false_sibling(pair_sample, window):
    from nbatools.query_service import execute_structured_query
    from tests.test_qualified_played_pair import TATUM

    rows = pair_sample["ledger"]
    rows.loc[
        rows.game_id.eq(pair_sample["ids"][2]) & rows.player_id.eq(TATUM), "participation_state"
    ] = "unknown"
    result = execute_structured_query(
        "team_record",
        team="LAL",
        opponent="BOS",
        season="2023-24",
        with_player="Jayson Tatum",
        without_player="Austin Reaves",
        participation_scope="team",
        last_n=4 if window else None,
        last_n_scope=window,
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.fixture
def sample(monkeypatch):
    games = pd.DataFrame(
        [
            dict(game_id=g, team_id=1, opponent_team_id=2, game_date=f"2025-01-0{g}")
            for g in range(1, 6)
        ]
    )
    # Stipulated facts include a side change; no tenure is inferred.
    rows = pd.DataFrame(
        [
            dict(
                game_id=1,
                team_id=1,
                player_id=11,
                player_name="Transfer Player",
                game_date="2025-01-01",
                participation_state="played",
            ),
            dict(
                game_id=2,
                team_id=2,
                player_id=11,
                player_name="Transfer Player",
                game_date="2025-01-02",
                participation_state="played",
            ),
            dict(
                game_id=3,
                team_id=1,
                player_id=11,
                player_name="Transfer Player",
                game_date="2025-01-03",
                participation_state="did_not_play",
            ),
        ]
    )
    monkeypatch.setattr(appearances, "combined_observations", lambda *a: (rows, {11}))
    monkeypatch.setattr(
        appearances, "player_ids_for_name", lambda n: {"33"} if n == "Catalog Player" else set()
    )
    monkeypatch.setattr(
        appearances,
        "_coverage",
        lambda *a: {(g, t): (f"2025-01-0{g}", set()) for g in range(1, 5) for t in (1, 2)},
    )
    return games


def selected(games, name="Transfer Player", played=False, scope="team"):
    return set(
        appearances.select_appearances(
            games, name, ["2024-25"], "Regular Season", played=played, scope=scope
        ).game_id
    )


def test_team_without_includes_opponent_appearance_and_unlisted_complete_game(sample):
    assert selected(sample.iloc[:4]) == {2, 3, 4}
    assert selected(sample.iloc[:4], played=True) == {1}


def test_explicit_opponent_and_anywhere_keep_distinct_roles(sample):
    assert selected(sample.iloc[:4], played=True, scope="opponent") == {2}
    assert selected(sample.iloc[:4], scope="game") == {3, 4}


def test_own_side_exact_fact_needs_no_opponent_but_other_side_scope_does(sample):
    own = sample.iloc[:1].drop(columns="opponent_team_id")
    assert selected(own, played=True) == {1}
    with pytest.raises(ValueError, match="opponent identity"):
        selected(own, scope="opponent")
    with pytest.raises(ValueError, match="Conflicting"):
        selected(sample.iloc[1:2].drop(columns="opponent_team_id"))


def test_verified_catalog_identity_can_have_no_season_appearances(sample):
    assert selected(sample.iloc[:4], "Catalog Player") == {1, 2, 3, 4}
    assert selected(sample.iloc[:4], "Catalog Player", played=True) == set()


def test_missing_complete_list_blocks_negative_and_does_not_change_identity(sample):
    with pytest.raises(ValueError, match="Incomplete team appearance coverage"):
        selected(sample)
    with pytest.raises(ValueError, match="identity"):
        selected(sample.iloc[:4], "Invented Person")


def test_pair_checks_unknown_even_when_first_predicate_is_false(sample):
    with pytest.raises(ValueError, match="Incomplete team appearance coverage"):
        selected(sample, "Transfer Player and Catalog Player", played=True)


def test_another_game_on_the_same_date_does_not_fill_a_missing_list(sample):
    sample.loc[4, "game_date"] = "2025-01-01"
    with pytest.raises(ValueError, match="Incomplete team appearance coverage"):
        selected(sample.iloc[4:])


def test_retained_full_container_produces_complete_side_proof(source):
    run(source)
    proof = qualify_retained_appearances(source[0], "2025-26", "Regular Season")
    assert {(s["team_id"], tuple(s["played_ids"])) for s in proof["sides"]} == {
        (1, (11,)),
        (2, (21,)),
    }
    assert proof["source_requests"] == 0 and proof["unqualified"] == []


def test_precise_positive_source_clock_overrides_rounded_canonical_zero(source):
    path = source[0] / "raw/player_game_stats/2025-26_regular_season.csv"
    frame = pd.read_csv(path)
    frame["minutes"] = [0, 11]
    frame.to_csv(path, index=False)
    source[3]["boxScoreTraditional"]["homeTeam"]["players"][0]["statistics"]["minutes"] = "0:01"
    run(source)
    proof = qualify_retained_appearances(source[0], "2025-26", "Regular Season")
    assert next(s for s in proof["sides"] if s["team_id"] == 1)["played_ids"] == [11]


@pytest.mark.parametrize("clock", ["0:00", None])
def test_ambiguous_zero_or_blank_row_cannot_close_an_appearance_list(source, clock):
    player = source[3]["boxScoreTraditional"]["homeTeam"]["players"][1]
    player["statistics"]["minutes"] = clock
    player["comment"] = ""
    run(source)
    proof = qualify_retained_appearances(source[0], "2025-26", "Regular Season")
    assert not any(s["team_id"] == 1 for s in proof["sides"])
    assert any(s.get("team_id") == 1 for s in proof["unqualified"])


@pytest.mark.parametrize("damage", ["dependencies", "source", "subset", "game", "side"])
def test_completeness_claim_must_replay_its_original_container(source, damage):
    run(source)
    proof = qualify_retained_appearances(source[0], "2025-26", "Regular Season")
    validate_complete_appearance_proof(source[0], proof)
    wrong = copy.deepcopy(proof)
    if damage == "dependencies":
        wrong["dependencies"] = {}
    elif damage == "source":
        wrong["sides"][0]["source_files"] = {}
    elif damage == "subset":
        wrong["sides"][0]["played_ids"] = []
    else:
        wrong["sides"][0]["game_id" if damage == "game" else "team_id"] = 999
    with pytest.raises(ValueError):
        validate_complete_appearance_proof(source[0], wrong)
