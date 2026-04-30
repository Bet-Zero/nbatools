# Phase P1 Work Queue

> **Role:** Track A Part 3 first-run queue for
> [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md) -
> _landing/empty state, starter queries, freshness banner, and first-run mobile
> polish._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then immediately move on to the next unchecked item and repeat.
> Continue working items in order without stopping until every item is checked
> `[x]` or you hit a genuine blocker (failing tests you cannot resolve, missing
> credentials, an ambiguous decision that needs the user). If blocked, leave the
> item marked `[~]` with an inline note and stop. Do not stop merely because one
> item finished - the default is to keep going.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## Phase P1 goal

Make the first-run experience explain the app quickly, guide a new user to a
useful first query, and surface data freshness before a result exists. P1
should preserve the work-focused app shell from Track A Part 1/2 while making
the empty state feel like the actual product, not a placeholder.

Guardrails:

- Build the usable first screen, not a marketing page. The query bar remains
  the primary action.
- Starter queries must be supported by the current engine/API and should land
  on redesigned Part 2 result layouts.
- Do not move parser, routing, or analytics logic into React. The frontend
  selects example strings and renders API responses only.
- Freshness messaging must remain honest. Do not hide stale or unknown data
  state for visual cleanliness.
- Keep mobile first-run behavior explicit: no overlapping text, no horizontal
  shell overflow, and touch targets remain usable.

---

## 1. `[x]` Inventory first-run surfaces and starter-query fixtures

**Why:** P1 should start with a concrete first-run matrix so the landing work
does not accidentally depend on unsupported examples or undocumented freshness
states.

**Scope:**

- Audit the current first-run path across `App.tsx`, `EmptyState.tsx`,
  `SampleQueries.tsx`, `FreshnessStatus.tsx`, `QueryBar.tsx`, and the shell
  layout.
- Choose representative starter-query fixtures for Players, Teams,
  Comparisons, Records, and History using supported query families from Part 2.
- Identify how the freshness banner should appear before and after a query,
  including fresh, stale, unknown, and failed API states.
- Write the inventory as `docs/planning/phase_p1_first_run_inventory.md`.
- Do not change runtime UI behavior in this item.

**Files likely touched:**

- `docs/planning/phase_p1_first_run_inventory.md` (new)
- `docs/planning/phase_p1_work_queue.md`

**Acceptance criteria:**

- Inventory names the first-run surfaces, starter-query groups, freshness
  states, and mobile verification widths P1 will use.
- Starter-query candidates map to supported route/query-class families and
  redesigned result layouts.
- Any ambiguity is captured as a residual or blocker before runtime work starts.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs/files to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/phase_c9_part2_completion_audit.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/FreshnessStatus.tsx`

---

## 2. `[x]` Build the first-run landing/empty surface

**Why:** The initial screen should communicate what nbatools does, keep the
query bar central, and invite a useful first action without reading docs.

**Scope:**

- Redesign the no-query state into a first-run surface that sits inside the
  existing app shell and keeps the query bar as the primary interaction.
- Replace flat starter buttons with grouped starter-query controls for the
  inventory's selected Players, Teams, Comparisons, Records, and History
  examples.
- Keep starter-query selection as presentation-only React behavior that submits
  known query strings through the existing query path.
- Preserve URL/query history behavior when a starter query is selected.
- Add or update focused frontend tests for the first-run copy, starter groups,
  and selection behavior.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/EmptyState.module.css`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/SampleQueries.module.css`
- `frontend/src/test/UIComponents.test.tsx`
- `frontend/src/test/AppTheming.test.tsx` or another focused app test if
  needed
- `docs/planning/phase_p1_work_queue.md`

**Acceptance criteria:**

- First viewport explains the product in one compact surface and makes the
  query action obvious.
- Starter queries are grouped, clickable, keyboard-accessible, and run through
  the same query path as manual input.
- Mobile first-run layout has no horizontal overflow or text overlap at phone
  widths.
- Tests cover the new first-run starter-query behavior.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p1_first_run_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/SampleQueries.tsx`

---

## 3. `[ ]` Promote freshness into the first-run experience

**Why:** A friend should know how current the data is before trusting the first
answer, especially when the app is stale, unknown, or offline.

**Scope:**

- Adjust freshness presentation so the first-run screen has a clear freshness
  signal before any query result exists.
- Preserve the existing detailed `FreshnessStatus` behavior and API contract.
- Make stale, unknown, and failed states visually distinct without using team
  colors or hiding the status in a sidebar-only location.
- Add or update focused frontend tests for first-run freshness rendering and
  status variants.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/components/FreshnessStatus.tsx`
- `frontend/src/components/FreshnessStatus.module.css`
- `frontend/src/test/FreshnessStatus.test.tsx`
- `frontend/src/test/UIComponents.test.tsx` or focused app test if needed
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p1_work_queue.md`

**Acceptance criteria:**

- Freshness is visible before the first query and remains honest for fresh,
  stale, unknown, and failed states.
- The result envelope still shows result-level freshness when a query returns.
- Mobile layout keeps freshness content inside the shell without overlap or
  horizontal overflow.
- UI docs describe the first-run freshness behavior.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p1_first_run_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/FreshnessStatus.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/api/types.ts`

---

## 4. `[ ]` Verify first-run mobile and accessibility polish

**Why:** P1 is not done if the first-run surface only works on desktop or only
for pointer users.

**Scope:**

- Verify first-run layout at phone, tablet, and desktop widths using the P1
  inventory fixtures.
- Tighten CSS for long starter-query text, grouped controls, freshness states,
  empty-state copy, and query-bar focus behavior.
- Check keyboard flow through query input, starter queries, freshness details,
  saved/history/tools side panels, and result actions after a starter query.
- Update docs with verified mobile/accessibility behavior and any residuals
  that should move to later Part 3 phases.

**Files likely touched:**

- `frontend/src/App.module.css`
- `frontend/src/components/EmptyState.module.css`
- `frontend/src/components/SampleQueries.module.css`
- `frontend/src/components/FreshnessStatus.module.css`
- `frontend/src/test/UIComponents.test.tsx`
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p1_work_queue.md`

**Acceptance criteria:**

- First-run screen, starter groups, and freshness banner are usable at phone,
  tablet, and desktop widths.
- Keyboard focus order is coherent and visible for first-run controls.
- Long starter-query labels wrap without changing control heights in a way that
  destabilizes the layout.
- UI docs record the verified first-run mobile/accessibility behavior.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p1_first_run_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.module.css`
- `frontend/src/components/QueryBar.module.css`
- `frontend/src/components/SampleQueries.module.css`
- `frontend/src/components/EmptyState.module.css`

---

## 5. `[ ]` Phase P1 retrospective and P2 handoff

**Why:** Self-propagating final task. It closes the landing/first-run queue and
creates the executable loading/error/empty-states queue.

**Scope:**

- Write the Phase P1 retrospective in this file.
- Draft `phase_p2_work_queue.md` for Track A Part 3 Phase P2.
- Refresh `first_run_and_polish_plan.md` if P1 changes Part 3 priorities,
  phase names, or guardrails.
- Update `product_polish_master_plan.md` so Active Continuation points to Track
  A, Part 3, Phase P2.
- Update `docs/index.md` for the new active Part 3 queue.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_p1_work_queue.md` - check this item and add
  retrospective
- `docs/planning/phase_p2_work_queue.md` (new)
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_p2_work_queue.md` exists with concrete PR-sized loading/error/empty
  state items.
- Active-continuation docs point to Track A Part 3 Phase P2.
- Phase P1 is explicitly closed without implying Track A Part 3 or the whole
  polish plan is complete.
- This item is checked off.

**Tests to run:**

- None (docs/handoff only)

**Reference docs to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/operations/ui_guide.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase P1 is complete. The draft of
`phase_p2_work_queue.md` from item 5 is the handoff artifact for Track A Part 3
Phase P2.
