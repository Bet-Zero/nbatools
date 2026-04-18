"""Shared date parsing helpers for natural-query season and range handling."""

from __future__ import annotations

import re
from calendar import monthcalendar, monthrange
from zoneinfo import ZoneInfo

import pandas as pd

MONTH_NAME_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

CURRENT_QUERY_DATE = pd.Timestamp.now(tz=ZoneInfo("America/Detroit")).floor("D").tz_localize(None)

ALL_STAR_BREAK_START_OVERRIDES = {
    "2022-23": "2023-02-20",
    "2023-24": "2024-02-19",
    "2024-25": "2025-02-17",
    "2025-26": "2026-02-16",
}


def _infer_all_star_break_start(season: str | None) -> str | None:
    if season in ALL_STAR_BREAK_START_OVERRIDES:
        return ALL_STAR_BREAK_START_OVERRIDES[season]

    if season and re.match(r"^(?:19|20)\d{2}-\d{2}$", season):
        end_year = int(season.split("-")[0]) + 1
    else:
        end_year = (
            CURRENT_QUERY_DATE.year if CURRENT_QUERY_DATE.month < 7 else CURRENT_QUERY_DATE.year + 1
        )

    cal = monthcalendar(end_year, 2)
    sundays = [week[6] for week in cal if week[6] != 0]
    if len(sundays) < 3:
        return None

    third_sunday = sundays[2]
    start_ts = pd.Timestamp(year=end_year, month=2, day=third_sunday) + pd.Timedelta(days=1)
    return start_ts.date().isoformat()


def _resolve_year_for_month_in_season(season: str | None, month_num: int) -> int:
    if season and re.match(r"^(?:19|20)\d{2}-\d{2}$", season):
        start_year = int(season.split("-")[0])
        return start_year if month_num >= 10 else start_year + 1

    current_year = int(CURRENT_QUERY_DATE.year)
    current_month = int(CURRENT_QUERY_DATE.month)
    return current_year if month_num <= current_month else current_year - 1


def extract_date_range(text: str, season: str | None) -> tuple[str | None, str | None]:
    if re.search(r"\b(?:since|after|post)\s+(?:the\s+)?all[- ]star\s+break\b", text):
        return _infer_all_star_break_start(season), None

    # --- Fuzzy time words (spec §18.1) ---

    # `last night` / `yesterday` → yesterday's date
    if re.search(r"\b(?:last\s+night|yesterday)\b", text):
        d = (CURRENT_QUERY_DATE - pd.Timedelta(days=1)).date().isoformat()
        return d, d

    # `today` / `tonight` → today's date
    if re.search(r"\b(?:today|tonight)\b", text):
        d = CURRENT_QUERY_DATE.date().isoformat()
        return d, d

    # `past month` / `last month` → rolling 30 days
    if re.search(r"\b(?:past|last)\s+month\b", text):
        start = (CURRENT_QUERY_DATE - pd.Timedelta(days=29)).date().isoformat()
        end = CURRENT_QUERY_DATE.date().isoformat()
        return start, end

    # `last couple weeks` / `past 2 weeks` / `past few weeks` → rolling 14 days
    if re.search(r"\b(?:past|last)\s+(?:couple|couple\s+of|few|2)\s+weeks?\b", text):
        start = (CURRENT_QUERY_DATE - pd.Timedelta(days=13)).date().isoformat()
        end = CURRENT_QUERY_DATE.date().isoformat()
        return start, end

    m = re.search(r"\blast\s+(\d+)\s+days?\b", text)
    if m:
        days = int(m.group(1))
        if days > 0:
            start = (CURRENT_QUERY_DATE - pd.Timedelta(days=days - 1)).date().isoformat()
            end = CURRENT_QUERY_DATE.date().isoformat()
            return start, end

    month_pattern = "|".join(MONTH_NAME_TO_NUM.keys())

    m = re.search(rf"\bsince\s+({month_pattern})\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = _resolve_year_for_month_in_season(season, month_num)
        start = f"{year}-{month_num:02d}-01"
        return start, None

    m = re.search(rf"\b(?:in|during)\s+({month_pattern})\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = _resolve_year_for_month_in_season(season, month_num)
        last_day = monthrange(year, month_num)[1]
        start = f"{year}-{month_num:02d}-01"
        end = f"{year}-{month_num:02d}-{last_day:02d}"
        return start, end

    return None, None
