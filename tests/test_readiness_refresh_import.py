"""Single returned ZIP ingestion preserves originals and cannot bypass bounds."""

import hashlib
import io
import json
import stat
import struct
import warnings
import zipfile

import pytest

from tests.test_collect_rollover_readiness_laptop import fake_client, request
from tools import collect_rollover_readiness_laptop as collector
from tools.readiness_refresh import SourceCache, git_blob

SEED = "a" * 64
STAMP = "20261104T052000000000Z"
RECEIPT = f"runs/{STAMP}/receipt.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def zipped(files):
    buffer = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        warnings.simplefilter("ignore", UserWarning)
        for name, raw in files:
            z.writestr(name, raw)
    return buffer.getvalue()


def run_files(tmp_path, monkeypatch, *, failure=False, two_batches=False):
    calls, _ = fake_client(monkeypatch, [b'{"original":true}'] * 4, "403" if failure else None)
    plan = request()
    output = tmp_path / "batch"
    report = collector.collect(output, plan)
    request_sha = collector.validate_request(plan)
    files = [(f"batches/{request_sha}/collection.zip", (output / "collection.zip").read_bytes())]
    jobs = list(plan["jobs"])
    if two_batches:
        plan2 = request()
        for job in plan2["jobs"]:
            job["parameters"].update(StartPeriod=2, EndPeriod=2)
            job["source_file"] = job["source_file"].replace("q1", "q2")
        output2 = tmp_path / "batch2"
        collector.collect(output2, plan2)
        files.append(
            (
                f"batches/{collector.validate_request(plan2)}/collection.zip",
                (output2 / "collection.zip").read_bytes(),
            )
        )
        jobs.extend(plan2["jobs"])
    receipt = {
        "classification": "unvalidated_acquisition_only",
        "seed_sha256": SEED,
        "production_writes": 0,
        "statistical_acceptance": False,
        "lag_hours": 24,
        "state": "failed_preserve_output_do_not_retry" if failure else "transport_complete",
        "archive_requests": 0,
        "archive_bytes": 0,
        "jobs": jobs,
    }
    state = {"seed_sha256": SEED, "production_writes": 0, "blocked": failure, "blocked_files": []}
    files.extend(
        [(RECEIPT, json.dumps(receipt).encode()), ("state.json", json.dumps(state).encode())]
    )
    return files, calls, output, report


def import_files(cache, tmp_path, files, *, seed=SEED):
    payload = zipped(files)
    archive = tmp_path / "returned.zip"
    archive.write_bytes(payload)
    return cache.import_run(archive, digest(payload), seed)


def test_nested_success_originals_are_preserved_idempotent_and_replayable(tmp_path, monkeypatch):
    files, calls, _, _ = run_files(tmp_path, monkeypatch)
    raw = b'{"archive_original":true}'
    files.append((f"archive/{git_blob(raw)}.json", raw))
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    assert result["successful_sources"] == 2 and len(calls) == 2
    assert result["production_writes"] == 0
    assert result["classification"] == "authenticated_run_transport_not_statistical_acceptance"
    assert cache.data["mirror"] == {}
    preserved = tmp_path / "cache/run-imports" / (result["outer_sha256"] + ".zip")
    assert preserved.read_bytes() == (tmp_path / "returned.zip").read_bytes()
    assert cache.read(result["archive_originals"][0]) == raw
    restored = SourceCache(tmp_path / "cache")
    assert restored.import_run(preserved, result["outer_sha256"], SEED) == result
    assert len(restored.data["direct"]) == 2
    nested = result["nested_collections"][0]
    assert digest(open(nested["original_path"], "rb").read()) == nested["sha256"]
    with pytest.raises(ValueError, match="another reviewed seed"):
        restored.import_run(preserved, result["outer_sha256"], "b" * 64)


@pytest.mark.parametrize(
    "bad_name",
    [
        "../escape.json",
        "/absolute.json",
        "runs//x.json",
        "runs/./x.json",
        "runs/x/../x.json",
        "runs\\x.json",
        "C:escape.json",
        "runs/x\x00.json",
    ],
)
def test_outer_paths_are_rejected_before_cache_mutation(tmp_path, monkeypatch, bad_name):
    files, _, _, _ = run_files(tmp_path, monkeypatch)
    # zipfile truncates NUL names; that truncated unexpected member also rejects.
    files.append((bad_name, b"{}"))
    cache = SourceCache(tmp_path / "cache")
    with pytest.raises(ValueError):
        import_files(cache, tmp_path, files)
    assert not cache.path.exists() and not list(cache.objects.iterdir())


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "symlink",
        "two_receipts",
        "wrong_seed",
        "wrong_outer",
        "missing_state",
        "wrong_batch_hash",
    ],
)
def test_outer_identity_structure_and_seed_fail_closed(tmp_path, monkeypatch, damage):
    files, _, _, _ = run_files(tmp_path, monkeypatch)
    cache = SourceCache(tmp_path / "cache")
    if damage == "duplicate":
        files.append(files[-1])
    elif damage == "symlink":
        link = zipfile.ZipInfo("archive/" + "b" * 40 + ".json")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        files.append((link, b"/tmp/elsewhere"))
    elif damage == "two_receipts":
        files.append((RECEIPT.replace("052000", "052001"), files[-2][1]))
    elif damage == "wrong_seed":
        files[-1] = (
            "state.json",
            json.dumps({"seed_sha256": "b" * 64, "production_writes": 0}).encode(),
        )
    elif damage == "missing_state":
        files = files[:-1]
    elif damage == "wrong_batch_hash":
        files[0] = ("batches/" + "f" * 64 + "/collection.zip", files[0][1])
    if damage == "wrong_outer":
        payload = zipped(files)
        path = tmp_path / "returned.zip"
        path.write_bytes(payload)
        with pytest.raises(ValueError, match="expected SHA256"):
            cache.import_run(path, "f" * 64, SEED)
    else:
        with pytest.raises(ValueError):
            import_files(cache, tmp_path, files)
    assert not cache.path.exists() and not list(cache.objects.iterdir())


def test_corrupt_second_nested_capture_cannot_admit_first_batch(tmp_path, monkeypatch):
    files, _, _, _ = run_files(tmp_path, monkeypatch, two_batches=True)
    with zipfile.ZipFile(io.BytesIO(files[1][1])) as z:
        contents = [(name, z.read(name)) for name in z.namelist()]
    contents = [
        (name, b'{"changed":true}' if name.endswith("_q2.json") else raw) for name, raw in contents
    ]
    files[1] = (files[1][0], zipped(contents))
    cache = SourceCache(tmp_path / "cache")
    with pytest.raises(ValueError, match="size|checksum"):
        import_files(cache, tmp_path, files)
    assert cache.data["direct"] == {} and not cache.path.exists()
    assert not (tmp_path / "cache/run-imports").exists()
    assert not list(cache.objects.iterdir())


def test_failed_original_and_partial_archive_are_quarantined_without_retries(tmp_path, monkeypatch):
    files, calls, _, _ = run_files(tmp_path, monkeypatch, failure=True)
    name = "archive/" + "b" * 40 + ".json"
    state = json.loads(files[-1][1])
    state["blocked_files"] = [name]
    files[-1] = ("state.json", json.dumps(state).encode())
    files.append((name, b"partial original"))
    files.append((f"runs/{STAMP}/metadata/00.json", b"original failed metadata body"))
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    assert result["failed_or_interrupted"] is True
    assert result["successful_sources"] == 1 and len(cache.data["direct"]) == 1
    assert result["archive_originals"][0]["git_blob_matches"] is False
    assert result["archive_originals"][0]["classification"] == "quarantined_partial_original"
    assert cache.read(result["archive_originals"][0]) == b"partial original"
    assert cache.data["mirror"] == {}
    assert import_files(cache, tmp_path, files) == result
    assert len(calls) == 2


def test_successful_run_cannot_hide_invalid_archive_blob(tmp_path, monkeypatch):
    files, _, _, _ = run_files(tmp_path, monkeypatch)
    files.append(("archive/" + "b" * 40 + ".json", b"changed original"))
    cache = SourceCache(tmp_path / "cache")
    with pytest.raises(ValueError, match="Git blob"):
        import_files(cache, tmp_path, files)
    assert not cache.path.exists() and not list(cache.objects.iterdir())


def test_interrupted_loose_batch_is_retained_but_not_admitted(tmp_path, monkeypatch):
    files, _, output, _ = run_files(tmp_path, monkeypatch, failure=True)
    prefix = files[0][0].removesuffix("collection.zip")
    files = files[1:]
    receipt = json.loads(files[0][1])
    receipt["jobs"] = []  # Relaunch blocked before a new collection was attempted.
    files[0] = (RECEIPT, json.dumps(receipt).encode())
    for path in output.rglob("*.json"):
        files.append((prefix + path.relative_to(output).as_posix(), path.read_bytes()))
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    assert result["successful_sources"] == 0 and cache.data["direct"] == {}
    assert any(name.endswith("_q1.json") for name in result["loose_failed_files"])
    assert result["failed_or_interrupted"] is True


def test_header_expansion_and_entry_caps_apply_before_reading_payload(tmp_path):
    payload = bytearray(zipped([("state.json", b"{}")]))
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<I", payload, central + 24, 100_000_001)
    path = tmp_path / "bomb.zip"
    path.write_bytes(payload)
    cache = SourceCache(tmp_path / "cache")
    with pytest.raises(ValueError, match="expanded/entry"):
        cache.import_run(path, digest(payload), SEED)
    with path.open("wb") as handle:
        handle.seek(20_000_000)
        handle.write(b"x")
    with pytest.raises(ValueError, match="bounded regular-file"):
        cache.import_run(path, "f" * 64, SEED)
    payload = zipped([(str(n) + ".json", b"{}") for n in range(2001)])
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="expanded/entry"):
        cache.import_run(path, digest(payload), SEED)
    assert not cache.path.exists() and not list(cache.objects.iterdir())


def test_nested_501_request_plan_cannot_bypass_runtime_500_cap(tmp_path, monkeypatch):
    files, _, _, _ = run_files(tmp_path, monkeypatch)
    plan = request()
    plan["jobs"] = []
    for n in range(1, 502):
        job = request()["jobs"][0]
        gid = "00226" + str(n).zfill(5)
        job["parameters"]["GameID"] = gid
        job["source_file"] = f"sources/boxscoretraditionalv3_{gid}_q1.json"
        plan["jobs"].append(job)
    plan["maximum_requests"] = 501
    request_sha = collector.validate_request(plan)  # Existing fixed protocol allows1200.
    inner = zipped(
        [
            ("collection-manifest.json", json.dumps({"request": plan}).encode()),
            ("acquisition.json", b"{}"),
        ]
    )
    files[0] = (f"batches/{request_sha}/collection.zip", inner)
    cache = SourceCache(tmp_path / "cache")
    with pytest.raises(ValueError, match="bounds differ"):
        import_files(cache, tmp_path, files)
    assert not cache.path.exists() and not list(cache.objects.iterdir())


def test_preserved_outer_corruption_is_detected_before_reentry(tmp_path, monkeypatch):
    files, _, _, _ = run_files(tmp_path, monkeypatch)
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    path = tmp_path / "cache/run-imports" / (result["outer_sha256"] + ".zip")
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Preserved returned run ZIP changed"):
        SourceCache(tmp_path / "cache")


def test_failed_nested_identity_survives_reentry_and_blocks_replanning(tmp_path, monkeypatch):
    from tools.readiness_refresh import direct_delta, identity

    files, calls, _, report = run_files(tmp_path, monkeypatch, failure=True)
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    failed = report["attempts"][-1]["job"]
    key = identity(failed)
    assert set(cache.unresolved_direct_attempts()) == {key}
    assert key in result["blocked_direct_attempts"]
    restored = SourceCache(tmp_path / "cache")
    assert set(restored.unresolved_direct_attempts()) == {key}
    with pytest.raises(ValueError, match="explicit cloud diagnosis"):
        direct_delta(restored, ["0022600001"], period_counts={"0022600001": 4})
    # Reimporting evidence neither authorizes nor attempts a retry.
    assert import_files(restored, tmp_path, files) == result
    assert len(calls) == 2
    assert len(restored.data["direct_attempts"][key]["failures"]) == 1


def test_plain_collection_failed_identity_blocks_stale_fixed_package(tmp_path, monkeypatch):
    from tools import readiness_refresh as refresh

    _, calls, output, report = run_files(tmp_path, monkeypatch, failure=True)
    cache = SourceCache(tmp_path / "cache")
    raw = (output / "collection.zip").read_bytes()
    cache.import_collection(output / "collection.zip", digest(raw))
    failed = report["attempts"][-1]["job"]
    key = refresh.identity(failed)
    assert key in SourceCache(tmp_path / "cache").unresolved_direct_attempts()
    stale = tmp_path / "stale-plan.json"
    stale.write_text(json.dumps({"direct": {"jobs": [failed]}}))
    target = tmp_path / "must-not-build.zip"
    monkeypatch.setattr(
        "sys.argv",
        [
            "readiness_refresh",
            "--cache",
            str(cache.root),
            "package",
            str(stale),
            "--base-generation",
            "base",
            "--base-manifest-sha256",
            "a" * 64,
            "--output",
            str(target),
        ],
    )
    with pytest.raises(ValueError, match="explicit cloud diagnosis"):
        refresh.main()
    assert not target.exists() and len(calls) == 2


def test_loose_interrupted_attempt_identities_survive_cloud_import(tmp_path, monkeypatch):
    from tools.readiness_refresh import identity

    files, _, output, report = run_files(tmp_path, monkeypatch, failure=True)
    prefix = files[0][0].removesuffix("collection.zip")
    files = files[1:]
    receipt = json.loads(files[0][1])
    receipt["jobs"] = []
    files[0] = (RECEIPT, json.dumps(receipt).encode())
    # Model a killed process: intent was written, final response bookkeeping was not.
    interrupted = report["attempts"][-1]
    for key in ("transport_complete", "finished_at", "http_status", "error_type"):
        interrupted.pop(key, None)
    for path in output.rglob("*.json"):
        raw = path.read_bytes()
        if path.name in {"acquisition.json", "capture-attempt.json"}:
            raw = json.dumps(report).encode()
        files.append((prefix + path.relative_to(output).as_posix(), raw))
    cache = SourceCache(tmp_path / "cache")
    import_files(cache, tmp_path, files)
    restored = SourceCache(tmp_path / "cache")
    assert identity(interrupted["job"]) in restored.unresolved_direct_attempts()
    # Loose completed originals are not silently recollected either.
    assert identity(report["attempts"][0]["job"]) in restored.unresolved_direct_attempts()
    assert restored.data["direct"] == {}


def test_reimport_migrates_pre_fix_run_that_dropped_attempt_blocks(tmp_path, monkeypatch):
    from tools.readiness_refresh import identity

    files, _, _, report = run_files(tmp_path, monkeypatch, failure=True)
    cache = SourceCache(tmp_path / "cache")
    result = import_files(cache, tmp_path, files)
    cache.data["direct_attempts"] = {}
    cache.data["runs"][result["outer_sha256"]]["direct_attempt_tracking"] = True
    cache.save()
    restored = SourceCache(tmp_path / "cache")
    assert restored.unresolved_direct_attempts() == {}
    migrated = import_files(restored, tmp_path, files)
    assert identity(report["attempts"][-1]["job"]) in restored.unresolved_direct_attempts()
    assert migrated["direct_attempt_tracking"] == 2
