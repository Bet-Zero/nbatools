# Weak Contract Decision Preflight

Discovery date: 2026-05-10

Scope: product-decision preflight for the three weak contracts called out by
Core Result/Table Contract Lock Wave 2. This is not an implementation plan for
new query support, a UI redesign, or a route registry.

## Executive Summary

Targets reviewed:

- `lineup_summary`
- `player_on_off`
- `playoff_appearances` single-team summary variant

Biggest finding: `playoff_appearances` already has two backend shapes under the
same route. League-wide queries return `leaderboard`, while single-team queries
return `summary` plus `by_season`. The frontend maps the route only to the
leaderboard pattern, so a successful single-team result can render no visible
content.

Second finding: `lineup_summary` backend source-backed rows use `lineup_name`
and pipe-delimited `player_names`, but `EntitySummaryResult` currently recognizes
only `lineup`, `lineup_members`, or `members` as lineup labels. The current
Wave 2 frontend fixture protects the intended hero behavior, but it does not
match the actual source-backed backend row keys.

Recommended next implementation: Option E, a tiny combined frontend cleanup:

1. Keep `player_on_off` on the current `summary`-row split contract.
2. Add `lineup_summary` label support for actual backend keys
   (`lineup_name`, `player_names`, and metadata `lineup_members`) without adding
   a dedicated pattern yet.
3. Add UI support for single-team `playoff_appearances` summary results,
   preferably as a small playoff-history/appearances mode rather than a new
   broad pattern.

Production code should change in the next implementation wave: yes, narrowly.
This preflight changes docs only.

Highest-risk target: `playoff_appearances` single-team summary, because natural
queries can already produce an `ok` result that the current route mapping does
not display.

Lowest-risk target: `player_on_off`, because current frontend rendering matches
the current backend row shape; the weakness is semantic consistency, not a known
display failure.

## Files Inspected

| File | Why inspected | Key finding |
|---|---|---|
| `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md` | Current product map and route inventory | Lists all three targets as shipped and documents `player_on_off` as a split, `lineup_summary` as entity summary, and `playoff_appearances` as leaderboard. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Locked Wave 1/Wave 2 display contracts | Identifies the same three weak contracts, locks current `player_on_off`, `lineup_summary`, and ranked `playoff_appearances` behavior, and records that general leaderboard/detail/row-cap decisions were deferred. |
| `src/nbatools/commands/natural_query.py` | Natural route selection | Routes lineup summary before lineup leaderboard; routes on/off through `player_on_off`; delegates playoff routing to `try_playoff_record_route`. |
| `src/nbatools/commands/_natural_query_execution.py` | Route-to-builder map | Maps all three targets to production builders. |
| `src/nbatools/commands/_playoff_record_route_utils.py` | Playoff route selection | `playoff_appearance_intent` routes to `playoff_appearances` even when `team` is set. |
| `src/nbatools/commands/lineup_summary.py` | Lineup backend result builder | Returns `SummaryResult(summary=rows)` only; source-backed rows keep `lineup_name` and `player_names`. |
| `src/nbatools/commands/_lineup_execution.py` | Lineup row contract | `RESULT_COLUMNS` are `season`, `season_type`, `team_abbr`, `unit_size`, `lineup_id`, `lineup_name`, `player_ids`, `player_names`, `minute_minimum`, `minutes`, `off_rating`, `def_rating`, `net_rating`, `pace`, `ts_pct`. |
| `src/nbatools/commands/player_on_off.py` | On/off backend result builder | Returns `SummaryResult` with one row per `presence_state`, not `SplitSummaryResult`. |
| `src/nbatools/commands/playoff_history.py` | Playoff appearance builder | `build_playoff_appearances_result()` returns `LeaderboardResult` without `team`, but `SummaryResult` with `summary` and `by_season` when `team` is supplied. |
| `src/nbatools/query_service.py` | Query service routes and structured entrypoint | Accepts all three routes; structured `playoff_appearances` can expose the single-team summary variant directly. |
| `tests/test_core_result_table_contracts.py` | Backend section contract tests | Locks current `player_on_off` as `summary` rows and ranked `playoff_appearances` as `leaderboard`. |
| `tests/test_source_backed_lineup_dataset.py` | Source-backed lineup execution tests | Confirms source-backed lineup summary rows include actual backend columns such as `team_abbr`, `unit_size`, and `net_rating`. |
| `tests/test_source_backed_on_off_dataset.py` | Source-backed on/off execution tests | Confirms trusted on/off rows can return both `on` and `off` rows in `summary`. |
| `tests/test_playoff_history_queries.py` | Playoff appearance route tests | Confirms single-team playoff appearances are intentionally `SummaryResult` behavior. |
| `frontend/src/api/types.ts` | Route type coverage | Includes all three route names. |
| `frontend/src/components/results/config/routeToPattern.ts` | Frontend route-to-pattern mapping | Maps `lineup_summary` to `entity_summary`, `player_on_off` to split over `summary`, and all `playoff_appearances` to leaderboard over `leaderboard`. |
| `frontend/src/components/results/resultShapes.ts` | Shape classification | Classifies based on route pattern, so single-team `playoff_appearances` can classify as `leaderboard_table` despite lacking `leaderboard`. |
| `frontend/src/components/results/ResultRenderer.tsx` | Pattern dispatch | A pattern that finds no rows returns `null`; current single-team `playoff_appearances` does not fall back. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Lineup summary rendering | Lineup hero recognizes `lineup`, `lineup_members`, and `members`, but not actual backend `lineup_name` or `player_names`. |
| `frontend/src/components/results/patterns/SplitResult.tsx` | On/off display behavior | Supports `sectionKey=summary`, `bucketKey=presence_state`, on/off labels, split table columns, and edge chips. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Playoff ranked display behavior | Requires rows in `leaderboard`; single-team playoff-appearance summary rows are ignored by current mapping. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Candidate support pattern | Already renders `summary` plus `by_season`, and its hero handles `appearances`; it would need a small appearances-mode/table-column tweak for clean single-team playoff appearances. |
| `frontend/src/test/routeToPattern.test.ts` | Frontend mapping tests | Locks current mappings for all Wave 2 routes. |
| `frontend/src/test/resultShapes.test.ts` | Frontend shape tests | Locks `lineup_summary` as `entity_summary` and `player_on_off` as `on_off_split`. |
| `frontend/src/test/wave2SectionContracts.test.ts` | Frontend section tests | Protects `player_on_off` summary rows and ranked `playoff_appearances` leaderboard only. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Frontend table smoke tests | Tests `lineup_summary` with synthetic `lineup` field, not actual backend `lineup_name` / `player_names`. |

## Target Review: `lineup_summary`

### Current Behavior

Backend:

- Route: `lineup_summary`.
- Builder: `src/nbatools/commands/lineup_summary.py::build_result`.
- On successful source-backed execution, returns `SummaryResult`.
- Sections: `summary` only.
- With missing or untrusted local `league_lineup_viz` coverage, returns
  `NoResult(reason="unsupported")` with no sections.

Backend `summary` row fields are selected by
`src/nbatools/commands/_lineup_execution.py::RESULT_COLUMNS`:

- `season`
- `season_type`
- `team_abbr`
- `unit_size`
- `lineup_id`
- `lineup_name`
- `player_ids`
- `player_names`
- `minute_minimum`
- `minutes`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`
- `ts_pct`

`lineup_summary.py` coerces `minutes`, `off_rating`, `def_rating`,
`net_rating`, `pace`, and `ts_pct` to numeric values before returning the
summary.

Representative query observations in this checkout:

| Query | Observed route | Status | Sections | Notes |
|---|---|---|---|---|
| `lineup with Tatum and Jaylen Brown` | `lineup_summary` | `no_result` / `unsupported` | none | Trusted `league_lineup_viz` coverage unavailable locally. |
| `net rating with Tatum and Jaylen Brown together` | `lineup_summary` | `no_result` / `unsupported` | none | Parser preserved `lineup_members=["Jayson Tatum", "Jaylen Brown"]` and `unit_size=2`. |

Frontend:

- `routeToPattern.ts` maps `lineup_summary` to
  `{ type: "entity_summary", sectionKey: "summary" }`.
- `ResultRenderer.tsx` dispatches that to `EntitySummaryResult`.
- `EntitySummaryResult.summarySentence()` uses `lineupName(row)` to detect
  lineup rows.
- `lineupName(row)` currently recognizes array fields `lineup_members` and
  `members`, then string field `lineup`.
- If a lineup is detected, `lineupSummarySentence()` renders:
  `<lineup> posted <net_rating>, <off_rating>, <def_rating>, and <pace><context>.`
- `heroIdentity()` returns `null` for detected lineup rows, so the hero is text
  only.
- The component does not render a lineup table or raw detail drawer.

The frontend hero currently answers the Wave 2 synthetic fixture clearly:
`Jayson Tatum / Jaylen Brown posted ... net rating ...`. It does not yet
recognize the actual backend row label keys `lineup_name` or pipe-delimited
`player_names`, so once trusted coverage is present, the actual source-backed
row can miss the lineup-specific hero path unless the row is adapted.

### Product Assessment

The raw product does not need a dedicated lineup summary pattern right now.
For a specific lineup query, a compact answer card with net rating, offensive
rating, defensive rating, pace, season context, and freshness is acceptable.

However, the current hero should show enough trust and context to avoid looking
like a generic player summary:

- lineup label from actual backend fields
- team abbreviation when present
- minutes and minute minimum when available
- season or season range
- current-through/freshness already available in the envelope

A table is not required for a one-row lineup summary. A table becomes useful
only when lineup support expands into breakdowns, game logs, player-on/player-off
comparisons, or multiple candidate lineups.

### Options

- Keep current behavior and document it: acceptable only while local lineup
  coverage is unavailable, but it leaves a backend/frontend row-key mismatch.
- Small frontend rendering change: extend lineup label resolution to
  `lineup_name`, pipe-delimited `player_names`, and metadata `lineup_members`.
- Small backend shape normalization: add frontend-friendly `lineup` or
  `lineup_members` fields in the backend row. This is also low-risk, but changes
  the structured output contract.
- Dedicated pattern later: use a `LineupSummaryResult` pattern if the UI needs
  explicit cards for Team, Minutes, Net, ORtg, DRtg, Pace, TS%, and trust/source
  context.
- Explicitly mark out of UI scope: not recommended because the route is already
  shipped and mapped away from fallback.

### Recommendation

Keep `lineup_summary` on the generic `entity_summary` pattern for now, but make
the pattern lineup-aware for the actual backend row keys. Do not build a
dedicated lineup summary pattern in the next wave.

Minimal dedicated pattern later, if needed:

- Hero: lineup/member label, team, season/range, minute minimum.
- Metrics: `minutes`, `net_rating`, `off_rating`, `def_rating`, `pace`, `ts_pct`.
- Trust context: current-through and coverage/trust wording from existing
  result notes/caveats, not client-side inference.
- No table unless multiple lineup rows or a breakdown section exists.

Lowest-risk implementation path:

1. Update `EntitySummaryResult.lineupName()` to read `lineup_name`.
2. Parse `player_names` by `|` into a display label when no `lineup_name` is
   present.
3. Fall back to `metadata.lineup_members` if row labels are missing.
4. Add/update frontend tests with rows that match `_lineup_execution.RESULT_COLUMNS`.
5. Do not change backend row shape in this wave.

## Target Review: `player_on_off`

### Current Behavior

Backend:

- Route: `player_on_off`.
- Builder: `src/nbatools/commands/player_on_off.py::build_result`.
- On successful source-backed execution, returns `SummaryResult`.
- Sections: `summary` only.
- Rows are one row per `presence_state`, usually `on` and `off` when
  `presence_state="both"`.
- Missing source coverage returns `NoResult(reason="unsupported")`.

Backend `summary` row fields are defined by
`src/nbatools/commands/player_on_off.py::RESULT_COLUMNS`:

- `season`
- `season_type`
- `player_name`
- `team_abbr`
- `team_name`
- `presence_state`
- `gp`
- `minutes`
- `plus_minus`
- `off_rating`
- `def_rating`
- `net_rating`

Representative query observation in this checkout:

| Query | Observed route | Status | Sections | Notes |
|---|---|---|---|---|
| `Jokic on off` | `player_on_off` | `no_result` / `unsupported` | none | Local `team_player_on_off_summary` coverage unavailable; parser still routes correctly. |

Frontend:

- `routeToPattern.ts` maps `player_on_off` to:
  `{ type: "split", sectionKey: "summary", summaryKey: "summary", subject: "player", bucketKey: "presence_state", splitLabelOverride: "On/Off", primaryDetailTitle: "On/Off Detail", summaryDetailTitle: null }`.
- `SplitResult` reads rows from `summary`, labels buckets by `presence_state`,
  and renders the same split table primitive used by other split routes.
- Current visible columns align with backend fields:
  `Split`, `GP`, `ORtg`, `DRtg`, `Net`, `MIN`, `+/-`.
- `RawDetailToggle` uses title `On/Off Detail` over the same summary rows.
- Edge chips are available when both on/off rows exist.

Difference from `player_split_summary` / `team_split_summary`:

- Normal split routes use `SplitSummaryResult` with `summary` for context and
  `split_comparison` for bucket rows.
- `player_on_off` uses `SummaryResult.summary` as both the table source and the
  detail source.
- The frontend compensates with an explicit route pattern.

### Product Assessment

The current on/off display is understandable. Users see `On` and `Off` rows
with the expected rating metrics and edge chips. The section name is
semantically weaker than the split convention, but it is not currently risky for
display because the renderer and tests explicitly lock it.

Normalizing to `split_comparison` would improve consistency with other split
routes, but it would change a machine-readable contract that is already
documented, tested, and consumed by the frontend. The value is mostly internal
cleanliness unless another consumer needs all split bucket rows under the same
section name.

### Options

- Keep current behavior and document it: recommended for now.
- Small frontend mapping change: possible only after backend adds
  `split_comparison`; otherwise it would break current output.
- Small backend section-shape normalization: return `SplitSummaryResult` or add
  `split_comparison` rows while preserving `summary`.
- Dedicated pattern later: not needed; the current split primitive fits on/off.
- Explicitly mark out of UI scope: not appropriate because the route is already
  mapped and understandable when data exists.

### Recommendation

Keep `player_on_off` as `summary`-sourced split rows for the raw product. Treat
the current contract as acceptable current behavior, not a bug. Revisit
normalization only if a broader structured-result cleanup creates a migration
path that can preserve backward compatibility.

If normalization is later approved, the safest path is backend-first and
compatibility-preserving:

1. Return bucket rows in `split_comparison`.
2. Keep `summary` available for at least one compatibility wave, either as a
   context row or as duplicated bucket rows with clear docs.
3. Change `routeToPattern` to the default split section only after tests cover
   both old and new shapes or after the old shape is explicitly removed.

Risks of normalization now:

- Breaks API clients expecting `sections.summary` for `player_on_off`.
- Requires coordinated updates to backend section tests, frontend section tests,
  route mapping tests, shape tests, and table smoke tests.
- May introduce duplicated or ambiguous `summary` semantics if both old and new
  sections are emitted without a clean compatibility story.

## Target Review: `playoff_appearances` Single-Team Variant

### Current Behavior

Backend:

- Route: `playoff_appearances`.
- Builder: `src/nbatools/commands/playoff_history.py::build_playoff_appearances_result`.
- Without `team`, returns `LeaderboardResult`.
- With `team`, returns `SummaryResult`.

Leaderboard shape:

- Sections: `leaderboard`.
- Observed first-row fields:
  `rank`, `team_abbr`, `team_name`, `appearances`, `round`, `seasons`.

Single-team summary shape:

- Sections: `summary`, `by_season`.
- Observed `summary` fields:
  `team_name`, `appearances`, `round`, `season_start`, `season_end`.
- Observed `by_season` fields:
  `season`, `games`, `wins`, `losses`, `win_pct`.

Representative query observations in this checkout:

| Query | Observed route | Status | Query class | Sections |
|---|---|---|---|---|
| `most playoff appearances` | `playoff_appearances` | `ok` | `leaderboard` | `leaderboard` |
| `teams with most Finals appearances` | `playoff_appearances` | `ok` | `leaderboard` | `leaderboard` |
| `Lakers playoff appearances` | `playoff_appearances` | `ok` | `summary` | `summary`, `by_season` |
| `Lakers Finals appearances` | `playoff_appearances` | `ok` | `summary` | `summary`, `by_season` |
| structured `playoff_appearances(team="LAL", start_season="1996-97", end_season="2024-25")` | `playoff_appearances` | `ok` | `summary` | `summary`, `by_season` |

Observed structured single-team first summary row:

```text
team_name=Los Angeles Lakers
appearances=21
round=Playoffs
season_start=1996-97
season_end=2024-25
```

Frontend:

- `routeToPattern.ts` maps every `playoff_appearances` result to:
  `{ type: "leaderboard", sectionKey: "leaderboard", metricKey: "appearances", sentenceMetricLabel: "playoff appearances" }`.
- `LeaderboardResult` reads only `sections.leaderboard`.
- For a single-team summary result with only `summary` and `by_season`,
  `LeaderboardResult` returns `null`.
- `ResultRenderer` does not fall back once a route has a specific pattern.
- Result shape classification can still say `leaderboard_table` because it is
  based on route mapping, not on section compatibility.

So the current behavior is not a fallback or a wrong leaderboard table. It is a
successful backend result that can render as an empty result shell in the UI.

### Product Assessment

Users reasonably expect two distinct shapes:

- `most playoff appearances` means a ranked team leaderboard.
- `Lakers playoff appearances` means a direct answer for the Lakers and the
  seasons in which they appeared.

The single-team shape is important for the raw product now because it is already
reachable through natural query routing and explicitly covered by backend tests.
Avoiding the backend variant would regress supported behavior rather than reduce
scope.

The best UI fit is not a generic leaderboard and not a brand-new broad pattern.
It should use the existing playoff-history display family with a small
appearances-oriented mode:

- Hero: team, appearance count, round label, season range.
- Table: `Season`, `Record`, `Games`, `Win Pct`.
- Do not show `Round Reached` when rows do not contain round/deepest-round data.
- Preserve caveats about round data before 2001-02.

### Options

- Keep current behavior and document it: not recommended, because it leaves an
  `ok` result with no visible UI.
- Small frontend mapping/rendering change: recommended.
- Small backend section-shape normalization: not recommended. The backend
  distinction between leaderboard and single-team summary is product-correct.
- Dedicated pattern later: possible if playoff appearances grows beyond the
  existing playoff-history family.
- Explicitly mark out of UI scope: not recommended because natural queries and
  backend tests already support the variant.

### Recommendation

Support the single-team `playoff_appearances` variant in the UI. Implement it as
a small frontend section-shape branch under the existing route, not a backend
change:

1. Keep current leaderboard mapping when `sections.leaderboard` exists.
2. For `playoff_appearances` with `sections.summary`, map to a
   playoff-history/appearances display.
3. In that display, hide `Round Reached` when the row set lacks round fields.
4. Add frontend tests for both `playoff_appearances` shapes.

## Decision Matrix

| Target | Current behavior | Product risk | Options | Recommendation | Why | Implementation size | Test impact |
|---|---|---|---|---|---|---|---|
| `lineup_summary` | Backend returns `SummaryResult.summary` with source-backed fields including `lineup_name`, `player_names`, `minutes`, `off_rating`, `def_rating`, `net_rating`, `pace`, `ts_pct`; frontend maps to `entity_summary` and currently recognizes `lineup`, `lineup_members`, or `members`. | Medium. No local coverage means most live examples return no-result, but successful source-backed rows can miss lineup-specific hero labeling. | Keep and document; small frontend label support; backend add alias fields; dedicated lineup pattern later; mark out of UI scope. | Keep `entity_summary`, add frontend label support for actual backend keys, defer dedicated pattern. | Raw product only needs a clear one-row answer now; backend/frontend row-key mismatch is the real narrow bug. | Small frontend rendering change. | Update `wave2TableContracts.test.tsx` fixture to use actual backend keys; add label resolver coverage; no backend tests needed unless backend aliases are added. |
| `player_on_off` | Backend returns `SummaryResult.summary` rows keyed by `presence_state`; frontend renders split table over `summary` using `bucketKey=presence_state`. | Low. Semantically inconsistent with other split routes but display is understandable and tests lock it. | Keep and document; frontend remap after backend change; backend normalize to `split_comparison`; dedicated pattern later; mark out of UI scope. | Keep current behavior and document it as acceptable current contract. | Normalization would mostly improve internal consistency while risking a stable API shape. | None now. Later normalization would be small-to-medium backend and frontend change. | None now. Later change would touch backend section tests, route mapping tests, shape tests, and table smoke tests. |
| `playoff_appearances` single-team | Backend returns `summary` plus `by_season` for team-specific appearance queries; frontend always expects `leaderboard`. | High. Natural queries like `Lakers playoff appearances` return `ok` with sections but can render no visible pattern. | Keep and document; small frontend section-shape branch; backend force leaderboard/no-result; dedicated pattern later; mark out of UI scope. | Add UI support now using existing playoff-history family with an appearances mode. | The two shapes match user intent: league ranking vs single-team direct answer. Backend support already exists and should not be hidden. | Small frontend mapping/rendering change. | Add routeToPattern/result-shape coverage for summary variant; add table smoke test for `summary` + `by_season`; keep existing leaderboard tests. |

## Recommended Implementation Wave

Recommend Option E: a tiny combined cleanup for two frontend display gaps plus
one explicit no-change decision.

Exact next scope:

1. `lineup_summary`: keep the `entity_summary` pattern, but make
   `EntitySummaryResult` recognize actual backend label fields:
   `lineup_name`, pipe-delimited `player_names`, and metadata
   `lineup_members`.
2. `playoff_appearances`: keep leaderboard behavior for ranked results, but add
   a summary/appearances display branch when the result has `summary` and
   `by_season` instead of `leaderboard`.
3. `player_on_off`: no production change; update/keep docs that the
   `summary`-sourced split rows are acceptable current behavior.

Why this wave:

- It fixes a confirmed ok-but-blank UI risk for single-team playoff
  appearances.
- It fixes the actual backend/frontend row-key mismatch for lineup summaries
  without inventing a dedicated lineup UI.
- It avoids a contract migration for `player_on_off`, where current behavior is
  understandable and already locked by tests.
- It does not add query support, change backend data contracts, or refactor
  `routeToPattern` into a registry.

Recommended test impact for the next implementation:

- Frontend route mapping tests for both `playoff_appearances` shapes.
- Frontend shape classification tests for single-team `playoff_appearances`.
- Frontend table smoke test using `summary` + `by_season` single-team playoff
  appearances.
- Frontend lineup summary smoke test using actual backend keys
  (`lineup_name` / `player_names`), not only synthetic `lineup`.
- `npm run build` after frontend source changes.

No backend tests should be required unless the implementation changes backend
section names or row fields.

## Risks / Stop Conditions For Implementation

- Stop if the proposed single-team `playoff_appearances` display requires a
  broad `PlayoffHistoryResult` redesign. The approved next scope should be a
  route/section-specific branch plus narrow column handling only.
- Stop if the implementation requires changing backend `playoff_appearances`
  result shape; the current backend shape is product-correct.
- Stop if lineup support expands into multi-row breakdowns, game logs, or
  filters. That should become a dedicated lineup-pattern phase, not part of this
  cleanup.
- Stop if `player_on_off` normalization requires removing `summary` rows without
  a compatibility path. That is not justified by current product value.
- Stop if tests reveal local fixture assumptions diverge from source-backed row
  contracts again; update fixtures to match backend rows before changing display
  behavior.

## Validation / Confidence

Commands run:

```bash
.venv/bin/python -c "<representative query sweep through query_service>"
```

Representative queries executed:

| Query | Route | Status | Sections |
|---|---|---|---|
| `lineup with Tatum and Jaylen Brown` | `lineup_summary` | `no_result` / `unsupported` | none |
| `net rating with Tatum and Jaylen Brown together` | `lineup_summary` | `no_result` / `unsupported` | none |
| `Jokic on off` | `player_on_off` | `no_result` / `unsupported` | none |
| `most playoff appearances` | `playoff_appearances` | `ok` | `leaderboard` |
| `teams with most Finals appearances` | `playoff_appearances` | `ok` | `leaderboard` |
| `Lakers playoff appearances` | `playoff_appearances` | `ok` | `summary`, `by_season` |
| `Lakers Finals appearances` | `playoff_appearances` | `ok` | `summary`, `by_season` |
| structured `playoff_appearances(team="LAL", start_season="1996-97", end_season="2024-25")` | `playoff_appearances` | `ok` | `summary`, `by_season` |

Limitations:

- Local trusted lineup and on/off datasets were unavailable for the representative
  natural queries, so successful `lineup_summary` and `player_on_off` row
  behavior is inferred from the builders and source-backed tests.
- No frontend browser rendering was executed in this discovery pass.
- No production code or tests were changed in this preflight.
