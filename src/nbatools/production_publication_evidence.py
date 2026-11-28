"""Identify the expected production generation from existing durable GitHub receipts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from nbatools.deployment_monitoring import snapshot_live_gap_matches

REPOSITORY = "Bet-Zero/nbatools"
API = f"https://api.github.com/repos/{REPOSITORY}"
WORKFLOW_PATH = ".github/workflows/r2-data-publication.yml"
REGISTRY_PATH = ".github/data-publication-packages.json"
RELEASE_TAG = re.compile(r"data-publication-([1-9][0-9]*)")
GENERATION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")
SHA = re.compile(r"[0-9a-f]{64}")
VERIFIED_STATES = {
    "published_and_verified": ("publish", "publish"),
    "candidate_activated_historical_verified": ("activate_candidate", "candidate_activation"),
}
NON_SWITCH_STATES = {
    "publication_started_outcome_unknown",
    "published_verification_pending",
    "published_verification_failed",
    "candidate_activation_started_outcome_unknown",
    "candidate_activation_verification_pending",
    "candidate_activation_verification_failed",
    "candidate_upload_started_outcome_unknown",
    "candidate_verified_not_activated",
    "candidate_independently_verified_not_activated",
    "candidate_independent_verification_failed",
}
MAX_BODY_BYTES = 4_000_000
MAX_RECEIPTS_PER_PROBE = 8
GITHUB_REQUEST_TIMEOUT_SECONDS = 4
# This reviewed activation predated the separate health field in publication receipts.
CLEVELAND_LEGACY_HEALTH_RECEIPT = (
    "45763092143",
    "3dd58a0cf72daf934719523e3fdf42f57ca82846",
    "f20c829ba165a2d0b6715e683a76c5cb463ce6803708606a10dd942fda6b35c1",
)


class PublicationEvidenceError(ValueError):
    """No trustworthy expected generation could be resolved."""


@dataclass(frozen=True)
class VerifiedPublication:
    generation_id: str
    manifest_sha256: str
    publication_state: str
    workflow_run_id: str
    workflow_sha: str
    receipt_sha256: str


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _time(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise PublicationEvidenceError("Publication timestamp lacks a timezone")
    return stamp


def _safe_path(path):
    return (
        isinstance(path, str)
        and path.isprintable()
        and "\\" not in path
        and all(part not in {"", ".", ".."} for part in path.split("/"))
        and path not in {"metadata/generation_manifest.json", "metadata/active_generation.json"}
    )


def _verify_manifest_inventory(receipt, generation, manifest_sha256):
    objects = receipt["verified_objects"]
    count, size = receipt["file_count"], receipt["total_bytes"]
    written = receipt["publication"]
    if (
        not isinstance(objects, list)
        or type(count) is not int
        or count <= 0
        or len(objects) != count
        or type(written["file_count"]) is not int
        or written["file_count"] != count
        or type(size) is not int
        or size < 0
        or type(written["total_bytes"]) is not int
        or written["total_bytes"] != size
    ):
        raise PublicationEvidenceError("Verified object inventory has invalid counts or totals")
    paths = set()
    actual_bytes = 0
    reuse = False
    for item in objects:
        if not isinstance(item, dict) or set(item) - {"storage_generation"} != {
            "path",
            "size_bytes",
            "sha256",
        }:
            raise PublicationEvidenceError("Verified object inventory has invalid records")
        path, length = item["path"], item["size_bytes"]
        if (
            not _safe_path(path)
            or path in paths
            or type(length) is not int
            or length < 0
            or not _matches(SHA, item["sha256"])
        ):
            raise PublicationEvidenceError("Verified object inventory has invalid paths or hashes")
        if "storage_generation" in item:
            origin = item["storage_generation"]
            if not _matches(GENERATION, origin) or origin in {generation, "legacy"}:
                raise PublicationEvidenceError(
                    "Verified object inventory has an invalid storage generation"
                )
            reuse = True
        paths.add(path)
        actual_bytes += length
    # Current publishers serialize the same three manifest fields in schemas 1 and 2.
    # A schema 2 inventory may have no borrowed entries.
    possible_schemas = (2,) if reuse else (1, 2)
    hashes = {
        _sha(
            (
                json.dumps(
                    dict(schema_version=version, generation_id=generation, files=objects),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode()
        )
        for version in possible_schemas
    }
    if actual_bytes != size or manifest_sha256 not in hashes:
        raise PublicationEvidenceError(
            "Verified object inventory does not match the prepared manifest"
        )


def _verify_deployed_health_and_readiness(receipt, run_id, digest, generation, activation):
    body, status = receipt["deployed_readiness"], receipt["deployed_readiness_http_status"]
    if (
        not isinstance(body, dict)
        or body.get("active_generation") != generation
        or type(status) is not int
        or type(body.get("ready")) is not bool
        or body.get("immutable_generation") is not True
    ):
        raise PublicationEvidenceError(
            "Verified readiness does not match the generation or HTTP contract"
        )
    ready = body["ready"]
    strict = (
        status == 200 and ready and body.get("status") == "ready" and body.get("blockers") == []
    )
    snapshot = activation and status == 503 and snapshot_live_gap_matches(body, generation)
    if not (strict or snapshot) or (
        activation and receipt.get("operational_acceptance_complete") is not ready
    ):
        raise PublicationEvidenceError("Verified readiness failed the publication policy")
    if (
        "deployed_health" not in receipt
        and (run_id, receipt["workflow_sha"], digest) == CLEVELAND_LEGACY_HEALTH_RECEIPT
    ):
        return
    health = receipt.get("deployed_health")
    if (
        not isinstance(health, dict)
        or type(health.get("http_status")) is not int
        or health["http_status"] != 200
        or health.get("status") != "ok"
    ):
        raise PublicationEvidenceError("Verified deployment health is missing or unsuccessful")


def _rows_match(wanted, actual):
    return (
        isinstance(wanted, list)
        and wanted
        and isinstance(actual, list)
        and len(actual) == len(wanted)
        and all(
            isinstance(row, dict)
            and isinstance(fields, dict)
            and fields
            and all(
                k in row and row[k] == v and (type(v) is bool) == (type(row[k]) is bool)
                for k, v in fields.items()
            )
            for fields, row in zip(wanted, actual, strict=True)
        )
    )


def _verify_deployed_answers(receipt, package):
    checks, answers = package["deployed_checks"], receipt["deployed_answers"]
    attempts = receipt["deployed_query_attempts"]
    if (
        not isinstance(checks, list)
        or not checks
        or not isinstance(answers, list)
        or len(answers) != len(checks)
        or not isinstance(attempts, list)
        or any(
            not isinstance(attempt, dict)
            or any(type(attempt.get(key)) is not int for key in ("index", "attempt", "status"))
            for attempt in attempts
        )
    ):
        raise PublicationEvidenceError(
            "Deployment answers or HTTP attempts lack complete registered records"
        )
    ordered_attempts = iter(attempts)
    for index, (check, answer) in enumerate(zip(checks, answers, strict=True), 1):
        query = check["query"]
        if (
            not isinstance(query, str)
            or not query.strip()
            or not isinstance(answer, dict)
            or answer.get("query") != query
            or ("summary" in check) == ("sections" in check)
        ):
            raise PublicationEvidenceError(
                "Deployment answers differ from the ordered registered checks"
            )
        if "summary" in check:
            same = set(answer) == {"query", "summary"} and _rows_match(
                [check["summary"]], [answer["summary"]]
            )
        else:
            sections, actual = check["sections"], answer.get("sections")
            same = (
                isinstance(sections, dict)
                and sections
                and set(answer) == {"query", "sections"}
                and isinstance(actual, dict)
                and sections.keys() == actual.keys()
                and all(_rows_match(wanted, actual[key]) for key, wanted in sections.items())
            )
        if not same:
            raise PublicationEvidenceError(
                "Deployment answers differ from the registered values or rows"
            )
        first = next(ordered_attempts, {})
        if (first.get("index"), first.get("query"), first.get("attempt")) != (index, query, 1):
            raise PublicationEvidenceError(
                "Deployment HTTP attempts differ from the registered check order"
            )
        final = next(ordered_attempts, {}) if first["status"] == 429 else first
        expected_attempt = 2 if first["status"] == 429 else 1
        if (final.get("index"), final.get("query"), final.get("attempt"), final.get("status")) != (
            index,
            query,
            expected_attempt,
            200,
        ):
            raise PublicationEvidenceError(
                "Deployment HTTP attempts lack a verified successful response"
            )
    if next(ordered_attempts, None) is not None:
        raise PublicationEvidenceError("Deployment HTTP attempts include unregistered checks")


def _download(url, *, token=None, accept="application/vnd.github+json"):
    request = Request(url, headers={"User-Agent": "nbatools-production-monitor", "Accept": accept})
    if token:
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=GITHUB_REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raise PublicationEvidenceError("GitHub publication evidence exceeds its response bound")
    return raw


class GitHubPublicationEvidence:
    """Use the existing token for repository reads and public Actions evidence."""

    def __init__(self, token=None):
        self.token = token

    def api(self, path, *, public_actions=False):
        try:
            return json.loads(_download(API + path, token=self.token))
        except HTTPError as exc:
            if not (public_actions and self.token and exc.code in {403, 404}):
                raise
        return json.loads(_download(API + path))

    def receipt(self, tag):
        url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/receipt.json"
        return _download(url, accept="application/octet-stream")

    def registry(self, sha):
        return _download(
            f"{API}/contents/{REGISTRY_PATH}?ref={sha}",
            token=self.token,
            accept="application/vnd.github.raw+json",
        )


def _read_receipt(client, release, run_id):
    tag, commit = release["tag_name"], release["target_commitish"]
    assets = [asset for asset in release["assets"] if asset["name"] == "receipt.json"]
    if (
        release["draft"] is not False
        or release["prerelease"] is not False
        or release["author"]["login"] != "github-actions[bot]"
        or not _matches(GIT_SHA, commit)
        or len(assets) != 1
    ):
        raise PublicationEvidenceError(
            "Publication release does not match the durable receipt format"
        )
    asset = assets[0]
    if (
        asset["state"] != "uploaded"
        or asset["uploader"]["login"] != "github-actions[bot]"
        or type(asset["size"]) is not int
        or not 0 < asset["size"] <= MAX_BODY_BYTES
    ):
        raise PublicationEvidenceError("Publication receipt asset is invalid")
    raw = client.receipt(tag)
    digest = _sha(raw)
    if len(raw) != asset["size"] or asset["digest"] != f"sha256:{digest}":
        raise PublicationEvidenceError("Publication receipt asset does not match GitHub's digest")
    receipt = json.loads(raw)
    if (
        type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != 1
        or receipt["workflow_run_id"] != run_id
        or receipt["workflow_sha"] != commit
    ):
        raise PublicationEvidenceError("Publication receipt and release identities differ")
    return receipt, digest


def _verified_publication(client, release, run_id, receipt, receipt_digest):
    state, commit = receipt["publication_state"], receipt["workflow_sha"]
    operation, action = VERIFIED_STATES[state]
    generation = receipt["generation_id"]
    manifest = receipt["prepared_manifest_sha256"]
    previous = receipt["base_generation"]
    pointer, publication = receipt["verified_pointer"], receipt["publication"]
    if (
        not _matches(GENERATION, generation)
        or not _matches(GENERATION, previous)
        or not _matches(SHA, manifest)
        or previous == generation
        or pointer["generation_id"] != generation
        or type(pointer["schema_version"]) is not int
        or pointer["schema_version"] != 1
        or pointer["manifest_sha256"] != manifest
        or pointer["previous_generation_id"] != previous
        or _time(pointer["published_at"]) > _time(release["published_at"])
        or publication["target"] != "r2"
        or publication["action"] != action
        or publication["generation_id"] != generation
        or publication["manifest_sha256"] != manifest
        or publication["pointer"] != "metadata/active_generation.json"
        or publication["previous_generation_id"] != previous
    ):
        raise PublicationEvidenceError(
            "Verified publication disagrees with its pointer or manifest"
        )
    _verify_manifest_inventory(receipt, generation, manifest)
    _verify_deployed_health_and_readiness(
        receipt, run_id, receipt_digest, generation, operation == "activate_candidate"
    )

    tag = release["tag_name"]
    ref = client.api(f"/git/ref/tags/{tag}")
    run = client.api(f"/actions/runs/{run_id}", public_actions=True)
    if (
        ref["ref"] != f"refs/tags/{tag}"
        or ref["object"]["type"] != "commit"
        or ref["object"]["sha"] != commit
        or type(run["id"]) is not int
        or str(run["id"]) != run_id
        or run["repository"]["full_name"] != REPOSITORY
        or run["path"] != WORKFLOW_PATH
        or run["event"] != "workflow_dispatch"
        or run["head_branch"] != "main"
        or run["head_sha"] != commit
        or type(run["run_attempt"]) is not int
        or run["run_attempt"] != 1
    ):
        raise PublicationEvidenceError(
            "Publication release does not bind its original main workflow"
        )
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise PublicationEvidenceError("Publication workflow is not a completed success")

    raw_registry = client.registry(commit)
    if _sha(raw_registry) != receipt["registry_sha256"]:
        raise PublicationEvidenceError(
            "Publication receipt differs from its exact reviewed registry"
        )
    registry = json.loads(raw_registry)
    package = registry["packages"][receipt["package"]]
    if (
        registry["repository"] != REPOSITORY
        or registry["environment"] != "r2-publication"
        or package["generation_id"] != generation
        or package["publisher_sha"] != receipt["publisher_sha"]
        or operation not in package.get("operations", ("validate", "publish"))
        or operation == "activate_candidate"
        and (
            package["activation"] != receipt["activation_evidence"]
            or package["activation"]["manifest_sha256"] != manifest
            or receipt["previous_manifest_preserved"] is not True
        )
    ):
        raise PublicationEvidenceError("Publication receipt does not match the approved operation")
    _verify_deployed_answers(receipt, package)
    return VerifiedPublication(generation, manifest, state, run_id, commit, receipt_digest)


def resolve_verified_publication(client: GitHubPublicationEvidence) -> VerifiedPublication:
    """Select the latest accepted pointer switch without trusting the serving app."""
    try:
        releases = client.api("/releases?per_page=100")
        publication_releases = []
        for release in releases:
            match = RELEASE_TAG.fullmatch(release["tag_name"])
            if match and release["published_at"] is not None:
                publication_releases.append((_time(release["published_at"]), match[1], release))
        for _, run_id, release in sorted(
            publication_releases, key=lambda item: item[0], reverse=True
        )[:MAX_RECEIPTS_PER_PROBE]:
            receipt, receipt_digest = _read_receipt(client, release, run_id)
            state = receipt["publication_state"]
            if state in NON_SWITCH_STATES:
                continue
            if state not in VERIFIED_STATES:
                raise PublicationEvidenceError("Unrecognized durable publication outcome")
            return _verified_publication(client, release, run_id, receipt, receipt_digest)
    except PublicationEvidenceError:
        raise
    except (OSError, HTTPException, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise PublicationEvidenceError(
            "GitHub publication evidence could not be read or parsed"
        ) from exc
    raise PublicationEvidenceError(
        "No independently verified publication in the bounded receipt history"
    )
