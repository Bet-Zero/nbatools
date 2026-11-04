"""Authenticate and qualify retained readiness recovery sources offline.

Original archives stay separate. No acquisition, production writes, source edits,
clock repairs, completeness waiver or publication is performed here.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from tools.build_readiness_recovery import (
    ORIGINAL_ZIP_SHA256,
    PARENT_PATH,
    _instant,
    recovery_requirement,
)
from tools.collect_rollover_readiness_laptop import validate_request
from tools.collection_bundle import unpack
from tools.qualify_readiness_partial import PARTIAL

RECOVERY_SHA = "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17"
REQUEST_SHA = "ee6eb91d35ff5f1c2c008df3cd460e516bf412c8a0f0161c366c87098823ad6d"
REQUEST_PATH = PARENT_PATH.parent / "readiness-recovery-20261103.json"
RECOVERY = PARTIAL.parent / "recovery-capture-20261104"
SUPPLEMENT_SHA = "e2e5dff5ac60cdbb93371556490d5117d40012e452d47ea837092b8dccd53de1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def request_identity(job):
    return job["endpoint"], json.dumps(job["parameters"], sort_keys=True, separators=(",", ":"))


def authenticate(archive: Path, output: Path):
    """Bind exact 517 originals and reuse ledger before any statistical admission."""
    raw = archive.read_bytes()
    _require(
        len(raw) == 1_445_891 and hashlib.sha256(raw).hexdigest() == RECOVERY_SHA,
        "Recovery ZIP differs from owner handoff",
    )
    request = json.loads(REQUEST_PATH.read_bytes())
    _require(
        validate_request(request) == REQUEST_SHA and len(request["jobs"]) == 517,
        "Recovery request differs from reviewed fixed scope",
    )
    with zipfile.ZipFile(archive) as z:
        _require(z.testzip() is None, "Recovery ZIP CRC failure")
        _require(len(z.infolist()) == 520, "Recovery ZIP entry count differs")
    unpack(archive, request, output)
    acquisition_raw = (output / "acquisition.json").read_bytes()
    acquisition = json.loads(acquisition_raw)
    _require(
        (output / "sources/capture-attempt.json").read_bytes() == acquisition_raw,
        "Acquisition copies differ",
    )
    _require(
        acquisition["request"] == request
        and acquisition["request_sha256"] == REQUEST_SHA
        and acquisition["production_writes"] == 0
        and acquisition["canonical_period_accepted"] is False
        and acquisition["transport_finished"] is True
        and acquisition["unattempted_jobs"] == []
        and len(acquisition["attempts"]) == 517,
        "Recovery acquisition state differs",
    )
    _, ledger, _ = recovery_requirement(
        PARTIAL / "collection.zip", json.loads(PARENT_PATH.read_bytes()), ORIGINAL_ZIP_SHA256
    )
    with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
        old = json.loads(z.read("acquisition.json"))["attempts"][:602]
    old_identities = {request_identity(a["job"]) for a in old}
    seen, files, sources = set(), {"acquisition.json", "sources/capture-attempt.json"}, []
    previous = _instant(acquisition["captured_at"])
    for job, attempt in zip(request["jobs"], acquisition["attempts"], strict=True):
        identity = request_identity(job)
        _require(
            identity not in seen and identity not in old_identities,
            "Repeated successful request identity",
        )
        seen.add(identity)
        started, finished = _instant(attempt["started_at"]), _instant(attempt["finished_at"])
        _require(
            attempt["job"] == job
            and attempt["endpoint"] == job["endpoint"]
            and attempt["parameters"] == job["parameters"]
            and attempt["url"] == f"https://stats.nba.com/stats/{job['endpoint']}"
            and attempt["source_file"] == job["source_file"]
            and attempt["attempts"] == 1
            and attempt["timeout_seconds"] == 30
            and attempt["http_status"] == 200
            and attempt["response_complete"] is True
            and attempt["transport_complete"] is True
            and not attempt.get("error_type")
            and previous <= started <= finished,
            "Recovery attempt identity, success or chronology differs",
        )
        body = (output / job["source_file"]).read_bytes()
        _require(
            0 < len(body) <= 2_000_000
            and len(body) == attempt["response_bytes"]
            and hashlib.sha256(body).hexdigest() == attempt["response_sha256"],
            "Recovery source bytes differ",
        )
        parsed = json.loads(body)
        _require(isinstance(parsed, dict), "Recovery response must be a JSON object")
        key = {
            "boxscoretraditionalv3": "boxScoreTraditional",
            "boxscoreadvancedv3": "boxScoreAdvanced",
            "boxscoresummaryv3": "boxScoreSummary",
        }.get(job["endpoint"])
        if key:
            _require(
                parsed[key]["gameId"] == job["parameters"]["GameID"],
                "Recovery body game identity differs",
            )
        sources.append(
            {
                "job": job,
                "bytes": len(body),
                "sha256": attempt["response_sha256"],
                "captured_at": attempt["finished_at"],
            }
        )
        files.add(job["source_file"])
        previous = finished
    _require(_instant(acquisition["finished_at"]) >= previous, "Invalid capture finish time")
    _require(
        {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        == files | {"collection-manifest.json"},
        "Unexpected recovery source set",
    )
    return dict(
        classification="authenticated_transport_not_statistical_acceptance",
        original_zip_sha256=RECOVERY_SHA,
        original_bytes=len(raw),
        request_sha256=REQUEST_SHA,
        recovery_successes=517,
        prior_successes=ledger["retained_source_count"],
        repeated_successes=0,
        endpoint_counts=dict(Counter(j["endpoint"] for j in request["jobs"])),
        sources=sources,
        full_snapshot_accepted=False,
        production_writes=0,
    )


def checked_archive(path, expected):
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected, f"Retained archive differs: {path.name}")
    z = zipfile.ZipFile(path)
    if "sources.json" in z.namelist():
        for item in json.loads(z.read("sources.json"))["files"]:
            body = z.read(item["file"])
            _require(
                len(body) == item["bytes"]
                and hashlib.sha256(body).hexdigest() == item["sha256"]
                and hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()
                == item["git_blob_sha"],
                "Retained source binding differs",
            )
    return z


def recovery_context(schedule):
    """Retain accepted88 cells; corroborate only the four appended game contexts."""
    import copy

    import pandas as pd

    from nbatools.commands.pipeline.structured_participation import _table
    from tools.qualify_readiness_partial import retained_core
    from tools.season_rollover_core_bridge import Source, bridge_players, bridge_teams

    with checked_archive(
        PARTIAL / "current-sources.zip",
        "24d041dce0dc568802a4a2664dc2d40c1a4ed7ef4ddb96dc56c826d56587b3c4",
    ) as z:
        primary = _table(
            json.loads(z.read("playergamelogs-regular-season_base_totals.json")), "PlayerGameLogs"
        )
        finder = _table(
            json.loads(z.read("leaguegamefinder-regular-season.json")), "LeagueGameFinderResults"
        )
        subset = copy.deepcopy(schedule)
        ids = set(finder.GAME_ID)
        _require(len(ids) == 92, "Context must be exact retained92")
        for day in subset["leagueSchedule"]["gameDates"]:
            day["games"] = [g for g in day["games"] if g["gameId"] in ids]
        summaries = {
            gid: json.loads(z.read(f"boxscoresummaryv3-{gid}.json"))
            for gid in ["0022600155", "0022600156", "0022600157"]
        }
        accepted_players, accepted_teams = retained_core()
        valid, errors, changes = [], [], []
        from tools.season_rollover_core_bridge import _games, _traditional_teams

        games = _games(subset, finder)
        for gid in ["0022600154", "0022600155", "0022600156", "0022600157"]:
            source = Source(
                f"current-sources.zip/boxscoretraditionalv3-{gid}.json",
                z.read(f"boxscoretraditionalv3-{gid}.json"),
            )
            try:
                list(_traditional_teams(source, games))
            except ValueError as exc:
                errors.append(dict(game_id=gid, source_sha256=source.sha256, error=str(exc)))
            else:
                valid.append(source)
        corrected, player_ledger = bridge_players(primary, subset, finder, traditional=valid)
        corrected_teams, team_ledger = bridge_teams(finder, subset, traditional=valid)
        old_ids = set(accepted_players.GAME_ID)
        appended = corrected.loc[~corrected.GAME_ID.isin(old_ids)]
        appended_teams = corrected_teams.loc[~corrected_teams.GAME_ID.isin(old_ids)]
        for ledger in [player_ledger, team_ledger]:
            changes.extend(x for x in ledger if x["before"] != x["after"])
        players = pd.concat([accepted_players, appended], ignore_index=True)
        teams = pd.concat([accepted_teams, appended_teams], ignore_index=True)
        pd.testing.assert_frame_equal(
            players.loc[players.GAME_ID.isin(old_ids)].reset_index(drop=True),
            accepted_players,
            check_dtype=False,
        )
        pd.testing.assert_frame_equal(
            teams.loc[teams.GAME_ID.isin(old_ids)].reset_index(drop=True),
            accepted_teams,
            check_dtype=False,
        )
        return (
            players,
            teams,
            summaries,
            dict(
                prior88_cells_preserved=True,
                appended_game_ids=sorted(set(appended.GAME_ID)),
                explicit_new4_cell_changes=changes,
                quarantined_whole_sources=errors,
                accepted_old_game_ids=sorted(old_ids),
                full_core_accepted=False,
            ),
        )


def qualify(archive: Path, output: Path):
    """Exercise all paired windows through unchanged strict importer/validators."""
    import pandas as pd

    from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
    from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
    from tools.qualify_readiness_partial import ORACLE_SHA, REFRESH_SHA
    from tools.qualify_rollover_q1 import EVIDENCE, Q1_SHA, _local_stage
    from tools.stage_rollover_periods import import_window

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    auth = authenticate(archive, output / "original")
    with checked_archive(RECOVERY / "supplementary-sources.zip", SUPPLEMENT_SHA) as z:
        schedule_raw = z.read("schedule-current.json")
        metadata = json.loads(z.read("current-schedule-metadata.json"))
        _require(
            len(schedule_raw) == metadata["bytes"]
            and hashlib.sha256(schedule_raw).hexdigest() == metadata["capture"]["sha256"]
            and hashlib.sha1(f"blob {len(schedule_raw)}\0".encode() + schedule_raw).hexdigest()
            == metadata["git_blob_sha"],
            "Schedule source binding differs",
        )
        schedule = json.loads(schedule_raw)
        extra_summaries = {}
        for item in json.loads(z.read("summaries/sources.json"))["files"]:
            body = z.read("summaries/" + item["file"])
            _require(
                len(body) == item["bytes"]
                and hashlib.sha256(body).hexdigest() == item["sha256"]
                and hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()
                == item["git_blob_sha"],
                "First-time Summary binding differs",
            )
            extra_summaries[item["game_id"]] = json.loads(body)
    players, teams, summaries, context_report = recovery_context(schedule)
    summaries.update(extra_summaries)
    with checked_archive(EVIDENCE / "period-milestone/archive-refresh.zip", REFRESH_SHA) as z:
        for gid in [f"0022600{n}" for n in range(147, 154)]:
            summaries[gid] = json.loads(z.read(f"boxscoresummaryv3_{gid}.json"))
    from tools.season_rollover_core_bridge import _additional_sources

    summaries["0022600144"] = _additional_sources(EVIDENCE)["summary.json"].document
    with checked_archive(PARTIAL / "summary-oracles.zip", ORACLE_SHA) as z:
        for item in json.loads(z.read("sources.json"))["files"]:
            summaries[item["game_id"]] = json.loads(z.read(item["file"]))
    summaries["0022600154"] = json.loads(
        (output / "original/sources/boxscoresummaryv3_0022600154.json").read_bytes()
    )
    jobs = {}
    with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
        for attempt in json.loads(z.read("acquisition.json"))["attempts"][:602]:
            params = attempt["parameters"]
            if "GameID" not in params:
                continue
            key = params["GameID"], params["StartPeriod"], params["EndPeriod"]
            jobs.setdefault(key, {})[attempt["endpoint"]] = z.read(attempt["source_file"])
    for item in auth["sources"]:
        job = item["job"]
        params = job["parameters"]
        if (
            job["endpoint"] not in {"boxscoretraditionalv3", "boxscoreadvancedv3"}
            or params["RangeType"] != 1
        ):
            continue
        key = params["GameID"], params["StartPeriod"], params["EndPeriod"]
        _require(job["endpoint"] not in jobs.get(key, {}), "Cannot replace retained period source")
        jobs.setdefault(key, {})[job["endpoint"]] = (
            output / "original" / job["source_file"]
        ).read_bytes()
    with checked_archive(EVIDENCE / "q1-laptop-capture/collection.zip", Q1_SHA) as z:
        jobs[("0022600001", 1, 1)] = {
            endpoint: z.read(f"sources/{endpoint}_0022600001_q1.json")
            for endpoint in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
        }
    _require(len(jobs) == 555, "Expected exact555 direct windows")
    root = output / "stage"
    root.mkdir()
    admitted, quarantined, outputs = [], [], [[], []]
    with _local_stage(root):
        pull_games.run("2026-27", "Regular Season", raw_frame=teams)
        pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=teams)
        pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=players)
        contexts = [
            pd.read_csv(root / f"data/raw/{g}_game_stats/2026-27_regular_season.csv")
            for g in ["player", "team"]
        ]
        if "wl" not in contexts[0]:
            contexts[0] = contexts[0].merge(
                contexts[1][["game_id", "team_id", "wl"]],
                on=["game_id", "team_id"],
                validate="many_to_one",
            )
        for (gid, start, end), bodies in sorted(jobs.items()):
            _require(
                set(bodies) == {"boxscoretraditionalv3", "boxscoreadvancedv3"},
                "Unpaired period transport gap remains",
            )
            window = next(
                w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end)
            )
            row = dict(
                game_id=gid,
                start_period=start,
                end_period=end,
                period_family=window.period_family,
                period_value=window.period_value,
                source_sha256={name: hashlib.sha256(b).hexdigest() for name, b in bodies.items()},
            )
            try:
                result = import_window(
                    bodies["boxscoretraditionalv3"],
                    bodies["boxscoreadvancedv3"],
                    game_id=gid,
                    window=window,
                    summary=summaries[gid],
                    player_context=contexts[0],
                    team_context=contexts[1],
                )
            except ValueError as exc:
                row["error"] = str(exc)
                quarantined.append(row)
                continue
            admitted.append(
                dict(
                    row,
                    admission_basis="direct_originals",
                    player_rows=len(result[0]),
                    team_rows=len(result[1]),
                )
            )
            for target, frame in zip(outputs, result, strict=True):
                target.append(frame)
        original_quarantines = quarantined.copy()
        independent = {(r["game_id"], r["start_period"], r["end_period"]) for r in admitted}
        reconciled, remaining = [], []
        from tools.reconcile_period_clocks import derive_clocks

        for row in original_quarantines:
            key = row["game_id"], row["start_period"], row["end_period"]
            window = next(w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == key[1:])
            try:
                derived, observations = derive_clocks(key, jobs, independent)
                result = import_window(
                    derived["boxscoretraditionalv3"],
                    derived["boxscoreadvancedv3"],
                    game_id=key[0],
                    window=window,
                    summary=summaries[key[0]],
                    player_context=contexts[0],
                    team_context=contexts[1],
                )
            except ValueError as exc:
                remaining.append(dict(row, alternate_clock_qualification_error=str(exc)))
                continue
            directory = output / "derived-clocks" / f"{key[0]}-{key[1]}-{key[2]}"
            directory.mkdir(parents=True)
            for endpoint, body in derived.items():
                (directory / f"{endpoint}.json").write_bytes(body)
            entry = dict(
                row,
                admission_basis="explicit_complementary_clock_observations",
                clock_observations=observations,
                derived_sha256={
                    name: hashlib.sha256(body).hexdigest() for name, body in derived.items()
                },
                player_rows=len(result[0]),
                team_rows=len(result[1]),
            )
            reconciled.append(entry)
            admitted.append(entry)
            for target, frame in zip(outputs, result, strict=True):
                target.append(frame)
        quarantined = remaining
        for grain, frames in zip(["player", "team"], outputs, strict=True):
            path = root / f"data/raw/{grain}_game_period_stats/2026-27_regular_season.csv"
            path.parent.mkdir(parents=True)
            pd.concat(frames, ignore_index=True).to_csv(path, index=False)
        from nbatools.commands.player_game_finder import build_result

        new_q1 = build_result(
            season="2026-27",
            player="Cameron Boozer",
            quarter="1",
            start_date="2026-10-25",
            end_date="2026-10-25",
        )
        _require(new_q1.result_status == "ok", "Required retained-source consumer failed")
        answers = dict(boozer_q1=new_q1.games.to_dict("records"))
    report = dict(
        classification="qualified_windows_not_coherent_full_snapshot",
        authentication=auth,
        context=context_report,
        paired_windows=len(jobs),
        admitted_windows=admitted,
        original_quarantined_windows=original_quarantines,
        derived_clock_windows=reconciled,
        quarantined_windows=quarantined,
        waiting_windows=[],
        player_rows=sum(len(f) for f in outputs[0]),
        team_rows=sum(len(f) for f in outputs[1]),
        actual_answers=answers,
        full_snapshot_accepted=False,
        readiness_accepted=False,
        production_writes=0,
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(RECOVERY / "collection.zip", args.output)
    print(
        json.dumps(
            {
                "paired_windows": report["paired_windows"],
                "admitted_windows": len(report["admitted_windows"]),
                "derived_clock_windows": len(report["derived_clock_windows"]),
                "quarantined_windows": len(report["quarantined_windows"]),
                "full_snapshot_accepted": False,
                "production_writes": 0,
            }
        )
    )
