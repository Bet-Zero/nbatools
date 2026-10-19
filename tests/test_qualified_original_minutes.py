"""Original-matchup time checks require qualified report seconds, not rounded MIN."""

import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import _participation_observations as observations
from nbatools.commands._parse_helpers import extract_threshold_conditions
from nbatools.query_service import execute_natural_query
from tests.test_qualified_played_pair import TATUM
from tests.test_qualified_played_pair import pair_sample as _pair_sample

pair_sample = _pair_sample
NATIVE_OBSERVATION_LOADER = observations.load_observations
pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def question(predicate, scope="", player="Tatum"):
    return (
        f"Did {player} play {predicate} in the Lakers last game against Celtics {scope} in 2023-24?"
    )


def unknown(result):
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
    assert not result.metadata.get("answer_phrase")
    assert not result.result.to_dict()["sections"]
    assert not any(f["label"] == "Minutes check" for f in result.metadata["applied_filters"])


def success(result, gid, truth, player="Jayson Tatum"):
    assert result.route == "game_finder" and result.result_status == "ok", result.metadata
    assert result.metadata["player"] == player
    assert set(result.metadata["player_context"]) == {"player_id", "player_name"}
    assert result.metadata["stat"] is None
    assert result.metadata["min_value"] is None and result.metadata["max_value"] is None
    assert not result.metadata["threshold_conditions"]
    assert not result.metadata["with_player"] and not result.metadata["without_player"]
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(("Yes:" if truth else "No:") + " " + player)
    assert not any("unsupported_boundary:" in n for n in result.metadata["notes"])
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == gid
    assert rows[0]["team_id"] == 1610612747 and rows[0]["opponent_team_id"] == 1610612738
    assert not any(k in rows[0] for k in ("player", "player_name", "player_id"))
    assert str(rows[0]["game_date"])[:10] in phrase
    filters = result.metadata["applied_filters"]
    assert any(f["label"] == "Minutes check" and f["value"].startswith(player) for f in filters)
    assert not any(f["label"] in ("Played check", "With player", "Without player") for f in filters)
    assert any(
        f["label"] == "Sample selection" and "original team matchup" in f["value"] for f in filters
    )
    assert any("team-game totals" in c and "MM:SS" in c for c in result.result.caveats)
    return phrase


@pytest.fixture
def exact_sample(pair_sample):
    ledger = pair_sample["ledger"]
    ledger["source_minutes"] = ledger.participation_state.map({"played": 25.0})
    first = pair_sample["candidates"].sort_values("game_date").iloc[0]
    return pair_sample, f"on {str(first.game_date)[:10]}", int(first.game_id)


@pytest.mark.parametrize(
    "bound", ["at least 30 minutes", "fewer than 30 minutes", "at most 0 minutes"]
)
def test_explicit_dnp_answers_no_for_played_and_any_bound_without_numeric_zero(pair_sample, bound):
    result = execute_natural_query(question(bound))
    phrase = success(result, pair_sample["ids"][-1], False)
    assert "did not play" in phrase and "played 0:" not in phrase
    assert "0 points" not in phrase and "25:" not in phrase


@pytest.mark.parametrize(
    "bound,truth",
    [
        ("at least 25 minutes", True),
        ("over 25 minutes", False),
        ("at most 25 minutes", True),
        ("under 25 minutes", False),
        ("over 24.99999 minutes", True),
        ("under 25.00001 minutes", True),
        ("at least 25.00001 minutes", False),
        ("at most 24.99999 minutes", False),
        ("between 25 and 26 minutes", True),
        ("minutes over 25", False),
    ],
)
def test_exact_seconds_and_explicit_operator_control_threshold(exact_sample, bound, truth):
    sample, scope, gid = exact_sample
    path = (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2023-24_regular_season.csv"
    )
    rows = pd.read_csv(path)
    rows.loc[rows.player_id.eq(TATUM), "minutes"] = (
        99  # deliberately different positive rounding carrier
    )
    rows.to_csv(path, index=False)
    result = execute_natural_query(question(bound, scope))
    assert "played 25:00" in success(result, gid, truth)


@pytest.mark.parametrize(
    "damage",
    [
        "missing_row",
        "missing_minutes",
        "null",
        "inf",
        "zero",
        "negative",
        "half_second",
        "tiny_positive",
        "wrong_date",
        "wrong_side",
        "unknown",
        "duplicate",
    ],
)
def test_selected_report_time_cannot_be_replaced_by_positive_appearance_or_older_time(
    exact_sample, damage, monkeypatch
):
    sample, scope, gid = exact_sample
    ledger = sample["ledger"]
    mask = ledger.game_id.eq(gid) & ledger.player_id.eq(TATUM)
    if damage == "missing_row":
        ledger.drop(ledger.index[mask], inplace=True)
    elif damage == "missing_minutes":
        ledger.drop(columns="source_minutes", inplace=True)
    elif damage in ("null", "inf", "zero", "negative", "half_second", "tiny_positive"):
        ledger.loc[mask, "source_minutes"] = {
            "null": float("nan"),
            "inf": float("inf"),
            "zero": 0,
            "negative": -1,
            "half_second": 25 + 0.5 / 60,
            "tiny_positive": 1e-12,
        }[damage]
    elif damage == "wrong_date":
        ledger.loc[mask, "game_date"] = "1900-01-01"
    elif damage == "wrong_side":
        ledger.loc[mask, "team_id"] = 1610612752
    elif damage == "unknown":
        ledger.loc[mask, "participation_state"] = "unknown"
    else:
        ledger.loc[len(ledger)] = ledger.loc[mask].iloc[0]
        # Exercise the real retained-observation schema/duplicate boundary,
        # rather than bypass its guarantee through the pair fixture's loader.
        saved = ledger.assign(
            season="2023-24",
            season_type="Regular Season",
            coverage_scope="listed_player_rows_only",
            source="nba_official_finalbox:20231028_LALBOS",
            source_sha256="a" * 64,
        )
        path = (
            Path(os.environ["NBATOOLS_DATA_ROOT"])
            / "data/raw/player_game_availability/2023-24_regular_season.csv"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        saved.to_csv(path, index=False)
        monkeypatch.setattr(observations, "load_observations", NATIVE_OBSERVATION_LOADER)
    result = execute_natural_query(question("at least 20 minutes", scope))
    unknown(result)
    assert result.metadata["player_context"]["player_id"] == TATUM


def test_older_time_unknown_does_not_block_selected_known_original_game(exact_sample):
    sample, scope, gid = exact_sample
    sample["ledger"].loc[lambda d: ~d.game_id.eq(gid), "source_minutes"] = float("nan")
    assert "played 25:00" in success(
        execute_natural_query(question("at least 20 minutes", scope)), gid, True
    )


@pytest.mark.parametrize(
    "query",
    [
        "For the Lakers latest meeting against Boston on {day} in 2023-24, did Jayson Tatum play more than 24 minutes?",
        "In the Lakers most recent matchup versus Celtics on {day} in 2023-24, has Tatum played at most 25 minutes?",
        "Did Jayson Tatum play 25+ minutes in the Lakers last one game vs Boston on {day} in 2023-24?",
    ],
)
def test_complete_alias_and_leading_scope_wording_retains_same_original(exact_sample, query):
    _, scope, gid = exact_sample
    result = execute_natural_query(query.format(day=scope.removeprefix("on ")))
    assert "played 25:00" in success(result, gid, True)


@pytest.mark.parametrize(
    "tail",
    [
        "while LeBron was healthy",
        "and do a backflip",
        "while Blorg plays",
        "in the first half",
        "on the court",
    ],
)
def test_unread_tail_is_not_an_admitted_exact_time_answer(exact_sample, tail):
    _, scope, _ = exact_sample
    result = execute_natural_query(question("at least 20 minutes " + tail, scope))
    assert not result.metadata.get("answer_phrase")
    assert not any(
        f["label"] == "Minutes check" for f in result.metadata.get("applied_filters") or []
    )


def test_exact_extractor_retains_operators_without_changing_default_dictionaries():
    legacy = extract_threshold_conditions("over 36.6166 minutes")[0]
    assert legacy["min_value"] == pytest.approx(36.6167)
    assert "min_inclusive" not in legacy and "max_inclusive" not in legacy
    precise = extract_threshold_conditions("over 36.6166 minutes", exact_stat="minutes")[0]
    assert precise["min_value"] == 36.6166 and precise["min_inclusive"] is False
    assert extract_threshold_conditions(
        "over 30 points", exact_stat="minutes"
    ) == extract_threshold_conditions("over 30 points")
    assert "max_inclusive" in precise
    assert precise["max_value"] is None


def test_dnp_with_positive_report_time_is_conflicting_not_a_boolean(pair_sample):
    ledger = pair_sample["ledger"]
    mask = ledger.game_id.eq(pair_sample["ids"][-1]) & ledger.player_id.eq(TATUM)
    ledger["source_minutes"] = float("nan")
    ledger.loc[mask, "source_minutes"] = 25.0
    unknown(execute_natural_query(question("at least 30 minutes")))


def test_checked_decimal_label_retains_full_normalized_threshold_precision(exact_sample):
    _, scope, gid = exact_sample
    result = execute_natural_query(question("over 24.999999 minutes", scope))
    phrase = success(result, gid, True)
    assert "played > 24.999999 minutes" in phrase
    assert any(
        f["value"] == "Jayson Tatum played > 24.999999 minutes"
        for f in result.metadata["applied_filters"]
    )


@pytest.mark.parametrize("scope_first", [False, True])
def test_explicit_regular_season_is_consumed_in_complete_original_scope(exact_sample, scope_first):
    _, scope, gid = exact_sample
    game_scope = (
        f"the Lakers latest meeting against Boston {scope} during the 2023-24 regular season"
    )
    query = (
        f"For {game_scope}, did Tatum play at least 20 minutes?"
        if scope_first
        else f"Did Tatum play at least 20 minutes in {game_scope}?"
    )
    assert "played 25:00" in success(execute_natural_query(query), gid, True)


@pytest.mark.parametrize("pair", [False, True])
def test_shared_regular_season_reader_preserves_plain_scalar_and_both(pair_sample, pair):
    subject = "both Tatum and Reaves" if pair else "Tatum"
    result = execute_natural_query(
        f"Did {subject} play in the Lakers latest game against Boston during the 2023-24 regular season?"
    )
    assert result.result_status == "ok" and result.route == "game_finder"
    assert result.metadata["answer_phrase"].startswith("No:")
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == pair_sample["ids"][-1]
    assert not any(f["label"] == "Minutes check" for f in result.metadata["applied_filters"])
    assert any(f["label"] == "Played check" for f in result.metadata["applied_filters"])


@pytest.mark.parametrize(
    "season",
    ["2023-24 postseason", "2023-24 playoff season", "2023-24 and 2024-25 regular seasons"],
)
def test_regular_season_wording_does_not_consume_other_season_types_or_multiple_seasons(
    exact_sample, season
):
    _, scope, _ = exact_sample
    query = f"Did Tatum play at least 20 minutes in the Lakers last game against Celtics {scope} during the {season}?"
    result = execute_natural_query(query)
    assert not result.metadata.get("answer_phrase")
    assert not any(
        f["label"] == "Minutes check" for f in result.metadata.get("applied_filters") or []
    )
