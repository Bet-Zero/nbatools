"""Reconcile one authenticated full R2 run with the frozen Section 6 scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

from tools.raw_query_answer_qa import (
    failed_case_ids_from_rows,
    load_corpus,
    review_output_sha256,
    selected_cases_sha256,
)

SCOPE = Path("working/nba-tools-completion-program/stabilization-release-scope-20261127.json")
CORPUS = Path("qa/raw_query_answer_corpus.yaml")
FILTER_CONFIG = Path("qa/filter_execution_sweep.yaml")
ACTIONS = "repos/Bet-Zero/nbatools/actions/runs"
ARTIFACTS = ("required-numerical", "raw-qa", "filter-sweep")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def node_id(case):
    package, module, *classes = case.attrib["classname"].split(".")
    require(package == "tests" and module.startswith("test_"), "Unexpected pytest location")
    return "::".join([f"{package}/{module}.py", *classes, case.attrib["name"]])


def failure_fingerprint(message):
    first_line = message.splitlines()[0]
    # Runner-local interpreter and pytest work paths vary across executions.
    first_line = re.sub(r"'[^']+/bin/python[0-9.]*'", "'<python>'", first_line)
    first_line = re.sub(r"/tmp/pytest-of-[^']+", "<pytest-work>", first_line)
    return hashlib.sha256(first_line.encode()).hexdigest()


def verify_artifacts(run, source, paths):
    def github(url):
        return json.loads(subprocess.check_output(["gh", "api", url]))

    workflow = github(f"{ACTIONS}/{run}")
    require(
        workflow["path"] == ".github/workflows/r2-real-data-validation.yml"
        and workflow["event"] == "workflow_dispatch"
        and workflow["status"] == "completed"
        and workflow["head_sha"] == source,
        "Run does not identify a completed R2 validation workflow at this revision",
    )
    artifacts = github(f"{ACTIONS}/{run}/artifacts")["artifacts"]
    ids = {}
    for name, path in zip(ARTIFACTS, paths, strict=True):
        matches = [item for item in artifacts if item["name"] == f"{name}-{run}"]
        require(len(matches) == 1, f"Missing or duplicate workflow artifact: {name}")
        artifact = matches[0]
        require(
            artifact["workflow_run"]["id"] == run
            and artifact["workflow_run"]["head_sha"] == source
            and artifact["digest"] == "sha256:" + digest(path),
            f"Artifact digest, workflow run or revision differs: {name}",
        )
        ids[name] = artifact["id"]
    return ids


def numerical(archive, source, generation, scope):
    summary = json.loads(archive.read("summary.json"))
    cases = ElementTree.fromstring(archive.read("junit.xml")).findall(".//testcase")
    nodes = sorted(node_id(case) for case in cases)
    failed = {
        node_id(case): failure_fingerprint(failure.attrib["message"])
        for case in cases
        if (failure := case.find("failure")) is not None
    }
    require(
        (summary["candidate_sha"], summary["generation"], summary["scope"])
        == (source, generation, "full")
        and len(set(nodes)) == len(cases) == summary["selected"] == summary["executed"] > 0
        and len(failed) == summary["failed"]
        and summary["passed"] + summary["failed"] == len(cases)
        and not any(summary[key] for key in ("skipped", "errors", "xfailed"))
        and all(case.find("skipped") is None and case.find("error") is None for case in cases)
        and hashlib.sha256("\n".join(nodes).encode()).hexdigest() == scope["population_sha256"],
        "Numerical run has a different identity, population, or inconsistent counts",
    )
    records = [
        (node, (category, fingerprint))
        for category, cohorts in scope["failures"].items()
        for failures in cohorts.values()
        for node, fingerprint in failures.items()
    ]
    expected = dict(records)
    require(len(records) == len(expected), "Duplicate numerical disposition")
    require(expected.keys() <= set(nodes), "Baseline numerical assertions absent")
    outside_snapshot = {
        node: expected[node][0]
        for node, fingerprint in failed.items()
        if node in expected
        and not expected[node][0].startswith("snapshot_")
        and fingerprint == expected[node][1]
    }
    return {
        "passed": summary["passed"],
        "full_gate": summary["conclusion"],
        "failures_outside_snapshot": dict(sorted(Counter(outside_snapshot.values()).items())),
        "snapshot_failures": sorted(failed.keys() - outside_snapshot.keys()),
    }


def raw_qa(archive, source, generation, scope):
    summary = json.loads(archive.read("summary.json"))
    rows = [json.loads(line) for line in archive.read("report.jsonl").splitlines()]
    ids = [row["id"] for row in rows]
    _, cases = load_corpus(CORPUS)
    failed = set(failed_case_ids_from_rows(rows))
    require(
        (summary["source_commit"], summary["data_generation"], summary["scope"])
        == (source, generation, "full_corpus")
        and summary["source_tree_clean"] is True
        and summary["corpus_sha256"] == digest(CORPUS)
        and summary["selected_cases_sha256"] == selected_cases_sha256(cases)
        and summary["output_sha256"] == review_output_sha256(rows)
        and len(set(ids)) == summary["case_count"] == len(ids) > 0
        and ids == summary["case_ids"] == [case["id"] for case in cases]
        and failed == set(summary["failed_case_ids"]),
        "Raw QA evidence identity or selection differs",
    )
    require(
        {ident for group in scope.values() for ident in group} <= set(ids),
        "Baseline Raw QA cases absent",
    )
    allowed = {
        "literal_current": {"no_data"},
        "full_participation_or_status": {"unsupported", "filter_not_supported"},
    }
    remaining = {
        row["id"]
        for category, reasons in allowed.items()
        for row in rows
        if row["id"] in failed
        and row["id"] in scope[category]
        and row["result_status"] == "no_result"
        and row["result_reason"] in reasons
    }
    return {
        "passed": len(rows) - len(failed),
        "full_failures": len(failed),
        "outside_snapshot": sorted(remaining),
        "snapshot_failures": sorted(failed - remaining),
    }


def filters(archive, generation, scope):
    document = json.loads(archive.read("r2_validation.json"))
    summary, rows = document["summary"], document["rows"]
    pairs = {(r["seed"], r["filter"]): r["verdict"] for r in rows}
    config = yaml.safe_load(FILTER_CONFIG.read_bytes())
    configured = {
        (seed["id"], flt["id"])
        for seed in config["seeds"]
        for flt in config["filters"]
        if seed["id"] not in (flt.get("skip_seeds") or [])
    }
    counters = Counter(pairs.values())
    require(
        summary["data_generation"] == generation
        and summary["config_sha256"] == digest(FILTER_CONFIG)
        and summary["only"] is None
        and len(pairs)
        == len(rows)
        == summary["configured_comparisons"]
        == summary["executed_comparisons"]
        > 0
        and counters == Counter(summary["verdict_counts"])
        and pairs.keys() == configured,
        "Filter evidence identity or selection differs",
    )
    floors = {
        tuple(pair)
        for category in ("already_applied", "bound_to_existing_consumer")
        for pair in scope[category]
    }
    no_signal = {tuple(pair) for pair in scope["no_signal"]}
    require(
        {tuple(pair) for group in scope.values() for pair in group} <= pairs.keys(),
        "Baseline filter combinations absent",
    )
    return {
        "verdicts": dict(sorted(counters.items())),
        "nondiscriminating_floors": sorted(floors),
        "snapshot_failures": [
            [*pair, verdict]
            for pair, verdict in pairs.items()
            if verdict in {"ERROR", "LIED"}
            or verdict == "DROPPED"
            and pair not in floors
            or verdict == "NO_SIGNAL"
            and pair not in no_signal
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--numerical", type=Path, required=True)
    parser.add_argument("--raw-qa", type=Path, required=True)
    parser.add_argument("--filter-sweep", type=Path, required=True)
    args = parser.parse_args()
    scope = json.loads(SCOPE.read_bytes())
    generation = scope["generation"]
    paths = (args.numerical, args.raw_qa, args.filter_sweep)
    artifacts = verify_artifacts(args.run, args.source, paths)
    with (
        ZipFile(args.numerical) as num,
        ZipFile(args.raw_qa) as raw,
        ZipFile(args.filter_sweep) as sweep,
    ):
        report = {
            "numerical": numerical(num, args.source, generation, scope["numerical"]),
            "raw_qa": raw_qa(raw, args.source, generation, scope["raw_qa"]),
            "filters": filters(sweep, generation, scope["filters"]),
        }
    print(
        json.dumps(
            {
                "run": args.run,
                "source": args.source,
                "generation": generation,
                "artifacts": artifacts,
                **report,
            },
            indent=2,
        )
    )
    return int(any(value["snapshot_failures"] for value in report.values()))


if __name__ == "__main__":
    raise SystemExit(main())
