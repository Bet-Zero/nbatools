# Phase P4 Work Queue

> **Role:** Track A Part 3 felt-polish queue for
> [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md) -
> _small interaction details that make the finished UI feel intentional._
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

## Phase P4 goal

Finish Track A Part 3's felt-polish list without changing engine behavior.
P4 covers keyboard shortcuts, copy/share confirmation, stat abbreviation help,
standardized formatting touch-ups, restrained transitions, optional stat value
motion, and final saved/history ergonomics. These are UI interaction details,
not parser, analytics, filtering, or data-contract changes.

Guardrails:

- Keep React as a presentation layer. Do not parse query intent, calculate NBA
  facts, or transform result payloads in the frontend.
- Respect reduced-motion preferences for transitions and any numeric animation.
- Do not add visible tutorial or shortcut text unless it belongs naturally in an
  existing control. Prefer accessible labels, titles, or tooltips for discovery.
- Keep copy/share behavior URL-state based; do not invent a new sharing model.
- Preserve mobile containment from P3 when adding motion, tooltips, or action
  feedback.
- If runtime frontend source changes, run the full frontend test and build
  commands before checking off the item.

---

## 1. `[x]` Inventory felt-polish gaps and fixture set

**Why:** P4 touches many small interactions. Start by naming the current state,
target behavior, owner files, fixtures, and test/screenshot strategy before
runtime changes.

**Scope:**

- Audit current implementation for:
  - copy/share confirmation and clipboard fallback behavior
  - keyboard shortcuts and query-history navigation
  - stat abbreviation help and formatting consistency
  - transitions between loading, result, error, and empty states
  - query history and saved-query interaction ergonomics
- Define the P4 browser fixture set for desktop and mobile checks.
- Record any already-shipped behavior so P4 does not duplicate it.
- Write the inventory as `docs/planning/phase_p4_felt_polish_inventory.md`.
- Do not change runtime UI behavior in this item.

**Files likely touched:**

- `docs/planning/phase_p4_felt_polish_inventory.md` (new)
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- Inventory maps each P4 surface to owner components/hooks, current behavior,
  desired behavior, risk, tests, and browser evidence.
- Inventory identifies which first-run/P2/P3 behaviors are already complete.
- Any ambiguity is captured as a residual or blocker before runtime work
  starts.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Completion notes:**

- Added
  [`phase_p4_felt_polish_inventory.md`](./phase_p4_felt_polish_inventory.md)
  covering current behavior, target P4 behavior, owner files, risks, fixture
  queries, and verification strategy for keyboard shortcuts, copy/share
  feedback, stat help, formatting, transitions/value motion, and history/saved
  ergonomics.
- Identified already-complete P1/P2/P3 behavior so P4 runtime work can focus on
  remaining interaction polish instead of duplicating shipped first-run,
  non-result, and mobile containment work.

**Reference docs/files to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/CopyButton.tsx`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/design-system/Stat.tsx`
- `frontend/src/hooks/useQueryHistory.ts`
- `frontend/src/hooks/useUrlState.ts`

---

## 2. `[ ]` Add keyboard shortcuts and query-history navigation

**Why:** The query-first UI should be fast without the mouse, especially for
repeat use and quick exploration.

**Scope:**

- Add app-level keyboard handling for:
  - `Cmd+K` / `Ctrl+K` focusing and selecting the query input
  - `Escape` clearing the active query text when focus is in the query input
  - up/down arrow navigation through session history from the query input
- Keep normal text editing behavior intact when modifier keys, composition, or
  cursor movement should win.
- Ensure shortcut handlers do not fire from textareas, dialogs, raw JSON, or
  dev-tool kwargs fields where they would be disruptive.
- Preserve existing URL, submit, starter-query, saved-query, and history
  behavior.
- Update focused tests and UI guide notes.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/hooks/useQueryHistory.ts`
- focused frontend tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- `Cmd+K` / `Ctrl+K` focuses the query input without submitting or changing the
  current result.
- Query-input up/down can recall previous session queries in order and enter can
  submit the recalled text.
- Shortcuts avoid dialogs, raw JSON, and structured-query editing fields.
- Tests cover shortcut and history-navigation behavior.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p4_felt_polish_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/QueryBar.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/hooks/useQueryHistory.ts`
- `frontend/src/test/FirstRun.test.tsx`

---

## 3. `[ ]` Polish copy/share feedback and failure states

**Why:** Copy actions already exist, but friend-ready polish needs durable,
accessible confirmation and graceful behavior when clipboard APIs fail.

**Scope:**

- Refine `CopyButton` confirmation for query, JSON, and share-link actions.
- Add accessible status feedback without relying only on button text changes.
- Keep the existing fallback for non-secure contexts, but expose a clear failure
  state if both clipboard paths fail.
- Ensure repeated copy clicks reset timers cleanly and do not update state after
  unmount.
- Preserve share-link generation through `useUrlState`.
- Update focused tests and UI guide notes.

**Files likely touched:**

- `frontend/src/components/CopyButton.tsx`
- `frontend/src/components/CopyButton.module.css`
- `frontend/src/hooks/useUrlState.ts`
- focused frontend tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- Copy/share buttons give accessible success feedback and recover to their
  normal label.
- Clipboard failure is visible and non-crashing.
- Rapid repeated clicks and unmounts do not leak timers or stale state.
- Tests cover success, fallback, failure, and timer reset behavior.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p4_felt_polish_inventory.md`
- `frontend/src/components/CopyButton.tsx`
- `frontend/src/test/Button.test.tsx`
- `frontend/src/hooks/useUrlState.ts`
- `frontend/src/test/useUrlState.test.ts`

---

## 4. `[ ]` Add stat abbreviation help and formatting polish

**Why:** Designed result cards use compact stat labels. A friend should be able
to understand abbreviations such as eFG%, TS%, USG%, AST%, REB%, TOV%, 3PM,
and +/- without cluttering cards.

**Scope:**

- Add a small presentation-layer help mechanism for common stat abbreviations.
- Apply it through existing `Stat` / `StatBlock` usage where labels are already
  supplied by owner components.
- Keep help text accessible and nonintrusive; avoid adding visible explainer
  copy inside dense cards.
- Audit obvious number-format consistency issues surfaced by P4 inventory, but
  do not change engine values or result contracts.
- Update focused tests and UI guide notes.

**Files likely touched:**

- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/Stat.module.css`
- owner components that pass compact labels, if needed
- focused frontend tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- Common stat abbreviations expose understandable help text via accessible
  labels, title text, or a local tooltip primitive.
- Cards remain visually clean and mobile-safe.
- Number-format touch-ups are presentation-only and tested.
- Tests cover abbreviation help behavior and any formatting changes.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p4_felt_polish_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/StatBlock.tsx`
- `frontend/src/components/tableFormatting.ts`
- result renderer components that pass compact stat labels

---

## 5. `[ ]` Add restrained result transitions and stat value motion

**Why:** Loading-to-result changes should feel finished without distracting from
the data or making the app feel slow.

**Scope:**

- Add subtle transitions for state changes between empty, loading, error, and
  result surfaces.
- Add opt-in value motion for hero stats where it improves readability.
- Respect `prefers-reduced-motion: reduce`; reduced-motion users should see no
  animated count-up or unnecessary movement.
- Avoid animating wide tables or changing layout size during animation.
- Verify motion does not reintroduce mobile overflow or text overlap.
- Update focused tests and UI guide notes.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/App.module.css`
- `frontend/src/design-system/Stat.tsx`
- `frontend/src/design-system/Stat.module.css`
- focused frontend tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- Result/state transitions are subtle and token-driven.
- Hero stat value motion is stable, optional, and reduced-motion aware.
- Mobile layouts remain contained at phone widths.
- Tests cover reduced-motion behavior and stable rendering.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p4_felt_polish_inventory.md`
- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`
- `frontend/src/styles/tokens.css`
- `frontend/src/App.tsx`
- `frontend/src/design-system/Stat.tsx`

---

## 6. `[ ]` Tighten query history and saved-query ergonomics

**Why:** Query history and saved queries exist, but final polish should make
them predictable, keyboard-friendly, and easy to trust.

**Scope:**

- Refine empty, pinned, import/export, save-from-history, edit, and run flows
  where P4 inventory identifies friction.
- Ensure history and saved-query action controls have accessible names,
  consistent ordering, and stable touch targets.
- Preserve storage format compatibility for existing saved queries.
- Keep saved-query JSON import/export client-side only.
- Verify mobile containment after any layout changes.
- Update focused tests and UI guide notes.

**Files likely touched:**

- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/QueryHistory.module.css`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/SavedQueries.module.css`
- `frontend/src/components/SaveQueryDialog.tsx`
- focused frontend tests
- `docs/operations/ui_guide.md`
- `docs/planning/phase_p4_work_queue.md`

**Acceptance criteria:**

- History and saved-query controls are keyboard reachable and clearly named.
- Save/edit/run/delete/pin/import/export flows remain stable and tested.
- Existing saved-query storage remains backward compatible.
- Mobile layout remains contained with long query labels and tags.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p4_felt_polish_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/SaveQueryDialog.tsx`
- `frontend/src/storage/savedQueryStorage.ts`
- `frontend/src/test/SavedQueries.test.tsx`

---

## 7. `[ ]` Phase P4 retrospective and P5 handoff

**Why:** Self-propagating final task. It closes the felt-polish queue and
creates the executable Track A Part 3 closure queue.

**Scope:**

- Write the Phase P4 retrospective in this file.
- Draft `phase_p5_work_queue.md` for Track A Part 3 Phase P5.
- Refresh `first_run_and_polish_plan.md` if P4 changes Part 3 priorities,
  phase names, done definition, or guardrails.
- Update `product_polish_master_plan.md` so Active Continuation points to Track
  A, Part 3, Phase P5.
- Update `docs/index.md` for the new active Part 3 queue.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_p4_work_queue.md` - check this item and add
  retrospective
- `docs/planning/phase_p5_work_queue.md` (new)
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_p5_work_queue.md` exists with concrete PR-sized closure items.
- Active-continuation docs point to Track A Part 3 Phase P5.
- Phase P4 is explicitly closed without implying Track A Part 3, Track B, or
  the whole polish plan is complete.
- This item is checked off.

**Tests to run:**

- None (docs/handoff only)

**Reference docs to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/operations/ui_guide.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase P4 is complete. The draft of
`phase_p5_work_queue.md` from item 7 is the handoff artifact for Track A Part 3
Phase P5.
