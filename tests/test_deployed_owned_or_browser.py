"""Public owned-opponent OR answers retain source rows and unread-clause safety."""

import hashlib
import os
from datetime import date, datetime
from pathlib import Path

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table
from tests.test_owned_opponent_or_real_data import ORACLE, _qualify

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-CJ1uR2hx.js"
FOLDER = "owned-or-browser"
DESCRIPTION = "(Opponent: BOS, WAS; 110+ BOS OPP PTS) OR (Opponent: BOS, WAS; 125+ WAS OPP PTS)"
HEADLINE = "Lakers had 2 games matching at least one condition in 2023-24."


def _cases():
    _qualify()  # Exact frozen CSV hashes, full candidates and reciprocal final-game identities.
    assert ORACLE["generation"] == "availability-opening-s4-v1-20261017"
    assert ORACLE["manifest_sha256"] == (
        "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
    )
    query = ORACLE["query"]
    return [
        dict(
            id="owned-or-positive",
            query=query,
            text=[HEADLINE, DESCRIPTION, "Any filter (OR)", "BOS, WAS"],
            forbidden=["highest-scoring", "undefined", "NaN", "Infinity"],
        ),
        dict(
            id="owned-or-unread-prefix",
            query=query.replace("or Wizards", "or Blorg plays and Wizards"),
            text=["Can't answer that one yet", "That combination isn't supported yet."],
            forbidden=["No Matching Results", HEADLINE, "undefined", "NaN", "Infinity"],
        ),
    ]


def _positive(item, metadata, sections):
    assert metadata["boolean_filter_mode"] == "any" and not metadata["grouped_boolean_used"]
    assert metadata["stat"] is metadata["min_value"] is metadata["max_value"] is None
    assert not metadata["conditions"] and not metadata["threshold_conditions"]
    assert not metadata["extra_conditions"]
    assert metadata["boolean_filter_branches"] == [
        dict(
            scope=dict(
                season="2023-24", season_type="Regular Season", team="LAL", opponent=["BOS", "WAS"]
            ),
            conditions=[condition],
        )
        for condition in ORACLE["branches"]
    ]
    assert (
        dict(label="Any branch (OR)", kind="boolean", value=DESCRIPTION)
        in metadata["applied_filters"]
    )
    assert all(isinstance(f["value"], str) for f in metadata["applied_filters"])
    assert not any(f["kind"] == "threshold" for f in metadata["applied_filters"])
    truth = {
        row["game_id"]: row
        for row in ORACLE["candidate_rows"]
        if row["game_id"] in {key[0] for key in ORACLE["expected"]["keys"]}
    }
    expected = sorted(
        truth.values(), key=lambda row: (row["game_date"], row["game_id"]), reverse=True
    )
    rows = sections["finder"]
    assert [int(row["game_id"]) for row in rows] == [row["game_id"] for row in expected]
    assert len(rows) == ORACLE["expected"]["games"] == 2
    for actual, frozen in zip(rows, expected):
        assert (
            datetime.fromisoformat(str(actual["game_date"]).replace("Z", "+00:00"))
            .date()
            .isoformat()
            == frozen["game_date"]
        )
        for key in ("team_abbr", "opponent_team_abbr", "wl", "pts", "reb", "ast", "opponent_pts"):
            assert actual[key] == frozen[key]
    for stat, total in ORACLE["expected"]["sums"].items():
        assert sum(row[stat] for row in rows) == total
    assert sum(row["wl"] == "W" for row in rows) == ORACLE["expected"]["wins"]
    assert sum(row["wl"] == "L" for row in rows) == ORACLE["expected"]["losses"]
    table = _table(item, "Game log")
    assert len(table["rows"]) == 2
    for displayed, frozen in zip(table["rows"], expected):
        cells = dict(zip(table["headers"], displayed))
        when = date.fromisoformat(frozen["game_date"])
        assert cells["Date"] == f"{when:%b} {when.day}"
        assert cells["Team"] == "LALLos Angeles Lakers"
        assert frozen["opponent_team_abbr"] in cells["Opp"]
        assert (
            "Boston Celtics" if frozen["opponent_team_abbr"] == "BOS" else "Washington Wizards"
        ) in cells["Opp"]
        assert cells["Score"] == f"{frozen['pts']}-{frozen['opponent_pts']}"
        assert cells["W/L"] == frozen["wl"]
        for stat in ("pts", "reb", "ast"):
            assert float(cells[stat.upper()]) == frozen[stat]


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"]
        assert not item["missing"] and not item["forbidden"] and not item["grainErrors"]
        assert item["overflow"]["document"] <= item["overflow"]["viewport"]
        assert item["assets"] == [f"{receipt['base']}/assets/{ASSET}"]
        assert all(value in item["text"] for value in case["text"])
        assert not any(value in item["text"] for value in case["forbidden"])
        for ready in (item["readinessBefore"], item["readinessAfter"]):
            assert ready["ready"] is True and ready["status"] == "ready"
            assert ready["immutable_generation"] is True
            assert ready["active_generation"] == ORACLE["generation"] and not ready.get("blockers")
        assert item["screenshot"] == f"{item['viewport']}-{item['id']}.png"
        assert (
            hashlib.sha256((output / item["screenshot"]).read_bytes()).hexdigest()
            == item["screenshotSha256"]
        )
        payload = item["payload"]
        metadata, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert payload["route"] == "game_finder"
        assert metadata["team"] == "LAL" and metadata["team_context"] == {
            "team_id": ORACLE["subject"]["team_id"],
            "team_abbr": "LAL",
            "team_name": "Lakers",
        }
        assert metadata["player"] is None and not metadata.get("player_context")
        assert metadata["season"] == "2023-24" and metadata["season_type"] == "Regular Season"
        assert metadata["opponents"] == ["BOS", "WAS"] and metadata["opponent"] == "BOS, WAS"
        assert not metadata.get("opponent_context")
        if item["id"] == "owned-or-positive":
            assert payload["result_status"] == "ok" and payload["result_reason"] is None
            _positive(item, metadata, sections)
        else:
            # An unresolved extra-player clause must never be answered as a zero.
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "unsupported"
            )
            assert not sections and not item["tables"]
    assert seen == {(viewport, ident) for viewport in ("desktop", "mobile") for ident in by_id}


def test_deployed_owned_or_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
