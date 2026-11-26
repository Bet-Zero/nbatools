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
def binding():
    return json.loads((gate.EVIDENCE / "live-code-binding.json").read_bytes())


def _reseal(tmp_path, mutate):
    proof = json.loads(gate.APPLICABILITY.read_bytes())
    mutate(proof)
    path = tmp_path / "controlled-companion.json"
    path.write_text(json.dumps(proof))
    return path, gate._sha(path.read_bytes())


def test_reviewed_original22_applicability(binding):
    result = gate._retained_applicability(binding)
    assert result["changed_files"] == 65
    assert len(result["cases"]) == 22
    assert result["companion_sha256"] == gate.APPLICABILITY_SHA256


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
    [None, "missing", "duplicate", "changed_text", "wrong_viewport", "old_time", "reused_request"],
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
    else:
        receipts[0]["requestId"] = receipts[1]["requestId"]
    with pytest.raises(AssertionError):
        gate._fresh_capture_set(receipts, original_cases, started=started, finished=finished)


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


def test_companion_tamper_rejected(binding, tmp_path):
    path, _ = _reseal(tmp_path, lambda proof: proof.update(full_core1_accepted=True))
    with pytest.raises(AssertionError, match="Unreviewed historical applicability"):
        gate._retained_applicability(binding, path=path)


@pytest.mark.parametrize(
    "field", ["live_binding_sha256", "original_capture_sha256", "original_case_manifest_sha256"]
)
def test_original_evidence_identity_remains_required(binding, tmp_path, field):
    path, digest = _reseal(tmp_path, lambda proof: proof.update({field: "0" * 64}))
    with pytest.raises(AssertionError):
        gate._retained_applicability(binding, path=path, expected_sha=digest)


def test_query_population_cannot_be_replaced(binding, tmp_path):
    def replace_query(proof):
        proof["cases"][0]["query"] = "Stephen Curry first quarter points"

    path, digest = _reseal(tmp_path, replace_query)
    with pytest.raises(AssertionError):
        gate._retained_applicability(binding, path=path, expected_sha=digest)


def test_original_bound_file_population_cannot_be_replaced(binding):
    relative = next(iter(binding["application_file_sha256"]))
    digest = binding["application_file_sha256"].pop(relative)
    binding["application_file_sha256"]["controlled-replacement"] = digest
    with pytest.raises(AssertionError, match="binding population must remain exact"):
        gate._retained_applicability(binding)


@pytest.mark.parametrize("kind", ["unchanged", "reviewed"])
def test_unreviewed_bound_file_change_rejected(binding, monkeypatch, kind):
    reviewed = {c["path"] for c in json.loads(gate.APPLICABILITY.read_bytes())["changes"]}
    relative = next(
        p for p in binding["application_file_sha256"] if (p in reviewed) == (kind == "reviewed")
    )
    target = gate.ROOT / relative
    original = Path.read_bytes

    def altered_bytes(path):
        raw = original(path)
        return raw + b"\n# controlled unreviewed change\n" if path == target else raw

    monkeypatch.setattr(Path, "read_bytes", altered_bytes)
    with pytest.raises(AssertionError, match="without semantic review|Unreviewed change"):
        gate._retained_applicability(binding)


def test_new_source_module_rejected(binding, monkeypatch):
    original = Path.rglob

    def extra_module(path, pattern):
        yield from original(path, pattern)
        if path == gate.ROOT / "src" and pattern == "*.py":
            yield path / "nbatools/controlled_unreviewed.py"

    monkeypatch.setattr(Path, "rglob", extra_module)
    with pytest.raises(AssertionError, match="source module addition/deletion"):
        gate._retained_applicability(binding)


def test_reviewed_added_module_change_rejected(binding, monkeypatch):
    proof = json.loads(gate.APPLICABILITY.read_bytes())
    target = gate.ROOT / proof["reviewed_added_source_modules"][0]["path"]
    original = Path.read_bytes

    def altered_bytes(path):
        raw = original(path)
        return raw + b"\n# unreviewed addition delta\n" if path == target else raw

    monkeypatch.setattr(Path, "read_bytes", altered_bytes)
    with pytest.raises(AssertionError, match="Unreviewed added module change"):
        gate._retained_applicability(binding)


def test_development_selector_cannot_qualify_production_captures(binding, monkeypatch):
    monkeypatch.setattr(gate, "selected_snapshot", lambda: object())
    with pytest.raises(AssertionError, match="cannot use development data"):
        gate._retained_applicability(binding)


def test_fresh_public_selector_keeps_original_strict_binding(tmp_path, monkeypatch):
    def forbidden_fallback(*args, **kwargs):
        pytest.fail("Fresh public selector used retained applicability")

    monkeypatch.setattr(gate, "_retained_applicability", forbidden_fallback)
    # The current reviewed development delta differs from the served old code.
    # A fresh capture cannot silently inherit the retained-applicability route.
    with pytest.raises(AssertionError):
        gate._run(tmp_path, retained=False)


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
