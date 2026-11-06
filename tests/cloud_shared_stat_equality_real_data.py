"""Pinned qualified rows discriminate explicit equality from inclusive floors."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_poeltl_full_season_real_data import build_qualified_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _ids(rows):
    return {int(r["game_id"]) for r in rows}


def _receipt(name, value, tmp_path):
    out = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "stat-equality"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n")


@pytest.mark.parametrize(
    ("player", "player_id", "value", "expected_ids"),
    [
        ("Nikola Jokic", 203999, 30, {22300226, 22301009}),
        ("Anthony Edwards", 1630162, 35, {22300050, 22300451, 22300471}),
    ],
)
def test_qualified_player_equality_all_consumers(player, player_id, value, expected_ids, tmp_path):
    raw = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
    base = raw.loc[raw.player_id.eq(player_id)]
    assert not base.duplicated(["game_id", "team_id", "player_id"]).any()
    expected = base.loc[base.pts.eq(value)]
    assert set(expected.game_id) == expected_ids
    assert len(base.loc[base.pts.ge(value)]) > len(expected)
    question = f"How many games did {player} score exactly {value} points in 2023-24?"
    natural = execute_natural_query(question)
    assert natural.result_status == "ok", natural.metadata
    assert natural.metadata["primary_count"] == len(expected)
    assert f"exactly {value} points" in natural.metadata["count_phrase"]
    assert _ids(natural.to_dict()["sections"]["finder"]) == expected_ids
    summary = execute_natural_query(
        f"{player} average assists with exactly {value} points in 2023-24"
    )
    assert summary.result_status == "ok", summary.metadata
    sections = summary.to_dict()["sections"]
    assert _ids(sections["game_log"]) == expected_ids
    assert sections["summary"][0]["ast_sum"] == int(expected.ast.sum())
    assert sections["summary"][0]["ast_avg"] == pytest.approx(expected.ast.mean(), abs=0.001)
    structured = execute_structured_query(
        "player_game_summary",
        player=player,
        season="2023-24",
        stat="pts",
        min_value=value,
        max_value=value,
    )
    assert _ids(structured.to_dict()["sections"]["game_log"]) == expected_ids
    http = TestClient(app).post("/query", json={"query": question})
    assert http.status_code == 200 and http.json()["result_status"] == "ok"
    assert _ids(http.json()["result"]["sections"]["finder"]) == expected_ids
    _receipt(
        str(player_id),
        dict(
            query=question,
            game_ids=sorted(expected_ids),
            count=len(expected),
            assists_sum=int(expected.ast.sum()),
            assists_mean=float(expected.ast.mean()),
            answer=natural.metadata["count_phrase"],
            summary=sections["summary"][0],
        ),
        tmp_path,
    )


def test_qualified_team_equality_and_full_season_absence(tmp_path, monkeypatch):
    root, teams, players = build_qualified_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    receipts = []
    try:
        own = teams.loc[teams.pts.eq(110)]
        expected = players.loc[players.player_id.eq(1627751)].merge(
            own[["game_id", "team_id"]], on=["game_id", "team_id"]
        )
        assert set(expected.game_id) == {22200209, 22200269, 22201150}
        assert len(expected) == 3
        query = "Jakob Poeltl average rebounds with exactly 110 team points in 2022-23"
        answer = execute_natural_query(query)
        assert answer.result_status == "ok", answer.metadata
        sections = answer.to_dict()["sections"]
        assert _ids(sections["game_log"]) == set(expected.game_id)
        assert sections["summary"][0]["reb_sum"] == int(expected.reb.sum())
        receipts.append(
            dict(
                query=query,
                game_ids=sorted(map(int, expected.game_id)),
                rebounds_sum=int(expected.reb.sum()),
            )
        )
        # Explicit DNPs and finite tenure remain authoritative after the new bound.
        ledger = data_read_csv("raw/player_game_availability/2022-23_regular_season.csv")
        absent = ledger.loc[
            ledger.player_id.eq(1627751) & ledger.participation_state.eq("did_not_play")
        ]
        missed = teams.loc[
            teams.pts.eq(112) & teams.game_id.isin(absent.game_id) & teams.team_abbr.eq("SAS")
        ]
        assert set(missed.game_id) == {22200406, 22200420}
        assert len(missed) == 2
        query = "How many games did Jakob Poeltl miss in 2022-23 with exactly 112 team points?"
        answer = execute_natural_query(query)
        assert answer.result_status == "ok", answer.metadata
        assert answer.metadata["primary_count"] == len(missed)
        assert "exactly 112" in answer.metadata["answer_phrase"]
        assert "112+" not in answer.metadata["answer_phrase"]
        assert _ids(answer.to_dict()["sections"]["finder"]) == set(missed.game_id)
        structured = execute_structured_query(
            "game_finder",
            membership_player="Jakob Poeltl",
            season="2022-23",
            stat="pts",
            min_value=112,
            max_value=112,
            limit=1000,
        )
        assert _ids(structured.to_dict()["sections"]["finder"]) == set(missed.game_id)
        http = TestClient(app).post("/query", json={"query": query})
        assert http.status_code == 200 and http.json()["result_status"] == "ok"
        assert _ids(http.json()["result"]["sections"]["finder"]) == set(missed.game_id)
        receipts.append(
            dict(
                query=query,
                game_ids=sorted(map(int, missed.game_id)),
                count=len(missed),
                answer=answer.metadata["answer_phrase"],
            )
        )
        _receipt("qualified-native", receipts, tmp_path)
    finally:
        reset_data_source_cache()
