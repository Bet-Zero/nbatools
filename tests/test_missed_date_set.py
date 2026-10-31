"""A date set owns the candidate sample before absence qualification."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.game_finder import _apply_filters
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def test_disjoint_dates_do_not_require_or_include_intervening_unknown_game(tmp_path, monkeypatch):
    root = tmp_path / "fx"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    filename = "2025-26_regular_season.csv"
    teams = pd.read_csv(root / "data/raw/team_game_stats" / filename)
    games = teams.loc[teams.team_abbr.eq("LAL")].sort_values("game_date").iloc[:3]
    dates = games.game_date.str[:10].tolist()
    path = root / "data/raw/player_game_stats" / filename
    players = pd.read_csv(path)
    selected = players.player_name.eq("LeBron James") & players.game_id.isin(games.game_id)
    evidence = players.loc[selected & players.game_id.isin(games.game_id.iloc[[0, 2]])].copy()
    evidence = evidence.assign(
        participation_state="did_not_play",
        coverage_scope="listed_player_rows_only",
        source="nba_official_finalbox:20251021_GSWLAL",
        source_sha256="a" * 64,
    )
    target = root / "data/raw/player_game_availability" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(target, index=False)
    players.loc[~selected].to_csv(path, index=False)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    try:
        query = f"how many games did LeBron miss on {dates[0]} and {dates[2]} in 2025-26"
        result = execute_natural_query(query)
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        assert sections["count"][0]["count"] == 2
        assert {int(r["game_id"]) for r in sections["finder"]} == set(games.game_id.iloc[[0, 2]])
        direct = execute_structured_query(
            "game_finder",
            team="LAL",
            season="2025-26",
            without_player="LeBron James",
            game_dates=[dates[0], dates[2]],
        )
        assert direct.result_status == "ok", direct.metadata
        assert {int(r["game_id"]) for r in direct.result.to_dict()["sections"]["finder"]} == set(
            games.game_id.iloc[[0, 2]]
        )
        assert {
            "label": "Dates",
            "value": ", ".join([dates[0], dates[2]]),
            "kind": "date",
        } in direct.metadata["applied_filters"]
        intersected = execute_structured_query(
            "game_finder",
            team="LAL",
            season="2025-26",
            without_player="LeBron James",
            game_dates=[dates[0], dates[2]],
            start_date=dates[1],
        )
        assert intersected.result_status == "ok", intersected.metadata
        assert [int(r["game_id"]) for r in intersected.result.to_dict()["sections"]["finder"]] == [
            int(games.game_id.iloc[2])
        ]
        assert {"Dates", "Date range"} <= {
            f["label"] for f in intersected.metadata["applied_filters"]
        }
        unknown = execute_natural_query(
            f"how many games did LeBron miss on {dates[0]}, {dates[1]} and {dates[2]} in 2025-26"
        )
        assert unknown.result_status == "no_result", unknown.metadata
        wider = execute_natural_query(
            f"how many games did LeBron miss from {dates[0]} to {dates[2]} in 2025-26"
        )
        assert wider.result_status == "no_result", wider.metadata
    finally:
        reset_data_source_cache()


@pytest.mark.parametrize(
    "dates", [[], "2025-10-24", ["2025-02-30"], [None], ["October 24"], ["20251024"]]
)
def test_structured_date_set_rejects_invalid_shape_and_dates(dates):
    frame = pd.DataFrame([dict(game_id=1, game_date="2025-10-24")])
    with pytest.raises(ValueError, match="game_dates"):
        _apply_filters(frame, game_dates=dates)


@pytest.mark.parametrize("dates", [[True], [None], True, 42, [], "2025-10-24", ["2025-02-30"]])
def test_public_structured_rejection_never_crashes_in_metadata(dates):
    result = execute_structured_query("game_finder", team="LAL", season="2025-26", game_dates=dates)
    assert result.result_status == "no_result", result.metadata
    assert not any(
        f["label"] == "Dates"
        for f in result.metadata.get("applied_filters", [])
        if not isinstance(dates, list) or not all(isinstance(day, str) for day in dates)
    )
