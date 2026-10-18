"""A prefixed question keeps its actual team, opponent and named-season sample."""

from __future__ import annotations

import pytest

from nbatools.commands import team_split_summary
from nbatools.data_source import data_read_csv
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_opponent_prefix_question_preserves_exact_named_seasons(monkeypatch):
    expected = {}
    ids = {"2023-24": {22301096}, "2025-26": {22500108, 22500244}}
    for season in ids:
        raw = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
        rows = raw.loc[
            raw.team_id.eq(1610612752) & raw.opponent_team_id.eq(1610612748) & raw.is_away.eq(1)
        ].copy()
        assert set(rows.game_id.astype(int)) == ids[season]
        expected[season] = rows
    captured = []
    compute = team_split_summary._summarize_bucket

    def capture(frame, bucket):
        captured.append((bucket, frame.copy()))
        return compute(frame, bucket)

    monkeypatch.setattr(team_split_summary, "_summarize_bucket", capture)
    result = execute_natural_query(
        "Against Miami, what was New York’s away record in each of 2023-24 and 2025-26?"
    )
    assert result.result_status == "ok", result.metadata
    assert result.route == "team_split_summary"
    assert result.metadata["team"] == "NYK"
    assert result.metadata["opponent"] == "MIA"
    assert result.metadata["season_list"] == ["2023-24", "2025-26"]
    assert {"label": "Location", "kind": "location", "value": "Away"} in result.metadata[
        "applied_filters"
    ]
    sections = result.result.to_dict()["sections"]
    assert sections["summary"][0]["team_name"] == "New York Knicks"
    assert sections["summary"][0]["games_total"] == 3
    assert [bucket for bucket, _ in captured] == list(ids)
    assert [row["bucket"] for row in sections["split_comparison"]] == list(ids)
    for row, (season, actual) in zip(sections["split_comparison"], captured):
        source = expected[season]
        assert len(actual) == len(source)
        keys = ["game_id", "team_id", "opponent_team_id"]
        assert sorted(actual[keys].astype(int).values.tolist()) == sorted(
            source[keys].astype(int).values.tolist()
        )
        assert actual.season.eq(season).all()
        assert row["games"] == len(source)
        assert row["wins"] == int(source.wl.eq("W").sum())
        assert row["losses"] == int(source.wl.eq("L").sum())
        for stat in ("pts", "reb", "ast"):
            assert row[stat + "_avg"] == pytest.approx(source[stat].mean(), abs=0.001)
