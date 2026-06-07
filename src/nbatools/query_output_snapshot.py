"""Canonical text snapshot for query output review.

This module converts the normal API payload consumed by the React UI into a
stable, user-visible text representation. Review harnesses should use this as
their shared human-facing output surface and keep backend diagnostics secondary.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

REVIEW_CHECKS = [
    "Good",
    "Answer needs work",
    "Wrong/missing table",
    "Subject/table mismatch",
    "Filter treated as subject",
    "Evidence columns insufficient",
    "Query/filter problem",
    "Unsupported",
    "Promote to Raw QA",
]

PERCENT_KEYS = ("pct", "%")
ONE_DECIMAL_SUFFIXES = (
    "_avg",
    "_per_game",
    "_rating",
)
INTERNAL_DETAIL_KEYS = {
    "game_id",
    "player_id",
    "team_id",
    "opponent_team_id",
    "winner_team_id",
    "start_game_id",
    "end_game_id",
    "route",
    "query_text",
}

GAME_LOG_PLAYER_STATS = [
    "minutes",
    "pts",
    "reb",
    "ast",
    "fg",
    "fg3",
    "ft",
    "stl",
    "blk",
    "tov",
    "plus_minus",
    "ts_pct",
    "efg_pct",
]
GAME_LOG_TEAM_STATS = [
    "pts",
    "opponent_pts",
    "margin",
    "reb",
    "ast",
    "fg3m",
    "fg",
    "fg3",
    "ft",
    "tov",
    "stl",
    "blk",
    "oreb",
    "dreb",
]
GAME_LOG_LABELS = {
    "ast": "AST",
    "blk": "BLK",
    "date": "Date",
    "efg_pct": "eFG%",
    "fg": "FG",
    "fg3": "3P",
    "fg3m": "3PM",
    "ft": "FT",
    "location": "",
    "margin": "Margin",
    "minutes": "MIN",
    "opponent": "Opp",
    "opponent_pts": "Opp PTS",
    "plus_minus": "+/-",
    "pts": "PTS",
    "reb": "REB",
    "score": "Score",
    "stl": "STL",
    "team": "TM",
    "tov": "TOV",
    "ts_pct": "TS%",
    "wl": "W/L",
}
RECORD_LABELS = {
    "ast_avg": "AST",
    "def_rating": "DRtg",
    "efg_pct_avg": "eFG%",
    "fg3m_avg": "3PM",
    "fg3_pct_avg": "3P%",
    "fg_pct_avg": "FG%",
    "ft_pct_avg": "FT%",
    "games": "Games",
    "games_played": "Games",
    "losses": "Losses",
    "net_rating": "Net",
    "opponent_pts_avg": "Opp PPG",
    "plus_minus_avg": "+/-",
    "pts_avg": "PPG",
    "reb_avg": "REB",
    "season": "Season",
    "season_type": "Season Type",
    "ts_pct_avg": "TS%",
    "win_pct": "Win %",
    "wins": "Wins",
}
TEAM_RECORD_DEFAULT_STATS = ["games", "win_pct", "pts_avg", "plus_minus_avg"]
TEAM_RECORD_BY_SEASON_STATS = [
    "win_pct",
    "pts_avg",
    "opponent_pts_avg",
    "plus_minus_avg",
    "net_rating",
    "off_rating",
    "def_rating",
    "reb_avg",
    "ast_avg",
    "fg_pct_avg",
    "fg3_pct_avg",
    "ft_pct_avg",
    "ts_pct_avg",
    "efg_pct_avg",
    "fg3m_avg",
    "pace",
    "season_type",
]
LEADERBOARD_LABELS = {
    "ast_per_game": "APG",
    "blk_per_game": "BPG",
    "def_rating": "DRtg",
    "efg_pct": "eFG%",
    "fg_pct": "FG%",
    "fg3_pct": "3P%",
    "fg3a_total": "3PA",
    "fg3m_total": "3PM",
    "fga_total": "FGA",
    "fgm_total": "FGM",
    "ft_pct": "FT%",
    "fta_total": "FTA",
    "ftm_total": "FTM",
    "games_played": "GP",
    "min_per_game": "MPG",
    "minutes_per_game": "MPG",
    "minutes_total": "MIN",
    "net_rating": "Net",
    "off_rating": "ORtg",
    "pf_total": "PF",
    "pts_per_game": "PPG",
    "reb_per_game": "RPG",
    "season_type": "Type",
    "seasons": "Season",
    "stl_per_game": "SPG",
    "team_abbr": "TM",
    "ts_pct": "TS%",
    "win_pct": "Win %",
}
LEADERBOARD_DISPLAY_ORDER = [
    "season",
    "seasons",
    "team_abbr",
    "games_played",
    "wins",
    "losses",
    "win_pct",
    "season_type",
    "minutes_per_game",
    "min_per_game",
    "minutes_total",
    "pts_per_game",
    "reb_per_game",
    "ast_per_game",
    "stl_per_game",
    "blk_per_game",
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "efg_pct",
    "ts_pct",
    "fgm_total",
    "fga_total",
    "fg3m_total",
    "fg3a_total",
    "ftm_total",
    "fta_total",
    "pf_total",
    "pts_total",
    "reb_total",
    "ast_total",
]
LEADERBOARD_ENTITY_KEYS = [
    "player_name",
    "player",
    "team_name",
    "team_abbr",
    "team",
    "entity",
    "name",
    "lineup_name",
    "lineup",
    "player_names",
]
LEADERBOARD_EXCLUDED_METRIC_KEYS = {
    "rank",
    "player_id",
    "team_id",
    "game_id",
    "opponent_team_id",
    "lineup_id",
    "season",
    "seasons",
    "season_type",
    "game_date",
    "window_size",
    "stretch_metric",
    "window_start_date",
    "window_end_date",
    "games_in_window",
    "is_home",
    "is_away",
    "wl",
    "opponent_team_abbr",
    "opponent_team_name",
    "qualified",
    "qualifier",
    "qualification",
    "threshold",
    "min_games",
    "min_value",
    "max_value",
    "sample_size",
    "games_played",
}


def build_query_ui_snapshot(payload: dict[str, Any] | None, *, top_rows: int = 3) -> dict[str, Any]:
    """Build a user-visible rendered-output snapshot from a QueryResponse payload."""
    if payload is None:
        return _snapshot_for_exception(top_rows=top_rows)

    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    sections = result.get("sections") if isinstance(result.get("sections"), dict) else {}
    route = payload.get("route") or metadata.get("route")
    result_status = payload.get("result_status")
    result_reason = payload.get("result_reason")
    query = str(payload.get("query") or metadata.get("query_text") or "")
    answer = _answer_for_payload(
        query=query,
        route=str(route) if route else None,
        result_status=str(result_status) if result_status else None,
        result_reason=str(result_reason) if result_reason else None,
        metadata=metadata,
        sections=sections,
    )

    blocks: list[dict[str, Any]] = []
    if result_status in {"no_result", "error"} or not _has_displayable_rows(sections):
        blocks.append(
            {
                "type": "message",
                "title": _status_title(result_status, result_reason),
                "lines": [_status_line(result_status, result_reason)],
            }
        )
    else:
        for pattern in route_to_snapshot_patterns(
            query=query,
            route=str(route) if route else None,
            metadata=metadata,
            sections=sections,
        ):
            blocks.extend(
                _blocks_for_pattern(
                    pattern,
                    query=query,
                    route=str(route) if route else None,
                    metadata=metadata,
                    sections=sections,
                    top_rows=top_rows,
                )
            )

    return {
        "query": query,
        "status": {
            "ok": payload.get("ok"),
            "route": route,
            "result_status": result_status,
            "result_reason": result_reason,
        },
        "rendered_output": {
            "answer": answer,
            "blocks": blocks,
        },
    }


def snapshot_for_exception(query: str, exc: Exception, *, top_rows: int = 3) -> dict[str, Any]:
    snapshot = _snapshot_for_exception(top_rows=top_rows)
    snapshot["query"] = query
    snapshot["rendered_output"]["answer"] = {
        "text": "Error while running query.",
        "source": "exception",
    }
    snapshot["rendered_output"]["blocks"][0]["lines"] = [f"{type(exc).__name__}: {exc}"]
    return snapshot


def route_to_snapshot_patterns(
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> list[dict[str, Any]]:
    """Route-to-pattern contract used by the text snapshot renderer."""
    route_key = route or _text(metadata, "route")
    if route_key == "player_game_summary":
        if _should_show_player_summary_game_log(query=query, metadata=metadata, sections=sections):
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
        if _section_rows(sections, "game_log"):
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
        if _section_rows(sections, "leaderboard"):
            return [
                {
                    "type": "leaderboard",
                    "section_key": "leaderboard",
                    "metric_key": "appearances",
                    "sentence_metric_label": "playoff appearances",
                }
            ]
        if _section_rows(sections, "summary") or _section_rows(sections, "by_season"):
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


def snapshot_review_markdown_lines(
    *,
    case_id: Any,
    snapshot: dict[str, Any],
    index: int | None = None,
    heading_level: int = 2,
    include_checks: bool = True,
) -> list[str]:
    prefix = "#" * heading_level
    title = f"{index}. {case_id}" if index is not None else str(case_id)
    rendered = snapshot.get("rendered_output") or {}
    answer = rendered.get("answer") if isinstance(rendered.get("answer"), dict) else {}
    lines = [
        f"{prefix} {md_escape(title)}",
        "",
        "**Query**  ",
        md_escape(snapshot.get("query")),
        "",
        "**Answer shown**  ",
        md_escape(answer.get("text") or "_none_"),
        "",
        "**Rendered output**",
        "",
    ]
    blocks = rendered.get("blocks") if isinstance(rendered.get("blocks"), list) else []
    if not blocks:
        lines.append("_No rendered blocks._")
    for block in blocks:
        lines.extend(_block_markdown_lines(block, heading_level=heading_level + 1))
    if include_checks:
        lines.extend(["", "**Reviewer checks**  "])
        for label in REVIEW_CHECKS:
            lines.append(f"[ ] {label}  ")
        lines.extend(["", "**Reviewer notes**  ", "-"])
    return lines


def snapshot_debug_markdown_lines(snapshot: dict[str, Any]) -> list[str]:
    status = snapshot.get("status") or {}
    rendered = snapshot.get("rendered_output") or {}
    answer = rendered.get("answer") if isinstance(rendered.get("answer"), dict) else {}
    blocks = rendered.get("blocks") if isinstance(rendered.get("blocks"), list) else []
    lines = [
        "**Query Output Snapshot**",
        "",
        f"- Route: {md_code(status.get('route'))}",
        f"- Result status: {md_code(status.get('result_status'))}",
        f"- Result reason: {md_code(status.get('result_reason'))}",
        f"- Answer source: {md_code(answer.get('source'))}",
        f"- Rendered block count: {md_code(len(blocks))}",
    ]
    for block in blocks:
        lines.append(
            "- "
            + md_escape(str(block.get("type") or "block"))
            + ": "
            + md_escape(str(block.get("title") or "Untitled"))
        )
    return lines


def md_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("&", "&amp;").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def md_code(value: Any) -> str:
    if value is None:
        return "`<none>`"
    text = str(value).replace("`", "\\`")
    return f"`{text}`"


def markdown_table_from_matrix(headers: list[str], rows: list[list[str]]) -> str:
    safe_headers = [md_escape(header) for header in headers]
    safe_rows = [[md_escape(cell) for cell in row] for row in rows]
    lines = [
        "| " + " | ".join(safe_headers) + " |",
        "| " + " | ".join("---" for _ in safe_headers) + " |",
    ]
    for row in safe_rows:
        padded = row[: len(safe_headers)] + [""] * max(0, len(safe_headers) - len(row))
        lines.append("| " + " | ".join(padded[: len(safe_headers)]) + " |")
    return "\n".join(lines)


def _blocks_for_pattern(
    pattern: dict[str, Any],
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    top_rows: int,
) -> list[dict[str, Any]]:
    pattern_type = pattern.get("type")
    if pattern_type == "entity_summary":
        return _entity_summary_blocks(
            pattern, query=query, metadata=metadata, sections=sections, top_rows=top_rows
        )
    if pattern_type == "game_log":
        return _game_log_blocks(
            pattern,
            query=query,
            route=route,
            metadata=metadata,
            sections=sections,
            top_rows=top_rows,
        )
    if pattern_type == "record":
        return _record_blocks(
            pattern,
            query=query,
            route=route,
            metadata=metadata,
            sections=sections,
            top_rows=top_rows,
        )
    if pattern_type == "leaderboard":
        return _leaderboard_blocks(
            pattern,
            query=query,
            route=route,
            metadata=metadata,
            sections=sections,
            top_rows=top_rows,
        )
    if pattern_type == "top_performances":
        rows = _section_rows(sections, str(pattern.get("section_key") or "leaderboard"))
        return [
            _generic_table_block(
                "Top Performances",
                rows,
                section_key="leaderboard",
                top_rows=top_rows,
                mode=str(pattern.get("subject") or ""),
            )
        ]
    if pattern_type == "split":
        section_key = str(pattern.get("section_key") or "split_comparison")
        rows = _section_rows(sections, section_key) or _section_rows(sections, "summary")
        return [
            _generic_table_block(
                "Split Comparison",
                rows,
                section_key=section_key,
                top_rows=top_rows,
                mode=f"{pattern.get('subject') or 'split'} split",
            )
        ]
    if pattern_type == "streak":
        rows = _section_rows(sections, str(pattern.get("section_key") or "streak"))
        return [
            _generic_table_block(
                "Streaks", rows, section_key="streak", top_rows=top_rows, mode="streak table"
            )
        ]
    if pattern_type == "comparison":
        rows = _section_rows(sections, "comparison") or _section_rows(sections, "summary")
        return [
            _generic_table_block(
                "Comparison",
                rows,
                section_key="comparison",
                top_rows=top_rows,
                mode=f"{pattern.get('subject') or 'entity'} comparison",
            )
        ]
    if pattern_type == "playoff_history":
        rows = (
            _section_rows(sections, "by_season")
            or _section_rows(sections, "leaderboard")
            or _section_rows(sections, "summary")
        )
        return [
            _generic_table_block(
                "Playoff History",
                rows,
                section_key="by_season",
                top_rows=top_rows,
                mode=str(pattern.get("mode") or "playoff history"),
            )
        ]
    if pattern_type == "rolling_stretch":
        rows = _section_rows(sections, str(pattern.get("section_key") or "leaderboard"))
        return [
            _generic_table_block(
                "Rolling Stretch",
                rows,
                section_key="leaderboard",
                top_rows=top_rows,
                mode="rolling stretch",
            )
        ]
    blocks: list[dict[str, Any]] = []
    for section_key, value in sections.items():
        rows = value if isinstance(value, list) else []
        if rows:
            blocks.append(
                _generic_table_block(
                    _title_from_section(section_key),
                    rows,
                    section_key=section_key,
                    top_rows=top_rows,
                    mode="fallback table",
                )
            )
    return blocks


def _entity_summary_blocks(
    pattern: dict[str, Any],
    *,
    query: str,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    top_rows: int,
) -> list[dict[str, Any]]:
    section_key = str(pattern.get("section_key") or "summary")
    rows = _section_rows(sections, section_key)
    if not rows:
        return []
    row = rows[0]
    blocks = [
        {
            "type": "hero_card",
            "title": "Summary",
            "lines": _summary_card_lines(row, metadata, query),
            "subject": _row_subject(row, metadata),
            "mode": "entity summary",
            "section_key": section_key,
            "filters": _filter_labels(metadata),
        }
    ]
    by_season = _section_rows(sections, "by_season")
    if by_season:
        columns = _entity_by_season_columns(by_season)
        blocks.append(
            _table_block(
                title="By Season",
                rows=by_season,
                columns=columns,
                section_key="by_season",
                subject=_row_subject(row, metadata),
                mode="season stats",
                filters=_filter_labels(metadata),
                top_rows=top_rows,
            )
        )
    return blocks


def _game_log_blocks(
    pattern: dict[str, Any],
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    top_rows: int,
) -> list[dict[str, Any]]:
    section_key = str(pattern.get("section_key") or "game_log")
    fallback_key = pattern.get("fallback_section_key")
    rows = _section_rows(sections, section_key)
    if not rows and isinstance(fallback_key, str):
        rows = _section_rows(sections, fallback_key)
        section_key = fallback_key
    summary_rows = _section_rows(sections, str(pattern.get("summary_key") or "summary"))
    if not rows and not summary_rows:
        return []
    mode = _game_log_mode(rows, str(pattern.get("mode") or "auto"))
    blocks: list[dict[str, Any]] = []
    if summary_rows and pattern.get("show_summary_strip", True):
        blocks.append(
            {
                "type": "hero_card",
                "title": "Averages",
                "lines": _summary_card_lines(summary_rows[0], metadata, query),
                "subject": _row_subject(summary_rows[0], metadata),
                "mode": f"{mode} summary",
                "section_key": str(pattern.get("summary_key") or "summary"),
                "filters": _filter_labels(metadata),
            }
        )
    if rows:
        columns = _game_log_columns(rows, mode=mode, metadata=metadata)
        title = str(
            pattern.get("raw_detail_title")
            or ("Player Game Log" if mode == "player" else "Game Log")
        )
        block_type = "detail_table" if pattern.get("collapse_to_detail") else "table"
        blocks.append(
            _table_block(
                title=title,
                rows=rows,
                columns=columns,
                section_key=section_key,
                subject=_game_log_subject(rows, mode, metadata),
                mode="Player game log" if mode == "player" else "Team game log",
                filters=_filter_labels(metadata),
                top_rows=top_rows,
                block_type=block_type,
                collapsed=bool(pattern.get("collapse_to_detail")),
                collapsed_label="Show game detail" if pattern.get("collapse_to_detail") else None,
            )
        )
    for detail_key in pattern.get("detail_section_keys") or []:
        detail_rows = _section_rows(sections, str(detail_key))
        if detail_rows:
            blocks.append(
                _generic_table_block(
                    _title_from_section(str(detail_key)),
                    detail_rows,
                    section_key=str(detail_key),
                    top_rows=top_rows,
                    mode="detail table",
                    block_type="detail_table",
                )
            )
    return blocks


def _record_blocks(
    pattern: dict[str, Any],
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    top_rows: int,
) -> list[dict[str, Any]]:
    mode = str(pattern.get("mode") or "team_record")
    if mode != "team_record":
        section_key = "leaderboard" if "leaderboard" in mode else "by_season"
        rows = _section_rows(sections, section_key) or _section_rows(sections, "summary")
        return [
            _generic_table_block(
                _record_mode_title(mode),
                rows,
                section_key=section_key,
                top_rows=top_rows,
                mode=mode.replace("_", " "),
            )
        ]

    summary = _section_rows(sections, "summary")
    if not summary:
        return []
    row = summary[0]
    subject = _team_subject(row, metadata)
    blocks = [
        {
            "type": "hero_card",
            "title": "Team Record",
            "lines": _team_record_card_lines(row),
            "subject": subject,
            "mode": "Team record",
            "section_key": "summary",
            "filters": _filter_labels(metadata),
        },
        _table_block(
            title="Team record",
            rows=summary,
            columns=_team_record_columns(summary, metadata),
            section_key="summary",
            subject=subject,
            mode="Team record",
            filters=_filter_labels(metadata),
            top_rows=top_rows,
        ),
    ]
    by_season = _section_rows(sections, "by_season")
    if by_season and _should_show_by_season(metadata, by_season):
        blocks.append(
            _table_block(
                title="Team record by season",
                rows=by_season,
                columns=_team_record_by_season_columns(by_season),
                section_key="by_season",
                subject=subject,
                mode="Team season records",
                filters=_filter_labels(metadata),
                top_rows=top_rows,
            )
        )
    return blocks


def _leaderboard_blocks(
    pattern: dict[str, Any],
    *,
    query: str,
    route: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
    top_rows: int,
) -> list[dict[str, Any]]:
    section_key = str(pattern.get("section_key") or "leaderboard")
    rows = _section_rows(sections, section_key)
    if not rows:
        return []
    metric = _leaderboard_metric(rows, metadata, pattern.get("metric_key"))
    entity_kind = _leaderboard_entity_kind(rows[0])
    columns = _leaderboard_columns(rows, metric=metric, entity_kind=entity_kind, route=route)
    return [
        _table_block(
            title="Leaderboard",
            rows=rows,
            columns=columns,
            section_key=section_key,
            subject="League" if entity_kind == "player" else "Teams",
            mode="Leaderboard",
            filters=_filter_labels(metadata),
            top_rows=top_rows,
        )
    ]


def _table_block(
    *,
    title: str,
    rows: list[dict[str, Any]],
    columns: list[dict[str, Any]],
    section_key: str,
    subject: str | None,
    mode: str | None,
    filters: list[str] | None,
    top_rows: int,
    block_type: str = "table",
    collapsed: bool = False,
    collapsed_label: str | None = None,
) -> dict[str, Any]:
    headers = [str(column["label"]) for column in columns]
    rendered_rows: list[list[str]] = []
    for index, row in enumerate(rows[:top_rows]):
        rendered_rows.append([_render_column(row, column, index) for column in columns])
    return {
        "type": block_type,
        "title": title,
        "subject": subject,
        "mode": mode,
        "section_key": section_key,
        "filters": filters or [],
        "row_count": len(rows),
        "visible_columns": headers,
        "rows": rendered_rows,
        "collapsed": collapsed,
        "collapsed_label": collapsed_label,
    }


def _generic_table_block(
    title: str,
    rows: list[dict[str, Any]],
    *,
    section_key: str,
    top_rows: int,
    mode: str,
    block_type: str = "table",
) -> dict[str, Any]:
    columns = [{"key": key, "label": _format_col_header(key)} for key in _generic_columns(rows)]
    return _table_block(
        title=title,
        rows=rows,
        columns=columns,
        section_key=section_key,
        subject=_row_subject(rows[0], {}) if rows else None,
        mode=mode,
        filters=[],
        top_rows=top_rows,
        block_type=block_type,
    )


def _block_markdown_lines(block: dict[str, Any], *, heading_level: int) -> list[str]:
    prefix = "#" * heading_level
    block_type = str(block.get("type") or "block")
    title = str(block.get("title") or "Untitled")
    label = {
        "hero_card": "Card",
        "table": "Table",
        "detail_table": "Detail",
        "message": "Message",
    }.get(block_type, "Block")
    lines = [f"{prefix} {label} — {md_escape(title)}", ""]
    if block.get("subject"):
        lines.append(f"Subject: {md_escape(block.get('subject'))}  ")
    if block.get("mode"):
        lines.append(f"Mode: {md_escape(block.get('mode'))}  ")
    filters = block.get("filters") if isinstance(block.get("filters"), list) else []
    if filters:
        lines.append(f"Filter: {md_escape('; '.join(str(item) for item in filters))}  ")
    if block_type in {"table", "detail_table"}:
        lines.append(f"Rows: {md_escape(block.get('row_count'))}  ")
        if block.get("collapsed"):
            lines.append(
                f"Collapsed label: {md_escape(block.get('collapsed_label') or 'Show details')}  "
            )
    if block.get("lines"):
        for line in block.get("lines") or []:
            lines.append(f"{md_escape(line)}  ")
    headers = block.get("visible_columns")
    rows = block.get("rows")
    if isinstance(headers, list) and headers and isinstance(rows, list):
        lines.extend(["", markdown_table_from_matrix([str(h) for h in headers], rows)])
    return lines + [""]


def _snapshot_for_exception(*, top_rows: int) -> dict[str, Any]:
    return {
        "query": "",
        "status": {
            "ok": False,
            "route": None,
            "result_status": "error",
            "result_reason": "exception",
        },
        "rendered_output": {
            "answer": {"text": "Error while running query.", "source": "exception"},
            "blocks": [
                {
                    "type": "message",
                    "title": "Error",
                    "lines": ["Error while running query."],
                }
            ],
        },
    }


def _answer_for_payload(
    *,
    query: str,
    route: str | None,
    result_status: str | None,
    result_reason: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any]:
    if result_status == "error":
        return {"text": "Error while running query.", "source": "status"}
    if result_status == "no_result":
        return {"text": "No answer returned.", "source": "status"}
    phrase = _text(metadata, "answer_phrase") or _text(metadata, "count_phrase")
    if phrase:
        return {"text": _trim_trailing_zeroes(phrase), "source": "ResultHero"}
    if route == "player_game_finder":
        rows = _section_rows(sections, "finder")
        if rows:
            return {
                "text": _player_finder_sentence(query, rows, metadata),
                "source": "ResultHero",
            }
    if route == "team_record":
        rows = _section_rows(sections, "summary")
        if rows:
            return {
                "text": _team_record_sentence(rows[0], metadata),
                "source": "ResultHero",
            }
    if route in {"season_leaders", "season_team_leaders", "team_record_leaderboard"}:
        rows = _section_rows(sections, "leaderboard")
        if rows:
            return {
                "text": _leaderboard_sentence(rows[0], metadata),
                "source": "ResultHero",
            }
    summary = _compact_answer_summary(
        route=route,
        result_status=result_status,
        result_reason=result_reason,
        metadata=metadata,
        sections=sections,
    )
    return {"text": summary or "_none_", "source": "snapshot_summary" if summary else None}


def _compact_answer_summary(
    *,
    route: str | None,
    result_status: str | None,
    result_reason: str | None,
    metadata: dict[str, Any],
    sections: dict[str, Any],
) -> str | None:
    if result_status in {"no_result", "error"}:
        return f"No answer rows returned; reason={result_reason or 'unknown'}"
    count_rows = _section_rows(sections, "count")
    if count_rows and count_rows[0].get("count") is not None:
        return f"Count: {_format_value(count_rows[0].get('count'), 'count')}"
    summary = _section_rows(sections, "summary")
    if summary:
        row = summary[0]
        entity = _row_subject(row, metadata) or "Result"
        bits: list[str] = []
        if row.get("wins") is not None and row.get("losses") is not None:
            wins = _format_value(row.get("wins"), "wins")
            losses = _format_value(row.get("losses"), "losses")
            record = f"{wins}-{losses}"
            if row.get("games") is not None:
                record = f"{record} over {_format_value(row.get('games'), 'games')} games"
            bits.append(record)
        elif row.get("games") is not None:
            bits.append(f"{_format_value(row.get('games'), 'games')} games")
        for key, label in (("pts_avg", "PPG"), ("reb_avg", "RPG"), ("ast_avg", "APG")):
            if key in row:
                bits.append(f"{_format_value(row[key], key)} {label}")
        return f"{entity} -- {', '.join(bits)}" if bits else entity
    for section_name in ("leaderboard", "finder", "streak", "split_comparison", "by_season"):
        rows = _section_rows(sections, section_name)
        if rows:
            entity = _row_subject(rows[0], metadata) or "Top row"
            return f"Top row: {entity}"
    return f"No compact answer summary available; route={route}" if route else None


def _status_title(result_status: Any, result_reason: Any) -> str:
    if result_status == "error" or result_reason == "exception":
        return "Error"
    return "No result"


def _status_line(result_status: Any, result_reason: Any) -> str:
    if result_status == "error" or result_reason == "exception":
        return "The query could not be rendered because execution raised an error."
    return f"No answer rows returned; reason={result_reason or 'no_result'}."


def _has_displayable_rows(sections: dict[str, Any]) -> bool:
    return any(isinstance(rows, list) and len(rows) > 0 for rows in sections.values())


def _section_rows(sections: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = sections.get(key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _should_show_player_summary_game_log(
    *, query: str, metadata: dict[str, Any], sections: dict[str, Any]
) -> bool:
    if not _section_rows(sections, "game_log"):
        return False
    if isinstance(metadata.get("window_size"), (int, float)):
        return True
    if re.search(r"\blast\s+\d+\s*(?:games?|gms?)?\b", query, flags=re.I):
        return True
    if _text(metadata, "opponent") or metadata.get("opponent_team_abbrs"):
        return True
    filters = metadata.get("applied_filters")
    if not isinstance(filters, list):
        return False
    meaningful = {
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
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        label = str(item.get("label") or "").strip().lower()
        if kind == "team" and "opponent" in label:
            return True
        if kind in meaningful:
            return True
    return False


def _summary_card_lines(row: dict[str, Any], metadata: dict[str, Any], query: str) -> list[str]:
    lines: list[str] = []
    games = row.get("games", row.get("games_played"))
    if games is not None:
        lines.append(f"Games: {_format_value(games, 'games')}")
    if row.get("wins") is not None or row.get("losses") is not None:
        lines.append(f"Record: {_record_value(row)}")
    for key, label in (("pts_avg", "PPG"), ("reb_avg", "RPG"), ("ast_avg", "APG")):
        if row.get(key) is not None:
            lines.append(f"{label}: {_format_value(row.get(key), key)}")
    if not lines:
        subject = _row_subject(row, metadata)
        lines.append(f"{subject or 'Summary'} is available.")
    return lines


def _team_record_card_lines(row: dict[str, Any]) -> list[str]:
    lines = [f"Record: {_record_value(row)}"]
    for key, label in (
        ("games", "Games"),
        ("win_pct", "Win %"),
        ("pts_avg", "PPG"),
        ("plus_minus_avg", "+/-"),
    ):
        if row.get(key) is not None:
            lines.append(f"{label}: {_format_value(row.get(key), key)}")
    return lines


def _team_record_sentence(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    team = _team_subject(row, metadata) or "This team"
    record = _record_value(row)
    context = _season_context(row, metadata)
    win_pct = (
        f", a {_format_prose_value(row.get('win_pct'), 'win_pct')} win rate"
        if row.get("win_pct") is not None
        else ""
    )
    if record != "—":
        return f"The {team} are {record}{context}{win_pct}."
    return f"The {team} have a record summary{context}."


def _player_finder_sentence(
    query: str, rows: list[dict[str, Any]], metadata: dict[str, Any]
) -> str:
    first = rows[0]
    player = (
        _text(metadata.get("player_context"), "player_name")
        or _text(first, "player_name")
        or "This player"
    )
    game_noun = "game" if len(rows) == 1 else "games"
    timeframe = ""
    if "this season" in query.lower():
        timeframe = " this season"
    elif _text(first, "season"):
        timeframe = f" in {_text(first, 'season')}"
    return f"{player} had {len(rows)} {game_noun} matching{timeframe}."


def _leaderboard_sentence(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    leader = _row_subject(row, metadata) or "The leader"
    metric = _leaderboard_metric([row], metadata, None)
    value = _format_prose_value(row.get(metric), metric) if metric else ""
    if metric and value != "—":
        return f"{leader} led with {value} {_format_col_header(metric).lower()}."
    return f"{leader} led the leaderboard."


def _team_record_columns(
    rows: list[dict[str, Any]], metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    columns = [
        {
            "key": "team",
            "label": "Team",
            "value": lambda row, index: _team_subject(row, metadata) or "—",
        }
    ]
    columns.append(
        {"key": "record", "label": "W-L", "value": lambda row, index: _record_value(row)}
    )
    for key in TEAM_RECORD_DEFAULT_STATS:
        if any(_has_value(row.get(key)) for row in rows):
            columns.append({"key": key, "label": RECORD_LABELS.get(key, _format_col_header(key))})
    if _applied_filter_value(metadata, "Opponent quality"):
        columns.append(
            {
                "key": "opponent_group",
                "label": "Opponent Group",
                "value": lambda row, index: (
                    _applied_filter_value(metadata, "Opponent quality") or "—"
                ),
            }
        )
    if _applied_filter_value(metadata, "Location"):
        columns.append(
            {
                "key": "location",
                "label": "Home/Away",
                "value": lambda row, index: _applied_filter_value(metadata, "Location") or "—",
            }
        )
    if _text(metadata.get("opponent_context"), "team_name") or _text(metadata, "opponent"):
        columns.append(
            {
                "key": "opponent",
                "label": "Opponent",
                "value": lambda row, index: (
                    _text(metadata.get("opponent_context"), "team_name")
                    or _text(metadata, "opponent")
                    or "—"
                ),
            }
        )
    return columns


def _team_record_by_season_columns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = [{"key": "season", "label": "Season"}]
    if any(_has_value(row.get("games")) or _has_value(row.get("games_played")) for row in rows):
        key = "games" if any(_has_value(row.get("games")) for row in rows) else "games_played"
        columns.append({"key": key, "label": RECORD_LABELS.get(key, _format_col_header(key))})
    if any(_has_value(row.get("wins")) or _has_value(row.get("losses")) for row in rows):
        columns.append(
            {"key": "record", "label": "W-L", "value": lambda row, index: _record_value(row)}
        )
    for key in TEAM_RECORD_BY_SEASON_STATS:
        if key in {"games", "games_played"}:
            continue
        if any(_has_value(row.get(key)) for row in rows):
            columns.append({"key": key, "label": RECORD_LABELS.get(key, _format_col_header(key))})
    return columns


def _entity_by_season_columns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred = [
        "season",
        "team_abbr",
        "games",
        "games_played",
        "wins",
        "losses",
        "win_pct",
        "pts_avg",
        "reb_avg",
        "ast_avg",
        "fg3m_avg",
        "tov_avg",
        "plus_minus_avg",
    ]
    keys = [key for key in preferred if any(_has_value(row.get(key)) for row in rows)]
    return [
        {"key": key, "label": RECORD_LABELS.get(key, _format_col_header(key))} for key in keys[:10]
    ]


def _game_log_columns(
    rows: list[dict[str, Any]],
    *,
    mode: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = [
        {"key": "rank", "label": "#", "value": lambda row, index: str(index + 1)}
    ]
    hide_player = mode == "player" and _has_pinned_player(metadata)
    if mode == "player" and not hide_player:
        columns.append(
            {
                "key": "player",
                "label": "Player",
                "value": lambda row, index: _text(row, "player_name") or "—",
            }
        )
    columns.append(
        {
            "key": "date",
            "label": "Date",
            "value": lambda row, index: _format_compact_date(_text(row, "game_date")),
        }
    )
    columns.append(
        {
            "key": "team",
            "label": "TM" if mode == "player" else "Team",
            "value": lambda row, index: _team_cell(row, metadata),
        }
    )
    columns.append(
        {"key": "location", "label": "", "value": lambda row, index: _location_cell(row)}
    )
    columns.append(
        {"key": "opponent", "label": "Opp", "value": lambda row, index: _opponent_cell(row)}
    )
    if any(_has_score(row, mode) for row in rows):
        columns.append(
            {"key": "score", "label": "Score", "value": lambda row, index: _score_cell(row, mode)}
        )
    if any(_has_value(row.get("wl")) for row in rows):
        columns.append(
            {
                "key": "wl",
                "label": "W/L",
                "value": lambda row, index: str(row.get("wl") or "—").upper(),
            }
        )
    stat_keys = GAME_LOG_PLAYER_STATS if mode == "player" else GAME_LOG_TEAM_STATS
    for key in stat_keys:
        if any(_has_stat_column(row, key) for row in rows):
            columns.append({"key": key, "label": GAME_LOG_LABELS.get(key, key)})
    return columns


def _leaderboard_columns(
    rows: list[dict[str, Any]],
    *,
    metric: str | None,
    entity_kind: str,
    route: str | None,
) -> list[dict[str, Any]]:
    entity_label = (
        "Team" if entity_kind == "team" else "Player" if entity_kind == "player" else "Name"
    )
    columns = [
        {
            "key": "rank",
            "label": "#",
            "value": lambda row, index: str(row.get("rank") or index + 1),
        },
        {
            "key": "entity",
            "label": entity_label,
            "value": lambda row, index: _row_subject(row, {}) or "—",
        },
    ]
    if metric:
        columns.append(
            {"key": metric, "label": LEADERBOARD_LABELS.get(metric, _format_col_header(metric))}
        )
    for key in LEADERBOARD_DISPLAY_ORDER:
        if key == metric:
            continue
        if any(_has_value(row.get(key)) for row in rows):
            columns.append(
                {"key": key, "label": LEADERBOARD_LABELS.get(key, _format_col_header(key))}
            )
        if len(columns) >= 10:
            break
    return columns


def _generic_columns(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "rank",
        "player_name",
        "team_name",
        "team_abbr",
        "season",
        "game_date",
        "opponent_team_abbr",
        "wl",
        "games",
        "wins",
        "losses",
        "win_pct",
        "pts",
        "pts_avg",
        "reb",
        "reb_avg",
        "ast",
        "ast_avg",
    ]
    row_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen and key not in INTERNAL_DETAIL_KEYS:
                seen.add(key)
                row_keys.append(key)
    ordered = [key for key in preferred if key in seen]
    ordered.extend(key for key in row_keys if key not in ordered)
    return ordered[:10]


def _render_column(row: dict[str, Any], column: dict[str, Any], index: int) -> str:
    value_getter = column.get("value")
    if callable(value_getter):
        return str(value_getter(row, index))
    key = str(column.get("key"))
    return _format_value(row.get(key), key)


def _game_log_mode(rows: list[dict[str, Any]], requested: str) -> str:
    if requested in {"player", "team"}:
        return requested
    if any("player_name" in row or "player_id" in row for row in rows):
        return "player"
    return "team"


def _game_log_subject(
    rows: list[dict[str, Any]], mode: str, metadata: dict[str, Any]
) -> str | None:
    if mode == "player":
        return (
            _text(metadata.get("player_context"), "player_name") or _text(rows[0], "player_name")
            if rows
            else None
        )
    return (
        _team_subject(rows[0], metadata)
        if rows
        else _text(metadata.get("team_context"), "team_name")
    )


def _team_subject(row: dict[str, Any], metadata: dict[str, Any]) -> str | None:
    return (
        _text(row, "team_name")
        or _text(metadata.get("team_context"), "team_name")
        or _text(row, "team_abbr")
        or _text(metadata.get("team_context"), "team_abbr")
        or _text(row, "team")
    )


def _row_subject(row: dict[str, Any], metadata: dict[str, Any]) -> str | None:
    return (
        _text(row, "player_name")
        or _text(metadata.get("player_context"), "player_name")
        or _team_subject(row, metadata)
        or _text(row, "entity")
        or _text(row, "name")
    )


def _leaderboard_entity_kind(row: dict[str, Any]) -> str:
    if row.get("player_name") or row.get("player_id"):
        return "player"
    if row.get("team_name") or row.get("team_abbr") or row.get("team_id"):
        return "team"
    return "unknown"


def _leaderboard_metric(
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    explicit_metric: Any,
) -> str | None:
    for candidate in (
        explicit_metric,
        metadata.get("stat"),
        metadata.get("metric"),
        metadata.get("sort_by"),
    ):
        if isinstance(candidate, str) and any(_has_value(row.get(candidate)) for row in rows):
            return candidate
    for key in rows[0] if rows else []:
        if key in LEADERBOARD_ENTITY_KEYS or key in LEADERBOARD_EXCLUDED_METRIC_KEYS:
            continue
        if any(isinstance(row.get(key), (int, float)) for row in rows):
            return key
    return None


def _filter_labels(metadata: dict[str, Any]) -> list[str]:
    filters = metadata.get("applied_filters")
    if not isinstance(filters, list):
        return []
    labels: list[str] = []
    for item in filters:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("kind") or "Filter").strip()
        value = item.get("value")
        if value is None or value == "":
            labels.append(label)
        else:
            labels.append(f"{label}: {value}")
    return labels


def _applied_filter_value(metadata: dict[str, Any], label: str) -> str | None:
    filters = metadata.get("applied_filters")
    if not isinstance(filters, list):
        return None
    for item in filters:
        if not isinstance(item, dict):
            continue
        if str(item.get("label") or "").casefold() == label.casefold():
            value = item.get("value")
            return str(value) if value is not None else None
    return None


def _record_value(row: dict[str, Any]) -> str:
    if row.get("wins") is None and row.get("losses") is None:
        return "—"
    return f"{_format_value(row.get('wins'), 'wins')}-{_format_value(row.get('losses'), 'losses')}"


def _season_context(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    season = _text(row, "season") or _text(row, "season_start") or _text(metadata, "season")
    season_type = _text(row, "season_type") or _text(metadata, "season_type")
    parts = [part for part in (season, season_type) if part]
    return f" in {' '.join(parts)}" if parts else ""


def _should_show_by_season(metadata: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    if len(rows) > 1:
        return True
    scope = _text(metadata, "scope_kind")
    return scope in {"career", "season_range", "all_time", "decade"}


def _record_mode_title(mode: str) -> str:
    return {
        "record_by_decade": "Record by decade",
        "record_by_decade_leaderboard": "Record by decade leaderboard",
        "matchup_by_decade": "Matchup by decade",
    }.get(mode, _format_col_header(mode))


def _title_from_section(section_key: str) -> str:
    return {
        "by_season": "By Season",
        "finder": "Matching Games",
        "game_log": "Game Log",
        "leaderboard": "Leaderboard",
        "split_comparison": "Split Comparison",
        "streak": "Streaks",
        "summary": "Summary",
        "top_performers": "Top Performers",
    }.get(section_key, _format_col_header(section_key))


def _team_cell(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    return (
        _text(row, "team_abbr")
        or _text(row, "team_name")
        or _text(metadata.get("team_context"), "team_abbr")
        or "—"
    )


def _opponent_cell(row: dict[str, Any]) -> str:
    return (
        _text(row, "opponent_team_abbr")
        or _text(row, "opponent_team_name")
        or _text(row, "opponent")
        or "—"
    )


def _location_cell(row: dict[str, Any]) -> str:
    if row.get("is_home") is True:
        return "vs"
    if row.get("is_away") is True:
        return "@"
    return _text(row, "location") or ""


def _has_score(row: dict[str, Any], mode: str) -> bool:
    if mode == "team":
        return _has_value(row.get("pts")) and _has_value(row.get("opponent_pts"))
    return (
        _has_value(row.get("team_score"))
        or _has_value(row.get("pts_team"))
        or _has_value(row.get("team_pts"))
    ) and (
        _has_value(row.get("opponent_score"))
        or _has_value(row.get("opponent_pts"))
        or _has_value(row.get("opp_pts"))
    )


def _score_cell(row: dict[str, Any], mode: str) -> str:
    if mode == "team":
        left = row.get("pts")
        right = row.get("opponent_pts")
    else:
        left = row.get("team_score", row.get("pts_team", row.get("team_pts")))
        right = row.get("opponent_score", row.get("opponent_pts", row.get("opp_pts")))
    if not _has_value(left) or not _has_value(right):
        return "—"
    return f"{_format_value(left, 'pts')}-{_format_value(right, 'pts')}"


def _has_stat_column(row: dict[str, Any], key: str) -> bool:
    if key == "fg":
        return (
            _has_value(row.get("fgm"))
            or _has_value(row.get("fga"))
            or _has_value(row.get("fg_pct"))
        )
    if key == "fg3":
        return (
            _has_value(row.get("fg3m"))
            or _has_value(row.get("fg3a"))
            or _has_value(row.get("fg3_pct"))
        )
    if key == "ft":
        return (
            _has_value(row.get("ftm"))
            or _has_value(row.get("fta"))
            or _has_value(row.get("ft_pct"))
        )
    if key == "margin":
        return _has_value(row.get("plus_minus")) or (
            _has_value(row.get("pts")) and _has_value(row.get("opponent_pts"))
        )
    return _has_value(row.get(key))


def _format_value(value: Any, key: str) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return _format_number(value, key)
    if key in {"game_date", "window_start_date", "window_end_date", "date"}:
        return _format_compact_date(str(value))
    return str(value)


def _format_prose_value(value: Any, key: str) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        if _is_percent_key(key):
            percent = value * 100 if 0 <= value <= 1 else value
            return f"{percent:.1f}".rstrip("0").rstrip(".") + "%"
        return (
            f"{value:.1f}".rstrip("0").rstrip(".")
            if not float(value).is_integer()
            else f"{int(value):,}"
        )
    return str(value)


def _format_number(value: int | float, key: str) -> str:
    if _is_percent_key(key):
        percent = value * 100 if 0 <= value <= 1 else value
        return f"{percent:.1f}%"
    if any(key.endswith(suffix) for suffix in ONE_DECIMAL_SUFFIXES) or key == "pace":
        return f"{value:.1f}"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:.1f}"


def _is_percent_key(key: str) -> bool:
    lower = key.lower()
    return "pct" in lower or lower.endswith("%")


def _format_compact_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value[:10]).replace(tzinfo=UTC)
    except ValueError:
        return value
    return parsed.strftime("%b ") + str(parsed.day)


def _format_col_header(key: str) -> str:
    if len(key) <= 5 and key.upper() == key:
        return key
    return " ".join(part.capitalize() for part in key.replace("_", " ").split())


def _has_pinned_player(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("player_context") or metadata.get("player"))


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _text(value: Any, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get(key)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _trim_trailing_zeroes(value: str) -> str:
    return value.replace(".0 ", " ").replace(".0.", ".")
