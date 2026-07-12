import json
from pathlib import Path

import pandas as pd

from nbatools.commands.validation_control import inspect_slice_manifest

RAW_TABLE_DIRS = [
    "games",
    "schedule",
    "rosters",
    "standings_snapshots",
    "team_game_stats",
    "player_game_stats",
    "team_season_advanced",
    "player_season_advanced",
    "player_game_starter_roles",
    "player_game_period_stats",
    "team_game_period_stats",
    "play_by_play_events",
    "team_player_on_off_summary",
    "league_lineup_viz",
    "teams",
]

PROCESSED_TABLE_DIRS = [
    "team_game_features",
    "game_features",
    "schedule_context_features",
    "player_game_features",
    "league_season_stats",
    "player_game_clutch_stats",
    "team_game_clutch_stats",
]


def list_files(base: Path, subdir: str) -> list[str]:
    path = base / subdir
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_file()])


def print_section(title: str, items: list[str]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    if not items:
        print("(none)")
        return
    for item in items:
        print(item)


def extract_labels(file_names: list[str]) -> list[str]:
    labels = set()

    for name in file_names:
        if name in {"teams_reference.csv", "team_history_reference.csv"}:
            continue

        stem = name[:-4] if name.endswith(".csv") else name
        labels.add(stem)

    return sorted(labels)


def season_start(label: str) -> int | None:
    if len(label) < 7 or "-" not in label:
        return None
    try:
        return int(label[:4])
    except ValueError:
        return None


def normalize_manifest_label(season: str, season_type: str) -> str:
    safe = season_type.lower().replace(" ", "_")
    return f"{season}_{safe}"


def is_season_type_label(label: str) -> bool:
    return label.endswith("_regular_season") or label.endswith("_playoffs")


def run() -> None:
    data_dir = Path("data")
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    manifest_path = data_dir / "metadata" / "backfill_manifest.csv"
    validation_manifest_dir = data_dir / "metadata" / "dataset_manifests"

    print("NBA Tools Inventory")
    print("===================")

    raw_labels = []
    for subdir in RAW_TABLE_DIRS:
        raw_labels.extend(extract_labels(list_files(raw_dir, subdir)))
    raw_labels = sorted(set(raw_labels), key=lambda x: (season_start(x) or 9999, x))

    processed_labels = []
    for subdir in PROCESSED_TABLE_DIRS:
        processed_labels.extend(extract_labels(list_files(processed_dir, subdir)))
    processed_labels = sorted(set(processed_labels), key=lambda x: (season_start(x) or 9999, x))

    raw_season_type_labels = sorted(
        [x for x in raw_labels if is_season_type_label(x)],
        key=lambda x: (season_start(x) or 9999, x),
    )

    raw_season_only_labels = sorted(
        [x for x in raw_labels if not is_season_type_label(x)],
        key=lambda x: (season_start(x) or 9999, x),
    )

    print("\nSUMMARY")
    print("-------")
    print(f"raw label count: {len(raw_labels)}")
    print(f"raw season-type label count: {len(raw_season_type_labels)}")
    print(f"processed label count: {len(processed_labels)}")

    season_years = [season_start(x) for x in raw_labels if season_start(x) is not None]
    if season_years:
        earliest = min(season_years)
        latest = max(season_years)
        print(f"earliest loaded season: {earliest}-{str(earliest + 1)[-2:]}")
        print(f"latest loaded season: {latest}-{str(latest + 1)[-2:]}")
    else:
        print("earliest loaded season: (none)")
        print("latest loaded season: (none)")

    current_playoff_label = "2025-26_playoffs"
    if current_playoff_label in raw_season_type_labels:
        print("current season playoffs: loaded")
    else:
        print("current season playoffs: not loaded")

    print("\nRAW TABLES")
    print("----------")
    for subdir in RAW_TABLE_DIRS:
        files = list_files(raw_dir, subdir)
        print(f"{subdir}: {len(files)} file(s)")

    print("\nPROCESSED TABLES")
    print("----------------")
    for subdir in PROCESSED_TABLE_DIRS:
        files = list_files(processed_dir, subdir)
        print(f"{subdir}: {len(files)} file(s)")

    if manifest_path.exists():
        manifest_df = pd.read_csv(manifest_path)
        manifest_labels = sorted(
            [
                normalize_manifest_label(r["season"], r["season_type"])
                for _, r in manifest_df.iterrows()
            ],
            key=lambda x: (season_start(x) or 9999, x),
        )

        print("\nMANIFEST")
        print("--------")
        print(f"manifest rows: {len(manifest_df)}")

        raw_set = set(raw_season_type_labels)
        processed_set = set(processed_labels)
        manifest_set = set(manifest_labels)

        raw_vs_manifest_missing = sorted(
            raw_set - manifest_set, key=lambda x: (season_start(x) or 9999, x)
        )
        manifest_vs_raw_missing = sorted(
            manifest_set - raw_set, key=lambda x: (season_start(x) or 9999, x)
        )
        processed_vs_manifest_missing = sorted(
            processed_set - manifest_set, key=lambda x: (season_start(x) or 9999, x)
        )
        manifest_vs_processed_missing = sorted(
            manifest_set - processed_set, key=lambda x: (season_start(x) or 9999, x)
        )

        raw_aligned = len(raw_vs_manifest_missing) == 0 and len(manifest_vs_raw_missing) == 0
        print(f"raw vs manifest aligned: {raw_aligned}")
        proc_aligned = (
            len(processed_vs_manifest_missing) == 0 and len(manifest_vs_processed_missing) == 0
        )
        print(f"processed vs manifest aligned: {proc_aligned}")

        if raw_vs_manifest_missing:
            print_section("RAW LABELS NOT IN MANIFEST", raw_vs_manifest_missing)
        if manifest_vs_raw_missing:
            print_section("MANIFEST LABELS NOT IN RAW", manifest_vs_raw_missing)
        if processed_vs_manifest_missing:
            print_section("PROCESSED LABELS NOT IN MANIFEST", processed_vs_manifest_missing)
        if manifest_vs_processed_missing:
            print_section("MANIFEST LABELS NOT IN PROCESSED", manifest_vs_processed_missing)
    else:
        print("\nMANIFEST")
        print("--------")
        print("No manifest found.")

    receipt_states: list[tuple[str, str, list[str]]] = []
    if validation_manifest_dir.exists():
        for path in sorted(validation_manifest_dir.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                season = str(document["season"])
                season_type = str(document["season_type"])
                inspection = inspect_slice_manifest(season, season_type, data_root=data_dir)
                receipt_states.append(
                    (
                        f"{season} {season_type}",
                        inspection["validation_state"],
                        inspection["errors"],
                    )
                )
            except Exception as exc:
                receipt_states.append((path.name, "failed", [f"manifest is corrupt: {exc}"]))

    print("\nVALIDATION RECEIPTS")
    print("-------------------")
    print(f"receipt count: {len(receipt_states)}")
    all_passed = bool(receipt_states) and all(state == "passed" for _, state, _ in receipt_states)
    print(f"all validation receipts passed: {all_passed}")
    for label, state, errors in receipt_states:
        print(f"{label}: {state}")
        for error in errors:
            print(f"  {error}")

    print_section("RAW SEASON-ONLY LABELS", raw_season_only_labels)
    print_section("RAW SEASON-TYPE LABELS", raw_season_type_labels)
    print_section("PROCESSED FILE LABELS", processed_labels)
