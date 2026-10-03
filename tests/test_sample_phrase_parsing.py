"""Parser helpers for recent-game samples (no data needed)."""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import (
    canonicalize_sample_phrases,
    detect_last_n_scope,
    extract_last_n,
    extract_last_n_seasons,
    extract_threshold_conditions,
)

pytestmark = pytest.mark.parser


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lebron last ten games", "lebron last 10 games"),
        ("lebron previous 5 games", "lebron last 5 games"),
        ("lebron's 5 most recent games", "lebron's last 5 games"),
        ("lebron's five latest games", "lebron's last 5 games"),
        ("celtics record over their prior twelve games", "celtics record over their last 12 games"),
        ("jokic over the past three seasons", "jokic over the past 3 seasons"),
        ("lakers last 3 meetings with the warriors", "lakers last 3 matchups vs the warriors"),
        ("lakers last meeting with the celtics", "lakers last game vs the celtics"),
        ("lakers vs celtics last 3 meetings", "lakers vs celtics last 3 matchups"),
        # Untouched: no sample unit, or a threshold that only looks similar.
        ("lebron points in the last five minutes", "lebron points in the last five minutes"),
        ("lebron previous season", "lebron previous season"),
        ("lebron 30 points most recent game", "lebron 30 points most recent game"),
        ("lebron 30 points last game", "lebron 30 points last game"),
    ],
)
def test_canonicalize_sample_phrases(text, expected):
    assert canonicalize_sample_phrases(text) == expected


def test_canonical_phrases_reach_the_existing_extractors():
    assert extract_last_n(canonicalize_sample_phrases("lebron last twenty games")) == 20
    assert extract_last_n_seasons(canonicalize_sample_phrases("curry past five seasons")) == 5


@pytest.mark.parametrize(
    ("text", "scope"),
    [
        ("how many times has lebron scored 30 in his last 10 games", "window"),
        ("lebron 30 point games in his last 10 games", "window"),
        ("how many of his last 10 games did lebron score 25", "window"),
        ("lebron 30 point games last 10 games", "window"),
        ("lebron stats in wins over his last 10 games", "window"),
        ("lebron last 10 games where he scored 30", "qualifying"),
        ("lebron last 5 games with 30 points", "qualifying"),
        ("lakers last 5 games scoring 120+", "qualifying"),
        ("lebron last 10 wins", "qualifying"),
        ("lebron last 10 games", "qualifying"),
        ("lakers record in their last 10 games when lebron scores 30", "qualifying"),
    ],
)
def test_detect_last_n_scope(text, scope):
    assert detect_last_n_scope(text, extract_threshold_conditions(text)) == scope
