"""Versioned current-season staging from qualified retained originals only.

Preserves accepted game cells and originals, adds new observed games, and keeps
all source/coverage disagreements explicit. Never publishes or writes R2.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pandas as pd

from tools.period_event_evidence import clock_facts, period_facts, require, usage_event_evidence
from tools.qualify_readiness_partial import PARTIAL
from tools.qualify_readiness_recovery import RECOVERY, checked_archive, recovery_context
from tools.qualify_rollover_q1 import EVIDENCE, _local_stage

CURRENT = EVIDENCE / "current-refresh-20261104"
BUNDLE_SHA = "0dfd1bb7dcd9cff467fb110cf888c006266f00c7f02073fa6956e4a0c965ae13"
CATALOG_SHA = "e03bc219cf7545e6926d004e0d6806726da0066a6e41f08a97dfbc182c462812"
PRIOR_STAGE_SHA = "535f20e988b6a7217c8e302e38c87f16e85d77afefdaddc5459010f047049c95"
SUFFIX = "2026-27_regular_season.csv"


def originals():
    bundle = CURRENT / "current-sources.zip"
    require(
        hashlib.sha256(bundle.read_bytes()).hexdigest() == BUNDLE_SHA,
        "Current source bundle differs",
    )
    with zipfile.ZipFile(bundle) as z:
        require(z.testzip() is None, "Current source CRC failure")
        manifest = json.loads(z.read("sources.json"))
        bodies = {}
        for item in manifest["files"]:
            raw = z.read(item["file"])
            require(
                len(raw) == item["bytes"] == item["size"]
                and hashlib.sha256(raw).hexdigest() == item["sha256"]
                and hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == item["sha"],
                "Current archive source binding differs",
            )
            require(
                item["url"] == "https://raw.githubusercontent.com/sportsdataverse/"
                f"hoopR-nba-stats-raw/{manifest['revision']}/{item['path']}",
                "Unexpected source identity",
            )
            bodies[item["file"]] = raw
    return bodies, manifest


def _write(root, dataset, frame, layer="raw"):
    path = root / f"data/{layer}/{dataset}/{SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _append_rows(path, frame):
    columns = list(pd.read_csv(path, nrows=0).columns)
    require(set(columns) == set(frame.columns), "Append schema differs from preserved history")
    previous = path.read_bytes()
    require(previous.endswith(b"\n"), "Preserved CSV must have a complete final line")
    with path.open("ab") as handle:
        handle.write(frame[columns].to_csv(index=False, header=False).encode())
    require(path.read_bytes().startswith(previous), "Historical CSV bytes changed")


def _whole_original(gid):
    folder = EVIDENCE / "readiness-reassessment"
    manifest_raw = (folder / "sources.json").read_bytes()
    require(
        hashlib.sha256(manifest_raw).hexdigest()
        == "e5ece22f60bf71b0976c1447cf854a99c2e842b802f812b69cf1e964d1a2fc51",
        "Whole source manifest differs",
    )
    manifest = json.loads(manifest_raw)
    name = f"boxscoretraditionalv3_{gid}.json"
    item = manifest["files"][name]
    raw = (folder / "sources" / name).read_bytes()
    require(
        len(raw) == item["size_bytes"]
        and hashlib.sha256(raw).hexdigest() == item["sha256"]
        and hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == item["git_blob_sha"],
        "Whole role source binding differs",
    )
    return raw


def refine_period_clocks(raws, *, event_raw, whole_raw, start, end):
    """Refine an entire clock vector from exact PBP, not selected residual cells."""
    whole = json.loads(whole_raw)["boxScoreTraditional"]
    period_report = period_facts(
        event_raw,
        game_id=whole["gameId"],
        final_teams={
            whole[s]["teamId"]: whole[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
        },
    )
    clocks = clock_facts(event_raw, whole_raw, period_report=period_report)
    gid = period_report["game_id"]
    require(
        period_report["complete_timeline"] and start <= end <= 4,
        "Validated regulation clock evidence required",
    )
    roots = {
        "boxscoretraditionalv3": "boxScoreTraditional",
        "boxscoreadvancedv3": "boxScoreAdvanced",
    }
    docs = {k: json.loads(v) for k, v in raws.items()}
    copies = copy.deepcopy(docs)
    ledger = []
    from tools.season_rollover_core_bridge import _literal_clock_seconds

    for endpoint, key in roots.items():
        box = copies[endpoint][key]
        require(box["gameId"] == gid, "Clock target identity differs")
        for side in ["homeTeam", "awayTeam"]:
            team = box[side]
            tid = team["teamId"]
            times = {}
            for q in range(start, end + 1):
                for pid, seconds in clocks[q][tid].items():
                    times[pid] = times.get(pid, Fraction(0)) + seconds
            positive = {
                p["personId"]
                for p in team["players"]
                if _literal_clock_seconds(p["statistics"]["minutes"]) > 0
            }
            require(
                positive == {p for p, v in times.items() if v > 0},
                "PBP/direct positive clock identity sets differ",
            )
            for person in team["players"]:
                pid = person["personId"]
                seconds = times.get(pid, Fraction(0))
                before = person["statistics"]["minutes"]
                require(
                    abs(seconds - _literal_clock_seconds(before)) <= 1,
                    "Clock refinement exceeds source display precision",
                )
                centiseconds = seconds * 100
                require(centiseconds.denominator == 1, "Unsupported event clock precision")
                minutes, remainder = divmod(int(centiseconds), 6000)
                after = f"{minutes}:{remainder // 100:02d}.{remainder % 100:02d}"
                person["statistics"]["minutes"] = after
                ledger.append(
                    dict(
                        endpoint=endpoint,
                        team_id=tid,
                        player_id=pid,
                        original_literal=before,
                        derived_literal=after,
                        seconds=str(seconds),
                        event_sha256=period_report["source_sha256"],
                        role_identity_sha256=hashlib.sha256(whole_raw).hexdigest(),
                        original_sha256=hashlib.sha256(raws[endpoint]).hexdigest(),
                    )
                )
    for endpoint, key in roots.items():
        restored = copy.deepcopy(copies[endpoint])
        for row in ledger:
            if row["endpoint"] != endpoint:
                continue
            for side in ["homeTeam", "awayTeam"]:
                if restored[key][side]["teamId"] == row["team_id"]:
                    for p in restored[key][side]["players"]:
                        if p["personId"] == row["player_id"]:
                            p["statistics"]["minutes"] = row["original_literal"]
        require(restored == docs[endpoint], "Non-clock target cells changed")
    return {k: json.dumps(v, separators=(",", ":")).encode() for k, v in copies.items()}, ledger


def project_season_basis(core, reported):
    """Explicit derived fields; preserve every literal reported value beside them."""
    frame = reported.copy(deep=True)
    require(not core.duplicated(["game_id", "player_id"]).any(), "Duplicate core player-game grain")
    for column in ["pts", "fga", "fta"]:
        require(
            core[column].map(lambda v: math.isfinite(v) and v >= 0 and float(v).is_integer()).all(),
            "Invalid whole-game count input",
        )
    require(
        core.minutes.map(lambda v: math.isfinite(float(v)) and float(v) > 0).all(),
        "Invalid positive game-minute input",
    )
    require(not frame.player_id.duplicated().any(), "Duplicate Advanced identity")
    totals = core.groupby("player_id")[["pts", "fga", "fta"]].sum()
    counts = core.groupby("player_id").size()
    require(set(frame.player_id) == set(totals.index), "Advanced/core population differs")
    require(frame.set_index("player_id").games_played.eq(counts).all(), "Advanced/core GP differs")
    frame["reported_ts_pct"] = frame.ts_pct
    frame["reported_minutes_per_game"] = frame.minutes_per_game
    ledger = []
    for index, row in frame.iterrows():
        pid = row.player_id
        t = totals.loc[pid]
        denom = 2 * (Fraction(str(t.fga)) + Fraction(11, 25) * Fraction(str(t.fta)))
        ts = Fraction(str(t.pts)) / denom if denom else Fraction(0)
        rows = core.loc[core.player_id.eq(pid), "minutes"]
        mean = sum((Fraction(str(v)) for v in rows), Fraction(0)) / len(rows)
        frame.loc[index, "ts_pct"] = float(ts)
        frame.loc[index, "minutes_per_game"] = float(mean)
        ledger.append(
            dict(
                player_id=int(pid),
                games=len(rows),
                pts=int(t.pts),
                fga=int(t.fga),
                fta=int(t.fta),
                reported_ts=float(row.ts_pct),
                derived_ts=str(ts),
                reported_minutes=float(row.minutes_per_game),
                derived_minutes=str(mean),
            )
        )
    frame["ts_pct_basis"] = "same_scope_game_count_ratio"
    frame["minutes_per_game_basis"] = "same_scope_game_minute_mean"
    return frame, ledger


def repair_partial_context_margins(core, period_rows):
    """Reconcile the unaccepted partial154 context using two explicit count bases."""
    with checked_archive(
        PARTIAL / "current-sources.zip",
        "24d041dce0dc568802a4a2664dc2d40c1a4ed7ef4ddb96dc56c826d56587b3c4",
    ) as z:
        raw = z.read("boxscoretraditionalv3-0022600154.json")
    box = json.loads(raw)["boxScoreTraditional"]
    quarters = period_rows.loc[
        period_rows.game_id.eq(22600154) & period_rows.period_family.eq("quarter")
    ].copy()
    require(
        not quarters.duplicated(["team_id", "player_id", "period_value"]).any(),
        "Duplicate corroborating quarter grain",
    )
    observed = core.loc[core.game_id.eq(22600154)]
    changes = []
    for side, opposite in [("homeTeam", "awayTeam"), ("awayTeam", "homeTeam")]:
        team = box[side]
        tid = team["teamId"]
        from tools.season_rollover_core_bridge import _literal_clock_seconds

        source = {
            p["personId"]: p["statistics"]
            for p in team["players"]
            if _literal_clock_seconds(p["statistics"]["minutes"]) > 0
        }
        current = observed.loc[observed.team_id.eq(tid)].set_index("player_id")
        require(set(current.index) == set(source), "Margin source participant identity differs")
        require(
            sum(p["plusMinusPoints"] for p in source.values())
            == 5 * (team["statistics"]["points"] - box[opposite]["statistics"]["points"]),
            "Whole margin source does not reconcile to final score",
        )
        for pid, stats in source.items():
            rows = quarters.loc[quarters.team_id.eq(tid) & quarters.player_id.eq(pid)]
            require(
                len(rows) == 4 and set(rows.period_value.astype(str)) == {"1", "2", "3", "4"},
                "Four qualified quarters required for context margin reconciliation",
            )
            value = stats["plusMinusPoints"]
            require(
                math.isfinite(value)
                and float(value).is_integer()
                and rows.plus_minus.sum() == value,
                "Whole and disjoint-quarter margin sources disagree",
            )
            if current.loc[pid, "plus_minus"] != value:
                changes.append(
                    dict(
                        game_id="0022600154",
                        team_id=tid,
                        player_id=pid,
                        field="plus_minus",
                        before=int(current.loc[pid, "plus_minus"]),
                        after=int(value),
                        whole_source_sha256=hashlib.sha256(raw).hexdigest(),
                        corroboration="sum of all four previously admitted quarter margins",
                        prior_context_acceptance="partial_unaccepted154_primary_context",
                    )
                )
    result = core.copy(deep=True)
    for row in changes:
        result.loc[
            result.game_id.eq(22600154) & result.player_id.eq(row["player_id"]), "plus_minus"
        ] = row["after"]
    return result, changes


def period_count_coherence(core, catalog):
    """Compare retained disjoint original quarters/OT to staged whole-game counts.

    This deliberately includes quarantined originals: it reports source conflicts,
    never promotes an original or modifies accepted core cells.
    """
    from tools.season_rollover_core_bridge import FIELDS

    fields = {**FIELDS, "plusMinusPoints": "PLUS_MINUS"}
    archives = [
        (
            PARTIAL / "collection.zip",
            "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3",
        ),
        (
            RECOVERY / "collection.zip",
            "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17",
        ),
        (
            EVIDENCE / "q1-laptop-capture/collection.zip",
            "ab6618b4b0da9ddd3f262547832718544d74de7cf24d67f4b7901cb9081ef88d",
        ),
    ]
    jobs = {}
    for path, expected in archives:
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Period archive differs")
        with zipfile.ZipFile(path) as z:
            require(z.testzip() is None, "Period archive CRC failure")
            for name in z.namelist():
                if not name.startswith("sources/boxscoretraditionalv3_"):
                    continue
                tag = name.rsplit("_", 1)[-1].removesuffix(".json")
                if tag not in {"q1", "q2", "q3", "q4", "ot"}:
                    continue
                raw = z.read(name)
                box = json.loads(raw)["boxScoreTraditional"]
                key = (box["gameId"], tag)
                require(key not in jobs, "Duplicate original period request")
                jobs[key] = (box, hashlib.sha256(raw).hexdigest())
    require(not core.duplicated(["game_id", "team_id", "player_id"]).any(), "Duplicate core grain")
    indexed = core.set_index(["game_id", "team_id", "player_id"])
    conflicts, compared, unknown = [], [], []
    for gid, metadata in sorted(catalog.items()):
        periods = metadata["periods"]
        if periods is None:
            unknown.append(gid)
            continue
        tags = ["q1", "q2", "q3", "q4"] + (["ot"] if periods > 4 else [])
        if not all((gid, tag) in jobs for tag in tags):
            continue
        totals = defaultdict(lambda: defaultdict(int))
        hashes = {}
        for tag in tags:
            box, hashes[tag] = jobs[(gid, tag)]
            for side in ["homeTeam", "awayTeam"]:
                team = box[side]
                for person in team["players"]:
                    for field in fields:
                        value = person["statistics"][field]
                        require(
                            isinstance(value, (int, float))
                            and math.isfinite(value)
                            and float(value).is_integer(),
                            "Invalid period integer count",
                        )
                        totals[(team["teamId"], person["personId"])][field] += int(value)
        for (tid, pid), counts in totals.items():
            if (int(gid), tid, pid) not in indexed.index:
                require(not any(counts.values()), "Nonzero period identity absent from whole core")
                continue
            row = indexed.loc[(int(gid), tid, pid)]
            for field, column in fields.items():
                if counts[field] != row[column.lower()]:
                    conflicts.append(
                        dict(
                            game_id=gid,
                            team_id=tid,
                            player_id=pid,
                            field=column,
                            period_sum=counts[field],
                            staged_core=int(row[column.lower()]),
                            original_sha256=hashes,
                        )
                    )
        compared.append(gid)
    return dict(
        compared_games=len(compared),
        compared_game_ids=compared,
        integer_cell_conflicts=len(conflicts),
        conflict_game_ids=sorted({x["game_id"] for x in conflicts}),
        conflicts=conflicts,
        metadata_unknown=unknown,
        original_quarantines_still_apply=True,
        accepted_core_rewritten=False,
    )


def stage(output):
    from nba_api.stats.endpoints import BoxScoreTraditionalV3

    from nbatools.commands.pipeline import (
        pull_games,
        pull_player_game_stats,
        pull_player_season_advanced,
        pull_standings_snapshots,
        pull_team_game_stats,
        pull_team_season_advanced,
    )
    from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
    from nbatools.commands.pipeline.pull_player_game_starter_roles import (
        add_trust_validation,
        normalize_boxscore_player_roles,
    )
    from nbatools.commands.pipeline.structured_participation import _table
    from tools.assess_readiness_recovery import (
        due_population,
        snapshot_record_checks,
        source_basis_report,
    )
    from tools.season_rollover_core_bridge import (
        Source,
        _games,
        _traditional_teams,
        bridge_players,
        bridge_teams,
    )
    from tools.stage_rollover_periods import _endpoint, import_window

    output = output.resolve()
    require(not output.exists(), "Use a fresh isolated output")
    output.mkdir(parents=True)
    root = output / "stage"
    root.mkdir()
    bodies, manifest = originals()
    with checked_archive(RECOVERY / "qualification-evidence.zip", PRIOR_STAGE_SHA) as z:
        for name in z.namelist():
            if name.startswith("stage/data/") and name.endswith(".csv"):
                target = root / name.removeprefix("stage/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    with checked_archive(
        RECOVERY / "supplementary-sources.zip",
        "e2e5dff5ac60cdbb93371556490d5117d40012e452d47ea837092b8dccd53de1",
    ) as z:
        schedule = json.loads(z.read("schedule-current.json"))
    prior_players, prior_teams, _, prior_context = recovery_context(schedule)
    primary = _table(
        json.loads(bodies["playergamelogs-regular-season_base_totals.json"]), "PlayerGameLogs"
    )
    finder = _table(
        json.loads(bodies["leaguegamefinder-regular-season.json"]), "LeagueGameFinderResults"
    )
    games = _games(schedule, finder)
    valid = []
    quarantined = []
    for name, raw in bodies.items():
        if not name.startswith("boxscoretraditionalv3-"):
            continue
        source = Source(name, raw)
        try:
            list(_traditional_teams(source, games))
        except ValueError as exc:
            quarantined.append(dict(source_file=name, error=str(exc)))
        else:
            valid.append(source)
    corrected, p_ledger = bridge_players(primary, schedule, finder, traditional=valid)
    corrected_teams, t_ledger = bridge_teams(finder, schedule, traditional=valid)
    old_ids = set(prior_players.GAME_ID)
    players = pd.concat(
        [prior_players, corrected[~corrected.GAME_ID.isin(old_ids)]], ignore_index=True
    )
    teams = pd.concat(
        [prior_teams, corrected_teams[~corrected_teams.GAME_ID.isin(old_ids)]], ignore_index=True
    )
    before = {
        g: pd.read_csv(root / f"data/raw/{g}_game_stats/{SUFFIX}") for g in ["player", "team"]
    }
    protected = {
        g: (root / f"data/raw/{g}_game_stats/{SUFFIX}").read_bytes() for g in ["player", "team"]
    }
    protected_games = (root / f"data/raw/games/{SUFFIX}").read_bytes()
    old_game_ids = set(pd.read_csv(io.BytesIO(protected_games)).game_id)
    evidence = {}
    refinements = []
    with _local_stage(root):
        pull_games.run("2026-27", "Regular Season", raw_frame=teams)
        pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=players)
        pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=teams)
        contexts = {
            g: pd.read_csv(root / f"data/raw/{g}_game_stats/{SUFFIX}") for g in ["player", "team"]
        }
        for g in contexts:
            path = root / f"data/raw/{g}_game_stats/{SUFFIX}"
            new = contexts[g][~contexts[g].game_id.isin(before[g].game_id)].copy()
            path.write_bytes(protected[g])
            _append_rows(path, new)
            contexts[g] = pd.read_csv(path)
            old = contexts[g][contexts[g].game_id.isin(before[g].game_id)].reset_index(drop=True)
            pd.testing.assert_frame_equal(old, before[g], check_dtype=False, check_exact=True)
        game_path = root / f"data/raw/games/{SUFFIX}"
        new_games = pd.read_csv(game_path)
        new_games = new_games.loc[~new_games.game_id.isin(old_game_ids)]
        game_path.write_bytes(protected_games)
        _append_rows(game_path, new_games)
        period_rows = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
        repaired, context_repairs = repair_partial_context_margins(contexts["player"], period_rows)
        accepted_ids = {int(x) for x in prior_context["accepted_old_game_ids"]}
        accepted_count = int(before["player"].game_id.isin(accepted_ids).sum())
        require(
            set(before["player"].iloc[:accepted_count].game_id) == accepted_ids
            and not before["player"].iloc[accepted_count:].game_id.isin(accepted_ids).any(),
            "Historical accepted prefix layout changed",
        )
        lines = protected["player"].splitlines(keepends=True)
        require(len(lines) == len(before["player"]) + 1, "Unsupported historical multiline CSV")
        player_path = root / f"data/raw/player_game_stats/{SUFFIX}"
        player_path.write_bytes(b"".join(lines[: accepted_count + 1]))
        _append_rows(player_path, repaired.loc[~repaired.game_id.isin(accepted_ids)])
        contexts["player"] = pd.read_csv(player_path)
        pc = contexts["player"].merge(
            contexts["team"][["game_id", "team_id", "wl"]],
            on=["game_id", "team_id"],
            validate="many_to_one",
        )
        for gid in ["0022600097", "0022600111"]:
            whole = _whole_original(gid)
            box = json.loads(whole)["boxScoreTraditional"]
            raw = bodies[f"playbyplayv3-{gid}.json"]
            facts = period_facts(
                raw,
                game_id=gid,
                final_teams={
                    box[s]["teamId"]: box[s]["statistics"]["points"]
                    for s in ["homeTeam", "awayTeam"]
                },
            )
            evidence[gid] = facts
            if gid.endswith("0111"):
                continue
            with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
                for label, bounds in [("q4", (4, 4)), ("h2", (3, 4))]:
                    originals_ = {
                        ep: z.read(f"sources/{ep}_{gid}_{label}.json")
                        for ep in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
                    }
                    with zipfile.ZipFile(PARTIAL / "summary-oracles.zip") as oracle:
                        summary = json.loads(oracle.read(gid + ".json"))
                    window = next(
                        w for w in PERIOD_WINDOWS if (w.start_period, w.end_period) == bounds
                    )
                    try:
                        import_window(
                            originals_["boxscoretraditionalv3"],
                            originals_["boxscoreadvancedv3"],
                            game_id=gid,
                            window=window,
                            summary=summary,
                            player_context=pc,
                            team_context=contexts["team"],
                        )
                    except ValueError as exc:
                        require(
                            str(exc) == "Period player clock denominator differs",
                            "Unexpected original failure",
                        )
                    else:
                        raise ValueError("Do not alter an already qualified window")
                    derived, ledger = refine_period_clocks(
                        originals_, event_raw=raw, whole_raw=whole, start=bounds[0], end=bounds[1]
                    )
                    result = import_window(
                        derived["boxscoretraditionalv3"],
                        derived["boxscoreadvancedv3"],
                        game_id=gid,
                        window=window,
                        summary=summary,
                        player_context=pc,
                        team_context=contexts["team"],
                    )
                    for grain, frame in zip(["player", "team"], result, strict=True):
                        path = root / f"data/raw/{grain}_game_period_stats/{SUFFIX}"
                        old = pd.read_csv(path)
                        require(
                            not (
                                old.game_id.eq(int(gid))
                                & old.period_family.eq(window.period_family)
                                & old.period_value.astype(str)
                                .str.lower()
                                .eq(str(window.period_value).lower())
                            ).any(),
                            "Existing window replacement forbidden",
                        )
                        _append_rows(path, frame)
                    folder = output / "clock-evidence" / label
                    folder.mkdir(parents=True)
                    for ep, value in derived.items():
                        (folder / (ep + ".json")).write_bytes(value)
                    refinements.append(
                        dict(
                            game_id=gid,
                            window=label,
                            clock_observations=ledger,
                            player_rows=len(result[0]),
                            team_rows=len(result[1]),
                        )
                    )
        extra = []
        positive = contexts["player"][["game_id", "team_id", "player_id"]]
        for name, raw in bodies.items():
            if not name.startswith("boxscoretraditionalv3-"):
                continue
            gid = json.loads(raw)["boxScoreTraditional"]["gameId"]
            f = normalize_boxscore_player_roles(
                _endpoint(BoxScoreTraditionalV3, raw, gid).player_stats.get_data_frame()
            )
            for key in ["game_id", "team_id", "player_id"]:
                f[key] = pd.to_numeric(f[key])
            f = f.merge(positive, on=["game_id", "team_id", "player_id"], validate="one_to_one")
            f["season"] = "2026-27"
            f["season_type"] = "Regular Season"
            extra.append(add_trust_validation(f))
        _append_rows(
            root / f"data/raw/player_game_starter_roles/{SUFFIX}",
            pd.concat(extra, ignore_index=True),
        )
        asof = max(str(x)[:10] for x in finder.GAME_DATE)
        reported = pull_player_season_advanced.normalize(
            _table(
                json.loads(bodies["leaguedashplayerstats-regular-season_advanced_pergame.json"]),
                "LeagueDashPlayerStats",
            ),
            "2026-27",
            "Regular Season",
            asof,
        )
        _write(root, "player_season_advanced", reported)
        _write(
            root,
            "team_season_advanced",
            pull_team_season_advanced.normalize(
                _table(
                    json.loads(bodies["leaguedashteamstats-regular-season_advanced_pergame.json"]),
                    "LeagueDashTeamStats",
                ),
                "2026-27",
                "Regular Season",
                asof,
            ),
        )
        _write(
            root,
            "standings_snapshots",
            pull_standings_snapshots.normalize(
                _table(json.loads(bodies["leaguestandingsv3-regular-season.json"]), "Standings"),
                "2026-27",
                "Regular Season",
                asof,
            ),
        )
        reported_source_basis = source_basis_report(root)
        reported_record_checks = snapshot_record_checks(root)
        reported_record_checks["statistical_scope"] = f"observed{len(games)}game_population"
        source_records = _table(
            json.loads(bodies["leaguedashplayerstats-regular-season_advanced_pergame.json"]),
            "LeagueDashPlayerStats",
        ).set_index("PLAYER_ID")
        expected_records = (
            pc.assign(W=pc.wl.eq("W").astype(int), L=pc.wl.eq("L").astype(int))
            .groupby("player_id")[["W", "L"]]
            .sum()
        )
        record_conflicts = []
        for pid, row in expected_records.iterrows():
            for field in ["W", "L"]:
                if row[field] != source_records.loc[pid, field]:
                    record_conflicts.append(
                        dict(
                            player_id=int(pid),
                            field=field,
                            expected=int(row[field]),
                            source=int(source_records.loc[pid, field]),
                        )
                    )
        reported_record_checks["player_win_loss_conflicts"] = record_conflicts
        reported_record_checks["player_win_loss_compared"] = len(expected_records)
        # Preserve the decimal CSV tokens for this derivation; a normal float
        # parser can round again before Fraction ever sees the original token.
        literal_core = pd.read_csv(
            root / f"data/raw/player_game_stats/{SUFFIX}", dtype={"minutes": str}
        )
        projected, projection_ledger = project_season_basis(literal_core, reported)
        _write(root, "player_season_advanced", projected)
        with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
            usage_traditional = z.read("sources/boxscoretraditionalv3_0022600116_q1.json")
        with zipfile.ZipFile(RECOVERY / "collection.zip") as z:
            usage_advanced = z.read("sources/boxscoreadvancedv3_0022600116_q1.json")
        usage_evidence = usage_event_evidence(
            bodies["playbyplayv3-0022600116.json"],
            _whole_original("0022600116"),
            usage_traditional,
            usage_advanced,
        )
        from nbatools.commands.pipeline import (
            build_game_features,
            build_league_season_stats,
            build_player_game_features,
            build_schedule_context_features,
            build_team_game_features,
            validate_raw,
        )

        stages = []
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
        from nbatools.commands.validation_control import DATASET_SPECS, build_slice_manifest

        receipt = build_slice_manifest(
            "2026-27",
            "Regular Season",
            data_root=root / "data",
            generation_id="unpublished-current-season-source-stage",
        )
        specs = [s for s in DATASET_SPECS if s.required and s.applies("Regular Season")]
        require(
            sum(s.layer == "raw" for s in specs) == 11
            and sum(s.layer == "processed" for s in specs) == 5,
            "Required dataset denominator changed",
        )
        from nbatools.commands.player_game_finder import build_result

        answer = build_result(
            player="Anthony Davis",
            season="2026-27",
            quarter="4",
            start_date="2026-10-23",
            end_date="2026-10-23",
        )
        require(answer.result_status == "ok", "Recovered clock-window consumer failed")
        fresh = contexts["player"].loc[contexts["player"].game_id.eq(22600158)].iloc[0]
        fresh_date = str(fresh.game_date)[:10]
        new_answer = build_result(
            player=fresh.player_name, season="2026-27", start_date=fresh_date, end_date=fresh_date
        )
        require(
            new_answer.result_status == "ok"
            and new_answer.games.loc[new_answer.games.game_id.eq(22600158), "pts"].tolist()
            == [fresh.pts],
            "New-game statistical consumer failed",
        )
    catalog_raw = (CURRENT / "summary-catalog.json").read_bytes()
    require(
        hashlib.sha256(catalog_raw).hexdigest() == CATALOG_SHA, "Summary catalog binding differs"
    )
    catalog = json.loads(catalog_raw)
    count_coherence = period_count_coherence(contexts["player"], catalog)
    known_ot = sorted(g for g, c in catalog.items() if c["periods"] and c["periods"] > 4)
    unknown = sorted(gid for gid in games if gid not in catalog or catalog[gid]["periods"] is None)
    expected = {
        (int(gid), family, value)
        for gid in games
        for family, value in [
            ("quarter", "1"),
            ("quarter", "2"),
            ("quarter", "3"),
            ("quarter", "4"),
            ("half", "first"),
            ("half", "second"),
        ]
    }
    expected.update((int(gid), "overtime", "ot") for gid in known_ot)
    observed = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    seen = {
        (int(row.game_id), row.period_family, str(row.period_value).lower())
        for row in observed.itertuples()
    }
    population = dict(
        known_expected_windows=len(expected),
        qualified_windows=len(seen),
        missing_known_windows=sorted(expected - seen),
        metadata_unresolved_game_ids=unknown,
        known_overtime_game_ids=known_ot,
        game0111_canonical_period_count=4,
        reported_0111_header_preserved=5,
        whole_period_universe_accepted=False,
    )
    report = dict(
        classification="qualified_current_staging_not_production_readiness",
        source_manifest=manifest,
        game_count=len(games),
        player_rows=len(players),
        team_rows=len(teams),
        prior88_core_cells_preserved=True,
        prior92_core_cells_preserved=not context_repairs,
        partial_context_margin_repairs=context_repairs,
        period_count_coherence=count_coherence,
        new_game_ids=sorted(set(primary.GAME_ID) - old_ids),
        new_source_clock_quarantines=quarantined,
        new_cell_changes=[x for x in [*p_ledger, *t_ledger] if x["before"] != x["after"]],
        period_evidence=evidence,
        refined_period_clocks=refinements,
        reported_source_basis=reported_source_basis,
        reported_record_checks=reported_record_checks,
        independent_usage_evidence=usage_evidence,
        advanced_derived_field_ledger=projection_ledger,
        required_raw=11,
        required_processed=5,
        dataset_assessment=receipt,
        executed_stages=stages,
        exact_due_population=due_population(root, datetime.now(UTC)),
        consumer_status=answer.result_status,
        consumer_rows=answer.games.to_dict("records") if answer.result_status == "ok" else [],
        new_game_consumer_rows=new_answer.games.to_dict("records"),
        source_period_population=population,
        reported_usage_independently_accepted=False,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    (output / "assessment.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    r = stage(parser.parse_args().output)
    print(
        {
            k: r[k]
            for k in [
                "game_count",
                "player_rows",
                "team_rows",
                "prior88_core_cells_preserved",
                "full_snapshot_accepted",
            ]
        }
    )
