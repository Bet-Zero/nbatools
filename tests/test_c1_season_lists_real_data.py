"""Named seasons on real rows: one row per season, gaps left out."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _assert_venue_flags(raw):
    """Neutral venues are neither home nor away under the canonical contract."""
    assert raw.is_home.isin([True, False]).all()
    assert raw.is_away.isin([True, False]).all()
    assert not (raw.is_home.eq(True) & raw.is_away.eq(True)).any()


def _split(query: str) -> dict:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    rows = result.result.to_dict()["sections"]["split_comparison"]
    return {row["bucket"]: row for row in rows}


@pytest.mark.parametrize(
    ("query", "seasons"),
    [
        ("Lakers record 2022-23 vs 2023-24", ["2022-23", "2023-24"]),
        ("Celtics record in 2016 and 2020", ["2015-16", "2019-20"]),
        ("Warriors record in 2016 vs 2017", ["2015-16", "2016-17"]),
    ],
)
def test_team_records_per_season(query, seasons):
    abbr = {"Lakers": "LAL", "Celtics": "BOS", "Warriors": "GSW"}[query.split()[0]]
    rows = _split(query)
    assert sorted(rows) == seasons
    for season in seasons:
        team = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
        team = team[team["team_abbr"] == abbr]
        assert (rows[season]["wins"], rows[season]["losses"]) == (
            int((team["wl"] == "W").sum()),
            int((team["wl"] == "L").sum()),
        )


def test_lebron_points_per_season():
    rows = _split("LeBron James points 2015-16 vs 2017-18")
    assert sorted(rows) == ["2015-16", "2017-18"]
    for season, row in rows.items():
        games = data_read_csv(f"data/raw/player_game_stats/{season}_regular_season.csv")
        games = games[games["player_name"] == "LeBron James"]
        assert row["games"] == len(games)
        assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)


def test_celtics_home_knicks_nonadjacent_seasons_and_single_season_controls(monkeypatch):
    """S1: exact source rows survive home + opponent + non-adjacent seasons."""
    import pandas as pd

    from nbatools.commands import team_record, team_split_summary
    from nbatools.query_service import execute_natural_query

    seasons = ["2023-24", "2025-26"]
    expected = {}
    required = {
        "season",
        "season_type",
        "game_id",
        "team_id",
        "team_abbr",
        "team_name",
        "opponent_team_abbr",
        "is_home",
        "is_away",
        "wl",
        "pts",
    }
    for season in seasons:
        raw = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
        assert not raw.empty, f"Required S1 source missing: {season}"
        assert required.issubset(raw.columns), required - set(raw.columns)
        assert raw[list(required)].notna().all().all(), f"Null required S1 values: {season}"
        assert raw.season.eq(season).all() and raw.season_type.eq("Regular Season").all()
        assert not raw.duplicated(["season", "game_id", "team_id"]).any()
        assert raw.wl.isin(["W", "L"]).all()
        _assert_venue_flags(raw)
        points = pd.to_numeric(raw.pts, errors="coerce")
        assert (points.notna() & points.ge(0) & points.mod(1).eq(0)).all()
        rows = raw.to_dict("records")
        expected[season] = [
            row
            for row in rows
            if row["team_abbr"] == "BOS" and row["opponent_team_abbr"] == "NYK" and row["is_home"]
        ]
        # Dropping either qualifier must change this required positive sample.
        assert expected[season], f"Required positive BOS home/NYK sample missing: {season}"
        assert any(
            r["team_abbr"] == "BOS" and r["opponent_team_abbr"] == "NYK" and not r["is_home"]
            for r in rows
        )
        assert any(
            r["team_abbr"] == "BOS" and r["opponent_team_abbr"] != "NYK" and r["is_home"]
            for r in rows
        )
        assert {row["team_name"] for row in expected[season]} == {"Boston Celtics"}

    def keys(rows):
        return {(r["season"], int(r["game_id"]), int(r["team_id"])) for r in rows}

    def assert_sample(frame, season):
        selected = frame.to_dict("records")
        assert len(selected) == len(expected[season])
        assert keys(selected) == keys(expected[season])
        assert all(
            r["season"] == season
            and r["team_abbr"] == "BOS"
            and r["opponent_team_abbr"] == "NYK"
            and r["is_home"]
            for r in selected
        )

    def assert_values(row, season):
        source = expected[season]
        assert row["games"] == len(source)
        assert row["wins"] == sum(r["wl"] == "W" for r in source)
        assert row["losses"] == sum(r["wl"] == "L" for r in source)
        assert row["win_pct"] == pytest.approx(row["wins"] / len(source), abs=0.001)
        assert row["pts_avg"] == pytest.approx(
            sum(r["pts"] for r in source) / len(source), abs=0.001
        )

    def assert_labels(result):
        assert result.result_status == "ok", (result.query, result.result_reason, result.metadata)
        assert result.metadata["team"] == "BOS"
        assert result.metadata["opponent"] == "NYK"
        assert result.metadata["season_type"] == "Regular Season"
        assert {"label": "Location", "kind": "location", "value": "Home"} in result.metadata[
            "applied_filters"
        ]
        assert {"label": "Opponent", "kind": "team", "value": "NYK"} in result.metadata[
            "applied_filters"
        ]
        summary = result.result.to_dict()["sections"]["summary"]
        assert len(summary) == 1
        assert summary[0]["team_name"] == "Boston Celtics"
        assert summary[0]["season_type"] == "Regular Season"

    split_frames = []
    summarize = team_split_summary._summarize_bucket

    def capture_split(frame, bucket):
        split_frames.append((bucket, frame.copy()))
        return summarize(frame, bucket)

    monkeypatch.setattr(team_split_summary, "_summarize_bucket", capture_split)
    combined = execute_natural_query("Celtics home record vs Knicks in 2023-24 and 2025-26")
    assert_labels(combined)
    assert combined.route == "team_split_summary"
    assert combined.metadata["season_list"] == seasons
    assert combined.metadata["split_type"] == "season"
    sections = combined.result.to_dict()["sections"]
    assert [row["bucket"] for row in sections["split_comparison"]] == seasons
    assert [bucket for bucket, _ in split_frames] == seasons  # Never include 2024-25.
    assert sections["summary"][0]["games_total"] == sum(map(len, expected.values()))
    assert (sections["summary"][0]["season_start"], sections["summary"][0]["season_end"]) == tuple(
        seasons
    )
    for row, (season, frame) in zip(sections["split_comparison"], split_frames):
        assert_sample(frame, season)
        assert_values(row, season)

    record_frames = []
    compute_record = team_record._compute_record

    def capture_record(frame):
        record_frames.append(frame.copy())
        return compute_record(frame)

    monkeypatch.setattr(team_record, "_compute_record", capture_record)
    for season in seasons:
        record_frames.clear()
        single = execute_natural_query(f"Celtics home record vs Knicks in {season}")
        assert_labels(single)
        assert single.route == "team_record"
        assert single.metadata["season"] == season
        assert len(record_frames) == 1
        assert_sample(record_frames[0], season)
        single_sections = single.result.to_dict()["sections"]
        row = single_sections["summary"][0]
        assert row["season_start"] == row["season_end"] == season
        assert [r["season"] for r in single_sections["by_season"]] == [season]
        assert_values(row, season)
