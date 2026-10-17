"""Assertions shared by controlled and actual participation contract checks."""

from functools import wraps

import pytest

from nbatools.commands import team_record
from nbatools.query_service import execute_natural_query, execute_structured_query


def assert_single_season_controls(kind, relation, season, expected, monkeypatch):
    captured = []
    compute = team_record._compute_record

    @wraps(compute)
    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    with monkeypatch.context() as scope:
        scope.setattr(team_record, "_compute_record", capture)
        subject = "Celtics record" if kind == "team" else "Jaylen Brown averages"
        route = "team_record" if kind == "team" else "player_game_summary"
        identity = {"team": "BOS"} if kind == "team" else {"player": "Jaylen Brown"}
        results = [
            execute_natural_query(f"{subject} vs Lakers {relation} Jayson Tatum in {season}"),
            execute_structured_query(
                route,
                season=season,
                opponent="LAL",
                **identity,
                **{relation + "_player": "Jayson Tatum"},
            ),
        ]
        if kind == "team":
            assert len(captured) == 2
        for index, result in enumerate(results):
            assert result.result_status == "ok", result.metadata
            assert result.route == route
            sections = result.result.to_dict()["sections"]
            summary = sections["summary"][0]
            assert summary["games"] == len(expected)
            assert summary["wins"] == expected.wl.eq("W").sum()
            assert summary["losses"] == expected.wl.eq("L").sum()
            assert summary["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
            keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
            rows = captured[index].to_dict("records") if kind == "team" else sections["game_log"]
            assert {tuple(int(row[key]) for key in keys) for row in rows} == set(
                map(tuple, expected[keys].astype(int).to_numpy())
            )
        labels = {r["label"]: r["value"] for r in results[0].metadata["applied_filters"]}
        assert labels[relation.capitalize() + " player"] == "Jayson Tatum"
        assert labels["Opponent"] == "LAL"
        assert results[0].metadata["season"] == season
