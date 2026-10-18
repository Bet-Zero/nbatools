"""K07 deployed split values and readable scope against frozen raw buckets."""

import json

import pytest

from nbatools.data_source import data_read_csv
from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_k07_split_real_data import CASES, _qualified_buckets

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
BINDING = ROOT / "working/nba-tools-completion-program"


def _cases():
    heldout = {
        c["id"]: c["query"]
        for c in json.loads((BINDING / "k07-heldout-wording.json").read_text())["cases"]
    }
    cases = []
    teams = data_read_csv("raw/teams/teams_reference.csv")
    for frozen in CASES:
        sample = _qualified_buckets(frozen)
        name = sample["player_name" if frozen["kind"] == "player" else "team_name"].iloc[0]
        text = ([name] if frozen["kind"] == "player" else []) + frozen["seasons"]
        identity = None
        if frozen["kind"] == "team":
            reference = teams.loc[teams.team_abbr.eq(frozen["team"])]
            assert len(reference) == 1
            row = reference.iloc[0]
            assert set(sample.team_id.astype(int)) == {int(row.team_id)}
            identity = {
                "team_abbr": frozen["team"],
                "team_id": int(row.team_id),
                "team_name": str(row.team_name),
                "visible_names": [frozen["team"], str(row.team_name), name],
            }
        if frozen["opponent"]:
            text += [frozen["opponent"]]
        if frozen["venue"]:
            text += ["Home"]
        if frozen["split"] == "home_away":
            text += ["Home", "Away"]
        if frozen["stat"]:
            text += [f"{frozen['min_inclusive']}+ {frozen['stat'].upper()}"]
        for suffix, query in [("", frozen["query"]), ("-heldout", heldout[frozen["id"]])]:
            cases.append(
                {
                    "id": frozen["id"].lower() + suffix,
                    "query": query,
                    "text": text,
                    "forbidden": ["undefined", "NaN", "Infinity", "2023-24 to 2025-26"],
                    "split": frozen,
                    "team_identity": identity,
                }
            )
    assert len(cases) == 12
    return cases


def _validate_answers(receipt, cases):
    by_id = {c["id"]: c for c in cases}
    seen = set()
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        frozen = case["split"]
        response = item["payload"]
        assert response["result_status"] == "ok"
        assert response["route"] == frozen["kind"] + "_split_summary"
        assert not item["missing"] and not item["forbidden"]
        metadata, sections = response["result"]["metadata"], response["result"]["sections"]
        if identity := case["team_identity"]:
            assert metadata["team"] == identity["team_abbr"]
            for field in ("team_id", "team_abbr", "team_name"):
                assert metadata["team_context"][field] == identity[field]
            # The visible subject can use the source-backed abbreviation or
            # canonical name; an opponent mention cannot satisfy this check.
            assert item["text"].splitlines()[0] in identity["visible_names"]
        assert metadata["opponent"] == frozen["opponent"]
        assert metadata["split_type"] == frozen["split"]
        if frozen["split"] == "season":
            assert metadata["season_list"] == frozen["seasons"]
        else:
            assert metadata["season"] == frozen["seasons"][0]
        if frozen["stat"]:
            assert metadata["stat"] == frozen["stat"]
            assert metadata["min_value"] == frozen["min_inclusive"]
        rows = sections["split_comparison"]
        assert len(rows) == len(frozen["buckets"])
        table = next(t for t in item["tables"] if t["label"] == "Split buckets")
        assert len(table["rows"]) == len(rows)
        expected = {b["bucket"]: b for b in frozen["buckets"]}
        assert {r["bucket"] for r in rows} == expected.keys()
        for actual, cells in zip(rows, table["rows"]):
            truth = expected[actual["bucket"]]
            displayed = dict(zip(table["headers"], cells))
            assert displayed["Split"].lower() == truth["bucket"]
            assert int(displayed["GP"]) == actual["games"] == truth["games"]
            assert displayed["Record"] == f"{truth['wins']}-{truth['losses']}"
            for field in ("wins", "losses"):
                assert actual[field] == truth[field]
            for stat, value in truth["means"].items():
                assert actual[stat + "_avg"] == pytest.approx(value, abs=0.001)
                assert float(displayed[stat.upper()].replace(",", "")) == pytest.approx(
                    value, abs=0.051
                )
        assert sections["summary"][0]["games_total"] == sum(b["games"] for b in frozen["buckets"])
    assert seen == {(v, ident) for v in ("desktop", "mobile") for ident in by_id}


def test_deployed_split_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "split-browser")
    _validate_answers(receipt, cases)
