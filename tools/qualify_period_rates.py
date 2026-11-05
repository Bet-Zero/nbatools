"""Qualify grouped corrected-count rates offline, with explicit missing dependencies.

Reported rates and possessions are never inputs to the calculation. Original
snapshots and every cell outside the declared withheld population are preserved.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pandas as pd

from tools.period_event_evidence import _alias, clock_facts, event_clock, period_facts, require
from tools.qualify_period_counts import (
    EVIDENCE as PRIOR,
)
from tools.qualify_period_counts import (
    FIELDS_BY_COLUMN,
    _window,
    count_events,
    retained_sources,
    sha,
)
from tools.stage_current_season import CURRENT, SUFFIX, _whole_original

STAGE_SHA = "6cecb60c127321c794733c65818054711445fcf9d6c049de342607fcb614060b"
FT = re.compile(r"Free Throw ([123]) of ([123])")
INPUTS = {
    "ast_pct": {"ast", "fgm"},
    "reb_pct": {"reb"},
    "tov_pct": {"fga", "fta", "tov", "ast"},
    "usg_pct": {"fga", "fta", "tov"},
}


def whole_original(gid):
    if gid in {"0022600138", "0022600142"}:
        from tools.season_rollover_source_stats import retained_stats_documents

        retained_stats_documents(CURRENT.parent)
        with zipfile.ZipFile(CURRENT.parent / "stats-sources.zip") as z:
            return z.read(f"representative-sources/traditional_{gid}.json")
    return _whole_original(gid)


def free_throw_facts(acts, teams):
    """Complete ordinary trips, and-ones and nonpossession technical attempts.

    Flagrant, missing subtype, canceled attempts and ambiguous foul credit reject
    this period's trip-dependent rates; they do not prevent assist qualification.
    """
    trips, credit, andones, dead = Counter(), {}, {}, set()
    for r in acts:
        if r["actionType"] != "Free Throw":
            continue
        aid, tid, pid = r["actionId"], r["teamId"], r["personId"]
        match = FT.fullmatch(r["subType"])
        fouls = [
            a
            for a in acts
            if a["actionId"] < aid and a["clock"] == r["clock"] and a["actionType"] == "Foul"
        ]
        # Match award types before requiring one anchor. A same-clock technical
        # is a separate award; an unpenalized personal foul cannot award an
        # ordinary multi-attempt trip. Unsupported foul types remain candidates
        # so their statistical meaning is never guessed by filtering them away.
        if r["subType"] == "Free Throw Technical":
            fouls = [a for a in fouls if a["subType"] in {"Technical", "Defense 3 Second"}]
        elif match is not None:
            fouls = [
                a
                for a in fouls
                if a["subType"] != "Technical"
                and not (
                    int(match[2]) > 1
                    and a["subType"] == "Personal"
                    and "PN" not in a["description"]
                )
            ]
        require(len(fouls) == 1, "FT lacks unique same-clock foul")
        foul = fouls[0]
        technical = r["subType"] == "Free Throw Technical" or (
            match is not None
            and match[1] == match[2] == "1"
            and foul["subType"] == "Defense 3 Second"
        )
        require(technical or match is not None, "Unsupported FT subtype")
        require(
            technical
            or foul["subType"] in {"Shooting", "Personal", "Loose Ball"}
            or (foul["subType"] == "Personal Take" and match is not None and int(match[2]) > 1),
            "Unsupported FT foul semantics",
        )
        require(
            technical or foul["subType"] == "Shooting" or "PN" in foul["description"],
            "Nonshooting FT lacks penalty foul evidence",
        )
        require(
            foul["teamId"] in ((teams - {tid}) | {0} if technical else teams - {tid}),
            "FT foul ownership differs",
        )
        require(
            not technical or foul["subType"] in {"Technical", "Defense 3 Second"},
            "Technical FT lacks qualified technical foul",
        )
        credit[aid] = foul["actionId"]
        if not technical:
            group = [
                a
                for a in acts
                if a["clock"] == r["clock"]
                and a["teamId"] == tid
                and a["personId"] == pid
                and FT.fullmatch(a["subType"])
            ]
            require(
                [FT.fullmatch(a["subType"])[1] for a in group]
                == list(map(str, range(1, int(match[2]) + 1)))
                and all(FT.fullmatch(a["subType"])[2] == match[2] for a in group),
                "Incomplete or conflicting FT trip",
            )
            if match[1] == "1":
                if match[2] == "1":
                    made = [
                        a
                        for a in acts
                        if a["actionType"] == "Made Shot"
                        and a["clock"] == r["clock"]
                        and a["teamId"] == tid
                        and a["personId"] == pid
                        and a["actionId"] < foul["actionId"]
                    ]
                    require(len(made) == 1, "And-one lacks unique made shot")
                    andones[made[0]["actionId"]] = aid
                else:
                    trips[pid] += 1
        if r["description"].startswith("MISS ") and (technical or match[1] != match[2]):
            following = next((a for a in acts if a["actionId"] == aid + 1), None)
            require(
                following is not None
                and following["actionType"] == "Rebound"
                and following["teamId"] == 0
                and following["personId"] == tid
                and following["clock"] == r["clock"],
                "Missing dead-ball FT rebound",
            )
            dead.add(aid + 1)
    return dict(trips=trips, credit=credit, andones=andones, dead=dead)


def rebound_facts(acts, teams):
    """Identify dead-ball rebounds from literal nonterminal/technical FT evidence."""
    dead, pending = set(), None
    for i, r in enumerate(acts):
        kind = r["actionType"]
        if kind == "Free Throw":
            match = FT.fullmatch(r["subType"])
            fouls = [a for a in acts[:i] if a["clock"] == r["clock"] and a["actionType"] == "Foul"]
            technical = r["subType"] == "Free Throw Technical" or (
                match is not None
                and match[1] == match[2] == "1"
                and len(fouls) == 1
                and fouls[0]["subType"] == "Defense 3 Second"
            )
            require(technical or match is not None, "Unqualified rebound FT semantics")
            if r["description"].startswith("MISS ") and (technical or match[1] != match[2]):
                require(i + 1 < len(acts), "Missing dead-ball rebound")
                nxt = acts[i + 1]
                require(
                    nxt["actionType"] == "Rebound"
                    and nxt["teamId"] == 0
                    and nxt["personId"] == r["teamId"]
                    and nxt["clock"] == r["clock"],
                    "Conflicting dead-ball rebound",
                )
                dead.add(nxt["actionId"])
            pending = r if r["description"].startswith("MISS ") else None
        elif kind in {"Made Shot", "Missed Shot", "Heave"}:
            pending = r if kind != "Made Shot" else None
        elif kind == "Rebound" and r["actionId"] not in dead:
            owner = r["teamId"] if r["teamId"] else r["personId"]
            require(owner in teams and pending is not None, "Rebound lacks live missed attempt")
            # An end-period team rebound after a buzzer miss is not a live chance.
            if event_clock(r["clock"]) == 0 and r["teamId"] == 0:
                dead.add(r["actionId"])
            pending = None
    return dead


def play_exposure(acts, teams, lineups, ft, aliases):
    """Reused 0144 credit rule: positive elapsed exposure or scoring credit.

    Own offensive rebounds start another play. An unfinished positive-duration
    terminal play counts; zero-duration postscore shells do not count.
    """
    first = next(
        a for a in acts if a["actionType"] in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}
    )
    initial_owner = first["teamId"]
    if initial_owner == 0 and first["actionType"] == "Turnover":
        initial_owner = first["personId"]
    require(initial_owner in teams, "Unknown initial offensive play owner")
    owner, seconds, scoring = initial_owner, Counter(), set()
    previous, pending = event_clock(acts[0]["clock"]), None
    plays = []

    def finish(aid, incomplete=False):
        require(owner in teams, "Unestablished offensive play")
        players = {p for p, sec in seconds.items() if sec > 0} | scoring
        if players:
            plays.append(
                dict(
                    team_id=owner,
                    end_action=aid,
                    players=sorted(players),
                    elapsed_seconds={p: str(v) for p, v in seconds.items()},
                    scoring_credit_players=sorted(scoring),
                    incomplete=incomplete,
                )
            )

    for r in acts:
        aid, tid, kind = r["actionId"], r["teamId"], r["actionType"]
        if kind == "Turnover" and tid == 0:
            tid = r["personId"]
            require(tid in teams, "Unknown team turnover owner")
        current = event_clock(r["clock"])
        if owner is not None:
            for p in lineups[aid][owner]:
                seconds[p] += previous - current
        previous = current
        if kind == "Substitution":
            continue
        if kind == "Free Throw" and aid in ft["credit"]:
            anchor = ft["credit"][aid]
            technical = (
                r["subType"] == "Free Throw Technical"
                or FT.fullmatch(r["subType"])[2] == "1"
                and aid not in ft["andones"].values()
            )
            if not r["description"].startswith("MISS ") and owner == tid:
                scoring.update(lineups[anchor][tid])
            if technical:
                continue
        if kind == "Made Shot":
            scoring.update(lineups[aid][tid])
        if kind in {"Made Shot", "Missed Shot", "Turnover", "Free Throw"}:
            require(owner == tid, f"Action {aid} contradicts offensive play owner {owner}: {tid}")
        match = FT.fullmatch(r["subType"]) if kind == "Free Throw" else None
        terminal = (
            kind in {"Made Shot", "Missed Shot", "Turnover", "Heave"}
            or match
            and match[1] == match[2]
        )
        if kind == "Made Shot" and aid in ft["andones"]:
            terminal = False
        if terminal:
            require(owner is not None, "Unestablished play end")
            if kind == "Heave":
                require(
                    tid == r["personId"] == 0 and r["subType"] == "Team Field Goal Attempt",
                    "Unsupported heave",
                )
            finish(aid)
            made = (
                kind == "Made Shot"
                or kind == "Free Throw"
                and not r["description"].startswith("MISS ")
            )
            if made or kind == "Turnover":
                owner = next(t for t in teams if t != owner)
                pending = None
            else:
                pending, owner = owner, None
            seconds, scoring = Counter(), set()
        elif kind == "Rebound" and aid not in ft["dead"]:
            require(owner is None and pending is not None, "Rebound lacks pending play end")
            owner = tid if tid else r["personId"]
            require(owner in teams, "Unknown rebound owner")
            pending = None
        elif kind == "Jump Ball":
            winner = re.search(r": Tip to (.+)$", r["description"])
            require(winner is not None, "Missing jump-ball winner")
            owners = [t for t in teams if aliases[t].get(_alias(winner[1]))]
            require(owners == [owner], "Jump ball ownership is not independently established")
        elif kind == "period" and r["subType"] == "end":
            if owner is not None:
                finish(aid, incomplete=True)
            owner = None
    return plays


def game_basis(raw, whole_raw, periods):
    counts, actions, count_facts = count_events(raw, whole_raw)
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    teams = {whole[s]["teamId"] for s in ("homeTeam", "awayTeam")}
    final = {whole[s]["teamId"]: whole[s]["statistics"]["points"] for s in ("homeTeam", "awayTeam")}
    score_error = None
    try:
        facts = period_facts(
            raw,
            game_id=whole["gameId"],
            final_teams=final,
            score_snapshots=count_facts.get("score_metadata_evidence"),
        )
    except ValueError as exc:
        facts, score_error = None, str(exc)
    rows = json.loads(raw)["game"]["actions"]
    aliases = {}
    for side in ("homeTeam", "awayTeam"):
        team = whole[side]
        index = defaultdict(set)
        for p in team["players"]:
            for family in (p["familyName"], re.sub(r"\s+Jr\.?$", "", p["familyName"])):
                index[_alias(family)].add(p["personId"])
                for size in range(1, len(p["firstName"]) + 1):
                    index[_alias(p["firstName"][:size] + " " + family)].add(p["personId"])
        aliases[team["teamId"]] = index
    result = {}
    for q in sorted(periods):
        acts = [a for a in rows if a["period"] == q]
        basis = dict(counts=counts, errors={}, teammate_fgm=Counter(), rebound_chances=Counter())
        try:
            ft = free_throw_facts(acts, teams)
            basis["trips"] = ft["trips"]
        except ValueError as exc:
            ft = None
            basis["errors"]["tov_pct"] = basis["errors"]["usg_pct"] = str(exc)
        try:
            require(facts is not None, score_error or "Score chronology unknown")
            trace = []
            basis["clocks"] = clock_facts(
                raw, whole_raw, period_report=facts, only_periods={q}, trace=trace
            )[q]
            lineups = {r["action_id"]: r["lineups"] for r in trace}
            # clock_facts proves the complete substitution sequence. Retain the
            # pre-substitution lineup for elapsed time ending at that action;
            # incoming players receive only time after their entry clock.
            active = {t: set(ps) for t, ps in lineups[acts[0]["actionId"]].items()}
            for a in acts:
                aid, tid = a["actionId"], a["teamId"]
                if a["actionType"] == "Substitution":
                    lineups[aid] = {t: sorted(ps) for t, ps in active.items()}
                    incoming = re.fullmatch(r"SUB: (.+) FOR (.+)", a["description"])
                    choices = aliases[tid].get(_alias(incoming[1]), set()) if incoming else set()
                    require(len(choices) == 1, "Ambiguous interval substitution")
                    active[tid].remove(a["personId"])
                    active[tid].add(next(iter(choices)))
                else:
                    require(
                        {t: sorted(ps) for t, ps in active.items()} == lineups[aid],
                        "Elapsed interval lineup differs from qualified trace",
                    )
            for a in acts:
                if a["actionType"] == "Made Shot":
                    for p in lineups[a["actionId"]][a["teamId"]]:
                        basis["teammate_fgm"][p] += p != a["personId"]
            try:
                dead = rebound_facts(acts, teams)
                for a in acts:
                    if a["actionType"] == "Rebound" and a["actionId"] not in dead:
                        for values in lineups[a["actionId"]].values():
                            basis["rebound_chances"].update(values)
                basis["dead_rebound_ids"] = sorted(dead)
            except ValueError as exc:
                basis["errors"]["reb_pct"] = str(exc)
            if ft is not None:
                try:
                    basis["plays"] = play_exposure(acts, teams, lineups, ft, aliases)
                except ValueError as exc:
                    basis["errors"]["usg_pct"] = str(exc)
        except ValueError as exc:
            for f in ("ast_pct", "reb_pct", "usg_pct"):
                basis["errors"][f] = str(exc)
        result[q] = basis
    return counts, actions, whole, result


def fresh_schedule_due(root, checked_at):
    """Reassess the exact cutoff from the authenticated retained official body."""
    from nbatools.commands.pipeline.official_schedule import normalize_official_schedule
    from nbatools.readiness import _missing_due_game_ids

    archive = PRIOR / "freshness-timing-originals.zip"
    require(
        sha(archive.read_bytes())
        == "2ca9194808c2856a510f52f48ab07ef5a06bb197aa3a96fc9f8969f9d654846e",
        "Retained official schedule archive differs",
    )
    with zipfile.ZipFile(archive) as z:
        raw = z.read("fresh-schedule.json")
    require(
        sha(raw) == "53e6083424d33d8941eff07a655e2922b63169f4185392ee0545ff19b0e46563",
        "Retained official schedule body differs",
    )
    schedule = normalize_official_schedule(raw, "2026-27")
    games = pd.read_csv(root / f"data/raw/games/{SUFFIX}")
    due = _missing_due_game_ids(schedule, games.iloc[:0], checked_at, "2026-27", "Regular Season")
    missing = _missing_due_game_ids(schedule, games, checked_at, "2026-27", "Regular Season")
    require(due is not None and missing is not None, "Exact due coverage unknown")
    return dict(
        checked_at=checked_at.isoformat(),
        lag_hours=24,
        due_game_ids=list(due),
        missing_due_game_ids=list(missing),
        schedule_sha256=sha(raw),
        archive_revision="2b57bdead60b670e161e4f9d265380dbab97c4e0",
        production_freshness_accepted=False,
    )


def teams_in_whole(whole):
    return {whole[s]["teamId"] for s in ("homeTeam", "awayTeam")}


def qualify(output: Path, *, now=None):
    from nbatools.commands.validation_control import build_slice_manifest
    from tools.assess_readiness_recovery import due_population
    from tools.qualify_rollover_q1 import _local_stage

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = PRIOR / "qualification-evidence.zip"
    require(sha(archive.read_bytes()) == STAGE_SHA, "PR579 stage differs")
    with zipfile.ZipFile(archive) as z:
        prior = json.loads(z.read("qualification.json"))
        original = {
            n: z.read(n) for n in z.namelist() if n.startswith("stage/data/") and n.endswith(".csv")
        }
    for name, raw in original.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    name = f"stage/data/raw/player_game_period_stats/{SUFFIX}"
    frame = pd.read_csv(io.BytesIO(original[name]))
    core = pd.read_csv(output / f"stage/data/raw/player_game_stats/{SUFFIX}")
    targets = prior["explicit_rate_invalidations"]
    require(
        len(targets) == 1365 and all(c["dataset"] == "player" for c in targets),
        "Withheld population differs",
    )
    groups = defaultdict(list)
    for c in targets:
        row = frame.iloc[c["row"]]
        require(pd.isna(row[c["field"]]), "Withheld observation is not unknown")
        groups[str(int(row.game_id)).zfill(10), tuple(_window(row)), c["field"]].append(c)
    sources, calculated, unknown, vectors, ledgers = retained_sources(), [], [], [], []
    cache = {}
    for gid, periods, field in sorted(groups):
        if gid not in cache:
            all_periods = {q for g, qs, _ in groups if g == gid for q in qs}
            cache[gid] = game_basis(sources[gid], whole_original(gid), all_periods)
        counts, actions, whole, basis = cache[gid]
        error = next(
            (basis[q]["errors"][field] for q in periods if field in basis[q]["errors"]), None
        )
        # Every numerator field needs complete whole-game independent corroboration,
        # and every affected window needs its complete preserved count vector.
        if error is None:
            try:
                for side in ("homeTeam", "awayTeam"):
                    team = whole[side]
                    for p in team["players"]:
                        pid, tid = p["personId"], team["teamId"]
                        canonical = core.loc[
                            core.game_id.eq(int(gid))
                            & core.team_id.eq(tid)
                            & core.player_id.eq(pid)
                        ]
                        for f in INPUTS[field]:
                            total = sum(
                                v
                                for (q, t, player, col), v in counts.items()
                                if (t, player, col) == (tid, pid, f)
                            )
                            require(
                                total == p["statistics"][FIELDS_BY_COLUMN[f]],
                                "Independent whole count vector differs: " + f,
                            )
                            require(
                                (len(canonical) == 1 and total == canonical.iloc[0][f])
                                or (canonical.empty and total == 0),
                                "Preserved canonical vector differs: " + f,
                            )
                selected = frame.loc[
                    frame.game_id.eq(int(gid))
                    & frame.source_start_period.eq(periods[0])
                    & frame.source_end_period.eq(periods[-1])
                ]
                if field in {"ast_pct", "reb_pct", "usg_pct"}:
                    for tid in teams_in_whole(whole):
                        exposed = {
                            pid
                            for q in periods
                            for pid, seconds in basis[q]["clocks"][tid].items()
                            if seconds > 0
                        }
                        scoped = selected.loc[selected.team_id.eq(tid)]
                        require(
                            exposed == set(scoped.loc[scoped.minutes.gt(0), "player_id"]),
                            "Complete positive-player population differs",
                        )
                for _, row in selected.iterrows():
                    if field in {"ast_pct", "reb_pct", "usg_pct"}:
                        seconds = sum(
                            basis[q]["clocks"][int(row.team_id)].get(
                                int(row.player_id), Fraction(0)
                            )
                            for q in periods
                        )
                        require(
                            abs(seconds - Fraction(str(row.minutes)) * 60) <= 2,
                            "Complete window clock vector differs",
                        )
                    for f in INPUTS[field]:
                        expected = sum(counts[q, row.team_id, row.player_id, f] for q in periods)
                        require(row[f] == expected, "Window count vector differs: " + f)
                vectors.append(
                    dict(
                        game_id=gid,
                        periods=periods,
                        field=field,
                        rows=len(selected),
                        fields=sorted(INPUTS[field]),
                    )
                )
            except ValueError as exc:
                error = str(exc)
        cases = []
        if error is None:
            for c in groups[gid, periods, field]:
                row = frame.iloc[c["row"]]
                pid, tid = int(row.player_id), int(row.team_id)
                stat = "ast" if field == "ast_pct" else "reb" if field == "reb_pct" else "tov"
                n = sum(counts[q, tid, pid, stat] for q in periods)
                trips = sum(basis[q].get("trips", Counter())[pid] for q in periods)
                involvement = (
                    sum(counts[q, tid, pid, "fga"] + counts[q, tid, pid, "tov"] for q in periods)
                    + trips
                )
                if field == "ast_pct":
                    d = sum(basis[q]["teammate_fgm"][pid] for q in periods)
                elif field == "reb_pct":
                    d = sum(basis[q]["rebound_chances"][pid] for q in periods)
                elif field == "tov_pct":
                    d = involvement + sum(counts[q, tid, pid, "ast"] for q in periods)
                else:
                    n = involvement
                    d = sum(
                        pid in play["players"]
                        for q in periods
                        for play in basis[q]["plays"]
                        if play["team_id"] == tid
                    )
                if not 0 <= n <= d:
                    error = "Numerator outside qualified denominator"
                    break
                cases.append(
                    dict(
                        c,
                        game_id=gid,
                        periods=periods,
                        team_id=tid,
                        player_id=pid,
                        numerator=n,
                        denominator=d,
                        exact=str(Fraction(n, d) if d else Fraction(0)),
                        after=float(Fraction(n, d)) if d else 0.0,
                    )
                )
        if error is not None:
            unknown.extend(
                dict(c, game_id=gid, periods=periods, reason=error)
                for c in groups[gid, periods, field]
            )
        else:
            calculated.extend(cases)
        ledgers.append(
            dict(
                game_id=gid,
                periods=periods,
                field=field,
                observations=len(groups[gid, periods, field]),
                qualified=error is None,
                reason=error,
            )
        )
    records = list(csv.reader(io.StringIO(original[name].decode())))
    lines = original[name].decode().splitlines(keepends=True)
    for c in calculated:
        records[c["row"] + 1][records[0].index(c["field"])] = str(c["after"])
    for i in {c["row"] for c in calculated}:
        stream = io.StringIO()
        csv.writer(stream, lineterminator="\n").writerow(records[i + 1])
        lines[i + 1] = stream.getvalue()
    (output / name).write_text("".join(lines))
    replay = {}
    for gid, (_, _, _, basis) in cache.items():
        replay[gid] = {q: {k: v for k, v in b.items() if k != "counts"} for q, b in basis.items()}
    (output / "event-basis.json").write_text(json.dumps(replay, indent=2, default=str) + "\n")
    checked_at = now or datetime.now(UTC)
    fresh_due = fresh_schedule_due(output / "stage", checked_at)
    with _local_stage(output / "stage"):
        assessment = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=output / "stage/data",
            generation_id="unpublished-grouped-rate-copy",
        )
        due = due_population(output / "stage", checked_at)
    require(due["due_game_ids"] == fresh_due["due_game_ids"], "Staged and fresh due IDs differ")
    report = dict(
        classification="grouped_rate_qualified_partial_unpublished_copy",
        original_withheld=1365,
        qualified=len(calculated),
        unresolved=len(unknown),
        qualified_by_field=dict(Counter(c["field"] for c in calculated)),
        unresolved_by_field=dict(Counter(c["field"] for c in unknown)),
        changes=calculated,
        unknown=unknown,
        groups=ledgers,
        complete_vectors=vectors,
        dataset_assessment=assessment,
        due_population=fresh_due,
        staged_schedule_due_population=due,
        reported_rates_used_as_oracle=False,
        reported_possessions_used_as_oracle=False,
        production_ready=False,
        full_numerical_acceptance=False,
        production_writes=0,
        source_hashes={
            gid: dict(events=sha(sources[gid]), whole=sha(whole_original(gid))) for gid in cache
        },
    )
    require(len(calculated) + len(unknown) == 1365, "Incomplete rate accounting")
    (output / "qualification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    qualify(args.output)
