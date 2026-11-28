"""Fail-closed tests for reusing the original historical 22-case/44-capture proof.

No source data, public queries, production requests or new captures are required.
"""

import copy
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests import cloud_core_historical_delivery_real_data as gate


@pytest.fixture
def original_cases():
    with ZipFile(gate.EVIDENCE / "historical-live-original.zip") as archive:
        return json.loads(archive.read("acquired_data/core-historical-live/cases.json"))


def test_replacement_binds_the_fixed_original_case_identities(original_cases):
    assert gate._original_case_identity(original_cases)["case_manifest_sha256"] == (
        gate.ORIGINAL_CASES_SHA256
    )
    original_cases[0]["query"] = "Stephen Curry first quarter averages"
    with pytest.raises(AssertionError):
        gate._original_case_identity(original_cases)


@pytest.mark.parametrize("name", ["live-code-binding.json", "historical-live-original.zip"])
def test_replacement_refuses_modified_original_evidence(original_cases, monkeypatch, name):
    original = Path.read_bytes

    def read(path):
        raw = original(path)
        return raw + b"changed" if path == gate.EVIDENCE / name else raw

    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(AssertionError):
        gate._original_case_identity(original_cases)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "missing",
        "duplicate",
        "changed_text",
        "wrong_viewport",
        "old_time",
        "reused_request",
        "swapped_order",
        "unordered_time",
    ],
)
def test_replacement_requires_every_fresh_case_and_viewport(original_cases, defect):
    started = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
    finished = datetime(2026, 11, 26, 9, 10, tzinfo=UTC)
    receipts = [
        {
            **case,
            "viewport": viewport,
            "requestId": f"req_{index:032x}",
            "capturedAt": "2026-11-26T09:05:00+00:00",
        }
        for index, (viewport, case) in enumerate(
            (view, case) for view in ("desktop", "mobile") for case in original_cases
        )
    ]
    if defect is None:
        gate._fresh_capture_set(receipts, original_cases, started=started, finished=finished)
        return
    if defect == "missing":
        receipts.pop()
    elif defect == "duplicate":
        receipts[0] = receipts[1]
    elif defect == "changed_text":
        receipts[0]["query"] = "Different question"
    elif defect == "wrong_viewport":
        receipts[0]["viewport"] = "tablet"
    elif defect == "old_time":
        receipts[0]["capturedAt"] = "2026-11-07T04:00:00+00:00"
    elif defect == "swapped_order":
        receipts[0], receipts[1] = receipts[1], receipts[0]
    elif defect == "unordered_time":
        receipts[0]["capturedAt"] = "2026-11-26T09:06:00+00:00"
    else:
        receipts[0]["requestId"] = receipts[1]["requestId"]
    with pytest.raises(AssertionError):
        gate._fresh_capture_set(receipts, original_cases, started=started, finished=finished)


def test_stabilization_keeps_original_cases_and_declared_repeat_order(original_cases):
    named_delivery = {case["id"]: case for case in original_cases[:12]}
    combined, repeat_base = gate._stabilization_capture_cases(original_cases, named_delivery)

    assert [case for case in combined if case["id"] not in repeat_base] == original_cases
    assert len(combined) == 42 and len(repeat_base) == 20
    assert [case["id"] for case in combined[12:16]] == [
        "k12-s1-repeat-1",
        "k12-r1-repeat-1",
        "k12-b1-repeat-1",
        "k12-m1-repeat-1",
    ]
    for case in combined[12:32]:
        assert case["query"] == named_delivery[repeat_base[case["id"]]]["query"]


@pytest.mark.parametrize("changed", [None, "missing", "nonfinite", "slow"])
def test_stabilization_requires_all_forty_latencies_and_the_existing_p95(changed):
    values = {key: [500] * 10 for key in gate.COMMON}
    if changed == "missing":
        values["k12-s1"].pop()
    elif changed == "nonfinite":
        values["k12-s1"][0] = float("nan")
    elif changed == "slow":
        values["k12-s1"][-3:] = [3001, 3002, 3003]
    if changed:
        with pytest.raises(AssertionError):
            gate._repeat_measurements(values)
    else:
        result = gate._repeat_measurements(values)
        assert result["observations"] == 40 and result["p95_ms"] == 500


@pytest.mark.parametrize("elapsed", [20_001, float("inf"), -1])
def test_stabilization_retains_k12_historical_response_time(elapsed):
    with pytest.raises(AssertionError):
        gate._response_elapsed_ms({"responseElapsedMs": elapsed}, {"id": "K12-H1"})
    assert gate._response_elapsed_ms({"responseElapsedMs": 20_000}, {"id": "K12-H1"}) == 20_000


@pytest.mark.parametrize("generation_drift", [False, True])
def test_replacement_requires_the_approved_active_manifest(monkeypatch, generation_drift):
    from nbatools.commands.pipeline import generation_publication

    raw = json.dumps(
        {"generation_id": gate.CLEVELAND, "files": [{"path": "confirmed.csv"}]}
    ).encode()
    expected_digest = gate._sha(raw)
    pointer = {"generation_id": gate.CLEVELAND, "manifest_sha256": expected_digest}

    class Reader:
        def get_object(self, *, Bucket, Key):
            assert Bucket == "data"
            if Key == "metadata/active_generation.json":
                return {"Body": io.BytesIO(json.dumps(pointer).encode())}
            assert Key == f"generations/{gate.CLEVELAND}/metadata/generation_manifest.json"
            return {"Body": io.BytesIO(raw)}

    monkeypatch.setattr(
        generation_publication, "_resolve_r2_target", lambda **kwargs: (Reader(), "data")
    )
    monkeypatch.setattr(
        gate, "CLEVELAND_MANIFEST", "0" * 64 if generation_drift else expected_digest
    )
    if generation_drift:
        with pytest.raises(AssertionError, match="differs from the frozen release"):
            gate._stabilization_active_pointer()
    else:
        assert gate._stabilization_active_pointer() == pointer


def test_replacement_validates_native_readiness_status_as_well_as_shape():
    from tests.test_r2_publication_gates import _native_activation_readiness

    body = _native_activation_readiness(gate.CLEVELAND)
    gate._stabilization_readiness(503, body)
    body["status"] = "ready"
    with pytest.raises(AssertionError):
        gate._stabilization_readiness(503, body)


def test_current_selector_refuses_pretransition_live_context(tmp_path):
    with pytest.raises(AssertionError, match="uses the frozen Cleveland selector"):
        gate._run(tmp_path, current_runtime=True, generation_name=gate.LIVE)


def test_stabilization_still_requires_current_runtime(tmp_path):
    with pytest.raises(AssertionError):
        gate._run(tmp_path, stabilization=True)


def test_current_selector_refuses_local_development_context(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "selected_snapshot", lambda: object())
    with pytest.raises(AssertionError, match="cannot use development data"):
        gate._run(
            tmp_path, current_runtime=True, generation_name=gate.CLEVELAND, stabilization=True
        )


def test_current_selector_does_not_read_the_historical_bridge(tmp_path, monkeypatch):
    def forbidden_fallback(*args, **kwargs):
        pytest.fail("Current runtime must use the deployment and capture proof")

    class ReachedFixedDataCheck(Exception):
        pass

    def stop_at_data_check():
        raise ReachedFixedDataCheck

    monkeypatch.setattr(gate, "_retained_applicability", forbidden_fallback)
    monkeypatch.setattr(gate, "data_generation_context", stop_at_data_check)
    with pytest.raises(ReachedFixedDataCheck):
        gate._run(
            tmp_path, current_runtime=True, generation_name=gate.CLEVELAND, stabilization=True
        )


def test_retained_capture_mode_cannot_be_called_fresh_runtime(tmp_path):
    with pytest.raises(AssertionError, match="cannot be fresh runtime evidence"):
        gate._run(tmp_path, retained=True, current_runtime=True)


@pytest.mark.parametrize("changed", [None, "id", "sha", "host", "tree"])
def test_new_runtime_capture_requires_one_fixed_deployment_and_build_tree(changed):
    before = dict(
        deployment=dict(id=12),
        deployed_sha="a" * 40,
        base_url="https://nbatools-reviewed-brents-projects-686e97fc.vercel.app",
        build_input_tree_sha256="b" * 64,
    )
    after = copy.deepcopy(before)
    if changed == "id":
        after["deployment"]["id"] = 13
    elif changed == "sha":
        after["deployed_sha"] = "c" * 40
    elif changed == "host":
        after["base_url"] = "https://nbatools-other-brents-projects-686e97fc.vercel.app"
    elif changed == "tree":
        after["build_input_tree_sha256"] = "d" * 64
    if changed:
        with pytest.raises(AssertionError):
            gate._assert_fixed_runtime(before, after)
    else:
        gate._assert_fixed_runtime(before, after)
