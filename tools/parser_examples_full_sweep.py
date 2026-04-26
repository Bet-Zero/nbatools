# ruff: noqa: E501, I001

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from nbatools.cli import app as cli_app


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "docs/architecture/parser/examples.md"
OUT_DIR = ROOT / "outputs/parser_examples_full_sweep"
RAW_DIR = OUT_DIR / "raw"
RESULTS_PATH = OUT_DIR / "results.csv"
REPORT_PATH = OUT_DIR / "report.md"
MANIFEST_PATH = OUT_DIR / "manifest.json"

RESULT_FIELDS = [
    "case_id",
    "source_section",
    "source_subsection",
    "case_kind",
    "query_text",
    "expected_behavior_category",
    "expected_notes",
    "cli_exit_code",
    "result_status",
    "result_reason",
    "route",
    "query_class",
    "intent",
    "confidence",
    "has_alternates",
    "notes",
    "caveats",
    "pass_fail",
    "pass_fail_reason",
    "raw_json_path",
]


@dataclass(frozen=True)
class Case:
    case_id: str
    source_section: str
    source_subsection: str
    case_kind: str
    query_text: str
    expected_behavior_category: str
    expected_notes: str
    pair_key: str = ""
    equivalence_group: str = ""


def slug_subsection(title: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)*)", title)
    if not match:
        return "unknown"
    return match.group(1).replace(".", "_")


def clean_query(text: str) -> str:
    text = text.strip()
    text = text.strip("|")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def md_section(lines: list[str], start: str, end: str | None) -> list[str]:
    start_idx = next(i for i, line in enumerate(lines) if line.startswith(start))
    if end is None:
        end_idx = len(lines)
    else:
        end_idx = next(
            i
            for i, line in enumerate(lines[start_idx + 1 :], start_idx + 1)
            if line.startswith(end)
        )
    return lines[start_idx:end_idx]


def expected_for(query: str, section: str, subsection: str) -> tuple[str, str]:
    q = query.lower()
    sub = subsection.lower()
    boundary_terms = (
        "clutch",
        "4th quarter",
        "fourth quarter",
        "first half",
        "second half",
        "overtime",
        "back-to-back",
        "back to back",
        "b2b",
        "rest advantage",
        "rest disadvantage",
        "2 days rest",
        "one-possession",
        "one possession",
        "national tv",
        "nationally televised",
        "starter",
        "starting",
        "off the bench",
        "on/off",
        "on off",
        "on-off",
        "on the floor",
        "off the floor",
        "with and without",
        "lineup",
        "lineups",
        "units",
        "together",
    )
    opponent_quality_terms = (
        "contenders",
        "good teams",
        "top teams",
        "playoff teams",
        "teams over .500",
        "teams above .500",
        "top-10 defenses",
        "top 10 defenses",
        "top defenses",
        "winning teams",
        "top-5 offenses",
        "elite frontcourts",
        "above .600",
    )
    future_or_unsupported = (
        "co-star",
        "star teammate",
        "leading scorer",
        "cooled off",
        "best defense recently",
        "best net rating in its last",
        "averaged a double-double",
        "drop-off",
        "catch-and-shoot",
        "catch and shoot",
        "drawing fouls",
        "transition scorer",
        "isolation defender",
        "shot creator",
        "paint points",
        "biggest triple-double",
        "attempts per game",
        "two-way",
        "all-around",
        "all around",
        "rebounding battle",
        "leads the team in scoring",
        "both play",
        "trailing after 3 quarters",
        "10+ assists and 0 turnovers",
        "offensive rating when",
        "offensive rating without",
        "road by 20",
        "road team won by 20",
        "at __",
        "___",
        "since becoming a starter",
        "elite frontcourts",
    )

    if section.startswith("5."):
        if "ambiguous references" in sub or "ambiguous intent" in sub:
            return "ambiguous_expected", "Stress subsection documents this as ambiguous."
        return (
            "stress_clean_failure_ok",
            "Stress input; clean routed result, ambiguity, no-result, or unsupported response is acceptable.",
        )

    if section.startswith("8.1") or subsection.startswith("8.1"):
        return (
            "unsupported_expected",
            "Section 8.1 marks these as future expansion requiring new definitions or sources.",
        )
    if section.startswith("8.5") or subsection.startswith("8.5"):
        return "unsupported_expected", "Section 8.5 is a future expansion-pattern boundary."

    if any(term in q for term in future_or_unsupported):
        return (
            "unsupported_expected",
            "Examples/reference docs mark this broader semantic family as unsupported or outside the core finish line.",
        )

    if any(term in q for term in boundary_terms):
        return (
            "supported_with_fallback",
            "Context/source-backed family is coverage-gated or can carry an explicit unfiltered/unsupported-data note.",
        )

    if any(term in q for term in opponent_quality_terms):
        if any(term in q for term in ("top-5 offenses", "elite frontcourts", "above .600")):
            return (
                "unsupported_expected",
                "Opponent-quality variant is documented as future expansion.",
            )
        return (
            "supported_with_fallback",
            "Opponent-quality filters are supported on core single-entity routes; unsupported routes should note unfiltered behavior.",
        )

    if section.startswith("7.7") or section.startswith("7.8") or section.startswith("7.9"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated or unfiltered execution note.",
        )
    if section.startswith("7.10") or section.startswith("7.11") or section.startswith("7.12"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated execution note.",
        )
    if section.startswith("7.13") or section.startswith("7.14") or section.startswith("7.15"):
        return (
            "supported_with_fallback",
            "Equivalence group includes an explicit coverage-gated or unsupported-data execution note.",
        )
    if section.startswith("7.16") or section.startswith("7.17"):
        return "supported_with_fallback", "Lineup equivalence group is source-coverage gated."
    if (
        section.startswith("8.2")
        or section.startswith("8.3")
        or subsection.startswith("8.2")
        or subsection.startswith("8.3")
    ):
        return (
            "supported_with_fallback",
            "Expansion boundary is shipped only inside documented coverage-gated route boundaries.",
        )

    return (
        "supported_exact",
        "Documented shipped query surface or canonical parser example without an explicit fallback/unsupported note.",
    )


def add_case(
    cases: list[Case],
    case_id: str,
    section: str,
    subsection: str,
    kind: str,
    query: str,
    pair_key: str = "",
    equivalence_group: str = "",
) -> None:
    query = clean_query(query)
    if not query:
        return
    category, notes = expected_for(query, section, subsection)
    cases.append(
        Case(
            case_id=case_id,
            source_section=section,
            source_subsection=subsection,
            case_kind=kind,
            query_text=query,
            expected_behavior_category=category,
            expected_notes=notes,
            pair_key=pair_key,
            equivalence_group=equivalence_group,
        )
    )


def extract_cases() -> list[Case]:
    lines = SOURCE_PATH.read_text().splitlines()
    cases: list[Case] = []

    # Section 2 numbered canonical examples.
    current_sub = ""
    sub_counts: Counter[str] = Counter()
    for line in md_section(lines, "## 2.", "## 3."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if match and current_sub:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S2_{slug}_{sub_counts[slug]:02d}",
                "2. Canonical example set",
                current_sub,
                "canonical_numbered",
                match.group(2),
            )

    # Section 3 paired tables.
    current_sub = ""
    for line in md_section(lines, "## 3.", "## 4."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("|"):
            continue
        cells = [clean_query(c) for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].isdigit():
            continue
        slug = slug_subsection(current_sub)
        pair_num = int(cells[0])
        pair_key = f"S3_{slug}_{pair_num:02d}"
        add_case(
            cases,
            f"{pair_key}_Q",
            "3. Paired examples",
            current_sub,
            "paired_question",
            cells[1],
            pair_key=pair_key,
        )
        add_case(
            cases,
            f"{pair_key}_S",
            "3. Paired examples",
            current_sub,
            "paired_search",
            cells[2],
            pair_key=pair_key,
        )

    # Section 4 cluster bullet queries.
    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 4.", "## 5."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S4_{slug}_{sub_counts[slug]:02d}",
                "4. Capability clusters",
                current_sub,
                "cluster_bullet",
                query,
            )

    # Section 5 stress inputs. Split slash-delimited phrase sets into separate members.
    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 5.", "## 6."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            parts = [clean_query(part) for part in re.split(r"\s+/\s+", query)]
            if len(parts) > 1:
                for part in parts:
                    slug = slug_subsection(current_sub)
                    sub_counts[slug] += 1
                    add_case(
                        cases,
                        f"S5_{slug}_{sub_counts[slug]:02d}",
                        "5. Stress test inputs",
                        current_sub,
                        "stress_fragment",
                        part,
                    )
            else:
                slug = slug_subsection(current_sub)
                sub_counts[slug] += 1
                add_case(
                    cases,
                    f"S5_{slug}_{sub_counts[slug]:02d}",
                    "5. Stress test inputs",
                    current_sub,
                    "stress_input",
                    query,
                )

    # Section 6 worked raw inputs.
    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 6.", "## 7."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        match = re.match(r"^\*\*Raw input:\*\*\s+`([^`]+)`", line)
        if match:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S6_{slug}_{sub_counts[slug]:02d}",
                "6. End-to-end worked examples",
                current_sub,
                "worked_raw_input",
                match.group(1),
            )

    # Section 7 equivalence group members.
    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 7.", "## 8."):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- ") or line.startswith("- _"):
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S7_{slug}_{sub_counts[slug]:02d}",
                f"7.{slug.split('_', 1)[1] if '_' in slug else ''} Equivalence groups",
                current_sub,
                "equivalence_member",
                query,
                equivalence_group=f"S7_{slug}",
            )

    # Section 8 boundary examples and templates.
    current_sub = ""
    sub_counts = Counter()
    for line in md_section(lines, "## 8.", None):
        if line.startswith("### "):
            current_sub = line.removeprefix("### ").strip()
        if not line.startswith("- "):
            continue
        if line.startswith("- _") or "See equivalence" in line or "specification.md" in line:
            continue
        queries = re.findall(r"`([^`]+)`", line)
        for query in queries:
            if query.startswith("specification.md") or query in {
                "team_record",
                "player_game_summary",
                "player_game_finder",
            }:
                continue
            slug = slug_subsection(current_sub)
            sub_counts[slug] += 1
            add_case(
                cases,
                f"S8_{slug}_{sub_counts[slug]:02d}",
                "8. Expansion patterns and explicit boundaries",
                current_sub,
                "boundary_example",
                query,
            )

    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise RuntimeError(f"duplicate case id: {case.case_id}")
        seen.add(case.case_id)
    return cases


def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text()), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def infer_status(data: dict[str, Any] | None, exit_code: int, parse_error: str) -> tuple[str, str]:
    if exit_code != 0:
        return "cli_error", "nonzero_exit"
    if data is None:
        return "malformed_json", parse_error or "missing_json"
    metadata = data.get("metadata") if isinstance(data, dict) else {}
    status = metadata.get("result_status") if isinstance(metadata, dict) else None
    reason = metadata.get("result_reason") if isinstance(metadata, dict) else None
    if status:
        return str(status), str(reason or "")
    if "error" in data:
        return "error", "error_payload"
    if "no_result" in data:
        reason = ""
        payload = data.get("no_result")
        if isinstance(payload, list) and payload:
            reason = str(payload[0].get("reason", ""))
        return "no_result", reason
    return "ok", ""


def text_blob(data: dict[str, Any] | None) -> str:
    if data is None:
        return ""
    return json.dumps(data, ensure_ascii=False, sort_keys=True).lower()


def score_case(
    case: Case, data: dict[str, Any] | None, exit_code: int, status: str, reason: str
) -> tuple[str, str]:
    if exit_code != 0:
        return "fail", "CLI exited non-zero."
    if data is None:
        return "fail", "JSON output was missing or malformed."

    metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
    route = metadata.get("route")
    blob = text_blob(data)
    has_fallback_note = any(
        token in blob
        for token in (
            "unfiltered",
            "coverage",
            "unsupported",
            "no_result",
            "no matching",
            "empty sample",
            "fallback",
            "opponent_quality",
            "clutch",
            "placeholder",
        )
    )

    if case.expected_behavior_category == "supported_exact":
        if status == "ok" and route:
            if "unrouted" in reason:
                return "fail", "Supported example returned unrouted."
            return "pass", "Returned a routed structured result."
        if status == "no_result" and reason in {"no_matching_rows", "no_match"} and route:
            return "pass", "Supported route returned an honest no-match result."
        return (
            "fail",
            f"Expected routed supported behavior, got status={status or 'blank'} reason={reason or 'blank'}.",
        )

    if case.expected_behavior_category == "supported_with_fallback":
        if route and status in {"ok", "no_result", "unsupported", "error"}:
            if has_fallback_note or status in {"ok", "no_result", "unsupported"}:
                return "pass", "Coverage-gated/fallback family behaved honestly."
        return (
            "fail",
            f"Expected routed coverage-gated/fallback behavior, got status={status or 'blank'} reason={reason or 'blank'}.",
        )

    if case.expected_behavior_category == "ambiguous_expected":
        if reason == "ambiguous" or "ambiguous" in blob or "multiple entities" in blob:
            return "pass", "Ambiguity surfaced instead of a silent guess."
        if status in {"error", "no_result"} and not route:
            return "pass", "Ambiguous/stress input failed cleanly without a confident route."
        return (
            "fail",
            "Expected ambiguity or clean non-guessing behavior, but got a confident route/result.",
        )

    if case.expected_behavior_category == "unsupported_expected":
        if status in {"error", "no_result", "unsupported"} and not (status == "ok" and route):
            return "pass", "Unsupported/boundary example failed cleanly."
        if "unsupported" in blob or "out of scope" in blob:
            return "pass", "Unsupported/boundary example carried an explicit unsupported note."
        return (
            "fail",
            "Docs mark this boundary unsupported/future, but the product returned a supported result.",
        )

    if case.expected_behavior_category == "stress_clean_failure_ok":
        return "pass", "Stress input produced a clean CLI/JSON result."

    return "fail", "Unknown expected behavior category."


def execute_cases(cases: list[Case]) -> list[dict[str, str]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for old in RAW_DIR.glob("*.json"):
        old.unlink()

    runner = CliRunner()
    rows: list[dict[str, str]] = []
    for idx, case in enumerate(cases, start=1):
        raw_path = RAW_DIR / f"{case.case_id}.json"
        result = runner.invoke(cli_app, ["ask", case.query_text, "--json", str(raw_path)])
        data, parse_error = load_json(raw_path) if raw_path.exists() else (None, "missing_json")
        status, reason = infer_status(data, result.exit_code, parse_error)
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        notes = metadata.get("notes", []) if isinstance(metadata, dict) else []
        caveats = metadata.get("caveats", []) if isinstance(metadata, dict) else []
        alternates = metadata.get("alternates", []) if isinstance(metadata, dict) else []
        pass_fail, pass_fail_reason = score_case(case, data, result.exit_code, status, reason)
        if data is None:
            raw_path.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "query_text": case.query_text,
                            "result_status": status,
                            "result_reason": reason,
                        },
                        "execution_failure": {
                            "exit_code": result.exit_code,
                            "stdout": result.stdout,
                            "exception": repr(result.exception),
                            "parse_error": parse_error,
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        rows.append(
            {
                "case_id": case.case_id,
                "source_section": case.source_section,
                "source_subsection": case.source_subsection,
                "case_kind": case.case_kind,
                "query_text": case.query_text,
                "expected_behavior_category": case.expected_behavior_category,
                "expected_notes": case.expected_notes,
                "cli_exit_code": str(result.exit_code),
                "result_status": status,
                "result_reason": reason,
                "route": str(metadata.get("route", "") if isinstance(metadata, dict) else ""),
                "query_class": str(
                    metadata.get("query_class", "") if isinstance(metadata, dict) else ""
                ),
                "intent": str(metadata.get("intent", "") if isinstance(metadata, dict) else ""),
                "confidence": str(
                    metadata.get("confidence", "") if isinstance(metadata, dict) else ""
                ),
                "has_alternates": str(bool(alternates)),
                "notes": " | ".join(map(str, notes)) if isinstance(notes, list) else str(notes),
                "caveats": " | ".join(map(str, caveats))
                if isinstance(caveats, list)
                else str(caveats),
                "pass_fail": pass_fail,
                "pass_fail_reason": pass_fail_reason,
                "raw_json_path": str(raw_path.relative_to(ROOT)),
                "_pair_key": case.pair_key,
                "_equivalence_group": case.equivalence_group,
            }
        )
        if idx == 1 or idx % 25 == 0 or idx == len(cases):
            print(f"executed {idx}/{len(cases)}", flush=True)
    return rows


def write_results(rows: list[dict[str, str]]) -> None:
    with RESULTS_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in RESULT_FIELDS})


def markdown_table(headers: list[str], rows: list[list[str]], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    if not selected:
        return "_None._\n"
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in selected:
        out.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    if limit and len(rows) > limit:
        out.append(
            f"\n_Additional rows omitted from report: {len(rows) - limit}. See results.csv._"
        )
    return "\n".join(out) + "\n"


def pair_mismatches(rows: list[dict[str, str]]) -> list[list[str]]:
    by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("_pair_key"):
            by_pair[row["_pair_key"]].append(row)
    issues: list[list[str]] = []
    for key, members in sorted(by_pair.items()):
        if len(members) != 2:
            issues.append([key, "missing pair member", "", ""])
            continue
        a, b = members
        diffs = []
        for field in ("route", "query_class", "result_status", "intent"):
            if a.get(field, "") != b.get(field, ""):
                diffs.append(field)
        one_failed = {m["pass_fail"] for m in members} == {"pass", "fail"}
        if diffs or one_failed:
            issues.append(
                [key, ", ".join(diffs) or "pass/fail divergence", a["query_text"], b["query_text"]]
            )
    return issues


def equivalence_mismatches(rows: list[dict[str, str]]) -> list[list[str]]:
    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("_equivalence_group"):
            by_group[row["_equivalence_group"]].append(row)
    issues: list[list[str]] = []
    for key, members in sorted(by_group.items()):
        routes = sorted({m.get("route", "") for m in members})
        classes = sorted({m.get("query_class", "") for m in members})
        statuses = sorted({m.get("result_status", "") for m in members})
        if len(routes) > 1 or len(classes) > 1 or len(statuses) > 1:
            issues.append(
                [key, f"routes={routes}; classes={classes}; statuses={statuses}", str(len(members))]
            )
    return issues


def write_manifest(
    cases: list[Case], rows: list[dict[str, str]], run_ts: str, git_sha: str
) -> None:
    case_counts = Counter(case.source_section for case in cases)
    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "source_file_path": str(SOURCE_PATH.relative_to(ROOT)),
                "source_commit_sha": git_sha,
                "extraction_timestamp": run_ts,
                "case_count": len(cases),
                "case_count_by_section": dict(case_counts),
                "artifact_paths": {
                    "results_csv": str(RESULTS_PATH.relative_to(ROOT)),
                    "report_md": str(REPORT_PATH.relative_to(ROOT)),
                    "manifest_json": str(MANIFEST_PATH.relative_to(ROOT)),
                    "raw_dir": str(RAW_DIR.relative_to(ROOT)),
                },
                "raw_json_count": len(list(RAW_DIR.glob("*.json"))),
                "required_columns": RESULT_FIELDS,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def write_report(cases: list[Case], rows: list[dict[str, str]], run_ts: str, git_sha: str) -> None:
    counts_by_section = Counter(row["source_section"] for row in rows)
    counts_by_expected = Counter(row["expected_behavior_category"] for row in rows)
    counts_by_status = Counter(row["result_status"] for row in rows)
    counts_by_pass = Counter(row["pass_fail"] for row in rows)
    failures = [row for row in rows if row["pass_fail"] == "fail"]
    canonical_failures = [row for row in failures if row["source_section"].startswith("2.")]
    supported_failures = [
        row for row in failures if row["expected_behavior_category"] == "supported_exact"
    ]
    fallback_passes = [
        row
        for row in rows
        if row["expected_behavior_category"] == "supported_with_fallback"
        and row["pass_fail"] == "pass"
    ]
    ambiguous = [row for row in rows if row["expected_behavior_category"] == "ambiguous_expected"]
    unsupported = [
        row for row in rows if row["expected_behavior_category"] == "unsupported_expected"
    ]
    failure_reasons = Counter(row["pass_fail_reason"] for row in failures)
    mismatch_patterns = Counter(
        (
            row["expected_behavior_category"],
            row["result_status"],
            row["result_reason"],
            row["route"] or "(no route)",
        )
        for row in failures
    )
    pair_issues = pair_mismatches(rows)
    equiv_issues = equivalence_mismatches(rows)
    followups: list[list[str]] = []
    for row in canonical_failures[:20]:
        followups.append(
            [
                row["case_id"],
                "Canonical section 2 failure",
                row["query_text"],
                row["pass_fail_reason"],
            ]
        )
    for issue in pair_issues[:20]:
        followups.append([issue[0], "Phrasing-pair mismatch", f"{issue[2]} / {issue[3]}", issue[1]])
    for issue in equiv_issues[:20]:
        followups.append([issue[0], "Equivalence-group mismatch", issue[2], issue[1]])
    for row in supported_failures[:20]:
        followups.append(
            [row["case_id"], "Supported example failed", row["query_text"], row["pass_fail_reason"]]
        )

    lines = [
        "# Parser Examples Full Sweep Report",
        "",
        "## Run summary",
        "",
        f"- Run timestamp: `{run_ts}`",
        f"- Git commit SHA: `{git_sha or 'unavailable'}`",
        f"- Source: `{SOURCE_PATH.relative_to(ROOT)}`",
        f"- Total cases: `{len(rows)}`",
        f"- Raw JSON captures: `{len(list(RAW_DIR.glob('*.json')))}`",
        "",
        "## Case counts by source section",
        "",
        markdown_table(
            ["Source section", "Count"], [[k, str(v)] for k, v in sorted(counts_by_section.items())]
        ),
        "## Case counts by expected behavior",
        "",
        markdown_table(
            ["Expected behavior", "Count"],
            [[k, str(v)] for k, v in sorted(counts_by_expected.items())],
        ),
        "## Actual result-status distribution",
        "",
        markdown_table(
            ["Result status", "Count"], [[k, str(v)] for k, v in sorted(counts_by_status.items())]
        ),
        "## Overall pass/fail summary",
        "",
        markdown_table(
            ["Pass/fail", "Count"], [[k, str(v)] for k, v in sorted(counts_by_pass.items())]
        ),
        "",
        "Grouped failure reasons:",
        "",
        markdown_table(
            ["Reason", "Count"], [[k, str(v)] for k, v in failure_reasons.most_common()]
        ),
        "## Phrasing-pair mismatches",
        "",
        markdown_table(["Pair", "Mismatch", "Question form", "Search form"], pair_issues, limit=50),
        "## Equivalence-group mismatches",
        "",
        markdown_table(["Group", "Mismatch", "Members"], equiv_issues, limit=50),
        "## Supported examples that failed",
        "",
        markdown_table(
            ["Case", "Query", "Status", "Reason", "Route", "Failure reason"],
            [
                [
                    r["case_id"],
                    r["query_text"],
                    r["result_status"],
                    r["result_reason"],
                    r["route"],
                    r["pass_fail_reason"],
                ]
                for r in supported_failures
            ],
            limit=100,
        ),
        "## Fallback / coverage-gated examples behaving as documented",
        "",
        markdown_table(
            ["Case", "Query", "Status", "Reason", "Route", "Notes"],
            [
                [
                    r["case_id"],
                    r["query_text"],
                    r["result_status"],
                    r["result_reason"],
                    r["route"],
                    r["notes"][:180],
                ]
                for r in fallback_passes
            ],
            limit=100,
        ),
        "## Ambiguous examples",
        "",
        markdown_table(
            ["Case", "Query", "Status", "Reason", "Pass/fail"],
            [
                [
                    r["case_id"],
                    r["query_text"],
                    r["result_status"],
                    r["result_reason"],
                    r["pass_fail"],
                ]
                for r in ambiguous
            ],
            limit=100,
        ),
        "## Unsupported / out-of-scope examples",
        "",
        markdown_table(
            ["Case", "Query", "Status", "Reason", "Route", "Pass/fail"],
            [
                [
                    r["case_id"],
                    r["query_text"],
                    r["result_status"],
                    r["result_reason"],
                    r["route"],
                    r["pass_fail"],
                ]
                for r in unsupported
            ],
            limit=100,
        ),
        "## Top follow-up candidates",
        "",
        "Top recurring mismatch patterns:",
        "",
        markdown_table(
            ["Expected", "Status", "Reason", "Route", "Count"],
            [[a, b, c, d, str(count)] for (a, b, c, d), count in mismatch_patterns.most_common(20)],
        ),
        "Specific examples that appear wrong enough to merit follow-up work:",
        "",
        markdown_table(["Case/group", "Issue", "Query/members", "Detail"], followups, limit=80),
        "## Appendix: artifact locations",
        "",
        f"- Machine-readable results: `{RESULTS_PATH.relative_to(ROOT)}`",
        f"- Raw JSON captures: `{RAW_DIR.relative_to(ROOT)}/<case_id>.json`",
        f"- Manifest: `{MANIFEST_PATH.relative_to(ROOT)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now(UTC).isoformat()
    git_sha = get_git_sha()
    cases = extract_cases()
    print(f"extracted {len(cases)} cases", flush=True)
    rows = execute_cases(cases)
    write_results(rows)
    write_manifest(cases, rows, run_ts, git_sha)
    write_report(cases, rows, run_ts, git_sha)
    print(f"wrote {RESULTS_PATH.relative_to(ROOT)}", flush=True)
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}", flush=True)
    print(f"wrote {MANIFEST_PATH.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
