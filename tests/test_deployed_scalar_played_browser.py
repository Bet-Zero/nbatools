"""Scalar participation answers retain target identity and honest team evidence."""

import csv
import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET, FOLDER = "index-ClijrUhz.js", "scalar-played-browser"
ORACLE_PATH = Path(__file__).parent / "fixtures/qualified_scalar_played/source_and_baseline.json"
ORACLE = json.loads(ORACLE_PATH.read_text())
SELECTION = "Select the latest original team game before checking the played predicate"
CAVEAT = (
    "The played check is qualified on the selected original game. "
    "Table values are team-game totals, not the checked player's statistics."
)


def _cases():
    assert hashlib.sha256(ORACLE_PATH.read_bytes()).hexdigest() == (
        "1d55567df1bd2cd8ea400b1d24ac0da1e5de22fe7c917c566c4c0984fbb3ddd1"
    )
    assert ORACLE["generation"] == "availability-opening-s4-v1-20261017"
    assert (
        ORACLE["manifest_sha256"]
        == "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
    )
    for path, digest in ORACLE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    assert (
        hashlib.sha256(data_path("raw/games/2023-24_regular_season.csv").read_bytes()).hexdigest()
        == "ddc195db5d6cb3f0e42361a8b873f0cef04813e1e49b2a1a070006dcfa1f7346"
    )

    def raw(kind, season):
        with data_path(f"raw/{kind}/{season}_regular_season.csv").open() as stream:
            return list(csv.DictReader(stream))

    cases = []
    for ident, index in [
        ("scalar-played-yes", 0),
        ("scalar-played-no", 1),
        ("scalar-played-unknown-bare", 5),
    ]:
        source = ORACLE["cases"][index]
        season, identity = source["season"], source["canonical_player"]
        teams, appearances, ledger = [
            raw(kind, season)
            for kind in ["team_game_stats", "player_game_stats", "player_game_availability"]
        ]
        expected = source["selected_original_team_row"]
        candidates = [
            r
            for r in teams
            if r["team_id"] == expected["team_id"]
            and (source["opponent"] is None or r["opponent_team_abbr"] == source["opponent"])
        ]
        candidates.sort(key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)
        assert [int(r["game_id"]) for r in candidates] == source["original_candidate_game_ids"]
        assert candidates[0] == expected
        assert len({(r["game_id"], r["team_id"]) for r in teams}) == len(teams)
        other = [
            r
            for r in teams
            if r["game_id"] == expected["game_id"] and r["team_id"] == expected["opponent_team_id"]
        ]
        assert (
            len(other) == 1
            and other[0]["game_date"] == expected["game_date"]
            and other[0]["opponent_team_id"] == expected["team_id"]
        )
        facts = [
            r
            for r in ledger
            if r["game_id"] == expected["game_id"] and int(r["player_id"]) == identity["player_id"]
        ]
        positive = [
            r
            for r in appearances
            if r["game_id"] == expected["game_id"]
            and int(r["player_id"]) == identity["player_id"]
            and float(r["minutes"]) > 0
        ]
        assert (
            facts == source["report_observation_rows"]
            and positive == source["positive_appearance_rows"]
        )
        for fact in facts:
            assert (
                fact["player_name"] == identity["player_name"]
                and fact["team_id"] == expected["team_id"]
                and fact["game_date"] == expected["game_date"]
            )
            assert fact["coverage_scope"] == "listed_player_rows_only"
        if index == 5:
            # Last appearance nominates DAL only as a candidate, never current membership.
            earlier = [
                r for r in appearances if int(r["player_id"]) == 203076 and float(r["minutes"]) > 0
            ]
            earlier.sort(key=lambda r: (r["game_date"], int(r["game_id"])), reverse=True)
            assert (
                earlier[0]["game_date"] == "2026-01-08" and int(earlier[0]["game_id"]) == 22500531
            )
            assert earlier[0]["team_abbr"] == "DAL"
            assert expected["game_date"] == "2026-04-12" and int(expected["game_id"]) == 22501193
            assert not facts and not positive and source["desired_boolean"] is None
            query = "Did Anthony Davis play last game in 2025-26?"
            text = [
                "Unavailable Filter",
                "The requested filter or metric is not available in the current dataset.",
            ]
            forbidden = [
                "Yes:",
                "No:",
                "No Matching Results",
                "Dallas Mavericks",
                "DAL",
                "2026-01-08",
                "Can't answer that one yet",
                "That combination isn't supported yet",
            ]
        else:
            assert (
                len(facts) == 1
                and (facts[0]["participation_state"] == "played") is source["desired_boolean"]
            )
            assert len(positive) == int(source["desired_boolean"])
            if not positive:
                assert (
                    facts[0]["participation_state"] == "did_not_play" and facts[0]["source_comment"]
                )
            else:
                assert (
                    positive[0]["team_id"] == expected["team_id"]
                    and positive[0]["game_date"] == facts[0]["game_date"]
                )
            schedule = [r for r in raw("games", season) if r["game_id"] == expected["game_id"]]
            assert (
                len(schedule) == 1
                and schedule[0]["game_date"] == expected["game_date"]
                and schedule[0]["is_final"] == "1"
            )
            assert {schedule[0]["home_team_id"], schedule[0]["away_team_id"]} == {
                expected["team_id"],
                expected["opponent_team_id"],
            }
            query = source["query"]
            text = [
                "Yes:" if source["desired_boolean"] else "No:",
                identity["player_name"],
                "2024-02-01",
                SELECTION,
                CAVEAT,
            ]
            forbidden = [
                "Unavailable Filter",
                "No Matching Results",
                "With player",
                "Without player",
            ]
        cases.append(
            dict(
                id=ident,
                query=query,
                truth=source["desired_boolean"],
                identity=identity,
                team=source["explicit_team"] if index != 5 else None,
                opponent=source["opponent"],
                season=season,
                row=expected,
                player_box=positive[0] if positive else None,
                opponent_pts=int(other[0]["pts"]),
                text=text,
                forbidden=forbidden + ["undefined", "NaN", "Infinity"],
            )
        )
    return cases


def _validate_answers(receipt, cases, output):
    by_id, seen = {c["id"]: c for c in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        key = item["viewport"], item["id"]
        assert key not in seen
        seen.add(key)
        case, payload = by_id[item["id"]], item["payload"]
        assert item["query"] == payload["query"] == case["query"]
        assert (
            item["http"] == 200
            and not item["errors"]
            and not item["missing"]
            and not item["forbidden"]
            and not item["grainErrors"]
        )
        assert all(t in item["text"] for t in case["text"]) and not any(
            t in item["text"] for t in case["forbidden"]
        )
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        for ready in [item["readinessBefore"], item["readinessAfter"]]:
            assert (
                ready["ready"] is True
                and ready["status"] == "ready"
                and ready["immutable_generation"] is True
            )
            assert ready["active_generation"] == ORACLE["generation"] and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        result = payload["result"]
        m, sections = result["metadata"], result["sections"]
        assert (
            m["player"] == case["identity"]["player_name"]
            and m["player_context"] == case["identity"]
        )
        assert m["season"] == case["season"] and not m["with_player"] and not m["without_player"]
        if case["truth"] is None:
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "filter_not_supported"
            )
            assert not sections and not item["tables"] and not m.get("answer_phrase")
            assert m["team"] is None and not m.get("team_context") and not m.get("opponent_context")
            assert m["opponent"] is None
            assert not any(f["label"] == "Played check" for f in m.get("applied_filters", []))
            assert "Incomplete game-day participation coverage for Anthony Davis" in result["notes"]
            continue
        assert (
            payload["route"] == "game_finder"
            and payload["result_status"] == "ok"
            and payload["result_reason"] is None
        )
        assert m["team"] == case["team"] and m["opponent"] == case["opponent"]
        assert m["team_context"]["team_id"] == int(case["row"]["team_id"]) and m[
            "opponent_context"
        ]["team_id"] == int(case["row"]["opponent_team_id"])
        assert (
            m["last_n"] == 1 and m["last_n_scope"] == "window" and not m.get("unsupported_filters")
        )
        assert m.get("intent") != "unsupported" and not any(
            "unsupported_boundary" in str(n) for n in m.get("notes", [])
        )
        phrase = m["answer_phrase"]
        assert (
            phrase.startswith("Yes:" if case["truth"] else "No:")
            and case["identity"]["player_name"] in phrase
            and "2024-02-01" in phrase
        )
        if case["truth"]:
            actual = case["player_box"]
            statline = (
                f"{actual['pts']} points, {actual['reb']} rebounds and {actual['ast']} assists"
            )
            assert statline in phrase and statline in item["text"]
        else:
            assert not any(word in phrase.lower() for word in ["points", "rebounds", "assists"])
        filters = m["applied_filters"]
        check = next(f for f in filters if f["label"] == "Played check")
        assert case["identity"]["player_name"] in check["value"] and check["value"] in item["text"]
        selection = next(f for f in filters if f["label"] == "Sample selection")
        assert selection == dict(label="Sample selection", value=SELECTION, kind="window")
        assert f"PLAYED CHECK\n{check['value']}" in item["text"] and not any(
            f["label"] in ["With player", "Without player"] for f in filters
        )
        assert (
            "with player" not in item["text"].lower()
            and "without player" not in item["text"].lower()
        )
        assert CAVEAT in result["caveats"] and CAVEAT in item["text"]
        assert set(sections) == {"finder"} and len(sections["finder"]) == 1
        row, truth = sections["finder"][0], case["row"]
        assert not any(k in row for k in ["player_id", "player_name", "player"])
        for field in ["game_id", "team_id", "opponent_team_id", "pts", "reb", "ast"]:
            assert row[field] == int(truth[field])
        for field in ["team_abbr", "team_name", "opponent_team_abbr", "opponent_team_name", "wl"]:
            assert row[field] == truth[field]
        assert (
            datetime.fromisoformat(str(row["game_date"]).replace("Z", "+00:00")).date().isoformat()
            == truth["game_date"]
        )
        assert row["plus_minus"] == int(truth["pts"]) - case["opponent_pts"]
        table = _table(item, "Game log")
        assert len(table["rows"]) == 1 and "Player" not in table["headers"]
        cells = dict(zip(table["headers"], table["rows"][0]))
        day = date.fromisoformat(truth["game_date"])
        assert cells["Date"] == f"{day:%b} {day.day}"
        assert (
            cells["Team"] == truth["team_abbr"] + truth["team_name"]
            and cells["Opp"] == truth["opponent_team_abbr"] + truth["opponent_team_name"]
        )
        assert (
            cells["Score"] == f"{truth['pts']}-{case['opponent_pts']}"
            and cells["W/L"] == truth["wl"]
        )
        for stat in ["pts", "reb", "ast"]:
            assert float(cells[stat.upper()]) == int(truth[stat])
    assert seen == {(view, ident) for view in ["desktop", "mobile"] for ident in by_id}


def test_deployed_scalar_played_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
