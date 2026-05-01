# Phase P5 Work Queue

> **Role:** Track A Part 3 closure queue for
> [`first_run_and_polish_plan.md`](./first_run_and_polish_plan.md) -
> _first-run/polish completion audit, Track A closure, and master-plan
> continuation handoff._
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

## Phase P5 goal

Close Track A Part 3 honestly. P1-P4 shipped first-run, designed non-result
states, broader mobile verification, and felt-polish interactions. P5 turns
that work into an evidence-based completion audit, refreshes active planning
docs, and hands the master plan to the next open continuation.

P5 must not declare the whole product-polish plan complete while Track B
deployment remains open. If Track A closes and Track B remains open, the
master-plan active continuation should move to the appropriate Track B queue.

Guardrails:

- Do not add runtime behavior in P5 unless the audit uncovers a small,
  verified doc/behavior mismatch that must be fixed before Track A closure.
- Keep completion language scoped: P5 can close Track A Part 3 and Track A, not
  the full product polish plan unless Track B is also closed.
- Residuals must have owners: Track B, a future post-polish plan, or an
  explicit documented non-blocker.
- The final P5 item must update the master plan active continuation to the next
  open queue or state that every queue under the master plan is closed.

---

## 1. `[x]` Audit Track A Part 3 completion

**Why:** Part 3 should close from the done definition and shipped evidence, not
from the absence of unchecked P1-P4 queue items.

**Scope:**

- Audit `first_run_and_polish_plan.md`'s done definition against shipped P1-P4
  work.
- Confirm first-run onboarding, mobile verification, loading/error/empty
  states, freshness visibility, and felt-polish interactions have evidence.
- Distinguish Track A Part 3 closure from Track B deployment/product URL work.
- Write the audit as `docs/planning/phase_p5_part3_completion_audit.md`.
- Do not change runtime behavior in this item.

**Files likely touched:**

- `docs/planning/phase_p5_part3_completion_audit.md` (new)
- `docs/planning/phase_p5_work_queue.md`
- `docs/index.md`

**Acceptance criteria:**

- Audit maps each Part 3 done-definition item to evidence, residual, or
  explicit non-blocker.
- Audit names any remaining product-polish blockers and assigns them to Track B
  or a future plan.
- This item is checked off.

**Tests to run:**

- None (docs/audit only)

**Completion notes:**

- Added
  [`phase_p5_part3_completion_audit.md`](./phase_p5_part3_completion_audit.md)
  mapping each Track A Part 3 done-definition item to shipped P1-P4 evidence.
- Confirmed Track A Part 3 has no closure-blocking residuals, while the whole
  master plan remains open for Track B deployment, R2 data sync, custom domain,
  and production monitoring.
- Updated `docs/index.md` for the new audit artifact.

**Reference docs to consult:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/phase_p1_work_queue.md`
- `docs/planning/phase_p2_work_queue.md`
- `docs/planning/phase_p3_work_queue.md`
- `docs/planning/phase_p4_work_queue.md`
- `docs/operations/ui_guide.md`

---

## 2. `[x]` Refresh Track A Part 3 status docs

**Why:** The Part 3 plan, master plan, and docs index should reflect the
completion audit before the final handoff updates active continuation.

**Scope:**

- Refresh `first_run_and_polish_plan.md` with P5 audit findings and Part 3
  closure status, or clearly name any residuals that prevent closure.
- Refresh `product_polish_master_plan.md` capability/status rows for Track A
  Part 3 without changing active continuation yet.
- Update `docs/index.md` for the new P5 audit artifact.
- Do not imply the whole product polish plan is done unless Track B is also
  closed.

**Files likely touched:**

- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`
- `docs/planning/phase_p5_work_queue.md`

**Acceptance criteria:**

- Track A Part 3 docs reflect the audit honestly.
- Whole-plan status remains in progress while Track B is open.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Completion notes:**

- Updated `first_run_and_polish_plan.md` with the P5 audit verdict: no Track A
  Part 3 closure-blocking residuals, with final closure still pending the P5
  handoff task.
- Updated `product_polish_master_plan.md` status language and capability rows
  to reflect the P5 audit while keeping Active Continuation on Phase P5.
- Confirmed `docs/index.md` already lists the P5 audit artifact from item 1.

**Reference docs to consult:**

- `docs/planning/phase_p5_part3_completion_audit.md`
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

---

## 3. `[ ]` Phase P5 retrospective and master-plan handoff

**Why:** Self-propagating final task. It closes Track A if the audit is green
and moves the master plan to the next open continuation.

**Scope:**

- Write the Phase P5 retrospective in this file.
- Update `product_polish_master_plan.md` Active Continuation:
  - to Track B's next open queue if Track A is closed and Track B remains open,
    or
  - to whole-plan complete only if Track B is also closed.
- Update `first_run_and_polish_plan.md` if the retrospective changes the final
  Track A status or residuals.
- Update `docs/index.md` if active-queue descriptions change.
- Check this item off.

**Files likely touched:**

- `docs/planning/phase_p5_work_queue.md` - check this item and add
  retrospective
- `docs/planning/product_polish_master_plan.md`
- `docs/planning/first_run_and_polish_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- Track A Part 3 and Track A are explicitly closed only if the audit supports
  closure.
- Active continuation points to the next open master-plan queue, likely Track B
  Phase N1 while deployment remains open.
- This item is checked off.

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- `docs/planning/phase_p5_part3_completion_audit.md`
- `docs/planning/first_run_and_polish_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/planning/production_deployment_plan.md`
- `docs/planning/phase_n1_work_queue.md`

---

## Appendix: progress tracking

When all items above are checked `[x]`, Track A Part 3 is closed if the audit
supports closure. The master plan remains open until Track B deployment work is
also closed.
