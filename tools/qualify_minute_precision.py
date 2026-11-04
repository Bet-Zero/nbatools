"""Qualify remaining Advanced minute boundaries from immutable exact event vectors.

Source clocks, raw game-log literals, canonical CSV tokens and reported snapshot
values remain untouched. Every game must provide a unique complete event replay;
missing or contradictory timing cannot become an accepted season mean.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from fractions import Fraction
from pathlib import Path

from tools.period_event_evidence import (
    clock_facts,
    period_facts,
    require,
    same_clock_score_evidence,
)
from tools.qualify_advanced_basis import COLLECTION_SHA, RETURNED, SOURCE_SHA, STAGE_SHA
from tools.qualify_incremental_return import CLOCK_SHA, SUMMARY_ARCHIVES, bound_zip
from tools.stage_current_season import CURRENT, SUFFIX, _whole_original

BOUNDARY_PLAYERS = (201144, 203081, 1629162, 1630192, 1630695, 1642854)
NEW_GAME_IDS = (
    "0022600092",
    "0022600094",
    "0022600103",
    "0022600109",
    "0022600121",
    "0022600125",
    "0022600127",
    "0022600130",
    "0022600131",
    "0022600146",
    "0022600147",
    "0022600149",
    "0022600160",
    "0022600167",
    "0022600169",
)


def _literal_table(raw, name):
    doc = json.loads(raw, parse_float=str)
    records = [r for r in doc["resultSets"] if r["name"] == name]
    require(len(records) == 1, "Minute source table identity differs")
    table = records[0]
    require(len(table["headers"]) == len(set(table["headers"])), "Duplicate source columns")
    return [dict(zip(table["headers"], row, strict=True)) for row in table["rowSet"]]


def authenticate_sources(archive, digest):
    """Bind originals, immutable approved URLs, sizes, SHA256 and Git object IDs."""
    sources, manifest = {}, None
    with bound_zip(Path(archive), digest) as z:
        manifest_raw = z.read("sources.json")
        document = json.loads(manifest_raw)
        require(
            isinstance(document, dict)
            and document.get("production_writes") == 0
            and set(document["required_game_ids"]) == set(NEW_GAME_IDS),
            "Precision source request scope differs",
        )
        records = document["files"]
        missing = set(document["missing_archive_game_ids"])
        directory_raw = z.read("directory-metadata.json")
        directory = json.loads(directory_raw)
        require(isinstance(directory, list), "Archive directory metadata differs")
        by_name = {item["name"]: item for item in directory}
        require(
            len(by_name) == len(directory) and all(g + ".json" not in by_name for g in missing),
            "Missing precision sources disagree with directory originals",
        )
        names = {"sources.json", "directory-metadata.json"}
        for row in records:
            name = row["file"]
            gid = Path(name).stem.removeprefix("playbyplayv3-").removeprefix("playbyplayv3_")
            require(
                gid in NEW_GAME_IDS and gid not in sources and name not in names,
                "Unexpected or duplicate precision source identity",
            )
            revision = document["revision"]
            expected_path = f"nba_stats/json/playbyplayv3/2027/{gid}.json"
            expected_url = (
                "https://raw.githubusercontent.com/sportsdataverse/"
                f"hoopR-nba-stats-raw/{revision}/{expected_path}"
            )
            require(
                len(revision) == 40
                and all(c in "0123456789abcdef" for c in revision)
                and row["path"] == expected_path
                and row["url"] == expected_url,
                "Unexpected precision source immutable provenance",
            )
            raw = z.read(name)
            size = row.get("bytes", row.get("size_bytes", row.get("size")))
            require(
                len(raw) == size and hashlib.sha256(raw).hexdigest() == row["sha256"],
                "Precision source byte binding differs",
            )
            blob = row["git_blob"]
            require(
                by_name[name]["sha"] == blob and by_name[name]["size"] == size,
                "Directory source identity differs",
            )
            require(
                hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == blob,
                "Precision source Git identity differs",
            )
            require(json.loads(raw)["game"]["gameId"] == gid, "Precision source game differs")
            sources[gid] = dict(raw=raw, provenance=row)
            names.add(name)
        require(
            set(z.namelist()) == names
            and not (set(sources) & missing)
            and set(sources) | missing == set(NEW_GAME_IDS),
            "Precision archive differs from reviewed request and exact missing originals",
        )
        manifest = dict(
            sha256=hashlib.sha256(manifest_raw).hexdigest(),
            files=records,
            revision=document["revision"],
            missing_game_ids=sorted(missing),
            directory_sha256=hashlib.sha256(directory_raw).hexdigest(),
        )
        for gid in missing:
            sources[gid] = dict(
                raw=None,
                provenance=dict(
                    state="absent_at_immutable_archive_revision",
                    revision=document["revision"],
                    directory_sha256=manifest["directory_sha256"],
                ),
            )
    return sources, manifest


def _whole(gid, current_bodies):
    """Reuse all required whole identities; no new collection or clock repair."""
    current = current_bodies.get(f"boxscoretraditionalv3-{gid}.json")
    if current is not None:
        return current
    if gid in {"0022600147", "0022600149"}:
        with bound_zip(
            CURRENT.parent / "period-milestone/archive-refresh.zip",
            SUMMARY_ARCHIVES["archive-refresh.zip"],
        ) as z:
            return z.read(f"boxscoretraditionalv3_{gid}.json")
    return _whole_original(gid)


def exact_game_clock(raw, whole_raw):
    """Reject score, timeline, substitution and event-actor contradictions intact."""
    box = json.loads(whole_raw)["boxScoreTraditional"]
    final = {
        box[side]["teamId"]: box[side]["statistics"]["points"] for side in ["homeTeam", "awayTeam"]
    }
    strict_failure = None
    try:
        facts = period_facts(raw, game_id=box["gameId"], final_teams=final)
    except ValueError as exc:
        if str(exc) != "Unexplained event score change":
            raise
        strict_failure = str(exc)
        proof = same_clock_score_evidence(raw, game_id=box["gameId"], final_teams=final)
        facts = period_facts(raw, game_id=box["gameId"], final_teams=final, score_snapshots=proof)
    clocks = clock_facts(raw, whole_raw, period_report=facts)
    return facts, clocks, strict_failure


def qualify(archive, digest, output):
    sources, manifest = authenticate_sources(archive, digest)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        current_bodies = {name: z.read(name) for name in z.namelist()}
        primary_raw = z.read("playergamelogs-regular-season_base_totals.json")
    with bound_zip(RETURNED / "clock-source-originals.zip", CLOCK_SHA) as z:
        raw = z.read("0022600168.json")
        sources["0022600168"] = dict(
            raw=raw,
            provenance=dict(
                archive="incremental-return-20261104/clock-source-originals.zip",
                file="0022600168.json",
                sha256=hashlib.sha256(raw).hexdigest(),
                already_retained=True,
            ),
        )
    with bound_zip(RETURNED / "collection.zip", COLLECTION_SHA) as z:
        snapshot_raw = z.read("sources/leaguedashplayerstats_advanced_through_20261102.json")
    primary = _literal_table(primary_raw, "PlayerGameLogs")
    snapshot = {r["PLAYER_ID"]: r for r in _literal_table(snapshot_raw, "LeagueDashPlayerStats")}
    with bound_zip(RETURNED / "qualification-evidence.zip", STAGE_SHA) as z:
        canonical_raw = z.read(f"stage/data/raw/player_game_stats/{SUFFIX}")
    canonical = list(csv.DictReader(io.StringIO(canonical_raw.decode())))
    game_results = {}
    for gid, source in sorted(sources.items()):
        if source["raw"] is None:
            game_results[gid] = dict(
                state="missing_immutable_archive_source",
                error="PlayByPlayV3 absent from checked immutable archive directory",
                event_sha256=None,
                whole_sha256=hashlib.sha256(_whole(gid, current_bodies)).hexdigest(),
                missing_source_provenance=source["provenance"],
                original_event_order_preserved=True,
            )
            continue
        whole = _whole(gid, current_bodies)
        try:
            facts, clocks, strict_failure = exact_game_clock(source["raw"], whole)
        except ValueError as exc:
            game_results[gid] = dict(
                state="unqualified_original",
                error=str(exc),
                event_sha256=hashlib.sha256(source["raw"]).hexdigest(),
                whole_sha256=hashlib.sha256(whole).hexdigest(),
                original_event_order_preserved=True,
                canonical_pbp_accepted=False,
            )
        else:
            game_results[gid] = dict(
                state="qualified_complete_clock_vector",
                strict_original_score_failure=strict_failure,
                period_facts=facts,
                clocks={
                    str(q): {
                        str(tid): {str(pid): str(value) for pid, value in players.items()}
                        for tid, players in teams.items()
                    }
                    for q, teams in clocks.items()
                },
                event_sha256=hashlib.sha256(source["raw"]).hexdigest(),
                whole_sha256=hashlib.sha256(whole).hexdigest(),
                original_event_order_preserved=True,
                canonical_pbp_accepted=False,
            )
    player_results = []
    for pid in BOUNDARY_PLAYERS:
        rows = [r for r in primary if r["PLAYER_ID"] == pid]
        rows.sort(key=lambda r: r["GAME_ID"])
        game_ids = [r["GAME_ID"] for r in rows]
        existing = [r for r in canonical if int(r["player_id"]) == pid]
        require(
            len(rows) == len(set(game_ids)) == int(snapshot[pid]["GP"])
            and set(game_ids) == {str(r["game_id"]).zfill(10) for r in existing},
            "Minute sample GP or canonical membership differs",
        )
        canonical_by_game = {str(r["game_id"]).zfill(10): r for r in existing}
        ledger, failures, total = [], [], Fraction(0)
        for row in rows:
            gid, tid = row["GAME_ID"], row["TEAM_ID"]
            original = game_results[gid]
            entry = dict(
                game_id=gid,
                team_id=tid,
                raw_game_minute_literal=str(row["MIN"]),
                canonical_game_minute_literal=canonical_by_game[gid]["minutes"],
                event_sha256=original["event_sha256"],
                whole_sha256=original["whole_sha256"],
            )
            if original["state"] != "qualified_complete_clock_vector":
                entry.update(state="unknown_exact_clock", error=original["error"])
                failures.append(dict(game_id=gid, error=original["error"]))
            else:
                seconds = sum(
                    (
                        Fraction(teams[str(tid)].get(str(pid), "0"))
                        for teams in original["clocks"].values()
                    ),
                    Fraction(0),
                )
                require(seconds > 0, "Played sample has no independent positive clock")
                total += seconds
                canonical_minute = Fraction(canonical_by_game[gid]["minutes"])
                entry.update(
                    state="qualified_exact_game_clock",
                    exact_seconds=str(seconds),
                    exact_minutes=str(seconds / 60),
                    canonical_minus_exact_seconds=str(canonical_minute * 60 - seconds),
                )
            ledger.append(entry)
        result = dict(
            player_id=pid,
            game_ids=game_ids,
            games=len(rows),
            game_clock_ledger=ledger,
            reported_minute_literal=str(snapshot[pid]["MIN"]),
            raw_serialized_mean=str(
                sum((Fraction(str(r["MIN"])) for r in rows), Fraction(0)) / len(rows)
            ),
            canonical_serialized_mean=str(
                sum((Fraction(r["minutes"]) for r in existing), Fraction(0)) / len(existing)
            ),
            unknown_games=failures,
            unchanged_inclusive_limit_minutes="1/20",
        )
        if failures:
            result.update(
                state="unknown_incomplete_unique_timing",
                exact_mean_minutes=None,
                precise_requirement=(
                    "Unique correct full event/lineup evidence for each named unqualified game; "
                    "no source retry without changed immutable bytes"
                ),
            )
        else:
            mean = total / (60 * len(rows))
            reported = Fraction(str(snapshot[pid]["MIN"]))
            residual = abs(reported - mean)
            result.update(
                state="qualified_exact_clock_rounding"
                if residual <= Fraction(1, 20)
                else "timed_reported_source_conflict",
                exact_total_seconds=str(total),
                exact_mean_minutes=str(mean),
                absolute_residual_minutes=str(residual),
                precise_requirement=None,
            )
        player_results.append(result)
    report = dict(
        classification="independent_minute_precision_not_snapshot_acceptance",
        source_archive_sha256=digest,
        source_manifest=manifest,
        retained0168_reused=True,
        requested_new_source_count=15,
        new_source_count=len(manifest["files"]),
        game_results=game_results,
        player_results=player_results,
        independently_qualified_player_ids=[
            r["player_id"] for r in player_results if r["state"] == "qualified_exact_clock_rounding"
        ],
        unresolved_player_ids=[
            r["player_id"] for r in player_results if r["state"] != "qualified_exact_clock_rounding"
        ],
        source_hashes=dict(
            primary=hashlib.sha256(primary_raw).hexdigest(),
            reported=hashlib.sha256(snapshot_raw).hexdigest(),
            canonical=hashlib.sha256(canonical_raw).hexdigest(),
        ),
        accepted_values_rewritten=False,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-zip", required=True, type=Path)
    parser.add_argument("--sources-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = qualify(args.sources_zip, args.sources_sha256, args.output)
    print(
        json.dumps(
            {
                key: report[key]
                for key in ["independently_qualified_player_ids", "unresolved_player_ids"]
            },
            indent=2,
        )
    )
