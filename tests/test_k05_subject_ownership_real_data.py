"""Finite K05: raw reciprocal opponent rows, exact sample keys and clause ownership."""

import hashlib
import json
from functools import wraps
from pathlib import Path

import pytest

from nbatools.commands import team_record
from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
BINDING = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
ORACLE = json.loads((BINDING / "k05-raw-oracle.json").read_text())
HELDOUT = {
    case["id"]: case["query"]
    for case in json.loads((BINDING / "k05-heldout-wording.json").read_text())["cases"]
}
CASES = ORACLE["cases"]


def _qualified_sample(case):
    sources = {}
    for source, expected_hash in ORACLE["sources"].items():
        path = "data/raw/" + source
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == expected_hash
        kind = source.split("_")[0]
        frame = data_read_csv(path)
        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
        assert not frame.empty and not frame[keys].isna().any().any()
        assert not frame.duplicated(keys).any()
        assert frame.season.eq("2023-24").all()
        assert frame.season_type.eq("Regular Season").all()
        sources[kind] = frame
    teams = sources["team"].set_index(["game_id", "team_id"])
    raw = sources[case["kind"]]
    sample = raw.loc[
        raw.team_abbr.eq(case["team"])
        if case["kind"] == "team"
        else raw.player_id.eq(case["player_id"])
    ].copy()
    opponent_points, home, outcomes = [], [], []
    for row in sample.itertuples():
        own = teams.loc[(row.game_id, row.team_id)]
        other = teams.loc[(row.game_id, own.opponent_team_id)]
        assert other.opponent_team_id == row.team_id
        assert bool(own.is_home) != bool(other.is_home)
        opponent_points.append(other.pts)
        home.append(bool(own.is_home))
        outcomes.append(own.wl)
    sample["raw_opponent_pts"] = opponent_points
    sample["raw_home"] = home
    sample["raw_wl"] = outcomes
    own = sample.pts.ge(case["own_pts_min_inclusive"])
    opponent = sample.raw_opponent_pts.lt(case["opponent_pts_max_exclusive"])
    venue = sample.raw_home.eq(case["venue"] == "home")
    discrimination = case["predicate_discrimination"]
    assert (
        int((own & opponent & ~venue).sum()) == discrimination["wrong_venue_otherwise_qualifying"]
    )
    assert (
        int((~own & opponent & venue).sum())
        == discrimination["own_threshold_failed_otherwise_qualifying"]
    )
    assert (
        int((own & ~opponent & venue).sum())
        == discrimination["opponent_threshold_failed_otherwise_qualifying"]
    )
    assert all(value > 0 for value in discrimination.values())
    selected = sample.loc[own & opponent & venue]
    assert sorted(selected[case["key_columns"]].astype(int).values.tolist()) == case["keys"]
    assert len(selected) == case["games"]
    assert int(selected.raw_wl.eq("W").sum()) == case["wins"]
    assert int(selected.raw_wl.eq("L").sum()) == case["losses"]
    for stat, value in case["sums"].items():
        assert selected[stat].sum() == value
        assert selected[stat].mean() == pytest.approx(case["means"][stat])
    return selected


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
@pytest.mark.parametrize("wording", ["primary", "heldout"])
def test_k05_owned_scoring_and_venue(case, wording, monkeypatch):
    sample = _qualified_sample(case)
    player = case["kind"] == "player"
    route = "player_game_summary" if player else "team_record"
    name = sample.player_name.iloc[0] if player else case["team"]
    identity = {"player" if player else "team": name}
    captured = []
    compute = team_record._compute_record

    @wraps(compute)
    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    with monkeypatch.context() as scope:
        scope.setattr(team_record, "_compute_record", capture)
        results = [
            execute_natural_query(case["query"] if wording == "primary" else HELDOUT[case["id"]]),
            execute_structured_query(
                route,
                season=case["season"],
                **identity,
                **{"home_only" if case["venue"] == "home" else "away_only": True},
                conditions=[
                    {"stat": "pts", "min_value": case["own_pts_min_inclusive"]},
                    {"stat": "opponent_pts", "max_value": case["opponent_pts_max_exclusive"] - 1},
                ],
            ),
        ]
    for index, result in enumerate(results):
        assert result.result_status == "ok", (result.result_reason, result.metadata)
        assert result.route == route
        assert result.metadata["season"] == case["season"]
        assert result.metadata["player" if player else "team"] == name
        sections = result.to_dict()["sections"]
        if not player:
            assert len(captured) == 2
        rows = sections["game_log"] if player else captured[index].to_dict("records")
        assert len(rows) == case["games"]
        assert sorted([[int(row[k]) for k in case["key_columns"]] for row in rows]) == case["keys"]
        assert len(sections["summary"]) == 1
        summary = sections["summary"][0]
        for field in ("games", "wins", "losses"):
            assert summary[field] == case[field]
        for stat, mean in case["means"].items():
            assert summary[stat + "_avg"] == pytest.approx(mean, abs=0.001)
            if player:
                assert summary[stat + "_sum"] == case["sums"][stat]
        assert summary["season_start"] == summary["season_end"] == case["season"]
    labels = results[0].metadata["applied_filters"]
    assert {
        "label": "Location",
        "value": "Home" if case["venue"] == "home" else "Away",
        "kind": "location",
    } in labels
    assert {
        "label": "pts min",
        "value": f"{case['own_pts_min_inclusive']:.1f}",
        "kind": "threshold",
    } in labels
    assert {
        "label": "OPP PTS max",
        "value": f"{case['opponent_pts_max_exclusive']} (exclusive)",
        "kind": "threshold",
    } in labels
