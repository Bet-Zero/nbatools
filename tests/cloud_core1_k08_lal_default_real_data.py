"""Only original16/18/35's missing exact-default integrations; no acquisition."""

import json
import os
import unicodedata
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.api_handlers import query_result_to_payload
from nbatools.commands._reported_absence_reasons import coverage_note
from nbatools.commands._seasons import default_end_season
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_composed_participation_stage_real_data import (
    BASE,
    MANIFEST,
    PACKAGES,
    _baseline,
    _receipt_json_default,
    _sha,
)
from tests.cloud_reported_rest_stage_real_data import _write_inventory
from tests.core1_k08_served_default_cases import (
    LAL,
    ORIGINAL,
    SEASON,
    STATS,
    _sample,
    assert_summary_metrics,
    compact_actual,
)
from tools.compose_participation_overlays import compose_overlays

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
QUESTIONS = {
    16: "Lakers record when Luka Doncic sits",
    18: "Lakers record when Luka Doncic rests",
    35: "Lakers record without Reaves",
}
PLAYER_IDS = {16: 1629029, 18: 1629029, 35: 1630559}
REST_COVERAGE = dict(
    basis="officially reported Rest",
    complete=True,
    requested_games=82,
    qualified_nonparticipations=18,
    reported_rest=0,
    reported_other=18,
    unknown=0,
)


def assert_private_rest(result, expected=REST_COVERAGE):
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert result.result.metadata["reported_reason_basis"] == "officially reported Rest"
    assert result.result.metadata["reported_reason_coverage"] == expected


def assert_public_rest(body, expected=REST_COVERAGE):
    """Existing API publishes the complete audit note, not engine metadata."""
    assert body["result_status"] == "no_result" and body["result_reason"] == "no_match", (
        compact_actual(body)
    )
    meta = body["result"]["metadata"]
    assert meta["without_player_reason"] == "reported_rest"
    assert (
        dict(
            label="Reported absence reason",
            value="officially reported Rest",
            kind="reported_reason",
        )
        in meta["applied_filters"]
    )
    assert coverage_note(expected) in body["notes"]
    assert not body["result"]["sections"]


def full_name_key(value):
    assert isinstance(value, str)
    return "".join(
        c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)
    ).casefold()


def exact_source_player_id(players, name):
    """Only accent-equivalent complete names; no aliases or team inference."""
    matches = players.loc[
        players.player_name.map(full_name_key).eq(full_name_key(name)), "player_id"
    ]
    ids = set(matches.astype(int))
    assert len(ids) == 1, (name, sorted(ids))
    return ids.pop()


def accepted_inputs():
    """Read existing qualified oracles, preserving every original package byte."""
    packages = [PACKAGES[0], PACKAGES[3]]
    docs, receipts = [], []
    for path, digest in packages:
        assert _sha(path.read_bytes()) == digest
        with ZipFile(path) as archive:
            docs.append(
                json.loads(
                    archive.read(
                        next(n for n in archive.namelist() if n.endswith("/validation.json"))
                    )
                )
            )
            suffix = "/receipt.json" if len(receipts) == 0 else "/acceptance.json"
            receipts.append(
                json.loads(archive.read(next(n for n in archive.namelist() if n.endswith(suffix))))
            )
    nodes = json.loads(ORIGINAL.read_bytes())["node_ids"]
    assert _sha(("\n".join(nodes) + "\n").encode()) == (
        "acc3d675811c80641aec64d60d76e90f7e6d8eb4dba66904fef5eff616cc1f96"
    )
    for ordinal, query in QUESTIONS.items():
        assert query in nodes[ordinal - 1]
    coverage = receipts[0]["coverage"]
    for pid, played, missed in [(1629029, 64, 18), (1630559, 51, 31)]:
        oracle = coverage[str(pid)]
        assert oracle["player_id"] == pid and len(oracle["games"]) == 82
        assert oracle["counts"] == dict(
            played=played, did_not_play=missed, same_game_other_side=0, unknown=0
        )
    population = receipts[1]["population"]
    assert receipts[1]["consumer_acceptance"] == "passed"
    assert population["observed_games"] == 82 and population["did_not_play"] == 18
    assert population["explicit_reported_rest"] == 0
    assert population["source_reported_other"] == 18 and population["reason_unknown"] == 0
    return packages, docs, coverage


def assert_record_body(body, case, *, natural):
    """Require the complete exact sample and every claimed public count metric."""
    assert body["route"] == "team_record", compact_actual(body)
    assert body["query"] == (case["query"] if natural else "structured:team_record")
    meta, sections = body["result"]["metadata"], body["result"]["sections"]
    assert meta["season"] == SEASON and meta["team"] == "LAL"
    assert full_name_key(meta["without_player"]) == full_name_key(case["kwargs"]["without_player"])
    assert case["source_player_id"] == PLAYER_IDS[case["ordinal"]]
    assert not any(
        meta.get(k) for k in ("opponent", "with_player", "data_quality", "unsupported_filters")
    )
    if case["ordinal"] == 18:
        assert_public_rest(body)
        return
    assert body["result_status"] == "ok" and body["result_reason"] is None, compact_actual(body)
    assert not meta.get("without_player_reason")
    expected = case["expected"]
    (summary,) = sections["summary"]
    for field in ("games", "wins", "losses"):
        assert summary[field] == expected[field]
    assert_summary_metrics(summary, expected, "team_record")
    rows = sections["game_log"]
    assert len(rows) == len(expected["rows"]) == expected["games"]
    actual = {int(row["game_id"]): row for row in rows}
    assert len(actual) == len(rows) and set(actual) == {int(r["game_id"]) for r in expected["rows"]}
    for source in expected["rows"]:
        row = actual[int(source["game_id"])]
        assert row["team_abbr"] == source["team_abbr"] == "LAL"
        assert int(row["team_id"]) == int(source["team_id"]) == LAL
        assert int(row["opponent_team_id"]) == int(source["opponent_team_id"])
        assert row["opponent_team_abbr"] == source["opponent_team_abbr"]
        assert str(row["game_date"])[:10] == source["game_date"]
        assert row["wl"] == source["wl"]
        for stat in STATS:
            assert stat in row and row[stat] == pytest.approx(source[stat], abs=0.001)


def test_original_luka_rest_and_reaves_default_questions(tmp_path, monkeypatch):
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-k08-lal-default"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        base_generation=BASE,
        base_manifest_sha256=MANIFEST,
        classification="original16_18_35_exact_default_channels_on_accepted_unpublished_stage",
        answers=[],
        accepted_original_ids=[],
        consumer_acceptance="pending",
        nba_source_requests=0,
        production_writes=0,
        publication_approved=False,
        deployed_acceptance=False,
        literal_current_accepted=False,
        all46_accepted=False,
    )

    def persist():
        (output / "acceptance.json").write_text(
            json.dumps(receipt, indent=2, default=_receipt_json_default) + "\n"
        )

    persist()
    try:
        packages, docs, coverage = accepted_inputs()
        root = tmp_path / "stage/data"
        root.mkdir(parents=True)
        _baseline(root, docs)
        validation = compose_overlays(
            packages,
            root,
            output / "overlay",
            base_generation=BASE,
            base_manifest_sha256=MANIFEST,
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
        for entry in validation["overlay_files"]:
            body = (output / "overlay" / entry["path"]).read_bytes()
            assert _sha(body) == entry["sha256"] and len(body) == entry["size_bytes"]
            target = root / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        teams = pd.read_csv(root / f"raw/team_game_stats/{SEASON}_regular_season.csv")
        teams = teams.loc[teams.team_id.eq(LAL)]
        assert len(teams) == teams.game_id.nunique() == 82
        players = pd.read_csv(root / f"raw/player_game_stats/{SEASON}_regular_season.csv")
        reasons = pd.read_csv(root / f"raw/player_game_absence_reasons/{SEASON}_regular_season.csv")
        assert len(reasons) == reasons.game_id.nunique() == 18
        assert reasons.player_id.eq(1629029).all() and reasons.team_id.eq(LAL).all()
        assert reasons.reported_reason.eq("reported_other").all()
        cases = []
        for ordinal, pid, player, games, wins, losses in [
            (16, 1629029, "Luka Doncic", 18, 10, 8),
            (18, 1629029, "Luka Doncic", 0, 0, 0),
            (35, 1630559, "Austin Reaves", 31, 17, 14),
        ]:
            states = coverage[str(pid)]["games"]
            assert {int(g["game_id"]) for g in states} == set(teams.game_id.astype(int))
            for fact in states:
                source = teams.loc[teams.game_id.eq(int(fact["game_id"]))].iloc[0]
                assert fact["team_id"] == LAL and fact["player_id"] == pid
                assert fact["game_date"] == str(source.game_date)[:10]
                assert fact["state"] in {"played", "did_not_play"}
            ids = {int(g["game_id"]) for g in states if g["state"] == "did_not_play"}
            if pid == 1629029:
                assert set(reasons.game_id.astype(int)) == ids
            # Zero Rest is an already independently qualified source population,
            # distinct from the eighteen source-listed generic nonparticipants.
            selected_ids = (
                set(reasons.loc[reasons.reported_reason.eq("reported_rest"), "game_id"].astype(int))
                if ordinal == 18
                else ids
            )
            selected = teams.loc[teams.game_id.isin(selected_ids)].copy()
            expected = _sample(selected)
            assert (expected["games"], expected["wins"], expected["losses"]) == (
                games,
                wins,
                losses,
            )
            kwargs = dict(team="LAL", season=SEASON, without_player=player)
            if ordinal == 18:
                kwargs["without_player_reason"] = "reported_rest"
            assert exact_source_player_id(players, player) == pid
            cases.append(
                dict(
                    ordinal=ordinal,
                    query=QUESTIONS[ordinal],
                    kwargs=kwargs,
                    expected=expected,
                    source_player_id=pid,
                )
            )
        receipt["source_oracles"] = cases
        receipt["composition_validation"] = validation
        persist()
        _write_inventory(root)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
        reset_data_source_cache()
        clear_frame_cache()
        assert default_end_season("Regular Season") == SEASON
        client = TestClient(app)
        for case in cases:
            actual = dict(original_id=case["ordinal"], query=case["query"], accepted=False)
            receipt["answers"].append(actual)
            compiled = parse_query(case["query"])
            actual["compiled_scope"] = compiled["route_kwargs"]
            persist()
            assert compiled["route"] == "team_record"
            for key, value in case["kwargs"].items():
                if key == "without_player":
                    subject = compiled["route_kwargs"].get(key)
                    assert full_name_key(subject) == full_name_key(value), actual["compiled_scope"]
                    assert exact_source_player_id(players, subject) == case["source_player_id"]
                else:
                    assert compiled["route_kwargs"].get(key) == value, actual["compiled_scope"]
            for channel in ("natural", "structured", "http_natural", "http_structured"):
                natural = channel in {"natural", "http_natural"}
                if channel == "natural":
                    result = execute_natural_query(case["query"])
                elif channel == "structured":
                    result = execute_structured_query("team_record", **case["kwargs"])
                else:
                    response = client.post(
                        "/query" if natural else "/structured-query",
                        json={"query": case["query"]}
                        if natural
                        else dict(route="team_record", kwargs=case["kwargs"]),
                    )
                    body = response.json()
                    actual[channel + "_status"] = response.status_code
                if channel in {"natural", "structured"}:
                    if case["ordinal"] == 18:
                        actual[channel + "_private_reason_metadata"] = dict(result.result.metadata)
                        persist()
                        assert_private_rest(result)
                    body = query_result_to_payload(result)
                actual[channel] = body
                persist()
                if channel.startswith("http"):
                    assert actual[channel + "_status"] == 200, compact_actual(body)
                subject = body["result"]["metadata"]["without_player"]
                assert exact_source_player_id(players, subject) == case["source_player_id"]
                assert_record_body(body, case, natural=natural)
            actual["accepted"] = True
            receipt["accepted_original_ids"].append(case["ordinal"])
            persist()
        receipt["consumer_acceptance"] = "passed"
        persist()
        print(
            json.dumps(
                dict(accepted_original_ids=receipt["accepted_original_ids"], executed_channels=12)
            )
        )
    except Exception as exc:
        receipt.update(consumer_acceptance="failed", failure=f"{type(exc).__name__}: {exc}")
        persist()
        raise
    finally:
        reset_data_source_cache()
        clear_frame_cache()
