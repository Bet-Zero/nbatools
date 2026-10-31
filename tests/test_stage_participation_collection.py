"""Retained-source staging preserves its base and never grants publication."""

import copy
import csv
import hashlib
import json
import shutil

import pandas as pd
import pytest

from nbatools.commands.pipeline.structured_participation import ARCHIVE, stage_structured_game
from nbatools.data_source import reset_data_source_cache
from tests.test_structured_participation import REV, source  # noqa: F401
from tools.stage_participation_collection import build_stage

pytestmark = pytest.mark.engine
SUFFIX = "2025-26_regular_season.csv"


@pytest.fixture
def collection(source, tmp_path, monkeypatch):  # noqa: F811 - reuse the existing pytest fixture
    root, traditional, summary, trad, summ = source
    for dataset in ["games", "team_game_stats", "player_game_stats"]:
        path = root / "raw" / dataset / SUFFIX
        current = pd.read_csv(path)
        old = current.assign(game_id=22500001)
        if "game_date" in old:
            old["game_date"] = "2025-10-20"
        pd.concat([old, current], ignore_index=True).to_csv(path, index=False)
    old_trad, old_summ = copy.deepcopy(trad), copy.deepcopy(summ)
    old_trad["boxScoreTraditional"]["gameId"] = "0022500001"
    for table in old_summ["resultSets"]:
        for row in table["rowSet"]:
            if "GAME_ID" in table["headers"]:
                row[table["headers"].index("GAME_ID")] = "0022500001"
            if "GAME_DATE_EST" in table["headers"]:
                row[table["headers"].index("GAME_DATE_EST")] = "2025-10-20"
    traditional.write_text(json.dumps(old_trad))
    summary.write_text(json.dumps(old_summ))
    stage_structured_game(
        root,
        season="2025-26",
        season_type="Regular Season",
        game_id=22500001,
        traditional=traditional,
        summary=summary,
        summary_version=2,
        revision=REV,
        retrieved_at="2026-10-31T12:00:00Z",
    )
    # Preserve equivalent serialized precision rather than a pandas round trip.
    baseline_csv = root / "raw/player_game_availability" / SUFFIX
    raw = baseline_csv.read_text().replace(",10.0,", ",10.0000000000000,")
    baseline_csv.write_text(raw)
    identity = root / "metadata/player_names.csv"
    identity.parent.mkdir(parents=True)
    identity.write_text(
        "player_id,player_name,season,first_seen\n11,A Player,2025-26,0\n21,B Player,2025-26,1\n"
    )
    served = tmp_path / "served/data/generations/base-fixture"
    shutil.copytree(root, served)
    entries = []
    for file in sorted(served.rglob("*")):
        if file.is_file():
            raw = file.read_bytes()
            entries.append(
                dict(
                    path=file.relative_to(served).as_posix(),
                    size_bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
    manifest_raw = json.dumps(dict(generation_id="base-fixture", files=entries)).encode()
    (served / "metadata/generation_manifest.json").write_bytes(manifest_raw)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path / "served"))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "base-fixture")
    reset_data_source_cache()
    retained = tmp_path / "retained"
    (retained / "sources").mkdir(parents=True)
    proposed, records = [], {}
    for endpoint, document in [("boxscoretraditionalv3", trad), ("boxscoresummaryv2", summ)]:
        filename = f"{endpoint}_0022500002.json"
        raw = json.dumps(document).encode()
        (retained / "sources" / filename).write_bytes(raw)
        url = f"{ARCHIVE}/{REV}/nba_stats/json/{endpoint}/2026/0022500002.json"
        proposed.append(dict(endpoint=endpoint, revision=REV, url=url))
        records[filename] = dict(
            url=url,
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            git_blob_sha=hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
            retrieved_at="2026-10-31T13:00:00Z",
        )
    provenance = dict(repository="sportsdataverse/hoopR-nba-stats-raw", revision=REV, files=records)
    (retained / "sources.json").write_text(json.dumps(provenance))
    request = dict(
        schema_version=1,
        dataset="raw/player_game_availability",
        season="2025-26",
        season_type="Regular Season",
        base_generation="base-fixture",
        base_manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        requirements=[
            dict(
                game_id="0022500002",
                game_date="2025-10-21",
                team_id=1,
                player_id=13,
                proposed_sources=proposed,
            )
        ],
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request))
    yield request_path, retained, tmp_path / "work", tmp_path / "overlay", served
    reset_data_source_cache()


def run(collection):
    request, retained, work, output, _ = collection
    return build_stage(request, retained, work, output, candidate_sha="c" * 40)


def test_originals_qualify_append_and_only_overlay_is_exported(collection):
    request, retained, work, output, served = collection
    baseline = {
        file.relative_to(served).as_posix(): file.read_bytes()
        for file in served.rglob("*")
        if file.is_file()
    }
    result = run(collection)
    assert result["qualified_targets"] == [
        dict(
            game_id="0022500002",
            game_date="2025-10-21",
            team_id=1,
            player_id=13,
            state="did_not_play",
        )
    ]
    assert result["publication_state"] == "staged_only_no_writes"
    assert result["append_only"]["raw/player_game_availability/" + SUFFIX]["added_records"] == 4
    assert {
        file.relative_to(served).as_posix(): file.read_bytes()
        for file in served.rglob("*")
        if file.is_file()
    } == baseline
    for relative, raw in baseline.items():
        if relative.startswith("raw/player_game_availability_sources/"):
            assert (work / "data" / relative).read_bytes() == raw
    path = "raw/player_game_availability/" + SUFFIX
    old = list(csv.DictReader(baseline[path].decode().splitlines()))
    staged = list(csv.DictReader((work / "data" / path).read_text().splitlines()))
    assert staged[: len(old)] == old
    assert json.loads((output / "validation.json").read_text()) == result
    files = {file.relative_to(output).as_posix() for file in output.rglob("*") if file.is_file()}
    assert files == {"validation.json", *(item["path"] for item in result["overlay_files"])}
    assert not any("metadata/" in path or "game_stats/" in path for path in files)
    assert len(result["input_hashes"]) == 4
    assert result["input_hashes"]["request"] == hashlib.sha256(request.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "damage",
    [
        "source_bytes",
        "blob",
        "url",
        "capture_time",
        "extra_source",
        "target",
        "date",
        "base",
        "manifest",
        "canonical",
        "existing_game",
    ],
)
def test_unqualified_collection_or_base_cannot_export(collection, damage):
    request_path, retained, _, output, served = collection
    request = json.loads(request_path.read_text())
    if damage == "source_bytes":
        next((retained / "sources").iterdir()).write_text("changed")
    elif damage in ["blob", "url", "capture_time"]:
        path = retained / "sources.json"
        provenance = json.loads(path.read_text())
        first = next(iter(provenance["files"].values()))
        field = {"blob": "git_blob_sha", "url": "url", "capture_time": "retrieved_at"}[damage]
        first[field] = "2026-10-31T13:00:00" if damage == "capture_time" else "bad"
        path.write_text(json.dumps(provenance))
    elif damage == "extra_source":
        (retained / "sources/extra.json").write_text("{}")
    elif damage == "target":
        request["requirements"][0]["player_id"] = 999
    elif damage == "date":
        request["requirements"][0]["game_date"] = "2025-10-22"
    elif damage == "base":
        request["base_generation"] = "another-generation"
    elif damage == "manifest":
        request["base_manifest_sha256"] = "f" * 64
    elif damage == "canonical":
        (served / "raw/player_game_stats" / SUFFIX).write_text("changed")
    elif damage == "existing_game":
        path = served / "raw/player_game_availability" / SUFFIX
        # Bind a modified baseline to isolate replacement from byte-integrity checks.
        rows = pd.read_csv(path).assign(game_id=22500002, game_date="2025-10-21")
        rows.to_csv(path, index=False)
        manifest_path = served / "metadata/generation_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for item in manifest["files"]:
            if item["path"] == path.relative_to(served).as_posix():
                item.update(
                    size_bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                )
        raw = json.dumps(manifest).encode()
        manifest_path.write_bytes(raw)
        request["base_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    request_path.write_text(json.dumps(request))
    with pytest.raises((ValueError, KeyError)):
        run(collection)
    assert not (output / "validation.json").exists()
