# Phase M Work Queue

> **Role:** Active continuation queue for
> [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
> after the Phase L full-sweep refresh.
>
> Phase L reran the full parser-examples sweep and improved the Phase K
> 384/18 baseline to 399 passing cases, 3 failing cases, 1 phrasing-pair
> mismatch, and 0 equivalence-group mismatches. This queue resolves those
> remaining closure blockers or records explicit product decisions for them.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped, with an inline documented reason

---

## Guardrails

- Use [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
  as the source of truth for remaining case IDs and pair IDs.
- Prefer small code fixes for clear parser/routing misses; prefer honest
  reclassification when the examples overstate shipped support.
- Do not broaden Finals, playoff-round, shot-profile, clutch, on/off, or
  lineup data contracts without documented source/grain/coverage semantics.
- Keep `examples.md`, `query_catalog.md`, `current_state_guide.md`, and parser
  docs in sync whenever supported behavior changes.
- Do not close this queue until the full sweep is rerun and the master plan
  names either the next continuation or whole-plan completion.
- As each item completes, commit it as a PR-sized unit, open the PR, wait for
  CI, merge when green, and continue to the next unchecked item.

---

## 1. `[x]` Resolve the remaining on/off net-rating phrasing mismatch

**Why:** `S3_3_10_50` is no longer a failing case, but the intended-equivalent
question and search forms still diverge by route and query class. The examples
library cannot close with unexplained pair divergence.

**Scope:**

- Resolve or honestly document the pair mismatch:
  - `S3_3_10_50_Q` - "What is the Nuggets' net rating with Nikola Jokic on the
    floor versus off the floor?"
  - `S3_3_10_50_S` - "Nuggets net rating Jokic on off"
- Prefer routing both forms to the same on/off boundary if the semantics are
  intended equivalent.
- Preserve honest unsupported-data behavior when trusted on/off coverage is
  unavailable; do not imply execution-backed on/off splits without coverage.

**Acceptance criteria:**

- The `S3_3_10_50` pair no longer has route, query-class, or result-status
  divergence in a targeted rerun, or the docs explicitly mark the pair as
  intentionally non-equivalent.
- Existing `player_on_off` behavior and unsupported-data messaging remain
  stable.
- Updated behavior is covered by parser/query tests or smoke tuples as
  appropriate.

**Tests to run:**

- `make test-parser`
- `make test-query`
- targeted rerun of the `S3_3_10_50` pair

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`
- [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md)

**Completed validation:** targeted CLI rerun of the `S3_3_10_50` pair passed
the route/query-class/status parity checks. Both `S3_3_10_50_Q` and
`S3_3_10_50_S` now return `player_on_off` / `summary` / `no_result` with the
explicit on/off unsupported-data note. Required local tests passed with
`make PYTEST="python3 -m pytest" test-parser` and
`make PYTEST="python3 -m pytest" test-query`.

---

## 2. `[ ]` Resolve the shot-creator clutch support-boundary mismatch

**Why:** `S2_2_7_09` is documented as unsupported/future behavior, but the
product currently returns a supported `season_leaders` result with only an
unfiltered clutch note. That makes the examples-library boundary dishonest.

**Scope:**

- Resolve or honestly reclassify:
  - `S2_2_7_09` - "Who's been the best shot creator in clutch time this
    season?"
- Decide whether broad `season_leaders` fallback is acceptable for this
  unsupported shot-creator concept, or whether the query should fail cleanly as
  unsupported/out of scope.
- Do not introduce shot-creator metrics unless they have a documented data
  source and result contract.

**Acceptance criteria:**

- `S2_2_7_09` either passes as an honest unsupported/future boundary or is
  reclassified with clear docs support.
- The behavior does not silently claim execution-backed shot-creator support.
- Docs/catalog/examples remain aligned with the shipped boundary.

**Tests to run:**

- `make test-parser`
- `make test-query`
- `make test-smoke-queries` if real natural-query behavior changes
- targeted rerun of `S2_2_7_09`

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)
- `outputs/parser_examples_full_sweep/results.csv`

---

## 3. `[ ]` Resolve Finals record execution or reclassification blockers

**Why:** Two remaining failures are Finals-specific record examples classified
as supported, while current execution returns unsupported. These need either
documented execution support or honest reclassification.

**Scope:**

- Resolve or honestly reclassify:
  - `S4_4_4_02` - "Celtics finals record"
  - `S4_4_4_10` - "LeBron record in the Finals"
- If implementing execution, keep the logic in command/helper modules and use
  documented data contracts.
- If not implementing execution, update examples/catalog/current-state docs so
  Finals-specific team and player records are not advertised as shipped.

**Acceptance criteria:**

- Both Finals examples pass in targeted reruns, either as execution-backed
  supported behavior or as honestly documented unsupported/out-of-scope
  behavior.
- No new historical/playoff dataset is introduced without a documented
  lifecycle layer, grain, join keys, trust fields, coverage semantics, fallback
  behavior, and placement rationale.
- CLI/API structured output contracts remain stable.

**Tests to run:**

- `make test-engine` if command execution changes
- `make test-query`
- `make test-output` if structured output changes
- `make test-smoke-queries`
- targeted rerun of `S4_4_4_02` and `S4_4_4_10`

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- `outputs/parser_examples_full_sweep/results.csv`

---

## 4. `[ ]` Rerun the full parser-examples sweep after Phase M fixes

**Why:** Phase M must prove that remaining targeted fixes removed the closure
blockers rather than only improving spot checks.

**Scope:**

- Rerun [`parser_examples_full_sweep_protocol.md`](../operations/parser_examples_full_sweep_protocol.md).
- Produce fresh ignored artifacts under `outputs/parser_examples_full_sweep/`.
- Update [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)
  to reflect only unresolved issues from the fresh sweep.
- Compare the new counts against the Phase L 399/3 baseline.

**Acceptance criteria:**

- Fresh sweep artifacts exist.
- The inventory either becomes empty or lists only explicitly unresolved
  closure blockers.
- The improvement or remaining blocker state is documented with exact counts.

**Tests to run:**

- `make parser-examples-sweep`
- `make test-smoke-all`

**Reference artifacts:**

- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`
- [`parser_examples_blocker_inventory.md`](./parser_examples_blocker_inventory.md)

---

## 5. `[ ]` Close the whole plan or draft the next explicit continuation

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
