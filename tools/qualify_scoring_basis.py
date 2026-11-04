"""Qualify event shooting counts separately from unavailable clock/rate facts."""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from tools.period_event_evidence import clock_facts, period_facts
from tools.readiness_refresh import SourceCache
from tools.season_rollover_core_bridge import _additional_sources
from tools.stage_current_season import CURRENT, originals

SHOOTING = {
    "fieldGoalsMade": "fgm",
    "fieldGoalsAttempted": "fga",
    "threePointersMade": "fg3m",
    "threePointersAttempted": "fg3a",
    "freeThrowsMade": "ftm",
    "freeThrowsAttempted": "fta",
    "points": "pts",
}


def shooting_counts(raw, *, start, end):
    """Every literal made/missed shot and FT; no estimated FT coefficient for counts."""
    totals = defaultdict(lambda: dict.fromkeys(SHOOTING.values(), 0))
    evidence = []
    for row in json.loads(raw)["game"]["actions"]:
        if not start <= row["period"] <= end:
            continue
        if row["actionType"] not in {"Made Shot", "Missed Shot", "Free Throw"}:
            continue
        tid, pid = row["teamId"], row["personId"]
        if tid <= 0 or pid <= 0:
            raise ValueError("Shooting event identity absent")
        values = dict.fromkeys(SHOOTING.values(), 0)
        if row["actionType"] in {"Made Shot", "Missed Shot"}:
            if row["shotValue"] not in [2, 3]:
                raise ValueError("Invalid literal shot value")
            made = int(row["actionType"] == "Made Shot")
            values.update(
                fga=1,
                fgm=made,
                fg3a=int(row["shotValue"] == 3),
                fg3m=made * int(row["shotValue"] == 3),
                pts=made * row["shotValue"],
            )
        else:
            made = int(not row["description"].startswith("MISS "))
            values.update(fta=1, ftm=made, pts=made)
        for key in [(tid, pid), (tid, 0)]:
            for name, value in values.items():
                totals[key][name] += value
        evidence.append(
            dict(
                action_id=row["actionId"],
                period=row["period"],
                clock=row["clock"],
                team_id=tid,
                player_id=pid,
                kind=row["actionType"],
                description=row["description"],
                counts=values,
            )
        )
    return dict(totals), evidence


def qualify(cache_path: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    cache = SourceCache(cache_path)
    bodies, _ = originals()
    reports = []
    for gid, windows in [("0022600142", [(3, 3), (3, 4)]), ("0022600144", [(2, 2), (1, 2)])]:
        if gid.endswith("0144"):
            sources = _additional_sources(CURRENT.parent)
            event = sources["pbp.json"].raw
            summary = sources["summary.json"].document
        else:
            event = bodies[f"playbyplayv3-{gid}.json"]
            from tools.qualify_incremental_return import SUMMARY_ARCHIVES, bound_zip

            path = CURRENT.parent / "recovery-capture-20261104/supplementary-sources.zip"
            with bound_zip(path, SUMMARY_ARCHIVES["supplementary-sources.zip"]) as z:
                summary = json.loads(z.read("summaries/" + gid + ".json"))
        whole_record = next(
            r
            for r in cache.data["direct"].values()
            if r["job"]["endpoint"] == "boxscoretraditionalv3"
            and str(r["job"]["parameters"].get("GameID")).zfill(10) == gid
            and int(r["job"]["parameters"].get("StartPeriod", 0)) == 0
        )
        whole = cache.read(whole_record)
        box = json.loads(whole)["boxScoreTraditional"]
        facts = period_facts(
            event,
            game_id=gid,
            final_teams={
                box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
            },
        )
        try:
            clocks = clock_facts(event, whole, period_report=facts)
        except ValueError as exc:
            clock_status = dict(unique=False, error=str(exc))
        else:
            clock_status = dict(unique=True, periods=sorted(clocks))
        for start, end in windows:
            pair = {
                r["job"]["endpoint"]: r
                for r in cache.data["direct"].values()
                if r["job"]["endpoint"] in {"boxscoretraditionalv3", "boxscoreadvancedv3"}
                and r["job"]["parameters"].get("GameID") == gid
                and int(r["job"]["parameters"].get("RangeType", 0)) == 1
                and int(r["job"]["parameters"].get("StartPeriod", 0)) == start
                and int(r["job"]["parameters"].get("EndPeriod", 0)) == end
            }
            original = json.loads(cache.read(pair["boxscoretraditionalv3"]))
            advanced = json.loads(cache.read(pair["boxscoreadvancedv3"]))["boxScoreAdvanced"]
            candidate = copy.deepcopy(original)
            changes = []
            missing = []
            basis = []
            counts, observations = shooting_counts(event, start=start, end=end)
            for side in ["homeTeam", "awayTeam"]:
                team = candidate["boxScoreTraditional"][side]
                tid = team["teamId"]
                expected = sum(
                    p["score"]
                    for p in summary["boxScoreSummary"][side]["periods"]
                    if start <= p["period"] <= end
                )
                if counts[(tid, 0)]["pts"] != expected:
                    raise ValueError("Event shooting points differ from Summary")
                listed = {p["personId"] for p in team["players"]}
                for (event_tid, pid), row in counts.items():
                    if event_tid == tid and pid and pid not in listed:
                        missing.append(
                            dict(
                                team_id=tid, player_id=pid, shooting_counts=row, clock_unknown=True
                            )
                        )
                for pid, stats in [
                    (0, team["statistics"]),
                    *[(p["personId"], p["statistics"]) for p in team["players"]],
                ]:
                    row = counts.get((tid, pid), dict.fromkeys(SHOOTING.values(), 0))
                    for field, col in SHOOTING.items():
                        if stats[field] != row[col]:
                            changes.append(
                                dict(
                                    team_id=tid,
                                    player_id=pid,
                                    field=field,
                                    before=stats[field],
                                    after=row[col],
                                )
                            )
                            stats[field] = row[col]
                    denominator = 2 * (Fraction(row["fga"]) + Fraction(11, 25) * row["fta"])
                    ts = Fraction(row["pts"], 1) / denominator if denominator else Fraction(0)
                    reported = (
                        advanced[side]["statistics"]
                        if pid == 0
                        else next(
                            (
                                p["statistics"]
                                for p in advanced[side]["players"]
                                if p["personId"] == pid
                            ),
                            None,
                        )
                    )
                    basis.append(
                        dict(
                            team_id=tid,
                            player_id=pid,
                            derived_ts=str(ts),
                            reported_ts=None
                            if reported is None
                            else reported.get("trueShootingPercentage"),
                            independent_count_basis=row,
                            reported_rate_promoted=False,
                        )
                    )
            # Copies remain field-scoped, not imported period data: source shooting
            # percentages and every original Advanced rate are still unqualified.
            folder = output / f"{gid}-{start}-{end}"
            folder.mkdir()
            (folder / "traditional-count-copy.json").write_text(
                json.dumps(candidate, indent=2) + "\n"
            )
            reports.append(
                dict(
                    game_id=gid,
                    start=start,
                    end=end,
                    changes=changes,
                    missing_positive_identities=missing,
                    event_shooting_observations=observations,
                    exact_ts_count_basis=basis,
                    clock_qualification=clock_status,
                    event_sha256=facts["source_sha256"],
                    sources={ep: r["sha256"] for ep, r in pair.items()},
                    period_admitted=False,
                    advanced_repaired=False,
                    source_bytes_changed=False,
                )
            )
    report = dict(
        classification="independent_shooting_field_evidence_not_period_acceptance",
        windows=reports,
        full_snapshot_accepted=False,
        production_writes=0,
    )
    (output / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    qualify(args.cache, args.output)
