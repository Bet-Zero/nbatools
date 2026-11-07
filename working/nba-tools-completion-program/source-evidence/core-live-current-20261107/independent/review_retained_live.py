"""Read-only independent retained-capture review; no application/source requests."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from tests import cloud_core_historical_delivery_real_data as harness
from tests.test_k11_population_real_data import _assert_rows
from tests.test_k12_delivery_real_data import _bindings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = HERE.parent


def document(name):
    return json.loads((PROGRAM / name).read_bytes())


bindings = {
    key.lower(): value for key, value in _bindings(document("k12-delivery-oracle.json")).items()
}
sequence = next(c for c in document("k09-raw-oracle.json")["cases"] if c["id"] == "K09-T1")
history = next(c for c in document("k10-raw-oracle.json")["cases"] if c["id"] == "K10-G1")
s4 = json.loads(harness.S4.read_bytes())
lebron = json.loads(harness.LEBRON.read_bytes())
owned = json.loads(harness.OWNED.read_bytes())
frozen = {"live-k05": ("ownership", harness.K05[0])}
frozen.update({f"live-s4-{c['kind']}-{c['relation']}": ("s4", c) for c in s4["s4_integration"]})
for owner, expression, name in [
    (
        "team", "(over 37 points or over 10 assists) with at least 125 team points",
        "native_team_owned",
    ),
    (
        "opponent",
        "(over 37 points or over 10 assists) when opponents scored under 110 points",
        "native_opponent_owned",
    ),
]:
    frozen["live-owned-" + owner] = (
        "owned",
        dict(owned["cases"][name], query=f"How many distinct players had {expression} in 2022-23?"),
    )

archive = EVIDENCE / "historical-live-original.zip"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
    "a5c718c7498f24d787866ff4e3d53220363e00588a045607e92f5947ac2074a5"
)
with TemporaryDirectory(prefix="nbatools-checker-live-") as temporary:
    root = Path(temporary)
    with ZipFile(archive) as zipped:
        for member in zipped.namelist():
            path = Path(member)
            assert not path.is_absolute() and ".." not in path.parts
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(member))
    output = root / "acquired_data/core-historical-live"
    browser = json.loads((output / "browser-receipt.json").read_bytes())
    acceptance = json.loads((output / "acceptance.json").read_bytes())
    assert acceptance["consumer_acceptance"] == "failed"
    cases = {c["id"]: c for c in json.loads((output / "cases.json").read_bytes())}
    assert len(cases) == 22 and len(browser["receipts"]) == 44
    seen, assets, checked = set(), set(), []
    for item in browser["receipts"]:
        ident = item["id"]
        key = item["viewport"], ident
        assert key not in seen
        seen.add(key)
        assert item["query"] == item["payload"]["query"] == cases[ident]["query"]
        assert not any(item[field] for field in ("errors", "forbidden", "grainErrors"))
        assert item["missing"] == (["Lakers"] if ident.startswith("live-s4-") else [])
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest() == (
            item["screenshotSha256"]
        )
        assets.add(tuple(item["assets"]))
        assert hashlib.sha256((output / "served-application.js").read_bytes()).hexdigest() == (
            item["servedAssetSha256"]
        )
        harness._readiness(item["readinessHttpBefore"], item["readinessBefore"])
        harness._readiness(item["readinessHttpAfter"], item["readinessAfter"])
        assert item["freshness"]["current_through"] == "2026-06-13"
        assert item["freshness"]["status"] == "stale"
        if ident == "k12-l1":
            case = bindings[ident]
            body = item["payload"]["result"]
            original = case["original"]
            _assert_rows(
                body["sections"]["finder"],
                original["expected"]["rows"],
                original["metric"],
                boundary_rows=original["expected"]["boundary_rows"],
                date_tiebreak=original["date_tiebreak"],
            )
            harness._assert_rendered(item, case)
        elif ident == "live-k09":
            row = item["payload"]["result"]["sections"]["streak"][0]
            truth = sequence["expected"]
            assert row["games"] == row["streak_length"] == row["wins"] == truth["games"]
            assert row["losses"] == 0 and row["team_name"] == "Miami Heat"
            assert row["start_date"] == truth["start_date"]
            assert row["end_date"] == truth["end_date"]
            assert [row["start_game_id"], row["end_game_id"]] == [
                int(truth["game_ids"][0]), int(truth["game_ids"][-1])
            ]
            assert item["heroText"] == "The Heat won 27 straight games from Feb 3 to Mar 25, 2013."
            shown = harness._shown(item, "Streaks")[0]
            assert shown["Team"] == "MIAHeat" and shown["Length"] == "27 games"
            assert shown["Record"] == "27-0" and shown["Streak"] == "Wins"
        elif ident == "live-k05":
            body = item["payload"]["result"]
            case = harness.K05[0]
            row = body["sections"]["summary"][0]
            for field in ("games", "wins", "losses"):
                assert row[field] == case[field]
            for stat, value in case["means"].items():
                assert row[stat + "_avg"] == harness.pytest.approx(value, abs=0.001)
            assert body["metadata"]["team"] == "LAL"
            assert body["metadata"]["team_context"]["team_id"] == 1610612747
            assert body["metadata"]["season"] == "2023-24"
            phrase = "The Los Angeles Lakers are 8-0 in the 2023-24 regular season"
            assert phrase in item["heroText"]
            for label in ("Home", "110+ PTS", "Opp PTS < 110"):
                assert label in item["text"]
            shown = harness._shown(item, "Team record")[0]
            assert shown["W-L"] == "8-0" and int(shown["Games"]) == 8
            assert float(shown["PPG"]) == harness.pytest.approx(case["means"]["pts"], abs=0.051)
        elif ident == "live-k10":
            body = item["payload"]["result"]
            assert body["metadata"]["team_context"]["team_id"] == history["team_id"]
            row = body["sections"]["summary"][0]
            assert [row[k] for k in ("games", "wins", "losses")] == [24, 15, 9]
            shown = harness._shown(item, "Team record")[0]
            assert shown["Team"] == "GSWGolden State Warriors" and shown["W-L"] == "15-9"
            assert "The Golden State Warriors are 15-9 in the 2015-16 playoffs" in item["heroText"]
        else:
            harness._verify(item, bindings, {}, frozen, {}, {}, lebron)
        checked.append(dict(viewport=key[0], id=ident, matched=True))
    assert seen == {(view, ident) for view in ("desktop", "mobile") for ident in cases}
    assert len(assets) == 1
    post = json.loads((EVIDENCE / "vercel-production-post-capture.json").read_bytes())
    deployment = json.loads(post["response"]["content"][0]["text"])["result"]["deployment"]
    assert deployment["id"] == acceptance["deployment_binding"]["production_deployment"]["id"]
    assert deployment["meta"]["githubCommitSha"] == "a0fb2211a6707d647325129f1262308545001241"
    assert deployment["state"] == "READY" and "nbatools.vercel.app" in deployment["alias"]
    assert datetime.fromisoformat(post["checked_at"].replace("Z", "+00:00")) > (
        datetime.fromisoformat(acceptance["capture_completed_at"])
    )
(HERE / "retained-live-independent-review.json").write_text(json.dumps(dict(
    actual_captures=44,
    frozen_case_pairs=checked,
    original_run_failed=True,
    classification=(
        "Independent retained actual capture review against existing qualified frozen oracles; "
        "K05/K12L1/K09/K10 source-body hash replay remains required on canonical runner"
    ),
    post_provider_same_deployment=True,
    full_core1_accepted=False,
    current_season_accepted=False,
), indent=2) + "\n")
print("All44 actual payload/rendered pairs match frozen scope; canonical source replay pending")
