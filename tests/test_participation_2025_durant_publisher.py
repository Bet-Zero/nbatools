"""The fixed 2025-26 + Durant wrapper preserves the reviewed scope before delegation."""

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
    script = tmp_path / "publish-participation-2025-durant.py"
    shutil.copy2(PROGRAM / script.name, script)
    spec = importlib.util.spec_from_file_location("fixed_2025_durant_publisher", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    created = {
        path: dict(
            base_presence="manifest_absent",
            added_observation_keys=sorted(module.REASON_KEYS),
            added_records=count,
        )
        for path, count in zip(module.REASON_PATHS, module.REASON_COUNTS)
    }
    created |= {
        path: dict(
            base_presence="manifest_absent",
            added_game_ids=sorted(module.DURANT_GAMES),
            added_records=count,
        )
        for path, count in zip(module.DURANT_PATHS, module.DURANT_COUNTS)
    }
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
        manifest_absent_creations=created,
        files=[
            dict(path=p)
            for p in (
                *module.APPEND_PATHS,
                *module.REASON_PATHS,
                *module.DURANT_PATHS,
                "raw/player_game_availability_sources/" + "c" * 64 + ".json",
                "raw/player_game_absence_reason_sources/" + "d" * 64 + ".pdf",
                "validation.json",
            )
        ],
    )
    return module, tmp_path / "participation-2025-durant-inventory.json", inventory


def test_fixed_scope_matches_the_reviewed_inventory(wrapper):
    module = wrapper[0]
    assert len(module.APPEND_GAMES) == 98 and len(module.REASON_KEYS) == 18
    assert all(g.startswith("00225") for g in module.APPEND_GAMES)
    assert all(
        k.startswith("225") and k.endswith(":1610612747:1629029") for k in module.REASON_KEYS
    )
    assert module.DURANT_GAMES and all(g.startswith("00207") for g in module.DURANT_GAMES)
    inventory = json.loads((PROGRAM / "participation-2025-durant-inventory.json").read_text())
    assert inventory["base_generation"] == module.BASE_GENERATION
    assert inventory["base_manifest_sha256"] == module.BASE_MANIFEST
    for path, count in zip(module.APPEND_PATHS, module.APPEND_COUNTS):
        entry = inventory["append_only"][path]
        assert (
            entry["added_records"] == count and set(entry["added_game_ids"]) == module.APPEND_GAMES
        )
    for paths, counts, field, expected in (
        (module.REASON_PATHS, module.REASON_COUNTS, "added_observation_keys", module.REASON_KEYS),
        (module.DURANT_PATHS, module.DURANT_COUNTS, "added_game_ids", module.DURANT_GAMES),
    ):
        for path, count in zip(paths, counts):
            entry = inventory["manifest_absent_creations"][path]
            assert entry["added_records"] == count and set(entry[field]) == expected


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
            default_generation="availability-participation-2025-durant-v1-20261114",
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
        "partial",
        "bad_hash",
        "extra_metadata",
        "reason_present",
        "reason_keys",
        "reason_rows",
        "durant_games",
        "durant_rows",
        "missing_creation",
        "foreign_file",
        "missing_validation",
        "foreign_root_file",
    ],
)
def test_changed_or_partial_publication_metadata_stops_before_delegation(wrapper, damage):
    module, path, inventory = wrapper
    first = inventory["append_only"][module.APPEND_PATHS[0]]
    reason = inventory["manifest_absent_creations"][module.REASON_PATHS[0]]
    durant = inventory["manifest_absent_creations"][module.DURANT_PATHS[0]]
    if damage == "generation":
        inventory["base_generation"] = "another-base"
    elif damage == "manifest":
        inventory["base_manifest_sha256"] = "b" * 64
    elif damage == "paths":
        inventory["append_only"]["raw/other.csv"] = first.copy()
    elif damage == "games":
        first["added_game_ids"][0] = "0022500002"
    elif damage == "duplicate_game":
        first["added_game_ids"].append(first["added_game_ids"][0])
    elif damage == "rows":
        first["added_records"] += 1
    elif damage == "partial":
        del first["base_sha256"]
    elif damage == "bad_hash":
        first["base_sha256"] = "unqualified"
    elif damage == "extra_metadata":
        first["allow_replace"] = True
    elif damage == "reason_present":
        reason["base_presence"] = "present"
    elif damage == "reason_keys":
        reason["added_observation_keys"][0] = "22500001:1610612747:1629029"
    elif damage == "reason_rows":
        reason["added_records"] += 1
    elif damage == "durant_games":
        durant["added_game_ids"][0] = "0020700001"
    elif damage == "durant_rows":
        durant["added_records"] += 1
    elif damage == "missing_creation":
        del inventory["manifest_absent_creations"][module.DURANT_PATHS[1]]
    elif damage == "foreign_file":
        inventory["files"].append(dict(path="raw/player_game_stats/2025-26_regular_season.csv"))
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
