"""Incremental transport planning is distinct from statistical acceptance."""

import hashlib
import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from tools.readiness_refresh import (
    SourceCache,
    direct_delta,
    due_population,
    git_blob,
    identity,
    mirror_delta,
    period_count,
    stage_mirror,
)


def schedule():
    return pd.DataFrame(
        [
            {
                "game_id": "0022600001",
                "game_date": "2026-11-02",
                "game_datetime": "2026-11-03T00:00:00Z",
            },
            {
                "game_id": "0022600002",
                "game_date": "2026-11-03",
                "game_datetime": "2026-11-04T00:00:01Z",
            },
        ]
    )


def games():
    return pd.DataFrame(columns=["game_id", "game_date", "is_final"])


def test_due_population_retains_exact_inclusive_24_hour_policy():
    first = due_population(schedule(), games(), datetime(2026, 11, 4, tzinfo=UTC))
    assert first["due_game_ids"] == ["0022600001"]
    later = due_population(schedule(), games(), datetime(2026, 11, 5, 0, 0, 1, tzinfo=UTC))
    assert later["due_game_ids"] == ["0022600001", "0022600002"]
    assert later["lag_hours"] == 24
    malformed = schedule()
    malformed.loc[0, "game_datetime"] = "2026-11-04T00:00:00Z"
    with pytest.raises(ValueError, match="unknown"):
        due_population(malformed, games(), datetime(2026, 11, 5, tzinfo=UTC))
    with pytest.raises(ValueError, match="timezone"):
        due_population(schedule(), games(), datetime(2026, 11, 5))


def test_incremental_periods_reuse_identity_not_filename_and_keep_unknown_ot(tmp_path):
    cache = SourceCache(tmp_path)
    initial = direct_delta(cache, ["0022600128"], period_counts={"0022600128": 5})
    assert len(initial["jobs"]) == 14
    old = initial["jobs"][0]
    cache.data["direct"][identity(old)] = {"job": {**old, "source_file": "renamed.json"}}
    changed = direct_delta(cache, ["0022600128"], period_counts={"0022600128": 5})
    assert len(changed["jobs"]) == 13
    assert old not in changed["jobs"]
    assert len([j for j in changed["jobs"] if j["parameters"]["StartPeriod"] == 5]) == 2
    unresolved = direct_delta(cache, ["0022600111"])
    assert len(unresolved["jobs"]) == 12
    assert unresolved["period_population_unresolved"] == ["0022600111"]
    assert unresolved["statistical_acceptance"] is False


def test_period_arrays_root_ambiguity_does_not_drop_overtime():
    box = {
        "gameId": "0022600111",
        "period": 5,
        "homeTeam": {"periods": [{"period": n} for n in range(1, 5)]},
        "awayTeam": {"periods": [{"period": n} for n in range(1, 5)]},
    }
    with pytest.raises(ValueError, match="ambiguous"):
        period_count({"boxScoreSummary": box}, "0022600111")
    box["period"] = 4
    assert period_count({"boxScoreSummary": box}, "0022600111") == 4
    with pytest.raises(ValueError, match="identity"):
        period_count({"boxScoreSummary": box}, "0022600128")


def inventory(raw=b'{"retained":true}'):
    path = "nba_stats/json/boxscoresummaryv3/2027/0022600001.json"
    return {
        "revision": "a" * 40,
        "entries": {"summaries": [{"path": path, "sha": git_blob(raw), "size": len(raw)}]},
    }, path


def test_archive_blob_reuse_survives_changed_revision_and_detects_corruption(tmp_path):
    cache = SourceCache(tmp_path)
    raw = b'{"retained":true}'
    index, path = inventory(raw)
    assert len(mirror_delta(cache, index, ["0022600001"])["jobs"]) == 1
    cache.import_mirror(raw, path=path, blob=git_blob(raw), revision="a" * 40, provenance={})
    index["revision"] = "b" * 40
    assert mirror_delta(cache, index, ["0022600001"])["jobs"] == []
    cache = SourceCache(tmp_path)
    (cache.objects / hashlib.sha256(raw).hexdigest()).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="changed"):
        SourceCache(tmp_path)


def test_staging_fails_fast_preserves_original_and_never_retries(tmp_path, monkeypatch):
    cache = SourceCache(tmp_path)
    index, _ = inventory()
    plan = mirror_delta(cache, index, ["0022600001"])
    calls = []

    def bad_fetch(path, destination, revision):
        calls.append(path)
        destination.write_bytes(b"bad")
        raise ValueError("diagnosed source failure")

    monkeypatch.setattr("tools.readiness_refresh.fetch_capture", bad_fetch)
    with pytest.raises(ValueError, match="diagnosed"):
        stage_mirror(cache, plan)
    assert len(calls) == 1
    assert next(tmp_path.glob("*.original")).read_bytes() == b"bad"
    with pytest.raises(ValueError, match="diagnosis"):
        stage_mirror(SourceCache(tmp_path), plan)
    assert len(calls) == 1
    assert json.loads((tmp_path / "ledger.json").read_bytes())["production_writes"] == 0


def test_staging_budget_and_pinned_blob_are_checked_before_acceptance(tmp_path, monkeypatch):
    cache = SourceCache(tmp_path)
    raw = b'{"retained":true}'
    index, _ = inventory(raw)
    plan = mirror_delta(cache, index, ["0022600001"])
    with pytest.raises(ValueError, match="finite"):
        stage_mirror(cache, plan, max_bytes=1)
    calls = []

    def fetch(path, destination, revision):
        calls.append(path)
        destination.write_bytes(raw)
        return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    monkeypatch.setattr("tools.readiness_refresh.fetch_capture", fetch)
    assert stage_mirror(cache, plan)["completed"] == 1
    assert stage_mirror(SourceCache(tmp_path), plan)["completed"] == 0
    assert len(calls) == 1


def portable_schedule(ids=("0022600001",), *, period=4):
    return {
        "leagueSchedule": {
            "seasonYear": "2026-27",
            "leagueId": "00",
            "gameDates": [
                {
                    "games": [
                        {
                            "gameId": gid,
                            "gameStatus": 3,
                            "gameDateEst": "2026-10-20T00:00:00Z",
                            "gameDateTimeUTC": "2026-10-21T00:00:00Z",
                        }
                        for gid in ids
                    ]
                }
            ],
        }
    }


def test_portable_due_policy_matches_canonical_including_future_games():
    from tools.readiness_refresh_laptop import schedule_due

    document = portable_schedule(("0022600001", "0022600002"))
    document["leagueSchedule"]["gameDates"][0]["games"][1].update(
        gameDateEst="2026-11-03T00:00:00Z", gameDateTimeUTC="2026-11-04T00:00:01Z"
    )
    now = datetime(2026, 11, 5, 0, 0, 1, tzinfo=UTC)
    canonical = pd.DataFrame(
        [
            {
                "game_id": g["gameId"],
                "game_date": g["gameDateEst"][:10],
                "game_datetime": g["gameDateTimeUTC"],
            }
            for g in document["leagueSchedule"]["gameDates"][0]["games"]
        ]
    )
    assert schedule_due(document, now) == due_population(canonical, games(), now)["due_game_ids"]
    document["leagueSchedule"]["gameDates"][0]["games"][0]["gameDateEst"] = "2026-10-21"
    with pytest.raises(ValueError, match="disagree"):
        schedule_due(document, now)


def runtime_seed(document):
    import base64

    raw = json.dumps(document).encode()
    return {
        "successes": {},
        "schedule": {"blob": git_blob(raw), "body_base64": base64.b64encode(raw).decode()},
        "summaries": {"0022600001": {"blob": "b" * 40, "periods": 4}},
        "base_generation": "preserved-base",
        "base_manifest_sha256": "c" * 64,
    }


def test_reusable_launcher_first_capture_reentry_and_evolving_due_population(tmp_path, monkeypatch):
    from tests.test_collect_rollover_readiness_laptop import fake_client
    from tools import readiness_refresh_laptop as runtime

    document = portable_schedule()
    seed = runtime_seed(document)
    summaries = {"0022600001.json": {"sha": "b" * 40}}

    def discover(self):
        return "a" * 40, {"sha": seed["schedule"]["blob"]}, summaries

    def body(self, revision, path, entry):
        if "scheduleleague" in path:
            return document
        return {
            "boxScoreSummary": {
                "gameId": "0022600002",
                "period": 5,
                "homeTeam": {"periods": [{"period": n} for n in range(1, 6)]},
                "awayTeam": {"periods": [{"period": n} for n in range(1, 6)]},
            }
        }

    monkeypatch.setattr(runtime.ArchiveSession, "discover", discover)
    monkeypatch.setattr(runtime.ArchiveSession, "body", body)
    calls, _ = fake_client(monkeypatch, [b'{"original":true}'] * 26)
    first = runtime.execute(tmp_path / "persistent", seed)
    assert first["state"] == "transport_complete"
    assert len(calls) == 12
    assert len(runtime.retained_successes(tmp_path / "persistent", seed)) == 12
    second = runtime.execute(tmp_path / "persistent", seed)
    assert second["state"] == "no_missing_direct_requests"
    assert len(calls) == 12
    document["leagueSchedule"]["gameDates"][0]["games"].append(
        portable_schedule(("0022600002",))["leagueSchedule"]["gameDates"][0]["games"][0]
    )
    summaries["0022600002.json"] = {"sha": "d" * 40}
    third = runtime.execute(tmp_path / "persistent", seed)
    assert third["state"] == "transport_complete"
    assert len(calls) == 26
    assert third["selected_game_ids"] == ["0022600002"]
    assert len([j for j in third["jobs"] if j["parameters"]["StartPeriod"] == 5]) == 2
    import zipfile

    with zipfile.ZipFile(tmp_path / "persistent/current-run.zip") as z:
        assert len([n for n in z.namelist() if n.endswith("collection.zip")]) == 1
        receipt = json.loads(z.read(next(n for n in z.namelist() if n.endswith("receipt.json"))))
        assert receipt["production_writes"] == 0 and receipt["statistical_acceptance"] is False


def test_reusable_bundle_is_standalone_and_seeds_every_prior_success(tmp_path):
    import zipfile

    from tools.readiness_refresh import build_reusable_bundle

    cache = SourceCache(tmp_path / "cache")
    raw = json.dumps(portable_schedule()).encode()
    target = tmp_path / "owner.zip"
    binding = build_reusable_bundle(
        cache,
        target,
        schedule_raw=raw,
        schedule_blob=git_blob(raw),
        summaries={},
        base_generation="base",
        base_manifest_sha256="f" * 64,
    )
    assert binding["seed_successes"] == 0
    with zipfile.ZipFile(target) as z:
        source = z.read("run_capture.py").decode()
        namespace = {"__name__": "not_main", "__file__": str(tmp_path / "run_capture.py")}
        exec(compile(source, "run_capture.py", "exec"), namespace)
        assert namespace["SEED"]["base_generation"] == "base"
        assert namespace["MAX_GAMES"] == 40 and namespace["MAX_DIRECT"] == 500
        assert "from tools." not in source[source.index("SEED = json.loads") :].split(
            "MIRROR =", 1
        )[0].replace(
            "from tools.collect_rollover_readiness_laptop import collect, validate_request", ""
        )
        assert "readiness-refresh/current-run.zip" in z.read("Run Capture.command").decode()


def test_missing_archive_summary_discovers_ot_in_same_invocation_without_retry(
    tmp_path, monkeypatch
):
    from tests.test_collect_rollover_readiness_laptop import fake_client
    from tools import readiness_refresh_laptop as runtime

    document = portable_schedule()
    seed = runtime_seed(document)
    monkeypatch.setattr(
        runtime.ArchiveSession,
        "discover",
        lambda self: ("a" * 40, {"sha": seed["schedule"]["blob"]}, {}),
    )
    monkeypatch.setattr(runtime.ArchiveSession, "body", lambda *args: document)
    summary = {
        "boxScoreSummary": {
            "gameId": "0022600001",
            "period": 5,
            "homeTeam": {"periods": [{"period": n} for n in range(1, 6)]},
            "awayTeam": {"periods": [{"period": n} for n in range(1, 6)]},
        }
    }
    calls, _ = fake_client(
        monkeypatch, [json.dumps(summary).encode()] + [b'{"original":true}'] * 14
    )
    first = runtime.execute(tmp_path / "persistent", seed)
    assert first["state"] == "transport_complete"
    assert len(calls) == 15
    assert first["period_population_unresolved"] == []
    assert len(first["jobs"]) == 15
    second = runtime.execute(tmp_path / "persistent", seed)
    assert second["state"] == "no_missing_direct_requests"
    assert len(calls) == 15


def test_reusable_failure_exports_original_and_reentry_makes_zero_requests(tmp_path, monkeypatch):
    import zipfile

    from tests.test_collect_rollover_readiness_laptop import fake_client
    from tools import readiness_refresh_laptop as runtime

    document = portable_schedule()
    seed = runtime_seed(document)
    discovers = []

    def discover(self):
        discovers.append(True)
        return "a" * 40, {"sha": seed["schedule"]["blob"]}, {"0022600001.json": {"sha": "b" * 40}}

    monkeypatch.setattr(runtime.ArchiveSession, "discover", discover)
    monkeypatch.setattr(runtime.ArchiveSession, "body", lambda *args: document)
    calls, _ = fake_client(monkeypatch, [b'{"original":true}'] * 2, "403")
    first = runtime.execute(tmp_path / "persistent", seed)
    assert first["state"] == "failed_preserve_output_do_not_retry"
    assert len(calls) == 2
    second = runtime.execute(tmp_path / "persistent", seed)
    assert second["state"] == "failed_preserve_output_do_not_retry"
    assert len(calls) == 2 and len(discovers) == 1
    with zipfile.ZipFile(tmp_path / "persistent/current-run.zip") as z:
        assert any(name.endswith("acquisition.json") for name in z.namelist())
        assert any(name.endswith("_q1.json") for name in z.namelist())


def test_all_three_retained_captures_seed_exact_1121_successes_offline(tmp_path):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    evidence = root / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    archives = [
        (
            "q1-laptop-capture",
            "ab6618b4b0da9ddd3f262547832718544d74de7cf24d67f4b7901cb9081ef88d",
            2,
        ),
        (
            "partial-capture-20261103",
            "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3",
            602,
        ),
        (
            "recovery-capture-20261104",
            "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17",
            517,
        ),
    ]
    cache = SourceCache(tmp_path / "cache")
    for directory, digest, count in archives:
        assert (
            cache.import_collection(evidence / directory / "collection.zip", digest)[
                "successful_sources"
            ]
            == count
        )
    assert len(cache.data["direct"]) == 1121
    assert len(cache.data["direct_attempts"]) == 1  # Historical timeout remains recorded.
    assert cache.unresolved_direct_attempts() == {}  # Its reviewed recovery already succeeded.
    restored = SourceCache(tmp_path / "cache")
    assert len(restored.data["direct"]) == 1121
    for directory, digest, _ in archives:
        restored.import_collection(evidence / directory / "collection.zip", digest)
    assert len(restored.data["direct"]) == 1121


def test_failed_archive_discovery_is_not_implicitly_retried(tmp_path, monkeypatch):
    from tools import readiness_refresh_laptop as runtime

    seed = runtime_seed(portable_schedule())
    calls = []

    def fail(self):
        calls.append(True)
        raise ValueError("Controlled diagnosed metadata failure")

    monkeypatch.setattr(runtime.ArchiveSession, "discover", fail)
    first = runtime.execute(tmp_path / "persistent", seed)
    second = runtime.execute(tmp_path / "persistent", seed)
    assert first["state"] == second["state"] == "failed_preserve_output_do_not_retry"
    assert len(calls) == 1


def test_portable_current_schedule_matches_exact_canonical_107_game_population():
    import zipfile
    from pathlib import Path

    from nbatools.commands.pipeline.official_schedule import normalize_official_schedule
    from tools.readiness_refresh_laptop import schedule_due

    archive = (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/source-evidence/rollover-2026-27/"
        "recovery-capture-20261104/supplementary-sources.zip"
    )
    with zipfile.ZipFile(archive) as z:
        raw = z.read("schedule-current.json")
    now = datetime(2026, 11, 4, 3, 56, 53, tzinfo=UTC)
    expected = due_population(normalize_official_schedule(raw, "2026-27"), games(), now)
    assert schedule_due(json.loads(raw), now) == expected["due_game_ids"]
    assert len(expected["due_game_ids"]) == 107


def test_failed_cloud_attempt_is_embedded_and_blocks_portable_transport(tmp_path, monkeypatch):
    import zipfile

    from tests.test_readiness_refresh_import import digest, run_files
    from tools.readiness_refresh import build_reusable_bundle, identity

    _, calls, output, report = run_files(tmp_path, monkeypatch, failure=True)
    cache = SourceCache(tmp_path / "cache")
    raw_zip = (output / "collection.zip").read_bytes()
    cache.import_collection(output / "collection.zip", digest(raw_zip))
    schedule_raw = json.dumps(portable_schedule()).encode()
    target = tmp_path / "owner.zip"
    build_reusable_bundle(
        cache,
        target,
        schedule_raw=schedule_raw,
        schedule_blob=git_blob(schedule_raw),
        summaries={},
        base_generation="base",
        base_manifest_sha256="f" * 64,
    )
    with zipfile.ZipFile(target) as z:
        namespace = {"__name__": "not_main", "__file__": str(tmp_path / "run_capture.py")}
        exec(compile(z.read("run_capture.py"), "run_capture.py", "exec"), namespace)
    seed = namespace["SEED"]
    key = identity(report["attempts"][-1]["job"])
    assert key in seed["blocked_attempts"]
    discoveries = []
    monkeypatch.setattr(
        namespace["ArchiveSession"], "discover", lambda self: discoveries.append(True)
    )
    result = namespace["execute"](tmp_path / "portable", seed)
    assert result["state"] == "failed_preserve_output_do_not_retry"
    assert discoveries == [] and len(calls) == 2


def test_optional_unset_round_has_one_transport_identity_and_migrates_cache(tmp_path):
    import hashlib

    from tools.readiness_refresh import readiness_dependencies
    from tools.readiness_refresh_laptop import token

    _, snapshots = readiness_dependencies("11/02/2026")
    omitted = snapshots[0]
    explicit = {**omitted, "parameters": {**omitted["parameters"], "ISTRound": None}}
    assert identity(omitted) == identity(explicit) == token(omitted) == token(explicit)
    filtered = {**omitted, "parameters": {**omitted["parameters"], "ISTRound": "Final"}}
    with pytest.raises(ValueError, match="tournament-round"):
        identity(filtered)
    with pytest.raises(ValueError, match="tournament-round"):
        token(filtered)
    cache = SourceCache(tmp_path / "cache")
    body = b'{"retained":true}'
    record = {
        **cache._body(body),
        "job": explicit,
        "captured_at": "2026-11-04T00:00:00Z",
        "original_zip_sha256": "a" * 64,
    }
    old_key = hashlib.sha256(
        json.dumps(
            [explicit["endpoint"], explicit["parameters"]], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert old_key != identity(explicit)
    cache.data["direct"][old_key] = record
    cache.save()
    restored = SourceCache(tmp_path / "cache")
    assert list(restored.data["direct"]) == [identity(omitted)]
    assert restored.data["direct"][identity(omitted)]["job"] == explicit
    assert restored.read(restored.data["direct"][identity(omitted)]) == body
    # Equivalent keys with different bodies remain an explicit source conflict.
    restored.data["direct"][old_key] = {**record, **restored._body(b'{"different":true}')}
    restored.save()
    with pytest.raises(ValueError, match="conflicting retained originals"):
        SourceCache(tmp_path / "cache")
