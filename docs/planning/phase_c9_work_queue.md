# Phase C9 Work Queue

> **Role:** Track A Part 2 closure queue for
> [`component_experience_plan.md`](./component_experience_plan.md) -
> _Part 2 retrospective, done-definition audit, and Part 3 handoff._
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

## Phase C9 goal

Close Track A Part 2 honestly before handing the visual track to Part 3.
C1-C8 built and mobile-polished the redesigned query-class renderers; C9 turns
that work into a completion audit, status refresh, and executable first-run /
felt-polish queue.

C9 is not allowed to declare the whole product-polish plan complete. The
master plan remains in progress until Track A Part 3 and Track B deployment
work are both closed.

Guardrails:

- Do not add runtime behavior in this phase unless a documentation audit
  uncovers a genuine shipped-behavior mismatch that must be fixed before
  handoff.
- Keep product-completion language scoped: C9 can close Track A Part 2, not the
  whole polish plan.
- If Part 2 done-definition gaps remain, document them explicitly and either
  convert them into Part 3 work or mark them as approved residuals.
- The final C9 item must draft the first Part 3 work queue and update active
  continuation to that queue.

---

## 1. `[ ]` Audit Track A Part 2 completion

**Why:** Part 2 should close from an explicit done-definition audit, not from
the absence of unchecked component items.

**Scope:**

- Audit `component_experience_plan.md`'s Track A Part 2 done definition against
  shipped C1-C8 work.
- Confirm every query class has an owner renderer, full detail remains visible,
  mobile acceptance criteria are met or named as residuals, and mixed/single
  team theming boundaries are accurate.
- Write the audit as `docs/planning/phase_c9_part2_completion_audit.md`.
- Do not change runtime rendering in this item.

**Files likely touched:**

- `docs/planning/phase_c9_part2_completion_audit.md` (new)
- `docs/planning/phase_c9_work_queue.md`

**Acceptance criteria:**

- Audit maps each Part 2 done-definition item to evidence or a residual.
- Audit distinguishes Part 2 closure from Part 3 first-run/felt-polish work.
- This item is checked off.

**Tests to run:**

- None (docs/audit only)

**Reference docs to consult:**

- `docs/planning/component_experience_plan.md`
- `docs/operations/ui_guide.md`
- `frontend/src/components/ResultSections.tsx`

---

## 2. `[ ]` Refresh Part 2 status and residual docs

**Why:** The planning and operations docs should reflect the Part 2 closure
audit before the handoff queue activates Part 3.

**Scope:**

- Refresh `component_experience_plan.md` with C9 audit findings, Part 2 closure
  status, and any explicit residuals that move to Part 3.
- Refresh `docs/operations/ui_guide.md` if the audit finds renderer or mobile
  behavior that is missing from the current UI docs.
- Update `docs/index.md` for any new C9 audit artifact.
- Do not change active continuation yet; C9 remains active until the final
  handoff item.

**Files likely touched:**

- `docs/planning/component_experience_plan.md`
- `docs/operations/ui_guide.md`
- `docs/index.md`
- `docs/planning/phase_c9_work_queue.md`

**Acceptance criteria:**

- Part 2 docs reflect the audit without overstating whole-plan completion.
- Residuals are assigned to Part 3 or documented as explicit non-blockers.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/phase_c9_part2_completion_audit.md`
- `docs/planning/component_experience_plan.md`
- `docs/planning/first_run_and_polish_plan.md`
- `docs/operations/ui_guide.md`

---

## 3. `[ ]` Phase C9 retrospective and Part 3 queue handoff

**Why:** Self-propagating final task. It closes Track A Part 2 and creates the
first executable Part 3 queue.

**Scope:**

- Write the Phase C9 retrospective in this file.
- Draft `phase_p1_work_queue.md` for Track A Part 3 Phase P1.
- Refresh `first_run_and_polish_plan.md` if C9 changes Part 3 priorities,
  phase names, or guardrails.
- Update `product_polish_master_plan.md` so Active Continuation points to Track
  A, Part 3, Phase P1.
- Update `docs/index.md` for the new active Part 3 queue.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_c9_work_queue.md` - check this item and add
  retrospective
- `docs/planning/phase_p1_work_queue.md` (new)
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_p1_work_queue.md` exists with concrete PR-sized first-run items.
- Active-continuation docs point to Track A Part 3 Phase P1.
- Track A Part 2 is explicitly closed without implying the whole polish plan is
  complete.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/phase_c9_part2_completion_audit.md`
- `docs/planning/component_experience_plan.md`
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Track A Part 2 is closed. The draft of
`phase_p1_work_queue.md` from item 3 is the handoff artifact for Track A Part 3.
