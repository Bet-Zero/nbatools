"""Actual K10 desktop/mobile answers against the frozen playoff source binding."""

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_k10_history_real_data import (
    ROUNDS,
    _assert_case,
    _bindings,
    _qualified_sources,
    _sample,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-vEjeGbzQ.js"
FOLDER = "k10-history-browser"


def _cases():
    oracle, sources = _qualified_sources()
    bindings = {key.lower(): case for key, case in _bindings(oracle).items()}
    cases = [
        dict(
            id=key,
            query=case["query"],
            text=[
                "Seattle"
                if case["id"] == "K10-F1"
                else "Lakers"
                if case["id"] == "K10-T1"
                else "Cavaliers"
                if case["id"] == "K10-T2"
                else "Warriors"
            ],
            forbidden=["Unavailable Filter", "No Matching Results", "NaN", "undefined", "Infinity"],
        )
        for key, case in bindings.items()
    ]
    return cases, bindings, sources


def _season_rows(case, sources, season):
    return [
        r
        for r in sources[f"raw/team_game_stats/{season}_playoffs.csv"]
        if int(r["team_id"]) == case["team_id"] and not r["game_id"].zfill(10).startswith("005")
    ]


def _validate(receipt, bindings, sources, output):
    assert receipt["base"] in ("https://nbatools.vercel.app", "http://127.0.0.1:8765")
    assert not receipt["failures"]
    seen = set()
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case, payload = bindings[item["id"]], item["payload"]
        assert item["http"] == 200 and item["query"] == payload["query"] == case["query"]
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
        body, meta = payload["result"], payload["result"]["metadata"]
        assert payload["route"] == meta["route"]
        result = SimpleNamespace(
            result_status=payload["result_status"],
            result_reason=payload["result_reason"],
            metadata=meta,
            result=SimpleNamespace(to_dict=lambda: body),
        )
        _assert_case(result, case, sources)
        if phrase := meta.get("answer_phrase"):
            assert phrase in item["text"]
        assert "Regular Season" not in item["text"]
        assert len(item["tables"]) == 1
        table = item["tables"][0]
        assert not table["footers"]
        shown = [dict(zip(table["headers"], row, strict=True)) for row in table["rows"]]
        sections, ident = body["sections"], case["id"]
        if ident in ("K10-G1", "K10-Q1"):
            assert table["label"] == "Team record" and len(shown) == 1
            row, expected = shown[0], case["expected"]
            subject = sections["summary"][0]["team_name"]
            assert (
                f"The {subject} are {expected['wins']}-{expected['losses']} "
                f"in the {case['seasons'][0]} playoffs"
            ) in item["text"]
            assert row["Team"] == "GSWGolden State Warriors"
            assert row["W-L"] == f"{expected['wins']}-{expected['losses']}"
            assert int(row["Games"]) == expected["games"]
            assert float(row["Win %"].rstrip("%")) == pytest.approx(
                100 * expected["wins"] / expected["games"], abs=0.051
            )
            selected = _sample(case, sources, expected)
            assert float(row["PPG"]) == pytest.approx(
                sum(float(r["pts"]) for r in selected) / len(selected), abs=0.051
            )
            # Historical plus/minus is unqualified; use reciprocal raw scores.
            peers = {
                r["game_id"]: r
                for r in sources[f"raw/team_game_stats/{case['seasons'][0]}_playoffs.csv"]
                if int(r["team_id"]) != case["team_id"] and r["game_id"] in expected["game_ids"]
            }
            margin = sum(
                float(r["pts"]) - float(peers[r["game_id"]]["pts"]) for r in selected
            ) / len(selected)
            assert float(row["+/-"]) == pytest.approx(margin, abs=0.051)
            if ident == "K10-Q1":
                assert "elimination" in item["text"].lower()
        elif table["label"] == "Playoff series":
            actual = sections["series"]
            assert len(shown) == len(actual)
            for visible, series in zip(shown, actual, strict=True):
                assert visible["Season"] == series["season"] and series["season"] in case["seasons"]
                assert visible["Round"] == series["playoff_round"]
                assert visible["Record"] == f"{series['wins']}-{series['losses']}"
                assert visible["Result"] == series["result"]
                assert visible["Opponent"] == series["opponent_team_name"]
                rows = _season_rows(case, sources, series["season"])
                sample = [
                    r for r in rows if r["opponent_team_abbr"] == series["opponent_team_abbr"]
                ]
                assert sample and len(sample) == series["wins"] + series["losses"]
                assert sum(r["wl"] == "W" for r in sample) == series["wins"]
                assert sum(r["wl"] == "L" for r in sample) == series["losses"]
                opponents = sorted(
                    {r["opponent_team_abbr"] for r in rows},
                    key=lambda opp: min(
                        r["game_date"] for r in rows if r["opponent_team_abbr"] == opp
                    ),
                )
                assert (
                    series["playoff_round"]
                    == ROUNDS[opponents.index(series["opponent_team_abbr"]) + 1]
                )
            if ident == "K10-S1":
                assert "3-1 in playoff series" in item["text"] and "15-9 in games" in item["text"]
            if ident == "K10-R1":
                assert "Finals series" in item["text"] and "3-4 in those games" in item["text"]
        else:
            assert table["label"] == "Playoff season breakdown"
            actual = sections["by_season"]
            assert len(shown) == len(actual)
            assert [r["Season"] for r in shown] == [r["season"] for r in actual]
            for visible, season in zip(shown, actual, strict=True):
                assert season["season"] in case["seasons"]
                rows = _season_rows(case, sources, season["season"])
                wins, losses = sum(r["wl"] == "W" for r in rows), sum(r["wl"] == "L" for r in rows)
                assert visible["Record"] == f"{wins}-{losses}"
                assert int(visible["Games"]) == len(rows)
                assert float(visible["Win Pct"].rstrip("%")) == pytest.approx(
                    100 * wins / len(rows), abs=0.051
                )
                if ident == "K10-T2":
                    assert visible["Round Reached"] == "Finals"
            if ident in ("K10-A1", "K10-F1"):
                assert f"playoffs {case['expected']['appearances']} times" in item["text"]
                if ident == "K10-F1":
                    assert "Seattle SuperSonics" in item["text"]
        if ident in ("K10-T1", "K10-T2"):
            expected = case["expected"]
            assert (
                f"{expected['titles']} {'title' if expected['titles'] == 1 else 'titles'}"
                in item["text"]
            )
            assert f"({', '.join(expected['title_seasons'])})" in item["text"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in bindings}


def test_deployed_k10_history_desktop_and_mobile(tmp_path):
    cases, bindings, sources = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate(receipt, bindings, sources, output)
