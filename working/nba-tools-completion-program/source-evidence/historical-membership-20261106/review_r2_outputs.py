"""Independently compare retained R2 outputs to original native evidence."""

import csv
import hashlib
import io
import json
import runpy
import subprocess
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("working/nba-tools-completion-program/source-evidence/historical-membership-20261106")
REV = "2a310bdf5c776e905508c8afd1d8decbd1f65e08"
subprocess.run(["git", "cat-file", "-e", REV + "^{commit}"], check=True)
source = runpy.run_path(str(ROOT / "source_oracle.py"))
facts, original_games, _ = source["facts"]()
original_score = json.loads((ROOT / "original-score-receipt.json").read_bytes())
bos = 1610612738
with ZipFile(ROOT / "required-numerical.zip") as z:
    assert (
        hashlib.sha256((ROOT / "required-numerical.zip").read_bytes()).hexdigest()
        == "cd1d1c9022458c3e92cb61bc351df617ee627bca7690e164333aa0692cc6aff2"
    )
    summary = json.loads(z.read("summary.json"))
    assert (
        summary["selected"],
        summary["executed"],
        summary["passed"],
        summary["skipped"],
        summary["failed"],
        summary["errors"],
        summary["xfailed"],
    ) == (2, 2, 2, 0, 0, 0, 0)
    assert summary["candidate_sha"] == "5db1448783efc40f7801956e67c5afc282a8f2f7"
    assert summary["generation"] == "availability-lebron-season-v1-20261031"
    prefix = "acquired_data/tatum-2023-stage/"
    acceptance = json.loads(z.read(prefix + "acceptance.json"))
    assert all(p["status"] == "passed" for p in acceptance["phases"].values())
    assert acceptance["candidate_stage_qualified"] and acceptance["consumer_acceptance"] == "passed"
    assert acceptance["production_writes"] == acceptance["new_nba_source_calls"] == 0
    rows = list(
        csv.DictReader(
            io.StringIO(
                z.read(
                    prefix
                    + "composed-overlay/raw/player_game_availability/2023-24_regular_season.csv"
                ).decode()
            )
        )
    )

    def key(row):
        return (f"{int(row['game_id']):010d}", int(row["team_id"]), int(row["player_id"]))

    selected = {key(r): r for r in rows if f"{int(r['game_id']):010d}" in original_games}
    assert selected.keys() == facts.keys()
    for k, expected in facts.items():
        actual = selected[k]
        assert (actual["game_date"], actual["participation_state"], actual["player_name"]) == (
            expected["date"],
            expected["state"],
            expected["player_name"].strip(),
        ), k
    coverage = acceptance["coverage"]
    expected = json.loads(
        subprocess.check_output(
            [
                "git",
                "show",
                source["REVISION"] + ":working/nba-tools-completion-program/source-evidence/"
                "k08-tatum-2023/independent-source-oracle.json",
            ]
        )
    )
    assert {int(r["game_id"]): (r["game_date"], r["state"]) for r in coverage["games"]} == {
        int(r["game_id"]): (r["game_date"], r["state"]) for r in expected["projected_games"]
    }
    assert coverage["requested_games"] == coverage["observed_team_games"] == 82
    assert coverage["counts"] == dict(played=74, did_not_play=8, same_game_other_side=0, unknown=0)
    assert coverage["missed_games"] == 8 and coverage["missing_keys"] == []
    assert "independent full-season completeness unknown" in coverage["denominator"]
    all_ids = {int(g) for g in original_score["all_game_ids"]}
    home_ids = {int(g) for g in original_score["home_game_ids"]}
    for entry in acceptance["answers"]:
        actual = entry["actual"]
        assert actual["status"] == "ok"
        sections = actual["result"]["sections"]
        if actual["route"] == "game_finder":
            wanted = home_ids if "home" in entry["query"] else all_ids
            assert {int(r["game_id"]) for r in sections["finder"]} == wanted
            assert sections["count"] == [dict(count=len(wanted))]
        else:
            assert {int(r["game_id"]) for r in sections["game_log"]} == all_ids
            row = sections["summary"][0]
            assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (8, 7, 1, 128.75)
    held_out = [e for e in acceptance["api_checks"] if "kwargs" in e]
    assert len(held_out) == 6
    for entry in held_out:
        args = entry["kwargs"]
        body = entry["body"]
        assert body["result_status"] == "ok"
        row = body["result"]["sections"]["summary"][0]
        gid = f"{args['game_id']:010d}"
        matching = [(k, v) for k, v in facts.items() if k[0] == gid and k[2] == args["player_id"]]
        assert len(matching) == 1
        (g, club, pid), native = matching[0]
        expected_state = native["state"] if args["team_id"] == club else "not_member"
        assert row["participation_state"] == expected_state
        assert row["membership_state"] == ("member" if args["team_id"] == club else "not_member")
        assert row["member_team_id"] == club and row["evidence_basis"] == "exact_game"
    validation = json.loads(z.read(prefix + "composed-overlay/validation.json"))
    assert len(validation["overlay_files"]) == 431
    for item in validation["overlay_files"]:
        raw = z.read(prefix + "composed-overlay/" + item["path"])
        assert len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    old_path = Path(
        "working/nba-tools-completion-program/source-evidence/k08-composition/staging-acceptance-source.zip"
    )
    assert (
        hashlib.sha256(old_path.read_bytes()).hexdigest()
        == "4ce53f28bd44230138f000927d3ffa43dbe618759e265ce65e095b505ecb92cf"
    )
    with ZipFile(old_path) as old:
        member = next(n for n in old.namelist() if n.endswith("/validation.json"))
        prior = json.loads(old.read(member))
        assert len(prior["overlay_files"]) == 407
        oldprefix = member.removesuffix("validation.json")
        for item in prior["overlay_files"]:
            path = item["path"]
            previous = old.read(oldprefix + path)
            current = z.read(prefix + "composed-overlay/" + path)
            if path == "raw/player_game_availability/2023-24_regular_season.csv":
                old_rows = {key(r): r for r in csv.DictReader(io.StringIO(previous.decode()))}
                current_rows = {key(r): r for r in csv.DictReader(io.StringIO(current.decode()))}
                assert len(old_rows) == 597 and len(current_rows) == 875
                assert all(current_rows[k] == v for k, v in old_rows.items())
            elif path == "raw/player_game_availability/2023-24_regular_season.imports.json":
                before = json.loads(previous)
                after = json.loads(current)
                assert len(before) == 17 and len(after) == 25
                assert all(after[k] == v for k, v in before.items())
            else:
                assert previous == current, path
    unknown = acceptance["unknown_control"]
    assert unknown["report"]["missed_games"] is None and unknown["report"]["counts"]["unknown"] == 1
    assert (
        unknown["actual"]["status"] == "no_result" and not unknown["actual"]["result"]["sections"]
    )
with ZipFile(ROOT / "raw-qa.zip") as z:
    assert (
        hashlib.sha256((ROOT / "raw-qa.zip").read_bytes()).hexdigest()
        == "d66a08055dc0dbc3fe831f8a22a20783a9b175755d80c09398d2474354a0b3e3"
    )
    rawqa = json.loads(z.read("summary.json"))
    assert rawqa["case_ids"] == ["k08_compact_home_absence_season"]
    assert rawqa["expectation_case_counts"] == {"pass": 1} and rawqa[
        "expectation_check_counts"
    ] == {"pass": 7}
    assert (
        rawqa["failed_case_ids"] == []
        and rawqa["data_generation"] == "availability-lebron-season-v1-20261031"
    )
print(
    json.dumps(
        dict(
            reviewed_revision=REV,
            actual_r2_revision=summary["candidate_sha"],
            required_tests=2,
            required_passed=2,
            rawqa_cases=1,
            rawqa_checks=7,
            states_compared=82,
            new_listed_cells_compared=278,
            held_out_http_cases=6,
            composed_paths=431,
            prior_paths_preserved=407,
            source_arithmetic=dict(
                games=8, home_games=5, wins=7, losses=1, points=1030, ppg=128.75
            ),
            unknown_control="passed",
            conclusion="independently_verified_bounded_staged_output_not_production_or_complete_historical_coverage",
        )
    )
)
