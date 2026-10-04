"""Conference and division opponents, season by season, on every game-log route.

"LeBron stats vs Western Conference teams", "Lakers games vs Pacific Division
teams", splits and comparisons against a conference all select the games
whose opponent belonged to that group in that season. Expected values come
from the fixture's game CSVs and its served membership table, never from the
engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _games(kind: str, season: str = "2025-26", **match: str) -> list[dict[str, str]]:
    rows = _csv(RAW / kind / f"{season}_regular_season.csv")
    rows = [row for row in rows if all(row[key] == value for key, value in match.items())]
    return sorted(rows, key=lambda row: (row["game_date"], int(row["game_id"])), reverse=True)


def _members(season: str, *, conference: str | None = None, division: str | None = None):
    """Team ids in a group, from the served membership table.

    Alignment has not changed since 2004-05, so 2024-25 membership also
    describes 2023-24, which the served table does not list.
    """
    table_season = season if season in {"2024-25", "2025-26"} else "2024-25"
    rows = _csv(RAW / "teams" / "team_conference_membership.csv")
    return {
        row["team_id"]
        for row in rows
        if row["season"] == table_season
        and (conference is None or row["conference"] == conference)
        and (division is None or row["division"] == division)
    }


def _vs(rows, season="2025-26", **group):
    members = _members(season, **group)
    return [row for row in rows if row["opponent_team_id"] in members]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _sections(result) -> dict:
    return result.result.to_dict()["sections"]


def _ids(rows) -> list[int]:
    return sorted(int(row["game_id"]) for row in rows)


def _won(row) -> bool:
    return row["wl"] == "W"


def _home(row) -> bool:
    return row["is_home"] == "True"


# -- the historical table agrees with the served membership table -------------


@pytest.mark.parametrize("season", ["2024-25", "2025-26"])
def test_historical_alignment_matches_the_served_table(season):
    from nbatools.commands._nba_alignment import historical_alignment

    rows = [
        r for r in _csv(RAW / "teams" / "team_conference_membership.csv") if r["season"] == season
    ]
    expected = {int(r["team_id"]): (r["conference"], r["division"]) for r in rows}
    assert historical_alignment(season) == expected


@pytest.mark.parametrize(
    ("season", "east", "west", "divisions"),
    [
        ("1996-97", 15, 14, {"Atlantic", "Central", "Midwest", "Pacific"}),
        ("2003-04", 15, 14, {"Atlantic", "Central", "Midwest", "Pacific"}),
        (
            "2004-05",
            15,
            15,
            {"Atlantic", "Central", "Southeast", "Northwest", "Pacific", "Southwest"},
        ),
    ],
)
def test_alignment_eras(season, east, west, divisions):
    from nbatools.commands._nba_alignment import historical_alignment

    alignment = historical_alignment(season)
    conferences = [conference for conference, _ in alignment.values()]
    assert conferences.count("East") == east
    assert conferences.count("West") == west
    assert {division for _, division in alignment.values()} == divisions


def test_new_orleans_changes_conference_in_2004_05():
    from nbatools.commands._nba_alignment import NOP, historical_alignment

    assert historical_alignment("2003-04")[NOP] == ("East", "Central")
    assert historical_alignment("2004-05")[NOP] == ("West", "Southwest")


def test_season_tokens_count_a_team_only_in_its_group_seasons():
    from nbatools.commands.data_utils import OpponentGroup, build_opponent_mask

    frame = pd.DataFrame(
        {
            "season": ["2003-04", "2004-05", "2004-05"],
            "opponent_team_id": [1610612740, 1610612740, 1610612738],
            "opponent_team_abbr": ["NOH", "NOH", "BOS"],
        }
    )
    east = OpponentGroup(["2003-04#1610612740", "2004-05#1610612738"], "Eastern Conference teams")
    assert build_opponent_mask(frame, east).tolist() == [True, False, True]

    celtics_in_the_east = OpponentGroup(list(east), "Eastern Conference teams", also="BOS")
    assert build_opponent_mask(frame, celtics_in_the_east).tolist() == [False, False, True]


# -- every game-log route takes the group --------------------------------------


def test_player_summary_vs_a_conference():
    rows = _vs(_games("player_game_stats", player_name="LeBron James"), conference="West")
    result = _run("LeBron stats vs Western conference teams")

    (summary,) = _sections(result)["summary"]
    assert summary["games"] == len(rows)
    assert summary["pts_avg"] == pytest.approx(
        sum(int(r["pts"]) for r in rows) / len(rows), abs=1e-3
    )
    assert "filtered to games vs Western Conference teams" in result.result.to_dict()["caveats"]


def test_player_summary_vs_a_division():
    rows = _vs(_games("player_game_stats", player_name="LeBron James"), division="Pacific")
    (summary,) = _sections(_run("LeBron stats vs Pacific division teams"))["summary"]
    assert summary["games"] == len(rows)


def test_player_finder_vs_a_conference():
    rows = [
        r
        for r in _vs(_games("player_game_stats", player_name="LeBron James"), conference="West")
        if int(r["pts"]) >= 30
    ]
    finder = _sections(_run("LeBron 30 point games vs the West"))["finder"]
    assert sorted(int(row["game_id"]) for row in finder) == _ids(rows)


def test_team_game_list_vs_a_division():
    rows = _vs(_games("team_game_stats", team_abbr="LAL"), division="Pacific")
    finder = _sections(_run("Lakers games vs Pacific division teams"))["finder"]
    assert sorted(int(row["game_id"]) for row in finder) == _ids(rows)


def test_player_split_vs_a_conference():
    rows = _vs(_games("player_game_stats", player_name="LeBron James"), conference="West")
    buckets = {
        row["bucket"]: row
        for row in _sections(_run("LeBron home away splits vs West teams"))["split_comparison"]
    }
    assert buckets["home"]["games"] == sum(_home(r) for r in rows)
    assert buckets["away"]["games"] == sum(not _home(r) for r in rows)


def test_team_split_vs_a_conference():
    rows = _vs(_games("team_game_stats", team_abbr="LAL"), conference="West")
    buckets = {
        row["bucket"]: row
        for row in _sections(_run("Lakers wins losses split vs West teams"))["split_comparison"]
    }
    assert buckets["wins"]["games"] == sum(_won(r) for r in rows)
    assert buckets["losses"]["games"] == sum(not _won(r) for r in rows)


def test_player_comparison_vs_a_conference():
    result = _run("compare LeBron and Curry vs the East")
    a, b = _sections(result)["summary"]
    for side, name in ((a, "LeBron James"), (b, "Stephen Curry")):
        rows = _vs(_games("player_game_stats", player_name=name), conference="East")
        assert side["games"] == len(rows)


def test_team_record_vs_a_conference_in_a_season_the_served_table_lacks():
    rows = _vs(
        _games("team_game_stats", season="2023-24", team_abbr="LAL"),
        season="2023-24",
        conference="West",
    )
    (summary,) = _sections(_run("Lakers record vs Western conference 2023-24"))["summary"]
    assert summary["games"] == len(rows)
    assert summary["wins"] == sum(_won(r) for r in rows)


def test_multi_season_conference_filter_counts_each_season():
    expected = 0
    for season in ("2023-24", "2024-25", "2025-26"):
        rows = _games("player_game_stats", season=season, player_name="LeBron James")
        expected += len(_vs(rows, season=season, conference="West"))
    (summary,) = _sections(_run("LeBron stats vs Western conference teams since 2023-24"))[
        "summary"
    ]
    assert summary["games"] == expected


def test_a_division_that_did_not_exist_refuses():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron stats vs Midwest division teams 2023-24")
    assert result.result_status == "no_result"
    notes = " ".join(result.result.to_dict()["notes"])
    assert "Midwest ran through 2003-04" in notes


# -- two named teams, players with teams ---------------------------------------


def test_team_vs_team_last_n_games_are_their_meetings():
    meetings = _games("team_game_stats", team_abbr="LAL", opponent_team_abbr="GSW")[:10]
    result = _run("Lakers vs Warriors last 10 games")
    a, b = _sections(result)["summary"]
    assert a["games"] == b["games"] == len(meetings)
    assert a["wins"] == sum(_won(r) for r in meetings)
    assert b["wins"] == len(meetings) - a["wins"]


def test_compare_two_teams_last_n_games_keeps_each_teams_own_games():
    result = _run("compare Lakers and Warriors last 10 games")
    a, b = _sections(result)["summary"]
    assert a["wins"] == sum(_won(r) for r in _games("team_game_stats", team_abbr="LAL")[:10])
    assert b["wins"] == sum(_won(r) for r in _games("team_game_stats", team_abbr="GSW")[:10])


@pytest.mark.parametrize(
    "query", ["compare LeBron and Lakers", "compare LeBron James and the Celtics"]
)
def test_comparing_a_player_with_a_team_asks_which_reading(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    notes = " ".join(result.result.to_dict()["notes"])
    assert "LeBron stats vs the Celtics" in notes
