"""Offline qualification of the first reusable refresh; never publication.

Reuses PR575's immutable stage and all authenticated direct captures. Existing
period cells are append-only. Alternate ranges remain diagnostic observations.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tools.qualify_readiness_recovery import checked_archive
from tools.qualify_rollover_q1 import _local_stage
from tools.readiness_refresh import SourceCache, period_count
from tools.stage_current_season import CURRENT, SUFFIX, _append_rows
from tools.stage_rollover_periods import import_window

CLOCK_SHA = "719eff651a2dbf6303f3a3e8fb2c1a0d65094561d28089f66fdd5824d4ff2bea"
OUTER_SHA = "8db6864968d2f6060959310517d6ef0d4838ded54b6100873ec8a8163264afc8"
SEED_SHA = "105a4e1536693d010cce534c45fdd5300632b0c1b499c1647a3f2ee07c7e79a0"
PRIOR_SHA = "1b5da5808bf9f8b6cd90d485436ecfe4a4dc057c83657592391a208f2a3b2aed"

SUMMARY_ARCHIVES = {
    "summary-oracles.zip": "487b42ca27753f778be4be677021bd350dbd212b0837167abe9f7768c81c9d71",
    "supplementary-sources.zip": "e2e5dff5ac60cdbb93371556490d5117d40012e452d47ea837092b8dccd53de1",
    "current-sources.zip": "0dfd1bb7dcd9cff467fb110cf888c006266f00c7f02073fa6956e4a0c965ae13",
    "archive-refresh.zip": "a0acf7bdc469fbef887b2ed1c12bc80e68e8bb8057fe9ffed08cf1cec53ce3a1",
}


@contextmanager
def bound_zip(path, digest):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Retained Summary archive differs")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError("Retained Summary archive CRC differs")
        yield z


def event_clock_copy(pair, event_raw, whole_raw, *, start, end):
    """Explicit copied full-vector refinement; original malformed tokens survive.

    Only the diagnosed display rollover ':60' is interpreted for a <=1 second
    proximity check. Exact replacement clocks come solely from validated events.
    The unchanged importer still rejects each malformed original.
    """
    import copy
    import re
    from fractions import Fraction

    from tools.period_event_evidence import clock_facts, period_facts
    from tools.season_rollover_core_bridge import _literal_clock_seconds

    whole = json.loads(whole_raw)["boxScoreTraditional"]
    facts = period_facts(
        event_raw,
        game_id=whole["gameId"],
        final_teams={
            whole[side]["teamId"]: whole[side]["statistics"]["points"]
            for side in ["homeTeam", "awayTeam"]
        },
    )
    clocks = clock_facts(event_raw, whole_raw, period_report=facts)
    ledger, result = [], {}
    for ep, raw in pair.items():
        doc = json.loads(raw)
        candidate = copy.deepcopy(doc)
        boxkey = "boxScoreTraditional" if ep == "boxscoretraditionalv3" else "boxScoreAdvanced"
        for side in ["homeTeam", "awayTeam"]:
            team = candidate[boxkey][side]
            times = {}
            for q in range(start, end + 1):
                for pid, seconds in clocks[q][team["teamId"]].items():
                    times[pid] = times.get(pid, Fraction(0)) + seconds
            for player in team["players"]:
                before = player["statistics"]["minutes"]
                try:
                    displayed = _literal_clock_seconds(before)
                except ValueError:
                    if not isinstance(before, str) or not re.fullmatch(r"\d+:60", before):
                        raise
                    displayed = Fraction(int(before.split(":")[0]) * 60 + 60)
                seconds = times.get(player["personId"], Fraction(0))
                if abs(seconds - displayed) > 1 or (seconds * 100).denominator != 1:
                    raise ValueError("Independent full-vector clock exceeds display precision")
                centis = int(seconds * 100)
                after = f"{centis // 6000}:{centis % 6000 // 100:02d}.{centis % 100:02d}"
                player["statistics"]["minutes"] = after
                ledger.append(
                    dict(
                        endpoint=ep,
                        team_id=team["teamId"],
                        player_id=player["personId"],
                        original_literal=before,
                        derived_literal=after,
                        exact_seconds=str(seconds),
                        source_sha256=hashlib.sha256(raw).hexdigest(),
                        event_sha256=hashlib.sha256(event_raw).hexdigest(),
                        whole_identity_sha256=hashlib.sha256(whole_raw).hexdigest(),
                    )
                )
        restored = copy.deepcopy(candidate)
        for side in ["homeTeam", "awayTeam"]:
            for old, changed in zip(
                doc[boxkey][side]["players"], restored[boxkey][side]["players"], strict=True
            ):
                changed["statistics"]["minutes"] = old["statistics"]["minutes"]
        if restored != doc:
            raise ValueError("Non-clock source mutation")
        result[ep] = json.dumps(candidate, separators=(",", ":")).encode()
    return result, ledger


def qualify(archive: Path, cache_path: Path, output: Path):
    from nbatools.commands.pipeline import (
        build_game_features,
        build_league_season_stats,
        build_player_game_features,
        build_schedule_context_features,
        build_team_game_features,
        pull_player_season_advanced,
        pull_team_season_advanced,
        validate_raw,
    )
    from nbatools.commands.pipeline import pull_game_period_stats as periods
    from nbatools.commands.pipeline.structured_participation import _table
    from nbatools.commands.validation_control import DATASET_SPECS, build_slice_manifest
    from tools.assess_readiness_recovery import (
        due_population,
        snapshot_record_checks,
        source_basis_report,
    )

    archive, output = archive.resolve(), output.resolve()
    cache = SourceCache(cache_path)
    imported = cache.import_run(archive, OUTER_SHA, SEED_SHA)
    output.mkdir(parents=True, exist_ok=False)
    root = output / "stage"
    prior = {}
    with checked_archive(CURRENT / "qualification-evidence.zip", PRIOR_SHA) as z:
        for name in z.namelist():
            if name.startswith("stage/data/") and name.endswith(".csv"):
                raw = z.read(name)
                target = output / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                prior[name.removeprefix("stage/")] = hashlib.sha256(raw).hexdigest()
    summaries = {}
    for path in [
        CURRENT.parent / "partial-capture-20261103/summary-oracles.zip",
        CURRENT.parent / "recovery-capture-20261104/supplementary-sources.zip",
        CURRENT / "current-sources.zip",
    ]:
        with bound_zip(path, SUMMARY_ARCHIVES[path.name]) as z:
            for name in z.namelist():
                if name.endswith(".json"):
                    doc = json.loads(z.read(name))
                    if "boxScoreSummary" in doc:
                        summaries[doc["boxScoreSummary"]["gameId"]] = doc
    from tools.season_rollover_core_bridge import _additional_sources

    summaries["0022600144"] = _additional_sources(CURRENT.parent)["summary.json"].document
    with bound_zip(
        CURRENT.parent / "period-milestone/archive-refresh.zip",
        SUMMARY_ARCHIVES["archive-refresh.zip"],
    ) as z:
        for gid in [f"0022600{n}" for n in range(147, 154)]:
            summaries[gid] = json.loads(z.read(f"boxscoresummaryv3_{gid}.json"))
    for record in cache.data["direct"].values():
        if record["job"]["endpoint"] == "boxscoresummaryv3":
            doc = json.loads(cache.read(record))
            summaries[doc["boxScoreSummary"]["gameId"]] = doc
    # PR575's independently established four-period interpretation remains pinned.
    catalog_raw = (CURRENT / "summary-catalog.json").read_bytes()
    assert (
        hashlib.sha256(catalog_raw).hexdigest()
        == "e03bc219cf7545e6926d004e0d6806726da0066a6e41f08a97dfbc182c462812"
    )
    catalog = json.loads(catalog_raw)
    counts = {g: item["periods"] for g, item in catalog.items()}
    summary161 = summaries["0022600161"]
    counts["0022600161"] = period_count(summary161, "0022600161")
    players = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
    teams = pd.read_csv(root / f"data/raw/team_game_stats/{SUFFIX}")
    pc = players.merge(
        teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"], validate="many_to_one"
    )
    old_period = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    seen = {
        (int(r.game_id), r.period_family, str(r.period_value).lower())
        for r in old_period.itertuples()
    }
    initial_seen = set(seen)
    groups = {}
    alternate = []
    for record in cache.data["direct"].values():
        job = record["job"]
        params = job["parameters"]
        if job["endpoint"] not in {"boxscoretraditionalv3", "boxscoreadvancedv3"}:
            continue
        if params.get("RangeType") == 2:
            alternate.append(record)
            continue
        if int(params.get("StartPeriod", 0)) == 0:
            continue
        key = (
            str(params["GameID"]).zfill(10),
            int(params["StartPeriod"]),
            int(params["EndPeriod"]),
        )
        groups.setdefault(key, {})[job["endpoint"]] = record
    clock_path = CURRENT.parent / "incremental-return-20261104/clock-source-originals.zip"
    with bound_zip(clock_path, CLOCK_SHA) as z:
        event_bodies = {n: z.read(n) for n in z.namelist() if n != "sources.json"}
    with bound_zip(CURRENT / "current-sources.zip", SUMMARY_ARCHIVES["current-sources.zip"]) as z:
        whole_bodies = {
            n: z.read(n) for n in z.namelist() if n.startswith("boxscoretraditionalv3-")
        }
    refinements = []
    admitted, rejected = [], []
    for (gid, start, end), pair in sorted(groups.items()):
        window = next(
            (w for w in periods.PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end)),
            None,
        )
        if window is None:
            continue
        key = (int(gid), window.period_family, str(window.period_value).lower())
        if key in seen:
            continue
        hashes = {ep: r["sha256"] for ep, r in pair.items()}
        try:
            if len(pair) != 2:
                raise ValueError("Missing endpoint pair")
            frames = import_window(
                cache.read(pair["boxscoretraditionalv3"]),
                cache.read(pair["boxscoreadvancedv3"]),
                game_id=gid,
                window=window,
                summary=summaries[gid],
                player_context=pc,
                team_context=teams,
            )
        except (ValueError, KeyError) as exc:
            original_error = str(exc)
            if original_error != "Invalid Traditional box-score duration" or gid not in {
                "0022600158",
                "0022600163",
                "0022600168",
            }:
                rejected.append(
                    dict(game_id=gid, window=key[1:], error=original_error, sources=hashes)
                )
                continue
            copied, ledger = event_clock_copy(
                {ep: cache.read(r) for ep, r in pair.items()},
                event_bodies[gid + ".json"],
                whole_bodies[f"boxscoretraditionalv3-{gid}.json"],
                start=start,
                end=end,
            )
            frames = import_window(
                copied["boxscoretraditionalv3"],
                copied["boxscoreadvancedv3"],
                game_id=gid,
                window=window,
                summary=summaries[gid],
                player_context=pc,
                team_context=teams,
            )
            refinements.append(
                dict(game_id=gid, window=key[1:], original_error=original_error, ledger=ledger)
            )
            folder = output / "clock-copies" / (gid + "-" + str(start) + "-" + str(end))
            folder.mkdir(parents=True)
            for ep, raw in copied.items():
                (folder / (ep + ".json")).write_bytes(raw)
        if frames is not None:
            for grain, frame in zip(["player", "team"], frames, strict=True):
                _append_rows(root / f"data/raw/{grain}_game_period_stats/{SUFFIX}", frame)
            seen.add(key)
            admitted.append(
                dict(game_id=gid, window=key[1:], sources=hashes, player_rows=len(frames[0]))
            )
    # Test every diagnostic pair through identical source gates, without replacing
    # any prior accepted window or treating gate success as cross-period coherence.
    alternate_groups = {}
    for r in alternate:
        j = r["job"]
        p = j["parameters"]
        alternate_groups.setdefault((p["GameID"], p["StartPeriod"], p["EndPeriod"]), {})[
            j["endpoint"]
        ] = r
    diagnostics = []
    for (gid, start, end), pair in sorted(alternate_groups.items()):
        window = next(
            w for w in periods.PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end)
        )
        try:
            import_window(
                cache.read(pair["boxscoretraditionalv3"]),
                cache.read(pair["boxscoreadvancedv3"]),
                game_id=gid,
                window=window,
                summary=summaries[gid],
                player_context=pc,
                team_context=teams,
            )
        except ValueError as exc:
            state, error = "rejected", str(exc)
        else:
            state, error = "local_gates_pass_not_admitted", None
        diagnostics.append(
            dict(
                game_id=gid,
                window=[start, end],
                state=state,
                error=error,
                sources={ep: r["sha256"] for ep, r in pair.items()},
            )
        )
    expected = {
        (int(g), w.period_family, str(w.period_value).lower())
        for g in counts
        for w in periods.PERIOD_WINDOWS
        if w.start_period <= counts[g]
    }
    assert initial_seen.issubset(seen)
    snapshot_observations = {}
    stages = []
    with _local_stage(root):
        # Select new snapshots by imported request identity, never by filename date.
        with zipfile.ZipFile(archive) as z:
            nested = next(n for n in z.namelist() if n.endswith("/collection.zip"))
            with zipfile.ZipFile(io.BytesIO(z.read(nested))) as nz:
                acquisition = json.loads(nz.read("acquisition.json"))
                for a in acquisition["attempts"]:
                    ep = a["job"]["endpoint"]
                    if ep not in {"leaguedashplayerstats", "leaguedashteamstats"}:
                        continue
                    raw = nz.read(a["job"]["source_file"])
                    table, normalizer, grain = (
                        ("LeagueDashPlayerStats", pull_player_season_advanced, "player")
                        if ep == "leaguedashplayerstats"
                        else ("LeagueDashTeamStats", pull_team_season_advanced, "team")
                    )
                    frame = normalizer.normalize(
                        _table(json.loads(raw), table),
                        "2026-27",
                        "Regular Season",
                        datetime.strptime(a["job"]["parameters"]["DateTo"], "%m/%d/%Y")
                        .date()
                        .isoformat(),
                    )
                    snapshot_observations[grain] = dict(
                        source_sha256=hashlib.sha256(raw).hexdigest(),
                        parameters=a["job"]["parameters"],
                        rows=len(frame),
                    )
                    frame.to_csv(root / f"data/raw/{grain}_season_advanced/{SUFFIX}", index=False)
        basis = source_basis_report(root)
        records = snapshot_record_checks(root)
        # These fresh snapshots are observations, not accepted replacements.
        # Retain every original stage value; compare and ledger all proposed cells.
        snapshot_deltas = []
        with zipfile.ZipFile(CURRENT / "qualification-evidence.zip") as z:
            for grain, identity in [("player", "player_id"), ("team", "team_id")]:
                path = root / f"data/raw/{grain}_season_advanced/{SUFFIX}"
                fresh_raw = path.read_bytes()
                (output / f"reported-{grain}-advanced.csv").write_bytes(fresh_raw)
                prior_raw = z.read(f"stage/data/raw/{grain}_season_advanced/{SUFFIX}")
                old = pd.read_csv(io.BytesIO(prior_raw)).set_index(identity)
                fresh = pd.read_csv(io.BytesIO(fresh_raw)).set_index(identity)
                for ident in fresh.index:
                    for field in old.columns.intersection(fresh.columns):
                        before, after = old.loc[ident, field], fresh.loc[ident, field]
                        if pd.isna(before) and pd.isna(after):
                            continue
                        if before != after:
                            snapshot_deltas.append(
                                dict(
                                    grain=grain,
                                    identity=int(ident),
                                    field=field,
                                    accepted_stage_value=before,
                                    new_reported_observation=after,
                                    source_sha256=snapshot_observations[grain]["source_sha256"],
                                    replacement_accepted=False,
                                )
                            )
                path.write_bytes(prior_raw)
        (output / "snapshot-deltas.json").write_text(
            json.dumps(snapshot_deltas, indent=2, default=str) + "\n"
        )
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
            generation_id="unpublished-incremental-return-20261104",
        )
        due = due_population(root, datetime.now(UTC))
    specs = [s for s in DATASET_SPECS if s.required and s.applies("Regular Season")]
    assert (
        sum(s.layer == "raw" for s in specs) == 11
        and sum(s.layer == "processed" for s in specs) == 5
    )
    preserved = {}
    for name, digest in prior.items():
        raw = (root / name).read_bytes()
        if "game_period_stats/" in name:
            with zipfile.ZipFile(CURRENT / "qualification-evidence.zip") as z:
                assert raw.startswith(z.read("stage/" + name))
        elif "/raw/" in name:
            assert hashlib.sha256(raw).hexdigest() == digest
            preserved[name] = digest
    report = dict(
        classification="offline_qualification_not_full_acceptance",
        outer_sha256=OUTER_SHA,
        retained_direct_successes=len(cache.data["direct"]),
        import_classification=imported["classification"],
        admitted=admitted,
        event_clock_refinements=refinements,
        rejected=rejected,
        alternate_range_diagnostics=diagnostics,
        summary161=summary161,
        period_counts=counts,
        known_expected_windows=len(expected),
        admitted_windows=len(seen),
        missing_windows=sorted(expected - seen),
        prior_raw_unchanged=preserved,
        prior_period_literal_prefixes_preserved=True,
        new_snapshot_observations=snapshot_observations,
        source_basis=basis,
        new_snapshot_cells_promoted=False,
        snapshot_deltas=snapshot_deltas,
        snapshot_records=records,
        executed_stages=stages,
        dataset_assessment=assessment,
        due_population=due,
        required_raw=11,
        required_processed=5,
        reported_usage_independently_accepted=False,
        full_snapshot_accepted=False,
        production_writes=0,
    )
    (output / "assessment.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(
        json.dumps(
            dict(
                admitted=len(admitted),
                rejected=Counter(r["error"] for r in rejected),
                expected=len(expected),
                observed=len(seen),
                missing=len(expected - seen),
                diagnostic=Counter(r["error"] or r["state"] for r in diagnostics),
            ),
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    qualify(args.archive, args.cache, args.output)
