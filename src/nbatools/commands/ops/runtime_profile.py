"""Time where a cold query process spends its time.

Read-only. Splits one fresh process into the stages the deployed function pays
on a cold start: imports, resolving the generation, building the player-name
index, then representative queries cold and warm, with the bytes fetched from
the data source at each stage. Run it in a new process so nothing is already
cached, against the configured source:

    NBATOOLS_R2_CACHE_DIR=$(mktemp -d) python -m nbatools.commands.ops.runtime_profile

Prints one JSON document. These are measurements of this machine and network,
not of the deployed function; use them to rank causes, not as latency claims.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_QUERIES = (
    "top 10 scorers 2025-26",
    "LeBron James career stats",
    "Celtics record last 10 games",
    "Jokic vs Embiid 2024-25",
)


def _cache_bytes() -> int:
    root = os.environ.get("NBATOOLS_R2_CACHE_DIR")
    if not root or not Path(root).exists():
        return 0
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())


def _files_cached() -> int:
    root = os.environ.get("NBATOOLS_R2_CACHE_DIR")
    if not root or not Path(root).exists():
        return 0
    return sum(1 for p in Path(root).rglob("*") if p.is_file())


def profile(queries: tuple[str, ...] = DEFAULT_QUERIES) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []

    def stage(name: str, fn):
        before_bytes, before_files = _cache_bytes(), _files_cached()
        started = time.perf_counter()
        value = fn()
        stages.append(
            {
                "stage": name,
                "seconds": round(time.perf_counter() - started, 3),
                "fetched_files": _files_cached() - before_files,
                "fetched_mb": round((_cache_bytes() - before_bytes) / 1e6, 2),
            }
        )
        return value

    def imports():
        import nbatools.query_service  # noqa: F401

    stage("import query service", imports)

    from nbatools.commands import entity_resolution
    from nbatools.data_source import data_generation_context
    from nbatools.query_service import execute_natural_query

    with data_generation_context() as generation:
        stage("player name index", entity_resolution._get_player_full_name_index)
        for query in queries:
            for label in ("cold", "warm"):
                result = stage(f"{label}: {query}", lambda q=query: execute_natural_query(q))
                stages[-1]["status"] = result.result_status
                stages[-1]["route"] = result.route
    return {
        "generation": generation,
        "data_source": os.environ.get("DATA_SOURCE", "local"),
        "total_seconds": round(sum(item["seconds"] for item in stages), 3),
        "stages": stages,
    }


def main(argv: list[str] | None = None) -> None:
    queries = tuple(argv if argv else sys.argv[1:]) or DEFAULT_QUERIES
    print(json.dumps(profile(queries), indent=2))


if __name__ == "__main__":
    main()
