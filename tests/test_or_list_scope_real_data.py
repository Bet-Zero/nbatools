"""Two LeBron appearances qualify; overlap between OR branches counts once."""

import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads((Path(__file__).parent / "fixtures/or_list_scope/primary.json").read_text())
CONTROLS = json.loads(
    (Path(__file__).parent / "fixtures/or_list_scope/revealed_controls.json").read_text()
)


@pytest.mark.parametrize("expected", [ORACLE["case"], *CONTROLS["cases"]])
def test_or_preserves_the_complete_opponent_sample_and_subject(expected):
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    result = execute_natural_query(expected["query"])
    assert result.result_status == "ok", result.metadata
    assert result.route == "player_game_finder"
    meta = result.metadata
    assert meta["player_context"]["player_id"] == expected["player_id"]
    assert meta["team"] is None
    assert meta["boolean_filter_mode"] == "any"
    bounds = [
        {"stat": branch["stat"], "min_value": branch["minimum_inclusive"], "max_value": None}
        for branch in expected["branches"]
    ]
    if expected["branches"][0]["opponents"] == expected["branches"][1]["opponents"]:
        assert meta["opponents"] == expected["base_opponents"]
        actual_bounds = meta["conditions"]
    else:
        assert meta["opponent"] is None and not meta.get("opponents")
        assert not meta["conditions"] and not meta["threshold_conditions"]
        branches = meta["boolean_filter_branches"]
        assert [branch["scope"]["opponent"] for branch in branches] == ["DEN", "GSW"]
        assert all(not branch["scope"].get("team") for branch in branches)
        actual_bounds = [branch["conditions"][0] for branch in branches]
        paired = next(f["value"] for f in meta["applied_filters"] if f["kind"] == "boolean")
        assert paired == "(Opponent: DEN; 25+ PTS) OR (Opponent: GSW; 14+ REB)"
    assert [
        {key: condition.get(key) for key in ("stat", "min_value", "max_value")}
        for condition in actual_bounds
    ] == bounds
    rows = result.result.to_dict()["sections"]["finder"]
    assert sorted(int(row["game_id"]) for row in rows) == expected["selected_ids"]
    assert len(rows) == expected["count"] == len({row["game_id"] for row in rows})
    by_id = {row["game_id"]: row for row in expected["selected_rows"]}
    for row in rows:
        truth = by_id[int(row["game_id"])]
        for key in ("player_id", "team_abbr", "opponent_team_abbr", "pts", "reb", "ast", "wl"):
            assert row[key] == truth[key]
    for stat, total in expected["totals"].items():
        assert sum(row[stat] for row in rows) == total
