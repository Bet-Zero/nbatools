"""Controlled verifier corruption tests; these are not NBA numerical proof."""

import copy

import pytest

from nbatools.commands import _seasons
from nbatools.commands.natural_query import parse_query
from tests import core1_k08_runtime_binding as runtime
from tests.cloud_core1_k08_served_default_deployed_real_data import _rendered
from tests.core1_k08_served_default_cases import (
    STATS,
    assert_answer,
    assert_ownership_answer,
    equivalent_structured_kwargs,
    original_bindings,
)


def test_original_mapping_and_served_default_remain_exact(monkeypatch):
    monkeypatch.setattr(_seasons, "latest_served_season", lambda kind: "2025-26")
    for case in original_bindings():
        parsed = parse_query(case["query"])
        assert parsed["route"] == case["route"]
        assert parsed["route_kwargs"]["season"] == "2025-26"
        assert "this season" not in case["query"] and "current season" not in case["query"]
    assert _seasons.previous_season("Regular Season") == "2024-25"


@pytest.mark.parametrize("ordinal", [7, 8])
def test_structured_missed_sample_is_complete_qualified_club_not_unscoped_chronology(ordinal):
    case = next(c for c in original_bindings() if c["ordinal"] == ordinal)
    kwargs = equivalent_structured_kwargs(case)
    assert kwargs["season"] == "2025-26" and kwargs["team"] == "LAL"
    assert kwargs["without_player"] == "LeBron James" and "membership_player" not in kwargs
    assert kwargs["home_only"] is (ordinal == 8)


def _controlled_answer():
    case = next(c for c in original_bindings() if c["ordinal"] == 24)
    row = dict(
        game_id=999,
        team_id=1610612747,
        team_abbr="LAL",
        game_date="2026-01-01",
        season="2025-26",
        **dict.fromkeys(STATS, 5),
    )
    case["expected"] = dict(
        games=1,
        wins=1,
        losses=0,
        keys=["game_id", "team_id"],
        rows=[row],
        means=dict.fromkeys(STATS, 5),
        sums=dict.fromkeys(STATS, 5),
    )
    metadata = dict(
        season="2025-26",
        without_player="Jayson Tatum",
        team="LAL",
        opponent="BOS",
        team_context=dict(team_id=1610612747),
    )
    summary = dict(games=1, wins=1, losses=0, **{k + "_avg": 5 for k in STATS})
    body = dict(
        route=case["route"],
        query=case["query"],
        result_status="ok",
        result_reason=None,
        result=dict(
            metadata=metadata, sections=dict(summary=[summary], game_log=[copy.deepcopy(row)])
        ),
    )
    return body, case


def test_controlled_complete_answer_verifies():
    assert_answer(*_controlled_answer())


@pytest.mark.parametrize("banner", ["PROVISIONAL development data", "Provisional data"])
def test_public_rendering_cannot_accept_provisional_banner(banner):
    body, case = _controlled_answer()
    item = dict(query=case["query"], http=200, payload=body, text="2025-26 " + banner)
    with pytest.raises(AssertionError):
        _rendered(item, case)


def test_established_finder_abbreviation_schema_still_requires_exact_source_team():
    body, case = _controlled_answer()
    case.update(next(c for c in original_bindings() if c["ordinal"] == 7))
    body.update(route=case["route"], query=case["query"])
    body["result"]["metadata"]["without_player"] = "LeBron James"
    row = body["result"]["sections"]["game_log"][0]
    row.pop("team_id")
    body["result"]["sections"] = dict(finder=[row], count=[dict(count=1)])
    assert_answer(body, case)
    row["team_abbr"] = "BOS"
    with pytest.raises(AssertionError):
        assert_answer(body, case)


@pytest.mark.parametrize("damage", [None, "false_zero", "implicit_WAS", "identity"])
def test_supplemental_ownership_control_requires_published_source_positive(damage):
    body, case = _controlled_answer()
    original = case["expected"]["rows"][0]
    original.update(
        team_id=1610612742, team_abbr="DAL", player_id=1629023, player_name="P.J. Washington"
    )
    case["expected"]["keys"] = ["game_id", "team_id", "player_id"]
    control = dict(
        query="P.J. Washington stats on 2026-01-01 in 2025-26",
        kwargs=dict(start_date="2026-01-01"),
        expected=case["expected"],
    )
    body.update(route="player_game_summary", query=control["query"])
    body["result"]["metadata"] = dict(
        season="2025-26",
        player="P.J. Washington",
        player_context=dict(player_id=1629023),
        team=None,
        opponent=None,
        start_date="2026-01-01",
        end_date="2026-01-01",
    )
    body["result"]["sections"]["game_log"] = [copy.deepcopy(original)]
    if damage == "false_zero":
        body["result"]["sections"]["summary"][0]["reb_avg"] = 0
    elif damage == "implicit_WAS":
        body["result"]["metadata"]["team"] = "WAS"
    elif damage == "identity":
        body["result"]["metadata"]["player_context"]["player_id"] = 999
    if damage:
        with pytest.raises(AssertionError):
            assert_ownership_answer(body, control)
    else:
        assert_ownership_answer(body, control)


@pytest.mark.parametrize(
    "damage", ["key", "value", "sample_count", "source_refusal", "season", "subject"]
)
def test_wrong_or_unavailable_answer_never_counts_as_original_positive(damage):
    body, case = copy.deepcopy(_controlled_answer())
    if damage == "key":
        body["result"]["sections"]["game_log"][0]["game_id"] = 998
    elif damage == "value":
        body["result"]["sections"]["summary"][0]["pts_avg"] = 6
    elif damage == "sample_count":
        body["result"]["sections"]["summary"][0]["games"] = 2
    elif damage == "source_refusal":
        body.update(result_status="no_result", result_reason="no_data")
        body["result"]["sections"] = {}
    elif damage == "season":
        body["result"]["metadata"]["season"] = "2026-27"
    else:
        body["result"]["metadata"]["without_player"] = "Jaylen Brown"
    with pytest.raises(AssertionError):
        assert_answer(body, case)


def test_qualified_empty_must_remain_distinct_from_missing_source():
    case = next(c for c in original_bindings() if c["ordinal"] == 30)
    case["expected"] = dict(games=0)
    metadata = dict(
        season="2025-26",
        without_player="Jayson Tatum",
        team="LAL",
        opponent="BOS",
        stat="pts",
        min_value=120,
    )
    body = dict(
        route=case["route"],
        query=case["query"],
        result_status="no_result",
        result_reason="no_match",
        result=dict(metadata=metadata, sections={}),
    )
    assert_answer(body, case)
    body["result_reason"] = "no_data"
    with pytest.raises(AssertionError):
        assert_answer(body, case)


@pytest.mark.parametrize("damage", [None, "runtime", "host", "deployment", "publisher"])
def test_new_runtime_binding_rejects_old_or_untrusted_execution(monkeypatch, damage):
    local = {"src/nbatools/query_service.py": dict(mode="100644", sha="a" * 40)}
    remote = copy.deepcopy(local)
    if damage == "runtime":
        remote["src/nbatools/query_service.py"]["sha"] = "b" * 40

    def github(path):
        if path.startswith("deployments?"):
            return [
                dict(
                    id=1,
                    environment="Production",
                    sha="c" * 40,
                    creator=dict(login="untrusted" if damage == "publisher" else "vercel[bot]"),
                )
            ]
        if "/statuses?" in path:
            return [
                dict(
                    state="error" if damage == "deployment" else "success",
                    creator=dict(login="vercel[bot]"),
                    environment_url="https://unrelated.example"
                    if damage == "host"
                    else "https://nbatools-reviewed-brents-projects-686e97fc.vercel.app",
                )
            ]
        assert path == "git/trees/" + "c" * 40 + "?recursive=1"
        return dict(
            truncated=False,
            tree=[dict(path=path, type="blob", **entry) for path, entry in remote.items()],
        )

    monkeypatch.setattr(runtime, "_github", github)
    monkeypatch.setattr(runtime, "_local_build_tree", lambda: local)
    if damage:
        with pytest.raises(AssertionError):
            runtime.deployed_runtime_binding()
    else:
        proof = runtime.deployed_runtime_binding()
        assert proof["compared_build_files"] == 1 and proof["deployed_sha"] == "c" * 40
        assert proof["production_writes"] == proof["access_changes"] == 0
