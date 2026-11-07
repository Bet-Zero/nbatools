"""Independent frozen-source ID18 consumer/provenance review; no acquisition."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from nbatools.api_handlers import natural_query_payload, structured_query_payload
from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline import reported_absence_reasons as producer
from nbatools.commands.pipeline.structured_participation import validate_structured_import
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_output_snapshot import build_query_ui_snapshot

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
E = OUT.parent
OLD = E.parent / "core-live-current-20261107"
CANDIDATE = "50630401"
SUFFIX = "2026-27_regular_season.csv"


def check_empty(body, expected, digest, *, count=False):
    assert body["result_reason"] != "no_data", body
    if count:
        assert body["result_status"] == "ok", body
        assert body["result"]["sections"]["count"] == [{"count": 0}], body
    else:
        assert (body["result_status"], body["result_reason"]) == ("no_result", "no_match"), body
        assert body["result"]["sections"] == {}, body
    meta = body["result"]["metadata"]
    assert meta["season"] == "2026-27", meta
    canonical_name = "".join(
        c
        for c in unicodedata.normalize("NFKD", meta["without_player"])
        if not unicodedata.combining(c)
    )
    assert canonical_name == "Luka Doncic", meta
    assert meta["without_player_reason"] == "reported_rest", meta
    assert meta["data_quality"]["manifest_sha256"] == digest
    assert meta["data_quality"]["state"] == "provisional"
    assert not meta["data_quality"]["production_accepted"]
    assert not meta["data_quality"]["numerical_acceptance"]
    assert {
        "label": "Reported absence reason",
        "value": "officially reported Rest",
        "kind": "reported_reason",
    } in meta["applied_filters"]
    notes = " ".join(body["notes"])
    assert "0 Rest, 1 reported other, 0 unknown" in notes
    assert "in 9 selected games" in notes
    assert "clinical or healthy status" in notes
    assert "PROVISIONAL" in notes
    view = build_query_ui_snapshot(body)
    assert "PROVISIONAL" in str(view)
    if count:
        assert "officially reported Rest" in str(view)
    else:
        # This existing Python snapshot emits a generic no-result block; the
        # actual React NoResultDisplay receives the separately asserted notes.
        assert view["status"]["result_reason"] == "no_match"
    return view


def main():
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", CANDIDATE], cwd=ROOT, text=True
    ).strip()
    assert (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        == candidate_sha
    )
    os.environ["DATA_SOURCE"] = "local"
    frozen = json.loads((OUT / "id18-expectation-freeze.json").read_bytes())
    assert (
        sha256((OUT / "id18-expectation-freeze.json").read_bytes())
        == "99606e19dcac707915c3d29b2fd70982724062c4a5b2660a8fce7f698405251a"
    )
    binding = json.loads((E / "binding.json").read_bytes())
    assert sha256((E / binding["archive"]).read_bytes()) == binding["archive_sha256"]
    digest = binding["manifest_sha256"]
    result = dict(
        reviewer="/root/id18_checker",
        backend_model="unavailable",
        candidate_sha=candidate_sha,
        source_oracle_sha256=sha256((OUT / "id18-expectation-freeze.json").read_bytes()),
        snapshot_manifest_sha256=digest,
        snapshot_archive_sha256=binding["archive_sha256"],
        production_writes=0,
        source_requests=0,
        natural=[],
        structured=[],
        http=[],
        controls={},
        guards={},
    )
    work_base = ROOT / "work"
    work_base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="id18-independent-", dir=work_base) as temp:
        work = Path(temp)
        current, old = work / "current", work / "old"
        for archive, destination in [
            (E / binding["archive"], current),
            (OLD / "current123-provisional.zip", old),
        ]:
            with ZipFile(archive) as z:
                assert len(z.namelist()) == len(set(z.namelist()))
                assert all(
                    not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist()
                )
                z.extractall(destination)
        DevelopmentSnapshot(current, digest)
        old_digest = sha256((old / MANIFEST).read_bytes())
        unchanged = []
        for file in (old / "data").rglob("*"):
            if file.is_file() and file.relative_to(old) != MANIFEST:
                assert (current / file.relative_to(old)).read_bytes() == file.read_bytes()
                unchanged.append(file.relative_to(old).as_posix())
        result["unchanged_old_files"] = unchanged
        assert not (current / "data/metadata/generation_manifest.json").exists()
        producer.validate_publication(current / "data")
        avail = pd.read_csv(current / f"data/raw/player_game_availability/{SUFFIX}")
        imports = json.loads(
            (current / f"data/raw/player_game_availability/{SUFFIX[:-4]}.imports.json").read_bytes()
        )
        validate_structured_import(
            current / "data", 22600143, avail.loc[avail.game_id.eq(22600143)], imports["22600143"]
        )
        result["original_reason_and_structured_replay"] = "passed"
        # A separate identity packet and explicit PDF reason are preserved; the
        # source facts are never recast as clinical or generic absence evidence.
        with development_snapshot(current, digest):
            observed = reasons.load_observations(["2026-27"], "Regular Season")
            assert len(observed) == 1
            row = observed.iloc[0]
            assert row.player_id == 1629029 and row.team_id == 1610612747
            assert row.game_id == 22600143 and row.reported_reason == frozen["reason_state"]
            assert row.reason_text == frozen["reason_literal"]
            assert row.source_sha256 == frozen["original_pdf_sha256"]
            parent = pd.read_csv(current / f"data/raw/team_game_stats/{SUFFIX}")
            parent = parent.loc[parent.team_id.eq(1610612747)]
            assert set(parent.game_id.astype(str).str.zfill(10)) == set(frozen["parent_game_ids"])
            coverage = {}
            assert reasons.filter_reported_rest(
                parent, "Luka Doncic", ["2026-27"], "Regular Season", evidence=coverage
            ).empty
            assert coverage == frozen["coverage"]
            result["complete_parent_coverage"] = coverage
            queries = [frozen["expected_original_id18"]["query"], *frozen["heldout_queries"]]
            for query in queries:
                body = natural_query_payload(query)
                view = check_empty(body, frozen, digest, count=query.startswith("How many"))
                result["natural"].append(dict(query=query, payload=body, visible_output=view))
            for route in frozen["affected_routes"]:
                kwargs = dict(
                    team="LAL",
                    season="2026-27",
                    without_player="Luka Doncic",
                    without_player_reason="reported_rest",
                )
                if route.startswith("player"):
                    kwargs["player"] = "Austin Reaves"
                body = structured_query_payload(route, kwargs)
                view = check_empty(body, frozen, digest)
                result["structured"].append(
                    dict(route=route, kwargs=kwargs, payload=body, visible_output=view)
                )
            for key, query in [
                ("without", "Lakers record when Luka Doncic sits this season"),
                ("with", "Lakers record with Luka Doncic playing this season"),
            ]:
                body = natural_query_payload(query)
                expected = frozen["control_expectations"][key]
                assert body["result_status"] == "ok", body
                rows = body["result"]["sections"]["game_log"]
                assert {str(int(r["game_id"])).zfill(10) for r in rows} == set(expected["game_ids"])
                summary = body["result"]["sections"]["summary"][0]
                assert (summary["games"], summary["wins"], summary["losses"]) == (
                    expected["games"],
                    expected["wins"],
                    expected["losses"],
                )
                assert sum(r["pts"] for r in rows) == expected["points_sum"]
                result["controls"][key] = dict(query=query, payload=body)
        query = frozen["expected_original_id18"]["query"]
        with development_snapshot(old, old_digest):
            assert natural_query_payload(query)["result_reason"] == "no_data"
            with development_snapshot(current, digest):
                assert natural_query_payload(query)["result_reason"] == "no_match"
            assert natural_query_payload(query)["result_reason"] == "no_data"
        result["guards"]["old_version_reader_pinned_across_new_reader"] = "passed"
        # Actual TCP HTTP server rather than merely comparing internal calls.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ)
        command = [
            sys.executable,
            "-m",
            "tools.development_query",
            "--snapshot",
            str(current),
            "--manifest-sha256",
            digest,
            "--serve",
            "--port",
            str(port),
        ]
        with (work / "server.log").open("w") as log:
            server = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 25
                while True:
                    try:
                        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).close()
                        break
                    except urllib.error.URLError:
                        if server.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError((work / "server.log").read_text())
                        time.sleep(0.1)
                for query in queries:
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{port}/query",
                        data=json.dumps({"query": query}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(request, timeout=15) as response:
                        assert response.status == 200
                        body = json.load(response)
                    view = check_empty(body, frozen, digest, count=query.startswith("How many"))
                    result["http"].append(dict(query=query, payload=body, visible_output=view))
            finally:
                server.terminate()
                server.wait(timeout=10)
        for variable in ("ENVIRONMENT", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME"):
            previous = os.environ.get(variable)
            os.environ[variable] = "production"
            try:
                try:
                    DevelopmentSnapshot(current, digest)
                except ValueError as exc:
                    assert "isolated local development" in str(exc)
                else:
                    raise AssertionError(variable)
            finally:
                if previous is None:
                    os.environ.pop(variable)
                else:
                    os.environ[variable] = previous
        result["guards"]["production_selection_rejected"] = "passed"
        # Remanifesting transport hashes cannot make a mismatched import digest
        # or removed table satisfy qualified source identity.
        for kind in ("source", "import", "reason_missing"):
            corrupt = work / ("corrupt-" + kind)
            shutil.copytree(current, corrupt)
            doc = json.loads((corrupt / MANIFEST).read_bytes())
            if kind == "source":
                target = next(
                    (corrupt / "data/raw/player_game_absence_reason_sources").glob("*.pdf")
                )
                target.write_bytes(b"%PDF synthetic corruption; not source evidence")
            elif kind == "import":
                target = corrupt / f"data/raw/player_game_availability/{SUFFIX[:-4]}.imports.json"
                value = json.loads(target.read_bytes())
                value["22600143"]["sha256"] = "0" * 64
                target.write_text(json.dumps(value))
            else:
                target = corrupt / f"data/raw/player_game_absence_reasons/{SUFFIX}"
                target.unlink()
            relative = target.relative_to(corrupt).as_posix()
            if target.exists():
                doc["files"][relative] = sha256(target.read_bytes())
            else:
                doc["files"].pop(relative)
            (corrupt / MANIFEST).write_text(json.dumps(doc))
            clear_frame_cache()
            with development_snapshot(corrupt, sha256((corrupt / MANIFEST).read_bytes())):
                assert natural_query_payload(query)["result_reason"] == "no_data"
            result["guards"][kind] = "no_data_rejected_not_qualified_empty"
        normalize = producer.report._name
        names = {normalize("Luka Doncic"), normalize("Doncic")}
        selected = producer.report._split_inactives(
            "Unrelated Name, Dončić (Injury/Illness - Other; Back Tightness)",
            reason_target_names=names,
        )
        assert selected == [("Dončić", "INACTIVE - Injury/Illness - Other; Back Tightness")]
        for literal, target_names in [
            ("Unrelated Name, Dončić", names),
            ("Unrelated Name, Dončić (Rest)", None),
            ("Unrelated Name7, Dončić (Rest)", names),
            ("Unrelated Name (, Dončić (Rest)", names),
        ]:
            try:
                producer.report._split_inactives(literal, reason_target_names=target_names)
            except ValueError:
                pass
            else:
                raise AssertionError((literal, target_names))
        result["guards"]["selected_bare_and_malformed_entries_and_whole_game_remain_strict"] = (
            "passed"
        )
        result["checks"] = dict(
            natural=4,
            structured=5,
            http_over_tcp=4,
            binary_controls=2,
            corruption_controls=3,
            full_parent_games=9,
            old_file_bytes_preserved=len(unchanged),
            source_replay="passed",
        )
        assert (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == candidate_sha
        )
        result["conclusion"] = "passed"
        (OUT / "candidate-execution.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n"
        )
        print(
            json.dumps(
                dict(candidate=CANDIDATE, checks=result["checks"], conclusion="passed"), indent=2
            )
        )


if __name__ == "__main__":
    main()
