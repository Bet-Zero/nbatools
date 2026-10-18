"""Pinned source rows distinguish a player's scoring from his team's score."""

import hashlib
import json
from pathlib import Path

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads(
    (Path(__file__).parent / "fixtures/list_owned_stats/primary-source-oracle.json").read_text()
)


def _answer(result, expected):
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    rows = sections["game_log"]
    assert (
        sorted([[int(row[key]) for key in ("game_id", "team_id", "player_id")] for row in rows])
        == expected["keys"]
    )
    summary = sections["summary"][0]
    for field in ("games", "wins", "losses"):
        assert summary[field] == expected[field]
    for stat in ("pts", "reb", "ast"):
        assert summary[stat + "_sum"] == expected["sums"][stat]
        assert summary[stat + "_avg"] == pytest.approx(expected["means"][stat], abs=0.001)


def test_opponent_union_preserves_team_owned_bound():
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    query = ORACLE["query"]
    result = execute_natural_query(query)
    _answer(result, ORACLE["expected"])
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["stat"] == result.metadata["stat"] == "team_pts"
    assert result.metadata["conditions"] == [
        {"stat": "team_pts", "min_value": 120, "max_value": None}
    ]
    assert result.metadata["team"] == "LAL"
    assert result.metadata["player_context"]["player_id"] == 2544
    assert result.metadata["opponents"] == ["BOS", "WAS"]
    for name, abbr in (("Celtics", "BOS"), ("Wizards", "WAS")):
        single = execute_natural_query(query.replace("Celtics and Wizards", name))
        expected = ORACLE["single_opponent_controls"][abbr]
        if not expected["games"]:
            assert single.result_status == "no_result" and single.result_reason == "no_match"
        else:
            _answer(single, expected)
    opposing = execute_natural_query(query.replace("Lakers score", "opponents score"))
    _answer(opposing, ORACLE["opponent_owned_same_floor_control"])


def test_named_opponent_bound_never_selects_other_list_members(monkeypatch):
    from nbatools.commands import team_record

    captured = []
    compute = team_record._compute_record

    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    queries = [
        "Lakers record against Celtics and Wizards when Celtics score at least 120 in 2023-24",
        "Lakers record against Celtics and Wizards when Lakers score at least 110 and Celtics score at least 120 in 2023-24",
    ]
    for query in queries:
        captured.clear()
        result = execute_natural_query(query)
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        assert captured
        assert captured[0][["game_id", "team_id", "opponent_team_id"]].astype(
            int
        ).values.tolist() == [[22300403, 1610612747, 1610612738]]
        summary = sections["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (1, 0, 1)
        assert (summary["pts_avg"], summary["reb_avg"], summary["ast_avg"]) == (115, 43, 24)
        assert result.metadata["opponents"] == ["BOS"]
        assert result.metadata["threshold_conditions"] == result.metadata["conditions"]
    result = execute_natural_query(ORACLE["query"].replace("Lakers score", "Celtics score"))
    _answer(
        result,
        {
            "keys": [[22300403, 1610612747, 2544]],
            "games": 1,
            "wins": 0,
            "losses": 1,
            "sums": {"pts": 16, "reb": 9, "ast": 8},
            "means": {"pts": 16, "reb": 9, "ast": 8},
        },
    )
    assert result.metadata["opponents"] == ["BOS"]
