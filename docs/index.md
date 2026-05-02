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
  planning/                — active plans and active work queues
  archive/                 — completed/superseded planning artifacts
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
- `architecture/design_system.md` — locked visual foundation reference for tokens, typography, color, and component treatment

## Operations — `operations/`

Runbooks and operational guides.

- `operations/pipeline_runbook.md` — data pipeline operations
- `operations/deployment.md` — Cloudflare R2 and Vercel deployment storage setup
- `operations/query_smoke_workflow.md` — terminal-driven natural-query smoke workflow
- `operations/ui_guide.md` — web UI setup, dev workflow, component reference

## Planning — `planning/`

Active master plans, active queues, and near-future planning docs.

- `planning/product_polish_master_plan.md` — single top-level authority for the product polish push from engineering-complete to friends-tier-production-grade
- `planning/visual_foundation_plan.md` — Track A Part 1 plan for design tokens, primitives, app shell, imagery, and team theming foundations
- `planning/component_experience_plan.md` — Track A Part 2 plan for query-class-specific result layouts
- `planning/phase_v2_work_queue.md` — completed Track A visual-foundation primitives queue and Phase V2 retrospective
- `planning/phase_v2_primitives_inventory.md` — primitive needs inventory and API-boundary record produced by Phase V2 item 1
- `planning/phase_v3_work_queue.md` — completed Track A visual-foundation queue for app shell and layout work
- `planning/phase_v3_app_shell_inventory.md` — app-shell ownership and boundary inventory produced by Phase V3 item 1
- `planning/phase_v4_work_queue.md` — completed Track A visual-foundation queue for player imagery, team logos, and team-color plumbing
- `planning/phase_v4_identity_inventory.md` — identity data, target UI surface, and fallback inventory produced by Phase V4 item 1
- `planning/phase_v5_work_queue.md` — completed Track A visual-foundation closure queue for Part 1 retrospective and Part 2 handoff
- `planning/phase_v5_part1_completion_audit.md` — Track A Part 1 done-definition audit produced by Phase V5 item 1
- `planning/phase_v5_component_layout_inventory.md` — Track A Part 2 renderer/data readiness inventory produced by Phase V5 item 2
- `planning/phase_c1_work_queue.md` — completed Track A component-experience queue for player summary layout work
- `planning/phase_c2_work_queue.md` — completed Track A component-experience queue for leaderboard layout work
- `planning/phase_c2_leaderboard_inventory.md` — leaderboard row-shape and metric-priority inventory produced by Phase C2 item 1
- `planning/phase_c3_work_queue.md` — completed Track A component-experience queue for player comparison layout work
- `planning/phase_c3_comparison_inventory.md` — comparison row-shape and renderer-boundary inventory produced by Phase C3 item 1
- `planning/phase_c4_work_queue.md` — completed Track A component-experience queue for player game finder layout work
- `planning/phase_c4_finder_inventory.md` — finder row-shape and renderer-boundary inventory produced by Phase C4 item 1
- `planning/phase_c5_work_queue.md` — completed Track A component-experience queue for team summary, team record, and split layout work
- `planning/phase_c5_team_split_inventory.md` — team summary, record, matchup-record, and split row-shape inventory produced by Phase C5 item 1
- `planning/phase_c6_work_queue.md` — completed Track A component-experience queue for streak and occurrence layout work
- `planning/phase_c6_streak_occurrence_inventory.md` — streak, count, and occurrence row-shape inventory produced by Phase C6 item 1
- `planning/phase_c7_work_queue.md` — completed Track A component-experience queue for head-to-head and playoff layout work
- `planning/phase_c7_head_to_head_playoff_inventory.md` — head-to-head and playoff row-shape inventory produced by Phase C7 item 1
- `planning/phase_c8_work_queue.md` — completed Track A component-experience queue for the full mobile pass across redesigned components
- `planning/phase_c8_mobile_inventory.md` — mobile-risk and verification-fixture inventory produced by Phase C8 item 1
- `planning/phase_c9_work_queue.md` — completed Track A component-experience closure queue for the Part 2 retrospective and Part 3 handoff
- `planning/phase_c9_part2_completion_audit.md` — Track A Part 2 done-definition audit produced by Phase C9 item 1
- `planning/phase_p1_work_queue.md` — completed Track A first-run queue for landing, starter queries, freshness, and first-run mobile polish
- `planning/phase_p1_first_run_inventory.md` — first-run surface, starter-query, freshness, and mobile inventory produced by Phase P1 item 1
- `planning/phase_p2_work_queue.md` — completed Track A loading/error/empty-state queue for designed non-result states and recovery paths
- `planning/phase_p2_state_inventory.md` — loading, empty, no-result, error, retry, and freshness state inventory produced by Phase P2 item 1
- `planning/phase_p3_work_queue.md` — completed Track A broader mobile-verification queue for first-run, result chrome, panels, and result renderers
- `planning/phase_p3_mobile_inventory.md` — mobile viewport, fixture, risk, and evidence inventory produced by Phase P3 item 1
- `planning/phase_p4_work_queue.md` — completed Track A felt-polish queue for keyboard shortcuts, copy/share feedback, stat help, transitions, and history ergonomics
- `planning/phase_p4_felt_polish_inventory.md` — felt-polish current-state, fixture, risk, and verification inventory produced by Phase P4 item 1
- `planning/phase_p5_work_queue.md` — completed Track A Part 3 closure queue for first-run/polish audit, Track A closure, and master-plan handoff
- `planning/phase_p5_part3_completion_audit.md` — Track A Part 3 done-definition audit produced by Phase P5 item 1
- `planning/phase_n1_work_queue.md` — active Track B deployment queue
- `planning/phase_n1_api_inventory.md` — FastAPI route, state, cold-start, and Vercel-refactor inventory produced by Phase N1 item 4
- `planning/data_freshness_plan.md` — data freshness design and implementation plan
- `planning/natural_query_cleanup_plan.md` — natural query cleanup tracker
- `planning/roadmap.md` — planned and future capabilities

## Archive — `archive/`

Completed or superseded planning artifacts preserved for historical reference.

- `archive/completed-plans/` — closed planning authorities and completion plans
- `archive/completed-work-queues/` — historical phase/work queue series
- `archive/handoffs-and-boundaries/` — closed source-boundary docs and handoffs
- `archive/inventories/` — historical inventory/recon docs tied to closed phases
- `archive/product-polish/` — completed product-polish queues and inventories

## Documentation Category Rules

### Reference

Stable, current truth about product behavior. Keep current; archive only when replaced by a newer reference doc.

### Architecture

Long-lived design/convention docs. Archive only when implementation is removed or replaced by a newer architecture decision.

### Operations

Runbooks and workflows. Keep active while workflow exists; archive when workflow is retired.

### Planning

Active master plans and active queues only. Completed queues and superseded plans should move to `archive/`.

### Archive

Historical planning artifacts. Preserved for history and context, but not active continuation authority.

### Audits / Reviews / Verdicts

Point-in-time assessments that can remain in `audits/` (and repo-level verdict docs) unless clearly superseded.

### Working / Temporary Inventories

May live near active plans while a phase is open; once phase closes, move them under `archive/.../inventories/`.

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
2. `archive/completed-plans/master_completion_plan.md`
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
