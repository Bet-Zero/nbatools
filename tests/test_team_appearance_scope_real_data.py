"""Retained Cleveland82 TEAM appearances, not new membership qualification."""

import hashlib
import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.pipeline.team_appearance_coverage import qualify_retained_appearances
from nbatools.data_source import (
    data_generation_context,
    data_path,
    data_read_text,
    reset_data_source_cache,
)
from nbatools.dataframe_cache import clear_frame_cache

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
SOURCES = PROGRAM / "source-evidence"
CLE = 1610612739
PROOF = SOURCES / "team-appearances-cleveland-2024-v1/2024-25_regular_season.json"


def test_published_lakers_mixed_record_preserves_written_dates():
    with data_generation_context() as generation:
        assert generation == "availability-lal-team-2025-v1-20261127"
        manifest = data_read_text("data/metadata/generation_manifest.json")
        assert hashlib.sha256(manifest.encode()).hexdigest() == (
            "2239be14825fed08e13da1cc118dd1082ea1f1edca86661ea39a7503ed5cce50"
        )
        # The existing independent final reports establish the only game in
        # this window with Dončić playing and James explicitly absent.
        query = (
            "Lakers record from October 24, 2025 to October 27, 2025 when "
            "Luka Doncic played but LeBron James did not play in 2025-26"
        )
        response = TestClient(app).post("/query", json={"query": query})
        assert response.status_code == 200
        body = response.json()
        assert (body["route"], body["result_status"]) == ("team_record", "ok"), body
        result = body["result"]
        metadata = result["metadata"]
        assert (
            metadata["participation_scope"],
            metadata["with_player"],
            metadata["without_player"],
        ) == (
            "team",
            "Luka Dončić",
            "LeBron James",
        )
        (summary,) = result["sections"]["summary"]
        assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
            1,
            1,
            0,
            128,
        )
        assert [row["game_id"] for row in result["sections"]["game_log"]] == [22500019]


def test_explicit_role_cannot_reduce_a_mixed_request_on_published_catalog():
    with data_generation_context() as generation:
        assert generation == "availability-season-inactive-2024-v1-20261116"
    client = TestClient(app)
    for clause in (
        "without Caris LeVert when opponent Stephen Curry plays",
        "with Caris LeVert when opponent Stephen Curry plays",
        "when opponent Stephen Curry plays without Caris LeVert",
        "without Stephen Curry when opponent Stephen Curry plays",
        "with Stephen Curry when opponent Stephen Curry plays",
        "without Stephen Curry anywhere in the game and with Caris LeVert",
        "not when opponent Stephen Curry plays",
        "except when opponent Stephen Curry plays",
        "not without Stephen Curry anywhere in the game",
    ):
        query = f"Cavaliers record {clause} vs Warriors in 2024-25"
        body = client.post("/query", json={"query": query}).json()
        assert body["query"] == query and body["result_status"] == "no_result", body
        assert "mixed_participation_roles" in body["result"]["metadata"]["unsupported_filters"]
        assert not body["result"]["sections"]
    oracle = json.loads(
        (SOURCES / "cleveland-full-boxscore-2024/independent/oracle.json").read_bytes()
    )
    games = {
        g["game_id"]: g
        for g in oracle["games"]
        if 1610612744 in (g["home_team_id"], g["away_team_id"])
    }
    assert set(games) == {22400188, 22400446}
    for bound in (False, True):
        query = (
            "Cavaliers record "
            + ("with 120 points " if bound else "")
            + "vs Warriors when opponent Stephen Curry plays in 2024-25"
        )
        body = client.post("/query", json={"query": query}).json()
        assert body["result_status"] == "ok", body
        assert body["result"]["metadata"]["participation_scope"] == "opponent"
        expected = {g for g in games if not bound or games[g]["points_by_team"][str(CLE)] >= 120}
        summary = body["result"]["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (
            len(expected),
            len(expected),
            0,
        )
        assert summary["pts_avg"] == sum(
            games[g]["points_by_team"][str(CLE)] for g in expected
        ) / len(expected)
        assert {int(r["game_id"]) for r in body["result"]["sections"]["game_log"]} == expected


def test_retained_complete_team_lists_unlock_real_team_records(tmp_path, monkeypatch):
    frozen = json.loads(PROOF.read_bytes())
    assert len(frozen["sides"]) == 82 and {s["team_id"] for s in frozen["sides"]} == {CLE}
    parent = json.loads(
        (SOURCES / "cleveland-full-boxscore-2024/independent/oracle.json").read_bytes()
    )
    replacement = json.loads(
        (SOURCES / "cleveland-two-game-2024/independent/source-oracle.json").read_bytes()
    )
    # Independent original-source expectations: no engine/qualifier-built oracle.
    source_rows = parent["accepted_rows"] + replacement["accepted_rows"]
    games = {g["game_id"]: g for g in parent["games"]}
    for report in replacement["reports"]:
        games[report["game_id"]]["points_by_team"] = report["points_by_team"]
    all_games = set(games)
    assert len(all_games) == 82
    root = tmp_path / "consumer/data"
    with data_generation_context() as generation:
        assert generation == "availability-season-inactive-2024-v1-20261116"
        for relative, digest in frozen["dependencies"].items():
            raw = data_path("data/" + relative).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == digest
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    overlay = SOURCES / "cleveland-two-game-2024/qualified-overlay-v2.zip"
    assert (
        hashlib.sha256(overlay.read_bytes()).hexdigest()
        == "a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298"
    )
    with ZipFile(overlay) as z:
        z.extractall(root)
    replay = qualify_retained_appearances(root, "2024-25", "Regular Season", team_ids={CLE})
    assert replay == frozen and not replay["unqualified"]
    target = root / "raw/team_game_appearances/2024-25_regular_season.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(PROOF, target)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    client = TestClient(app)
    receipts = []

    def check(body, keys, scope="team"):
        metadata = body["result"]["metadata"]
        assert metadata["team"] == "CLE" and metadata["team_context"]["team_abbr"] == "CLE"
        assert metadata["season"] == "2024-25" and metadata["season_type"] == "Regular Season"
        assert metadata["participation_scope"] == scope
        if not keys:
            assert body["result_status"] == "no_result" and body["result_reason"] == "no_match"
            assert not body["result"]["sections"]
            return
        assert body["result_status"] == "ok", body
        summary = body["result"]["sections"]["summary"][0]
        assert summary["team_name"] == "Cleveland Cavaliers"
        assert summary["season_start"] == summary["season_end"] == "2024-25"
        assert summary["season_type"] == "Regular Season"
        assert summary["games"] == len(keys)
        assert summary["pts_avg"] == round(
            sum(games[g]["points_by_team"][str(CLE)] for g in keys) / len(keys), 3
        )
        wins = sum(
            games[g]["points_by_team"][str(CLE)]
            > games[g]["points_by_team"][
                str(
                    games[g]["away_team_id"]
                    if games[g]["home_team_id"] == CLE
                    else games[g]["home_team_id"]
                )
            ]
            for g in keys
        )
        assert (summary["wins"], summary["losses"]) == (wins, len(keys) - wins)
        assert {int(r["game_id"]) for r in body["result"]["sections"]["game_log"]} == keys

    cohort = replacement["cleveland_cohort"] + [dict(player_id=201939, player_name="Stephen Curry")]
    for actor in cohort:
        played = {
            r["game_id"]
            for r in source_rows
            if r["team_id"] == CLE
            and r["player_id"] == actor["player_id"]
            and r["participation_state"] == "played"
        }
        for relation, keys in (("with", played), ("without", all_games - played)):
            request = dict(
                route="team_record",
                kwargs=dict(
                    team="CLE",
                    season="2024-25",
                    season_type="Regular Season",
                    **{relation + "_player": actor["player_name"]},
                ),
            )
            response = client.post("/structured-query", json=request)
            assert response.status_code == 200
            body = response.json()
            assert body["result"]["metadata"]["participation_scope"] == "team"
            check(body, keys)
            receipts.append(dict(player=actor["player_name"], relation=relation, games=len(keys)))
    for name, query_relation in [
        ("Caris LeVert", "without"),
        ("De'Andre Hunter", "without"),
        ("Stephen Curry", "without"),
    ]:
        body = client.post(
            "/query", json={"query": f"Cavaliers record {query_relation} {name} in 2024-25"}
        ).json()
        actor = next(c for c in cohort if c["player_name"] == name)
        played = {
            r["game_id"]
            for r in source_rows
            if r["team_id"] == CLE
            and r["player_id"] == actor["player_id"]
            and r["participation_state"] == "played"
        }
        check(body, all_games - played)
        assert any(
            f["kind"] == "participation_scope"
            for f in body["result"]["metadata"]["applied_filters"]
        )
    # Curry played against CLE in both GSW games, but never FOR Cleveland.
    own = client.post(
        "/query", json={"query": "Cavaliers record without Stephen Curry vs Warriors in 2024-25"}
    ).json()
    warriors_games = {
        g for g in games if 1610612744 in (games[g]["home_team_id"], games[g]["away_team_id"])
    }
    assert len(warriors_games) == 2
    check(own, warriors_games)
    anywhere = client.post(
        "/query",
        json={
            "query": "Cavaliers record without Stephen Curry anywhere in the game vs Warriors in 2024-25"
        },
    ).json()
    check(anywhere, set(), "game")
    opposing = client.post(
        "/query",
        json={"query": "Cavaliers record vs Warriors when opponent Stephen Curry plays in 2024-25"},
    ).json()
    check(opposing, warriors_games, "opponent")
    rostered = client.post(
        "/query",
        json={"query": "Cavaliers record without Caris LeVert while on the team in 2024-25"},
    ).json()
    assert rostered["result_status"] == "no_result" and rostered["result_reason"] != "no_match"
    # BKN199 remains genuinely unqualified: no team-side list, no invented No.
    incomplete = client.post(
        "/structured-query",
        json=dict(
            route="team_record",
            kwargs=dict(
                team="BKN",
                season="2024-25",
                start_date="2024-11-09",
                end_date="2024-11-09",
                without_player="Stephen Curry",
            ),
        ),
    ).json()
    assert incomplete["result_status"] == "no_result" and incomplete["result_reason"] != "no_match"
    assert not incomplete["result"]["sections"]
    if output := os.environ.get("NBATOOLS_ACQUISITION_OUTPUT"):
        path = Path(output).resolve() / "team-appearance-proof"
        path.mkdir(parents=True, exist_ok=True)
        (path / "answers.json").write_text(json.dumps(receipts, indent=2))
    reset_data_source_cache()
    clear_frame_cache()
