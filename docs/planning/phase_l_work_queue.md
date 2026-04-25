# Phase L Work Queue

> **Role:** Active continuation queue for
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
> after the Phase K full-sweep rerun.
>
> Phase K reduced the full parser-examples sweep from 78 failures to 18. This
> queue works the remaining blocker inventory down to closure or to one final,
> explicit continuation.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped, with an inline documented reason

---

## Guardrails

- Use [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
  as the source of truth for remaining case IDs.
- Prefer small code fixes for clear parser/routing misses; prefer honest
  reclassification when the examples overstate shipped support.
- Keep `examples.md`, `query_catalog.md`, `current_state_guide.md`, and parser
  docs in sync whenever supported behavior changes.
- Do not close this queue until the full sweep is rerun and the master plan
  names either the next continuation or whole-plan completion.
- As each item completes, commit it as a PR-sized unit, open the PR, wait for
  CI, merge when green, and continue to the next unchecked item.

---

## 1. `[ ]` Resolve remaining shorthand leaderboard and fallback parser misses

**Why:** Most remaining failures are ordinary parser/routing coverage gaps in
search-bar style phrasing. These should be fixed before deeper execution or
boundary decisions.

**Scope:**

- Resolve or honestly reclassify the following failing cases:
  - `S3_3_2_07_S` - "hottest from 3 lately"
  - `S3_3_3_14_S` - "double double average last 10 games"
  - `S3_3_5_23_Q` - "Which players shoot the best against top-10 defenses?"
  - `S3_3_5_23_S` - "best shooting vs top 10 defenses"
  - `S3_3_7_32_Q` - "Who's been the best shot blocker in the last 10 games?"
  - `S3_3_7_32_S` - "best shot blocker last 10 games"
  - `S8_8_1_03` - "against winning teams"
  - `S8_8_3_01` - "in clutch time"
- Fix the related pair mismatches for `S3_3_2_07` and `S3_3_3_14` when the
  shorthand side becomes consistent with the question side.
- Preserve fallback notes for opponent-quality and clutch/boundary fragments
  instead of silently pretending unsupported context is fully applied.

**Acceptance criteria:**

- Every scoped case either passes in a targeted sweep rerun or is honestly
  reclassified in docs/examples.
- The `S3_3_2_07` and `S3_3_3_14` pair mismatches are resolved or explicitly
  documented as intentionally non-equivalent.
- Updated behavior is covered by parser/query tests or smoke tuples as
  appropriate.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-smoke-queries`
- `make test-phase-smoke` when smoke tuples change
- targeted rerun of the scoped full-sweep cases and affected pairs

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`

---

## 2. `[ ]` Resolve absence, multi-player availability, and on/off equivalence blockers

**Why:** The remaining availability-style blockers mix true teammate-absence
summary support, intentionally unsupported multi-player availability, and on/off
token normalization. They need explicit behavior decisions so the examples
library is not ambiguous.

**Scope:**

- Resolve or honestly reclassify:
  - `S2_2_6_06` - "How does Jamal Murray score when Nikola Jokić is out?"
  - `S3_3_9_45` pair - Lakers record when LeBron James and Anthony Davis both
    play
  - `S7_7_15` group - `Jokic on/off`, `Jokic on off`, `Nikola Jokic on-off`
- Decide whether each item belongs to supported summary/record behavior,
  explicit unsupported-data behavior, or an honest unsupported boundary.
- Update docs/examples/catalog if a query is intentionally outside the current
  product boundary.

**Acceptance criteria:**

- The scoped Section 2 case passes or is honestly reclassified.
- The `S3_3_9_45` pair no longer has an unexplained result-status mismatch.
- The `S7_7_15` equivalence group no longer has unexplained route/status
  divergence, or the examples document the intended non-equivalence.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-api` if no-result/envelope behavior changes
- `make test-smoke-queries`
- targeted rerun of the scoped full-sweep cases, pair, and equivalence group

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md)
- `outputs/parser_examples_full_sweep/results.csv`

---

## 3. `[ ]` Resolve occurrence-count and historical execution blockers

**Why:** Five remaining failures are execution or data-support issues rather
than basic phrase recognition. These should be fixed in command modules when
the behavior is genuinely supported, or reclassified when the current product
does not have the required historical/playoff data contract.

**Scope:**

- Resolve or honestly reclassify:
  - `S4_4_2_10` - "how many players scored 40 points this season"
  - `S4_4_2_11` - "number of players with 10 assists this season"
  - `S4_4_4_06` - "Warriors conference finals appearances"
  - `S4_4_4_09` - "best second round record"
  - `S4_4_4_12` - "winningest team of the 2010s"
- Keep occurrence-count logic in command/helper modules, not CLI wrappers.
- Do not create or broaden historical/playoff datasets without a documented
  data contract and lifecycle placement.

**Acceptance criteria:**

- Occurrence-count runtime errors are fixed or the examples are reclassified
  with a documented reason.
- Historical/playoff examples either execute on a documented data contract or
  are honestly marked out of current scope.
- No command-layer business logic is added to CLI entrypoints.

**Tests to run:**

- `make test-engine`
- `make test-query`
- `make test-output` if structured output changes
- `make test-smoke-queries`
- targeted rerun of the scoped full-sweep cases

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- `outputs/parser_examples_full_sweep/results.csv`

---

## 4. `[ ]` Resolve remaining net-rating and placeholder boundary mismatches

**Why:** The last unresolved boundary cases are places where examples either
imply support that may not exist or placeholder templates route as if they were
real user queries.

**Scope:**

- Resolve or honestly reclassify:
  - `S3_3_3_12_S` - "best net rating last 15 games"
  - `S8_8_1_04` - "best record vs teams above .600"
  - `S8_8_5_02` - "Who has the most ___ since becoming a starter?"
  - `S8_8_5_04` - "What is ___ record in overtime games this season?"
- Decide whether each is supported behavior, coverage-gated fallback behavior,
  or an unsupported/future boundary.
- If placeholder examples remain in `examples.md`, make sure they fail cleanly
  or are not treated as runnable shipped queries by the sweep classification.

**Acceptance criteria:**

- The scoped failures are resolved by code or honest docs/examples
  reclassification.
- Placeholder/fill-in examples no longer appear to be supported real queries
  unless there is actual shipped behavior.
- The `S3_3_3_12` pair mismatch is resolved or documented as intentionally
  non-equivalent.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-smoke-queries`
- targeted rerun of the scoped full-sweep cases and affected pair

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- `outputs/parser_examples_full_sweep/results.csv`
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

---

## 5. `[ ]` Rerun the full parser-examples sweep and refresh the blocker inventory

**Why:** Phase L must prove that targeted fixes removed the remaining blocker
families rather than only improving spot checks.

**Scope:**

- Rerun [`parser_examples_full_sweep_protocol.md`](../operations/parser_examples_full_sweep_protocol.md).
- Produce fresh ignored artifacts under `outputs/parser_examples_full_sweep/`.
- Update [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
  to reflect only unresolved issues from the fresh sweep.
- Compare the new counts against the Phase K 384/18 baseline.

**Acceptance criteria:**

- Fresh sweep artifacts exist.
- The inventory either becomes empty or lists only explicitly unresolved
  closure blockers.
- The improvement or remaining blocker state is documented with exact counts.

**Tests to run:**

- Full parser-examples sweep protocol
- `make test-smoke-queries`
- `make test-phase-smoke`

**Reference artifacts:**

- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`
- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)

---

## 6. `[ ]` Close the whole plan or draft the next explicit continuation

**Why:** The repo must continue to give one truthful answer about whether the
whole plan is done.

**Scope:**

- If the blocker inventory is empty or all remaining items are explicitly
  resolved by product decisions, update
  [`master_completion_plan.md`](./master_completion_plan.md) to close the whole
  plan.
- If unresolved blocker groups remain, draft the next queue and make it the
  active continuation in `master_completion_plan.md`.
- Update [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
  and [`docs/index.md`](../index.md) so the active queue references are not
  stale.

**Acceptance criteria:**

- `master_completion_plan.md` names exactly one active continuation, or states
  that the whole plan is done.
- There is no open-ended examples-library blocker state undocumented.
- The latest full-sweep result is cited in the closure or continuation record.

**Tests to run:**

- None for docs-only closure / queue drafting.

**Reference docs:**

- [`master_completion_plan.md`](./master_completion_plan.md)
- [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
