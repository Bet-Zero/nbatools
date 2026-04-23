# Phase J Lineup Execution and Closure Audit Queue

> **Role:** Sequenced, PR-sized work items for Phase J in
> [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md) —
> resolving lineup placeholder execution and performing the final closure audit
> for parser-shipped-but-not-product-complete capability families.
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the listed
> test commands. Check the item off, commit. Repeat. When every item above is
> checked, work the final meta-task.
>
> **Guardrail:** This queue is lineup execution plus final Part 2 closure only.
> Do not treat whole-game roster membership as lineup-unit execution; real lineup
> results require lineup-unit tables or play-by-play/substitution-derived stints.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## 1. `[x]` Lock the lineup source boundary and execution contract

**Why:** Current lineup routes are honest placeholders. Before replacing them,
the repo needs a source decision for lineup-unit data or an explicit deferral
boundary.

**Scope:**

- Audit current raw/processed data for lineup-capable sources.
- Decide whether Phase J can use upstream lineup-unit tables, play-by-play plus
  substitutions, or must explicitly defer.
- Define the required dataset contract if a source path is viable:
  - unit size and membership keys
  - team/season/sample keys
  - minutes/possessions thresholds
  - supported metrics
  - trust/coverage semantics
- Keep roster snapshots explicitly out of scope as a lineup-unit substitute.

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/reference/data_contracts.md`
- `docs/planning/parser_execution_completion_plan.md`

**Acceptance criteria:**

- The repo has a concrete lineup source decision and contract, or an explicit
  deferral boundary naming the missing upstream artifact.
- The contract states why roster membership is not a lineup-unit source.
- The next implementation target is named exactly.

**Tests to run:**

- None for a docs-only contract item. If code paths change, run `make test-engine`.

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

---

## 2. `[x]` Build or explicitly defer the lineup dataset path

**Why:** `lineup_summary` and `lineup_leaderboard` cannot become real execution
routes without lineup-unit data. If no source is approved, Phase J should record
that explicitly instead of leaving a placeholder in informal limbo.

**Scope:**

- If a source path is viable, add build/backfill, validation, and loader support.
- If no source path is viable, create a review-handoff/deferral note that names:
  - required upstream source
  - why current repo data cannot derive it honestly
  - immediate next action after source approval
- Add tests for dataset normalization/validation/loader behavior if a dataset is
  added.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `docs/planning/phase_j_lineup_data_handoff.md` if deferred
- `tests/`

**Acceptance criteria:**

- A trustworthy lineup dataset can be rebuilt and validated, or the repo has an
  explicit deferral/handoff artifact.
- No implementation approximates lineup execution from roster membership.
- At least 4 tests cover dataset behavior if a dataset is added.

**Tests to run:**

- `make test-engine` if code paths change

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

---

## 3. `[-]` Replace lineup placeholder routes when data exists — skipped because [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md) explicitly defers real lineup execution until a trustworthy lineup-unit, play-by-play + substitution, or stint source is approved

**Why:** The parser already routes lineup queries. Once a trustworthy dataset
exists, `lineup_summary` and `lineup_leaderboard` should return real structured
results.

**Scope:**

- Wire `lineup_summary.build_result()` and `lineup_leaderboard.build_result()`
  to the lineup dataset.
- Support current parser slots:
  - `lineup_members`
  - `unit_size`
  - `minute_minimum`
  - `presence_state` where applicable
- Preserve explicit no-result/unsupported notes for combinations outside the
  dataset contract.

**Files likely touched:**

- `src/nbatools/commands/lineup_summary.py`
- `src/nbatools/commands/lineup_leaderboard.py`
- `tests/`
- `tests/_query_smoke.py`

**Acceptance criteria:**

- Supported lineup queries return real structured results rather than placeholder
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

## 4. `[x]` Final closure audit for Part 2

**Why:** Part 2 exists to prevent parser-shipped families from being mistaken for
product-complete capabilities. The final audit must name every remaining
deferral explicitly.

**Scope:**

- Audit parser spec, parser examples, query catalog, current-state references,
  and planning docs.
- Confirm each Part 2 family is either execution-backed on a documented route
  boundary or explicitly deferred.
- Keep `clutch`, on/off, and lineups explicit if still deferred.

**Files likely touched:**

- `docs/planning/parser_execution_completion_plan.md`
- `docs/planning/phase_f_execution_gap_inventory.md`
- `docs/reference/query_catalog.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`

**Acceptance criteria:**

- No parser-shipped family remains in an implicit “later” state.
- Current-state docs do not overstate deferred capabilities.
- The plan names the final Part 2 status clearly.

**Tests to run:**

- None for docs-only audit. If smoke inventory changes, run
  `make test-phase-smoke` and `make test-smoke-queries`.

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

---

## Phase J retrospective

### Outcome

- Real lineup execution is explicitly deferred under current repo constraints.
- [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md)
  records the source decision, required future artifacts, and the immediate next
  action after source approval.
- `lineup_summary` and `lineup_leaderboard` remain honest placeholders returning
  `NoResult(reason="unsupported")` with explicit lineup data notes.

### Key boundary

- Roster membership is not lineup execution. It identifies season/team
  membership but has no shared-court, stint, possession, or unit-level sample
  boundary.
- A future implementation needs stable lineup-unit tables, play-by-play plus
  substitutions, or a trusted lineup-unit/stint table.

### Final Part 2 closure audit

- `clutch` remains explicitly deferred pending a trustworthy game-grain clutch
  source or play-by-play derivation path.
- quarter / half / OT execution is coverage-gated on `player_game_finder` and
  `team_record`.
- starter / bench execution is coverage-gated on player summary/finder routes
  when trusted starter-role rows exist.
- schedule-context execution is coverage-gated on `team_record` and
  `player_game_summary`.
- on/off is explicitly deferred by Phase I.
- lineups are explicitly deferred by Phase J.

No parser-shipped Part 2 family remains in an implicit “later” state.

### Validation

- No code paths changed in Phase J after the Phase H implementation tests, so no
  additional test target was required for the docs-only deferral and closure
  audit.

---

## 5. `[x]` Phase J retrospective and Part 2 closure statement

**Why:** The final queue should close with a clear product/completion statement,
not an ambiguous absence of unchecked items.

**Scope:**

- Record the final Phase J outcome.
- Update `parser_execution_completion_plan.md` with a closure statement or a
  named follow-up handoff if a blocker remains unresolved.
- Update `docs/index.md` if planning entry points change.

**Acceptance criteria:**

- Part 2 has a clear final status statement.
- Any remaining deferrals are explicitly named with their required future
  source artifacts.
- The repo does not imply product completion for deferred capabilities.

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)
