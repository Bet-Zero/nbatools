"""Count-credit vectors and rejection of unsupported source interpretation."""

import copy
import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from tools.qualify_period_counts import (
    CURRENT,
    SUFFIX,
    _whole_original,
    count_events,
    qualify,
    retained_sources,
)
from tools.qualify_rollover_q1 import _local_stage


@pytest.fixture(scope="module")
def sources():
    return retained_sources()


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    output = tmp_path_factory.mktemp("count-credit") / "qualified"
    report = qualify(output, now=datetime(2026, 11, 4, 13, 37, tzinfo=UTC))
    return output, report


def test_all_original_groups_and_full_affected_vectors(qualified):
    output, report = qualified
    assert report["original_obligations"] == 83
    assert report["resolved_count_obligations"] == 80
    assert report["remaining_unadmitted_count_obligations"] == 3
    assert len(report["vectors"]) == 1440
    assert len(report["proofs"]) == 18
    assert len(report["count_changes"]) == 190
    assert all(r["event_count"] == r["canonical"] for r in report["resolutions"])
    assert report["missing_0142_windows"] == [[3, 3], [3, 4]]
    assert not report["full_numerical_acceptance"] and not report["production_ready"]
    frame = pd.read_csv(output / f"stage/data/raw/player_game_period_stats/{SUFFIX}")
    martin = frame.loc[frame.game_id.eq(22600142) & frame.player_id.eq(1628997)]
    assert not (martin.period_family.eq("quarter") & martin.period_value.eq("3")).any()
    assert not (martin.period_family.eq("half") & martin.period_value.eq("second")).any()


def test_actual_finder_uses_revised_credit_and_preserves_unknown_rates(qualified):
    from nbatools.commands.player_game_finder import build_result

    output, report = qualified
    with _local_stage(output / "stage"):
        for name, expected in [("Ajay Mitchell", 2), ("Jalen Williams", 0)]:
            result = build_result(
                player=name,
                season="2026-27",
                quarter="2",
                start_date="2026-10-22",
                end_date="2026-10-22",
            )
            assert result.result_status == "ok"
            assert result.games.game_id.tolist() == [22600007]
            assert result.games.stl.tolist() == [expected]
    assert report["explicit_rate_invalidations"]
    frame = pd.read_csv(output / f"stage/data/raw/player_game_period_stats/{SUFFIX}")
    for change in report["explicit_rate_invalidations"]:
        if change["dataset"] == "player":
            assert pd.isna(frame.loc[change["row"], change["field"]])


def test_only_declared_csv_tokens_change(qualified):
    import csv
    import io
    import zipfile

    output, report = qualified
    changes = report["count_changes"] + report["explicit_rate_invalidations"]
    changes += report["derived_count_ratio_changes"]
    with zipfile.ZipFile(CURRENT.parent / "technical-ft-20261104/qualification-evidence.zip") as z:
        for grain in ["player", "team"]:
            name = f"stage/data/raw/{grain}_game_period_stats/{SUFFIX}"
            before = list(csv.reader(io.StringIO(z.read(name).decode())))
            after = list(csv.reader(io.StringIO((output / name).read_text())))
            allowed = {
                (r["row"] + 1, before[0].index(r["field"]))
                for r in changes
                if r["dataset"] == grain
            }
            assert len(before) == len(after)
            for i, (left, right) in enumerate(zip(before, after, strict=True)):
                assert len(left) == len(right)
                for j, (old, new) in enumerate(zip(left, right, strict=True)):
                    assert old == new or (i, j) in allowed


def test_suffix_is_not_an_oracle(sources):
    doc = json.loads(sources["0022600007"])
    expected = count_events(sources["0022600007"], _whole_original("0022600007"))[0]
    for row in doc["game"]["actions"]:
        row["description"] = row["description"].replace(" STL)", " STL)")
        if " STEAL " in row["description"]:
            row["description"] = row["description"].split(" (")[0] + " (999 STL)"
    observed, _, _ = count_events(json.dumps(doc).encode(), _whole_original("0022600007"))
    assert observed == expected


@pytest.mark.parametrize("mutation", ["pair", "clock", "order", "alias", "shot", "boundary"])
def test_contradictory_source_rejects(sources, mutation):
    doc = copy.deepcopy(json.loads(sources["0022600007"]))
    rows = doc["game"]["actions"]
    if mutation == "pair":
        rows[154]["actionNumber"] += 1
    elif mutation == "clock":
        rows[59]["clock"] = "PT99M00S"
    elif mutation == "order":
        rows[154], rows[155] = rows[155], rows[154]
    elif mutation == "alias":
        row = next(r for r in rows if " AST)" in r["description"])
        row["description"] = row["description"].rsplit("(", 1)[0] + "(Unknown 1 AST)"
    elif mutation == "shot":
        next(r for r in rows if r["actionType"] == "Made Shot")["shotValue"] = 4
    else:
        next(r for r in rows if r["actionType"] == "period")["subType"] = "unknown"
    with pytest.raises(ValueError):
        count_events(json.dumps(doc).encode(), _whole_original("0022600007"))


def test_nonshooting_count_proof_does_not_certify_0009_scoreboard(sources):
    _, _, facts = count_events(sources["0022600009"], _whole_original("0022600009"))
    assert facts["strict_score_validation"] is False
    assert facts["strict_error"] == "Unexplained event score change"


def test_new_timing_and_exact_fresh_due_population(qualified):
    _, report = qualified
    timing = report["timing_addendum"]
    assert timing["quarter_seconds"] == ["275", "335", "211", "209"]
    assert timing["exact_seconds"] == "1030"
    assert timing["exact_mean_minutes"] == "227/20"
    assert timing["absolute_difference"] == timing["inclusive_limit"] == "1/20"
    assert not report["precision_0160_still_unknown"]
    assert len(report["due_population"]["due_game_ids"]) == 107
    assert report["due_population"]["missing_due_game_ids"] == []
    assert report["due_population"]["game0142_pbp_unchanged"]


def test_score_failure_cannot_hide_duplicate_boundary(sources):
    doc = json.loads(sources["0022600009"])
    rows = doc["game"]["actions"]
    end = next(
        i
        for i, r in enumerate(rows)
        if r["period"] == 1 and r["actionType"] == "period" and r["subType"] == "end"
    )
    rows.insert(end + 1, copy.deepcopy(rows[end]))
    for index, row in enumerate(rows, 1):
        row["actionId"] = index
    with pytest.raises(ValueError, match="nonterminal duplicate period end"):
        count_events(json.dumps(doc).encode(), _whole_original("0022600009"))
