# Phase P4 Felt Polish Inventory

> Inventory for
> [`phase_p4_work_queue.md`](./phase_p4_work_queue.md). This records the
> current interaction state, target P4 behavior, owner files, risk areas, and
> verification fixtures before runtime felt-polish work starts.

---

## Scope

Phase P4 covers small UI interactions that make the already-designed product
feel finished:

- keyboard shortcuts and query-history navigation
- copy/share feedback and clipboard failure handling
- stat abbreviation help and presentation-level number formatting polish
- restrained transitions and optional hero-stat value motion
- query history and saved-query ergonomics

Out of scope for P4:

- parser or routing changes
- new analytics or NBA fact computation in React
- result-contract changes unless a later item explicitly identifies a required
  API-owned value
- deployment, custom domain, and production data sync work, which remain Track B

---

## Already Complete Before P4

| Area | Current shipped state | Evidence/source |
| --- | --- | --- |
| First-run surface | Empty state, starter query groups, first-run freshness banner, and first-run keyboard flow are already shipped. | `phase_p1_work_queue.md`, `frontend/src/components/EmptyState.tsx`, `frontend/src/components/SampleQueries.tsx`, `frontend/src/test/FirstRun.test.tsx` |
| Loading/error/no-result states | Designed loading, no-result, unsupported/ambiguous, empty-section, and network/API failure states are already shipped. | `phase_p2_work_queue.md`, `frontend/src/components/Loading.tsx`, `frontend/src/components/NoResultDisplay.tsx`, `frontend/src/components/ErrorBox.tsx` |
| Mobile containment | P3 verified shell, first-run/non-result states, result chrome, secondary panels, table-heavy results, and card-heavy renderers at phone width. | `phase_p3_work_queue.md`, `docs/operations/ui_guide.md` |
| URL deep links | Natural and structured queries are reflected in URL state; refresh and browser back/forward are supported. | `frontend/src/hooks/useUrlState.ts`, `frontend/src/test/useUrlState.test.ts` |
| Copy/share entry points | Result actions expose Copy Link, Copy Query, and Copy JSON buttons. | `frontend/src/App.tsx`, `frontend/src/components/CopyButton.tsx` |
| Saved/history surfaces | Query history, saved queries, tags, pinning, edit/run/delete, import/export, and save-from-history exist. | `frontend/src/components/QueryHistory.tsx`, `frontend/src/components/SavedQueries.tsx`, `frontend/src/storage/savedQueryStorage.ts` |

---

## Surface Inventory

| Surface | Owner files | Current behavior | P4 target | Risks | Verification |
| --- | --- | --- | --- | --- | --- |
| Query input shortcuts | `App.tsx`, `QueryBar.tsx`, `useQueryHistory.ts` | Input autofocuses on first load. Enter submits through the form. Clear button empties text. No app-level `Cmd+K` / `Ctrl+K`, Escape clear, or up/down history recall exists. | `Cmd+K` / `Ctrl+K` focuses and selects the query input; Escape clears only when appropriate; up/down from the query input recalls session queries; Enter submits recalled text. | Overriding normal text editing, firing while a dialog or dev-tool textarea is active, breaking URL state or existing history buttons. | `frontend/src/test/FirstRun.test.tsx` or focused App/QueryBar tests; browser smoke at 390x844 and 1280x900. |
| Query history panel | `QueryHistory.tsx`, `QueryHistory.module.css`, `useQueryHistory.ts` | Newest entries appear first. Query text can be clicked or Enter-activated to rerun. Edit, Rerun, Save, and Clear actions exist. History is in-session only. | Keyboard-friendly history selection and predictable recall order from the input; action names and focus order stay clear. | Confusing browser history with app query history; stale index after new query; long query labels on mobile. | Component tests plus browser fixture after running several queries. |
| Copy/share buttons | `CopyButton.tsx`, `CopyButton.module.css`, `useUrlState.ts`, `App.tsx` | Uses `navigator.clipboard.writeText`, falls back to hidden textarea and `document.execCommand("copy")`, then shows `✓ Copied` for 1500ms. Failure after fallback is not surfaced. Timers are not explicitly cleaned up. | Accessible success and failure feedback; repeated clicks reset cleanly; unmounts do not update stale state; share URL remains URL-state based. | Clipboard API unavailable in insecure contexts, false success when fallback fails, timer leaks in tests, button width shift on mobile. | `frontend/src/test/Button.test.tsx`, `frontend/src/test/useUrlState.test.ts`, browser copy-button smoke. |
| Stat abbreviation help | `Stat.tsx`, `StatBlock.tsx`, owner result renderers, `tableFormatting.ts` | Compact labels such as PTS, REB, AST, eFG%, TS%, USG%, AST%, REB%, TOV%, 3PM, and +/- render as short text. No help text or tooltip is supplied. | Common compact stat labels expose accessible help through a nonintrusive title/tooltip/label mechanism. Dense cards remain clean. | Adding visible explanatory clutter, applying incorrect definitions, widening stat cards, duplicating help logic across owners. | Design-system/component tests for help text; browser hover/focus check on player summary, player comparison, leaderboard, and streak fixtures. |
| Number formatting polish | `tableFormatting.ts`, stat owner components | Percent columns convert 0-1 values to percent, large integers use locale formatting, small decimals show one decimal. Formatting is presentation-only. | Inventory-driven touch-ups only where labels/values are obviously inconsistent; no engine-value mutation. | Accidentally changing raw values, over-rounding detail tables, inconsistent percent treatment between card stats and tables. | Focused formatter tests and renderer tests for changed labels/values. |
| State transitions | `App.tsx`, `App.module.css`, state components, tokens | Buttons/query controls have hover/focus transitions; skeleton/spinner animate. Result, empty, loading, and error surfaces swap immediately. | Subtle token-driven transitions between empty/loading/error/result states that do not shift layout or delay data. | Motion that feels slow, animation during reduced-motion preference, layout flicker, mobile overflow. | Component tests for reduced-motion class/behavior where practical; browser screenshots at 390x844 and 1280x900. |
| Hero-stat value motion | `Stat.tsx`, `Stat.module.css`, renderer components | Stat values render immediately. No count-up or value motion exists. | Optional motion for hero stat values where useful, disabled for reduced-motion users and stable for nonnumeric values. | Misrepresenting values during animation, animating table cells, reflow from changing digit width, locale/percent values that are hard to parse safely. | Unit/component tests for numeric/non-numeric/reduced-motion behavior; browser check on player/team summary and count fixtures. |
| Saved queries | `SavedQueries.tsx`, `SavedQueries.module.css`, `SaveQueryDialog.tsx`, `savedQueryStorage.ts` | Saved queries are persisted locally. Tags, pinning, import/export, edit, delete, and clear-all exist. Bad import files are silently ignored. | Cleaner action naming/focus order, visible import failure if needed, stable empty/filter states, mobile-safe long labels/tags. Storage format stays compatible. | Breaking persisted data, noisy confirmations, hidden file input accessibility, long tags widening the sidebar. | `frontend/src/test/SavedQueries.test.tsx`, storage tests, mobile browser fixture with long saved labels/tags. |

---

## P4 Fixture Set

Use API-backed pages for browser evidence when interaction state depends on real
results. Use component tests for deterministic keyboard, clipboard, formatter,
and reduced-motion behavior.

### Natural-query fixtures

| Query | Purpose | Viewports |
| --- | --- | --- |
| `Jokic last 10 games` | Player summary, hero stats, copy/share actions, stat help, value motion, history entry. | 390x844, 1280x900 |
| `Celtics summary 2024-25` | Team theming, team summary stats, freshness/result chrome, detail table containment. | 390x844, 1280x900 |
| `Jokic vs Embiid 2024-25` | Player comparison cards, metric cards, long labels, stat help. | 390x844, 1280x900 |
| `Lakers head-to-head vs Celtics since 2010` | Neutral multi-team head-to-head cards and detail tables. | 390x844 |
| `top 10 scorers 2024-25` | Leaderboard metric labels, detail table containment, copy JSON. | 390x844 |
| `how many Jokic games with 30+ points and 10+ rebounds since 2021` | Count answer card, query-history save flow, optional value motion. | 390x844 |
| `Lakers playoff history` | Playoff card context labels and stat help on postseason surfaces. | 390x844 |

### Structured-query fixtures

| Route/kwargs | Purpose |
| --- | --- |
| `player_occurrence_leaders` with `{"stat":"pts","min_value":40,"season":"2024-25"}` | Long dynamic event labels, occurrence metric help/formatting. |
| Invalid structured kwargs in Dev Tools | Verify keyboard shortcuts avoid textarea/dev-tool editing and errors stay friendly. |

### Non-result fixtures

| State | Purpose |
| --- | --- |
| First-run empty state | Confirm `Cmd+K` / `Ctrl+K` focus behavior and no regression to starter-query flow. |
| Loading state | Verify state transition does not shift layout or conflict with skeleton motion. |
| API-offline query error | Verify transition/error behavior and retry control remain usable. |
| Saved queries with long labels/tags | Verify saved-query ergonomics and mobile containment. |

---

## Test Map

| P4 item | Primary tests | Browser evidence |
| --- | --- | --- |
| Item 2 - keyboard shortcuts/history | `frontend/src/test/FirstRun.test.tsx` or focused App/QueryBar tests; `useQueryHistory` tests if hook changes. | First-run plus several query result states at 390x844. |
| Item 3 - copy/share feedback | `frontend/src/test/Button.test.tsx`; `frontend/src/test/useUrlState.test.ts`. | Result action panel with Copy Link, Copy Query, Copy JSON at 390x844. |
| Item 4 - stat help/formatting | Design-system Stat tests; formatter tests; affected renderer tests. | Player summary, player comparison, leaderboard, streak/card fixtures. |
| Item 5 - transitions/value motion | Reduced-motion and stat rendering tests; App state tests if state wrapper changes. | Loading -> result, result -> result, and error -> retry at 390x844 and 1280x900. |
| Item 6 - history/saved ergonomics | `frontend/src/test/SavedQueries.test.tsx`, storage tests, QueryHistory tests. | Long saved labels/tags in secondary panel at 390x844. |

All runtime P4 items should finish with:

- `cd frontend && npm test`
- `cd frontend && npm run build`

Docs-only inventory/handoff items require no local tests.

---

## Residuals To Carry Into P4

- P4 should keep mobile overflow checks from P3 in scope whenever it changes
  action rows, secondary panels, stat cards, or animated regions.
- Copy/share is functional today, but accessible failure feedback and timer
  cleanup are not yet verified.
- Keyboard shortcuts are not shipped beyond native form submit, input autofocus,
  and Enter activation on history/saved-query text controls.
- Stat abbreviation help is absent. Definitions should be conservative and
  common, and should not claim data semantics beyond the displayed metric name.
- Value motion is optional. If it adds complexity, prefer subtle state
  transitions and mark stat count-up as skipped only with an inline rationale in
  the queue item that owns it.

Immediate next action: start
[`phase_p4_work_queue.md`](./phase_p4_work_queue.md) item 2.
