"""C2 playoff series and rounds.

"Celtics conference finals record" was refused, "how did the Lakers do in the
2026 playoffs" read "2026 playoffs" as no season, and "how many playoff series
have the Lakers won" was blocked as a game-wins filter. Expected values are
counted from game rows with plain loops, never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import playoff_history
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _game(gid, season, date, team, opp, wl):
    return {
        "game_id": gid,
        "season": season,
        "game_date": date,
        "team_id": team,
        "team_abbr": f"T{team}",
        "team_name": f"Team {team}",
        "opponent_team_id": opp,
        "opponent_team_abbr": f"T{opp}",
        "opponent_team_name": f"Team {opp}",
        "wl": wl,
    }


def _run(team, opponents, season="1998-99", gid_prefix="0049800000"):
    """A team's playoff run: each opponent is (date, wins, losses)."""
    rows = []
    for n, (opp, date, wins, losses) in enumerate(opponents):
        for g in range(wins + losses):
            day = pd.Timestamp(date) + pd.Timedelta(days=2 * g)
            # Positions 6-7 carry the round code: "00" (none) unless given.
            gid = f"{gid_prefix[:5]}{n}{gid_prefix[6:8]}{g:02d}"
            rows.append(_game(gid, season, day, team, opp, "W" if g < wins else "L"))
    return rows


def test_rounds_without_id_codes_follow_series_order():
    rows = _run(
        1,
        [
            (2, "1999-05-08", 3, 1),
            (3, "1999-05-18", 4, 0),
            (4, "1999-05-30", 4, 2),
            (5, "1999-06-16", 4, 1),
        ],
    )
    labelled = playoff_history._add_round_column(pd.DataFrame(rows))
    by_opp = labelled.groupby("opponent_team_id")["playoff_round"].first().to_dict()
    assert by_opp == {2: "First Round", 3: "Second Round", 4: "Conference Finals", 5: "Finals"}

    series = playoff_history._build_series_table(labelled)
    assert series["result"].tolist() == ["Won"] * 4  # 3-1 wins a best-of-five first round


def test_game_id_round_code_wins_over_series_order():
    rows = [_game("0042300401", "2023-24", "2024-06-06", 1, 9, "W")]
    labelled = playoff_history._add_round_column(pd.DataFrame(rows))
    assert labelled["playoff_round"].tolist() == ["Finals"]


def test_best_of_seven_series_needs_four_wins():
    rows = _run(1, [(2, "2024-04-20", 3, 2)], season="2023-24", gid_prefix="0042300100")
    series = playoff_history._build_series_table(
        playoff_history._add_round_column(pd.DataFrame(rows))
    )
    assert series["result"].tolist() == ["In progress"]


def test_play_in_games_are_not_playoff_games(monkeypatch):
    rows = [
        _game("0052300101", "2023-24", "2024-04-16", 1, 2, "W"),
        _game("0042300101", "2023-24", "2024-04-20", 1, 3, "W"),
    ]
    monkeypatch.setattr(
        playoff_history, "load_team_games_for_seasons", lambda seasons, kind: pd.DataFrame(rows)
    )
    games = playoff_history._load_playoff_games(["2023-24"])
    assert games["opponent_team_id"].tolist() == [3]
    assert games["playoff_round"].tolist() == ["First Round"]


@pytest.mark.parametrize(
    ("query", "round_code"),
    [
        ("Celtics conference finals record", "03"),
        ("What is the Bulls Finals record?", "04"),
        ("Celtics record in the second round", "02"),
    ],
)
def test_single_team_round_records_route_without_refusal(query, round_code):
    parsed = parse_query(query)
    assert parsed["route"] == "playoff_history"
    assert parsed["route_kwargs"]["playoff_round"] == round_code
    assert not parsed["route_kwargs"].get("unsupported_filters")
    assert parsed["route_kwargs"]["start_season"] == "1996-97"


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("how did the Lakers do in the 2026 playoffs", "2025-26"),
        ("Lakers series results in the 2024 playoffs", "2023-24"),
        ("Spurs 1999 playoffs series", "1998-99"),
    ],
)
def test_year_named_playoffs_route_to_the_run(query, season):
    parsed = parse_query(query)
    assert parsed["route"] == "playoff_history"
    assert parsed["route_kwargs"]["season"] == season


def test_series_won_is_not_a_game_filter():
    parsed = parse_query("how many playoff series have the Lakers won")
    assert parsed["route"] == "playoff_history"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.fixture_data
@pytest.mark.query
def test_playoff_run_lists_each_series_from_raw_rows():
    games = pd.read_csv(RAW / "2025-26_playoffs.csv", dtype={"game_id": str})
    lakers = games[games["team_abbr"] == "LAL"]
    expected = {}
    for opp, rows in lakers.groupby("opponent_team_name"):
        expected[opp] = (int((rows["wl"] == "W").sum()), int((rows["wl"] == "L").sum()))

    result = execute_natural_query("how did the Lakers do in the 2026 playoffs")
    assert result.result_status == "ok"
    series = result.result.to_dict()["sections"]["series"]
    assert {row["opponent_team_name"]: (row["wins"], row["losses"]) for row in series} == expected
    wins = int((lakers["wl"] == "W").sum())
    losses = int((lakers["wl"] == "L").sum())
    assert result.metadata["answer_phrase"].startswith(
        f"The Los Angeles Lakers went {wins}-{losses} in the 2025-26 playoffs"
    )


@pytest.mark.parametrize(
    ("query", "season", "start_season"),
    [
        ("Lakers titles since 2000", None, "2000-01"),
        ("how many championships have the Spurs won", None, "1996-97"),
        ("Spurs championships", None, "1996-97"),
        ("did the Warriors win the title in 2017", "2016-17", None),
        ("Warriors 2017 championship", "2016-17", None),
    ],
)
def test_team_title_counts_route_to_playoff_history(query, season, start_season):
    parsed = parse_query(query)
    assert parsed["route"] == "playoff_history"
    kwargs = parsed["route_kwargs"]
    assert (kwargs["season"], kwargs["start_season"]) == (season, start_season)
    assert not kwargs.get("playoff_round")


@pytest.mark.parametrize(
    "query",
    [
        "how many rings does lebron have",
        "Celtics division titles",
        "Heat eastern conference titles",
        "which team has won the most titles since 1997",
    ],
)
def test_other_title_counts_stay_refused(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["championship_count"]


def test_titles_phrase_lists_finals_won():
    from nbatools.query_service import _team_titles_phrase

    series = pd.DataFrame(
        [
            {"season": "1998-99", "playoff_round": "Finals", "result": "Won", "start_date": "a"},
            {"season": "2012-13", "playoff_round": "Finals", "result": "Lost", "start_date": "b"},
            {"season": "2013-14", "playoff_round": "Finals", "result": "Won", "start_date": "c"},
            {
                "season": "2014-15",
                "playoff_round": "First Round",
                "result": "Lost",
                "start_date": "d",
            },
        ]
    )
    phrase = _team_titles_phrase(
        "San Antonio Spurs", series, {"start_season": "1996-97", "end_season": "2014-15"}
    )
    assert phrase == (
        "The San Antonio Spurs won 2 titles from 1996-97 to 2014-15 (1998-99, 2013-14), "
        "in 3 Finals appearances."
    )


@pytest.mark.fixture_data
@pytest.mark.query
def test_unfinished_run_is_not_called_a_title_miss():
    result = execute_natural_query("did the Lakers win the title in 2026")
    assert result.result_status == "ok"
    assert result.metadata["answer_phrase"] == (
        "The Los Angeles Lakers have not won a title in 2025-26; "
        "their 2025-26 playoff run is still in progress."
    )


def test_numeric_game_ids_keep_their_round_code():
    # Read as numbers, "0042300401" is 42300401 and "0052300101" is 52300101.
    rows = [
        _game(42300401, "2023-24", "2024-06-06", 1, 9, "W"),
        _game(49600001, "1996-97", "1997-04-25", 1, 2, "W"),
    ]
    labelled = playoff_history._add_round_column(pd.DataFrame(rows))
    assert labelled["playoff_round"].tolist() == ["Finals", "First Round"]
    assert playoff_history._game_id_text(pd.Series([52300101])).str.startswith("005").all()


def test_single_season_title_names_the_finals_opponent():
    from nbatools.query_service import _team_titles_phrase

    series = pd.DataFrame(
        [
            {
                "season": "2016-17",
                "playoff_round": "Finals",
                "opponent_team_name": "Cleveland Cavaliers",
                "wins": 4,
                "losses": 1,
                "result": "Won",
                "start_date": "2017-06-01",
            }
        ]
    )
    phrase = _team_titles_phrase("Golden State Warriors", series, {"season": "2016-17"})
    assert phrase == (
        "The Golden State Warriors won the 2016-17 title, "
        "beating the Cleveland Cavaliers 4-1 in the Finals."
    )
    series.loc[0, ["result", "wins", "losses"]] = ["Lost", 1, 4]
    phrase = _team_titles_phrase("Golden State Warriors", series, {"season": "2016-17"})
    assert phrase.endswith("they lost to the Cleveland Cavaliers 1-4 in the Finals.")
