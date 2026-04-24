# Phase H Schedule-Context Execution Queue

> **Role:** Sequenced, PR-sized work items for Phase H in
> [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md) —
> _execution-backed schedule-context filters after the Phase G period-only queue
> closed with `clutch` still explicitly deferred._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the listed
> test commands. Check the item off, commit. Repeat. When every item above is
> checked, work the final meta-task.
>
> For any item here that changes real natural-query behavior, updating
> `PHASE_H_QUERY_SMOKE_CASES` or the relevant schedule-context cases in
> `tests/_query_smoke.py` and running the listed smoke targets is part of done.
>
> **Guardrail:** This queue is whole-game schedule-context work only. Do not
> fold `clutch` back into Phase H. At queue closure, `clutch` remained
> explicitly deferred pending a trustworthy game-grain clutch source or
> play-by-play derivation path.
>
> **Follow-up (April 24, 2026):** The later master-plan source-approval queue
> approved official `PlayByPlayV3` plus local score-state derivation for future
> clutch work. This Phase H queue remains historical and did not ship clutch
> execution.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## 1. `[x]` Lock the schedule-context feature contract and source boundary

**Why:** Phase F identified the shared feature-join contract, but Phase H still
needs one execution-oriented source decision covering `back_to_back`,
`rest_days`, `one_possession`, and `nationally_televised`.

**Scope:**

- Define the execution-grade dataset or join path that will own schedule-context
  filtering for the initial route set.
- Lock the join keys, required fields, and period-of-record semantics for:
  - `back_to_back`
  - normalized `rest_days`
  - `one_possession`
  - `nationally_televised`
- Record the current source-quality boundary:
  - `national_tv` is still a placeholder in raw schedule pulls until Phase H
    resolves the source
  - one-possession semantics belong in a shared feature table, not ad hoc query
    math inside route owners

**Files likely touched:**

- `docs/reference/data_contracts.md`
- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/planning/parser_execution_completion_plan.md`

**Acceptance criteria:**

- A documented schedule-context feature contract exists with explicit grain, join
  keys, required fields, and initial route ownership.
- The contract states how `back_to_back`, `rest_days`, `one_possession`, and
  `nationally_televised` are represented.
- The repo names the exact next implementation target instead of leaving the
  schedule-context join as an informal note.

**Tests to run:**

- None for a docs-only contract item. If code paths change, run `make test-engine`.

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §4](./phase_f_execution_gap_inventory.md#4-schedule-context-feature-join-contract)
- [`parser_execution_completion_plan.md` §5.3](./parser_execution_completion_plan.md#53-phase-h--schedule-context-execution)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 2. `[x]` Build the schedule-context dataset, validation path, and loaders

**Why:** Route owners should consume one validated whole-game context layer, not
  derive rest, B2B, one-possession, or national-TV state independently.

**Scope:**

- Add the build/backfill command(s) that materialize the shared schedule-context
  dataset from the current raw inputs plus any approved upstream source needed
  for `nationally_televised`.
- Add validation and manifest support so the repo can tell whether the requested
  slice has schedule-context coverage.
- Add or extend loader helpers for the initial route owners.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/pipeline/validate_raw.py`
- `src/nbatools/commands/ops/update_manifest.py`
- `src/nbatools/commands/data_utils.py`
- `tests/` — dataset / loader coverage

**Acceptance criteria:**

- A documented schedule-context dataset exists and can be rebuilt from the
  chosen source path.
- Validation/manifest tooling records whether the dataset is present and
  structurally trustworthy enough for route execution.
- Loader helpers expose the schedule-context fields without mutating the current
  whole-game loaders into ambiguous mixed-grain behavior.
- At least 4 tests cover normalization, validation, or loader behavior.

**Tests to run:**

- `make test-engine`

**Reference docs to consult:**

- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

---

## 3. `[x]` Ship `back_to_back` and `rest_days` execution on the initial routes

**Why:** These two filters share the same schedule-derivation path and are the
lowest-risk whole-game schedule-context items once the feature table exists.

**Scope:**

- Join the schedule-context dataset into `team_record` and `player_game_summary`.
- Apply real `back_to_back` and `rest_days` filtering on those routes.
- Remove the unfiltered-results note for these filters when execution is backed.
- Preserve honest fallback notes where coverage is absent.

**Files likely touched:**

- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/` — route coverage
- `tests/_query_smoke.py`

**Acceptance criteria:**

- `back_to_back` and `rest_days` queries return actually filtered results on the
  documented initial routes.
- These routes no longer append the unfiltered-results note when the filter is
  execution-backed.
- At least 4 tests verify execution and honest fallback behavior.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Schedule-context filters](./phase_f_execution_gap_inventory.md#3-schedule-context-filters)
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_game_summary.py`

---

## 4. `[x]` Ship `one_possession` and `nationally_televised` execution on the initial routes

**Why:** These are the remaining Phase H filters, but they depend on the shared
feature table and need explicit semantics rather than one-off route logic.

**Scope:**

- Join the schedule-context dataset into `team_record` and `player_game_summary`
  for `one_possession` and `nationally_televised`.
- Resolve the honest source/semantics boundary for national-TV tagging.
- Remove the unfiltered-results note for these filters when execution is backed.
- Preserve honest fallback notes where coverage is absent or the selected source
  remains incomplete.

**Files likely touched:**

- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/`
- `tests/_query_smoke.py`

**Acceptance criteria:**

- `one_possession` and `nationally_televised` queries return actually filtered
  results on the documented initial routes.
- The routes retain explicit fallback notes when coverage is absent.
- At least 4 tests verify execution and honest fallback behavior.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`phase_f_execution_gap_inventory.md` §Schedule-context filters](./phase_f_execution_gap_inventory.md#3-schedule-context-filters)
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_game_summary.py`

---

## 5. `[x]` Sync current-state docs and smoke inventory with the shipped Phase H boundary

**Why:** Once schedule-context filters become execution-backed, the repo needs
the docs and smoke inventory to describe the exact route and coverage boundary
without overstating national-TV reliability or implying clutch progress.

**Scope:**

- Update `docs/reference/query_catalog.md`,
  `docs/architecture/parser/specification.md`, and
  `docs/architecture/parser/examples.md`.
- Update `tests/_query_smoke.py` so the Phase H schedule-context surface is
  represented honestly, including explicit exclusions where trusted in-repo
  coverage is not present.
- Keep `clutch` wording explicitly deferred.

**Acceptance criteria:**

- Current-state docs match the shipped Phase H boundary exactly.
- Smoke coverage represents the shipped schedule-context surface honestly.
- Docs do not imply that `clutch` became execution-backed.

**Tests to run:**

- None beyond the shipping-item smoke and test runs above

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

---

## Phase H retrospective

### Shipped boundary

- `schedule_context_features` is now the shared execution-grade team-game table
  for Phase H schedule filters.
- `team_record` and `player_game_summary` execute `back_to_back`, normalized
  `rest_days` / rest advantage, `one_possession`, and `nationally_televised`
  when trusted feature coverage exists for the requested slice.
- `nationally_televised` remains source-quality gated: current placeholder
  schedule pulls can still make national-TV coverage untrusted, in which case
  execution falls back with an explicit unfiltered-results note for that filter.
- Unsupported routes still use the explicit unfiltered-results note instead of
  silently claiming schedule-context execution.

### Implementation notes

- The feature table is built from `team_game_stats` plus `schedule`, keyed by
  `game_id` + `team_id`, so team-relative rest and back-to-back state remain
  unambiguous.
- `rest_days` is normalized to full off days since the previous team game; the
  second game of a back-to-back has `rest_days=0`.
- One-possession semantics are centralized as `abs(score_margin) <= 3` in the
  feature table, not recomputed independently inside route owners.
- Manifest/processed inventory paths include `schedule_context_features` so a
  season is not considered fully processed without the Phase H dataset.

### Remaining blockers

- At Phase H closure, `clutch` was still explicitly deferred pending a
  trustworthy game-grain clutch source or play-by-play derivation path. Phase H
  did not change clutch status.
- Later route expansion can reuse `schedule_context_features`, but Phase H only
  shipped the documented initial boundary: `team_record` and
  `player_game_summary`.
- On/off remains placeholder-backed and is now owned by
  [`phase_i_work_queue.md`](./phase_i_work_queue.md).

### Validation

- `make test-query`
- `make test-engine`

The initial `make test-impacted` run selected 1,370 tests because shared files
changed. It exposed the Phase H compatibility issues fixed in this queue pass,
plus unrelated local-data/stale-expectation failures outside the schedule-context
change set.

---

## 6. `[x]` Phase H retrospective, explicit clutch deferral check, and Phase I queue draft

**Why:** Phase H should close by naming the next active queue cleanly while
keeping the unresolved `clutch` prerequisite visible.

**Scope:**

- Review the schedule-context outcomes and any remaining blockers.
- Draft `phase_i_work_queue.md` for real on/off execution.
- Re-state the current clutch position explicitly:
  - at Phase H closure, still deferred pending a trustworthy game-grain clutch
    source or play-by-play derivation path
  - not completed by Phase G or Phase H

**Files likely touched:**

- `docs/planning/phase_h_work_queue.md` (check this item)
- `docs/planning/phase_i_work_queue.md` (new)
- `docs/planning/parser_execution_completion_plan.md`

**Acceptance criteria:**

- `phase_i_work_queue.md` exists and is the next active queue named by the plan.
- The repo retains an explicit documented clutch deferral.
- Phase H does not close with only an informal residual list.

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
