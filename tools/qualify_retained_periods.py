"""Append independently qualified0161 windows to the immutable PR576 stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tools.period_event_evidence import period_facts, same_clock_score_evidence
from tools.qualify_incremental_return import (
    CLOCK_SHA,
    SUMMARY_ARCHIVES,
    bound_zip,
    event_clock_copy,
)
from tools.qualify_rollover_q1 import _local_stage
from tools.readiness_refresh import SourceCache
from tools.stage_current_season import CURRENT, SUFFIX, _append_rows
from tools.stage_rollover_periods import import_window

RETURN = CURRENT.parent / "incremental-return-20261104"
BASE_SHA = "04151f5ed20aedf27ee2a5c279ee75babc9084170a01b64ab79104ec8eaa4486"


def stage(cache_path: Path, output: Path):
    from nbatools.commands.pipeline import (
        build_game_features,
        build_league_season_stats,
        build_player_game_features,
        build_schedule_context_features,
        build_team_game_features,
        validate_raw,
    )
    from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
    from nbatools.commands.validation_control import build_slice_manifest
    from tools.assess_readiness_recovery import due_population

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cache = SourceCache(cache_path)
    root = output / "stage"
    prior = {}
    with bound_zip(RETURN / "qualification-evidence.zip", BASE_SHA) as z:
        for name in z.namelist():
            if name.startswith("stage/data/") and name.endswith(".csv"):
                raw = z.read(name)
                path = output / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                prior[name.removeprefix("stage/")] = raw
    with bound_zip(RETURN / "clock-source-originals.zip", CLOCK_SHA) as z:
        events = z.read("0022600161.json")
    with bound_zip(CURRENT / "current-sources.zip", SUMMARY_ARCHIVES["current-sources.zip"]) as z:
        whole = z.read("boxscoretraditionalv3-0022600161.json")
    box = json.loads(whole)["boxScoreTraditional"]
    final = {box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]}
    proof = same_clock_score_evidence(events, game_id="0022600161", final_teams=final)
    # The original strict failure remains mandatory evidence, not a waived gate.
    try:
        period_facts(events, game_id="0022600161", final_teams=final)
    except ValueError as exc:
        if str(exc) != "Unexplained event score change":
            raise
    else:
        raise ValueError("Original strict chronology unexpectedly accepted")
    qualified = period_facts(events, game_id="0022600161", final_teams=final, score_snapshots=proof)
    players = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
    teams = pd.read_csv(root / f"data/raw/team_game_stats/{SUFFIX}")
    pc = players.merge(
        teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
    )
    summary_record = next(
        r
        for r in cache.data["direct"].values()
        if r["job"]["endpoint"] == "boxscoresummaryv3"
        and r["job"]["parameters"]["GameID"] == "0022600161"
    )
    summary = json.loads(cache.read(summary_record))
    # Bind every period score to both independent Summary arrays.
    for side in ["homeTeam", "awayTeam"]:
        tid = summary["boxScoreSummary"][side]["teamId"]
        for row in summary["boxScoreSummary"][side]["periods"]:
            if qualified["period_scores"][row["period"]][tid] != row["score"]:
                raise ValueError("Qualified event period score differs from Summary")
    admissions = []
    for q in [2, 3]:
        records = {
            r["job"]["endpoint"]: r
            for r in cache.data["direct"].values()
            if r["job"]["endpoint"] in {"boxscoretraditionalv3", "boxscoreadvancedv3"}
            and r["job"]["parameters"].get("GameID") == "0022600161"
            and int(r["job"]["parameters"].get("RangeType", 0)) == 1
            and int(r["job"]["parameters"].get("StartPeriod", 0)) == q
            and int(r["job"]["parameters"].get("EndPeriod", 0)) == q
        }
        pair = {ep: cache.read(r) for ep, r in records.items()}
        window = next(w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == (q, q))
        try:
            import_window(
                pair["boxscoretraditionalv3"],
                pair["boxscoreadvancedv3"],
                game_id="0022600161",
                window=window,
                summary=summary,
                player_context=pc,
                team_context=teams,
            )
        except ValueError as exc:
            if str(exc) != "Invalid Traditional box-score duration":
                raise
        else:
            raise ValueError("Malformed period original unexpectedly accepted")
        copied, ledger = event_clock_copy(
            pair, events, whole, start=q, end=q, score_snapshots=proof
        )
        frames = import_window(
            copied["boxscoretraditionalv3"],
            copied["boxscoreadvancedv3"],
            game_id="0022600161",
            window=window,
            summary=summary,
            player_context=pc,
            team_context=teams,
        )
        for grain, frame in zip(["player", "team"], frames, strict=True):
            path = root / f"data/raw/{grain}_game_period_stats/{SUFFIX}"
            before = pd.read_csv(path)
            if (
                before.game_id.eq(22600161)
                & before.period_family.eq("quarter")
                & before.period_value.astype(str).eq(str(q))
            ).any():
                raise ValueError("Existing window replacement forbidden")
            _append_rows(path, frame)
        folder = output / f"clock-copies/0161-q{q}"
        folder.mkdir(parents=True)
        for ep, raw in copied.items():
            (folder / (ep + ".json")).write_bytes(raw)
        admissions.append(
            dict(
                game_id="0022600161",
                quarter=q,
                ledger=ledger,
                player_rows=len(frames[0]),
                team_rows=len(frames[1]),
            )
        )
    stages = []
    with _local_stage(root):
        for fn in [
            validate_raw.run,
            build_team_game_features.run,
            build_game_features.run,
            build_schedule_context_features.run,
            build_player_game_features.run,
            build_league_season_stats.run,
        ]:
            try:
                fn("2026-27", "Regular Season")
            except Exception as exc:
                stages.append(dict(stage=fn.__module__, state="failed", error=str(exc)))
            else:
                stages.append(dict(stage=fn.__module__, state="passed"))
        assessment = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=root / "data",
            generation_id="unpublished-retained-chronology-0161",
        )
        due = due_population(root, datetime.now(UTC))
        from nbatools.commands.player_game_finder import build_result

        consumers = []
        for q in [2, 3]:
            answer = build_result(
                player="Jalen Brunson",
                season="2026-27",
                quarter=str(q),
                start_date="2026-11-01",
                end_date="2026-11-03",
            )
            if answer.result_status != "ok" or 22600161 not in set(answer.games.game_id):
                raise ValueError("Qualified quarter consumer unavailable")
            consumers.append(dict(quarter=q, rows=answer.games.to_dict("records")))
    for path, raw in prior.items():
        observed = (root / path).read_bytes()
        if "/raw/" in path:
            if "game_period_stats/" in path:
                if not observed.startswith(raw):
                    raise ValueError("Prior period prefix changed")
            elif observed != raw:
                raise ValueError("Accepted raw data changed")
    period = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    seen = {
        (int(r.game_id), r.period_family, str(r.period_value).lower()) for r in period.itertuples()
    }
    report = dict(
        classification="qualified_retained_periods_not_full_readiness",
        source_event_sha256=hashlib.sha256(events).hexdigest(),
        score_snapshot_evidence=proof,
        qualified_period_facts=qualified,
        admissions=admissions,
        consumers=consumers,
        admitted_windows=len(seen),
        known_required_windows=647,
        remaining_period_windows=[
            ["0022600142", "quarter", "3"],
            ["0022600142", "half", "second"],
            ["0022600144", "quarter", "2"],
            ["0022600144", "half", "first"],
        ],
        raw_bytes_preserved=True,
        prior_period_prefixes_preserved=True,
        required_raw=11,
        required_processed=5,
        executed_stages=stages,
        dataset_assessment=assessment,
        due_population=due,
        full_snapshot_accepted=False,
        production_writes=0,
    )
    (output / "assessment.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    stage(args.cache, args.output)
