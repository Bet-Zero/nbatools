"""Manual publication gates around the reviewed overlay script and immutable publisher.

No arbitrary refs/artifacts/commands are accepted. The registry is reviewed code.
Candidate upload and pointer-only activation are separate protected operations.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path, PurePosixPath

import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".github/data-publication-packages.json"
REPOSITORY = "Bet-Zero/nbatools"
ENVIRONMENT = "r2-publication"
OWNER_ID = 205859440
MAX_ARCHIVE = 32 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def api(path, *, binary=False, accept="application/vnd.github+json"):
    """Only fixed same-repository GET endpoints; requests strips redirected auth."""
    if not path.startswith("/") or ".." in path or ":" in path:
        raise ValueError("Invalid GitHub API path")
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    response = requests.get(
        f"https://api.github.com/repos/{REPOSITORY}{path}",
        headers=headers,
        timeout=60,
        stream=binary,
    )
    # Do not log response bodies, redirects or tokens on failure.
    if response.status_code != 200:
        raise ValueError(f"GitHub metadata/download unavailable: HTTP {response.status_code}")
    if binary:
        payload = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=65536):
                payload.extend(chunk)
                if len(payload) > MAX_ARCHIVE:
                    raise ValueError("Source artifact exceeds the bounded archive size")
        finally:
            response.close()
        return bytes(payload)
    return response.json()


def load_package(name, publisher):
    policy = json.loads(REGISTRY.read_text())
    if policy["repository"] != REPOSITORY or policy["environment"] != ENVIRONMENT:
        raise ValueError("Publication registry repository/environment mismatch")
    if name not in policy["packages"]:
        raise ValueError("Package is not in the reviewed registry")
    package = policy["packages"][name]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", name):
        raise ValueError("Invalid package identifier")
    if not re.fullmatch(r"[0-9a-f]{40}", package["publisher_sha"]):
        raise ValueError("Publisher must be an immutable commit")
    for key in ("script", "inventory"):
        path = PurePosixPath(package[key])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe package path")
        actual = publisher / package[key]
        if actual.is_symlink() or digest(actual.read_bytes()) != package[key + "_sha256"]:
            raise ValueError(f"Reviewed {key} differs")
    head = subprocess.check_output(
        ["git", "-C", str(publisher), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != package["publisher_sha"]:
        raise ValueError("Publisher checkout differs from reviewed commit")
    inventory = json.loads((publisher / package["inventory"]).read_text())
    for item in inventory["code_files"]:
        path = PurePosixPath(item["path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe reviewed code path")
        actual = publisher / path
        if actual.is_symlink() or digest(actual.read_bytes()) != item["sha256"]:
            raise ValueError("Publisher code differs from reviewed inventory")
    return policy, package, inventory


def check_main_revision(sha):
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
    ):
        raise ValueError("Publication requires a fresh manual main-branch run")
    if api("/git/ref/heads/main")["object"]["sha"] != sha:
        raise ValueError("Main changed; start a new reviewed workflow run")
    prs = api(f"/commits/{sha}/pulls")
    if not any(
        p.get("merged_at")
        and p.get("merge_commit_sha") == sha
        and p.get("base", {}).get("ref") == "main"
        for p in prs
    ):
        raise ValueError("Workflow revision is not a merged main pull request")
    runs = api(f"/actions/runs?head_sha={sha}&event=push&per_page=100")["workflow_runs"]
    ci = [r for r in runs if r.get("path") == ".github/workflows/ci.yml"]
    if not ci or max(ci, key=lambda r: r["id"]).get("conclusion") != "success":
        raise ValueError("Reviewed main revision has no successful post-merge CI")


def check_environment(document, branches):
    if document.get("name") != ENVIRONMENT or document.get("can_admins_bypass") is not False:
        raise ValueError("Publishing environment must disable administrator bypass")
    policy = document.get("deployment_branch_policy") or {}
    if policy != {"protected_branches": False, "custom_branch_policies": True}:
        raise ValueError("Publishing environment must use explicit branch restrictions")
    rules = branches.get("branch_policies", [])
    if len(rules) != 1 or rules[0].get("name") != "main" or rules[0].get("type") != "branch":
        raise ValueError("Only the main branch may access publisher credentials")
    reviewers = [
        r for r in document.get("protection_rules", []) if r.get("type") == "required_reviewers"
    ]
    if len(reviewers) != 1:
        raise ValueError("Publishing requires an owner approval rule")
    entries = reviewers[0].get("reviewers", [])
    if (
        len(entries) != 1
        or entries[0].get("type") != "User"
        or entries[0].get("reviewer", {}).get("id") != OWNER_ID
    ):
        raise ValueError("Only the repository owner may approve publication")


def environment_audit():
    """Report only nonsecret environment policy; missing access is never approval."""
    result = {"publication_ready": False, "environment": ENVIRONMENT}
    try:
        result["environments"] = [
            {
                k: e.get(k)
                for k in (
                    "name",
                    "id",
                    "can_admins_bypass",
                    "deployment_branch_policy",
                    "protection_rules",
                )
            }
            for e in api("/environments?per_page=100").get("environments", [])
        ]
        document = api(f"/environments/{ENVIRONMENT}")
        branches = api(f"/environments/{ENVIRONMENT}/deployment-branch-policies?per_page=100")
        result.update(configuration=document, branches=branches)
        check_environment(document, branches)
        result["publication_ready"] = True
    except (ValueError, requests.RequestException) as exc:
        result["blocker"] = (
            str(exc) if isinstance(exc, ValueError) else "GitHub policy request failed"
        )
    return result


def check_approval(audit, approvals):
    if not audit.get("publication_ready"):
        raise ValueError("Publishing environment protections are unverified")
    check_environment(audit["configuration"], audit["branches"])
    environment_id = audit["configuration"]["id"]
    if not any(
        a.get("state") == "approved"
        and a.get("user", {}).get("id") == OWNER_ID
        and environment_id in [e.get("id") for e in a.get("environments", [])]
        for a in approvals
    ):
        raise ValueError("This run lacks explicit owner approval for the publishing environment")


def acquire_overlay(inventory, destination):
    run = api(f"/actions/runs/{inventory['run_id']}")
    artifact = api(f"/actions/artifacts/{inventory['artifact_id']}")
    if (
        run.get("head_sha") != inventory["request_sha"]
        or run.get("conclusion") != "success"
        or run.get("path") != ".github/workflows/r2-real-data-validation.yml"
        or artifact.get("expired")
        or artifact.get("workflow_run", {}).get("id") != inventory["run_id"]
        or artifact.get("workflow_run", {}).get("head_sha") != inventory["request_sha"]
    ):
        raise ValueError("Artifact is not the reviewed successful source run")
    parents = api(f"/commits/{inventory['request_sha']}").get("parents", [])
    if len(parents) != 1 or parents[0].get("sha") != inventory["reviewed_sha"]:
        raise ValueError("Source request does not bind the reviewed producer")
    payload = api(f"/actions/artifacts/{inventory['artifact_id']}/zip", binary=True)
    if digest(payload) != inventory["artifact_zip_sha256"]:
        raise ValueError("Artifact archive checksum differs from reviewed package")
    expected = {"acquired_data/" + f["path"] for f in inventory["files"]}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if (
            len(names) != len(set(names))
            or sum(i.file_size for i in archive.infolist()) > MAX_ARCHIVE
        ):
            raise ValueError("Duplicate or oversized archive")
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe artifact member")
        actual = {n for n in names if n.startswith("acquired_data/") and not n.endswith("/")}
        if actual != expected:
            raise ValueError("Artifact overlay inventory differs")
        summary = json.loads(archive.read("summary.json"))
        counts = [summary.get(k) for k in ("selected", "executed", "passed")]
        if (
            summary.get("candidate_sha") != inventory["request_sha"]
            or summary.get("generation") != inventory["base_generation"]
            or not isinstance(counts[0], int)
            or counts[0] < 1
            or counts != [counts[0]] * 3
            or any(summary.get(k) != 0 for k in ("skipped", "failed", "errors", "xfailed"))
        ):
            raise ValueError("Source numerical gate did not execute and pass")
        for name in sorted(expected):
            target = destination / name.removeprefix("acquired_data/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    return summary


def publisher_modules(publisher):
    sys.path.insert(0, str(publisher / "src"))
    from nbatools.commands.pipeline import generation_publication as publication

    if not Path(publication.__file__).resolve().is_relative_to(publisher.resolve()):
        raise ValueError("Publisher imported from the wrong checkout")
    return publication


def verify_pointer_manifest(client, bucket, generation):
    pointer = json.loads(
        client.get_object(Bucket=bucket, Key="metadata/active_generation.json")["Body"].read()
    )
    if pointer.get("generation_id") != generation:
        raise ValueError("Active R2 generation differs from the approved base/target")
    raw = client.get_object(
        Bucket=bucket, Key=f"generations/{generation}/metadata/generation_manifest.json"
    )["Body"].read()
    if pointer.get("manifest_sha256") != digest(raw):
        raise ValueError("Active pointer does not authenticate the generation manifest")
    manifest = json.loads(raw)
    if manifest.get("generation_id") != generation or not manifest.get("files"):
        raise ValueError("Invalid active generation manifest")
    return pointer, manifest, digest(raw)


def bucket_budget(client, bucket, policy, local):
    if (
        local["total_bytes"] > policy["max_snapshot_bytes"]
        or local["file_count"] > policy["max_snapshot_objects"]
    ):
        raise ValueError("Complete generation exceeds the reviewed size/object limit")
    used = 0
    pages = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        pages += 1
        if pages > 100:
            raise ValueError("Bucket inventory exceeds the bounded operation budget")
        used += sum(item["Size"] for item in page.get("Contents", []))
    projected = used + local["total_bytes"] + 10_000_000
    if projected > policy["max_bucket_bytes"]:
        raise ValueError(
            "Immutable generation would exceed the storage ceiling; no pruning authorized"
        )
    return {
        "current_bytes": used,
        "conservative_projected_bytes": projected,
        "limit_bytes": policy["max_bucket_bytes"],
        "inventory_list_requests": pages,
    }


def prepare(name, publisher, work, *, expected=None):
    policy, package, inventory = load_package(name, publisher)
    if work.exists():
        raise ValueError("Preparation requires a new workspace")
    work.mkdir(parents=True)
    if "retained_files" in inventory:
        # These are already accepted, Git-retained source bodies, not a new
        # acquisition or an untrusted archive supplied by workflow input.
        for item in inventory["retained_files"]:
            relative = PurePosixPath(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe retained source path")
            source = publisher / relative
            if source.is_symlink() or digest(source.read_bytes()) != item["sha256"]:
                raise ValueError("Exact retained qualification input differs")
            target = work / "overlay" / relative.name
            if target.exists():
                raise ValueError("Duplicate retained input name")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        summary = inventory["source_qualification"]
    else:
        summary = acquire_overlay(inventory, work / "overlay")
    publication = publisher_modules(publisher)
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    pointer, _, base_hash = verify_pointer_manifest(client, bucket, inventory["base_generation"])
    if inventory.get("base_manifest_sha256") not in (None, base_hash):
        raise ValueError("Base manifest differs from the reviewed package")
    subprocess.run(
        [
            sys.executable,
            str(publisher / package["script"]),
            "--artifact-dir",
            str(work / "overlay"),
            "--code-root",
            str(publisher),
            "--work-dir",
            str(work / "staging"),
            "--generation-id",
            package["generation_id"],
            "--prepare",
        ],
        check=True,
    )
    local = json.loads((work / "staging/local-validation.json").read_text())
    budget = bucket_budget(client, bucket, policy, local)
    after, _, after_hash = verify_pointer_manifest(client, bucket, inventory["base_generation"])
    if after != pointer or after_hash != base_hash:
        raise ValueError("Active base changed during snapshot preparation")
    receipt = {
        "schema_version": 1,
        "package": name,
        "registry_sha256": digest(REGISTRY.read_bytes()),
        "publisher_sha": package["publisher_sha"],
        "script_sha256": package["script_sha256"],
        "inventory_sha256": package["inventory_sha256"],
        "artifact_id": inventory.get("artifact_id"),
        "artifact_zip_sha256": inventory.get("artifact_zip_sha256"),
        "source_run_id": inventory.get("run_id"),
        "retained_files": inventory.get("retained_files"),
        "base_generation": inventory["base_generation"],
        "base_manifest_sha256": base_hash,
        "generation_id": package["generation_id"],
        "prepared_manifest_sha256": local["manifest_sha256"],
        "file_count": local["file_count"],
        "total_bytes": local["total_bytes"],
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "required_source_gate": summary,
        "budget": budget,
        "publication_state": "prepared_no_writes",
        "base_pointer": pointer,
    }
    if "upload_candidate" in package.get("operations", []):
        receipt["operation_budget"] = {
            "candidate_object_puts": local["file_count"] + 1,
            "active_pointer_puts": 0,
            "maximum_bucket_list_requests_per_inventory": 100,
            "read_requests_ceiling": 100_000,
            "candidate_writer_sdk_max_attempts": 1,
            "preparation_read_retries": "existing bounded SDK policy",
            "preview_deployments_ceiling": 2,
            "preview_query_requests_ceiling": 8,
            "automatic_publication_retries_or_refresh": False,
        }
    if expected is not None:
        keys = set(receipt) - {"budget", "publication_state", "base_pointer"}
        if any(receipt[k] != expected.get(k) for k in keys):
            raise ValueError("Rebuilt snapshot differs from the owner-visible preparation")
    write_json(work / "prepared.json", receipt)
    return receipt, publication, client, bucket


def publish(name, publisher, work, prepared_path):
    expected = json.loads(prepared_path.read_text())
    check_main_revision(os.environ["GITHUB_SHA"])
    audit = environment_audit()
    approvals = api(f"/actions/runs/{os.environ['GITHUB_RUN_ID']}/approvals")
    check_approval(audit, approvals)
    policy = json.loads(REGISTRY.read_text())
    if "publish" not in policy["packages"].get(name, {}).get("operations", ["validate", "publish"]):
        raise ValueError("Package forbids combined upload and activation")
    # This rebuild reads with the separate publisher token; no mutation occurs
    # until every source/base/code/manifest/cost/approval check has succeeded.
    receipt, publication, _, _ = prepare(name, publisher, work, expected=expected)
    receipt.update(
        publication_state="publication_started_outcome_unknown",
        environment_audit=audit,
        owner_approval=approvals,
    )
    # Persist intent before the first write. An interrupted/failed writer must
    # never be reported as an untouched bucket or a verified publication.
    write_json(work / "publication.json", receipt)
    try:
        result = publication.publish_r2_generation(
            receipt["generation_id"],
            source_dir=work / "staging/data",
            expected_base=receipt["base_generation"],
            env_file=None,
        )
        receipt.update(
            publication_state="published_verification_pending",
            publication=asdict(result),
        )
    finally:
        write_json(work / "publication.json", receipt)

    return receipt


def upload_candidate(name, publisher, work, prepared_path):
    """Protected upload only; every write is confined to the candidate prefix."""
    policy = json.loads(REGISTRY.read_text())
    if "upload_candidate" not in policy["packages"][name].get("operations", []):
        raise ValueError("Package does not authorize candidate upload")
    expected = json.loads(prepared_path.read_text())
    check_main_revision(os.environ["GITHUB_SHA"])
    audit = environment_audit()
    approvals = api(f"/actions/runs/{os.environ['GITHUB_RUN_ID']}/approvals")
    check_approval(audit, approvals)
    receipt, publication, _, _ = prepare(name, publisher, work, expected=expected)
    receipt.update(
        publication_state="candidate_upload_started_outcome_unknown",
        environment_audit=audit,
        owner_approval=approvals,
    )
    write_json(work / "publication.json", receipt)
    try:
        result = publication.upload_r2_candidate(
            receipt["generation_id"],
            source_dir=work / "staging/data",
            expected_base=receipt["base_generation"],
            expected_base_manifest_sha256=receipt["base_manifest_sha256"],
            expected_manifest_sha256=receipt["prepared_manifest_sha256"],
            env_file=None,
        )
        receipt.update(
            publication_state="candidate_verified_not_activated", publication=asdict(result)
        )
    finally:
        write_json(work / "publication.json", receipt)
    return receipt


def verify_candidate(name, publisher, work, published_path):
    _, package, inventory = load_package(name, publisher)
    receipt = json.loads(published_path.read_text())
    if any(
        (
            receipt.get("package") != name,
            receipt.get("registry_sha256") != digest(REGISTRY.read_bytes()),
            receipt.get("publisher_sha") != package["publisher_sha"],
            receipt.get("workflow_sha") != os.environ.get("GITHUB_SHA"),
            receipt.get("workflow_run_id") != os.environ.get("GITHUB_RUN_ID"),
            receipt.get("generation_id") != package["generation_id"],
            receipt.get("publication_state") != "candidate_verified_not_activated",
        )
    ):
        raise ValueError("Candidate receipt differs from this protected operation")
    publication = publisher_modules(publisher)
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    before = publication._candidate_base(
        client,
        bucket,
        package["generation_id"],
        inventory["base_generation"],
        inventory["base_manifest_sha256"],
    )
    publication.verify_r2_candidate(
        client, bucket, package["generation_id"], receipt["prepared_manifest_sha256"]
    )
    if publication._read_r2_pointer(client, bucket) != before:
        raise ValueError("Production pointer changed during independent candidate verification")
    receipt["publication_state"] = "candidate_independently_verified_not_activated"
    write_json(work / "receipt.json", receipt)
    return receipt


def read_activation_evidence(name, package, inventory):
    """Bind the prior independent upload and the reviewed hosted cold result."""
    if "activate_candidate" not in package.get("operations", []):
        raise ValueError("Package does not authorize candidate activation")
    evidence = package["activation"]
    asset = evidence["upload_receipt_asset_id"]
    raw = api(f"/releases/assets/{asset}", binary=True, accept="application/octet-stream")
    if digest(raw) != evidence["upload_receipt_sha256"]:
        raise ValueError("Independent upload receipt checksum differs")
    uploaded = json.loads(raw)
    bindings = {
        "package": name,
        "publisher_sha": package["publisher_sha"],
        "inventory_sha256": package["inventory_sha256"],
        "workflow_run_id": str(evidence["upload_run_id"]),
        "publication_state": "candidate_independently_verified_not_activated",
        "base_generation": inventory["base_generation"],
        "base_manifest_sha256": inventory["base_manifest_sha256"],
        "generation_id": package["generation_id"],
        "prepared_manifest_sha256": evidence["manifest_sha256"],
    }
    if any(uploaded.get(key) != val for key, val in bindings.items()):
        raise ValueError("Independent upload receipt does not bind this candidate and base")
    hosted = evidence["hosted"]
    pr = api(f"/pulls/{hosted['pr']}")
    if (
        not pr.get("merged_at")
        or pr.get("merge_commit_sha") != hosted["runtime_sha"]
        or pr.get("base", {}).get("ref") != "main"
        or hosted["generation_id"] != package["generation_id"]
        or hosted["manifest_sha256"] != evidence["manifest_sha256"]
        or not 0 < hosted["elapsed_seconds"] <= 20
        or hosted["first_query_passed"] is not True
        or hosted["followup_checks_passed"] != 6
    ):
        raise ValueError("Hosted cold qualification does not bind this candidate")
    return uploaded


def prepare_activation(name, publisher, work, *, expected=None):
    """Check current identities. The protected writer verifies all stored bodies before CAS."""
    policy, package, inventory = load_package(name, publisher)
    upload = read_activation_evidence(name, package, inventory)
    publication = publisher_modules(publisher)
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    base = upload["base_generation"]
    generation = upload["generation_id"]
    base_pointer, _, base_hash = verify_pointer_manifest(client, bucket, base)
    if base_pointer != upload["base_pointer"] or base_hash != upload["base_manifest_sha256"]:
        raise ValueError("The approved base pointer or manifest changed since the upload")
    raw = client.get_object(
        Bucket=bucket, Key=f"generations/{generation}/metadata/generation_manifest.json"
    )["Body"].read()
    manifest_hash = upload["prepared_manifest_sha256"]
    if digest(raw) != manifest_hash:
        raise ValueError("Uploaded candidate manifest differs from independent verification")
    manifest = json.loads(raw)
    count, size = len(manifest["files"]), sum(row["size_bytes"] for row in manifest["files"])
    if (
        manifest["generation_id"] != generation
        or count != upload["file_count"]
        or size != upload["total_bytes"]
        or not 0 < count <= policy["max_snapshot_objects"]
        or not 0 < size <= policy["max_snapshot_bytes"]
    ):
        raise ValueError("Uploaded candidate inventory differs from the approved bounds")
    receipt = dict(
        schema_version=1,
        publication_state="activation_prepared_no_writes",
        package=name,
        publisher_sha=package["publisher_sha"],
        registry_sha256=digest(REGISTRY.read_bytes()),
        workflow_sha=os.environ["GITHUB_SHA"],
        workflow_run_id=os.environ["GITHUB_RUN_ID"],
        base_generation=base,
        base_manifest_sha256=base_hash,
        base_pointer=base_pointer,
        generation_id=generation,
        prepared_manifest_sha256=manifest_hash,
        file_count=count,
        total_bytes=size,
        activation_evidence=package["activation"],
        operation_budget={"active_pointer_puts": 1, "snapshot_object_puts": 0, "sdk_attempts": 1},
    )
    if expected is not None and receipt != expected:
        raise ValueError("Activation differs from the owner-visible preparation")
    work.mkdir(parents=True, exist_ok=False)
    write_json(work / "prepared.json", receipt)
    return receipt, publication


def activate_candidate(name, publisher, work, prepared_path):
    expected = json.loads(prepared_path.read_text())
    check_main_revision(os.environ["GITHUB_SHA"])
    audit = environment_audit()
    approvals = api(f"/actions/runs/{os.environ['GITHUB_RUN_ID']}/approvals")
    check_approval(audit, approvals)
    receipt, publication = prepare_activation(name, publisher, work, expected=expected)
    receipt.update(
        publication_state="candidate_activation_started_outcome_unknown",
        environment_audit=audit,
        owner_approval=approvals,
    )
    write_json(work / "publication.json", receipt)
    try:
        result = publication.activate_r2_candidate(
            receipt["generation_id"],
            expected_base=receipt["base_generation"],
            expected_base_manifest_sha256=receipt["base_manifest_sha256"],
            expected_manifest_sha256=receipt["prepared_manifest_sha256"],
            env_file=None,
        )
        receipt.update(
            publication_state="candidate_activation_verification_pending",
            publication=asdict(result),
        )
    finally:
        write_json(work / "publication.json", receipt)
    return receipt


def verify_candidate_cold_response(response, *, generation, manifest_sha256, elapsed_seconds, case):
    """An actual hosted first-query miss is required; runner timings cannot qualify."""
    if response.status_code != 200 or not 0 < elapsed_seconds <= 20:
        raise ValueError("Candidate cold query exceeded the existing hosted budget or failed")
    proof = json.loads(response.headers.get("X-NBATools-Candidate-Qualification", "null"))
    if (
        not isinstance(proof, dict)
        or proof.get("generation") != generation
        or proof.get("manifest_sha256") != manifest_sha256
        or proof.get("invocation") != 1
        or proof.get("disk_cache_empty") is not True
        or proof.get("frame_entries_before") != 0
        or proof.get("appearance_loads") != 1
        or proof.get("appearance_loads_completed") != 1
        or proof.get("succeeded") is not True
        or not re.fullmatch(r"[0-9a-f]{32}", str(proof.get("worker")))
        or type(proof.get("elapsed_ms")) is not int
        or not 0 < proof["elapsed_ms"] <= elapsed_seconds * 1000
    ):
        raise ValueError("Candidate response does not prove a cold complete-appearance load")
    return {
        "cold_proof": proof,
        "http_elapsed_seconds": elapsed_seconds,
        "answer": verify_answer(case, response.json()),
    }


def verify_answer(case, answer):
    """Check registered numeric sections, preserving the existing summary contract."""
    if answer.get("result_status") != "ok":
        raise ValueError("Deployed publication query returned no numeric result")
    if "expected_route" in case and answer.get("route") != case["expected_route"]:
        raise ValueError("Deployed publication query changed operation")
    if ("summary" in case) == ("sections" in case):
        raise ValueError("Publication check needs exactly one expectation shape")
    expected = {"summary": [case["summary"]]} if "summary" in case else case["sections"]
    actual = answer.get("result", {}).get("sections", {})
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Publication check needs nonempty sections")
    for section, wanted in expected.items():
        rows = actual.get(section, [])
        if not isinstance(wanted, list) or not wanted or len(rows) != len(wanted):
            raise ValueError("Deployed publication query changed the verified population")
        for row, fields in zip(rows, wanted):
            if (
                not isinstance(fields, dict)
                or not fields
                or not isinstance(row, dict)
                or any(k not in row or row[k] != v for k, v in fields.items())
            ):
                raise ValueError("Deployed publication query differs from verified NBA evidence")
    if "summary" in case:
        return {"query": case["query"], "summary": actual["summary"][0]}
    return {"query": case["query"], "sections": {key: actual[key] for key in expected}}


def verify(name, publisher, work, published_path, *, activation=False):
    _, package, inventory = load_package(name, publisher)
    receipt = json.loads(published_path.read_text())
    if (
        receipt.get("package") != name
        or receipt.get("registry_sha256") != digest(REGISTRY.read_bytes())
        or receipt.get("workflow_sha") != os.environ.get("GITHUB_SHA")
        or receipt.get("workflow_run_id") != os.environ.get("GITHUB_RUN_ID")
        or receipt.get("generation_id") != package["generation_id"]
    ):
        raise ValueError("Publication receipt does not bind this workflow/package")
    if activation and (
        "activate_candidate" not in package.get("operations", [])
        or receipt.get("publication_state") != "candidate_activation_verification_pending"
        or receipt.get("activation_evidence") != package["activation"]
        or receipt.get("publication", {}).get("action") != "candidate_activation"
    ):
        raise ValueError("Activation receipt does not bind this protected candidate switch")
    publication = publisher_modules(publisher)
    return verify_published_snapshot(
        package, inventory, publication, work, receipt, activation=activation
    )


def check_live_answers(package, receipt):
    """Keep every check mandatory while honoring the public rate-limit contract."""
    if not package["deployed_checks"]:
        raise ValueError("Publication requires registered deployed checks")
    answers = receipt["deployed_answers"] = []
    attempts = receipt["deployed_query_attempts"] = []
    started = next_request_at = time.monotonic()
    for index, case in enumerate(package["deployed_checks"], 1):
        for attempt in (1, 2):
            record = dict(index=index, query=case["query"], attempt=attempt)
            attempts.append(record)
            delay_before_request = max(0, next_request_at - time.monotonic())
            if delay_before_request:
                record["pacing_seconds"] = delay_before_request
                time.sleep(delay_before_request)
            request_started = time.monotonic()
            record["started_after_seconds"] = round(request_started - started, 3)
            # Allow at most nine starts per rolling minute, including retries,
            # leaving room for readiness at the edge. No quota is bypassed.
            next_request_at = request_started + 7.0
            try:
                response = requests.post(
                    "https://nbatools.vercel.app/query", json={"query": case["query"]}, timeout=30
                )
            except requests.RequestException as exc:
                record["error_type"] = type(exc).__name__
                raise ValueError(
                    f"Deployed query {index} transport failed: {case['query']}"
                ) from exc
            record["status"] = response.status_code
            record["headers"] = {
                key: response.headers[key]
                for key in ("Retry-After", "X-Request-Id", "X-Vercel-Id")
                if key in response.headers
            }
            if response.status_code != 200:
                record["body"] = response.text[:8192]
                try:
                    error = response.json()
                except ValueError:
                    error = {}
                delay = response.headers.get("Retry-After", "")
                if (
                    attempt == 1
                    and response.status_code == 429
                    and isinstance(error, dict)
                    and error.get("error") == "rate_limited"
                    and re.fullmatch(r"[0-9]{1,2}", delay)
                    and 1 <= int(delay) <= 60
                ):
                    record["retry_after_seconds"] = int(delay)
                    time.sleep(int(delay))
                    continue
                raise ValueError(
                    f"Deployed query {index} HTTP {response.status_code}: {case['query']}"
                )
            try:
                answers.append(verify_answer(case, response.json()))
            except Exception:
                record["body"] = response.text[:8192]
                raise
            break
    if len(answers) != len(package["deployed_checks"]):
        raise ValueError("Every registered deployed answer must pass")
    return answers


def readiness_for_generation(response, generation, *, activation=False):
    """Recognize the existing historical limitation without claiming readiness."""
    if response.status_code != 200 and not (activation and response.status_code == 503):
        return None
    body = response.json()
    if body.get("active_generation") != generation:
        return None
    if activation and (
        body.get("immutable_generation") is not True
        or body.get("exception", {}).get("applied") is not False
    ):
        return None
    if response.status_code == 200 and body.get("ready") is True:
        return body
    if (
        response.status_code == 503
        and body.get("ready") is False
        and [row.get("code") for row in body.get("blockers", [])] == ["new_season_not_loaded"]
    ):
        return body
    return None


def verify_published_snapshot(package, inventory, publication, work, receipt, *, activation=False):
    """Read-only core shared by same-run verification and authenticated recovery."""
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    try:
        pointer, manifest, manifest_hash = verify_pointer_manifest(
            client, bucket, package["generation_id"]
        )
        if (
            pointer.get("previous_generation_id") != inventory["base_generation"]
            or manifest_hash != receipt["prepared_manifest_sha256"]
        ):
            raise ValueError("Published pointer/manifest differs from approved preparation")
        if activation:
            previous = client.get_object(
                Bucket=bucket,
                Key=f"generations/{inventory['base_generation']}/metadata/generation_manifest.json",
            )["Body"].read()
            if digest(previous) != inventory["base_manifest_sha256"]:
                raise ValueError("Previous generation manifest was not preserved")
            receipt["previous_manifest_preserved"] = True
        publication._validate_r2_manifest_inventory(
            client, bucket, package["generation_id"], manifest
        )
        if len(manifest["files"]) != receipt["file_count"]:
            raise ValueError("Published generation object count differs")
        checked = []
        for item in manifest["files"]:
            key = f"generations/{package['generation_id']}/{item['path']}"
            payload = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            if len(payload) != item["size_bytes"] or digest(payload) != item["sha256"]:
                raise ValueError("Published object byte verification failed")
            checked.append(item)
        after, _, _ = verify_pointer_manifest(client, bucket, package["generation_id"])
        if after != pointer:
            raise ValueError("Active pointer moved during verification")
        receipt.update(verified_objects=checked, verified_pointer=pointer)
        base_url = "https://nbatools.vercel.app"
        readiness = None
        for attempt in range(10):
            response = requests.get(base_url + "/readiness", timeout=20)
            readiness = readiness_for_generation(
                response, package["generation_id"], activation=activation
            )
            if readiness is not None:
                break
            if attempt < 9:
                time.sleep(15)
        if readiness is None:
            raise ValueError("Deployed readiness did not adopt the verified generation")
        receipt["deployed_readiness"] = readiness
        if activation:
            receipt["deployed_readiness_http_status"] = response.status_code
        answers = check_live_answers(package, receipt)
        final_pointer, _, final_hash = verify_pointer_manifest(
            client, bucket, package["generation_id"]
        )
        if final_pointer != pointer or final_hash != manifest_hash:
            raise ValueError("Active pointer moved during deployed verification")
        if activation:
            receipt["operational_acceptance_complete"] = readiness["ready"]
        receipt.update(
            publication_state=(
                "candidate_activated_historical_verified"
                if activation
                else "published_and_verified"
            ),
            verified_objects=checked,
            verified_pointer=pointer,
            deployed_readiness=readiness,
            deployed_answers=answers,
        )
    except Exception:
        if activation:
            receipt["operational_acceptance_complete"] = False
        receipt["publication_state"] = (
            "candidate_activation_verification_failed"
            if activation
            else "published_verification_failed"
        )
        raise
    finally:
        write_json(work / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=[
            "resolve",
            "audit",
            "prepare",
            "publish",
            "verify",
            "upload_candidate",
            "verify_candidate",
            "prepare_activation",
            "activate_candidate",
            "verify_activation",
        ],
    )
    parser.add_argument("--package", default="opening-availability-v1")
    parser.add_argument("--publisher", type=Path, default=Path("publisher"))
    parser.add_argument("--work", type=Path, default=Path("work/publication"))
    parser.add_argument("--prepared", type=Path)
    args = parser.parse_args()
    if args.mode == "resolve":
        check_main_revision(os.environ["GITHUB_SHA"])
        if os.environ.get("PUBLICATION_MODE") in {
            "publish",
            "upload_candidate",
            "activate_candidate",
        }:
            audit = environment_audit()
            if not audit.get("publication_ready"):
                raise ValueError(
                    "Configure protected publication environment before requesting publish"
                )
        policy = json.loads(REGISTRY.read_text())
        if args.package not in policy["packages"]:
            raise ValueError("Package is not reviewed")
        package = policy["packages"][args.package]
        mode = os.environ.get("PUBLICATION_MODE", "validate")
        if mode not in package.get("operations", ["validate", "publish"]):
            raise ValueError("Operation is not approved for this package")
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"publisher_sha={package['publisher_sha']}\n")
            output.write(f"generation_id={package['generation_id']}\n")
    elif args.mode == "audit":
        write_json(args.work / "environment-audit.json", environment_audit())
    elif args.mode == "prepare":
        prepare(args.package, args.publisher.resolve(), args.work.resolve())
    elif args.mode == "publish":
        publish(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)
    elif args.mode == "upload_candidate":
        upload_candidate(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)
    elif args.mode == "verify_candidate":
        verify_candidate(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)
    elif args.mode == "prepare_activation":
        prepare_activation(args.package, args.publisher.resolve(), args.work.resolve())
    elif args.mode == "activate_candidate":
        activate_candidate(
            args.package, args.publisher.resolve(), args.work.resolve(), args.prepared
        )
    elif args.mode == "verify_activation":
        verify(
            args.package,
            args.publisher.resolve(),
            args.work.resolve(),
            args.prepared,
            activation=True,
        )
    else:
        verify(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)


if __name__ == "__main__":
    main()
