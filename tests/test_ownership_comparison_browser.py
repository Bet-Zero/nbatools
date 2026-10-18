"""Deployed K05/K06 values and visible scope, backed by frozen raw samples."""

import json

import pytest

from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_k05_subject_ownership_real_data import CASES as OWNERSHIP_CASES
from tests.test_k05_subject_ownership_real_data import HELDOUT as OWNERSHIP_HELDOUT
from tests.test_k05_subject_ownership_real_data import _qualified_sample
from tests.test_k06_comparison_real_data import _qualified_samples

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
BINDING = ROOT / "working/nba-tools-completion-program"


def _cases():
    cases = []
    for frozen in OWNERSHIP_CASES:
        sample = _qualified_sample(frozen)
        name = (
            sample.player_name.iloc[0] if frozen["kind"] == "player" else sample.team_name.iloc[0]
        )
        text = [
            name,
            "2023-24",
            "Home" if frozen["venue"] == "home" else "Away",
            f"{frozen['own_pts_min_inclusive']}+ PTS",
            f"Opp PTS < {frozen['opponent_pts_max_exclusive']}",
        ]
        if frozen["kind"] == "player":
            text += [f"with fewer than {frozen['opponent_pts_max_exclusive']} OPP PTS"]
        for suffix, query in [("", frozen["query"]), ("-heldout", OWNERSHIP_HELDOUT[frozen["id"]])]:
            cases.append(
                {
                    "id": frozen["id"].lower() + suffix,
                    "query": query,
                    "text": text,
                    "forbidden": ["undefined", "NaN"],
                    "ownership": frozen,
                }
            )
    oracle = json.loads((BINDING / "k06-raw-oracle.json").read_text())
    heldout = {
        c["id"]: c["query"]
        for c in json.loads((BINDING / "k06-heldout-wording.json").read_text())["cases"]
    }
    for frozen in oracle["cases"]:
        _qualified_samples(frozen)
        text = [s["name"] if frozen["kind"] == "player" else s["entity"] for s in frozen["samples"]]
        text += ["2023-24"] if not frozen["date_range"] else ["Jan 1–31, 2024"]
        if frozen["opponent"] == "h2h":
            text += ["head-to-head"]
        elif frozen["opponent"] == "LAL":
            text += ["OPPONENT", "LAL"]
        for suffix, query in [("", frozen["query"]), ("-heldout", heldout[frozen["id"]])]:
            cases.append(
                {
                    "id": frozen["id"].lower() + suffix,
                    "query": query,
                    "text": text,
                    "forbidden": ["undefined", "NaN"],
                    "comparison": frozen,
                }
            )
    assert len(cases) == 20
    return cases


def _summary_matches(actual, expected):
    for field in ("games", "wins", "losses"):
        assert actual[field] == expected[field]
    for stat, value in expected["means"].items():
        assert actual[stat + "_avg"] == pytest.approx(value, abs=0.001)


def _validate_answers(receipt, cases):
    by_id = {c["id"]: c for c in cases}
    seen = set()
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case, response = by_id[item["id"]], item["payload"]
        assert response["result_status"] == "ok", response
        assert not item["missing"] and not item["forbidden"]
        result = response["result"]
        metadata, sections = result["metadata"], result["sections"]
        rows = sections["summary"]
        if "ownership" in case:
            frozen = case["ownership"]
            player = frozen["kind"] == "player"
            assert response["route"] == ("player_game_summary" if player else "team_record")
            assert len(rows) == 1
            _summary_matches(rows[0], frozen)
            if player:
                games = sections["game_log"]
                assert len(games) == frozen["games"]
                assert (
                    sorted([[int(r[k]) for k in frozen["key_columns"]] for r in games])
                    == frozen["keys"]
                )
        else:
            frozen = case["comparison"]
            assert response["route"] == frozen["kind"] + "_compare"
            assert len(rows) == len(frozen["samples"]) == 2
            field = "player_name" if frozen["kind"] == "player" else "team_name"
            table = next(t for t in item["tables"] if t["label"] == "Comparison metrics")
            assert table["headers"][1:3] == [row[field] for row in rows]
            displayed = {row[0]: row for row in table["rows"]}
            for column, actual in enumerate(rows, start=1):
                assert int(displayed["Games"][column]) == actual["games"]
                assert displayed["Record"][column] == f"{actual['wins']}-{actual['losses']}"
                for stat in ("pts", "reb", "ast"):
                    assert float(
                        displayed[stat.upper() + " Avg"][column].replace(",", "")
                    ) == pytest.approx(actual[stat + "_avg"], abs=0.051)
            matched = set()
            comparison = {row["metric"]: row for row in sections["comparison"]}
            assert len(comparison) == len(sections["comparison"])
            for row in rows:
                sample = next(
                    s for s in frozen["samples"] if row[field] in (s["name"], s["entity"])
                )
                assert sample["entity"] not in matched
                matched.add(sample["entity"])
                _summary_matches(row, sample)
                values = {key: sample[key] for key in ("games", "wins", "losses")}
                values.update({stat + "_avg": value for stat, value in sample["means"].items()})
                values.update({stat + "_sum": value for stat, value in sample["sums"].items()})
                for metric, value in values.items():
                    assert row[metric] == pytest.approx(value, abs=0.001)
                    assert comparison[metric][row[field]] == pytest.approx(value, abs=0.001)
            assert bool(metadata.get("head_to_head_used")) == (frozen["opponent"] == "h2h")
            if frozen["opponent"] == "LAL":
                assert metadata["opponent"] == "LAL"
            if frozen["date_range"]:
                assert [metadata["start_date"], metadata["end_date"]] == frozen["date_range"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_ownership_comparison_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "ownership-comparison-browser")
    _validate_answers(receipt, cases)
