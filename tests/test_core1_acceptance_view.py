"""The Core-1 acceptance view scores against fixed expectations, never the run itself."""

import copy
import json

import pytest

from tools import core1_acceptance_view as view

SPEC = json.loads(view.MAP.read_bytes())
REGISTRY = json.loads((view.ROOT / ".github/data-publication-packages.json").read_bytes())


def test_map_covers_all_46_original_questions_once():
    original = json.loads((view.ROOT / SPEC["original46_source"]).read_bytes())["node_ids"]
    assert [e["id"] for e in SPEC["k08"]] == list(range(1, 47))
    assert [e["original_node_id"] for e in SPEC["k08"]] == original
    assert {e["expect"] for e in SPEC["k08"]} == {"pass", "missing_data", "live"}
    assert sorted(SPEC["groups"]) == [f"K{n:02d}" for n in range(1, 13)]
    for key, group in SPEC["groups"].items():
        assert bool(group["tests"]) is (key != "K08")
        for path in group["tests"]:
            assert (view.ROOT / path).is_file()


def test_answer_expectations_are_the_audited_live_checks():
    live = REGISTRY["packages"]["participation-2025-durant-v1"]["deployed_checks"]
    fields = [{k: v for k, v in c.items() if k != "query"} for c in live]
    for entry in SPEC["k08"]:
        check = entry.get("check", {})
        for case in check.get("cases", []):
            assert case["query"] in entry["queries"]
            assert {k: v for k, v in case.items() if k != "query"} in fields
        if "rest_count_case" in check:
            assert check["rest_count_case"] in live


def test_independent_oracle_is_pinned():
    cases = view._oracle_cases(SPEC["independent_oracle"])
    oracle_ids = [
        e["id"] for e in SPEC["k08"] if e.get("check", {}).get("kind") == "independent_oracle"
    ]
    assert sorted(cases) == oracle_ids == [7, 8, 23, 24, 25, 30, 31, 32, 41]
    damaged = dict(SPEC["independent_oracle"], sha256="0" * 64)
    with pytest.raises(ValueError):
        view._oracle_cases(damaged)


class _Client:
    def __init__(self, bodies):
        self.bodies = bodies

    def post(self, path, json):
        body = self.bodies[json["query"]]
        return type("R", (), {"json": lambda self: body})()


def _record(games, wins, losses, pts):
    return dict(
        result_status="ok",
        result_reason=None,
        route="team_record",
        result=dict(
            sections=dict(
                summary=[
                    dict(
                        team_name="Los Angeles Lakers",
                        season_start="2025-26",
                        season_end="2025-26",
                        season_type="Regular Season",
                        games=games,
                        wins=wins,
                        losses=losses,
                        pts_avg=pts,
                    )
                ]
            )
        ),
    )


def _entry(ordinal):
    return copy.deepcopy(next(e for e in SPEC["k08"] if e["id"] == ordinal))


def test_matching_answer_passes_and_changed_answer_is_a_software_failure():
    entry = _entry(35)
    good = _Client({"Lakers record without Reaves": _record(31, 17, 14, 114.419)})
    assert view._k08(entry, good, {}, [])["verdict"] == view.PASS
    bad = _Client({"Lakers record without Reaves": _record(31, 18, 13, 114.419)})
    row = view._k08(entry, bad, {}, [])
    assert row["verdict"] == view.FAIL and row["problems"]


def test_refusal_is_missing_data_but_a_numeric_answer_is_a_failure():
    entry = _entry(33)
    refused = dict(result_status="no_result", result_reason="filter_not_supported", result={})
    assert (
        view._k08(entry, _Client({"Lakers record without Davis": refused}), {}, [])["verdict"]
        == view.MISSING
    )
    invented = _Client({"Lakers record without Davis": _record(5, 3, 2, 110.0)})
    assert view._k08(entry, invented, {}, [])["verdict"] == view.FAIL


def test_a_skipped_or_absent_verifier_never_counts_as_passing():
    assert view._verdict_from_counts(dict(passed=3, failed=0, skipped=0)) == view.PASS
    assert view._verdict_from_counts(dict(passed=3, failed=0, skipped=1)) == view.FAIL
    assert view._verdict_from_counts(dict(passed=0, failed=0, skipped=0)) == view.FAIL
    entry = _entry(45)
    assert view._k08(entry, _Client({}), {}, [])["verdict"] == view.FAIL
