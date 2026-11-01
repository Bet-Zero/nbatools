"""Read-only Tatum/Brown observed-season audit; missing rows stay unknown."""

import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path, data_read_csv, data_read_text
from tools.participation_coverage import build_report

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
GENERATION = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SEASON = "2025-26"
BOS = 1610612738
PEOPLE = (1628369, 1627759)
SUFFIX = SEASON + "_regular_season.csv"


def _raw_oracle(teams, players, ledger):
    dates = {int(r.game_id): pd.Timestamp(r.game_date).date() for r in teams.itertuples()}
    opponents = {int(r.game_id): int(r.opponent_team_id) for r in teams.itertuples()}
    facts = defaultdict(lambda: defaultdict(set))
    for rows, appearance in [(ledger, False), (players, True)]:
        for row in rows.itertuples():
            gid, pid, tid = int(row.game_id), int(row.player_id), int(row.team_id)
            if pid not in PEOPLE or gid not in dates or appearance and not row.minutes > 0:
                continue
            assert pd.Timestamp(row.game_date).date() == dates[gid]
            assert tid in {BOS, opponents[gid]}
            facts[(gid, pid)][tid].add("played" if appearance else row.participation_state)
    expected = {}
    for pid in PEOPLE:
        states = {}
        for gid in dates:
            sides = facts[(gid, pid)]
            assert len(sides) <= 1, "Conflicting exact-game side association"
            values = sides.get(BOS, set())
            assert not values or len(values) == 1 and values <= {"played", "did_not_play"}
            states[gid] = (
                next(iter(values)) if values else "same_game_other_side" if sides else "unknown"
            )
        expected[pid] = states
    return expected


def test_current_tatum_brown_exact_observed_population_and_missing_keys():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == GENERATION
    raw = data_read_text("data/metadata/generation_manifest.json")
    assert hashlib.sha256(raw.encode()).hexdigest() == MANIFEST
    manifest = json.loads(raw)
    teams = data_read_csv("data/raw/team_game_stats/" + SUFFIX)
    teams = teams.loc[teams.team_id.eq(BOS)].copy()
    players = data_read_csv("data/raw/player_game_stats/" + SUFFIX)
    ledger = data_read_csv("data/raw/player_game_availability/" + SUFFIX)
    assert len(ledger) == 804  # 950 is the previously accepted ALL-season total.
    assert len(teams) == teams.game_id.nunique() == 82
    selected = players.loc[players.player_id.isin(PEOPLE)].copy()
    listed = ledger.loc[ledger.player_id.isin(PEOPLE)].copy()
    oracle = _raw_oracle(teams, selected, listed)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "bos-participation-coverage"
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in [
        ("team82.csv", teams),
        ("target-player-rows.csv", selected),
        ("target-ledger-rows.csv", listed),
    ]:
        rows.to_csv(output / name, index=False)
    reports = []
    for pid in PEOPLE:
        report = build_report(
            generation=GENERATION,
            manifest_sha256=MANIFEST,
            season=SEASON,
            team_id=BOS,
            player_id=pid,
        )
        assert report["observed_team_games"] == report["requested_games"] == 82
        assert report["counts"] == {
            state: Counter(oracle[pid].values())[state]
            for state in ["played", "did_not_play", "same_game_other_side", "unknown"]
        }
        # This audit discovers coverage; it never prelabels a missing row DNP.
        incomplete = bool(report["counts"]["unknown"])
        assert report["complete_requested_population"] is not incomplete
        assert report["missed_games"] == (None if incomplete else report["counts"]["did_not_play"])
        assert {int(row["game_id"]) for row in report["missing_keys"]} == {
            gid for gid, state in oracle[pid].items() if state == "unknown"
        }
        (output / f"{pid}-coverage.json").write_text(json.dumps(report, indent=2) + "\n")
        reports.append(report)
    source_paths = {
        "raw/" + kind + "/" + SUFFIX
        for kind in ["games", "team_game_stats", "player_game_stats", "player_game_availability"]
    }
    bindings = [row for row in manifest["files"] if row["path"] in source_paths]
    assert {row["path"] for row in bindings} == source_paths
    for row in bindings:
        raw = data_path("data/" + row["path"]).read_bytes()
        assert len(raw) == row["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    binding = dict(
        generation=GENERATION,
        manifest_sha256=MANIFEST,
        classification="read_only_observed_population_audit_not_complete_absence_or_publication",
        availability_rows_in_requested_season=len(ledger),
        source_files=bindings,
        subset_hashes={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")
        },
        missing_keys=[key for report in reports for key in report["missing_keys"]],
        production_writes=0,
    )
    (output / "source-bindings.json").write_text(json.dumps(binding, indent=2) + "\n")
