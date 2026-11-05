"""Required compact-clause acceptance on the already-qualified pinned generation."""

import pytest

from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_compact_home_absence_matches_literal_qualified_rows_and_api():
    # Reuse PR559's accepted source qualification; this is an independent raw-row
    # selection/arithmetic oracle, not another inference from absent appearances.
    availability = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    states = availability.loc[availability.player_id.eq(2544) & availability.team_id.eq(1610612747)]
    assert not states.duplicated(["game_id", "team_id", "player_id"]).any()
    dnp = states.loc[states.participation_state.eq("did_not_play")]
    assert len(dnp) == 22 and dnp.source_sha256.str.len().eq(64).all()
    own = teams.loc[teams.team_id.eq(1610612747)]
    assert len(own) == own.game_id.nunique() == 82
    home = own.loc[own.game_id.isin(dnp.game_id) & own.is_home.eq(1)]
    assert len(home) == 11
    expected_ids = set(home.game_id.astype(int))
    query = "how many home games did LeBron miss in2025-26"
    for question in [
        query,
        "how many home games did LeBron miss in 2025-26",
        "games LeBron missed during2025-26 at home",
    ]:
        result = execute_natural_query(question)
        assert result.route == "game_finder" and result.result_status == "ok", result.metadata
        sections = result.to_dict()["sections"]
        assert sections["count"] == [{"count": 11}]
        assert {int(row["game_id"]) for row in sections["finder"]} == expected_ids
        assert "LeBron James missed" in result.metadata["answer_phrase"]
        assert "home" in result.metadata["answer_phrase"]
    record = execute_natural_query("Lakers record at home without LeBron James in2025-26")
    assert record.result_status == "ok", record.metadata
    summary = record.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (
        11,
        int(home.wl.eq("W").sum()),
        int(home.wl.eq("L").sum()),
    )
    assert summary["pts_avg"] == pytest.approx(home.pts.mean(), abs=0.001)
    from fastapi.testclient import TestClient

    from nbatools.api import app

    response = TestClient(app).post("/query", json={"query": query})
    assert response.status_code == 200 and response.json()["result_status"] == "ok"
    assert response.json()["result"]["sections"]["count"] == [{"count": 11}]
