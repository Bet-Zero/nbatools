# ruff: noqa: I001

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbatools.query_feedback_review import (  # noqa: E402
    FeedbackReviewFilters,
    group_records,
    load_local_records,
    load_r2_records,
    normalize_record,
    parse_datetime_filter,
    parse_multi_filter,
    record_matches_filters,
)


DEFAULT_BUCKET = "nbatools-data"
DEFAULT_PREFIX = "query_feedback/preview"
DEFAULT_OUTPUT_DIR = "outputs/query_feedback_exports"

NORMALIZED_FIELDS = [
    "id",
    "created_at",
    "schema_version",
    "feedback_source",
    "feedback_type",
    "query",
    "query_normalized",
    "query_normalized_hash",
    "source_page",
    "environment",
    "deployment_vercel_url",
    "deployment_vercel_git_commit_sha",
    "route",
    "status",
    "reason",
    "unsupported_filters",
    "metadata_summary",
    "result_query_class",
    "result_section_keys",
    "result_section_row_counts",
    "notes",
    "caveats",
    "user_note",
    "answer_text_preview",
    "error_message",
    "elapsed_ms",
    "review_status",
    "triage_decision",
    "is_smoke",
    "group_id",
    "suggested_triage",
    "triage_modifiers",
    "object_key",
]

TRIAGE_TEMPLATE_FIELDS = [
    "group_id",
    "representative_query",
    "count",
    "suggested_triage",
    "review_status",
    "triage_decision",
    "linked_case_id",
    "reviewer_notes",
    "next_action",
]

OUTPUT_KEYS = {
    "feedback_review_md": "feedback_review.md",
    "feedback_records_csv": "feedback_records.csv",
    "feedback_records_jsonl": "feedback_records.jsonl",
    "summary_json": "summary.json",
    "triage_decisions_template_csv": "triage_decisions_template.csv",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export immutable query feedback records into review artifacts."
    )
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--since", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--feedback-type", action="append", default=[])
    parser.add_argument("--status", action="append", default=[])
    parser.add_argument("--route", action="append", default=[])
    smoke_group = parser.add_mutually_exclusive_group()
    smoke_group.add_argument("--include-smoke", dest="include_smoke", action="store_true")
    smoke_group.add_argument("--exclude-smoke", dest="include_smoke", action="store_false")
    parser.set_defaults(include_smoke=False)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--local-dir", default=None)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_export(args)
    run_dir = Path(summary["output_paths"]["run_dir"])
    print(f"Wrote query feedback export: {display_path(run_dir)}")
    print(f"Records exported: {summary['total_exported']}")
    print(f"Groups: {summary['group_count']}")
    print(f"Excluded smoke records: {summary['excluded_smoke_count']}")
    return 0


def run_export(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_base = resolve_path(args.output_dir)
    run_dir = output_base / run_id
    output_paths = {key: run_dir / filename for key, filename in OUTPUT_KEYS.items()}
    output_paths["run_dir"] = run_dir

    filters = build_filters(args)
    loaded_records = load_records(args)
    normalized_records = [normalize_record(loaded) for loaded in loaded_records]
    records_after_filters = [
        record for record in normalized_records if record_matches_filters(record, filters)
    ]

    exported_records: list[dict[str, Any]] = []
    excluded_smoke_count = 0
    for record in records_after_filters:
        if record["is_smoke"] and not filters.include_smoke:
            excluded_smoke_count += 1
            continue
        exported_records.append(record)

    if filters.limit is not None:
        exported_records = exported_records[: filters.limit]

    groups = group_records(exported_records)
    run_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(
        args=args,
        run_id=run_id,
        filters=filters,
        total_found=len(loaded_records),
        total_filtered=len(records_after_filters),
        total_exported=len(exported_records),
        excluded_smoke_count=excluded_smoke_count,
        records=exported_records,
        groups=groups,
        output_paths=output_paths,
    )
    write_records_csv(output_paths["feedback_records_csv"], exported_records)
    write_records_jsonl(output_paths["feedback_records_jsonl"], exported_records)
    write_summary_json(output_paths["summary_json"], summary)
    write_triage_template(output_paths["triage_decisions_template_csv"], groups)
    write_review_markdown(
        output_paths["feedback_review_md"],
        summary=summary,
        records=exported_records,
        groups=groups,
    )
    return summary


def build_filters(args: argparse.Namespace) -> FeedbackReviewFilters:
    limit = args.limit
    if limit is not None and limit < 0:
        raise ValueError("--limit must be non-negative")
    return FeedbackReviewFilters(
        since=parse_datetime_filter(args.since, is_until=False),
        until=parse_datetime_filter(args.until, is_until=True),
        sources=parse_multi_filter(args.source),
        feedback_types=parse_multi_filter(args.feedback_type),
        statuses=parse_multi_filter(args.status),
        routes=parse_multi_filter(args.route),
        include_smoke=bool(args.include_smoke),
        limit=limit,
    )


def load_records(args: argparse.Namespace):
    if args.local_dir:
        return load_local_records(resolve_path(args.local_dir))
    return load_r2_records(bucket=args.bucket, prefix=args.prefix)


def build_summary(
    *,
    args: argparse.Namespace,
    run_id: str,
    filters: FeedbackReviewFilters,
    total_found: int,
    total_filtered: int,
    total_exported: int,
    excluded_smoke_count: int,
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    source_mode = "local" if args.local_dir else "r2"
    high_priority_group_ids = [
        group["group_id"]
        for group in groups
        if "prioritize_review" in group.get("triage_modifiers", [])
    ]
    triage_bucket_counts = Counter(group["suggested_triage"] for group in groups)
    summary: dict[str, Any] = {
        "run_id": run_id,
        "filters": filters_to_summary(args, filters),
        "source_mode": source_mode,
        "total_found": total_found,
        "total_filtered": total_filtered,
        "total_exported": total_exported,
        "excluded_smoke_count": excluded_smoke_count,
        "group_count": len(groups),
        "high_priority_group_ids": high_priority_group_ids,
        "triage_bucket_counts": dict(sorted(triage_bucket_counts.items())),
        "records_by_feedback_source": counter_to_dict(
            Counter(record.get("feedback_source") or "unknown" for record in records)
        ),
        "records_by_feedback_type": counter_to_dict(
            Counter(record.get("feedback_type") or "unknown" for record in records)
        ),
        "records_by_status_reason": counter_to_dict(
            Counter(status_reason_label(record) for record in records)
        ),
        "records_by_route": counter_to_dict(
            Counter(record.get("route") or "unknown" for record in records)
        ),
        "smoke_record_count": sum(1 for record in records if record.get("is_smoke")),
        "automatic_record_count": sum(
            1 for record in records if record.get("feedback_source") == "automatic"
        ),
        "user_submitted_record_count": sum(
            1 for record in records if record.get("feedback_source") == "user_submitted"
        ),
        "output_paths": {key: str(path) for key, path in output_paths.items()},
    }
    if source_mode == "local":
        summary["local_dir"] = str(resolve_path(args.local_dir))
    else:
        summary["bucket"] = args.bucket
        summary["prefix"] = args.prefix
    return summary


def filters_to_summary(args: argparse.Namespace, filters: FeedbackReviewFilters) -> dict[str, Any]:
    return {
        "since": args.since,
        "until": args.until,
        "source": sorted(filters.sources),
        "feedback_type": sorted(filters.feedback_types),
        "status": sorted(filters.statuses),
        "route": sorted(filters.routes),
        "include_smoke": filters.include_smoke,
        "limit": filters.limit,
    }


def status_reason_label(record: dict[str, Any]) -> str:
    status = record.get("status") or "unknown"
    reason = record.get("reason") or "none"
    return f"{status}/{reason}"


def counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def write_records_csv(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NORMALIZED_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow({field: csv_value(record.get(field)) for field in NORMALIZED_FIELDS})


def write_records_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(json_ready(record), sort_keys=True) + "\n")


def write_summary_json(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(json_ready(summary), indent=2, sort_keys=True) + "\n")


def write_triage_template(path: Path, groups: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRIAGE_TEMPLATE_FIELDS)
        writer.writeheader()
        for group in groups:
            writer.writerow(
                {
                    "group_id": group["group_id"],
                    "representative_query": group["representative_query"],
                    "count": group["count"],
                    "suggested_triage": group["suggested_triage"],
                    "review_status": "new",
                    "triage_decision": "",
                    "linked_case_id": "",
                    "reviewer_notes": "",
                    "next_action": "",
                }
            )


def write_review_markdown(
    path: Path,
    *,
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
) -> None:
    lines = [
        "# Query Feedback Review",
        "",
        "## Run metadata and filters",
        "",
        markdown_table(
            [
                {"field": "run_id", "value": summary["run_id"]},
                {"field": "source_mode", "value": summary["source_mode"]},
                {"field": "filters", "value": json.dumps(summary["filters"], sort_keys=True)},
            ]
        ),
        "",
        "## Totals",
        "",
        markdown_table(
            [
                {"metric": "total_found", "count": summary["total_found"]},
                {"metric": "total_filtered", "count": summary["total_filtered"]},
                {"metric": "total_exported", "count": summary["total_exported"]},
                {"metric": "excluded_smoke_records", "count": summary["excluded_smoke_count"]},
                {"metric": "group_count", "count": summary["group_count"]},
            ]
        ),
        "",
        "## Records by feedback_source",
        "",
        counter_markdown(summary["records_by_feedback_source"]),
        "",
        "## Records by feedback_type",
        "",
        counter_markdown(summary["records_by_feedback_type"]),
        "",
        "## Records by status/reason",
        "",
        counter_markdown(summary["records_by_status_reason"]),
        "",
        "## Records by route",
        "",
        counter_markdown(summary["records_by_route"]),
        "",
        "## Duplicate groups",
        "",
        group_markdown([group for group in groups if group["count"] > 1]),
        "",
        "## High-priority groups",
        "",
        group_markdown(
            [group for group in groups if "prioritize_review" in group.get("triage_modifiers", [])]
        ),
        "",
        "## Smoke-test summary",
        "",
        markdown_table(
            [
                {"metric": "included_smoke_records", "count": summary["smoke_record_count"]},
                {"metric": "excluded_smoke_records", "count": summary["excluded_smoke_count"]},
            ]
        ),
        "",
        "## Automatic diagnostics",
        "",
        group_markdown(
            [group for group in groups if "automatic" in group.get("feedback_sources", [])]
        ),
        "",
        "## User-submitted reports",
        "",
        group_markdown(
            [group for group in groups if "user_submitted" in group.get("feedback_sources", [])]
        ),
    ]
    lines.extend(candidate_sections(groups))
    lines.extend(recommended_next_actions(summary, records, groups))
    path.write_text("\n".join(lines).rstrip() + "\n")


def candidate_sections(groups: list[dict[str, Any]]) -> list[str]:
    sections = [
        ("Candidate raw QA cases", {"raw_qa_case", "parser_issue"}),
        ("Candidate frontend-copy QA cases", {"frontend_copy_case"}),
        ("Candidate visual QA cases", {"visual_qa_case"}),
        ("Unsupported-family candidates", {"unsupported_family"}),
        ("Data issue candidates", {"data_issue"}),
        ("Expected unsupported / no-action candidates", {"no_action"}),
    ]
    lines: list[str] = []
    for title, triage_values in sections:
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                group_markdown(
                    [group for group in groups if group["suggested_triage"] in triage_values]
                ),
            ]
        )
    return lines


def recommended_next_actions(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    groups: list[dict[str, Any]],
) -> list[str]:
    del records
    high_priority_count = len(summary["high_priority_group_ids"])
    return [
        "",
        "## Recommended next actions",
        "",
        "- Review high-priority duplicate groups first."
        if high_priority_count
        else "- Review candidate groups by suggested triage bucket.",
        "- Fill `triage_decisions_template.csv`; do not edit source R2 records.",
        "- Convert accepted feedback into QA cases or product work manually after review.",
        "- Treat suggested triage as a heuristic, not automatic QA truth.",
        f"- Groups available for review: {len(groups)}.",
    ]


def counter_markdown(values: dict[str, int]) -> str:
    if not values:
        return "_None._"
    return markdown_table([{"value": key, "count": count} for key, count in values.items()])


def group_markdown(groups: list[dict[str, Any]], *, limit: int = 25) -> str:
    if not groups:
        return "_None._"
    rows: list[dict[str, Any]] = []
    for group in groups[:limit]:
        rows.append(
            {
                "group_id": group["group_id"],
                "count": group["count"],
                "suggested_triage": group["suggested_triage"],
                "modifiers": ", ".join(group.get("triage_modifiers", [])),
                "query": group["representative_query"],
                "routes": ", ".join(group.get("routes", [])),
                "statuses": ", ".join(group.get("statuses", [])),
                "reasons": ", ".join(group.get("reasons", [])),
            }
        )
    table = markdown_table(rows)
    if len(groups) > limit:
        table += f"\n\n_Additional groups omitted: {len(groups) - limit}._"
    return table


def markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_None._"
    columns = list(rows[0])
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def markdown_cell(value: Any) -> str:
    text = csv_value(value)
    text = text.replace("|", "\\|")
    return text or ""


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list | dict):
        return json.dumps(json_ready(value), sort_keys=True)
    return str(value)


def json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    return value


def resolve_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
