"""Verify STAT_PATTERN is provably correct for all entries in STAT_ALIASES.

Phase B item 6: reconcile STAT_PATTERN with alias dict.
"""

import re

import pytest

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN

pytestmark = pytest.mark.parser


class TestStatPatternCoversAllAliases:
    """Every key in STAT_ALIASES must match STAT_PATTERN."""

    @pytest.mark.parametrize("alias", list(STAT_ALIASES.keys()))
    def test_alias_matches_pattern(self, alias: str):
        m = re.search(STAT_PATTERN, alias)
        assert m is not None, f"STAT_PATTERN does not match alias: {alias!r}"

    @pytest.mark.parametrize("alias", list(STAT_ALIASES.keys()))
    def test_alias_matches_fully(self, alias: str):
        """Match should capture the full alias key, not a partial substring."""
        m = re.search(STAT_PATTERN, alias)
        assert m is not None
        assert m.group(1) == alias, f"Partial match: {alias!r} matched as {m.group(1)!r}"


class TestMultiWordAliases:
    """Multi-word aliases should match correctly in surrounding context."""

    @pytest.mark.parametrize(
        "phrase,expected_stat",
        [
            ("three point percentage leaders", "three point percentage"),
            ("over 50 free throw percentage", "free throw percentage"),
            ("effective field goal percentage this season", "effective field goal percentage"),
            ("true shooting percentage leaders", "true shooting percentage"),
            ("three-point percentage leaders", "three-point percentage"),
            ("offensive rating leaders", "offensive rating"),
            ("defensive rating this season", "defensive rating"),
        ],
    )
    def test_multi_word_in_context(self, phrase: str, expected_stat: str):
        m = re.search(STAT_PATTERN, phrase)
        assert m is not None, f"No match in: {phrase!r}"
        assert m.group(1) == expected_stat, f"Expected {expected_stat!r}, got {m.group(1)!r}"


class TestLongestMatchFirst:
    """Longer aliases should match before shorter substrings."""

    @pytest.mark.parametrize(
        "phrase,expected",
        [
            # "three point percentage" should match before "three"
            ("three point percentage", "three point percentage"),
            # "free throw percentage" should match before "free throw %"
            ("turnover percentage", "turnover percentage"),
            # "rebound percentage" should match before "rebound"
            ("rebound percentage", "rebound percentage"),
            # "assist percentage" should match before "assist"
            ("assist percentage", "assist percentage"),
        ],
    )
    def test_longest_match_preferred(self, phrase: str, expected: str):
        m = re.search(STAT_PATTERN, phrase)
        assert m is not None
        assert m.group(1) == expected


class TestVerbalFormAliases:
    """Verbal forms added in Phase A should be in STAT_PATTERN."""

    @pytest.mark.parametrize(
        "verbal_form,canonical",
        [
            ("scored", "pts"),
            ("scoring", "pts"),
            ("scores", "pts"),
            ("rebounded", "reb"),
            ("rebounding", "reb"),
            ("assisted", "ast"),
        ],
    )
    def test_verbal_form_in_pattern(self, verbal_form: str, canonical: str):
        m = re.search(STAT_PATTERN, verbal_form)
        assert m is not None, f"STAT_PATTERN should match verbal form: {verbal_form!r}"
        assert STAT_ALIASES[verbal_form] == canonical
