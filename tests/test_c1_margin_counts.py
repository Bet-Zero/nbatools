"""Win/loss margin counts: "how many times did the Lakers win by 20".

A bare margin of 10 or more reads as "at least" ("win by 20" counts every
20+ win); smaller bare margins ("won by 1") and "exactly N" stay exact. The
margin after an opponent ("beat the Celtics by 20", "lost to the Knicks by
10 or more") is kept rather than dropped by the beat/lose-to rewrite.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import canonicalize_margin_phrases
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

GAMES = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats/2025-26_regular_season.csv")


def _games(team: str, opponent: str | None = None) -> pd.DataFrame:
    games = pd.read_csv(GAMES)
    games = games[games["team_abbr"] == team]
    if opponent:
        games = games[games["opponent_team_abbr"] == opponent]
    return games


def _count(query: str) -> tuple[int, str]:
    result = execute_natural_query(query)
    return (
        result.result.to_dict()["sections"]["count"][0]["count"],
        result.metadata["count_phrase"],
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        ("lakers won by 20", "lakers won at 20+ win margin"),
        ("lakers won by 1", "lakers won at between 1 and 1 win margin"),
        ("lakers won by exactly 20", "lakers won at between 20 and 20 win margin"),
        ("lakers beat the celtics by 20", "lakers beat the celtics at 20+ win margin"),
        ("lakers beat the 76ers by 10", "lakers beat the 76ers at 10+ win margin"),
        ("were the lakers beaten by 20", "were the lakers lost at 20+ loss margin"),
        (
            "were the lakers beaten by the celtics by 20",
            "were the lakers lost to the celtics at 20+ loss margin",
        ),
        ("lakers lost to the knicks by 10 or more", "lakers lost to the knicks at 10+ loss margin"),
        ("celtics beat boston by 5 rebounds", "celtics beat boston by 5 rebounds"),
        (
            "lakers lost to the celtics by 10 at halftime",
            "lakers lost to the celtics by 10 in-game lead at halftime",
        ),
    ],
)
def test_margin_wording(text, expected):
    assert canonicalize_margin_phrases(text) == expected


def test_win_by_twenty_counts_every_twenty_plus_win():
    games = _games("LAL")
    expected = int(((games["wl"] == "W") & (games["plus_minus"] >= 20)).sum())
    count, phrase = _count("how many times did the Lakers win by 20")
    assert count == expected
    assert f"have won {expected} games by 20+ points in the 2025-26" in phrase


def test_beat_opponent_by_margin_keeps_opponent_and_margin():
    games = _games("LAL", "BOS")
    expected = int(((games["wl"] == "W") & (games["plus_minus"] >= 20)).sum())
    count, phrase = _count("how many times did the Lakers beat the Celtics by 20")
    assert count == expected
    assert (
        f"have won {expected} game{'s' if expected != 1 else ''} by 20+ points against the Boston Celtics"
        in phrase
    )


def test_lose_to_opponent_by_margin():
    games = _games("BOS", "NYK")
    expected = int(((games["wl"] == "L") & (games["plus_minus"] <= -10)).sum())
    count, phrase = _count("how many times did the Celtics lose to the Knicks by 10 or more")
    assert count == expected
    assert "by 10+ points against the New York Knicks" in phrase


def test_small_bare_margin_stays_exact():
    games = _games("LAL")
    expected = int(((games["wl"] == "W") & (games["plus_minus"] == 1)).sum())
    count, phrase = _count("how many times did the lakers win by 1")
    assert count == expected
    assert "by exactly 1 point" in phrase


@pytest.mark.parametrize(
    "query",
    [
        "how many times were the Lakers beaten by the Celtics by 20",
        "how many times have the Lakers been beaten by the Celtics by 20",
    ],
)
def test_passive_beaten_by_is_a_loss(query):
    games = _games("LAL", "BOS")
    expected = int(((games["wl"] == "L") & (games["plus_minus"] <= -20)).sum())
    count, phrase = _count(query)
    assert count == expected
    assert "have lost" in phrase


def test_home_win_count_names_the_venue():
    games = _games("LAL")
    expected = int(
        ((games["wl"] == "W") & (games["plus_minus"] >= 20) & (games["is_home"] == 1)).sum()
    )
    count, phrase = _count("how many times did the Lakers win by 20 at home")
    assert count == expected
    assert "by 20+ points at home in the 2025-26" in phrase
