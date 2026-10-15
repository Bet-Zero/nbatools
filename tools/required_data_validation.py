"""Fail closed on required numerical tests; write counts even when pytest fails.

Used only by the manual R2 workflow. Ordinary pytest keeps its data-free skip
behavior. All selected needs_data tests are required here, including skips and
expected failures: a successful collection or an xfail is not numeric evidence.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest


class RequiredResults:
    def __init__(self) -> None:
        self.selected: set[str] = set()
        self.executed: set[str] = set()
        self.passed: set[str] = set()
        self.skipped: set[str] = set()
        self.failed: set[str] = set()
        self.errors: set[str] = set()
        self.xfailed: set[str] = set()

    def pytest_collection_finish(self, session) -> None:
        self.selected.update(item.nodeid for item in session.items)

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node, ids) -> None:
        self.selected.update(ids)

    def pytest_collectreport(self, report) -> None:
        if report.failed:
            self.errors.add(report.nodeid)
        if report.skipped:
            self.skipped.add(report.nodeid)

    def pytest_runtest_logreport(self, report) -> None:
        if report.when == "call":
            self.executed.add(report.nodeid)
            if report.passed:
                self.passed.add(report.nodeid)
        if report.skipped:
            self.skipped.add(report.nodeid)
        if report.failed:
            target = self.failed if report.when == "call" else self.errors
            target.add(report.nodeid)
        if hasattr(report, "wasxfail"):
            self.xfailed.add(report.nodeid)

    def counts(self) -> dict[str, int]:
        successful = self.passed - self.skipped - self.failed - self.errors - self.xfailed
        return {
            "selected": len(self.selected),
            "executed": len(self.executed),
            "passed": len(successful),
            "skipped": len(self.skipped),
            "failed": len(self.failed),
            "errors": len(self.errors),
            "xfailed": len(self.xfailed),
        }


def required_selection(scope: str, value: str) -> list[str]:
    if scope == "full":
        return []
    if scope != "targeted":
        raise ValueError("scope must be full or targeted")
    selection = value.split()
    if not selection:
        raise ValueError("Targeted required numerical selection is empty")
    for test_id in selection:
        if not re.fullmatch(r"tests/[][A-Za-z0-9_./:-]+", test_id) or ".." in test_id:
            raise ValueError(f"Invalid test path or node id: {test_id}")
    return selection


def main() -> int:
    output = Path("outputs/required_data_validation")
    output.mkdir(parents=True, exist_ok=True)
    results = RequiredResults()
    problems: list[str] = []
    selection: list[str] = []
    pytest_exit: int | None = None
    actual_sha = ""
    generation = os.environ.get("NBATOOLS_DATA_GENERATION", "")
    try:
        selection = required_selection(os.environ.get("SCOPE", ""), os.environ.get("TESTS", ""))
        actual_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        expected_sha = os.environ.get("VALIDATION_SHA", "")
        if not re.fullmatch(r"[a-f0-9]{40}", expected_sha) or actual_sha != expected_sha:
            raise ValueError("Checkout does not match the preflight-resolved candidate SHA")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", generation) or generation == "legacy":
            raise ValueError("Required numerical validation needs a pinned immutable generation")
        pytest_exit = int(
            pytest.main(
                [
                    "-m",
                    "needs_data",
                    "-rf",
                    "--no-header",
                    "-q",
                    f"--junitxml={output / 'junit.xml'}",
                    *selection,
                ],
                plugins=[results],
            )
        )
        for selector in selection:
            prefix = selector.rstrip("/")
            if not any(
                nodeid == prefix
                or nodeid.startswith(prefix + "::")
                or nodeid.startswith(prefix + "[")
                or nodeid.startswith(prefix + "/")
                for nodeid in results.selected
            ):
                problems.append(f"Required selector matched no needs_data tests: {selector}")
    except Exception as exc:
        problems.append(f"Validation execution error: {type(exc).__name__}: {exc}")

    counts = results.counts()
    if pytest_exit != 0:
        problems.append(f"pytest did not succeed (exit={pytest_exit})")
    if not counts["selected"] or counts["passed"] != counts["selected"]:
        problems.append("Every selected required test must execute and pass")
    if any(counts[key] for key in ("skipped", "failed", "errors", "xfailed")):
        problems.append("Required tests contain skips, failures, errors, or expected failures")
    report = {
        "candidate_sha": actual_sha,
        "generation": generation,
        "scope": os.environ.get("SCOPE", ""),
        "required_selection": selection,
        **counts,
        "pytest_exit": pytest_exit,
        "conclusion": "failure" if problems else "success",
        "problems": problems,
    }
    rendered = json.dumps(report, indent=2)
    (output / "summary.json").write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write("## Required numerical validation\n\n```json\n" + rendered + "\n```\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
