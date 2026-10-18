"""Validate the existing R2 workflow's request before any credential-bearing job.

Automatic requests are one manifest-only commit on already reviewed candidate
code. This binds evidence to that code; it does not manufacture review approval.
This module is standard-library-only so it can run before project installation.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REQUEST_PATH = Path(".github/r2-validation-request.json")
MAX_REQUEST_BYTES = 8192
MAX_SELECTORS = 20
MAX_CASES = 20
REPOSITORY = "Bet-Zero/nbatools"
SHA = re.compile(r"[a-f0-9]{40}")
TEST = re.compile(r"tests/[][A-Za-z0-9_./:-]+")
CASE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
GENERATION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate request field: {key}")
        result[key] = value
    return result


def _selection(value, *, tests: bool, automatic: bool) -> list[str]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise ValueError("Selections must be arrays of strings")
    if automatic and len(value) > (MAX_SELECTORS if tests else MAX_CASES):
        raise ValueError("Automatic selection exceeds its targeted request limit")
    if len(value) != len(set(value)):
        raise ValueError("Duplicate selectors are not allowed")
    for item in value:
        pattern = TEST if tests else CASE
        if len(item) > 256 or not pattern.fullmatch(item) or ".." in item:
            raise ValueError(f"Invalid {'test selector' if tests else 'Raw QA case id'}: {item!r}")
        if tests:
            file = Path(item.split("::", 1)[0])
            if file.suffix != ".py" or not file.is_file() or file.is_symlink():
                raise ValueError("Test selectors must name existing Python files or node ids")
            if not file.resolve().is_relative_to(Path("tests").resolve()):
                raise ValueError("Test selectors must remain inside tests/")
    return value


def resolve_request(env: dict[str, str]) -> dict[str, str]:
    actual_sha = _git("rev-parse", "HEAD")
    if not SHA.fullmatch(actual_sha):
        raise ValueError("Checkout has no resolved candidate SHA")
    event_name = env.get("GITHUB_EVENT_NAME")
    if generation := env.get("BACKUP_GENERATION", ""):
        if (
            event_name != "workflow_dispatch"
            or env.get("GITHUB_REPOSITORY") != REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_SHA") != actual_sha
            or env.get("GITHUB_WORKFLOW_REF")
            != f"{REPOSITORY}/.github/workflows/r2-data-publication.yml@refs/heads/main"
        ):
            raise ValueError("Automatic backup requires the trusted main publication caller")
        if not GENERATION.fullmatch(generation) or generation == "legacy":
            raise ValueError("Automatic backup requires a pinned immutable generation")
        # The caller runs only after protected owner approval, successful
        # publication and live verification. Source is reviewed merged main;
        # callers cannot supply arbitrary tests, scripts, branches or cases.
        tests = _selection(
            ["tests/cloud_operations_real_data.py::test_full_generation_backup"],
            tests=True,
            automatic=True,
        )
        cases, scope, reviewed_sha, automatic = [], "targeted", actual_sha, "true"
    elif event_name == "push":
        event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        repository = event.get("repository", {})
        if (
            env.get("GITHUB_REPOSITORY") != REPOSITORY
            or repository.get("full_name") != REPOSITORY
            or repository.get("fork") is not False
            or not env.get("GITHUB_REF", "").startswith("refs/heads/r2-validation/")
            or event.get("ref") != env["GITHUB_REF"]
            or event.get("deleted") is not False
            or event.get("after") != actual_sha
            or env.get("GITHUB_SHA") != actual_sha
        ):
            raise ValueError(
                "Automatic validation requires this repository's dedicated-branch push SHA"
            )
        if REQUEST_PATH.is_symlink() or not REQUEST_PATH.is_file():
            raise ValueError("Automatic validation requires a regular request manifest")
        if REQUEST_PATH.stat().st_size > MAX_REQUEST_BYTES:
            raise ValueError("Automatic request exceeds 8 KiB")
        request = json.loads(
            REQUEST_PATH.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
        required = {"schema_version", "reviewed_sha", "generation", "tests", "raw_qa_cases"}
        if not isinstance(request, dict) or set(request) != required:
            raise ValueError("Automatic request must contain exactly the documented schema fields")
        if type(request["schema_version"]) is not int or request["schema_version"] != 1:
            raise ValueError("Unsupported automatic request schema_version")
        reviewed_sha = request["reviewed_sha"]
        if not isinstance(reviewed_sha, str) or not SHA.fullmatch(reviewed_sha):
            raise ValueError("reviewed_sha must be an exact commit SHA")
        if _git("rev-list", "--parents", "-n", "1", "HEAD").split() != [actual_sha, reviewed_sha]:
            raise ValueError(
                "Request commit must have exactly the reviewed candidate as its parent"
            )
        changed = _git("diff", "--name-only", reviewed_sha, actual_sha).splitlines()
        if changed != [REQUEST_PATH.as_posix()]:
            raise ValueError(
                "Request commit may change only the request manifest, never candidate code"
            )
        generation = request["generation"]
        if (
            not isinstance(generation, str)
            or not GENERATION.fullmatch(generation)
            or generation == "legacy"
        ):
            raise ValueError("Automatic request requires a pinned immutable generation")
        tests = _selection(request["tests"], tests=True, automatic=True)
        cases = _selection(request["raw_qa_cases"], tests=False, automatic=True)
        if not tests and not cases:
            raise ValueError("Automatic targeted validation requires tests or Raw QA cases")
        scope = "targeted"
        automatic = "true"
    elif event_name == "workflow_dispatch":
        scope = env.get("SCOPE", "")
        if scope not in {"full", "targeted"}:
            raise ValueError("scope must be full or targeted")
        values = [env.get("TESTS", ""), env.get("RAW_QA_CASES", "")]
        if scope == "targeted" and (
            not any(value.strip() for value in values)
            or any(value and not value.strip() for value in values)
        ):
            raise ValueError("Targeted validation requires nonempty tests or Raw QA cases")
        tests = (
            _selection(values[0].split(), tests=True, automatic=False)
            if scope == "targeted"
            else []
        )
        cases = (
            _selection(values[1].split(), tests=False, automatic=False)
            if scope == "targeted"
            else []
        )
        generation = ""  # Dispatch retains preflight resolution of the active generation.
        reviewed_sha = actual_sha
        automatic = "false"
    else:
        raise ValueError("Only dedicated pushes and workflow_dispatch are supported")
    return {
        "candidate_sha": actual_sha,
        "reviewed_sha": reviewed_sha,
        "generation": generation,
        "scope": scope,
        "tests": " ".join(tests),
        "raw_qa_cases": " ".join(cases),
        "automatic": automatic,
    }


def main() -> int:
    try:
        request = resolve_request(dict(os.environ))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"Invalid R2 validation request: {exc}")
        return 1
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
        for key, value in request.items():
            handle.write(f"{key}={value}\n")
    rendered = json.dumps(request, indent=2)
    print(rendered)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write("## Resolved R2 validation request\n\n```json\n" + rendered + "\n```\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
