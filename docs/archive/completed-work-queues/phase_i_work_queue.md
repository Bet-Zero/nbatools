> **Archive status:** Completed / superseded historical planning document.
>
> **Current active plan:** See [../../planning/product_polish_master_plan.md](../../planning/product_polish_master_plan.md).
>
> **Do not use this file as the active continuation source.**

# Phase I On/Off Execution Queue

> **Role:** Sequenced, PR-sized work items for Phase I in
> [`parser_execution_completion_plan.md`](../completed-plans/parser_execution_completion_plan.md) —
> replacing the current `player_on_off` placeholder with data-backed execution,
> or explicitly deferring it with a documented source boundary.
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the listed
> test commands. Check the item off, commit. Repeat. When every item above is
> checked, work the final meta-task.
>
> **Guardrail:** This queue is on/off only. Do not fold lineup-unit execution
> into Phase I; lineups remain Phase J. Whole-game `without_player` filters are
> already separate from possession-level on/off and must not be reused as a fake
> on/off implementation.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## 1. `[x]` Lock the on/off source boundary and execution contract

**Why:** The current `player_on_off` route is an honest placeholder because the
repo has no on/off split table, play-by-play, substitution, or stint source. The
first Phase I step must decide the exact source path before any route work can
claim execution support.

**Scope:**

- Audit current raw/processed data for on/off-capable sources.
- Decide whether Phase I can use an upstream on/off split table, a local
  play-by-play + substitution-derived stint model, or must explicitly defer.
- Define the required dataset contract if a source path is viable:
  - grain
  - join keys
  - on/off identity fields
  - sample and possession/minutes fields
  - supported metrics
  - coverage/trust semantics
- Keep whole-game absence (`without_player`) explicitly out of scope for
  possession-level on/off.

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/reference/data_contracts.md`
- `docs/planning/parser_execution_completion_plan.md`

**Acceptance criteria:**

- The repo has a concrete on/off source decision and contract, or an explicit
  deferral boundary naming the missing upstream artifact.
- The contract states why whole-game absence is not a substitute for on/off.
- The next implementation target is named exactly instead of leaving on/off as
  a generic placeholder.

**Tests to run:**

- None for a docs-only contract item. If code paths change, run `make test-engine`.

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](../inventories/phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](../inventories/phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 2. `[x]` Build or explicitly defer the on/off dataset path

**Why:** Route execution can only proceed if a trustworthy data source exists.
If no source is approved within current repo constraints, Phase I should stop
with an explicit deferral artifact rather than approximating on/off from
whole-game logs.

**Scope:**

- If a source path is viable, add the backfill/build command and validation
  path for the on/off dataset.
- If no source path is viable, create a review-handoff/deferral note that names:
  - required upstream source
  - why current repo data cannot derive it honestly
  - immediate next action after source approval
- Add loader helpers only when a real dataset exists.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/pipeline/validate_raw.py`
- `docs/planning/phase_i_on_off_data_handoff.md` if deferred
- `tests/`

**Acceptance criteria:**

- A trustworthy on/off dataset can be rebuilt and validated, or the repo has an
  explicit deferral/handoff artifact.
- No implementation approximates on/off from whole-game absence.
- At least 4 tests cover dataset normalization/validation/loader behavior if a
  dataset is added.

**Tests to run:**

- `make test-engine` if code paths change

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](../inventories/phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](../inventories/phase_f_execution_gap_inventory.md)

---

## 3. `[-]` Replace `player_on_off` placeholder execution when data exists — skipped at Phase I closure because no trustworthy source was then approved; later master-plan queues approved and implemented `teamplayeronoffsummary`

**Why:** The dedicated route already exists. Once a trustworthy dataset exists,
the placeholder should become execution-backed without changing parser
semantics.

**Scope:**

- Wire `player_on_off.build_result()` to the on/off dataset.
- Support current parser slots:
  - `lineup_members`
  - `presence_state`
  - player/team/season/time filters already routed to the placeholder where
    applicable
- Preserve explicit no-result/unsupported notes for combinations outside the
  dataset contract.

**Files likely touched:**

- `src/nbatools/commands/player_on_off.py`
- `src/nbatools/commands/_natural_query_execution.py` if transport changes are needed
- `tests/`
- `tests/_query_smoke.py`

**Acceptance criteria:**

- Supported on/off queries return real structured results rather than placeholder
  no-results.
- Unsupported/coverage-missing queries retain honest no-result or fallback notes.
- At least 4 tests cover execution and unsupported boundaries.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

---

## 4. `[x]` Sync current-state docs and smoke inventory with the Phase I boundary

**Why:** Whether Phase I ships execution or an explicit deferral, current-state
docs must describe the exact boundary and avoid implying that `without_player`
answers on/off.

**Scope:**

- Update `docs/reference/query_catalog.md`,
  `docs/architecture/parser/specification.md`, and
  `docs/architecture/parser/examples.md`.
- Update `tests/_query_smoke.py` for the shipped on/off boundary.
- Keep lineup placeholder wording unchanged unless Phase J has started.

**Acceptance criteria:**

- Current-state docs match the shipped on/off boundary exactly.
- Smoke coverage represents either real execution or explicit deferral honestly.
- Docs continue to distinguish whole-game absence from possession-level on/off.

**Tests to run:**

- None beyond the implementation-item smoke/test runs above

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](../inventories/phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](../inventories/phase_f_execution_gap_inventory.md)

---

## 5. `[x]` Phase I retrospective and Phase J queue draft

**Why:** Phase I should close by naming the lineup continuation path cleanly,
whether on/off execution shipped or was explicitly deferred.

**Scope:**

- Review the on/off outcome and any remaining blockers.
- Draft `phase_j_work_queue.md` for lineup execution and closure audit.
- Re-state any unresolved on/off deferral explicitly if Phase I could not ship
  execution.

**Files likely touched:**

- `docs/planning/phase_i_work_queue.md` (check this item)
- `docs/planning/phase_j_work_queue.md` (new)
- `docs/planning/parser_execution_completion_plan.md`

**Acceptance criteria:**

- `phase_j_work_queue.md` exists and is the next active queue named by the plan,
  or an explicit review-handoff exists if Phase J cannot responsibly be authored.
- Phase I does not close with only an informal residual list.

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](../completed-plans/parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](../inventories/phase_f_execution_gap_inventory.md)

---

## Phase I retrospective

### Outcome

- Real `player_on_off` execution was unshipped at Phase I closure.
- [`phase_i_on_off_source_boundary.md`](../handoffs-and-boundaries/phase_i_on_off_source_boundary.md)
  records the source decision, required future artifacts, and the immediate next
  action after source approval. A later master-plan source-approval queue
  approved upstream `teamplayeronoffsummary` via
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary` for future implementation.
- The existing `player_on_off` route remains an honest placeholder returning
  `NoResult(reason="unsupported")` with the on/off data note.

### Key boundary

- Whole-game `without_player` absence is not on/off. It excludes entire games
  and cannot recover on-court/off-court possession or stint boundaries.
- The approved future implementation path is the upstream
  `teamplayeronoffsummary` split table; whole-game absence remains rejected as a
  substitute.

### Remaining blockers

- No `team_player_on_off_summary` dataset, validation path, loader, or
  coverage-gated route execution existed at Phase I closure. A later
  source-backed execution queue added those pieces for the approved
  `teamplayeronoffsummary` boundary.
- Lineups remain placeholder-backed and are now owned by
  [`phase_j_work_queue.md`](./phase_j_work_queue.md).

### Validation

- No code paths changed in Phase I after the Phase H implementation tests, so no
  additional test target was required for the docs-only deferral.
