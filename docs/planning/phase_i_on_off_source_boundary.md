# Phase I On/Off Source Boundary

> Role: Phase I source decision and deferral artifact for
> [`phase_i_work_queue.md`](./phase_i_work_queue.md).

## Decision

Real `player_on_off` execution is explicitly deferred under current repo
constraints.

The repo still does not contain a trustworthy on/off-capable source:

- no play-by-play event table
- no substitution table
- no rotation/stint table
- no upstream on/off split table
- no possession-level on-court/off-court sample table

Because of that, Phase I must not replace the existing `player_on_off`
placeholder with an approximation derived from whole-game logs.

## Why whole-game absence is not on/off

The existing `without_player` execution path removes entire games where a player
appeared. That answers a different question: team/player performance in games
where a player did not play at all.

On/off asks for possession- or stint-level performance while a player is on the
floor versus off the floor within the relevant sample. Whole-game absence cannot
recover that boundary because a game log row has no substitution times, stint
membership, possession counts, or on-court lineup state.

## Required future source

A future on/off implementation needs one of these approved inputs:

- a stable upstream on/off split table with on-court/off-court metrics
- play-by-play plus substitution events sufficient to derive stint membership
- an already-derived local stint table with possession/minute and team scoring
  context

Until one of those exists, the only honest execution behavior is the current
placeholder route with an unsupported-data note.

## Future dataset contract, once a source is approved

If a source is approved later, the dataset should be documented before route
execution changes. A viable contract should include at minimum:

- grain: one row per player/team/season/sample split, or one row per stint if
  execution derives splits dynamically
- keys: `season`, `season_type`, `team_id`, `player_id`, and the source's sample
  identity fields
- split fields: `presence_state` (`on` / `off`) and the queried player identity
- sample-size fields: possessions and/or minutes, plus games represented where
  available
- result metrics: at least `off_rating`, `def_rating`, `net_rating`, and any
  counting/rate fields exposed in structured output
- trust fields: source name, source version or pull date, and coverage flags so
  route execution can fall back honestly for missing slices

## Current route boundary

- `parse_query()` and structured query execution keep routing on/off phrasing to
  `player_on_off`.
- `player_on_off.build_result()` remains a placeholder and returns a
  `NoResult(reason="unsupported")` with an explicit on/off data note.
- `without_player` remains a whole-game absence filter and must not be reused as
  an on/off substitute.

## Immediate next action after source approval

If a trustworthy source is approved, reopen Phase I implementation work by:

1. adding the raw/processed data contract to `docs/reference/data_contracts.md`
2. building the ingestion or derivation path
3. adding validation and loader helpers
4. replacing `player_on_off` placeholder execution with coverage-gated results

Until then, Phase I is execution/data complete by explicit deferral rather than
by shipped on/off computation.
