"""Frozen Core-1 K03 questions checked against independently selected raw keys."""

import json
from pathlib import Path

import pytest

from nbatools.commands import player_occurrence_leaders as occurrences
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
CASES = json.loads(Path(__file__).with_name("k03_expected.json").read_text())
KEYS = ["game_id", "team_id", "player_id"]


def _keys(rows):
    return {tuple(int(row[k]) for k in KEYS) for row in rows}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_k03_actual_keys_and_count(case, monkeypatch):
    raw = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
    assert not raw.duplicated(KEYS).any()
    ident = case["id"]
    subject = {
        "A1": 203999,
        "A2": 1628973,
        "B1": 203999,
        "B2": 203999,
        "B3": 1630162,
        "B4": 1630162,
        "C1": 1628973,
        "C2": 1630162,
        "E1": 203999,
        "E2": 1628973,
    }.get(ident[4:])
    base = raw if subject is None else raw.loc[raw.player_id.eq(subject)]
    assert len(base) > 0
    selectors = {
        "A1": lambda r: r.ast.ge(10) & r.tov.eq(0),
        "A2": lambda r: r.ast.ge(8) & r.tov.eq(0),
        "B1": lambda r: r.pts.gt(30),
        "B2": lambda r: r.pts.ge(30),
        "B3": lambda r: r.pts.gt(35),
        "B4": lambda r: r.pts.ge(35),
        "C1": lambda r: r.pts.gt(40) | r.ast.gt(12),
        "C2": lambda r: r.pts.gt(40) | r.reb.gt(12),
        "D1": lambda r: r.pts.ge(50),
        "D2": lambda r: r.pts.ge(50),
        "E1": lambda r: r.pts.ge(80),
        "E2": lambda r: r.pts.ge(80),
    }
    expected = base.loc[selectors[ident[4:]](base)]
    expected_keys = set(map(tuple, case["keys"]))
    assert _keys(expected.to_dict("records")) == expected_keys
    captured = []
    original = occurrences._flag_compound_conditions

    def capture(rows, conditions):
        mask = original(rows, conditions)
        captured.extend(rows.loc[mask].to_dict("records"))
        return mask

    monkeypatch.setattr(occurrences, "_flag_compound_conditions", capture)
    response = execute_natural_query(case["query"])
    assert response.metadata["season"] == "2023-24"
    sections = response.to_dict()["sections"]
    if ident == "K03-E2":
        assert response.result_status == "no_result"
        assert response.result_reason == "no_match"
        assert not sections
        return
    assert response.result_status == "ok", response.to_dict()
    if ident in {"K03-A2", "K03-B1", "K03-B2", "K03-C1", "K03-D1", "K03-D2", "K03-E1"}:
        count = expected.player_id.nunique() if ident == "K03-D2" else len(expected)
        assert sections["count"] == [{"count": count}]
        assert response.metadata["primary_count"] == count
        assert ("players" if ident == "K03-D2" else "games") in response.metadata["count_phrase"]
    actual = (
        captured if response.route == "player_occurrence_leaders" else sections.get("finder", [])
    )
    assert len(actual) == len(expected_keys)
    team_ids = dict(
        raw[["team_abbr", "team_id"]].drop_duplicates().itertuples(index=False, name=None)
    )
    normalized = [dict(row, team_id=team_ids[row["team_abbr"]]) for row in actual]
    assert _keys(normalized) == expected_keys
