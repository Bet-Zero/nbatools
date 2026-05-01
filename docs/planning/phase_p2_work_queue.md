# Phase P2 Work Queue

> **Role:** Track A Part 3 loading/error/empty-state queue for
> [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md) -
> _designed non-result states, retry affordances, and state-specific mobile
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

## Phase P2 goal

Make every state that is not "showing a successful result" feel designed,
honest, and recoverable. P2 covers loading, no-result, unsupported/ambiguous
query responses, network/API failures, and retry paths. It should preserve the
query/result contract: React renders supplied API state and user-facing
affordances, but it does not parse queries or invent result data.

Guardrails:

- Do not hide engine/API reasons. Friendly copy can summarize, but supplied
  notes and caveats remain visible.
- Retry affordances should reuse the existing query/structured-query handlers
  and preserve URL/history behavior where applicable.
- Loading states should use the design-system skeleton primitives and should
  not imply specific result data before the API responds.
- Error states must not expose stack traces or implementation internals.
- Mobile behavior remains explicit: long messages and suggestions wrap without
  shell overflow.

---

## 1. `[x]` Inventory loading, empty, and error-state fixtures

**Why:** P2 touches multiple response states. Start by naming the exact states,
owners, fixtures, and copy boundaries before runtime changes.

**Scope:**

- Audit current loading, no-result, unsupported, ambiguous, API-error, network
  failure, freshness-stale, and empty-section behavior.
- Map each state to its owner component and test fixture.
- Decide which states need retry, suggested-query, or detail disclosure
  affordances without moving parser logic into React.
- Write the inventory as `docs/planning/phase_p2_state_inventory.md`.
- Do not change runtime UI behavior in this item.

**Files likely touched:**

- `docs/planning/phase_p2_state_inventory.md` (new)
- `docs/planning/phase_p2_work_queue.md`

**Acceptance criteria:**

- Inventory names each P2 state, owner component, fixture data, and intended
  user-facing affordance.
- Inventory distinguishes API result states from client/network failures.
- Any ambiguity is captured as a residual or blocker before runtime work
  starts.
- This item is checked off.

**Tests to run:**

- None (docs/inventory only)

**Reference docs/files to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/Loading.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/ErrorBox.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/ResultSections.tsx`

---

## 2. `[x]` Redesign loading and skeleton states

**Why:** Loading should feel connected to the incoming result, not like a
generic blocking spinner.

**Scope:**

- Redesign `Loading.tsx` to use design-system skeleton primitives in a compact
  result-preview shape.
- Preserve accessible loading status semantics.
- Ensure loading state works for natural and structured query submissions.
- Add or update focused frontend tests for loading copy, skeleton structure,
  and accessibility.

**Files likely touched:**

- `frontend/src/components/Loading.tsx`
- `frontend/src/components/Loading.module.css`
- `frontend/src/test/UIComponents.test.tsx`
- `docs/planning/phase_p2_work_queue.md`

**Acceptance criteria:**

- Loading state has a designed skeleton preview without implying unsupplied NBA
  facts.
- Screen-reader status behavior remains intact.
- Mobile loading layout stays inside the main result region.
- Tests cover the redesigned loading state.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p2_state_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/design-system/Skeleton.tsx`
- `frontend/src/components/Loading.tsx`

---

## 3. `[x]` Redesign no-result, unsupported, and ambiguous states

**Why:** Empty API results should help the user recover without implying the
engine found data it did not find.

**Scope:**

- Redesign `NoResultDisplay.tsx` states for `no_match`, `unsupported`,
  `ambiguous`, and generic no-result responses.
- Keep supplied notes visible and avoid parser logic in React.
- Add suggestion presentation only for states where the API/result reason makes
  suggestions appropriate.
- Add or update tests for state-specific copy, notes, suggestions, and mobile
  containment.

**Files likely touched:**

- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/NoResultDisplay.module.css`
- `frontend/src/test/UIComponents.test.tsx`
- `docs/planning/phase_p2_work_queue.md`

**Acceptance criteria:**

- No-result, unsupported, and ambiguous states have distinct designed layouts.
- Unsupported states do not show irrelevant suggestions.
- Supplied notes/caveats remain visible.
- Tests cover the redesigned state variants.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p2_state_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/ResultSections.tsx`

---

## 4. `[x]` Add API/network failure recovery affordances

**Why:** A friend should get a clear recovery path when a request fails instead
of a dead-end error box.

**Scope:**

- Redesign client/network failure presentation around `ErrorBox.tsx` and the
  `App.tsx` error path.
- Add retry affordances for the last natural or structured query without
  duplicating query execution logic.
- Keep error details user-safe; do not expose stack traces.
- Add or update tests for retry behavior, API-offline messaging, and mobile
  wrapping.

**Files likely touched:**

- `frontend/src/App.tsx`
- `frontend/src/components/ErrorBox.tsx`
- `frontend/src/components/ErrorBox.module.css`
- `frontend/src/test/FirstRun.test.tsx` or another focused app test
- `frontend/src/test/UIComponents.test.tsx`
- `docs/planning/phase_p2_work_queue.md`

**Acceptance criteria:**

- Network/API failures have a designed state with safe copy and an actionable
  retry path when a previous query exists.
- Retry reuses the existing natural/structured query handlers and preserves URL
  behavior.
- API-offline messaging remains distinct from no-result API responses.
- Tests cover retry and failure-state rendering.
- This item is checked off.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs/files to consult:**

- `docs/planning/phase_p2_state_inventory.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/ErrorBox.tsx`
- `frontend/src/hooks/useUrlState.ts`

---

## 5. `[ ]` Phase P2 retrospective and P3 handoff

**Why:** Self-propagating final task. It closes the state-design queue and
creates the executable broader mobile-verification queue.

**Scope:**

- Write the Phase P2 retrospective in this file.
- Draft `phase_p3_work_queue.md` for Track A Part 3 Phase P3.
- Refresh `first_run_and_polish_plan.md` if P2 changes Part 3 priorities,
  phase names, or guardrails.
- Update `product_polish_master_plan.md` so Active Continuation points to Track
  A, Part 3, Phase P3.
- Update `docs/index.md` for the new active Part 3 queue.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_p2_work_queue.md` - check this item and add
  retrospective
- `docs/planning/phase_p3_work_queue.md` (new)
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_p3_work_queue.md` exists with concrete PR-sized mobile-verification
  items.
- Active-continuation docs point to Track A Part 3 Phase P3.
- Phase P2 is explicitly closed without implying Track A Part 3 or the whole
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

When all items above are checked `[x]`, Phase P2 is complete. The draft of
`phase_p3_work_queue.md` from item 5 is the handoff artifact for Track A Part 3
Phase P3.
