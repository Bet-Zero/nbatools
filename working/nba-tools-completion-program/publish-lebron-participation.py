"""Fixed 17-game participation overlay; preparation is not publication approval."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

BASE_GENERATION = "availability-k08-retained-v1-20261031"
BASE_MANIFEST = "de83522f37f6bd7f26b51c1bf869deb05bbe242d3249d685997a979c050d16a9"
GENERATION = "availability-lebron-season-v1-20261031"
GAMES = {
    "0022500136",
    "0022500024",
    "0022500155",
    "0022500163",
    "0022500179",
    "0022500185",
    "0022500198",
    "0022500222",
    "0022500045",
    "0022500231",
    "0022500308",
    "0022500523",
    "0022500774",
    "0022500914",
    "0022500922",
    "0022500946",
    "0022501155",
}
APPEND_PATHS = (
    "raw/player_game_availability/2025-26_regular_season.csv",
    "raw/player_game_availability/2025-26_regular_season.imports.json",
)
_BINDING_FIELDS = {"base_sha256", "base_size_bytes", "added_game_ids", "added_records"}


def main() -> None:
    directory = Path(__file__).resolve().parent
    inventory_path = directory / "lebron-participation-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    policy = inventory.get("append_only")
    if (
        inventory.get("base_generation") != BASE_GENERATION
        or inventory.get("base_manifest_sha256") != BASE_MANIFEST
        or not isinstance(policy, dict)
        or set(policy) != set(APPEND_PATHS)
    ):
        raise ValueError("Participation package differs from the fixed base/append scope")
    for path, count in zip(APPEND_PATHS, (598, 17)):
        entry = policy[path]
        if (
            not isinstance(entry, dict)
            or set(entry) != _BINDING_FIELDS
            or not isinstance(entry["base_sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", entry["base_sha256"])
            or type(entry["base_size_bytes"]) is not int
            or entry["base_size_bytes"] <= 0
            or not isinstance(entry["added_game_ids"], list)
            or not all(isinstance(game, str) for game in entry["added_game_ids"])
            or len(entry["added_game_ids"]) != len(GAMES)
            or set(entry["added_game_ids"]) != GAMES
            or type(entry["added_records"]) is not int
            or entry["added_records"] != count
        ):
            raise ValueError("Participation append binding/game/record scope changed")
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
