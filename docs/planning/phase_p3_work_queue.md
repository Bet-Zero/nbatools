# Phase P3 Work Queue

> **Role:** Track A Part 3 broader mobile-verification queue for
> [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md) -
> _explicit mobile verification and fixes across first-run, result chrome,
> secondary panels, and result renderers._
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

## Phase P3 goal

Make the mobile experience explicitly verified rather than assumed. P3 covers
mobile viewport behavior across the app shell, first-run state, loading/error
states, result chrome, secondary panels, table-heavy results, card-heavy
results, and query-class renderers. The goal is not a new visual system; it is
to fix wrapping, overflow, touch-target, scroll-containment, and spacing issues
that only show up on small screens.

Guardrails:

- Do not move parser, filtering, or analytics logic into React while fixing
  mobile rendering.
- Keep table overflow contained inside the data-table wrapper; avoid making the
  whole page horizontally scroll.
- Prefer existing design-system primitives and CSS tokens over one-off mobile
  styling.
- Mobile fixes should preserve desktop layouts unless the desktop layout was
  already broken.
- If a runtime change affects frontend source, run the full frontend test and
  build commands before checking off the item.

---

## 1. `[x]` Inventory mobile verification fixtures and risk areas

**Why:** P3 touches many UI surfaces. Start by naming the viewport fixtures,
owner components, likely overflow risks, and verification approach before
runtime changes.

**Scope:**

- Audit current mobile-sensitive surfaces:
  - app shell, header/status, query bar, starter queries, and first-run state
  - freshness, loading, no-result, and network/API failure states
  - result envelope, copy/share/save actions, raw JSON, saved queries, history,
    and dev tools
  - table-heavy result renderers
  - card-heavy summary/comparison/streak/playoff renderers
- Define the mobile viewport set for P3 verification.
- Map each surface to owner component, fixture query/response, risk type, and
  likely test/screenshot evidence.
- Write the inventory as `docs/planning/phase_p3_mobile_inventory.md`.
- Do not change runtime UI behavior in this item.

**Files likely touched:**

- `docs/planning/phase_p3_mobile_inventory.md` (new)
- `docs/planning/phase_p3_work_queue.md`

**Acceptance criteria:**

- Inventory names each P3 mobile surface, owner component, fixture, risk, and
  verification evidence.
- Inventory distinguishes already-covered P1/C8 mobile checks from broader P3
  checks still required.
- Any ambiguity is captured as a residual or blocker before runtime work
  starts.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs/files to consult:**

- `docs/planning/phase_p1_first_run_inventory.md`
- `docs/planning/phase_c8_mobile_inventory.md`
- `docs/planning/phase_p2_state_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/ResultSections.tsx`

---

## 2. `[ ]` Verify core shell, query, and non-result states on mobile

**Why:** The first mobile impression is the shell, query bar, empty state, and
non-result states before any data table appears.

**Scope:**

- Verify and fix mobile behavior for:
  - `AppShell`, header/status stack, query region, and primary result region
  - `QueryBar`, `SampleQueries`, `EmptyState`, and first-run freshness banner
  - `Loading`, `NoResultDisplay`, and `ErrorBox`
- Ensure long query text, long notes/details, suggestions, and retry actions
  wrap without shell overflow.
- Preserve keyboard/accessibility behavior already covered by P1/P2 tests.
- Update focused frontend tests where a fix changes structure or behavior.
- Update `docs/operations/ui_guide.md` if mobile behavior or ownership notes
  change.

**Files likely touched:**

- `frontend/src/App.module.css`
- `frontend/src/components/AppShell.module.css`
- `frontend/src/components/QueryBar.module.css`
- `frontend/src/components/SampleQueries.module.css`
- `frontend/src/components/EmptyState.module.css`
- `frontend/src/components/FreshnessStatus.module.css`
- `frontend/src/components/Loading.module.css`
- `frontend/src/components/NoResultDisplay.module.css`
- `frontend/src/components/ErrorBox.module.css`
- focused frontend tests as needed
- `docs/planning/phase_p3_work_queue.md`

**Acceptance criteria:**

- Core shell, first-run, loading, no-result, and error states stay within the
  mobile viewport with no page-level horizontal overflow.
- Primary query controls remain thumb-sized and usable on mobile.
- Long messages/details wrap cleanly.
- Tests cover any changed behavior or structure.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p3_mobile_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/Loading.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/ErrorBox.tsx`

---

## 3. `[ ]` Verify result chrome and secondary panels on mobile

**Why:** Result actions and secondary tools can easily crowd the main column on
small screens.

**Scope:**

- Verify and fix mobile behavior for:
  - `ResultEnvelope`
  - result action panel, `CopyButton`, save-query action, and `RawJsonToggle`
  - `SavedQueries`, `SaveQueryDialog`, `QueryHistory`, and `DevTools`
- Ensure action rows wrap without overlapping, dialogs fit narrow viewports,
  and raw JSON/details do not force page-level horizontal scroll.
- Preserve URL/share behavior and saved-query behavior.
- Update focused frontend tests where a fix changes structure or behavior.
- Update `docs/operations/ui_guide.md` if ownership or mobile notes change.

**Files likely touched:**

- `frontend/src/App.module.css`
- `frontend/src/components/ResultEnvelope.module.css`
- `frontend/src/components/CopyButton.module.css`
- `frontend/src/components/RawJsonToggle.module.css`
- `frontend/src/components/SavedQueries.module.css`
- `frontend/src/components/SaveQueryDialog.module.css`
- `frontend/src/components/QueryHistory.module.css`
- `frontend/src/components/DevTools.module.css`
- focused frontend tests as needed
- `docs/planning/phase_p3_work_queue.md`

**Acceptance criteria:**

- Result action controls and secondary panels wrap cleanly on mobile.
- Dialogs and raw JSON remain contained inside the app shell.
- Existing saved-query, history, share-link, and structured-query tests remain
  green.
- Tests cover any changed behavior or structure.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p3_mobile_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/CopyButton.tsx`
- `frontend/src/components/RawJsonToggle.tsx`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/SaveQueryDialog.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/DevTools.tsx`

---

## 4. `[ ]` Verify table-heavy result renderers on mobile

**Why:** Tables are the highest overflow risk in the app and need explicit
containment checks after the result layout work.

**Scope:**

- Verify and fix mobile behavior for:
  - `DataTable`
  - `FinderSection` and `PlayerGameFinderSection`
  - `LeaderboardSection` and `OccurrenceLeaderboardSection`
  - `CountSection`
  - table-heavy playoff/detail sections
- Ensure dense tables scroll inside their own wrapper and do not widen the
  entire page.
- Ensure section headers, counts, and top-row/card summaries wrap cleanly.
- Update focused frontend tests where a fix changes structure or behavior.
- Update `docs/operations/ui_guide.md` if table mobile guidance changes.

**Files likely touched:**

- `frontend/src/components/DataTable.module.css`
- `frontend/src/design-system/DataTable.module.css`
- `frontend/src/components/FinderSection.module.css`
- `frontend/src/components/PlayerGameFinderSection.module.css`
- `frontend/src/components/LeaderboardSection.module.css`
- `frontend/src/components/OccurrenceLeaderboardSection.module.css`
- `frontend/src/components/CountSection.module.css`
- `frontend/src/components/PlayoffSection.module.css`
- focused frontend tests as needed
- `docs/planning/phase_p3_work_queue.md`

**Acceptance criteria:**

- Table-heavy result pages avoid page-level horizontal overflow on mobile.
- Internal horizontal scrolling remains discoverable and contained to table
  wrappers.
- Header/action/count areas wrap without overlapping.
- Tests cover any changed behavior or structure.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p3_mobile_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/design-system/DataTable.tsx`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/OccurrenceLeaderboardSection.tsx`
- `frontend/src/components/CountSection.tsx`
- `frontend/src/components/PlayoffSection.tsx`

---

## 5. `[ ]` Verify card-heavy result renderers on mobile

**Why:** Designed card layouts can still fail on mobile through long names,
dense stat grids, and wide action/detail regions.

**Scope:**

- Verify and fix mobile behavior for:
  - `SummarySection`, `PlayerSummarySection`, and `TeamSummarySection`
  - `ComparisonSection`, `PlayerComparisonSection`, and `HeadToHeadSection`
  - `SplitSummarySection` and `SplitSummaryCardsSection`
  - `TeamRecordSection`
  - `StreakSection`
  - card-heavy playoff layouts
- Ensure long player/team names, missing imagery, dense stat grids, and detail
  rows wrap without overlap.
- Preserve team-theming behavior and neutral multi-team behavior.
- Update focused frontend tests where a fix changes structure or behavior.
- Update `docs/operations/ui_guide.md` if renderer mobile guidance changes.

**Files likely touched:**

- renderer module CSS under `frontend/src/components/`
- focused frontend tests as needed
- `docs/planning/phase_p3_work_queue.md`

**Acceptance criteria:**

- Card-heavy result renderers remain readable at mobile widths.
- Long names and dense stats wrap without clipping or overlap.
- Team-themed and neutral surfaces remain visually coherent.
- Tests cover any changed behavior or structure.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p3_mobile_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/TeamSummarySection.tsx`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/HeadToHeadSection.tsx`
- `frontend/src/components/SplitSummarySection.tsx`
- `frontend/src/components/SplitSummaryCardsSection.tsx`
- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/PlayoffSection.tsx`

---

## 6. `[ ]` Phase P3 retrospective and P4 handoff

**Why:** Self-propagating final task. It closes the mobile-verification queue
and creates the executable felt-polish queue.

**Scope:**

- Write the Phase P3 retrospective in this file.
- Draft `phase_p4_work_queue.md` for Track A Part 3 Phase P4.
- Refresh `first_run_and_polish_plan.md` if P3 changes Part 3 priorities,
  phase names, or guardrails.
- Update `product_polish_master_plan.md` so Active Continuation points to Track
  A, Part 3, Phase P4.
- Update `docs/index.md` for the new active Part 3 queue.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_p3_work_queue.md` - check this item and add
  retrospective
- `docs/planning/phase_p4_work_queue.md` (new)
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_p4_work_queue.md` exists with concrete PR-sized felt-polish items.
- Active-continuation docs point to Track A Part 3 Phase P4.
- Phase P3 is explicitly closed without implying Track A Part 3 or the whole
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

When all items above are checked `[x]`, Phase P3 is complete. The draft of
`phase_p4_work_queue.md` from item 6 is the handoff artifact for Track A Part 3
Phase P4.
