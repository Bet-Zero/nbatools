> **Archive status:** Completed / superseded historical planning document.
>
> **Current active plan:** See [../../planning/product_polish_master_plan.md](../../planning/product_polish_master_plan.md).
>
> **Do not use this file as the active continuation source.**

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

- Use [`parser_examples_blocker_inventory.md`](../inventories/parser_examples_blocker_inventory.md)
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
- **Closure-pass exception:** when the remaining unchecked items are only the
  final fix/reclassification, the full-sweep rerun, and the master-plan closure
  step, bundle them into a single PR. The per-item PR ceremony is intended for
  larger phases; it is overhead when only the tail of the queue remains.

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

- [`parser_examples_blocker_inventory.md`](../inventories/parser_examples_blocker_inventory.md)
- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`
- [`phase_i_on_off_source_boundary.md`](../handoffs-and-boundaries/phase_i_on_off_source_boundary.md)

**Completed validation:** targeted CLI rerun of the `S3_3_10_50` pair passed
the route/query-class/status parity checks. Both `S3_3_10_50_Q` and
`S3_3_10_50_S` now return `player_on_off` / `summary` / `no_result` with the
explicit on/off unsupported-data note. Required local tests passed with
`make PYTEST="python3 -m pytest" test-parser` and
`make PYTEST="python3 -m pytest" test-query`.

---

## 2. `[x]` Resolve the shot-creator clutch support-boundary mismatch

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

- [`parser_examples_blocker_inventory.md`](../inventories/parser_examples_blocker_inventory.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)
- `outputs/parser_examples_full_sweep/results.csv`

**Completed validation:** targeted sweep-style CLI rerun of `S2_2_7_09`
passed as `unsupported_expected`: the query still returns the broad
`season_leaders` fallback, but CLI JSON metadata now preserves the explicit
`unsupported_boundary` note alongside clutch fallback notes, so it no longer
silently claims execution-backed shot-creator support. Required local tests
passed with `make PYTEST="python3 -m pytest" test-parser`,
`make PYTEST="python3 -m pytest" test-query`, and
`make PYTEST="python3 -m pytest" test-smoke-queries`.

---

## 3. `[x]` Bundled closure: resolve remaining Finals failures, rerun the full sweep, and close the plan

**Why:** Two remaining failures (`S4_4_4_02`, `S4_4_4_10`) are the only thing
between Phase M and whole-plan closure. With the queue tail this short, the
fix, the proof rerun, and the closure update belong in one PR — splitting them
adds CI/wait overhead without changing the outcome.

**Scope:**

- Resolve both Finals failures, in the same PR:
  - `S4_4_4_02` - "Celtics finals record"
  - `S4_4_4_10` - "LeBron record in the Finals"
- Decide fix vs reclassify using the default rule in
  [`parser_examples_completion_plan.md`](./parser_examples_completion_plan.md)
  §12 (reclassify when no documented source path exists; route the parser when
  the route exists but isn't being matched). Do not re-litigate the choice
  beyond applying the default.
- If reclassifying, move the affected lines in
  [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md),
  [`docs/reference/query_catalog.md`](../reference/query_catalog.md), and
  [`docs/reference/current_state_guide.md`](../reference/current_state_guide.md)
  to honest unsupported/out-of-scope wording in a single doc-sync pass.
- If implementing execution, keep logic in existing command/helper modules and
  reuse documented data contracts; do not introduce a new historical/playoff
  dataset under this queue.
- Rerun the full parser-examples sweep once, at the end of the same PR.
- Refresh [`parser_examples_blocker_inventory.md`](../inventories/parser_examples_blocker_inventory.md)
  with the fresh counts.
- Update [`master_completion_plan.md`](../completed-plans/master_completion_plan.md) to either
  declare the whole plan done (preferred path if the sweep is clean) or, only
  if a true unresolved blocker family remains, name the next continuation.

**Acceptance criteria:**

- Both Finals cases pass in the fresh full sweep (as supported behavior or as
  honestly documented unsupported/out-of-scope behavior).
- Fresh sweep artifacts exist under `outputs/parser_examples_full_sweep/`.
- The blocker inventory is empty or lists only explicitly resolved items.
- `master_completion_plan.md` names exactly one active continuation or states
  the whole plan is done, citing the latest sweep counts.
- CLI/API structured output contracts remain stable.

**Tests to run:**

- `make test-impacted` for narrowly-scoped doc/parser-only changes; promote to
  `make test-parser` / `make test-query` / `make test-engine` /
  `make test-output` only if the corresponding code layer actually changes.
- `make parser-examples-sweep` (one rerun, at end).
- `make test-smoke-queries` (full smoke is only required if execution changes).

**Reference artifacts:**

- [`parser_examples_blocker_inventory.md`](../inventories/parser_examples_blocker_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)
- [`docs/reference/current_state_guide.md`](../reference/current_state_guide.md)
- `outputs/parser_examples_full_sweep/results.csv`
- `outputs/parser_examples_full_sweep/report.md`

**Completed validation:** applied the §12 default reclassification path for
`S4_4_4_02` and `S4_4_4_10` because Finals-specific team/player records do not
have an approved entity-grain playoff-round record data contract. Targeted CLI
reruns of both original queries returned clean `no_result` / `unsupported`
responses. Required local validation passed with
`make PYTEST="python3 -m pytest" test-impacted` (2544 passed, 1 xpassed; the
local testmon cache invalidated and reselected the full serial suite). The
closure sweep passed with `make PYTHON=python3 parser-examples-sweep`: 402
total cases, 402 passing cases, 0 failing cases, 0 phrasing-pair mismatches,
and 0 equivalence-group mismatches.
