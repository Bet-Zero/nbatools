"""Offline source-scope and rollover safety checks; no network in ordinary CI."""

import copy

import pytest

from tools.cloud_season_sources import check_parameters, check_schedule, qualify


def schedule():
    return {
        "leagueSchedule": {
            "seasonYear": "2026-27",
            "leagueId": "00",
            "gameDates": [
                {
                    "games": [
                        {
                            "gameId": "0022600001",
                            "gameStatus": 1,
                            "gameDateEst": "2026-10-20T00:00:00Z",
                            "homeTeam": {"teamId": 1},
                            "awayTeam": {"teamId": 2},
                        },
                        {
                            "gameId": "0022601201",
                            "gameStatus": 1,
                            "gameDateEst": "2026-12-04T00:00:00Z",
                            "homeTeam": {"teamId": 0},
                            "awayTeam": {"teamId": 0},
                        },
                    ]
                }
            ],
        }
    }


def test_rollover_keeps_future_and_tbd_out_of_completed_game_contract():
    result = check_schedule(schedule(), "2026-27")
    assert result["regular_games"] == 2 and result["final_regular_games"] == 0
    assert result["unresolved_matchups"] == 1
    assert "planning only" in result["scope"]


@pytest.mark.parametrize(
    "mutation", ["season", "duplicate", "self", "final_tbd", "status", "preseason_only"]
)
def test_untrustworthy_schedule_cannot_establish_rollover(mutation):
    document = schedule()
    league = document["leagueSchedule"]
    games = league["gameDates"][0]["games"]
    if mutation == "season":
        league["seasonYear"] = "2025-26"
    elif mutation == "duplicate":
        games.append(copy.deepcopy(games[0]))
    elif mutation == "self":
        games[0]["awayTeam"]["teamId"] = 1
    elif mutation == "final_tbd":
        games[1]["gameStatus"] = 3
    elif mutation == "status":
        games[0]["gameStatus"] = 99
    elif mutation == "preseason_only":
        for game in games:
            game["gameId"] = game["gameId"].replace("00226", "00126")
    with pytest.raises(ValueError):
        check_schedule(document, "2026-27")


@pytest.mark.parametrize("actual", [None, "2025-26", "", "2026"])
def test_old_or_omitted_season_never_becomes_fresh_by_filename(actual):
    with pytest.raises(ValueError):
        check_parameters({"parameters": {"Season": actual}}, {"Season": "2026-27"})


@pytest.mark.parametrize(
    "change",
    [
        {"Period": 1},
        {"PerMode": "Totals"},
        {"DateFrom": "01/01/2026"},
        {"MeasureType": "Base"},
        {"TeamID": 1},
    ],
)
def test_filters_and_statistical_bases_cannot_be_silently_substituted(change):
    expected = {
        "Season": "2025-26",
        "Period": 0,
        "PerMode": "PerGame",
        "DateFrom": "",
        "MeasureType": "Advanced",
        "TeamID": 0,
    }
    with pytest.raises(ValueError):
        check_parameters({"parameters": expected | change}, expected)


def test_stage_cannot_overwrite_previous_season(tmp_path):
    previous = tmp_path / "accepted"
    previous.mkdir()
    marker = previous / "keep.txt"
    marker.write_text("last good")
    with pytest.raises(FileExistsError):
        qualify(previous)
    assert marker.read_text() == "last good"
