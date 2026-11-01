"""Mixed predicates use qualified82-game absence and canonical positive appearances."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv, data_read_text
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/source-evidence"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
LAL = 1610612747


def _assert_numeric(result, expected):
    sections = result["sections"]
    assert {int(row["game_id"]) for row in sections["game_log"]} == set(
        expected.game_id.astype(int)
    )
    assert all(row["season"] == "2025-26" for row in sections["game_log"])
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (
        len(expected),
        int(expected.wl.eq("W").sum()),
        int(expected.wl.eq("L").sum()),
    )
    assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
    assert row["season_start"] == row["season_end"] == "2025-26"


def test_qualified_season_mixed_team_record_and_api(tmp_path, monkeypatch):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    manifest_raw = data_read_text("data/metadata/generation_manifest.json")
    assert hashlib.sha256(manifest_raw.encode()).hexdigest() == MANIFEST
    manifest = json.loads(manifest_raw)
    qualification = json.loads((EVIDENCE / "k08-lebron-remaining/qualification.json").read_text())
    states = json.loads((EVIDENCE / "k08-three-reports/independent-pdf-states.json").read_text())
    population = json.loads(
        (EVIDENCE / "k08-three-reports/independent-pdf-population.json").read_text()
    )
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    teams = teams.loc[teams.team_id.eq(LAL)].copy()
    players = data_read_csv("data/raw/player_game_stats/2025-26_regular_season.csv")
    positive = players.loc[players.team_id.eq(LAL) & pd.to_numeric(players.minutes).gt(0)]
    ledger = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    absent = ledger.loc[
        ledger.team_id.eq(LAL)
        & ledger.player_id.eq(2544)
        & ledger.participation_state.eq("did_not_play")
    ]
    missed = set(absent.game_id.astype(int))
    played = set(positive.loc[positive.player_id.eq(2544), "game_id"].astype(int))
    assert len(teams) == teams.game_id.nunique() == 82
    assert len(missed) == 22 and len(played) == 60 and not missed.intersection(played)
    assert missed == set(qualification["missed_game_ids"])
    assert missed | played == set(teams.game_id.astype(int))
    output = (
        Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "mixed-participation"
    )
    output.mkdir(parents=True, exist_ok=True)
    columns = [
        "game_id",
        "team_id",
        "opponent_team_id",
        "game_date",
        "player_id",
        "player_name",
        "minutes",
        "pts",
        "season",
        "season_type",
    ]
    subsets = {
        "lal-team82.csv": teams,
        "lebron-raw-availability.csv": ledger.loc[
            ledger.team_id.eq(LAL) & ledger.player_id.eq(2544)
        ],
        "lebron-positive-appearances.csv": positive.loc[positive.player_id.eq(2544), columns],
        "luka-reaves-positive-appearances.csv": positive.loc[
            positive.player_id.isin([1629029, 1630559]), columns
        ],
    }
    # Preserve source subsets separately from this diagnostic82-state projection.
    # Positive minutes establish played, never DNP/membership through omission.
    nonplayed = absent.copy().assign(evidence_basis="published_explicit_did_not_play")
    observed_played = (
        positive.loc[positive.player_id.eq(2544), columns]
        .copy()
        .assign(participation_state="played", evidence_basis="canonical_positive_minutes")
    )
    observed = pd.concat([nonplayed, observed_played], ignore_index=True).sort_values("game_id")
    assert len(observed) == observed.game_id.nunique() == 82
    subsets["lebron82-observed-state-projection.csv"] = observed
    subset_hashes = {}
    for name, rows in subsets.items():
        path = output / name
        rows.to_csv(path, index=False)
        subset_hashes[name] = dict(
            rows=len(rows), sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        )
    source_paths = {
        f"raw/{kind}/2025-26_regular_season.csv"
        for kind in ["team_game_stats", "player_game_stats", "player_game_availability"]
    }
    manifest_entries = [item for item in manifest["files"] if item["path"] in source_paths]
    assert {item["path"] for item in manifest_entries} == source_paths
    (output / "raw-oracle-bindings.json").write_text(
        json.dumps(
            dict(
                base_generation=BASE,
                manifest_sha256=MANIFEST,
                source_files=manifest_entries,
                subsets=subset_hashes,
            ),
            indent=2,
        )
        + "\n"
    )
    # This independent projection never invokes runtime participation filters.
    # It makes no inference about Luka/Reaves DNP or membership in other games.
    scope = {22500019, 22500113, 22500122}
    assert {row["game_id"] for row in states} == scope
    for game in states:
        expected = {
            row["player_id"]: row["state"] for row in game["states"] if row["team_id"] == LAL
        }
        assert expected[2544] == "did_not_play"
        assert expected[1630559] == "played"
        assert expected[1629029] == ("played" if game["game_id"] == 22500019 else "did_not_play")
    raw_scores = {
        row["game_id"]: next(side["points"] for side in row["sides"] if side["team_id"] == LAL)
        for row in population
    }
    assert raw_scores == {22500019: 128, 22500113: 127, 22500122: 108}
    for row in absent.itertuples():
        assert pd.Timestamp(row.game_date) == pd.Timestamp(
            teams.loc[teams.game_id.eq(row.game_id), "game_date"].item()
        )
    # Existing single/pair consumers use the same source projection. These
    # regression controls require no additional HTTP requests or source reads.
    single = execute_natural_query("Lakers record without LeBron James in 2025-26")
    assert single.result_status == "ok", single.metadata
    _assert_numeric(single.result.to_dict(), teams.loc[teams.game_id.astype(int).isin(missed)])
    pair = execute_natural_query(
        "Lakers record without LeBron and Luka playing from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert pair.result_status == "ok", pair.metadata
    _assert_numeric(
        pair.result.to_dict(), teams.loc[teams.game_id.astype(int).isin({22500113, 22500122})]
    )
    own = execute_natural_query("LeBron James games with at least 30 points in 2025-26")
    assert own.result_status == "ok" and own.metadata["player"] == "LeBron James"
    own_ids = set(
        positive.loc[positive.player_id.eq(2544) & positive.pts.ge(30), "game_id"].astype(int)
    )
    assert 0 < len(own_ids) <= 25
    assert {int(row["game_id"]) for row in own.result.to_dict()["sections"]["finder"]} == own_ids
    from fastapi.testclient import TestClient

    from nbatools.api import app

    client = TestClient(app)
    answers = []
    for name, pid in [("Luka Doncic", 1629029), ("Austin Reaves", 1630559)]:
        appearances = positive.loc[positive.player_id.eq(pid)]
        assert not appearances.duplicated(["game_id", "player_id"]).any()
        for row in appearances.itertuples():
            assert pd.Timestamp(row.game_date) == pd.Timestamp(
                teams.loc[teams.game_id.eq(row.game_id), "game_date"].item()
            )
        expected_ids = missed & set(appearances.game_id.astype(int))
        for bounded in [True, False]:
            expected = teams.loc[
                teams.game_id.astype(int).isin(
                    expected_ids & (scope if bounded else set(teams.game_id.astype(int)))
                )
            ]
            assert not expected.empty
            if bounded:
                assert set(expected.game_id.astype(int)) == (
                    {22500019} if pid == 1629029 else scope
                )
                assert (len(expected), int(expected.wl.eq("W").sum()), expected.pts.mean()) == (
                    (1, 1, 128) if pid == 1629029 else (3, 2, 121)
                )
            dates = " from 2025-10-24 to 2025-10-27" if bounded else ""
            question = f"Lakers record without LeBron James and with {name} in 2025-26{dates}"
            natural = execute_natural_query(question)
            structured = execute_structured_query(
                "team_record",
                team="LAL",
                season="2025-26",
                without_player="LeBron James",
                with_player=name,
                **(dict(start_date="2025-10-24", end_date="2025-10-27") if bounded else {}),
            )
            for result in [natural, structured]:
                assert result.result_status == "ok", result.metadata
                assert result.route == "team_record" and result.metadata.get("player") is None
                assert (
                    result.metadata["without_player"] == "LeBron James"
                    and result.metadata["with_player"]
                )
                _assert_numeric(result.result.to_dict(), expected)
            if not bounded:
                swapped = execute_natural_query(
                    f"Lakers record with {name} and with LeBron James out in 2025-26"
                )
                assert swapped.result_status == "ok", swapped.metadata
                _assert_numeric(swapped.result.to_dict(), expected)
                response = client.post("/query", json={"query": question})
                assert response.status_code == 200 and response.json()["result_status"] == "ok"
                assert response.json()["route"] == "team_record"
                _assert_numeric(response.json()["result"], expected)
            answers.append(
                dict(
                    query=question,
                    game_ids=sorted(expected.game_id.astype(int).tolist()),
                    games=len(expected),
                    wins=int(expected.wl.eq("W").sum()),
                    losses=int(expected.wl.eq("L").sum()),
                    points=int(expected.pts.sum()),
                )
            )
    (output / "receipt.json").write_text(
        json.dumps(
            dict(
                base_generation=BASE,
                manifest_sha256=MANIFEST,
                absence_population=82,
                positive_only_sibling=True,
                answers=answers,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
    from tools.raw_query_answer_qa import main as raw_qa

    qa_output = (
        Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path)))
        / "mixed-participation-raw-qa"
    )
    with monkeypatch.context() as scope:
        scope.setattr(
            "sys.argv",
            [
                "raw-query-answer-qa",
                "--out",
                str(qa_output),
                "--run-id",
                "mixed-participation",
                "--case",
                "k08_mixed_participation_bounded_record",
                "--case",
                "k08_mixed_participation_out_order_variant",
                "--fail-on-expectation-failure",
            ],
        )
        assert raw_qa() == 0
