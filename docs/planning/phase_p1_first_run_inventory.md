# Phase P1 First-Run Inventory

> **Role:** Planning inventory for
> [`phase_p1_work_queue.md`](./phase_p1_work_queue.md) item 1. This document
> records the current first-run UI surfaces, starter-query fixtures, freshness
> states, and mobile/accessibility checks that Phase P1 will use before runtime
> first-run changes begin.

---

## Current First-Run Path

The first-run screen is the `App.tsx` state where no query is loading, no
result exists, and no error exists:

```ts
const showEmpty = !loading && !hasResult && !hasError;
```

Current surface ownership:

| Surface | Current owner | Current behavior | P1 implication |
| --- | --- | --- | --- |
| App frame | `AppShell.tsx` / `AppShell.module.css` | Header, freshness status region, primary query/results column, secondary saved/history/tools column. Collapses below 900px. | Keep the work-focused shell. P1 should improve the first-run content inside it, not replace it with a marketing page. |
| Header | `App.tsx` | Brand block, API online/offline pill, version badge. | Keep API health visible; do not overload the header with first-run instructions. |
| Freshness | `FreshnessStatus.tsx` | Collapsible status card appears in `AppShell` status region only when `apiOnline` is true and `/freshness` returns data. | P1 should make first-run freshness more prominent while preserving the existing detailed status and API contract. |
| Query controls | `QueryBar.tsx` | Label, text input, clear icon, submit button, disabled/loading state. `App.tsx` owns query execution and URL state. | Query bar remains the first-run primary action. Starter queries must use the same handlers as manual queries. |
| Starter examples | `SampleQueries.tsx` | Flat list of button strings that immediately submit through `handleSampleSelect`. | Replace with grouped starter controls by intent without adding parser/routing logic to React. |
| Empty state | `EmptyState.tsx` | Passive card with "Ready", title, description, and non-clickable tip chips. | Convert into the first-run surface that explains the product and coordinates with grouped starters. |
| Secondary panels | `SavedQueries.tsx`, `QueryHistory.tsx`, `DevTools.tsx` | Always present in the secondary column/stack. Query history starts empty. | Keep available, but avoid making them the dominant first-run path. Mobile ordering and focus still need verification. |
| Result path after starter | `App.tsx`, `ResultEnvelope.tsx`, `ResultSections.tsx` | Starter query runs through `pushQuery`, `runQuery`, query history, result envelope, result actions, and the Part 2 renderer dispatcher. | P1 runtime work must preserve URL state, history insertion, result actions, and renderer ownership. |

No runtime blocker was found in the current ownership. The frontend already has
the right event path for starter-query buttons; P1 needs better first-run
composition, grouping, and freshness prominence.

---

## Starter-Query Fixture Set

Starter queries should be short, familiar, and backed by query families that
Part 2 already redesigned. P1 should use one primary starter from each group
and may include the secondary starter if the layout can support two per group
without crowding mobile.

| Group | Primary starter | Expected route / query class | Part 2 renderer | Secondary starter |
| --- | --- | --- | --- | --- |
| Players | `Jokic last 10 games` | `player_game_summary` / `summary` | `PlayerSummarySection.tsx` | `Curry 5+ threes` -> `player_game_finder` / `finder` |
| Teams | `Celtics home vs away 2024-25` | `team_split_summary` / `split_summary` | `SplitSummaryCardsSection.tsx` | `Lakers longest winning streak 2024-25` -> `team_streak_finder` / `streak` |
| Comparisons | `Jokic vs Embiid 2024-25` | `player_compare` / `comparison` | `PlayerComparisonSection.tsx` | `Lakers vs Celtics since 2010` -> head-to-head comparison path |
| Records | `Celtics record 2024-25` | `team_record` / `summary` | `TeamRecordSection.tsx` | `best record since 2015` -> record leaderboard path |
| History | `Lakers playoff history` | `playoff_history` / `summary` | `PlayoffSection.tsx` | `Lakers vs Celtics playoff history` -> `playoff_matchup_history` / `comparison` |

Fixture notes:

- These are presentation fixtures only. React should not infer routes, parse
  slots, or validate NBA semantics; it should submit the selected query string
  through the existing natural-query flow.
- The examples intentionally cover summary, split, finder, streak, comparison,
  record, leaderboard, and playoff result families without requiring new API
  fields.
- Avoid "today's highlights" in P1. That optional plan idea would require a
  product decision about backend-generated recommendations and belongs outside
  the first P1 runtime pass.
- Avoid unsupported historical split examples such as `Celtics finals record`
  or `LeBron record in the Finals`; the query catalog explicitly keeps those
  outside the current shipped playoff/era-history surface.

---

## Freshness States

`FreshnessStatus.tsx` consumes `FreshnessResponse.status` values:

| State | Current label behavior | P1 first-run target |
| --- | --- | --- |
| `fresh` | Shows `Data through <date>` when `current_through` exists, with a success badge. | Promote as a compact confidence signal near the first-run surface and keep details expandable. |
| `stale` | Shows `Data through <date>` when present, with a warning badge. | Make visually distinct before the first query; stale state should not be hidden in a sidebar or secondary-only region. |
| `unknown` | Shows "Freshness unknown" when no date exists, with a neutral badge. | Keep honest and visible; pair with concise copy that avoids implying current data. |
| `failed` | Shows "Last refresh failed" or the last date with a danger badge and optional error detail. | Keep prominent enough that a friend will not mistake stale/failed data for current results. |
| API offline / fetch failure | `App.tsx` hides freshness when health is offline; `FreshnessStatus` returns `null` if `/freshness` fails. | P1 can keep health handling separate, but first-run copy should not promise freshness when the API/freshness endpoint is unavailable. |

Result-level freshness remains owned by `ResultEnvelope.tsx` after a query
returns. P1 should not remove that result-level metadata; the first-run
freshness work is additive before a result exists.

---

## Mobile and Accessibility Fixtures

P1 should verify the first-run path at these widths:

| Fixture | Viewport | Why it matters |
| --- | --- | --- |
| Narrow phone | 360 x 740 | Stress long starter labels and card padding below the 640px shell breakpoint. |
| Large phone | 390 x 844 | Common phone width for first-run touch target checks. |
| Tablet | 768 x 1024 | Single-column shell near tablet size; secondary panels stack after the primary workspace. |
| Desktop | 1280 x 900 | Baseline two-column shell with first-run and secondary panels visible. |

Mobile/accessibility checks for P1 runtime items:

- Query input remains first in the primary flow, with visible focus and usable
  clear/submit controls.
- Starter groups use real buttons, not passive chips, and preserve the same
  query execution path as manual input.
- Long group labels and starter-query strings wrap without causing horizontal
  shell overflow or unstable control heights.
- Freshness summary and details stay inside the status/first-run region at
  phone widths.
- Secondary saved/history/tools panels remain reachable after the primary
  first-run path, but they should not interrupt a new user's route to the query
  bar and starter controls.

---

## Residuals and Non-Blockers

- P1 item 1 found no ambiguous decision that blocks runtime work.
- Browser screenshot capture across real devices remains a later P1/P3
  verification task; this inventory names the target widths but does not
  produce screenshots.
- Loading, no-result, network-error, and empty-result copy refinements belong
  to Phase P2 unless they are directly required by the P1 first-run screen.
- Keyboard shortcuts, transitions, number animation, tooltips, and copy/share
  confirmation polish remain Phase P4 scope.
