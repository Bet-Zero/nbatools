"""Comparison subjects and shared historical team context survive together."""

import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
A, B = "Luka Dončić", "Anthony Davis"


@pytest.fixture
def sample(tmp_path, monkeypatch):
    root = tmp_path / "sample"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    # Build expectations directly from the retained controlled positive rows,
    # independently of structured/natural query execution agreement.
    raw = pd.read_csv(root / "data/raw/player_game_stats/2024-25_regular_season.csv")
    expected = {}
    for name in (A, B):
        rows = raw.loc[
            raw.player_name.eq(name) & raw.team_abbr.eq("LAL") & raw.opponent_team_abbr.eq("GSW")
        ]
        expected[name] = (len(rows), {s: rows[s].sum() for s in ("pts", "reb", "ast")})
    assert all(v[0] for v in expected.values())
    yield expected
    reset_data_source_cache()


def comparison(result, expected, order=(A, B)):
    assert result.route == "player_compare" and result.result_status == "ok", result.metadata
    rows = result.result.to_dict()["sections"]["summary"]
    assert [r["player_name"] for r in rows] == list(order)
    for row in rows:
        n, totals = expected[row["player_name"]]
        assert row["games"] == n
        for s, total in totals.items():
            assert row[s + "_sum"] == total
            assert row[s + "_avg"] == pytest.approx(round(total / n, 3))
    m = result.metadata
    assert m["team"] == "LAL" and m["team_context"]["team_abbr"] == "LAL"
    assert m["opponent"] == "GSW" and m["opponent_context"]["team_abbr"] == "GSW"
    assert [p["player_name"] for p in m["players_context"]] == list(order)
    assert not m["with_player"] and not m["without_player"] and not m["head_to_head_used"]
    assert {"label": "Playing for", "value": "LAL", "kind": "team"} in m["applied_filters"]
    assert {"label": "Opponent", "value": "GSW", "kind": "team"} in m["applied_filters"]
    assert not any("unsupported_boundary:" in n for n in m.get("notes") or [])


@pytest.mark.parametrize(
    "query",
    [
        "Compare Luka Doncic and Anthony Davis for the Lakers against Warriors in 2024-25",
        "How did Luka Doncic and Anthony Davis compare for Lakers against the Warriors in 2024-25?",
        "Compare Luka Doncic and Anthony Davis while playing for the Lakers against Golden State in 2024-25",
        "Compare Luka Doncic and Anthony Davis only in their games for the Lakers against Warriors in 2024-25",
        "For the Lakers in 2024-25, compare Luka Doncic and Anthony Davis against Golden State",
        "Compare Luka Doncic with Anthony Davis for Lakers against Warriors in 2024-25",
        "Show Luka Doncic and Anthony Davis averages side by side for Lakers against Warriors in 2024-25",
    ],
)
def test_shared_team_comparison_keeps_both_complete_subjects(sample, query):
    comparison(execute_natural_query(query), sample)


def test_reversed_subject_order_and_structured_context(sample):
    comparison(
        execute_natural_query(
            "Compare Anthony Davis and Luka Doncic for Lakers against Warriors in 2024-25"
        ),
        sample,
        (B, A),
    )
    comparison(
        execute_structured_query(
            "player_compare", player_a=A, player_b=B, team="LAL", opponent="GSW", season="2024-25"
        ),
        sample,
    )


@pytest.mark.parametrize(
    "clause",
    [
        "Luka Doncic and Blorg for Lakers",
        "Blorg and Anthony Davis for Lakers",
        "Luka Doncic and Williams for Lakers",
        "Luka Doncic and the Lakers for Lakers",
        "Luka Doncic for Dallas and Anthony Davis for Lakers",
        "Luka Doncic for Lakers and Anthony Davis",
        "Luka Doncic and Anthony Davis and LeBron James for Lakers",
    ],
)
def test_unknown_or_differently_owned_operand_cannot_become_first_player(sample, clause):
    result = execute_natural_query(f"Compare {clause} against Warriors in 2024-25")
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported"
    assert result.route == "player_compare"
    assert not result.result.to_dict()["sections"] and not result.metadata.get("answer_phrase")
    assert not result.metadata.get("applied_filters")


@pytest.mark.parametrize(
    "tail",
    [
        "while LeBron is healthy",
        "with LeBron playing",
        "while Anthony Davis scores 30 points",
        "and do a backflip",
        "in the first half",
        "on the court",
        "or at most 10 rebounds",
        "and 2023-24",
        "against Blorg",
        "while in Dallas",
    ],
)
def test_unread_or_changed_owner_clause_is_never_dropped(sample, tail):
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 " + tail
    )
    assert result.result_status == "no_result"
    assert not result.result.to_dict()["sections"] and not result.metadata.get("answer_phrase")
    assert not result.metadata.get("applied_filters")


@pytest.mark.parametrize("suffix", ["at home", "since 2025-01-01", "with at least 20 points"])
def test_complete_common_static_and_numeric_filters_execute_before_summarizing(sample, suffix):
    query = "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 " + suffix
    result = execute_natural_query(query)
    kwargs = parse_query(query)["route_kwargs"]
    assert result.route == "player_compare" and result.result_status == "ok", kwargs
    raw = pd.read_csv(
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2024-25_regular_season.csv"
    )
    for row in result.result.to_dict()["sections"]["summary"]:
        rows = raw.loc[
            raw.player_name.eq(row["player_name"])
            & raw.team_abbr.eq("LAL")
            & raw.opponent_team_abbr.eq("GSW")
        ]
        if suffix == "at home":
            rows = rows.loc[rows.is_home.eq(1)]
        if suffix.startswith("since"):
            rows = rows.loc[pd.to_datetime(rows.game_date).ge("2025-01-01")]
        if suffix.startswith("with"):
            rows = rows.loc[rows.pts.ge(20)]
        assert row["games"] == len(rows)
        assert row["pts_sum"] == rows.pts.sum()
    assert {"label": "Playing for", "value": "LAL", "kind": "team"} in result.metadata[
        "applied_filters"
    ]
