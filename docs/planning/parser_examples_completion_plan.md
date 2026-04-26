# Parser Examples Completion Plan

> **Role: post-core completion plan for making the parser examples library behave honestly and consistently end to end.**
>
> This plan exists because the core finish-line plan is closed, but the full examples-library sweep showed that `docs/architecture/parser/examples.md` still contains meaningful mismatches across canonical examples, phrasing pairs, equivalence groups, ambiguity handling, and supported-vs-unsupported boundaries.

---

## 1. Purpose

The goal of this plan is simple:

> When we say the parser examples surface is done, we mean the example library is no longer materially out of sync with the shipped product behavior.

This plan is not about broad new feature invention. It is about closing the gap between:

- the large example library in `docs/architecture/parser/examples.md`
- the actual routed and executed query behavior
- the living shipped inventory in `docs/reference/query_catalog.md`
- the current-state claims in `docs/reference/current_state_guide.md`

---

## 2. Source artifacts

This plan is grounded in the latest full-sweep audit artifacts:

- `docs/operations/parser_examples_full_sweep_protocol.md`
- `outputs/parser_examples_full_sweep/report.md`
- `outputs/parser_examples_full_sweep/results.csv`
- optional `outputs/parser_examples_full_sweep/manifest.json`
- raw JSON captures under `outputs/parser_examples_full_sweep/raw/`
- `docs/planning/parser_examples_blocker_inventory.md`

These artifacts are the evidence base for deciding what is actually broken.

---

## 3. Completion rule

This plan is **not done** until all of the following are true:

1. every `supported_exact` example from the full sweep either:
   - passes as supported behavior, or
   - is reclassified with a documented reason because the docs/examples were overstating support
2. question-form vs search-form pairs no longer show unexplained route/query-class/result-status mismatches
3. equivalence groups no longer show unexplained divergence across intended-equivalent phrasings
4. intentionally ambiguous examples behave honestly and consistently
5. stress-test inputs fail cleanly or succeed honestly; they do not silently guess wrong
6. `examples.md`, `query_catalog.md`, `current_state_guide.md`, and parser spec docs no longer disagree materially about what is shipped
7. a rerun of the full-sweep protocol produces a report with no unresolved canonical/example-library blockers

Substeps, queue items, and intermediate sweep improvements do **not** count as completion on their own.

---

## 4. What counts as a blocker

This plan treats the following as blocking issues:

- canonical section 2 examples that fail
- paired phrasing examples where only one side works or they route differently without a documented reason
- equivalence groups with inconsistent route or result-class behavior
- supported examples returning `unrouted`, `unsupported`, or materially wrong routes
- ambiguity examples that produce confident wrong guesses instead of honest ambiguity handling
- docs claiming support that the sweep disproves
- examples implying support that the product intentionally does not provide

The plan is allowed to close only when each blocker is either fixed in code or resolved by honest doc/example reclassification.

---

## 5. Non-goals

This plan is not for:

- broad architecture rewrites without direct payoff to the examples sweep
- changing the core data-storage model
- inventing large new NBA feature families beyond what is needed to make the examples library honest
- weakening the examples or reclassifying failures away without evidence

---

## 6. Workstreams

### 6.1 Sweep normalization and case triage

Use the full-sweep outputs to build a clean blocker inventory:

- supported failures
- pair mismatches
- equivalence-group mismatches
- ambiguity-handling mismatches
- unsupported-vs-doc mismatches
- docs/examples overstating support

This is the only acceptable source of truth for the remaining work under this plan.

### 6.2 Canonical examples repair

Fix or honestly reclassify section 2 canonical examples first. These are the highest-value examples and the strongest signal of whether the product matches natural user expectations.

### 6.3 Phrasing parity repair

Fix the paired examples and equivalence groups so question form, search form, and shorthand form behave consistently.

### 6.4 Ambiguity and fallback repair

Fix cases where the product confidently guesses when it should be ambiguous, unsupported, or fallback-noted.

### 6.5 Documentation truth pass

When code behavior changes, update:

- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`

When the docs/examples were wrong, correct them honestly rather than pretending the product already supports more than it does.

### 6.6 Final rerun and closure audit

The plan closes only after rerunning the full-sweep protocol and auditing the remaining mismatches.

---

## 7. Queue model

This plan is worked through companion queues. Each queue item must:

- cite the relevant failure evidence from `report.md` / `results.csv`
- define acceptance criteria in terms of the sweep categories
- run the required test commands
- update docs in the same pass when supported behavior changes
- update the sweep artifacts or the blocker inventory when classification changes

The final item of each queue must either:

1. draft the next queue and make it the active continuation, or
2. update `master_completion_plan.md` to state that this plan is now complete

There must never be a state where this plan is still open but no active continuation is named.

---

## 8. Continuous-execution rule

This plan is meant to be worked continuously.

Agents working this plan must:

- start from `master_completion_plan.md`
- follow the active continuation queue named there
- work the first unchecked item
- run the required tests/smoke checks
- check it off only when truly complete
- then immediately repeat the process

Operational cadence for each completed item: commit it as its own PR-sized unit, open the PR immediately, wait for CI, merge immediately when green, then continue to the next unchecked item.

Do **not** stop after one item, one commit, one PR-sized task, or one queue unless:

- the active queue explicitly requires a review-handoff because a true blocker prevents responsible continuation, or
- `master_completion_plan.md` is updated to say this plan is done

“Done” under this plan means **done with the entire examples-library cleanup effort**, not done with one substep.

---

## 9. Required tests and audits

Normal implementation work under this plan should use the existing repo commands:

- `make test-impacted`
- `make test-impacted-parser` or `make test-impacted-query` for tight iteration
  on a known parser/query slice before running the full required target
- `make test-parser`
- `make test-query`
- `make test-engine`
- `make test-output`
- `make test-api` when envelopes change
- `make test-phase-smoke`
- `make test-smoke-queries`

This plan also requires recurring reruns of:

- `make parser-examples-sweep`
- `docs/operations/parser_examples_full_sweep_protocol.md`

A queue item that changes the examples-library behavior is not complete until its targeted failures are verified and the sweep-based blocker inventory is updated.

Sweep-only inventory-refresh items should run the full sweep and the smoke
targets named by the queue. They should not add `make test-impacted` unless the
item also changes code.

---

## 10. Current continuation

This plan is closed.

Latest closure evidence:

- full sweep timestamp: `2026-04-26T10:08:40.940353+00:00`
- total cases: 402
- passing cases: 402
- failing cases: 0
- phrasing-pair mismatches: 0
- equivalence-group mismatches: 0

Phase K is complete. It built the evidence-based blocker inventory, repaired
the largest canonical/pair/equivalence/ambiguity blocker families, reran the
full sweep, and reduced the baseline from 78 failures to 18. Phase L is
complete: it worked the remaining blocker groups from that fresh 384/18 sweep,
reran the full parser-examples sweep, and refreshed the blocker inventory to
399 passing cases, 3 failing cases, 1 phrasing-pair mismatch, and 0
equivalence-group mismatches. Phase M is complete: it resolved the remaining
closure blockers, reran the full sweep, and closed the examples-library
surface.

---

## 11. Closure-pass efficiency rules

These rules apply once the active queue's blocker inventory is small enough
that the planning ceremony costs more than the remaining work. They exist to
prevent the per-item PR cycle, repeated full-sweep reruns, and successor-phase
scaffolding from outweighing two or three trivial fixes at the tail of a phase.

**Bundling rule.** When the only unchecked items in the active queue are (a)
the final fix/reclassification(s), (b) the proof full-sweep rerun, and (c) the
master-plan closure step, those items must be bundled into a single PR. The
per-item PR cycle is for substantive work, not closure scaffolding.

**No-successor-phase rule.** Do not draft a Phase N successor queue when the
remaining blocker inventory is ≤ 3 cases of the same family and a default
resolution rule (see §12) applies. Inline-finish the current phase instead.
Drafting a successor queue is required only when a genuinely new blocker
family appears or a true product decision must be escalated.

**Single-sweep rule.** Run `make parser-examples-sweep` once per phase, at
closure, as the proof rerun. Do not rerun the full sweep mid-phase to confirm
spot fixes; targeted CLI reruns of the affected case IDs are sufficient until
the closure rerun.

**Test-target proportionality.** For doc-only or narrowly-scoped parser-only
changes, prefer `make test-impacted` (or `make test-impacted-parser` /
`make test-impacted-query`) over the full matrix in §9. Promote to the full
target list only when the corresponding code layer actually changes. The §9
list is the maximum, not the default.

---

## 12. Default resolution rule for fix-vs-reclassify

When a queue item asks "fix execution or reclassify as unsupported," apply the
following default before opening a debate:

- If the parser **route exists** but the example isn't being matched to it
  (route mismatch, phrasing miss, missing alias), the default is a **parser
  fix**. Reclassification is not honest if the route already supports the
  intent.
- If the parser route exists but the **underlying data contract does not**
  (no documented source path, no approved dataset, no coverage semantics for
  the boundary), the default is **honest reclassification** to
  unsupported/out-of-scope in `examples.md`, `query_catalog.md`, and
  `current_state_guide.md`. Do not introduce a new dataset under this plan;
  dataset work is governed by the master-plan structure invariant.
- If neither holds, escalate as a true product decision in the queue rather
  than picking arbitrarily.

This rule prevents the same fix-vs-reclassify discussion from being relitigated
on every Finals/playoff/round case the queue touches.

---

## 13. Closure condition

This plan may close only when:

- the blocker inventory created from the full-sweep artifacts is empty, or every remaining item is explicitly resolved by honest reclassification / out-of-scope decision
- the latest full-sweep rerun shows no unresolved canonical-example blockers
- `master_completion_plan.md` is updated to state that the whole plan is done again, this time including the examples-library surface

Until then, the whole plan remains open.
