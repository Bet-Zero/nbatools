# Phase J Lineup Source Boundary

> Role: Phase J source decision and deferral artifact for
> [`phase_j_work_queue.md`](./phase_j_work_queue.md).

## Decision

Real lineup execution is explicitly deferred under current repo constraints.

The repo still does not contain a trustworthy lineup-capable source:

- no lineup-unit table
- no play-by-play event table
- no substitution table
- no rotation/stint table
- no possession-level lineup membership table

Because of that, Phase J must not replace `lineup_summary` or
`lineup_leaderboard` placeholders with approximations derived from roster
membership.

## Why roster membership is not lineup execution

The raw roster files identify season/team membership. They do not identify which
players shared the floor, when a unit started or ended, how many possessions or
minutes a unit played, or what scoring happened during that unit's stint.

Lineup queries ask for unit-level performance for 2-man, 3-man, 5-man, or
specific-player groups. Roster membership cannot reconstruct those groups or
their sample sizes.

## Required future source

A future lineup implementation needs one of these approved inputs:

- stable upstream lineup-unit tables with unit membership, minutes/possessions,
  and metrics
- play-by-play plus substitutions sufficient to derive stint-level lineup
  membership
- an already-derived local lineup-unit/stint table with possession/minute and
  scoring context

Until one of those exists, the only honest execution behavior is the current
placeholder route family with unsupported-data notes.

## Future dataset contract, once a source is approved

If a source is approved later, the dataset should be documented before route
execution changes. A viable contract should include at minimum:

- grain: one row per lineup unit/team/season/sample, or one row per stint if
  execution derives units dynamically
- keys: `season`, `season_type`, `team_id`, `unit_size`, and a stable lineup
  membership key
- membership fields: ordered or normalized player IDs/names for the unit
- sample-size fields: minutes and/or possessions, plus games represented where
  available
- thresholds: explicit handling for `minute_minimum`
- result metrics: at least minutes, possessions where available, offensive and
  defensive efficiency or net rating, and any exposed counting/rate fields
- trust fields: source name, source version or pull date, and coverage flags so
  route execution can fall back honestly for missing slices

## Current route boundary

- `parse_query()` and structured query execution keep routing lineup phrasing to
  `lineup_summary` or `lineup_leaderboard`.
- `lineup_summary.build_result()` and `lineup_leaderboard.build_result()` remain
  placeholders returning `NoResult(reason="unsupported")` with explicit lineup
  data notes.
- roster membership remains an identity/enrichment source only and must not be
  reused as a lineup-unit substitute.

## Immediate next action after source approval

If a trustworthy source is approved, reopen lineup implementation work by:

1. adding the raw/processed data contract to `docs/reference/data_contracts.md`
2. building the ingestion or derivation path
3. adding validation and loader helpers
4. replacing lineup placeholder execution with coverage-gated structured results

Until then, Phase J is execution/data complete by explicit deferral rather than
by shipped lineup-unit computation.
