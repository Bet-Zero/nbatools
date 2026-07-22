# Query Service Layer

The query service (`src/nbatools/query_service.py`) is the primary programmatic
entry point for executing NBA queries. It returns structured result objects
directly, without going through CLI rendering paths.

## Entry points

### `execute_natural_query(query: str) -> QueryResult`

Parse a natural-language query string, route it to the appropriate command,
execute it, and return a `QueryResult` envelope.

```python
from nbatools import execute_natural_query

qr = execute_natural_query("Jokic summary 2024-25")
print(qr.is_ok)           # True
print(type(qr.result))    # SummaryResult
print(qr.result.to_dict())
```

### `execute_structured_query(route: str, **kwargs) -> QueryResult`

Execute a named route directly with explicit keyword arguments.

```python
from nbatools import execute_structured_query

qr = execute_structured_query(
    "season_leaders",
    season="2024-25",
    stat="pts",
    limit=10,
)
print(qr.result.leaders)  # pandas DataFrame
```

Valid routes are defined by `VALID_ROUTES` in `src/nbatools/query_service.py`
and exposed by `GET /routes` plus `nbatools-cli query routes`. The
[generated repository inventory](../../contracts/repository_inventory.json)
records the current registered count; `VALID_ROUTES` remains the runtime
authority.

## QueryResult envelope

Both entry points return a `QueryResult` dataclass:

| Field             | Type         | Description                                                      |
| ----------------- | ------------ | ---------------------------------------------------------------- |
| `result`          | typed result | `SummaryResult`, `FinderResult`, etc. or `NoResult`              |
| `metadata`        | dict         | Route, query_class, season, player, team, current_through, notes |
| `query`           | str          | Original query string                                            |
| `route`           | str or None  | Resolved route name                                              |
| `is_ok`           | bool         | `True` unless result is `NoResult`                               |
| `result_status`   | str          | `"ok"`, `"no_result"`, or `"error"`                              |
| `result_reason`   | str or None  | `"no_match"`, `"no_data"`, `"unrouted"`, etc.                    |
| `current_through` | str or None  | Latest game date covered                                         |

### `to_dict()`

Returns a JSON-serializable dict combining the result's sections and metadata.

## Request-scoped data generation

Both public entry points resolve the active data generation before parsing or
execution and pin it for the full request. Natural parsing, structured
execution, file reads, DataFrame loaders, and data-backed entity indexes
therefore use one immutable generation even if the active pointer changes
while the request is running. A later request observes the new pointer and
uses different file, frame, and entity cache keys.

The runtime reads `data/metadata/active_generation.json` locally or
`metadata/active_generation.json` in R2. Its `generation_id` selects logical
data beneath `data/generations/<generation_id>/` locally or
`generations/<generation_id>/` in R2. When no pointer exists, the source uses
the legacy canonical paths for backward compatibility. An invalid or
unreadable pointer fails closed rather than combining generations.

`NBATOOLS_DATA_GENERATION` is an explicit generation override for controlled
tests and operations. It selects the same immutable directory/prefix layout;
it is not a substitute for publishing and switching the active pointer.

## Bounded DataFrame loader cache

Data-backed command loaders share one process-local, thread-safe LRU cache.
Entries are keyed by dataset, pinned generation, normalized slice parameters,
and one season; a multi-season query concatenates those season frames for its
caller without retaining another full-range entry. This keeps overlapping
queries reusable without allowing arbitrary season-range tuples to accumulate.

The cache is bounded by both retained entry count and the deep pandas memory
size of its frames. The defaults are 16 entries and 128 MiB. Operators may set
`NBATOOLS_FRAME_CACHE_MAX_ENTRIES` and `NBATOOLS_FRAME_CACHE_MAX_BYTES` before
process startup to use tighter deployment-specific budgets. A zero value
disables retention for that dimension, and any frame larger than the byte
budget is returned without being cached.

Concurrent misses for the same key are coalesced into one load. Command
loaders return caller-owned results, so downstream mutations cannot alter a
retained season frame. `frame_cache_info()` exposes hit, miss, coalescing,
eviction, oversize-skip, entry, and byte counters for runtime diagnostics;
`clear_frame_cache()` is available for controlled tests and operations. The
cache is an optimization only: immutable generation keys remain the
correctness boundary for data refreshes.

## What calls the service

| Caller | Entry point | Notes |
| --- | --- | --- |
| CLI `ask` command | `execute_natural_query` via `natural_query.run()` | Renders to pretty/raw/exports |
| CLI `query` subcommands | `execute_structured_query` via `_run_and_handle_exports()` | Normalizes wrapper arguments before service execution |
| Tests and library callers | Both | May call command builders directly for focused unit scope |
| HTTP API on behalf of React and API clients | Both | Serializes the service envelope as JSON |

## Service boundary

All natural and structured query paths exposed by the CLI and HTTP API use the
query service. CLI apps for raw data, processing, operations, and analysis
(`cli_apps/raw.py`, `cli_apps/processing.py`, and peers) are intentionally
outside this boundary because they are not query surfaces. Focused tests and
library code may call command builders directly when the query envelope is not
under test.

## Result types

All result types are re-exported from `nbatools.query_service` for convenience:

- `SummaryResult` — player/team summaries
- `ComparisonResult` — player or team comparisons
- `SplitSummaryResult` — home/away or wins/losses splits
- `FinderResult` — game finder results
- `LeaderboardResult` — season leaders or top games
- `StreakResult` — streak finder results
- `CountResult` — count results plus evaluated matching rows
- `NoResult` — no data / unrouted / error sentinel
- `ResultStatus`, `ResultReason` — status enums

## Rendering

`render_query_result()` in
`src/nbatools/commands/_natural_query_execution.py` takes a `QueryResult` and
handles CLI output (pretty or raw) and file exports (CSV, TXT, JSON).
`natural_query.py` imports that helper, and the CLI's `run()` calls it after
getting a result from the service.

The React UI skips the CLI renderer entirely. The HTTP layer passes the
`QueryResult` through `api_handlers.query_result_to_payload()`, serializes that
payload as JSON, and the typed frontend client consumes the JSON response from
`/query` or `/structured-query`. Browser code never receives or operates on a
Python `QueryResult` or structured-result object.
