"""C1: record bars against one team on the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _lakers_opponents(season: str):
    from nbatools.commands.data_utils import load_team_games_for_seasons

    games = load_team_games_for_seasons([season], "Regular Season")
    return games[games["opponent_team_abbr"] == "LAL"]


def test_teams_with_a_winning_record_against_the_lakers_in_2023_24():
    from nbatools.query_service import execute_natural_query

    games = _lakers_opponents("2023-24")
    record = games.groupby("team_abbr")["wl"].agg(
        wins=lambda s: int((s == "W").sum()), losses=lambda s: int((s == "L").sum())
    )
    expected = {t for t, row in record.iterrows() if row.wins > row.losses}
    rows = execute_natural_query(
        "which teams have a winning record against the Lakers in 2023-24"
    ).result.to_dict()["sections"]["leaderboard"]
    assert {r["team_abbr"] for r in rows} == expected


def test_winning_teams_the_lakers_beat_in_2023_24():
    from nbatools.commands.data_utils import load_latest_standings_snapshot
    from nbatools.query_service import execute_natural_query

    standings = load_latest_standings_snapshot("2023-24")
    winning = set(standings.loc[standings["win_pct"].astype(float) >= 0.5, "team_abbr"])
    games = _lakers_opponents("2023-24")
    beaten = games[(games["wl"] == "L") & games["team_abbr"].isin(winning)]
    expected = beaten["team_abbr"].value_counts().to_dict()
    result = execute_natural_query("which winning teams have the Lakers beaten in 2023-24")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {r["team_abbr"]: r["losses"] for r in rows} == expected


def test_zero_answer_names_the_team():
    from nbatools.query_service import execute_natural_query

    phrase = (
        execute_natural_query(
            "how many teams have a losing record against the Pistons in 2023-24"
        ).metadata.get("answer_phrase")
        or ""
    )
    assert "the DET" not in phrase
