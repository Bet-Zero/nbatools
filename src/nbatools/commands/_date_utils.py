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
        rf"\b(?:(?:from\s+)?({token})\s+(?:to|through|thru|until|till)"
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
    # "from March 2025 to January": one named year, the other month rolled
    # forward; both ends name their seasons.
    span = _month_only_range(text, None)
    if seasons and span is not None and all(span):
        for day in span:
            seasons.append(_season_for_date(int(day[:4]), int(day[5:7])))
    if not seasons:
        return None, None
    return min(seasons), max(seasons)


_SEASON_SPAN_TO_TODAY = re.compile(
    r"\b(?:from|since|starting|in|for|during)\s+(?:the\s+)?(?:19|20)\d{2}(?:-\d{2})?(?:\s+(?:nba\s+)?season)?"
    r"\s+(?:up\s+to|to|through|thru|until|till|til)\s+(?:today|tonight)\b"
)


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


# "from January to March", "between Nov and Jan", "January through March",
# "Jan-Mar", "January to March 2025": whole months, years from the season
# (or the one year named). Day forms ("March 1 to March 31") read first.
_Y = r"(?:\s+((?:19|20)\d{2})(?!-\d))?"
_MONTH_ONLY_RANGE = re.compile(
    rf"(?:\bbetween\s+{_MONTH_WORDS}{_Y}\s+(?:and|to|through|thru|-)"
    rf"|(?:\bfrom\s+|\b){_MONTH_WORDS}{_Y}\s*(?:to|through|thru|-))"
    rf"\s*{_MONTH_WORDS}{_Y}\b(?!\s*\d)"
)
# "in the month of March" is "in March", as are "for / over the month of".
_MONTH_OF = r"(?:the\s+months?\s+of\s+)?"
_IN_MONTH = rf"\b(?:(?:in|during)\s+{_MONTH_OF}|(?:for|over)\s+the\s+months?\s+of\s+)"
# "in January and February": both months; adjacent months are one span.
_MONTH_SEP = r"(?:\s*,\s*(?:and\s+|&\s+)?|\s+(?:and|&)\s+)"
_MONTH_PAIR = re.compile(
    rf"{_IN_MONTH}{_MONTH_WORDS}(?:{_MONTH_SEP}{_MONTH_WORDS})+"
    r"(?:\s+((?:19|20)\d{2})(?!-\d))?\b(?!\s*\d)"
)
_MONTH_WORD_RE = re.compile(_MONTH_WORDS)
# Full month names, or an abbreviation that ends the clause ("after Jan
# Vesely left" is not January).
_FULL_MONTHS = (
    r"(january|february|march|april|may|june|july|august|september|october|november|december"
    r"|(?:jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)(?=\s*(?:$|[,.?!]|(?:19|20)\d{2}\b|"
    r"(?:in|this|last|since|for|vs|against|at|and|or|of)\b)))"
)
_MONTH_BEFORE_AFTER = re.compile(
    rf"\b(?P<word>before|after|through|thru)\s+{_FULL_MONTHS}{_Y}\b(?!\s*\d)"
)


def _year_for(month: int, season: str | None, year: str | None) -> int:
    return int(year) if year else _resolve_year_for_month_in_season(season, month)


def _month_span(
    first: int, first_year: str | None, last: int, last_year: str | None, season: str | None
) -> tuple[str, str] | None:
    if first_year and not last_year:
        start_year = int(first_year)
        end_year = start_year if last >= first else start_year + 1
    elif last_year and not first_year:
        end_year = int(last_year)
        start_year = end_year if first <= last else end_year - 1
    else:
        start_year = _year_for(first, season, first_year)
        end_year = _year_for(last, season, last_year)
    if (end_year, last) < (start_year, first):
        return None
    end_day = monthrange(end_year, last)[1]
    return f"{start_year}-{first:02d}-01", f"{end_year}-{last:02d}-{end_day:02d}"


def _month_only_range(text: str, season: str | None) -> tuple[str | None, str | None] | None:
    m = _MONTH_ONLY_RANGE.search(text)
    if m:
        first_word = m.group(1) or m.group(3)
        first_year = m.group(2) if m.group(1) else m.group(4)
        first, last = _month_num(first_word), _month_num(m.group(5))
        if first is not None and last is not None:
            return _month_span(first, first_year, last, m.group(6), season)
    months = _paired_months(text)
    if months is not None:
        nums, year = months
        if _consecutive(nums):
            return _month_span(nums[0], None, nums[-1], year, season)
    m = _MONTH_BEFORE_AFTER.search(text)
    if m:
        month = _month_num(m.group(2))
        if month is None:
            return None
        year = _year_for(month, season, m.group(3))
        first_day = pd.Timestamp(year=year, month=month, day=1)
        last_day = first_day + pd.offsets.MonthEnd(0)
        word = m.group("word")
        if word == "before":
            return None, (first_day - pd.Timedelta(days=1)).date().isoformat()
        if word == "after":
            return (last_day + pd.Timedelta(days=1)).date().isoformat(), None
        return None, last_day.date().isoformat()
    return None


def _paired_months(text: str) -> tuple[list[int], str | None] | None:
    """ "in January and February (2025)", "in January, February and March":
    the months named and a year closing the list."""
    m = _MONTH_PAIR.search(text)
    if not m:
        return None
    words = _MONTH_WORD_RE.findall(m.group(0))
    nums = [_month_num(w) for w in words]
    if any(n is None for n in nums):
        return None
    year = re.search(r"((?:19|20)\d{2})\s*$", m.group(0))
    return nums, year.group(1) if year else None


def _consecutive(nums: list[int]) -> bool:
    return all(b == a % 12 + 1 for a, b in zip(nums, nums[1:], strict=False))


# "between January and March 2024 and 2025": a range in two seasons, which
# one window does not answer.
_SEASON_WORD = r"(?:(?:19|20)\d{2}(?:-\d{2})?\b|(?:this|last|next)\s+season\b)"
_SECOND_YEAR = re.compile(
    # ", last season" alone names the one season; a joined second one is two.
    rf"(?:\s*,?\s*{_SEASON_WORD})?\s*,?\s*(?:and|&|or)\s+(?:the\s+)?{_SEASON_WORD}"
)
_TWO_SEASONS = re.compile(rf"{_SEASON_WORD}\s*,?\s*(?:and|&|or)\s+(?:the\s+)?{_SEASON_WORD}")


# "in March vs April", "in March or April": two months to compare or choose
# between, not one window (it read March alone).
_MONTH_VERSUS = re.compile(
    rf"{_IN_MONTH}{_MONTH_WORDS}{_Y}\s*,?\s+"
    rf"(?:vs\.?|versus|compared\s+(?:to|with)|against|or)\s+(?:(?:in|during)\s+)?"
    rf"{_MONTH_OF}{_FULL_MONTHS}\b"
)
# Calendar landmarks the date reader does not place ("after Christmas",
# "before the All-Star break", "since the trade deadline"): it read the
# whole season. "since / after the All-Star break" is read.
# The spelling matches extract_date_range's ("allstar break" is not read).
_READ_LANDMARK = re.compile(
    r"\b(?:since|after|post)\s+(?:the\s+)?all[- ]star\s+break\b"
    r"|\b(?:dionte|rakeem)\s+christmas\b"
)
_DATE_LANDMARK = re.compile(
    r"\b(?:christmas|thanksgiving|new\s+years?|new\s+year'?s|mlk|martin\s+luther\s+king|"
    r"trade\s+deadline|all[-\s]?star\s+break)\b"
)


def unread_date_landmark(text: str, names: tuple[str | None, ...] = ()) -> str | None:
    """The landmark a query names that no date window reads; a resolved
    player's own name ("Rakeem Christmas") is not one."""
    text = _READ_LANDMARK.sub(" ", text)
    for name in names:
        if name:
            text = text.replace(name.lower(), " ")
    m = _DATE_LANDMARK.search(text)
    return m.group(0) if m else None


def unread_month_pair(text: str, season: str | None = None) -> str | None:
    """ "in January and March": months that are not one span, "from March to
    January" within one season, or a range named for two seasons: no single
    window answers it (it read January alone, or the whole season)."""
    versus = _MONTH_VERSUS.search(text)
    if versus:
        return versus.group(0).strip()
    months = _paired_months(text)
    if months is not None and not _consecutive(months[0]):
        return _MONTH_PAIR.search(text).group(0).strip()
    m = _MONTH_ONLY_RANGE.search(text)
    if m and (_SECOND_YEAR.match(text, m.end()) or _TWO_SEASONS.search(text)):
        # "from January to March this season and last season".
        return m.group(0).strip()
    if m and _MONTH_YEAR_RANGE.search(text) is None:
        first_word = m.group(1) or m.group(3)
        first_year = m.group(2) if m.group(1) else m.group(4)
        first, last = _month_num(first_word), _month_num(m.group(5))
        if (
            first is not None
            and last is not None
            and _month_span(first, first_year, last, m.group(6), season) is None
        ):
            return m.group(0).strip()
    return None


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
            if _SEASON_SPAN_TO_TODAY.search(text):
                # "from 2019 to today": the season span runs to the latest season.
                continue
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

    month_only = _month_only_range(text, season)
    if month_only is not None:
        return month_only

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

    m = re.search(rf"{_IN_MONTH}({month_pattern})(?:\s+((?:19|20)\d{{2}}))?\b", text)
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
