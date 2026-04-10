# NBA Tools Documentation

This docs set reflects the current shipped query surface of NBA Tools.

If you're new, start here and follow the order below.

---

## Start Here

1. `../README.md` — project overview and fastest examples
2. `quick_query_guide.md` — short mental model and starter queries
3. `current_state_guide.md` — current supported behavior
4. `../QUERY_GUIDE.md` — deeper structured and natural query reference

---

## Core Guides

### Project overview
- `../README.md`

### Current query surface
- `current_state_guide.md`
- `quick_query_guide.md`
- `../QUERY_GUIDE.md`

### Data and pipeline
- `../DATA_CATALOG.md`
- `../PIPELINE_RUNBOOK.md`

### System design
- `../SYSTEM_CONVENTIONS.md`
- `../SCHEMA_FINAL_DECISIONS.md`

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
3. `../QUERY_GUIDE.md`
4. `../DATA_CATALOG.md`
5. `../PIPELINE_RUNBOOK.md`

### Extending the system
1. `../SYSTEM_CONVENTIONS.md`
2. `../SCHEMA_FINAL_DECISIONS.md`
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

- full suite: **206 passing tests**
