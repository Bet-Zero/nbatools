# Phase V5 Work Queue

> **Role:** Final Track A Part 1 work queue for
> [`visual_foundation_plan.md`](./visual_foundation_plan.md) - _Part 1
> retrospective and Part 2 handoff._
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

## Phase V5 goal

Close Track A Part 1 cleanly and hand Part 2 a usable starting point. Part 1
has built the visual foundation: design tokens, primitives, app shell, identity
imagery, team badges, and scoped team theming. Phase V5 verifies that foundation
against the Part 1 done definition, captures residuals honestly, and drafts the
first component-experience queue.

Phase V5 should not redesign query-class layouts. It should prepare Part 2 to
start with clear contracts, known residuals, and a concrete first queue.

---

## 1. `[x]` Audit Track A Part 1 against the done definition

**Why:** Before Part 2 starts, the foundation should be checked against the
actual Part 1 done definition rather than assumed complete because V1-V4 items
were checked off.

**Scope:**

- Review `visual_foundation_plan.md` done definition and visual quality bar.
- Review the shipped V1-V4 queue outcomes and known residuals.
- Inspect current frontend token/primitives/shell/imagery/theming coverage.
- Create `docs/planning/phase_v5_part1_completion_audit.md`.
- Document any residuals that Part 2 must account for, distinguishing blockers
  from acceptable follow-up work.
- Do not redesign query-class layouts in this item.

**Files likely touched:**

- `docs/planning/phase_v5_part1_completion_audit.md` (new)
- `docs/planning/phase_v5_work_queue.md` - check this item when complete
- `docs/index.md` - add the new audit doc

**Acceptance criteria:**

- Audit maps each Part 1 done-definition item to `complete`, `partial`, or
  `residual`.
- Any residual has a clear owner: Part 2, Part 3, Track B, or explicit
  follow-up.
- No unresolved Part 1 blocker is hidden by the handoff.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`

**Reference docs to consult:**

- `docs/planning/visual_foundation_plan.md`
- `docs/planning/phase_v4_work_queue.md`
- `docs/architecture/design_system.md`
- `docs/operations/ui_guide.md`

---

## 2. `[ ]` Inventory Part 2 component-layout readiness

**Why:** Part 2 should start with a concrete view of current result renderers,
available structured data, and likely gaps before redesigning the first query
class.

**Scope:**

- Inventory current result section components and their query classes.
- Inventory which sections already expose player/team identity fields useful
  to Part 2 layouts.
- Identify data/contract gaps for player summary, leaderboard, comparison,
  finder, team summary, streak, split, occurrence, and playoff layouts.
- Create `docs/planning/phase_v5_component_layout_inventory.md`.
- Keep this as a readiness inventory; do not implement new layouts.

**Files likely touched:**

- `docs/planning/phase_v5_component_layout_inventory.md` (new)
- `docs/planning/phase_v5_work_queue.md` - check this item when complete
- `docs/index.md` - add the new inventory doc

**Acceptance criteria:**

- Inventory names the owner component for every current query class renderer.
- Inventory identifies the first likely C1 data needs for player summary
  layout work.
- Gaps are categorized as frontend-only, API/result-contract, engine output, or
  deferred.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/component_experience_plan.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/components/StreakSection.tsx`

---

## 3. `[ ]` Retrospective, component plan refresh, and C1 queue draft

**Why:** Self-propagating final task. It closes Track A Part 1 and creates the
first executable Part 2 queue.

**Scope:**

- Write the Phase V5 retrospective in this file.
- Refresh `component_experience_plan.md` if the Part 1 audit or readiness
  inventory changes Part 2 scope, ordering, or guardrails.
- Draft `phase_c1_work_queue.md` for player summary layout work.
- Update `visual_foundation_plan.md` to mark Track A Part 1 complete.
- Update `product_polish_master_plan.md` so Active Continuation points to
  Track A, Part 2, Phase C1.
- Update `docs/index.md` for new active queue/planning docs.

**Files likely touched:**

- `docs/planning/phase_v5_work_queue.md` - check this item and add
  retrospective
- `docs/planning/component_experience_plan.md`
- `docs/planning/phase_c1_work_queue.md` (new)
- `docs/planning/visual_foundation_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_c1_work_queue.md` exists with concrete PR-sized player-summary items.
- Active-continuation docs point to Phase C1.
- Track A Part 1 is explicitly closed, without implying the whole polish plan
  is complete.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/phase_v5_part1_completion_audit.md`
- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/planning/component_experience_plan.md`
- `docs/planning/product_polish_master_plan.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Track A Part 1 is complete. The draft
of `phase_c1_work_queue.md` from item 3 is the handoff artifact.
