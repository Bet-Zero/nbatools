"""Fixed six-game retained-source package; preparation never authorizes publication."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE_MANIFEST = "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
PDF_GAMES = {"0022500019", "0022500113", "0022500122"}
APPEND_PATHS = (
    "raw/player_game_availability/2025-26_regular_season.csv",
    "raw/player_game_availability/2025-26_regular_season.imports.json",
)


def main() -> None:
    directory = Path(__file__).resolve().parent
    inventory_path = directory / "retained-k08-availability-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    policy = inventory.get("append_only", {})
    if inventory.get("base_manifest_sha256") != BASE_MANIFEST or set(policy) != set(APPEND_PATHS):
        raise ValueError("Retained K08 package differs from the fixed base/append scope")
    for path, count in zip(APPEND_PATHS, (104, 3)):
        if (
            set(policy[path]["added_game_ids"]) != PDF_GAMES
            or policy[path]["added_records"] != count
        ):
            raise ValueError("Retained K08 append game/record scope changed")
    spec = importlib.util.spec_from_file_location(
        "reviewed_availability_publisher", directory / "publish-opening-availability.py"
    )
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    publisher.main(
        inventory_path=inventory_path,
        default_generation="availability-k08-retained-v1-20261031",
        append_only_paths=APPEND_PATHS,
    )


if __name__ == "__main__":
    main()
