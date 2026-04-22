# Phase F Work Queue

> **Role:** Sequenced, PR-sized work items for Phase F of [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md) — _execution-gap audit and shared contracts._
>
> **How to work this file:** Find the first unchecked item below. Review the reference docs it cites. Execute per its acceptance criteria. Run the test commands. Check the item off, commit. Repeat. When every item above is checked, work the final meta-task.
>
> **This queue exists because Part 1 is not the finish line.** Parser/query-surface completion is already done; this queue starts the execution/data continuation needed for end-to-end capability completion.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## 1. `[x]` Audit all execution-partial capability families into one inventory

**Why:** The repo currently knows these gaps through a mix of Phase E retrospective notes, parser spec status blocks, examples, and the query catalog. Phase F starts by consolidating that into one execution-oriented inventory so implementation phases are driven by a single source of truth.

**Scope:**

- Inventory every parser-shipped but execution-partial capability family listed in [`parser_execution_completion_plan.md` §4](./parser_execution_completion_plan.md#4-current-open-capability-gaps)
- For each family, record:
  - parser surface / route(s)
  - current execution behavior (`placeholder`, `unfiltered`, `unsupported-data note`, etc.)
  - required data source or aggregation layer
  - current blockers or missing joins
  - authoritative docs that currently describe the behavior
- Produce a consolidated markdown inventory, e.g. `docs/planning/phase_f_execution_gap_inventory.md`

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md` (new)
- Possibly small doc corrections if the audit finds contradictory wording

**Acceptance criteria:**

- Every family in Part 2 scope is represented in one inventory
- Each family is classified as `execution-backed`, `unfiltered`, `placeholder`, or `explicitly deferred`
- The inventory names the exact routes and data prerequisites for each family

**Tests to run:**

- None (audit doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md` §4](./parser_execution_completion_plan.md#4-current-open-capability-gaps)
- [`phase_e_work_queue.md`](./phase_e_work_queue.md)
- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

---

## 2. `[ ]` Map execution-partial families to concrete data and route ownership

**Why:** “Needs data work” is too vague to drive implementation. Each family needs a concrete owner surface: which route executes it, what `route_kwargs` matter, and what data table/join/aggregation is missing.

**Scope:**

- For each audited family, trace the exact execution path in `src/nbatools/query_service.py`, `_natural_query_execution.py`, and the relevant command modules
- Record which existing data files/tables feed the route today and which missing table/join prevents correct execution
- Produce a route/data ownership matrix (can live in the inventory doc or a companion doc)

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md` or a companion matrix doc

**Acceptance criteria:**

- Every execution-partial family has named route ownership
- Every family has named data ownership (existing table vs missing table/join)
- Phase G can target implementation slices without reopening broad exploration

**Tests to run:**

- None (audit doc only)

**Reference docs to consult:**

- [`phase_e_data_inventory.md`](./phase_e_data_inventory.md)
- `src/nbatools/query_service.py`
- `src/nbatools/commands/_natural_query_execution.py`

---

## 3. `[ ]` Define the shared execution prerequisites for context and schedule filters

**Why:** Clutch, period, rest, B2B, one-possession, national TV, and role filtering likely share feature-table or join prerequisites. Documenting the shared prerequisites avoids six one-off fixes.

**Scope:**

- Identify shared feature requirements across clutch, period, schedule, and role filters
- Propose the minimal data contracts needed to support those families honestly
- State which prerequisites are Phase G vs Phase H work

**Files likely touched:**

- `docs/planning/phase_f_execution_gap_inventory.md`
- Possibly a new contract sketch doc if the material is too large

**Acceptance criteria:**

- Shared prerequisites are grouped instead of duplicated per filter
- The boundary between Phase G and Phase H is explicit
- Later queues can target one prerequisite at a time

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md` §§5.2-5.3](./parser_execution_completion_plan.md#52-phase-g--execution-backed-context-filters)
- [`docs/architecture/parser/specification.md` §8](../architecture/parser/specification.md#8-context-filters)

---

## 4. `[ ]` Reconcile current-state docs with Part 2 tracking

**Why:** The reference docs are honest about placeholder and unfiltered behavior, but they should also point readers to the fact that these states are actively tracked in Part 2 rather than left behind after Phase E.

**Scope:**

- Audit whether [`docs/reference/query_catalog.md`](../reference/query_catalog.md), [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md), and [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md) need a brief cross-reference to the Part 2 plan
- Add only the minimum wording needed to make the continuation explicit without turning reference docs into roadmap docs

**Files likely touched:**

- `docs/reference/query_catalog.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`

**Acceptance criteria:**

- Any capability doc that describes a placeholder/unfiltered family can point readers to the active continuation plan without overstating support
- Current-state docs remain current-state docs; they do not become roadmap documents

**Tests to run:**

- None (docs only)

**Reference docs to consult:**

- [`docs/index.md`](../index.md)
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)

---

## 5. `[ ]` Phase F retrospective and Phase G work queue draft

**Why:** Phase F should end with implementation-ready next steps, not another retrospective that admits meaningful work remains without a queue.

**Scope:**

- Review Phase F outcomes and residual ambiguities
- Draft `phase_g_work_queue.md` for execution-backed context filters using the audited inventory and shared prerequisites
- If Phase G truly cannot be authored responsibly yet, write an explicit review-handoff that names:
  - the files/artifacts to review
  - who should review them
  - the immediate next action after review

**Files likely touched:**

- `docs/planning/phase_f_work_queue.md` (check this item)
- `docs/planning/phase_g_work_queue.md` (new), or explicit handoff note if a queue cannot yet be authored
- `docs/planning/parser_execution_completion_plan.md` if phase boundaries need adjustment

**Acceptance criteria:**

- Phase G queue exists, or an explicit review-handoff exists with the exact files and next action
- This queue does not close with only an informal residual list
- This item is checked off

**Tests to run:**

- None (planning/doc only)

**Reference docs to consult:**

- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
- This file as the Phase F record
