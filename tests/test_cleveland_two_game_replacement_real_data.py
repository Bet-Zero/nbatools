"""Reuse two retained official reports; no acquisition or production publication."""

import hashlib
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
from nbatools.commands.pipeline.player_game_availability_report import (
    UnresolvedIdentity,
    official_report_as_v3,
)
from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    validate_publication,
)
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.test_cleveland_full_boxscore_real_data import (
    CSV,
    GENERATION,
    MANIFEST,
)
from tests.test_cleveland_full_boxscore_real_data import (
    OVERLAY as PARENT_SHA,
)
from tests.test_season_inactive_pilot_real_data import _census
from tools.availability_overlay import binding, preserve_cells, verify_append

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/cleveland-two-game-2024"
PARENT = PROGRAM / "source-evidence/cleveland-full-boxscore-2024"
ORIGINALS = "df954fe55ca067859dfa0cd76571b76cb8af7439eef27e037820665e131c535d"
OVERLAY = "a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298"
ORACLE = "14d76b4016cf26905a273c70366646a667597ced5ef1a89ce281d587a87082ea"
CLE, MIA, BKN = 1610612739, 1610612748, 1610612751
SEASON = "2024-25"
LEDGER = CSV.replace(".csv", ".imports.json")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path):
    return json.loads(path.read_bytes())


def _reports(cache, oracle):
    assert _sha((EVIDENCE / "originals.zip").read_bytes()) == ORIGINALS
    cache.mkdir()
    with ZipFile(EVIDENCE / "originals.zip") as archive:
        for case in oracle["reports"]:
            prefix = f"acquired_data/cleveland-two-game-source/{case['game_id']:010d}/"
            receipt = json.loads(archive.read(prefix + "capture.json"))
            assert receipt["http_status"] == 200 and receipt["attempts"] == 1
            assert receipt["redirects_followed"] == 0 and receipt["page_count"] == 1
            assert receipt["response_url"] == receipt["source_url"] == case["source_url"]
            body = archive.read(prefix + receipt["raw_file"])
            assert _sha(body) == receipt["sha256"] == case["pdf_sha256"]
            assert len(body) == receipt["size_bytes"] == case["pdf_bytes"]
            (cache / receipt["raw_file"]).write_bytes(body)
            name = Path(case["source_url"]).stem + ".json"
            record = dict(
                source_url=receipt["source_url"],
                retrieved_at=receipt["finished_at"],
                sha256=receipt["sha256"],
                size_bytes=len(body),
                raw_file=receipt["raw_file"],
            )
            (cache / name).write_text(json.dumps(record, sort_keys=True) + "\n")


def test_two_report_replacement_unlocks_four_cases_without_membership_guesses(
    tmp_path, monkeypatch, capfd
):
    assert _sha((EVIDENCE / "independent/source-oracle.json").read_bytes()) == ORACLE
    oracle = _json(EVIDENCE / "independent/source-oracle.json")
    assert oracle["parent_overlay_sha256"] == PARENT_SHA
    parent_proof = _json(PARENT / "independent/oracle.json")
    assert _sha((EVIDENCE / "qualified-overlay-v2.zip").read_bytes()) == OVERLAY
    assert _sha((PARENT / "qualified-overlay-v1.zip").read_bytes()) == PARENT_SHA
    specification = _json(EVIDENCE / "validation.json")
    root = tmp_path / "consumer/data"
    cache = tmp_path / "reports"
    _reports(cache, oracle)
    r2 = None
    if os.environ.get("DATA_SOURCE") == "r2":
        from nbatools.data_source import _get_data_source

        r2 = _get_data_source()
        assert r2.active_generation() == GENERATION
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(manifest_raw) == MANIFEST
        entries = {r["path"]: r for r in json.loads(manifest_raw)["files"]}
        assert not any(p.startswith("raw/player_team_membership/") for p in entries)

        def copy(relative):
            body = data_path("data/" + relative).read_bytes()
            assert len(body) == entries[relative]["size_bytes"]
            assert _sha(body) == entries[relative]["sha256"]
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return body

        for path, digest in specification["base_file_hashes"].items():
            assert _sha(copy(path)) == digest
        base_tables = {p: (root / p).read_bytes() for p in (CSV, LEDGER)}
        # Copy only the ten prior game packets and original bodies consumed by
        # this season. The other immutable base objects are never changed.
        old = pd.read_csv(root / CSV)
        source_prefix = "raw/player_game_availability_sources/"
        assert old.source.str.startswith("nba_stats_structured_archive:").all()
        for digest in old.source_sha256.unique():
            packet = json.loads(copy(source_prefix + digest + ".structured.json"))
            for source in packet["sources"].values():
                copy(source_prefix + source["file"])
        inactive_prefix = f"raw/player_game_inactive/{SEASON}_regular_season"
        inactive_receipt = json.loads(copy(inactive_prefix + ".source.json"))
        copy(inactive_prefix + ".csv")
        copy(f"raw/player_game_inactive_sources/{inactive_receipt['sha256']}.csv")
    with ZipFile(PARENT / "qualified-overlay-v1.zip") as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == 242
        for relative in archive.namelist():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(relative))
    parent_tables = {p: (root / p).read_bytes() for p in (CSV, LEDGER)}
    parent_sources = {p.name: _sha(p.read_bytes()) for p in (root / source_prefix).iterdir()}
    teams = pd.read_csv(root / f"raw/team_game_stats/{SEASON}_regular_season.csv")
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    try:
        before_obs, _ = combined_observations([SEASON], "Regular Season")
        pairs = {(CLE, r["player_id"]) for r in oracle["cleveland_cohort"]}
        before, before_full = _census(
            before_obs, teams, pairs, {int(g) for g in parent_proof["qualified_game_ids"]}
        )
        assert before["complete_cases"] == 10 and len(pairs) == 21
        # Entire Brooklyn side stays unqualified; never repair one name to make
        # the clock replacement pass. Cached mode cannot fetch identity fallbacks.
        with pytest.raises(UnresolvedIdentity, match="Cui Yongxi"):
            official_report_as_v3(
                game_id=22400199,
                game_date="2024-11-09",
                season=SEASON,
                season_type="Regular Season",
                home_team_id=CLE,
                away_team_id=BKN,
                data_root=root,
                cached_reports=cache,
            )
        for case in oracle["reports"]:
            backfill(
                SEASON,
                "Regular Season",
                root=root,
                cached_reports=cache,
                game_ids=[case["game_id"]],
                source="report",
                imported_team_ids=case["imported_team_ids"],
            )
        ids = ["0022400199", "0022400893"]
        (root / CSV).write_bytes(
            preserve_cells(
                CSV,
                parent_tables[CSV],
                (root / CSV).read_bytes(),
                binding(parent_tables[CSV], ids, added_records=52),
            )
        )
        verify_append(
            LEDGER,
            parent_tables[LEDGER],
            (root / LEDGER).read_bytes(),
            binding(parent_tables[LEDGER], ids, added_records=2),
        )
        # Consume exact retained v2 bytes, independent of pandas CSV spelling.
        with ZipFile(EVIDENCE / "qualified-overlay-v2.zip") as archive:
            assert len(archive.namelist()) == len(set(archive.namelist())) == 247
            assert archive.read("validation.json") == (EVIDENCE / "validation.json").read_bytes()
            for item in specification["overlay_files"]:
                relative = item["path"]
                body = archive.read(relative)
                assert _sha(body) == item["sha256"] and len(body) == item["size_bytes"]
                if relative != CSV:
                    assert body == (root / relative).read_bytes(), relative
                if relative in specification["append_only"]:
                    verify_append(
                        relative,
                        base_tables[relative],
                        body,
                        specification["append_only"][relative],
                    )
                (root / relative).write_bytes(body)
        verify_append(
            CSV,
            parent_tables[CSV],
            (root / CSV).read_bytes(),
            binding(parent_tables[CSV], ids, added_records=52),
        )
        assert all(
            _sha((root / source_prefix / n).read_bytes()) == h for n, h in parent_sources.items()
        )
        validate_publication(root)
        new = pd.read_csv(root / CSV)
        added = new.loc[new.game_id.isin([22400199, 22400893])]
        indexed = added.set_index(["game_id", "team_id", "player_id"])
        assert len(added) == len(oracle["accepted_rows"]) == 52
        assert set(indexed.index) == {
            (r["game_id"], r["team_id"], r["player_id"]) for r in oracle["accepted_rows"]
        }
        for expected in oracle["accepted_rows"]:
            row = indexed.loc[expected["game_id"], expected["team_id"], expected["player_id"]]
            for field in ("game_date", "player_name", "participation_state"):
                assert row[field] == expected[field]
            assert ("" if pd.isna(row.source_comment) else row.source_comment) == expected[
                "source_comment"
            ]
            if expected["source_minutes"] is None:
                assert pd.isna(row.source_minutes)
            else:
                assert row.source_minutes == pytest.approx(
                    expected["source_minutes"], abs=1e-10, rel=0
                )
        assert indexed.loc[22400199, CLE, 1630241].source_minutes == 20
        assert indexed.loc[22400893, MIA, 1629130].source_minutes == pytest.approx(28 + 59 / 60)
        clear_frame_cache()
        observations, _ = combined_observations([SEASON], "Regular Season")
        after, full = _census(
            observations, teams, pairs, set(teams.loc[teams.team_id.eq(CLE), "game_id"])
        )
        assert (
            after["complete_cases"] == 14
            and after["states"] == oracle["summary"]["cleveland_after_states"]
        )
        assert set(before_full) <= set(full)
        assert set(full) - set(before_full) == {tuple(p) for p in oracle["new_complete_pairs"]}
        empty = pd.DataFrame(columns=COLUMNS)
        for expected in oracle["cleveland_cohort"]:
            pid = expected["player_id"]
            rows = observations.loc[observations.player_id.eq(pid)]
            states = {
                int(g.game_id): game_participation(
                    rows,
                    empty,
                    pid,
                    int(g.game_id),
                    CLE,
                    pd.Timestamp(g.game_date).date(),
                    other_team=int(g.opponent_team_id),
                )[0]
                for g in teams.loc[teams.team_id.eq(CLE)].itertuples()
            }
            assert states == {int(g): s for g, s in expected["after_game_states"].items()}
        api = TestClient(app)
        answer_count = 0
        for case in oracle["new_complete_answers"] + parent_proof["new_complete_answers"]:
            for word in ("with", "without"):
                expected = case[word]
                result = api.post("/query", json={"query": expected["query"]})
                assert result.status_code == 200
                result = result.json()
                assert result["result_status"] == "ok", expected["query"]
                sections = result["result"]["sections"]
                assert {int(r["game_id"]) for r in sections["game_log"]} == set(
                    expected["game_ids"]
                )
                summary = sections["summary"][0]
                assert summary["team_name"] == case["team_name"]
                assert summary["season_start"] == summary["season_end"] == SEASON
                assert summary["season_type"] == "Regular Season"
                for field in ("games", "wins", "losses"):
                    assert summary[field] == expected[field]
                assert summary["pts_avg"] == pytest.approx(expected["pts_avg"], abs=0.001)
                answer_count += 1
        for case in oracle["cleveland_cohort"]:
            if case["after"]["unknown"]:
                result = api.post(
                    "/query",
                    json={"query": f"Cavaliers record without {case['player_name']} in 2024-25"},
                ).json()
                assert (result["result_status"], result["result_reason"]) == (
                    "no_result",
                    "unsupported",
                )
                assert "Incomplete game-day participation coverage" in " ".join(result["notes"])
        assert observations.loc[
            observations.game_id.eq(22400199) & observations.player_id.eq(1642385)
        ].empty
        rejected = {22400022, 22400027, 22400113, 22400136, 22400276, 22400348, 22401211}
        assert observations.loc[
            observations.game_id.isin(rejected) & observations.player_id.eq(1642385)
        ].empty
        output = (
            Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path))
            / "cleveland-two-game-qualified"
        )
        output.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(EVIDENCE / "qualified-overlay-v2.zip", output / "qualified-overlay-v2.zip")
        report = dict(
            classification="qualified_staging_only_no_publication",
            before=before,
            after=after,
            added_rows=52,
            new_complete_cases=4,
            new_answer_checks=8,
            total_answer_checks=answer_count,
            incomplete_cases=7,
            source_requests=0,
            source_bytes=52597,
            overlay_sha256=OVERLAY,
            overlay_data_bytes=4044711,
            parent_sha256=PARENT_SHA,
            production_writes=0,
            brooklyn_side_accepted=False,
        )
        (output / "product-results.json").write_text(json.dumps(report, indent=2) + "\n")
        with capfd.disabled():
            print("CLEVELAND_TWO_REPORT_PRODUCT " + json.dumps(report), flush=True)
    finally:
        reset_data_source_cache()
        clear_frame_cache()
    if r2 is not None:
        assert r2.active_generation() == GENERATION
