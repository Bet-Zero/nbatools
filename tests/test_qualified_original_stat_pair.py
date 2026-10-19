"""One player owns both original-game predicates; every played fact is required."""

import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query
from tests.test_qualified_original_minutes import exact_sample as _exact_sample
from tests.test_qualified_original_minutes import pair_sample as _pair_sample
from tests.test_qualified_original_minutes import success, unknown
from tests.test_qualified_played_pair import TATUM

pair_sample = _pair_sample
exact_sample = _exact_sample
pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def player_path():
    return (
        Path(os.environ["NBATOOLS_DATA_ROOT"])
        / "data/raw/player_game_stats/2023-24_regular_season.csv"
    )


def question(
    count="have at least 1 assist", minutes="at least 20 minutes", scope="", reverse=False
):
    predicates = f"{count} and play {minutes}" if reverse else f"play {minutes} and {count}"
    return f"Did Tatum {predicates} in the Lakers last game against Celtics {scope} in 2023-24?"


@pytest.fixture
def stat_sample(exact_sample):
    sample, scope, gid = exact_sample
    frame = pd.read_csv(player_path())
    match = frame.game_id.eq(gid) & frame.player_id.eq(TATUM)
    frame.loc[match, ["pts", "reb", "ast"]] = [8, 0, 1]
    frame.to_csv(player_path(), index=False)
    return sample, scope, gid


def pair_success(result, gid, truth, stat="AST", actual=1):
    phrase = success(result, gid, truth)
    assert f"with {actual} {stat}" in phrase
    assert any(
        f["label"] == "Count check" and stat in f["value"]
        for f in result.metadata["applied_filters"]
    )
    assert "Jayson Tatum" in next(
        f["value"] for f in result.metadata["applied_filters"] if f["label"] == "Count check"
    )
    return phrase


@pytest.mark.parametrize("verb", ["have", "record", "have recorded", "score"])
def test_generic_statistical_verbs_keep_both_original_checks(stat_sample, verb):
    _, scope, gid = stat_sample
    # A HAVE+RECORD auxiliary chain is a coherent predicate, not another actor.
    unit = "point" if verb == "score" else "assist"
    result = execute_natural_query(question(verb + " at least 1 " + unit, scope=scope))
    pair_success(
        result,
        gid,
        True,
        stat="PTS" if verb == "score" else "AST",
        actual=8 if verb == "score" else 1,
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "count,truth",
    [
        ("have at least 1 assist", True),
        ("have over 1 assist", False),
        ("record at most 1 assist", True),
        ("record under 1 assist", False),
        ("have over 0.99999 assists", True),
        ("have under 1.00001 assists", True),
        ("have at least 1.00001 assists", False),
        ("have at most 0.99999 assists", False),
        ("have between 0 and 1 assists", True),
        ("have between 2 and 3 assists", False),
    ],
)
def test_count_strictness_range_and_order_preserve_decimal_bound(
    stat_sample, reverse, count, truth
):
    _, scope, gid = stat_sample
    pair_success(execute_natural_query(question(count, scope=scope, reverse=reverse)), gid, truth)


@pytest.mark.parametrize(
    "count,truth", [("have at most 0 rebounds", True), ("have over 0 rebounds", False)]
)
def test_actual_positive_appearance_zero_is_real_data(stat_sample, count, truth):
    _, scope, gid = stat_sample
    pair_success(
        execute_natural_query(question(count, scope=scope)), gid, truth, stat="REB", actual=0
    )


@pytest.mark.parametrize(
    "damage", ["null", "inf", "fractional", "negative", "missing_column", "missing_appearance"]
)
def test_missing_count_never_hidden_by_false_minutes_or_older_positive(stat_sample, damage):
    _, scope, gid = stat_sample
    frame = pd.read_csv(player_path())
    match = frame.game_id.eq(gid) & frame.player_id.eq(TATUM)
    if damage == "missing_column":
        frame = frame.drop(columns="ast")
    elif damage == "missing_appearance":
        frame = frame.loc[~match]
    else:
        frame["ast"] = frame["ast"].astype(float)
        frame.loc[match, "ast"] = {
            "null": float("nan"),
            "inf": float("inf"),
            "fractional": 0.5,
            "negative": -1,
        }[damage]
    frame.to_csv(player_path(), index=False)
    unknown(execute_natural_query(question(minutes="at least 30 minutes", scope=scope)))


def test_missing_time_never_hidden_by_false_known_count(stat_sample):
    sample, scope, gid = stat_sample
    mask = sample["ledger"].game_id.eq(gid) & sample["ledger"].player_id.eq(TATUM)
    sample["ledger"].loc[mask, "source_minutes"] = float("nan")
    unknown(execute_natural_query(question("have over 1 assist", scope=scope)))


@pytest.mark.parametrize(
    "count", ["have at least 1 assist", "have at most 0 rebounds", "have between 0 and 1 assists"]
)
def test_source_dnp_has_no_numeric_stat_appearance(pair_sample, count):
    result = execute_natural_query(question(count))
    phrase = success(result, pair_sample["ids"][-1], False)
    assert "did not play" in phrase and "with 0" not in phrase and "played 0:" not in phrase
    assert any(f["label"] == "Count check" for f in result.metadata["applied_filters"])


@pytest.mark.parametrize(
    "extra",
    [
        "have LeBron record at least 1 assist",
        "have at least 1 assist while LeBron plays",
        "have a healthy knee",
        "have at least 1 assist and win",
        "have at least 1 assist in the first half",
        "have at least 1 assist and at least 2 points",
        "have at least 1 assist while on the court",
    ],
)
def test_new_grammar_cannot_hide_changed_actor_or_extra_clause(stat_sample, extra):
    _, scope, _ = stat_sample
    result = execute_natural_query(question(extra, scope=scope))
    assert not result.metadata.get("answer_phrase")
    assert not any(
        f["label"] == "Count check" for f in result.metadata.get("applied_filters") or []
    )


def test_explicit_original_or_have_is_unfinished_without_native_older_row_bypass():
    result = execute_natural_query(
        "Did Anthony Davis play at least 30 minutes or have at least 1 assist in the Lakers last game against Celtics in 2023-24?"
    )
    assert not result.metadata.get("answer_phrase")
    assert not any(
        f["label"] == "Count check" for f in result.metadata.get("applied_filters") or []
    )


@pytest.mark.parametrize("verb", ["have", "record"])
def test_native_bare_statistical_and_restores_complete_verb(verb):
    result = execute_natural_query(
        f"Did LeBron play at least 1 minute and {verb} at least 1 assist last game?"
    )
    assert result.result_status == "ok" and result.route == "player_game_finder"
    assert result.metadata["answer_phrase"].startswith("Yes:")
    assert not any(
        f["label"] in ("Minutes check", "Count check") for f in result.metadata["applied_filters"]
    )


@pytest.mark.parametrize("wrong_side", [False, True])
def test_precise_played_report_qualifies_count_even_with_rounded_zero_minutes(
    stat_sample, wrong_side
):
    sample, scope, gid = stat_sample
    mask = sample["ledger"].game_id.eq(gid) & sample["ledger"].player_id.eq(TATUM)
    sample["ledger"].loc[mask, "source_minutes"] = 20 / 60
    frame = pd.read_csv(player_path())
    match = frame.game_id.eq(gid) & frame.player_id.eq(TATUM)
    frame.loc[match, "minutes"] = 0
    if wrong_side:
        frame.loc[match, "team_id"] = 1610612747
    frame.to_csv(player_path(), index=False)
    result = execute_natural_query(question(minutes="under 1 minute", scope=scope))
    if wrong_side:
        unknown(result)
    else:
        assert "played 0:20 with 1 AST" in pair_success(result, gid, True)


@pytest.mark.parametrize(
    "stat,word",
    [
        ("pts", "point"),
        ("reb", "rebound"),
        ("ast", "assist"),
        ("fg3m", "3PM"),
        ("stl", "steal"),
        ("blk", "block"),
        ("tov", "turnover"),
    ],
)
def test_existing_count_vocabulary_uses_same_identity_and_known_field(stat_sample, stat, word):
    _, scope, gid = stat_sample
    frame = pd.read_csv(player_path())
    frame.loc[frame.game_id.eq(gid) & frame.player_id.eq(TATUM), stat] = 1
    frame.to_csv(player_path(), index=False)
    pair_success(
        execute_natural_query(question("record at least 1 " + word, scope=scope)),
        gid,
        True,
        stat=stat.upper(),
    )


@pytest.mark.parametrize("count_first", [False, True])
def test_leading_regular_season_scope_keeps_complete_reversed_predicates(stat_sample, count_first):
    _, scope, gid = stat_sample
    predicates = (
        "have at least 1 assist and play at least 20 minutes"
        if count_first
        else "play at least 20 minutes and record at least 1 assist"
    )
    result = execute_natural_query(
        f"For the Lakers latest meeting against Boston {scope} during the 2023-24 regular season, did Tatum {predicates}?"
    )
    pair_success(result, gid, True)
