"""S3: own scoring, opponent scoring and venue retain distinct owners.

Expected selections come from keyed raw team/player rows, never parsed filters.
Fixture and actual-source executions remain separate acceptance categories.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nbatools.data_source import data_read_csv, data_read_text
from nbatools.query_service import execute_natural_query, execute_structured_query


def _check_subjects(season, monkeypatch):
    from nbatools.commands import team_record

    captured = []
    compute = team_record._compute_record

    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    sources = {}
    for kind in ("team", "player"):
        path = f"data/raw/{kind}_game_stats/{season}_regular_season.csv"
        frame = data_read_csv(path)
        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
        assert not frame.empty
        assert not frame[keys].isna().any().any() and not frame.duplicated(keys).any()
        assert frame.season.eq(season).all() and frame.season_type.eq("Regular Season").all()
        assert (frame.pts.notna() & frame.pts.ge(0) & frame.pts.mod(1).eq(0)).all()
        sources[kind] = frame
        destination = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
        if destination:
            target = Path(destination) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data_read_text(path), encoding="utf-8")
    teams = sources["team"]
    assert teams.wl.isin(["W", "L"]).all()
    assert teams.is_home.isin([True, False]).all()
    # Raw opponent rows establish the opponent's score; no derived engine join.
    team_lookup = teams.set_index(["game_id", "team_id"])
    for kind, name, floor in (("team", "LAL", 110), ("player", "LeBron James", 25)):
        raw = sources[kind]
        sample = raw.loc[
            raw.team_abbr.eq(name) if kind == "team" else raw.player_name.eq(name)
        ].copy()
        assert not sample.empty
        opponent_points, at_home, outcomes = [], [], []
        for row in sample.itertuples():
            own = team_lookup.loc[(row.game_id, row.team_id)]
            other = team_lookup.loc[(row.game_id, own.opponent_team_id)]
            assert other.opponent_team_id == row.team_id
            opponent_points.append(other.pts)
            at_home.append(bool(own.is_home))
            outcomes.append(own.wl)
        sample["raw_opponent_pts"] = opponent_points
        sample["raw_home"] = at_home
        sample["raw_wl"] = outcomes
        own_mask = sample.pts.ge(floor)
        opponent_mask = sample.raw_opponent_pts.lt(110)
        location_mask = sample.raw_home
        selected = sample.loc[own_mask & opponent_mask & location_mask]
        assert not selected.empty, f"Missing positive {kind} S3 source sample"
        for omitted in (
            own_mask & opponent_mask,
            own_mask & location_mask,
            opponent_mask & location_mask,
        ):
            assert omitted.sum() > len(selected), f"Each {kind} S3 condition must discriminate"
        expected_keys = set(zip(selected.game_id.astype(int), selected.team_id.astype(int)))
        if kind == "team":
            questions = [
                f"Lakers home record when they score at least 110 points and allow under 110 points in {season}",
                f"Lakers record at home when opponents score under 110 points and the Lakers score at least 110 points in {season}",
            ]
            route, identity = "team_record", {"team": name}
        else:
            questions = [
                f"LeBron James averages at home with at least 25 points when opponents score under 110 points in {season}",
                f"LeBron James averages at home when opponents score under 110 points and LeBron scores at least 25 points in {season}",
            ]
            route, identity = "player_game_summary", {"player": name}
        captured.clear()
        results = [execute_natural_query(query) for query in questions]
        results.append(
            execute_structured_query(
                route,
                season=season,
                home_only=True,
                conditions=[
                    {"stat": "pts", "min_value": floor},
                    {"stat": "opponent_pts", "max_value": 109},
                ],
                **identity,
            )
        )
        if kind == "team":
            assert len(captured) == len(results)
        for index, result in enumerate(results):
            assert result.result_status == "ok", result.metadata
            sections = result.to_dict()["sections"]
            log = captured[index].to_dict("records") if kind == "team" else sections["game_log"]
            assert len(log) == len(selected)
            assert {(int(r["game_id"]), int(r["team_id"])) for r in log} == expected_keys
            summary = sections["summary"][0]
            assert summary["games"] == len(selected)
            assert summary["wins"] == selected.raw_wl.eq("W").sum()
            assert summary["losses"] == selected.raw_wl.eq("L").sum()
            assert summary["pts_avg"] == pytest.approx(selected.pts.mean(), abs=0.001)
            if kind == "player":
                assert {
                    (int(r["game_id"]), int(r["team_id"]), int(r["player_id"])) for r in log
                } == set(
                    zip(
                        selected.game_id.astype(int),
                        selected.team_id.astype(int),
                        selected.player_id.astype(int),
                    )
                )
                assert {r["player_name"] for r in log} == {name}
                assert summary["pts_sum"] == selected.pts.sum()
        for result in results[:2]:
            assert result.metadata["team" if kind == "team" else "player"] == name
            labels = result.metadata["applied_filters"]
            assert {"label": "Location", "value": "Home", "kind": "location"} in labels
            assert {"label": "pts min", "value": f"{floor:.1f}", "kind": "threshold"} in labels
            assert {
                "label": "OPP PTS max",
                "value": "110 (exclusive)",
                "kind": "threshold",
            } in labels


@pytest.mark.fixture_data
@pytest.mark.query
def test_s3_owned_scoring_and_venue_fixture(monkeypatch):
    _check_subjects("2025-26", monkeypatch)


@pytest.mark.needs_data
@pytest.mark.query
def test_s3_owned_scoring_and_venue_actual_data(monkeypatch):
    _check_subjects("2023-24", monkeypatch)
