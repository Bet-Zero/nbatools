"""C1: "how many games was LeBron over 30 points" is not a Wizards question.

"was" after a count ("how many games was", "how often was") or at the start
of a player's bound ("was LeBron over 30 points last game") read as the
Washington abbreviation: the team filter emptied the list (0 games). The
Wizards' own "was over 120 points" keeps the team. Expected values come from
the fixture's player rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.entity_resolution import mask_copula_team_lookalikes
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _player(name: str) -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    return games[games["player_name"] == name]


@pytest.mark.parametrize(
    ("query", "name", "keep"),
    [
        ("how many games was LeBron over 30 points", "LeBron James", lambda g: g["pts"] > 30),
        (
            "how many games was LeBron over 30 points or over 10 assists",
            "LeBron James",
            lambda g: (g["pts"] > 30) | (g["ast"] > 10),
        ),
        ("how often was Jokic held under 20 points", "Nikola Jokić", lambda g: g["pts"] < 20),
    ],
)
def test_copula_was_in_a_count(query, name, keep):
    games = _player(name)
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"] == [{"count": int(keep(games).sum())}]


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("how many games was lebron over 30 points", True),
        ("how often was jokic held under 20 points", True),
        ("against miami, what was new york's away record", True),
        ("versus boston, how was lebron's record", True),
        ("who was lebron playing against", True),
        ("which was boston's best stretch", True),
        ("was over 120 points", False),
        ("was record this season", False),
        ("what was record against miami", False),
        ("how was scored over 120", False),
        ("which was player had the highest ppg", False),
        ("what was ppg in 2023-24", False),
        ("which was season had the most wins", False),
        # The Wizards after a count word keep the team.
        ("how many times was scored 120 points", False),
        ("games when was won by 20", False),
        ("how many nights was scored over 120", False),
    ],
)
def test_copula_mask(text, masked):
    assert ("was" not in mask_copula_team_lookalikes(text).split()) is masked


@pytest.mark.parametrize(
    "query",
    [
        "Which WAS player had the highest PPG in 2023-24?",
        "Which WAS players averaged the most assists in 2023-24?",
        "What WAS player scored the most points in 2023-24?",
    ],
)
def test_question_word_preserves_explicit_washington_population(query):
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(query)
    assert parsed["route"] == "season_leaders"
    assert parsed["team"] == "WAS"
    assert parsed["route_kwargs"]["team"] == "WAS"


@pytest.mark.parametrize(
    "query",
    [
        "Against Boston, what was the Lakers away record in 2025-26?",
        "Versus Boston, how was the Lakers road record in 2025-26?",
        "In 2025-26 against Boston, what was the Lakers' away record?",
    ],
)
def test_opponent_prefix_question_retains_subject_and_away_sample(query, monkeypatch):
    from nbatools.commands import team_record

    rows = pd.read_csv(RAW.parent / "team_game_stats/2025-26_regular_season.csv")
    expected = rows.loc[
        rows.team_abbr.eq("LAL") & rows.opponent_team_abbr.eq("BOS") & rows.is_away.eq(1)
    ]
    assert not expected.empty
    captured = []
    compute = team_record._compute_record

    def capture(frame):
        captured.append(frame.copy())
        return compute(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture)
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert result.route == "team_record"
    assert result.metadata["team"] == "LAL"
    assert result.metadata["opponent"] == "BOS"
    assert len(captured) == 1
    assert sorted(captured[0].game_id.astype(int)) == sorted(expected.game_id.astype(int))
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == len(expected)
    assert summary["wins"] == int(expected.wl.eq("W").sum())
    assert summary["losses"] == int(expected.wl.eq("L").sum())
    for stat in ("pts", "reb", "ast"):
        assert summary[stat + "_avg"] == pytest.approx(expected[stat].mean(), abs=0.001)


@pytest.mark.parametrize(
    "query",
    [
        # A month repeated in each season of a span was read in one season
        # only ("Lakers record in March from 2023-24 to 2025-26": 1-2, not 6-4).
        "Lakers record in March from 2023-24 to 2025-26",
        "LeBron stats in March over the last 2 seasons",
        "Celtics record after the all star break over the last 3 seasons",
        "LeBron career stats in March",
        # Short month names too.
        "Lakers record in Mar from 2023-24 to 2025-26",
        "LeBron career stats in Feb",
        "Lakers record in Dec over the last 2 seasons",
    ],
)
def test_month_repeated_over_a_span_refuses(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_one_window_across_seasons_still_answers():
    games = pd.concat(
        [
            pd.read_csv(Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats") / f)
            for f in ("2024-25_regular_season.csv", "2025-26_regular_season.csv")
        ]
    )
    lakers = games[
        (games["team_abbr"] == "LAL") & (pd.to_datetime(games["game_date"]) >= "2025-01-01")
    ]
    summary = execute_natural_query("Lakers record since January 2025").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((lakers["wl"] == "W").sum()),
        int((lakers["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        # A window with its year inside a career or span is one window.
        "LeBron career stats since January 2025",
        "Lakers all time record since January 2025",
        "Lakers record since January 2025 over the last 3 seasons",
        "Lakers record since Jan 2025 over the last 3 seasons",
        "Lakers record since Mar. 3, 2025 over the last 3 seasons",
    ],
)
def test_dated_window_inside_a_span_answers(query):
    assert execute_natural_query(query).result_status == "ok"
