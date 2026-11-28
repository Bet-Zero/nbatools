"""Verified release receipts select the generation independently of serving."""

import hashlib
import json
import sys
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from nbatools import production_publication_evidence as evidence
from tools import production_monitor


class Receipts:
    def __init__(self):
        self.releases = []
        self.responses = {}
        self.bodies = {}
        self.registries = {}
        self.lookups = []

    def api(self, path, *, public_actions=False):
        self.lookups.append((path, public_actions))
        if path == "/releases?per_page=100":
            return self.releases
        return self.responses[path]

    def receipt(self, tag):
        return self.bodies[tag]

    def registry(self, sha):
        return self.registries[sha]

    def add(self, run_id, state, *, mutate=None, reuse=False):
        tag = f"data-publication-{run_id}"
        commit = f"{run_id:040x}"
        generation, base = f"fixture-next-{run_id}", "fixture-base"
        objects = [{"path": "raw/verified.csv", "size_bytes": 42, "sha256": "5" * 64}]
        if reuse:
            objects[0]["storage_generation"] = base
        manifest_body = (
            json.dumps(
                {
                    "schema_version": 2 if reuse else 1,
                    "files": objects,
                    "generation_id": generation,
                },
                indent=2,
                sort_keys=True,
            ).encode()
            + b"\n"
        )
        manifest = hashlib.sha256(manifest_body).hexdigest()
        candidate = state == "candidate_activated_historical_verified"
        operation = "activate_candidate" if candidate else "publish"
        activation = dict(manifest_sha256=manifest, upload_run_id=31)
        checks = [
            {"query": "fixture team record", "summary": {"games": 2}},
            {"query": "fixture team games", "sections": {"finder": [{"game_id": 314}]}},
        ]
        package = dict(generation_id=generation, publisher_sha="e" * 40, deployed_checks=checks)
        if candidate:
            package.update(activation=activation, operations=[operation])
        registry = json.dumps(
            dict(
                repository=evidence.REPOSITORY,
                environment="r2-publication",
                packages={"example": package},
            )
        ).encode()
        self.registries[commit] = registry
        day = f"2026-11-{run_id:02d}"
        receipt = dict(
            schema_version=1,
            workflow_sha=commit,
            workflow_run_id=str(run_id),
            publication_state=state,
            generation_id=generation,
            base_generation=base,
            prepared_manifest_sha256=manifest,
            verified_pointer=dict(
                generation_id=generation,
                previous_generation_id=base,
                manifest_sha256=manifest,
                schema_version=1,
                published_at=day + "T10:00:00Z",
            ),
            publication=dict(
                action="candidate_activation" if candidate else "publish",
                target="r2",
                generation_id=generation,
                previous_generation_id=base,
                manifest_sha256=manifest,
                pointer="metadata/active_generation.json",
                file_count=1,
                total_bytes=42,
            ),
            deployed_readiness=dict(
                active_generation=generation,
                ready=True,
                status="ready",
                immutable_generation=True,
                blockers=[],
            ),
            deployed_readiness_http_status=200,
            deployed_health={"http_status": 200, "status": "ok"},
            operational_acceptance_complete=True,
            deployed_answers=checks,
            deployed_query_attempts=[
                dict(index=i, query=check["query"], attempt=1, status=200)
                for i, check in enumerate(checks, 1)
            ],
            file_count=1,
            total_bytes=42,
            verified_objects=objects,
            package="example",
            registry_sha256=hashlib.sha256(registry).hexdigest(),
            publisher_sha=package["publisher_sha"],
            activation_evidence=activation,
            previous_manifest_preserved=True,
        )
        if mutate:
            mutate(receipt)
        body = json.dumps(receipt).encode()
        digest = hashlib.sha256(body).hexdigest()
        asset = dict(
            name="receipt.json",
            state="uploaded",
            size=len(body),
            digest=f"sha256:{digest}",
            uploader={"login": "github-actions[bot]"},
        )
        self.releases.append(
            dict(
                tag_name=tag,
                target_commitish=commit,
                draft=False,
                prerelease=False,
                published_at=day + "T10:30:00Z",
                author={"login": "github-actions[bot]"},
                assets=[asset],
            )
        )
        self.bodies[tag] = body
        self.responses[f"/git/ref/tags/{tag}"] = dict(
            ref=f"refs/tags/{tag}", object=dict(type="commit", sha=commit)
        )
        self.responses[f"/actions/runs/{run_id}"] = dict(
            id=run_id,
            path=evidence.WORKFLOW_PATH,
            repository={"full_name": evidence.REPOSITORY},
            head_branch="main",
            head_sha=commit,
            event="workflow_dispatch",
            run_attempt=1,
            status="completed",
            conclusion="success",
        )
        return generation, manifest


def test_newest_verified_activation_wins_over_candidate_and_failed_writes():
    repo = Receipts()
    repo.add(10, "published_and_verified")
    generation, manifest = repo.add(20, "candidate_activated_historical_verified")
    repo.releases.append({"tag_name": "cloud-backup-22"})
    repo.add(23, "candidate_independently_verified_not_activated")
    repo.add(24, "candidate_activation_verification_failed")
    selected = evidence.resolve_verified_publication(repo)
    assert (selected.generation_id, selected.manifest_sha256) == (generation, manifest)
    assert selected.workflow_run_id == "20"
    assert repo.lookups == [
        ("/releases?per_page=100", False),
        ("/git/ref/tags/data-publication-20", False),
        ("/actions/runs/20", True),
    ]


def test_verified_ordinary_publication_uses_historical_publish_registry_default():
    repo = Receipts()
    generation, _ = repo.add(10, "published_and_verified")
    resolved = evidence.resolve_verified_publication(repo)
    assert resolved.generation_id == generation
    assert resolved.publication_state == "published_and_verified"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda r: r.update(workflow_run_id="9"), "receipt and release identities"),
        (lambda r: r["verified_pointer"].update(manifest_sha256="0" * 64), "pointer or manifest"),
        (lambda r: r["publication"].update(action="candidate_upload"), "pointer or manifest"),
        (
            lambda r: r["deployed_readiness"].update(active_generation="other"),
            "readiness does not match",
        ),
        (lambda r: r["activation_evidence"].update(upload_run_id=123), "approved operation"),
        (lambda r: r.update(registry_sha256="0" * 64), "exact reviewed registry"),
    ],
)
def test_invalid_newest_success_never_falls_back_to_older_green(mutate, message):
    repo = Receipts()
    repo.add(10, "published_and_verified")
    repo.add(20, "candidate_activated_historical_verified", mutate=mutate)
    with pytest.raises(evidence.PublicationEvidenceError, match=message):
        evidence.resolve_verified_publication(repo)


@pytest.mark.parametrize("fault", ["github_asset_digest", "tag_commit", "workflow", "failed_run"])
def test_github_identities_and_completed_success_are_required(fault):
    repo = Receipts()
    repo.add(20, "candidate_activated_historical_verified")
    message = "original main workflow"
    if fault == "github_asset_digest":
        repo.releases[0]["assets"][0]["digest"] = "sha256:" + "0" * 64
        message = "GitHub's digest"
    elif fault == "tag_commit":
        repo.responses["/git/ref/tags/data-publication-20"]["object"]["sha"] = "0" * 40
    elif fault == "workflow":
        repo.responses["/actions/runs/20"]["path"] = ".github/workflows/not-publication.yml"
    else:
        repo.responses["/actions/runs/20"]["conclusion"] = "failure"
        message = "completed success"
    with pytest.raises(evidence.PublicationEvidenceError, match=message):
        evidence.resolve_verified_publication(repo)


def test_no_accepted_outcome_fails_closed():
    repo = Receipts()
    repo.add(20, "candidate_independently_verified_not_activated")
    with pytest.raises(evidence.PublicationEvidenceError, match="bounded receipt history"):
        evidence.resolve_verified_publication(repo)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda r: r.update(verified_objects="x", deployed_answers="invalid"), "inventory"),
        (lambda r: r.update(deployed_answers="invalid"), "registered records"),
        (lambda r: r["verified_pointer"].update(schema_version=True), "pointer or manifest"),
        (lambda r: r["verified_objects"][0].update(path="raw/../data"), "paths or hashes"),
        (lambda r: r["verified_objects"][0].update(sha256="bogus"), "paths or hashes"),
        (lambda r: r["verified_objects"][0].update(sha256="f" * 64), "prepared manifest"),
        (lambda r: r["verified_objects"][0].update(size_bytes=True), "paths or hashes"),
        (lambda r: r["publication"].update(file_count=True), "counts or totals"),
        (lambda r: r.update(total_bytes=41), "counts or totals"),
        (lambda r: r["deployed_readiness"].update(ready="bad"), "readiness does not match"),
        (lambda r: r["deployed_health"].update(http_status=503, status="failed"), "health"),
        (lambda r: r.pop("deployed_health"), "health"),
        (lambda r: r.update(deployed_answers=r["deployed_answers"][::-1]), "registered checks"),
        (lambda r: r.update(deployed_answers=r["deployed_answers"][:1]), "registered records"),
        (
            lambda r: r["deployed_answers"].__setitem__(
                0, {"query": "fixture team record", "summary": {"games": "2"}}
            ),
            "registered values or rows",
        ),
        (lambda r: r["deployed_query_attempts"][0].update(status=503), "successful response"),
        (lambda r: r["deployed_query_attempts"][0].update(attempt=True), "registered records"),
    ],
)
def test_malformed_success_with_valid_release_asset_is_untrusted(mutate, message):
    repo = Receipts()
    repo.add(20, "candidate_activated_historical_verified", mutate=mutate)
    with pytest.raises(evidence.PublicationEvidenceError, match=message):
        evidence.resolve_verified_publication(repo)


def test_shared_object_manifest_and_one_approved_retry_are_accepted():
    def accepted_retry(receipt):
        attempts = receipt["deployed_query_attempts"]
        attempts[0:1] = [dict(attempts[0], status=429), dict(attempts[0], attempt=2)]

    repo = Receipts()
    generation, manifest = repo.add(
        20, "candidate_activated_historical_verified", reuse=True, mutate=accepted_retry
    )
    result = evidence.resolve_verified_publication(repo)
    assert (result.generation_id, result.manifest_sha256) == (generation, manifest)


def test_legacy_health_exception_requires_the_original_run_commit_and_bytes(monkeypatch):
    repo = Receipts()
    repo.add(
        20, "candidate_activated_historical_verified", mutate=lambda r: r.pop("deployed_health")
    )
    tag = "data-publication-20"
    raw = repo.bodies[tag]
    sha = hashlib.sha256(raw).hexdigest()
    commit = repo.releases[0]["target_commitish"]
    monkeypatch.setattr(evidence, "CLEVELAND_LEGACY_HEALTH_RECEIPT", ("20", commit, sha))
    assert evidence.resolve_verified_publication(repo).receipt_sha256 == sha
    repo.bodies[tag] += b"\n"
    repo.releases[0]["assets"][0].update(
        size=len(repo.bodies[tag]), digest="sha256:" + hashlib.sha256(repo.bodies[tag]).hexdigest()
    )
    with pytest.raises(evidence.PublicationEvidenceError, match="health"):
        evidence.resolve_verified_publication(repo)


def test_cli_alerts_on_evidence_failure_without_a_serving_request(monkeypatch, capsys):
    def fail(_):
        raise evidence.PublicationEvidenceError("evidence unavailable")

    def no_probe(*_args, **_kwargs):
        pytest.fail("a resolution failure must not run a generation-unbound production probe")

    monkeypatch.setattr(production_monitor, "resolve_verified_publication", fail)
    monkeypatch.setattr(production_monitor, "run_production_monitor", no_probe)
    monkeypatch.setattr(
        sys,
        "argv",
        ["monitor", "--base-url", "https://public.example", "--expected-verified-publication"],
    )
    assert production_monitor.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["notification_required"] and report["cases"] == []
    assert report["failures"] == ["verified_publication_resolution"]


def test_cli_keeps_serving_policy_failure_after_verified_resolution(monkeypatch, capsys):
    repo = Receipts()
    generation, _ = repo.add(20, "candidate_activated_historical_verified")
    monkeypatch.setattr(production_monitor, "GitHubPublicationEvidence", lambda _token: repo)

    def probe(url, *, expected_generation):
        assert (url, expected_generation) == ("https://public.example", generation)
        return SimpleNamespace(
            to_dict=lambda: {"ok": False, "failures": ["unexpected_active_generation"]}
        )

    monkeypatch.setattr(production_monitor, "run_production_monitor", probe)
    monkeypatch.setattr(
        sys,
        "argv",
        ["monitor", "--base-url", "https://public.example", "--expected-verified-publication"],
    )
    assert production_monitor.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["failures"] == ["unexpected_active_generation"]
    assert report["verified_publication"]["generation_id"] == generation


def test_current_read_only_token_can_fall_back_to_public_actions_reads(monkeypatch):
    options = []

    def download(url, *, token=None, accept=None):
        options.append((url, token))
        if token:
            raise HTTPError(url, 403, "no Actions permission", None, None)
        return b'{"id": 20}'

    monkeypatch.setattr(evidence, "_download", download)
    client = evidence.GitHubPublicationEvidence("test-token")
    assert client.api("/actions/runs/20", public_actions=True) == {"id": 20}
    assert options == [
        (evidence.API + "/actions/runs/20", "test-token"),
        (evidence.API + "/actions/runs/20", None),
    ]
