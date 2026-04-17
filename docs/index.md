# NBA Tools Documentation

This docs set reflects the current shipped query surface of NBA Tools.

If you're new, start here and follow the order below.

---

## Start Here

1. `../README.md` — project overview and fastest examples
2. `quick_query_guide.md` — quick-start examples (shortest path to trying queries)
3. `current_state_guide.md` — verified shipped behavior (the source of truth for what works)
4. `query_guide.md` — full structured and natural query reference

---

## Core Guides

### Project overview

- `../README.md`

### Current query surface

- `current_state_guide.md` — verified shipped behavior
- `quick_query_guide.md` — quick-start examples
- `query_guide.md` — comprehensive reference (structured + natural)

### Data and pipeline

- `data_catalog.md`
- `pipeline_runbook.md`

### System design

- `project_conventions.md` — engineering conventions and architecture rules
- `system_conventions.md` — data format and naming conventions

### Result contracts

- `result_contracts.md` — **design target** for engine result shapes
- `result_contracts_audit.md` — historical audit snapshot (pre-structured-result-layer)

### Internal architecture

- `query_service_layer.md` — query service interface
- `structured_result_layer.md` — structured result object design
- `api_layer.md` — FastAPI HTTP layer

### UI

- `ui_guide.md` — web UI setup, dev workflow, component reference

### Release history

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

1. `quick_query_guide.md`
2. try a few `nbatools-cli ask` queries
3. use `current_state_guide.md` as reference

### Full product understanding

1. `../README.md`
2. `current_state_guide.md`
3. `query_guide.md`
4. `data_catalog.md`
5. `pipeline_runbook.md`

### Extending the system

1. `project_conventions.md`
2. `system_conventions.md`
3. `../CHANGELOG.md`

---

## CLI Entry Points

Main commands:

    nbatools-cli ask
    nbatools-cli query

Help:

    nbatools-cli --help
    nbatools-cli ask --help
    nbatools-cli query --help

Tests:

    pytest
    nbatools-cli test

---

## Current Tested State

- full suite: **1650+ passing tests** across 41+ test files
