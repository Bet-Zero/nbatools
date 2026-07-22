# Result Contracts

> **Status: current reference.**
> The typed result layer in
> [`structured_results.py`](../../src/nbatools/commands/structured_results.py)
> implements the contracts described here. The generated
> [`repository_inventory.json`](../../contracts/repository_inventory.json)
> records the current result-type names and count. The original gap analysis
> is retained separately as the historical
> [result contracts audit](../audits/result_contracts_audit.md).

This document separates the shipped result boundary from design guidance for
extending it. For verified query behavior, see
[current_state_guide.md](current_state_guide.md).

Related docs:

- [project_conventions.md](../architecture/project_conventions.md) — engineering conventions
- [data_contracts.md](data_contracts.md) — dataset-level contracts
- [structured_result_layer.md](../architecture/structured_result_layer.md) — result-layer architecture

---

## 1. Current implementation

### 1.1 Consumer boundaries

The repository has three consumer surfaces over the shared query engine:

- The CLI receives a query-service `QueryResult` and renders its typed result
  through `format_output.py`. It does **not** consume the FastAPI
  `QueryResponse` model.
- The FastAPI layer converts the same `QueryResult` into the HTTP
  `QueryResponse` envelope.
- The React web UI calls the HTTP endpoints and renders that `QueryResponse`.

The shared source of truth is the typed structured result. Pretty terminal
text, exports, the HTTP envelope, and browser components are presentation or
transport layers over it; none should be the first place an NBA value is
calculated.

### 1.2 Implemented result types

There are eight structured result types:

| Python type | `query_class` | Structured `sections` keys | Labeled CLI/raw sections |
| --- | --- | --- | --- |
| `SummaryResult` | `summary` | `summary`; optional `by_season`, `game_log`, `top_performers` | `SUMMARY`; optional `BY_SEASON`, `TOP_PERFORMERS` (`GAME_LOG` is also available in the CLI section map) |
| `ComparisonResult` | `comparison` | `summary`, `comparison` | `SUMMARY`, `COMPARISON` |
| `SplitSummaryResult` | `split_summary` | `summary`, `split_comparison` | `SUMMARY`, `SPLIT_COMPARISON` |
| `FinderResult` | `finder` | `finder` | `FINDER` |
| `LeaderboardResult` | `leaderboard` | `leaderboard` | `LEADERBOARD` |
| `StreakResult` | `streak` | `streak` | `STREAK` |
| `CountResult` | `count` | `count`; optional `finder` detail | `COUNT`; optional `FINDER` detail |
| `NoResult` | route-specific | no successful data sections | rendered from `result_status` and `result_reason`; the compatibility parser recognizes `NO_RESULT` and `ERROR` labels |

The generated repository inventory is the machine-checked source for this
list. New result types must be added deliberately and wired through structured
rendering, API serialization, UI rendering, tests, and the inventory.

### 1.3 Shared structured fields

Every result object carries the same trust and status boundary:

- `query_class`
- `result_status`: `ok`, `no_result`, or `error`
- `result_reason`, when the result is not `ok`
- `current_through`, when determinable
- `metadata`
- `notes`
- `caveats`
- `sections` in the dictionary representation

`QueryResult` adds query-level context, including the original or synthetic
query text and resolved route. The API then exposes request-level fields such
as `ok`, `query`, `route`, `confidence`, `intent`, and `alternates` alongside
the structured result payload.

Metadata values are populated when they apply and are known. A field being
part of the shared vocabulary does not justify inventing a value when the
engine did not resolve one.

### 1.4 No-result and error semantics

`NoResult` is a first-class structured result. Its current canonical reasons
are:

- `no_match`
- `no_data`
- `unsupported`
- `filter_not_supported`
- `ambiguous`
- `ambiguous_query`
- `unrouted`
- `error`

The query service maps expected failures (`no_match`, `no_data`,
`unsupported`, `filter_not_supported`, `ambiguous`, and `ambiguous_query`) to
`result_status: "no_result"`. `unrouted` and `error` map to
`result_status: "error"`.

This distinction lets every consumer tell a valid empty answer from missing
coverage, an unsupported request, an ambiguity, or a system failure.

---

## 2. Current role of each result class

### 2.1 Finder

Returns games or entities matching a filter. The `finder` section contains one
row per match and may include rank, entity identity, game context, and the
requested statistics. Sample count, filter context, sort information, and
truncation details belong in structured data or metadata when applicable.

Typical routes include `player_game_finder` and `game_finder`.

### 2.2 Summary

Returns aggregated statistics for one entity over a sample. The `summary`
section is the primary answer. A summary may also supply `by_season`,
`game_log`, or `top_performers` detail without changing result class.

Typical routes include `player_game_summary`, `game_summary`,
`player_on_off`, and `lineup_summary`.

### 2.3 Comparison

Returns consistent side-by-side statistics for multiple entities or matchup
scopes. The `summary` section carries entity-level context and the
`comparison` section carries the aligned comparison rows. Metadata identifies
special semantics such as head-to-head scope when applicable.

Typical routes include `player_compare`, `team_compare`, and matchup-history
routes.

### 2.4 Split summary

Returns two or more sub-samples of one entity. The `summary` section describes
the base sample and `split_comparison` contains aligned bucket rows such as
home/away or wins/losses.

Typical routes include `player_split_summary` and `team_split_summary`.

### 2.5 Leaderboard

Returns ranked entities, games, stretches, appearances, or other occurrences.
The `leaderboard` section contains the ordered rows. Ranking metric, direction,
qualifiers, source provenance, and coverage caveats belong in metadata when
applicable.

Typical routes include `season_leaders`, `season_team_leaders`,
`top_player_games`, `top_team_games`, and the specialized leaderboard routes.

### 2.6 Streak

Returns streak detections or longest-streak results. The `streak` section
contains the qualifying runs and their start/end context. Threshold, mode,
scope, and coverage information belong in the rows or metadata rather than in
renderer-only inference.

Typical routes include `player_streak_finder` and `team_streak_finder`.

### 2.7 Count

Returns a scalar count without forcing a consumer to infer it from detail-row
length. The `count` section always contains the answer, including zero. A
`finder` detail section may accompany the count when matching games are useful,
but that detail is optional and does not change the result class.

`CountResult` is produced by query-service count-intent post-processing rather
than by a separate public route name.

### 2.8 No result

Represents a non-successful answer with explicit status and reason fields.
Consumers render the reason and any supplied recovery context; they do not
deduce failure type from an empty table or a literal text string.

---

## 3. Stable section names

The current structured result layer establishes these uppercase labels for
labeled text and CLI section maps:

- `SUMMARY`
- `BY_SEASON`
- `TOP_PERFORMERS`
- `COMPARISON`
- `SPLIT_COMPARISON`
- `COUNT`
- `FINDER`
- `LEADERBOARD`
- `STREAK`

`GAME_LOG` is an optional `SummaryResult` CLI section-map key. `NO_RESULT` and
`ERROR` remain recognized compatibility labels in `format_output.py`; direct
typed-result rendering uses `NoResult.result_status` and
`NoResult.result_reason` instead.

The dictionary/API representation uses lowercase section keys. Section labels
live inside a result and are not substitutes for the result class itself. Do
not rename them casually because CLI/export consumers and tests may depend on
them.

---

## 4. Rendering and export contract

- **Typed result objects** are the engine contract.
- **`QueryResult`** is the query-service envelope used by in-process consumers,
  including the CLI.
- **Pretty CLI output** may align columns, add headings, and format values, but
  it must not invent data.
- **CSV/TXT/JSON exports** project the typed result into their target format.
  A single-table CSV may intentionally omit optional mixed-grain detail, as the
  count export does, while JSON retains the structured sections.
- **FastAPI `QueryResponse`** is the HTTP transport envelope derived from
  `QueryResult`.
- **React rendering** consumes `QueryResponse` and selects presentation
  patterns from the supplied route, metadata, and result sections.

The invariant is:

> Any NBA value a user sees must exist in the typed result first.

---

## 5. Design guidance for extensions

The following are design rules, not claims that every field is populated by
every route:

- Echo resolved scope when relevant: season or season range, season type,
  absolute date window, entity/opponent identity, split type, and sort order.
- Preserve semantic flags such as grouped-boolean mode and head-to-head scope.
- Surface trusted freshness through `current_through` and put real limitations
  or fallback behavior in `notes` or `caveats`.
- Keep player/team samples comparable in comparison and split results.
- Add data to the engine/API contract when the UI needs it; do not compute NBA
  facts in React.
- Fit a new route into an existing result type when its shape genuinely
  matches. Add a ninth type only when the existing eight cannot represent it
  without distortion.
- Protect contract changes with structured-result, export, API, and frontend
  tests appropriate to the affected consumers.

Grouped boolean filtering is not implied for every class simply because the
metadata vocabulary can represent it. Query support remains governed by the
verified query catalog and current-state guide.

---

## 6. Historical context

This reference began as a design target before the UI and typed result layer
existed. At that time, command output was stdout CSV text and downstream code
had to infer shapes from labels and columns. The historical
[result contracts audit](../audits/result_contracts_audit.md) records those
gaps and the incremental migration rationale.

That audit is retained as history, not as current release evidence. Current
claims must be verified against `structured_results.py`, `query_service.py`,
`api.py`, the frontend renderer, their tests, and the generated repository
inventory.
