from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands.data_utils import (
    load_play_by_play_events_for_seasons,
    load_player_game_clutch_stats_for_seasons,
    load_team_game_clutch_stats_for_seasons,
    select_trusted_play_by_play_events,
)
from nbatools.commands.pipeline.build_clutch_stats import (
    build_clutch_stats_for_season,
    derive_player_game_clutch_stats,
    derive_team_game_clutch_stats,
)
from nbatools.commands.pipeline.pull_play_by_play_events import (
    build_play_by_play_events_backfill,
    normalize_play_by_play_events,
    parse_clock_seconds_remaining,
)
from nbatools.commands.pipeline.validate_raw import (
    validate_play_by_play_events_df,
    validate_player_game_clutch_stats_df,
)
from nbatools.commands.player_game_finder import build_result as build_player_finder
from nbatools.commands.player_game_summary import build_result as build_player_summary
from nbatools.commands.season_leaders import build_result as build_season_leaders
from nbatools.commands.team_record import build_team_record_result

pytestmark = pytest.mark.engine


def _source_row(
    *,
    game_id: str = "0029900001",
    action_number: int = 1,
    clock: str = "PT04M59.00S",
    period: int = 4,
    team_id: int = 1610612738,
    team_abbr: str = "BOS",
    player_id: int = 1628369,
    player_name: str = "Jayson Tatum",
    score_home: int = 100,
    score_away: int = 98,
) -> dict:
    return {
        "gameId": game_id,
        "actionNumber": action_number,
        "clock": clock,
        "period": period,
        "teamId": team_id,
        "teamTricode": team_abbr,
        "personId": player_id,
        "playerName": player_name,
        "actionType": "2pt",
        "subType": "Jump Shot",
        "description": "Tatum 15' pullup jump shot",
        "scoreHome": score_home,
        "scoreAway": score_away,
    }


def _normalized_pbp_df() -> pd.DataFrame:
    return normalize_play_by_play_events(
        pd.DataFrame(
            [
                _source_row(action_number=1, clock="PT05M00.00S"),
                _source_row(action_number=2, clock="PT04M45.00S", score_home=102),
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        source_pull_date="2099-01-01",
    )


def _clutch_source_events_df() -> pd.DataFrame:
    return normalize_play_by_play_events(
        pd.DataFrame(
            [
                _source_row(action_number=1, clock="PT05M10.00S", score_home=100, score_away=98),
                _source_row(action_number=2, clock="PT04M59.00S", score_home=102, score_away=98),
                _source_row(
                    action_number=3,
                    clock="PT04M30.00S",
                    team_id=1610612743,
                    team_abbr="DEN",
                    player_id=203999,
                    player_name="Nikola Jokic",
                    score_home=102,
                    score_away=101,
                ),
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        source_pull_date="2099-01-01",
    )


def _route_source_events_df() -> pd.DataFrame:
    return normalize_play_by_play_events(
        pd.DataFrame(
            [
                _source_row(
                    game_id="G1",
                    action_number=1,
                    clock="PT04M59.00S",
                    score_home=100,
                    score_away=98,
                ),
                _source_row(
                    game_id="G1",
                    action_number=2,
                    clock="PT04M30.00S",
                    score_home=102,
                    score_away=98,
                ),
                _source_row(
                    game_id="G2",
                    action_number=1,
                    clock="PT04M59.00S",
                    score_home=110,
                    score_away=103,
                ),
            ]
        ),
        season="2099-00",
        season_type="Regular Season",
        source_pull_date="2099-01-01",
    )


def _write_route_source_files(tmp_path) -> None:
    player_dir = tmp_path / "data/raw/player_game_stats"
    team_dir = tmp_path / "data/raw/team_game_stats"
    clutch_player_dir = tmp_path / "data/processed/player_game_clutch_stats"
    clutch_team_dir = tmp_path / "data/processed/team_game_clutch_stats"
    player_dir.mkdir(parents=True)
    team_dir.mkdir(parents=True)
    clutch_player_dir.mkdir(parents=True)
    clutch_team_dir.mkdir(parents=True)

    common_player = {
        "season": "2099-00",
        "season_type": "Regular Season",
        "player_id": 1628369,
        "player_name": "Jayson Tatum",
        "team_id": 1610612738,
        "team_abbr": "BOS",
        "team_name": "Boston Celtics",
        "minutes": 35,
        "fgm": 12,
        "fga": 24,
        "fg3m": 4,
        "fg3a": 9,
        "ftm": 12,
        "fta": 13,
        "oreb": 1,
        "dreb": 7,
        "reb": 8,
        "ast": 5,
        "stl": 1,
        "blk": 0,
        "tov": 2,
        "pf": 2,
        "plus_minus": 6,
    }
    player_rows = [
        {
            **common_player,
            "game_id": "G1",
            "game_date": "2099-01-01",
            "opponent_team_id": 1610612743,
            "opponent_team_abbr": "DEN",
            "opponent_team_name": "Denver Nuggets",
            "is_home": 1,
            "is_away": 0,
            "wl": "W",
            "pts": 40,
        },
        {
            **common_player,
            "game_id": "G2",
            "game_date": "2099-01-03",
            "opponent_team_id": 1610612747,
            "opponent_team_abbr": "LAL",
            "opponent_team_name": "Los Angeles Lakers",
            "is_home": 0,
            "is_away": 1,
            "wl": "L",
            "pts": 31,
        },
    ]
    common_team = {
        "season": "2099-00",
        "season_type": "Regular Season",
        "team_id": 1610612738,
        "team_abbr": "BOS",
        "team_name": "Boston Celtics",
        "minutes": 240,
        "fgm": 44,
        "fga": 90,
        "fg3m": 13,
        "fg3a": 35,
        "ftm": 17,
        "fta": 20,
        "oreb": 9,
        "dreb": 33,
        "reb": 42,
        "ast": 27,
        "stl": 7,
        "blk": 5,
        "tov": 11,
        "pf": 18,
        "plus_minus": 5,
    }
    team_rows = [
        {
            **common_team,
            "game_id": "G1",
            "game_date": "2099-01-01",
            "opponent_team_id": 1610612743,
            "opponent_team_abbr": "DEN",
            "opponent_team_name": "Denver Nuggets",
            "is_home": 1,
            "is_away": 0,
            "wl": "W",
            "pts": 118,
        },
        {
            **common_team,
            "game_id": "G2",
            "game_date": "2099-01-03",
            "opponent_team_id": 1610612747,
            "opponent_team_abbr": "LAL",
            "opponent_team_name": "Los Angeles Lakers",
            "is_home": 0,
            "is_away": 1,
            "wl": "L",
            "pts": 110,
        },
    ]
    pd.DataFrame(player_rows).to_csv(player_dir / "2099-00_regular_season.csv", index=False)
    pd.DataFrame(team_rows).to_csv(team_dir / "2099-00_regular_season.csv", index=False)
    derive_player_game_clutch_stats(_route_source_events_df()).to_csv(
        clutch_player_dir / "2099-00_regular_season.csv", index=False
    )
    derive_team_game_clutch_stats(_route_source_events_df()).to_csv(
        clutch_team_dir / "2099-00_regular_season.csv", index=False
    )


def test_parse_clock_seconds_remaining_accepts_iso_and_scoreboard_formats():
    assert parse_clock_seconds_remaining("PT04M59.00S") == 299.0
    assert parse_clock_seconds_remaining("4:59") == 299.0


def test_normalize_play_by_play_events_marks_trusted_and_parses_score_state():
    df = _normalized_pbp_df()

    assert df["pbp_source_trusted"].eq(1).all()
    assert df["pbp_validation_reason"].fillna("").eq("").all()
    assert df["clock_seconds_remaining"].tolist() == [300.0, 285.0]
    assert df["score_home"].tolist() == [100, 102]
    assert df["score_away"].tolist() == [98, 98]


def test_normalize_play_by_play_events_rejects_unparseable_clock():
    with pytest.raises(ValueError, match="clock"):
        normalize_play_by_play_events(
            pd.DataFrame([_source_row(clock="late")]),
            season="2099-00",
            season_type="Regular Season",
            source_pull_date="2099-01-01",
        )


def test_validate_play_by_play_events_rejects_duplicate_event_keys():
    df = pd.concat([_normalized_pbp_df(), _normalized_pbp_df()], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate"):
        validate_play_by_play_events_df(df)


def test_validate_play_by_play_events_rejects_out_of_order_actions():
    df = _normalized_pbp_df().sort_values("action_number", ascending=False).reset_index(drop=True)

    with pytest.raises(ValueError, match="action_number order"):
        validate_play_by_play_events_df(df)


def test_load_play_by_play_events_for_seasons_requires_all_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="play_by_play_events"):
        load_play_by_play_events_for_seasons(["2099-00"], "Regular Season")


def test_load_play_by_play_events_for_seasons_accepts_valid_dataset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "data/raw/play_by_play_events"
    out_dir.mkdir(parents=True)
    _normalized_pbp_df().to_csv(out_dir / "2099-00_regular_season.csv", index=False)

    loaded = load_play_by_play_events_for_seasons(["2099-00"], "Regular Season")

    assert len(loaded) == 2
    assert loaded["game_id"].astype(str).unique().tolist() == ["0029900001"]


def test_select_trusted_play_by_play_events_reports_coverage_failures():
    trusted = _normalized_pbp_df()
    untrusted = trusted.copy()
    untrusted["game_id"] = "0029900002"
    untrusted["pbp_source_trusted"] = 0
    untrusted["pbp_validation_reason"] = "missing_game_events"
    df = pd.concat([trusted, untrusted], ignore_index=True)

    selected, failures = select_trusted_play_by_play_events(df)

    assert set(selected["game_id"].astype(str)) == {"0029900001"}
    assert failures == ["missing_game_events"]


def test_build_play_by_play_events_backfill_uses_game_sources(monkeypatch):
    from nbatools.commands.pipeline import pull_play_by_play_events as puller

    monkeypatch.setattr(puller, "game_ids_for_season", lambda season, season_type: ["0029900001"])
    monkeypatch.setattr(
        puller,
        "fetch_play_by_play_events_for_game",
        lambda game_id: pd.DataFrame([_source_row(game_id=game_id)]),
    )

    df = build_play_by_play_events_backfill("2099-00", "Regular Season")

    assert len(df) == 1
    assert df["game_id"].astype(str).tolist() == ["0029900001"]
    assert df["pbp_source_trusted"].tolist() == [1]


def test_derive_player_and_team_game_clutch_stats_from_trusted_events():
    events = _clutch_source_events_df()

    player = derive_player_game_clutch_stats(events)
    team = derive_team_game_clutch_stats(events)

    assert player["player_name"].tolist() == ["Jayson Tatum", "Nikola Jokic"]
    assert player["pts"].tolist() == [2, 3]
    assert player["clutch_events"].tolist() == [1, 1]
    assert team["team_abbr"].tolist() == ["BOS", "DEN"]
    assert team["pts"].tolist() == [2, 3]
    assert team["clutch_source_trusted"].eq(1).all()


def test_validate_player_game_clutch_stats_rejects_duplicate_keys():
    player = derive_player_game_clutch_stats(_clutch_source_events_df())
    duplicated = pd.concat([player, player.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate"):
        validate_player_game_clutch_stats_df(duplicated)


def test_load_clutch_stats_for_seasons_accepts_valid_processed_datasets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    player_dir = tmp_path / "data/processed/player_game_clutch_stats"
    team_dir = tmp_path / "data/processed/team_game_clutch_stats"
    player_dir.mkdir(parents=True)
    team_dir.mkdir(parents=True)
    player = derive_player_game_clutch_stats(_clutch_source_events_df())
    team = derive_team_game_clutch_stats(_clutch_source_events_df())
    player.to_csv(player_dir / "2099-00_regular_season.csv", index=False)
    team.to_csv(team_dir / "2099-00_regular_season.csv", index=False)

    loaded_player = load_player_game_clutch_stats_for_seasons(["2099-00"], "Regular Season")
    loaded_team = load_team_game_clutch_stats_for_seasons(["2099-00"], "Regular Season")

    assert len(loaded_player) == 2
    assert len(loaded_team) == 2


def test_build_clutch_stats_for_season_uses_trusted_raw_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_dir = tmp_path / "data/raw/play_by_play_events"
    raw_dir.mkdir(parents=True)
    _clutch_source_events_df().to_csv(raw_dir / "2099-00_regular_season.csv", index=False)

    player, team = build_clutch_stats_for_season("2099-00", "Regular Season")

    assert player["pts"].sum() == 5
    assert team["pts"].sum() == 5


def test_clutch_player_summary_uses_derived_clutch_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_route_source_files(tmp_path)

    result = build_player_summary(
        season="2099-00",
        season_type="Regular Season",
        player="Jayson Tatum",
        clutch=True,
    )

    assert result.notes == []
    assert result.summary.loc[0, "games"] == 1
    assert result.summary.loc[0, "pts_sum"] == 2
    assert result.summary.loc[0, "clutch_events_sum"] == 2


def test_clutch_player_finder_filters_to_trusted_clutch_games(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_route_source_files(tmp_path)

    result = build_player_finder(
        season="2099-00",
        season_type="Regular Season",
        player="Jayson Tatum",
        clutch=True,
    )

    assert result.notes == []
    assert result.games["game_id"].tolist() == ["G1"]
    assert result.games["pts"].tolist() == [2]


def test_clutch_team_record_uses_derived_team_clutch_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_route_source_files(tmp_path)

    result = build_team_record_result(
        season="2099-00",
        season_type="Regular Season",
        team="BOS",
        clutch=True,
    )

    assert result.notes == []
    assert result.summary.loc[0, "games"] == 1
    assert result.summary.loc[0, "wins"] == 1
    assert result.summary.loc[0, "pts_avg"] == 2


def test_clutch_season_leaders_uses_derived_clutch_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_route_source_files(tmp_path)

    result = build_season_leaders(
        season="2099-00",
        season_type="Regular Season",
        stat="pts",
        clutch=True,
        min_games=1,
    )

    assert result.notes == []
    assert result.leaders.loc[0, "player_name"] == "Jayson Tatum"
    assert result.leaders.loc[0, "pts_per_game"] == 2
    assert result.leaders.loc[0, "clutch_events"] == 2


def test_clutch_route_falls_back_unfiltered_when_coverage_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_route_source_files(tmp_path)
    for path in (tmp_path / "data/processed/player_game_clutch_stats").glob("*.csv"):
        path.unlink()

    result = build_player_finder(
        season="2099-00",
        season_type="Regular Season",
        player="Jayson Tatum",
        clutch=True,
    )

    assert len(result.games) == 2
    assert any("clutch" in note and "unfiltered" in note for note in result.notes)
