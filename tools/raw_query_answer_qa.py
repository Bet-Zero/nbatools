# ruff: noqa: I001

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
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
ANSWER_TEXT_POLICIES = {
    "requires_backend_answer_text",
    "frontend_hero_expected",
    "no_answer_text_expected",
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
REVIEW_CLOSURE_STATES = {
    "human_review_pending",
    "human_review_complete",
    "human_review_complete_with_followup",
}
PRODUCT_DECISION_STATUSES = {
    "open",
    "resolved",
    "deferred",
}
UI_SPOT_CHECK_STATUSES = {
    "not_run",
    "passed",
    "failed",
    "not_applicable",
}
ACCEPTANCE_VARIANTS = {
    "canonical",
    "short",
    "sentence",
    "synonym",
    "inverse_sibling",
    "nearby_unsupported",
    "typo_partial",
}
ACCEPTANCE_REVIEW_ROLES = {
    "representative",
    "supporting",
    "boundary",
    "decision",
}
ACCEPTANCE_FIELD_NAMES = {
    "family",
    "variant",
    "concept",
    "review_required",
    "review_role",
    "public_surface",
    "no_broad_fallback",
    "sibling_of",
    "intent_model",
    "qualifier_model",
}
HUMAN_REVIEW_PASS_STATUSES = {
    "pass",
    "verified_outlier",
    "expected_unsupported",
}
HUMAN_REVIEW_FOLLOWUP_STATUSES = MANUAL_REVIEW_STATUSES - {
    "unreviewed",
    *HUMAN_REVIEW_PASS_STATUSES,
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
    "missing_backend_answer_text": ["backend_answer_text_required"],
    "ok_no_sections": ["shape_section_contract"],
    "top_performance_high_points": ["top_performance_data_quality"],
    "playoff_teams_playoff_season_type": ["opponent_quality_semantics"],
    "expected_unsupported_returned_ok": ["unsupported_no_result_policy"],
    "expected_ok_returned_non_ok": ["routing_or_data_gap"],
}
ANSWER_TEXT_STATUS_LABELS = {
    "backend_answer_text_present": "backend answer text present",
    "frontend_hero_expected": "frontend-rendered hero expected",
    "missing_backend_answer_text": "backend answer text missing",
    "no_answer_text_expected": "no answer text expected",
    "not_required": "not required",
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
DEFAULT_SLICE_DIR = ROOT / "qa" / "harness_slices"
DEFAULT_ACCEPTANCE_FAMILIES_PATH = ROOT / "qa" / "raw_query_answer_acceptance_families.yaml"
DEFAULT_RAW_QA_OUTPUT_ROOT = ROOT / "outputs" / "raw_query_answer_qa"
RUN_ID_LABEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the raw NBA query answer QA corpus and write review reports."
    )
    parser.add_argument("--corpus", default="qa/raw_query_answer_corpus.yaml")
    parser.add_argument("--out", default="outputs/raw_query_answer_qa")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--overwrite-run-id", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--slice", action="append", default=[])
    parser.add_argument("--failed-from", action="append", default=[])
    parser.add_argument("--compare-to", default=None)
    parser.add_argument("--top-rows", type=int, default=3)
    parser.add_argument("--verified-outliers", default=str(DEFAULT_VERIFIED_OUTLIERS_PATH))
    parser.add_argument("--acceptance-families", default=str(DEFAULT_ACCEPTANCE_FAMILIES_PATH))
    parser.add_argument("--fail-on-expectation-failure", action="store_true")
    return parser.parse_args()


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def validate_run_id_label(run_id: str) -> str:
    label = run_id.strip()
    if not label:
        raise ValueError("--run-id must be a non-empty folder name")
    path = Path(label)
    if path.is_absolute() or path.name != label or label in {".", ".."}:
        raise ValueError("--run-id must be a folder name, not a path")
    if RUN_ID_LABEL_PATTERN.fullmatch(label) is None:
        raise ValueError(
            "--run-id may contain only letters, numbers, dots, hyphens, and underscores, "
            "and must start with a letter or number"
        )
    return label


def validate_overwrite_run_directory(
    run_dir: Path,
    *,
    expected_root: Path = DEFAULT_RAW_QA_OUTPUT_ROOT,
) -> None:
    root = expected_root.resolve(strict=False)
    parent = run_dir.parent.resolve(strict=False)
    target = run_dir.resolve(strict=False)
    if parent != root or target == root or not target.is_relative_to(root):
        raise ValueError(
            "--overwrite-run-id may only replace a named run directory directly under "
            f"{display_path(expected_root)}"
        )
    if run_dir.is_symlink():
        raise ValueError(f"Refusing to overwrite symlinked run directory: {display_path(run_dir)}")


def validate_run_directory_target(
    run_dir: Path,
    *,
    overwrite_run_id: bool,
    expected_root: Path = DEFAULT_RAW_QA_OUTPUT_ROOT,
) -> None:
    if overwrite_run_id:
        validate_overwrite_run_directory(run_dir, expected_root=expected_root)
    if not run_dir.exists():
        return
    if not run_dir.is_dir():
        raise ValueError(
            f"Run output path already exists and is not a directory: {display_path(run_dir)}"
        )
    if not overwrite_run_id:
        raise ValueError(
            f"Run directory already exists: {display_path(run_dir)}. "
            "Use --overwrite-run-id with --run-id to replace it."
        )


def prepare_run_directory(
    run_dir: Path,
    *,
    overwrite_run_id: bool,
    expected_root: Path = DEFAULT_RAW_QA_OUTPUT_ROOT,
) -> None:
    if run_dir.exists():
        if not overwrite_run_id:
            raise ValueError(
                f"Run directory already exists: {display_path(run_dir)}. "
                "Use --overwrite-run-id with --run-id to replace it."
            )
        validate_overwrite_run_directory(run_dir, expected_root=expected_root)
        if not run_dir.is_dir():
            raise ValueError(
                f"Run output path already exists and is not a directory: {display_path(run_dir)}"
            )
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


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
        normalize_answer_text_policy(case)
        normalize_manual_review(case)
        acceptance = normalize_acceptance(case)
        if acceptance:
            case["acceptance"] = acceptance

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


def read_yaml_or_json(path: Path) -> Any:
    raw = path.read_text()
    if yaml is not None:
        return yaml.safe_load(raw)
    return json.loads(raw)


def normalize_registry_variant_entries(
    value: Any,
    *,
    label: str,
) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")

    entries: list[dict[str, str]] = []
    for index, raw_entry in enumerate(value, start=1):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"{label} entry {index} must be a mapping")
        variant = require_nonempty_string(
            raw_entry.get("variant"),
            label=f"{label} entry {index} variant",
        )
        if variant not in ACCEPTANCE_VARIANTS:
            allowed = ", ".join(sorted(ACCEPTANCE_VARIANTS))
            raise ValueError(f"{label} entry {index} variant must be one of: {allowed}")
        entries.append(
            {
                "variant": variant,
                "reason": require_nonempty_string(
                    raw_entry.get("reason"),
                    label=f"{label} entry {index} reason",
                ),
            }
        )
    return entries


def normalize_product_decisions(value: Any, *, label: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")

    decisions: list[dict[str, str]] = []
    for index, raw_decision in enumerate(value, start=1):
        if isinstance(raw_decision, str):
            decisions.append(
                {
                    "question": require_nonempty_string(
                        raw_decision,
                        label=f"{label} entry {index}",
                    )
                }
            )
            continue
        if not isinstance(raw_decision, dict):
            raise ValueError(f"{label} entry {index} must be a string or mapping")
        decision = {
            "question": require_nonempty_string(
                raw_decision.get("question"),
                label=f"{label} entry {index} question",
            )
        }
        for key in ("variant", "current_behavior", "decision_owner", "next_action"):
            if key in raw_decision:
                decision[key] = require_nonempty_string(
                    raw_decision[key],
                    label=f"{label} entry {index} {key}",
                )
        if "variant" in decision and decision["variant"] not in ACCEPTANCE_VARIANTS:
            allowed = ", ".join(sorted(ACCEPTANCE_VARIANTS))
            raise ValueError(f"{label} entry {index} variant must be one of: {allowed}")
        status = str(raw_decision.get("status") or "open")
        if status not in PRODUCT_DECISION_STATUSES:
            allowed = ", ".join(sorted(PRODUCT_DECISION_STATUSES))
            raise ValueError(f"{label} entry {index} status must be one of: {allowed}")
        decision["status"] = status
        decisions.append(decision)
    return decisions


def normalize_review_closure(value: Any, *, label: str) -> dict[str, Any]:
    if value is None:
        return {"state": "human_review_pending"}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")

    state = require_nonempty_string(value.get("state"), label=f"{label}.state")
    if state not in REVIEW_CLOSURE_STATES:
        allowed = ", ".join(sorted(REVIEW_CLOSURE_STATES))
        raise ValueError(f"{label}.state must be one of: {allowed}")

    closure: dict[str, Any] = {"state": state}
    for key in ("scope", "reviewed_run_id", "completed_on", "notes"):
        if key in value:
            closure[key] = require_nonempty_string(value[key], label=f"{label}.{key}")
    if "case_count" in value:
        case_count = value["case_count"]
        if not isinstance(case_count, int) or case_count <= 0:
            raise ValueError(f"{label}.case_count must be a positive integer")
        closure["case_count"] = case_count

    raw_ui_spot_check = value.get("ui_spot_check")
    if raw_ui_spot_check is not None:
        if not isinstance(raw_ui_spot_check, dict):
            raise ValueError(f"{label}.ui_spot_check must be a mapping")
        status = str(raw_ui_spot_check.get("status") or "not_run")
        if status not in UI_SPOT_CHECK_STATUSES:
            allowed = ", ".join(sorted(UI_SPOT_CHECK_STATUSES))
            raise ValueError(f"{label}.ui_spot_check.status must be one of: {allowed}")
        ui_spot_check: dict[str, str] = {"status": status}
        if "notes" in raw_ui_spot_check:
            ui_spot_check["notes"] = require_nonempty_string(
                raw_ui_spot_check["notes"],
                label=f"{label}.ui_spot_check.notes",
            )
        closure["ui_spot_check"] = ui_spot_check

    return closure


def load_acceptance_family_registry(path: Path) -> dict[str, Any]:
    data = read_yaml_or_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Acceptance family registry must be a mapping: {path}")
    if data.get("version") != 1:
        raise ValueError(f"Acceptance family registry version must be 1: {path}")
    raw_families = data.get("families")
    if not isinstance(raw_families, list):
        raise ValueError(f"Acceptance family registry must contain a families list: {path}")

    families: list[dict[str, Any]] = []
    family_ids: set[str] = set()
    for index, raw_family in enumerate(raw_families, start=1):
        if not isinstance(raw_family, dict):
            raise ValueError(f"Acceptance family registry entry {index} must be a mapping")
        family_id = require_nonempty_string(
            raw_family.get("id"),
            label=f"Acceptance family registry entry {index} id",
        )
        if family_id in family_ids:
            raise ValueError(f"Duplicate acceptance family id: {family_id}")
        family_ids.add(family_id)

        public_surface = raw_family.get("public_surface")
        if not isinstance(public_surface, bool):
            raise ValueError(f"Acceptance family {family_id} public_surface must be a boolean")
        required_variants = normalize_string_list(
            raw_family.get("required_variants"),
            label=f"Acceptance family {family_id} required_variants",
        )
        invalid_variants = sorted(set(required_variants) - ACCEPTANCE_VARIANTS)
        if invalid_variants:
            raise ValueError(
                f"Acceptance family {family_id} has invalid required_variants: {invalid_variants}"
            )
        if len(required_variants) != len(set(required_variants)):
            raise ValueError(f"Acceptance family {family_id} has duplicate required_variants")

        not_applicable = normalize_registry_variant_entries(
            raw_family.get("not_applicable_variants"),
            label=f"Acceptance family {family_id} not_applicable_variants",
        )
        intentionally_unsupported = normalize_registry_variant_entries(
            raw_family.get("intentionally_unsupported_variants"),
            label=f"Acceptance family {family_id} intentionally_unsupported_variants",
        )
        resolved_variants = {
            entry["variant"] for entry in [*not_applicable, *intentionally_unsupported]
        }
        if len(resolved_variants) != len(not_applicable) + len(intentionally_unsupported):
            raise ValueError(
                f"Acceptance family {family_id} variants cannot appear in multiple resolution lists"
            )

        families.append(
            {
                "id": family_id,
                "label": require_nonempty_string(
                    raw_family.get("label"),
                    label=f"Acceptance family {family_id} label",
                ),
                "public_surface": public_surface,
                "required_variants": required_variants,
                "not_applicable_variants": not_applicable,
                "intentionally_unsupported_variants": intentionally_unsupported,
                "coverage_questions": normalize_string_list(
                    raw_family.get("coverage_questions") or [],
                    label=f"Acceptance family {family_id} coverage_questions",
                ),
                "sibling_families": normalize_string_list(
                    raw_family.get("sibling_families") or [],
                    label=f"Acceptance family {family_id} sibling_families",
                ),
                "product_decisions": normalize_product_decisions(
                    raw_family.get("product_decisions"),
                    label=f"Acceptance family {family_id} product_decisions",
                ),
            }
        )

    for family in families:
        unknown_siblings = sorted(set(family["sibling_families"]) - family_ids)
        if unknown_siblings:
            raise ValueError(
                f"Acceptance family {family['id']} has unknown sibling_families: {unknown_siblings}"
            )

    return {
        "version": data.get("version"),
        "surface": require_nonempty_string(
            data.get("surface"),
            label="Acceptance family registry surface",
        ),
        "review_closure": normalize_review_closure(
            data.get("review_closure"),
            label="Acceptance family registry review_closure",
        ),
        "families": families,
        "families_by_id": {family["id"]: family for family in families},
    }


def validate_corpus_acceptance(
    cases: list[dict[str, Any]],
    family_registry: dict[str, Any],
) -> None:
    families_by_id = family_registry.get("families_by_id") or {}
    known_case_ids = {str(case["id"]) for case in cases}
    for case in cases:
        acceptance = case.get("acceptance") or {}
        if not acceptance:
            continue
        family = acceptance["family"]
        if family not in families_by_id:
            raise ValueError(
                f"Case {case.get('id')} acceptance.family {family!r} is not in the registry"
            )
        raw_siblings = acceptance.get("sibling_of") or []
        siblings = [raw_siblings] if isinstance(raw_siblings, str) else raw_siblings
        unknown_siblings = sorted(set(siblings) - known_case_ids)
        if unknown_siblings:
            raise ValueError(
                f"Case {case.get('id')} acceptance.sibling_of has unknown case ids: "
                f"{unknown_siblings}"
            )


def selected_case_ids(values: list[str]) -> set[str]:
    ids: set[str] = set()
    for value in values:
        for case_id in value.split(","):
            case_id = case_id.strip()
            if case_id:
                ids.add(case_id)
    return ids


def resolve_slice_path(value: str) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute() or raw_path.parent != Path(".") or raw_path.suffix:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
    else:
        path = DEFAULT_SLICE_DIR / f"{value}.yaml"
    if not path.exists():
        raise ValueError(f"Slice file not found for {value!r}: {display_path(path)}")
    return path


def load_slice_case_ids(value: str) -> list[str]:
    path = resolve_slice_path(value)
    data = read_yaml_or_json(path)
    if isinstance(data, dict):
        raw_case_ids = data.get("case_ids")
    elif isinstance(data, list):
        raw_case_ids = data
    else:
        raise ValueError(f"Slice file must be a mapping or list: {display_path(path)}")
    if not isinstance(raw_case_ids, list):
        raise ValueError(f"Slice file must contain a case_ids list: {display_path(path)}")

    case_ids: list[str] = []
    for index, raw_case_id in enumerate(raw_case_ids, start=1):
        case_id = str(raw_case_id).strip()
        if not case_id:
            raise ValueError(f"Slice {display_path(path)} has blank case id at index {index}")
        case_ids.append(case_id)
    return case_ids


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} must be a mapping: {display_path(path)}")
        rows.append(row)
    return rows


def expectation_failed(row: dict[str, Any]) -> bool:
    expectation_results = row.get("expectation_results") or {}
    if not isinstance(expectation_results, dict):
        return False
    status = str(expectation_results.get("status") or "").casefold()
    if status in {"fail", "failed"}:
        return True
    fail_count = expectation_results.get("fail_count")
    if isinstance(fail_count, int | float) and fail_count > 0:
        return True
    return any(
        str(check.get("status") or "").casefold() in {"fail", "failed"}
        for check in expectation_results.get("checks") or []
        if isinstance(check, dict)
    )


def failed_case_ids_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("id")) for row in rows if row.get("id") and expectation_failed(row)]


def load_failed_case_ids(path: Path) -> list[str]:
    if not path.exists():
        raise ValueError(f"Failed-from path does not exist: {display_path(path)}")
    if path.suffix == ".jsonl":
        return failed_case_ids_from_rows(read_jsonl_rows(path))

    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Failed-from JSON must be a mapping: {display_path(path)}")
    raw_case_ids = data.get("failed_case_ids")
    if not isinstance(raw_case_ids, list):
        raise ValueError(
            f"Failed-from summary must contain failed_case_ids list: {display_path(path)}"
        )
    return [str(case_id).strip() for case_id in raw_case_ids if str(case_id).strip()]


def collect_selected_case_ids(
    *,
    case_values: list[str],
    slice_values: list[str],
    failed_from_values: list[str],
) -> tuple[set[str], bool]:
    case_ids = selected_case_ids(case_values)
    for slice_value in slice_values:
        case_ids.update(load_slice_case_ids(slice_value))
    for failed_from_value in failed_from_values:
        case_ids.update(load_failed_case_ids(resolve_path(failed_from_value)))
    explicit_selection = bool(case_values or slice_values or failed_from_values)
    return case_ids, explicit_selection


def filter_cases(
    cases: list[dict[str, Any]],
    *,
    case_ids: set[str],
    limit: int | None,
    explicit_selection: bool = False,
) -> list[dict[str, Any]]:
    filtered = cases
    if explicit_selection:
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


def normalize_answer_text_policy(case: dict[str, Any]) -> str | None:
    raw = case.get("answer_text_policy")
    if raw is None:
        return None
    policy = str(raw)
    if policy not in ANSWER_TEXT_POLICIES:
        allowed = ", ".join(sorted(ANSWER_TEXT_POLICIES))
        raise ValueError(
            f"Case {case.get('id')} has invalid answer_text_policy {policy!r}; "
            f"expected one of: {allowed}"
        )
    return policy


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


def require_nonempty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def normalize_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return [require_nonempty_string(item, label=f"{label} entry") for item in value]


def has_hard_assertion(case: dict[str, Any], path_fragment: str | None = None) -> bool:
    for assertion in case.get("hard_assertions") or []:
        if not isinstance(assertion, dict) or "path" not in assertion:
            continue
        if path_fragment is None or path_fragment in str(assertion["path"]):
            return True
    return False


def validate_no_broad_fallback_proof(case: dict[str, Any]) -> None:
    acceptance = case.get("acceptance") or {}
    if not acceptance.get("no_broad_fallback"):
        return

    case_id = case.get("id")
    expected_status = case.get("expected_status")
    if not isinstance(expected_status, str):
        raise ValueError(
            f"Case {case_id} acceptance.no_broad_fallback requires one exact expected_status"
        )
    if expected_status not in {"ok", "no_result", "error"}:
        raise ValueError(
            f"Case {case_id} acceptance.no_broad_fallback expected_status must be "
            "ok, no_result, or error"
        )
    if "expected_route" not in case:
        raise ValueError(
            f"Case {case_id} acceptance.no_broad_fallback requires expected_route, "
            "including explicit null for unrouted cases"
        )

    has_scoped_contract = any(
        (
            bool(case.get("expected_filters")),
            "expected_sections" in case,
            bool(case.get("expected_row_counts")),
            has_hard_assertion(case),
        )
    )
    if expected_status == "ok":
        if case.get("expected_route") is None:
            raise ValueError(
                f"Case {case_id} acceptance.no_broad_fallback supported proof requires "
                "a non-null expected_route"
            )
        if not has_scoped_contract:
            raise ValueError(
                f"Case {case_id} acceptance.no_broad_fallback supported proof requires "
                "expected_filters, expected_sections, expected_row_counts, or hard_assertions"
            )
        return

    has_boundary_contract = any(
        (
            "expected_reason" in case,
            case.get("expected_sections") == [],
            bool(case.get("expected_filters")),
            has_hard_assertion(case),
        )
    )
    if not has_boundary_contract:
        raise ValueError(
            f"Case {case_id} acceptance.no_broad_fallback unsupported proof requires "
            "expected_reason, empty expected_sections, expected_filters, or hard_assertions"
        )


def normalize_acceptance(case: dict[str, Any]) -> dict[str, Any]:
    raw = case.get("acceptance")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Case {case.get('id')} acceptance must be a mapping")

    unknown = sorted(set(raw) - ACCEPTANCE_FIELD_NAMES)
    if unknown:
        raise ValueError(f"Case {case.get('id')} acceptance has unknown fields: {unknown}")

    acceptance: dict[str, Any] = {
        "family": require_nonempty_string(
            raw.get("family"),
            label=f"Case {case.get('id')} acceptance.family",
        ),
        "variant": require_nonempty_string(
            raw.get("variant"),
            label=f"Case {case.get('id')} acceptance.variant",
        ),
    }
    if acceptance["variant"] not in ACCEPTANCE_VARIANTS:
        allowed = ", ".join(sorted(ACCEPTANCE_VARIANTS))
        raise ValueError(
            f"Case {case.get('id')} has invalid acceptance.variant "
            f"{acceptance['variant']!r}; expected one of: {allowed}"
        )

    for key in ("concept", "intent_model"):
        if key in raw:
            acceptance[key] = require_nonempty_string(
                raw[key],
                label=f"Case {case.get('id')} acceptance.{key}",
            )
    for key in ("review_required", "public_surface", "no_broad_fallback"):
        if key in raw:
            if not isinstance(raw[key], bool):
                raise ValueError(f"Case {case.get('id')} acceptance.{key} must be a boolean")
            acceptance[key] = raw[key]
    if "review_role" in raw:
        review_role = require_nonempty_string(
            raw["review_role"],
            label=f"Case {case.get('id')} acceptance.review_role",
        )
        if review_role not in ACCEPTANCE_REVIEW_ROLES:
            allowed = ", ".join(sorted(ACCEPTANCE_REVIEW_ROLES))
            raise ValueError(
                f"Case {case.get('id')} has invalid acceptance.review_role "
                f"{review_role!r}; expected one of: {allowed}"
            )
        acceptance["review_role"] = review_role
    if "sibling_of" in raw:
        sibling_of = raw["sibling_of"]
        if isinstance(sibling_of, str):
            acceptance["sibling_of"] = require_nonempty_string(
                sibling_of,
                label=f"Case {case.get('id')} acceptance.sibling_of",
            )
        else:
            acceptance["sibling_of"] = normalize_string_list(
                sibling_of,
                label=f"Case {case.get('id')} acceptance.sibling_of",
            )
    if "qualifier_model" in raw:
        acceptance["qualifier_model"] = normalize_string_list(
            raw["qualifier_model"],
            label=f"Case {case.get('id')} acceptance.qualifier_model",
        )

    validate_no_broad_fallback_proof({**case, "acceptance": acceptance})
    return acceptance


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


def format_summary_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def row_entity_label(row: dict[str, Any]) -> str:
    for key in ("player_name", "team_name", "team_abbr"):
        value = row.get(key)
        if value:
            return str(value)
    return "row"


def row_stat_label(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    stat = metadata.get("stat")
    if isinstance(stat, str) and stat in row:
        return f"{format_summary_number(row[stat])} {stat.upper()}"
    for key in ("pts", "ast", "reb", "stl", "blk", "fg3m", "wins", "count"):
        if key in row:
            return f"{format_summary_number(row[key])} {key.upper()}"
    return ""


def row_matchup_label(row: dict[str, Any]) -> str:
    date_text = date_prefix(row.get("game_date"))
    team = row.get("team_abbr") or row.get("team_name")
    opponent = row.get("opponent_team_abbr") or row.get("opp_abbr")
    parts = [
        part for part in (date_text, team, "vs" if team and opponent else None, opponent) if part
    ]
    return " ".join(str(part) for part in parts)


def build_answer_summary(
    *,
    result_status: str | None,
    result_reason: str | None,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> str | None:
    """Build a compact QA-only fact line for report review."""
    if result_status in {"no_result", "error"}:
        reason = result_reason or "unknown"
        return f"No answer rows returned; reason={reason}"

    count_rows = sections.get("count")
    if isinstance(count_rows, list) and count_rows and isinstance(count_rows[0], dict):
        count = count_rows[0].get("count")
        if count is not None:
            return f"Count: {format_summary_number(count)}"

    summary_rows = sections.get("summary")
    if isinstance(summary_rows, list) and summary_rows and isinstance(summary_rows[0], dict):
        row = summary_rows[0]
        entity = row_entity_label(row)
        bits: list[str] = []
        games = row.get("games")
        wins = row.get("wins")
        losses = row.get("losses")
        if wins is not None and losses is not None:
            record = f"{format_summary_number(wins)}-{format_summary_number(losses)}"
            if games is not None:
                record = f"{record} over {format_summary_number(games)} games"
            bits.append(record)
        elif games is not None:
            bits.append(f"{format_summary_number(games)} games")
        for key, label in (("pts_avg", "PPG"), ("reb_avg", "RPG"), ("ast_avg", "APG")):
            if key in row:
                bits.append(f"{format_summary_number(row[key])} {label}")
        season_type = row.get("season_type") or metadata.get("season_type")
        if season_type:
            bits.append(str(season_type))
        return f"{entity} -- {', '.join(bits)}" if bits else entity

    for section_name in ("leaderboard", "finder", "streak", "split_comparison", "by_season"):
        rows = sections.get(section_name)
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            continue
        row = rows[0]
        entity = row_entity_label(row)
        stat_text = row_stat_label(row, metadata)
        matchup = row_matchup_label(row)
        details = ", ".join(part for part in (stat_text, matchup) if part)
        prefix = "Top row" if section_name in {"leaderboard", "finder"} else section_name
        return f"{prefix}: {entity}" + (f" -- {details}" if details else "")

    if route:
        return f"No compact answer summary available; route={route}"
    return None


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


def make_informational_flag(
    flag_id: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    flag = make_suspicious_flag(flag_id, message, details=details)
    flag["severity"] = "informational"
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


def legacy_requires_backend_answer_text(
    case: dict[str, Any],
    *,
    result_status: str | None,
    route: str | None,
    metadata: dict[str, Any],
) -> bool:
    priority = str(case.get("priority"))
    query_class = metadata.get("query_class")
    return (
        result_status == "ok"
        and priority in {"p0", "p1"}
        and (route in SUMMARY_ROUTES or query_class in {"summary", "split_summary"})
    )


def classify_answer_text(
    case: dict[str, Any],
    *,
    result_status: str | None,
    route: str | None,
    answer_text: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    policy = normalize_answer_text_policy(case)
    query_class = metadata.get("query_class")

    if answer_text:
        return {
            "answer_text_policy": policy,
            "answer_text_status": "backend_answer_text_present",
            "suspicious_flags": [],
            "informational_flags": [],
        }

    details = {
        "route": route,
        "query_class": query_class,
        "answer_text_policy": policy,
    }
    if policy == "frontend_hero_expected":
        if result_status == "ok":
            return {
                "answer_text_policy": policy,
                "answer_text_status": "frontend_hero_expected",
                "suspicious_flags": [],
                "informational_flags": [
                    make_informational_flag(
                        "frontend_hero_expected",
                        "Frontend result component is expected to provide the hero answer text.",
                        details=details,
                    )
                ],
            }
        return {
            "answer_text_policy": policy,
            "answer_text_status": "not_required",
            "suspicious_flags": [],
            "informational_flags": [],
        }

    if policy == "no_answer_text_expected":
        return {
            "answer_text_policy": policy,
            "answer_text_status": "no_answer_text_expected",
            "suspicious_flags": [],
            "informational_flags": [],
        }

    if policy == "requires_backend_answer_text" and result_status == "ok":
        return {
            "answer_text_policy": policy,
            "answer_text_status": "missing_backend_answer_text",
            "suspicious_flags": [
                make_suspicious_flag(
                    "missing_backend_answer_text",
                    (
                        "Case requires backend answer text but metadata has no "
                        "answer_phrase or count_phrase."
                    ),
                    details=details,
                )
            ],
            "informational_flags": [],
        }

    if policy is None and legacy_requires_backend_answer_text(
        case,
        result_status=result_status,
        route=route,
        metadata=metadata,
    ):
        return {
            "answer_text_policy": policy,
            "answer_text_status": "missing_backend_answer_text",
            "suspicious_flags": [
                make_suspicious_flag(
                    "missing_backend_answer_text",
                    "P0/P1 summary-style result has no backend answer text.",
                    details=details,
                )
            ],
            "informational_flags": [],
        }

    return {
        "answer_text_policy": policy,
        "answer_text_status": "not_required",
        "suspicious_flags": [],
        "informational_flags": [],
    }


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
) -> dict[str, Any]:
    answer_text_review = classify_answer_text(
        case,
        result_status=result_status,
        route=route,
        answer_text=answer_text,
        metadata=metadata,
    )
    flags: list[dict[str, Any]] = list(answer_text_review["suspicious_flags"])
    informational_flags: list[dict[str, Any]] = list(answer_text_review["informational_flags"])
    verified_flags: list[dict[str, Any]] = []

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

    return {
        "answer_text_policy": answer_text_review["answer_text_policy"],
        "answer_text_status": answer_text_review["answer_text_status"],
        "suspicious_flags": flags,
        "informational_flags": informational_flags,
        "verified_outliers": verified_flags,
    }


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
    answer_text_policy = normalize_answer_text_policy(case)
    acceptance = normalize_acceptance(case)
    base = {
        "id": case_id,
        "query": query,
        "category": case["category"],
        "priority": case["priority"],
        "expected": case_expectations(case),
        "manual_review": manual_review,
        "answer_text_policy": answer_text_policy,
        "acceptance": acceptance,
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
        informational_flags = review_flags["informational_flags"]
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
            "answer_text_status": review_flags["answer_text_status"],
            "answer_summary": "No answer rows returned; reason=exception",
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
            "informational_flags": informational_flags,
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
    informational_flags = review_flags["informational_flags"]
    verified_flags = review_flags["verified_outliers"]
    answer_summary = build_answer_summary(
        result_status=payload.get("result_status"),
        result_reason=payload.get("result_reason"),
        route=payload.get("route"),
        metadata=metadata,
        sections=sections,
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
            "answer_text_status": review_flags["answer_text_status"],
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
            "expectation_results": expectation_results,
            "suggested_review_tags": suggested_review_tags(flags),
            "suspicious_flags": flags,
            "informational_flags": informational_flags,
            "verified_outliers": verified_flags,
        }
    )


def run_case_with_timing(
    case: dict[str, Any],
    *,
    top_rows: int,
    verified_outliers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    row = run_case(case, top_rows=top_rows, verified_outliers=verified_outliers)
    row["duration_seconds"] = round(time.monotonic() - started, 6)
    return row


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(json_ready(data), ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(json_ready(row), ensure_ascii=False, sort_keys=True) + "\n")


def build_slowest_cases(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    timed_rows: list[dict[str, Any]] = []
    for row in rows:
        duration = row.get("duration_seconds")
        if not isinstance(duration, int | float):
            continue
        timed_rows.append(
            {
                "id": row.get("id"),
                "query": row.get("query"),
                "duration_seconds": round(float(duration), 6),
                "result_status": row.get("result_status"),
                "route": row.get("route"),
            }
        )
    timed_rows.sort(key=lambda row: float(row["duration_seconds"]), reverse=True)
    return timed_rows[:limit]


def count_flag_ids(rows: list[dict[str, Any]], flag_key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for flag in row.get(flag_key) or []:
            if isinstance(flag, dict):
                counts[str(flag.get("id"))] += 1
    return dict(sorted(counts.items()))


def result_status_counts_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get("result_status")) for row in rows).items()))


def count_delta(current: dict[str, int], previous: dict[str, int]) -> dict[str, int]:
    delta = {
        key: int(current.get(key, 0)) - int(previous.get(key, 0))
        for key in sorted(set(current) | set(previous))
    }
    return {key: value for key, value in delta.items() if value}


def load_comparison_reference(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Compare-to path does not exist: {display_path(path)}")
    if path.suffix == ".jsonl":
        rows = read_jsonl_rows(path)
        return {
            "source_path": display_path(path),
            "source_type": "report_jsonl",
            "detail_level": "per_case",
            "case_count": len(rows),
            "failed_case_ids": failed_case_ids_from_rows(rows),
            "result_status_counts": result_status_counts_from_rows(rows),
            "suspicious_flag_counts": count_flag_ids(rows, "suspicious_flags"),
            "verified_outlier_counts": count_flag_ids(rows, "verified_outliers"),
            "rows_by_id": {str(row.get("id")): row for row in rows if row.get("id")},
        }

    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Compare-to summary must be a mapping: {display_path(path)}")
    return {
        "source_path": display_path(path),
        "source_type": "summary_json",
        "detail_level": "summary_only",
        "case_count": int(data.get("case_count") or 0),
        "failed_case_ids": [str(case_id) for case_id in data.get("failed_case_ids") or []],
        "result_status_counts": {
            str(key): int(value) for key, value in (data.get("result_status_counts") or {}).items()
        },
        "suspicious_flag_counts": {
            str(key): int(value)
            for key, value in (data.get("suspicious_flag_counts") or {}).items()
        },
        "verified_outlier_counts": {
            str(key): int(value)
            for key, value in (data.get("verified_outlier_counts") or {}).items()
        },
        "rows_by_id": {},
    }


def build_route_status_drift(
    rows: list[dict[str, Any]],
    previous_rows_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("id"))
        previous = previous_rows_by_id.get(case_id)
        if not previous:
            continue
        previous_route = previous.get("route")
        current_route = row.get("route")
        previous_status = previous.get("result_status")
        current_status = row.get("result_status")
        if previous_route == current_route and previous_status == current_status:
            continue
        drift.append(
            {
                "id": case_id,
                "previous_route": previous_route,
                "current_route": current_route,
                "previous_result_status": previous_status,
                "current_result_status": current_status,
            }
        )
    return drift


def build_run_comparison(rows: list[dict[str, Any]], compare_to_path: Path) -> dict[str, Any]:
    reference = load_comparison_reference(compare_to_path)
    current_failed_case_ids = failed_case_ids_from_rows(rows)
    current_failed = set(current_failed_case_ids)
    previous_failed = set(reference["failed_case_ids"])
    current_case_ids = [str(row.get("id")) for row in rows if row.get("id")]
    current_case_id_set = set(current_case_ids)
    previous_rows_by_id = reference["rows_by_id"]

    current_result_counts = result_status_counts_from_rows(rows)
    current_suspicious_counts = count_flag_ids(rows, "suspicious_flags")
    current_verified_counts = count_flag_ids(rows, "verified_outliers")
    suspicious_flag_counts_delta = count_delta(
        current_suspicious_counts,
        reference["suspicious_flag_counts"],
    )
    verified_outlier_counts_delta = count_delta(
        current_verified_counts,
        reference["verified_outlier_counts"],
    )
    route_status_drift = build_route_status_drift(rows, previous_rows_by_id)

    notes: list[str] = []
    if reference["detail_level"] == "summary_only":
        notes.append(
            "Comparison source is summary-only; route/status drift and overlapping-case "
            "presence are unavailable."
        )
    if len(rows) != reference["case_count"]:
        notes.append(
            "Case count differs; count deltas compare this run selection against the "
            "reference source."
        )

    return {
        "source_path": reference["source_path"],
        "source_type": reference["source_type"],
        "detail_level": reference["detail_level"],
        "current_case_count": len(rows),
        "previous_case_count": reference["case_count"],
        "case_count_delta": len(rows) - reference["case_count"],
        "current_failed_case_count": len(current_failed),
        "previous_failed_case_count": len(previous_failed),
        "failed_case_delta": len(current_failed) - len(previous_failed),
        "newly_failing_case_ids": [
            case_id for case_id in current_failed_case_ids if case_id not in previous_failed
        ],
        "newly_passing_case_ids": [
            case_id
            for case_id in current_case_ids
            if case_id in previous_failed and case_id not in current_failed
        ],
        "previous_failed_not_rerun_case_ids": sorted(previous_failed - current_case_id_set),
        "result_status_count_delta": count_delta(
            current_result_counts,
            reference["result_status_counts"],
        ),
        "suspicious_flag_count_delta": sum(current_suspicious_counts.values())
        - sum(reference["suspicious_flag_counts"].values()),
        "suspicious_flag_counts_delta": suspicious_flag_counts_delta,
        "verified_outlier_count_delta": sum(current_verified_counts.values())
        - sum(reference["verified_outlier_counts"].values()),
        "verified_outlier_counts_delta": verified_outlier_counts_delta,
        "route_status_drift": route_status_drift,
        "notes": notes,
    }


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
    answer_text_policy_counts = Counter(
        str(row.get("answer_text_policy") or "<unspecified>") for row in rows
    )
    answer_text_status_counts = Counter(str(row.get("answer_text_status")) for row in rows)
    manual_review_tag_counts: Counter[str] = Counter()
    suspicious_flag_counts: Counter[str] = Counter()
    informational_flag_counts: Counter[str] = Counter()
    verified_outlier_counts: Counter[str] = Counter()
    suggested_review_tag_counts: Counter[str] = Counter()
    expectation_case_counts = Counter(
        str((row.get("expectation_results") or {}).get("status")) for row in rows
    )
    expectation_check_counts: Counter[str] = Counter()
    failed_case_ids: list[str] = []
    suspicious_flag_case_ids: list[str] = []
    informational_flag_case_ids: list[str] = []
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
        informational_flags = row.get("informational_flags") or []
        if informational_flags:
            informational_flag_case_ids.append(str(row.get("id")))
        for flag in informational_flags:
            informational_flag_counts[str(flag.get("id"))] += 1
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

    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "corpus_path": display_path(corpus_path),
        "case_count": len(rows),
        "result_status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "manual_review_status_counts": dict(sorted(manual_review_status_counts.items())),
        "manual_review_tag_counts": dict(sorted(manual_review_tag_counts.items())),
        "answer_text_policy_counts": dict(sorted(answer_text_policy_counts.items())),
        "answer_text_status_counts": dict(sorted(answer_text_status_counts.items())),
        "suspicious_flag_case_count": len(suspicious_flag_case_ids),
        "suspicious_flag_case_ids": suspicious_flag_case_ids,
        "suspicious_flag_counts": dict(sorted(suspicious_flag_counts.items())),
        "informational_flag_case_count": len(informational_flag_case_ids),
        "informational_flag_case_ids": informational_flag_case_ids,
        "informational_flag_counts": dict(sorted(informational_flag_counts.items())),
        "verified_outlier_case_count": len(verified_outlier_case_ids),
        "verified_outlier_case_ids": verified_outlier_case_ids,
        "verified_outlier_counts": dict(sorted(verified_outlier_counts.items())),
        "suggested_review_tag_counts": dict(sorted(suggested_review_tag_counts.items())),
        "expectation_case_counts": dict(sorted(expectation_case_counts.items())),
        "expectation_check_counts": dict(sorted(expectation_check_counts.items())),
        "failed_case_ids": failed_case_ids,
        "slowest_cases": build_slowest_cases(rows),
        "output_file_paths": {key: display_path(path) for key, path in output_paths.items()},
    }


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def md_code(value: Any) -> str:
    if value is None:
        return "`<none>`"
    return f"`{str(value).replace('`', '')}`"


def answer_text_status_label(status: Any) -> str:
    status_text = str(status or "")
    return str(ANSWER_TEXT_STATUS_LABELS.get(status_text, status or ""))


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


def human_review_status(rows: list[dict[str, Any]]) -> str:
    required_rows = [row for row in rows if (row.get("acceptance") or {}).get("review_required")]
    if not required_rows:
        return "pending"

    statuses = {
        str((row.get("manual_review") or {}).get("status", "unreviewed")) for row in required_rows
    }
    if statuses & HUMAN_REVIEW_FOLLOWUP_STATUSES:
        return "reviewed_followup"
    if statuses and statuses <= HUMAN_REVIEW_PASS_STATUSES:
        return "reviewed_pass"
    return "pending"


def variant_resolution_map(
    family: dict[str, Any],
    family_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_variant: dict[str, list[str]] = {}
    for row in family_rows:
        variant = (row.get("acceptance") or {}).get("variant")
        if variant:
            rows_by_variant.setdefault(str(variant), []).append(str(row.get("id")))

    not_applicable = {
        entry["variant"]: entry["reason"] for entry in family["not_applicable_variants"]
    }
    intentionally_unsupported = {
        entry["variant"]: entry["reason"] for entry in family["intentionally_unsupported_variants"]
    }
    decision_variants = {
        decision.get("variant")
        for decision in family["product_decisions"]
        if decision.get("variant") and decision.get("status", "open") == "open"
    }

    checklist: list[dict[str, Any]] = []
    for variant in family["required_variants"]:
        case_ids = rows_by_variant.get(variant) or []
        reason = ""
        if case_ids:
            state = "covered"
        elif variant in decision_variants:
            state = "needs_product_decision"
        elif variant in intentionally_unsupported:
            state = "intentionally_unsupported"
            reason = intentionally_unsupported[variant]
        elif variant in not_applicable:
            state = "not_applicable"
            reason = not_applicable[variant]
        else:
            state = "missing"
        checklist.append(
            {
                "family": family["id"],
                "variant": variant,
                "state": state,
                "case_ids": case_ids,
                "reason": reason,
            }
        )
    return checklist


def product_decision_rows(
    families: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for family in families:
        for decision in family["product_decisions"]:
            if decision.get("status", "open") == "open":
                decisions.append({"family": family["id"], **decision})
    for row in rows:
        acceptance = row.get("acceptance") or {}
        manual_review = row.get("manual_review") or {}
        if (
            acceptance.get("review_role") != "decision"
            and manual_review.get("status") != "needs_product_decision"
        ):
            continue
        decisions.append(
            {
                "family": acceptance.get("family"),
                "case_id": row.get("id"),
                "question": manual_review.get("notes")
                or row.get("expected", {}).get("review_notes")
                or "Product decision required for tagged case.",
            }
        )
    return decisions


def compact_product_review_row(row: dict[str, Any]) -> dict[str, Any]:
    acceptance = row.get("acceptance") or {}
    return {
        "id": row.get("id"),
        "query": row.get("query"),
        "family": acceptance.get("family"),
        "concept": acceptance.get("concept"),
        "variant": acceptance.get("variant"),
        "review_role": acceptance.get("review_role"),
        "sibling_of": acceptance.get("sibling_of"),
        "expected_route": (row.get("expected") or {}).get("expected_route"),
        "expected_status": (row.get("expected") or {}).get("expected_status"),
        "expected_shape": (row.get("expected") or {}).get("expected_shape"),
        "route": row.get("route"),
        "result_status": row.get("result_status"),
        "shape_hint": row.get("shape_hint"),
        "answer_text": row.get("answer_text"),
        "answer_summary": row.get("answer_summary"),
        "applied_filters": row.get("applied_filters") or [],
        "section_summaries": row.get("section_summaries") or {},
        "expectation_status": (row.get("expectation_results") or {}).get("status"),
        "manual_review": row.get("manual_review") or {},
        "suspicious_flags": row.get("suspicious_flags") or [],
    }


def build_product_review(
    rows: list[dict[str, Any]],
    *,
    family_registry: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    families = family_registry["families"]
    review_closure = family_registry.get("review_closure") or {"state": "human_review_pending"}
    closure_state = review_closure.get("state", "human_review_pending")
    closure_case_count = review_closure.get("case_count")
    closure_matches_scope = (
        closure_state != "human_review_pending"
        and not summary["failed_case_ids"]
        and (closure_case_count is None or closure_case_count == summary["case_count"])
    )
    rows_by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family = (row.get("acceptance") or {}).get("family")
        if family:
            rows_by_family.setdefault(str(family), []).append(row)

    decisions = product_decision_rows(families, rows)
    decisions_by_family = Counter(str(row.get("family")) for row in decisions)
    checklist: list[dict[str, Any]] = []
    family_summary: list[dict[str, Any]] = []
    for family in families:
        family_rows = rows_by_family.get(family["id"], [])
        family_checklist = variant_resolution_map(family, family_rows)
        checklist.extend(family_checklist)
        machine_pass_count = sum(
            (row.get("expectation_results") or {}).get("status") == "pass" for row in family_rows
        )
        machine_fail_count = len(family_rows) - machine_pass_count
        missing_variants = [row["variant"] for row in family_checklist if row["state"] == "missing"]
        decision_variants = [
            row["variant"] for row in family_checklist if row["state"] == "needs_product_decision"
        ]
        if decisions_by_family[family["id"]] or decision_variants:
            coverage_review = "needs_product_decision"
        elif missing_variants:
            coverage_review = "missing_variants"
        else:
            coverage_review = "complete"
        row_human_review = human_review_status(family_rows)
        closure_can_mark_reviewed = bool(
            closure_matches_scope
            and family_rows
            and not machine_fail_count
            and coverage_review == "complete"
            and not any(row.get("suspicious_flags") for row in family_rows)
        )
        if closure_can_mark_reviewed:
            family_human_review = (
                "reviewed_followup"
                if closure_state == "human_review_complete_with_followup"
                else "reviewed_pass"
            )
            human_review_source = "registry_closure"
        else:
            family_human_review = row_human_review
            human_review_source = "case_manual_review"
        representative_count = sum(
            bool((row.get("acceptance") or {}).get("review_required")) for row in family_rows
        )
        public_accepted = bool(
            family["public_surface"]
            and family_rows
            and not machine_fail_count
            and coverage_review == "complete"
            and representative_count
            and family_human_review == "reviewed_pass"
            and not any(row.get("suspicious_flags") for row in family_rows)
        )
        family_summary.append(
            {
                "id": family["id"],
                "label": family["label"],
                "public_surface": family["public_surface"],
                "case_count": len(family_rows),
                "machine_pass_count": machine_pass_count,
                "machine_fail_count": machine_fail_count,
                "machine_status": "fail"
                if machine_fail_count
                else ("pass" if family_rows else "not_run"),
                "required_variants": family["required_variants"],
                "covered_variants": sorted(
                    {
                        str((row.get("acceptance") or {}).get("variant"))
                        for row in family_rows
                        if (row.get("acceptance") or {}).get("variant")
                    }
                ),
                "missing_variants": missing_variants,
                "coverage_review": coverage_review,
                "human_review": family_human_review,
                "human_review_source": human_review_source,
                "representative_count": representative_count,
                "public_accepted": public_accepted,
                "coverage_questions": family["coverage_questions"],
            }
        )

    representative_rows = [
        compact_product_review_row(row)
        for row in rows
        if (row.get("acceptance") or {}).get("review_required")
    ]
    unsupported_rows = [
        compact_product_review_row(row)
        for row in rows
        if (row.get("acceptance") or {}).get("no_broad_fallback")
        or row.get("result_status") in {"no_result", "error"}
    ]
    suspicious_rows = [
        compact_product_review_row(row) for row in rows if row.get("suspicious_flags")
    ]

    family_coverage_statuses = {family["coverage_review"] for family in family_summary}
    if "needs_product_decision" in family_coverage_statuses:
        coverage_declaration = "needs_product_decision"
    elif "missing_variants" in family_coverage_statuses:
        coverage_declaration = "missing_variants"
    else:
        coverage_declaration = "complete"

    family_human_statuses = {family["human_review"] for family in family_summary}
    if "pending" in family_human_statuses:
        review_declaration = "human_review_pending"
    elif "reviewed_followup" in family_human_statuses:
        review_declaration = "human_review_complete_with_followup"
    else:
        review_declaration = "human_review_complete"

    return {
        "run_id": summary["run_id"],
        "corpus_path": summary["corpus_path"],
        "case_count": summary["case_count"],
        "machine_regression": "fail" if summary["failed_case_ids"] else "pass",
        "coverage_declaration": coverage_declaration,
        "review_declaration": review_declaration,
        "review_closure": review_closure,
        "family_registry_surface": family_registry["surface"],
        "family_summary": family_summary,
        "variant_checklist": checklist,
        "representative_rows": representative_rows,
        "unsupported_no_broad_fallback_rows": unsupported_rows,
        "product_decisions": decisions,
        "suspicious_rows": suspicious_rows,
    }


def format_case_ids(case_ids: list[str]) -> str:
    if not case_ids:
        return ""
    return ", ".join(md_code(case_id) for case_id in case_ids)


def write_product_review_markdown(path: Path, product_review: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Raw Query Answer QA Product Review",
        "",
        "## Run Metadata And Review Status",
        "",
        f"- Run ID: {md_code(product_review['run_id'])}",
        f"- Corpus: {md_code(product_review['corpus_path'])}",
        f"- Cases run: {md_code(product_review['case_count'])}",
        f"- Family registry surface: {md_code(product_review['family_registry_surface'])}",
        f"- Machine regression: {md_code(product_review['machine_regression'])}",
        f"- Coverage review: {md_code(product_review['coverage_declaration'])}",
        f"- Human review declaration: {md_code(product_review['review_declaration'])}",
    ]
    review_closure = product_review.get("review_closure") or {}
    if review_closure.get("state") != "human_review_pending":
        lines.extend(
            [
                "- Human review closure source: "
                f"{md_code('qa/raw_query_answer_acceptance_families.yaml')}",
                f"- Reviewed scope: {md_code(review_closure.get('scope'))}",
                f"- Reviewed run ID: {md_code(review_closure.get('reviewed_run_id'))}",
                f"- Review completed on: {md_code(review_closure.get('completed_on'))}",
            ]
        )
        ui_spot_check = review_closure.get("ui_spot_check") or {}
        if ui_spot_check:
            lines.append(f"- UI spot check: {md_code(ui_spot_check.get('status'))}")
        if review_closure.get("notes"):
            lines.append(f"- Review closure notes: {md_escape(review_closure['notes'])}")
    lines.extend(
        [
            "",
            "Machine regression passing does not mean coverage review, human review, or "
            "public acceptance is complete.",
            "",
            "## Feature-Family Summary",
            "",
            "| Family | Public | Cases | Machine pass/fail | "
            "Required variants | Covered variants | Missing variants | "
            "Coverage review | Human review | Public accepted |",
            "|---|---|---:|---|---|---|---|---|---|---|",
        ]
    )
    for family in product_review["family_summary"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(family["label"]),
                    "yes" if family["public_surface"] else "no",
                    md_escape(family["case_count"]),
                    md_escape(
                        f"{family['machine_pass_count']} pass / {family['machine_fail_count']} fail"
                    ),
                    md_escape(", ".join(family["required_variants"])),
                    md_escape(", ".join(family["covered_variants"])),
                    md_escape(", ".join(family["missing_variants"]) or "none"),
                    md_escape(family["coverage_review"]),
                    md_escape(family["human_review"]),
                    "yes" if family["public_accepted"] else "no",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Missing / Unchecked Variant Checklist",
            "",
            "| Family | Variant | State | Cases | Reason |",
            "|---|---|---|---|---|",
        ]
    )
    for row in product_review["variant_checklist"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["family"]),
                    md_escape(row["variant"]),
                    md_escape(row["state"]),
                    format_case_ids(row["case_ids"]),
                    md_escape(row["reason"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Representative Outputs Requiring Human Review", ""])
    if not product_review["representative_rows"]:
        lines.append("_None tagged yet._")
    for row in product_review["representative_rows"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Query: {md_code(row['query'])}",
                (
                    f"- Family / concept / variant: {md_code(row['family'])} / "
                    f"{md_code(row['concept'])} / {md_code(row['variant'])}"
                ),
                f"- Review role: {md_code(row['review_role'])}",
                f"- Sibling of: {md_code(row['sibling_of'])}",
                (
                    f"- Expected route / status / shape: {md_code(row['expected_route'])} / "
                    f"{md_code(row['expected_status'])} / {md_code(row['expected_shape'])}"
                ),
                (
                    f"- Actual route / status / shape: {md_code(row['route'])} / "
                    f"{md_code(row['result_status'])} / {md_code(row['shape_hint'])}"
                ),
                f"- Machine expectation status: {md_code(row['expectation_status'])}",
                (
                    f"- Backend answer text: {md_escape(row['answer_text'])}"
                    if row["answer_text"]
                    else "- Backend answer text: _not backend-provided_"
                ),
                (
                    f"- Answer summary: {md_escape(row['answer_summary'])}"
                    if row["answer_summary"]
                    else "- Answer summary: _not available_"
                ),
                f"- Filters: {format_filters(row['applied_filters'])}",
                f"- Sections: {format_sections(row['section_summaries'])}",
                f"- Manual review status: {md_code(row['manual_review'].get('status'))}",
                "- Reviewer checkbox: [ ] output scope and answer look correct",
                "- Reviewer notes:",
            ]
        )
        for section_name, section_summary in row["section_summaries"].items():
            top_rows = section_summary.get("top_rows") or []
            if top_rows:
                lines.extend(
                    [
                        "",
                        f"Section {md_code(section_name)} top rows:",
                        "",
                        markdown_table(top_rows),
                    ]
                )
        lines.append("")

    lines.extend(
        [
            "## Unsupported / No-Broad-Fallback Rows",
            "",
            "| Case | Family | Variant | Expected status | Actual route/status/shape | "
            "Machine expectation |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in product_review["unsupported_no_broad_fallback_rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["id"]),
                    md_escape(row["family"]),
                    md_escape(row["variant"]),
                    md_escape(row["expected_status"]),
                    md_escape(f"{row['route']} / {row['result_status']} / {row['shape_hint']}"),
                    md_escape(row["expectation_status"]),
                ]
            )
            + " |"
        )
    if not product_review["unsupported_no_broad_fallback_rows"]:
        lines.append("| _none_ |  |  |  |  |  |")

    lines.extend(["", "## Product Decisions Needed", ""])
    if product_review["product_decisions"]:
        lines.extend(
            [
                "| Family | Case | Variant | Question | Current behavior | Owner | Next action |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for row in product_review["product_decisions"]:
            lines.append(
                "| "
                + " | ".join(
                    md_escape(row.get(key))
                    for key in (
                        "family",
                        "case_id",
                        "variant",
                        "question",
                        "current_behavior",
                        "decision_owner",
                        "next_action",
                    )
                )
                + " |"
            )
    else:
        lines.append("_None._")

    lines.extend(["", "## Suspicious Rows", ""])
    if product_review["suspicious_rows"]:
        lines.extend(["| Case | Family | Flags |", "|---|---|---|"])
        for row in product_review["suspicious_rows"]:
            flag_ids = ", ".join(str(flag.get("id")) for flag in row["suspicious_flags"])
            lines.append(
                f"| {md_escape(row['id'])} | {md_escape(row['family'])} | {md_escape(flag_ids)} |"
            )
    else:
        lines.append("_None._")

    lines.extend(["", "## Human Review Worksheet", ""])
    for family in product_review["family_summary"]:
        lines.extend(
            [
                f"### {family['label']}",
                "",
                f"- Coverage questions: {md_code(family['coverage_questions'])}",
                "- [ ] Examples represent real public usage.",
                "- [ ] Representative outputs have correct scope and answer shape.",
                "- [ ] Missing variants are resolved or recorded as follow-up.",
                "- Reviewer notes:",
                "",
            ]
        )

    lines.extend(
        [
            "## What To Send ChatGPT",
            "",
            "Send ChatGPT this file:",
            "",
            f"`{display_path(path)}`",
            "",
            "Use this exact instruction block:",
            "",
            "```text",
            "Review this NBA Tools Raw QA product-review artifact as a product coverage",
            "audit. Do not treat machine pass counts as sufficient. For each feature",
            "family:",
            "1. Decide whether the examples represent real public usage.",
            "2. Flag missing canonical, short, sentence, synonym, sibling/inverse,",
            "   nearby-unsupported, or typo/partial variants.",
            "3. Review the representative answer outputs for wrong scope, misleading",
            "   answers, and broad fallback.",
            "4. Separate behavior bugs from corpus gaps and product decisions.",
            "5. Return a family-by-family table with verdict, missing cases, suspicious",
            "   outputs, and recommended next action.",
            "```",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n")


def append_slowest_cases_section(lines: list[str], summary: dict[str, Any]) -> None:
    lines.extend(["", "## Slowest Cases", ""])
    slowest_cases = summary.get("slowest_cases") or []
    if not slowest_cases:
        lines.append("_None._")
        return
    lines.extend(
        [
            "| Case | Seconds | Status | Route |",
            "|---|---:|---|---|",
        ]
    )
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


def append_comparison_section(lines: list[str], summary: dict[str, Any]) -> None:
    comparison = summary.get("comparison")
    if not isinstance(comparison, dict):
        return

    lines.extend(
        [
            "",
            "## Comparison",
            "",
            f"- Source: {md_code(comparison.get('source_path'))}",
            f"- Source type: {md_code(comparison.get('source_type'))}",
            f"- Detail level: {md_code(comparison.get('detail_level'))}",
            f"- Previous cases: {md_code(comparison.get('previous_case_count'))}",
            f"- Current cases: {md_code(comparison.get('current_case_count'))}",
            f"- Case count delta: {md_code(comparison.get('case_count_delta'))}",
            f"- Failed case delta: {md_code(comparison.get('failed_case_delta'))}",
            f"- Newly failing cases: {md_code(comparison.get('newly_failing_case_ids'))}",
            f"- Newly passing cases: {md_code(comparison.get('newly_passing_case_ids'))}",
            (
                "- Previous failed cases not rerun: "
                f"{md_code(comparison.get('previous_failed_not_rerun_case_ids'))}"
            ),
            f"- Result status count delta: {md_code(comparison.get('result_status_count_delta'))}",
            (
                "- Suspicious flag count delta: "
                f"{md_code(comparison.get('suspicious_flag_count_delta'))}"
            ),
            (
                "- Suspicious flag counts delta: "
                f"{md_code(comparison.get('suspicious_flag_counts_delta'))}"
            ),
            (
                "- Verified outlier count delta: "
                f"{md_code(comparison.get('verified_outlier_count_delta'))}"
            ),
            (
                "- Verified outlier counts delta: "
                f"{md_code(comparison.get('verified_outlier_counts_delta'))}"
            ),
        ]
    )
    notes = comparison.get("notes") or []
    if notes:
        lines.extend(["", "Notes:"])
        for note in notes:
            lines.append(f"- {md_escape(note)}")

    drift = comparison.get("route_status_drift") or []
    lines.extend(["", "Route/status drift:"])
    if drift:
        lines.extend(
            [
                "",
                "| Case | Previous route | Current route | Previous status | Current status |",
                "|---|---|---|---|---|",
            ]
        )
        for row in drift:
            lines.append(
                "| "
                + " | ".join(
                    md_escape(row.get(key))
                    for key in (
                        "id",
                        "previous_route",
                        "current_route",
                        "previous_result_status",
                        "current_result_status",
                    )
                )
                + " |"
            )
    else:
        lines.append("_None._")


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
        f"- Answer text policies: {md_code(summary['answer_text_policy_counts'])}",
        f"- Answer text statuses: {md_code(summary['answer_text_status_counts'])}",
        f"- Suspicious flag cases: {md_code(summary['suspicious_flag_case_count'])}",
        f"- Suspicious flags: {md_code(summary['suspicious_flag_counts'])}",
        f"- Informational flag cases: {md_code(summary['informational_flag_case_count'])}",
        f"- Informational flags: {md_code(summary['informational_flag_counts'])}",
        f"- Verified outlier cases: {md_code(summary['verified_outlier_case_count'])}",
        f"- Verified outliers: {md_code(summary['verified_outlier_counts'])}",
        f"- Suggested review tags: {md_code(summary['suggested_review_tag_counts'])}",
        f"- Expectation cases: {md_code(summary['expectation_case_counts'])}",
        f"- Expectation checks: {md_code(summary['expectation_check_counts'])}",
        f"- Failed case IDs: {md_code(summary['failed_case_ids'])}",
    ]

    append_slowest_cases_section(lines, summary)
    append_comparison_section(lines, summary)
    lines.extend(["", "## Suspicious / Review Flags", ""])

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

    lines.extend(["", "## Informational Flags", ""])
    informational_rows = [row for row in rows if row.get("informational_flags")]
    if informational_rows:
        lines.extend(
            [
                "| Case | Flags | Answer text policy | Answer text status |",
                "|---|---|---|---|",
            ]
        )
        for row in informational_rows:
            flag_ids = ", ".join(
                str(flag.get("id")) for flag in row.get("informational_flags") or []
            )
            status = str(row.get("answer_text_status") or "")
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.get("id")),
                        md_escape(flag_ids),
                        md_escape(row.get("answer_text_policy")),
                        md_escape(answer_text_status_label(status)),
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
                f"- Answer text policy: {md_code(row.get('answer_text_policy'))}",
                (
                    "- Answer text status: "
                    f"{md_escape(answer_text_status_label(row.get('answer_text_status')))}"
                ),
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
        if row.get("informational_flags"):
            flag_ids = ", ".join(str(flag.get("id")) for flag in row["informational_flags"])
            lines.append(f"- Informational flags: {md_code(flag_ids)}")
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
    if args.overwrite_run_id and args.run_id is None:
        raise ValueError("--overwrite-run-id requires --run-id")
    run_id = (
        validate_run_id_label(args.run_id)
        if args.run_id
        else datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    run_dir = out_base / run_id
    validate_run_directory_target(run_dir, overwrite_run_id=args.overwrite_run_id)
    report_jsonl_path = run_dir / "report.jsonl"
    report_md_path = run_dir / "report.md"
    summary_path = run_dir / "summary.json"
    product_review_md_path = run_dir / "product_review.md"
    product_review_json_path = run_dir / "product_review.json"

    family_registry = load_acceptance_family_registry(resolve_path(args.acceptance_families))
    version, cases = load_corpus(corpus_path)
    del version
    validate_corpus_acceptance(cases, family_registry)
    verified_outliers = load_verified_outliers(resolve_path(args.verified_outliers))
    selected_ids, explicit_selection = collect_selected_case_ids(
        case_values=args.case,
        slice_values=args.slice,
        failed_from_values=args.failed_from,
    )
    selected = filter_cases(
        cases,
        case_ids=selected_ids,
        limit=args.limit,
        explicit_selection=explicit_selection,
    )

    started_at = datetime.now(UTC).isoformat()
    rows = [
        run_case_with_timing(case, top_rows=args.top_rows, verified_outliers=verified_outliers)
        for case in selected
    ]
    completed_at = datetime.now(UTC).isoformat()

    prepare_run_directory(run_dir, overwrite_run_id=args.overwrite_run_id)
    output_paths = {
        "report_jsonl": report_jsonl_path,
        "report_md": report_md_path,
        "summary_json": summary_path,
        "product_review_md": product_review_md_path,
        "product_review_json": product_review_json_path,
    }
    summary = summarize_rows(
        rows,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        corpus_path=corpus_path,
        output_paths=output_paths,
    )
    if args.compare_to:
        summary["comparison"] = build_run_comparison(rows, resolve_path(args.compare_to))
    product_review = build_product_review(
        rows,
        family_registry=family_registry,
        summary=summary,
    )

    write_jsonl(report_jsonl_path, rows)
    dump_json(summary_path, summary)
    write_markdown(report_md_path, rows, summary)
    dump_json(product_review_json_path, product_review)
    write_product_review_markdown(product_review_md_path, product_review)

    failed_case_ids = summary["failed_case_ids"]
    print(f"Wrote raw query answer QA report: {run_dir.relative_to(ROOT)}")
    print(f"Cases: {summary['case_count']}")
    print(f"Result statuses: {summary['result_status_counts']}")
    print(f"Expectation cases: {summary['expectation_case_counts']}")
    print(f"Suspicious flag cases: {summary['suspicious_flag_case_count']}")
    print(f"Informational flag cases: {summary['informational_flag_case_count']}")
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
