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
and exposed by `GET /routes` plus `nbatools-cli query routes`. The current
service surface has 30 routes: `top_player_games`, `top_team_games`,
`season_leaders`, `season_team_leaders`, `player_game_summary`,
`game_summary`, `player_game_finder`, `game_finder`, `player_compare`,
`team_compare`, `team_record`, `team_matchup_record`,
`team_record_leaderboard`, `player_split_summary`, `team_split_summary`,
`player_streak_finder`, `team_streak_finder`, `player_occurrence_leaders`,
`team_occurrence_leaders`, `player_on_off`, `lineup_summary`,
`lineup_leaderboard`, `player_stretch_leaderboard`, `playoff_history`,
`playoff_appearances`, `playoff_matchup_history`, `playoff_round_record`,
`record_by_decade`, `record_by_decade_leaderboard`, `matchup_by_decade`.

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

## What calls the service

| Caller                   | Entry point                                                | Notes                                                                |
| ------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------- |
| CLI `ask` command        | `execute_natural_query` via `natural_query.run()`          | Renders to pretty/raw/exports                                        |
| CLI `query` sub-commands | `execute_structured_query` via `_run_and_handle_exports()` | Kwargs path only; positional-arg callers use direct `build_result()` |
| Tests                    | Both                                                       | Dedicated tests in `test_query_service.py`                           |
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
