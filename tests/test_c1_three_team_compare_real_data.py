"""Independent real-data checks for three teams' month and scoring samples."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    ("season", "query", "prefix"),
    [
        ("2023-24", "Lakers vs Celtics vs Knicks in March 2024", "2024-03"),
        ("2025-26", "Lakers vs Celtics vs Knicks in March", "2026-03"),
    ],
)
def test_three_team_month_keeps_independent_real_game_samples(season, query, prefix):
    """Verify all three outputs against qualified team-game source, not engine totals."""
    source = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
    required = {"team_abbr", "game_id", "game_date", "wl", "pts"}
    assert required.issubset(source.columns), required - set(source.columns)
    assert not source.duplicated(["game_id", "team_abbr"]).any()
    assert source[list(required)].notna().all().all()
    source = source[source["game_date"].astype(str).str.startswith(prefix)]
    expected = {}
    for abbr in ("LAL", "BOS", "NYK"):
        games = source[source["team_abbr"].eq(abbr)]
        assert not games.empty, f"{abbr} missing {prefix} real-data coverage"
        assert games["wl"].isin(["W", "L"]).all()
        expected[abbr] = (
            len(games),
            int(games["wl"].eq("W").sum()),
            float(games["pts"].mean()),
            set(games["game_id"].astype(str)),
        )
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.route == "team_compare"
    rows = result.result.to_dict()["sections"]["summary"]
    assert [row["team_name"] for row in rows] == ["LAL", "BOS", "NYK"]
    for row in rows:
        count, wins, avg, _ids = expected[row["team_name"]]
        assert row["games"] == count
        assert row["wins"] == wins
        assert row["losses"] == count - wins
        assert row["pts_avg"] == pytest.approx(avg, abs=1e-3)
    # The date must be selected, not silently widened to an entire season.
    for abbr in ("LAL", "BOS", "NYK"):
        all_season = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
        assert len(expected[abbr][3]) < len(all_season[all_season.team_abbr.eq(abbr)])


def test_deployed_three_team_month_matches_pinned_raw_rows():
    """Read-only deployed verification; require the same immutable NBA generation."""
    import json
    import os
    import urllib.request

    base = "https://nbatools.vercel.app"
    with urllib.request.urlopen(base + "/readiness", timeout=20) as response:
        readiness = json.load(response)
    assert readiness["ready"] is True
    assert readiness["immutable_generation"] is True
    assert readiness["active_generation"] == os.environ["NBATOOLS_DATA_GENERATION"]
    query = "Lakers vs Celtics vs Knicks in March 2024"
    request = urllib.request.Request(
        base + "/query",
        data=json.dumps(dict(query=query)).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    assert payload["ok"] is True
    assert payload["route"] == "team_compare"
    assert payload["result_status"] == "ok"
    actual = payload["result"]["sections"]["summary"]
    assert [row["team_name"] for row in actual] == ["LAL", "BOS", "NYK"]
    source = data_read_csv("data/raw/team_game_stats/2023-24_regular_season.csv")
    source = source[source.game_date.astype(str).str.startswith("2024-03")]
    assert not source.duplicated(["game_id", "team_abbr"]).any()
    for row in actual:
        raw = source[source.team_abbr.eq(row["team_name"])]
        assert not raw.empty
        assert raw.wl.isin(["W", "L"]).all()
        assert row["games"] == len(raw)
        assert row["wins"] == int(raw.wl.eq("W").sum())
        assert row["losses"] == int(raw.wl.eq("L").sum())
        assert row["pts_avg"] == pytest.approx(float(raw.pts.mean()), abs=1e-3)
    print(
        "Deployed three-team exact month sample verified:", readiness["active_generation"], actual
    )
