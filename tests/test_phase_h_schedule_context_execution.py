from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._natural_query_execution import _route_context_filters_for_execution
from nbatools.commands.data_utils import load_schedule_context_features_for_seasons
from nbatools.commands.natural_query import parse_query
from nbatools.commands.pipeline.build_schedule_context_features import (
    build_schedule_context_features,
)
from nbatools.commands.pipeline.validate_raw import validate_schedule_context_features_df
from nbatools.commands.player_game_summary import build_result as build_player_summary_result
from nbatools.commands.team_record import build_team_record_result

pytestmark = [pytest.mark.engine, pytest.mark.query]


def _team_game_row(
    *,
    game_id: int,
    game_date: str,
    team_id: int,
    team_abbr: str,
    team_name: str,
    opponent_team_id: int,
    opponent_team_abbr: str,
    opponent_team_name: str,
    is_home: int,
    wl: str,
    pts: int,
    plus_minus: int,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": team_id,
        "team_abbr": team_abbr,
        "team_name": team_name,
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_team_abbr,
        "opponent_team_name": opponent_team_name,
        "is_home": is_home,
        "is_away": 0 if is_home else 1,
        "wl": wl,
        "minutes": 240,
        "pts": pts,
        "fgm": 40,
        "fga": 84,
        "fg_pct": 0.476,
        "fg3m": 12,
        "fg3a": 32,
        "fg3_pct": 0.375,
        "ftm": 18,
        "fta": 22,
        "ft_pct": 0.818,
        "oreb": 9,
        "dreb": 34,
        "reb": 43,
        "ast": 26,
        "stl": 7,
        "blk": 4,
        "tov": 12,
        "pf": 19,
        "plus_minus": plus_minus,
    }


def _paired_rows(
    *,
    game_id: int,
    game_date: str,
    team_id: int,
    team_abbr: str,
    team_name: str,
    opponent_team_id: int,
    opponent_team_abbr: str,
    opponent_team_name: str,
    team_pts: int,
    opponent_pts: int,
) -> list[dict]:
    margin = team_pts - opponent_pts
    return [
        _team_game_row(
            game_id=game_id,
            game_date=game_date,
            team_id=team_id,
            team_abbr=team_abbr,
            team_name=team_name,
            opponent_team_id=opponent_team_id,
            opponent_team_abbr=opponent_team_abbr,
            opponent_team_name=opponent_team_name,
            is_home=1,
            wl="W" if margin > 0 else "L",
            pts=team_pts,
            plus_minus=margin,
        ),
        _team_game_row(
            game_id=game_id,
            game_date=game_date,
            team_id=opponent_team_id,
            team_abbr=opponent_team_abbr,
            team_name=opponent_team_name,
            opponent_team_id=team_id,
            opponent_team_abbr=team_abbr,
            opponent_team_name=team_name,
            is_home=0,
            wl="L" if margin > 0 else "W",
            pts=opponent_pts,
            plus_minus=-margin,
        ),
    ]


def _player_row(*, game_id: int, game_date: str, opponent_team_id: int, pts: int) -> dict:
    opponent_lookup = {
        2: ("BBB", "Beta"),
        3: ("CCC", "Gamma"),
        4: ("DDD", "Delta"),
    }
    opponent_abbr, opponent_name = opponent_lookup[opponent_team_id]
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": 1,
        "team_abbr": "AAA",
        "team_name": "Alpha",
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_abbr,
        "opponent_team_name": opponent_name,
        "is_home": 1,
        "is_away": 0,
        "player_id": 10,
        "player_name": "Schedule Star",
        "starter_flag": 1,
        "start_position": "G",
        "minutes": 32,
        "pts": pts,
        "fgm": 8,
        "fga": 17,
        "fg_pct": 0.471,
        "fg3m": 3,
        "fg3a": 7,
        "fg3_pct": 0.429,
        "ftm": 4,
        "fta": 4,
        "ft_pct": 1.0,
        "oreb": 1,
        "dreb": 5,
        "reb": 6,
        "ast": 7,
        "stl": 1,
        "blk": 0,
        "tov": 2,
        "pf": 2,
        "plus_minus": 5,
        "comment": "",
        "wl": "W",
    }


def _write_schedule_context_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    build_context: bool = True,
    trusted_national_tv: bool = True,
) -> None:
    monkeypatch.chdir(tmp_path)

    team_rows = (
        _paired_rows(
            game_id=1,
            game_date="2099-10-01",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            team_pts=110,
            opponent_pts=100,
        )
        + _paired_rows(
            game_id=2,
            game_date="2099-10-02",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=3,
            opponent_team_abbr="CCC",
            opponent_team_name="Gamma",
            team_pts=101,
            opponent_pts=103,
        )
        + _paired_rows(
            game_id=4,
            game_date="2099-10-04",
            team_id=4,
            team_abbr="DDD",
            team_name="Delta",
            opponent_team_id=5,
            opponent_team_abbr="EEE",
            opponent_team_name="Epsilon",
            team_pts=115,
            opponent_pts=108,
        )
        + _paired_rows(
            game_id=3,
            game_date="2099-10-05",
            team_id=1,
            team_abbr="AAA",
            team_name="Alpha",
            opponent_team_id=4,
            opponent_team_abbr="DDD",
            opponent_team_name="Delta",
            team_pts=120,
            opponent_pts=116,
        )
    )
    player_rows = [
        _player_row(game_id=1, game_date="2099-10-01", opponent_team_id=2, pts=18),
        _player_row(game_id=2, game_date="2099-10-02", opponent_team_id=3, pts=28),
        _player_row(game_id=3, game_date="2099-10-05", opponent_team_id=4, pts=35),
    ]
    national_tv = "ESPN" if trusted_national_tv else ""
    schedule_rows = [
        {"game_id": 1, "season": "2099-00", "season_type": "Regular Season", "national_tv": ""},
        {
            "game_id": 2,
            "season": "2099-00",
            "season_type": "Regular Season",
            "national_tv": national_tv,
        },
        {"game_id": 3, "season": "2099-00", "season_type": "Regular Season", "national_tv": ""},
        {"game_id": 4, "season": "2099-00", "season_type": "Regular Season", "national_tv": ""},
    ]

    team_path = tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv"
    player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
    schedule_path = tmp_path / "data/raw/schedule/2099-00_regular_season.csv"
    team_path.parent.mkdir(parents=True, exist_ok=True)
    player_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(team_rows).to_csv(team_path, index=False)
    pd.DataFrame(player_rows).to_csv(player_path, index=False)
    pd.DataFrame(schedule_rows).to_csv(schedule_path, index=False)

    if build_context:
        context_path = (
            tmp_path / "data/processed/schedule_context_features/2099-00_regular_season.csv"
        )
        context_path.parent.mkdir(parents=True, exist_ok=True)
        build_schedule_context_features("2099-00", "Regular Season").to_csv(
            context_path, index=False
        )


def test_build_schedule_context_features_derives_core_fields(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch, trusted_national_tv=True)

    features = build_schedule_context_features("2099-00", "Regular Season")
    aaa = features[features["team_abbr"] == "AAA"].sort_values("game_id")

    assert list(aaa["game_id"]) == [1, 2, 3]
    assert aaa.loc[aaa["game_id"] == 2, "rest_days"].iloc[0] == 0
    assert aaa.loc[aaa["game_id"] == 2, "back_to_back"].iloc[0] == 1
    assert aaa.loc[aaa["game_id"] == 2, "one_possession"].iloc[0] == 1
    assert aaa.loc[aaa["game_id"] == 2, "nationally_televised"].iloc[0] == 1
    assert aaa.loc[aaa["game_id"] == 3, "rest_advantage"].iloc[0] == "advantage"


def test_schedule_context_loader_and_validator_accept_valid_dataset(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch)

    loaded = load_schedule_context_features_for_seasons(["2099-00"], "Regular Season")
    validated = validate_schedule_context_features_df(loaded)

    assert not loaded.empty
    assert validated["schedule_context_source_trusted"].eq(1).all()


def test_schedule_context_validator_rejects_invalid_flags(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch)
    loaded = load_schedule_context_features_for_seasons(["2099-00"], "Regular Season")
    loaded.loc[loaded.index[0], "back_to_back"] = 2

    with pytest.raises(ValueError, match="back_to_back"):
        validate_schedule_context_features_df(loaded)


def test_team_record_filters_back_to_back_and_rest_advantage(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch)

    b2b = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        back_to_back=True,
    )
    rest_advantage = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        rest_days="advantage",
    )

    assert b2b.summary.iloc[0]["games"] == 1
    assert b2b.summary.iloc[0]["losses"] == 1
    assert b2b.notes == []
    assert rest_advantage.summary.iloc[0]["games"] == 1
    assert rest_advantage.summary.iloc[0]["wins"] == 1
    assert rest_advantage.notes == []


def test_player_summary_filters_one_possession_and_national_tv(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch, trusted_national_tv=True)

    one_possession = build_player_summary_result(
        season="2099-00",
        season_type="Regular Season",
        player="Schedule Star",
        one_possession=True,
    )
    national_tv = build_player_summary_result(
        season="2099-00",
        season_type="Regular Season",
        player="Schedule Star",
        nationally_televised=True,
    )

    assert one_possession.summary.iloc[0]["games"] == 1
    assert one_possession.summary.iloc[0]["pts_avg"] == 28
    assert one_possession.notes == []
    assert national_tv.summary.iloc[0]["games"] == 1
    assert national_tv.summary.iloc[0]["pts_avg"] == 28
    assert national_tv.notes == []


def test_schedule_context_filters_fall_back_when_dataset_missing(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch, build_context=False)

    result = build_player_summary_result(
        season="2099-00",
        season_type="Regular Season",
        player="Schedule Star",
        back_to_back=True,
    )

    assert result.summary.iloc[0]["games"] == 3
    assert any("back_to_back" in note and "unfiltered" in note for note in result.notes)


def test_national_tv_filter_falls_back_when_source_is_placeholder(tmp_path, monkeypatch):
    _write_schedule_context_fixture(tmp_path, monkeypatch, trusted_national_tv=False)

    result = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="AAA",
        nationally_televised=True,
    )

    assert result.summary.iloc[0]["games"] == 3
    assert any("national_tv" in note and "unfiltered" in note for note in result.notes)


def test_supported_schedule_context_route_keeps_kwargs_without_transport_note():
    routed, notes = _route_context_filters_for_execution(
        "team_record",
        {"team": "AAA", "back_to_back": True, "rest_days": 0},
    )

    assert routed["back_to_back"] is True
    assert routed["rest_days"] == 0
    assert not any("schedule/context" in note or "unfiltered" in note for note in notes)


def test_parse_query_supported_schedule_context_route_has_no_unfiltered_note():
    parsed = parse_query("Celtics record on back-to-backs")

    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["back_to_back"] is True
    assert not any(
        "back_to_back" in note and "unfiltered" in note for note in parsed.get("notes", [])
    )
