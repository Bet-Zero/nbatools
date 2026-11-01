"""Controlled reported-rest positives are distinct from DNP, health and missing data."""

import pandas as pd
import pytest

from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_qualified_participation_pair import SEASON
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair
pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.fixture
def reported(qualified_pair, monkeypatch):
    data = qualified_pair
    # Independent stipulated reasons over the four controlled participation games.
    observations = []
    for row in data["ledger"].itertuples():
        if row.participation_state != "did_not_play":
            continue
        rest = (row.player_id == 203076 and row.game_id == data["ids"][0]) or (
            row.player_id == 2544 and row.game_id == data["ids"][1]
        )
        observations.append(
            dict(
                game_id=row.game_id,
                game_date=row.game_date,
                team_id=row.team_id,
                player_id=row.player_id,
                player_name=row.player_name,
                reported_reason="reported_rest" if rest else "reported_other",
            )
        )
    data["reasons"] = pd.DataFrame(observations)
    monkeypatch.setattr(reasons, "load_observations", lambda *args: data["reasons"].copy())
    return data


def _options(**extra):
    return dict(
        team="LAL",
        season=SEASON,
        opponent="BOS",
        without_player="Anthony Davis",
        without_player_reason="reported_rest",
        **extra,
    )


def _ids(result):
    sections = result.result.to_dict()["sections"]
    return {int(row["game_id"]) for row in sections.get("finder", sections.get("game_log", []))}


@pytest.mark.parametrize("floor", [80, 90])
def test_explicit_team_gerund_keeps_its_bound_after_mixed_reason(reported, floor):
    query = (
        "Lakers record when LeBron James rests and Anthony Davis plays, "
        f"scoring at least {floor} points as a team vs Celtics in {SEASON}"
    )
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["min_value"] == floor
    assert "teammate_stat_condition" not in parsed["route_kwargs"].get("unsupported_filters", [])
    result = execute_natural_query(query)
    expected = reported["teams"].loc[lambda f: f.game_id.eq(reported["ids"][1]) & f.pts.ge(floor)]
    if expected.empty:
        assert result.result_status == "no_result" and result.result_reason == "no_match"
    else:
        assert result.result_status == "ok"
        assert _ids(result) == set(expected.game_id.astype(int))


@pytest.mark.parametrize("actor", ["Anthony Davis", "Alex"])
def test_team_gerund_does_not_hide_following_actor_bound(reported, actor):
    result = execute_natural_query(
        "Lakers record when LeBron James rests and Anthony Davis plays, "
        f"scoring at least 80 points as a team, {actor} scores 30 vs Celtics in {SEASON}"
    )
    assert result.result_status == "no_result"
    assert "teammate_stat_condition" in result.metadata["unsupported_filters"]
    assert not result.result.to_dict()["sections"]


@pytest.mark.parametrize(
    "route",
    ["team_record", "game_summary", "game_finder", "player_game_summary", "player_game_finder"],
)
def test_five_consumers_select_reported_rest_not_every_dnp(reported, route):
    kwargs = _options()
    if route.startswith("player"):
        kwargs["player"] = "Austin Reaves"
    result = execute_structured_query(route, **kwargs)
    assert result.result_status == "ok", result.metadata
    assert _ids(result) == {reported["ids"][0]}
    assert result.result.metadata["reported_reason_basis"] == "officially reported Rest"
    assert result.result.metadata["reported_reason_coverage"]["reported_other"] == 1


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when Davis rests vs Celtics in 2023-24",
        "Lakers record when Anthony Davis rested vs Celtics in 2023-24",
        "Lakers record in 2023-24 when Davis is resting vs Celtics",
        "Austin Reaves stats when Davis rests vs Celtics in 2023-24",
        "Austin Reaves 20 point games when Davis rests vs Celtics in 2023-24",
    ],
)
def test_scalar_reason_survives_shared_name_scope_and_primary_ownership(reported, query):
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["without_player"] == "Anthony Davis", parsed
    assert parsed["route_kwargs"]["without_player_reason"] == "reported_rest", parsed
    assert parsed["player"] == ("Austin Reaves" if query.startswith("Austin") else None)
    result = execute_natural_query(query)
    expected = reported["players"].loc[
        lambda f: f.game_id.eq(reported["ids"][0]) & f.player_id.eq(1630559)
    ]
    if "20 point" in query and expected.pts.lt(20).all():
        assert result.result_status == "no_result" and result.result_reason == "no_match", (
            result.metadata
        )
    else:
        assert result.result_status == "ok", result.metadata
        assert _ids(result) == {reported["ids"][0]}


@pytest.mark.parametrize(
    "route",
    ["team_record", "game_summary", "game_finder", "player_game_summary", "player_game_finder"],
)
def test_unknown_reason_is_not_hidden_by_a_stat_filter(reported, route):
    target = reported["ids"][2]
    reported["reasons"].loc[
        lambda f: f.game_id.eq(target) & f.player_id.eq(203076), "reported_reason"
    ] = "unknown"
    kwargs = _options(stat="pts", min_value=500)
    if route.startswith("player"):
        kwargs["player"] = "Austin Reaves"
    result = execute_structured_query(route, **kwargs)
    assert result.result_status == "no_result" and result.result_reason != "no_match", (
        result.metadata
    )
    assert result.result.metadata["reported_reason_coverage"]["unknown"] == 1


def test_unknown_reason_is_not_hidden_by_a_false_played_sibling(reported):
    reported["reasons"].loc[
        lambda f: f.game_id.eq(reported["ids"][2]) & f.player_id.eq(203076), "reported_reason"
    ] = "unknown"
    result = execute_structured_query("team_record", **_options(with_player="LeBron James"))
    assert result.result_status == "no_result" and result.result_reason != "no_match"


def test_complete_other_reasons_are_a_known_empty_match(reported):
    reported["reasons"].loc[:, "reported_reason"] = "reported_other"
    result = execute_structured_query("team_record", **_options())
    assert result.result_status == "no_result" and result.result_reason == "no_match", (
        result.metadata
    )
    evidence = result.result.metadata["reported_reason_coverage"]
    assert evidence["reported_rest"] == evidence["unknown"] == 0
    assert evidence["qualified_nonparticipations"] == evidence["reported_other"] == 2


def test_binary_absence_does_not_read_companion_reasons(reported, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Binary queries must not load reason data")

    monkeypatch.setattr(reasons, "load_observations", forbidden)
    options = _options()
    options.pop("without_player_reason")
    result = execute_structured_query("team_record", **options)
    assert result.result_status == "ok" and _ids(result) == {reported["ids"][0], reported["ids"][2]}


def test_unknown_outside_original_window_is_irrelevant_but_selected_unknown_blocks(reported):
    row = reported["reasons"].player_id.eq(2544) & reported["reasons"].game_id.eq(
        reported["ids"][0]
    )
    reported["reasons"].loc[row, "reported_reason"] = "unknown"
    options = dict(
        team="LAL",
        opponent="BOS",
        season=SEASON,
        without_player="LeBron James",
        without_player_reason="reported_rest",
        with_player="Anthony Davis",
        last_n=3,
        last_n_scope="original_window",
    )
    result = execute_structured_query("team_record", **options)
    assert result.result_status == "ok" and _ids(result) == {reported["ids"][1]}, result.metadata
    result = execute_structured_query("team_record", **{**options, "last_n": 4})
    assert result.result_status == "no_result" and result.result_reason != "no_match"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when Davis rests and Davis scores 30 points vs Celtics in 2023-24",
        "Lakers record when Davis rests and with LeBron James injured vs Celtics in 2023-24",
        "Lakers record when Davis rests or LeBron James plays vs Celtics in 2023-24",
        "Lakers record when Davis rests and LeBron James is healthy vs Celtics in 2023-24",
    ],
)
def test_reason_clause_keeps_unimplemented_actor_stat_status_or_meaning(reported, query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason != "no_match", (
        result.metadata
    )


def test_natural_original_window_does_not_fall_back_to_last_qualifying_rest(reported):
    # Rest is oldest game; original last three have no Rest, while last three
    # qualifying Rest would incorrectly return that oldest game.
    query = "Lakers record within their last 3 games when Davis rests vs Celtics in 2023-24"
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["last_n_scope"] == "original_window", parsed
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason == "no_match", (
        result.metadata
    )


@pytest.mark.parametrize(
    "query",
    [
        "How many games did Anthony Davis rest in 2023-24?",
        "How many home games did Anthony Davis rest in 2023-24?",
        "Which games has Anthony Davis rested in 2023-24?",
        "Anthony Davis rested games in 2023-24",
    ],
)
def test_reason_counts_reuse_missed_game_scope_without_binary_equivalence(reported, query):
    parsed = parse_query(query)
    assert parsed["route_kwargs"].get("without_player_reason") == "reported_rest", parsed
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    expected = reported["teams"].loc[lambda f: f.game_id.eq(reported["ids"][0])]
    if "home" in query:
        expected = expected.loc[expected.is_home]
    sections = result.result.to_dict()["sections"]
    if "count" in sections:
        assert sections["count"][0]["count"] == len(expected)
    else:
        assert _ids(result) == set(expected.game_id)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when Davis rests and LeBron James plays vs Celtics in 2023-24",
        "Lakers record when LeBron James plays and Davis rests vs Celtics in 2023-24",
    ],
)
def test_rest_reason_composes_with_independently_owned_played_actor(reported, query):
    parsed = parse_query(query)
    assert parsed["route_kwargs"].get("without_player_reason") == "reported_rest", parsed
    result = execute_natural_query(query)
    # Davis rested only in game3; LeBron explicitly DNP in that game.
    assert result.result_status == "no_result" and result.result_reason == "no_match", (
        result.metadata
    )
    assert result.result.metadata["reported_reason_coverage"]["reported_rest"] == 1


def test_reason_coverage_counts_games_once_for_player_grain_rows(reported):
    sample = pd.concat([reported["teams"], reported["teams"]], ignore_index=True)
    evidence = {}
    selected = reasons.filter_reported_rest(
        sample, "Anthony Davis", [SEASON], "Regular Season", evidence=evidence
    )
    assert len(selected) == 2 and set(selected.game_id) == {reported["ids"][0]}
    assert evidence["requested_games"] == 4 and evidence["qualified_nonparticipations"] == 2


def test_actual_complete_other_count_is_zero_with_explicit_basis(reported):
    reported["reasons"].loc[:, "reported_reason"] = "reported_other"
    result = execute_natural_query("How many games did Anthony Davis rest in 2023-24?")
    assert (
        result.result_status == "ok"
        and result.result.to_dict()["sections"]["count"][0]["count"] == 0
    )
    assert "officially reported Rest" in result.metadata["answer_phrase"]
    assert result.result.metadata["reported_reason_coverage"]["unknown"] == 0


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when Davis rests and where Lakers scored 80 and Lakers reserve Blorg scored 30 points vs Celtics in 2023-24",
        "Lakers record when Davis rests and where Lakers scored 80 and Lakers reserve Blorg scored30 points vs Celtics in 2023-24",
        "Lakers record from 2023-11-01 to 2024-04-01 when Davis rests and Blorg scores 30 points vs Celtics in 2023-24",
        "Lakers record when Davis rests from 2023-11-01 to 2024-04-01 and Blorg scores 30 points vs Celtics in 2023-24",
        "Lakers record when LeBron James scores 30 points and Davis rests vs Celtics in 2023-24",
        "Lakers record when Davis rests and LeBron James scores 30 points vs Celtics in 2023-24",
        "Lakers record when Lakers reserve Blorg scores 30 points and Davis rests vs Celtics in 2023-24",
        "Lakers record when Davis rests and where Lakers scored 80 and Anthony Davis of the Lakers scores 30 points vs Celtics in 2023-24",
        "Lakers record when Davis rests and where Lakers scored 80 and Lakers reserve Blorg 30 points vs Celtics in 2023-24",
        "Lakers record when Davis rests and Davis 30 points vs Celtics in 2023-24",
    ],
)
def test_all_unclaimed_stat_owners_survive_calendar_and_clause_order(reported, query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported", (
        result.metadata
    )
    assert "teammate_stat_condition" in result.metadata["unsupported_filters"], result.metadata


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when Davis rests and where Lakers scored 80 vs Celtics in 2023-24",
        "Lakers record when Lakers scored 80 and Davis rests vs Celtics in 2023-24",
        "Austin Reaves scores 5 points when Davis rests vs Celtics in 2023-24",
    ],
)
def test_claimed_team_and_primary_player_bounds_keep_their_own_rows(reported, query):
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    assert _ids(result) == {reported["ids"][0]}
