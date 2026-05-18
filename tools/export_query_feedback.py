# ruff: noqa: I001

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbatools import data_source  # noqa: E402
from nbatools.query_feedback import (  # noqa: E402
    DISALLOWED_FIELD_NAMES,
    METADATA_ALLOWLIST,
    SLOW_QUERY_WARNING_MS,
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

TRIAGE_PRIORITY = [
    "parser_issue",
    "raw_qa_case",
    "data_issue",
    "unsupported_family",
    "visual_qa_case",
    "frontend_copy_case",
    "performance_review",
    "no_action",
]

RAW_OR_PII_KEYS = DISALLOWED_FIELD_NAMES | {
    "raw_rows",
    "row",
    "rows",
    "section_rows",
    "sections",
    "table",
    "tables",
}


@dataclass(frozen=True)
class LoadedFeedbackRecord:
    record: dict[str, Any]
    object_key: str
    last_modified: datetime | None = None


@dataclass(frozen=True)
class ExportFilters:
    since: datetime | None
    until: datetime | None
    sources: set[str]
    feedback_types: set[str]
    statuses: set[str]
    routes: set[str]
    include_smoke: bool
    limit: int | None


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


def build_filters(args: argparse.Namespace) -> ExportFilters:
    limit = args.limit
    if limit is not None and limit < 0:
        raise ValueError("--limit must be non-negative")
    return ExportFilters(
        since=parse_datetime_filter(args.since, is_until=False),
        until=parse_datetime_filter(args.until, is_until=True),
        sources=parse_multi_filter(args.source),
        feedback_types=parse_multi_filter(args.feedback_type),
        statuses=parse_multi_filter(args.status),
        routes=parse_multi_filter(args.route),
        include_smoke=bool(args.include_smoke),
        limit=limit,
    )


def parse_multi_filter(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        for part in str(value).split(","):
            text = part.strip()
            if text:
                result.add(text)
    return result


def parse_datetime_filter(value: str | None, *, is_until: bool) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        date_value = datetime.strptime(text, "%Y-%m-%d").date()
        boundary_time = time.max if is_until else time.min
        return datetime.combine(date_value, boundary_time, tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid datetime filter: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_records(args: argparse.Namespace) -> list[LoadedFeedbackRecord]:
    if args.local_dir:
        return load_local_records(resolve_path(args.local_dir))
    return load_r2_records(bucket=args.bucket, prefix=args.prefix)


def load_local_records(local_dir: Path) -> list[LoadedFeedbackRecord]:
    if not local_dir.exists():
        raise FileNotFoundError(f"Local feedback directory does not exist: {local_dir}")
    records: list[LoadedFeedbackRecord] = []
    for path in sorted(local_dir.rglob("*.json")):
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Feedback JSON must be an object: {path}")
        records.append(
            LoadedFeedbackRecord(
                record=data,
                object_key=path.relative_to(local_dir).as_posix(),
                last_modified=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            )
        )
    return records


def load_r2_records(*, bucket: str, prefix: str) -> list[LoadedFeedbackRecord]:
    env = dict(os.environ)
    env["R2_BUCKET_NAME"] = bucket
    config = data_source.load_r2_config(env=env)
    client = data_source.create_r2_client(config)
    records: list[LoadedFeedbackRecord] = []
    continuation_token: str | None = None
    prefix_value = prefix.strip("/")

    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix_value}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = str(item.get("Key") or "")
            if not key or key.endswith("/") or not key.endswith(".json"):
                continue
            object_response = client.get_object(Bucket=bucket, Key=key)
            data = json.loads(read_body_text(object_response.get("Body")))
            if not isinstance(data, dict):
                raise ValueError(f"Feedback JSON must be an object: {key}")
            last_modified = item.get("LastModified")
            records.append(
                LoadedFeedbackRecord(
                    record=data,
                    object_key=key,
                    last_modified=last_modified if isinstance(last_modified, datetime) else None,
                )
            )

        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
        if not continuation_token:
            break

    return records


def read_body_text(body: Any) -> str:
    payload = body.read() if hasattr(body, "read") else body
    if isinstance(payload, bytes):
        return payload.decode("utf-8")
    return str(payload)


def normalize_record(loaded: LoadedFeedbackRecord) -> dict[str, Any]:
    record = loaded.record
    metadata = safe_metadata(record.get("metadata"))
    result_shape = (
        record.get("result_shape") if isinstance(record.get("result_shape"), dict) else {}
    )
    deployment = record.get("deployment") if isinstance(record.get("deployment"), dict) else {}
    query = clean_text(record.get("query"))
    unsupported_filters = normalize_string_list(
        metadata.get("unsupported_filters") or record.get("unsupported_filters")
    )
    section_row_counts = safe_section_counts(result_shape.get("section_row_counts"))
    section_keys = normalize_string_list(result_shape.get("section_keys")) or sorted(
        section_row_counts
    )

    normalized: dict[str, Any] = {
        "id": clean_text(record.get("id")),
        "created_at": clean_text(record.get("created_at")),
        "schema_version": record.get("schema_version"),
        "feedback_source": clean_text(record.get("feedback_source")),
        "feedback_type": clean_text(record.get("feedback_type")),
        "query": query,
        "query_normalized": normalize_query(query),
        "query_normalized_hash": clean_text(record.get("query_normalized_hash")),
        "source_page": clean_text(record.get("source_page")),
        "environment": clean_text(record.get("environment")),
        "deployment_vercel_url": clean_text(deployment.get("vercel_url")),
        "deployment_vercel_git_commit_sha": clean_text(deployment.get("vercel_git_commit_sha")),
        "route": clean_text(record.get("route")),
        "status": clean_text(record.get("status")),
        "reason": clean_text(record.get("reason")),
        "unsupported_filters": unsupported_filters,
        "metadata_summary": metadata,
        "result_query_class": clean_text(result_shape.get("query_class")),
        "result_section_keys": section_keys,
        "result_section_row_counts": section_row_counts,
        "notes": normalize_string_list(record.get("notes")),
        "caveats": normalize_string_list(record.get("caveats")),
        "user_note": clean_text(record.get("user_note")),
        "answer_text_preview": clean_text(record.get("answer_text_preview")),
        "error_message": clean_text(record.get("error_message")),
        "elapsed_ms": number_or_none(record.get("elapsed_ms")),
        "review_status": clean_text(record.get("review_status")),
        "triage_decision": clean_text(record.get("triage_decision")),
        "is_smoke": False,
        "group_id": "",
        "suggested_triage": "",
        "triage_modifiers": [],
        "object_key": loaded.object_key,
    }
    normalized["is_smoke"] = is_smoke_record(normalized)
    normalized["suggested_triage"] = suggest_triage(normalized)
    return normalized


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text


def normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    result: list[str] = []
    for item in values:
        text = clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def number_or_none(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    try:
        return float(str(value))
    except ValueError:
        return None


def safe_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key, raw_value in value.items():
        key_text = clean_text(key)
        if not key_text or key_text in RAW_OR_PII_KEYS or key_text not in METADATA_ALLOWLIST:
            continue
        clean_value = strip_disallowed_value(raw_value)
        if clean_value is not None:
            result[key_text] = clean_value
    return result


def strip_disallowed_value(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean for item in value if (clean := strip_disallowed_value(item)) is not None]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, raw_item in value.items():
            key_text = clean_text(key)
            if not key_text or key_text in RAW_OR_PII_KEYS:
                continue
            clean_item = strip_disallowed_value(raw_item)
            if clean_item is not None:
                result[key_text] = clean_item
        return result
    return clean_text(value)


def safe_section_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, raw_count in value.items():
        key_text = clean_text(key)
        count = number_or_none(raw_count)
        if key_text and count is not None and count >= 0:
            counts[key_text] = int(count)
    return counts


def is_smoke_record(record: dict[str, Any]) -> bool:
    query = str(record.get("query", "")).lower()
    user_note = str(record.get("user_note", "")).lower()
    route = str(record.get("route", "")).lower()
    reason = str(record.get("reason", "")).lower()
    feedback_type = str(record.get("feedback_type", "")).lower()
    source_page = str(record.get("source_page", "")).lower()
    environment = str(record.get("environment", "")).lower()
    deployment_url = str(record.get("deployment_vercel_url", "")).lower()

    if "smoke" in query:
        return True
    if "smoke test" in user_note:
        return True
    if route == "smoke" or reason == "smoke":
        return True
    if feedback_type == "other" and "direct endpoint smoke" in query:
        return True
    return any(
        label in {"smoke", "smoke-test", "test", "testing"}
        or "smoke" in label
        or label.endswith("/smoke")
        or label.endswith("/test")
        for label in (source_page, environment, deployment_url)
        if label
    )


def suggest_triage(record: dict[str, Any]) -> str:
    if record.get("is_smoke"):
        return "no_action"
    status = record.get("status")
    reason = record.get("reason")
    feedback_type = record.get("feedback_type")
    feedback_source = record.get("feedback_source")
    elapsed_ms = record.get("elapsed_ms")

    if status == "error" and reason == "unrouted":
        return "parser_issue"
    if status == "no_result" and reason == "filter_not_supported":
        return "unsupported_family"
    if status == "no_result" and reason == "no_data":
        return "data_issue"
    if feedback_type == "wrong_answer":
        return "raw_qa_case"
    if feedback_type == "confusing_answer":
        return "frontend_copy_case"
    if feedback_type == "ui_issue":
        return "visual_qa_case"
    if (
        feedback_source == "automatic"
        and status == "ok"
        and isinstance(elapsed_ms, int | float)
        and elapsed_ms >= SLOW_QUERY_WARNING_MS
    ):
        return "performance_review"
    return "no_action"


def record_matches_filters(record: dict[str, Any], filters: ExportFilters) -> bool:
    created_at = parse_record_datetime(record.get("created_at"))
    if filters.since is not None and (created_at is None or created_at < filters.since):
        return False
    if filters.until is not None and (created_at is None or created_at > filters.until):
        return False
    if filters.sources and record.get("feedback_source") not in filters.sources:
        return False
    if filters.feedback_types and record.get("feedback_type") not in filters.feedback_types:
        return False
    if filters.statuses and record.get("status") not in filters.statuses:
        return False
    return not (filters.routes and record.get("route") not in filters.routes)


def parse_record_datetime(value: Any) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def group_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = grouping_key(record)
        buckets.setdefault(key, []).append(record)

    groups: list[dict[str, Any]] = []
    for key, group_records_value in buckets.items():
        group_id = deterministic_group_id(key)
        group = build_group(group_id, group_records_value)
        groups.append(group)
        for record in group_records_value:
            record["group_id"] = group_id
            record["triage_modifiers"] = list(group["triage_modifiers"])

    groups.sort(key=lambda group: (group["first_seen"], group["group_id"]))
    return groups


def grouping_key(record: dict[str, Any]) -> str:
    query_hash = record.get("query_normalized_hash")
    if query_hash:
        return f"hash|{query_hash}"
    fallback_parts = [
        str(record.get("query_normalized") or ""),
        str(record.get("route") or ""),
        str(record.get("status") or ""),
        str(record.get("reason") or ""),
        json.dumps(sorted(record.get("unsupported_filters") or []), sort_keys=True),
        str(record.get("feedback_type") or ""),
    ]
    return "fallback|" + "|".join(fallback_parts)


def deterministic_group_id(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"qfg_{digest}"


def build_group(group_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_records = sorted(records, key=record_sort_key)
    user_submitted_count = sum(
        1 for record in sorted_records if record.get("feedback_source") == "user_submitted"
    )
    modifiers: list[str] = []
    if len(sorted_records) >= 3 or user_submitted_count >= 2:
        modifiers.append("prioritize_review")

    return {
        "group_id": group_id,
        "count": len(sorted_records),
        "first_seen": first_non_empty(record.get("created_at") for record in sorted_records),
        "last_seen": last_non_empty(record.get("created_at") for record in sorted_records),
        "representative_query": first_non_empty(record.get("query") for record in sorted_records),
        "feedback_sources": sorted(
            unique_values(record.get("feedback_source") for record in records)
        ),
        "feedback_types": sorted(unique_values(record.get("feedback_type") for record in records)),
        "routes": sorted(unique_values(record.get("route") for record in records)),
        "statuses": sorted(unique_values(record.get("status") for record in records)),
        "reasons": sorted(unique_values(record.get("reason") for record in records)),
        "unsupported_filters": sorted(
            {
                unsupported_filter
                for record in records
                for unsupported_filter in record.get("unsupported_filters", [])
                if unsupported_filter
            }
        ),
        "user_notes": unique_ordered(record.get("user_note") for record in sorted_records),
        "record_ids": unique_ordered(record.get("id") for record in sorted_records),
        "object_keys": unique_ordered(record.get("object_key") for record in sorted_records),
        "suggested_triage": group_suggested_triage(records),
        "triage_modifiers": modifiers,
    }


def record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    created_at = record.get("created_at") or ""
    return (str(created_at), str(record.get("id") or ""))


def first_non_empty(values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def last_non_empty(values: Any) -> str:
    result = ""
    for value in values:
        text = clean_text(value)
        if text:
            result = text
    return result


def unique_values(values: Any) -> set[str]:
    return {text for value in values if (text := clean_text(value))}


def unique_ordered(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = clean_text(value)
        if text and text not in result:
            result.append(text)
    return result


def group_suggested_triage(records: list[dict[str, Any]]) -> str:
    suggestions = {record.get("suggested_triage") or "no_action" for record in records}
    for triage in TRIAGE_PRIORITY:
        if triage in suggestions:
            return triage
    return "no_action"


def build_summary(
    *,
    args: argparse.Namespace,
    run_id: str,
    filters: ExportFilters,
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


def filters_to_summary(args: argparse.Namespace, filters: ExportFilters) -> dict[str, Any]:
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
