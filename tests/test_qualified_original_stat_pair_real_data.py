"""Original TEAM-game MIN+count answers authenticated against the frozen source."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
FIXTURE = (
    Path(__file__).parent / "fixtures/qualified_original_stat_pair/preimplementation_source.json"
)
SOURCE = json.loads(FIXTURE.read_text())
PRIMARY = SOURCE["source_fact"]


def authenticate():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == (
        "78e57eddf60d6b227d8f73e0a57487347efaa0fc3d57c343c99d629ffbc6dad0"
    )
    for path, sha in SOURCE["source_hashes"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == sha
    for kind, expected in (
        ("games", PRIMARY["catalog_rows"]),
        ("team_game_stats", PRIMARY["team_rows"]),
        ("player_game_stats", [PRIMARY["canonical_player_row"]]),
        ("player_game_availability", [PRIMARY["report_observation"]]),
    ):
        with data_path(f"raw/{kind}/2023-24_regular_season.csv").open() as stream:
            raw = list(csv.DictReader(stream))
        assert all(row in raw for row in expected)
    appearance, report = PRIMARY["canonical_player_row"], PRIMARY["report_observation"]
    assert appearance["player_id"] == report["player_id"] == "1630202"
    assert appearance["team_id"] == report["team_id"] == "1610612738"
    assert appearance["game_id"] == report["game_id"] == "0022300684"
    assert appearance["game_date"] == report["game_date"] == "2024-02-01"
    assert PRIMARY["pdf_time"] == "21:18"
    assert PRIMARY["elapsed_seconds"] == 21 * 60 + 18 == 1278
    assert float(report["source_minutes"]) * 60 == 1278
    assert int(appearance["ast"]) == 1 and int(appearance["reb"]) == 0


def checked(result, player, player_id, team, truth, stat):
    assert result.route == "game_finder" and result.result_status == "ok", result.metadata
    assert result.metadata["player"] == player
    assert result.metadata["player_context"] == {"player_id": player_id, "player_name": player}
    assert result.metadata["stat"] is None and not result.metadata["threshold_conditions"]
    assert result.metadata["min_value"] is None and result.metadata["max_value"] is None
    assert not result.metadata["with_player"] and not result.metadata["without_player"]
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(("Yes:" if truth else "No:") + " " + player)
    assert "2024-02-01" in phrase
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == 1 and int(rows[0]["game_id"]) == 22300684
    row = rows[0]
    expected = next(r for r in PRIMARY["team_rows"] if r["team_abbr"] == team)
    assert row["team_id"] == int(expected["team_id"])
    assert row["opponent_team_id"] == int(expected["opponent_team_id"])
    assert str(row["game_date"])[:10] == expected["game_date"]
    assert [row[k] for k in ("pts", "reb", "ast")] == [
        int(expected[k]) for k in ("pts", "reb", "ast")
    ]
    assert not any(k in row for k in ("player", "player_name", "player_id"))
    filters = result.metadata["applied_filters"]
    assert any(f["label"] == "Minutes check" and f["value"].startswith(player) for f in filters)
    assert any(
        f["label"] == "Count check" and player in f["value"] and stat in f["value"] for f in filters
    )
    assert any(
        f["label"] == "Sample selection" and "original team matchup" in f["value"] for f in filters
    )
    assert not any(f["label"] in ("Played check", "With player", "Without player") for f in filters)
    assert not any("unsupported_boundary:" in n for n in result.metadata["notes"])
    assert any("team-game totals" in c and "MM:SS" in c for c in result.result.caveats)
    return phrase


@pytest.mark.parametrize(
    "predicate,truth,stat,actual",
    [
        ("play at least 21 minutes and have at least 1 assist", True, "AST", 1),
        ("play at least 21 minutes and record at least 1 assist", True, "AST", 1),
        ("play at least 21 minutes and have recorded at least 1 assist", True, "AST", 1),
        ("play at least 21 minutes and score at least 1 point", True, "PTS", 8),
        ("play at least 21 minutes and at least 1 assist", True, "AST", 1),
        ("play at least 21 minutes and have fewer than 1 assist", False, "AST", 1),
        ("have at least 1 assist and play at least 21 minutes", True, "AST", 1),
        ("play between 21 and 22 minutes and have between 0 and 1 assists", True, "AST", 1),
        ("play at least 21 minutes and have at most 0 rebounds", True, "REB", 0),
        ("play at least 21 minutes and record over 0.99999 assists", True, "AST", 1),
        ("play at least 21 minutes and record under 1.00001 assists", True, "AST", 1),
        ("play at least 21 minutes and record at least 1.00001 assists", False, "AST", 1),
        ("play at least 21 minutes and record at most 0.99999 assists", False, "AST", 1),
    ],
)
def test_original_stat_pair_source_positive_fields(predicate, truth, stat, actual):
    authenticate()
    result = execute_natural_query(
        f"Did Payton Pritchard {predicate} in the Celtics last game against Lakers in 2023-24?"
    )
    phrase = checked(result, "Payton Pritchard", 1630202, "BOS", truth, stat)
    assert f"played 21:18 with {actual} {stat}" in phrase
    assert int(PRIMARY["canonical_player_row"][stat.lower()]) == actual


@pytest.mark.parametrize("count", ["at least 1 assist", "at most 0 rebounds"])
def test_original_stat_pair_source_explicit_dnp_never_old_row_or_numeric_zero(count):
    authenticate()
    old_source = json.loads(
        (FIXTURE.parent.parent / "qualified_original_minutes/source_and_baseline.json").read_text()
    )
    facts = old_source["source_games"]["22300684"]
    report = next(r for r in facts["target_observation_rows"] if r["player_id"] == "203076")
    assert report["participation_state"] == "did_not_play"
    assert report["team_id"] == "1610612747" and report["game_date"] == "2024-02-01"
    assert not any(r["player_id"] == "203076" for r in facts["target_positive_appearance_rows"])
    result = execute_natural_query(
        f"Did Anthony Davis play at least 30 minutes and have {count} in the Lakers last game against Celtics in 2023-24?"
    )
    phrase = checked(
        result, "Anthony Davis", 203076, "LAL", False, "AST" if "assist" in count else "REB"
    )
    assert "did not play" in phrase and "with 0" not in phrase and "played 0:" not in phrase


def test_native_bare_stat_pair_source_restores_complete_implicit_actor_verb():
    result = execute_natural_query(
        "Did LeBron play at least 30 minutes and have at least 10 assists last game in 2023-24?"
    )
    assert result.result_status == "ok" and result.route == "player_game_finder"
    assert result.metadata["answer_phrase"].startswith("Yes:")
    row = result.result.to_dict()["sections"]["finder"][0]
    assert int(row["game_id"]) == 22301195 and int(row["player_id"]) == 2544
    assert row["minutes"] == 38 and row["ast"] == 17
    with data_path("raw/player_game_stats/2023-24_regular_season.csv").open() as stream:
        raw = next(
            r
            for r in csv.DictReader(stream)
            if int(r["game_id"]) == 22301195 and int(r["player_id"]) == 2544
        )
    assert raw["minutes"] == "38" and raw["ast"] == "17" and raw["game_date"] == "2024-04-14"
    assert not any(
        f["label"] in ("Minutes check", "Count check") for f in result.metadata["applied_filters"]
    )


@pytest.mark.parametrize(
    "bound,truth",
    [
        ("under 22.6500000000000001 minutes", True),
        ("over 22.6499999999999999 minutes", True),
        ("at least 22.6500000000000001 minutes", False),
        ("at most 22.6499999999999999 minutes", False),
    ],
)
@pytest.mark.parametrize("pair", [False, True])
def test_post_start_decimal_precision_source_audit_hauser(bound, truth, pair):
    # This precision audit was discovered after comparison implementation;
    # source rows/PDF MM:SS were already independently frozen for PR531.
    path = FIXTURE.parent / "checker_revealed_controls.json"
    oracle = json.loads(path.read_text())
    facts = oracle["source"]["Sam Hauser"]
    for kind, field in [("player_game_availability", "report"), ("player_game_stats", "positive")]:
        rows = list(csv.DictReader(data_path(f"raw/{kind}/2023-24_regular_season.csv").open()))
        assert facts[field] in rows
    assert facts["time"] == "22:39" and facts["seconds"] == 22 * 60 + 39 == 1359
    assert facts["report"]["player_id"] == facts["positive"]["player_id"] == "1630573"
    assert (
        facts["report"]["source_sha256"]
        == "98f2dbbf9db7b64a99a19e80721196ec788632c5ba0bae881c70bcd3799cfda4"
    )
    assert facts["positive"]["ast"] == "0"
    suffix = " and have at most 0 assists" if pair else ""
    result = execute_natural_query(
        f"Did Sam Hauser play {bound}{suffix} in the Celtics last game against Lakers in 2023-24?"
    )
    assert result.result_status == "ok" and result.route == "game_finder", result.metadata
    assert result.metadata["answer_phrase"].startswith("Yes:" if truth else "No:")
    assert "played 22:39" in result.metadata["answer_phrase"]
    assert bound.split()[-2] in result.metadata["answer_phrase"]
    assert bound.split()[-2] in str(result.metadata["applied_filters"])
    (row,) = result.result.to_dict()["sections"]["finder"]
    assert int(row["game_id"]) == 22300684 and row["team_id"] == 1610612738
