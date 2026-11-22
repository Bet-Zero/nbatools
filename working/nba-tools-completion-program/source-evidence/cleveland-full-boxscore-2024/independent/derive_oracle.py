"""Independent native-row arithmetic. No NBA Tools imports, network, or publication."""

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

CLE = 1610612739
BASE = "availability-season-inactive-2024-v1-20261116"
MANIFEST = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
DNP = re.compile(
    r"^(DNP|DND|NWT|INACTIVE|DID NOT PLAY|DID NOT DRESS|NOT WITH TEAM|NOT PLAYING)\b", re.I
)
ACTIVITY = (
    "points",
    "fieldGoalsMade",
    "fieldGoalsAttempted",
    "threePointersMade",
    "threePointersAttempted",
    "freeThrowsMade",
    "freeThrowsAttempted",
    "reboundsOffensive",
    "reboundsDefensive",
    "reboundsTotal",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "foulsPersonal",
)
REJECTED = {
    (g, 1610612751, 1642385)
    for g in (22400022, 22400027, 22400113, 22400136, 22400276, 22400348, 22401211)
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def name_key(name):
    words = re.sub(
        r"[^a-z0-9]+",
        " ",
        unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower(),
    ).split()
    if words and words[-1] in {"jr", "sr", "ii", "iii", "iv"}:
        words.pop()
    return " ".join(words)


def derive(base, sources, evidence, movement):
    manifest_raw = (base / "metadata/generation_manifest.json").read_bytes()
    assert sha(manifest_raw) == MANIFEST
    entries = {r["path"]: r for r in json.loads(manifest_raw)["files"]}
    canonical_hashes = {}

    def body(relative):
        raw = (base / relative).read_bytes()
        assert sha(raw) == entries[relative]["sha256"]
        assert len(raw) == entries[relative]["size_bytes"]
        canonical_hashes[relative] = sha(raw)
        return raw

    def frame(kind):
        import io

        return pd.read_csv(io.BytesIO(body(f"raw/{kind}/2024-25_regular_season.csv")))

    stats, teams, catalog, old = [
        frame(k)
        for k in ("player_game_stats", "team_game_stats", "games", "player_game_availability")
    ]
    import io

    roster = pd.read_csv(io.BytesIO(body("raw/rosters/2024-25.csv")))
    baseline_raw, request_raw = [
        (evidence / n).read_bytes() for n in ("baseline.json", "request.json")
    ]
    baseline, request = map(json.loads, (baseline_raw, request_raw))
    metadata_raw = (sources / "sources.json").read_bytes()
    metadata = json.loads(metadata_raw)
    assert request["frozen_baseline_sha256"] == sha(baseline_raw)
    assert metadata["collection_request_sha256"] == sha(request_raw)
    assert request["base_generation"] == baseline["base_generation"] == BASE
    assert request["base_manifest_sha256"] == baseline["base_manifest_sha256"] == MANIFEST
    assert metadata["errors"] == [] and metadata["production_writes"] == 0
    assert len(metadata["files"]) == len(request["source_files"]) == 164
    assert {p.name for p in (sources / "sources").iterdir()} == set(metadata["files"])
    source_hashes = {}
    documents = {}
    for filename, record in metadata["files"].items():
        raw = (sources / "sources" / filename).read_bytes()
        item = request["source_files"][filename]
        assert sha(raw) == record["sha256"] and len(raw) == record["size_bytes"] <= 2_000_000
        blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        assert blob == record["git_blob_sha"] == item["git_blob_sha"]
        assert record["url"] == item["url"] and record["reader_attempts"] == 1
        assert record["revision"] == metadata["revision"] == request["revision"]
        assert datetime.fromisoformat(record["retrieved_at"]).tzinfo is not None
        source_hashes[filename] = dict(
            sha256=sha(raw),
            size_bytes=len(raw),
            git_blob_sha=blob,
            url=record["url"],
            retrieved_at=record["retrieved_at"],
        )
        documents[filename] = json.loads(raw)

    identity_names = {
        int(pid): set(f.player_name.map(name_key)) for pid, f in stats.groupby("player_id")
    }
    listed, game_rows, errors = [], [], {}
    requirements = request["requirements"]
    assert len(requirements) == 82
    assert {int(r["game_id"]) for r in requirements} == set(
        teams.loc[teams.team_id.eq(CLE), "game_id"]
    )
    for req in requirements:
        gid = int(req["game_id"])
        traditional = documents[f"boxscoretraditionalv3_{gid:010d}.json"]["boxScoreTraditional"]
        summary = documents[f"boxscoresummaryv3_{gid:010d}.json"]["boxScoreSummary"]
        game = catalog.loc[catalog.game_id.eq(gid)].iloc[0]
        gt = teams.loc[teams.game_id.eq(gid)].set_index("team_id")
        assert len(gt) == 2 and CLE in gt.index
        problem = []
        assert int(traditional["gameId"]) == int(summary["gameId"]) == gid
        assert int(summary["gameStatus"]) == 3
        assert summary["gameEt"][:10] == req["game_date"] == str(game.game_date)[:10]
        assert {int(game.home_team_id), int(game.away_team_id)} == set(gt.index)
        rowset = []
        for side, canonical_side in (
            ("homeTeam", int(game.home_team_id)),
            ("awayTeam", int(game.away_team_id)),
        ):
            td, sm = traditional[side], summary[side]
            tid = int(td["teamId"])
            assert tid == int(sm["teamId"]) == canonical_side
            assert traditional["homeTeamId"] == summary["homeTeamId"] == int(game.home_team_id)
            assert traditional["awayTeamId"] == summary["awayTeamId"] == int(game.away_team_id)
            assert td["teamTricode"] == sm["teamTricode"] == gt.loc[tid, "team_abbr"]
            assert int(td["statistics"]["points"]) == int(sm["score"]) == int(gt.loc[tid, "pts"])
            for person in td["players"]:
                clock = str(person["statistics"].get("minutes") or "").strip()
                comment = str(person.get("comment") or "").strip()
                seconds = None
                invalid = bool(clock) and (
                    not re.fullmatch(r"\d+:\d{2}(?:\.\d+)?", clock)
                    or float(clock.split(":")[-1]) >= 60
                )
                if invalid:
                    problem.append(
                        dict(
                            code="invalid_native_clock",
                            team_id=tid,
                            player_id=int(person["personId"]),
                            literal=clock,
                        )
                    )
                    state = "invalid"
                else:
                    seconds = (
                        sum(float(x) * 60**i for i, x in enumerate(reversed(clock.split(":"))))
                        if clock
                        else None
                    )
                    positive = seconds is not None and seconds > 0
                    explicit_dnp = bool(DNP.match(comment))
                    if positive and explicit_dnp:
                        problem.append(
                            dict(code="clock_comment_conflict", player_id=int(person["personId"]))
                        )
                    state = "played" if positive else "did_not_play" if explicit_dnp else "unknown"
                    if state == "did_not_play" and any(
                        float(person["statistics"].get(k) or 0) != 0 for k in ACTIVITY
                    ):
                        problem.append(
                            dict(code="dnp_positive_activity", player_id=int(person["personId"]))
                        )
                rowset.append(
                    dict(
                        game_id=gid,
                        game_date=req["game_date"],
                        team_id=tid,
                        player_id=int(person["personId"]),
                        player_name=(person["firstName"] + " " + person["familyName"]).strip(),
                        participation_state=state,
                        source_minutes=None if seconds is None else seconds / 60,
                        source_clock_literal=clock,
                        source_comment=comment,
                        source_kind="Traditional.players",
                        points=int(person["statistics"]["points"]),
                    )
                )
            for person in sm["inactives"]:
                rowset.append(
                    dict(
                        game_id=gid,
                        game_date=req["game_date"],
                        team_id=tid,
                        player_id=int(person["personId"]),
                        player_name=(person["firstName"] + " " + person["familyName"]).strip(),
                        participation_state="did_not_play",
                        source_minutes=None,
                        source_clock_literal="",
                        source_comment="INACTIVE - BoxScoreSummaryV3 explicit listed row",
                        source_kind="Summary.inactives",
                        points=None,
                    )
                )
            summary_only = {int(p["personId"]) for p in sm["players"]} - {
                r["player_id"] for r in rowset if r["team_id"] == tid
            }
            if summary_only:
                problem.append(
                    dict(
                        code="summary_players_without_traditional_state",
                        team_id=tid,
                        player_ids=sorted(summary_only),
                    )
                )
        keys = [(r["game_id"], r["player_id"]) for r in rowset]
        if len(keys) != len(set(keys)):
            problem.append(dict(code="duplicate_listed_player_game"))
        for r in rowset:
            known = identity_names.get(r["player_id"], set())
            words = r["player_name"].split()
            variants = {name_key(r["player_name"]), name_key(" ".join(words[1:] + words[:1]))}
            if known and not known.intersection(variants):
                problem.append(
                    dict(
                        code="canonical_name_conflict",
                        player_id=r["player_id"],
                        literal=r["player_name"],
                    )
                )
        played = {
            (r["team_id"], r["player_id"]) for r in rowset if r["participation_state"] == "played"
        }
        appearances = stats.loc[stats.game_id.eq(gid)]
        expected = set(zip(appearances.team_id, appearances.player_id))
        if played != expected and not any(p["code"] == "invalid_native_clock" for p in problem):
            problem.append(
                dict(
                    code="canonical_played_identity_conflict",
                    native_only=sorted(played - expected),
                    canonical_only=sorted(expected - played),
                )
            )
        by_key = {(r["team_id"], r["player_id"]): r for r in rowset}
        for p in appearances.itertuples():
            if (int(p.team_id), int(p.player_id)) in by_key and by_key[
                int(p.team_id), int(p.player_id)
            ]["points"] != int(p.pts):
                problem.append(
                    dict(code="canonical_player_points_conflict", player_id=int(p.player_id))
                )
        if problem:
            errors[str(gid)] = problem
        for row in rowset:
            row["game_qualified"] = not problem
        listed.extend(rowset)
        game_rows.append(
            dict(
                game_id=gid,
                game_date=req["game_date"],
                qualified=not problem,
                home_team_id=int(game.home_team_id),
                away_team_id=int(game.away_team_id),
                points_by_team={str(int(t)): int(gt.loc[t, "pts"]) for t in gt.index},
                listed_players=len(rowset),
                errors=problem,
            )
        )

    receipt = json.loads(body("raw/player_game_inactive/2024-25_regular_season.source.json"))
    assert {
        (r["game_id"], r["team_id"], r["player_id"]) for r in receipt["identity_name_rejections"]
    } == REJECTED
    inactive = pd.read_csv(
        io.BytesIO(
            body(
                "raw/player_game_inactive_sources/906e36b7f4f5010ff33b35bf12b22d0083b9a0099f49383b01d2fea8ae82e769.csv"
            )
        )
    )
    inactive = inactive.loc[inactive.season_type_id.eq(2)].copy()
    inactive["player_name"] = inactive.first_name + " " + inactive.last_name
    before = {}

    def add(facts, gid, tid, pid, state):
        if state not in {"played", "did_not_play"}:
            return
        key, value = (int(gid), int(pid)), (int(tid), state)
        assert key not in facts or facts[key] == value, (key, facts.get(key), value)
        facts[key] = value

    for r in stats.loc[stats.minutes.gt(0)].itertuples():
        add(before, r.game_id, r.team_id, r.player_id, "played")
    for r in old.itertuples():
        add(before, r.game_id, r.team_id, r.player_id, r.participation_state)
    for r in inactive.itertuples():
        if (int(r.game_id), int(r.team_id), int(r.player_id)) not in REJECTED:
            add(before, r.game_id, r.team_id, r.player_id, "did_not_play")
    after = dict(before)
    accepted = [r for r in listed if r["game_qualified"]]
    for r in accepted:
        add(after, r["game_id"], r["team_id"], r["player_id"], r["participation_state"])
    pairs = {
        (int(t), int(p))
        for f in (stats, old, roster, inactive)
        for t, p in zip(f.team_id, f.player_id)
    }
    with ZipFile(movement) as archive:
        movement_raw = archive.read("player-movement.json")
        moves = json.loads(movement_raw)["NBA_Player_Movement"]["rows"]
    for m in moves:
        if "2024-10-21" <= m["TRANSACTION_DATE"][:10] <= "2025-04-13" and m["PLAYER_ID"]:
            pairs.add((int(m["TEAM_ID"]), int(m["PLAYER_ID"])))
            if m["Transaction_Type"] == "Trade":
                pairs.add((int(m["Additional_Sort"]), int(m["PLAYER_ID"])))
    assert sorted(map(list, pairs)) == sorted(baseline["all_team_candidate_pairs"])
    expanded_pairs = pairs | {(r["team_id"], r["player_id"]) for r in listed}
    team_games = {int(t): set(map(int, f.game_id)) for t, f in teams.groupby("team_id")}

    def complete(facts, cohort):
        return {(t, p) for t, p in cohort if all((g, p) in facts for g in team_games[t])}

    before_full, after_full = complete(before, pairs), complete(after, expanded_pairs)
    fixed = [int(r["player_id"]) for r in baseline["candidates"]]
    expanded = sorted(p for t, p in expanded_pairs if t == CLE)
    cle_games = sorted(team_games[CLE])
    names = {
        int(r.player_id): str(r.player_name)
        for f in (inactive, roster, stats)
        for r in f.itertuples()
    }
    for r in listed:
        names.setdefault(r["player_id"], r["player_name"])

    def state(facts, tid, gid, pid):
        value = facts.get((gid, pid))
        return "unknown" if value is None else value[1] if value[0] == tid else "not_member"

    def cohort_rows(ids):
        def counts(values):
            return {
                s: list(values).count(s)
                for s in ("played", "did_not_play", "not_member", "unknown")
            }

        result = []
        for pid in ids:
            before_states = {g: state(before, CLE, g, pid) for g in cle_games}
            after_states = {g: state(after, CLE, g, pid) for g in cle_games}
            unknown = [g for g, s in after_states.items() if s == "unknown"]
            result.append(
                dict(
                    player_id=pid,
                    player_name=names.get(pid),
                    before=counts(before_states.values()),
                    after=counts(after_states.values()),
                    before_complete="unknown" not in before_states.values(),
                    after_complete=not unknown,
                    unknown_game_ids=unknown,
                    unknown_in_unqualified_games=[g for g in unknown if str(g) in errors],
                    unknown_without_listed_evidence=[g for g in unknown if str(g) not in errors],
                    before_game_states=before_states,
                    after_game_states=after_states,
                )
            )
        return result

    fixed_rows, expanded_rows = cohort_rows(fixed), cohort_rows(expanded)
    assert sum(r["before_complete"] for r in fixed_rows) == 5
    assert (
        dict(sum((Counter(r["before"]) for r in fixed_rows), Counter()))
        == baseline["census"]["states"]
    )
    # Native Summary scores own all captured-game outcomes, including games
    # whose Traditional clock makes player observations unqualified. Scores
    # outside this capture come from retained canonical raw team totals.
    scores = {(int(r.game_id), int(r.team_id)): int(r.pts) for r in teams.itertuples()}
    for game in game_rows:
        for tid, score in game["points_by_team"].items():
            assert scores[game["game_id"], int(tid)] == score
            scores[game["game_id"], int(tid)] = score
    opponents = {
        (int(r.game_id), int(r.team_id)): int(r.opponent_team_id) for r in teams.itertuples()
    }
    team_names = {int(r.team_id): str(r.team_name) for r in teams.itertuples()}
    answers = []
    for tid, pid in sorted(after_full - before_full):
        case = dict(
            team_id=tid,
            team_name=team_names[tid],
            player_id=pid,
            player_name=names[pid],
            cohort="original_cleveland"
            if tid == CLE and pid in fixed
            else "new_cleveland"
            if tid == CLE
            else "opponent",
        )
        for label, wanted in (("with", "played"), ("without", "did_not_play")):
            ids = [g for g in sorted(team_games[tid]) if after[g, pid] == (tid, wanted)]
            assert all(scores[g, tid] != scores[g, opponents[g, tid]] for g in ids)
            wins = sum(scores[g, tid] > scores[g, opponents[g, tid]] for g in ids)
            points = sum(scores[g, tid] for g in ids)
            case[label] = dict(
                query=f"{team_names[tid]} record {label} {names[pid]} in 2024-25",
                game_ids=ids,
                games=len(ids),
                wins=int(wins),
                losses=len(ids) - int(wins),
                pts_sum=points,
                pts_avg=round(points / len(ids), 3) if ids else None,
                result_status="ok" if ids else "no_result",
                result_reason=None if ids else "no_match",
            )
        answers.append(case)
    original_zip = (evidence / "originals.zip").read_bytes()
    assert sha(original_zip) == "594bab365fa2eda59a217c2137bda901dd0d55b7c8e60268a7ba9f2da2ab66d6"
    with ZipFile(io.BytesIO(original_zip)) as archive:
        assert archive.read("sources.json") == metadata_raw
        for filename, binding in source_hashes.items():
            assert sha(archive.read("sources/" + filename)) == binding["sha256"]
    return dict(
        classification="independent_native_source_oracle_not_publication",
        bindings=dict(
            base_generation=BASE,
            base_manifest_sha256=MANIFEST,
            baseline_sha256=sha(baseline_raw),
            request_sha256=sha(request_raw),
            sources_sha256=sha(metadata_raw),
            movement_sha256=sha(movement_raw),
            canonical_hashes=canonical_hashes,
            source_files=source_hashes,
            original_zip_sha256=sha(original_zip),
            original_zip_size_bytes=len(original_zip),
            original_body_bytes=sum(r["size_bytes"] for r in source_hashes.values()),
        ),
        qualified_game_ids=[r["game_id"] for r in game_rows if r["qualified"]],
        quarantined_games=errors,
        games=game_rows,
        accepted_rows=accepted,
        original_candidate_pairs=sorted(map(list, pairs)),
        expanded_candidate_pairs=sorted(map(list, expanded_pairs)),
        before_complete_pairs=sorted(map(list, before_full)),
        after_complete_pairs=sorted(map(list, after_full)),
        opponent_new_complete_pairs=sorted(
            map(list, {(t, p) for t, p in after_full - before_full if t != CLE})
        ),
        fixed_cohort=fixed_rows,
        expanded_cohort=expanded_rows,
        new_cleveland_candidate_ids=sorted(set(expanded) - set(fixed)),
        new_complete_answers=answers,
        summary=dict(
            requested_games=len(game_rows),
            qualified_games=sum(r["qualified"] for r in game_rows),
            quarantined_games=len(errors),
            accepted_rows=len(accepted),
            accepted_states=dict(Counter(r["participation_state"] for r in accepted)),
            fixed_before_full=sum(r["before_complete"] for r in fixed_rows),
            fixed_after_full=sum(r["after_complete"] for r in fixed_rows),
            fixed_after_states=dict(sum((Counter(r["after"]) for r in fixed_rows), Counter())),
            league_before_full=len(before_full),
            league_after_full=len(after_full),
            original_pairs=len(pairs),
            expanded_pairs=len(expanded_pairs),
            net_new_direct_facts=dict(Counter(v[1] for k, v in after.items() if k not in before)),
            cleveland_unknown_reason_counts=dict(
                whole_game_unqualified=sum(
                    len(r["unknown_in_unqualified_games"]) for r in fixed_rows
                ),
                omitted_from_qualified_game_sources=sum(
                    len(r["unknown_without_listed_evidence"]) for r in fixed_rows
                ),
            ),
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("base", "sources", "evidence", "movement", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    result = derive(args.base, args.sources, args.evidence, args.movement)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "oracle.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
