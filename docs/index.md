# NBA Tools Documentation

This docs set reflects the current shipped query surface of NBA Tools.

If you're new, start here and follow the order below.

---

## Start Here

1. `../README.md` — project overview and fastest examples
2. `reference/quick_query_guide.md` — quick-start examples (shortest path to trying queries)
3. `reference/current_state_guide.md` — verified shipped behavior (the source of truth for what works)
4. `reference/query_catalog.md` — living catalog of supported question/query types and common phrasing
5. `reference/query_guide.md` — full structured and natural query reference

---

## Directory Layout

```text
docs/
  index.md                 ← you are here
  reference/               — current-state, verified behavior, data specs
  architecture/            — design docs, conventions, internal layers
  operations/              — runbooks, pipeline ops, UI dev guide
  planning/                — roadmap, active plans
  audits/                  — audit snapshots, historical docs
```

---

## Reference — `reference/`

Current-state documentation and verified behavior specs.

- `reference/current_state_guide.md` — verified shipped behavior
- `reference/quick_query_guide.md` — quick-start examples
- `reference/query_catalog.md` — living catalog of supported question/query types and phrasing patterns
- `reference/query_guide.md` — comprehensive reference (structured + natural)
- `reference/data_catalog.md` — dataset inventory
- `reference/data_contracts.md` — dataset-level contracts
- `reference/result_contracts.md` — **design target** for engine result shapes
- `reference/system_conventions.md` — data format and naming conventions

## Architecture — `architecture/`

Engineering conventions and internal layer design.

- `architecture/project_conventions.md` — engineering conventions and architecture rules
- `architecture/api_layer.md` — FastAPI HTTP layer
- `architecture/query_service_layer.md` — query service interface
- `architecture/structured_result_layer.md` — structured result object design

## Operations — `operations/`

Runbooks and operational guides.

- `operations/pipeline_runbook.md` — data pipeline operations
- `operations/query_smoke_workflow.md` — terminal-driven natural-query smoke workflow
- `operations/ui_guide.md` — web UI setup, dev workflow, component reference

## Planning — `planning/`

Roadmap, active plans, and closed closure records.

- `planning/master_completion_plan.md` — single top-level authority for whole-plan completion status, active continuation, and open core capability families
- `planning/parser_examples_completion_plan.md` — active continuation plan for resolving full-sweep examples-library mismatches
- `planning/parser_examples_blocker_inventory.md` — Phase K blocker inventory derived from the latest full parser-examples sweep
- `planning/phase_k_work_queue.md` — active queue for the parser examples completion plan
- `planning/source_backed_execution_queue.md` — closed master-plan continuation queue that implemented approved clutch, on/off, and lineup source paths
- `planning/source_approval_route_expansion_queue.md` — closed master-plan continuation queue for source approvals and route-expansion product decisions
- `planning/clutch_source_boundary.md` — approved clutch source path and dataset boundary used by shipped source-backed clutch execution
- `planning/roadmap.md` — planned and future capabilities
- `planning/query_surface_expansion_plan.md` — closed Part 1 parser/query-surface expansion plan (subsystem-complete only)
- `planning/parser_execution_completion_plan.md` — closed Part 2 execution/data closure record for parser-shipped capabilities
- `planning/phase_g_work_queue.md` — completed original Phase G queue for execution-backed context filters
- `planning/phase_g_period_only_work_queue.md` — completed period-only continuation queue for quarter / half / OT execution after the Phase G segment-data review
- `planning/phase_g_segment_data_review_handoff.md` — resolved Phase G handoff that split period-only continuation from clutch deferral
- `planning/phase_h_work_queue.md` — completed queue for schedule-context execution after the Phase G period-only continuation
- `planning/phase_i_work_queue.md` — completed queue for real on/off execution / source-boundary deferral
- `planning/phase_i_on_off_source_boundary.md` — approved future on/off source path and implementation requirements
- `planning/phase_j_work_queue.md` — completed queue for lineup execution / source-boundary deferral and final Part 2 closure audit
- `planning/phase_j_lineup_source_boundary.md` — approved future lineup source path and implementation requirements
- `planning/phase_f_work_queue.md` — completed Phase F audit queue and handoff into Phase G
- `planning/phase_f_execution_gap_inventory.md` — consolidated inventory of parser-shipped but execution-partial capability families
- `planning/phase_e_data_inventory.md` — on/off and lineup data-layer audit for Phase E item 7
- `planning/phase_a_work_queue.md` through `planning/phase_e_work_queue.md` — historical Part 1 work-queue series for the query-surface expansion plan
- `planning/phase_a_gap_inventory.md` — reconnaissance of question/search parity gaps (Phase A item 2)
- `planning/data_freshness_plan.md` — data freshness design and implementation plan
- `planning/natural_query_cleanup_plan.md` — natural query cleanup tracker

## Audits — `audits/`

Point-in-time audit snapshots and historical records.

- `audits/architecture_hygiene_audit.md` — full architecture review
- `audits/glue_layer_scope_audit.md` — glue layer scope assessment
- `audits/natural_query_final_scope_audit.md` — natural_query.py final scope audit
- `audits/repo_structure_audit.md` — folder/file architecture audit
- `audits/result_contracts_audit.md` — result contracts audit (pre-structured-result-layer)
- `audits/scripts_retirement.md` — scripts retirement decision record

## Verdicts

- `repo_structure_final_verdict.md` — final assessment: is the repo-structure phase done enough to stop?

## Release History

- `../CHANGELOG.md`

---

## What NBA Tools Currently Supports

- natural-language NBA queries
- structured CLI commands
- player and team leaderboards
- player and team summaries
- player and team comparisons
- split summaries
- matchup / head-to-head phrasing
- month / date-window queries
- `since All-Star break`
- player streaks
- team streaks
- CSV / TXT / JSON exports

---

## Recommended Reading Paths

### Fastest path

1. `reference/quick_query_guide.md`
2. try a few `nbatools-cli ask` queries
3. use `reference/current_state_guide.md` as reference

### Full product understanding

1. `../README.md`
2. `reference/current_state_guide.md`
3. `reference/query_catalog.md`
4. `reference/query_guide.md`
5. `reference/data_catalog.md`
6. `operations/pipeline_runbook.md`

### Extending the system

1. `architecture/project_conventions.md`
2. `planning/master_completion_plan.md`
3. `reference/system_conventions.md`
4. `../CHANGELOG.md`

---

## CLI Entry Points

Main commands:

```bash
nbatools-cli ask
nbatools-cli query
```

Help:

```bash
nbatools-cli --help
nbatools-cli ask --help
nbatools-cli query --help
```

Tests:

```bash
pytest
nbatools-cli test
```

---

## Current Tested State

- full suite: **1650+ passing tests** across 41+ test files
