"""K11 exact source populations and labels through actual desktop/mobile search."""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_k11_population_real_data import _assert_case, _bindings, _qualified_sources

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-J0ysoRNG.js"
FOLDER = "k11-population-browser"


def _cases():
    oracle, sources = _qualified_sources()
    bindings = {key.lower(): case for key, case in _bindings(oracle).items()}
    cases = [
        dict(
            id=key,
            query=case["query"],
            text=[case["season"]],
            forbidden=["Unavailable Filter", "No Matching Results", "NaN", "undefined", "Infinity"],
        )
        for key, case in bindings.items()
    ]
    assert len(cases) == 11
    return cases, bindings, sources


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
            assert ready["active_generation"] == "availability-opening-s4-v1-20261017"
            assert not ready.get("blockers")
        body, meta = payload["result"], payload["result"]["metadata"]
        assert payload["route"] == meta["route"]
        result = SimpleNamespace(
            result_status=payload["result_status"],
            result_reason=payload["result_reason"],
            metadata=meta,
            result=SimpleNamespace(to_dict=lambda: body),
        )
        _assert_case(result, case, sources)
        league = case["id"] in ("K11-L1", "K11-L2")
        rows = body["sections"]["leaderboard" if league else "finder"]
        assert len(item["tables"]) == 1
        table = item["tables"][0]
        assert table["label"] == ("Top performances" if league else "Game log")
        assert not table["footers"]
        shown = [dict(zip(table["headers"], row, strict=True)) for row in table["rows"]]
        assert len(shown) == len(rows) == case["limit"]
        assert not {"Score", "Margin", "Opp PTS"} & set(table["headers"])
        qualified_names = {
            (str(row["game_id"]).zfill(10), int(row["player_id"])): row
            for row in sources[f"raw/player_game_stats/{case['season']}_regular_season.csv"]
        }
        for visible, raw in zip(shown, rows, strict=True):
            source = qualified_names[(str(raw["game_id"]).zfill(10), int(raw["player_id"]))]
            assert raw["team_name"] == source["team_name"]
            assert raw["opponent_team_name"] == source["opponent_team_name"]
            assert int(visible["Rank" if league else "#"]) == int(raw["rank"])
            assert raw["player_name"] in visible["Player"]
            assert visible["Player"].endswith(raw["team_abbr"])
            day = datetime.strptime(str(raw["game_date"])[:10], "%Y-%m-%d")
            assert visible["Date"] == f"{day:%b} {day.day}"
            assert visible["Opp"] == raw["opponent_team_abbr"] + raw["opponent_team_name"]
            if not league:
                assert visible["TM"] == raw["team_abbr"] + raw["team_name"]
            for stat in ("pts", "reb", "ast"):
                assert float(visible[stat.upper()]) == float(raw[stat])
        metric = {"pts": "scoring", "reb": "rebounding", "ast": "assist"}[case["metric"]]
        if league:
            unit = {"pts": "points", "reb": "rebounds", "ast": "assists"}[case["metric"]]
            first = rows[0]
            assert (
                f"{first['player_name']} had the top {metric} game in the {case['season']} "
                f"regular season with {int(first[case['metric']])} {unit}"
            ) in item["text"]
        else:
            population = (
                f"{'rookie ' if case.get('rookies') else ''}{case['position']}"
                if case.get("position")
                else "rookies"
                if case.get("rookies")
                else "players"
            )
            if case.get("team"):
                population = {"LAL": "Lakers", "BOS": "Celtics"}[case["team"]] + " " + population
            assert (
                f"Top {case['limit']} {metric} games by {population} in {case['season']}."
                in item["text"]
            )
            assert (
                f"{rows[0]['player_name']}'s {case['limit']} highest-scoring games"
                not in item["text"]
            )
        for caveat in body.get("caveats", []):
            assert caveat in item["text"]
        if case.get("opponent"):
            assert "OPPONENT\n" + case["opponent"] in item["text"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in bindings}


def test_deployed_k11_population_desktop_and_mobile(tmp_path):
    cases, bindings, sources = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate(receipt, bindings, sources, output)
