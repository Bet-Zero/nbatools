"""Pinned observed-season accounting and the smallest retained K08 data request."""

import json
import os
import time
from pathlib import Path

import pytest

from tools.participation_coverage import build_report

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"


def test_current_lebron_population_and_exact_missing_requirement():
    request = json.loads(
        (PROGRAM / "collection-requests/lebron-structured-remaining-2025-26.json").read_text()
    )
    result = build_report(
        generation=request["base_generation"],
        manifest_sha256=request["base_manifest_sha256"],
        season="2025-26",
        team_id=1610612747,
        player_id=2544,
    )
    assert result["requested_games"] == result["observed_team_games"] == 82
    assert result["counts"] == dict(played=60, did_not_play=5, same_game_other_side=0, unknown=17)
    assert result["missed_games"] is None and not result["complete_requested_population"]
    keys = ["game_id", "game_date", "team_id", "player_id"]
    assert result["missing_keys"] == [
        {key: row[key] for key in keys} for row in request["requirements"]
    ]
    # Reuse the independently checked original catalog/player hashes, preserving
    # the audit's historical identity instead of relabeling it as a new scan.
    audit = json.loads(
        (PROGRAM / "source-evidence/k08-coverage/selected-populations.json").read_text()
    )
    for kind in ["team_game_stats", "player_game_stats"]:
        path = f"raw/{kind}/2025-26_regular_season.csv"
        assert result["source_hashes"][path] == audit["source_hashes"][path]
    old = next(
        row
        for row in audit["populations"]
        if row["season"] == "2025-26" and row["player_id"] == 2544
    )
    explicit = {row["game_id"] for row in old["games"] if row["state"] == "did_not_play"}
    explicit.update(request["qualified_published_reports"]["game_ids"])
    assert {row["game_id"] for row in result["games"] if row["state"] == "did_not_play"} == explicit
    output = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if output:
        target = Path(output) / "k08-lebron-participation-coverage.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


@pytest.mark.slow
def test_deployed_absence_answers_on_qualified_population():
    """PR555 follow-through and a complete scoped coverage-report consumer."""
    from tests.test_deployed_completion_contracts import _query, _ready

    generation = "availability-k08-retained-v1-20261031"
    result = build_report(
        generation=generation,
        manifest_sha256="de83522f37f6bd7f26b51c1bf869deb05bbe242d3249d685997a979c050d16a9",
        season="2025-26",
        team_id=1610612747,
        player_id=2544,
        game_ids=[22500019, 22500113, 22500122],
    )
    assert result["complete_requested_population"] and result["missed_games"] == 3
    before = _ready("k08-absence-before")
    scope = "from 2025-10-24 to 2025-10-27 in 2025-26"
    # Preserve public rate limits and fail actual errors without retries.
    time.sleep(7)
    record = _query(f"Lakers record with LeBron James out {scope}", "k08-absence-record")
    assert record["route"] == "team_record"
    sections = record["result"]["sections"]
    row = sections["summary"][0]
    assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (3, 2, 1, 121)
    assert {int(row["game_id"]) for row in sections["game_log"]} == {
        int(row["game_id"]) for row in result["games"]
    }
    time.sleep(7)
    pair = _query(
        f"Austin Reaves games with at least 40 points without LeBron and Luka playing {scope}",
        "k08-absence-pair",
    )
    assert pair["route"] == "player_game_finder"
    assert [(int(row["game_id"]), row["pts"]) for row in pair["result"]["sections"]["finder"]] == [
        (22500113, 51),
        (22500122, 41),
    ]
    assert pair["result"]["metadata"]["without_player"] == "LeBron James and Luka Dončić"
    assert (
        _ready("k08-absence-after")["active_generation"]
        == before["active_generation"]
        == generation
    )
