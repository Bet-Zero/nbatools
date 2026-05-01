# Phase P3 Mobile Inventory

> **Role:** Planning inventory for
> [`phase_p3_work_queue.md`](./phase_p3_work_queue.md) item 1. This records
> the mobile verification surfaces, fixtures, risks, and evidence expectations
> for the broader Track A Part 3 mobile pass before runtime fixes begin.

---

## Sources Reviewed

- `docs/planning/phase_p1_first_run_inventory.md`
- `docs/planning/phase_c8_mobile_inventory.md`
- `docs/planning/phase_p2_state_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/AppShell.module.css`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/*Section.tsx`
- `frontend/src/components/*Section.module.css`
- `frontend/src/design-system/DataTable.module.css`

---

## Viewport Set

Use these viewports as the P3 baseline:

| Viewport | Role | Why it matters |
| --- | --- | --- |
| 360 x 740 | narrow phone | Stress shell padding, long query text, starter labels, detail copy, and full-width actions. |
| 390 x 844 | common phone | Main phone fixture for touch-target, no-overflow, and first-screen composition checks. |
| 430 x 932 | large phone | Catches layouts that pass narrow phone but still feel cramped with taller content. |
| 768 x 1024 | tablet | Verifies the single-column shell near the tablet breakpoint and secondary-panel stacking. |
| 1280 x 900 | desktop control | Confirms mobile fixes do not regress the intended desktop layout. |

When a component has a breakpoint near another width, verify one sample just
above and below that breakpoint. Keep the shared viewports above as the
comparable baseline across P3 PRs.

---

## Inherited Coverage

P1 already named first-run mobile and accessibility fixtures for the query bar,
starter queries, empty state, and freshness banner. P1 also shipped the
first-run mobile/accessibility pass. P3 should treat that as a baseline and
verify the full shell again after P2 added new non-result panels.

C8 already ran a dedicated mobile pass across redesigned Part 2 result
components. P3 should not repeat C8 as a planning exercise; it should verify
the integrated product surface after P1/P2 changes, with extra attention to
shell-level overflow, action wrapping, secondary panels, and recently changed
loading/error/empty states.

P2 shipped designed loading, no-result, empty-section, and network/API failure
states. P3 is responsible for mobile containment of those new panels,
especially long notes, caveats, suggestions, details, and retry actions.

---

## Surface Matrix

| Surface | Owner components | Fixture data/query | Mobile risk | Evidence expected |
| --- | --- | --- | --- | --- |
| App shell and header | `App.tsx`, `AppShell.tsx`, `App.module.css`, `AppShell.module.css` | Cold load and a result page at each baseline viewport | Header/status stack, 900px workspace collapse, 640px shell padding, clipped overflow hiding real issues | Screenshot or DOM overflow check at 360/390/768 plus existing app tests if structure changes. |
| Query controls and first-run | `QueryBar`, `SampleQueries`, `EmptyState` | Empty app; long manual query; grouped starters such as `Celtics record 2024-25` and `Lakers playoff history` | Query button full-width behavior, clear button alignment, long starter text, first-run card grid collapse | Existing keyboard-flow test plus screenshot/overflow check. Add tests only if markup changes. |
| Freshness | `FreshnessStatus` | `fresh`, `stale`, `unknown`, `failed`, and API offline fixtures | Banner/panel copy wrapping, expanded season details, failed refresh detail, status button width | Existing freshness tests plus mobile screenshot/overflow check for stale/failed expanded states. |
| Loading and skeleton | `Loading` | Pending natural and structured query promises | Skeleton preview grid, status row, spinner/copy alignment, no implied result data | Existing loading tests plus screenshot/overflow check at phone widths. |
| No-result and empty-section | `NoResultDisplay`, `ResultSections` | `no_match`, `no_data`, `unrouted`, `unsupported`, `ambiguous`, `error`, `empty_sections` | Details and suggestions wrapping, badge/title stacking, no page overflow with long notes/caveats | Existing state tests plus mobile fixture with intentionally long notes/caveats. |
| Client/API failure | `ErrorBox`, `App.tsx`, `DevTools` | Natural failure with retry, structured failure with retry, API offline failure | Retry button wrapping, failure details, offline title duplication with shell status, no stack trace exposure | Existing retry/offline tests plus mobile screenshot/overflow check. |
| Result envelope and actions | `ResultEnvelope`, `CopyButton`, `RawJsonToggle`, App result action panel | Successful result with route, notes, caveats, alternates, copy/share/save actions, raw JSON open | Action wrapping, alternate-query buttons, route/status metadata chips, raw JSON containment | Existing result-envelope/copy tests plus screenshot/overflow check with raw JSON expanded. |
| Secondary panels | `SavedQueries`, `SaveQueryDialog`, `QueryHistory`, `DevTools` | Empty and populated saved queries; long labels/tags; long query history; structured route with long kwargs | Secondary column stacking, details panels, dialog max-width, textarea/pre overflow, action rows | Existing saved-query/history/dev-tools tests plus phone/tablet visual check. |
| Generic table shell | `DataTable`, design-system `DataTable` | Wide synthetic rows and fallback section rows | Table scroll must stay inside wrapper; table must not widen the page | Existing table tests plus DOM overflow check on wrapper/page. |
| Finder and player-game finder | `FinderSection`, `PlayerGameFinderSection` | `player_game_finder`, generic `game_finder`, sparse finder row, long opponent/team labels | Game cards, stat grid, W/L badge, opponent row, detail table containment | Existing C4/C8 coverage plus mobile screenshot/overflow check. |
| Leaderboards and count | `LeaderboardSection`, `OccurrenceLeaderboardSection`, `CountSection`, leaderboard paths in `PlayoffSection` | `top 10 scorers 2024-25`, `most 40 point games 2024-25`, direct count result, playoff leaderboard | Ranked row grid, metric label/value, event label, count hero, detail table containment | Existing C2/C6/C7 coverage plus mobile screenshot/overflow check. |
| Summary and record cards | `PlayerSummarySection`, `TeamSummarySection`, `TeamRecordSection`, `SummarySection` | `Jokic last 10 games`, `Celtics record 2024-25`, sparse/missing identity fixtures, long names | Hero identity/stat grid, team logo/title, scoped team wash, record grid, recent-game strip | Existing C1/C5/C8 coverage plus phone/tablet visual check. |
| Comparison and split cards | `ComparisonSection`, `PlayerComparisonSection`, `HeadToHeadSection`, `SplitSummarySection`, `SplitSummaryCardsSection` | `Jokic vs Embiid 2024-25`, `Lakers vs Celtics since 2010`, `Celtics home vs away 2024-25`, long bucket labels | Side-by-side cards stacking, metric card labels, participant cards, bucket cards, detail tables | Existing C3/C5/C7/C8 coverage plus mobile screenshot/overflow check. |
| Streak and playoff cards | `StreakSection`, `PlayoffSection` | `Lakers longest winning streak 2024-25`, `Lakers playoff history`, `Lakers vs Celtics playoff history`, long round labels | Condition/status badges, answer blocks, context chips, matchup cards, dynamic round/team columns | Existing C6/C7/C8 coverage plus phone/tablet visual check. |

---

## Manual Browser Fixtures

Use real queries when data is available. If local data is unavailable or a
fixture needs an edge case, use existing frontend test payloads or structured
API responses with the same shape.

| Fixture | Primary surfaces | Viewports |
| --- | --- | --- |
| Cold load with API online/fresh | Shell, first-run, query bar, starter queries, freshness banner | 360 / 390 / 768 / 1280 |
| Cold load with stale or failed freshness | Freshness trust messaging and expanded details | 360 / 390 / 768 |
| Pending `Jokic last 10 games` | Loading skeleton | 360 / 390 / 768 |
| Failed `Jokic last 10 games`, then retry | ErrorBox, retry, query URL preservation | 360 / 390 / 768 |
| `Jokic last 10 games` | Player summary hero, recent games, detail table, result actions | 360 / 390 / 768 / 1280 |
| `Celtics record 2024-25` | Team record cards, scoped team theme, detail table | 360 / 390 / 768 / 1280 |
| `Celtics home vs away 2024-25` | Split cards and comparison table | 360 / 390 / 768 |
| `Jokic vs Embiid 2024-25` | Player comparison cards and metric detail | 360 / 390 / 768 |
| `Lakers vs Celtics since 2010` | Head-to-head cards and neutral multi-team layout | 360 / 390 / 768 |
| `top 10 scorers 2024-25` | Generic leaderboard and full leaderboard table | 360 / 390 / 768 |
| `most 40 point games 2024-25` | Occurrence leaderboard dynamic labels | 360 / 390 / 768 |
| `Lakers longest winning streak 2024-25` | Streak answer and detail rows | 360 / 390 / 768 |
| `Lakers playoff history` | Playoff summary, context chips, long detail labels | 360 / 390 / 768 |
| Raw JSON expanded on any successful result | Raw JSON containment | 360 / 390 |
| Saved queries and dev tools expanded | Secondary panel stack, save dialog, long kwargs | 360 / 390 / 768 |

---

## Automated Evidence Targets

Use automated tests for behavior and structural guarantees that jsdom can
verify:

- Owned routes still dispatch to the intended renderer.
- Long labels, notes, caveats, player/team names, split buckets, and structured
  kwargs render without throwing.
- Retry, copy/share, save-query, history, URL-state, raw JSON, and dev-tools
  behaviors remain intact.
- Detail sections remain present after mobile-specific markup changes.

Use browser or screenshot evidence for layout guarantees that jsdom cannot
prove:

- No page-level horizontal overflow at the P3 baseline widths.
- Tables scroll inside table wrappers rather than widening the whole page.
- Buttons and action groups wrap without overlapping adjacent text.
- Long names/details remain readable and do not clip.

Runtime P3 PRs should record the mobile evidence they used in the PR body or
queue item notes when CSS/layout changes are material.

---

## P3 Item Mapping

| P3 item | Surfaces covered |
| --- | --- |
| Item 2 | App shell, query controls, first-run, freshness, loading, no-result, and error states |
| Item 3 | Result envelope/actions, copy/share/save, raw JSON, saved queries, query history, dev tools, save dialog |
| Item 4 | DataTable, finder, player-game finder, leaderboards, occurrence leaderboards, count, and table-heavy playoff/detail sections |
| Item 5 | Player/team summaries, team records, comparison, head-to-head, split cards, streaks, and card-heavy playoff sections |

---

## Residuals and Non-Blockers

- No ambiguous decision blocks P3 runtime work.
- This inventory names the verification fixtures but does not produce browser
  screenshots; runtime items should collect evidence when they change layout.
- The exact browser tooling can be chosen per item. The acceptance target is
  evidence of no mobile overflow and no incoherent wrapping, not a specific
  screenshot tool.
- P4 remains responsible for felt-polish features such as transitions,
  confirmation feedback, keyboard shortcuts, and stat/tooltips after mobile
  containment is verified.
