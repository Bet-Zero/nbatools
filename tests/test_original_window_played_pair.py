"""Original windows qualify both played predicates on the selected games only."""

import pytest

from nbatools.commands import game_finder, game_summary, player_game_finder, player_game_summary
from nbatools.commands.data_utils import validate_last_n_scope
from nbatools.query_service import VALID_ROUTES, execute_natural_query, execute_structured_query
from tests.test_qualified_played_pair import PAIR, TATUM
from tests.test_qualified_played_pair import pair_sample as _pair_sample

pair_sample = _pair_sample

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _record(**kwargs):
    options = dict(
        team="LAL",
        opponent="BOS",
        season="2023-24",
        with_player=PAIR,
        last_n=1,
        last_n_scope="original_window",
    )
    options.update(kwargs)
    return execute_structured_query("team_record", **options)


def _ids(result):
    return [int(row["game_id"]) for row in result.result.to_dict()["sections"].get("game_log", [])]


@pytest.mark.parametrize(
    "phrase", ["within their last 1 game", "among their last 1 game", "of their last 1 game"]
)
@pytest.mark.parametrize("tail", [False, True])
def test_explicit_original_window_qualifies_latest_original_not_latest_match(
    pair_sample, phrase, tail
):
    clause = "with Tatum playing while Reaves plays"
    middle = f"{clause} {phrase}" if tail else f"{phrase} {clause}"
    result = execute_natural_query(f"Lakers record against Celtics {middle} in 2023-24")
    assert result.route == "team_record"
    assert result.metadata["last_n_scope"] == "original_window"
    assert result.metadata["with_player"] == PAIR
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert not result.result.to_dict()["sections"]
    assert any(
        "before checking both played" in f["value"] for f in result.metadata["applied_filters"]
    )
    assert any("selected 1" in n for n in result.result.to_dict()["notes"])


def test_explicit_qualifying_keeps_cohort_first(pair_sample):
    result = execute_natural_query(
        "Lakers record against Celtics in their last 1 qualifying game with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "ok"
    assert result.metadata["last_n_scope"] == "qualifying"
    assert _ids(result) == [pair_sample["ids"][0]]


@pytest.mark.parametrize("scope", [None, "qualifying", "window", "outcome_window"])
def test_legacy_structured_scopes_unchanged(pair_sample, scope):
    assert _ids(_record(last_n_scope=scope)) == [pair_sample["ids"][0]]


def test_original_window_does_not_require_older_unknown_coverage(pair_sample):
    ledger = pair_sample["ledger"]
    older = ~ledger.game_id.eq(pair_sample["ids"][-1]) & ledger.participation_state.eq(
        "did_not_play"
    )
    ledger.loc[older, "participation_state"] = "unknown"
    result = _record()
    assert result.result_reason == "no_match"
    # The same incomplete older games genuinely prevent cohort-first selection.
    assert _record(last_n_scope="qualifying").result_reason != "no_match"
    assert _record(last_n_scope="qualifying").result_status == "no_result"


@pytest.mark.parametrize("damage", ["missing", "unknown", "wrong_date", "wrong_team"])
@pytest.mark.parametrize("false_stat", [False, True])
def test_selected_second_predicate_must_be_known_even_if_first_or_stat_false(
    pair_sample, damage, false_stat
):
    ledger = pair_sample["ledger"]
    mask = ledger.game_id.eq(pair_sample["ids"][-1]) & ledger.player_id.eq(TATUM)
    if damage == "missing":
        ledger.drop(ledger.index[mask], inplace=True)
    elif damage == "unknown":
        ledger.loc[mask, "participation_state"] = "unknown"
    elif damage == "wrong_date":
        ledger.loc[mask, "game_date"] = "1900-01-01"
    else:
        ledger.loc[mask, "team_id"] = 1610612752
    result = _record(
        with_player="Austin Reaves and Jayson Tatum",
        **({"stat": "pts", "min_value": 9999} if false_stat else {}),
    )
    assert result.result_status == "no_result"
    assert result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


def test_static_date_and_venue_scope_precede_original_window(pair_sample):
    candidates = pair_sample["candidates"]
    first = candidates.loc[candidates.game_id.eq(pair_sample["ids"][0])].iloc[0]
    result = _record(
        end_date=str(first.game_date)[:10],
        home_only=bool(first.is_home),
        away_only=bool(first.is_away),
    )
    assert result.result_status == "ok"
    assert _ids(result) == [int(first.game_id)]
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["games"] == 1 and row["wins"] == int(first.wl == "W")
    for stat in ["pts", "reb", "ast"]:
        assert row[stat + "_avg"] == first[stat]
    assert any(
        "original game (selected 1; both played in 1)" in c
        for c in result.result.to_dict()["caveats"]
    )


@pytest.mark.parametrize(
    "options",
    [
        {"quarter": "1"},
        {"half": "1"},
        {"wins_only": True},
        {"losses_only": True},
        {"clutch": True},
        {"opponent": ["BOS", "NYK"]},
        {"opponent": "East"},
        {"opponent": "LAL"},
        {"without_player": "LeBron James"},
        {"with_player": "Jayson Tatum"},
        {"with_player": PAIR + " and Anthony Davis"},
        {"with_player": "Jayson Tatum and Tatum"},
        {"with_player": "Jayson Tatum and Jayson Tatum"},
        {"season": None},
        {"start_season": "2022-23"},
        {"back_to_back": True},
        {"rest_days": 1},
        {"last_n": None},
    ],
)
def test_unsupported_original_window_composition_cannot_fall_back(pair_sample, options):
    result = _record(**options)
    assert result.result_reason == "filter_not_supported"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("route", sorted(VALID_ROUTES - {"team_record"}))
def test_unsupported_route_cannot_silently_drop_new_ordering(pair_sample, route):
    result = execute_structured_query(
        route,
        team="LAL",
        player="LeBron James",
        opponent="BOS",
        season="2023-24",
        last_n=1,
        last_n_scope="original_window",
        with_player=PAIR,
    )
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "selector,kwargs",
    [
        (game_summary.select_team_summary_sample, {"team": "LAL"}),
        (player_game_summary.select_player_summary_sample, {"player": "LeBron James"}),
        (game_finder.build_result, {"team": "LAL"}),
        (player_game_finder.build_result, {"player": "LeBron James"}),
    ],
)
def test_direct_consumers_reject_unimplemented_ordering(selector, kwargs):
    with pytest.raises(ValueError, match="Original participation windows"):
        selector(season="2023-24", last_n=1, last_n_scope="original_window", **kwargs)


def test_unknown_scope_is_not_qualifying():
    with pytest.raises(ValueError, match="Unknown last-N"):
        validate_last_n_scope("original_typo")


@pytest.mark.parametrize(
    "suffix",
    [
        "while LeBron plays",
        "and scores 30 points",
        "for 35 minutes",
        "if Blorg plays",
        "while Reaves is healthy",
    ],
)
def test_temporal_tail_cannot_drop_an_extra_predicate(pair_sample, suffix):
    result = execute_natural_query(
        f"Lakers record against Celtics within their last 1 game with Tatum playing while Reaves plays {suffix} in 2023-24"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("owner", ["Celtics", "Blorg", "the Celtics'"])
def test_original_window_owner_cannot_silently_become_subject(pair_sample, owner):
    result = execute_natural_query(
        f"Lakers record against Celtics among {owner} last 1 game with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "context", ["in the first quarter", "in the clutch", "on back to backs", "with one day rest"]
)
@pytest.mark.parametrize("scope", ["within their last 1 game", "in their last 1 qualifying game"])
def test_temporal_promotion_does_not_drop_other_context(pair_sample, context, scope):
    result = execute_natural_query(
        f"Lakers record {context} against Celtics {scope} with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "tail",
    ["or Lakers score at least 20", "and (Lakers score at least 20 or Lakers score at least 30)"],
)
def test_new_original_ordering_does_not_open_boolean_composition(pair_sample, tail):
    result = execute_natural_query(
        f"Lakers record against Celtics within their last 1 game with Tatum playing while Reaves plays in 2023-24 {tail}"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("n,expected", [(2, []), (4, [0])])
def test_original_multi_game_window_uses_stipulated_pair_intersection(pair_sample, n, expected):
    result = _record(last_n=n)
    ids = [int(pair_sample["ids"][index]) for index in expected]
    assert _ids(result) == ids
    assert result.result_reason == (None if ids else "no_match")
    if ids:
        summary = result.result.to_dict()["sections"]["summary"][0]
        source = pair_sample["candidates"].loc[pair_sample["candidates"].game_id.isin(ids)]
        assert summary["games"] == len(ids)
        assert summary["wins"] == int(source.wl.eq("W").sum())
        for stat in ["pts", "reb", "ast"]:
            assert summary[stat + "_avg"] == source[stat].mean()


@pytest.mark.parametrize(
    "phrase",
    [
        "in their last qualifying game",
        "in their last qualifying meeting",
        "within their last 1 qualifying game",
    ],
)
def test_explicit_qualifying_singular_and_preposition_take_precedence(pair_sample, phrase):
    result = execute_natural_query(
        f"Lakers record against Celtics {phrase} with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "ok"
    assert result.metadata["last_n_scope"] == "qualifying" and result.metadata["last_n"] == 1
    assert _ids(result) == [pair_sample["ids"][0]]


@pytest.mark.parametrize(
    "prefix",
    [
        "What was the Lakers record against Celtics within their last game",
        "Among the Lakers' last meeting against Celtics, their record",
        "Lakers record in 2023-24 against Celtics among their last meeting",
    ],
)
def test_singular_window_keeps_named_subject_and_original_candidate(pair_sample, prefix):
    result = execute_natural_query(f"{prefix} with Tatum playing while Reaves plays in 2023-24")
    assert result.metadata["team_context"]["team_abbr"] == "LAL"
    assert result.metadata["last_n_scope"] == "original_window" and result.metadata["last_n"] == 1
    assert result.result_reason == "no_match"


@pytest.mark.parametrize("phrase", ["in their last original game", "in their last 1 original game"])
def test_original_marker_never_silently_uses_cohort(pair_sample, phrase):
    result = execute_natural_query(
        f"Lakers record against Celtics {phrase} with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.metadata["last_n_scope"] == "original_window"
    assert result.result_reason == "no_match"


@pytest.mark.parametrize("phrase", ["in their original last game", "in their original last 1 game"])
def test_unread_explicit_original_marker_cannot_fall_back_to_cohort(pair_sample, phrase):
    result = execute_natural_query(
        f"Lakers record against Celtics {phrase} with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


def test_two_distinct_temporal_windows_are_not_collapsed(pair_sample):
    result = execute_natural_query(
        "Lakers record against Celtics within their last 2 games in their last 1 qualifying game with Tatum playing while Reaves plays in 2023-24"
    )
    assert result.result_status == "no_result" and result.result_reason != "no_match"
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize("last_n", [None, 1])
@pytest.mark.parametrize(
    "route",
    [
        "team_record",
        "game_summary",
        "player_game_summary",
        "game_finder",
        "player_game_finder",
        "team_split_summary",
        "player_split_summary",
    ],
)
def test_explicit_null_scope_keeps_legacy_qualifying_behavior(pair_sample, route, last_n):
    options = dict(team="LAL", opponent="BOS", season="2023-24", last_n=last_n)
    if route.startswith("player_"):
        options["player"] = "LeBron James"
    if route.endswith("split_summary"):
        options["split"] = "opponent"
    unset = execute_structured_query(route, last_n_scope=None, **options)
    qualifying = execute_structured_query(route, last_n_scope="qualifying", **options)
    assert unset.result_status == qualifying.result_status == "ok"
    assert unset.result.to_dict()["sections"] == qualifying.result.to_dict()["sections"]
    if route == "team_record":
        sections = unset.result.to_dict()["sections"]
        expected = (
            [int(pair_sample["ids"][-1])]
            if last_n
            else [int(value) for value in pair_sample["ids"]]
        )
        source = pair_sample["candidates"].loc[pair_sample["candidates"].game_id.isin(expected)]
        summary = sections["summary"][0]
        assert summary["games"] == len(expected)
        assert summary["wins"] == int(source.wl.eq("W").sum())
        for stat in ["pts", "reb", "ast"]:
            assert summary[stat + "_avg"] == source[stat].mean()
        if last_n:
            assert sorted(int(row["game_id"]) for row in sections["game_log"]) == expected
        else:
            # The accepted unfiltered record does not expose a game-log table.
            assert "game_log" not in sections
    if last_n:
        assert {
            "label": "Sample selection",
            "value": "Select the last 1 games matching the conditions",
            "kind": "window",
        } in unset.metadata["applied_filters"]


def test_scope_validation_distinguishes_unset_unknown_and_unsupported_mode():
    validate_last_n_scope(None)
    with pytest.raises(ValueError, match="Unknown last-N"):
        validate_last_n_scope("original_typo")
    with pytest.raises(ValueError, match="Original participation"):
        validate_last_n_scope("original_window")
