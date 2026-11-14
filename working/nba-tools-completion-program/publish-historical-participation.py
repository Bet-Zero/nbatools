"""Fixed historical participation overlay; preparation is not publication approval.

Appends 15 qualified 2023-24 Lakers games to the existing 2023-24 table and creates
the 2024-25 table with 10 qualified Boston games. Everything else is unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

BASE_GENERATION = "availability-lebron-season-v1-20261031"
BASE_MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
GENERATION = "availability-historical-participation-v1-20261114"
APPEND_GAMES = {
    "0022300163",
    "0022300187",
    "0022300316",
    "0022300331",
    "0022300380",
    "0022300549",
    "0022300618",
    "0022300669",
    "0022300788",
    "0022300802",
    "0022300915",
    "0022301045",
    "0022301055",
    "0022301143",
    "0022301155",
}
CREATED_GAMES = {
    "0022400319",
    "0022400393",
    "0022400891",
    "0022400929",
    "0022400994",
    "0022401058",
    "0022401137",
    "0022401156",
    "0022401187",
    "0022401205",
}
APPEND_PATHS = (
    "raw/player_game_availability/2023-24_regular_season.csv",
    "raw/player_game_availability/2023-24_regular_season.imports.json",
)
CREATED_PATHS = (
    "raw/player_game_availability/2024-25_regular_season.csv",
    "raw/player_game_availability/2024-25_regular_season.imports.json",
)
APPEND_COUNTS = (529, 15)
CREATED_COUNTS = (347, 10)
_BINDING_FIELDS = {"base_sha256", "base_size_bytes", "added_game_ids", "added_records"}
_CREATED_FIELDS = {"base_presence", "added_game_ids", "added_records"}


def _games(entry, expected):
    games = entry.get("added_game_ids")
    return (
        isinstance(games, list)
        and all(isinstance(game, str) for game in games)
        and len(games) == len(expected)
        and set(games) == expected
    )


def main() -> None:
    directory = Path(__file__).resolve().parent
    inventory_path = directory / "historical-participation-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    append, created = inventory.get("append_only"), inventory.get("manifest_absent_creations")
    if (
        inventory.get("base_generation") != BASE_GENERATION
        or inventory.get("base_manifest_sha256") != BASE_MANIFEST
        or not isinstance(append, dict)
        or set(append) != set(APPEND_PATHS)
        or not isinstance(created, dict)
        or set(created) != set(CREATED_PATHS)
    ):
        raise ValueError("Historical package differs from the fixed base/append/creation scope")
    for path, count in zip(APPEND_PATHS, APPEND_COUNTS):
        entry = append[path]
        if (
            not isinstance(entry, dict)
            or set(entry) != _BINDING_FIELDS
            or not isinstance(entry["base_sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", entry["base_sha256"])
            or type(entry["base_size_bytes"]) is not int
            or entry["base_size_bytes"] <= 0
            or not _games(entry, APPEND_GAMES)
            or type(entry["added_records"]) is not int
            or entry["added_records"] != count
        ):
            raise ValueError("Historical append binding/game/record scope changed")
    for path, count in zip(CREATED_PATHS, CREATED_COUNTS):
        entry = created[path]
        if (
            not isinstance(entry, dict)
            or set(entry) != _CREATED_FIELDS
            or entry["base_presence"] != "manifest_absent"
            or not _games(entry, CREATED_GAMES)
            or type(entry["added_records"]) is not int
            or entry["added_records"] != count
        ):
            raise ValueError("Historical creation binding/game/record scope changed")
    files = {item.get("path") for item in inventory.get("files", [])}
    tables = {p for p in files if p.startswith("raw/player_game_availability/")}
    # validation.json is the stage provenance the delegated publisher reads; it
    # is not copied as data because only raw/ items are published.
    data = files - {"validation.json"}
    if (
        "validation.json" not in files
        or tables != set(APPEND_PATHS) | set(CREATED_PATHS)
        or not all(
            isinstance(p, str) and p.startswith("raw/player_game_availability") for p in data
        )
    ):
        raise ValueError("Historical overlay contains files outside the reviewed scope")
    spec = importlib.util.spec_from_file_location(
        "reviewed_availability_publisher", directory / "publish-opening-availability.py"
    )
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    publisher.main(
        inventory_path=inventory_path,
        default_generation=GENERATION,
        append_only_paths=APPEND_PATHS,
    )


if __name__ == "__main__":
    main()
