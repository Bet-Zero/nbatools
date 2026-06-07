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
DEFAULT_INPUT_PATH = Path("qa/exploratory_query_samples.yaml")
DEFAULT_MANIFEST_PATH = Path("qa/exploratory/manifest.yaml")
DEFAULT_SLICES_ROOT = Path("qa/exploratory/slices")
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

DISPLAY_SHAPES: dict[str, dict[str, str]] = {
    "no_result_guided": {
        "name": "Guided No Result",
        "description": "Message card with suggested next-step chips.",
    },
    "no_result_message": {
        "name": "Message No Result",
        "description": "Message card without the recovery suggestion grid.",
    },
    "entity_summary": {
        "name": "Entity Summary",
        "description": "Single hero answer card for a player summary.",
    },
    "entity_summary_with_gamelog": {
        "name": "Entity Summary + Recent Games",
        "description": "Player summary hero followed by a recent-games table.",
    },
    "game_log_player_table": {
        "name": "Player Game Log",
        "description": "Summary strip plus player-first game table.",
    },
    "game_log_team_table": {
        "name": "Team Game Log",
        "description": "Summary strip plus team-first game table.",
    },
    "game_log_team_detail": {
        "name": "Game Summary Log",
        "description": "Team game table with extra raw-detail drawers.",
    },
    "split_table": {
        "name": "Split Comparison",
        "description": "Hero, split bucket table, edge chips, and detail drawers.",
    },
    "on_off_split": {
        "name": "On/Off Split",
        "description": "Two-bucket on/off table with edge chips and one raw drawer.",
    },
    "streak_table": {
        "name": "Streak Table",
        "description": "Hero, ranked streak table, and highlighted raw detail.",
    },
    "playoff_history": {
        "name": "Playoff History",
        "description": "Team playoff hero with season-by-season table.",
    },
    "playoff_round_record": {
        "name": "Playoff Round Records",
        "description": "Round leaderboard with a highlighted playoff metric.",
    },
    "playoff_matchup_history": {
        "name": "Playoff Matchup History",
        "description": "Two-team playoff matchup hero with series table.",
    },
    "comparison": {
        "name": "Comparison Panels",
        "description": "Head-to-head hero, subject panels, and metric comparison table.",
    },
    "team_record": {
        "name": "Team Record",
        "description": "Team record hero with a single-summary record table.",
    },
    "record_by_decade": {
        "name": "Record By Decade",
        "description": "Team hero plus decade breakdown table.",
    },
    "record_by_decade_leaderboard": {
        "name": "Record By Decade Leaderboard",
        "description": "Ranked decade leaderboard for team records.",
    },
    "matchup_by_decade": {
        "name": "Matchup By Decade",
        "description": "Two-team hero with decade-by-decade matchup table.",
    },
    "leaderboard_table": {
        "name": "Leaderboard Table",
        "description": "Hero sentence over a ranked leaderboard table.",
    },
    "top_performances": {
        "name": "Top Performances",
        "description": "League-wide ranked single-game performance table.",
    },
    "rolling_stretch": {
        "name": "Rolling Stretch",
        "description": "Rolling-window leaderboard or named-player stretch table.",
    },
    "fallback_table": {
        "name": "Fallback Tables",
        "description": "One plain data card per populated section.",
    },
    "unclassified": {
        "name": "Unclassified",
        "description": "Loaded result whose pattern stack does not match the catalog.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run input-only natural-language NBA query samples and write exploratory "
            "human-review artifacts."
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="YAML or JSON sample file for a full exploratory run.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run the full exploratory sample file. This is also the default without --slice.",
    )
    parser.add_argument(
        "--slice",
        dest="slice_id",
        default=None,
        help="Run one exploratory slice by ID, such as 001_player_last_n.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Optional exploratory slice manifest YAML/JSON.",
    )
    parser.add_argument(
        "--slices-root",
        default=str(DEFAULT_SLICES_ROOT),
        help="Directory used to resolve --slice when no manifest entry is present.",
    )
    parser.add_argument("--out", default="outputs/exploratory_query_review")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--overwrite-run-id", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--top-rows", type=int, default=3)
    args = parser.parse_args()
    if args.all and args.slice_id:
        parser.error("--all and --slice are mutually exclusive")
    return args


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


def normalize_samples(raw_entries: list[Any]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_sample in enumerate(raw_entries, start=1):
        sample = normalize_sample(raw_sample, index=index)
        sample_id = str(sample["id"])
        if sample_id in seen_ids:
            raise ValueError(f"Duplicate sample id: {sample_id}")
        seen_ids.add(sample_id)
        samples.append(sample)
    return samples


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
        "input_notes": metadata.get("notes"),
        "metadata": metadata,
    }


def load_samples(path: Path) -> tuple[int | None, list[dict[str, Any]]]:
    data = read_yaml_or_json(path)
    raw_entries = raw_sample_entries(data, path=path)
    samples = normalize_samples(raw_entries)

    version = data.get("version") if isinstance(data, dict) else None
    if isinstance(version, int | str) and str(version).isdigit():
        return int(version), samples
    return None, samples


def manifest_slice_path(
    *,
    slice_id: str,
    manifest_path: Path,
) -> Path | None:
    if not manifest_path.exists():
        return None
    data = read_yaml_or_json(manifest_path)
    if not isinstance(data, dict):
        raise ValueError(f"Exploratory manifest must be a mapping: {display_path(manifest_path)}")
    slices = data.get("slices")
    if not isinstance(slices, list):
        raise ValueError(
            f"Exploratory manifest must contain a slices list: {display_path(manifest_path)}"
        )

    for index, entry in enumerate(slices, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Manifest slice entry {index} must be a mapping")
        entry_id = require_nonempty_string(entry.get("id"), label=f"Manifest slice {index} id")
        if entry_id != slice_id:
            continue
        file_text = require_nonempty_string(
            entry.get("file"),
            label=f"Manifest slice {entry_id} file",
        )
        path = Path(file_text)
        return path if path.is_absolute() else manifest_path.parent / path
    return None


def resolve_slice_path(
    *,
    slice_id: str,
    manifest_path: Path,
    slices_root: Path,
) -> Path:
    safe_slice_id = validate_run_id_label(slice_id)
    from_manifest = manifest_slice_path(slice_id=safe_slice_id, manifest_path=manifest_path)
    if from_manifest is not None:
        return from_manifest
    return slices_root / f"{safe_slice_id}.yaml"


def load_slice(
    path: Path,
    *,
    requested_slice_id: str | None = None,
) -> tuple[int | None, list[dict[str, Any]], dict[str, Any]]:
    data = read_yaml_or_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Exploratory slice must be a mapping: {display_path(path)}")

    slice_id = require_nonempty_string(data.get("id"), label="Slice id")
    if requested_slice_id is not None and slice_id != requested_slice_id:
        raise ValueError(
            f"Slice id mismatch: requested {requested_slice_id}, "
            f"but {display_path(path)} declares {slice_id}"
        )
    description = require_nonempty_string(
        data.get("description"),
        label=f"Slice {slice_id} description",
    )
    review_goal_value = data.get("review_goal")
    review_goal = (
        require_nonempty_string(review_goal_value, label=f"Slice {slice_id} review_goal")
        if review_goal_value is not None
        else None
    )
    samples = normalize_samples(raw_sample_entries(data, path=path))
    version = data.get("version")
    numeric_version = (
        int(version) if isinstance(version, int | str) and str(version).isdigit() else None
    )
    slice_metadata = {
        "slice_id": slice_id,
        "slice_description": description,
        "slice_review_goal": review_goal,
        "input_slice_path": display_path(path),
        "slice_sample_count": len(samples),
    }
    return numeric_version, samples, slice_metadata


def load_review_source(
    args: argparse.Namespace,
) -> tuple[Path, list[dict[str, Any]], dict[str, Any] | None]:
    if args.slice_id:
        manifest_path = resolve_path(args.manifest)
        slices_root = resolve_path(args.slices_root)
        slice_id = validate_run_id_label(args.slice_id)
        input_path = resolve_slice_path(
            slice_id=slice_id,
            manifest_path=manifest_path,
            slices_root=slices_root,
        )
        _version, samples, slice_metadata = load_slice(input_path, requested_slice_id=slice_id)
        return input_path, samples, slice_metadata

    input_path = resolve_path(args.input)
    _version, samples = load_samples(input_path)
    return input_path, samples, None


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


def section_rows(sections: dict[str, Any], key: str) -> list[Any]:
    rows = sections.get(key)
    return rows if isinstance(rows, list) else []


def has_displayable_rows(sections: dict[str, Any]) -> bool:
    return any(isinstance(rows, list) and len(rows) > 0 for rows in sections.values())


def filter_text(value: Any, key: str) -> str:
    if not isinstance(value, dict):
        return ""
    raw = value.get(key)
    return str(raw or "").casefold()


def should_show_player_summary_game_log(
    *,
    query: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> bool:
    if not section_rows(sections, "game_log"):
        return False

    window_size = metadata.get("window_size")
    if isinstance(window_size, int | float) and not isinstance(window_size, bool):
        return True
    if re.search(r"\blast\s+\d+\s*(?:games?|gms?)?\b", query, flags=re.I):
        return True
    if metadata.get("opponent_context"):
        return True

    filters = metadata.get("applied_filters")
    if not isinstance(filters, list):
        return False
    meaningful_kinds = {
        "date",
        "location",
        "outcome",
        "period",
        "player",
        "position",
        "quality",
        "role",
        "schedule",
        "season",
        "situation",
        "threshold",
        "window",
    }
    for item in filters:
        kind = filter_text(item, "kind")
        label = filter_text(item, "label")
        if kind == "team" and "opponent" in label:
            return True
        if kind in meaningful_kinds:
            return True
    return False


def route_to_display_patterns(
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> list[dict[str, Any]]:
    route_key = route or metadata.get("route")
    if route_key == "player_game_summary":
        if should_show_player_summary_game_log(query=query, metadata=metadata, sections=sections):
            return [
                {"type": "entity_summary", "section_key": "summary"},
                {
                    "type": "game_log",
                    "section_key": "game_log",
                    "summary_key": "summary",
                    "show_summary_strip": False,
                },
            ]
        return [{"type": "entity_summary", "section_key": "summary"}]
    if route_key == "player_game_finder":
        return [
            {
                "type": "game_log",
                "section_key": "finder",
                "mode": "player",
                "raw_detail_title": "Player Game Detail",
            }
        ]
    if route_key == "game_finder":
        return [
            {
                "type": "game_log",
                "section_key": "finder",
                "mode": "team",
                "raw_detail_title": "Game Detail",
            }
        ]
    if route_key == "top_player_games":
        return [{"type": "top_performances", "section_key": "leaderboard", "subject": "player"}]
    if route_key == "top_team_games":
        return [{"type": "top_performances", "section_key": "leaderboard", "subject": "team"}]
    if route_key == "game_summary":
        return [
            {
                "type": "game_log",
                "section_key": "game_log",
                "summary_key": "summary",
                "mode": "team",
                "raw_detail_title": "Game Detail",
                "detail_section_keys": ["top_performers"],
            }
        ]
    if route_key == "player_split_summary":
        return [{"type": "split", "subject": "player"}]
    if route_key == "team_split_summary":
        return [{"type": "split", "subject": "team"}]
    if route_key == "player_on_off":
        return [
            {
                "type": "split",
                "section_key": "summary",
                "summary_key": "summary",
                "subject": "player",
                "bucket_key": "presence_state",
                "split_label_override": "On/Off",
                "primary_detail_title": "On/Off Detail",
                "summary_detail_title": None,
            }
        ]
    if route_key in {"player_streak_finder", "team_streak_finder"}:
        return [{"type": "streak", "section_key": "streak"}]
    if route_key == "playoff_history":
        return [{"type": "playoff_history", "mode": "history"}]
    if route_key == "playoff_round_record":
        return [{"type": "playoff_history", "mode": "round_record"}]
    if route_key == "playoff_matchup_history":
        return [{"type": "playoff_history", "mode": "matchup"}]
    if route_key == "player_compare":
        return [
            {
                "type": "comparison",
                "subject": "player",
                "head_to_head": metadata.get("head_to_head_used") is True,
            }
        ]
    if route_key == "team_compare":
        return [
            {
                "type": "comparison",
                "subject": "team",
                "head_to_head": metadata.get("head_to_head_used") is True,
            }
        ]
    if route_key == "team_matchup_record":
        return [{"type": "comparison", "subject": "team", "head_to_head": True}]
    if route_key == "team_record":
        if section_rows(sections, "game_log"):
            return [
                {"type": "record", "mode": "team_record"},
                {
                    "type": "game_log",
                    "section_key": "game_log",
                    "summary_key": "summary",
                    "mode": "team",
                    "show_summary_strip": False,
                    "raw_detail_title": "Game Detail",
                    "collapse_to_detail": True,
                },
            ]
        return [{"type": "record", "mode": "team_record"}]
    if route_key == "record_by_decade":
        return [{"type": "record", "mode": "record_by_decade"}]
    if route_key == "record_by_decade_leaderboard":
        return [{"type": "record", "mode": "record_by_decade_leaderboard"}]
    if route_key == "matchup_by_decade":
        return [{"type": "record", "mode": "matchup_by_decade"}]
    if route_key in {
        "season_leaders",
        "season_team_leaders",
        "team_record_leaderboard",
        "player_occurrence_leaders",
        "team_occurrence_leaders",
    }:
        return [{"type": "leaderboard", "section_key": "leaderboard"}]
    if route_key == "player_stretch_leaderboard":
        return [{"type": "rolling_stretch", "section_key": "leaderboard"}]
    if route_key == "lineup_summary":
        return [{"type": "entity_summary", "section_key": "summary"}]
    if route_key == "lineup_leaderboard":
        return [{"type": "leaderboard", "section_key": "leaderboard", "metric_key": "net_rating"}]
    if route_key == "playoff_appearances":
        if section_rows(sections, "leaderboard"):
            return [
                {
                    "type": "leaderboard",
                    "section_key": "leaderboard",
                    "metric_key": "appearances",
                    "sentence_metric_label": "playoff appearances",
                }
            ]
        if section_rows(sections, "summary") or section_rows(sections, "by_season"):
            return [{"type": "playoff_history", "mode": "appearances"}]
        return [
            {
                "type": "leaderboard",
                "section_key": "leaderboard",
                "metric_key": "appearances",
                "sentence_metric_label": "playoff appearances",
            }
        ]
    return [{"type": "fallback_table"}]


def no_result_display_shape(result_status: str | None, result_reason: str | None) -> str:
    if result_status == "error" or result_reason == "error":
        return "no_result_message"
    if result_reason in {None, "no_match", "no_data"}:
        return "no_result_guided"
    return "no_result_message"


def classify_display_shape(
    *,
    query: str,
    result_status: str | None,
    result_reason: str | None,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    if not has_displayable_rows(sections):
        key = no_result_display_shape(result_status, result_reason)
        return {"key": key, **DISPLAY_SHAPES[key]}, []

    patterns = route_to_display_patterns(
        query=query,
        route=route,
        metadata=metadata,
        sections=sections,
    )
    pattern_types = [pattern.get("type") for pattern in patterns]
    if pattern_types == ["entity_summary", "game_log"]:
        key = "entity_summary_with_gamelog"
    elif (
        len(patterns) == 2
        and patterns[0].get("type") == "record"
        and patterns[0].get("mode") == "team_record"
        and patterns[1].get("type") == "game_log"
    ):
        key = "team_record"
    elif len(patterns) != 1:
        key = "unclassified"
    else:
        pattern = patterns[0]
        pattern_type = pattern.get("type")
        if pattern_type == "entity_summary":
            key = "entity_summary"
        elif pattern_type == "game_log":
            if pattern.get("detail_section_keys"):
                key = "game_log_team_detail"
            else:
                key = (
                    "game_log_player_table"
                    if pattern.get("mode") == "player"
                    else "game_log_team_table"
                )
        elif pattern_type == "split":
            key = "on_off_split" if pattern.get("bucket_key") == "presence_state" else "split_table"
        elif pattern_type == "streak":
            key = "streak_table"
        elif pattern_type == "playoff_history":
            key = {
                "history": "playoff_history",
                "appearances": "playoff_history",
                "round_record": "playoff_round_record",
                "matchup": "playoff_matchup_history",
            }.get(str(pattern.get("mode")), "unclassified")
        elif pattern_type == "comparison":
            key = "comparison"
        elif pattern_type == "record":
            key = {
                "team_record": "team_record",
                "record_by_decade": "record_by_decade",
                "record_by_decade_leaderboard": "record_by_decade_leaderboard",
                "matchup_by_decade": "matchup_by_decade",
            }.get(str(pattern.get("mode")), "unclassified")
        elif pattern_type == "leaderboard":
            key = "leaderboard_table"
        elif pattern_type == "top_performances":
            key = "top_performances"
        elif pattern_type == "rolling_stretch":
            key = "rolling_stretch"
        elif pattern_type == "fallback_table":
            key = "fallback_table"
        else:
            key = "unclassified"

    return {"key": key, **DISPLAY_SHAPES[key]}, patterns


def section_preview_kind(section_name: str) -> str:
    if section_name in {"summary", "count"}:
        return "hero_or_summary"
    if section_name in {"finder", "game_log", "leaderboard", "streak", "comparison"}:
        return "table"
    if section_name in {"by_season", "split_comparison", "top_performers"}:
        return "detail_table"
    return "table"


def build_search_box_preview(
    *,
    query: str,
    route: str | None,
    result_status: str | None,
    result_reason: str | None,
    query_class: str | None,
    answer_text: str | None,
    answer_text_source: str | None,
    answer_summary: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    section_summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    display_shape, patterns = classify_display_shape(
        query=query,
        result_status=result_status,
        result_reason=result_reason,
        route=route,
        metadata=metadata,
        sections=sections,
    )
    visible_sections = [
        {
            "name": name,
            "row_count": summary.get("row_count", 0),
            "kind": section_preview_kind(name),
            "columns": summary.get("columns", []),
        }
        for name, summary in section_summaries.items()
    ]
    problem_flags: list[dict[str, str]] = []
    if result_status == "ok" and not visible_sections:
        problem_flags.append(
            {
                "id": "ok_without_visible_sections",
                "message": "The search box would return ok without displayable sections.",
            }
        )
    if display_shape["key"] == "fallback_table":
        problem_flags.append(
            {
                "id": "fallback_display_shape",
                "message": (
                    "The search box would use generic fallback tables, not a dedicated renderer."
                ),
            }
        )
    if display_shape["key"] == "unclassified":
        problem_flags.append(
            {
                "id": "unclassified_display_shape",
                "message": (
                    "The route produced a pattern stack that is not in the result-shape catalog."
                ),
            }
        )
    answer_line = answer_text or answer_summary
    return json_ready(
        {
            "display_shape": display_shape,
            "renderer_patterns": patterns,
            "answer_line": answer_line,
            "answer_line_source": answer_text_source
            or ("tool_summary" if answer_summary else None),
            "route": route,
            "result_status": result_status,
            "result_reason": result_reason,
            "query_class": query_class,
            "visible_sections": visible_sections,
            "problem_flags": problem_flags,
        }
    )


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
    preview = build_search_box_preview(
        query=str(sample.get("query") or ""),
        route=None,
        result_status="error",
        result_reason="exception",
        query_class=None,
        answer_text=None,
        answer_text_source=None,
        answer_summary="No answer rows returned; reason=exception",
        metadata={},
        sections={},
        section_summaries={},
    )
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
            "search_box_preview": preview,
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
    section_summaries = build_section_summaries(sections, top_rows=top_rows)
    preview = build_search_box_preview(
        query=query,
        route=payload.get("route"),
        result_status=payload.get("result_status"),
        result_reason=payload.get("result_reason"),
        query_class=query_class,
        answer_text=answer_text,
        answer_text_source=answer_text_source,
        answer_summary=answer_summary,
        metadata=metadata,
        sections=sections,
        section_summaries=section_summaries,
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
            "section_summaries": section_summaries,
            "notes": payload.get("notes") or result.get("notes") or [],
            "caveats": payload.get("caveats") or result.get("caveats") or [],
            "errors": [],
            "search_box_preview": preview,
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
    slice_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    route_counts = Counter(str(row.get("route") or "<none>") for row in rows)
    status_counts = Counter(str(row.get("result_status") or "<none>") for row in rows)
    query_class_counts = Counter(str(row.get("query_class") or "<none>") for row in rows)
    category_counts = Counter(str(row.get("category") or "<unspecified>") for row in rows)
    display_shape_counts = Counter(
        str(
            ((row.get("search_box_preview") or {}).get("display_shape") or {}).get("key")
            or "<none>"
        )
        for row in rows
    )

    no_result_case_ids: list[str] = []
    error_case_ids: list[str] = []
    suspicious_case_ids: list[str] = []
    display_problem_case_ids: list[str] = []
    error_details: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("id"))
        if row.get("result_status") == "no_result":
            no_result_case_ids.append(case_id)
        if row.get("result_status") == "error" or row.get("errors"):
            error_case_ids.append(case_id)
        if any(str(flag.get("severity")) == "suspicious" for flag in row.get("review_flags") or []):
            suspicious_case_ids.append(case_id)
        preview = row.get("search_box_preview") or {}
        if preview.get("problem_flags"):
            display_problem_case_ids.append(case_id)
        for error in row.get("errors") or []:
            error_details.append(
                {
                    "id": case_id,
                    "query": row.get("query"),
                    **error,
                }
            )

    slice_metadata = slice_metadata or {}
    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "input_path": display_path(input_path),
        "slice_id": slice_metadata.get("slice_id"),
        "slice_description": slice_metadata.get("slice_description"),
        "slice_review_goal": slice_metadata.get("slice_review_goal"),
        "input_slice_path": slice_metadata.get("input_slice_path"),
        "slice_sample_count": slice_metadata.get("slice_sample_count"),
        "case_count": len(rows),
        "result_status_counts": dict(sorted(status_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "query_class_counts": dict(sorted(query_class_counts.items())),
        "display_shape_counts": dict(sorted(display_shape_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "review_flag_counts": count_review_flags(rows),
        "suspicious_case_count": len(suspicious_case_ids),
        "suspicious_case_ids": suspicious_case_ids,
        "display_problem_case_count": len(display_problem_case_ids),
        "display_problem_case_ids": display_problem_case_ids,
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
            "regression evidence. Backend result statuses are execution/result "
            "statuses only; result_status=ok means the backend returned a structured "
            "result, not that the answer is semantically correct."
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
    is_slice_report = summary.get("slice_id") is not None
    opening_note = (
        "This is an exploratory slice report. It records what the backend returned for "
        "this slice's queries. It has no expected outputs and does not grade correctness. "
        "Backend status values are execution/result statuses only, not pass/fail QA "
        "judgments."
        if is_slice_report
        else (
            "This report is an exploratory output snapshot. It records what the real "
            "backend returned for each query. It has no expected outputs and does not "
            "grade correctness. Backend status values are execution/result statuses "
            "only, not pass/fail QA judgments."
        )
    )
    lines: list[str] = [
        "# Exploratory Query Review",
        "",
        opening_note,
        "",
        "Backend `ok` means the query returned a structured backend result. It does not "
        "imply semantic correctness, good query handling, or Raw QA pass/fail status. "
        "A human reviewer still needs to inspect the query/result pair.",
        "",
        "Reviewed cases should be promoted manually into `qa/raw_query_answer_corpus.yaml` "
        "only after a reviewer records expected status, route, shape, filters, row counts, "
        "or hard assertions.",
        "",
        "Human review should focus on whether the returned result appears appropriate for "
        "the query. Some unsupported or ambiguous queries are intentionally included. Do "
        "not treat every `no_result` as a bug. Do not treat every backend `ok` as correct.",
        "",
        "## Run Metadata",
        "",
        f"- Run ID: {md_code(summary['run_id'])}",
        f"- Started: {md_code(summary['started_at'])}",
        f"- Completed: {md_code(summary['completed_at'])}",
        f"- Input: {md_code(summary['input_path'])}",
        f"- Samples: {md_code(summary['case_count'])}",
        f"- Review state: {md_code(summary['review_state'])}",
    ]
    if is_slice_report:
        lines.extend(
            [
                f"- Slice ID: {md_code(summary.get('slice_id'))}",
                f"- Slice description: {md_escape(summary.get('slice_description'))}",
                (
                    f"- Slice review goal: {md_escape(summary.get('slice_review_goal'))}"
                    if summary.get("slice_review_goal")
                    else "- Slice review goal: _none_"
                ),
                f"- Input slice file: {md_code(summary.get('input_slice_path'))}",
                f"- Slice sample count: {md_code(summary.get('slice_sample_count'))}",
            ]
        )
    lines.extend(
        [
            "",
            "## Summary Counts",
            "",
            "These are backend execution/result counts, not correctness counts.",
            "",
            f"- Backend result statuses: {md_code(summary['result_status_counts'])}",
            f"- Routes: {md_code(summary['route_counts'])}",
            f"- Query classes: {md_code(summary['query_class_counts'])}",
            f"- Display shapes: {md_code(summary['display_shape_counts'])}",
            f"- Categories: {md_code(summary['category_counts'])}",
            f"- Review flags: {md_code(summary['review_flag_counts'])}",
            f"- Display problem cases: {md_code(summary['display_problem_case_count'])}",
            f"- Suspicious cases: {md_code(summary['suspicious_case_count'])}",
            f"- No-result cases: {md_code(summary['no_result_case_count'])}",
            f"- Error cases: {md_code(summary['error_case_count'])}",
            "",
            "Automatically detected flags are limited to structural/display/result-shape "
            "issues. A count of zero does not mean every answer is semantically correct.",
        ]
    )
    append_slowest_cases_section(lines, summary)

    lines.extend(["", "## Review Queue", ""])
    if not rows:
        lines.append("_No samples selected._")

    for row in rows:
        preview = row.get("search_box_preview") or {}
        display_shape = preview.get("display_shape") or {}
        problem_flags = preview.get("problem_flags") or []
        answer_line = md_escape(preview["answer_line"]) if preview.get("answer_line") else "_none_"
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"**Query:** {md_code(row.get('query'))}",
                "",
                f"**Answer line:** {answer_line}",
                "",
                f"**Display shape:** {md_code(display_shape.get('name'))} "
                f"({md_code(display_shape.get('key'))})",
                "",
                "<details>",
                "<summary>Supporting details</summary>",
                "",
                f"- Category: {md_code(row.get('category'))}",
                f"- Priority: {md_code(row.get('priority'))}",
                (
                    f"- Input notes: {md_escape(row.get('input_notes'))}"
                    if row.get("input_notes")
                    else "- Input notes: _none_"
                ),
                "",
                "**Search Box Preview**",
                "",
                f"- Display shape: {md_code(display_shape.get('name'))} "
                f"({md_code(display_shape.get('key'))})",
                f"- Display description: {md_escape(display_shape.get('description'))}",
                f"- Renderer patterns: {md_code(preview.get('renderer_patterns') or [])}",
                (
                    f"- Answer line: {md_escape(preview['answer_line'])}"
                    if preview.get("answer_line")
                    else "- Answer line: _not available_"
                ),
                f"- Answer line source: {md_code(preview.get('answer_line_source'))}",
                f"- Visible sections/tables: {md_code(preview.get('visible_sections') or [])}",
                f"- Display problem flags: {md_code(problem_flags) if problem_flags else '_none_'}",
                "",
                "**Engine Details**",
                "",
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
        lines.extend(["", "</details>", ""])

    path.write_text("\n".join(lines).rstrip() + "\n")


def run_review(
    *,
    input_path: Path,
    out_base: Path,
    run_id: str | None,
    overwrite_run_id: bool,
    limit: int | None,
    top_rows: int,
    samples: list[dict[str, Any]] | None = None,
    slice_metadata: dict[str, Any] | None = None,
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
    slice_id = validate_run_id_label(str(slice_metadata["slice_id"])) if slice_metadata else None
    run_parent = out_base / resolved_run_id
    run_dir = run_parent / slice_id if slice_id else run_parent
    overwrite_root = run_parent if slice_id else out_base
    validate_run_directory_target(
        run_dir,
        overwrite_run_id=overwrite_run_id,
        expected_root=overwrite_root,
    )

    source_samples = samples if samples is not None else load_samples(input_path)[1]
    selected = source_samples[:limit] if limit is not None else source_samples

    started_at = datetime.now(UTC).isoformat()
    rows = [run_sample_with_timing(sample, top_rows=top_rows) for sample in selected]
    if slice_metadata:
        row_slice_metadata = {
            "slice_id": slice_metadata.get("slice_id"),
            "slice_description": slice_metadata.get("slice_description"),
            "slice_review_goal": slice_metadata.get("slice_review_goal"),
            "input_slice_path": slice_metadata.get("input_slice_path"),
            "slice_sample_count": slice_metadata.get("slice_sample_count"),
        }
        for row in rows:
            row.update(row_slice_metadata)
    completed_at = datetime.now(UTC).isoformat()

    prepare_run_directory(
        run_dir,
        overwrite_run_id=overwrite_run_id,
        expected_root=overwrite_root,
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
        slice_metadata=slice_metadata,
    )

    write_jsonl(output_paths["report_jsonl"], rows)
    dump_json(output_paths["summary_json"], summary)
    write_markdown(output_paths["report_md"], rows, summary)

    return {"run_dir": run_dir, "rows": rows, "summary": summary}


def main() -> int:
    args = parse_args()
    input_path, samples, slice_metadata = load_review_source(args)
    result = run_review(
        input_path=input_path,
        out_base=resolve_path(args.out),
        run_id=args.run_id,
        overwrite_run_id=args.overwrite_run_id,
        limit=args.limit,
        top_rows=args.top_rows,
        samples=samples,
        slice_metadata=slice_metadata,
    )
    summary = result["summary"]
    print(f"Wrote exploratory query review: {display_path(result['run_dir'])}")
    if summary.get("slice_id"):
        print(f"Slice: {summary['slice_id']} ({summary['slice_sample_count']} samples)")
    print(f"Samples: {summary['case_count']}")
    print(f"Backend result statuses: {summary['result_status_counts']}")
    print(
        "Backend ok means a structured result was returned; it does not imply semantic correctness."
    )
    print(f"Routes: {summary['route_counts']}")
    print(f"Review flags: {summary['review_flag_counts']}")
    print(f"No-result cases: {summary['no_result_case_count']}")
    print(f"Error cases: {summary['error_case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
