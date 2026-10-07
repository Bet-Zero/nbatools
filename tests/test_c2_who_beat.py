"""C2: "which teams beat the Lakers", "who did the Celtics beat".

These refused (or listed the subject's games). They now rank the teams with a
win (or loss) against that team, listing every team with at least one (or
"twice", "at least 6 times"); "the most" keeps the full board. Expected rows
come from the fixture CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _record_vs(opponent: str, *files: str) -> pd.DataFrame:
    games = pd.concat(pd.read_csv(RAW / name) for name in files)
    games = games[games["opponent_team_abbr"] == opponent]
    wins = games.assign(win=games["wl"] == "W").groupby("team_abbr")["win"]
    return pd.DataFrame({"wins": wins.sum(), "losses": wins.size() - wins.sum()})


def _rows(query: str) -> dict[str, tuple[int, int]]:
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    return {row["team_abbr"]: (row["wins"], row["losses"]) for row in rows}


@pytest.mark.parametrize(
    "query",
    [
        "teams that beat the Lakers",
        "which teams beat the Lakers this season",
        "who beat the Lakers",
        "teams the Lakers lost to",
        "who did the Lakers lose to",
    ],
)
def test_teams_that_beat_the_lakers(query):
    record = _record_vs("LAL", "2025-26_regular_season.csv")
    expected = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.wins >= 1}
    assert _rows(query) == expected


def test_beat_twice_and_at_least_n_times():
    record = _record_vs(
        "LAL",
        "2023-24_regular_season.csv",
        "2024-25_regular_season.csv",
        "2025-26_regular_season.csv",
    )
    expected = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.wins >= 6}
    assert _rows("which teams beat the Lakers at least 6 times since 2023") == expected


def test_who_did_the_celtics_beat_lists_their_victims():
    record = _record_vs("BOS", "2024-25_regular_season.csv")
    expected = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.losses >= 1}
    rows = _rows("who did the Celtics beat in 2024-25")
    assert rows == expected
    losses = [loss for _, loss in rows.values()]
    assert losses == sorted(losses, reverse=True)


def test_beaten_the_most_keeps_every_team():
    record = _record_vs("BOS", "2025-26_regular_season.csv")
    rows = _rows("which teams have beaten the Celtics the most")
    assert rows == {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows()}
    wins = [win for win, _ in rows.values()]
    assert wins == sorted(wins, reverse=True)


@pytest.mark.parametrize(
    "query",
    [
        "who beat the buzzer",
        "teams that beat the Lakers and Celtics",
        "who did LeBron beat",
        "which teams did the Celtics beat by 20",
    ],
)
def test_other_readings_are_not_the_opponent_board(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert "which teams have the most" not in parsed["normalized_query"]


def test_headline_names_the_teams():
    result = execute_natural_query("teams that beat the Lakers")
    record = _record_vs("LAL", "2025-26_regular_season.csv")
    winners = record[record["wins"] >= 1].sort_values("wins", ascending=False)
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(f"{len(winners)} teams beat the Los Angeles Lakers in the 2025-26")
    top = winners.iloc[0]
    assert f"({int(top.wins)} times)" in phrase


def test_headline_for_the_teams_a_team_beat():
    phrase = execute_natural_query("who did the Celtics beat in 2024-25").metadata["answer_phrase"]
    assert phrase.startswith("The Boston Celtics beat ")
    assert "in the 2024-25 regular season" in phrase


def _home_record_vs(opponent: str, home: bool) -> pd.DataFrame:
    """Each team's record against ``opponent`` in ``opponent``'s home (or road) games."""
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[
        (games["opponent_team_abbr"] == opponent) & (games["is_home"] == (0 if home else 1))
    ]
    wins = games.assign(win=games["wl"] == "W").groupby("team_abbr")["win"]
    return pd.DataFrame({"wins": wins.sum(), "losses": wins.size() - wins.sum()})


def test_at_home_is_the_named_teams_home():
    record = _home_record_vs("LAL", home=True)
    beat_them = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.wins >= 1}
    assert _rows("which teams beat the Lakers at home") == beat_them
    assert _rows("who did the Lakers lose to at home") == beat_them
    they_beat = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.losses >= 1}
    assert _rows("who did the Lakers beat at home") == they_beat
    phrase = execute_natural_query("which teams beat the Lakers at home").metadata["answer_phrase"]
    assert "beat the Los Angeles Lakers in their home games" in phrase


@pytest.mark.parametrize(
    ("query", "minimum"),
    [
        ("which teams beat the Lakers more than twice", 3),
        ("which teams beat the Lakers 3 or more times", 3),
        ("which teams beat the Lakers twice", 2),
    ],
)
def test_repeat_counts(query, minimum):
    record = _record_vs("LAL", "2025-26_regular_season.csv")
    expected = {t: (int(r.wins), int(r.losses)) for t, r in record.iterrows() if r.wins >= minimum}
    assert _rows(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "which teams beat the Lakers only once",
        "who beat the Lakers last",
        "who beat the Lakers by the most",
        "who did the Lakers beat in their last game",
    ],
)
def test_exact_last_and_margin_questions_are_not_the_board(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert "which teams have the most" not in parsed["normalized_query"]


@pytest.mark.parametrize(
    "query",
    ["did the Lakers lose their last game", "did the Lakers lose in their last 5 games"],
)
def test_yes_no_lose_question_keeps_every_game(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert not kwargs.get("losses_only")
