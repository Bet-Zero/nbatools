# Phase K Work Queue

> **Role:** Active queue for [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md).
>
> This queue turns the latest full-sweep audit into a real blocker inventory and works it down until the examples-library surface is honest and consistent.
>
> **How to work this file:** Find the first unchecked item below. Review the cited sweep evidence and docs. Execute the item per acceptance criteria. Run the listed tests. Check the item off, commit as its own PR-sized unit, push/open the PR immediately, wait for CI, merge as soon as CI is green, and continue immediately to the next unchecked item.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped, with an inline documented reason

---

## Guardrails

- Do not close this queue just because one failure family improved.
- Do not rewrite docs just to make failures disappear; only reclassify when the docs/examples are provably overstating support.
- Do not call a case fixed unless the targeted sweep evidence improves and the supported behavior is honest.
- Use the full-sweep artifacts as the blocker inventory source of truth.
- Keep `examples.md`, `query_catalog.md`, `current_state_guide.md`, and parser docs in sync whenever supported behavior changes.
- Keep running continuously. Queue completion is not a stopping point unless the final item drafts the next queue or updates `master_completion_plan.md` to close the whole plan.

---

## 1. `[x]` Build the evidence-based blocker inventory from the latest full sweep

**Why:** Work should not proceed from vague impressions. The latest full sweep identified failures across canonical examples, supported examples, pairs, equivalence groups, and ambiguity handling. The repo needs one explicit blocker inventory derived from the sweep artifacts.

**Scope:**

- Read `outputs/parser_examples_full_sweep/report.md` and `outputs/parser_examples_full_sweep/results.csv`.
- Build a durable blocker inventory doc or section under `docs/planning/` that groups blockers into at least:
  - canonical section 2 failures
  - `supported_exact` failures
  - pair mismatches from section 3
  - equivalence-group mismatches from section 7
  - ambiguity-handling failures
  - doc/support-boundary mismatches
- Each blocker group must cite representative case IDs and queries.
- The inventory must state which issues are expected to be fixed in code and which might require honest reclassification.

**Files likely touched:**

- a new `docs/planning/parser_examples_blocker_inventory.md` file
- `docs/planning/parser_examples_completion_plan.md` if cross-links are needed
- `docs/index.md`

**Acceptance criteria:**

- The blocker inventory is explicit and derived from the latest sweep artifacts.
- Every remaining Phase K item can cite the blocker inventory instead of vague summaries.
- The inventory distinguishes implementation blockers from documentation-truth blockers.

**Tests to run:**

- None for docs-only triage.

**Reference artifacts to consult:**

- `outputs/parser_examples_full_sweep/report.md`
- `outputs/parser_examples_full_sweep/results.csv`
- `docs/operations/parser_examples_full_sweep_protocol.md`

**Completed artifact:** [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)

---

## 2. `[x]` Fix or honestly reclassify canonical section 2 failures

**Why:** Section 2 is the canonical 100-example set. If those examples fail, the examples library is not meaningfully aligned with the product.

**Scope:**

- Use the blocker inventory to identify every failing section 2 case.
- Prioritize true supported-behavior fixes first.
- Where a canonical example is not actually in the shipped support boundary, correct the docs/examples/catalog honestly rather than leaving a false supported impression.
- Update parser/routing/execution/docs as needed.

**Acceptance criteria:**

- Every previously failing section 2 case is either fixed in code or honestly reclassified with updated docs/examples.
- No canonical example remains in a vague unsupported state.
- A targeted rerun of the affected section 2 cases shows the intended improvement.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-smoke-queries`
- `make test-phase-smoke` when phase tuples change
- targeted rerun of the affected full-sweep cases

**Reference artifacts to consult:**

- blocker inventory from item 1
- `outputs/parser_examples_full_sweep/report.md`
- `outputs/parser_examples_full_sweep/results.csv`

**Completed validation:** targeted rerun of the 31 affected Section 2 cases passed
31/31 using `outputs/parser_examples_full_sweep/sweep_runner.py` scoring logic.

---

## 3. `[x]` Repair question/search pair mismatches from section 3

**Why:** Phrasing parity is one of the main promises of the parser surface. Pairs that diverge in route, query class, or status are direct evidence that the surface is still inconsistent.

**Scope:**

- Use the blocker inventory and full-sweep results to identify all failing pairs.
- Fix parsing/routing/defaults where the two phrasings should clearly match.
- If a pair cannot honestly be made equivalent because one phrasing implies a different boundary, document that explicitly and adjust the examples/spec/catalog.
- Preserve a clear record of pair-level mismatches in the audit artifacts.

**Acceptance criteria:**

- Previously failing section 3 pairs are either equivalent after fixes or explicitly documented as intentionally non-equivalent.
- No unexplained pair mismatch remains.
- Targeted rerun of affected pairs confirms the new behavior.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-smoke-queries`
- targeted rerun of affected pair cases

**Reference artifacts to consult:**

- blocker inventory from item 1
- `outputs/parser_examples_full_sweep/report.md`
- `outputs/parser_examples_full_sweep/results.csv`

**Completed validation:** targeted rerun of the 12 listed Section 3 pairs passed
with 24/24 cases passing and no remaining pair signature mismatches.

---

## 4. `[x]` Repair equivalence-group and ambiguity-handling failures

**Why:** The examples sweep found cases where intended-equivalent phrasings diverged and ambiguous inputs did not behave honestly.

**Scope:**

- Work through the equivalence-group mismatches from section 7.
- Work through ambiguity-handling failures where the product confidently guessed instead of surfacing ambiguity / alternates / honest no-result behavior.
- Fix parser confidence/alternate handling, route defaults, or docs/examples as needed.

**Acceptance criteria:**

- No unexplained equivalence-group mismatch remains.
- Intentional ambiguity behaves honestly and consistently.
- Targeted reruns confirm the fixes.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-api` if envelope or alternates handling changes
- targeted rerun of affected ambiguity/equivalence cases

**Reference artifacts to consult:**

- blocker inventory from item 1
- `outputs/parser_examples_full_sweep/report.md`
- `outputs/parser_examples_full_sweep/results.csv`

**Completed validation:** targeted rerun of the listed Section 7 equivalence
groups and Section 5.8 ambiguity cases passed with no failed cases and no
remaining equivalence signature mismatches.

---

## 5. `[x]` Run the full parser-examples sweep again and compare deltas

**Why:** This queue should not close on local spot checks alone. The blocker inventory must be validated against a fresh full sweep.

**Scope:**

- Rerun `docs/operations/parser_examples_full_sweep_protocol.md`.
- Produce a fresh `results.csv`, `report.md`, and raw artifacts.
- Compare new pass/fail counts and blocker categories against the prior sweep.
- Update the blocker inventory to reflect only the remaining unresolved issues.

**Acceptance criteria:**

- Fresh sweep artifacts exist.
- Improvement vs. the prior sweep is documented.
- Remaining blockers, if any, are explicit and small enough to scope into the next queue.

**Tests to run:**

- Full parser-examples sweep protocol
- `make test-smoke-queries`
- `make test-phase-smoke`

**Reference artifacts to consult:**

- prior sweep outputs in `outputs/parser_examples_full_sweep/`
- `docs/operations/parser_examples_full_sweep_protocol.md`

**Completed validation:** full sweep rerun at
`2026-04-25T15:42:59Z` on commit
`8cd6441fadcba3e14ac0d095dc43e5cd9a16cb44` produced 402 cases,
384 passing and 18 failing. This improves the prior Phase K baseline from
324/78 to 384/18, reduces pair mismatches from 12 to 4, and reduces
equivalence-group mismatches from 7 to 1. The blocker inventory now reflects
only the remaining unresolved issues from this fresh sweep.

---

## 6. `[ ]` Draft the next queue or close the whole plan

**Why:** This queue cannot end with another vague “much better now” state. It must either continue the plan explicitly or close it honestly.

**Scope:**

- If the rerun still shows unresolved blocker groups, draft the next queue under `docs/planning/` and make it the active continuation.
- If the rerun shows the blocker inventory is truly resolved, update `docs/planning/master_completion_plan.md` so the whole plan is done again, now including the examples-library surface.
- Update any plan/queue/docs index references accordingly.

**Acceptance criteria:**

- `master_completion_plan.md` names exactly one active continuation, or states that the whole plan is done.
- No open-ended examples-library blocker state remains undocumented.
- The repo gives one truthful answer to whether the whole plan is done.

**Tests to run:**

- None for docs-only closure / queue drafting.
- If sweep outputs change during closure, ensure the latest artifacts are preserved.

**Reference docs to consult:**

- `docs/planning/master_completion_plan.md`
- `docs/planning/parser_examples_completion_plan.md`
- the latest blocker inventory and sweep outputs
