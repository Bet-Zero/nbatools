"""Actual historical HTTP/rendered answers; current readiness is separately false.

This does not replace or relax the existing strict-ready deployed P3 gates.
"""

import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
import requests

from nbatools.data_source import data_generation_context, data_path
from tests.cloud_reported_rest_deployed_real_data import _assert_count
from tests.test_deployed_k12_delivery_browser import _assert_rendered
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
URL = "https://nbatools.vercel.app"
S4 = PROGRAM / "source-evidence/paired-missing-20261107/r2-final/composed-acceptance.json"
OWNED = PROGRAM / "source-evidence/distinct-player-or-20261106/independent/oracle.json"
LEBRON = PROGRAM / "source-evidence/k08-lebron-remaining/qualification.json"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _outcome(body):
    return SimpleNamespace(
        result_status=body["result_status"],
        result_reason=body["result_reason"],
        route=body["route"],
        metadata=body["result"]["metadata"],
        result=SimpleNamespace(to_dict=lambda: body["result"]),
    )


def _readiness(http, body):
    assert http == 503
    assert body["ready"] is False and body["immutable_generation"] is True
    assert body["active_generation"] == BASE
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
            assert row["Team"] == "MIAHeat"
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
        assert row["Team"] == "GSWGolden State Warriors"
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
        assert len(shown) == 1 and shown[0]["Team"] == "LALLos Angeles Lakers"
        assert shown[0]["W-L"] == f"{case['wins']}-{case['losses']}"
        assert int(shown[0]["Games"]) == case["games"]
        assert float(shown[0]["PPG"]) == pytest.approx(case["means"]["pts"], abs=0.051)


def _run(tmp_path, *, retained=False):
    binding = json.loads((EVIDENCE / "live-code-binding.json").read_bytes())
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
    for path, digest in binding["application_file_sha256"].items():
        assert _sha((ROOT / path).read_bytes()) == digest
    for path, digest in binding["reused_evidence_sha256"].items():
        assert _sha((ROOT / path).read_bytes()) == digest
    with data_generation_context() as generation:
        assert (
            generation == BASE
            and _sha(data_path("metadata/generation_manifest.json").read_bytes()) == MANIFEST
        )
        cases, delivery, sources, frozen, seq_sources, history_sources, lebron, s4 = _cases()
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
            assert entries[path]["sha256"] == digest
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core-historical-live"
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "cases.json"
    inputs.write_text(json.dumps(cases) + "\n")
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
        generation=BASE,
        manifest_sha256=MANIFEST,
        full_core1_accepted=False,
        current_season_accepted=False,
        operational_readiness_accepted=False,
        nba_source_requests=0,
        k05_sample_keys_scope="qualified independent raw cohort; public summary does not expose game_log",
        production_writes=0,
        consumer_acceptance="pending",
        capture_started_at=datetime.now(UTC).isoformat(),
        deployment_post_binding="pending independent provider observation after capture",
    )
    try:
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
                    URL,
                ],
                env=env,
                check=True,
                timeout=900,
            )
        actual = json.loads((output / "browser-receipt.json").read_bytes())
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
        assets = None
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
            assert _sha((output / item["screenshot"]).read_bytes()) == item["screenshotSha256"]
            assets = item["assets"] if assets is None else assets
            assert (
                item["assets"] == assets
                and len(assets) == 1
                and assets[0].startswith(URL + "/assets/index-")
            )
            _readiness(item["readinessHttpBefore"], item["readinessBefore"])
            _readiness(item["readinessHttpAfter"], item["readinessAfter"])
            assert item["freshness"]["current_through"] == "2026-06-13"
            assert item["freshness"]["status"] == "stale"
            assert "Data through 2026-06-13" in item["freshnessText"]
            assert "awaiting refresh" in item["freshnessText"].lower()
            _verify(item, delivery, sources, frozen, seq_sources, history_sources, lebron)
        asset_hashes = [item["servedAssetSha256"] for item in actual["receipts"]]
        assert len(set(asset_hashes)) == 1
        assert _sha((output / "served-application.js").read_bytes()) == asset_hashes[0]
        assert seen == {(viewport, c["id"]) for viewport in ("desktop", "mobile") for c in cases}
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
                URL + "/query", json={"query": question}, timeout=30, allow_redirects=False
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
    except Exception as exc:
        receipt.update(
            consumer_acceptance="failed", failure=dict(type=type(exc).__name__, message=str(exc))
        )
        raise
    finally:
        receipt["capture_completed_at"] = datetime.now(UTC).isoformat()
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")


def test_original_historical_consumers_through_live_api_and_ui(tmp_path):
    _run(tmp_path)


def test_requalify_retained_actual_historical_api_and_ui(tmp_path):
    _run(tmp_path, retained=True)
