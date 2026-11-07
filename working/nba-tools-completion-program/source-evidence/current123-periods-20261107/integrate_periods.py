"""Replay this fixed returned capture through existing staging and immutable versions."""

import io
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.collection_bundle import unpack
from tools.development_snapshot import _safe_contracts, intake, write_json
from tools.reconcile_period_clocks import derive_clocks
from tools.stage_rollover_periods import import_window

E = Path(__file__).resolve().parent
ROOT = E.parents[3]
SUFFIX = "2026-27_regular_season.csv"
PARENT = E.parent / "id18-current-required-20261107/current123-required-v3.zip"
PARENT_SHA = "d6b730742a05653e03f5640f29e4d7e5c0a67ed4297ec99daa35d89875a6c6ef"
PARENT_MANIFEST = "5fb3326f512037c69c815a06cb73ab41a9a8187bf5dcdc36cd114f2da7eb6a4c"
CAPTURE_SHA = "81eea4d32217e541cab13783a06031616abb192e56b7c7b37d10f1f460978faf"
SUMMARY = E.parent / "core-live-current-20261107/new16-summary-originals.zip"
SUMMARY_SHA = "dbf426144fe30017bb0b96eac184897ce344938fa73c6670672c150474a5381b"
VERSION = "current123-period-source-development-v4"


def qualify(output: Path, backlog: Path):
    output.mkdir(parents=True, exist_ok=False)
    request = json.loads((ROOT / "working/nba-tools-completion-program/collection-requests/current123-new16-periods-20261107.json").read_bytes())
    assert sha256((E / "collection.zip").read_bytes()) == CAPTURE_SHA
    custody = unpack(E / "collection.zip", request, output / "original")
    capture = json.loads((output / "original/acquisition.json").read_bytes())
    assert capture["transport_finished"] and capture["production_writes"] == 0
    assert len(capture["attempts"]) == len(request["jobs"]) == 196
    assert capture["unattempted_jobs"] == [] and not capture.get("error_type")
    assert (datetime.fromisoformat(capture["finished_at"]) - datetime.fromisoformat(capture["captured_at"])).total_seconds() <= 1050
    jobs = {}
    for job, attempt in zip(request["jobs"], capture["attempts"], strict=True):
        assert attempt["job"] == job and attempt["parameters"] == job["parameters"]
        assert attempt["endpoint"] == job["endpoint"]
        assert attempt["url"] == "https://stats.nba.com/stats/" + job["endpoint"]
        assert attempt["http_status"] == 200 and attempt["transport_complete"] and attempt["response_complete"]
        assert attempt["attempts"] == 1 and attempt["timeout_seconds"] == 30 and not attempt.get("error_type")
        assert attempt["source_file"] == job["source_file"]
        body = (output / "original" / job["source_file"]).read_bytes()
        assert len(body) == attempt["response_bytes"] <= 2_000_000
        assert sha256(body) == attempt["response_sha256"]
        p = job["parameters"]
        key = p["GameID"], p["StartPeriod"], p["EndPeriod"]
        assert job["endpoint"] not in jobs.setdefault(key, {})
        jobs[key][job["endpoint"]] = body
    assert sha256(PARENT.read_bytes()) == PARENT_SHA
    root = output / "stage"
    with ZipFile(PARENT) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(root)
    prior = DevelopmentSnapshot(root, PARENT_MANIFEST)
    players, teams = [pd.read_csv(root / f"data/raw/{g}_game_stats/{SUFFIX}") for g in ("player", "team")]
    if "wl" not in players:
        players = players.merge(teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one")
    assert sha256(SUMMARY.read_bytes()) == SUMMARY_SHA
    denominator = json.loads((E.parent / "core-live-current-20261107/new16-window-denominator.json").read_bytes())
    source_shas = {r["game_id"]: r["source_sha256"] for r in denominator["new16"]}
    summaries = {}
    with ZipFile(SUMMARY) as z:
        for gid, digest in source_shas.items():
            raw = z.read(gid + ".json")
            assert sha256(raw) == digest
            summaries[gid] = json.loads(raw)
    assert len(jobs) == 98
    admitted, quarantined, frames = [], [], [[], []]
    def import_pair(key, bodies):
        gid, start, end = key
        window = next(w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end))
        return import_window(bodies["boxscoretraditionalv3"], bodies["boxscoreadvancedv3"], game_id=gid,
                             window=window, summary=summaries[gid], player_context=players, team_context=teams)
    for key, bodies in jobs.items():
        try:
            pair = import_pair(key, bodies)
        except ValueError as exc:
            quarantined.append(dict(key=list(key), error=str(exc)))
            continue
        admitted.append(key)
        for bucket, frame in zip(frames, pair, strict=True): bucket.append(frame)
    assert len(admitted) == 95 and len(quarantined) == 3
    ledger = []
    for row in quarantined:
        key = tuple(row["key"])
        derived, changes = derive_clocks(key, jobs, set(admitted))
        pair = import_pair(key, derived)  # Unchanged strict importer must pass again.
        ledger.extend(changes)
        for name, raw in derived.items():
            target = output / "derived-clock-inputs" / f"{name}-{key[0]}-{key[1]}-{key[2]}.json"
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
        for bucket, frame in zip(frames, pair, strict=True): bucket.append(frame)
    assert len(ledger) == 6
    changes = []
    for grain, parts, expected in zip(("player", "team"), frames, (2236, 196), strict=True):
        new = pd.concat(parts, ignore_index=True).sort_values(["game_id", "period_family", "period_value", "team_id", *( ["player_id"] if grain == "player" else [])])
        assert len(new) == expected
        path = root / f"data/raw/{grain}_game_period_stats/{SUFFIX}"
        before = path.read_bytes()
        old = pd.read_csv(io.BytesIO(before))
        assert list(old.columns) == list(new.columns)
        assert not set(new.game_id) & set(old.game_id)
        assert before.endswith(b"\n")
        # Preserve every old CSV token/unknown and append only the new rows.
        path.write_bytes(before + new.to_csv(index=False, header=False).encode())
        assert path.read_bytes().startswith(before)
        changes.append(dict(path=path.relative_to(root).as_posix(), before_sha256=sha256(before), after_sha256=sha256(path.read_bytes()), old_rows=len(old), added_rows=len(new)))
    _safe_contracts(root, "2026-27", "Regular Season")
    report = build_slice_manifest("2026-27", "Regular Season", data_root=root / "data", generation_id=VERSION)
    assert report["validation_state"] == "passed", report
    evidence = dict(reference=str((E / "collection.zip").relative_to(ROOT)), sha256=CAPTURE_SHA, source_sha256=CAPTURE_SHA)
    conflict = dict(game_id="0022600184", team_id=1610612742, player_id=1629023,
                    fields={"player_dreb": {"quarter_sum": 5, "retained_whole": 6}, "player_reb": {"quarter_sum": 9, "retained_whole": 10},
                            "team_dreb": {"quarter_sum": 31, "retained_whole": 32}, "team_reb": {"quarter_sum": 49, "retained_whole": 50}},
                    unknown_fact="Independent authoritative Washington full-game rebound total and period allocation of the disputed defensive rebound; neither current source basis is selected as truth")
    ident = intake(backlog, dict(dataset="player_and_team_game_period_stats", source_sha256=CAPTURE_SHA,
        scope={"season":"2026-27", "season_type":"Regular Season", "game_id":"0022600184", "team_id":1610612742, "player_id":1629023},
        check="new period-to-retained-whole defensive rebound basis", observed=conflict, expected="independently consistent whole/period rebound credit",
        impact="P.J. Washington/DAL DREB/REB and dependent rebound rates/filters for game184 remain numerically unqualified; score/PTS/record unaffected",
        evidence=evidence, next_evidence=conflict["unknown_fact"], snapshot=VERSION))
    quality = dict(capture=custody, transport_requests=196, windows=98, directly_imported=95, independently_derived_clock_windows=3,
                   player_keys_added=2236, standard_player_keys_added=2208, source_ot_player_keys_added=28, team_keys_added=196,
                   source_listed_zero_clock_rows=7, standard_completed_zero_rows=317, ot_unlisted_whole_players_not_fabricated=13,
                   total_windows=745, total_team_keys=1490, total_player_keys=16783, period_key_coverage_complete=True,
                   acquisition_gap_closed=True, period_numerical_complete=False, new_count_basis_conflict=conflict,
                   old_484_rate_unknowns_preserved=True, dq006_membership_separate=True,
                   full_snapshot_accepted=False, production_writes=0, parent_manifest_sha256=PARENT_MANIFEST,
                   original_source_bytes_changed=False, raw_malformed_clocks_quarantined=quarantined, derived_clock_ledger=ledger,
                   changes=changes, source_summary_archive_sha256=SUMMARY_SHA)
    write_json(output / "qualification.json", quality)
    validation_path = "data/metadata/period-current-validation.json"
    validation_sha = write_json(root / validation_path, report)
    write_json(root / "data/metadata/period-current-custody.json", quality)
    previous = prior.document
    missing_coverage = {"DQ-auto-3f8b2f8fe51af9fa22be8c76af20c0a48fb369107778660fb34703f070141db2", "DQ-auto-a30681d45aee2d804d7d341bc1c6b816b465b4dd81703907a8050b2ca6e01e0a"}
    doc = dict(previous, version=VERSION, scope="Fixed123-game cutoff; all745period windows present; game184 rebound basis and old484rates/membership/freshness/production acceptance remain open",
               source_evidence=evidence, exceptions=sorted((set(previous["exceptions"]) - missing_coverage) | {ident, "DQ-006"}),
               validation_reports=[dict(path=validation_path, sha256=validation_sha, state="passed")])
    doc["files"] = {p.relative_to(root).as_posix():sha256(p.read_bytes()) for p in sorted((root / "data").rglob("*")) if p.is_file() and p.relative_to(root) != MANIFEST}
    digest = write_json(root / MANIFEST, doc)
    DevelopmentSnapshot(root, digest)
    with ZipFile(output / "current123-period-v4.zip", "x", ZIP_DEFLATED) as z:
        for p in sorted((root / "data").rglob("*")):
            if p.is_file(): z.write(p, p.relative_to(root).as_posix())
    binding = dict(archive="current123-period-v4.zip", archive_sha256=sha256((output / "current123-period-v4.zip").read_bytes()), manifest_sha256=digest, parent_manifest_sha256=PARENT_MANIFEST, source_archive_sha256=CAPTURE_SHA, exceptions=doc["exceptions"], production_writes=0)
    write_json(output / "binding.json", binding)
    return binding, quality


if __name__ == "__main__":
    import sys
    print(json.dumps(qualify(Path(sys.argv[1]), Path(sys.argv[2]))[0], indent=2))
