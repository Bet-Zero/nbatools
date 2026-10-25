"""K09's frozen answers through the actual desktop/mobile deployed interface."""

import hashlib
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_k09_sequences_real_data import SELECTION, _assert_case, _qualified_sources

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-vEjeGbzQ.js"
FOLDER = "k09-sequences-browser"
SUFFIX = {
    "query": "",
    "synonym_control_query": "-synonym",
    "last_n_control_query": "-last",
    "single_season_control_query": "-single",
}


def _cases():
    oracle, sources = _qualified_sources()
    cases, bindings = [], {}
    for ident, field in SELECTION:
        case = next(c for c in oracle["cases"] if c["id"] == ident)
        key = ident.lower() + SUFFIX[field]
        # Names here accept the canonical franchise label; payload IDs below
        # establish exact identities, and actual rendered table values are checked.
        name = (
            "Stephen Curry"
            if "player_id" in case["subject"]
            else "Celtics"
            if ident == "K09-W1"
            else "Heat"
        )
        cases.append(
            dict(
                id=key,
                query=case[field],
                text=[name],
                forbidden=[
                    "Unavailable Filter",
                    "No Matching Results",
                    "NaN",
                    "undefined",
                    "Infinity",
                ],
            )
        )
        bindings[key] = (case, field)
    return cases, bindings, sources


def _table(item, label):
    tables = [t for t in item["tables"] if t["label"] == label]
    assert len(tables) == 1, (
        item["id"],
        item["viewport"],
        label,
        [t["label"] for t in item["tables"]],
    )
    return tables[0]


def _validate(receipt, bindings, sources, output):
    assert receipt["base"] in ("https://nbatools.vercel.app", "http://127.0.0.1:8765")
    assert not receipt["failures"]
    seen = set()
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case, field = bindings[item["id"]]
        payload = item["payload"]
        assert item["http"] == 200 and item["query"] == payload["query"] == case[field]
        assert not any(item[name] for name in ("errors", "missing", "forbidden", "grainErrors"))
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        for ready in (item["readinessBefore"], item["readinessAfter"]):
            assert ready["ready"] is True and ready["immutable_generation"] is True
            assert ready[
                "active_generation"
            ] == "availability-opening-s4-v1-20261017" and not ready.get("blockers")
        meta, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert payload["result_status"] == "ok" and payload["result_reason"] is None
        assert not meta.get("unsupported_filters")
        assert meta["query_text"] == case[field]
        route = (
            "team_record"
            if case["id"] == "K09-W1" and field == "last_n_control_query"
            else case["route"]
        )
        assert payload["route"] == route
        if "player_id" in case["subject"]:
            assert meta["player"] == "Stephen Curry" and not meta.get("team")
            assert meta["player_context"]["player_id"] == case["subject"]["player_id"]
        else:
            assert meta["team"] == case["subject"].get("team_abbr", "MIA")
            assert meta["team_context"]["team_id"] == case["subject"]["team_id"]
        result = SimpleNamespace(
            result_status=payload["result_status"],
            result_reason=payload["result_reason"],
            metadata=meta,
            result=SimpleNamespace(to_dict=lambda: payload["result"]),
        )
        _assert_case(result, case, sources, field)
        if "streak" in sections:
            table = _table(item, "Streaks")
            rows = [dict(zip(table["headers"], r)) for r in table["rows"]]
            assert len(rows) == len(sections["streak"]) and not table["footers"]
            assert [r["Length"] for r in rows] == [
                f"{r['streak_length']} {'game' if r['streak_length'] == 1 else 'games'}"
                for r in sections["streak"]
            ]
            for shown, actual in zip(rows, sections["streak"], strict=True):
                assert int(shown["Games"]) == actual["games"]
                assert shown["Record"] == f"{actual['wins']}-{actual['losses']}"
                for label, key in (("Start", "start_date"), ("End", "end_date")):
                    assert shown[label] == datetime.fromisoformat(actual[key]).strftime("%b %-d")
                assert (
                    shown["Streak"]
                    == {"wins": "Wins", "pts>=20": "20+ PTS", "made_three": "Made three"}[
                        actual["condition"]
                    ]
                )
                for label, stat in (("PTS", "pts"), ("3PM", "fg3m")):
                    if label in shown:
                        assert float(shown[label]) == pytest.approx(
                            actual[stat + "_avg"], abs=0.051
                        )
            if "count" in sections:
                assert meta["primary_count"] == sections["count"][0]["count"]
                assert meta["count_phrase"] in item["text"]
        elif route == "team_record":
            table = _table(item, "Team record")
            rows = [dict(zip(table["headers"], r)) for r in table["rows"]]
            assert len(rows) == 1
            assert rows[0]["W-L"] == "7-3" and int(rows[0]["Games"]) == 10
            assert float(rows[0]["PPG"]) == pytest.approx(
                sections["summary"][0]["pts_avg"], abs=0.051
            )
            assert float(rows[0]["+/-"]) == pytest.approx(
                sections["summary"][0]["plus_minus_avg"], abs=0.051
            )
        else:
            label = "Leaderboard" if case["id"] == "K09-W1" else "Player rolling stretch windows"
            table = _table(item, label)
            assert len(table["rows"]) == len(sections["leaderboard"]) and not table["footers"]
            displayed = [dict(zip(table["headers"], r)) for r in table["rows"]]
            for shown, actual in zip(displayed, sections["leaderboard"], strict=True):
                if case["id"] == "K09-W1":
                    assert shown["W-L"] == f"{actual['wins']}-{actual['losses']}"
                    assert float(shown["Net/G"]) == pytest.approx(actual["net_per_game"], abs=0.051)
                    date_columns = (("From", "window_start_date"), ("To", "window_end_date"))
                else:
                    assert shown["Window"] == "5 games"
                    assert float(shown["3P%"].rstrip("%")) == pytest.approx(
                        actual["stretch_value"] * 100, abs=0.051
                    )
                    date_columns = (("Start", "window_start_date"), ("End", "window_end_date"))
                for label, key in date_columns:
                    assert shown[label] == datetime.fromisoformat(
                        str(actual[key]).replace("Z", "+00:00")
                    ).strftime("%b %-d")
    assert seen == {(view, ident) for view in ("desktop", "mobile") for ident in bindings}


def test_deployed_k09_sequences_desktop_and_mobile(tmp_path):
    import os

    cases, bindings, sources = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate(receipt, bindings, sources, output)
