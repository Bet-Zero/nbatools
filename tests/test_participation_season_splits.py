"""S4 fixture contract: explicit participation and sparse seasons precede splitting."""

from __future__ import annotations

import shutil
from functools import wraps
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations, player_split_summary, team_split_summary
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
FIXTURE = Path(__file__).resolve().parents[1] / "qa/fixtures/query_engine_sample/data"
SEASONS = ["2023-24", "2025-26"]


@pytest.fixture
def explicit_participation(tmp_path, monkeypatch):
    root = tmp_path / "data"
    shutil.copytree(FIXTURE, root)
    observations, raw = [], {}
    for season in SEASONS:
        teams = pd.read_csv(root / f"raw/team_game_stats/{season}_regular_season.csv")
        path = root / f"raw/player_game_stats/{season}_regular_season.csv"
        players = pd.read_csv(path)
        candidates = teams.loc[teams.team_abbr.eq("BOS") & teams.opponent_team_abbr.eq("LAL")]
        named = players.player_name.eq("Jayson Tatum") & players.game_id.isin(candidates.game_id)
        explicit = players.loc[named].copy()
        assert len(explicit) == len(candidates) > 1
        explicit["participation_state"] = "played" if season == SEASONS[0] else "did_not_play"
        explicit["coverage_scope"] = "controlled_fixture"
        explicit["source"] = "synthetic_test_observation"
        observations.append(explicit)
        if season == SEASONS[1]:
            players = players.loc[~named]
            players.to_csv(path, index=False)
        raw[season] = (
            candidates,
            players.loc[
                players.player_name.eq("Jaylen Brown") & players.game_id.isin(candidates.game_id)
            ],
        )
    # An excluded intermediate year must not become a data dependency or a
    # participation-coverage requirement. Never modify the committed fixture.
    for path in root.rglob("2024-25*"):
        if path.is_file():
            path.unlink()
    observed = pd.concat(observations, ignore_index=True)

    def load(seasons, season_type):
        assert seasons == SEASONS or len(seasons) == 1 and seasons[0] in SEASONS
        assert season_type == "Regular Season"
        return observed.loc[observed.season.isin(seasons)].copy()

    monkeypatch.setattr(_participation_observations, "load_observations", load)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    yield raw
    reset_data_source_cache()


@pytest.mark.parametrize(
    "kind,subject", [("team", "Celtics record"), ("player", "Jaylen Brown stats")]
)
@pytest.mark.parametrize("relation", ["with", "without"])
def test_participation_survives_named_season_split(
    explicit_participation, monkeypatch, kind, subject, relation
):
    module = team_split_summary if kind == "team" else player_split_summary
    helper = "select_team_summary_sample" if kind == "team" else "select_player_summary_sample"
    original = getattr(module, helper)
    captured = []

    @wraps(original)
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.append(result.copy() if isinstance(result, pd.DataFrame) else result.df.copy())
        return result

    monkeypatch.setattr(module, helper, capture)
    selected_season = SEASONS[0 if relation == "with" else 1]
    empty_season = SEASONS[1 if relation == "with" else 0]
    expected = explicit_participation[selected_season][0 if kind == "team" else 1]
    questions = [
        f"{subject} vs Lakers {relation} Jayson Tatum in 2023-24 and 2025-26",
        f"{subject} {relation} Jayson Tatum against Lakers in 2023-24 and 2025-26",
    ]
    results = [execute_natural_query(query) for query in questions]
    identity = {"team": "BOS"} if kind == "team" else {"player": "Jaylen Brown"}
    results.append(
        execute_structured_query(
            f"{kind}_split_summary",
            split="season",
            start_season=SEASONS[0],
            end_season=SEASONS[1],
            split_seasons=SEASONS,
            opponent="LAL",
            **identity,
            **{relation + "_player": "Jayson Tatum"},
        )
    )
    assert len(captured) == len(results)
    expected_keys = set(zip(expected.game_id.astype(int), expected.team_id.astype(int)))
    for result, sample in zip(results, captured):
        assert result.result_status == "ok", (result.result_reason, result.metadata)
        assert set(zip(sample.game_id.astype(int), sample.team_id.astype(int))) == expected_keys
        assert set(sample.season) == {selected_season}
        sections = result.result.to_dict()["sections"]
        assert sections["summary"][0]["games_total"] == len(expected)
        rows = sections["split_comparison"]
        assert len(rows) == 1 and rows[0]["bucket"] == selected_season
        assert (rows[0]["games"], rows[0]["wins"], rows[0]["losses"]) == (
            len(expected),
            int(expected.wl.eq("W").sum()),
            int(expected.wl.eq("L").sum()),
        )
        assert rows[0]["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
        assert "no games in " + empty_season in result.result.to_dict()["caveats"]
    from tests.participation_contract_helpers import assert_single_season_controls

    assert_single_season_controls(kind, relation, selected_season, expected, monkeypatch)
    for result in results[:2]:
        badges = {row["label"]: row["value"] for row in result.metadata["applied_filters"]}
        assert badges[relation.capitalize() + " player"] == "Jayson Tatum"
        assert badges["Opponent"] == "LAL"
        assert badges["Seasons"] == ", ".join(SEASONS)


def test_missing_with_player_rows_cannot_return_unfiltered_sample(explicit_participation):
    from nbatools.commands.player_game_summary import select_player_summary_sample

    # Curry is a known NBA identity but has no same-team participation with Brown.
    # An unresolved name also must not silently turn this into all Brown games.
    for teammate in ["Stephen Curry", "Missing Test Player"]:
        sample = select_player_summary_sample(
            start_season=SEASONS[0],
            end_season=SEASONS[1],
            sample_seasons=SEASONS,
            player="Jaylen Brown",
            opponent="LAL",
            with_player=teammate,
        )
        assert sample.df.empty


@pytest.mark.parametrize("seasons", ["2023-24", "2023-24 and 2025-26"])
def test_teammate_owned_threshold_is_not_applied_to_subject(explicit_participation, seasons):
    for condition in ["scoring 20 points", "playing and scoring 20 points"]:
        wrong_owner = execute_natural_query(
            f"Jaylen Brown stats with Tatum {condition} in {seasons}"
        )
        assert wrong_owner.result_status != "ok"
        assert "teammate_stat_condition" in wrong_owner.metadata["unsupported_filters"]
    own_bound = execute_natural_query(
        f"Jaylen Brown stats scoring 20 points with Tatum in {seasons}"
    )
    assert own_bound.result_status == "ok", own_bound.metadata


@pytest.mark.parametrize("minutes", [0, None, "bad"])
def test_played_requires_positive_canonical_minutes(monkeypatch, minutes):
    from nbatools.commands import data_utils

    players = pd.DataFrame(
        {
            "game_id": [1],
            "team_id": [1610612738],
            "team_abbr": ["BOS"],
            "player_id": [1628369],
            "player_name": ["Jayson Tatum"],
            "minutes": [minutes],
        }
    )
    monkeypatch.setattr(data_utils, "load_player_games_for_seasons", lambda *a: players)
    candidates = players[["game_id", "team_id", "team_abbr"]].copy()
    assert data_utils.filter_with_player(
        candidates, "Jayson Tatum", SEASONS, "Regular Season"
    ).empty
    players["minutes"] = 0.1
    assert (
        len(data_utils.filter_with_player(candidates, "Jayson Tatum", SEASONS, "Regular Season"))
        == 1
    )


def test_teammate_condition_keeps_unresolved_name_and_new_subject(explicit_participation):
    ambiguous = execute_natural_query(
        "Stephen Curry averages with Thompson scoring at least 20 points in 2023-24 and 2025-26"
    )
    assert ambiguous.result_status != "ok"
    assert "teammate_stat_condition" in ambiguous.metadata["unsupported_filters"]
    owned = execute_natural_query(
        "Jaylen Brown stats with Tatum playing and Brown scoring 20 points in 2023-24 and 2025-26"
    )
    assert owned.result_status == "ok", owned.metadata
