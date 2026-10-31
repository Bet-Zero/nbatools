"""Synthetic listed identities without appearances; identity is not coverage."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]
NAME = "Sample Prospect"
SEASON = "2025-26"


@pytest.fixture
def listed_root(tmp_path, monkeypatch):
    root = tmp_path / "fx"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    stats = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(stats)
    # A different indexed Prospect must not own the source-only condition.
    players.loc[players.player_name.eq("Austin Reaves"), "player_name"] = "Other Prospect"
    players.to_csv(stats, index=False)
    teams = pd.read_csv(root / "data/raw/team_game_stats/2025-26_regular_season.csv")
    games = teams.loc[teams.team_abbr.eq("LAL")].sort_values("game_date").iloc[:2].copy()
    rows = games[["game_id", "game_date", "team_id"]].copy()
    rows = rows.assign(
        season=SEASON,
        season_type="Regular Season",
        player_id=999001,
        player_name=NAME,
        participation_state=["did_not_play", "played"],
        coverage_scope="listed_player_rows_only",
        source="nba_stats_structured_archive:" + "a" * 40 + ":0022500001",
        source_sha256="b" * 64,
    )
    target = root / "data/raw/player_game_availability/2025-26_regular_season.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(target, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield root, target, rows, games
    reset_data_source_cache()


def bounded(query, games):
    day = games.game_date.iloc[0]
    return f"{query} in {SEASON} from {day} to {day}"


@pytest.mark.parametrize(
    "condition",
    [
        "without Sample Prospect",
        "while Sample Prospect did not play",
        "when Sample Prospect was out",
    ],
)
def test_source_only_condition_preserves_team_and_exact_game(listed_root, condition):
    _, _, _, games = listed_root
    query = bounded(f"Lakers record {condition}", games)
    parsed = parse_query(query)
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["without_player"] == NAME
    assert not parsed.get("entity_ambiguity")
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    sections = result.result.to_dict()["sections"]
    expected = games.iloc[0]
    summary = sections["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
        1,
        int(expected.wl == "W"),
        int(expected.wl == "L"),
        expected.pts,
    )
    assert [int(row["game_id"]) for row in sections["game_log"]] == [int(expected.game_id)]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with at least 1 point without Sample Prospect",
        "Without Sample Prospect, LeBron James games with at least 1 point",
    ],
)
def test_source_condition_never_replaces_primary_player(listed_root, query):
    root, _, _, games = listed_root
    query = bounded(query, games)
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["player"] == "LeBron James"
    assert parsed["route_kwargs"]["without_player"] == NAME
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    actual = result.result.to_dict()["sections"]["game_log"]
    expected = pd.read_csv(root / "data/raw/player_game_stats/2025-26_regular_season.csv")
    expected = expected.loc[
        expected.player_name.eq("LeBron James") & expected.game_id.eq(games.game_id.iloc[0])
    ].iloc[0]
    assert [(int(r["game_id"]), r["player_name"], r["pts"]) for r in actual] == [
        (int(expected.game_id), "LeBron James", expected.pts)
    ]


def test_identity_does_not_supply_missing_game_coverage_or_medical_state(listed_root):
    _, _, _, games = listed_root
    result = execute_natural_query(f"Lakers record without {NAME} in {SEASON}")
    assert result.result_status == "no_result"
    for condition in [f"when {NAME} was injured", f"without {NAME} and Blorg Example"]:
        result = execute_natural_query(bounded(f"Lakers record {condition}", games))
        assert result.result_status != "ok", result.metadata


def test_source_identity_is_scoped_and_not_a_primary_or_surname_index(listed_root):
    assert (
        observations.resolve_observed_name(NAME.lower(), [SEASON], "Regular Season").resolved
        == NAME
    )
    assert not observations.resolve_observed_name(
        "Prospect", [SEASON], "Regular Season"
    ).is_confident
    assert not observations.resolve_observed_name(NAME, ["2024-25"], "Regular Season").is_confident
    assert not observations.resolve_observed_name(NAME, [SEASON], "Playoffs").is_confident
    assert not observations.resolve_observed_name(
        NAME + " extra", [SEASON], "Regular Season"
    ).is_confident
    parsed = parse_query(f"{NAME} stats in {SEASON}")
    assert parsed.get("route_kwargs", {}).get("player") != NAME


@pytest.mark.parametrize("conflict", ["observed", "index"])
def test_duplicate_full_name_identity_is_unresolved(listed_root, monkeypatch, conflict):
    _, target, rows, games = listed_root
    if conflict == "observed":
        other = rows.copy().assign(player_id=999002)
        pd.concat([rows, other]).to_csv(target, index=False)
        reset_data_source_cache()
    else:
        monkeypatch.setattr(observations, "player_ids_for_name", lambda name: {"999002"})
    resolution = observations.resolve_observed_name(NAME, [SEASON], "Regular Season")
    assert resolution.is_ambiguous
    result = execute_natural_query(bounded(f"Lakers record without {NAME}", games))
    assert result.result_status != "ok", result.metadata


def test_unknown_state_and_opposite_side_remain_execution_checks(listed_root):
    _, target, rows, games = listed_root
    for changed in [rows.assign(participation_state="unknown"), rows.assign(team_id=1610612738)]:
        changed.to_csv(target, index=False)
        reset_data_source_cache()
        assert observations.resolve_observed_name(NAME, [SEASON], "Regular Season").resolved == NAME
        result = execute_natural_query(bounded(f"Lakers record without {NAME}", games))
        assert result.result_status != "ok", result.metadata
