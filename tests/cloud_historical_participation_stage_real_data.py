"""Bounded offline historical participation stages; no acquisition or publication."""

import csv
import hashlib
import io
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.commands._player_identity import player_name_key
from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.data_source import (
    data_generation_context,
    data_path,
    reset_data_source_cache,
)
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.test_lal_participation_stage_real_data import _assert_record, _original_fact
from tools.availability_overlay import verify_append
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
BASE = "availability-lebron-season-v1-20261031"
BASE_MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
LAL_REQUEST = PROGRAM / "collection-requests/lal-participation-remaining-2023-24.json"
BOS_REQUEST = PROGRAM / "collection-requests/bos-tatum-participation-remaining-2024-25.json"
LAL_SOURCES = PROGRAM / "source-evidence/k08-direct-dependencies/lal-2023-24"
BOS_SOURCES = PROGRAM / "source-evidence/k08-direct-dependencies/bos-2024-25"
SOURCE_MANIFEST_SHA256 = {
    "lal-2023-24": "ff5f604392b168c1259e3a219c2cdddc58b25b392fa8b7fbac74872b3b7f33df",
    "bos-2024-25": "b38929d14ed1827245307a4e666e82c3a810514fef57fe5ef46c212075993be7",
}
PROOF_SHA256 = {
    "historical-source-qualification.json": "b22dd69bd22f48767c760bb71a85e1796243b857662108cd9363bfe8d55c3389",
    "historical-projection-oracle.json": "fceebc26212b0d41f697246a68a3b23f129f6044f8dd60443668f178e5473cd3",
    "historical-answer-oracle.json": "b589e2b3b8b9a9539ac4909d891854cd0bbeb156add92913e43acfb6138ec2e9",
}
LAL, BOS = 1610612747, 1610612738
CSV = "raw/player_game_availability/2023-24_regular_season.csv"
LEDGER = CSV.removesuffix(".csv") + ".imports.json"
SOURCES = "raw/player_game_availability_sources/"
PEOPLE = {203076: "Anthony Davis", 2544: "LeBron James", 1630559: "Austin Reaves"}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _baseline(manifest):
    """Reuse the accepted exact328-state audit only while every input hash still matches."""
    path = PROGRAM / "source-evidence/k08-direct-dependencies/input-audit-source.zip"
    assert (
        _sha(path.read_bytes())
        == "33f4a6d9a013da81f3f4c3c25f837c44cd7248de42f425b92e01af68b71cb67a"
    )
    entries = {row["path"]: row for row in manifest["files"]}
    states, teams, players, subsets = {}, {}, {}, {}
    prefix = "acquired_data/direct-k08-participation-coverage/"
    with ZipFile(path) as archive:
        binding = json.loads(archive.read(prefix + "source-bindings.json"))
        assert binding["generation"] == BASE and binding["manifest_sha256"] == BASE_MANIFEST
        for item in binding["source_files"]:
            assert entries[item["path"]] == item
        for relative in binding["manifest_absent_optional_paths"]:
            assert relative not in entries
        for filename, digest in binding["subset_sha256"].items():
            raw = archive.read(prefix + filename)
            assert _sha(raw) == digest
            subsets[filename] = raw
        for season, team_id, people in [
            ("2023-24", LAL, PEOPLE),
            ("2024-25", BOS, {1628369: "Jayson Tatum"}),
        ]:
            teams[season] = pd.read_csv(io.BytesIO(subsets[f"{season}-{team_id}-team82.csv"]))
            players[season] = pd.read_csv(
                io.BytesIO(subsets[f"{season}-{team_id}-target-player-rows.csv"])
            )
            assert len(teams[season]) == teams[season].game_id.nunique() == 82
            for pid in people:
                audit = json.loads(archive.read(prefix + f"{season}-{pid}-coverage.json"))
                assert audit["runtime_exception"] is None
                assert audit["disposition"] in {
                    "qualified_incomplete_missing_evidence",
                    "qualified_complete_observed_population",
                }
                report = audit["runtime_report"]
                assert report["requested_games"] == report["observed_team_games"] == 82
                assert report["source_hashes"] == {
                    p: entries[p]["sha256"] for p in report["source_hashes"]
                }
                states[(season, pid)] = {
                    int(row["game_id"]): row["state"] for row in report["games"]
                }
    return states, teams, players, subsets


def _source_facts(request, directory, states):
    """Independent target arithmetic from literal Traditional rows and Summary inactives."""
    result, populations = [], {}
    for requirement in request["requirements"]:
        gid = requirement["game_id"]
        if gid not in populations:
            summary_endpoint = next(
                p["endpoint"]
                for p in requirement["proposed_sources"]
                if p["endpoint"] != "boxscoretraditionalv3"
            )
            documents, hashes = [], {}
            for endpoint in ("boxscoretraditionalv3", summary_endpoint):
                path = directory / "sources" / f"{endpoint}_{gid}.json"
                raw = path.read_bytes()
                documents.append(json.loads(raw))
                hashes[path.name] = _sha(raw)
            traditional = documents[0]["boxScoreTraditional"]
            assert int(traditional["gameId"]) == int(gid)
            if summary_endpoint == "boxscoresummaryv2":
                table = next(
                    t for t in documents[1]["resultSets"] if t["name"] == "InactivePlayers"
                )
                assert len(table["headers"]) == len(set(table["headers"]))
                inactive = [
                    dict(zip(table["headers"], row, strict=True)) for row in table["rowSet"]
                ]
                summary = {
                    side: dict(
                        teamId=traditional[side]["teamId"],
                        inactives=[
                            dict(personId=p["PLAYER_ID"], original_summary_row=p)
                            for p in inactive
                            if int(p["TEAM_ID"]) == int(traditional[side]["teamId"])
                        ],
                    )
                    for side in ("homeTeam", "awayTeam")
                }
                assert all(
                    int(p["TEAM_ID"])
                    in {int(traditional[s]["teamId"]) for s in ("homeTeam", "awayTeam")}
                    for p in inactive
                )
            else:
                summary = documents[1]["boxScoreSummary"]
                assert int(summary["gameId"]) == int(gid)
            listed = [
                (int(d[side]["teamId"]), int(p["personId"]))
                for d, collection in ((traditional, "players"), (summary, "inactives"))
                for side in ("homeTeam", "awayTeam")
                for p in d[side][collection]
            ]
            assert len(listed) == len(set(listed)) == len({pid for _, pid in listed})
            populations[gid] = (traditional, summary, hashes, len(listed))
        traditional, summary, hashes, _ = populations[gid]
        key = request["season"], requirement["player_id"]
        assert states[key][int(gid)] == "unknown"
        fact = _original_fact(
            traditional, summary, player_id=requirement["player_id"], team_id=requirement["team_id"]
        )
        states[key][int(gid)] = fact["state"]
        result.append({**requirement, **fact, "source_hashes": hashes})
    return result, sum(row[3] for row in populations.values())


def _check_projection(projections, states, teams):
    assert {(row["season"], row["player_id"]) for row in projections} == set(states)
    for row in projections:
        sample = states[(row["season"], row["player_id"])]
        counts = Counter(sample.values())
        assert all(counts[key] == row[key] for key in ("played", "did_not_play", "unknown"))
        missed = {gid for gid, state in sample.items() if state == "did_not_play"}
        assert missed == set(row["did_not_play_game_ids"])
        team = teams[row["season"]]
        expected = team.loc[team.game_id.isin(missed)]
        home = set(
            expected.loc[
                expected.is_home.astype(str).str.lower().isin(["true", "1", "1.0"]), "game_id"
            ].astype(int)
        )
        assert home == set(row["home_dnp_game_ids"]) and len(home) == row["home_dnp"]
        record = row["without_record"]
        assert set(record["game_ids"]) == missed
        assert (
            len(expected),
            int(expected.wl.eq("W").sum()),
            int(expected.wl.eq("L").sum()),
            int(expected.pts.sum()),
        ) == tuple(record[k] for k in ("games", "wins", "losses", "points"))


def _check_staged_populations(root, qualification):
    for group in qualification["groups"]:
        season = {"lal-2023-24": "2023-24", "bos-2024-25": "2024-25"}[group["cohort"]]
        rows = pd.read_csv(root / f"raw/player_game_availability/{season}_regular_season.csv")
        rows = rows.loc[rows.game_id.eq(int(group["game_id"]))]
        expected = {(r["team_id"], r["player_id"]): r for r in group["listed_population"]}
        assert len(rows) == len(expected) == group["all_listed_rows"]
        assert set(zip(rows.team_id, rows.player_id)) == set(expected)
        assert rows.game_date.eq(group["game_date"]).all()
        for row in rows.itertuples():
            fact = expected[(row.team_id, row.player_id)]
            assert player_name_key(row.player_name) == player_name_key(fact["player_name"])
            assert row.participation_state == fact["source_state"]
            if row.participation_state == "played":
                assert row.source_minutes * 60 == pytest.approx(
                    float(fact["source_seconds"]), abs=1e-6
                )


def _stage_requests(tmp_path, lal_path, bos_path, lal_sources, bos_sources):
    """Each season is prepared independently from the same real published base."""
    stages = []
    for label, request_path, sources, season in (
        ("lal", lal_path, lal_sources, "2023-24"),
        ("bos", bos_path, bos_sources, "2024-25"),
    ):
        request = json.loads(request_path.read_bytes())
        assert request["base_generation"] == BASE
        assert request["base_manifest_sha256"] == BASE_MANIFEST
        assert request["season"] == season and request["season_type"] == "Regular Season"
        work = tmp_path / (label + "-stage")
        validation = build_stage(
            request_path,
            sources,
            work,
            tmp_path / (label + "-overlay"),
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
        assert (
            validation["base_generation"] == BASE
            and validation["base_manifest_sha256"] == BASE_MANIFEST
        )
        stages.append((work / "data", validation))
    lal, bos = (row[1] for row in stages)
    assert set(lal["append_only"]) == {CSV, LEDGER}
    assert not lal["manifest_absent_creations"] and not bos["append_only"]
    assert set(bos["manifest_absent_creations"]) == {
        "raw/player_game_availability/2024-25_regular_season.csv",
        "raw/player_game_availability/2024-25_regular_season.imports.json",
    }
    shared = lal["base_file_hashes"].keys() & bos["base_file_hashes"].keys()
    assert all(lal["base_file_hashes"][p] == bos["base_file_hashes"][p] for p in shared)
    return stages


def _merge_roots(roots, work):
    """A shared path must contain identical bytes; neither stage can overwrite the other."""
    assert not work.exists()
    combined = work / "data"
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            assert not path.is_symlink()
            relative = path.relative_to(root)
            assert relative.as_posix() != "metadata/generation_manifest.json"
            target = combined / relative
            raw = path.read_bytes()
            if target.exists():
                assert target.read_bytes() == raw, f"Conflicting stage path: {relative}"
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    validate_publication(combined)
    return combined


def _export_overlay(root, manifest, output, lal, bos):
    entries = {row["path"]: row for row in manifest["files"]}
    append = {**lal["append_only"], **bos["append_only"]}
    creations = bos["manifest_absent_creations"]
    assert not append.keys() & creations.keys()
    assert len(append) == len(creations) == 2
    output.mkdir()
    files = []
    for directory in ("raw/player_game_availability", SOURCES):
        for path in sorted((root / directory).iterdir()):
            relative, raw = path.relative_to(root).as_posix(), path.read_bytes()
            if relative in entries and _sha(raw) == entries[relative]["sha256"]:
                continue
            if relative in entries:
                assert relative in append, "Changed existing source authority"
            elif directory == "raw/player_game_availability":
                assert relative in creations, "Unregistered new availability table"
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            files.append(dict(path=relative, sha256=_sha(raw), size_bytes=len(raw)))
    assert {
        r["path"] for r in files if r["path"].startswith("raw/player_game_availability/")
    } == append.keys() | creations.keys()
    return dict(
        base_generation=BASE,
        base_manifest_sha256=BASE_MANIFEST,
        append_only=append,
        manifest_absent_creations=creations,
        overlay_files=files,
        production_writes=0,
        full_required_slice_accepted=False,
        publication_state="staged_only_no_writes",
    )


def _assert_finder(result, ids, *, route):
    if not ids:
        assert result.result_status == "no_result" and result.result_reason == "no_match", (
            result.metadata
        )
        return
    assert result.result_status == "ok" and result.route == route, result.metadata
    assert {int(row["game_id"]) for row in result.result.to_dict()["sections"]["finder"]} == ids


def _run_consumers(manifest_sha, states, teams, players):
    """Real consumers of the retained AD/Reaves/LeBron/Tatum requirements."""
    from fastapi.testclient import TestClient

    from nbatools.api import app

    client, coverage, answers = TestClient(app), [], []
    actors = [("2023-24", LAL, pid, name) for pid, name in PEOPLE.items()]
    actors.append(("2024-25", BOS, 1628369, "Jayson Tatum"))
    for season, team_id, pid, name in actors:
        expected = states[(season, pid)]
        report = build_report(
            generation="legacy",
            manifest_sha256=manifest_sha,
            season=season,
            team_id=team_id,
            player_id=pid,
        )
        assert report["requested_games"] == report["observed_team_games"] == 82
        assert report["complete_requested_population"] and not report["missing_keys"]
        assert {int(row["game_id"]): row["state"] for row in report["games"]} == expected
        assert report["counts"] == {
            key: Counter(expected.values())[key]
            for key in ("played", "did_not_play", "same_game_other_side", "unknown")
        }
        missed = {gid for gid, state in expected.items() if state == "did_not_play"}
        assert report["missed_games"] == len(missed)
        team = teams[season]
        home = set(
            team.loc[
                team.game_id.isin(missed)
                & team.is_home.astype(str).str.lower().isin(["1", "1.0", "true"]),
                "game_id",
            ].astype(int)
        )
        for query, ids in [
            (f"how many games did {'Tatum' if pid == 1628369 else name} miss in {season}", missed),
            (f"how many home games did {name} miss in {season}", home),
        ]:
            result = execute_natural_query(query)
            assert result.result_status == "ok" and result.route == "game_finder", result.metadata
            sections = result.result.to_dict()["sections"]
            assert sections["count"] == [{"count": len(ids)}]
            assert {int(row["game_id"]) for row in sections["finder"]} == ids
            answers.append(dict(query=query, ids=sorted(ids), count=len(ids)))
            if pid == 1628369 and ids == missed:
                response = client.post("/query", json={"query": query})
                assert response.status_code == 200 and response.json()["result_status"] == "ok"
                assert response.json()["result"]["sections"]["count"] == [{"count": len(ids)}]
        coverage.append(report)
    assert states[("2023-24", 1630559)] == {int(g): "played" for g in teams["2023-24"].game_id}
    lal = teams["2023-24"]
    ad_out = {gid for gid, state in states[("2023-24", 203076)].items() if state == "did_not_play"}
    lebron_played = {gid for gid, state in states[("2023-24", 2544)].items() if state == "played"}
    for query, absent, positive, ids in [
        ("Lakers record without Davis in 2023-24", "Anthony Davis", None, ad_out),
        (
            "Lakers record without Davis and with LeBron James in 2023-24",
            "Anthony Davis",
            "LeBron James",
            ad_out & lebron_played,
        ),
        (
            "Lakers record without Davis and Reaves in 2023-24",
            "Anthony Davis and Austin Reaves",
            None,
            set(),
        ),
        ("Lakers record without Reaves in 2023-24", "Austin Reaves", None, set()),
    ]:
        expected = lal.loc[lal.game_id.isin(ids)]
        results = [
            execute_natural_query(query),
            execute_structured_query(
                "team_record",
                team="LAL",
                season="2023-24",
                without_player=absent,
                **(dict(with_player=positive) if positive else {}),
            ),
        ]
        for result in results:
            if expected.empty:
                assert result.result_status == "no_result" and result.result_reason == "no_match", (
                    result.metadata
                )
            else:
                assert result.result_status == "ok" and result.route == "team_record", (
                    result.metadata
                )
                _assert_record(result.result.to_dict(), expected)
        if absent == "Anthony Davis":
            response = client.post("/query", json={"query": query})
            assert response.status_code == 200
            if expected.empty:
                assert (
                    response.json()["result_status"] == "no_result"
                    and response.json()["result_reason"] == "no_match"
                )
            else:
                assert response.json()["result_status"] == "ok"
                _assert_record(response.json()["result"], expected)
        answers.append(
            dict(
                query=query,
                ids=sorted(ids),
                wins=int(expected.wl.eq("W").sum()),
                losses=int(expected.wl.eq("L").sum()),
                points=int(expected.pts.sum()),
            )
        )
    primary = players["2023-24"].loc[
        lambda f: f.player_id.eq(2544) & f.team_id.eq(LAL) & f.minutes.gt(0)
    ]
    primary = primary.merge(
        lal[["game_id", "wl"]], on="game_id", how="left", validate="many_to_one"
    )
    assert primary.wl.isin(["W", "L"]).all()
    summary_sample = primary.loc[primary.game_id.isin(ad_out)]
    query = "LeBron James stats without Davis in 2023-24"
    for result in [
        execute_natural_query(query),
        execute_structured_query(
            "player_game_summary",
            player="LeBron James",
            season="2023-24",
            without_player="Anthony Davis",
        ),
    ]:
        assert result.result_status == "ok" and result.route == "player_game_summary", (
            result.metadata
        )
        summary = _assert_record(result.result.to_dict(), summary_sample)
        assert summary["player_name"] == "LeBron James" and summary["pts_sum"] == int(
            summary_sample.pts.sum()
        )
    response = client.post("/query", json={"query": query})
    assert response.status_code == 200 and response.json()["result_status"] == "ok"
    summary = _assert_record(response.json()["result"], summary_sample)
    assert summary["player_name"] == "LeBron James" and summary["pts_sum"] == int(
        summary_sample.pts.sum()
    )
    answers.append(
        dict(
            query=query,
            ids=sorted(summary_sample.game_id.astype(int)),
            games=len(summary_sample),
            points=int(summary_sample.pts.sum()),
        )
    )
    expected = primary.loc[primary.game_id.isin(ad_out) & primary.pts.ge(30)]
    query = "LeBron James 30 point games with Davis out in 2023-24"
    for result in [
        execute_natural_query(query),
        execute_structured_query(
            "player_game_finder",
            player="LeBron James",
            season="2023-24",
            without_player="Anthony Davis",
            stat="pts",
            min_value=30,
        ),
    ]:
        _assert_finder(result, set(expected.game_id.astype(int)), route="player_game_finder")
    answers.append(
        dict(query=query, ids=sorted(expected.game_id.astype(int)), points=int(expected.pts.sum()))
    )
    result = execute_natural_query(
        "LeBron James games with 20 points without Davis and Reaves in 2023-24"
    )
    _assert_finder(result, set(), route="player_game_finder")
    return coverage, answers


def test_retained_historical_sources_expand_direct_absence_consumers(tmp_path, monkeypatch):
    requests = [
        (
            LAL_REQUEST,
            LAL_SOURCES,
            "7c77db1142276fff8cf8181f744c0040b550d7d8b7d3f7994c348e5d0fb11036",
        ),
        (
            BOS_REQUEST,
            BOS_SOURCES,
            "5bedec01c26494aee835c8503216e65abd71c8bddf2854f9baf409256843fb83",
        ),
    ]
    proofs = {}
    for name, digest in PROOF_SHA256.items():
        raw = (PROGRAM / "source-evidence/k08-direct-dependencies" / name).read_bytes()
        assert _sha(raw) == digest
        proofs[name] = json.loads(raw)
    qualification = proofs["historical-source-qualification.json"]
    assert qualification["source_qualification_passed"] and not qualification["blocked_groups"]
    assert (
        not qualification["canonical_PGA_full_validation_accepted"]
        and not qualification["staging_accepted"]
    )
    assert qualification["source_files"] == 50 and qualification["total_source_bytes"] == 722069
    assert (
        qualification["oracle_bindings"]["projection_sha256"]
        == PROOF_SHA256["historical-projection-oracle.json"]
    )
    assert (
        qualification["oracle_bindings"]["answer_sha256"]
        == PROOF_SHA256["historical-answer-oracle.json"]
    )
    groups = {row["game_id"]: row for row in qualification["groups"]}
    assert len(groups) == 25
    with data_generation_context() as generation:
        assert generation == BASE
        manifest_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert _sha(manifest_raw) == BASE_MANIFEST
        manifest = json.loads(manifest_raw)
        assert manifest["generation_id"] == BASE and len(manifest["files"]) == 775
        entries = {r["path"]: r for r in manifest["files"]}
        assert len(entries) == 775
        states, teams, players, subsets = _baseline(manifest)
        facts, source_population_rows = [], []
        for path, source, digest in requests:
            assert _sha(path.read_bytes()) == digest
            request = json.loads(path.read_bytes())
            source_manifest_raw = (source / "sources.json").read_bytes()
            assert _sha(source_manifest_raw) == SOURCE_MANIFEST_SHA256[source.name]
            provenance = json.loads(source_manifest_raw)
            assert provenance["collection_request_sha256"] == digest
            requested = {
                (request["season"], row["player_id"], int(row["game_id"]))
                for row in request["requirements"]
            }
            unknown = {
                (season, pid, gid)
                for (season, pid), sample in states.items()
                if season == request["season"]
                for gid, state in sample.items()
                if state == "unknown"
            }
            assert requested == unknown
            target_facts, population_rows = _source_facts(request, source, states)
            facts.extend(target_facts)
            source_population_rows.append(population_rows)
        for fact in facts:
            group = groups[fact["game_id"]]
            assert (fact["team_id"], fact["player_id"], fact["state"]) == (
                group["target_fact"]["team_id"],
                group["target_fact"]["player_id"],
                group["target_fact"]["source_state"],
            )
            assert fact["game_date"] == group["game_date"]
            assert fact["source_hashes"] == {
                Path(item["file"]).name: item["sha256"] for item in group["source_bindings"]
            }
        _check_projection(proofs["historical-projection-oracle.json"], states, teams)
        assert len(facts) == 25 and not any(
            state == "unknown" for sample in states.values() for state in sample.values()
        )
        baseline = {path: data_path("data/" + path).read_bytes() for path in (CSV, LEDGER)}
        assert all(_sha(raw) == entries[path]["sha256"] for path, raw in baseline.items())
        old = list(csv.DictReader(io.StringIO(baseline[CSV].decode(), newline="")))
        assert len(old) == 68 and len(json.loads(baseline[LEDGER])) == 2
        stages = _stage_requests(tmp_path, LAL_REQUEST, BOS_REQUEST, LAL_SOURCES, BOS_SOURCES)
    lal, bos = (row[1] for row in stages)
    assert lal["append_only"][CSV]["added_records"] == source_population_rows[0]
    bos_csv = "raw/player_game_availability/2024-25_regular_season.csv"
    assert bos["manifest_absent_creations"][bos_csv]["added_records"] == source_population_rows[1]
    assert lal["requested_game_count"] == lal["requested_target_count"] == 15
    assert bos["requested_game_count"] == bos["requested_target_count"] == 10
    assert {
        (int(row["game_id"]), row["player_id"], row["state"])
        for row in lal["qualified_targets"] + bos["qualified_targets"]
    } == {(int(row["game_id"]), row["player_id"], row["state"]) for row in facts}
    root = _merge_roots([row[0] for row in stages], tmp_path / "combined")
    _check_staged_populations(root, qualification)
    for relative, spec in lal["append_only"].items():
        verify_append(relative, baseline[relative], (root / relative).read_bytes(), spec)
    after = {
        (r["game_id"], r["team_id"], r["player_id"]): r
        for r in csv.DictReader(io.StringIO((root / CSV).read_bytes().decode(), newline=""))
    }
    assert all(after[(r["game_id"], r["team_id"], r["player_id"])] == r for r in old)
    for path, item in entries.items():
        local = root / path
        if local.exists() and path not in lal["append_only"]:
            assert _sha(local.read_bytes()) == item["sha256"]
    destination = tmp_path / "historical-overlay"
    validation = _export_overlay(root, manifest, destination, lal, bos)
    diagnostics = destination / "historical-participation-acceptance"
    diagnostics.mkdir()
    for name, raw in subsets.items():
        (diagnostics / name).write_bytes(raw)
    (diagnostics / "source-target-facts.json").write_text(json.dumps(facts, indent=2) + "\n")
    # This inventory only enables local test consumers over the copied/staged
    # files. It is never exported as a publication manifest or full-slice claim.
    inventory = json.dumps(
        dict(
            generation_id="legacy",
            classification="test_only_development_staging",
            files=[
                dict(
                    path=p.relative_to(root).as_posix(),
                    size_bytes=p.stat().st_size,
                    sha256=_sha(p.read_bytes()),
                )
                for p in sorted(root.rglob("*"))
                if p.is_file()
            ],
        )
    ).encode()
    (root / "metadata/generation_manifest.json").write_bytes(inventory)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        reports, answers = _run_consumers(_sha(inventory), states, teams, players)
        answer_oracle = proofs["historical-answer-oracle.json"]
        for answer in answers:
            if "wins" in answer:
                matches = [
                    r
                    for r in answer_oracle
                    if r["route"] == "team_record" and set(r["game_ids"]) == set(answer["ids"])
                ]
                assert matches and all(
                    tuple(answer[k] for k in ("wins", "losses", "points"))
                    == tuple(r[k] for k in ("wins", "losses", "points"))
                    for r in matches
                )

        # Filling the two selected cohorts does not fill other player-seasons.
        unknown = build_report(
            generation="legacy",
            manifest_sha256=_sha(inventory),
            season="2023-24",
            team_id=BOS,
            player_id=1628369,
        )
        assert unknown["counts"]["unknown"] > 0 and not unknown["complete_requested_population"]
        assert unknown["missed_games"] is None and unknown["missing_keys"]
        result = execute_natural_query("how many games did Tatum miss in 2023-24")
        assert result.result_status == "no_result" and result.result_reason != "no_match", (
            result.metadata
        )
    finally:
        reset_data_source_cache()
    validation.update(
        candidate_sha=os.environ["VALIDATION_SHA"],
        request_sha256={p.name: digest for p, _, digest in requests},
        source_manifests_sha256={
            p.name: _sha((source / "sources.json").read_bytes()) for p, source, _ in requests
        },
        source_kind="retained_originals_only_no_acquisition",
        source_proof_sha256=PROOF_SHA256,
        staged_target_keys=25,
        season_stage_validations=[lal, bos],
    )
    receipt = dict(
        classification="isolated_historical_cohorts_staging_not_publication_or_2025_composition",
        validation=validation,
        reports=reports,
        answers=answers,
        incomplete_other_scope=unknown,
        production_writes=0,
        full_required_slice_accepted=False,
    )
    (destination / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    (diagnostics / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "historical-participation-stage"
    assert not output.exists()
    shutil.copytree(destination, output)
