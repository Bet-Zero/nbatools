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
MANUAL_REVIEW_STATUSES = {
    "unreviewed",
    "pass",
    "verified_outlier",
    "needs_followup",
    "semantics_issue",
    "data_quality_question",
    "routing_issue",
    "missing_filter",
    "wrong_shape",
    "bad_answer_text",
    "expected_unsupported",
    "needs_product_decision",
}
SUMMARY_ROUTES = {
    "game_summary",
    "lineup_summary",
    "matchup_by_decade",
    "player_game_summary",
    "player_on_off",
    "player_split_summary",
    "playoff_appearances",
    "playoff_history",
    "record_by_decade",
    "team_record",
    "team_split_summary",
}
SUGGESTED_TAGS_BY_FLAG = {
    "missing_backend_answer_text": ["frontend_hero_extraction"],
    "ok_no_sections": ["shape_section_contract"],
    "top_performance_high_points": ["top_performance_data_quality"],
    "playoff_teams_playoff_season_type": ["opponent_quality_semantics"],
    "expected_unsupported_returned_ok": ["unsupported_no_result_policy"],
    "expected_ok_returned_non_ok": ["routing_or_data_gap"],
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
DEFAULT_VERIFIED_OUTLIERS_PATH = ROOT / "qa" / "verified_outliers.yaml"


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
    parser.add_argument("--verified-outliers", default=str(DEFAULT_VERIFIED_OUTLIERS_PATH))
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
        normalize_manual_review(case)

    version = data.get("version")
    if isinstance(version, int | str) and str(version).isdigit():
        return int(version), cases
    return None, cases


def load_verified_outliers(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = path.read_text()
    if yaml is not None:
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Verified outliers file must be a mapping: {path}")
    entries = data.get("verified_outliers") or []
    if not isinstance(entries, list):
        raise ValueError(f"verified_outliers must be a list: {path}")
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Verified outlier {index} must be a mapping")
    return entries


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


def normalize_manual_review(case: dict[str, Any]) -> dict[str, Any]:
    raw = case.get("manual_review")
    if raw is None:
        return {"status": "unreviewed", "tags": [], "notes": ""}
    if not isinstance(raw, dict):
        raise ValueError(f"Case {case.get('id')} manual_review must be a mapping")

    status = str(raw.get("status") or "unreviewed")
    if status not in MANUAL_REVIEW_STATUSES:
        allowed = ", ".join(sorted(MANUAL_REVIEW_STATUSES))
        raise ValueError(
            f"Case {case.get('id')} has invalid manual_review.status {status!r}; "
            f"expected one of: {allowed}"
        )

    raw_tags = raw.get("tags") or []
    if not isinstance(raw_tags, list):
        raise ValueError(f"Case {case.get('id')} manual_review.tags must be a list")

    notes = raw.get("notes") or ""
    return {
        "status": status,
        "tags": [str(tag) for tag in raw_tags],
        "notes": str(notes),
    }


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


def make_suspicious_flag(
    flag_id: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flag = {"id": flag_id, "message": message}
    if details:
        flag["details"] = json_ready(details)
    return flag


def make_verified_outlier_flag(
    flag_id: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flag = make_suspicious_flag(flag_id, message, details=details)
    flag["status"] = "verified"
    return flag


def expected_allows(case: dict[str, Any], status: str) -> bool:
    return status in as_allowed_values(case.get("expected_status"))


def expected_is_unsupported_like(case: dict[str, Any]) -> bool:
    allowed = {str(value) for value in as_allowed_values(case.get("expected_status"))}
    manual_review = normalize_manual_review(case)
    return (
        (bool(allowed) and allowed <= {"error", "no_result"})
        or str(case.get("category")) == "unsupported_boundary"
        or manual_review["status"] == "expected_unsupported"
    )


def top_performance_high_point_rows(
    *,
    route: str | None,
    shape_hint: str,
    sections: dict[str, Any],
    threshold: int = 75,
) -> list[dict[str, Any]]:
    if shape_hint != "top_performances" and route not in {"top_player_games", "top_team_games"}:
        return []

    matches: list[dict[str, Any]] = []
    for section_name, rows in sections.items():
        if not isinstance(rows, list):
            continue
        for row in rows[:3]:
            if not isinstance(row, dict):
                continue
            if route != "top_player_games" and not row.get("player_name"):
                continue
            points = row.get("pts")
            if isinstance(points, int | float) and points >= threshold:
                matches.append(
                    {
                        "category": "top_performance_high_points",
                        "section": section_name,
                        "rank": row.get("rank"),
                        "player_id": row.get("player_id"),
                        "player_name": row.get("player_name"),
                        "team_name": row.get("team_name"),
                        "team_abbr": row.get("team_abbr"),
                        "opponent_team_abbr": row.get("opponent_team_abbr"),
                        "game_id": row.get("game_id"),
                        "game_date": row.get("game_date"),
                        "stat": "pts",
                        "value": points,
                        "pts": points,
                    }
                )
    return matches


def game_id_variants(value: Any) -> set[str]:
    if value is None:
        return set()
    text = str(value).strip()
    if not text:
        return set()
    if text.endswith(".0"):
        text = text[:-2]
    stripped = text.lstrip("0") or "0"
    return {text, stripped}


def date_prefix(value: Any) -> str:
    return str(value or "").strip()[:10]


def normalized_number(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def value_matches(expected: Any, actual: Any) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    expected_number = normalized_number(expected)
    actual_number = normalized_number(actual)
    if expected_number is not None and actual_number is not None:
        return expected_number == actual_number
    return normalized_match_text(expected) == normalized_match_text(actual)


def outlier_entry_matches_row(entry: dict[str, Any], row: dict[str, Any]) -> bool:
    if entry.get("verification_status") != "verified_official":
        return False
    if normalized_match_text(entry.get("category")) != normalized_match_text(row.get("category")):
        return False
    if str(entry.get("stat") or "").casefold() != str(row.get("stat") or "").casefold():
        return False
    if not value_matches(entry.get("value"), row.get("value")):
        return False
    if date_prefix(entry.get("game_date")) != date_prefix(row.get("game_date")):
        return False

    entry_game_ids = game_id_variants(entry.get("game_id"))
    row_game_ids = game_id_variants(row.get("game_id"))
    if entry_game_ids and row_game_ids and entry_game_ids.isdisjoint(row_game_ids):
        return False

    player_id = entry.get("player_id")
    if player_id is not None and row.get("player_id") is not None:
        return value_matches(player_id, row.get("player_id"))

    return normalized_match_text(entry.get("player_name")) == normalized_match_text(
        row.get("player_name")
    )


def verified_outlier_match(
    row: dict[str, Any],
    verified_outliers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for entry in verified_outliers:
        if outlier_entry_matches_row(entry, row):
            return entry
    return None


def split_verified_high_point_rows(
    rows: list[dict[str, Any]],
    verified_outliers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unverified_rows: list[dict[str, Any]] = []
    verified_rows: list[dict[str, Any]] = []
    for row in rows:
        match = verified_outlier_match(row, verified_outliers)
        if match:
            verified_rows.append({**row, "verified_outlier_id": match.get("id")})
        else:
            unverified_rows.append(row)
    return unverified_rows, verified_rows


def build_review_flags(
    case: dict[str, Any],
    *,
    result_status: str | None,
    route: str | None,
    answer_text: str | None,
    shape_hint: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    verified_outliers: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    flags: list[dict[str, Any]] = []
    verified_flags: list[dict[str, Any]] = []
    priority = str(case.get("priority"))
    query_class = metadata.get("query_class")

    if (
        result_status == "ok"
        and priority in {"p0", "p1"}
        and not answer_text
        and (route in SUMMARY_ROUTES or query_class in {"summary", "split_summary"})
    ):
        flags.append(
            make_suspicious_flag(
                "missing_backend_answer_text",
                "P0/P1 summary-style result has no backend answer text.",
                details={"route": route, "query_class": query_class},
            )
        )

    if result_status == "ok" and not sections:
        flags.append(
            make_suspicious_flag(
                "ok_no_sections",
                "Result status is ok but no result sections were returned.",
                details={"route": route},
            )
        )

    high_point_rows = top_performance_high_point_rows(
        route=route,
        shape_hint=shape_hint,
        sections=sections,
    )
    if high_point_rows:
        unverified_rows, verified_rows = split_verified_high_point_rows(
            high_point_rows,
            verified_outliers or [],
        )
        if unverified_rows:
            flags.append(
                make_suspicious_flag(
                    "top_performance_high_points",
                    "Top performance point total is unusually high (>= 75).",
                    details={"rows": unverified_rows},
                )
            )
        if verified_rows:
            verified_flags.append(
                make_verified_outlier_flag(
                    "top_performance_high_points",
                    "Top performance point total is unusually high (>= 75) but verified official.",
                    details={"rows": verified_rows},
                )
            )

    if (
        "playoff teams" in normalized_match_text(case.get("query"))
        and metadata.get("season_type") == "Playoffs"
    ):
        flags.append(
            make_suspicious_flag(
                "playoff_teams_playoff_season_type",
                'Query contains "playoff teams" but result metadata uses season_type=Playoffs.',
                details={"season": metadata.get("season"), "route": route},
            )
        )

    if result_status == "ok" and expected_is_unsupported_like(case):
        flags.append(
            make_suspicious_flag(
                "expected_unsupported_returned_ok",
                "Case is expected unsupported/error-like but returned ok.",
                details={"expected_status": case.get("expected_status"), "route": route},
            )
        )

    if result_status in {"no_result", "error"} and expected_allows(case, "ok"):
        flags.append(
            make_suspicious_flag(
                "expected_ok_returned_non_ok",
                "Case expects ok but returned no_result/error.",
                details={
                    "expected_status": case.get("expected_status"),
                    "actual_status": result_status,
                },
            )
        )

    return {"suspicious_flags": flags, "verified_outliers": verified_flags}


def build_suspicious_flags(
    case: dict[str, Any],
    *,
    result_status: str | None,
    route: str | None,
    answer_text: str | None,
    shape_hint: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    verified_outliers: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return build_review_flags(
        case,
        result_status=result_status,
        route=route,
        answer_text=answer_text,
        shape_hint=shape_hint,
        metadata=metadata,
        sections=sections,
        verified_outliers=verified_outliers,
    )["suspicious_flags"]


def suggested_review_tags(flags: list[dict[str, Any]]) -> list[str]:
    tags: set[str] = set()
    for flag in flags:
        tags.update(SUGGESTED_TAGS_BY_FLAG.get(str(flag.get("id")), []))
    return sorted(tags)


def run_case(
    case: dict[str, Any],
    *,
    top_rows: int,
    verified_outliers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    case_id = str(case["id"])
    query = str(case["query"])
    manual_review = normalize_manual_review(case)
    base = {
        "id": case_id,
        "query": query,
        "category": case["category"],
        "priority": case["priority"],
        "expected": case_expectations(case),
        "manual_review": manual_review,
    }

    try:
        qr = execute_natural_query(query)
        payload = query_result_to_payload(qr)
    except Exception as exc:  # pragma: no cover - exercised manually through harness.
        review_flags = build_review_flags(
            case,
            result_status="error",
            route=None,
            answer_text=None,
            shape_hint="error",
            metadata={},
            sections={},
            verified_outliers=verified_outliers,
        )
        flags = review_flags["suspicious_flags"]
        verified_flags = review_flags["verified_outliers"]
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
            "suggested_review_tags": suggested_review_tags(flags),
            "suspicious_flags": flags,
            "verified_outliers": verified_flags,
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
    review_flags = build_review_flags(
        case,
        result_status=payload.get("result_status"),
        route=payload.get("route"),
        answer_text=answer_text,
        shape_hint=shape_hint,
        metadata=metadata,
        sections=sections,
        verified_outliers=verified_outliers,
    )
    flags = review_flags["suspicious_flags"]
    verified_flags = review_flags["verified_outliers"]

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
            "suggested_review_tags": suggested_review_tags(flags),
            "suspicious_flags": flags,
            "verified_outliers": verified_flags,
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
    manual_review_status_counts = Counter(
        str((row.get("manual_review") or {}).get("status", "unreviewed")) for row in rows
    )
    manual_review_tag_counts: Counter[str] = Counter()
    suspicious_flag_counts: Counter[str] = Counter()
    verified_outlier_counts: Counter[str] = Counter()
    suggested_review_tag_counts: Counter[str] = Counter()
    expectation_case_counts = Counter(
        str((row.get("expectation_results") or {}).get("status")) for row in rows
    )
    expectation_check_counts: Counter[str] = Counter()
    failed_case_ids: list[str] = []
    suspicious_flag_case_ids: list[str] = []
    verified_outlier_case_ids: list[str] = []
    for row in rows:
        manual_review = row.get("manual_review") or {}
        for tag in manual_review.get("tags", []):
            manual_review_tag_counts[str(tag)] += 1
        flags = row.get("suspicious_flags") or []
        if flags:
            suspicious_flag_case_ids.append(str(row.get("id")))
        for flag in flags:
            suspicious_flag_counts[str(flag.get("id"))] += 1
        verified_outliers = row.get("verified_outliers") or []
        if verified_outliers:
            verified_outlier_case_ids.append(str(row.get("id")))
        for flag in verified_outliers:
            verified_outlier_counts[str(flag.get("id"))] += 1
        for tag in row.get("suggested_review_tags") or []:
            suggested_review_tag_counts[str(tag)] += 1
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
        "manual_review_status_counts": dict(sorted(manual_review_status_counts.items())),
        "manual_review_tag_counts": dict(sorted(manual_review_tag_counts.items())),
        "suspicious_flag_case_count": len(suspicious_flag_case_ids),
        "suspicious_flag_case_ids": suspicious_flag_case_ids,
        "suspicious_flag_counts": dict(sorted(suspicious_flag_counts.items())),
        "verified_outlier_case_count": len(verified_outlier_case_ids),
        "verified_outlier_case_ids": verified_outlier_case_ids,
        "verified_outlier_counts": dict(sorted(verified_outlier_counts.items())),
        "suggested_review_tag_counts": dict(sorted(suggested_review_tag_counts.items())),
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
        f"- Manual review statuses: {md_code(summary['manual_review_status_counts'])}",
        f"- Manual review tags: {md_code(summary['manual_review_tag_counts'])}",
        f"- Suspicious flag cases: {md_code(summary['suspicious_flag_case_count'])}",
        f"- Suspicious flags: {md_code(summary['suspicious_flag_counts'])}",
        f"- Verified outlier cases: {md_code(summary['verified_outlier_case_count'])}",
        f"- Verified outliers: {md_code(summary['verified_outlier_counts'])}",
        f"- Suggested review tags: {md_code(summary['suggested_review_tag_counts'])}",
        f"- Expectation cases: {md_code(summary['expectation_case_counts'])}",
        f"- Expectation checks: {md_code(summary['expectation_check_counts'])}",
        f"- Failed case IDs: {md_code(summary['failed_case_ids'])}",
        "",
        "## Suspicious / Review Flags",
        "",
    ]

    flagged_rows = [row for row in rows if row.get("suspicious_flags")]
    if flagged_rows:
        lines.extend(
            [
                "| Case | Flags | Suggested tags | Manual review |",
                "|---|---|---|---|",
            ]
        )
        for row in flagged_rows:
            flag_ids = ", ".join(str(flag.get("id")) for flag in row.get("suspicious_flags") or [])
            tags = ", ".join(row.get("suggested_review_tags") or [])
            manual_review = row.get("manual_review") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.get("id")),
                        md_escape(flag_ids),
                        md_escape(tags),
                        md_escape(manual_review.get("status", "unreviewed")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("_None._")

    lines.extend(["", "## Verified Outliers", ""])
    verified_rows = [row for row in rows if row.get("verified_outliers")]
    if verified_rows:
        lines.extend(
            [
                "| Case | Flags | Details | Manual review |",
                "|---|---|---|---|",
            ]
        )
        for row in verified_rows:
            flag_ids = ", ".join(str(flag.get("id")) for flag in row.get("verified_outliers") or [])
            detail_parts: list[str] = []
            for flag in row.get("verified_outliers") or []:
                for item in (flag.get("details") or {}).get("rows") or []:
                    player = item.get("player_name") or item.get("team_name") or "row"
                    stat = item.get("stat") or "stat"
                    value = item.get("value")
                    game_date = date_prefix(item.get("game_date"))
                    outlier_id = item.get("verified_outlier_id")
                    detail = f"{player} {value} {stat} on {game_date}"
                    if outlier_id:
                        detail = f"{detail} ({outlier_id})"
                    detail_parts.append(detail)
            manual_review = row.get("manual_review") or {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.get("id")),
                        md_escape(flag_ids),
                        md_escape("; ".join(detail_parts)),
                        md_escape(manual_review.get("status", "unreviewed")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("_None._")

    lines.extend(
        [
            "",
            "## Failed Expectations",
            "",
        ]
    )

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
        manual_review = row.get("manual_review") or {}
        manual_status = manual_review.get("status", "unreviewed")
        manual_tags = ", ".join(manual_review.get("tags") or [])
        manual_display = f"{manual_status}" + (f" [{manual_tags}]" if manual_tags else "")
        lines.append(f"- Manual review: {md_code(manual_display)}")
        if manual_review.get("notes"):
            lines.append(f"- Manual review notes: {md_escape(manual_review.get('notes'))}")
        if row.get("suspicious_flags"):
            flag_ids = ", ".join(str(flag.get("id")) for flag in row["suspicious_flags"])
            lines.append(f"- Suspicious flags: {md_code(flag_ids)}")
        if row.get("verified_outliers"):
            flag_ids = ", ".join(str(flag.get("id")) for flag in row["verified_outliers"])
            lines.append(f"- Verified outliers: {md_code(flag_ids)}")
        if row.get("suggested_review_tags"):
            lines.append(f"- Suggested review tags: {md_code(row.get('suggested_review_tags'))}")
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
    verified_outliers = load_verified_outliers(resolve_path(args.verified_outliers))
    selected = filter_cases(cases, case_ids=selected_case_ids(args.case), limit=args.limit)

    started_at = datetime.now(UTC).isoformat()
    rows = [
        run_case(case, top_rows=args.top_rows, verified_outliers=verified_outliers)
        for case in selected
    ]
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
    print(f"Suspicious flag cases: {summary['suspicious_flag_case_count']}")
    print(f"Verified outlier cases: {summary['verified_outlier_case_count']}")
    if failed_case_ids:
        print(f"Failed case IDs: {', '.join(failed_case_ids)}")
    else:
        print("Failed case IDs: none")

    if failed_case_ids and args.fail_on_expectation_failure:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
