"""Manual publication gates around the reviewed overlay script and immutable publisher.

No arbitrary refs/artifacts/commands are accepted. The registry is reviewed code.
Only ``publish`` can call the existing writer; all other modes are read-only.
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


def api(path, *, binary=False):
    """Only fixed same-repository GET endpoints; requests strips redirected auth."""
    if not path.startswith("/") or ".." in path or ":" in path:
        raise ValueError("Invalid GitHub API path")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
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
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
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
    }


def prepare(name, publisher, work, *, expected=None):
    policy, package, inventory = load_package(name, publisher)
    if work.exists():
        raise ValueError("Preparation requires a new workspace")
    work.mkdir(parents=True)
    summary = acquire_overlay(inventory, work / "overlay")
    publication = publisher_modules(publisher)
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    pointer, _, base_hash = verify_pointer_manifest(client, bucket, inventory["base_generation"])
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
        "artifact_id": inventory["artifact_id"],
        "artifact_zip_sha256": inventory["artifact_zip_sha256"],
        "source_run_id": inventory["run_id"],
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


def verify(name, publisher, work, published_path):
    policy, package, inventory = load_package(name, publisher)
    receipt = json.loads(published_path.read_text())
    if (
        receipt.get("package") != name
        or receipt.get("registry_sha256") != digest(REGISTRY.read_bytes())
        or receipt.get("workflow_sha") != os.environ.get("GITHUB_SHA")
        or receipt.get("workflow_run_id") != os.environ.get("GITHUB_RUN_ID")
        or receipt.get("generation_id") != package["generation_id"]
    ):
        raise ValueError("Publication receipt does not bind this workflow/package")
    publication = publisher_modules(publisher)
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
        base_url = "https://nbatools.vercel.app"
        readiness = None
        for attempt in range(10):
            response = requests.get(base_url + "/readiness", timeout=20)
            if response.status_code == 200:
                value = response.json()
                if (
                    value.get("ready")
                    and value.get("active_generation") == package["generation_id"]
                ):
                    readiness = value
                    break
            if attempt < 9:
                time.sleep(15)
        if readiness is None:
            raise ValueError("Deployed readiness did not adopt the verified generation")
        answers = []
        for case in package["deployed_checks"]:
            response = requests.post(base_url + "/query", json={"query": case["query"]}, timeout=30)
            if response.status_code != 200:
                raise ValueError("Deployed publication query did not succeed")
            answer = response.json()
            rows = answer.get("result", {}).get("sections", {}).get("summary", [])
            if answer.get("result_status") != "ok" or len(rows) != 1:
                raise ValueError("Deployed publication query returned no numeric result")
            if any(rows[0].get(k) != v for k, v in case["summary"].items()):
                raise ValueError("Deployed publication query differs from verified NBA evidence")
            answers.append({"query": case["query"], "summary": rows[0]})
        final_pointer, _, final_hash = verify_pointer_manifest(
            client, bucket, package["generation_id"]
        )
        if final_pointer != pointer or final_hash != manifest_hash:
            raise ValueError("Active pointer moved during deployed verification")
        receipt.update(
            publication_state="published_and_verified",
            verified_objects=checked,
            verified_pointer=pointer,
            deployed_readiness=readiness,
            deployed_answers=answers,
        )
    except Exception:
        receipt["publication_state"] = "published_verification_failed"
        raise
    finally:
        write_json(work / "receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["resolve", "audit", "prepare", "publish", "verify"])
    parser.add_argument("--package", default="opening-availability-v1")
    parser.add_argument("--publisher", type=Path, default=Path("publisher"))
    parser.add_argument("--work", type=Path, default=Path("work/publication"))
    parser.add_argument("--prepared", type=Path)
    args = parser.parse_args()
    if args.mode == "resolve":
        check_main_revision(os.environ["GITHUB_SHA"])
        if os.environ.get("PUBLICATION_MODE") == "publish":
            audit = environment_audit()
            if not audit.get("publication_ready"):
                raise ValueError(
                    "Configure protected publication environment before requesting publish"
                )
        policy = json.loads(REGISTRY.read_text())
        if args.package not in policy["packages"]:
            raise ValueError("Package is not reviewed")
        package = policy["packages"][args.package]
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"publisher_sha={package['publisher_sha']}\n")
            output.write(f"generation_id={package['generation_id']}\n")
    elif args.mode == "audit":
        write_json(args.work / "environment-audit.json", environment_audit())
    elif args.mode == "prepare":
        prepare(args.package, args.publisher.resolve(), args.work.resolve())
    elif args.mode == "publish":
        publish(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)
    else:
        verify(args.package, args.publisher.resolve(), args.work.resolve(), args.prepared)


if __name__ == "__main__":
    main()
