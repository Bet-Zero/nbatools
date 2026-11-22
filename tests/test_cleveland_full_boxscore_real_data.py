"""One bounded, retained 82-game pilot; no acquisition or production writes."""

import csv
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands._dated_membership import COLUMNS
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.test_season_inactive_pilot_real_data import _census
from tools.availability_overlay import verify_append
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/cleveland-full-boxscore-2024"
)
GENERATION = "availability-season-inactive-2024-v1-20261116"
MANIFEST = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
ORIGINALS = "594bab365fa2eda59a217c2137bda901dd0d55b7c8e60268a7ba9f2da2ab66d6"
BASELINE = "34723320958903239d353760c61c23310de3577a1143154df1fe4fd40e866a4c"
OVERLAY = "6be56cee625fde1dc31e805e6491d3873a88531e3d9d5c5738db7921fc2cdd26"
CLE = 1610612739
SEASON = "2024-25"
CSV = f"raw/player_game_availability/{SEASON}_regular_season.csv"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path):
    return json.loads(path.read_bytes())


def _retained_subset(destination):
    """Verify all original bodies, then select the qualified 80-game subset."""
    request = _json(EVIDENCE / "request.json")
    qualified = _json(EVIDENCE / "qualified-request.json")
    assert qualified["parent_request_sha256"] == _sha((EVIDENCE / "request.json").read_bytes())
    assert qualified["parent_originals_zip_sha256"] == ORIGINALS
    assert _sha((EVIDENCE / "originals.zip").read_bytes()) == ORIGINALS
    assert len(request["requirements"]) == 82 and len(request["source_files"]) == 164
    assert len(qualified["requirements"]) == 80 and len(qualified["source_files"]) == 160
    quarantine = {r["game_id"]: r["error"] for r in qualified["quarantined_games"]}
    assert quarantine == {
        "0022400199": "Invalid box-score duration: 19:60",
        "0022400893": "Invalid box-score duration: 28:60",
    }
    assert {r["game_id"] for r in request["requirements"]} == {
        r["game_id"] for r in qualified["requirements"]
    } | quarantine.keys()
    destination.mkdir()
    (destination / "sources").mkdir()
    with ZipFile(EVIDENCE / "originals.zip") as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == 165
        assert set(archive.namelist()) == {"sources.json"} | {
            "sources/" + f for f in request["source_files"]
        }
        provenance = json.loads(archive.read("sources.json"))
        assert archive.read("sources.json") == (EVIDENCE / "sources.json").read_bytes()
        assert not provenance["errors"] and len(provenance["files"]) == 164
        assert provenance["collection_request_sha256"] == _sha(
            (EVIDENCE / "request.json").read_bytes()
        )
        for name, record in request["source_files"].items():
            body = archive.read("sources/" + name)
            actual = provenance["files"][name]
            assert len(body) == record["size_bytes"] == actual["size_bytes"]
            assert _sha(body) == actual["sha256"]
            assert (
                hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()
                == record["git_blob_sha"]
            )
            assert actual["reader_attempts"] == 1
            if name in qualified["source_files"]:
                assert qualified["source_files"][name] == record
                (destination / "sources" / name).write_bytes(body)
        provenance["files"] = {
            n: r for n, r in provenance["files"].items() if n in qualified["source_files"]
        }
        (destination / "sources.json").write_text(json.dumps(provenance))
    return request, qualified


def test_cleveland_full_boxscore_pilot_preserves_unknowns_and_adds_complete_answers(
    tmp_path, monkeypatch, capfd
):
    assert _sha((EVIDENCE / "baseline.json").read_bytes()) == BASELINE
    baseline = _json(EVIDENCE / "baseline.json")
    oracle = _json(EVIDENCE / "independent/oracle.json")
    assert oracle["bindings"]["baseline_sha256"] == BASELINE
    assert oracle["bindings"]["sources_sha256"] == _sha((EVIDENCE / "sources.json").read_bytes())
    request, qualified = _retained_subset(tmp_path / "sources")
    r2_source = None
    if os.environ.get("DATA_SOURCE") == "r2":
        from nbatools.data_source import _get_data_source

        r2_source = _get_data_source()
        assert r2_source.active_generation() == GENERATION
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "cleveland-pilot"
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(manifest) == MANIFEST
        entries = {e["path"]: e for e in json.loads(manifest)["files"]}
        for relative, digest in baseline["source_hashes"].items():
            assert _sha(data_path("data/" + relative).read_bytes()) == digest
        assert not any(p.startswith("raw/player_team_membership/") for p in entries)
        before_obs, _ = combined_observations([SEASON], "Regular Season")
        append_bases = {
            p: data_path("data/" + p).read_bytes()
            for p in (CSV, CSV.removesuffix(".csv") + ".imports.json")
        }
        old_game_ids = set(pd.read_csv(data_path("data/" + CSV)).game_id.astype(int))
        teams = pd.read_csv(data_path(f"data/raw/team_game_stats/{SEASON}_regular_season.csv"))
        fixed = {(CLE, int(r["player_id"])) for r in baseline["candidates"]}
        before, before_full = _census(before_obs, teams, fixed, set())
        assert before == baseline["census"] and len(before_full) == 5
        validation = build_stage(
            EVIDENCE / "qualified-request.json",
            tmp_path / "sources",
            tmp_path / "stage",
            output,
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
        root = tmp_path / "stage/data"
        # PR619's stager preserves all structured/PDF authority. Carry the exact
        # published inactive inputs too, so consumers see the whole current base.
        prefix = f"raw/player_game_inactive/{SEASON}_regular_season"
        inactive_receipt = json.loads(data_path("data/" + prefix + ".source.json").read_bytes())
        inactive_paths = [
            prefix + ".csv",
            prefix + ".source.json",
            f"raw/player_game_inactive_sources/{inactive_receipt['sha256']}.csv",
        ]
        for relative in inactive_paths:
            raw = data_path("data/" + relative).read_bytes()
            assert _sha(raw) == entries[relative]["sha256"]
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for relative, digest in validation["base_file_hashes"].items():
            assert _sha(data_path("data/" + relative).read_bytes()) == digest
        # Both malformed whole games must fail unchanged. Their otherwise
        # plausible rows never become new facts, nor replace old accepted facts.
        bad_root = tmp_path / "bad/data"
        for family in ("games", "team_game_stats", "player_game_stats"):
            relative = f"raw/{family}/{SEASON}_regular_season.csv"
            target = bad_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        with ZipFile(EVIDENCE / "originals.zip") as archive:
            for row in qualified["quarantined_games"]:
                gid = row["game_id"]
                paths = []
                for endpoint in ("boxscoretraditionalv3", "boxscoresummaryv3"):
                    path = tmp_path / f"{endpoint}_{gid}.json"
                    path.write_bytes(archive.read("sources/" + path.name))
                    paths.append(path)
                with pytest.raises(ValueError, match=row["error"]):
                    stage_structured_game(
                        bad_root,
                        season=SEASON,
                        season_type="Regular Season",
                        game_id=int(gid),
                        traditional=paths[0],
                        summary=paths[1],
                        summary_version=3,
                        revision=request["revision"],
                        retrieved_at=_json(EVIDENCE / "sources.json")["files"][paths[0].name][
                            "retrieved_at"
                        ],
                    )
    assert validation["requested_game_count"] == 80
    assert validation["publication_state"] == "staged_only_no_writes"
    assert validation["append_only"][CSV]["added_records"] == 2772
    assert sum(r["listed_players"] for r in validation["qualified_games"]) == 2772
    assert _sha((EVIDENCE / "qualified-overlay-v1.zip").read_bytes()) == OVERLAY
    # A fresh pandas version can serialize the same minute float differently.
    # Rebuild proof stays separate; the consumer MUST use the exact frozen ZIP.
    (output / "validation.json").rename(output / "rebuild-validation.json")
    frozen_files, changed_minute_spellings = [], 0
    with ZipFile(EVIDENCE / "qualified-overlay-v1.zip") as frozen:
        assert len(frozen.namelist()) == len(set(frozen.namelist())) == 242
        assert set(frozen.namelist()) == {r["path"] for r in validation["overlay_files"]}
        for relative in frozen.namelist():
            body, rebuilt = frozen.read(relative), (output / relative).read_bytes()
            if relative == CSV:
                left = csv.DictReader(io.StringIO(body.decode()))
                right = csv.DictReader(io.StringIO(rebuilt.decode()))
                assert left.fieldnames == right.fieldnames
                for old, new in zip(left, right, strict=True):
                    for field in old:
                        if old[field] != new[field]:
                            assert field == "source_minutes" and old[field] and new[field]
                            # Existing _game_digest contract is %.9g. Every new
                            # frozen clock also faces the independent raw oracle below.
                            assert format(float(old[field]), ".9g") == format(
                                float(new[field]), ".9g"
                            )
                            changed_minute_spellings += 1
            else:
                assert body == rebuilt, relative
            if relative in validation["append_only"]:
                verify_append(
                    relative, append_bases[relative], body, validation["append_only"][relative]
                )
            (root / relative).write_bytes(body)
            (output / relative).write_bytes(body)
            frozen_files.append(dict(path=relative, size_bytes=len(body), sha256=_sha(body)))
    assert sum(r["size_bytes"] for r in frozen_files) == 3978591
    # This replays exact frozen rows/receipts against the original native bodies,
    # not the locally rebuilt CSV. A real format/lineage incompatibility still fails.
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    try:
        observations, _ = combined_observations([SEASON], "Regular Season")
        pairs = {tuple(p) for p in oracle["expanded_candidate_pairs"]}
        accepted_ids = {int(r["game_id"]) for r in qualified["requirements"]}
        census, full = _census(observations, teams, pairs, accepted_ids | old_game_ids)
        assert set(full) == {tuple(p) for p in oracle["after_complete_pairs"]}
        assert {tuple(p) for p in oracle["before_complete_pairs"]} <= set(full)
        cle_pairs = {p for p in pairs if p[0] == CLE}
        cle, cle_full = _census(observations, teams, cle_pairs, accepted_ids)
        assert cle["states"] == oracle["summary"]["fixed_after_states"]
        assert cle["complete_cases"] == 10 and cle["candidate_cases"] == 21
        assert set(before_full) <= set(cle_full) and fixed == cle_pairs
        membership = pd.DataFrame(columns=COLUMNS)
        for expected in oracle["expanded_cohort"]:
            pid = int(expected["player_id"])
            rows = observations.loc[observations.player_id.eq(pid)]
            states = {
                int(g.game_id): game_participation(
                    rows,
                    membership,
                    pid,
                    int(g.game_id),
                    CLE,
                    pd.Timestamp(g.game_date).date(),
                    other_team=int(g.opponent_team_id),
                )[0]
                for g in teams.loc[teams.team_id.eq(CLE)].itertuples()
            }
            assert states == {int(g): s for g, s in expected["after_game_states"].items()}
        new = pd.read_csv(root / CSV)
        actual = {
            (int(r.game_id), int(r.team_id), int(r.player_id)): r.participation_state
            for r in new.loc[new.game_id.isin(accepted_ids)].itertuples()
        }
        assert actual == {
            (int(r["game_id"]), int(r["team_id"]), int(r["player_id"])): r["participation_state"]
            for r in oracle["accepted_rows"]
        }
        by_key = new.set_index(["game_id", "team_id", "player_id"])
        for expected in oracle["accepted_rows"]:
            row = by_key.loc[expected["game_id"], expected["team_id"], expected["player_id"]]
            assert row.player_name == expected["player_name"]
            assert row.game_date == expected["game_date"]
            assert ("" if pd.isna(row.source_comment) else row.source_comment) == expected[
                "source_comment"
            ]
            if expected["source_minutes"] is None:
                assert pd.isna(row.source_minutes)
            else:
                assert row.source_minutes == pytest.approx(
                    expected["source_minutes"], abs=1e-10, rel=0
                )
        rejected_ids = {22400022, 22400027, 22400113, 22400136, 22400276, 22400348, 22401211}
        assert not rejected_ids & accepted_ids
        assert observations.loc[
            observations.game_id.isin(rejected_ids) & observations.player_id.eq(1642385)
        ].empty
        api = TestClient(app)
        answers = [
            dict(
                expected,
                query=f"{case['team_name']} record {word} {case['player_name']} in 2024-25",
                team_name=case["team_name"],
            )
            for case in oracle["new_complete_answers"]
            for word, expected in (("with", case["with"]), ("without", case["without"]))
        ]
        for case in answers:
            answer = api.post("/query", json={"query": case["query"]})
            assert answer.status_code == 200
            body = answer.json()
            if not case["game_ids"]:
                assert (body["result_status"], body["result_reason"]) == ("no_result", "no_match")
            else:
                assert body["result_status"] == "ok", (case["query"], body)
                sections = body["result"]["sections"]
                assert {int(r["game_id"]) for r in sections["game_log"]} == set(case["game_ids"])
                summary = sections["summary"][0]
                assert summary["team_name"] == case["team_name"]
                assert summary["season_start"] == SEASON and summary["season_end"] == SEASON
                assert summary["season_type"] == "Regular Season"
                assert (summary["games"], summary["wins"], summary["losses"]) == (
                    len(case["game_ids"]),
                    case["wins"],
                    case["losses"],
                )
                assert summary["pts_avg"] == pytest.approx(case["pts_avg"], abs=0.001)
        for candidate in baseline["candidates"]:
            if (CLE, candidate["player_id"]) not in cle_full:
                answer = api.post(
                    "/query",
                    json={
                        "query": f"Cavaliers record without {candidate['player_name']} in 2024-25"
                    },
                )
                assert answer.status_code == 200
                body = answer.json()
                assert (body["result_status"], body["result_reason"]) == (
                    "no_result",
                    "unsupported",
                )
                metadata = body["result"]["metadata"]
                assert metadata["team"] == "CLE" and metadata["season"] == SEASON
                assert metadata["without_player"] == candidate["player_name"]
                assert "Incomplete game-day participation coverage" in " ".join(body["notes"])
        report = dict(
            classification="qualified_staging_only_not_production",
            base_generation=GENERATION,
            base_manifest_sha256=MANIFEST,
            fixed_before=before,
            fixed_after=cle,
            expanded_after=cle,
            league_after=census,
            new_complete_answers=len(answers),
            opponent_new_complete_cases=len(oracle["opponent_new_complete_pairs"]),
            newly_discovered_cleveland_candidates=oracle["new_cleveland_candidate_ids"],
            collection_files=164,
            collection_bytes=3066238,
            qualified_games=80,
            qualified_rows=2772,
            quarantined_games=qualified["quarantined_games"],
            majority_goal_met=2 * cle["complete_cases"] > cle["candidate_cases"],
            production_writes=0,
            frozen_overlay_sha256=OVERLAY,
            frozen_overlay_files=frozen_files,
            rebuild_validation_sha256=_sha((output / "rebuild-validation.json").read_bytes()),
            rebuilt_minute_spellings_changed=changed_minute_spellings,
        )
        (output / "product-results.json").write_text(json.dumps(report, indent=2) + "\n")
        shutil.copyfile(EVIDENCE / "qualified-overlay-v1.zip", output / "overlay.zip")
        with capfd.disabled():
            print("CLEVELAND_PILOT " + json.dumps(report), flush=True)
    finally:
        reset_data_source_cache()
        clear_frame_cache()
    if r2_source is not None:
        assert r2_source.active_generation() == GENERATION
