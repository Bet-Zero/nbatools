"""Explicit synthetic game-day evidence; missing appearances are never proof."""

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands.data_utils import filter_without_player
from nbatools.data_source import reset_data_source_cache

pytestmark = [pytest.mark.engine, pytest.mark.fixture_data]


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setattr(observations, "player_ids_for_name", lambda name: set())
    reset_data_source_cache()
    rows = []
    for game, date in [(22500002, "2025-10-21"), (22500003, "2025-10-22")]:
        for pid, name, state in [
            (2544, "LeBron James", "did_not_play"),
            (1628467, "Maxi Kleber", "did_not_play"),
            (1629029, "Luka Doncic", "played"),
        ]:
            rows.append(
                dict(
                    game_id=f"{game:010d}",
                    game_date=date,
                    season="2025-26",
                    season_type="Regular Season",
                    team_id=1610612747,
                    player_id=pid,
                    player_name=name,
                    participation_state=state,
                    coverage_scope="listed_player_rows_only",
                    source="nba_official_finalbox:20251021_GSWLAL",
                    source_sha256="a" * 64,
                )
            )
    path = tmp_path / "data/raw/player_game_availability/2025-26_regular_season.csv"
    path.parent.mkdir(parents=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    candidates = pd.DataFrame(
        [
            dict(game_id=22500002, game_date="2025-10-21", team_id=1610612747, pts=109, wl="L"),
            dict(game_id=22500003, game_date="2025-10-22", team_id=1610612747, pts=111, wl="W"),
        ]
    )
    yield candidates, frame, path
    reset_data_source_cache()


def apply(rows, names):
    return filter_without_player(rows, names, ["2025-26"], "Regular Season", team="LAL")


def test_dnp_without_any_player_stat_appearance(source):
    candidates, _, _ = source
    result = apply(candidates.iloc[:1], "LeBron James and Maxi Kleber")
    assert result.game_id.tolist() == [22500002]
    assert result.pts.sum() == 109
    assert result.wl.tolist() == ["L"]


def test_explicit_played_proves_empty_sample(source):
    assert apply(source[0], "Luka Doncic").empty


@pytest.mark.parametrize("damage", ["missing", "unknown", "wrong_team", "wrong_date", "duplicate"])
def test_unqualified_observation_never_returns_partial_answer(source, damage):
    candidates, rows, path = source
    mask = rows.player_name.eq("LeBron James") & rows.game_id.eq("0022500003")
    if damage == "missing":
        rows = rows.loc[~mask]
    elif damage == "unknown":
        rows.loc[mask, "participation_state"] = "unknown"
    elif damage == "wrong_team":
        rows.loc[mask, "team_id"] = 1610612744
    elif damage == "wrong_date":
        rows.loc[mask, "game_date"] = "2025-10-23"
    else:
        rows = pd.concat([rows, rows.loc[mask]])
    rows.to_csv(path, index=False)
    with pytest.raises(ValueError):
        apply(candidates, "LeBron James")


def test_first_false_predicate_cannot_hide_missing_second(source):
    candidates, rows, path = source
    rows = rows.loc[~rows.player_name.eq("Maxi Kleber")]
    rows.to_csv(path, index=False)
    with pytest.raises(ValueError):
        apply(candidates, "Luka Doncic and Maxi Kleber")


def test_opposite_team_is_not_same_team_absence(source):
    candidates = source[0].copy()
    candidates.team_id = 1610612744
    with pytest.raises(ValueError):
        apply(candidates, "LeBron James")


def test_shared_team_record_consumer(source, monkeypatch):
    from nbatools.commands import team_record

    rows = source[0].iloc[:1].copy()
    rows["season"] = "2025-26"
    rows["season_type"] = "Regular Season"
    rows["team_abbr"] = "LAL"
    rows["team_name"] = "Los Angeles Lakers"
    monkeypatch.setattr(team_record, "load_team_games_for_seasons", lambda *a: rows.copy())
    result = team_record.build_team_record_result(
        team="LAL", season="2025-26", without_player="LeBron James and Maxi Kleber"
    )
    actual = result.summary.iloc[0]
    assert (actual.games, actual.wins, actual.losses, actual.pts_avg) == (1, 0, 1, 109)


def test_same_player_on_both_teams_rejected(source):
    candidates, rows, path = source
    other = rows.iloc[:1].copy()
    other.team_id = 1610612744
    other.participation_state = "played"
    pd.concat([rows, other]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Duplicate"):
        apply(candidates, "LeBron James")


def test_explicit_opponent_context_resolves_other_side(source):
    candidates = source[0].copy()
    candidates["opponent_team_id"] = candidates.team_id
    candidates.team_id = 1610612744
    result = filter_without_player(
        candidates, "LeBron James", ["2025-26"], "Regular Season", team="GSW", opponent="LAL"
    )
    assert result.game_id.tolist() == candidates.game_id.tolist()


def test_positive_minutes_can_prove_played_without_report(source, monkeypatch):
    from nbatools.commands import data_utils

    candidates, rows, path = source
    path.unlink()
    played = rows.loc[rows.player_name.eq("LeBron James")].assign(minutes=31.0)
    monkeypatch.setattr(data_utils, "load_player_games_for_seasons", lambda *a: played)
    assert apply(candidates, "LeBron James").empty


def test_positive_rows_never_prove_absence_in_another_game(source, monkeypatch):
    from nbatools.commands import data_utils

    candidates, rows, path = source
    path.unlink()
    played = rows.loc[rows.player_name.eq("LeBron James")].iloc[:1].assign(minutes=31.0)
    monkeypatch.setattr(data_utils, "load_player_games_for_seasons", lambda *a: played)
    with pytest.raises(ValueError, match="coverage"):
        apply(candidates, "LeBron James")


def test_positive_minutes_conflicting_with_explicit_dnp_rejects(source, monkeypatch):
    from nbatools.commands import data_utils

    candidates, rows, _ = source
    played = rows.loc[rows.player_name.eq("LeBron James")].assign(minutes=31.0)
    monkeypatch.setattr(data_utils, "load_player_games_for_seasons", lambda *a: played)
    with pytest.raises(ValueError, match="Contradictory"):
        apply(candidates, "LeBron James")


@pytest.mark.parametrize("minutes", [0, -1, float("nan")])
def test_nonpositive_minutes_cannot_qualify_absence(source, monkeypatch, minutes):
    from nbatools.commands import data_utils

    candidates, rows, path = source
    path.unlink()
    played = rows.loc[rows.player_name.eq("LeBron James")].assign(minutes=minutes)
    monkeypatch.setattr(data_utils, "load_player_games_for_seasons", lambda *a: played)
    with pytest.raises(ValueError):
        apply(candidates, "LeBron James")
