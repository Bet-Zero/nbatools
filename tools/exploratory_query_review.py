#!/usr/bin/env python3
# ruff: noqa: I001
"""Run input-only natural-query samples and write human-review artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - local dev venv includes PyYAML.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbatools.api_handlers import query_result_to_payload  # noqa: E402
from nbatools.query_service import execute_natural_query  # noqa: E402
from tools.raw_query_answer_qa import (  # noqa: E402
    answer_text_from_metadata,
    build_answer_summary,
    build_section_summaries,
    build_slowest_cases,
    compact_value,
    display_path,
    format_filters,
    format_sections,
    infer_shape_hint,
    json_ready,
    markdown_table,
    md_code,
    md_escape,
    prepare_run_directory,
    top_performance_high_point_rows,
    validate_run_directory_target,
    validate_run_id_label,
)


FORBIDDEN_SAMPLE_FIELDS = {
    "expected_status",
    "expected_route",
    "expected_reason",
    "expected_shape",
    "expected_filters",
    "expected_sections",
    "expected_row_counts",
    "hard_assertions",
    "answer_text_policy",
    "manual_review",
    "acceptance",
    "review_notes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run input-only natural-language NBA query samples and write exploratory "
            "human-review artifacts."
        )
    )
    parser.add_argument("--input", required=True, help="YAML or JSON sample file.")
    parser.add_argument("--out", default="outputs/exploratory_query_review")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--overwrite-run-id", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-rows", type=int, default=3)
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def require_nonempty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def read_yaml_or_json(path: Path) -> Any:
    raw = path.read_text()
    if yaml is not None:
        return yaml.safe_load(raw)
    if path.suffix.lower() in {".yaml", ".yml"}:
        raise ValueError(f"PyYAML is required to read YAML input: {display_path(path)}")
    return json.loads(raw)


def raw_sample_entries(data: Any, *, path: Path) -> list[Any]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError(f"Exploratory query input must be a mapping or list: {display_path(path)}")

    for key in ("samples", "queries"):
        value = data.get(key)
        if value is not None:
            if not isinstance(value, list):
                raise ValueError(f"{key} must be a list: {display_path(path)}")
            return value

    if "cases" in data:
        raise ValueError("Exploratory query input must use samples or queries, not Raw QA cases.")
    raise ValueError(
        f"Exploratory query input must contain samples or queries: {display_path(path)}"
    )


def normalize_sample(raw_sample: Any, *, index: int) -> dict[str, Any]:
    if isinstance(raw_sample, str):
        raw = {"query": raw_sample}
    elif isinstance(raw_sample, dict):
        raw = dict(raw_sample)
    else:
        raise ValueError(f"Sample {index} must be a query string or mapping")

    forbidden = sorted(FORBIDDEN_SAMPLE_FIELDS & set(raw))
    if forbidden:
        raise ValueError(
            f"Sample {raw.get('id', index)} contains Raw QA expectation/review fields: "
            f"{forbidden}. Exploratory samples must be input-only."
        )

    query = require_nonempty_string(raw.get("query"), label=f"Sample {index} query")
    sample_id_value = raw.get("id")
    sample_id = (
        f"sample_{index:03d}"
        if sample_id_value is None
        else require_nonempty_string(sample_id_value, label=f"Sample {index} id")
    )
    metadata = {key: json_ready(value) for key, value in raw.items() if key not in {"id", "query"}}
    return {
        "id": sample_id,
        "query": query,
        "category": metadata.get("category"),
        "priority": metadata.get("priority"),
        "notes": metadata.get("notes"),
        "metadata": metadata,
    }


def load_samples(path: Path) -> tuple[int | None, list[dict[str, Any]]]:
    data = read_yaml_or_json(path)
    raw_entries = raw_sample_entries(data, path=path)

    samples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_sample in enumerate(raw_entries, start=1):
        sample = normalize_sample(raw_sample, index=index)
        sample_id = str(sample["id"])
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate sample id: {sample_id}")
        seen_ids.add(sample_id)
        samples.append(sample)

    version = data.get("version") if isinstance(data, dict) else None
    if isinstance(version, int | str) and str(version).isdigit():
        return int(version), samples
    return None, samples


def execute_query_payload(query: str) -> dict[str, Any]:
    return query_result_to_payload(execute_natural_query(query))


def make_review_flag(
    flag_id: str,
    message: str,
    *,
    severity: str = "review",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flag = {"id": flag_id, "severity": severity, "message": message}
    if details:
        flag["details"] = json_ready(details)
    return flag


def normalized_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def build_review_flags(
    sample: dict[str, Any],
    *,
    result_status: str | None,
    result_reason: str | None = None,
    route: str | None,
    shape_hint: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    errors: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if errors:
        flags.append(
            make_review_flag(
                "exception",
                "Query execution raised an exception.",
                severity="error",
                details={"route": route, "errors": errors},
            )
        )
    elif result_status == "error":
        flags.append(
            make_review_flag(
                "error_result",
                "Shared query engine returned result_status=error.",
                severity="error",
                details={"route": route, "reason": result_reason},
            )
        )
    elif result_status == "no_result":
        flags.append(
            make_review_flag(
                "no_result",
                "Shared query engine returned result_status=no_result.",
                details={"route": route},
            )
        )

    if result_status == "ok" and not sections:
        flags.append(
            make_review_flag(
                "ok_no_sections",
                "Result status is ok but no result sections were returned.",
                severity="suspicious",
                details={"route": route},
            )
        )

    high_point_rows = top_performance_high_point_rows(
        route=route,
        shape_hint=shape_hint,
        sections=sections,
    )
    if high_point_rows:
        flags.append(
            make_review_flag(
                "top_performance_high_points",
                "Top performance point total is unusually high (>= 75).",
                severity="suspicious",
                details={"rows": high_point_rows},
            )
        )

    if (
        "playoff teams" in normalized_text(sample.get("query"))
        and metadata.get("season_type") == "Playoffs"
    ):
        flags.append(
            make_review_flag(
                "playoff_teams_playoff_season_type",
                'Query contains "playoff teams" but result metadata uses season_type=Playoffs.',
                severity="suspicious",
                details={"route": route, "season": metadata.get("season")},
            )
        )

    if result_status not in {None, "ok", "no_result", "error"}:
        flags.append(
            make_review_flag(
                "unknown_result_status",
                "Result status is outside the known QueryResponse statuses.",
                severity="suspicious",
                details={"status": result_status, "route": route},
            )
        )

    return flags


def row_from_exception(sample: dict[str, Any], exc: Exception) -> dict[str, Any]:
    errors = [{"type": type(exc).__name__, "message": str(exc)}]
    return json_ready(
        {
            **sample,
            "route": None,
            "intent": None,
            "query_class": None,
            "result_status": "error",
            "result_reason": "exception",
            "ok": False,
            "confidence": None,
            "current_through": None,
            "answer_text": None,
            "answer_text_source": None,
            "answer_summary": "No answer rows returned; reason=exception",
            "shape_hint": "error",
            "shape_source": "backend_approximation",
            "metadata": {},
            "applied_filters": [],
            "sections": {},
            "section_summaries": {},
            "notes": [],
            "caveats": [],
            "errors": errors,
            "review_flags": build_review_flags(
                sample,
                result_status="error",
                result_reason="exception",
                route=None,
                shape_hint="error",
                metadata={},
                sections={},
                errors=errors,
            ),
            "payload": None,
        }
    )


def run_sample(sample: dict[str, Any], *, top_rows: int) -> dict[str, Any]:
    query = str(sample["query"])
    try:
        payload = execute_query_payload(query)
    except Exception as exc:  # pragma: no cover - covered by tests through monkeypatch.
        return row_from_exception(sample, exc)

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    applied_filters = metadata.get("applied_filters")
    if not isinstance(applied_filters, list):
        applied_filters = []

    answer_text, answer_text_source = answer_text_from_metadata(metadata)
    shape_hint = infer_shape_hint(payload.get("route"), payload.get("result_status"), sections)
    query_class = result.get("query_class") or metadata.get("query_class")
    answer_summary = build_answer_summary(
        result_status=payload.get("result_status"),
        result_reason=payload.get("result_reason"),
        route=payload.get("route"),
        metadata=metadata,
        sections=sections,
    )

    return json_ready(
        {
            **sample,
            "route": payload.get("route"),
            "intent": payload.get("intent"),
            "query_class": query_class,
            "result_status": payload.get("result_status"),
            "result_reason": payload.get("result_reason"),
            "ok": payload.get("ok"),
            "confidence": payload.get("confidence"),
            "current_through": payload.get("current_through"),
            "answer_text": answer_text,
            "answer_text_source": answer_text_source,
            "answer_summary": answer_summary,
            "shape_hint": shape_hint,
            "shape_source": "backend_approximation",
            "metadata": metadata,
            "applied_filters": applied_filters,
            "sections": sections,
            "section_summaries": build_section_summaries(sections, top_rows=top_rows),
            "notes": payload.get("notes") or result.get("notes") or [],
            "caveats": payload.get("caveats") or result.get("caveats") or [],
            "errors": [],
            "review_flags": build_review_flags(
                sample,
                result_status=payload.get("result_status"),
                result_reason=payload.get("result_reason"),
                route=payload.get("route"),
                shape_hint=shape_hint,
                metadata=metadata,
                sections=sections,
            ),
            "payload": payload,
        }
    )


def run_sample_with_timing(sample: dict[str, Any], *, top_rows: int) -> dict[str, Any]:
    started = time.monotonic()
    row = run_sample(sample, top_rows=top_rows)
    row["duration_seconds"] = round(time.monotonic() - started, 6)
    return row


def count_review_flags(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for flag in row.get("review_flags") or []:
            counts[str(flag.get("id"))] += 1
    return dict(sorted(counts.items()))


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    input_path: Path,
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    route_counts = Counter(str(row.get("route") or "<none>") for row in rows)
    status_counts = Counter(str(row.get("result_status") or "<none>") for row in rows)
    query_class_counts = Counter(str(row.get("query_class") or "<none>") for row in rows)
    category_counts = Counter(str(row.get("category") or "<unspecified>") for row in rows)

    no_result_case_ids: list[str] = []
    error_case_ids: list[str] = []
    suspicious_case_ids: list[str] = []
    error_details: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("id"))
        if row.get("result_status") == "no_result":
            no_result_case_ids.append(case_id)
        if row.get("result_status") == "error" or row.get("errors"):
            error_case_ids.append(case_id)
        if any(str(flag.get("severity")) == "suspicious" for flag in row.get("review_flags") or []):
            suspicious_case_ids.append(case_id)
        for error in row.get("errors") or []:
            error_details.append(
                {
                    "id": case_id,
                    "query": row.get("query"),
                    **error,
                }
            )

    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "input_path": display_path(input_path),
        "case_count": len(rows),
        "result_status_counts": dict(sorted(status_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "query_class_counts": dict(sorted(query_class_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "review_flag_counts": count_review_flags(rows),
        "suspicious_case_count": len(suspicious_case_ids),
        "suspicious_case_ids": suspicious_case_ids,
        "no_result_case_count": len(no_result_case_ids),
        "no_result_case_ids": no_result_case_ids,
        "error_case_count": len(error_case_ids),
        "error_case_ids": error_case_ids,
        "errors": error_details,
        "slowest_cases": build_slowest_cases(rows),
        "output_file_paths": {key: display_path(path) for key, path in output_paths.items()},
        "review_state": "human_review_pending",
        "validation_note": (
            "Exploratory query review is input-only human inspection, not Raw QA "
            "regression evidence."
        ),
    }


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(json_ready(data), ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(json_ready(row), ensure_ascii=False, sort_keys=True) + "\n")


def append_slowest_cases_section(lines: list[str], summary: dict[str, Any]) -> None:
    lines.extend(["", "## Slowest Cases", ""])
    slowest_cases = summary.get("slowest_cases") or []
    if not slowest_cases:
        lines.append("_None._")
        return
    lines.extend(["| Sample | Seconds | Status | Route |", "|---|---:|---|---|"])
    for row in slowest_cases:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row.get("id")),
                    md_escape(compact_value(row.get("duration_seconds"))),
                    md_escape(row.get("result_status")),
                    md_escape(row.get("route")),
                ]
            )
            + " |"
        )


def format_review_flags(flags: list[dict[str, Any]]) -> str:
    if not flags:
        return "_none_"
    parts = []
    for flag in flags:
        flag_id = flag.get("id")
        severity = flag.get("severity")
        parts.append(f"{flag_id} ({severity})" if severity else str(flag_id))
    return ", ".join(md_code(part) for part in parts)


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Exploratory Query Review",
        "",
        "This report is an input-only human-inspection snapshot. It has no expected "
        "outputs, does not pass or fail cases, and is not Raw QA regression evidence.",
        "",
        "Reviewed cases should be promoted manually into `qa/raw_query_answer_corpus.yaml` "
        "only after a reviewer records expected status, route, shape, filters, row counts, "
        "or hard assertions.",
        "",
        "## Run Metadata",
        "",
        f"- Run ID: {md_code(summary['run_id'])}",
        f"- Started: {md_code(summary['started_at'])}",
        f"- Completed: {md_code(summary['completed_at'])}",
        f"- Input: {md_code(summary['input_path'])}",
        f"- Samples: {md_code(summary['case_count'])}",
        f"- Review state: {md_code(summary['review_state'])}",
        "",
        "## Summary Counts",
        "",
        f"- Result statuses: {md_code(summary['result_status_counts'])}",
        f"- Routes: {md_code(summary['route_counts'])}",
        f"- Query classes: {md_code(summary['query_class_counts'])}",
        f"- Categories: {md_code(summary['category_counts'])}",
        f"- Review flags: {md_code(summary['review_flag_counts'])}",
        f"- Suspicious cases: {md_code(summary['suspicious_case_count'])}",
        f"- No-result cases: {md_code(summary['no_result_case_count'])}",
        f"- Error cases: {md_code(summary['error_case_count'])}",
    ]
    append_slowest_cases_section(lines, summary)

    lines.extend(["", "## Review Queue", ""])
    if not rows:
        lines.append("_No samples selected._")

    for row in rows:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Query: {md_code(row.get('query'))}",
                f"- Category: {md_code(row.get('category'))}",
                f"- Priority: {md_code(row.get('priority'))}",
                f"- Input notes: {md_escape(row.get('notes')) if row.get('notes') else '_none_'}",
                f"- Route: {md_code(row.get('route'))}",
                f"- Result status: {md_code(row.get('result_status'))}",
                f"- Result reason: {md_code(row.get('result_reason'))}",
                f"- Intent: {md_code(row.get('intent'))}",
                f"- Query class: {md_code(row.get('query_class'))}",
                f"- Shape hint: {md_code(row.get('shape_hint'))}",
                (
                    f"- Backend answer text: {md_escape(row['answer_text'])}"
                    if row.get("answer_text")
                    else "- Backend answer text: _not backend-provided_"
                ),
                (
                    f"- Answer summary: {md_escape(row['answer_summary'])}"
                    if row.get("answer_summary")
                    else "- Answer summary: _not available_"
                ),
                f"- Applied filters: {format_filters(row.get('applied_filters') or [])}",
                f"- Sections: {format_sections(row.get('section_summaries') or {})}",
                f"- Review flags: {format_review_flags(row.get('review_flags') or [])}",
            ]
        )
        if row.get("notes"):
            lines.append(f"- Result notes: {md_code(row.get('notes'))}")
        if row.get("caveats"):
            lines.append(f"- Caveats: {md_code(row.get('caveats'))}")
        if row.get("errors"):
            lines.append(f"- Errors: {md_code(row.get('errors'))}")

        lines.extend(
            [
                "- Reviewer status: [ ] correct [ ] bug [ ] expected unsupported "
                "[ ] needs follow-up [ ] promote to Raw QA",
                "- Reviewer notes:",
                "- Raw QA promotion draft:",
                "  - case id:",
                "  - expected status:",
                "  - expected route:",
                "  - expected shape/sections/filters/assertions:",
            ]
        )

        section_summaries = row.get("section_summaries") or {}
        for section_name, section_summary in section_summaries.items():
            top_rows = section_summary.get("top_rows") or []
            columns = section_summary.get("columns") or []
            shown_columns = ", ".join(columns[:12])
            if len(columns) > 12:
                shown_columns = f"{shown_columns}, ..."
            lines.extend(
                [
                    "",
                    f"Section {md_code(section_name)}",
                    "",
                    f"- Rows: {md_code(section_summary.get('row_count'))}",
                    f"- Columns: {md_escape(shown_columns) if shown_columns else '_none_'}",
                ]
            )
            if top_rows:
                lines.extend(["", markdown_table(top_rows)])
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n")


def run_review(
    *,
    input_path: Path,
    out_base: Path,
    run_id: str | None,
    overwrite_run_id: bool,
    limit: int | None,
    top_rows: int,
) -> dict[str, Any]:
    if overwrite_run_id and run_id is None:
        raise ValueError("--overwrite-run-id requires --run-id")
    if limit is not None and limit < 0:
        raise ValueError("--limit must be non-negative")
    if top_rows < 0:
        raise ValueError("--top-rows must be non-negative")

    resolved_run_id = (
        validate_run_id_label(run_id) if run_id else datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    run_dir = out_base / resolved_run_id
    validate_run_directory_target(
        run_dir,
        overwrite_run_id=overwrite_run_id,
        expected_root=out_base,
    )

    _version, samples = load_samples(input_path)
    selected = samples[:limit] if limit is not None else samples

    started_at = datetime.now(UTC).isoformat()
    rows = [run_sample_with_timing(sample, top_rows=top_rows) for sample in selected]
    completed_at = datetime.now(UTC).isoformat()

    prepare_run_directory(
        run_dir,
        overwrite_run_id=overwrite_run_id,
        expected_root=out_base,
    )
    output_paths = {
        "report_jsonl": run_dir / "report.jsonl",
        "report_md": run_dir / "report.md",
        "summary_json": run_dir / "summary.json",
    }
    summary = summarize_rows(
        rows,
        run_id=resolved_run_id,
        started_at=started_at,
        completed_at=completed_at,
        input_path=input_path,
        output_paths=output_paths,
    )

    write_jsonl(output_paths["report_jsonl"], rows)
    dump_json(output_paths["summary_json"], summary)
    write_markdown(output_paths["report_md"], rows, summary)

    return {"run_dir": run_dir, "rows": rows, "summary": summary}


def main() -> int:
    args = parse_args()
    result = run_review(
        input_path=resolve_path(args.input),
        out_base=resolve_path(args.out),
        run_id=args.run_id,
        overwrite_run_id=args.overwrite_run_id,
        limit=args.limit,
        top_rows=args.top_rows,
    )
    summary = result["summary"]
    print(f"Wrote exploratory query review: {display_path(result['run_dir'])}")
    print(f"Samples: {summary['case_count']}")
    print(f"Result statuses: {summary['result_status_counts']}")
    print(f"Routes: {summary['route_counts']}")
    print(f"Review flags: {summary['review_flag_counts']}")
    print(f"No-result cases: {summary['no_result_case_count']}")
    print(f"Error cases: {summary['error_case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
