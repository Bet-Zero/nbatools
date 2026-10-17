"""S4 numeric acceptance from four independently qualified official reports."""

from __future__ import annotations

from functools import wraps

import pandas as pd
import pytest

from nbatools.commands import player_split_summary, team_split_summary
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_pipeline_player_game_availability_real_data import _stage_celtics_lakers_reports

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_qualified_participation_and_opponent_survive_nonadjacent_season_splits(
    tmp_path, monkeypatch
):
    root = _stage_celtics_lakers_reports(tmp_path)
    seasons = ["2023-24", "2025-26"]
    source = {}
    for season in seasons:
        source[season] = {
            kind: pd.read_csv(root / f"raw/{kind}/{season}_regular_season.csv")
            for kind in ["player_game_stats", "team_game_stats", "player_game_availability"]
        }
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        for kind, subject in [("team", "Celtics record"), ("player", "Jaylen Brown stats")]:
            module = team_split_summary if kind == "team" else player_split_summary
            helper = (
                "select_team_summary_sample" if kind == "team" else "select_player_summary_sample"
            )
            original = getattr(module, helper)
            captured = []

            @wraps(original)
            def capture(*args, **kwargs):
                result = original(*args, **kwargs)
                captured.append(
                    result.copy() if isinstance(result, pd.DataFrame) else result.df.copy()
                )
                return result

            with monkeypatch.context() as scope:
                scope.setattr(module, helper, capture)
                for relation, state in [("with", "played"), ("without", "did_not_play")]:
                    expected = []
                    for season, frames in source.items():
                        evidence = frames["player_game_availability"]
                        games = evidence.loc[
                            evidence.player_id.eq(1628369)
                            & evidence.team_id.eq(1610612738)
                            & evidence.participation_state.eq(state),
                            "game_id",
                        ]
                        rows = frames["team_game_stats" if kind == "team" else "player_game_stats"]
                        rows = rows.loc[
                            rows.game_id.isin(games)
                            & rows.team_id.eq(1610612738)
                            & rows.opponent_team_abbr.eq("LAL")
                        ]
                        if kind == "player":
                            rows = rows.loc[rows.player_id.eq(1627759)].merge(
                                frames["team_game_stats"][["game_id", "team_id", "wl"]],
                                on=["game_id", "team_id"],
                                validate="many_to_one",
                            )
                        expected.append(rows)
                    expected = pd.concat(expected, ignore_index=True)
                    assert len(expected) == 2
                    selected = "2023-24" if relation == "with" else "2025-26"
                    empty = "2025-26" if relation == "with" else "2023-24"
                    questions = [
                        f"{subject} vs Lakers {relation} Jayson Tatum in 2023-24 and 2025-26",
                        f"{subject} {relation} Jayson Tatum against Lakers in 2023-24 and 2025-26",
                    ]
                    captured.clear()
                    results = [execute_natural_query(q) for q in questions]
                    identity = {"team": "BOS"} if kind == "team" else {"player": "Jaylen Brown"}
                    results.append(
                        execute_structured_query(
                            f"{kind}_split_summary",
                            split="season",
                            start_season=seasons[0],
                            end_season=seasons[1],
                            split_seasons=seasons,
                            opponent="LAL",
                            **identity,
                            **{relation + "_player": "Jayson Tatum"},
                        )
                    )
                    assert len(captured) == len(results)
                    for result, sample in zip(results, captured):
                        assert result.result_status == "ok", (result.result_reason, result.metadata)
                        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
                        assert set(map(tuple, sample[keys].astype(int).to_numpy())) == set(
                            map(tuple, expected[keys].astype(int).to_numpy())
                        )
                        sections = result.result.to_dict()["sections"]
                        assert sections["summary"][0]["games_total"] == 2
                        rows = sections["split_comparison"]
                        assert len(rows) == 1 and rows[0]["bucket"] == selected
                        assert (rows[0]["games"], rows[0]["wins"], rows[0]["losses"]) == (
                            2,
                            int(expected.wl.eq("W").sum()),
                            int(expected.wl.eq("L").sum()),
                        )
                        for stat in ["pts", "reb", "ast"]:
                            assert rows[0][stat + "_avg"] == pytest.approx(
                                expected[stat].mean(), abs=0.001
                            )
                        assert "no games in " + empty in result.result.to_dict()["caveats"]
                    for result in results[:2]:
                        badges = {
                            row["label"]: row["value"] for row in result.metadata["applied_filters"]
                        }
                        assert badges[relation.capitalize() + " player"] == "Jayson Tatum"
                        assert badges["Opponent"] == "LAL"
                        assert badges["Seasons"] == ", ".join(seasons)
    finally:
        reset_data_source_cache()
