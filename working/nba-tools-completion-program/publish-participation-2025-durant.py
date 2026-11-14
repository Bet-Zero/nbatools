"""Fixed 2025-26 LAL/BOS participation plus Durant 2007-08; preparation is not approval.

Appends 98 qualified 2025-26 games to the existing 2025-26 availability table,
creates the 2025-26 reported-absence-reason table (18 rows) and creates the
2007-08 availability table with the 2 qualified Seattle games Durant missed.
Base is the live historical-participation-v1 generation. Everything else is unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

BASE_GENERATION = "availability-historical-participation-v1-20261114"
BASE_MANIFEST = "be0940172453b76cd81f636d3f27c8bd3e0f428dcb35be5c1b01c4aa6af74a58"
GENERATION = "availability-participation-2025-durant-v1-20261114"
APPEND_GAMES = {
    "0022500017",
    "0022500018",
    "0022500021",
    "0022500028",
    "0022500049",
    "0022500060",
    "0022500083",
    "0022500106",
    "0022500117",
    "0022500128",
    "0022500146",
    "0022500158",
    "0022500174",
    "0022500193",
    "0022500209",
    "0022500216",
    "0022500233",
    "0022500250",
    "0022500277",
    "0022500293",
    "0022500302",
    "0022500320",
    "0022500334",
    "0022500336",
    "0022500358",
    "0022500379",
    "0022500381",
    "0022500388",
    "0022500395",
    "0022500403",
    "0022500418",
    "0022500426",
    "0022500444",
    "0022500446",
    "0022500459",
    "0022500460",
    "0022500474",
    "0022500485",
    "0022500493",
    "0022500501",
    "0022500503",
    "0022500514",
    "0022500520",
    "0022500532",
    "0022500541",
    "0022500545",
    "0022500559",
    "0022500562",
    "0022500569",
    "0022500580",
    "0022500586",
    "0022500594",
    "0022500601",
    "0022500607",
    "0022500617",
    "0022500621",
    "0022500633",
    "0022500637",
    "0022500647",
    "0022500648",
    "0022500660",
    "0022500661",
    "0022500671",
    "0022500673",
    "0022500688",
    "0022500689",
    "0022500702",
    "0022500708",
    "0022500721",
    "0022500728",
    "0022500741",
    "0022500753",
    "0022500757",
    "0022500769",
    "0022500778",
    "0022500791",
    "0022500799",
    "0022500839",
    "0022500847",
    "0022500859",
    "0022500874",
    "0022500880",
    "0022500894",
    "0022500959",
    "0022501067",
    "0022501085",
    "0022501092",
    "0022501098",
    "0022501140",
    "0022501168",
    "0022501170",
    "0022501174",
    "0022501185",
    "0022501186",
    "0022501198",
    "0022501206",
    "0022501222",
    "0022501228",
}
REASON_KEYS = {
    "22500113:1610612747:1629029",
    "22500122:1610612747:1629029",
    "22500136:1610612747:1629029",
    "22500163:1610612747:1629029",
    "22500336:1610612747:1629029",
    "22500338:1610612747:1629029",
    "22500418:1610612747:1629029",
    "22500601:1610612747:1629029",
    "22500753:1610612747:1629029",
    "22500769:1610612747:1629029",
    "22500774:1610612747:1629029",
    "22500791:1610612747:1629029",
    "22501098:1610612747:1629029",
    "22501140:1610612747:1629029",
    "22501155:1610612747:1629029",
    "22501170:1610612747:1629029",
    "22501185:1610612747:1629029",
    "22501198:1610612747:1629029",
}
DURANT_GAMES = {
    "0020700456",
    "0020700788",
}
APPEND_PATHS = (
    "raw/player_game_availability/2025-26_regular_season.csv",
    "raw/player_game_availability/2025-26_regular_season.imports.json",
)
APPEND_COUNTS = (3272, 98)
REASON_PATHS = (
    "raw/player_game_absence_reasons/2025-26_regular_season.csv",
    "raw/player_game_absence_reasons/2025-26_regular_season.imports.json",
)
REASON_COUNTS = (18, 18)
DURANT_PATHS = (
    "raw/player_game_availability/2007-08_regular_season.csv",
    "raw/player_game_availability/2007-08_regular_season.imports.json",
)
DURANT_COUNTS = (57, 2)
DATA_PREFIXES = (
    "raw/player_game_availability/",
    "raw/player_game_availability_sources/",
    "raw/player_game_absence_reasons/",
    "raw/player_game_absence_reason_sources/",
)
_BINDING_FIELDS = {"base_sha256", "base_size_bytes", "added_game_ids", "added_records"}


def _exact(values, expected):
    return (
        isinstance(values, list)
        and all(isinstance(value, str) for value in values)
        and len(values) == len(expected)
        and set(values) == expected
    )


def _created(entry, field, expected, count):
    return (
        isinstance(entry, dict)
        and set(entry) == {"base_presence", field, "added_records"}
        and entry["base_presence"] == "manifest_absent"
        and _exact(entry[field], expected)
        and type(entry["added_records"]) is int
        and entry["added_records"] == count
    )


def main() -> None:
    directory = Path(__file__).resolve().parent
    inventory_path = directory / "participation-2025-durant-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    append, created = inventory.get("append_only"), inventory.get("manifest_absent_creations")
    if (
        inventory.get("base_generation") != BASE_GENERATION
        or inventory.get("base_manifest_sha256") != BASE_MANIFEST
        or not isinstance(append, dict)
        or set(append) != set(APPEND_PATHS)
        or not isinstance(created, dict)
        or set(created) != set(REASON_PATHS) | set(DURANT_PATHS)
    ):
        raise ValueError("Package differs from the fixed base/append/creation scope")
    for path, count in zip(APPEND_PATHS, APPEND_COUNTS):
        entry = append[path]
        if (
            not isinstance(entry, dict)
            or set(entry) != _BINDING_FIELDS
            or not isinstance(entry["base_sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", entry["base_sha256"])
            or type(entry["base_size_bytes"]) is not int
            or entry["base_size_bytes"] <= 0
            or not _exact(entry["added_game_ids"], APPEND_GAMES)
            or type(entry["added_records"]) is not int
            or entry["added_records"] != count
        ):
            raise ValueError("2025-26 append binding/game/record scope changed")
    for path, count in zip(REASON_PATHS, REASON_COUNTS):
        if not _created(created[path], "added_observation_keys", REASON_KEYS, count):
            raise ValueError("2025-26 reported-reason creation scope changed")
    for path, count in zip(DURANT_PATHS, DURANT_COUNTS):
        if not _created(created[path], "added_game_ids", DURANT_GAMES, count):
            raise ValueError("Durant 2007-08 creation scope changed")
    files = {item.get("path") for item in inventory.get("files", [])}
    tables = {
        p
        for p in files
        if p.startswith(("raw/player_game_availability/", "raw/player_game_absence_reasons/"))
    }
    # validation.json is the stage provenance the delegated publisher reads; it
    # is not copied as data because only raw/ items are published.
    data = files - {"validation.json"}
    if (
        "validation.json" not in files
        or tables != set(APPEND_PATHS) | set(REASON_PATHS) | set(DURANT_PATHS)
        or not all(isinstance(p, str) and p.startswith(DATA_PREFIXES) for p in data)
    ):
        raise ValueError("Overlay contains files outside the reviewed scope")
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
