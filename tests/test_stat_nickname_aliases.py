"""Tests for spec-documented stat nickname aliases (Phase B item 11).

Verifies that colloquial stat nicknames (boards, dimes, swipes, swats)
route equivalently to their canonical forms in leaderboard queries.
"""

import pytest

from tests._parser_equivalence import assert_parse_equivalence

pytestmark = pytest.mark.parser


class TestStatNicknameEquivalence:
    """Each nickname should parse identically to its canonical stat form."""

    def test_boards_equals_rebounds(self):
        ref = assert_parse_equivalence(
            [
                "most rebounds this season",
                "most boards this season",
            ]
        )
        assert ref["stat"] == "reb"
        assert ref["leaderboard_intent"] is True

    def test_dimes_equals_assists(self):
        ref = assert_parse_equivalence(
            [
                "most assists this season",
                "most dimes this season",
            ]
        )
        assert ref["stat"] == "ast"
        assert ref["leaderboard_intent"] is True

    def test_swipes_equals_steals(self):
        ref = assert_parse_equivalence(
            [
                "top steals this season",
                "top swipes this season",
            ]
        )
        assert ref["stat"] == "stl"
        assert ref["leaderboard_intent"] is True

    def test_swats_equals_blocks(self):
        ref = assert_parse_equivalence(
            [
                "most blocks this season",
                "most swats this season",
            ]
        )
        assert ref["stat"] == "blk"
        assert ref["leaderboard_intent"] is True


class TestStatNicknameDetection:
    """Verify nicknames are picked up by STAT_PATTERN and STAT_ALIASES."""

    def test_aliases_contain_nicknames(self):
        from nbatools.commands._constants import STAT_ALIASES

        assert STAT_ALIASES["boards"] == "reb"
        assert STAT_ALIASES["dimes"] == "ast"
        assert STAT_ALIASES["swipes"] == "stl"
        assert STAT_ALIASES["swats"] == "blk"

    def test_pattern_matches_nicknames(self):
        import re

        from nbatools.commands._constants import STAT_PATTERN

        for nickname in ("boards", "dimes", "swipes", "swats"):
            m = re.search(STAT_PATTERN, nickname)
            assert m is not None, f"STAT_PATTERN does not match: {nickname!r}"
            assert m.group(1) == nickname
