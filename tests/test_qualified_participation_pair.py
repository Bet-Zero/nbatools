"""K08 positives use explicit synthetic observations, never missing-row inference."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands.data_utils import filter_without_player
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
PAIR = "LeBron James and Anthony Davis"
SEASON = "2023-24"
LAL = 1610612747
PEOPLE = {2544: "LeBron James", 203076: "Anthony Davis"}


@pytest.fixture
def qualified_pair(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    suffix = f"{SEASON}_regular_season.csv"
    teams_path = root / "data/raw/team_game_stats" / suffix
    players_path = root / "data/raw/player_game_stats" / suffix
    teams, players = pd.read_csv(teams_path), pd.read_csv(players_path)
    candidates = teams.loc[teams.team_abbr.eq("LAL") & teams.opponent_team_abbr.eq("BOS")]
    ids = sorted(candidates.game_id.unique())[:4]
    assert len(ids) == 4
    # Stipulate the facts first: both absent, only LeBron absent, only Davis
    # absent, both played. Removing contradictory appearance rows below merely
    # makes the synthetic tables agree with these explicit observations.
    absence = {ids[0]: {2544, 203076}, ids[1]: {2544}, ids[2]: {203076}, ids[3]: set()}
    dropped_games = set(candidates.game_id) - set(ids)
    teams = teams.loc[~teams.game_id.isin(dropped_games)].copy()
    players = players.loc[~players.game_id.isin(dropped_games)].copy()
    candidates = teams.loc[teams.team_abbr.eq("LAL") & teams.game_id.isin(ids)].copy()
    evidence = []
    for game in candidates.itertuples():
        for pid, name in PEOPLE.items():
            evidence.append(
                dict(
                    game_id=int(game.game_id),
                    team_id=LAL,
                    player_id=pid,
                    player_name=name,
                    game_date=game.game_date,
                    season=SEASON,
                    season_type="Regular Season",
                    participation_state="did_not_play"
                    if pid in absence[game.game_id]
                    else "played",
                    coverage_scope="controlled_fixture",
                    source="synthetic_explicit_observation",
                )
            )
            if pid in absence[game.game_id]:
                players = players.loc[
                    ~(players.game_id.eq(game.game_id) & players.player_id.eq(pid))
                ]
    teams.to_csv(teams_path, index=False)
    players.to_csv(players_path, index=False)
    ledger = pd.DataFrame(evidence)

    def load(seasons, season_type):
        assert seasons == [SEASON] and season_type == "Regular Season"
        return ledger.copy()

    # This tests calculation/interpretation, not provenance qualification. The
    # real-data companion verifies actual retained-source hashes separately.
    monkeypatch.setattr(observations, "load_observations", load)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    monkeypatch.setenv("DATA_SOURCE", "local")
    reset_data_source_cache()
    yield dict(ids=ids, teams=candidates, players=players, ledger=ledger)
    reset_data_source_cache()


def _apply(sample, names):
    return filter_without_player(sample, names, [SEASON], "Regular Season", team="LAL")


def _assert_answer(result, expected, *, player=False, mode="without"):
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    sections = result.result.to_dict()["sections"]
    rows = sections.get("finder", sections.get("game_log", []))
    assert len(rows) == len(expected)
    assert {int(row["game_id"]) for row in rows} == set(expected.game_id.astype(int))
    assert all(row["season"] == SEASON for row in rows)
    assert all(row["opponent_team_abbr"] == "BOS" for row in rows)
    if player:
        assert all(row["player_id"] == 1630559 for row in rows)
    else:
        row = sections["summary"][0]
        assert (row["games"], row["wins"], row["losses"]) == (
            len(expected),
            int(expected.wl.eq("W").sum()),
            int(expected.wl.eq("L").sum()),
        )
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)
    assert result.metadata[mode + "_player"] == PAIR
    assert result.metadata.get(("with" if mode == "without" else "without") + "_player") is None
    assert result.metadata["opponent"] == "BOS"
    assert result.metadata["season"] == SEASON
    assert result.metadata["player"] == ("Austin Reaves" if player else None)
    label = "Without player" if mode == "without" else "With player"
    assert {"label": label, "value": PAIR, "kind": "player"} in result.metadata["applied_filters"]


def test_pair_is_conjunction_not_union_or_last_named_player(qualified_pair):
    fixture = qualified_pair
    a, b, c, _ = fixture["ids"]
    assert set(_apply(fixture["teams"], "LeBron James").game_id) == {a, b}
    assert set(_apply(fixture["teams"], "Anthony Davis").game_id) == {a, c}
    assert set(_apply(fixture["teams"], PAIR).game_id) == {a}
    assert set(_apply(fixture["teams"], "Anthony Davis and LeBron James").game_id) == {a}


@pytest.mark.parametrize("damage", ["unknown", "missing", "wrong_date", "conflicting_played"])
def test_pair_qualifies_both_names_across_original_sample(qualified_pair, damage):
    fixture = qualified_pair
    # Unknown affects the both-DNP game, with no positive row to fill the gap.
    # The last game has LeBron playing: a false first predicate cannot hide
    # missing second-player coverage. The conflict contradicts canonical play.
    target = fixture["ids"][0 if damage == "unknown" else 3]
    mask = fixture["ledger"].game_id.eq(target) & fixture["ledger"].player_id.eq(203076)
    if damage == "unknown":
        fixture["ledger"].loc[mask, "participation_state"] = "unknown"
    elif damage == "missing":
        fixture["ledger"].drop(fixture["ledger"].index[mask], inplace=True)
        # Canonical positive minutes independently qualify a played row; remove
        # that positive observation as well so this is truly unknown coverage.
        from nbatools.commands import data_utils

        original = data_utils.load_player_games_for_seasons
        frame = original([SEASON], "Regular Season")
        frame = frame.loc[
            ~(frame.game_id.astype(int).eq(fixture["ids"][3]) & frame.player_id.eq(203076))
        ]
        from unittest.mock import patch

        with patch.object(data_utils, "load_player_games_for_seasons", return_value=frame):
            with pytest.raises(ValueError, match="coverage"):
                _apply(fixture["teams"], PAIR)
        return
    elif damage == "wrong_date":
        fixture["ledger"].loc[mask, "game_date"] = "1900-01-01"
    else:
        fixture["ledger"].loc[mask, "participation_state"] = "did_not_play"
    with pytest.raises(ValueError, match="Contradictory|Unqualified"):
        _apply(fixture["teams"], PAIR)


@pytest.mark.parametrize(
    "clause,mode",
    [
        ("without LeBron James and Anthony Davis", "without"),
        ("with LeBron James and Anthony Davis both out", "without"),
        ("with LeBron James and Anthony Davis not playing", "without"),
        ("with LeBron James and Anthony Davis DNP", "without"),
        ("with LeBron James and Anthony Davis both playing", "with"),
    ],
)
def test_team_pair_wording_preserves_condition_and_exact_sample(qualified_pair, clause, mode):
    game = qualified_pair["ids"][0 if mode == "without" else 3]
    expected = qualified_pair["teams"].loc[qualified_pair["teams"].game_id.eq(game)]
    result = execute_natural_query(f"Lakers record vs Celtics {clause} in {SEASON}")
    _assert_answer(result, expected, mode=mode)


def test_existing_native_cooperative_pair_last_n_is_preserved(qualified_pair):
    expected = qualified_pair["teams"].loc[
        qualified_pair["teams"].game_id.eq(qualified_pair["ids"][3])
    ]
    result = execute_natural_query(
        "Lakers record vs Celtics last 1 game with LeBron James and Anthony Davis both playing in 2023-24"
    )
    _assert_answer(result, expected, mode="with")


@pytest.mark.parametrize(
    "query",
    [
        "Austin Reaves games with at least 10 points vs Celtics without LeBron James and Anthony Davis in 2023-24",
        "Austin Reaves games without LeBron James and Anthony Davis with at least 10 points vs Celtics in 2023-24",
        "Austin Reaves games with at least 10 points vs Celtics with LeBron James and Anthony Davis both out in 2023-24",
    ],
)
def test_player_own_bound_and_pair_keep_both_conditions(qualified_pair, query):
    rows = qualified_pair["players"]
    expected = rows.loc[
        rows.player_id.eq(1630559) & rows.pts.ge(10) & rows.game_id.eq(qualified_pair["ids"][0])
    ]
    assert len(expected) == 1
    _assert_answer(execute_natural_query(query), expected, player=True)


def test_structured_pair_and_subject_bound_are_already_execution_backed(qualified_pair):
    rows = qualified_pair["players"]
    expected = rows.loc[
        rows.player_id.eq(1630559) & rows.pts.ge(10) & rows.game_id.eq(qualified_pair["ids"][0])
    ]
    result = execute_structured_query(
        "player_game_finder",
        player="Austin Reaves",
        stat="pts",
        min_value=10,
        opponent="BOS",
        season=SEASON,
        without_player=PAIR,
    )
    _assert_answer(result, expected, player=True)


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and with Anthony Davis",
        "with Anthony Davis and without LeBron James",
        "with LeBron James out and with Anthony Davis",
        "with LeBron James OUT and Anthony Davis playing",
        "when LeBron James is out and Anthony Davis plays",
        "with Anthony Davis playing and LeBron James out",
        "with LeBron James not playing and Anthony Davis playing",
        "when LeBron James did not play and Anthony Davis played",
    ],
)
def test_mixed_polarity_preserves_each_clause_and_team_subject(qualified_pair, clause):
    expected = qualified_pair["teams"].loc[
        qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])
    ]
    result = execute_natural_query(f"Lakers record vs Celtics {clause} in {SEASON}")
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    assert result.route == "team_record"
    assert result.metadata["player"] is None
    assert result.metadata["with_player"] == "Anthony Davis"
    assert result.metadata["without_player"] == "LeBron James"
    sections = result.result.to_dict()["sections"]
    assert {int(r["game_id"]) for r in sections["game_log"]} == set(expected.game_id)
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (
        1,
        int(expected.wl.eq("W").sum()),
        int(expected.wl.eq("L").sum()),
        expected.pts.item(),
    )
    assert {"label": "With player", "value": "Anthony Davis", "kind": "player"} in result.metadata[
        "applied_filters"
    ]
    assert {
        "label": "Without player",
        "value": "LeBron James",
        "kind": "player",
    } in result.metadata["applied_filters"]


@pytest.mark.parametrize("last_scope", [None, "qualifying", "window"])
def test_positive_sibling_cannot_hide_unknown_absence_on_original_candidates(
    qualified_pair, last_scope
):
    from nbatools.commands.team_record import build_team_record_result

    fixture = qualified_pair
    # Davis is explicitly absent in this game: a positive-Davis filter would
    # erase it. LeBron's unknown absence must still block the conjunction.
    mask = fixture["ledger"].game_id.eq(fixture["ids"][0]) & fixture["ledger"].player_id.eq(2544)
    fixture["ledger"].loc[mask, "participation_state"] = "unknown"
    kwargs = dict(
        team="LAL",
        opponent="BOS",
        season=SEASON,
        with_player="Anthony Davis",
        without_player="LeBron James",
    )
    if last_scope:
        kwargs.update(last_n=1, last_n_scope=last_scope)
    with pytest.raises(ValueError, match="Unqualified|coverage"):
        build_team_record_result(**kwargs)
    result = execute_natural_query(
        f"Lakers record vs Celtics without LeBron James and with Anthony Davis in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


def test_date_scope_is_owned_before_mixed_participation_qualification(qualified_pair):
    fixture = qualified_pair
    mask = fixture["ledger"].game_id.eq(fixture["ids"][0]) & fixture["ledger"].player_id.eq(2544)
    fixture["ledger"].loc[mask, "participation_state"] = "unknown"
    expected = fixture["teams"].loc[fixture["teams"].game_id.eq(fixture["ids"][1])]
    day = expected.game_date.item()
    result = execute_natural_query(
        f"Lakers record without LeBron James and with Anthony Davis vs Celtics in {SEASON} from {day} to {day}"
    )
    assert result.result_status == "ok", result.metadata
    assert {int(r["game_id"]) for r in result.result.to_dict()["sections"]["game_log"]} == set(
        expected.game_id
    )


def test_structured_request_preserves_both_scalar_predicates(qualified_pair):
    result = execute_structured_query(
        "team_record",
        team="LAL",
        opponent="BOS",
        season=SEASON,
        without_player="LeBron James",
        with_player="Anthony Davis",
    )
    assert result.result_status == "ok", result.metadata
    assert {int(r["game_id"]) for r in result.result.to_dict()["sections"]["game_log"]} == {
        qualified_pair["ids"][1]
    }
    assert (
        result.metadata["without_player"] == "LeBron James"
        and result.metadata["with_player"] == "Anthony Davis"
    )


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and Anthony Davis playing",
        "with LeBron James and Anthony Davis both out",
    ],
)
def test_shared_negative_name_list_is_not_reinterpreted_as_mixed(qualified_pair, clause):
    expected = qualified_pair["teams"].loc[
        qualified_pair["teams"].game_id.eq(qualified_pair["ids"][0])
    ]
    result = execute_natural_query(f"Lakers record vs Celtics {clause} in {SEASON}")
    _assert_answer(result, expected)


def test_legacy_lebron_luka_gerund_keeps_shared_negative_parse():
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(
        "Lakers record without LeBron and Luka playing from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["with_player"] is None
    assert parsed["route_kwargs"]["without_player"] == "LeBron James and Luka Dončić"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.parametrize(
    "clause",
    [
        "with LeBron James out and Anthony Davis playing",
        "without LeBron James and with Anthony Davis",
        "without LeBron James while Anthony Davis plays",
    ],
)
def test_independently_marked_states_keep_mixed_polarity(qualified_pair, clause):
    result = execute_natural_query(f"Lakers record vs Celtics {clause} in {SEASON}")
    assert result.result_status == "ok", result.metadata
    assert result.metadata["without_player"] == "LeBron James"
    assert result.metadata["with_player"] == "Anthony Davis"
    assert {int(row["game_id"]) for row in result.result.to_dict()["sections"]["game_log"]} == {
        qualified_pair["ids"][1]
    }


@pytest.mark.parametrize(
    "window", ["last 2 qualifying games", "within their last 2 qualifying games"]
)
def test_mixed_qualifying_window_remains_positive(qualified_pair, window):
    result = execute_natural_query(
        f"Lakers record vs Celtics {window} without LeBron James and with Anthony Davis in {SEASON}"
    )
    assert result.result_status == "ok", result.metadata
    assert result.metadata["last_n_scope"] == "qualifying"
    assert {int(row["game_id"]) for row in result.result.to_dict()["sections"]["game_log"]} == {
        qualified_pair["ids"][1]
    }


@pytest.mark.parametrize(
    "window",
    [
        "within their last 2 games",
        "among their last 2 games",
        "of their last 2 games",
        "in their last 2 original games",
        "in their last 2 original meetings",
    ],
)
def test_mixed_original_window_never_falls_back_to_older_qualifying_game(qualified_pair, window):
    fixture = qualified_pair
    original = set(fixture["teams"].sort_values("game_date").tail(2).game_id)
    assert original == set(fixture["ids"][-2:]) and fixture["ids"][1] not in original
    # The only conjunction match is the older second fixture game, so the
    # qualifying reading would silently change the requested population.
    result = execute_natural_query(
        f"Lakers record vs Celtics {window} without LeBron James and with Anthony Davis in {SEASON}"
    )
    assert result.result_status == "no_result", result.metadata
    assert result.result_reason == "filter_not_supported"
    assert result.metadata["last_n_scope"] == "original_window"
    assert "multi_player_availability" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "extra",
    [
        dict(with_player="Anthony Davis and Austin Reaves"),
        dict(with_player="LeBron James"),
        dict(quarter="1"),
    ],
)
def test_structured_mixed_scope_does_not_expand_to_extra_actors_or_periods(qualified_pair, extra):
    kwargs = dict(
        team="LAL",
        opponent="BOS",
        season=SEASON,
        without_player="LeBron James",
        with_player="Anthony Davis",
    )
    kwargs.update(extra)
    result = execute_structured_query("team_record", **kwargs)
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize("status", ["injured", "healthy", "available", "on the court"])
def test_pair_participation_never_substitutes_for_status(qualified_pair, status):
    result = execute_natural_query(
        f"Lakers record vs Celtics with LeBron James and Anthony Davis {status} in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and with Anthony Davis, scoring at least 30 points",
        "with LeBron James out and Anthony Davis playing,30 points",
        "with Anthony Davis, at least30 points and without LeBron James",
        "without LeBron James, scoring at least30 points and with Anthony Davis",
        "with LeBron James out,10 assists and Anthony Davis playing",
        "without LeBron James and with Anthony Davis, at least35 minutes",
    ],
)
def test_mixed_actor_bound_does_not_become_team_threshold(qualified_pair, clause):
    fixture = qualified_pair
    game = fixture["ids"][1]
    own = fixture["teams"].loc[fixture["teams"].game_id.eq(game)]
    actor = fixture["players"].loc[
        fixture["players"].game_id.eq(game) & fixture["players"].player_id.eq(203076)
    ]
    assert actor.pts.item() < 30 <= own.pts.item()  # AD26 and LAL89 discriminate ownership.
    result = execute_natural_query(f"Lakers record {clause} vs Celtics in {SEASON}")
    assert result.result_status == "no_result", result.metadata
    assert "teammate_stat_condition" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and with Anthony Davis, when Lakers score at least80 points",
        "with LeBron James out and Anthony Davis playing, scoring at least80 points as a team",
    ],
)
def test_mixed_predicates_preserve_explicit_team_owned_threshold(qualified_pair, clause):
    result = execute_natural_query(f"Lakers record {clause} vs Celtics in {SEASON}")
    assert result.result_status == "ok", result.metadata
    assert {int(row["game_id"]) for row in result.result.to_dict()["sections"]["game_log"]} == {
        qualified_pair["ids"][1]
    }


@pytest.mark.parametrize(
    "suffix",
    [
        "not both playing",
        "either out",
        "out and playing",
        "both out with injuries",
        "both out and injured",
        "both out but healthy",
    ],
)
def test_pair_does_not_drop_boolean_or_medical_qualifiers(qualified_pair, suffix):
    result = execute_natural_query(
        f"Lakers record vs Celtics with LeBron James and Anthony Davis {suffix} in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize(
    "extra", ["while Gabe Vincent plays", "when Gabe Vincent plays", ", and Gabe Vincent playing"]
)
def test_team_pair_never_drops_an_additional_named_predicate(qualified_pair, extra):
    result = execute_natural_query(
        f"Lakers record vs Celtics with LeBron James and Anthony Davis both out {extra} in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert "multi_player_availability" in result.metadata["unsupported_filters"]
    assert not result.to_dict()["sections"]
