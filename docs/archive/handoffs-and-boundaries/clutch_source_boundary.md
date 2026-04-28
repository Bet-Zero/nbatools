> **Archive status:** Completed / superseded historical planning document.
>
> **Current active plan:** See [../../planning/product_polish_master_plan.md](../../planning/product_polish_master_plan.md).
>
> **Do not use this file as the active continuation source.**

# Clutch Source Boundary

> Role: source approval and future implementation contract for clutch execution
> from [`source_approval_route_expansion_queue.md`](../completed-work-queues/source_approval_route_expansion_queue.md).

## Decision

The approved source path for future clutch execution is an official NBA
play-by-play event feed, normalized from `nba_api.stats.endpoints.PlayByPlayV3`,
plus local score-state derivation.

This approves the source path only. It does not ship clutch-filtered query
execution. Current natural queries that set `clutch=True` must keep returning
the explicit unfiltered-results note until the implementation queue builds,
validates, and wires the derived clutch datasets into route execution.

## Why this source is approved

`PlayByPlayV3` exposes a game-grain event stream with fields needed to identify
the NBA clutch window:

- `gameId`
- `actionNumber`
- `clock`
- `period`
- `teamId`
- `teamTricode`
- `personId`
- `playerName`
- `actionType`
- `subType`
- `description`
- `scoreHome`
- `scoreAway`

Those fields are sufficient for a validated derivation layer to identify events
in the last five minutes of the fourth quarter or overtime when the score is
within five points.

The existing NBA clutch dashboard endpoints remain rejected for route
execution. They are season aggregates and do not expose `game_id`, so they
cannot join honestly to player-game or team-game route outputs.

## Rejected substitutes

The following inputs are not approved as clutch sources:

- whole-game player or team logs
- period-only box-score window rows from `BoxScoreTraditionalV3` or
  `BoxScoreAdvancedV3`
- season-level clutch dashboard aggregates without `game_id`
- roster, starter-role, schedule-context, or period datasets

Whole-game logs have no time/score boundary. Period-only rows can isolate the
fourth quarter or overtime but cannot isolate score-within-five possessions.

## Required future datasets

A future implementation should define both a raw normalized play-by-play event
contract and derived clutch aggregates before route execution changes.

### `play_by_play_events`

Minimum contract:

- path pattern: `data/raw/play_by_play_events/{season}_{season_type_safe}.csv`
- grain: one row per NBA play-by-play event
- keys: `season`, `season_type`, `game_id`, `action_number`
- identity fields: `team_id`, `team_abbr`, `player_id`, `player_name`
- event fields: `period`, `clock`, `action_type`, `sub_type`,
  `description`, `score_home`, `score_away`
- trust fields: `pbp_source`, `pbp_source_trusted`, `pbp_validation_reason`

### `player_game_clutch_stats`

Minimum contract:

- path pattern: `data/processed/player_game_clutch_stats/{season}_{season_type_safe}.csv`
- grain: one row per player-game clutch sample
- keys: `season`, `season_type`, `game_id`, `team_id`, `player_id`
- clutch definition fields: `clutch_window`, `clutch_time_remaining_start`,
  `clutch_score_margin_max`
- sample-size fields: `clutch_events`, `clutch_seconds`, and possessions when
  the possession parser is validated
- metrics: traditional counting fields derivable from the event feed, plus
  rate/efficiency fields only after their denominators are validated
- trust fields: `clutch_source`, `clutch_source_trusted`,
  `clutch_validation_reason`

### `team_game_clutch_stats`

Minimum contract:

- path pattern: `data/processed/team_game_clutch_stats/{season}_{season_type_safe}.csv`
- grain: one row per team-game clutch sample
- keys: `season`, `season_type`, `game_id`, `team_id`
- clutch definition fields: `clutch_window`, `clutch_time_remaining_start`,
  `clutch_score_margin_max`
- sample-size fields: `clutch_events`, `clutch_seconds`, and possessions when
  the possession parser is validated
- metrics: team scoring and traditional event-derived totals, plus rating
  fields only after possession counts are validated
- outcome fields: final `wl` may be joined from `team_game_stats`; clutch-only
  lead-change or plus/minus fields must come from the derived event sample
- trust fields: `clutch_source`, `clutch_source_trusted`,
  `clutch_validation_reason`

## Coverage and fallback behavior

Clutch execution must be coverage-gated.

Commands may use a derived clutch row only when `clutch_source_trusted=1` for
the requested game/team/player slice. Missing, incomplete, or untrusted
play-by-play coverage must keep the current honest unfiltered-results note
instead of partially mixing clutch rows with whole-game logs.

The route boundary should start with the already transported clutch routes:

- `player_game_summary`
- `player_game_finder`
- `team_record`
- `season_leaders`

If the first implementation queue narrows that route list for risk control, it
must document the narrower boundary in the queue and current-state docs before
removing fallback notes on any route.

## Historical next action after source approval

The implementation path after source approval was
[`source_backed_execution_queue.md`](../completed-work-queues/source_backed_execution_queue.md), which
included clutch items that started with:

1. documenting the final data contracts in `docs/reference/data_contracts.md`
2. adding a `PlayByPlayV3` ingestion/backfill path
3. validating score-state and trust coverage

Current whole-plan status and active continuation are controlled only by
[`master_completion_plan.md`](../completed-plans/master_completion_plan.md).
4. deriving player-game and team-game clutch aggregates
5. wiring coverage-gated execution into the supported route boundary
6. replacing the unfiltered clutch note only on routes that truly execute the
   clutch filter
