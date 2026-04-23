# NBA Tools — Pipeline Runbook

This document explains how the NBA Tools pipeline is operated.

It covers:
- core commands
- workflow order
- retry / skip behavior
- backfill usage
- failure handling

---

# 1. Core Pipeline Flow

The standard season pipeline is:

1. pull raw tables
2. validate raw tables
3. build processed tables
4. update manifest

This is automated by `backfill-season`.

---

# 2. Core Commands

## Backfill one season
`nbatools-cli backfill-season --season 2024-25 --season-type "Regular Season"`

## Backfill one season and skip already-built outputs
`nbatools-cli backfill-season --season 2024-25 --season-type "Regular Season" --skip-existing`

## Backfill a range
`nbatools-cli backfill-range --start-season 2018-19 --end-season 2020-21 --include-playoffs`

## Backfill a range and skip existing outputs
`nbatools-cli backfill-range --start-season 2018-19 --end-season 2020-21 --include-playoffs --skip-existing`

## Inventory
`nbatools-cli inventory`

## Show manifest
`nbatools-cli show-manifest`

---

# 3. What `backfill-season` Does

For a given season and season_type, `backfill-season` runs:

## Raw pulls
- `pull-games`
- `pull-schedule`
- `pull-rosters`
- `pull-team-game-stats`
- `pull-player-game-stats`
- `pull-standings-snapshots` (regular season only)
- `pull-team-season-advanced`
- `pull-player-season-advanced`

## Validation
- `validate-raw`

## Processed builds
- `build-team-game-features`
- `build-game-features`
- `build-schedule-context-features`
- `build-player-game-features`
- `build-league-season-stats`

## Metadata
- `update-manifest`

---

# 4. Playoff Handling

## Playoff rules
- playoffs use the same schema as regular season
- `season_type = "Playoffs"`
- standings snapshots do not exist for playoffs

## Current-season playoff skip behavior
If playoffs have not started yet and no data exists:
- `backfill-season` will skip that season/type cleanly
- it will not print a large traceback
- `backfill-range` can continue safely

Example:
- `2025-26 Playoffs` before playoff games exist

---

# 5. Skip-Existing Behavior

## Purpose
Avoid rerunning already-complete seasons.

## Rule
If all processed output files already exist for a season/type, and `--skip-existing` is used:
- the season/type is skipped
- no new API calls are made
- this is safe for incremental reruns

---

# 6. Failure Handling

## If a season fails partway through
Do not rerun everything blindly.

Instead:
1. identify the failed season/type
2. rerun that season directly
3. if needed, resume later range runs with `--skip-existing`

Example:
`nbatools-cli backfill-season --season 2009-10 --season-type "Regular Season"`

## Common causes of failure
- transient NBA API timeouts
- empty API responses
- historical endpoint flakiness
- current-season playoffs not available yet

---

# 7. Manifest Meaning

`backfill_manifest.csv` tracks whether a season/type is complete.

## `raw_complete = 1`
All expected raw files exist for that season/type.

## `processed_complete = 1`
All expected processed files exist for that season/type.

## `loaded_at`
Timestamp when the manifest row was last updated.

---

# 8. Inventory Meaning

`inventory` is a dashboard-style scan of the data warehouse.

It shows:
- file counts
- earliest / latest season
- current playoff availability
- manifest alignment
- raw season-only labels
- raw season-type labels
- processed season-type labels

If `raw vs manifest aligned` and `processed vs manifest aligned` are both `True`, the warehouse is internally aligned.

---

# 9. Recommended Operating Pattern

## For new historical chunks
Use:
`nbatools-cli backfill-range --start-season XXXX-YY --end-season YYYY-ZZ --include-playoffs --skip-existing`

## For current season refreshes
Use:
`nbatools-cli backfill-season --season 2025-26 --season-type "Regular Season"`

## After major runs
Check:
- `nbatools-cli inventory`
- `nbatools-cli show-manifest`
- `du -sh data`

---

# 10. Current Coverage

Current known coverage:

- `1996-97` through `2024-25`: Regular Season + Playoffs
- `2025-26`: Regular Season only

Update this section if historical coverage expands.
