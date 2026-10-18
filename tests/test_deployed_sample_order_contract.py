"""Deployed S5 evidence; generation attribution is readiness-bracketed only."""

from pathlib import Path

import pytest
import yaml

from tests.sample_order_contract import check_sample_order
from tests.test_deployed_completion_contracts import _query, _ready

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("operation", ["date", "window", "qualifying"])
def test_deployed_s5_sample_order(kind, operation, monkeypatch):
    suffix = "date_opponent" if operation == "date" else "last_n_" + operation
    case_id = "s5_" + kind + "_" + suffix
    corpus = yaml.safe_load(Path("qa/raw_query_answer_corpus.yaml").read_text())
    case = next(row for row in corpus["cases"] if row["id"] == case_id)
    expected = check_sample_order(kind, operation, monkeypatch)
    before = _ready("before-" + case_id)
    payload = _query(case["query"], case_id)
    assert payload["route"] == case["expected_route"]
    assert payload["query"] == case["query"]
    metadata = payload["result"]["metadata"]
    assert metadata["team" if kind == "team" else "player"] == (
        "BOS" if kind == "team" else "Stephen Curry"
    )
    assert metadata["season"] == "2023-24"
    for badge in case["expected_filters"]:
        assert badge in metadata["applied_filters"]
    if operation == "date":
        assert metadata["opponent"] == ("NYK" if kind == "team" else "LAL")
    else:
        assert metadata["stat"] == "pts"
        assert metadata["min_value"] == (110 if kind == "team" else 30)
        assert metadata["last_n"] == 10
        assert metadata["last_n_scope"] == operation
    sections = payload["result"]["sections"]
    row = sections["summary"][0]
    assert row["games"] == len(expected)
    assert row["wins"] == expected.wl.eq("W").sum()
    assert row["losses"] == expected.wl.eq("L").sum()
    for stat in ["pts", "reb", "ast"]:
        assert row[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)
    if kind == "player":
        assert row["pts_sum"] == expected.pts.sum()
    if kind == "player":
        assert "game_log" in sections
    if "game_log" in sections:
        assert len(sections["game_log"]) == len(expected)
        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
        assert {tuple(int(r[k]) for k in keys) for r in sections["game_log"]} == set(
            map(tuple, expected[keys].astype(int).to_numpy())
        )
    assert _ready("after-" + case_id)["active_generation"] == before["active_generation"]
