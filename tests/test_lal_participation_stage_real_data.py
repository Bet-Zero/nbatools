"""Thirty structured games plus one official report qualify an isolated stage."""

import hashlib
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import backfill, validate_publication
from nbatools.data_source import data_path, data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tools.availability_overlay import binding, preserve_cells, verify_append
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
REQUEST = PROGRAM / "collection-requests/lal-participation-remaining-2025-26.json"
SOURCES = PROGRAM / "source-evidence/k08-lal-remaining"
SUFFIX = "2025-26_regular_season.csv"
CSV = "raw/player_game_availability/" + SUFFIX
LAL = 1610612747
PEOPLE = {1629029: "Luka Doncic", 1630559: "Austin Reaves"}
FALLBACK_GAME = "0022500708"
SUPPLEMENT = PROGRAM / "collection-requests/lal-0708-report-fallback-2025-26.json"
REPORT_CACHE = SOURCES / "0708-official-report"
DNP = re.compile(
    r"^(DNP|DND|NWT|INACTIVE|DID NOT PLAY|DID NOT DRESS|NOT WITH TEAM|NOT PLAYING)\b", re.I
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _original_fact(traditional, summary, *, player_id, team_id):
    """Independent listed-row oracle; neither omission nor zero proves absence."""
    facts, observations = set(), []
    for label, document, collection in [
        ("traditional", traditional, "players"),
        ("summary", summary, "inactives"),
    ]:
        found = [
            (int(document[side]["teamId"]), person)
            for side in ("homeTeam", "awayTeam")
            for person in document[side][collection]
            if int(person["personId"]) == player_id
        ]
        assert len(found) <= 1, "Duplicate source player identity"
        if not found:
            continue
        tid, person = found[0]
        assert tid == team_id, "Source player is associated with the opposite side"
        if label == "summary":
            state = "did_not_play"
        else:
            text = str(person["statistics"]["minutes"] or "").strip()
            # Actual retained Traditional originals use MM:SS. Accept an empty
            # clock only with an explicit nonparticipation comment below.
            if text:
                assert re.fullmatch(r"\d+:\d{2}(?:\.\d+)?", text), text
                minute, second = map(float, text.split(":"))
                assert 0 <= second < 60
                positive = minute * 60 + second > 0
            else:
                positive = False
            inactive = bool(DNP.match(str(person.get("comment", "")).strip()))
            assert not (positive and inactive), "Source clock and comment conflict"
            state = "played" if positive else "did_not_play" if inactive else "unknown"
        observations.append(dict(source=label, row=person, state=state))
        if state != "unknown":
            facts.add(state)
    assert len(facts) == 1, "Target has missing or conflicting explicit source facts"
    return dict(state=facts.pop(), observations=observations)


def _baseline_states(teams, players, ledger):
    dates = {int(r.game_id): pd.Timestamp(r.game_date).date() for r in teams.itertuples()}
    opponents = {int(r.game_id): int(r.opponent_team_id) for r in teams.itertuples()}
    facts = defaultdict(lambda: defaultdict(set))
    for rows, appearance in [(players, True), (ledger, False)]:
        for row in rows.loc[rows.player_id.isin(PEOPLE)].itertuples():
            gid, tid = int(row.game_id), int(row.team_id)
            if gid not in dates or appearance and not row.minutes > 0:
                continue
            assert pd.Timestamp(row.game_date).date() == dates[gid]
            assert tid in {LAL, opponents[gid]}
            facts[(int(row.player_id), gid)][tid].add(
                "played" if appearance else row.participation_state
            )
    result = {}
    for pid in PEOPLE:
        result[pid] = {}
        for gid in dates:
            sides = facts[(pid, gid)]
            assert len(sides) <= 1
            states = sides.get(LAL, set())
            assert not states or len(states) == 1 and states <= {"played", "did_not_play"}
            result[pid][gid] = (
                next(iter(states)) if states else "same_game_other_side" if sides else "unknown"
            )
    return result


def _combined_stage(tmp_path, request, *, candidate_sha):
    """Compose existing qualified structured and scoped-report importers only."""
    original = json.loads((SOURCES / "sources.json").read_bytes())
    supplement = json.loads(SUPPLEMENT.read_bytes())
    assert supplement["game_id"] == FALLBACK_GAME
    assert (supplement["target_team_id"], supplement["target_player_id"]) == (LAL, 1630559)
    assert supplement["base_generation"] == request["base_generation"]
    assert supplement["base_manifest_sha256"] == request["base_manifest_sha256"]
    valid = [row for row in request["requirements"] if row["game_id"] != FALLBACK_GAME]
    fallback = [row for row in request["requirements"] if row["game_id"] == FALLBACK_GAME]
    assert len(valid) == 35 and len(fallback) == 1
    assert fallback[0]["team_id"] == LAL and fallback[0]["player_id"] == 1630559
    assert supplement["game_date"] == fallback[0]["game_date"]
    filenames = {
        name for name in request["source_files"] if not name.endswith(f"_{FALLBACK_GAME}.json")
    }
    assert len(filenames) == 60
    derived = tmp_path / "structured-input"
    (derived / "sources").mkdir(parents=True)
    subset = {
        key: request[key]
        for key in (
            "schema_version",
            "dataset",
            "season",
            "season_type",
            "base_generation",
            "base_manifest_sha256",
            "revision",
            "repository",
        )
    }
    subset.update(
        requirements=valid,
        source_files={name: request["source_files"][name] for name in sorted(filenames)},
        classification="derived_30_game_staging_subset_not_acquisition_or_publication",
        parent_request_sha256=_sha(REQUEST.read_bytes()),
    )
    request_path = derived / "request.json"
    request_path.write_text(json.dumps(subset, indent=2) + "\n")
    (derived / "sources.json").write_text(
        json.dumps(
            dict(
                repository=original["repository"],
                revision=original["revision"],
                files={name: original["files"][name] for name in sorted(filenames)},
                parent_sources_sha256=_sha((SOURCES / "sources.json").read_bytes()),
            ),
            indent=2,
        )
        + "\n"
    )
    for name in sorted(filenames):
        path = SOURCES / "sources" / name
        assert not path.is_symlink()
        (derived / "sources" / name).write_bytes(path.read_bytes())
    ledger_path = CSV.removesuffix(".csv") + ".imports.json"
    baseline = {
        relative: data_path("data/" + relative).read_bytes() for relative in (CSV, ledger_path)
    }
    work, intermediate = tmp_path / "stage", tmp_path / "structured-overlay"
    partial = build_stage(request_path, derived, work, intermediate, candidate_sha=candidate_sha)
    assert partial["requested_target_count"] == 35 and partial["requested_game_count"] == 30
    root = work / "data"
    report_receipt_path = REPORT_CACHE / "20260201_LALNYK.json"
    report_receipt_raw = report_receipt_path.read_bytes()
    report_receipt = json.loads(report_receipt_raw)
    report_raw = (REPORT_CACHE / report_receipt["raw_file"]).read_bytes()
    assert report_receipt["source_url"] == supplement["source_url"]
    assert (
        _sha(report_raw) == report_receipt["sha256"]
        and len(report_raw) == report_receipt["size_bytes"]
    )
    backfill(
        "2025-26",
        root=root,
        source="report",
        game_ids=[int(FALLBACK_GAME)],
        cached_reports=REPORT_CACHE,
        imported_team_ids=[LAL],
    )
    after = pd.read_csv(root / CSV)
    report_rows = after.loc[after.game_id.eq(int(FALLBACK_GAME))]
    assert report_rows.team_id.eq(LAL).all() and not report_rows.empty
    assert report_rows.source.eq("nba_official_finalbox:20260201_LALNYK").all()
    target = report_rows.loc[report_rows.player_id.eq(fallback[0]["player_id"])]
    assert len(target) == 1 and target.game_date.item() == fallback[0]["game_date"]
    assert target.participation_state.item() == "did_not_play"
    games = sorted({row["game_id"] for row in request["requirements"]})
    append = {
        CSV: binding(baseline[CSV], games, added_records=len(after) - 804),
        ledger_path: binding(baseline[ledger_path], games, added_records=31),
    }
    (root / CSV).write_bytes(
        preserve_cells(CSV, baseline[CSV], (root / CSV).read_bytes(), append[CSV])
    )
    verify_append(
        ledger_path, baseline[ledger_path], (root / ledger_path).read_bytes(), append[ledger_path]
    )
    validate_publication(root)
    output = tmp_path / "overlay"
    output.mkdir()
    files = []
    for directory in ("raw/player_game_availability", "raw/player_game_availability_sources"):
        for path in sorted((root / directory).iterdir()):
            relative, raw = path.relative_to(root).as_posix(), path.read_bytes()
            if partial["base_file_hashes"].get(relative) == _sha(raw):
                continue
            assert relative not in partial["base_file_hashes"] or relative in append
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            files.append(dict(path=relative, size_bytes=len(raw), sha256=_sha(raw)))
    quarantined = {
        name: original["files"][name]["sha256"]
        for name in request["source_files"]
        if name not in filenames
    }
    assert not set(quarantined.values()) & {row["sha256"] for row in files}
    assert {
        row["path"] for row in files if row["path"].startswith("raw/player_game_availability/")
    } == set(append)
    validation = {
        **partial,
        "input_hashes": {
            **partial["input_hashes"],
            "full_request": _sha(REQUEST.read_bytes()),
            "full_sources.json": _sha((SOURCES / "sources.json").read_bytes()),
            "source-qualification.json": _sha((SOURCES / "source-qualification.json").read_bytes()),
            "report_supplement_request": _sha(SUPPLEMENT.read_bytes()),
            "report_receipt": _sha(report_receipt_raw),
            "report_original_pdf": _sha(report_raw),
        },
        "append_only": append,
        "requested_target_count": 36,
        "requested_game_count": 31,
        "qualified_targets": [
            *partial["qualified_targets"],
            {
                **{
                    key: fallback[0][key]
                    for key in ("game_id", "game_date", "team_id", "player_id")
                },
                "state": target.participation_state.item(),
            },
        ],
        "overlay_files": files,
        "strategy": "30_structured_games_plus_one_LAL_only_official_report",
        "full_request_sha256": _sha(REQUEST.read_bytes()),
        "full_sources_manifest_sha256": _sha((SOURCES / "sources.json").read_bytes()),
        "quarantined_structured_originals_not_imported": quarantined,
        "report_game_id": FALLBACK_GAME,
        "report_imported_team_ids": [LAL],
        "full_required_slice_accepted": False,
    }
    (output / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    return work, output, validation, len(report_rows)


def _assert_record(result, expected):
    assert result["sections"]["summary"][0]["games"] == len(expected)
    assert {int(row["game_id"]) for row in result["sections"]["game_log"]} == set(expected.game_id)
    row = result["sections"]["summary"][0]
    assert (row["wins"], row["losses"]) == (
        int(expected.wl.eq("W").sum()),
        int(expected.wl.eq("L").sum()),
    )
    assert row["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
    return row


@pytest.mark.needs_data
@pytest.mark.engine
def test_retained_lal_sources_close_both_populations_and_reverse_mixed_records(
    tmp_path, monkeypatch
):
    request = json.loads(REQUEST.read_bytes())
    assert request["base_generation"] == "availability-lebron-season-v1-20261031"
    assert (
        request["base_manifest_sha256"]
        == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
    )
    requirements = request["requirements"]
    keys = {(int(r["game_id"]), r["player_id"]) for r in requirements}
    groups = {int(r["game_id"]) for r in requirements}
    assert len(requirements) == len(keys) == 36 and len(groups) == 31
    assert all(r["prior_state"] == "unknown" and r["team_id"] == LAL for r in requirements)
    teams = data_read_csv("data/raw/team_game_stats/" + SUFFIX)
    teams = teams.loc[teams.team_id.eq(LAL)].copy()
    players = data_read_csv("data/raw/player_game_stats/" + SUFFIX)
    ledger = data_read_csv("data/" + CSV)
    assert len(teams) == teams.game_id.nunique() == 82 and len(ledger) == 804
    states = _baseline_states(teams, players, ledger)
    assert Counter(states[1629029].values()) == {"played": 64, "did_not_play": 7, "unknown": 11}
    assert Counter(states[1630559].values()) == {"played": 51, "did_not_play": 6, "unknown": 25}
    assert keys == {
        (gid, pid) for pid in PEOPLE for gid, state in states[pid].items() if state == "unknown"
    }
    source_facts, originals, expected_append_rows, quarantined_rows = [], {}, 0, 0
    for gid in groups:
        pair = []
        hashes = {}
        for endpoint, key in [
            ("boxscoretraditionalv3", "boxScoreTraditional"),
            ("boxscoresummaryv3", "boxScoreSummary"),
        ]:
            path = SOURCES / "sources" / f"{endpoint}_{gid:010d}.json"
            raw = path.read_bytes()
            pair.append(json.loads(raw)[key])
            hashes[path.name] = _sha(raw)
        assert all(int(document["gameId"]) == gid for document in pair)
        listed = [
            (int(document[side]["teamId"]), int(person["personId"]))
            for document, collection in zip(pair, ("players", "inactives"), strict=True)
            for side in ("homeTeam", "awayTeam")
            for person in document[side][collection]
        ]
        assert len(listed) == len(set(listed)) == len({pid for _, pid in listed})
        expected_append_rows += len(listed)
        if gid == int(FALLBACK_GAME):
            quarantined_rows = len(listed)
        originals[gid] = (pair, hashes)
    assert expected_append_rows == 1087
    baseline_csv = data_path("data/" + CSV).read_bytes()
    for r in requirements:
        gid, pid = int(r["game_id"]), r["player_id"]
        assert (
            pd.Timestamp(teams.loc[teams.game_id.eq(gid), "game_date"].item()).date().isoformat()
            == r["game_date"]
        )
        documents, hashes = originals[gid]
        fact = _original_fact(*documents, player_id=pid, team_id=LAL)
        states[pid][gid] = fact["state"]
        source_facts.append(
            dict(
                **{key: r[key] for key in ("game_id", "game_date", "team_id", "player_id")},
                **fact,
                source_hashes=hashes,
                evidence_role="corroboration_only_quarantined_original"
                if r["game_id"] == FALLBACK_GAME
                else "imported_structured_originals",
            )
        )
    assert Counter(r["state"] for r in source_facts) == {"did_not_play": 36}
    assert all("unknown" not in row.values() for row in states.values())

    qualification = json.loads((SOURCES / "source-qualification.json").read_bytes())
    assert qualification["request_sha256"] == _sha(REQUEST.read_bytes())
    assert qualification["sources_manifest_sha256"] == _sha((SOURCES / "sources.json").read_bytes())
    assert (
        not qualification["all_originals_stage_eligible"]
        and not qualification["full_append_qualified"]
    )
    invalid = qualification["clock_evidence"]["invalid_clocks"]
    assert len(invalid) == 1
    assert (invalid[0]["game_id"], invalid[0]["player_id"], invalid[0]["raw_minutes"]) == (
        FALLBACK_GAME,
        1629060,
        "28:60",
    )
    work, destination, validation, report_rows = _combined_stage(
        tmp_path, request, candidate_sha=os.environ["VALIDATION_SHA"]
    )
    expected_append_rows = expected_append_rows - quarantined_rows + report_rows
    assert validation["requested_target_count"] == 36 and validation["requested_game_count"] == 31
    assert {
        (int(r["game_id"]), r["player_id"], r["state"]) for r in validation["qualified_targets"]
    } == {(int(r["game_id"]), r["player_id"], r["state"]) for r in source_facts}
    root = work / "data"
    assert len(pd.read_csv(root / CSV)) == 804 + expected_append_rows
    assert validation["append_only"][CSV]["added_records"] == expected_append_rows
    assert (
        validation["append_only"][CSV.removesuffix(".csv") + ".imports.json"]["added_records"] == 31
    )
    import csv
    import io

    before = list(csv.DictReader(io.StringIO(baseline_csv.decode())))
    after = list(csv.DictReader(io.StringIO((root / CSV).read_text())))
    by_key = {(r["game_id"], r["team_id"], r["player_id"]): r for r in after}
    assert all(by_key[(r["game_id"], r["team_id"], r["player_id"])] == r for r in before)
    for kind in ["games", "team_game_stats", "player_game_stats"]:
        path = f"raw/{kind}/" + SUFFIX
        assert _sha((root / path).read_bytes()) == validation["base_file_hashes"][path]
    # Reuse the accepted stage-report harness: this local inventory describes
    # only copied/staged files, is test-only, and is never in the overlay export.
    entries = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.relative_to(root).as_posix() != "metadata/generation_manifest.json"
        ):
            raw = path.read_bytes()
            entries.append(
                dict(path=path.relative_to(root).as_posix(), size_bytes=len(raw), sha256=_sha(raw))
            )
    manifest = json.dumps(
        dict(generation_id="legacy", classification="test_only_development_staging", files=entries)
    ).encode()
    (root / "metadata/generation_manifest.json").write_bytes(manifest)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(work))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        diagnostics = destination / "lal-participation-acceptance"
        diagnostics.mkdir()
        teams.to_csv(diagnostics / "team82.csv", index=False)
        players.loc[players.player_id.isin([*PEOPLE, 2544])].to_csv(
            diagnostics / "canonical-player-rows.csv", index=False
        )
        ledger.loc[ledger.player_id.isin(PEOPLE)].to_csv(
            diagnostics / "prior-target-ledger.csv", index=False
        )
        (diagnostics / "source-target-facts.json").write_text(
            json.dumps(source_facts, indent=2) + "\n"
        )
        lebron = set(
            players.loc[
                players.team_id.eq(LAL) & players.player_id.eq(2544) & players.minutes.gt(0),
                "game_id",
            ].astype(int)
        )
        assert len(lebron) == 60
        reports, answers = {}, []
        for pid, name in PEOPLE.items():
            report = build_report(
                generation="legacy",
                manifest_sha256=_sha(manifest),
                season="2025-26",
                team_id=LAL,
                player_id=pid,
            )
            assert report["requested_games"] == report["observed_team_games"] == 82
            assert report["complete_requested_population"] and not report["missing_keys"]
            assert report["counts"] == {
                state: Counter(states[pid].values())[state]
                for state in ("played", "did_not_play", "same_game_other_side", "unknown")
            }
            missed = {gid for gid, state in states[pid].items() if state == "did_not_play"}
            assert report["missed_games"] == len(missed) == (18 if pid == 1629029 else 31)
            reports[pid] = report
            for question, expected in [
                (f"how many games did {name} miss in 2025-26", missed),
                (
                    f"how many home games did {name} miss in 2025-26",
                    set(
                        teams.loc[
                            teams.game_id.isin(missed)
                            & teams.is_home.astype(str).str.lower().isin(["1", "1.0", "true"]),
                            "game_id",
                        ].astype(int)
                    ),
                ),
            ]:
                result = execute_natural_query(question)
                assert result.result_status == "ok", result.metadata
                sections = result.result.to_dict()["sections"]
                assert result.route == "game_finder" and sections["count"] == [
                    {"count": len(expected)}
                ]
                assert {int(row["game_id"]) for row in sections["finder"]} == expected
            expected = teams.loc[teams.game_id.isin(missed & lebron)]
            assert (len(expected), int(expected.wl.eq("W").sum()), int(expected.pts.sum())) == (
                (11, 7, 1285) if pid == 1629029 else (25, 15, 2918)
            )
            question = f"Lakers record without {name} and with LeBron James in 2025-26"
            natural = execute_natural_query(question)
            structured = execute_structured_query(
                "team_record",
                team="LAL",
                season="2025-26",
                without_player=name,
                with_player="LeBron James",
            )
            for result in [natural, structured]:
                assert result.result_status == "ok" and result.route == "team_record", (
                    result.metadata
                )
                summary = _assert_record(result.result.to_dict(), expected)
            response = client.post("/query", json={"query": question})
            assert response.status_code == 200 and response.json()["result_status"] == "ok"
            _assert_record(response.json()["result"], expected)
            answers.append(
                dict(
                    query=question,
                    game_ids=sorted(expected.game_id.astype(int).tolist()),
                    points=int(expected.pts.sum()),
                    summary=summary,
                )
            )
        receipt = dict(
            classification="qualified_development_staging_only_no_publication",
            base_generation=request["base_generation"],
            base_manifest_sha256=request["base_manifest_sha256"],
            validation=validation,
            source_targets=source_facts,
            coverage=reports,
            answers=answers,
            full_required_slice_accepted=False,
            production_writes=0,
        )
        (diagnostics / "receipt.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")
        if output := os.environ.get("NBATOOLS_ACQUISITION_OUTPUT"):
            export = Path(output)
            export.mkdir(parents=True, exist_ok=True)
            assert not any(export.iterdir()), (
                "Staging transport requires a new empty export directory"
            )
            shutil.copytree(destination, export, dirs_exist_ok=True)
    finally:
        reset_data_source_cache()


@pytest.mark.parametrize(
    "minutes,comment,summary,state",
    [
        ("01:00", "", False, "played"),
        ("00:00", "DNP - Coach", False, "did_not_play"),
        ("", "DND - Injury/Illness", False, "did_not_play"),
        ("", "NWT - League Suspension", False, "did_not_play"),
        ("", "", True, "did_not_play"),
    ],
)
def test_original_oracle_requires_explicit_clock_or_state(minutes, comment, summary, state):
    player = dict(personId=7, statistics=dict(minutes=minutes), comment=comment)
    traditional = dict(
        homeTeam=dict(teamId=1, players=[player]), awayTeam=dict(teamId=2, players=[])
    )
    envelope = dict(
        homeTeam=dict(teamId=1, inactives=[dict(personId=7)] if summary else []),
        awayTeam=dict(teamId=2, inactives=[]),
    )
    assert _original_fact(traditional, envelope, player_id=7, team_id=1)["state"] == state


@pytest.mark.parametrize(
    "minutes,comment,listed", [("00:00", "", False), ("01:00", "DNP", False), ("01:00", "", True)]
)
def test_original_oracle_rejects_unknown_or_conflicting_facts(minutes, comment, listed):
    player = dict(personId=7, statistics=dict(minutes=minutes), comment=comment)
    traditional = dict(
        homeTeam=dict(teamId=1, players=[player]), awayTeam=dict(teamId=2, players=[])
    )
    summary = dict(
        homeTeam=dict(teamId=1, inactives=[dict(personId=7)] if listed else []),
        awayTeam=dict(teamId=2, inactives=[]),
    )
    with pytest.raises(AssertionError):
        _original_fact(traditional, summary, player_id=7, team_id=1)


@pytest.mark.parametrize("case", ["omitted", "wrong_side", "duplicate"])
def test_original_oracle_never_fills_identity_or_membership_gaps(case):
    player = dict(personId=7, statistics=dict(minutes="01:00"), comment="")
    traditional = dict(homeTeam=dict(teamId=1, players=[]), awayTeam=dict(teamId=2, players=[]))
    summary = dict(homeTeam=dict(teamId=1, inactives=[]), awayTeam=dict(teamId=2, inactives=[]))
    if case == "wrong_side":
        traditional["awayTeam"]["players"] = [player]
    elif case == "duplicate":
        traditional["homeTeam"]["players"] = [player, player]
    with pytest.raises(AssertionError):
        _original_fact(traditional, summary, player_id=7, team_id=1)
