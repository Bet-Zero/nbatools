"""Tests for fuzzy-time phrases: last couple weeks / past 2 weeks (Phase B item 12).

Verifies that rolling 14-day window phrases resolve correctly through the
glossary and date-extraction pipeline, including data-aware anchoring.
"""

import re

import pandas as pd
import pytest

from nbatools.commands._date_utils import extract_date_range
from nbatools.commands._glossary import FUZZY_DATE_TERMS
from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.parser


class TestGlossaryRegexMatches:
    """The glossary regex must match all documented surface forms."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "last couple weeks",
            "past 2 weeks",
            "last couple of weeks",
            "past few weeks",
            "last few weeks",
        ],
    )
    def test_fuzzy_weeks_phrases_match(self, phrase: str):
        matched = False
        for term in FUZZY_DATE_TERMS:
            if re.search(term.regex, phrase):
                assert term.days_back == 14
                matched = True
                break
        assert matched, f"No glossary regex matched: {phrase!r}"


class TestExtractDateRangeWeeks:
    """extract_date_range should produce a 14-day window for week phrases."""

    @pytest.mark.parametrize(
        "phrase",
        [
            "jokic last couple weeks",
            "jokic past 2 weeks",
            "jokic last few weeks",
        ],
    )
    def test_returns_14_day_window(self, phrase: str):
        start, end = extract_date_range(phrase, None)
        assert start is not None
        assert end is not None
        start_dt = pd.Timestamp(start)
        end_dt = pd.Timestamp(end)
        delta = (end_dt - start_dt).days
        assert delta == 13, f"Expected 13-day span (14 days inclusive), got {delta}"

    def test_anchor_date_shifts_window(self):
        """When anchor_date is provided, the window should be relative to it."""
        anchor = pd.Timestamp("2026-04-04")
        start, end = extract_date_range("jokic last couple weeks", None, anchor_date=anchor)
        assert end == "2026-04-04"
        assert start == "2026-03-22"


class TestParseQueryWeeksPhrases:
    """parse_query should wire week phrases through to start_date/end_date."""

    @pytest.mark.parametrize(
        "query",
        [
            "Jokic last couple weeks",
            "Jokic past 2 weeks",
        ],
    )
    def test_produces_date_range(self, query: str):
        state = parse_query(query)
        assert state["start_date"] is not None
        assert state["end_date"] is not None

    def test_couple_weeks_and_2_weeks_equivalent(self):
        state_a = parse_query("Jokic last couple weeks")
        state_b = parse_query("Jokic past 2 weeks")
        assert state_a["start_date"] == state_b["start_date"]
        assert state_a["end_date"] == state_b["end_date"]


class TestNoRegressionExistingFuzzyTime:
    """Existing fuzzy-time forms must continue to work."""

    def test_lately_still_uses_last_n(self):
        state = parse_query("Jokic lately")
        assert state["last_n"] == 10
        assert state["start_date"] is None

    def test_recently_still_uses_last_n(self):
        state = parse_query("Jokic recently")
        assert state["last_n"] == 10
        assert state["start_date"] is None

    def test_past_month_still_returns_date_range(self):
        state = parse_query("Jokic past month")
        assert state["start_date"] is not None
        assert state["end_date"] is not None
