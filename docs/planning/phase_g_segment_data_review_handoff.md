# Phase G Segment-Data Review Handoff

> **Review outcome (April 23, 2026):** No trustworthy clutch-capable game-grain
> source was approved under current repo constraints. The repo now continues
> quarter / half / OT work in
> [`phase_g_period_only_work_queue.md`](./phase_g_period_only_work_queue.md) and
> keeps `clutch` explicitly deferred pending a play-by-play or equivalent
> game-grain source.
>
> **Follow-up (April 24, 2026):** The master-plan source-approval queue later
> approved official `PlayByPlayV3` plus local score-state derivation as the
> future clutch source path. See
> [`clutch_source_boundary.md`](./clutch_source_boundary.md). This follow-up
> does not change the Phase G historical outcome or ship clutch execution.

## Why This Exists

Phase G item 3 asked for one shared segment-split contract that could back
both period filters (`quarter`, `half`, `OT`) and clutch filters from a
game-grain source.

That shared contract could not be landed honestly under the current repo
constraints, so this handoff records the blocker and the exact next review
step instead of leaving an informal residual note.

## What Was Reviewed

- Current repo data under `data/raw/` and `data/processed/`
- Installed `nba_api` endpoint surfaces and schemas
- Existing Phase G execution/planning docs:
  - `docs/planning/phase_f_execution_gap_inventory.md`
  - `docs/planning/phase_g_work_queue.md`
  - `docs/planning/parser_execution_completion_plan.md`

## Findings

### 1. The repo still has no in-repo segment tables

Current raw and processed data remain whole-game only. There is no existing:

- player-grain segment table
- team-grain segment table
- play-by-play source
- score-state feature layer that could define official clutch possessions

### 2. Period data appears reachable from box-score window endpoints

Installed `nba_api` inspection shows:

- `BoxScoreTraditionalV3(game_id, start_period, end_period, start_range, end_range, range_type, ...)`
- `BoxScoreAdvancedV3(game_id, start_period, end_period, start_range, end_range, range_type, ...)`

These endpoints expose period-window parameters and are a plausible source for
quarter / half / OT backfill at game grain.

### 3. The available clutch endpoints are not game-grain joinable

Installed endpoint inspection also showed:

- `PlayerDashboardByClutch`
- `LeagueDashPlayerClutch`

But their schemas are season aggregates. They do not expose `game_id`, so they
cannot support:

- `player_game_finder`
- `team_record`
- a reusable segment table keyed back to existing game-log routes

The same pattern holds for season split dashboards like
`PlayerDashboardByGameSplits`: they provide aggregated split buckets, not
game-grain rows.

### 4. The shared Phase G segment item is therefore blocked on clutch source choice

Phase G item 3 required one reusable contract that can represent both period
and clutch contexts without inventing separate ad hoc tables. Under current
constraints, period looks feasible, but clutch does not have a trustworthy
game-grain source in-repo or in the currently inspected upstream endpoint
surface.

That means the exact shared contract requested by item 3 cannot be shipped
honestly yet.

## Files / Artifacts Produced During Phase G Before This Blocker

- `src/nbatools/commands/pipeline/pull_player_game_starter_roles.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/pipeline/validate_raw.py`
- `src/nbatools/commands/ops/update_manifest.py`
- `src/nbatools/commands/pipeline/orchestrator.py`
- `docs/reference/data_contracts.md`
- `docs/reference/query_catalog.md`
- `docs/architecture/parser/specification.md`
- `docs/architecture/parser/examples.md`

## Review Target

Review the missing clutch-capable artifact decision:

- either an official game-grain clutch split source keyed by `game_id`
- or a play-by-play ingest/derivation path that can reproduce the glossary
  clutch definition (`last 5 min of 4th quarter or OT, score within 5`)

## Immediate Next Action After Review

Choose one of these paths explicitly:

1. If a trustworthy game-grain clutch source is approved, keep the shared
   Phase G segment-contract design and implement a single segment backfill for
   period + clutch.
2. If no such clutch source is available, split the work:
   - draft a period-only continuation queue that uses `BoxScore*V3` window
     backfills for quarter / half / OT
   - defer clutch to a later play-by-play / upstream-source phase with an
     explicit blocker note

Do not approximate clutch from whole-game logs.
