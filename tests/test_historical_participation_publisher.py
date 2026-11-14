"""The fixed historical wrapper preserves the reviewed publication scope before delegation."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.engine
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"


@pytest.fixture
def wrapper(tmp_path):
    script = tmp_path / "publish-historical-participation.py"
    shutil.copy2(PROGRAM / script.name, script)
    spec = importlib.util.spec_from_file_location("fixed_historical_publisher", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = dict(
        base_generation=module.BASE_GENERATION,
        base_manifest_sha256=module.BASE_MANIFEST,
        append_only={
            path: dict(
                base_sha256="a" * 64,
                base_size_bytes=100,
                added_game_ids=sorted(module.APPEND_GAMES),
                added_records=count,
            )
            for path, count in zip(module.APPEND_PATHS, module.APPEND_COUNTS)
        },
        manifest_absent_creations={
            path: dict(
                base_presence="manifest_absent",
                added_game_ids=sorted(module.CREATED_GAMES),
                added_records=count,
            )
            for path, count in zip(module.CREATED_PATHS, module.CREATED_COUNTS)
        },
        files=[
            dict(path=p)
            for p in (
                *module.APPEND_PATHS,
                *module.CREATED_PATHS,
                "raw/player_game_availability_sources/" + "c" * 64 + ".json",
                "validation.json",
            )
        ],
    )
    return module, tmp_path / "historical-participation-inventory.json", inventory


def test_fixed_scope_matches_the_accepted_stage(wrapper):
    module = wrapper[0]
    assert len(module.APPEND_GAMES) == 15 and len(module.CREATED_GAMES) == 10
    assert all(g.startswith("00223") for g in module.APPEND_GAMES)
    assert all(g.startswith("00224") for g in module.CREATED_GAMES)
    accepted = json.loads(
        (PROGRAM / "source-evidence/k08-direct-dependencies/staging-acceptance.json").read_text()
    )["validation"]
    assert accepted["base_manifest_sha256"] == module.BASE_MANIFEST
    assert accepted["base_generation"] == module.BASE_GENERATION
    for paths, counts, games, key in (
        (module.APPEND_PATHS, module.APPEND_COUNTS, module.APPEND_GAMES, "append_only"),
        (
            module.CREATED_PATHS,
            module.CREATED_COUNTS,
            module.CREATED_GAMES,
            "manifest_absent_creations",
        ),
    ):
        for path, count in zip(paths, counts):
            assert accepted[key][path]["added_records"] == count
            assert set(accepted[key][path]["added_game_ids"]) == games


def test_fixed_wrapper_delegates_to_unchanged_publisher_with_bound_scope(wrapper, monkeypatch):
    module, path, inventory = wrapper
    path.write_text(json.dumps(inventory))
    calls, loaded = [], []
    spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda publisher: None))
    monkeypatch.setattr(
        module.importlib.util,
        "spec_from_file_location",
        lambda name, source: loaded.append(source) or spec,
    )
    monkeypatch.setattr(
        module.importlib.util,
        "module_from_spec",
        lambda spec: SimpleNamespace(main=lambda **kwargs: calls.append(kwargs)),
    )
    module.main()
    assert loaded == [path.parent / "publish-opening-availability.py"]
    assert calls == [
        dict(
            inventory_path=path,
            default_generation="availability-historical-participation-v1-20261114",
            append_only_paths=module.APPEND_PATHS,
        )
    ]


@pytest.mark.parametrize(
    "damage",
    [
        "missing_inventory",
        "generation",
        "manifest",
        "paths",
        "games",
        "duplicate_game",
        "rows",
        "ledger",
        "partial",
        "bad_hash",
        "bad_size",
        "extra_metadata",
        "created_present",
        "created_rows",
        "created_games",
        "missing_creation",
        "foreign_file",
        "missing_validation",
        "foreign_root_file",
    ],
)
def test_changed_or_partial_publication_metadata_stops_before_delegation(wrapper, damage):
    module, path, inventory = wrapper
    first = inventory["append_only"][module.APPEND_PATHS[0]]
    created = inventory["manifest_absent_creations"][module.CREATED_PATHS[0]]
    if damage == "generation":
        inventory["base_generation"] = "another-base"
    elif damage == "manifest":
        inventory["base_manifest_sha256"] = "b" * 64
    elif damage == "paths":
        inventory["append_only"]["raw/other.csv"] = first.copy()
    elif damage == "games":
        first["added_game_ids"][0] = "0022300002"
    elif damage == "duplicate_game":
        first["added_game_ids"].append(first["added_game_ids"][0])
    elif damage == "rows":
        first["added_records"] = 530
    elif damage == "ledger":
        inventory["append_only"][module.APPEND_PATHS[1]]["added_records"] = 16
    elif damage == "partial":
        del first["base_sha256"]
    elif damage == "bad_hash":
        first["base_sha256"] = "unqualified"
    elif damage == "bad_size":
        first["base_size_bytes"] = 0
    elif damage == "extra_metadata":
        first["allow_replace"] = True
    elif damage == "created_present":
        created["base_presence"] = "present"
    elif damage == "created_rows":
        created["added_records"] = 348
    elif damage == "created_games":
        created["added_game_ids"][0] = "0022400001"
    elif damage == "missing_creation":
        del inventory["manifest_absent_creations"][module.CREATED_PATHS[1]]
    elif damage == "foreign_file":
        inventory["files"].append(dict(path="raw/player_game_stats/2023-24_regular_season.csv"))
    elif damage == "missing_validation":
        inventory["files"].remove(dict(path="validation.json"))
    elif damage == "foreign_root_file":
        inventory["files"].append(dict(path="consumer-acceptance.json"))
    if damage != "missing_inventory":
        path.write_text(json.dumps(inventory))
    # No delegated script exists. A valid wrapper would reach FileNotFoundError
    # there; all malformed inputs must fail their own scope check first.
    with pytest.raises(FileNotFoundError if damage == "missing_inventory" else ValueError):
        module.main()


def test_producer_transport_layout_passes_the_real_overlay_check(wrapper, tmp_path):
    """The producer exports raw/ plus validation.json; the delegated check accepts it."""
    module = wrapper[0]
    spec = importlib.util.spec_from_file_location(
        "reviewed_publisher", PROGRAM / "publish-opening-availability.py"
    )
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    root = tmp_path / "acquired_data"
    paths = [*module.APPEND_PATHS, *module.CREATED_PATHS]
    paths.append("raw/player_game_availability_sources/" + "c" * 64 + ".json")
    for relative in paths:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(relative)
    request = "d" * 40
    (root / "validation.json").write_text(
        json.dumps(dict(candidate_sha=request, base_generation=module.BASE_GENERATION))
    )
    files = [
        dict(
            path=p.relative_to(root).as_posix(),
            size_bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]
    inventory = dict(request_sha=request, base_generation=module.BASE_GENERATION, files=files)
    items = publisher.verify_overlay(root, inventory)
    assert sorted(item["path"] for item in items) == sorted(paths)
    # The wrapper's file-scope rule accepts exactly this listing.
    listed = {item["path"] for item in files}
    assert listed - {"validation.json"} == set(paths) and "validation.json" in listed
