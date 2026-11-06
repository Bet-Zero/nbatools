"""Synthetic phase boundaries catch lost evidence and changed source/canonical facts."""

import copy
import json

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import COLUMNS
from tests.cloud_tatum_2023_participation_stage_real_data import _compare_population, _phase

pytestmark = pytest.mark.engine


@pytest.fixture
def population():
    fact = dict(
        game_id="0022300373",
        game_date="2023-12-20",
        season="2023-24",
        season_type="Regular Season",
        team_id=1,
        team_abbr="AAA",
        player_id=11,
        player_name_raw="Controlled Player",
        participation_state="played",
        source_seconds=61,
        comment_literal="",
        traditional_row_literal={"original": "fixture"},
        source_points=7,
    )
    row = dict(
        zip(
            COLUMNS,
            [
                "22300373",
                "2023-12-20",
                "2023-24",
                "Regular Season",
                "1",
                "AAA",
                "11",
                "Controlled Player",
                "played",
                str(61 / 60),
                "",
                "nba_stats_structured_archive:2e44b7c039f104bc6b41a1de494411e83a03714e:0022300373",
                "a" * 64,
                "",
                "listed_player_rows_only",
            ],
        )
    )
    canonical = pd.DataFrame(
        [dict(game_id=22300373, team_id=1, player_id=11, player_name="Controlled Player", pts=7)]
    )
    return pd.DataFrame([row], columns=COLUMNS), [fact], {22300373: "a" * 64}, canonical


def test_source_and_canonical_values_both_required(population):
    _compare_population(*population)


@pytest.mark.parametrize(
    "damage",
    [
        "source_clock",
        "source_state",
        "source_name",
        "duplicate",
        "unlisted",
        "canonical_points",
        "canonical_id",
        "canonical_name",
    ],
)
def test_no_candidate_qualification_with_changed_or_conflicting_facts(population, damage):
    frame, facts, packets, canonical = copy.deepcopy(population)
    if damage == "source_clock":
        frame.loc[0, "source_minutes"] = "1.0"
    elif damage == "source_state":
        frame.loc[0, "participation_state"] = "unknown"
    elif damage == "source_name":
        frame.loc[0, "player_name"] = "Different Player"
    elif damage == "duplicate":
        frame = pd.concat([frame, frame], ignore_index=True)
    elif damage == "unlisted":
        frame.loc[0, "player_id"] = "99"
    elif damage == "canonical_points":
        canonical.loc[0, "pts"] = 8
    elif damage == "canonical_id":
        canonical.loc[0, "player_id"] = 99
    else:
        canonical.loc[0, "player_name"] = "Different Player"
    with pytest.raises(AssertionError):
        _compare_population(frame, facts, packets, canonical)


def test_failure_keeps_candidate_bytes_and_prior_phase_evidence(tmp_path):
    artifact = tmp_path / "candidate-overlay.zip"
    artifact.write_bytes(b"controlled qualified candidate bytes")
    path = tmp_path / "acceptance.json"
    receipt = dict(
        phases={}, candidate_role="qualified_during_current_gate", consumer_acceptance="pending"
    )
    with _phase(receipt, path, "canonical_candidate"):
        pass
    with pytest.raises(RuntimeError, match="controlled consumer failure"):
        with _phase(receipt, path, "consumers"):
            raise RuntimeError("controlled consumer failure")
    persisted = json.loads(path.read_bytes())
    assert persisted["phases"]["canonical_candidate"]["status"] == "passed"
    assert persisted["phases"]["consumers"] == dict(
        status="failed", error_type="RuntimeError", error="controlled consumer failure"
    )
    assert persisted["consumer_acceptance"] == "pending"
    assert artifact.read_bytes() == b"controlled qualified candidate bytes"


def test_failed_first_phase_is_not_labelled_qualified(tmp_path):
    path = tmp_path / "acceptance.json"
    receipt = dict(phases={}, candidate_stage_qualified=False)
    with pytest.raises(AssertionError):
        with _phase(receipt, path, "canonical_candidate"):
            raise AssertionError("source mismatch")
    persisted = json.loads(path.read_bytes())
    assert persisted["phases"]["canonical_candidate"]["status"] == "failed"
    assert not persisted["candidate_stage_qualified"]
