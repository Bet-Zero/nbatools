"""Offline count-credit qualification; preserves original snapshots and rate gates.

This is a bounded evidence tool, not a general possession or publication path.
A revised count snapshot explicitly invalidates dependent imported rates. Missing
0142 rows are count evidence only and never fabricated into Advanced observations.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tools.period_event_evidence import (
    _alias,
    event_clock,
    period_facts,
    require,
    same_clock_score_evidence,
)
from tools.qualify_minute_precision import authenticate_sources
from tools.season_rollover_core_bridge import FIELDS
from tools.stage_current_season import CURRENT, SUFFIX, _whole_original, originals

EVIDENCE = CURRENT.parent / "count-credit-20261104"
FIELDS_BY_COLUMN = {v.lower(): k for k, v in FIELDS.items()}
RATE_FIELDS = ("usg_pct", "ast_pct", "reb_pct", "tov_pct")
COUNT_FIELDS = (
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "pts",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
)
PRIOR = CURRENT.parent / "technical-ft-20261104"
STAGE_SHA = "ea4ecc075abf28e8c09b662185ad40a86f9d94ed18aec2a330ffbb485e846296"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def count_events(raw, whole_raw):
    """Literal event credits, checked against paired actions; no suffix arithmetic."""
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    gid = whole["gameId"]
    teams = {whole[s]["teamId"]: whole[s] for s in ("homeTeam", "awayTeam")}
    final = {t: x["statistics"]["points"] for t, x in teams.items()}
    document = json.loads(raw)["game"]
    require(document["gameId"] == gid, "Event game differs")
    rows = document["actions"]
    try:
        facts = period_facts(raw, game_id=gid, final_teams=final)
    except ValueError as exc:
        strict_error = str(exc)
        require(strict_error == "Unexplained event score change", strict_error)
        try:
            proof = same_clock_score_evidence(raw, game_id=gid, final_teams=final)
            facts = period_facts(raw, game_id=gid, final_teams=final, score_snapshots=proof)
            facts["score_metadata_evidence"] = proof
        except ValueError:
            # Count extraction is not a certificate for an event scoreboard or
            # on-court chronology. Preserve the strict failure. Only a separately
            # corroborated nonshooting vector may use this narrower evidence.
            facts = dict(strict_score_validation=False, strict_error=strict_error)
    previous = (1, event_clock("PT12M00S"))
    starts, ends = set(), set()
    for index, row in enumerate(rows, 1):
        q, clock = row["period"], event_clock(row["clock"])
        require(0 <= clock <= (720 if q <= 4 else 300), "Count event clock outside period")
        require(
            row["actionId"] == index and type(q) is int and 1 <= q <= 14,
            "Count event sequence malformed",
        )
        require(
            q == previous[0]
            and clock <= previous[1]
            or q == previous[0] + 1
            and clock == (720 if q <= 4 else 300),
            "Count events reordered or missing boundary",
        )
        if row["actionType"] == "period":
            if row["subType"] == "start":
                require(clock == (720 if q <= 4 else 300), "Period start clock differs")
                require(q not in starts, "Duplicate count period start")
                starts.add(q)
            elif row["subType"] == "end":
                require(clock == 0, "Period end clock differs")
                if q in ends:
                    omit = {"actionId", "actionNumber", "videoAvailable"}
                    require(
                        index == len(rows)
                        and index > 1
                        and {k: v for k, v in row.items() if k not in omit}
                        == {k: v for k, v in rows[index - 2].items() if k not in omit},
                        "Conflicting or nonterminal duplicate period end",
                    )
                ends.add(q)
        previous = q, clock
    require(
        starts == ends == set(range(1, rows[-1]["period"] + 1)),
        "Count event period coverage incomplete",
    )
    aliases = defaultdict(set)
    identities = set()
    for tid, team in teams.items():
        for p in team["players"]:
            pid = p["personId"]
            identities.add((tid, pid))
            for family in (p["familyName"], re.sub(r"\s+Jr\.?$", "", p["familyName"])):
                aliases[tid, _alias(family)].add(pid)
                for n in range(1, len(p["firstName"]) + 1):
                    aliases[tid, _alias(p["firstName"][:n] + " " + family)].add(pid)
    counts, evidence = Counter(), []
    last_shot = None
    for index, r in enumerate(rows):
        tid, pid, q = r["teamId"], r["personId"], r["period"]
        kind, desc = r["actionType"], r["description"]
        updates = {}
        link = None
        if kind in ("Made Shot", "Missed Shot"):
            require(r["shotValue"] in (2, 3), "Unknown shot value")
            made = int(kind == "Made Shot")
            updates = dict(
                fga=1,
                fgm=made,
                fg3a=int(r["shotValue"] == 3),
                fg3m=made * int(r["shotValue"] == 3),
                pts=made * r["shotValue"],
            )
        elif kind == "Free Throw":
            made = int(not desc.startswith("MISS "))
            updates = dict(fta=1, ftm=made, pts=made)
        elif kind == "Turnover" and (tid, pid) in identities:
            updates = dict(tov=1)
        elif kind == "Rebound" and (tid, pid) in identities:
            require(
                last_shot is not None
                and last_shot["period"] == q
                and (
                    last_shot["actionType"] == "Missed Shot"
                    or (
                        last_shot["actionType"] == "Free Throw"
                        and last_shot["description"].startswith("MISS ")
                    )
                ),
                "Player rebound lacks preceding missed shot",
            )
            require(last_shot["teamId"] in teams, "Missed shot lacks paired team")
            updates = {"oreb" if last_shot["teamId"] == tid else "dreb": 1, "reb": 1}
            link = last_shot["actionId"]
        elif kind == "" and (" STEAL " in desc or " BLOCK " in desc):
            column, paired = ("stl", "Turnover") if " STEAL " in desc else ("blk", "Missed Shot")
            matches = [
                a
                for a in rows[max(0, index - 2) : index + 3]
                if a["actionType"] == paired
                and a["period"] == q
                and a["clock"] == r["clock"]
                and a["actionNumber"] == r["actionNumber"]
                and a["teamId"] in teams
                and a["teamId"] != tid
            ]
            require(len(matches) == 1, "Credit lacks unique paired opposing action")
            updates = {column: 1}
            link = matches[0]["actionId"]
        if updates:
            require((tid, pid) in identities, "Count actor absent from whole-game identity")
            for field, value in updates.items():
                counts[q, tid, pid, field] += value
            evidence.append(
                dict(
                    action_id=r["actionId"],
                    period=q,
                    clock=r["clock"],
                    team_id=tid,
                    player_id=pid,
                    counts=updates,
                    paired_action=link,
                )
            )
        if kind == "Made Shot":
            match = re.search(r"\(([^()]+) \d+ AST\)", desc)
            if match:
                choices = aliases[tid, _alias(match[1])]
                require(len(choices) == 1, "Assist name lacks unique literal identity")
                actor = next(iter(choices))
                counts[q, tid, actor, "ast"] += 1
                evidence.append(
                    dict(
                        action_id=r["actionId"],
                        period=q,
                        clock=r["clock"],
                        team_id=tid,
                        player_id=actor,
                        counts={"ast": 1},
                        paired_action=r["actionId"],
                    )
                )
            require("AST" not in desc or match is not None, "Unparsed assist credit")
        if kind in ("Made Shot", "Missed Shot", "Free Throw", "Heave"):
            last_shot = r
    return counts, evidence, facts


def retained_sources():
    bodies, _ = originals()
    sources = {
        json.loads(raw)["game"]["gameId"]: raw
        for name, raw in bodies.items()
        if name.startswith("playbyplayv3-")
    }
    precision_path = (
        CURRENT.parent / "retained-qualification-20261104/precision-source-originals.zip"
    )
    # The established authenticator binds immutable URL, SHA256, Git blob and exact scope.
    precision, _ = authenticate_sources(
        precision_path, "888bbbcf8a1bc4b15bdbb2a04433bcabe1b81da6994c8c593b37d2a9e9362bd2"
    )
    for gid, record in precision.items():
        sources.setdefault(gid, record["raw"])
    manifest = json.loads((EVIDENCE / "acquisition.json").read_text())
    require(
        manifest["source_body_requests"] == 10 and manifest["production_writes"] == 0,
        "Count capture authority differs",
    )
    archive = EVIDENCE / "source-originals.zip"
    require(sha(archive.read_bytes()) == manifest["archive_sha256"], "Count source archive differs")
    with zipfile.ZipFile(archive) as z:
        require(
            set(z.namelist()) == {r["name"] for r in manifest["files"]}, "Capture scope differs"
        )
        for r in manifest["files"]:
            raw = z.read(r["name"])
            gid = Path(r["name"]).stem
            require(gid not in sources, "Successful original acquired again")
            require(
                len(raw) == r["size"]
                and sha(raw) == r["sha256"]
                and hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == r["sha"],
                "Count source bytes differ",
            )
            require(
                r["path"] == f"nba_stats/json/playbyplayv3/2027/{gid}.json"
                and r["download_url"]
                == "https://raw.githubusercontent.com/sportsdataverse/"
                f"hoopR-nba-stats-raw/{manifest['revision']}/{r['path']}",
                "Count source immutable identity differs",
            )
            require(json.loads(raw)["game"]["gameId"] == gid, "Count event identity differs")
            sources[gid] = raw
    return sources


def _window(row):
    return range(int(row.source_start_period), int(row.source_end_period) + 1)


def fresh_due_and_timing(root, checked_at):
    """Changed archive availability closes 0160; fresh schedule binds the cutoff."""
    from fractions import Fraction

    from nbatools.commands.pipeline.official_schedule import normalize_official_schedule
    from nbatools.readiness import _missing_due_game_ids
    from tools.qualify_minute_precision import exact_game_clock

    manifest = json.loads((EVIDENCE / "freshness-timing-acquisition.json").read_text())
    archive = EVIDENCE / "freshness-timing-originals.zip"
    require(sha(archive.read_bytes()) == manifest["archive_sha256"], "Freshness archive differs")
    require(
        manifest["new_successful_body_requests"] == 2 and manifest["production_writes"] == 0,
        "Freshness source scope differs",
    )
    with zipfile.ZipFile(archive) as z:
        sources = {}
        for r in manifest["files"]:
            raw = z.read(r["file"])
            require(
                len(raw) == r["bytes"]
                and sha(raw) == r["sha256"]
                and hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == r["git_blob"],
                "Fresh source bytes differ",
            )
            sources[r["file"]] = raw
    directory = json.loads(sources["fresh-pbp-directory.json"])
    metadata = next(r for r in directory if r["name"] == "0022600160.json")
    require(
        metadata["sha"] == "e7a3c84ab2dd494d06b019d0ace81c7c548038b0",
        "Newly available timing source identity differs",
    )
    bodies, _ = originals()
    retained142 = bodies["playbyplayv3-0022600142.json"]
    blob142 = hashlib.sha1(f"blob {len(retained142)}\0".encode() + retained142).hexdigest()
    require(
        next(r for r in directory if r["name"] == "0022600142.json")["sha"] == blob142,
        "0142 changed; re-investigate before reusing ambiguity evidence",
    )
    facts, clocks, strict_error = exact_game_clock(
        sources["0022600160.json"], bodies["boxscoretraditionalv3-0022600160.json"]
    )
    seconds = sum(
        (teams[1610612737].get(1642854, Fraction(0)) for teams in clocks.values()), Fraction(0)
    )
    with zipfile.ZipFile(
        CURRENT.parent / "retained-qualification-20261104/qualification-evidence.zip"
    ) as z:
        prior = json.loads(z.read("minute-precision/qualification.json"))
    person = next(r for r in prior["player_results"] if r["player_id"] == 1642854)
    require(
        person["game_ids"] == ["0022600094", "0022600125", "0022600149", "0022600160"],
        "Precise minute sample changed",
    )
    previous = [
        Fraction(r["exact_seconds"])
        for r in person["game_clock_ledger"]
        if r["game_id"] != "0022600160"
    ]
    mean = (sum(previous, Fraction(0)) + seconds) / 240
    difference = abs(Fraction(person["reported_minute_literal"]) - mean)
    require(difference <= Fraction(1, 20), "Exact mean fails unchanged precision boundary")
    schedule_raw = sources["fresh-schedule.json"]
    schedule_metadata = next(
        r for r in json.loads(sources["fresh-schedule-directory.json"]) if r["name"] == "2027.json"
    )
    require(
        schedule_metadata["sha"] == "ef4feaa4328dba873c9cb18fd678c284775d68c8"
        and hashlib.sha1(f"blob {len(schedule_raw)}\0".encode() + schedule_raw).hexdigest()
        == schedule_metadata["sha"],
        "Fresh schedule blob differs",
    )
    schedule = normalize_official_schedule(schedule_raw, "2026-27")
    games = pd.read_csv(root / f"data/raw/games/{SUFFIX}")
    due = _missing_due_game_ids(schedule, games.iloc[:0], checked_at, "2026-27", "Regular Season")
    missing = _missing_due_game_ids(schedule, games, checked_at, "2026-27", "Regular Season")
    require(due is not None and missing is not None, "Fresh exact due population unknown")
    return dict(
        checked_at=checked_at.isoformat(),
        lag_hours=24,
        due_game_ids=list(due),
        missing_due_game_ids=list(missing),
        fresh_schedule_sha256=sha(schedule_raw),
        archive_revision=manifest["revision"],
        source_snapshot_is_not_production=True,
        timing_0160=dict(
            state="qualified_exact_complete_vector",
            exact_seconds=str(seconds),
            quarter_seconds=[str(clocks[q][1610612737][1642854]) for q in sorted(clocks)],
            reused_prior_seconds=list(map(str, previous)),
            exact_mean_minutes=str(mean),
            absolute_difference=str(difference),
            inclusive_limit="1/20",
            period_facts=facts,
            strict_score_error=strict_error,
            event_sha256=sha(sources["0022600160.json"]),
        ),
        game0142_pbp_unchanged=True,
    )


def qualify(output: Path, *, now=None):
    """Correct complete count vectors in an isolated, explicitly rate-incomplete copy."""
    from nbatools.commands.validation_control import build_slice_manifest
    from tools.assess_readiness_recovery import due_population
    from tools.qualify_rollover_q1 import _local_stage

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = PRIOR / "qualification-evidence.zip"
    require(sha(archive.read_bytes()) == STAGE_SHA, "Prior stage archive differs")
    root, original_bytes = output / "stage", {}
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.startswith("stage/data/") and name.endswith(".csv"):
                raw = z.read(name)
                path = output / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                original_bytes[name] = raw
    players_path = root / f"data/raw/player_game_period_stats/{SUFFIX}"
    teams_path = root / f"data/raw/team_game_period_stats/{SUFFIX}"
    period = pd.read_csv(players_path)
    team_period = pd.read_csv(teams_path)
    core = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
    old = json.loads((PRIOR / "count-coherence.json").read_text())
    original = json.loads((CURRENT / "period-basis-deltas.json").read_text())
    obligations = list(old["conflicts"])
    obligations += [
        dict(
            game_id=r["game_id"],
            team_id=r["team_id"],
            player_id=r["player_id"],
            field=r["field"].lower(),
            period_sum=r["period_sum"],
            canonical=r["staged_core"],
        )
        for r in original["conflicts"]
        if r["game_id"] == "0022600142"
    ]
    require(len(obligations) == 83, "Original obligation denominator differs")
    sources = retained_sources()
    changes, vectors, proofs, resolutions = [], [], [], []
    for gid in sorted({r["game_id"] for r in obligations}):
        fields = {r["field"] for r in obligations if r["game_id"] == gid}
        require(fields <= set(COUNT_FIELDS), "Unsupported count family")
        raw = sources[gid]
        if gid in {"0022600138", "0022600142"}:
            from tools.season_rollover_source_stats import retained_stats_documents

            retained_stats_documents(CURRENT.parent)
            with zipfile.ZipFile(CURRENT.parent / "stats-sources.zip") as z:
                whole_raw = z.read(f"representative-sources/traditional_{gid}.json")
        else:
            whole_raw = _whole_original(gid)
        counts, actions, facts = count_events(raw, whole_raw)
        require(
            facts.get("strict_score_validation") is not False
            or not fields.intersection({"fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "pts"}),
            "Shooting count promotion requires qualified event scoring",
        )
        whole = json.loads(whole_raw)["boxScoreTraditional"]
        selected = core.loc[core.game_id.eq(int(gid))]
        # Qualify the entire affected actor/stat population, including every zero.
        for side in ("homeTeam", "awayTeam"):
            t = whole[side]
            tid = t["teamId"]
            for person in t["players"]:
                pid = person["personId"]
                expected = selected.loc[selected.team_id.eq(tid) & selected.player_id.eq(pid)]
                for field in sorted(fields):
                    total = sum(
                        v
                        for (q, team, p, f), v in counts.items()
                        if (team, p, f) == (tid, pid, field)
                    )
                    direct = person["statistics"][FIELDS_BY_COLUMN[field]]
                    require(total == direct, "Event vector differs from independent whole source")
                    if len(expected):
                        require(
                            len(expected) == 1 and total == expected.iloc[0][field],
                            "Event vector differs from preserved canonical count",
                        )
                    else:
                        require(total == 0, "Nonzero event identity absent from canonical")
                    vectors.append(
                        dict(
                            game_id=gid,
                            team_id=tid,
                            player_id=pid,
                            field=field,
                            count=total,
                            direct_whole=direct,
                        )
                    )
        for r in obligations:
            if r["game_id"] == gid:
                total = sum(
                    v
                    for (q, t, p, f), v in counts.items()
                    if (t, p, f) == (r["team_id"], r["player_id"], r["field"])
                )
                require(total == r["canonical"], "Original obligation event basis differs")
                resolutions.append(
                    dict(
                        r,
                        event_count=total,
                        state="unadmitted_0142_count_proven"
                        if gid.endswith("0142")
                        else "resolved_in_explicit_count_copy",
                    )
                )
        game_rows = period.loc[period.game_id.eq(int(gid))]
        for index, row in game_rows.iterrows():
            for field in sorted(fields):
                value = sum(counts[q, row.team_id, row.player_id, field] for q in _window(row))
                if row[field] != value:
                    changes.append(
                        dict(
                            dataset="player",
                            row=int(index),
                            game_id=gid,
                            team_id=int(row.team_id),
                            player_id=int(row.player_id),
                            family=row.period_family,
                            window=str(row.period_value),
                            field=field,
                            before=row[field],
                            after=value,
                        )
                    )
                    period.loc[index, field] = value
        # Team credits are sums of player credits except rebounds/turnovers, which
        # include separate team events. Preserve those unaffected team source cells.
        for index, row in team_period.loc[team_period.game_id.eq(int(gid))].iterrows():
            for field in sorted(fields - {"oreb", "dreb", "reb", "tov"}):
                value = sum(
                    v
                    for (q, t, p, f), v in counts.items()
                    if q in _window(row) and (t, f) == (row.team_id, field)
                )
                if row[field] != value:
                    changes.append(
                        dict(
                            dataset="team",
                            row=int(index),
                            game_id=gid,
                            team_id=int(row.team_id),
                            player_id=0,
                            family=row.period_family,
                            window=str(row.period_value),
                            field=field,
                            before=row[field],
                            after=value,
                        )
                    )
                    team_period.loc[index, field] = value
        proofs.append(
            dict(
                game_id=gid,
                fields=sorted(fields),
                event_sha256=sha(raw),
                whole_sha256=sha(whole_raw),
                period_facts=facts,
                credits=actions,
            )
        )
    dependencies = dict(
        ast={"ast_pct"},
        oreb={"reb_pct"},
        dreb={"reb_pct"},
        reb={"reb_pct"},
        fgm={"ast_pct"},
        fga={"usg_pct", "tov_pct"},
        fta={"usg_pct", "tov_pct"},
        tov={"usg_pct", "tov_pct"},
    )
    changed_windows = defaultdict(set)
    for change in changes:
        changed_windows[change["game_id"], change["family"], change["window"]].update(
            dependencies.get(change["field"], set())
        )
    affected = sorted({r["game_id"] for r in changes})
    invalidations, derived_changes = [], []
    changed_cells = defaultdict(set)
    for change in changes:
        changed_cells[change["dataset"], change["row"]].add(change["field"])
    for frame, name, path in [(period, "player", players_path), (team_period, "team", teams_path)]:
        for index, row in frame.loc[frame.game_id.isin(map(int, affected))].iterrows():
            dependent = changed_windows[
                str(int(row.game_id)).zfill(10), row.period_family, str(row.period_value)
            ]
            for field in sorted(dependent & set(frame.columns)):
                if pd.notna(row[field]):
                    invalidations.append(
                        dict(
                            dataset=name, row=int(index), field=field, before=row[field], after=None
                        )
                    )
                    frame.loc[index, field] = float("nan")
            changed = changed_cells[name, index]
            ratios = [
                ({"fgm", "fga"}, "fg_pct", row.fgm / row.fga if row.fga else 0),
                ({"fg3m", "fg3a"}, "fg3_pct", row.fg3m / row.fg3a if row.fg3a else 0),
                ({"ftm", "fta"}, "ft_pct", row.ftm / row.fta if row.fta else 0),
                (
                    {"fgm", "fg3m", "fga"},
                    "efg_pct",
                    (row.fgm + 0.5 * row.fg3m) / row.fga if row.fga else 0,
                ),
            ]
            den = 2 * (row.fga + 0.44 * row.fta)
            ratios.append(({"pts", "fga", "fta"}, "ts_pct", row.pts / den if den else 0))
            for inputs, field, value in ratios:
                if changed & inputs and field in frame and row[field] != value:
                    derived_changes.append(
                        dict(
                            dataset=name,
                            row=int(index),
                            field=field,
                            before=row[field],
                            after=value,
                        )
                    )
                    frame.loc[index, field] = value
        # Patch only declared CSV cells; every untouched literal token survives.
        raw = path.read_bytes()
        lines = raw.decode().splitlines(keepends=True)
        records = list(csv.reader(io.StringIO(raw.decode())))
        header = records[0]
        for change in [*changes, *invalidations, *derived_changes]:
            if change["dataset"] == name:
                records[change["row"] + 1][header.index(change["field"])] = (
                    "" if change["after"] is None else str(change["after"])
                )
        modified = {
            c["row"] for c in [*changes, *invalidations, *derived_changes] if c["dataset"] == name
        }
        require(len(lines) == len(records), "Unexpected multiline CSV cannot be patched literally")
        for index in modified:
            stream = io.StringIO()
            csv.writer(stream, lineterminator="\n").writerow(records[index + 1])
            lines[index + 1] = stream.getvalue()
        path.write_text("".join(lines))
    # Verify complete disjoint vector coherence, not just the original mismatch cells.
    for vector in vectors:
        if vector["game_id"].endswith("0142"):
            continue
        rows = period.loc[
            period.game_id.eq(int(vector["game_id"]))
            & period.team_id.eq(vector["team_id"])
            & period.player_id.eq(vector["player_id"])
            & period.period_family.isin(["quarter", "overtime"])
        ]
        require(rows[vector["field"]].sum() == vector["count"], "Corrected vector is incomplete")
    checked_at = now or datetime.now(UTC)
    fresh = fresh_due_and_timing(root, checked_at)
    with _local_stage(root):
        assessment = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=root / "data",
            generation_id="unpublished-count-credit-copy",
        )
        due = due_population(root, checked_at)
        require(
            due["due_game_ids"] == fresh["due_game_ids"],
            "Fresh due population changed; refresh the affected source families",
        )
    # Whole-game and all other raw inputs remain byte-identical; original period
    # bytes live in the immutable prior ZIP, not overwritten in place.
    for name, raw in original_bytes.items():
        if "/raw/" in name and "game_period_stats/" not in name:
            require((output / name).read_bytes() == raw, "Accepted raw input changed")
    report = dict(
        classification="count_qualified_rate_incomplete_unpublished_copy",
        original_obligations=83,
        resolved_count_obligations=80,
        remaining_unadmitted_count_obligations=3,
        independent_event_supported_counts=83,
        resolutions=resolutions,
        by_statistic=dict(Counter(r["field"] for r in obligations)),
        vectors=vectors,
        proofs=proofs,
        count_changes=changes,
        explicit_rate_invalidations=invalidations,
        derived_count_ratio_changes=derived_changes,
        rate_fields=list(RATE_FIELDS),
        dataset_assessment=assessment,
        due_population=fresh,
        prior_schedule_due_population=due,
        original_period_bytes_preserved_in_archive=STAGE_SHA,
        full_numerical_acceptance=False,
        production_ready=False,
        production_writes=0,
        missing_0142_windows=[[3, 3], [3, 4]],
        general_possession_usage_accepted=False,
        precision_0160_still_unknown=False,
        timing_addendum=fresh["timing_0160"],
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    qualify(args.output)
