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
from tools import stage_participation_collection as builder
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


def multiple_targets(collection, ids=(11, 13)):
    path = collection[0]
    request = json.loads(path.read_text())
    first = request["requirements"][0]
    names = {11: "A Player", 13: "Inactive Player"}
    request["requirements"] = [
        dict(
            copy.deepcopy(first),
            player_id=pid,
            player_name=names.get(pid, "Unlisted Player"),
            prior_state="unknown",
        )
        for pid in ids
    ]
    path.write_text(json.dumps(request))
    return request


def stage_calls(monkeypatch):
    calls = []
    original = builder.stage_structured_game

    def stage(*args, **kwargs):
        calls.append(kwargs["game_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(builder, "stage_structured_game", stage)
    return calls


def metadata(collection, request):
    provenance = json.loads((collection[1] / "sources.json").read_text())
    index = {}
    for row in request["requirements"]:
        for item in row["proposed_sources"]:
            filename = f"{item['endpoint']}_{row['game_id']}.json"
            original = provenance["files"][filename]
            item.update(git_blob_sha=original["git_blob_sha"], size_bytes=original["size_bytes"])
            index[filename] = dict(item, game_id=row["game_id"], source_tree_sha="e" * 40)
    request["source_files"] = index
    collection[0].write_text(json.dumps(request))


def test_multiple_unknown_targets_share_one_source_normalization(collection, monkeypatch):
    request = multiple_targets(collection)
    # Source order does not change the pair's identity.
    request["requirements"][1]["proposed_sources"].reverse()
    metadata(collection, request)
    calls = stage_calls(monkeypatch)
    result = run(collection)
    assert calls == [22500002]
    assert result["requested_game_count"] == 1 and result["requested_target_count"] == 2
    assert [(row["player_id"], row["state"]) for row in result["qualified_targets"]] == [
        (11, "played"),
        (13, "did_not_play"),
    ]
    assert result["append_only"]["raw/player_game_availability/" + SUFFIX]["added_records"] == 4
    assert (
        result["append_only"][
            "raw/player_game_availability/" + SUFFIX.removesuffix(".csv") + ".imports.json"
        ]["added_records"]
        == 1
    )
    assert len(result["input_hashes"]) == 4


@pytest.mark.parametrize(
    "damage",
    [
        "missing_second",
        "wrong_side",
        "duplicate",
        "conflicting_side",
        "date",
        "source",
        "name",
        "prior_dnp",
    ],
)
def test_no_second_target_is_ignored_or_inferred_from_the_first(collection, monkeypatch, damage):
    request = multiple_targets(collection)
    second = request["requirements"][1]
    if damage == "missing_second":
        second["player_id"] = 999
    elif damage == "wrong_side":
        second["team_id"] = 2
    elif damage == "duplicate":
        second.update(player_id=11, player_name="A Player")
    elif damage == "conflicting_side":
        second.update(player_id=11, team_id=2)
    elif damage == "date":
        second["game_date"] = "2025-10-22"
    elif damage == "source":
        second["proposed_sources"][0]["url"] += "?different"
    elif damage == "name":
        second["player_name"] = "A Player"
    elif damage == "prior_dnp":
        second["prior_state"] = "did_not_play"
    collection[0].write_text(json.dumps(request))
    calls = stage_calls(monkeypatch)
    with pytest.raises(ValueError):
        run(collection)
    assert not collection[3].exists()
    if damage in {"duplicate", "conflicting_side", "date", "source", "prior_dnp"}:
        assert calls == [] and not collection[2].exists()
    else:
        assert calls == [22500002]


@pytest.mark.parametrize(
    "damage",
    [
        "proposed_blob",
        "index_size",
        "missing_metadata",
        "extra_metadata",
        "self_consistent_rewrite",
    ],
)
def test_audited_original_metadata_cannot_be_replaced_by_new_self_consistent_hashes(
    collection, damage
):
    request = multiple_targets(collection)
    metadata(collection, request)
    name = next(iter(request["source_files"]))
    if damage == "proposed_blob":
        for target in request["requirements"]:
            next(
                row
                for row in target["proposed_sources"]
                if row["endpoint"] == "boxscoretraditionalv3"
            )["git_blob_sha"] = "0" * 40
    elif damage == "index_size":
        request["source_files"][name]["size_bytes"] += 1
    elif damage == "missing_metadata":
        request["source_files"].pop(name)
    elif damage == "extra_metadata":
        request["source_files"]["extra.json"] = {}
    else:
        path = collection[1] / "sources" / name
        raw = path.read_bytes() + b"\n"
        path.write_bytes(raw)
        provenance_path = collection[1] / "sources.json"
        provenance = json.loads(provenance_path.read_text())
        provenance["files"][name].update(
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            git_blob_sha=hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
        )
        provenance_path.write_text(json.dumps(provenance))
    collection[0].write_text(json.dumps(request))
    with pytest.raises(ValueError):
        run(collection)
    assert not collection[3].exists()


def test_multiple_game_groups_append_once_and_preserve_existing_cells_and_sources(
    collection, monkeypatch
):
    request = multiple_targets(collection)
    request_path, retained, work, output, served = collection
    for dataset in ["games", "team_game_stats", "player_game_stats"]:
        path = served / "raw" / dataset / SUFFIX
        rows = pd.read_csv(path)
        extra = rows.loc[rows.game_id.eq(22500002)].assign(game_id=22500003, game_date="2025-10-22")
        pd.concat([rows, extra], ignore_index=True).to_csv(path, index=False)
    provenance = json.loads((retained / "sources.json").read_text())
    extra_targets = copy.deepcopy(request["requirements"])
    for target in extra_targets:
        target.update(game_id="0022500003", game_date="2025-10-22")
        for proposed in target["proposed_sources"]:
            proposed["url"] = proposed["url"].replace("0022500002", "0022500003")
    for endpoint in ["boxscoretraditionalv3", "boxscoresummaryv2"]:
        name = f"{endpoint}_0022500002.json"
        document = json.loads((retained / "sources" / name).read_text())
        if endpoint == "boxscoretraditionalv3":
            document["boxScoreTraditional"]["gameId"] = "0022500003"
        else:
            for table in document["resultSets"]:
                for row in table["rowSet"]:
                    if "GAME_ID" in table["headers"]:
                        row[table["headers"].index("GAME_ID")] = "0022500003"
                    if "GAME_DATE_EST" in table["headers"]:
                        row[table["headers"].index("GAME_DATE_EST")] = "2025-10-22"
        raw = json.dumps(document).encode()
        name = f"{endpoint}_0022500003.json"
        (retained / "sources" / name).write_bytes(raw)
        provenance["files"][name] = dict(
            provenance["files"][name.replace("0003", "0002")],
            url=next(
                p["url"] for p in extra_targets[0]["proposed_sources"] if p["endpoint"] == endpoint
            ),
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            git_blob_sha=hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
        )
    (retained / "sources.json").write_text(json.dumps(provenance))
    # Deliberately interleave scalar records to test grouping rather than adjacency.
    request["requirements"] = [
        request["requirements"][0],
        extra_targets[0],
        request["requirements"][1],
        extra_targets[1],
    ]
    manifest_path = served / "metadata/generation_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        raw = (served / entry["path"]).read_bytes()
        entry.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(raw)
    request["base_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    metadata(collection, request)
    reset_data_source_cache()
    baseline = {
        path.relative_to(served).as_posix(): path.read_bytes()
        for path in served.rglob("*")
        if path.is_file()
    }
    calls = stage_calls(monkeypatch)
    result = run(collection)
    assert calls == [22500002, 22500003]
    assert result["requested_game_count"] == 2 and result["requested_target_count"] == 4
    assert {(row["game_id"], row["player_id"]) for row in result["qualified_targets"]} == {
        (gid, pid) for gid in ["0022500002", "0022500003"] for pid in [11, 13]
    }
    relative = "raw/player_game_availability/" + SUFFIX
    assert result["append_only"][relative]["added_records"] == 8
    assert (
        result["append_only"][relative.removesuffix(".csv") + ".imports.json"]["added_records"] == 2
    )
    old = list(csv.DictReader(baseline[relative].decode().splitlines()))
    staged = list(csv.DictReader((work / "data" / relative).read_text().splitlines()))
    assert staged[: len(old)] == old
    assert {
        p.relative_to(served).as_posix(): p.read_bytes() for p in served.rglob("*") if p.is_file()
    } == baseline
    for path, raw in baseline.items():
        if path.startswith("raw/player_game_availability_sources/"):
            assert (work / "data" / path).read_bytes() == raw
