"""Actual deployed K01/K03 browser answers, qualified against pinned raw data."""

import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv
from tests.test_k01_identity_real_data import CASES as IDENTITY_CASES
from tests.test_k01_identity_real_data import HISTORY, _keys

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ROOT = Path(__file__).resolve().parents[1]


def _cases():
    cases = []
    for ident, query, player, seasons, team in IDENTITY_CASES:
        frames = []
        outcomes = []
        for season in seasons:
            teams = data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv")
            if player:
                raw = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
                rows = raw.loc[raw.player_id.eq(player)]
                if team:
                    rows = rows.loc[rows.team_abbr.eq(team)]
                joined = rows.merge(
                    teams[["game_id", "team_id", "wl"]],
                    on=["game_id", "team_id"],
                    validate="many_to_one",
                )
                assert len(joined) == len(rows)
                outcomes.extend(joined.wl)
            else:
                rows = teams.loc[teams.team_id.eq(1610612760)]
                assert _keys(rows, False) == HISTORY["K01-D1-" + season]["expected"]["ids"]
                outcomes.extend(rows.wl)
            assert not rows.empty
            frames.append(rows)
        rows = pd.concat(frames, ignore_index=True)
        summary = {
            "games": len(rows),
            "wins": outcomes.count("W"),
            "losses": outcomes.count("L"),
            "season_start": seasons[0],
            "season_end": seasons[-1],
        }
        for stat in ["pts", "reb", "ast"]:
            summary[stat + "_avg"] = float(rows[stat].mean())
            if player:
                summary[stat + "_sum"] = float(rows[stat].sum())
        text = [str(len(rows))]
        if ident == "E1":
            text += [
                "covered career games",
                "1996-97–2001-02",
                "earlier seasons are not in the data",
                "SEARCHED SEASONS",
            ]
        if ident.startswith("B1"):
            text += ["More than one player is named Marcus Williams", "Another player"]
        if ident == "D1":
            text += ["from 2007-08 to 2008-09", "Seattle SuperSonics"]
        cases.append(
            {
                "id": "k01_" + ident.lower(),
                "query": query,
                "text": text,
                "player": player,
                "keys": _keys(rows, bool(player)),
                "summary": summary,
            }
        )
    frozen = json.loads((ROOT / "tests/k03_expected.json").read_text())
    for case in frozen:
        ident = case["id"]
        text = {
            "K03-D1": ["20 player-games"],
            "K03-D2": ["11 players"],
            "K03-E1": ["0 games", "80+"],
            "K03-E2": ["No Matching Results"],
            "K03-C1": ["Any filter (OR)", "> 40 PTS", "> 12 AST"],
            "K03-C2": ["> 40 PTS OR > 12 REB"],
            "K03-B1": ["> 30 PTS"],
            "K03-B2": ["30+ PTS"],
            "K03-B3": ["> 35 PTS"],
            "K03-B4": ["35+ PTS"],
        }.get(ident, [])
        cases.append(
            {
                "id": ident.lower(),
                "query": case["query"],
                "text": text,
                "keys": case["keys"],
                "route": "player_occurrence_leaders"
                if ident in {"K03-A2", "K03-D2"}
                else "player_game_finder",
                "count": ident
                in {"K03-A2", "K03-B1", "K03-B2", "K03-C1", "K03-D1", "K03-D2", "K03-E1"},
                "finder": ident not in {"K03-A2", "K03-D2", "K03-E1", "K03-E2"},
            }
        )
    assert len(cases) == 26
    return cases


def test_deployed_core_identity_find_count_desktop_and_mobile(tmp_path):
    generation = os.environ["NBATOOLS_DATA_GENERATION"]
    assert generation == "queue-d-production-0574735-20260716"
    cases = _cases()
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "core-browser"
    output.mkdir(parents=True, exist_ok=True)
    inputs = tmp_path / "browser-cases.json"
    inputs.write_text(json.dumps(cases))
    # The public browser and npm installer need no NBA/GitHub credentials.
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "CI",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "NODE_EXTRA_CA_CERTS",
        "SSL_CERT_FILE",
    }
    clean_env = {key: value for key, value in os.environ.items() if key in allowed}
    subprocess.run(
        ["npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=ROOT / "frontend",
        env=clean_env,
        check=True,
        timeout=180,
    )
    subprocess.run(
        [
            "node",
            str(ROOT / "frontend/tools/captureCoreIdentityFindCount.mjs"),
            str(inputs),
            str(output),
        ],
        env=clean_env,
        check=True,
        timeout=900,
    )
    receipt = json.loads((output / "browser-receipt.json").read_text())
    assert not receipt["failures"]
    assert len(receipt["receipts"]) == 52
    for item in receipt["receipts"]:
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert ready["ready"] is True and ready["immutable_generation"] is True
            assert ready["active_generation"] == generation
    _validate_answers(receipt, cases)


def _validate_answers(receipt, cases):
    by_id = {case["id"]: case for case in cases}
    seen = set()
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        payload = item["payload"]
        result = payload["result"]
        sections = result["sections"]
        if "route" in case:
            assert payload["route"] == case["route"]
        if item["id"] == "k03-e2":
            assert (
                payload["result_status"] == "no_result" and payload["result_reason"] == "no_match"
            )
            assert not sections
            continue
        assert payload["result_status"] == "ok", payload
        if "summary" in case:
            assert len(sections["summary"]) == 1
            for key, value in case["summary"].items():
                actual = sections["summary"][0][key]
                assert (
                    actual == pytest.approx(value, abs=0.00051)
                    if isinstance(value, (int, float))
                    else actual == value
                )
            if case["player"]:
                assert _keys(pd.DataFrame(sections["game_log"]), True) == case["keys"]
            # Team record API exposes aggregate/by-season, not individual keys.
        else:
            if case["count"]:
                expected = (
                    len({row[2] for row in case["keys"]})
                    if item["id"] == "k03-d2"
                    else len(case["keys"])
                )
                assert sections["count"] == [{"count": expected}]
            if case["finder"]:
                rows = sections["finder"]
                assert len(rows) == len(case["keys"])
                raw = data_read_csv("raw/player_game_stats/2023-24_regular_season.csv")
                team_ids = dict(
                    raw[["team_abbr", "team_id"]]
                    .drop_duplicates()
                    .itertuples(index=False, name=None)
                )
                actual = {
                    (int(r["game_id"]), int(team_ids[r["team_abbr"]]), int(r["player_id"]))
                    for r in rows
                }
                assert actual == set(map(tuple, case["keys"]))
    assert seen == {(viewport, ident) for viewport in ["desktop", "mobile"] for ident in by_id}
