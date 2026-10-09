"""Shared date parsing helpers for natural-query season and range handling."""

from __future__ import annotations

import re
from calendar import monthcalendar, monthrange
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from nbatools.commands._glossary import FUZZY_DATE_TERMS

MONTH_NAME_TO_NUM = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
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


def _month_name_pattern() -> str:
    return "|".join(sorted(MONTH_NAME_TO_NUM.keys(), key=len, reverse=True))


def has_explicit_calendar_date(text: str) -> bool:
    """Return True for month-day calendar dates such as ``January 1 2026``."""
    month_pattern = _month_name_pattern()
    return bool(
        re.search(
            rf"\b(?:on\s+)?(?:{month_pattern})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?"
            rf"(?:,?\s+(?:19|20)\d{{2}})?\b",
            text,
        )
    )


def _extract_explicit_calendar_date(
    text: str,
    season: str | None,
) -> tuple[str | None, str | None]:
    month_pattern = _month_name_pattern()
    m = re.search(
        rf"\b(?:on\s+)?({month_pattern})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?"
        rf"(?:,?\s+((?:19|20)\d{{2}}))?\b",
        text,
    )
    if not m:
        return None, None

    month_num = MONTH_NAME_TO_NUM[m.group(1)]
    day = int(m.group(2))
    year = int(m.group(3)) if m.group(3) else _resolve_year_for_month_in_season(season, month_num)

    last_day = monthrange(year, month_num)[1]
    if day < 1 or day > last_day:
        return None, None

    value = f"{year}-{month_num:02d}-{day:02d}"
    return value, value


def _extract_since_explicit_calendar_date(
    text: str,
    season: str | None,
    anchor_date: pd.Timestamp,
) -> tuple[str | None, str | None]:
    month_pattern = _month_name_pattern()
    m = re.search(
        rf"\b(?:since|after|post)\s+({month_pattern})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?"
        rf"(?:,?\s+((?:19|20)\d{{2}}))?\b",
        text,
    )
    if not m:
        return None, None

    month_num = MONTH_NAME_TO_NUM[m.group(1)]
    day = int(m.group(2))
    year = int(m.group(3)) if m.group(3) else _resolve_year_for_month_in_season(season, month_num)

    last_day = monthrange(year, month_num)[1]
    if day < 1 or day > last_day:
        return None, None

    start = f"{year}-{month_num:02d}-{day:02d}"
    end = anchor_date.date().isoformat()
    return start, end


_ISO_DATE = r"(?:19|20)\d{2}-\d{2}-\d{2}"


def _date_token_pattern() -> str:
    """One explicit calendar date: ISO ``2025-11-01`` or ``November 1[, 2025]``."""
    month_pattern = _month_name_pattern()
    return (
        rf"(?:{_ISO_DATE}"
        rf"|(?:{month_pattern})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+(?:19|20)\d{{2}})?)"
    )


def _parse_date_token(token: str, season: str | None) -> str | None:
    """Return the ISO date a ``_date_token_pattern`` match names, or None if invalid."""
    token = token.strip()
    if re.fullmatch(_ISO_DATE, token):
        try:
            return date.fromisoformat(token).isoformat()
        except ValueError:
            return None
    m = re.fullmatch(
        rf"({_month_name_pattern()})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+((?:19|20)\d{{2}}))?",
        token,
    )
    if not m:
        return None
    month_num = MONTH_NAME_TO_NUM[m.group(1)]
    year = int(m.group(3)) if m.group(3) else _resolve_year_for_month_in_season(season, month_num)
    try:
        return date(year, month_num, int(m.group(2))).isoformat()
    except ValueError:
        return None


def _extract_explicit_date_range(
    text: str,
    season: str | None,
    anchor_date: pd.Timestamp,
) -> tuple[str | None, str | None]:
    """Explicit two-ended ranges, ``since <date>`` and lone ISO dates.

    "from November 1 to December 15" must bound both ends; the single-date
    matcher alone read it as November 1 only.
    """
    token = _date_token_pattern()
    m = re.search(
        rf"\b(?:from\s+({token})\s+(?:to|through|thru|until|till)"
        rf"|between\s+({token})\s+and)\s+({token})(?!\d)",
        text,
    )
    if m:
        start = _parse_date_token(m.group(1) or m.group(2), season)
        end = _parse_date_token(m.group(3), season)
        if start and end:
            return start, end
        return None, None

    m = re.search(rf"\b(?:since|after|post)\s+({token})(?!\d)", text)
    if m and (re.fullmatch(_ISO_DATE, m.group(1)) or re.search(r"\d{4}$", m.group(1))):
        start = _parse_date_token(m.group(1), season)
        return (start, anchor_date.date().isoformat()) if start else (None, None)

    # An open start: "before" excludes the named day, "until"/"through" keep it.
    # Without these the lone-date fallbacks answered about that single day.
    m = re.search(rf"\b(before|prior\s+to|until|till|through|thru|up\s+to)\s+({token})(?!\d)", text)
    if m:
        end = _parse_date_token(m.group(2), season)
        if end is None:
            return None, None
        if m.group(1) == "before" or m.group(1).startswith("prior"):
            end = (date.fromisoformat(end) - timedelta(days=1)).isoformat()
        return None, end

    m = re.search(rf"\b({_ISO_DATE})\b", text)
    if m:
        value = _parse_date_token(m.group(1), season)
        return value, value

    return None, None


def _season_for_date(year: int, month_num: int) -> str:
    # NBA seasons span two calendar years: October onward opens the season
    # named for that year, January-September closes the previous one.
    start_year = year if month_num >= 10 else year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def seasons_for_explicit_dates(text: str) -> tuple[str | None, str | None]:
    """Return the first and last NBA seasons named by year-bearing dates.

    Covers ISO dates and ``<month> [day] <year>`` phrases. Callers pin the
    season (or a season span, when the dates cross a season boundary) from
    these so the date window is not applied to a default season it misses.
    """
    month_pattern = _month_name_pattern()
    seasons: list[str] = []
    for m in re.finditer(
        rf"\b(?:((?:19|20)\d{{2}})-(\d{{2}})-\d{{2}}"
        rf"|({month_pattern})\.?(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?,?\s+((?:19|20)\d{{2}}))\b",
        text,
    ):
        if m.group(1):
            month_num = int(m.group(2))
            if not 1 <= month_num <= 12:
                continue
            seasons.append(_season_for_date(int(m.group(1)), month_num))
        else:
            seasons.append(_season_for_date(int(m.group(4)), MONTH_NAME_TO_NUM[m.group(3)]))
    if not seasons:
        return None, None
    return min(seasons), max(seasons)


def explicit_date_is_open_ended(text: str) -> bool:
    """True when a year-bearing date opens a window that runs to today.

    "since 2025-03-01" or "since March 2025" must load every season from that
    date's season to the latest one, not only the season the date falls in.
    """
    month_pattern = _month_name_pattern()
    return bool(
        re.search(
            rf"\b(?:since|after|post)\s+(?:(?:19|20)\d{{2}}-\d{{2}}-\d{{2}}"
            rf"|(?:{month_pattern})\.?\s+(?:\d{{1,2}}(?:st|nd|rd|th)?,?\s+)?(?:19|20)\d{{2}})\b",
            text,
        )
    )


def invalid_explicit_date(text: str) -> str | None:
    """Return a named calendar date that does not exist, such as "2025-02-30".

    An impossible date must not silently fall back to the whole season.
    """
    for m in re.finditer(rf"\b({_ISO_DATE})\b", text):
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            return m.group(1)
    month_pattern = _month_name_pattern()
    for m in re.finditer(
        rf"\b({month_pattern})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+((?:19|20)\d{{2}}))?\b",
        text,
    ):
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        # Without a year, judge against a leap year so "February 29" stands.
        year = int(m.group(3)) if m.group(3) else 2024
        if not 1 <= int(m.group(2)) <= monthrange(year, month_num)[1]:
            return m.group(0).strip()
    return None


def uses_fuzzy_date_term(text: str) -> bool:
    """True when the text uses a day-anchored fuzzy window (yesterday,
    last night, today, this week, last N days). Empty results for these
    need a data-currency explanation."""
    if any(re.search(term.regex, text) for term in FUZZY_DATE_TERMS):
        return True
    return bool(re.search(r"\blast\s+\d+\s+days?\b", text))


# "Jan. 2025", "January, 2025": the year belongs to the month (they were read
# as the month in the current season: 2026-01-01 for "since Jan. 2025").
_MONTH_PUNCT_YEAR = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|"
    r"december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)(?:\.\s*,?|\s*,)\s*((?:19|20)\d{2})\b(?!-\d)"
)


_MONTH_WORDS = (
    r"(january|february|march|april|may|june|july|august|september|october|november|"
    r"december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)"
)
# "from January 2024 to March 2025", "Jan 2025 - Mar 2025", "between January
# 2025 and March 2026". "March 2024 and March 2025" (no "between") is two
# months, not a span.
_MONTH_YEAR_RANGE = re.compile(
    rf"(?:\bbetween\s+(?<![\d-]){_MONTH_WORDS}\s+((?:19|20)\d{{2}})(?!-\d)\s*"
    r"(?:and|to|through|thru|until|-)"
    rf"|(?:\bfrom\s+|\b)(?<![\d-]){_MONTH_WORDS}\s+((?:19|20)\d{{2}})(?!-\d)\s*"
    r"(?:to|through|thru|until|-))"
    rf"\s*{_MONTH_WORDS}\s+((?:19|20)\d{{2}})\b(?!-\d)"
)


def _month_num(word: str) -> int | None:
    for name, num in MONTH_NAME_TO_NUM.items():
        if name.startswith(word[:3]):
            return num
    return None


def _month_year_range(text: str) -> tuple[str, str] | None:
    """ "from January 2024 to March 2025": the first day of the first month to
    the last day of the last (the dates were dropped)."""
    m = _MONTH_YEAR_RANGE.search(text)
    if not m:
        return None
    first_word, first_year = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    first, last = _month_num(first_word), _month_num(m.group(5))
    if first is None or last is None:
        return None
    start_year, end_year = int(first_year), int(m.group(6))
    if (end_year, last) < (start_year, first):
        return None
    end_day = monthrange(end_year, last)[1]
    return f"{start_year}-{first:02d}-01", f"{end_year}-{last:02d}-{end_day:02d}"


def extract_date_range(
    text: str,
    season: str | None,
    anchor_date: pd.Timestamp | None = None,
) -> tuple[str | None, str | None]:
    text = _MONTH_PUNCT_YEAR.sub(r"\1 \2", text)
    month_range = _month_year_range(text)
    if month_range is not None:
        return month_range
    if re.search(r"\b(?:since|after|post)\s+(?:the\s+)?all[- ]star\s+break\b", text):
        return _infer_all_star_break_start(season), None

    anchor = anchor_date if anchor_date is not None else CURRENT_QUERY_DATE

    # --- Fuzzy time words (glossary / spec §18.1) ---
    for term in FUZZY_DATE_TERMS:
        if not re.search(term.regex, text):
            continue
        if term.yesterday:
            d = (anchor - pd.Timedelta(days=1)).date().isoformat()
            return d, d
        if term.same_day:
            d = anchor.date().isoformat()
            return d, d
        if term.days_back is not None:
            start = (anchor - pd.Timedelta(days=term.days_back - 1)).date().isoformat()
            end = anchor.date().isoformat()
            return start, end

    m = re.search(r"\blast\s+(\d+)\s+days?\b", text)
    if m:
        days = int(m.group(1))
        if days > 0:
            start = (anchor - pd.Timedelta(days=days - 1)).date().isoformat()
            end = anchor.date().isoformat()
            return start, end

    month_pattern = "|".join(MONTH_NAME_TO_NUM.keys())

    range_start, range_end = _extract_explicit_date_range(text, season, anchor)
    if range_start or range_end:
        return range_start, range_end

    since_explicit_start, since_explicit_end = _extract_since_explicit_calendar_date(
        text,
        season,
        anchor,
    )
    if since_explicit_start or since_explicit_end:
        return since_explicit_start, since_explicit_end

    explicit_start, explicit_end = _extract_explicit_calendar_date(text, season)
    if explicit_start or explicit_end:
        return explicit_start, explicit_end

    # The optional trailing year mirrors the month-day forms above. Without it
    # "in January 2024" matched only "in january" and the year was dropped on
    # the floor, silently answering about the current season instead.
    m = re.search(rf"\bsince\s+({month_pattern})(?:\s+((?:19|20)\d{{2}}))?\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = (
            int(m.group(2)) if m.group(2) else _resolve_year_for_month_in_season(season, month_num)
        )
        start = f"{year}-{month_num:02d}-01"
        return start, None

    m = re.search(rf"\b(?:in|during)\s+({month_pattern})(?:\s+((?:19|20)\d{{2}}))?\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = (
            int(m.group(2)) if m.group(2) else _resolve_year_for_month_in_season(season, month_num)
        )
        last_day = monthrange(year, month_num)[1]
        start = f"{year}-{month_num:02d}-01"
        end = f"{year}-{month_num:02d}-{last_day:02d}"
        return start, end

    return None, None
