"""Deployed K02/K04 responses checked against the frozen source oracles."""

import hashlib
import json
from datetime import date
from types import SimpleNamespace

import pytest

from nbatools.data_source import data_path, data_read_csv
from tests.test_core_identity_find_count_browser import ROOT, _capture_browser
from tests.test_k02_explicit_season_real_data import ORACLE as SUMMARY_ORACLE
from tests.test_k04_ranking_real_data import CASES as RANKING_CASES
from tests.test_k04_ranking_real_data import verify_answer

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]


def _cases():
    for source, digest in SUMMARY_ORACLE["sources"].items():
        assert hashlib.sha256(data_path("data/raw/" + source).read_bytes()).hexdigest() == digest
    cases = []
    for frozen in SUMMARY_ORACLE["cases"]:
        case = dict(frozen, id=frozen["id"].lower())
        names = {
            "BOS": "Boston Celtics",
            "DEN": "Denver Nuggets",
            201939: "Stephen Curry",
            203999: "Nikola Jokić",
        }
        name = names.get(case["entity"], case["entity"])
        # Canonical rendered name is accented for Jokic.
        if "Jokic" in str(name):
            name = "Nikola Jokić"
        case["text"] = [name, str(case["games"])]
        if case["window"]:
            n, floor = case["window"]
            case["text"] += [f"{floor}+ PTS", f"Last {n}"]
            case["text"].append(
                f"Check conditions within the last {n} games"
                if case["operation"] == "window"
                else f"Select the last {n} games matching the conditions"
            )
        if case["start"]:
            case["text"] += [
                date.fromisoformat(case[key]).strftime("%b %-d, %Y") for key in ("start", "end")
            ]
        cases.append(case)
    baseline = json.loads(
        (ROOT / "working/nba-tools-completion-program/k02-language-baseline.json").read_text()
    )
    booker = next(row for row in baseline["results"] if row["case"]["id"] == "h2")
    players = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
    rows = players.loc[players.player_id.eq(1626164)]
    cases.append(
        {
            "id": "k02-booker",
            "query": booker["case"]["query"],
            "text": ["Devin Booker", "68"],
            "kind": "player",
            "operation": "season",
            "entity": "Devin Booker",
            "window": None,
            "games": 68,
            "wins": 43,
            "losses": 25,
            "means": {stat: booker["truth"][stat + "_avg"] for stat in ("pts", "reb", "ast")},
            "keys": ["game_id", "team_id", "player_id"],
            "expected_keys": rows[["game_id", "team_id", "player_id"]].astype(int).values.tolist(),
        }
    )
    for frozen in RANKING_CASES:
        text = ["2023-24"]
        if frozen["kind"] == "player_board":
            text += [row["player_name"] for row in frozen["expected"]]
        else:
            text += ["Stephen Curry" if frozen["player_id"] == 201939 else "Jalen Brunson"]
        if frozen["id"] == "K04-A1":
            text += ["total points", "PTS TOTAL"]
        elif frozen["id"] == "K04-A2":
            text += ["PPG"]
        elif frozen["id"] == "K04-B1":
            text += ["3P%", "at least 300 three-point attempts"]
        elif frozen["id"] == "K04-B2":
            text += ["FT%", "at least 200 free-throw attempts"]
        elif frozen["kind"] == "ranked_games":
            text += ["highest-scoring"]
        elif frozen["id"] == "K04-D1":
            text += ["games with 40+ points"]
        elif frozen["id"] == "K04-D2":
            text += ["games with 10+ assists and 0 turnovers"]
        for suffix, key in [("", "query"), ("-heldout", "heldout_query")]:
            cases.append(
                {
                    "id": frozen["id"].lower() + suffix,
                    "query": frozen[key],
                    "text": text,
                    "ranking": frozen,
                }
            )
    for case in cases:
        case["forbidden"] = ["undefined", "NaN"]
    assert len(cases) == 33
    return cases


def _validate_answers(receipt, cases):
    by_id = {case["id"]: case for case in cases}
    seen = set()
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case, payload = by_id[item["id"]], item["payload"]
        assert payload["result_status"] == "ok", payload
        assert not item["missing"] and not item["forbidden"]
        if case["id"] == "k02-b1":
            assert "against NYK" in item["text"]
        if case["id"] in {"k04-c2", "k04-c2-heldout"}:
            table = next(t for t in item["tables"] if t["label"] == "Game log")
            cells = [cell for row in table["rows"] for cell in row]
            assert "106.9%" in cells and "111.1%" in cells
            if item["viewport"] == "desktop":
                assert "106.9%" in item["text"] and "111.1%" in item["text"]
            total = next(row for row in table["footers"] if "Total" in row)
            assert not any("%" in cell for cell in total)

        if "ranking" in case:
            response = SimpleNamespace(
                **{
                    key: payload.get(key)
                    for key in ("route", "result_status", "result_reason", "metadata")
                }
            )
            response.result = SimpleNamespace(to_dict=lambda: payload["result"])
            verify_answer(case["ranking"], response)
            frozen = case["ranking"]
            if frozen["kind"] == "player_board":
                table = next(t for t in item["tables"] if "Player" in t["headers"])
                column = table["headers"].index("Player")
                assert len(table["rows"]) == len(frozen["expected"]) == 5
                for row, expected in zip(table["rows"], frozen["expected"]):
                    assert expected["player_name"] in row[column]
            if frozen["kind"] == "ranked_games":
                table = next(t for t in item["tables"] if t["label"] == "Game log")
                dates = table["headers"].index("Date")
                assert [row[dates] for row in table["rows"]] == [
                    date.fromisoformat(row["game_date"]).strftime("%b %-d")
                    for row in frozen["expected_rows"]
                ]
                column = table["headers"].index("PTS")
                assert [int(row[column]) for row in table["rows"]] == [
                    row["pts"] for row in frozen["expected_rows"]
                ]
            continue
        assert payload["route"] == (
            "player_game_summary"
            if case["kind"] == "player"
            else "game_summary"
            if case["id"].startswith("k02-d")
            else "team_record"
        )
        sections = payload["result"]["sections"]
        assert len(sections["summary"]) == 1
        summary = sections["summary"][0]
        for field in ("games", "wins", "losses"):
            assert summary[field] == case[field]
        for stat, expected in case["means"].items():
            assert summary[stat + "_avg"] == pytest.approx(expected, abs=0.001)
        if case["kind"] == "player" or payload["route"] == "game_summary":
            rows = sections["game_log"]
            assert len(rows) == len(case["expected_keys"])
            assert {tuple(int(row[key]) for key in case["keys"]) for row in rows} == set(
                map(tuple, case["expected_keys"])
            )
        if case["window"]:
            assert payload["result"]["metadata"]["last_n"] == case["window"][0]
            assert payload["result"]["metadata"]["last_n_scope"] == case["operation"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_summary_ranking_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, "summary-ranking-browser")
    _validate_answers(receipt, cases)
