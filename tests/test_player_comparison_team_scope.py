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
    # A controlled historical team change on one complete game makes the
    # shared team filter discriminate for BOTH subjects, unlike an all-LAL
    # carrier. Keep the catalog and reciprocal team/player sides consistent.
    gid = raw.loc[raw.team_abbr.eq("LAL") & raw.opponent_team_abbr.eq("GSW"), "game_id"].iloc[0]
    team_path = root / "data/raw/team_game_stats/2024-25_regular_season.csv"
    teams = pd.read_csv(team_path)
    own_id = int(teams.loc[teams.team_abbr.eq("LAL"), "team_id"].iloc[0])
    replacement_id = int(teams.loc[teams.team_abbr.eq("BOS"), "team_id"].iloc[0])
    for kind in ("team_game_stats", "player_game_stats"):
        path = root / f"data/raw/{kind}/2024-25_regular_season.csv"
        frame = pd.read_csv(path)
        for prefix in ("", "opponent_"):
            mask = frame.game_id.eq(gid) & frame[prefix + "team_abbr"].eq("LAL")
            frame.loc[mask, [prefix + "team_id", prefix + "team_abbr", prefix + "team_name"]] = [
                replacement_id,
                "BOS",
                "Boston Celtics",
            ]
        frame.to_csv(path, index=False)
    path = root / "data/raw/games/2024-25_regular_season.csv"
    catalog = pd.read_csv(path)
    for col in ("home_team_id", "away_team_id"):
        catalog.loc[catalog.game_id.eq(gid) & catalog[col].eq(own_id), col] = replacement_id
    catalog.to_csv(path, index=False)
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
    assert result.result_status == "no_result" and result.result_reason == "unsupported"
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
        "vs Celtics",
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


@pytest.mark.parametrize(
    "bound,minimum,maximum",
    [
        ("over 35.99999 points", 36, None),
        ("under 36.00001 points", None, 36),
        ("at least 36.00001 points", 37, None),
        ("at most 35.99999 points", None, 35),
        ("over 36 points", 37, None),
        ("at least 36 points", 36, None),
        ("under 0 points", None, -1),
        ("between 0.1 and 0.9 points", 1, 0),
    ],
)
def test_new_count_bounds_have_exact_integer_execution_and_original_labels(
    sample, bound, minimum, maximum
):
    query = (
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 with " + bound
    )
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert kwargs["min_value"] == minimum and kwargs["max_value"] == maximum, kwargs
    result = execute_natural_query(query)
    raw = pd.read_csv(
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2024-25_regular_season.csv"
    )
    expected = {}
    for name in (A, B):
        rows = raw.loc[
            raw.player_name.eq(name) & raw.team_abbr.eq("LAL") & raw.opponent_team_abbr.eq("GSW")
        ]
        if minimum is not None:
            rows = rows.loc[rows.pts.ge(minimum)]
        if maximum is not None:
            rows = rows.loc[rows.pts.le(maximum)]
        expected[name] = rows
    if not any(len(rows) for rows in expected.values()):
        assert result.result_status == "no_result" and result.result_reason == "no_match"
        assert not result.result.to_dict()["sections"]
    else:
        assert result.result_status == "ok"
        for row in result.result.to_dict()["sections"]["summary"]:
            expected_rows = expected[row["player_name"]]
            assert row["games"] == len(expected_rows)
            assert row["pts_sum"] == expected_rows.pts.sum()
            if not len(expected_rows):
                assert row["pts_avg"] is None
    labels = [
        f["value"] for f in result.metadata["applied_filters"] if f["label"] == "Count filter"
    ]
    assert len(labels) == 1
    if bound.startswith(("over", "under", "between")) or "00001" in bound or "99999" in bound:
        assert "integer execution:" in labels[0]
    if "35.99999" in bound:
        assert "35.99999" in labels[0]
    if "36.00001" in bound:
        assert "36.00001" in labels[0]
    if maximum == -1:
        assert "<= -1 PTS" in labels[0]


@pytest.mark.parametrize(
    "predicate", ["at least 30 minutes", "over 50 percent shooting", "under .51 fg pct"]
)
def test_other_numeric_domains_are_not_silently_integer_lowered(sample, predicate):
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 with "
        + predicate
    )
    assert result.result_status == "no_result" and not result.result.to_dict()["sections"]
    assert not result.metadata.get("applied_filters")


@pytest.mark.parametrize(
    "tail",
    [
        "at home and on the road",
        "last 1 games and last 2 games",
        "after January 1, 2025 and before January 20, 2025",
        "since January 1, 2025 and since February 1, 2025",
    ],
)
def test_unrepresented_static_composition_retains_comparison_operation(sample, tail):
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 " + tail
    )
    assert result.route == "player_compare"
    assert result.result_status == "no_result"
    assert result.result_reason == "unsupported"
    assert not result.result.to_dict()["sections"]
    assert not result.metadata.get("applied_filters")


def test_question_intent_selects_complete_operands_before_versus_opponent(sample):
    comparison(
        execute_natural_query(
            "How did Luka Doncic and Anthony Davis compare for Lakers versus Warriors in 2024-25?"
        ),
        sample,
    )


@pytest.mark.parametrize(
    "bound,minimum,maximum",
    [
        ("under 20.000000000000001 points", None, 20),
        ("at most 19.999999999999999 points", None, 19),
        ("over 19.999999999999999 points", 20, None),
        ("at least 20.000000000000001 points", 21, None),
        ("points between 19.999999999999999 and 20.000000000000001", 20, 20),
    ],
)
def test_exact_count_lowering_preserves_original_decimal_lexeme(sample, bound, minimum, maximum):
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 with " + bound
    )
    parsed = parse_query(result.query)
    assert parsed["route_kwargs"]["min_value"] == minimum
    assert parsed["route_kwargs"]["max_value"] == maximum
    assert result.result_status in ("ok", "no_result")
    if result.result_status == "ok":
        labels = str(result.metadata["applied_filters"])
        assert any(literal in labels for literal in ("19.999999999999999", "20.000000000000001"))


def test_final_comparison_contract_rejects_changed_grain_or_dropped_scope():
    from nbatools.commands._player_comparison_scope import comparison_contract_matches

    request = {"players": [A, B], "sample": {"team": "LAL", "last_n": 2}}
    kwargs = {"player_a": A, "player_b": B, "team": "LAL", "last_n": 2}
    assert comparison_contract_matches(request, "player_compare", kwargs)
    assert not comparison_contract_matches(request, "team_split_summary", kwargs)
    assert not comparison_contract_matches(request, "player_compare", {**kwargs, "last_n": 1})


def test_ambiguous_operand_id_cannot_be_guessed_from_shared_team(sample, monkeypatch):
    from nbatools.commands import _player_comparison_scope as scope

    original = scope.player_ids_for_name
    monkeypatch.setattr(
        scope,
        "player_ids_for_name",
        lambda name: frozenset({"1", "2"}) if name == A else original(name),
    )
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25"
    )
    assert result.result_status == "no_result" and result.result_reason == "unsupported"
    assert result.route == "player_compare" and not result.result.to_dict()["sections"]


def test_two_complete_count_predicates_filter_both_samples_before_aggregation(sample):
    result = execute_natural_query(
        "Compare Luka Doncic and Anthony Davis for Lakers against Warriors in 2024-25 with at least 20 points and at most 8 rebounds"
    )
    parsed = parse_query(result.query)
    assert result.result_status == "ok" and result.route == "player_compare"
    assert {c["stat"] for c in parsed["route_kwargs"]["conditions"]} == {"pts", "reb"}
    raw = pd.read_csv(
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2024-25_regular_season.csv"
    )
    for row in result.result.to_dict()["sections"]["summary"]:
        expected = raw.loc[
            raw.player_name.eq(row["player_name"])
            & raw.team_abbr.eq("LAL")
            & raw.opponent_team_abbr.eq("GSW")
            & raw.pts.ge(20)
            & raw.reb.le(8)
        ]
        assert row["games"] == len(expected)
        assert row["pts_sum"] == expected.pts.sum()


@pytest.mark.parametrize(
    "query",
    [
        "Compare LeBron James and the Warriors against Lakers in 2024-25",
        "How did LeBron James and the Warriors compare against Lakers in 2024-25?",
        "Compare the Warriors and LeBron James against Lakers in 2024-25",
    ],
)
def test_explicit_opponent_does_not_erase_mixed_grain_subject(sample, query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported"
    assert not result.result.to_dict()["sections"]
    assert not result.metadata.get("applied_filters")
