"""C2 playoff series and rounds against the real 1996-97+ playoff rows.

Rounds come from the game id from 2001-02 and from each team's series order
before that. These checks hold the fallback to the official id codes and to
known champions, and count records from the raw rows with plain loops.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands import playoff_history
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

EARLY_CHAMPIONS = {
    "1996-97": "CHI",
    "1997-98": "CHI",
    "1998-99": "SAS",
    "1999-00": "LAL",
    "2000-01": "LAL",
}


def _raw_playoffs(season: str) -> pd.DataFrame:
    frame = data_read_csv(f"raw/team_game_stats/{season}_playoffs.csv", dtype={"game_id": str})
    return frame[~frame["game_id"].str.startswith("005")]


def test_series_order_matches_game_id_rounds():
    seasons = [f"{y}-{str(y + 1)[-2:]}" for y in range(2001, 2025)]
    games = playoff_history.load_team_games_for_seasons(seasons, "Playoffs")
    ids = playoff_history._game_id_text(games["game_id"])
    games = games[~ids.str.startswith("005")]
    by_order = playoff_history._series_order_codes(games)
    by_id = ids[games.index].str[6:8]
    mismatched = games.loc[by_order != by_id, ["season", "team_abbr", "opponent_team_abbr"]]
    assert mismatched.empty, mismatched.drop_duplicates().head(10)


@pytest.mark.parametrize(("season", "champion"), sorted(EARLY_CHAMPIONS.items()))
def test_early_finals_winner_from_series_order(season, champion):
    games = playoff_history._load_playoff_games([season])
    runs = {
        abbr: playoff_history._build_series_table(team) for abbr, team in games.groupby("team_abbr")
    }
    titles = [
        abbr
        for abbr, run in runs.items()
        if ((run["playoff_round"] == "Finals") & (run["result"] == "Won")).any()
    ]
    assert titles == [champion]
    # 16 teams play 15 series; every run but the champion's ends in a loss.
    assert len(runs) == 16
    assert sum(len(run) for run in runs.values()) == 30
    assert sum(int((run["result"] == "Lost").sum()) for run in runs.values()) == 15


def test_bulls_finals_record_counts_raw_games():
    wins = losses = 0
    for season in ("1996-97", "1997-98"):
        rows = _raw_playoffs(season)
        chi = rows[rows["team_abbr"] == "CHI"]
        finals_opponent = chi.sort_values("game_date")["opponent_team_abbr"].iloc[-1]
        finals = chi[chi["opponent_team_abbr"] == finals_opponent]
        wins += int((finals["wl"] == "W").sum())
        losses += int((finals["wl"] == "L").sum())

    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("Bulls Finals record")
    assert result.metadata["route"] == "playoff_history"
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (wins, losses)
    assert (summary["series_won"], summary["series_lost"]) == (2, 0)


def _finals_winners() -> dict[str, str]:
    """Season -> champion, from each season's last matchup in the raw rows."""
    winners = {}
    for year in range(1996, 2025):
        season = f"{year}-{str(year + 1)[-2:]}"
        rows = _raw_playoffs(season)
        last = rows.sort_values("game_date").iloc[-1]
        pair = {last["team_abbr"], last["opponent_team_abbr"]}
        # Finalists come from different conferences, so they meet only once.
        finals = rows[rows["team_abbr"].isin(pair) & rows["opponent_team_abbr"].isin(pair)]
        wins = finals[finals["wl"] == "W"].groupby("team_abbr").size()
        winners[season] = str(wins.idxmax())
    return winners


@pytest.mark.parametrize(
    ("query", "team"), [("Spurs championships", "SAS"), ("Lakers titles", "LAL")]
)
def test_team_titles_match_raw_finals_winners(query, team):
    from nbatools.query_service import execute_natural_query

    expected = sorted(s for s, champ in _finals_winners().items() if champ == team)
    result = execute_natural_query(query)
    assert result.metadata["route"] == "playoff_history"
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["titles"] == len(expected)
    assert f"({', '.join(expected)})" in result.metadata["answer_phrase"]
