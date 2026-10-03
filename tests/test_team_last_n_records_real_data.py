"""Team last-N records against the real 1996-97+ team game rows.

Companion to ``test_team_last_n_records.py`` (fixture). Expected records come
from the raw ``team_game_stats`` rows of the pinned generation, ordered newest
first by date then game id, never from the code under test.
"""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _expected(
    team: str, season: str, last_n: int, *, season_type: str = "regular_season", home=False
) -> dict:
    frame = data_read_csv(f"raw/team_game_stats/{season}_{season_type}.csv", dtype={"game_id": str})
    rows = frame[frame["team_abbr"] == team]
    if home:
        rows = rows[rows["is_home"].astype(str).isin({"1", "True", "true"})]
    rows = rows.sort_values(["game_date", "game_id"], ascending=False).head(last_n)
    return {
        "games": len(rows),
        "wins": int((rows["wl"] == "W").sum()),
        "losses": int((rows["wl"] == "L").sum()),
        "game_ids": sorted(rows["game_id"].astype(str).str.lstrip("0")),
    }


def _answer(query: str) -> dict:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.route == "team_record"
    sections = result.result.to_dict()["sections"]
    (summary,) = sections["summary"]
    return {
        "games": summary["games"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "game_ids": sorted(str(row["game_id"]).lstrip("0") for row in sections["game_log"]),
    }


@pytest.mark.parametrize(
    ("query", "team", "season", "last_n", "options"),
    [
        ("Warriors record last 10 games 2023-24", "GSW", "2023-24", 10, {}),
        ("Celtics record in their last 15 games 2015-16", "BOS", "2015-16", 15, {}),
        ("Lakers home record last 10 games 2009-10", "LAL", "2009-10", 10, {"home": True}),
        (
            "Spurs playoff record last 5 games 2013-14",
            "SAS",
            "2013-14",
            5,
            {"season_type": "playoffs"},
        ),
    ],
)
def test_last_n_record_matches_raw_rows(query, team, season, last_n, options):
    assert _answer(query) == _expected(team, season, last_n, **options)


def test_default_season_last_ten_matches_raw_rows():
    from nbatools.commands._seasons import LATEST_REGULAR_SEASON

    assert _answer("Warriors record over the last 10 games") == _expected(
        "GSW", LATEST_REGULAR_SEASON, 10
    )
