"""Original team windows precede mixed participation and team-stat conditions."""

import pytest

from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_qualified_participation_pair import SEASON
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair
pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _record(**overrides):
    options = dict(
        team="LAL",
        opponent="BOS",
        season=SEASON,
        with_player="Anthony Davis",
        without_player="LeBron James",
        last_n=3,
        last_n_scope="original_window",
    )
    options.update(overrides)
    return execute_structured_query("team_record", **options)


def _assert_one(result, expected):
    assert result.result_status == "ok", result.metadata
    assert result.route == "team_record" and result.metadata["last_n_scope"] == "original_window"
    assert result.metadata["player"] is None and result.metadata["team"] == "LAL"
    assert result.metadata["without_player"] == "LeBron James"
    assert result.metadata["with_player"] == "Anthony Davis"
    sections = result.result.to_dict()["sections"]
    assert [int(row["game_id"]) for row in sections["game_log"]] == [int(expected.game_id)]
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (
        1,
        int(expected.wl == "W"),
        int(expected.wl == "L"),
    )
    for stat in ("pts", "reb", "ast"):
        assert row[stat + "_avg"] == expected[stat]
    assert any(
        "before checking participation" in item["value"]
        for item in result.metadata["applied_filters"]
    )


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and with Anthony Davis",
        "with Anthony Davis and with LeBron James out",
        "with Anthony Davis playing while LeBron James sits",
    ],
)
@pytest.mark.parametrize("tail", [False, True])
def test_mixed_predicates_execute_inside_original_matchup_window(qualified_pair, clause, tail):
    window = "within their last 3 games"
    middle = f"{clause} {window}" if tail else f"{window} {clause}"
    question = f"Lakers record vs Celtics {middle} in {SEASON}"
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    _assert_one(execute_natural_query(question), expected)
    _assert_one(_record(), expected)


def test_static_date_and_venue_define_the_original_team_window(qualified_pair):
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    day = str(expected.game_date)[:10]
    result = _record(
        opponent=None,
        last_n=1,
        start_date=day,
        end_date=day,
        home_only=bool(expected.is_home),
        away_only=bool(expected.is_away),
    )
    _assert_one(result, expected)
    label = next(
        item["value"]
        for item in result.metadata["applied_filters"]
        if item["label"] == "Sample selection"
    )
    assert "original game" in label and "matchup" not in label
    _assert_one(
        execute_natural_query(
            f"Lakers record without LeBron James and with Anthony Davis within their last 1 game from {day} to {day} in {SEASON}"
        ),
        expected,
    )


def test_unknown_older_game_outside_original_window_does_not_block_answer(qualified_pair):
    ledger = qualified_pair["ledger"]
    mask = ledger.game_id.eq(qualified_pair["ids"][0]) & ledger.player_id.eq(2544)
    ledger.loc[mask, "participation_state"] = "unknown"
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    _assert_one(_record(), expected)
    qualifying = _record(last_n_scope="qualifying")
    assert qualifying.result_status == "no_result" and qualifying.result_reason != "no_match"


@pytest.mark.parametrize("damage", ["missing", "unknown", "wrong_date", "wrong_team"])
@pytest.mark.parametrize("false_stat", [False, True])
def test_selected_unknown_absence_cannot_hide_behind_false_positive_or_team_stat(
    qualified_pair, damage, false_stat
):
    # The oldest selected game explicitly has Davis DNP. Its unknown LeBron
    # status must still block, even though Davis or the team-stat condition
    # would otherwise remove that row before the absence check.
    ledger = qualified_pair["ledger"]
    mask = ledger.game_id.eq(qualified_pair["ids"][0]) & ledger.player_id.eq(2544)
    if damage == "missing":
        ledger.drop(ledger.index[mask], inplace=True)
    elif damage == "unknown":
        ledger.loc[mask, "participation_state"] = "unknown"
    elif damage == "wrong_date":
        ledger.loc[mask, "game_date"] = "1900-01-01"
    else:
        ledger.loc[mask, "team_id"] = 1610612752
    result = _record(last_n=4, **(dict(stat="pts", min_value=9999) if false_stat else {}))
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]
    natural = execute_natural_query(
        f"Lakers record vs Celtics within their last 4 games without LeBron James and with Anthony Davis in {SEASON}"
    )
    assert natural.result_status == "no_result" and natural.result_reason != "no_match"


def test_team_owned_stat_is_checked_after_both_window_predicates(qualified_pair):
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    _assert_one(_record(stat="pts", min_value=float(expected.pts)), expected)
    rejected = _record(stat="pts", min_value=float(expected.pts) + 1)
    assert rejected.result_reason == "no_match" and not rejected.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James or with Anthony Davis",
        "without LeBron James and with Anthony Davis scoring 30 points",
        "with LeBron James injured and Anthony Davis playing",
        "without LeBron James and with Anthony Davis and Austin Reaves",
        "without LeBron James and with Anthony Davis of Austin Reaves",
        "without LeBron James and with Anthony Davis within Blorg",
    ],
)
def test_new_ordering_preserves_unimplemented_predicate_boundaries(qualified_pair, clause):
    result = execute_natural_query(
        f"Lakers record vs Celtics within their last 3 games {clause} in {SEASON}"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "options",
    [
        dict(quarter="1"),
        dict(half="1"),
        dict(wins_only=True),
        dict(rest_days=1),
        dict(opponent="East"),
        dict(start_season="2022-23"),
        dict(with_player="Anthony Davis and Austin Reaves"),
    ],
)
def test_existing_original_window_context_limits_remain_honest(qualified_pair, options):
    result = _record(**options)
    assert (
        result.result_reason == "filter_not_supported" and not result.result.to_dict()["sections"]
    )


def test_natural_team_stat_remains_owned_after_the_temporal_actor_boundary(qualified_pair):
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    prefix = f"Lakers record vs Celtics without LeBron James and with Anthony Davis within their last 3 games in {SEASON} where the Lakers scored at least "
    _assert_one(execute_natural_query(prefix + f"{int(expected.pts)} points"), expected)
    empty = execute_natural_query(prefix + f"{int(expected.pts) + 1} points")
    assert empty.result_reason == "no_match" and not empty.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "window",
    [
        "within the Celtics' last 3 games",
        "within the Celtics' original last 3 games",
        "in their original last 3 games",
    ],
)
def test_original_window_cannot_change_owner_or_drop_unrecognized_ordering(qualified_pair, window):
    result = execute_natural_query(
        f"Lakers record vs Celtics {window} without LeBron James and with Anthony Davis in {SEASON}"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "clause",
    [
        "without LeBron James and with Anthony Davis, scoring at least30 points",
        "with LeBron James out and Anthony Davis playing,30 points",
    ],
)
def test_temporal_suffix_does_not_hide_comma_attached_player_stat(qualified_pair, clause):
    result = execute_natural_query(
        f"Lakers record vs Celtics {clause} within their last 3 games in {SEASON}"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert "teammate_stat_condition" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "suffix",
    [
        "Davis scores 30 points",
        "Anthony Davis scores 30 points",
        "he scores 30 points",
        "he scores 130 points",
        "Blorg scores 30 points",
        "Blorg grabs 10 rebounds",
        "Davis scoring30 points",
        "Blorg scoring30 points",
        "the Lakers' Anthony Davis scores 30 points",
        "Anthony Davis of the Lakers scores 30 points",
        "Davis from the Lakers scores 30 points",
        "the Lakers' Blorg scores 30 points",
        "Blorg of the Lakers scores 30 points",
        "the player named Anthony Davis on the Lakers scores 30 points",
        "the Lakers' unindexed deep bench player Blorg scores 30 points",
        "Anthony Davis of the Lakers scoring 30 points",
    ],
)
@pytest.mark.parametrize("team_first", [False, True])
@pytest.mark.parametrize("temporal_tail", [False, True])
def test_claimed_team_bound_cannot_swallow_residual_actor_stat(
    qualified_pair, suffix, team_first, temporal_tail
):
    fixture = qualified_pair
    game = fixture["ids"][1]
    actor = fixture["players"].loc[
        fixture["players"].game_id.eq(game) & fixture["players"].player_id.eq(203076)
    ]
    team = fixture["teams"].loc[fixture["teams"].game_id.eq(game)]
    assert actor.pts.item() == 26 and team.pts.item() == 89
    clause = "without LeBron James and with Anthony Davis"
    window = "within their last 3 games"
    middle = f"{clause} {window}" if temporal_tail else f"{window} {clause}"
    conditions = ["the Lakers scored at least 80 points", suffix]
    if not team_first:
        conditions.reverse()
    question = f"Lakers record {middle} in {SEASON} vs Celtics where " + " and ".join(conditions)
    result = execute_natural_query(question)
    assert result.result_status == "no_result", result.metadata
    assert "teammate_stat_condition" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("temporal_tail", [False, True])
def test_team_bound_alone_remains_positive_after_residual_validation(qualified_pair, temporal_tail):
    clause = "without LeBron James and with Anthony Davis"
    window = "within their last 3 games"
    middle = f"{clause} {window}" if temporal_tail else f"{window} {clause}"
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    _assert_one(
        execute_natural_query(
            f"Lakers record {middle} in {SEASON} vs Celtics where the Lakers scored at least 80 points"
        ),
        expected,
    )


@pytest.mark.parametrize(
    "suffix", ["Davis scores30points", "he scores30points", "Blorg grabs10 rebounds"]
)
def test_compact_residual_actor_stat_still_cannot_become_a_team_answer(qualified_pair, suffix):
    result = execute_natural_query(
        f"Lakers record without LeBron James and with Anthony Davis within their last 3 games in {SEASON} vs Celtics where the Lakers scored at least 80 points and {suffix}"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("subject", ["", "they ", "the Lakers "])
def test_existing_inherited_team_bound_is_not_an_unindexed_actor(qualified_pair, subject):
    expected = (
        qualified_pair["teams"]
        .loc[qualified_pair["teams"].game_id.eq(qualified_pair["ids"][1])]
        .iloc[0]
    )
    question = f"Lakers record without LeBron James and with Anthony Davis within their last 3 games in {SEASON} vs Celtics where the Lakers scored at least 80 points and {subject}grabbed at least 10 rebounds"
    assert expected.reb >= 10
    _assert_one(execute_natural_query(question), expected)
