"""Real source repairs and versioned projections do not erase blocking evidence."""

import copy
import json
import zipfile
from fractions import Fraction

import pandas as pd
import pytest

from tools.period_event_evidence import clock_facts, period_facts
from tools.stage_current_season import (
    PARTIAL,
    _whole_original,
    originals,
    project_season_basis,
    refine_period_clocks,
    repair_partial_context_margins,
    stage,
)


def facts_for(gid):
    bodies, _ = originals()
    whole = _whole_original(gid)
    box = json.loads(whole)["boxScoreTraditional"]
    raw = bodies[f"playbyplayv3-{gid}.json"]
    facts = period_facts(
        raw,
        game_id=gid,
        final_teams={
            box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
        },
    )
    return raw, whole, facts


def test111_metadata_resolves_from_all_events_without_removing_duplicate():
    raw, _, facts = facts_for("0022600111")
    assert facts["period_count"] == 4
    assert facts["events"] == 527 and facts["repeated_terminal_markers"] == [527]
    assert facts["period_scores"][4] == {1610612756: 29, 1610612744: 30}
    assert len(json.loads(raw)["game"]["actions"]) == 527
    assert not facts["canonical_pbp_accepted"]


@pytest.mark.parametrize("bad", [None, "", "PT00M60.00S", 0, "0:00"])
def test_missing_or_malformed_event_clock_never_becomes_terminal_zero(bad):
    raw, whole, _ = facts_for("0022600111")
    doc = json.loads(raw)
    for row in doc["game"]["actions"][-2:]:
        row["clock"] = bad
    box = json.loads(whole)["boxScoreTraditional"]
    with pytest.raises(ValueError, match="clock"):
        period_facts(
            json.dumps(doc).encode(),
            game_id=box["gameId"],
            final_teams={
                box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
            },
        )


def test_conflicting_terminal_marker_rejected():
    raw, whole, _ = facts_for("0022600111")
    doc = json.loads(raw)
    doc["game"]["actions"][-1]["scoreHome"] = "130"
    box = json.loads(whole)["boxScoreTraditional"]
    with pytest.raises(ValueError):
        period_facts(
            json.dumps(doc).encode(),
            game_id=box["gameId"],
            final_teams={
                box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
            },
        )


def test97_exact_subsecond_clock_vector_and_unchanged_count_rate_cells():
    raw, whole, facts = facts_for("0022600097")
    clocks = clock_facts(raw, whole, period_report=facts)
    assert all(sum(team.values()) == 3600 for period in clocks.values() for team in period.values())
    assert clocks[4][1610612764][203076] == 496.5
    with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
        targets = {
            ep: z.read(f"sources/{ep}_0022600097_q4.json")
            for ep in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
        }
    before = copy.deepcopy(targets)
    derived, ledger = refine_period_clocks(targets, event_raw=raw, whole_raw=whole, start=4, end=4)
    assert targets == before
    assert len(ledger) > 6  # entire clock vector, not selected rounding cells
    for ep, key in [
        ("boxscoretraditionalv3", "boxScoreTraditional"),
        ("boxscoreadvancedv3", "boxScoreAdvanced"),
    ]:
        actual = json.loads(derived[ep])
        old = json.loads(before[ep])
        for side in ["homeTeam", "awayTeam"]:
            for a, b in zip(actual[key][side]["players"], old[key][side]["players"], strict=True):
                a["statistics"]["minutes"] = b["statistics"]["minutes"]
        assert actual == old


def test_invalid_substitution_and_forged_clock_report_fail():
    raw, whole, facts = facts_for("0022600097")
    fake = copy.deepcopy(facts)
    fake["period_count"] = 5
    with pytest.raises(ValueError):
        clock_facts(raw, whole, period_report=fake)
    doc = json.loads(raw)
    row = next(r for r in doc["game"]["actions"] if r["actionType"] == "Substitution")
    row["personId"] = 9999999
    box = json.loads(whole)["boxScoreTraditional"]
    mutated = json.dumps(doc).encode()
    valid = period_facts(
        mutated,
        game_id=box["gameId"],
        final_teams={
            box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]
        },
    )
    with pytest.raises(ValueError):
        clock_facts(mutated, whole, period_report=valid)


def test_projection_has_exact_basis_and_preserves_reported_values():
    core = pd.DataFrame(
        [
            dict(game_id=1, player_id=10, pts=10, fga=8, fta=2, minutes=20.5),
            dict(game_id=2, player_id=10, pts=6, fga=4, fta=0, minutes=21.75),
        ]
    )
    reported = pd.DataFrame(
        [dict(player_id=10, games_played=2, ts_pct=0.9, minutes_per_game=20.0, usage_rate=0.3)]
    )
    old = reported.copy(deep=True)
    new, ledger = project_season_basis(core, reported)
    assert new.iloc[0].ts_pct == pytest.approx(16 / (2 * (12 + 0.44 * 2)))
    assert new.iloc[0].minutes_per_game == 21.125
    assert (new.iloc[0].reported_ts_pct, new.iloc[0].reported_minutes_per_game) == (0.9, 20.0)
    assert new.iloc[0].usage_rate == 0.3 and ledger[0]["games"] == 2
    pd.testing.assert_frame_equal(reported, old)
    precise = core.copy()
    precise["minutes"] = ["5.3499999999999996", "5.35"]
    _, exact = project_season_basis(precise, reported)
    assert exact[0]["derived_minutes"] == str(
        (Fraction("5.3499999999999996") + Fraction("5.35")) / 2
    )
    bad = core.copy()
    bad.loc[0, "fta"] = -1
    with pytest.raises(ValueError):
        project_season_basis(bad, reported)
    reported.loc[0, "games_played"] = 3
    with pytest.raises(ValueError):
        project_season_basis(core, reported)


def test_current107_stage_preserves_history_and_exposes_missing_period_data(tmp_path):
    report = stage(tmp_path / "qualified")
    assert (report["game_count"], report["player_rows"], report["team_rows"]) == (107, 2413, 214)
    assert report["prior88_core_cells_preserved"]
    assert not report["prior92_core_cells_preserved"]
    assert len(report["partial_context_margin_repairs"]) == 14
    assert {x["game_id"] for x in report["partial_context_margin_repairs"]} == {"0022600154"}
    from tools.stage_current_season import RECOVERY

    with zipfile.ZipFile(RECOVERY / "qualification-evidence.zip") as z:
        for dataset in [
            "games",
            "player_game_stats",
            "team_game_stats",
            "player_game_starter_roles",
            "player_game_period_stats",
            "team_game_period_stats",
        ]:
            name = f"data/raw/{dataset}/2026-27_regular_season.csv"
            prior = z.read("stage/" + name)
            current = (tmp_path / "qualified/stage" / name).read_bytes()
            if dataset == "player_game_stats":
                # Preserve all accepted88 original CSV bytes; the four later
                # partial contexts were explicitly unaccepted in the prior receipt.
                old = pd.read_csv(__import__("io").BytesIO(prior))
                accepted = old[old.game_id < 22600154]
                assert current.startswith(
                    b"".join(prior.splitlines(keepends=True)[: len(accepted) + 1])
                )
                now = pd.read_csv(__import__("io").BytesIO(current)).iloc[: len(old)]
                for change in report["partial_context_margin_repairs"]:
                    mask = (old.game_id == int(change["game_id"])) & (
                        old.player_id == change["player_id"]
                    )
                    assert old.loc[mask, "plus_minus"].item() == change["before"]
                    old.loc[mask, "plus_minus"] = change["after"]
                pd.testing.assert_frame_equal(now, old, check_exact=True)
            else:
                assert current.startswith(prior)
    assert report["new_game_ids"] == [f"0022600{i}" for i in range(158, 173)]
    assert len(report["refined_period_clocks"]) == 2
    assert report["period_evidence"]["0022600111"]["period_count"] == 4
    assert report["exact_due_population"]["missing_due_game_ids"] == []
    pop = report["source_period_population"]
    assert (pop["known_expected_windows"], pop["qualified_windows"]) == (647, 551)
    assert len(pop["missing_known_windows"]) == 96
    assert pop["metadata_unresolved_game_ids"] == ["0022600161"]
    required = [r for r in report["dataset_assessment"]["datasets"] if r["required"]]
    assert len(required) == 16
    assert {r["name"] for r in required if r["validation"]["state"] == "failed"} == {
        "player_game_period_stats",
        "team_game_period_stats",
    }
    assert report["dataset_assessment"]["validation_state"] == "failed"
    assert len(report["reported_source_basis"]["ts_conflicts"]) == 12
    assert len(report["reported_record_checks"]["player_win_loss_conflicts"]) == 0
    assert report["consumer_status"] == "ok"
    assert report["consumer_rows"][0]["minutes"] == 8.275
    assert report["new_game_consumer_rows"][0]["game_id"] == 22600158
    assert (
        not report["reported_usage_independently_accepted"] and not report["full_snapshot_accepted"]
    )
    assert report["production_writes"] == 0
    coherence = report["period_count_coherence"]
    assert (coherence["integer_cell_conflicts"], len(coherence["conflict_game_ids"])) == (86, 19)
    assert "0022600154" not in coherence["conflict_game_ids"]


def test_partial_context_margin_repair_requires_all_qualified_quarters():
    from tools.stage_current_season import RECOVERY, SUFFIX

    with zipfile.ZipFile(RECOVERY / "qualification-evidence.zip") as z:
        import io

        core = pd.read_csv(io.BytesIO(z.read(f"stage/data/raw/player_game_stats/{SUFFIX}")))
        periods = pd.read_csv(
            io.BytesIO(z.read(f"stage/data/raw/player_game_period_stats/{SUFFIX}"))
        )
    old = core.copy(deep=True)
    repaired, changes = repair_partial_context_margins(core, periods)
    assert len(changes) == 14
    pd.testing.assert_frame_equal(core, old)
    assert repaired.loc[repaired.game_id != 22600154].equals(core.loc[core.game_id != 22600154])
    bad = periods.drop(
        periods[(periods.game_id == 22600154) & (periods.period_value.astype(str) == "4")].index
    )
    with pytest.raises(ValueError, match="Four qualified quarters"):
        repair_partial_context_margins(core, bad)
    bad = periods.copy()
    bad.loc[
        bad[(bad.game_id == 22600154) & (bad.period_family == "quarter")].index[0], "plus_minus"
    ] += 1
    with pytest.raises(ValueError, match="disagree"):
        repair_partial_context_margins(core, bad)


def test_independent_usage_evidence_does_not_hide_credit_semantics():
    from tools.period_event_evidence import usage_event_evidence

    bodies, _ = originals()
    with zipfile.ZipFile(PARTIAL / "collection.zip") as z:
        t = z.read("sources/boxscoretraditionalv3_0022600116_q1.json")
    from tools.stage_current_season import RECOVERY

    with zipfile.ZipFile(RECOVERY / "collection.zip") as z:
        a = z.read("sources/boxscoreadvancedv3_0022600116_q1.json")
    whole = _whole_original("0022600116")
    r = usage_event_evidence(bodies["playbyplayv3-0022600116.json"], whole, t, a)
    assert (r["exact_ratio_matches"], r["unresolved_credit_semantics"]) == (4, 6)
    matched = {
        x["player_id"]: (x["independent_numerator"], x["end_action_denominator"])
        for x in r["cases"]
        if x["matches_reported_rounding"]
    }
    assert matched == {1627884: (2, 19), 1630543: (2, 14), 1629636: (4, 21), 1642394: (2, 5)}
    assert not r["reported_values_rewritten"] and not r["full_independent_NBA_usage_accepted"]
    doc = json.loads(whole)
    cloned = copy.deepcopy(doc["boxScoreTraditional"]["homeTeam"]["players"][7])
    cloned.update(personId=9999999, firstName="Jayden", familyName="Williams", position="")
    doc["boxScoreTraditional"]["homeTeam"]["players"].append(cloned)
    with pytest.raises(ValueError, match="Ambiguous"):
        usage_event_evidence(bodies["playbyplayv3-0022600116.json"], json.dumps(doc).encode(), t, a)
