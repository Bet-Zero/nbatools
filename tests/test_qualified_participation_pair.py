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


@pytest.mark.parametrize("status", ["injured", "healthy", "available", "on the court"])
def test_pair_participation_never_substitutes_for_status(qualified_pair, status):
    result = execute_natural_query(
        f"Lakers record vs Celtics with LeBron James and Anthony Davis {status} in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


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
