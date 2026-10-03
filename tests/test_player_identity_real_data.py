"""Name collisions against the real 1996-97+ player data.

Companion to ``test_player_identity_collisions.py``, which proves the same
behaviour on controlled names and the synthetic fixture. Here the expected
values come from the raw ``player_game_stats`` rows of the pinned generation,
selected by exact player name and aggregated with plain pandas, never through
the summary code under test. Each name must also map to exactly one
``player_id`` in that season, so a shared-name merge cannot pass silently.
"""

from __future__ import annotations

import pytest

from nbatools.commands import entity_resolution
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _expected(name: str, season: str, last_n: int | None = None) -> dict[str, float]:
    frame = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
    rows = frame[frame["player_name"] == name].sort_values(["game_date", "game_id"])
    assert not rows.empty, f"{name} has no {season} rows in this generation"
    assert rows["player_id"].nunique() == 1, f"{name!r} is several players in {season}"
    if last_n is not None:
        rows = rows.tail(last_n)
    return {
        "games": len(rows),
        "pts_sum": float(rows["pts"].sum()),
        "reb_sum": float(rows["reb"].sum()),
    }


def _summaries(query: str) -> dict[str, dict]:
    from nbatools.query_service import execute_natural_query

    entity_resolution.reset_player_index()
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    rows = result.result.to_dict()["sections"]["summary"]
    return {row["player_name"]: row for row in rows}


def _assert_matches(row: dict, expected: dict[str, float]) -> None:
    assert row["games"] == expected["games"]
    assert row["pts_sum"] == pytest.approx(expected["pts_sum"])
    assert row["reb_sum"] == pytest.approx(expected["reb_sum"])


@pytest.mark.parametrize(
    ("query", "name", "season"),
    [
        ("karl anthony towns stats 2023-24", "Karl-Anthony Towns", "2023-24"),
        ("Karl-Anthony Towns stats 2018-19", "Karl-Anthony Towns", "2018-19"),
        ("Carmelo Anthony stats 2012-13", "Carmelo Anthony", "2012-13"),
        ("Nikola Jovic stats 2024-25", "Nikola Jović", "2024-25"),
        ("Tim Hardaway Jr stats 2015-16", "Tim Hardaway Jr.", "2015-16"),
        ("Tim Hardaway stats 1996-97", "Tim Hardaway", "1996-97"),
        ("jaren jackson jr stats 2022-23", "Jaren Jackson Jr.", "2022-23"),
    ],
)
def test_named_season_summary_matches_raw_rows(query, name, season):
    summaries = _summaries(query)
    assert set(summaries) == {name}
    _assert_matches(summaries[name], _expected(name, season))


@pytest.mark.parametrize(
    ("query", "names", "season"),
    [
        ("Luka Dončić vs Nikola Jokić 2023-24", ("Luka Dončić", "Nikola Jokić"), "2023-24"),
        ("nikola jovic vs nikola jokic 2024-25", ("Nikola Jović", "Nikola Jokić"), "2024-25"),
    ],
)
def test_comparison_matches_raw_rows_for_each_player(query, names, season):
    summaries = _summaries(query)
    assert set(summaries) == set(names)
    for name in names:
        _assert_matches(summaries[name], _expected(name, season))
