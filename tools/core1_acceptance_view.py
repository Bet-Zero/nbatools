"""One-command Core-1 acceptance view.

Prints every K01-K12 row and each of the 46 original K08 questions as
PASS / SOFTWARE FAILURE / MISSING DATA / LIVE, against whatever data generation
the environment serves (local root or R2). No new framework: the K rows run the
existing ``tests/test_kNN_*_real_data.py`` verifiers, and K08 asks the app over
HTTP and compares with expectations fixed in ``core1-acceptance-map.json``.
Those expectations come from independent oracles or qualified stages, never
from the run being scored.

Usage::

    python tools/core1_acceptance_view.py [--output view.json] [--skip-pytest]

Exit status is 1 when any row is a SOFTWARE FAILURE, else 0. MISSING DATA means
the app refused honestly; an app that answers a missing-data question with
numbers is a SOFTWARE FAILURE, because that answer could only come from
inferring absence from missing rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "working/nba-tools-completion-program/core1-acceptance-map.json"
PASS, FAIL, MISSING, LIVE = "PASS", "SOFTWARE FAILURE", "MISSING DATA", "LIVE"


DATA_ENV = ("DATA_SOURCE", "NBATOOLS_DATA_ROOT", "NBATOOLS_DATA_GENERATION")


def _pytest(nodes, *, synthetic=False):
    """Run pytest node ids once; return one (file, class, name, outcome) per test.

    Synthetic unit tests build their own data, so they run without the
    data-source environment that points the real-data verifiers at a generation.
    """
    env = {k: v for k, v in os.environ.items() if not (synthetic and k in DATA_ENV)}
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        cmd += [f"--junitxml={junit}", "--rootdir", str(ROOT), "-c", str(ROOT / "pyproject.toml")]
        # Absolute node ids, so the caller's working directory (which decides
        # where local data is found) is kept.
        subprocess.run(
            [*cmd, *(str(ROOT / n) for n in nodes)], cwd=os.getcwd(), env=env, check=False
        )
        cases = ET.parse(junit).getroot().iter("testcase") if junit.exists() else []
        results = []
        for case in cases:
            outcome = "passed"
            for child in case:
                if child.tag in {"failure", "error"}:
                    outcome = "failed"
                elif child.tag == "skipped":
                    outcome = "skipped"
            path = case.get("file") or case.get("classname", "").replace(".", "/") + ".py"
            results.append((path, case.get("classname", ""), case.get("name", ""), outcome))
    return results


def _tally(results, wanted):
    """Counts for one test file or one node id from the junit results."""
    if "::" in wanted:
        path, rest = wanted.split("::", 1)
        name = rest.split("::")[-1]
        hits = [r for r in results if r[2] == name and Path(path).stem in r[1]]
    else:
        hits = [r for r in results if Path(wanted).stem in r[0] or Path(wanted).stem in r[1]]
    counts = {k: sum(r[3] == k for r in hits) for k in ("passed", "failed", "skipped")}
    return counts


def _verdict_from_counts(counts):
    # Nothing ran, or anything skipped, proves nothing: a skipped real-data
    # verifier usually means the data was not reachable.
    return PASS if counts["passed"] and not (counts["failed"] or counts["skipped"]) else FAIL


def _oracle_cases(spec):
    path = ROOT / spec["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError("independent K08 oracle archive changed")
    with ZipFile(path) as archive:
        oracle = json.loads(archive.read(spec["member"]))
    return {case["ordinal"]: case for case in oracle["cases"]}


def _short(body):
    sections = (body.get("result") or {}).get("sections") or {}
    summary = sections.get("summary") or sections.get("count")
    row = summary[0] if summary else None
    if isinstance(row, dict):
        keep = ("team_name", "player_name", "season_start", "games", "wins", "losses", "count")
        row = {k: row[k] for k in keep if k in row}
    return dict(status=body.get("result_status"), reason=body.get("result_reason"), first_row=row)


def _k08(entry, client, oracle, results):
    from tools.r2_publication import verify_answer

    observed, problems = [], []
    for query in entry.get("queries", []):
        body = client.post("/query", json={"query": query}).json()
        observed.append(dict(query=query, **_short(body)))
        answered = body.get("result_status") == "ok"
        expect, check = entry["expect"], entry.get("check", {})
        if expect == "missing_data" and answered:
            problems.append(f"answered without qualified data: {query!r}")
        if expect != "pass":
            continue
        try:
            if check["kind"] == "independent_oracle":
                from tests.core1_k08_served_default_cases import assert_answer

                assert_answer(body, oracle[entry["id"]])
            elif check["kind"] == "answers":
                case = next(c for c in check["cases"] if c["query"] == query)
                verify_answer(case, body)
            elif check["kind"] == "no_match":
                metadata = (body.get("result") or {}).get("metadata") or {}
                assert body.get("route") == check["route"], body.get("route")
                assert (body.get("result_status"), body.get("result_reason")) == (
                    "no_result",
                    "no_match",
                ), _short(body)
                assert metadata.get("without_player") == check["without_player"], metadata
                rest = client.post("/query", json={"query": check["rest_count_case"]["query"]})
                verify_answer(check["rest_count_case"], rest.json())
        except (AssertionError, ValueError, KeyError, StopIteration) as exc:
            problems.append(f"{query!r}: {type(exc).__name__}: {str(exc)[:300]}")
    for node in entry.get("check", {}).get("pytest", []):
        counts = _tally(results, node)
        if _verdict_from_counts(counts) != PASS:
            problems.append(f"{node}: {counts}")
    if problems:
        verdict = FAIL
    else:
        verdict = {"pass": PASS, "missing_data": MISSING, "live": LIVE}[entry["expect"]]
    return dict(
        id=entry["id"], verdict=verdict, why=entry["reason"], problems=problems, observed=observed
    )


def build_view(*, run_pytest=True):
    spec = json.loads(MAP.read_bytes())
    real = [t for group in spec["groups"].values() for t in group["tests"]]
    unit = [n for e in spec["k08"] for n in e.get("check", {}).get("pytest", [])]
    results = _pytest(real) + _pytest(unit, synthetic=True) if run_pytest else []

    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.data_source import data_generation_context

    with data_generation_context() as generation:
        served = generation
    client = TestClient(app)
    oracle = _oracle_cases(spec["independent_oracle"])
    k08 = [_k08(entry, client, oracle, results) for entry in spec["k08"]]
    groups = {}
    for key, group in spec["groups"].items():
        if key == "K08":
            counts = {v: sum(r["verdict"] == v for r in k08) for v in (PASS, FAIL, MISSING, LIVE)}
            # The group passes only when every original question does; refusals
            # for missing data are honest but still not passes.
            verdict = FAIL if counts[FAIL] else MISSING if counts[MISSING] else PASS
        elif not run_pytest:
            verdict, counts = "NOT RUN", {}
        else:
            per = [_tally(results, t) for t in group["tests"]]
            counts = {k: sum(c[k] for c in per) for k in ("passed", "failed", "skipped")}
            verdict = _verdict_from_counts(counts)
        groups[key] = dict(
            name=group["name"], verdict=verdict, counts=counts, note=group.get("note")
        )
    return dict(generation=served, groups=groups, k08=k08)


def render(view):
    lines = [f"Core-1 acceptance view on generation {view['generation']}", ""]
    for key, row in view["groups"].items():
        counts = ", ".join(f"{k} {v}" for k, v in row["counts"].items())
        lines.append(f"{key}  {row['verdict']:<16} {row['name']}  ({counts})")
        if row.get("note"):
            lines.append(f"      note: {row['note']}")
    lines += ["", "K08 original questions:"]
    for row in view["k08"]:
        first = row["observed"][0]["query"] if row["observed"] else "(structured-route test)"
        lines.append(f"  {row['id']:>2}  {row['verdict']:<16} {first}")
        for problem in row["problems"]:
            lines.append(f"        problem: {problem}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args(argv)
    view = build_view(run_pytest=not args.skip_pytest)
    print(render(view))
    if args.output:
        args.output.write_text(json.dumps(view, indent=2, default=str) + "\n")
    failed = [k for k, r in view["groups"].items() if r["verdict"] == FAIL]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
