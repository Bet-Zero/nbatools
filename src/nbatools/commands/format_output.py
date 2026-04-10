from __future__ import annotations

from io import StringIO

import pandas as pd

SECTION_RULE = "────────────────────────"


def _read_csv_block(block: str) -> pd.DataFrame | None:
    block = block.strip()
    if not block or block.lower() == "no matching games":
        return None
    try:
        return pd.read_csv(StringIO(block))
    except Exception:
        return None


def _extract_sections(text: str) -> dict[str, str]:
    text = text.strip().replace("\r\n", "\n")
    sections: dict[str, str] = {}

    if text.startswith("SUMMARY\n"):
        remaining = text[len("SUMMARY\n") :]

        if "\nCOMPARISON\n" in remaining:
            summary_part, comparison_part = remaining.split("\nCOMPARISON\n", 1)
            sections["SUMMARY"] = summary_part.strip()
            sections["COMPARISON"] = comparison_part.strip()
            return sections

        if "\nSPLIT_COMPARISON\n" in remaining:
            summary_part, split_part = remaining.split("\nSPLIT_COMPARISON\n", 1)
            sections["SUMMARY"] = summary_part.strip()
            sections["SPLIT_COMPARISON"] = split_part.strip()
            return sections

        if "\nBY_SEASON\n" in remaining:
            summary_part, by_season_part = remaining.split("\nBY_SEASON\n", 1)
            sections["SUMMARY"] = summary_part.strip()
            sections["BY_SEASON"] = by_season_part.strip()
            return sections

        sections["SUMMARY"] = remaining.strip()
        return sections

    sections["TABLE"] = text
    return sections


def _format_number(value) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, int):
        return str(value)
    try:
        value = float(value)
    except Exception:
        return str(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _format_record(wins, losses) -> str:
    try:
        return f"{int(float(wins))}-{int(float(losses))}"
    except Exception:
        return f"{wins}-{losses}"


def _safe_get(row, key, default="NA"):
    return row[key] if key in row.index else default


def _detect_value_column(df: pd.DataFrame) -> str | None:
    priority = [
        "pts",
        "reb",
        "ast",
        "stl",
        "blk",
        "fg3m",
        "fg3a",
        "plus_minus",
        "pts_per_game",
        "reb_per_game",
        "ast_per_game",
        "minutes_per_game",
        "fg_pct",
        "fg3_pct",
        "ft_pct",
        "usage_rate",
        "usg_pct",
        "assist_percentage",
        "ast_pct",
        "rebound_percentage",
        "reb_pct",
        "ts_pct",
        "pie",
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
    ]
    for col in priority:
        if col in df.columns:
            return col

    excluded = {
        "rank",
        "season",
        "season_type",
        "game_id",
        "game_date",
        "player_id",
        "team_id",
        "games_played",
        "player_name",
        "team_name",
        "team_abbr",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
        "wl",
        "wins",
        "losses",
        "games",
    }
    candidates = [c for c in df.columns if c not in excluded]
    for col in candidates:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    return None


def _pretty_split_name(value: str) -> str:
    mapping = {
        "home_away": "Home vs Away",
        "wins_losses": "Wins vs Losses",
    }
    return mapping.get(str(value), str(value).replace("_", " ").title())


def _pretty_bucket_name(value: str) -> str:
    mapping = {
        "home": "Home",
        "away": "Away",
        "wins": "Wins",
        "losses": "Losses",
    }
    return mapping.get(str(value), str(value).replace("_", " ").title())


def _pretty_metric_label(value: str) -> str:
    mapping = {
        "minutes_avg": "MIN",
        "pts_avg": "PTS",
        "reb_avg": "REB",
        "ast_avg": "AST",
        "stl_avg": "STL",
        "blk_avg": "BLK",
        "fg3m_avg": "3PM",
        "tov_avg": "TOV",
        "plus_minus_avg": "+/-",
        "efg_pct_avg": "eFG%",
        "ts_pct_avg": "TS%",
        "usg_pct_avg": "USG%",
        "usg_pct": "USG%",
        "ast_pct_avg": "AST%",
        "ast_pct": "AST%",
        "reb_pct_avg": "REB%",
        "reb_pct": "REB%",
        "win_pct": "Win%",
        "games": "Games",
        "wins": "Wins",
        "losses": "Losses",
        "pts_sum": "PTS Total",
        "reb_sum": "REB Total",
        "ast_sum": "AST Total",
        "bucket": "Bucket",
        "metric": "Metric",
    }
    return mapping.get(str(value), str(value))


def _make_display_table(
    df: pd.DataFrame,
    rename_metric: bool = False,
    rename_columns: bool = False,
) -> pd.DataFrame:
    display = df.copy()

    if "bucket" in display.columns:
        display["bucket"] = display["bucket"].apply(_pretty_bucket_name)

    if rename_metric and "metric" in display.columns:
        display["metric"] = display["metric"].apply(_pretty_metric_label)

    if rename_columns:
        display = display.rename(
            columns={col: _pretty_metric_label(col) for col in display.columns}
        )

    for col in display.columns:
        if col not in {"Bucket", "bucket", "Metric", "metric"}:
            display[col] = display[col].apply(_format_number)

    return display


def _format_subject_header(name: str) -> list[str]:
    return [name, SECTION_RULE]


def _format_comparison(summary_df: pd.DataFrame, comparison_df: pd.DataFrame, query: str) -> str:
    lines: list[str] = [f'Query: "{query}"', ""]

    if len(summary_df) < 2:
        lines.append(summary_df.round(3).to_string(index=False))
        if comparison_df is not None and not comparison_df.empty:
            lines.append("")
            lines.append("Comparison")
            lines.append(SECTION_RULE)
            lines.append(comparison_df.round(3).to_string(index=False))
        return "\n".join(lines).strip()

    a = summary_df.iloc[0]
    b = summary_df.iloc[1]

    if "player_name" in summary_df.columns:
        name_a = _safe_get(a, "player_name", "Player A")
        name_b = _safe_get(b, "player_name", "Player B")
        metric_map = [
            ("MIN", "minutes_avg"),
            ("PTS", "pts_avg"),
            ("REB", "reb_avg"),
            ("AST", "ast_avg"),
            ("STL", "stl_avg"),
            ("BLK", "blk_avg"),
            ("3PM", "fg3m_avg"),
            ("eFG%", "efg_pct_avg"),
            ("TS%", "ts_pct_avg"),
            ("USG%", "usg_pct_avg"),
            ("AST%", "ast_pct_avg"),
            ("REB%", "reb_pct_avg"),
            ("+/-", "plus_minus_avg"),
        ]
    else:
        name_a = _safe_get(a, "team_name", "Team A")
        name_b = _safe_get(b, "team_name", "Team B")
        metric_map = [
            ("PTS", "pts_avg"),
            ("REB", "reb_avg"),
            ("AST", "ast_avg"),
            ("STL", "stl_avg"),
            ("BLK", "blk_avg"),
            ("3PM", "fg3m_avg"),
            ("TOV", "tov_avg"),
            ("eFG%", "efg_pct_avg"),
            ("TS%", "ts_pct_avg"),
            ("+/-", "plus_minus_avg"),
        ]

    lines.extend(_format_subject_header(f"{name_a} vs {name_b}"))
    lines.append(
        f"Games: {_format_number(_safe_get(a, 'games'))} vs {_format_number(_safe_get(b, 'games'))}"
    )
    lines.append(
        f"Record: {_format_record(_safe_get(a, 'wins', 0), _safe_get(a, 'losses', 0))} vs "
        f"{_format_record(_safe_get(b, 'wins', 0), _safe_get(b, 'losses', 0))}"
    )
    win_pct_a = _format_number(_safe_get(a, "win_pct"))
    win_pct_b = _format_number(_safe_get(b, "win_pct"))
    lines.append(f"Win%: {win_pct_a} vs {win_pct_b}")
    lines.append("")
    lines.append("Averages")
    lines.append(SECTION_RULE)
    for label, key in metric_map:
        if key in a.index and key in b.index:
            lines.append(f"{label:>4}: {_format_number(a[key])} vs {_format_number(b[key])}")

    if comparison_df is not None and not comparison_df.empty:
        display = _make_display_table(comparison_df, rename_metric=True, rename_columns=True)
        lines.append("")
        lines.append("Comparison Table")
        lines.append(SECTION_RULE)
        lines.append(display.to_string(index=False))

    return "\n".join(lines).strip()


def _format_split_summary(summary_df: pd.DataFrame, split_df: pd.DataFrame, query: str) -> str:
    lines: list[str] = [f'Query: "{query}"', ""]

    if summary_df is None or summary_df.empty or split_df is None or split_df.empty:
        return "\n".join(lines + ["No split data available"]).strip()

    meta = summary_df.iloc[0]

    if "player_name" in meta.index:
        subject = _safe_get(meta, "player_name")
        metric_map = [
            ("MIN", "minutes_avg"),
            ("PTS", "pts_avg"),
            ("REB", "reb_avg"),
            ("AST", "ast_avg"),
            ("STL", "stl_avg"),
            ("BLK", "blk_avg"),
            ("3PM", "fg3m_avg"),
            ("eFG%", "efg_pct_avg"),
            ("TS%", "ts_pct_avg"),
            ("USG%", "usg_pct_avg"),
            ("AST%", "ast_pct_avg"),
            ("REB%", "reb_pct_avg"),
            ("+/-", "plus_minus_avg"),
        ]
    else:
        subject = _safe_get(meta, "team_name")
        metric_map = [
            ("PTS", "pts_avg"),
            ("REB", "reb_avg"),
            ("AST", "ast_avg"),
            ("STL", "stl_avg"),
            ("BLK", "blk_avg"),
            ("3PM", "fg3m_avg"),
            ("TOV", "tov_avg"),
            ("eFG%", "efg_pct_avg"),
            ("TS%", "ts_pct_avg"),
            ("+/-", "plus_minus_avg"),
        ]

    split_name = _pretty_split_name(_safe_get(meta, "split"))
    games_total = _format_number(_safe_get(meta, "games_total"))
    season_start = _safe_get(meta, "season_start")
    season_end = _safe_get(meta, "season_end")
    season_type = _safe_get(meta, "season_type")

    lines.extend(_format_subject_header(subject))
    lines.append(f"Span: {season_start} to {season_end} ({season_type})")
    lines.append(f"Split: {split_name}")
    lines.append(f"Games: {games_total}")
    lines.append("")

    if len(split_df) >= 2:
        a = split_df.iloc[0]
        b = split_df.iloc[1]
        bucket_a = _pretty_bucket_name(_safe_get(a, "bucket", "bucket_a"))
        bucket_b = _pretty_bucket_name(_safe_get(b, "bucket", "bucket_b"))

        lines.extend(_format_subject_header(f"{bucket_a} vs {bucket_b}"))
        games_a = _format_number(_safe_get(a, "games"))
        games_b = _format_number(_safe_get(b, "games"))
        lines.append(f"Games: {games_a} vs {games_b}")
        lines.append(
            f"Record: {_format_record(_safe_get(a, 'wins', 0), _safe_get(a, 'losses', 0))} vs "
            f"{_format_record(_safe_get(b, 'wins', 0), _safe_get(b, 'losses', 0))}"
        )
        win_pct_a = _format_number(_safe_get(a, "win_pct"))
        win_pct_b = _format_number(_safe_get(b, "win_pct"))
        lines.append(f"Win%: {win_pct_a} vs {win_pct_b}")
        lines.append("")
        lines.append("Averages")
        lines.append(SECTION_RULE)
        for label, key in metric_map:
            if key in a.index and key in b.index:
                lines.append(f"{label:>4}: {_format_number(a[key])} vs {_format_number(b[key])}")
    else:
        only = split_df.iloc[0]
        bucket = _pretty_bucket_name(_safe_get(only, "bucket"))
        lines.extend(_format_subject_header(bucket))
        lines.append(f"Games: {_format_number(_safe_get(only, 'games'))}")
        lines.append(
            f"Record: {_format_record(_safe_get(only, 'wins', 0), _safe_get(only, 'losses', 0))}"
        )
        lines.append(f"Win%: {_format_number(_safe_get(only, 'win_pct'))}")
        lines.append("")
        lines.append("Averages")
        lines.append(SECTION_RULE)
        for label, key in metric_map:
            if key in only.index:
                lines.append(f"{label:>4}: {_format_number(only[key])}")

    display = _make_display_table(split_df, rename_columns=True)

    lines.append("")
    lines.append("Split Table")
    lines.append(SECTION_RULE)
    lines.append(display.to_string(index=False))

    return "\n".join(lines).strip()


def format_pretty_output(raw_text: str, query: str) -> str:
    sections = _extract_sections(raw_text)

    if "SUMMARY" in sections:
        summary_df = _read_csv_block(sections["SUMMARY"])
        by_season_df = _read_csv_block(sections.get("BY_SEASON", ""))
        comparison_df = _read_csv_block(sections.get("COMPARISON", ""))
        split_df = _read_csv_block(sections.get("SPLIT_COMPARISON", ""))

        if summary_df is None:
            return raw_text.strip()

        if comparison_df is not None:
            return _format_comparison(summary_df, comparison_df, query)

        if split_df is not None:
            return _format_split_summary(summary_df, split_df, query)

        row = summary_df.iloc[0]
        lines: list[str] = [f'Query: "{query}"', ""]

        if "player_name" in row.index:
            lines.extend(_format_subject_header(f"{_safe_get(row, 'player_name')}"))
            lines.append(
                f"Span: {_safe_get(row, 'season_start')} to {_safe_get(row, 'season_end')} "
                f"({_safe_get(row, 'season_type')})"
            )
            lines.append(f"Games: {_format_number(_safe_get(row, 'games'))}")
            lines.append(
                f"Record: {_format_record(_safe_get(row, 'wins', 0), _safe_get(row, 'losses', 0))}"
            )
            lines.append(f"Win%: {_format_number(_safe_get(row, 'win_pct'))}")

            stat_bits = []
            for label, key in [
                ("PTS", "pts_avg"),
                ("REB", "reb_avg"),
                ("AST", "ast_avg"),
                ("MIN", "minutes_avg"),
                ("STL", "stl_avg"),
                ("BLK", "blk_avg"),
                ("eFG%", "efg_pct_avg"),
                ("TS%", "ts_pct_avg"),
                ("USG%", "usg_pct_avg"),
                ("AST%", "ast_pct_avg"),
                ("REB%", "reb_pct_avg"),
            ]:
                if key in row.index:
                    stat_bits.append(f"{label} {_format_number(row[key])}")
            if stat_bits:
                lines.append("")
                lines.append("Averages")
                lines.append(SECTION_RULE)
                lines.append(" | ".join(stat_bits))

        elif "team_name" in row.index:
            lines.extend(_format_subject_header(f"{_safe_get(row, 'team_name')}"))
            lines.append(
                f"Span: {_safe_get(row, 'season_start')} to {_safe_get(row, 'season_end')} "
                f"({_safe_get(row, 'season_type')})"
            )
            lines.append(f"Games: {_format_number(_safe_get(row, 'games'))}")
            lines.append(
                f"Record: {_format_record(_safe_get(row, 'wins', 0), _safe_get(row, 'losses', 0))}"
            )
            lines.append(f"Win%: {_format_number(_safe_get(row, 'win_pct'))}")

            stat_bits = []
            for label, key in [
                ("PTS", "pts_avg"),
                ("REB", "reb_avg"),
                ("AST", "ast_avg"),
                ("3PM", "fg3m_avg"),
                ("TOV", "tov_avg"),
                ("eFG%", "efg_pct_avg"),
                ("TS%", "ts_pct_avg"),
                ("+/-", "plus_minus_avg"),
            ]:
                if key in row.index:
                    stat_bits.append(f"{label} {_format_number(row[key])}")
            if stat_bits:
                lines.append("")
                lines.append("Averages")
                lines.append(SECTION_RULE)
                lines.append(" | ".join(stat_bits))

        else:
            lines.append("Summary")
            lines.append(SECTION_RULE)
            lines.append(summary_df.round(3).to_string(index=False))

        if by_season_df is not None and not by_season_df.empty:
            display_cols = [
                c
                for c in by_season_df.columns
                if c
                in {
                    "season",
                    "games",
                    "wins",
                    "losses",
                    "pts_avg",
                    "reb_avg",
                    "ast_avg",
                    "minutes_avg",
                    "fg3m_avg",
                    "tov_avg",
                    "plus_minus_avg",
                    "efg_pct_avg",
                    "ts_pct_avg",
                    "usg_pct_avg",
                    "ast_pct_avg",
                    "reb_pct_avg",
                }
            ]
            shown = (
                by_season_df[display_cols].copy().round(3)
                if display_cols
                else by_season_df.round(3)
            )
            lines.append("")
            lines.append("By Season")
            lines.append(SECTION_RULE)
            lines.append(shown.to_string(index=False))

        return "\n".join(lines).strip()

    table_df = _read_csv_block(sections.get("TABLE", ""))
    if table_df is None:
        return raw_text.strip()

    lines: list[str] = [f'Query: "{query}"', ""]

    if "rank" in table_df.columns:
        lines.append(f"Rows returned: {len(table_df)}")
        lines.append(SECTION_RULE)
        preview = table_df.copy().round(3)

        value_col = _detect_value_column(preview)

        preferred_cols = [
            "rank",
            "season",
            "season_type",
            "game_date",
            "player_name",
            "team_name",
            "team_abbr",
            "opponent_team_abbr",
        ]

        if value_col and value_col not in preferred_cols:
            preferred_cols.append(value_col)

        for extra in ["pts", "reb", "ast", "fg3m", "wl"]:
            if extra != value_col and extra in preview.columns:
                preferred_cols.append(extra)

        cols = [c for c in preferred_cols if c in preview.columns]
        if not cols:
            cols = list(preview.columns[:10])

        lines.append(preview[cols].to_string(index=False))
        return "\n".join(lines).strip()

    lines.append(table_df.round(3).to_string(index=False))
    return "\n".join(lines).strip()
