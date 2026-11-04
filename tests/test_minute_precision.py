"""Exact full-population minute boundaries remain distinct from missing timing."""

import json
from fractions import Fraction

import pytest

from tools.qualify_advanced_basis import SOURCE_SHA
from tools.qualify_incremental_return import bound_zip
from tools.qualify_minute_precision import (
    CURRENT,
    NEW_GAME_IDS,
    _whole,
    authenticate_sources,
    exact_game_clock,
    qualify,
)

PRECISION_ARCHIVE = (
    CURRENT.parent / "retained-qualification-20261104/precision-source-originals.zip"
)
PRECISION_SHA = "888bbbcf8a1bc4b15bdbb2a04433bcabe1b81da6994c8c593b37d2a9e9362bd2"


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    return qualify(
        PRECISION_ARCHIVE, PRECISION_SHA, tmp_path_factory.mktemp("precision") / "qualified"
    )


def test_real_complete_exact_boundaries_keep_unchanged_inclusive_rule(qualified):
    cases = {p["player_id"]: p for p in qualified["player_results"]}
    for pid, mean in [
        (201144, Fraction(107, 20)),
        (1629162, Fraction(121, 20)),
        (1630192, Fraction(71, 20)),
        (203081, Fraction(583, 20)),
        (1630695, Fraction(163, 20)),
    ]:
        row = cases[pid]
        assert row["state"] == "qualified_exact_clock_rounding"
        assert Fraction(row["exact_mean_minutes"]) == mean
        assert (
            row["absolute_residual_minutes"] == row["unchanged_inclusive_limit_minutes"] == "1/20"
        )
        assert not row["unknown_games"]
        assert all(g["state"] == "qualified_exact_game_clock" for g in row["game_clock_ledger"])
    assert not qualified["accepted_values_rewritten"]
    assert not qualified["full_snapshot_accepted"]
    assert qualified["production_writes"] == 0
    assert qualified["new_source_count"] == 14
    assert qualified["unresolved_player_ids"] == [1642854]
    proof = qualified["game_results"]["0022600127"]["period_facts"]["score_snapshot_evidence"]
    assert proof["observations"] == [
        {
            "action_id": 174,
            "period": 2,
            "clock": "PT06M17.00S",
            "event_prefix_score": {1610612743: 46, 1610612744: 44},
            "literal_score": {1610612743: 47, 1610612744: 44},
            "explaining_scoring_action_ids": [177],
            "event_order_changed": False,
            "clock_changed": False,
        }
    ]
    assert qualified["retained0168_reused"]


def test_absent_source_never_imputed_from_retained_canonical_minutes(qualified):
    source = qualified["game_results"]["0022600160"]
    assert source["state"] == "missing_immutable_archive_source"
    assert source["event_sha256"] is None
    case = next(p for p in qualified["player_results"] if p["player_id"] == 1642854)
    assert case["state"] == "unknown_incomplete_unique_timing"
    assert case["exact_mean_minutes"] is None
    assert case["unknown_games"] == [
        {
            "game_id": "0022600160",
            "error": "PlayByPlayV3 absent from checked immutable archive directory",
        }
    ]
    missing = next(g for g in case["game_clock_ledger"] if g["game_id"] == "0022600160")
    assert missing["canonical_game_minute_literal"]
    assert missing["raw_game_minute_literal"]
    assert "exact_seconds" not in missing


def test_original_source_bindings_and_order_remain_required():
    with pytest.raises(ValueError, match="archive differs"):
        authenticate_sources(PRECISION_ARCHIVE, "0" * 64)
    sources, manifest = authenticate_sources(PRECISION_ARCHIVE, PRECISION_SHA)
    assert len(manifest["files"]) == 14 and manifest["missing_game_ids"] == ["0022600160"]
    assert set(sources) == set(NEW_GAME_IDS)
    raw = sources["0022600092"]["raw"]
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        bodies = {n: z.read(n) for n in z.namelist()}
    whole = _whole("0022600092", bodies)
    doc = json.loads(raw)
    rows = doc["game"]["actions"]
    rows[1], rows[2] = rows[2], rows[1]
    with pytest.raises(ValueError, match="chronology"):
        exact_game_clock(json.dumps(doc).encode(), whole)


@pytest.mark.parametrize("alteration", ["remove", "collision"])
def test_display_alias_requires_literal_unique_source_identity(alteration):
    sources, _ = authenticate_sources(PRECISION_ARCHIVE, PRECISION_SHA)
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        bodies = {n: z.read(n) for n in z.namelist()}
    raw = sources["0022600146"]["raw"]
    doc = json.loads(_whole("0022600146", bodies))
    team = next(
        doc["boxScoreTraditional"][s]
        for s in ["homeTeam", "awayTeam"]
        if any(p["personId"] == 1642905 for p in doc["boxScoreTraditional"][s]["players"])
    )
    target = next(p for p in team["players"] if p["personId"] == 1642905)
    assert target["firstName"] == "Hansen" and target["familyName"] == "Yang"
    assert target["nameI"] == "Y. Hansen"
    if alteration == "remove":
        target.pop("nameI")
    else:
        other = next(p for p in team["players"] if p["personId"] != 1642905)
        other["nameI"] = "A. Hansen"
    with pytest.raises(ValueError, match="Ambiguous incoming substitution identity"):
        exact_game_clock(raw, json.dumps(doc).encode())


def test_source_display_alias_does_not_invent_first_name_prefixes():
    sources, _ = authenticate_sources(PRECISION_ARCHIVE, PRECISION_SHA)
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        bodies = {n: z.read(n) for n in z.namelist()}
    whole = _whole("0022600146", bodies)
    doc = json.loads(sources["0022600146"]["raw"])
    incoming = next(
        r for r in doc["game"]["actions"] if r["description"].startswith("SUB: Hansen FOR ")
    )
    incoming["description"] = incoming["description"].replace(
        "SUB: Hansen FOR ", "SUB: H. Hansen FOR "
    )
    with pytest.raises(ValueError, match="Ambiguous incoming substitution identity"):
        exact_game_clock(json.dumps(doc).encode(), whole)
