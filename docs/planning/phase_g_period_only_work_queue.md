# Phase G Period-Only Continuation Queue

> **Role:** Sequenced, PR-sized work items for the period-only continuation of Phase G in [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md) — _execution-backed quarter / half / overtime filters after the Phase G clutch-source review split the original shared segment scope._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> For any item here that changes real natural-query behavior, updating `PHASE_G_QUERY_SMOKE_CASES` in `tests/_query_smoke.py` and running the listed smoke targets is part of done.
>
> **Do not skip ahead** unless an earlier item is genuinely blocked. Items are ordered to minimize rework — later items assume earlier ones are done.
>
> **⚠️ Guardrail:** This queue is period-only on purpose. Do not approximate `clutch` from whole-game logs, and do not quietly stretch period-window box scores into clutch semantics. `clutch` remains explicitly deferred until a trustworthy game-grain clutch source or play-by-play derivation path is approved.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Phase G segment-review outcome (context for this continuation)

The original Phase G queue grouped `clutch` and `quarter / half / overtime`
under one shared segment-split contract. The review recorded in
[`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)
found that this shared path could not land honestly under current repo
constraints:

- no trustworthy clutch-capable game-grain source was approved
- `BoxScoreTraditionalV3` / `BoxScoreAdvancedV3` window parameters still make
  period-only execution look feasible
- Phase G already landed the shared transport work and the trusted
  starter-role path, so the remaining honest continuation is to split period
  execution from clutch deferral instead of blocking both behind the same
  source decision

This queue continues only the period-backed subset of the former Phase G scope.
`clutch` stays explicitly deferred and should not re-enter implementation here
unless a new reviewed source decision changes the constraint.

---

## 1. `[ ]` Define the period-window data contract and route support boundary

**Why:** The handoff established that period execution can likely use box-score
window endpoints, but the repo still needs one explicit contract that says what
is being backfilled, at what grain, for which routes, and why the contract does
not claim clutch support.

**Scope:**

- Choose the period-window source of record for the initial route set:
  `BoxScoreTraditionalV3`, `BoxScoreAdvancedV3`, or an explicit combination
  where each endpoint owns a documented subset of fields.
- Define the minimal period dataset(s) needed for the currently supported
  quarter / half / OT routes:
  - player-grain period rows for `player_game_finder`
  - team-grain period rows for `team_record`
- Lock the join keys, segment descriptors, and supported period semantics:
  `quarter`, `half`, and `OT`.
- Document the intentional out-of-scope boundary: this contract does not power
  `clutch`.

**Files likely touched:**

- `docs/reference/data_contracts.md`
- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/planning/parser_execution_completion_plan.md`
- Data-pipeline file(s) under `src/nbatools/commands/pipeline/` if a probe or
  command skeleton is committed during the contract work

**Acceptance criteria:**

- A documented period-window contract exists with explicit grain, join keys,
  required fields, and route ownership for the initial route set.
- The contract states exactly how `quarter`, `half`, and `OT` are represented.
- The contract explicitly says that `clutch` remains out of scope because no
  trustworthy game-grain clutch source is currently approved.
- The repo names the exact next implementation target from this contract rather
  than leaving “use `BoxScore*V3` somehow” as an informal note.

**Tests to run:**

- None for a docs-only contract item. If a committed probe or command skeleton
  changes code paths, run `make test-engine`.

**Reference docs to consult:**

- [`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)
- [`phase_f_execution_gap_inventory.md` §2](./phase_f_execution_gap_inventory.md#2-segment-split-data-contract)
- [`parser_execution_completion_plan.md` §5.2](./parser_execution_completion_plan.md#52-phase-g--execution-backed-context-filters)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 2. `[ ]` Build the period-window dataset and validation path

**Why:** Route-level period execution should consume a reusable dataset, not
ad hoc endpoint calls or route-specific one-off joins.

**Scope:**

- Add the backfill command(s) that fan out over the existing
  `data/raw/games/*` inventory and materialize the documented period-window
  dataset(s).
- Normalize the raw endpoint output into the chosen player-grain and team-grain
  period contract.
- Add validation and manifest support so the repo can tell whether a requested
  slice has period coverage.
- Add or extend loader helpers needed by the initial route owners.

**Files likely touched:**

- `src/nbatools/commands/pipeline/` — period-window backfill command(s)
- `src/nbatools/commands/pipeline/validate_raw.py`
- `src/nbatools/commands/ops/update_manifest.py`
- `src/nbatools/commands/data_utils.py`
- `docs/reference/data_contracts.md`
- `tests/` — pipeline / loader coverage

**Acceptance criteria:**

- A documented raw period dataset exists and can be backfilled from the current
  repo inputs plus the chosen upstream box-score window endpoint(s).
- Validation/manifest tooling records whether the dataset is present and
  structurally trustworthy enough for route execution.
- Loader helpers can fetch period rows for the supported route family without
  mutating existing whole-game loaders into ambiguous mixed-grain behavior.
- At least 4 tests cover normalization, validation, or loader behavior for the
  new period dataset path.

**Tests to run:**

- `make test-engine`

**Reference docs to consult:**

- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)
- `src/nbatools/commands/data_utils.py`

---

## 3. `[ ]` Ship quarter / half / overtime execution on `player_game_finder`

**Why:** `player_game_finder` is one of the currently documented routes that
already recognizes period filters but still returns full-game rows with an
explicit unfiltered-results note.

**Scope:**

- Join the period dataset into `player_game_finder` execution.
- Apply real `quarter`, `half`, and `OT` filtering for the supported player
  route.
- Remove the unfiltered-results note for period filters on this route once the
  results are actually filtered.
- Preserve honest notes on any route or slice still outside the period-backed
  support boundary.

**Files likely touched:**

- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/query_service.py`
- `tests/` — player period execution coverage
- `tests/_query_smoke.py` — `PHASE_G_QUERY_SMOKE_CASES`

**Acceptance criteria:**

- `quarter`, `half`, and `OT` queries return actually filtered results on
  `player_game_finder`.
- This route no longer appends the period unfiltered-results note when the
  filter is execution-backed.
- At least 4 tests verify quarter / half / OT execution behavior on
  `player_game_finder`, including honest fallback behavior where applicable.
- `PHASE_G_QUERY_SMOKE_CASES` includes representative player period queries if
  the repo has trusted in-repo coverage for those slices.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Quarter / half / overtime](./phase_f_execution_gap_inventory.md#2-quarter--half--overtime)
- [`docs/architecture/parser/examples.md` §7.8](../architecture/parser/examples.md#78-period-context--4th-quarter-scoring-leaders)
- `src/nbatools/commands/player_game_finder.py`

---

## 4. `[ ]` Ship quarter / half / overtime execution on `team_record`

**Why:** `team_record` is the other currently documented route that should stop
returning full-game results with a period note once a period dataset exists.

**Scope:**

- Join the period dataset into the team-record execution path.
- Apply real `quarter`, `half`, and `OT` filtering for the supported team
  record route.
- Remove the unfiltered-results note for period filters on this route once the
  results are actually filtered.
- Preserve honest notes on any route or slice still outside the period-backed
  support boundary.

**Files likely touched:**

- Team-record command owner under `src/nbatools/commands/`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/` — team-record period execution coverage
- `tests/_query_smoke.py` — `PHASE_G_QUERY_SMOKE_CASES`

**Acceptance criteria:**

- `quarter`, `half`, and `OT` queries return actually filtered results on
  `team_record`.
- This route no longer appends the period unfiltered-results note when the
  filter is execution-backed.
- At least 4 tests verify quarter / half / OT execution behavior on
  `team_record`, including honest fallback behavior where applicable.
- `PHASE_G_QUERY_SMOKE_CASES` includes representative team period queries if the
  repo has trusted in-repo coverage for those slices.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Quarter / half / overtime](./phase_f_execution_gap_inventory.md#2-quarter--half--overtime)
- Team-record command owner under `src/nbatools/commands/`

---

## 5. `[ ]` Sync current-state docs and Phase G smoke inventory with the shipped period boundary

**Why:** Once period filters become execution-backed on the documented initial
routes, the current-state docs and smoke inventory need to describe that exact
boundary without drifting into clutch claims or broader unsupported routes.

**Scope:**

- Update `docs/reference/query_catalog.md`,
  `docs/architecture/parser/specification.md`, and
  `docs/architecture/parser/examples.md` to reflect the real period execution
  boundary.
- Update `tests/_query_smoke.py` so `PHASE_G_QUERY_SMOKE_CASES` covers the
  shipped period-backed surface and keeps honest exclusions for deferred slices.
- Keep `clutch` wording explicitly deferred and unchanged unless a separate
  reviewed source decision lands.

**Files likely touched:**

- `docs/reference/query_catalog.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`
- `tests/_query_smoke.py`

**Acceptance criteria:**

- Current-state docs match the actual period-backed route boundary exactly.
- `PHASE_G_QUERY_SMOKE_CASES` represents the shipped Phase G surface honestly,
  including explicit exclusions where trusted period coverage is not present
  in-repo.
- Docs do not imply that `clutch` became execution-backed as part of this queue.

**Tests to run:**

- None beyond the shipping-item smoke and test runs above

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_g_segment_data_review_handoff.md`](./phase_g_segment_data_review_handoff.md)

---

## 6. `[ ]` Period-only retrospective, explicit clutch deferral note, and Phase H work queue draft

**Why:** This continuation queue should close by naming the next active queue
cleanly, while keeping the unresolved clutch prerequisite explicit instead of
letting it disappear behind the period-only progress.

**Scope:**

- Review the period-only outcomes and any remaining blockers.
- Draft `phase_h_work_queue.md` for schedule-context execution using the shared
  feature-join contract from Phase F.
- Record the post-review clutch state explicitly:
  - still deferred pending a trustworthy game-grain clutch source or
    play-by-play derivation path
  - not completed by the period-only queue

**Files likely touched:**

- `docs/planning/phase_g_period_only_work_queue.md` (check this item)
- `docs/planning/phase_h_work_queue.md` (new)
- `docs/planning/parser_execution_completion_plan.md`
- Possibly a short clutch deferral note if the plan needs a separate artifact

**Acceptance criteria:**

- `phase_h_work_queue.md` exists and is the next active queue named by the plan.
- The repo retains an explicit documented clutch deferral rather than implying
  that all former Phase G work is now complete.
- This queue does not close with only an informal residual list.
- This item is checked off.

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Schedule-context feature-join contract](./phase_f_execution_gap_inventory.md#4-schedule-context-feature-join-contract)
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
