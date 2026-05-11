# ruff: noqa: I001

from __future__ import annotations

import argparse
import json
import math
import re
import sys
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
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbatools.api_handlers import query_result_to_payload  # noqa: E402
from nbatools.query_service import execute_natural_query  # noqa: E402


REQUIRED_CASE_FIELDS = {"id", "query", "category", "priority", "expected_status"}
EXPECTED_FIELD_NAMES = {
    "expected_status",
    "expected_route",
    "expected_reason",
    "expected_shape",
    "expected_filters",
    "expected_sections",
    "expected_row_counts",
    "hard_assertions",
    "review_notes",
}
SHAPE_BY_ROUTE = {
    "game_finder": "game_log_team_table",
    "game_summary": "game_log_team_detail",
    "lineup_leaderboard": "leaderboard_table",
    "lineup_summary": "entity_summary",
    "player_game_summary": "entity_summary",
    "player_on_off": "on_off_split",
    "player_streak_finder": "streak_table",
    "player_stretch_leaderboard": "rolling_stretch",
    "playoff_history": "playoff_history",
    "playoff_matchup_history": "playoff_matchup_history",
    "playoff_round_record": "playoff_round_record",
    "record_by_decade": "record_by_decade",
    "record_by_decade_leaderboard": "record_by_decade_leaderboard",
    "season_leaders": "leaderboard_table",
    "season_team_leaders": "leaderboard_table",
    "team_matchup_record": "comparison",
    "team_record": "team_record",
    "team_record_leaderboard": "leaderboard_table",
    "team_streak_finder": "streak_table",
    "top_player_games": "top_performances",
    "top_team_games": "top_performances",
}
LEADERBOARD_ROUTES = {
    "player_occurrence_leaders",
    "team_occurrence_leaders",
    "playoff_appearances",
}
PREFERRED_MARKDOWN_COLUMNS = [
    "rank",
    "player_name",
    "team_name",
    "team_abbr",
    "season",
    "season_start",
    "season_end",
    "game_date",
    "opponent_team_abbr",
    "wl",
    "count",
    "games",
    "wins",
    "losses",
    "win_pct",
    "pts",
    "pts_avg",
    "pts_per_game",
    "reb",
    "reb_avg",
    "ast",
    "ast_avg",
    "window_size",
    "stretch_value",
    "streak_length",
    "start_date",
    "end_date",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the raw NBA query answer QA corpus and write review reports."
    )
    parser.add_argument("--corpus", default="qa/raw_query_answer_corpus.yaml")
    parser.add_argument("--out", default="outputs/raw_query_answer_qa")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--top-rows", type=int, default=3)
    parser.add_argument("--fail-on-expectation-failure", action="store_true")
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def load_corpus(path: Path) -> tuple[int | None, list[dict[str, Any]]]:
    raw = path.read_text()
    if yaml is not None:
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError(f"Corpus must be a mapping: {path}")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"Corpus must contain a cases list: {path}")

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be a mapping")
        missing = REQUIRED_CASE_FIELDS - set(case)
        if missing:
            raise ValueError(f"Case {case.get('id', index)} missing fields: {sorted(missing)}")

    version = data.get("version")
    if isinstance(version, int | str) and str(version).isdigit():
        return int(version), cases
    return None, cases


def selected_case_ids(values: list[str]) -> set[str]:
    ids: set[str] = set()
    for value in values:
        for case_id in value.split(","):
            case_id = case_id.strip()
            if case_id:
                ids.add(case_id)
    return ids


def filter_cases(
    cases: list[dict[str, Any]],
    *,
    case_ids: set[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    filtered = cases
    if case_ids:
        known = {str(case["id"]) for case in cases}
        unknown = sorted(case_ids - known)
        if unknown:
            raise ValueError(f"Unknown case id(s): {', '.join(unknown)}")
        filtered = [case for case in cases if str(case["id"]) in case_ids]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def json_ready(value: Any) -> Any:
    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, dict):
        return {str(key): json_ready(inner) for key, inner in value.items()}
    if isinstance(value, list | tuple):
        return [json_ready(inner) for inner in value]
    if hasattr(value, "item"):
        try:
            return json_ready(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def case_expectations(case: dict[str, Any]) -> dict[str, Any]:
    return {key: json_ready(case.get(key)) for key in EXPECTED_FIELD_NAMES if key in case}


def answer_text_from_metadata(metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    for key in ("answer_phrase", "count_phrase"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value, f"backend_metadata.{key}"
    return None, None


def infer_shape_hint(route: str | None, status: str | None, sections: dict[str, Any]) -> str:
    if status == "error":
        return "error"
    if status == "no_result":
        return "no_result"
    if "count" in sections and "finder" in sections:
        return "count_with_finder"
    if route in LEADERBOARD_ROUTES:
        return "leaderboard_table"
    if route in SHAPE_BY_ROUTE:
        return SHAPE_BY_ROUTE[route]
    if "leaderboard" in sections:
        return "leaderboard_table"
    if "streak" in sections:
        return "streak_table"
    if "finder" in sections:
        return "game_log_table"
    if "summary" in sections and "comparison" in sections:
        return "comparison"
    if "summary" in sections:
        return "entity_summary"
    return "unknown"


def section_columns(rows: list[Any]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns


def build_section_summaries(
    sections: dict[str, Any],
    *,
    top_rows: int,
) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for name, rows_value in sections.items():
        rows = rows_value if isinstance(rows_value, list) else []
        columns = section_columns(rows)
        summary: dict[str, Any] = {
            "row_count": len(rows),
            "columns": columns,
            "top_rows": rows[:top_rows],
        }
        if name == "summary" and len(rows) == 1 and isinstance(rows[0], dict):
            summary["summary_row"] = rows[0]
        summaries[name] = json_ready(summary)
    return summaries


def as_allowed_values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def make_check(
    name: str,
    passed: bool,
    *,
    expected: Any = None,
    actual: Any = None,
    message: str | None = None,
    include_expected: bool = True,
    include_actual: bool = True,
) -> dict[str, Any]:
    check: dict[str, Any] = {"name": name, "status": "pass" if passed else "fail"}
    if include_expected:
        check["expected"] = json_ready(expected)
    if include_actual:
        check["actual"] = json_ready(actual)
    if message:
        check["message"] = message
    return check


def normalized_match_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def filter_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    for key in ("kind", "label", "value"):
        if key not in expected or expected[key] is None:
            continue
        if normalized_match_text(expected[key]) != normalized_match_text(actual.get(key)):
            return False
    return True


def resolve_dot_path(root: Any, path: str) -> tuple[bool, Any, str | None]:
    current = root
    traversed: list[str] = []
    for part in path.split("."):
        traversed.append(part)
        if isinstance(current, dict):
            if part not in current:
                return False, None, f"Missing key at {'.'.join(traversed)}"
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return False, None, f"Expected list index at {'.'.join(traversed)}"
            index = int(part)
            if index >= len(current):
                return False, None, f"Missing list index at {'.'.join(traversed)}"
            current = current[index]
            continue
        return False, None, f"Cannot traverse scalar at {'.'.join(traversed[:-1])}"
    return True, current, None


def check_expectations(
    case: dict[str, Any],
    *,
    payload: dict[str, Any],
    shape_hint: str,
    applied_filters: list[dict[str, Any]],
) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    checks: list[dict[str, Any]] = []

    expected_status = case["expected_status"]
    status = payload.get("result_status")
    checks.append(
        make_check(
            "expected_status",
            status in as_allowed_values(expected_status),
            expected=expected_status,
            actual=status,
        )
    )

    if "expected_route" in case:
        expected_route = case.get("expected_route")
        route = payload.get("route")
        checks.append(
            make_check(
                "expected_route",
                route in as_allowed_values(expected_route),
                expected=expected_route,
                actual=route,
            )
        )

    if "expected_reason" in case:
        expected_reason = case.get("expected_reason")
        reason = payload.get("result_reason")
        checks.append(
            make_check(
                "expected_reason",
                reason in as_allowed_values(expected_reason),
                expected=expected_reason,
                actual=reason,
            )
        )

    if "expected_shape" in case:
        expected_shape = case.get("expected_shape")
        checks.append(
            make_check(
                "expected_shape",
                shape_hint in as_allowed_values(expected_shape),
                expected=expected_shape,
                actual=shape_hint,
            )
        )

    if "expected_sections" in case:
        expected_sections = case.get("expected_sections") or []
        if expected_sections:
            missing = [name for name in expected_sections if name not in sections]
            checks.append(
                make_check(
                    "expected_sections",
                    not missing,
                    expected=expected_sections,
                    actual=sorted(sections),
                    message=f"Missing section(s): {', '.join(missing)}" if missing else None,
                )
            )
        else:
            checks.append(
                make_check(
                    "expected_sections",
                    not sections,
                    expected=[],
                    actual=sorted(sections),
                )
            )

    expected_row_counts = case.get("expected_row_counts")
    if isinstance(expected_row_counts, dict):
        for section_name, expected_count in expected_row_counts.items():
            rows = sections.get(section_name)
            actual_count = len(rows) if isinstance(rows, list) else None
            checks.append(
                make_check(
                    f"expected_row_counts.{section_name}",
                    actual_count == expected_count,
                    expected=expected_count,
                    actual=actual_count,
                    message=f"Missing section: {section_name}" if rows is None else None,
                )
            )

    expected_filters = case.get("expected_filters")
    if isinstance(expected_filters, list):
        for index, expected_filter in enumerate(expected_filters, start=1):
            if not isinstance(expected_filter, dict):
                checks.append(
                    make_check(
                        f"expected_filters.{index}",
                        False,
                        expected=expected_filter,
                        actual=None,
                        message="Expected filter must be a mapping.",
                    )
                )
                continue
            matched = any(filter_matches(expected_filter, actual) for actual in applied_filters)
            checks.append(
                make_check(
                    f"expected_filters.{index}",
                    matched,
                    expected=expected_filter,
                    actual=applied_filters,
                    message="No matching applied filter found." if not matched else None,
                )
            )

    hard_assertions = case.get("hard_assertions")
    if isinstance(hard_assertions, list):
        for index, assertion in enumerate(hard_assertions, start=1):
            if not isinstance(assertion, dict) or "path" not in assertion:
                checks.append(
                    make_check(
                        f"hard_assertions.{index}",
                        False,
                        expected=assertion,
                        actual=None,
                        message="Hard assertion must contain a path.",
                    )
                )
                continue
            path = str(assertion["path"])
            expected = assertion.get("equals")
            found, actual, message = resolve_dot_path(payload, path)
            checks.append(
                make_check(
                    path,
                    found and actual == expected,
                    expected=expected,
                    actual=actual if found else None,
                    message=message if not found else None,
                )
            )

    fail_count = sum(1 for check in checks if check["status"] == "fail")
    pass_count = len(checks) - fail_count
    return {
        "status": "fail" if fail_count else "pass",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "checks": checks,
    }


def error_expectation_results(exc: Exception) -> dict[str, Any]:
    return {
        "status": "fail",
        "pass_count": 0,
        "fail_count": 1,
        "checks": [
            {
                "name": "query_exception",
                "status": "fail",
                "message": f"{type(exc).__name__}: {exc}",
            }
        ],
    }


def run_case(case: dict[str, Any], *, top_rows: int) -> dict[str, Any]:
    case_id = str(case["id"])
    query = str(case["query"])
    base = {
        "id": case_id,
        "query": query,
        "category": case["category"],
        "priority": case["priority"],
        "expected": case_expectations(case),
    }

    try:
        qr = execute_natural_query(query)
        payload = query_result_to_payload(qr)
    except Exception as exc:  # pragma: no cover - exercised manually through harness.
        return {
            **base,
            "route": None,
            "intent": None,
            "query_class": None,
            "family": None,
            "result_status": "error",
            "result_reason": "exception",
            "ok": False,
            "answer_text": None,
            "answer_text_source": None,
            "shape_hint": "error",
            "shape_source": "backend_approximation",
            "metadata": {},
            "applied_filters": [],
            "sections": {},
            "section_summaries": {},
            "notes": [],
            "caveats": [],
            "errors": [{"type": type(exc).__name__, "message": str(exc)}],
            "expectation_results": error_expectation_results(exc),
        }

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    applied_filters = metadata.get("applied_filters")
    if not isinstance(applied_filters, list):
        applied_filters = []

    answer_text, answer_text_source = answer_text_from_metadata(metadata)
    shape_hint = infer_shape_hint(payload.get("route"), payload.get("result_status"), sections)
    expectation_results = check_expectations(
        case,
        payload=payload,
        shape_hint=shape_hint,
        applied_filters=applied_filters,
    )

    return json_ready(
        {
            **base,
            "route": payload.get("route"),
            "intent": payload.get("intent"),
            "query_class": result.get("query_class") or metadata.get("query_class"),
            "family": result.get("query_class") or metadata.get("query_class"),
            "result_status": payload.get("result_status"),
            "result_reason": payload.get("result_reason"),
            "ok": payload.get("ok"),
            "answer_text": answer_text,
            "answer_text_source": answer_text_source,
            "shape_hint": shape_hint,
            "shape_source": "backend_approximation",
            "metadata": metadata,
            "applied_filters": applied_filters,
            "sections": sections,
            "section_summaries": build_section_summaries(sections, top_rows=top_rows),
            "notes": payload.get("notes") or result.get("notes") or [],
            "caveats": payload.get("caveats") or result.get("caveats") or [],
            "errors": [],
            "expectation_results": expectation_results,
        }
    )


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(json_ready(data), ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(json_ready(row), ensure_ascii=False, sort_keys=True) + "\n")


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    corpus_path: Path,
    output_paths: dict[str, Path],
) -> dict[str, Any]:
    status_counts = Counter(str(row.get("result_status")) for row in rows)
    category_counts = Counter(str(row.get("category")) for row in rows)
    route_counts = Counter(str(row.get("route") or "<none>") for row in rows)
    expectation_case_counts = Counter(
        str((row.get("expectation_results") or {}).get("status")) for row in rows
    )
    expectation_check_counts: Counter[str] = Counter()
    failed_case_ids: list[str] = []
    for row in rows:
        expectation_results = row.get("expectation_results") or {}
        if expectation_results.get("status") == "fail":
            failed_case_ids.append(str(row.get("id")))
        for check in expectation_results.get("checks", []):
            expectation_check_counts[str(check.get("status"))] += 1

    corpus_display = (
        corpus_path.relative_to(ROOT) if corpus_path.is_relative_to(ROOT) else corpus_path
    )
    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "corpus_path": str(corpus_display),
        "case_count": len(rows),
        "result_status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "expectation_case_counts": dict(sorted(expectation_case_counts.items())),
        "expectation_check_counts": dict(sorted(expectation_check_counts.items())),
        "failed_case_ids": failed_case_ids,
        "output_file_paths": {
            key: str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
            for key, path in output_paths.items()
        },
    }


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def md_code(value: Any) -> str:
    if value is None:
        return "`<none>`"
    return f"`{str(value).replace('`', '')}`"


def compact_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def pick_markdown_columns(rows: list[dict[str, Any]], max_columns: int = 10) -> list[str]:
    all_columns = section_columns(rows)
    chosen: list[str] = []
    for column in PREFERRED_MARKDOWN_COLUMNS:
        if column in all_columns and column not in chosen:
            chosen.append(column)
        if len(chosen) >= max_columns:
            return chosen
    for column in all_columns:
        if column not in chosen:
            chosen.append(column)
        if len(chosen) >= max_columns:
            break
    return chosen


def markdown_table(rows: list[dict[str, Any]], *, max_columns: int = 10) -> str:
    if not rows:
        return ""
    columns = pick_markdown_columns(rows, max_columns=max_columns)
    if not columns:
        return ""
    lines = [
        "| " + " | ".join(md_escape(column) for column in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(md_escape(compact_value(row.get(column))) for column in columns)
            + " |"
        )
    return "\n".join(lines)


def format_filters(filters: list[dict[str, Any]]) -> str:
    if not filters:
        return "_none_"
    parts = []
    for item in filters:
        label = item.get("label") or item.get("kind") or "filter"
        value = item.get("value")
        kind = item.get("kind")
        display = f"{label}={value}" if value is not None else str(label)
        if kind:
            display = f"{display} ({kind})"
        parts.append(md_code(display))
    return ", ".join(parts)


def format_sections(section_summaries: dict[str, dict[str, Any]]) -> str:
    if not section_summaries:
        return "_none_"
    return ", ".join(
        f"{md_code(name)} {summary.get('row_count', 0)} row(s)"
        for name, summary in section_summaries.items()
    )


def failed_checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        for check in (row.get("expectation_results") or {}).get("checks", []):
            if check.get("status") == "fail":
                failures.append(
                    {
                        "id": row.get("id"),
                        "query": row.get("query"),
                        "check": check.get("name"),
                        "expected": check.get("expected"),
                        "actual": check.get("actual"),
                        "message": check.get("message"),
                    }
                )
    return failures


def write_markdown(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Raw Query Answer QA Report",
        "",
        "## Run Metadata",
        "",
        f"- Run ID: {md_code(summary['run_id'])}",
        f"- Started: {md_code(summary['started_at'])}",
        f"- Completed: {md_code(summary['completed_at'])}",
        f"- Corpus: {md_code(summary['corpus_path'])}",
        f"- Cases: {md_code(summary['case_count'])}",
        "",
        "## Summary Counts",
        "",
        f"- Result statuses: {md_code(summary['result_status_counts'])}",
        f"- Categories: {md_code(summary['category_counts'])}",
        f"- Routes: {md_code(summary['route_counts'])}",
        f"- Expectation cases: {md_code(summary['expectation_case_counts'])}",
        f"- Expectation checks: {md_code(summary['expectation_check_counts'])}",
        f"- Failed case IDs: {md_code(summary['failed_case_ids'])}",
        "",
        "## Failed Expectations",
        "",
    ]

    failures = failed_checks(rows)
    if failures:
        lines.extend(
            [
                "| Case | Check | Expected | Actual | Message |",
                "|---|---|---|---|---|",
            ]
        )
        for failure in failures:
            lines.append(
                "| "
                + " | ".join(
                    md_escape(compact_value(failure.get(key)))
                    for key in ("id", "check", "expected", "actual", "message")
                )
                + " |"
            )
    else:
        lines.append("_None._")

    lines.extend(["", "## Query Review Cards", ""])

    for row in rows:
        expectation_results = row.get("expectation_results") or {}
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Query: {md_code(row.get('query'))}",
                f"- Category: {md_code(row.get('category'))}",
                f"- Priority: {md_code(row.get('priority'))}",
                f"- Status: {md_code(row.get('result_status'))}",
                f"- Reason: {md_code(row.get('result_reason'))}",
                f"- Route: {md_code(row.get('route'))}",
                f"- Intent: {md_code(row.get('intent'))}",
                f"- Query class: {md_code(row.get('query_class'))}",
                f"- Shape hint: {md_code(row.get('shape_hint'))}",
                f"- Shape source: {md_code(row.get('shape_source'))}",
                (
                    f"- Backend answer text: {md_escape(row['answer_text'])}"
                    if row.get("answer_text")
                    else "- Backend answer text: _not backend-provided_"
                ),
                f"- Filters: {format_filters(row.get('applied_filters') or [])}",
                f"- Sections: {format_sections(row.get('section_summaries') or {})}",
                (
                    f"- Expectations: {md_code(expectation_results.get('status'))} "
                    f"({expectation_results.get('pass_count', 0)} pass, "
                    f"{expectation_results.get('fail_count', 0)} fail)"
                ),
            ]
        )
        if row.get("expected", {}).get("review_notes"):
            lines.append(f"- Review notes: {md_escape(row['expected']['review_notes'])}")
        if row.get("notes"):
            lines.append(f"- Notes: {md_code(row.get('notes'))}")
        if row.get("caveats"):
            lines.append(f"- Caveats: {md_code(row.get('caveats'))}")
        if row.get("errors"):
            lines.append(f"- Errors: {md_code(row.get('errors'))}")

        section_summaries = row.get("section_summaries") or {}
        for section_name, section_summary in section_summaries.items():
            top_rows = section_summary.get("top_rows") or []
            if not top_rows:
                continue
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
                    f"- Columns: {md_escape(shown_columns)}",
                    "",
                    markdown_table(top_rows),
                ]
            )
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n")


def main() -> int:
    args = parse_args()
    corpus_path = resolve_path(args.corpus)
    out_base = resolve_path(args.out)
    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_base / run_id
    report_jsonl_path = run_dir / "report.jsonl"
    report_md_path = run_dir / "report.md"
    summary_path = run_dir / "summary.json"

    version, cases = load_corpus(corpus_path)
    del version
    selected = filter_cases(cases, case_ids=selected_case_ids(args.case), limit=args.limit)

    started_at = datetime.now(UTC).isoformat()
    rows = [run_case(case, top_rows=args.top_rows) for case in selected]
    completed_at = datetime.now(UTC).isoformat()

    run_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "report_jsonl": report_jsonl_path,
        "report_md": report_md_path,
        "summary_json": summary_path,
    }
    summary = summarize_rows(
        rows,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        corpus_path=corpus_path,
        output_paths=output_paths,
    )

    write_jsonl(report_jsonl_path, rows)
    dump_json(summary_path, summary)
    write_markdown(report_md_path, rows, summary)

    failed_case_ids = summary["failed_case_ids"]
    print(f"Wrote raw query answer QA report: {run_dir.relative_to(ROOT)}")
    print(f"Cases: {summary['case_count']}")
    print(f"Result statuses: {summary['result_status_counts']}")
    print(f"Expectation cases: {summary['expectation_case_counts']}")
    if failed_case_ids:
        print(f"Failed case IDs: {', '.join(failed_case_ids)}")
    else:
        print("Failed case IDs: none")

    if failed_case_ids and args.fail_on_expectation_failure:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
