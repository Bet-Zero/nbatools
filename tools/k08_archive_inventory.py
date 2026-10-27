"""Inventory four representative archive seasons without acquiring game bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPOSITORY = "sportsdataverse/hoopR-nba-stats-raw"
REVISION = "2e44b7c039f104bc6b41a1de494411e83a03714e"
SEASONS = (("1997-98", "1998"), ("2004-05", "2005"), ("2014-15", "2015"), ("2025-26", "2026"))
ENDPOINTS = ("boxscoretraditionalv3", "boxscoresummaryv2", "boxscoresummaryv3")


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/{path}"]))


def tree(sha):
    result = api(f"git/trees/{sha}")
    if result.get("truncated"):
        raise ValueError("Archive tree is truncated; cannot claim file coverage")
    return result["tree"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    endpoint_entries = api(f"contents/nba_stats/json?ref={REVISION}")
    endpoint_ids = {row["name"]: row["sha"] for row in endpoint_entries}
    result = dict(
        repository=REPOSITORY,
        revision=REVISION,
        generated_at=datetime.now(UTC).isoformat(),
        classification="metadata_index_only_not_game_body_or_inactive_completeness",
        bulk_game_acquisition=False,
        scope="four representative season indexes; not all historical seasons",
        canonical_manifest_sha256=hashlib.sha256(
            (args.canonical_root / "metadata/generation_manifest.json").read_bytes()
        ).hexdigest(),
        endpoints={},
    )
    for endpoint in ENDPOINTS:
        years = {entry["path"]: entry["sha"] for entry in tree(endpoint_ids[endpoint])}
        endpoint_result = dict(
            endpoint_tree_sha=endpoint_ids[endpoint], indexed_years=sorted(years), samples=[]
        )
        result["endpoints"][endpoint] = endpoint_result
        for season, year in SEASONS:
            if year not in years:
                endpoint_result["samples"].append(dict(season=season, status="year_not_indexed"))
                continue
            entries = tree(years[year])
            ids = {
                item["path"][:-5]
                for item in entries
                if item["type"] == "blob"
                and item["path"].endswith(".json")
                and len(item["path"]) == 15
                and item["path"][:10].isdigit()
            }
            slices = []
            for suffix in ("regular_season", "playoffs"):
                path = args.canonical_root / "raw/games" / f"{season}_{suffix}.csv"
                games = pd.read_csv(path, dtype={"game_id": str})
                final = games.loc[games.is_final.astype(str).str.lower().isin(["true", "1"])]
                known = {f"{int(gid):010d}" for gid in final.game_id}
                type_prefix = "002" if suffix == "regular_season" else "004"
                indexed_type = {gid for gid in ids if gid.startswith(type_prefix)}
                slices.append(
                    dict(
                        season_type=suffix,
                        canonical_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        canonical_final_games=len(known),
                        indexed_games=len(known & ids),
                        missing_game_ids=sorted(known - ids),
                        indexed_matching_type_files=len(indexed_type),
                        indexed_outside_canonical_ids=sorted(indexed_type - known),
                    )
                )
            endpoint_result["samples"].append(
                dict(
                    season=season,
                    status="untruncated_index_checked",
                    season_tree_sha=years[year],
                    indexed_game_files=len(ids),
                    observed_slices=slices,
                )
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
