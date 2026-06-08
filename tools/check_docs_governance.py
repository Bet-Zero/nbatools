#!/usr/bin/env python3
"""Reject non-durable dependencies from durable documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

DURABLE_ENTRYPOINTS = (
    Path("README.md"),
    Path("AGENTS.md"),
    Path("docs/index.md"),
)
DURABLE_GLOBS = (
    "docs/architecture/**/*.md",
    "docs/operations/**/*.md",
    "docs/reference/**/*.md",
)
DOCS_ROOT_MARKDOWN_ALLOWLIST = {
    Path("docs/index.md"),
}
PROHIBITED_DOCS_DIRECTORIES = (
    Path("docs/planning"),
    Path("docs/archive"),
)

BANNED_PATH_PATTERNS = {
    "planning/": re.compile(r"(?<![\w-])(?:docs/|\.\.?/)+planning/"),
    "archive/": re.compile(r"(?<![\w-])(?:docs/|\.\.?/)*archive/"),
    "return_packages/": re.compile(r"(?<![\w-])(?:docs/|\.\.?/)*return_packages/"),
    "working/": re.compile(r"(?<![\w-])(?:docs/|\.\.?/)*working/"),
}

# These documents define the lifecycle rule itself. They may name lifecycle
# directories, but they may not use those paths as evidence for product facts.
BANNED_PATH_ALLOWLIST = {
    Path("AGENTS.md"): {
        "archive/": "agent lifecycle instructions",
        "return_packages/": "legacy migration-protection instruction",
        "working/": "agent lifecycle instructions",
    },
    Path("docs/operations/working_and_archive_policy.md"): {
        "archive/": "canonical lifecycle policy",
        "return_packages/": "canonical legacy migration-protection policy",
        "working/": "canonical lifecycle policy",
    },
}

# Generated files may be named only where the durable doc explains their
# operational role. Exact values keep each exception scoped to documented
# evidence artifacts or export destinations.
OUTPUT_REFERENCE_ALLOWLIST = {
    Path("README.md"): (
        "outputs/jokic_embiid_recent.json",
        "outputs/jokic_recent.txt",
        "outputs/top_scorers_march.csv",
    ),
    Path("AGENTS.md"): ("outputs/raw_query_answer_qa/<run_id>/product_review.md",),
    Path("docs/operations/deployment.md"): (
        "outputs/deployment_smoke/",
        "outputs/deployment_smoke/<label>.json",
        "outputs/deployment_smoke/preview.json",
    ),
    Path("docs/operations/exploratory_query_review.md"): (
        "outputs/exploratory_query_review/<run_id>/report.jsonl",
        "outputs/exploratory_query_review/<run_id>/report.md",
        "outputs/exploratory_query_review/<run_id>/summary.json",
        "outputs/exploratory_query_review/<run_id>/",
        "outputs/exploratory_query_review/<run_id>/<slice_id>/",
    ),
    Path("docs/operations/frontend_visual_qa.md"): (
        "outputs/",
        "outputs/frontend_visual_qa/<run_id>/",
        "outputs/public_ui_render_review/",
        "outputs/public_ui_render_review/<run_id>/",
        "outputs/visual_qa_screenshots/",
        "outputs/visual_qa_screenshots/<run_id>/",
    ),
    Path("docs/operations/parser_examples_full_sweep_protocol.md"): (
        "outputs/parser_examples_full_sweep/",
        "outputs/parser_examples_full_sweep/manifest.json",
        "outputs/parser_examples_full_sweep/raw/<case_id>.json",
        "outputs/parser_examples_full_sweep/report.md",
        "outputs/parser_examples_full_sweep/results.csv",
    ),
    Path("docs/operations/query_feedback_review.md"): (
        "outputs/query_feedback_exports",
        "outputs/query_feedback_exports/",
        "outputs/query_feedback_exports/<run_id>/",
        "outputs/query_feedback_exports/<run_id>/feedback_review.md",
        "outputs/query_feedback_exports/<run_id>/triage_decisions_template.csv",
    ),
    Path("docs/operations/query_validation_map.md"): (
        "outputs/exploratory_query_review/",
        "outputs/exploratory_query_review/<run_id>/",
        "outputs/public_ui_render_review/",
        "outputs/public_ui_render_review/<run_id>/",
        "outputs/raw_query_answer_qa/",
        "outputs/raw_query_answer_qa/20260607T033127Z/",
        "outputs/raw_query_answer_qa/20260607T033127Z/product_review.md",
        "outputs/raw_query_answer_qa/20260607T033519Z/",
        "outputs/raw_query_answer_qa/20260608T040000Z_top_single_game_performances_007/",
        "outputs/raw_query_answer_qa/20260608T040000Z_top_single_game_performances_007/product_review.md",
        "outputs/raw_query_answer_qa/20260608T041500Z_full_top_single_game_performances_007/",
        "outputs/raw_query_answer_qa/latest_public_query_acceptance/",
        "outputs/raw_query_answer_qa/<run_id>/product_review.md",
    ),
    Path("docs/operations/raw_query_answer_qa.md"): (
        "outputs/raw_query_answer_qa/",
        "outputs/raw_query_answer_qa/latest_public_query_acceptance/",
        "outputs/raw_query_answer_qa/<prior_run_id>/report.jsonl",
        "outputs/raw_query_answer_qa/<prior_run_id>/summary.json",
        "outputs/raw_query_answer_qa/<run_id>/",
        "outputs/raw_query_answer_qa/<run_id>/product_review.json",
        "outputs/raw_query_answer_qa/<run_id>/product_review.md",
        "outputs/raw_query_answer_qa/<run_id>/report.jsonl",
        "outputs/raw_query_answer_qa/<run_id>/report.md",
        "outputs/raw_query_answer_qa/<run_id>/summary.json",
    ),
    Path("docs/operations/ui_guide.md"): ("outputs/visual_qa_screenshots/<run_id>/",),
    Path("docs/operations/working_and_archive_policy.md"): ("outputs/",),
    Path("docs/reference/current_state_guide.md"): (
        "outputs/jokic_recent.txt",
        "outputs/top_scorers_march.csv",
    ),
    Path("docs/reference/query_guide.md"): (
        "outputs/jokic_embiid_recent.json",
        "outputs/jokic_recent.txt",
        "outputs/player_summary.json",
        "outputs/top_scorers_march.csv",
    ),
    Path("docs/reference/quick_query_guide.md"): (
        "outputs/jokic_embiid_recent.json",
        "outputs/jokic_recent.txt",
        "outputs/player_summary.json",
        "outputs/top_scorers_march.csv",
    ),
}

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
OUTPUT_PATH = re.compile(r"outputs/[A-Za-z0-9_./<>-]*")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")
TRACKED_OUTPUT_DEPENDENCY_GLOBS = (
    "qa/**/*.yaml",
    "qa/**/*.json",
    "frontend/src/test/**/*.ts",
    "frontend/src/test/**/*.tsx",
    "tests/**/*.py",
)
TRACKED_OUTPUT_DEPENDENCY_ALLOWLIST = {
    Path("tests/test_raw_query_answer_qa.py"): (
        "outputs/test/report.jsonl",
        "outputs/test/summary.json",
    ),
}


def durable_files() -> list[Path]:
    files = set(DURABLE_ENTRYPOINTS)
    for pattern in DURABLE_GLOBS:
        files.update(path.relative_to(ROOT) for path in ROOT.glob(pattern))
    return sorted(files)


def tracked_output_dependency_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in TRACKED_OUTPUT_DEPENDENCY_GLOBS:
        files.update(path.relative_to(ROOT) for path in ROOT.glob(pattern) if path.is_file())
    return sorted(files)


def check_docs_layout() -> list[str]:
    errors: list[str] = []
    for path in PROHIBITED_DOCS_DIRECTORIES:
        if (ROOT / path).exists():
            errors.append(f"{path}/: prohibited docs directory exists")

    for path in sorted((ROOT / "docs").glob("*.md")):
        relative_path = path.relative_to(ROOT)
        if relative_path not in DOCS_ROOT_MARKDOWN_ALLOWLIST:
            errors.append(f"{relative_path}: direct docs-root Markdown file is not allowlisted")

    return errors


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_banned_paths(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    exceptions = BANNED_PATH_ALLOWLIST.get(path, {})
    for label, pattern in BANNED_PATH_PATTERNS.items():
        if label in exceptions:
            continue
        for match in pattern.finditer(text):
            errors.append(
                f"{path}:{line_number(text, match.start())}: durable docs may not reference {label}"
            )
    return errors


def check_output_paths(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    allowed_values = OUTPUT_REFERENCE_ALLOWLIST.get(path, ())
    for match in OUTPUT_PATH.finditer(text):
        value = match.group(0)
        if value in allowed_values:
            continue
        errors.append(
            f"{path}:{line_number(text, match.start())}: "
            f"generated output path is not explicitly allowlisted: {value}"
        )
    return errors


def check_tracked_output_dependencies(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    allowed_values = TRACKED_OUTPUT_DEPENDENCY_ALLOWLIST.get(path, ())
    for match in OUTPUT_PATH.finditer(text):
        value = match.group(0)
        if value in allowed_values:
            continue
        errors.append(
            f"{path}:{line_number(text, match.start())}: "
            f"tracked corpus/test files may not depend on ignored outputs: {value}"
        )
    return errors


def normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target:
        target = target.split(" ", 1)[0]
    return unquote(target.split("#", 1)[0])


def check_relative_links(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for match in MARKDOWN_LINK.finditer(text):
        target = normalize_link_target(match.group(1))
        if not target or target.startswith(EXTERNAL_SCHEMES) or target.startswith("/"):
            continue
        resolved = (ROOT / path.parent / target).resolve()
        if not resolved.exists():
            errors.append(
                f"{path}:{line_number(text, match.start())}: "
                f"broken relative Markdown link: {match.group(1)}"
            )
    return errors


def main() -> int:
    errors = check_docs_layout()
    for path in durable_files():
        text = (ROOT / path).read_text(encoding="utf-8")
        errors.extend(check_banned_paths(path, text))
        errors.extend(check_output_paths(path, text))
        errors.extend(check_relative_links(path, text))
    for path in tracked_output_dependency_files():
        text = (ROOT / path).read_text(encoding="utf-8")
        errors.extend(check_tracked_output_dependencies(path, text))

    if errors:
        print("docs governance check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("docs governance check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
