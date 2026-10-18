"""K06 comparison samples and bases are independently frozen before interpretation."""

import hashlib
import json
from functools import wraps
from pathlib import Path

import pytest

from nbatools.commands import player_compare, team_compare
from nbatools.data_source import data_path, data_read_csv
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
BINDING = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
ORACLE = json.loads((BINDING / "k06-raw-oracle.json").read_text())
CASES = ORACLE["cases"]


def _qualified_samples(case):
    sources = {}
    for source, digest in ORACLE["sources"].items():
        path = "data/raw/" + source
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
        kind = source.split("_")[0]
        frame = data_read_csv(path)
        keys = ["game_id", "team_id"] + (["player_id"] if kind == "player" else [])
        assert not frame.empty and not frame[keys].isna().any().any()
        assert not frame.duplicated(keys).any()
        assert frame.season.eq(case["season"]).all()
        assert frame.season_type.eq("Regular Season").all()
        sources[kind] = frame
    teams = sources["team"].set_index(["game_id", "team_id"])
    samples = []
    for index, expected in enumerate(case["samples"]):
        raw = sources[case["kind"]]
        selected = raw.loc[
            raw.player_id.eq(expected["entity"])
            if case["kind"] == "player"
            else raw.team_abbr.eq(expected["entity"])
        ].copy()
        original_count = len(selected)
        opponents, outcomes = [], []
        for row in selected.itertuples():
            own = teams.loc[(row.game_id, row.team_id)]
            other = teams.loc[(row.game_id, own.opponent_team_id)]
            assert other.opponent_team_id == row.team_id
            opponents.append(other.team_abbr)
            outcomes.append(own.wl)
        selected["raw_opponent"] = opponents
        selected["raw_wl"] = outcomes
        if case["date_range"]:
            start, end = case["date_range"]
            selected = selected.loc[selected.game_date.astype(str).between(start, end)]
        if case["opponent"]:
            opponent = (
                case["samples"][1 - index]["entity"]
                if case["opponent"] == "h2h"
                else case["opponent"]
            )
            selected = selected.loc[selected.raw_opponent.eq(opponent)]
        assert original_count == expected["games"] + expected["excluded_by_clause"]
        assert original_count - len(selected) == expected["excluded_by_clause"]
        if case["opponent"] or case["date_range"]:
            assert expected["excluded_by_clause"] > 0
        assert len(selected) == expected["games"]
        assert (
            sorted(selected[expected["key_columns"]].astype(int).values.tolist())
            == expected["keys"]
        )
        assert int(selected.raw_wl.eq("W").sum()) == expected["wins"]
        assert int(selected.raw_wl.eq("L").sum()) == expected["losses"]
        for stat, total in expected["sums"].items():
            assert selected[stat].sum() == total
            assert selected[stat].mean() == pytest.approx(expected["means"][stat])
        samples.append(selected)
    if case["opponent"] == "h2h":
        assert set(samples[0].game_id) == set(samples[1].game_id)
        assert case["samples"][0]["wins"] == case["samples"][1]["losses"]
    return samples


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
@pytest.mark.parametrize("wording", ["primary", "heldout"])
def test_k06_comparison_samples_and_basis(case, wording, monkeypatch):
    _qualified_samples(case)
    heldout = {
        row["id"]: row["query"]
        for row in json.loads((BINDING / "k06-heldout-wording.json").read_text())["cases"]
    }
    player = case["kind"] == "player"
    module = player_compare if player else team_compare
    attr = "summarize_player" if player else "summarize_team"
    compute = getattr(module, attr)
    captured = []

    @wraps(compute)
    def capture(frame, *args, **kwargs):
        captured.append(frame.copy())
        return compute(frame, *args, **kwargs)

    names = [sample["name"] if player else sample["entity"] for sample in case["samples"]]
    identity = {f"{case['kind']}_a": names[0], f"{case['kind']}_b": names[1]}
    dates = dict(zip(("start_date", "end_date"), case["date_range"])) if case["date_range"] else {}
    route = case["kind"] + "_compare"
    with monkeypatch.context() as scope:
        scope.setattr(module, attr, capture)
        results = [
            execute_natural_query(case["query"] if wording == "primary" else heldout[case["id"]]),
            execute_structured_query(
                route,
                season=case["season"],
                **identity,
                **dates,
                opponent=None if case["opponent"] == "h2h" else case["opponent"],
                head_to_head=case["opponent"] == "h2h",
            ),
        ]
    for result_index, result in enumerate(results):
        assert result.result_status == "ok", (result.result_reason, result.metadata)
        assert result.route == route
        assert result.metadata["season"] == case["season"]
        assert result.metadata["head_to_head_used"] == (case["opponent"] == "h2h")
        assert result.metadata["opponent"] == (
            None if case["opponent"] == "h2h" else case["opponent"]
        )
        for field, value in dates.items():
            assert result.metadata[field] == value
        assert len(captured) == 4
        sections = result.to_dict()["sections"]
        summaries = sections["summary"]
        assert len(summaries) == 2
        assert {row["player_name" if player else "team_name"] for row in summaries} == set(names)
        comparison = {row["metric"]: row for row in sections["comparison"]}
        assert len(comparison) == len(sections["comparison"])
        expected_by_name = dict(zip(names, case["samples"]))
        for index, summary in enumerate(summaries):
            entity_name = summary["player_name" if player else "team_name"]
            expected = expected_by_name[entity_name]
            frame = captured[result_index * 2 + index]
            assert len(frame) == expected["games"]
            assert (
                sorted(frame[expected["key_columns"]].astype(int).values.tolist())
                == expected["keys"]
            )
            values = {key: expected[key] for key in ("games", "wins", "losses")}
            values.update({stat + "_avg": value for stat, value in expected["means"].items()})
            values.update({stat + "_sum": value for stat, value in expected["sums"].items()})
            for key, expected_value in values.items():
                assert summary[key] == pytest.approx(expected_value, abs=0.001)
                assert set(comparison[key]) == {"metric", *names}
                assert comparison[key][entity_name] == pytest.approx(expected_value, abs=0.001)
