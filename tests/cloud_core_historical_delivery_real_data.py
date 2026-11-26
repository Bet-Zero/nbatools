"""Actual historical HTTP/rendered answers; current readiness is separately false.

This does not replace or relax the existing strict-ready deployed P3 gates.
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
import requests

from nbatools.data_source import data_generation_context, data_path
from nbatools.development_data import selected_snapshot
from tests.cloud_reported_rest_deployed_real_data import _assert_count
from tests.test_deployed_k12_delivery_browser import (
    COMMON,
    _assert_rendered,
    _repeat_measurements,
    _response_elapsed_ms,
)
from tests.test_k05_subject_ownership_real_data import CASES as K05
from tests.test_k05_subject_ownership_real_data import _qualified_sample as _ownership_sample
from tests.test_k09_sequences_real_data import _assert_case as _assert_sequence
from tests.test_k09_sequences_real_data import _qualified_sources as _sequence_sources
from tests.test_k10_history_real_data import _assert_case as _assert_history
from tests.test_k10_history_real_data import _qualified_sources as _history_sources
from tests.test_k12_delivery_real_data import _assert_case as _assert_delivery
from tests.test_k12_delivery_real_data import _bindings, _qualified_sources

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/core-live-current-20261107"
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
# The live generation after both approved 2026-11-14 publications. It adds only
# participation files; the stats inputs these 22 cases read are rebound below.
LIVE = "availability-participation-2025-durant-v1-20261114"
LIVE_MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
GENERATIONS = {BASE: MANIFEST, LIVE: LIVE_MANIFEST}
CLEVELAND = "availability-cleveland-2024-v3-20261124"
CLEVELAND_MANIFEST = "d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034"
ORIGINAL_BINDING_SHA256 = "b2c2e145acec65db5e7707cb69ae4d1a194c19b97f5a2a52e3dbe632e326638f"
ORIGINAL_CAPTURE_SHA256 = "a5c718c7498f24d787866ff4e3d53220363e00588a045607e92f5947ac2074a5"
ORIGINAL_CASES_SHA256 = "096f093c24df872fca3107a1d4a23b19fc98e549b86aecfdc9df3b538ca1382a"
URL = "https://nbatools.vercel.app"
S4 = PROGRAM / "source-evidence/paired-missing-20261107/r2-final/composed-acceptance.json"
OWNED = PROGRAM / "source-evidence/distinct-player-or-20261106/independent/oracle.json"
LEBRON = PROGRAM / "source-evidence/k08-lebron-remaining/qualification.json"
APPLICABILITY = EVIDENCE / "historical-applicability-20261110.json"
APPLICABILITY_SHA256 = "230c8d46cd0306799f65d0d43f2b226c284a0639f269733aa3a2323ff9f926c5"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _original_case_identity(cases, *, evidence=EVIDENCE):
    """Verify the original archive without inspecting current source hashes."""
    binding = evidence / "live-code-binding.json"
    archive = evidence / "historical-live-original.zip"
    assert _sha(binding.read_bytes()) == ORIGINAL_BINDING_SHA256
    assert _sha(archive.read_bytes()) == ORIGINAL_CAPTURE_SHA256
    with ZipFile(archive) as original:
        captured_cases = original.read("acquired_data/core-historical-live/cases.json")
    assert _sha(captured_cases) == ORIGINAL_CASES_SHA256
    identity = [(case["id"], case["query"]) for case in cases]
    assert identity == [(case["id"], case["query"]) for case in json.loads(captured_cases)]
    assert len(identity) == len({case_id for case_id, _ in identity}) == 22
    return {
        "binding_sha256": ORIGINAL_BINDING_SHA256,
        "archive_sha256": ORIGINAL_CAPTURE_SHA256,
        "case_manifest_sha256": ORIGINAL_CASES_SHA256,
    }


def _fresh_capture_set(rows, cases, *, started, finished, expected_count=44):
    expected = [
        (viewport, case["id"], case["query"])
        for viewport in ("desktop", "mobile")
        for case in cases
    ]
    actual = [(item["viewport"], item["id"], item["query"]) for item in rows]
    assert len(actual) == len(set(actual)) == len(expected) == expected_count
    assert actual == expected, "Fresh capture changed question identity, order or viewport coverage"
    request_ids = [item.get("requestId") for item in rows]
    assert all(
        isinstance(rid, str) and re.fullmatch(r"req_[0-9a-f]{32}", rid) for rid in request_ids
    )
    assert len(set(request_ids)) == expected_count, "Every capture must have its own live request"
    captured_at = [datetime.fromisoformat(item["capturedAt"]) for item in rows]
    assert captured_at == sorted(captured_at), "Fresh capture timestamps must follow request order"
    assert all(started <= timestamp <= finished for timestamp in captured_at)


def _stabilization_capture_cases(original, delivery):
    named = {case["id"]: case for case in original}
    repeat_base = {
        f"{key}-repeat-{repetition}": key for repetition in range(1, 6) for key in COMMON
    }
    repeats = [dict(named[base], id=repeat_id) for repeat_id, base in repeat_base.items()]
    assert len(delivery) == 12
    assert [case["id"] for case in original[:12]] == list(delivery)
    return [*original[:12], *repeats, *original[12:]], repeat_base


def _stabilization_active_pointer():
    from nbatools.commands.pipeline.generation_publication import _resolve_r2_target
    from tools.r2_publication import verify_pointer_manifest

    client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    pointer, _, digest = verify_pointer_manifest(client, bucket, CLEVELAND)
    assert digest == CLEVELAND_MANIFEST, "Active R2 manifest differs from the frozen release"
    return pointer


def _stabilization_readiness(http, body):
    from tools.r2_publication import readiness_for_generation

    assert http == 503
    response = SimpleNamespace(status_code=http, json=lambda: body)
    assert readiness_for_generation(response, CLEVELAND, activation=True) is not None


def _parser_predicates(source):
    """Evaluate only the three reviewed historical-query detection predicates."""
    tree = ast.parse(source)
    nodes = [
        node
        for node in tree.body
        if (isinstance(node, ast.FunctionDef) and node.name in {"detect_quarter", "detect_half"})
        or (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "_LIST_VS" for target in node.targets
            )
        )
    ]
    assert len(nodes) == 3
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "reviewed_predicates", "exec"), namespace)
    return namespace


def _retained_applicability(binding, *, path=APPLICABILITY, expected_sha=APPLICABILITY_SHA256):
    """Bind the original 44 captures to a separately reviewed, finite code delta.

    This never qualifies a new deployment. Every old bound file still has an
    exact hash, and changed files need both an exact reviewed hash and an
    explicit semantic reach explanation for all original 22 query identities.
    """
    raw = path.read_bytes()
    assert _sha(raw) == expected_sha, "Unreviewed historical applicability companion"
    proof = json.loads(raw)
    assert proof["classification"] == "retained_original44_applicability_only"
    binding_raw = (EVIDENCE / "live-code-binding.json").read_bytes()
    assert proof["live_binding_sha256"] == _sha(binding_raw)
    assert binding == json.loads(binding_raw), "Original binding population must remain exact"
    assert len(binding["application_file_sha256"]) == proof["original_bound_file_count"] == 663
    assert selected_snapshot() is None, "Retained production captures cannot use development data"
    archive = EVIDENCE / "historical-live-original.zip"
    assert _sha(archive.read_bytes()) == proof["original_capture_sha256"]
    with ZipFile(archive) as z:
        cases_raw = z.read("acquired_data/core-historical-live/cases.json")
        captures = json.loads(z.read("acquired_data/core-historical-live/browser-receipt.json"))
    assert _sha(cases_raw) == proof["original_case_manifest_sha256"]
    cases = [{"id": c["id"], "query": c["query"]} for c in json.loads(cases_raw)]
    assert cases == proof["cases"] and len(cases) == 22
    assert len({c["id"] for c in cases}) == 22 and len(captures["receipts"]) == 44
    assert all(
        "data_quality" not in c["payload"]["result"]["metadata"] for c in captures["receipts"]
    )
    reviewed = {change["path"]: change for change in proof["changes"]}
    assert len(reviewed) == len(proof["changes"]) == 66
    changed = {}
    for relative, old_digest in binding["application_file_sha256"].items():
        actual = _sha((ROOT / relative).read_bytes())
        if actual != old_digest:
            changed[relative] = actual
    assert set(changed) == set(reviewed), "Historical bound file changed without semantic review"
    for relative, actual in changed.items():
        item = reviewed[relative]
        assert item["old_sha256"] == binding["application_file_sha256"][relative]
        assert item["reviewed_sha256"] == actual, f"Unreviewed change: {relative}"
        assert item["reviewed_functions"] and item["semantic_reach"]
        assert item["eligible_existing_case_ids"] == [case["id"] for case in cases]
    inventory = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py"))
    added = proof["reviewed_added_source_modules"]
    assert len(added) == len({item["path"] for item in added}) == 4
    for item in added:
        assert item["path"] not in proof["original_src_python_inventory"]
        assert item["path"].startswith("src/") and item["path"].endswith(".py")
        assert _sha((ROOT / item["path"]).read_bytes()) == item["reviewed_sha256"], (
            "Unreviewed added module change"
        )
        assert item["semantic_reach"] and item["eligible_existing_case_ids"] == [
            c["id"] for c in cases
        ]
    assert inventory == sorted(
        proof["original_src_python_inventory"] + [item["path"] for item in added]
    ), "Unreviewed source module addition/deletion"
    parser_path = "src/nbatools/commands/_parse_helpers.py"
    original = _parser_predicates(proof["original_parser_predicates"])
    current = _parser_predicates((ROOT / parser_path).read_text())
    for case in cases:
        text = case["query"].lower()
        for name in ("detect_quarter", "detect_half"):
            assert original[name](text) is None and current[name](text) is None
        assert original["_LIST_VS"].findall(text) == current["_LIST_VS"].findall(text)
        assert not re.search(r"\b(?:vs\.?|against|versus)\s+either\b", text)
        assert not re.search(r"\b(?:rest|injured|injury)\b", text)
    assert proof["full_core1_accepted"] is False and proof["fresh_deployment_accepted"] is False
    return {"companion_sha256": expected_sha, "cases": cases, "changed_files": len(changed)}


def _outcome(body):
    return SimpleNamespace(
        result_status=body["result_status"],
        result_reason=body["result_reason"],
        route=body["route"],
        metadata=body["result"]["metadata"],
        result=SimpleNamespace(to_dict=lambda: body["result"]),
    )


def _readiness(http, body, generation=BASE):
    assert http == 503
    assert body["ready"] is False and body["immutable_generation"] is True
    assert body["active_generation"] == generation
    assert [b["code"] for b in body["blockers"]] == ["new_season_not_loaded"]
    assert not body["exception"]["applied"]


def _cases():
    oracle, sources = _qualified_sources()
    _ownership_sample(K05[0])  # Independent raw identity/means; public summary omits game_log.
    delivery = {key.lower(): case for key, case in _bindings(oracle).items()}
    cases = [
        dict(id=key, query=case["query"], text=[], forbidden=["NaN", "undefined", "Infinity"])
        for key, case in delivery.items()
    ]
    seq, seq_sources = _sequence_sources()
    history, history_sources = _history_sources()
    frozen = {
        "live-k05": ("ownership", K05[0]),
        "live-k09": ("sequence", next(c for c in seq["cases"] if c["id"] == "K09-T1")),
        "live-k10": ("history", next(c for c in history["cases"] if c["id"] == "K10-G1")),
    }
    for key, (_, case) in frozen.items():
        cases.append(
            dict(
                id=key,
                query=case["query"],
                text=[],
                forbidden=[
                    "Data Not Available",
                    "No Matching Results",
                    "NaN",
                    "undefined",
                    "Infinity",
                ],
            )
        )
    assert (
        _sha(LEBRON.read_bytes())
        == "772db656d061d8b459e62c24aa939a9cae13479492eb5c1d7f1b1a6973fb9c1c"
    )
    lebron = json.loads(LEBRON.read_bytes())
    cases.append(
        dict(
            id="live-k08",
            query="How many games did LeBron James miss in 2025-26?",
            text=["LeBron James", "22", "2025-26"],
            forbidden=["Data Not Available", "NaN", "undefined"],
        )
    )
    # These frozen exact source/mean receipts were independently accepted in
    # PR594. Their manifest-bound raw inputs are authenticated below, not replaced
    # with agreeing results from another application path.
    s4 = json.loads(S4.read_bytes())
    for case in s4["s4_integration"]:
        key = f"live-s4-{case['kind']}-{case['relation']}"
        frozen[key] = ("s4", case)
        cases.append(
            dict(
                id=key,
                query=case["query"],
                text=["Jayson Tatum", case["selected_season"], "LAL"],
                forbidden=["Data Not Available", "No Matching Results", "NaN", "undefined"],
            )
        )
    owned = json.loads(OWNED.read_bytes())
    for owner, expression, name in [
        (
            "team",
            "(over 37 points or over 10 assists) with at least 125 team points",
            "native_team_owned",
        ),
        (
            "opponent",
            "(over 37 points or over 10 assists) when opponents scored under 110 points",
            "native_opponent_owned",
        ),
    ]:
        key = "live-owned-" + owner
        frozen[key] = (
            "owned",
            dict(
                owned["cases"][name],
                query=f"How many distinct players had {expression} in 2022-23?",
            ),
        )
        cases.append(
            dict(
                id=key,
                query=f"How many distinct players had {expression} in 2022-23?",
                text=["players", "2022-23"],
                forbidden=["Data Not Available", "NaN", "undefined"],
            )
        )
    assert len(cases) == len({c["id"] for c in cases}) == 22
    return cases, delivery, sources, frozen, seq_sources, history_sources, lebron, s4


def _assert_s4(body, case):
    result = _outcome(body)
    assert result.result_status == "ok" and result.result_reason is None
    meta, sections = result.metadata, body["result"]["sections"]
    assert meta[case["relation"] + "_player"] == "Jayson Tatum"
    assert meta["opponent"] == "LAL" and meta["split_type"] == "season"
    assert meta["season_list"] == ["2023-24", "2025-26"]
    assert sections["summary"][0]["games_total"] == 2
    actual, expected = (
        sections["split_comparison"],
        case["answer"]["result"]["sections"]["split_comparison"],
    )
    assert len(actual) == len(expected) == 1
    assert actual[0]["bucket"] == case["selected_season"]
    for field in ("games", "wins", "losses", "pts_avg", "reb_avg", "ast_avg"):
        assert actual[0][field] == pytest.approx(expected[0][field], abs=0.001)
    assert "no games in " + case["qualified_empty_season"] in body["result"]["caveats"]
    context = meta["team_context"] if case["kind"] == "team" else meta["player_context"]
    assert context["team_id" if case["kind"] == "team" else "player_id"] == (
        1610612738 if case["kind"] == "team" else 1627759
    )


def _assert_team(cell, abbreviation, name):
    # The 2026-11-07 interface rendered the abbreviation as cell text; the
    # current one shows only the full name. The name must match exactly.
    assert cell in (abbreviation + name, name), cell


def _shown(item, label):
    tables = [t for t in item["tables"] if t["label"] == label]
    assert len(tables) == 1
    return [dict(zip(tables[0]["headers"], row, strict=True)) for row in tables[0]["rows"]]


def _verify(item, delivery, sources, frozen, seq_sources, history_sources, lebron):
    body, key = item["payload"], item["id"]
    expected_query = (
        delivery[key]["query"]
        if key in delivery
        else "How many games did LeBron James miss in 2025-26?"
        if key == "live-k08"
        else frozen[key][1]["query"]
    )
    assert item["http"] == 200 and body["query"] == item["query"] == expected_query
    assert body["route"] == body["result"]["metadata"]["route"]
    assert body["result"]["metadata"]["query_text"] == expected_query
    outcome = _outcome(body)
    if key in delivery:
        _assert_delivery(outcome, delivery[key], sources)
        _assert_rendered(item, delivery[key])
        return
    if key == "live-k08":
        _assert_count(body, item["query"], set(lebron["missed_game_ids"]))
        assert outcome.metadata["team_context"]["team_id"] == 1610612747
        assert outcome.metadata["without_player"] == "LeBron James"
        assert "LeBron James missed 22 Lakers games" in item["text"]
        assert "2025-26" in item["text"]
        return
    family, case = frozen[key]
    if family == "sequence":
        _assert_sequence(outcome, case, seq_sources, "query")
        assert outcome.metadata["team_context"]["team_id"] == 1610612748
        assert "The Heat won 27 straight games from Feb 3 to Mar 25, 2013." == item["heroText"]
        shown = _shown(item, "Streaks")
        actual = body["result"]["sections"]["streak"]
        assert len(shown) == len(actual)
        for row, value in zip(shown, actual, strict=True):
            _assert_team(row["Team"], "MIA", "Heat")
            assert row["Length"] == f"{value['streak_length']} games"
            assert int(row["Games"]) == value["games"]
            assert row["Record"] == f"{value['wins']}-{value['losses']}"
            assert row["Streak"] == "Wins"
            for label, field in (("Start", "start_date"), ("End", "end_date")):
                assert row[label] == datetime.fromisoformat(value[field]).strftime("%b %-d")
    elif family == "history":
        _assert_history(outcome, case, history_sources)
        assert outcome.metadata["team_context"]["team_id"] == 1610612744
        expected = case["expected"]
        phrase = f"The Golden State Warriors are {expected['wins']}-{expected['losses']} in the 2015-16 playoffs"
        assert phrase in item["heroText"]
        rows = _shown(item, "Team record")
        assert len(rows) == 1
        row = rows[0]
        _assert_team(row["Team"], "GSW", "Golden State Warriors")
        assert row["W-L"] == f"{expected['wins']}-{expected['losses']}"
        assert int(row["Games"]) == expected["games"]
        for label, value in (
            ("Win %", 100 * expected["wins"] / expected["games"]),
            ("PPG", body["result"]["sections"]["summary"][0]["pts_avg"]),
        ):
            assert float(row[label].rstrip("%")) == pytest.approx(value, abs=0.051)
    elif family == "s4":
        _assert_s4(body, case)
        name = "Celtics" if case["kind"] == "team" else "Jaylen Brown"
        possessive = name + ("'" if name.endswith("s") else "'s")
        assert item["heroText"] == f"{possessive} season split for 2023-24, 2025-26 Regular Season."
        polarity = case["relation"].capitalize() + " player"
        opposite = "Without player" if case["relation"] == "with" else "With player"
        assert polarity in item["text"] and opposite not in item["text"]
        assert "Jayson Tatum" in item["text"] and "LAL" in item["text"]
        assert "no games in " + case["qualified_empty_season"] in item["text"].lower()
        rows = _shown(item, "Split buckets")
        assert len(rows) == 1
        shown, expected = rows[0], case["answer"]["result"]["sections"]["split_comparison"][0]
        assert shown["Split"] == case["selected_season"] and int(shown["GP"]) == 2
        assert shown["Record"] == f"{expected['wins']}-{expected['losses']}"
        for label, field in (("PTS", "pts_avg"), ("REB", "reb_avg"), ("AST", "ast_avg")):
            assert float(shown[label]) == pytest.approx(expected[field], abs=0.051)
    elif family == "owned":
        assert outcome.result_status == "ok"
        assert outcome.metadata["primary_count"] == case["distinct_players"]
        rows = body["result"]["sections"]["leaderboard"]
        actual = [(int(r["player_id"]), int(r["matching_games"])) for r in rows]
        assert len(actual) == len({pid for pid, _ in actual}) == case["distinct_players"]
        assert sorted(actual) == sorted(map(tuple, case["player_occurrences"]))
        assert (
            f"{case['distinct_players']} distinct players had a matching game in the 2022-23 regular season."
            in item["heroText"]
        )
        expression = case["query"].split(" had ", 1)[1].rsplit(" in ", 1)[0]
        assert expression in item["text"]
        counterowner = "opponents scored" if key == "live-owned-team" else "team points"
        assert counterowner not in item["text"]
    else:
        assert family == "ownership" and outcome.result_status == "ok"
        meta, sections = outcome.metadata, body["result"]["sections"]
        assert meta["team"] == case["team"] and meta["season"] == case["season"]
        assert meta["team_context"]["team_id"] == 1610612747
        row = sections["summary"][0]
        for field in ("games", "wins", "losses"):
            assert row[field] == case[field]
        for stat, value in case["means"].items():
            assert row[stat + "_avg"] == pytest.approx(value, abs=0.001)
        assert {"label": "Location", "value": "Home", "kind": "location"} in meta["applied_filters"]
        assert f"The Los Angeles Lakers are {case['wins']}-{case['losses']}" in item["heroText"]
        assert "2023-24" in item["heroText"]
        for phrase in ("Home", "110+ PTS", "Opp PTS < 110"):
            assert phrase in item["text"]
        shown = _shown(item, "Team record")
        assert len(shown) == 1
        _assert_team(shown[0]["Team"], "LAL", "Los Angeles Lakers")
        assert shown[0]["W-L"] == f"{case['wins']}-{case['losses']}"
        assert int(shown[0]["Games"]) == case["games"]
        assert float(shown[0]["PPG"]) == pytest.approx(case["means"]["pts"], abs=0.051)


# Approved 2026-11-14 packages whose append-only inventories bind each S4
# participation input's old bytes; LIVE equals those bytes plus appended rows.
PACKAGES = ("historical-participation-v1", "participation-2025-durant-v1")


def _assert_published_append(path, digest, entries):
    raw = data_path(path).read_bytes()
    assert _sha(raw) == entries[path]["sha256"] and len(raw) == entries[path]["size_bytes"]
    registry = json.loads((ROOT / ".github/data-publication-packages.json").read_bytes())
    packages = registry["packages"]
    bases = []
    for name in PACKAGES:
        package = packages[name]
        inventory = (ROOT / package["inventory"]).read_bytes()
        assert _sha(inventory) == package["inventory_sha256"]
        item = json.loads(inventory)["append_only"].get(path)
        if item:
            bases.append(item)
    # The first package touching the path appended to exactly the S4 input.
    assert bases and bases[0]["base_sha256"] == digest, path
    if path.endswith(".csv"):
        assert _sha(raw[: bases[0]["base_size_bytes"]]) == digest, path


def _assert_fixed_runtime(before, after):
    assert before["deployment"]["id"] == after["deployment"]["id"]
    assert before["deployed_sha"] == after["deployed_sha"]
    assert before["base_url"] == after["base_url"]
    assert before["build_input_tree_sha256"] == after["build_input_tree_sha256"]


def _run(
    tmp_path, *, retained=False, current_runtime=False, generation_name=BASE, stabilization=False
):
    assert not (retained and current_runtime), "Retained captures cannot be fresh runtime evidence"
    assert generation_name == BASE or current_runtime, "Only a fresh capture may use LIVE"
    assert not stabilization or (current_runtime and generation_name == CLEVELAND)
    manifest = CLEVELAND_MANIFEST if stabilization else GENERATIONS[generation_name]
    binding = json.loads((EVIDENCE / "live-code-binding.json").read_bytes())
    applicability = None
    capture_url = URL
    runtime_before = None
    deployment = binding["production_deployment"]
    assert deployment["id"] == "dpl_4nuGwYBav8vm6s3gfqFoGYdQgdeL"
    assert (
        deployment["meta"]["githubCommitSha"]
        == binding["deployed_commit"]
        == "a0fb2211a6707d647325129f1262308545001241"
    )
    assert URL.removeprefix("https://") in deployment["alias"]
    if retained:
        post = json.loads((EVIDENCE / "vercel-production-post-capture.json").read_bytes())
        observed = json.loads(post["response"]["content"][0]["text"])["result"]["deployment"]
        assert observed["id"] == deployment["id"] and observed["state"] == "READY"
        assert observed["meta"]["githubCommitSha"] == binding["deployed_commit"]
        assert URL.removeprefix("https://") in observed["alias"]
        assert datetime.fromisoformat(binding["checked_at"]) < datetime.fromisoformat(
            "2026-11-07T04:15:54.778806+00:00"
        )
        assert datetime.fromisoformat(post["checked_at"]) > datetime.fromisoformat(
            "2026-11-07T04:21:56.249817+00:00"
        )
    if stabilization:
        # The replacement runs alongside the existing gates until acceptance.
        assert _sha((EVIDENCE / "live-code-binding.json").read_bytes()) == ORIGINAL_BINDING_SHA256
    elif retained or current_runtime:
        applicability = _retained_applicability(binding)
    else:
        # Fresh public captures retain the original strict deployed-code binding.
        for path, digest in binding["application_file_sha256"].items():
            assert _sha((ROOT / path).read_bytes()) == digest
    for path, digest in binding["reused_evidence_sha256"].items():
        assert _sha((ROOT / path).read_bytes()) == digest
    with data_generation_context() as generation:
        assert (
            generation == generation_name
            and _sha(data_path("metadata/generation_manifest.json").read_bytes()) == manifest
        )
        cases, delivery, sources, frozen, seq_sources, history_sources, lebron, s4 = _cases()
        original_identity = _original_case_identity(cases) if stabilization else None
        if applicability:
            assert [{"id": c["id"], "query": c["query"]} for c in cases] == applicability["cases"]
        entries = json.loads(data_path("metadata/generation_manifest.json").read_bytes())["files"]
        entries = {e["path"]: e for e in entries}
        # Rebind retained S4 source inputs and accepted 2022 Boolean inputs.
        for path in [
            f"raw/{kind}/{season}_regular_season.csv"
            for season in ("2023-24", "2025-26", "2022-23")
            for kind in ("team_game_stats", "player_game_stats")
        ]:
            raw = data_path(path).read_bytes()
            assert _sha(raw) == entries[path]["sha256"] and len(raw) == entries[path]["size_bytes"]
        for path, digest in s4["validation"]["base_file_hashes"].items():
            if generation_name == BASE:
                assert entries[path]["sha256"] == digest
            else:
                _assert_published_append(path, digest, entries)
    folder = "core-historical-live-new-runtime" if current_runtime else "core-historical-live"
    if generation_name != BASE:
        folder += "-" + generation_name
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / folder
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "cases.json"
    capture_cases, repeat_base = (
        _stabilization_capture_cases(cases, delivery) if stabilization else (cases, {})
    )
    inputs.write_text(json.dumps(capture_cases) + "\n")
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "CI",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "NODE_EXTRA_CA_CERTS",
        "SSL_CERT_FILE",
    }
    env = {k: v for k, v in os.environ.items() if k in allowed}
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        classification="named_historical_API_rendered_acceptance_with_current_readiness_separate",
        deployment_binding=binding,
        generation=generation_name,
        manifest_sha256=manifest,
        full_core1_accepted=False,
        current_season_accepted=False,
        operational_readiness_accepted=False,
        nba_source_requests=0,
        k05_sample_keys_scope="qualified independent raw cohort; public summary does not expose game_log",
        production_writes=0,
        retained_code_applicability=applicability,
        consumer_acceptance="pending",
        capture_started_at=datetime.now(UTC).isoformat(),
        deployment_post_binding="pending independent provider observation after capture",
    )
    try:
        if current_runtime:
            from tests.core1_k08_runtime_binding import deployed_runtime_binding

            runtime_before = deployed_runtime_binding()
            capture_url = runtime_before["base_url"]
            receipt.update(
                classification="fresh_actual_original22_HTTP_UI_on_exact_reviewed_deployed_runtime",
                runtime_before=runtime_before,
                deployment_binding=runtime_before,
                original_historical_source_and_capture_binding=binding,
                historical_original_binding_preserved=True,
                fresh_deployment_accepted=False,
            )
        if stabilization:
            receipt["original_case_identity"] = original_identity
            receipt["active_pointer_before"] = _stabilization_active_pointer()
            receipt["provider_build_evidence"] = {
                "reference": runtime_before["base_url"],
                "deployed_sha": runtime_before["deployed_sha"],
                "required_review": "Bind actual provider build logs for the interpreter, toolchain, lock consumption and nonsecret runtime configuration to this immutable deployment before stabilization acceptance.",
            }
            receipt["locked_build_input_sha256"] = {
                relative: _sha((ROOT / relative).read_bytes())
                for relative in (
                    "pyproject.toml",
                    "uv.lock",
                    "vercel.json",
                    "frontend/package-lock.json",
                )
            }
        if retained:
            archive = EVIDENCE / "historical-live-original.zip"
            assert (
                _sha(archive.read_bytes())
                == "a5c718c7498f24d787866ff4e3d53220363e00588a045607e92f5947ac2074a5"
            )
            with ZipFile(archive) as z:
                for name in z.namelist():
                    assert not Path(name).is_absolute() and ".." not in Path(name).parts
                    prefix = "acquired_data/core-historical-live/"
                    if name.startswith(prefix):
                        (output / name.removeprefix(prefix)).write_bytes(z.read(name))
            receipt.update(
                classification="retained_actual44_HTTP_browser_captures_requalified_with_correct_canonical_labels",
                public_queries_this_replay=0,
                original_run=42337545754,
                deployment_post_binding="passed provider before/after alias, deployment and commit comparison",
            )
        else:
            subprocess.run(
                ["npm", "ci", "--ignore-scripts", "--no-audit"],
                cwd=ROOT / "frontend",
                env=env,
                check=True,
                timeout=180,
            )
            subprocess.run(
                [
                    "node",
                    str(ROOT / "frontend/tools/captureCoreIdentityFindCount.mjs"),
                    str(inputs),
                    str(output),
                    capture_url,
                ],
                env=env,
                check=True,
                timeout=900,
            )
        actual = json.loads((output / "browser-receipt.json").read_bytes())
        if current_runtime:
            assert actual["base"] == capture_url
        if stabilization:
            _fresh_capture_set(
                actual["receipts"],
                capture_cases,
                started=datetime.fromisoformat(receipt["capture_started_at"]),
                finished=datetime.now(UTC),
                expected_count=84,
            )
        else:
            assert len(actual["receipts"]) == 44
        if retained:
            # Preserve the original red run. The driver falsely required the word
            # Lakers where the existing interface correctly shows canonical LAL.
            expected_failures = {
                f"{view}/live-s4-{kind}-{relation}"
                for view in ("desktop", "mobile")
                for kind in ("team", "player")
                for relation in ("with", "without")
            }
            assert set(actual["failures"]) == expected_failures
            receipt["original_driver_failures"] = actual["failures"]
            receipt["original_capture_started_at"] = "2026-11-07T04:15:54.778806+00:00"
            receipt["original_capture_completed_at"] = "2026-11-07T04:21:56.249817+00:00"
        else:
            assert not actual["failures"]
        reviewed_cases = {c["id"]: c for c in cases}
        seen = set()
        assets, repeats = None, {}
        for item in actual["receipts"]:
            if retained:
                assert (
                    datetime.fromisoformat("2026-11-07T04:15:54.778806+00:00")
                    <= datetime.fromisoformat(item["capturedAt"])
                    <= datetime.fromisoformat("2026-11-07T04:21:56.249817+00:00")
                )
            pair = item["viewport"], item["id"]
            assert pair not in seen
            seen.add(pair)
            if retained:
                assert item["missing"] == (
                    ["Lakers"] if f"{item['viewport']}/{item['id']}" in expected_failures else []
                )
                item = dict(
                    item,
                    missing=[
                        text
                        for text in reviewed_cases[item["id"]]["text"]
                        if text not in item["text"]
                    ],
                )
            assert not any(item[name] for name in ("errors", "missing", "forbidden", "grainErrors"))
            assert item["overflow"]["document"] <= item["overflow"]["viewport"]
            if stabilization:
                assert item["screenshot"] == f"{pair[0]}-{pair[1]}.png"
                _stabilization_readiness(item["readinessHttpBefore"], item["readinessBefore"])
                _stabilization_readiness(item["readinessHttpAfter"], item["readinessAfter"])
            assert _sha((output / item["screenshot"]).read_bytes()) == item["screenshotSha256"]
            assets = item["assets"] if assets is None else assets
            assert (
                item["assets"] == assets
                and len(assets) == 1
                and assets[0].startswith(capture_url + "/assets/index-")
            )
            _readiness(item["readinessHttpBefore"], item["readinessBefore"], generation_name)
            _readiness(item["readinessHttpAfter"], item["readinessAfter"], generation_name)
            assert item["freshness"]["current_through"] == "2026-06-13"
            assert item["freshness"]["status"] == "stale"
            assert "Data through 2026-06-13" in item["freshnessText"]
            assert "awaiting refresh" in item["freshnessText"].lower()
            if current_runtime:
                assert "provisional" not in item["text"].lower()
                assert not item["payload"]["result"]["metadata"].get("data_quality")
            base_id = repeat_base.get(item["id"])
            if stabilization and (case := delivery.get(base_id or item["id"])):
                elapsed = _response_elapsed_ms(item, case)
                if base_id:
                    repeats.setdefault(base_id, []).append(elapsed)
                    item = dict(item, id=base_id)
            _verify(item, delivery, sources, frozen, seq_sources, history_sources, lebron)
        asset_hashes = [item["servedAssetSha256"] for item in actual["receipts"]]
        assert len(set(asset_hashes)) == 1
        assert _sha((output / "served-application.js").read_bytes()) == asset_hashes[0]
        assert seen == {
            (viewport, c["id"]) for viewport in ("desktop", "mobile") for c in capture_cases
        }
        receipt.update(
            consumer_acceptance="passed", actual_captures=44, actual_cases=22, served_assets=assets
        )
        # Separate deployment limitations. These are unmet original positives,
        # never counted among accepted cases or changed into refusal requirements.
        diagnostics = []
        for question in (
            []
            if retained
            else [
                "Thunder record without Kevin Durant in 2007-08",
                "Celtics record with Tatum and Brown missing in 2025-26",
            ]
        ):
            time.sleep(7)
            response = requests.post(
                capture_url + "/query", json={"query": question}, timeout=30, allow_redirects=False
            )
            diagnostics.append(
                dict(
                    query=question,
                    http=response.status_code,
                    actual=response.json(),
                    accepted=False,
                    classification="stage_only_source_dependency_not_positive_acceptance",
                )
            )
        receipt["unpublished_positive_observations"] = diagnostics
        if current_runtime:
            runtime_after = deployed_runtime_binding()
            _assert_fixed_runtime(runtime_before, runtime_after)
            if stabilization:
                pointer_after = _stabilization_active_pointer()
                assert receipt["active_pointer_before"] == pointer_after
                receipt["active_pointer_after"] = pointer_after
            receipt.update(
                runtime_after=runtime_after,
                deployment_post_binding="passed provider GitHub Production deployment/commit/immutable host/build-tree comparison",
                fresh_deployment_accepted=True,
                current_season_accepted=False,
                operational_readiness_accepted=False,
                public_UI_queries=len(actual["receipts"]),
                separate_unaccepted_source_diagnostics=2,
            )
            if stabilization:
                receipt["k12_deployed_repeat_measurements"] = _repeat_measurements(repeats)
    except Exception as exc:
        receipt.update(
            consumer_acceptance="failed", failure=dict(type=type(exc).__name__, message=str(exc))
        )
        if current_runtime:
            receipt["fresh_deployment_accepted"] = False
        raise
    finally:
        receipt["capture_completed_at"] = datetime.now(UTC).isoformat()
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")


def test_original_historical_consumers_through_live_api_and_ui(tmp_path):
    _run(tmp_path)


def test_requalify_retained_actual_historical_api_and_ui(tmp_path):
    _run(tmp_path, retained=True)


def test_actual_new_runtime_historical_api_and_ui(tmp_path):
    """Fresh original22/44 delivery; current readiness/source gaps stay open."""
    _run(tmp_path, current_runtime=True)


def test_actual_new_runtime_historical_api_and_ui_on_live_generation(tmp_path):
    """The same fresh original22/44 delivery on the generation served after 2026-11-14."""
    _run(tmp_path, current_runtime=True, generation_name=LIVE)


def test_stabilization_original_historical_api_and_ui(tmp_path):
    """Fresh acceptance on the frozen Cleveland runtime, alongside the old gate."""
    _run(tmp_path, current_runtime=True, generation_name=CLEVELAND, stabilization=True)
