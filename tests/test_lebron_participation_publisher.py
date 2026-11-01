"""The fixed wrapper preserves the reviewed publication scope before delegation."""

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
    script = tmp_path / "publish-lebron-participation.py"
    shutil.copy2(PROGRAM / script.name, script)
    spec = importlib.util.spec_from_file_location("fixed_participation_publisher", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = dict(
        base_generation=module.BASE_GENERATION,
        base_manifest_sha256=module.BASE_MANIFEST,
        append_only={
            path: dict(
                base_sha256="a" * 64,
                base_size_bytes=100,
                added_game_ids=sorted(module.GAMES),
                added_records=count,
            )
            for path, count in zip(module.APPEND_PATHS, (598, 17))
        },
    )
    return module, tmp_path / "lebron-participation-inventory.json", inventory


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
            default_generation="availability-lebron-season-v1-20261031",
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
    ],
)
def test_changed_or_partial_publication_metadata_stops_before_delegation(wrapper, damage):
    module, path, inventory = wrapper
    first = inventory["append_only"][module.APPEND_PATHS[0]]
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
        first["added_records"] = 599
    elif damage == "ledger":
        inventory["append_only"][module.APPEND_PATHS[1]]["added_records"] = 18
    elif damage == "partial":
        del first["base_sha256"]
    elif damage == "bad_hash":
        first["base_sha256"] = "unqualified"
    elif damage == "bad_size":
        first["base_size_bytes"] = 0
    elif damage == "extra_metadata":
        first["allow_replace"] = True
    if damage != "missing_inventory":
        path.write_text(json.dumps(inventory))
    # No delegated script exists. A valid wrapper would reach FileNotFoundError
    # there; all malformed inputs must fail their own scope check first.
    with pytest.raises(FileNotFoundError if damage == "missing_inventory" else ValueError):
        module.main()
