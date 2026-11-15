"""Replay retained whole-team sources against a pinned season, without fetching."""

import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.data_source import data_generation_context, data_path
from tools.assess_team_membership import build_assessment, name_key

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
EVIDENCE = Path(__file__).resolve().parents[1] / (
    "working/nba-tools-completion-program/source-evidence/team-membership-20261114"
)
GENERATION = "availability-participation-2025-durant-v1-20261114"
MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"


def test_bulk_opening_and_movements_expose_membership_unknowns(tmp_path):
    bundle = EVIDENCE / "originals.zip"
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == (
        "60a17134030c73ea0cf76233ca790bbd6d2e5c62265fdd4110e9918f0ee66ade"
    )
    with ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "opening-2023.pdf",
            "player-movement.json",
            "sources.json",
        }
        for name in archive.namelist():
            (tmp_path / name).write_bytes(archive.read(name))
    oracle_raw = (EVIDENCE / "independent-oracle.json").read_bytes()
    assert hashlib.sha256(oracle_raw).hexdigest() == (
        "3cfc88eb66d9e7840e3166101a80db1e60cc2a948330d734319064ad8ea04f10"
    )
    oracle = json.loads(oracle_raw)
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == MANIFEST
        paths = []
        for dataset in ["games", "player_game_stats"]:
            path = data_path(f"data/raw/{dataset}/2023-24_regular_season.csv")
            target = tmp_path / (dataset + ".csv")
            target.write_bytes(path.read_bytes())
            paths.append(target)
        report = build_assessment(EVIDENCE / "sample-request.json", tmp_path, *paths)
    assert report["source"]["native_row_count"] == 10144
    assert report["source"]["earliest"] == "2015-07-01"
    assert report["source"]["latest"] == "2026-11-13"
    assert len(report["source"]["events"]) == 14  # 13 changes plus one conversion
    assert len(report["source"]["ignored"]) == 1
    expected = {
        1610612745: (
            "rockets",
            18,
            22,
            17,
            880,
            924,
            {"member": 1394, "not_member": 246, "unknown": 164},
        ),
        1610612747: (
            "lakers",
            17,
            21,
            21,
            867,
            855,
            {"member": 1420, "not_member": 300, "unknown": 2},
        ),
    }
    for team in report["teams"]:
        label, opening_count, people, played, known, unknown, conditional = expected[
            team["team_id"]
        ]
        assert team["observed_games"] == 82
        assert len(team["opening"]) == opening_count
        assert sum(r["two_way"] for r in team["opening"]) == 3
        assert {name_key(r["source_name"]) for r in team["opening"]} == {
            name_key(n) for n in oracle[f"opening_{label}_names"]
        }
        assert sorted(
            (e["date"], "add" if e["action"] == "member" else "remove", e["player_id"])
            for e in team["events"]
            if e["action"] != "status_only"
        ) == sorted(tuple(r[:3]) for r in oracle[f"{label}_membership_event_oracle"])
        assert team["candidate_people"] == people and team["played_people"] == played
        assert team["conditional_cells"] == conditional
        assert team["exact_game_membership_cells"] == {"member": known, "unknown": unknown}
        assert team["participation_cells"] == {"played": known, "unknown": unknown}
        assert not team["unexplained_appearance_people"]
        assert not team["appearance_contradictions"]
        assert team["complete_membership"] is False and team["accepted_intervals"] == []
        assert team["verified_missed_games"] is None
    hou, lal = report["teams"]
    assert {r["player_id"] for r in hou["opening_conflicts"]} == {1630207, 1631309}
    assert hou["zero_appearance_candidates"] == [203500, 203506, 1630526, 1630620, 1631309]
    assert lal["opening_conflicts"] == []
    boundary = [r for r in lal["cells"] if r["conditional_membership"] == "unknown"]
    assert {(r["game_id"], r["player_id"]) for r in boundary} == {
        (22300869, 1628385),
        (22300869, 1629685),
    }
    # Independently chosen whole-team controls: opener/end absences, zero-
    # appearance trade, late signing, waiver and arbitrary two-way/bench names.
    for team, player, day, conditional in [
        (lal, 1629020, "2023-10-24", "member"),  # Vanderbilt opener
        (lal, 1626174, "2024-04-14", "member"),  # Wood finale
        (hou, 1631106, "2024-04-14", "member"),  # Eason finale
        (hou, 203500, "2024-02-02", "member"),  # Adams after trade
        (hou, 203506, "2024-02-02", "not_member"),  # Oladipo departed
        (lal, 203915, "2024-02-09", "not_member"),  # before Dinwiddie signing
        (lal, 1641788, "2024-01-07", "not_member"),  # Fudge waived
        (hou, 1631257, "2023-10-25", "member"),  # Samuels two-way
    ]:
        cell = next(r for r in team["cells"] if r["player_id"] == player and r["date"] == day)
        assert cell["conditional_membership"] == conditional
        assert cell["participation"] == ("played" if player == 1631257 else "unknown")
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "membership-assessment"
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
