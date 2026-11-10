"""Read-only exact GitHub Production deployment/source binding for actual D.

The repository's existing delivery-scope exclusions are mirrored explicitly;
all other tracked bytes and file modes must equal the deployed commit's tree.
This does not create share links, tokens, deployments or protection changes.
"""

import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime

import requests

from tests.core1_k08_served_default_cases import ROOT

API = "https://api.github.com/repos/Bet-Zero/nbatools/"
IMMUTABLE_HOST = re.compile(r"https://nbatools-[a-z0-9]+-brents-projects-686e97fc\.vercel\.app")


def non_build(path):
    return path in {
        "AGENTS.md",
        "ROADMAP.md",
        "working/nba-tools-completion-program/README.md",
        "frontend/tools/captureCoreIdentityFindCount.mjs",
        ".github/r2-validation-request.json",
    } or path.startswith(("tests/", "working/"))


def _github(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nbatools-bounded-core1-verification",
    }
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    response = requests.get(API + path, headers=headers, allow_redirects=False, timeout=30)
    assert response.status_code == 200, (
        f"Existing read-only GitHub route unavailable ({response.status_code})"
    )
    return response.json()


def _local_build_tree():
    raw = subprocess.check_output(["git", "ls-files", "-s", "-z"], cwd=ROOT)
    result = {}
    for entry in raw.decode().split("\0"):
        if not entry:
            continue
        fields, relative = entry.split("\t", 1)
        mode, _, stage = fields.split()
        assert stage == "0"
        if non_build(relative):
            continue
        path = ROOT / relative
        body = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        result[relative] = dict(mode=mode, sha=digest)
    assert result
    return result


def deployed_runtime_binding():
    deployments = _github("deployments?environment=Production&per_page=1")
    assert len(deployments) == 1
    deployment = deployments[0]
    assert deployment["environment"] == "Production"
    assert deployment["creator"]["login"] == "vercel[bot]"
    assert re.fullmatch(r"[a-f0-9]{40}", deployment["sha"])
    statuses = _github(f"deployments/{int(deployment['id'])}/statuses?per_page=1")
    assert len(statuses) == 1 and statuses[0]["state"] == "success"
    assert statuses[0]["creator"]["login"] == "vercel[bot]"
    url = statuses[0]["environment_url"].rstrip("/")
    assert IMMUTABLE_HOST.fullmatch(url), (
        "Only the existing project's immutable deployment host is allowed"
    )
    tree = _github(f"git/trees/{deployment['sha']}?recursive=1")
    assert tree["truncated"] is False
    remote = {
        entry["path"]: dict(mode=entry["mode"], sha=entry["sha"])
        for entry in tree["tree"]
        if entry["type"] == "blob" and not non_build(entry["path"])
    }
    local = _local_build_tree()
    assert local == remote, (
        "Served deployment is not byte-equivalent to the reviewed candidate's build inputs"
    )
    digest = hashlib.sha256(json.dumps(local, sort_keys=True).encode()).hexdigest()
    return dict(
        checked_at=datetime.now(UTC).isoformat(),
        classification="GitHub_Production_deployment_and_exact_immutable_host_source_binding",
        deployment=deployment,
        latest_status=statuses[0],
        base_url=url,
        deployed_sha=deployment["sha"],
        compared_build_files=len(local),
        build_input_tree_sha256=digest,
        candidate_build_inputs=local,
        source_requests=0,
        production_writes=0,
        access_changes=0,
    )
