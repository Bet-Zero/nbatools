from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from nbatools.commands._natural_query_execution import _route_context_filters_for_execution
from nbatools.commands.natural_query import parse_query
from nbatools.commands.pipeline.pull_player_game_starter_roles import (
    build_starter_role_backfill,
)
from nbatools.commands.player_game_finder import build_result as build_player_finder_result
from nbatools.commands.player_game_summary import build_result as build_player_summary_result

pytestmark = [pytest.mark.engine, pytest.mark.query]


def _player_row(
    *,
    game_id: int,
    game_date: str,
    opponent_team_id: int,
    opponent_team_abbr: str,
    opponent_team_name: str,
    pts: int,
) -> dict:
    return {
        "game_id": game_id,
        "season": "2099-00",
        "season_type": "Regular Season",
        "game_date": game_date,
        "team_id": 1,
        "team_abbr": "AAA",
        "team_name": "Alpha",
        "opponent_team_id": opponent_team_id,
        "opponent_team_abbr": opponent_team_abbr,
        "opponent_team_name": opponent_team_name,
        "is_home": 1,
        "is_away": 0,
        "player_id": 10,
        "player_name": "Role Star",
        "starter_flag": 0,
        "start_position": "",
        "minutes": 30,
        "pts": pts,
        "fgm": 8,
        "fga": 15,
        "fg_pct": 0.533,
        "fg3m": 2,
        "fg3a": 5,
        "fg3_pct": 0.4,
        "ftm": 2,
        "fta": 2,
        "ft_pct": 1.0,
        "oreb": 1,
        "dreb": 4,
        "reb": 5,
        "ast": 6,
        "stl": 1,
        "blk": 0,
        "tov": 2,
        "pf": 2,
        "plus_minus": 8,
        "comment": "",
    }


def _team_rows(
    *,
    game_id: int,
    opponent_team_id: int,
    opponent_team_abbr: str,
) -> list[dict]:
    return [
        {
            "game_id": game_id,
            "team_id": 1,
            "team_abbr": "AAA",
            "team_name": "Alpha",
            "opponent_team_id": opponent_team_id,
            "opponent_team_abbr": opponent_team_abbr,
            "minutes": 240,
            "fgm": 40,
            "fga": 85,
            "fta": 20,
            "tov": 12,
            "reb": 44,
            "wl": "W",
        },
        {
            "game_id": game_id,
            "team_id": opponent_team_id,
            "team_abbr": opponent_team_abbr,
            "team_name": f"Opponent {opponent_team_abbr}",
            "opponent_team_id": 1,
            "opponent_team_abbr": "AAA",
            "minutes": 240,
            "fgm": 38,
            "fga": 82,
            "fta": 18,
            "tov": 11,
            "reb": 40,
            "wl": "L",
        },
    ]


def _role_rows(*, trusted: bool = True) -> list[dict]:
    trusted_flag = 1 if trusted else 0
    validation_reason = "" if trusted else "starter_count_not_five"
    starter_count = 5 if trusted else 6
    return [
        {
            "game_id": 1,
            "season": "2099-00",
            "season_type": "Regular Season",
            "team_id": 1,
            "team_abbr": "AAA",
            "player_id": 10,
            "player_name": "Role Star",
            "starter_position_raw": "G",
            "starter_flag": 1,
            "role_source": "boxscore_traditional_v3.position",
            "role_source_trusted": trusted_flag,
            "starter_count_for_team_game": starter_count,
            "role_validation_reason": validation_reason,
        },
        {
            "game_id": 2,
            "season": "2099-00",
            "season_type": "Regular Season",
            "team_id": 1,
            "team_abbr": "AAA",
            "player_id": 10,
            "player_name": "Role Star",
            "starter_position_raw": "",
            "starter_flag": 0,
            "role_source": "boxscore_traditional_v3.position",
            "role_source_trusted": trusted_flag,
            "starter_count_for_team_game": starter_count,
            "role_validation_reason": validation_reason,
        },
        {
            "game_id": 3,
            "season": "2099-00",
            "season_type": "Regular Season",
            "team_id": 1,
            "team_abbr": "AAA",
            "player_id": 10,
            "player_name": "Role Star",
            "starter_position_raw": "F",
            "starter_flag": 1,
            "role_source": "boxscore_traditional_v3.position",
            "role_source_trusted": trusted_flag,
            "starter_count_for_team_game": starter_count,
            "role_validation_reason": validation_reason,
        },
    ]


def _write_role_query_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_role_file: bool = True,
    trusted: bool = True,
) -> None:
    monkeypatch.chdir(tmp_path)

    player_rows = [
        _player_row(
            game_id=1,
            game_date="2099-10-01",
            opponent_team_id=2,
            opponent_team_abbr="BBB",
            opponent_team_name="Beta",
            pts=20,
        ),
        _player_row(
            game_id=2,
            game_date="2099-10-03",
            opponent_team_id=3,
            opponent_team_abbr="CCC",
            opponent_team_name="Gamma",
            pts=14,
        ),
        _player_row(
            game_id=3,
            game_date="2099-10-05",
            opponent_team_id=4,
            opponent_team_abbr="DDD",
            opponent_team_name="Delta",
            pts=28,
        ),
    ]
    team_rows = (
        _team_rows(game_id=1, opponent_team_id=2, opponent_team_abbr="BBB")
        + _team_rows(game_id=2, opponent_team_id=3, opponent_team_abbr="CCC")
        + _team_rows(game_id=3, opponent_team_id=4, opponent_team_abbr="DDD")
    )

    player_path = tmp_path / "data/raw/player_game_stats/2099-00_regular_season.csv"
    team_path = tmp_path / "data/raw/team_game_stats/2099-00_regular_season.csv"
    player_path.parent.mkdir(parents=True, exist_ok=True)
    team_path.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(player_rows).to_csv(player_path, index=False)
    pd.DataFrame(team_rows).to_csv(team_path, index=False)

    if include_role_file:
        role_path = tmp_path / "data/raw/player_game_starter_roles/2099-00_regular_season.csv"
        role_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(_role_rows(trusted=trusted)).to_csv(role_path, index=False)


def _boxscore_player_rows(*, game_id: str, starter_positions: list[str]) -> pd.DataFrame:
    rows = []
    for idx, starter_position in enumerate(starter_positions, start=1):
        rows.append(
            {
                "gameId": game_id,
                "teamId": 1,
                "teamTricode": "AAA",
                "personId": idx,
                "firstName": f"Player{idx}",
                "familyName": "Alpha",
                "position": starter_position,
            }
        )
    return pd.DataFrame(rows)


def test_summary_role_filter_uses_trusted_starter_roles(tmp_path, monkeypatch):
    _write_role_query_fixture(tmp_path, monkeypatch, include_role_file=True, trusted=True)

    result = build_player_summary_result(
        season="2099-00",
        season_type="Regular Season",
        player="Role Star",
        role="starter",
    )

    assert result.summary.iloc[0]["games"] == 2
    assert result.notes == []


def test_finder_role_filter_uses_trusted_starter_roles(tmp_path, monkeypatch):
    _write_role_query_fixture(tmp_path, monkeypatch, include_role_file=True, trusted=True)

    result = build_player_finder_result(
        season="2099-00",
        season_type="Regular Season",
        player="Role Star",
        role="bench",
    )

    assert list(result.games["game_id"]) == [2]
    assert result.notes == []


def test_summary_role_filter_falls_back_when_role_dataset_is_missing(tmp_path, monkeypatch):
    _write_role_query_fixture(tmp_path, monkeypatch, include_role_file=False)

    result = build_player_summary_result(
        season="2099-00",
        season_type="Regular Season",
        player="Role Star",
        role="starter",
    )

    assert result.summary.iloc[0]["games"] == 3
    assert any("role" in note and "unfiltered" in note for note in result.notes)


def test_finder_role_filter_falls_back_when_coverage_is_untrusted(tmp_path, monkeypatch):
    _write_role_query_fixture(tmp_path, monkeypatch, include_role_file=True, trusted=False)

    result = build_player_finder_result(
        season="2099-00",
        season_type="Regular Season",
        player="Role Star",
        role="bench",
    )

    assert list(result.games["game_id"]) == [3, 2, 1]
    assert any("role" in note and "unfiltered" in note for note in result.notes)


def test_build_starter_role_backfill_marks_trusted_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    games_path = tmp_path / "data/raw/games/2099-00_regular_season.csv"
    games_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"game_id": 1}]).to_csv(games_path, index=False)

    with patch(
        "nbatools.commands.pipeline.pull_player_game_starter_roles.fetch_starter_role_rows_for_game",
        return_value=_boxscore_player_rows(
            game_id="0000000001",
            starter_positions=["G", "G", "F", "F", "C", "", "", ""],
        ),
    ):
        df = build_starter_role_backfill("2099-00", "Regular Season")

    assert df["role_source_trusted"].eq(1).all()
    assert df["starter_count_for_team_game"].eq(5).all()
    assert df["role_validation_reason"].fillna("").eq("").all()


def test_build_starter_role_backfill_marks_untrusted_rows_when_count_is_not_five(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    games_path = tmp_path / "data/raw/games/2099-00_regular_season.csv"
    games_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"game_id": 1}]).to_csv(games_path, index=False)

    with patch(
        "nbatools.commands.pipeline.pull_player_game_starter_roles.fetch_starter_role_rows_for_game",
        return_value=_boxscore_player_rows(
            game_id="0000000001",
            starter_positions=["G", "G", "F", "F", "C", "G", "", ""],
        ),
    ):
        df = build_starter_role_backfill("2099-00", "Regular Season")

    assert df["role_source_trusted"].eq(0).all()
    assert df["starter_count_for_team_game"].eq(6).all()
    assert df["role_validation_reason"].eq("starter_count_not_five").all()


def test_supported_role_route_keeps_kwarg_without_transport_note():
    routed, notes = _route_context_filters_for_execution(
        "player_game_finder",
        {"player": "Role Star", "role": "bench"},
    )

    assert routed["role"] == "bench"
    assert not any("role" in note and "unfiltered" in note for note in notes)


def test_parse_query_supported_role_route_no_longer_appends_unfiltered_note():
    parsed = parse_query("Brunson off the bench")

    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["role"] == "bench"
    assert not any("role" in note and "unfiltered" in note for note in parsed.get("notes", []))
