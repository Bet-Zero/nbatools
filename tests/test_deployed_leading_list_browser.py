"""Leading-list request identity and honest third-team refusal through public UI."""

import hashlib
import os
from pathlib import Path

import pytest

from tests.test_core_identity_find_count_browser import _capture_browser
from tests.test_deployed_union_pair_browser import _table
from tests.test_owned_opponent_or_real_data import ORACLE, _qualify

pytestmark = [pytest.mark.needs_data, pytest.mark.query, pytest.mark.slow]
ASSET = "index-ClijrUhz.js"
FOLDER = "leading-list-browser"
REFUSAL = "A condition on another named team's statistics is not supported for this sample yet."


def _cases():
    assert ORACLE["generation"] == "availability-opening-s4-v1-20261017"
    assert (
        ORACLE["manifest_sha256"]
        == "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
    )
    _qualify()  # Authenticated CSV bytes, complete four-game sample and reciprocal final-game facts.
    rows = ORACLE["candidate_rows"]
    assert {r["game_id"] for r in rows} == {22300403, 22300684, 22300856, 22301103}
    assert len(rows) == 4 and sum(row["wl"] == "W" for row in rows) == 3
    assert [sum(row[stat] for row in rows) for stat in ["pts", "reb", "ast"]] == [488, 189, 105]
    forbidden = [
        "No Matching Results",
        "Points is not available for this query.",
        "undefined",
        "NaN",
        "Infinity",
    ]
    return [
        dict(
            id="leading-list-third-owner",
            query="Against Celtics and Wizards, what was Lakers record when NYK score at least 110 in 2023-24?",
            text=[REFUSAL, "Unavailable Filter"],
            forbidden=forbidden,
        ),
        dict(
            id="leading-list-baseline",
            query="Against Celtics and Wizards, what was Lakers record in 2023-24?",
            text=["Lakers are 3-1", "BOS, WAS", "75% win rate"],
            forbidden=forbidden + [REFUSAL],
        ),
    ]


def _baseline(item, metadata, sections):
    assert item["payload"]["result_status"] == "ok" and item["payload"]["result_reason"] is None
    assert not metadata.get("unsupported_filters") and metadata["stat"] is None
    assert not metadata.get("conditions")
    assert dict(label="Opponent", kind="team", value="BOS, WAS") in metadata["applied_filters"]
    assert set(sections) == {"summary", "by_season"}
    assert len(sections["summary"]) == len(sections["by_season"]) == 1
    assert sections["summary"][0]["team_name"] == "Los Angeles Lakers"
    assert sections["by_season"][0]["season"] == "2023-24"
    for row in (sections["summary"][0], sections["by_season"][0]):
        assert (row["games"], row["wins"], row["losses"]) == (4, 3, 1)
        assert row["win_pct"] == 0.75
        assert [row[stat + "_avg"] for stat in ["pts", "reb", "ast"]] == [122, 47.25, 26.25]
    table = _table(item, "Team record")
    assert len(table["rows"]) == 1
    cells = dict(zip(table["headers"], table["rows"][0]))
    assert cells["Team"] == "LALLos Angeles Lakers" and cells["W-L"] == "3-1"
    assert int(cells["Games"]) == 4 and cells["Win %"] == "75.0%" and float(cells["PPG"]) == 122


def _validate_answers(receipt, cases, output):
    by_id, seen = {case["id"]: case for case in cases}, set()
    assert not receipt["failures"]
    for item in receipt["receipts"]:
        pair = item["viewport"], item["id"]
        assert pair not in seen
        seen.add(pair)
        case = by_id[item["id"]]
        assert item["query"] == item["payload"]["query"] == case["query"]
        assert item["http"] == 200 and not item["errors"] and not item["missing"]
        assert not item["forbidden"] and not item["grainErrors"]
        assert all(value in item["text"] for value in case["text"])
        assert not any(value in item["text"] for value in case["forbidden"])
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
        payload = item["payload"]
        assert payload["route"] == "team_record"
        metadata, sections = payload["result"]["metadata"], payload["result"]["sections"]
        assert metadata["team"] == "LAL" and metadata["team_context"] == dict(
            team_id=1610612747, team_abbr="LAL", team_name="Lakers"
        )
        assert metadata["season"] == "2023-24" and metadata["season_type"] == "Regular Season"
        assert metadata["opponents"] == ["BOS", "WAS"] and metadata["opponent"] == "BOS, WAS"
        assert not metadata.get("opponent_context")
        assert metadata["player"] is None and not metadata.get("player_context")
        if item["id"] == "leading-list-third-owner":
            # The third-team calculation remains unfinished; never present it as a zero/partial answer.
            assert (
                payload["result_status"] == "no_result"
                and payload["result_reason"] == "filter_not_supported"
            )
            assert metadata["unsupported_filters"] == ["other_team_stat"]
            assert not metadata.get("applied_filters") and not sections and not item["tables"]
        else:
            _baseline(item, metadata, sections)
    assert seen == {(viewport, ident) for viewport in ["desktop", "mobile"] for ident in by_id}


def test_deployed_leading_list_desktop_and_mobile(tmp_path):
    cases = _cases()
    receipt = _capture_browser(cases, tmp_path, FOLDER)
    assert receipt["base"] == "https://nbatools.vercel.app"
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / FOLDER
    _validate_answers(receipt, cases, output)
