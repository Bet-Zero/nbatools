"""Two LeBron appearances qualify; overlap between OR branches counts once."""

import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads((Path(__file__).parent / "fixtures/or_list_scope/primary.json").read_text())


def test_or_preserves_the_complete_opponent_sample_and_subject():
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    expected = ORACLE["case"]
    result = execute_natural_query(expected["query"])
    assert result.result_status == "ok", result.metadata
    assert result.route == "player_game_finder"
    meta = result.metadata
    assert meta["player_context"]["player_id"] == expected["player_id"]
    assert meta["team"] is None
    assert meta["opponents"] == expected["base_opponents"]
    assert meta["boolean_filter_mode"] == "any"
    assert [
        {key: condition.get(key) for key in ("stat", "min_value", "max_value")}
        for condition in meta["conditions"]
    ] == [
        {"stat": "pts", "min_value": 30, "max_value": None},
        {"stat": "ast", "min_value": 9, "max_value": None},
    ]
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
