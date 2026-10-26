"""K12 source-bound delivery and declared repeat observations in the existing UI."""

import hashlib
import math
import os
import re
import warnings
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_k12_delivery_real_data import _assert_case, _bindings, _qualified_sources

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-DBZ_rW6j.js"
FOLDER = "k12-delivery-browser"
COMMON = ("k12-s1", "k12-r1", "k12-b1", "k12-m1")


def _cases():
    oracle, sources = _qualified_sources()
    bindings = {key.lower(): case for key, case in _bindings(oracle).items()}
    for repetition in range(1, 6):
        for key in COMMON:
            bindings[f"{key}-repeat-{repetition}"] = bindings[key]
    assert len(bindings) == 32
    return (
        [
            dict(id=key, query=case["query"], text=[], forbidden=["NaN", "undefined", "Infinity"])
            for key, case in bindings.items()
        ],
        bindings,
        sources,
    )


def _table(item, label):
    tables = [table for table in item["tables"] if table["label"] == label]
    assert len(tables) == 1, (item["id"], label, [t["label"] for t in item["tables"]])
    table = tables[0]
    return [dict(zip(table["headers"], row, strict=True)) for row in table["rows"]]


def _number(value):
    return float(value.replace(",", "").rstrip("%"))


def _assert_rendered(item, case):
    body = item["payload"]["result"]
    sections, meta, text = body["sections"], body["metadata"], item["text"]
    ident = case["id"]
    if ident == "K12-N1":
        assert "Data Not Available" in text and "Stephen Curry" in text and "2026-27" in text
        assert "No Matching Results" not in text and "0 games" not in text
        assert not item["tables"]
        return
    assert "2023-24" in text or ident == "K12-H1"
    if ident == "K12-E1":
        assert "No Matching Results" in text and "Jalen Brunson" in text and "80" in text
        assert "Data Not Available" not in text and not item["tables"]
        return
    assert "Data Not Available" not in text and "No Matching Results" not in text
    if ident in ("K12-C1", "K12-Z1"):
        expected = (
            "Jalen Brunson has had 4 games with 8+ assists and at most 0 turnovers "
            "in the 2023-24 regular season."
            if ident == "K12-C1"
            else "Nikola Jokić has had 0 games with 80+ points in the 2023-24 regular season."
        )
        assert meta["count_phrase"] == expected and expected in text
        return
    if ident in ("K12-S1", "K12-H1"):
        summary = sections["summary"][0]
        expected = case["original"]
        averages = expected["expected"]["averages"] if ident == "K12-H1" else expected["means"]
        name = "Patrick Ewing" if ident == "K12-H1" else "Stephen Curry"
        basis = (
            "over his covered career games (1996-97–2001-02)"
            if ident == "K12-H1"
            else "in the 2023-24 regular season"
        )
        assert (
            f"{name} has averaged {averages['pts']:.1f} points, "
            f"{averages['reb']:.1f} rebounds and {averages['ast']:.1f} assists {basis}."
        ) in text
        assert summary["player_name"] in text
        for stat, noun in (("pts", "points"), ("reb", "rebounds"), ("ast", "assists")):
            assert f"{summary[stat + '_avg']:.1f} {noun}" in text
        if ident == "K12-H1":
            assert "covered career games (1996-97–2001-02)" in text and "GAMES\n348" in text
            assert "earlier seasons are not in the data" in text
            assert not any("201607.png" in image for image in item["images"])
            for image in item["images"]:
                if "/headshots/" in image:
                    assert image.endswith("/121.png")
        return
    if ident == "K12-R1":
        row = _table(item, "Team record")[0]
        expected = case["original"]
        assert (
            f"The Boston Celtics are {expected['wins']}-{expected['losses']} "
            "in the 2023-24 regular season against the Knicks, "
            f"a {expected['wins'] / expected['games']:.0%} win rate."
        ) in text
        assert row["Team"].endswith("Boston Celtics")
        assert row["W-L"] == f"{expected['wins']}-{expected['losses']}"
        assert int(row["Games"]) == expected["games"]
        assert _number(row["PPG"]) == pytest.approx(expected["means"]["pts"], abs=0.051)
        assert "Knicks" in text or "NYK" in text
        assert "Nov 1, 2023" in text and "Mar 1, 2024" in text
        return
    if ident == "K12-B1":
        rows = next(table for table in item["tables"] if "3P%" in table["headers"])
        displayed = [dict(zip(rows["headers"], row, strict=True)) for row in rows["rows"]]
        expected = case["original"]["expected"]
        assert len(displayed) == 5
        for visible, raw in zip(displayed, expected, strict=True):
            assert raw["player_name"] in visible["Player"]
            assert _number(visible["3P%"]) == pytest.approx(100 * raw["metric"], abs=0.051)
            assert int(visible["3PA"]) == raw["fg3a"] >= 300
        assert "at least 300 three-point attempts" in text
        return
    if ident == "K12-L1":
        actual = sections["finder"]
        shown = _table(item, "Game log")
        assert len(shown) == len(actual) == 5
        assert "Top 5 scoring games by rookies in 2023-24." in text
        for visible, row in zip(shown, actual, strict=True):
            assert row["player_name"] in visible["Player"]
            assert visible["Player"].endswith(row["team_abbr"])
            day = datetime.strptime(row["game_date"][:10], "%Y-%m-%d")
            assert visible["Date"] == f"{day:%b} {day.day}"
            assert visible["Opp"] == row["opponent_team_abbr"] + row["opponent_team_name"]
            for stat in ("pts", "reb", "ast"):
                assert _number(visible[stat.upper()]) == row[stat]
        for caveat in body["caveats"]:
            assert caveat in text
        return
    if ident == "K12-X1":
        assert text.splitlines()[0] in ("Denver Nuggets", "DEN", "Nuggets")
        assert "110+ PTS" in text and ("MIN" in text or "Timberwolves" in text)
        shown = _table(item, "Split buckets")
        expected = {row["bucket"]: row for row in case["original"]["buckets"]}
        assert len(shown) == len(expected) == 2
        for row in shown:
            truth = expected[row["Split"].lower()]
            assert int(row["GP"]) == truth["games"]
            assert row["Record"] == f"{truth['wins']}-{truth['losses']}"
            for stat, value in truth["means"].items():
                assert _number(row[stat.upper()]) == pytest.approx(value, abs=0.051)
        return
    assert ident == "K12-M1"
    shown = {row["Metric"]: row for row in _table(item, "Comparison metrics")}
    first, second = case["original"]["samples"]
    leader, other = sorted((first, second), key=lambda sample: sample["wins"], reverse=True)
    assert (
        f"{leader['name']} has {leader['wins']} wins to {other['name']}'s {other['wins']} "
        "in the 2023-24 regular season."
    ) in text
    for sample in case["original"]["samples"]:
        assert sample["name"] in text
        for stat, value in sample["means"].items():
            assert _number(shown[stat.upper() + " Avg"][sample["name"]]) == pytest.approx(
                value, abs=0.051
            )
    assert "2023-24" in text


def _validate(receipt, bindings, sources, output):
    assert receipt["base"] in ("https://nbatools.vercel.app", "http://127.0.0.1:8765")
    assert not receipt["failures"]
    seen, repeats, per_case = set(), [], {}
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = bindings[item["id"]]
        assert item["http"] == 200 and item["query"] == item["payload"]["query"] == case["query"]
        assert not any(item[key] for key in ("errors", "missing", "forbidden", "grainErrors"))
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        for ready in (item["readinessBefore"], item["readinessAfter"]):
            assert ready["ready"] is True and ready["immutable_generation"] is True
            assert ready["active_generation"] == "availability-opening-s4-v1-20261017"
            assert not ready.get("blockers")
        assert item["freshness"]["current_through"] == "2026-06-13"
        assert item["freshness"]["status"] == "stale"
        assert "Data through 2026-06-13" in item["freshnessText"]
        assert "awaiting refresh" in item["freshnessText"].lower()
        payload, body = item["payload"], item["payload"]["result"]
        meta = body["metadata"]
        assert payload["route"] == meta["route"]
        result = SimpleNamespace(
            route=payload["route"],
            metadata=meta,
            result_status=payload["result_status"],
            result_reason=payload["result_reason"],
            result=SimpleNamespace(to_dict=lambda: body),
        )
        _assert_case(result, case, sources)
        _assert_rendered(item, case)
        elapsed = item["responseElapsedMs"]
        assert math.isfinite(elapsed) and elapsed >= 0
        if case["id"] == "K12-H1":
            assert elapsed <= 20_000
        if re.search(r"-repeat-[1-5]$", item["id"]):
            repeats.append(elapsed)
            per_case.setdefault(item["id"].split("-repeat-")[0], []).append(elapsed)
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in bindings}
    assert len(repeats) == 40
    p95 = sorted(repeats)[math.ceil(0.95 * len(repeats)) - 1]
    assert p95 <= 3000
    return dict(
        observations=40,
        p95_ms=p95,
        per_case={
            key: {
                "observations": len(values),
                "p95_ms": sorted(values)[math.ceil(0.95 * len(values)) - 1],
            }
            for key, values in per_case.items()
        },
        scope="Declared deployed primed repeats; Vercel process reuse/cold start is not established",
    )


def test_deployed_k12_delivery_desktop_and_mobile(tmp_path):
    cases, bindings, sources = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    result = _validate(receipt, bindings, sources, output)
    warnings.warn("K12_DEPLOYED_MEASUREMENTS " + str(result), stacklevel=1)
