"""Compact calendar clauses preserve absence and sample ownership.

Explicit controlled DNP observations distinguish missed games from appearances;
no fixture establishes an NBA injury, tenure or real absence fact.
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.api_handlers import query_result_to_payload
from nbatools.commands._constants import normalize_text
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.fixture
def absence_source(tmp_path, monkeypatch):
    root = tmp_path / "controlled-absence"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    filename = "2025-26_regular_season.csv"
    path = root / "data/raw/player_game_stats" / filename
    players = pd.read_csv(path)
    own = players.loc[players.player_id.eq(2544)].sort_values(["game_date", "game_id"])
    home = own.loc[own.is_home.eq(1)].iloc[:2]
    away = own.loc[own.is_away.eq(1)].iloc[:1]
    dnp = pd.concat([home, away])
    assert len(dnp) == 3 and len(own) > 20
    evidence = dnp.assign(
        participation_state="did_not_play",
        coverage_scope="listed_player_rows_only",
        source="nba_official_finalbox:20251021_GSWLAL",
        source_sha256="a" * 64,
    )
    target = root / "data/raw/player_game_availability" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    evidence.to_csv(target, index=False)
    players.loc[~(players.player_id.eq(2544) & players.game_id.isin(dnp.game_id))].to_csv(
        path, index=False
    )
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    try:
        yield root, home, away
    finally:
        reset_data_source_cache()


@pytest.mark.parametrize(
    "query",
    [
        "how many home games did LeBron miss in2025-26",
        "how many home games did LeBron miss in 2025-26",
        "how many home games did LeBron miss during2025-26?",
        "games LeBron missed in2025-26 at home",
    ],
)
def test_compact_season_does_not_fall_back_to_played_games(absence_source, query):
    _, home, _ = absence_source
    result = execute_natural_query(query)
    payload = query_result_to_payload(result)
    assert payload["route"] == "game_finder" and payload["result_status"] == "ok"
    sections = payload["result"]["sections"]
    assert sections["count"] == [{"count": 2}]
    assert {int(r["game_id"]) for r in sections["finder"]} == set(home.game_id)
    assert "LeBron James missed" in result.metadata["answer_phrase"]
    assert "home" in result.metadata["answer_phrase"]
    assert "2025-26" in result.metadata["answer_phrase"]


def test_compact_explicit_date_keeps_selected_absence_ids(absence_source):
    _, home, _ = absence_source
    day = home.iloc[0].game_date[:10]
    result = execute_natural_query(f"how many home games did LeBron miss on{day} in2025-26")
    assert result.result_status == "ok", result.metadata
    sections = result.to_dict()["sections"]
    assert sections["count"] == [{"count": 1}]
    assert [int(r["game_id"]) for r in sections["finder"]] == [int(home.iloc[0].game_id)]


@pytest.mark.parametrize("text", ["within2025-26", "Martin2025", "in20250", "30points", "top10"])
def test_calendar_normalization_does_not_split_names_or_stat_tokens(text):
    assert normalize_text(text) == text.lower()


def test_injury_wording_is_not_equated_with_fixture_dnp(absence_source):
    result = execute_natural_query("how many home games was LeBron injured in2025-26")
    assert result.result_status == "no_result"
    assert "count" not in result.to_dict().get("sections", {})
