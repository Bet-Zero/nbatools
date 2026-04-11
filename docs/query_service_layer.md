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

Valid routes: `top_player_games`, `top_team_games`, `season_leaders`,
`season_team_leaders`, `player_game_summary`, `game_summary`,
`player_game_finder`, `game_finder`, `player_compare`, `team_compare`,
`player_split_summary`, `team_split_summary`, `player_streak_finder`,
`team_streak_finder`.

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

## What calls the service

| Caller                   | Entry point                                                | Notes                                                                |
| ------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------- |
| CLI `ask` command        | `execute_natural_query` via `natural_query.run()`          | Renders to pretty/raw/exports                                        |
| CLI `query` sub-commands | `execute_structured_query` via `_run_and_handle_exports()` | Kwargs path only; positional-arg callers use direct `build_result()` |
| Tests                    | Both                                                       | 45 dedicated tests in `test_query_service.py`                        |
| React UI / API clients   | Both                                                       | Primary intended consumer                                            |

## What still bypasses the service

- **Positional-arg callers of `_run_and_handle_exports`** (some tests) call
  `build_result()` directly instead of going through the service. These use
  the same `build_result` functions but skip the service's metadata construction.
- **Grouped boolean / OR query text-based fallbacks**: if the structured-first
  path in `execute_natural_query` raises an exception for a grouped boolean
  or OR query, `natural_query.run()` still falls back to the legacy stdout
  capture path. These are edge-case backward-compatibility paths.
- **CLI apps for raw data, processing, ops, and analysis** (`cli_apps/raw.py`,
  `cli_apps/processing.py`, etc.) are not query commands and do not go through
  the service.

## Result types

All result types are re-exported from `nbatools.query_service` for convenience:

- `SummaryResult` — player/team summaries
- `ComparisonResult` — player or team comparisons
- `SplitSummaryResult` — home/away or wins/losses splits
- `FinderResult` — game finder results
- `LeaderboardResult` — season leaders or top games
- `StreakResult` — streak finder results
- `NoResult` — no data / unrouted / error sentinel
- `ResultStatus`, `ResultReason` — status enums

## Rendering

`render_query_result()` in `natural_query.py` takes a `QueryResult` and handles
CLI output (pretty or raw) and file exports (CSV, TXT, JSON). This is the
function that the CLI's `run()` calls after getting a result from the service.
The React UI skips this entirely and consumes `QueryResult.to_dict()` or
the result object directly.
