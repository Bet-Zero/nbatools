"""Candidate isolation, integrity and pointer-only activation contracts."""

import hashlib
import json

import pytest

from nbatools.commands.pipeline import generation_publication as pub
from tests.test_generation_publication import FakeR2Client, _write_valid_source


def prepared(tmp_path):
    source = tmp_path / "data"
    _write_valid_source(source, "retained")
    client = FakeR2Client()
    base = pub.publish_r2_generation("base", source_dir=source, client=client, bucket_name="b")
    local = pub.publish_local_generation(
        "candidate", source_dir=source, data_root=tmp_path / "local"
    )
    client.put_order.clear()
    return (
        source,
        client,
        dict(
            expected_base="base",
            expected_base_manifest_sha256=base.manifest_sha256,
            expected_manifest_sha256=local.manifest_sha256,
            client=client,
            bucket_name="b",
        ),
    )


def test_candidate_upload_never_writes_pointer_then_activation_only_writes_pointer(tmp_path):
    source, client, args = prepared(tmp_path)
    pointer = client.objects["metadata/active_generation.json"]
    original = dict(client.objects)
    result = pub.upload_r2_candidate("candidate", source_dir=source, **args)
    assert result.action == "candidate_upload"
    assert client.objects["metadata/active_generation.json"] == pointer
    assert client.put_order and all(
        k.startswith("generations/candidate/") for k in client.put_order
    )
    assert all(client.objects[k] == v for k, v in original.items())
    candidate_objects = dict(client.objects)
    client.put_order.clear()
    result = pub.activate_r2_candidate("candidate", **args)
    assert result.action == "candidate_activation"
    assert client.put_order == ["metadata/active_generation.json"]
    assert all(
        client.objects[k] == v
        for k, v in candidate_objects.items()
        if k != "metadata/active_generation.json"
    )
    assert (
        json.loads(client.objects["metadata/active_generation.json"])["previous_generation_id"]
        == "base"
    )


@pytest.mark.parametrize("defect", ["base", "base_hash", "candidate_hash"])
def test_bad_approval_tuple_cannot_upload(tmp_path, defect):
    source, client, args = prepared(tmp_path)
    args[
        {
            "base": "expected_base",
            "base_hash": "expected_base_manifest_sha256",
            "candidate_hash": "expected_manifest_sha256",
        }[defect]
    ] = "wrong"
    with pytest.raises(pub.GenerationPublicationError):
        pub.upload_r2_candidate("candidate", source_dir=source, **args)
    assert not client.put_order


def test_partial_upload_failure_keeps_base(tmp_path):
    source, client, args = prepared(tmp_path)
    before = client.objects["metadata/active_generation.json"]
    client.fail_put_keys.add("generations/candidate/raw/sample.csv")
    with pytest.raises(pub.GenerationPublicationError):
        pub.upload_r2_candidate("candidate", source_dir=source, **args)
    assert client.objects["metadata/active_generation.json"] == before
    assert "metadata/active_generation.json" not in client.put_order


def test_activation_rejects_body_corruption_even_when_metadata_matches(tmp_path):
    source, client, args = prepared(tmp_path)
    pub.upload_r2_candidate("candidate", source_dir=source, **args)
    path = "generations/candidate/raw/sample.csv"
    client.objects[path] = b"x" * len(client.objects[path])
    client.put_order.clear()
    with pytest.raises(pub.GenerationValidationError, match="checksum"):
        pub.activate_r2_candidate("candidate", **args)
    assert not client.put_order


def test_activation_compare_and_swap_rejects_race_without_reupload(tmp_path):
    source, client, args = prepared(tmp_path)
    pub.upload_r2_candidate("candidate", source_dir=source, **args)
    client.put_order.clear()
    client.pointer_conflict_payload = json.dumps(dict(generation_id="another")).encode()
    with pytest.raises(pub.GenerationConflictError):
        pub.activate_r2_candidate("candidate", **args)
    assert not client.put_order


def test_upload_rejects_corruption_of_an_existing_candidate(tmp_path):
    source, client, args = prepared(tmp_path)
    pub.upload_r2_candidate("candidate", source_dir=source, **args)
    key = "generations/candidate/raw/sample.csv"
    client.objects[key] = b"x" * len(client.objects[key])
    with pytest.raises(pub.GenerationValidationError):
        pub.upload_r2_candidate("candidate", source_dir=source, **args)


def test_preview_pin_is_preview_only_and_authenticates_exact_manifest(monkeypatch):
    from types import SimpleNamespace

    from nbatools import candidate_preview as preview
    from nbatools.data_source import DataSourceConfigError

    client = FakeR2Client()
    raw = json.dumps(dict(generation_id="candidate")).encode()
    client.objects["generations/candidate/metadata/generation_manifest.json"] = raw
    source = SimpleNamespace(client=client, config=SimpleNamespace(bucket_name="b"))
    monkeypatch.setenv(preview.MANIFEST_ENV, hashlib.sha256(raw).hexdigest())
    monkeypatch.setenv("DATA_SOURCE", "r2")
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "candidate")
    for mode in ("production", "development", ""):
        monkeypatch.setenv("VERCEL_ENV", mode)
        with pytest.raises(DataSourceConfigError):
            preview.verify_pin(source, "candidate")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    preview.verify_pin(source, "candidate")
    monkeypatch.setenv(preview.MANIFEST_ENV, "0" * 64)
    with pytest.raises(DataSourceConfigError, match="checksum"):
        preview.verify_pin(source, "candidate")


def test_candidate_diagnostics_do_nothing_without_preview_pin(monkeypatch):
    from nbatools.candidate_preview import MANIFEST_ENV, ColdQualification

    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    with ColdQualification() as qualification:
        pass
    assert qualification.headers == {}


def test_cold_evidence_survives_real_admitted_executor(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from nbatools import candidate_preview as preview
    from nbatools import data_source, vercel_functions
    from nbatools.admission_control import AdmissionController
    from nbatools.dataframe_cache import clear_frame_cache

    clear_frame_cache()
    monkeypatch.setenv(preview.MANIFEST_ENV, "a" * 64)
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "candidate")
    monkeypatch.setattr(preview, "_requests", 0)
    monkeypatch.setattr(preview, "verify_pin", lambda *args: None)
    monkeypatch.setattr(
        data_source, "_get_data_source", lambda: SimpleNamespace(cache_root=tmp_path)
    )
    monkeypatch.setattr("nbatools.admission_control.ADMISSION_CONTROLLER", AdmissionController())

    def execute(query):
        preview.appearance_load_event()
        preview.appearance_load_event(completed=True)
        return {"ok": True, "query": query}

    monkeypatch.setattr(vercel_functions, "natural_query_payload", execute)
    with preview.ColdQualification() as qualification:
        status, payload = vercel_functions.query_response(
            {"query": "Cavaliers record"}, client_id="test"
        )
    proof = json.loads(qualification.headers["X-NBATools-Candidate-Qualification"])
    assert status == 200 and payload["ok"]
    assert proof["invocation"] == 1 and proof["disk_cache_empty"]
    assert proof["frame_entries_before"] == 0
    assert proof["appearance_loads"] == proof["appearance_loads_completed"] == 1
    assert proof["succeeded"]


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "warm",
        "disk",
        "no_loader",
        "incomplete_loader",
        "generation",
        "manifest",
        "slow",
        "unknown",
        "wrong_answer",
    ],
)
def test_cold_verifier_requires_actual_cold_positive_answer(damage):
    from types import SimpleNamespace

    from tools.r2_publication import verify_candidate_cold_response

    proof = dict(
        worker="a" * 32,
        invocation=1,
        disk_cache_empty=True,
        frame_entries_before=0,
        appearance_loads=1,
        appearance_loads_completed=1,
        succeeded=True,
        generation="candidate",
        manifest_sha256="b" * 64,
        elapsed_ms=100,
    )
    case = dict(
        query="Cavaliers record without Caris LeVert in 2024-25",
        summary=dict(games=44, wins=31, losses=13),
    )
    answer = dict(result_status="ok", result=dict(sections=dict(summary=[dict(case["summary"])])))
    elapsed = 0.2
    if damage == "warm":
        proof["invocation"] = 2
    if damage == "disk":
        proof["disk_cache_empty"] = False
    if damage == "no_loader":
        proof["appearance_loads"] = 0
    if damage == "incomplete_loader":
        proof["appearance_loads_completed"] = 0
    if damage == "generation":
        proof["generation"] = "other"
    if damage == "manifest":
        proof["manifest_sha256"] = "c" * 64
    if damage == "slow":
        elapsed = 20.01
    if damage == "unknown":
        answer["result_status"] = "no_result"
    if damage == "wrong_answer":
        answer["result"]["sections"]["summary"][0]["games"] = 45
    response = SimpleNamespace(
        status_code=200,
        json=lambda: answer,
        headers={"X-NBATools-Candidate-Qualification": json.dumps(proof)},
    )
    if damage:
        with pytest.raises(ValueError):
            verify_candidate_cold_response(
                response,
                generation="candidate",
                manifest_sha256="b" * 64,
                elapsed_seconds=elapsed,
                case=case,
            )
    else:
        result = verify_candidate_cold_response(
            response,
            generation="candidate",
            manifest_sha256="b" * 64,
            elapsed_seconds=elapsed,
            case=case,
        )
        assert result["answer"]["summary"] == case["summary"]


def test_candidate_package_forbids_combined_publish(tmp_path, monkeypatch):
    from tools import r2_publication as gate

    monkeypatch.setattr(gate, "check_main_revision", lambda *args: None)
    monkeypatch.setattr(gate, "environment_audit", lambda: {})
    monkeypatch.setattr(gate, "check_approval", lambda *args: None)
    monkeypatch.setattr(gate, "api", lambda *args: [])
    monkeypatch.setenv("GITHUB_SHA", "code")
    monkeypatch.setenv("GITHUB_RUN_ID", "run")
    monkeypatch.setattr(
        gate, "prepare", lambda *args, **kwargs: pytest.fail("Combined publish reached")
    )
    prepared = tmp_path / "prepared.json"
    prepared.write_text("{}")
    with pytest.raises(ValueError, match="forbids"):
        gate.publish("cleveland-team-appearances-2024-v1", tmp_path, tmp_path / "work", prepared)


def test_candidate_client_disables_sdk_retries_without_changing_legacy(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(pub, "load_r2_config", lambda **kwargs: SimpleNamespace(bucket_name="b"))
    calls = []
    monkeypatch.setattr(
        pub, "create_r2_client", lambda config, **kwargs: calls.append(kwargs) or "client"
    )
    pub._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None, disable_retries=True
    )
    pub._resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    assert calls == [{"disable_retries": True}, {}]
