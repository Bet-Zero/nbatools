"""Last-N windows, qualifying games and meetings against real 1996-97+ rows.

Companion to ``test_last_n_sample_scope.py`` (fixture). Expected answers come
from the raw game rows of the pinned generation, ordered newest first by date
then game id, never from the code under test.
"""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _rows(kind: str, season: str, *, column: str, value: str, opponent: str | None = None):
    frame = data_read_csv(f"raw/{kind}/{season}_regular_season.csv", dtype={"game_id": str})
    rows = frame[frame[column] == value]
    if opponent:
        rows = rows[rows["opponent_team_abbr"] == opponent]
    return rows.sort_values(["game_date", "game_id"], ascending=False)


def _player(name: str, season: str, **kwargs):
    return _rows("player_game_stats", season, column="player_name", value=name, **kwargs)


def _team(abbr: str, season: str, **kwargs):
    return _rows("team_game_stats", season, column="team_abbr", value=abbr, **kwargs)


def _ids(rows) -> list[str]:
    return sorted(rows["game_id"].astype(str).str.lstrip("0"))


def _triple_doubles(rows):
    stats = rows[["pts", "reb", "ast", "stl", "blk"]].apply(lambda col: col.astype(float) >= 10)
    return rows[stats.sum(axis=1) >= 3]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    sections = result.result.to_dict()["sections"]
    rows = sections.get("finder") or sections.get("game_log") or []
    game_ids = sorted(str(row["game_id"]).lstrip("0") for row in rows)
    count = sections["count"][0]["count"] if sections.get("count") else None
    return result, game_ids, count


def test_points_window_counts_inside_the_last_ten_games():
    window = _player("LeBron James", "2017-18").head(10)
    expected = window[window["pts"].astype(float) >= 30]

    _, game_ids, count = _run("how many times did LeBron score 30 in his last 10 games 2017-18")

    assert count == len(expected)
    assert game_ids == _ids(expected)


def test_triple_double_window_counts_inside_the_last_twenty_games():
    expected = _triple_doubles(_player("Nikola Jokić", "2022-23").head(20))

    _, game_ids, count = _run("how many triple doubles did Jokic have in his last 20 games 2022-23")

    assert count == len(expected)
    assert game_ids == _ids(expected)


def test_team_window_counts_inside_the_last_fifteen_games():
    window = _team("BOS", "2023-24").head(15)
    expected = window[window["pts"].astype(float) >= 120]

    _, game_ids, count = _run(
        "how many times did the Celtics score 120 in their last 15 games 2023-24"
    )

    assert count == len(expected)
    assert game_ids == _ids(expected)


def test_qualifying_games_are_the_most_recent_that_meet_the_condition():
    rows = _player("Stephen Curry", "2015-16")
    expected = rows[rows["pts"].astype(float) >= 30].head(5)

    _, game_ids, _ = _run("Curry last 5 games with 30 points 2015-16")

    assert game_ids == _ids(expected)


def test_last_meetings_are_games_against_that_opponent():
    expected = _team("BOS", "2023-24", opponent="NYK").head(3)

    result, game_ids, _ = _run("Celtics last 3 meetings with the Knicks 2023-24")

    assert result.metadata["opponent"] == "NYK"
    assert game_ids == _ids(expected)


def test_number_word_window_is_kept():
    expected = _team("BOS", "2023-24").head(10)

    result, game_ids, _ = _run("Celtics record over their last ten games 2023-24")

    assert result.route == "team_record"
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["wins"] == int((expected["wl"] == "W").sum())
    assert game_ids == _ids(expected)
