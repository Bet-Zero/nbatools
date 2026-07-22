# Structured Result Layer

The structured result layer is the transport-neutral contract between command
execution and the CLI, API, and React UI. It lives in
`src/nbatools/commands/structured_results.py`.

## Result families

The module defines seven successful result families plus the explicit
`NoResult` sentinel:

| Result type | Query shape |
| --- | --- |
| `SummaryResult` | One entity summary, optionally grouped by season |
| `ComparisonResult` | Two or more entities plus comparison rows |
| `SplitSummaryResult` | One summary split into labeled buckets |
| `FinderResult` | Matching game rows |
| `LeaderboardResult` | Ranked player, team, game, lineup, or record rows |
| `StreakResult` | Matching streak rows |
| `CountResult` | A count plus the evaluated matching rows |
| `NoResult` | No data, no match, unsupported, ambiguous, unrouted, or error state |

Every registered public query route executes a command `build_result()` path
through the query service. Natural-language execution resolves a route first;
structured execution supplies the route and arguments directly. Both paths
therefore return the same typed result contract.

## Rendering contracts

Successful result objects expose:

| Method | Consumer and purpose |
| --- | --- |
| `to_labeled_text()` | Stable labeled CSV text for raw CLI output and text export |
| `to_dict()` | JSON-serializable result data for the query service, API, UI, and JSON export |
| `to_sections_dict()` | Labeled CSV sections consumed by CLI presentation formatting |

`NoResult` exposes `to_labeled_text()` and `to_dict()` with the same status,
reason, metadata, notes, and caveat vocabulary, but it has no successful data
sections to format.

## Data flow

```text
natural text or structured route
  -> query service
  -> command build_result()
  -> typed result object
       -> to_dict() for API/UI/JSON
       -> labeled text or sections for CLI rendering and text/CSV export
```

CLI command wrappers remain presentation adapters: they normalize arguments,
call the query service, and render the returned result. The HTTP layer calls
the same service and serializes `QueryResult.to_dict()`. Business logic stays
in command modules rather than either transport.

## Compatibility and validation

The labeled section vocabulary remains part of the CLI/raw-output contract,
while `to_dict()` is the machine-readable contract shared by API and web
consumers. `src/nbatools/commands/format_output.py` owns CLI presentation; it
does not become the source for API data.

Tests in `tests/test_structured_results.py`, the query-service tests, API
tests, output tests, and frontend contract tests protect these boundaries.
