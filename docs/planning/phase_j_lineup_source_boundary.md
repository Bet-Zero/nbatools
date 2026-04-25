# Phase J Lineup Source Boundary

> Role: Phase J source decision and deferral artifact for
> [`phase_j_work_queue.md`](./phase_j_work_queue.md).

## Decision

The future lineup-unit source path is approved:
`nba_api.stats.endpoints.LeagueLineupViz`, normalized from the upstream
`leaguelineupviz` endpoint.

This artifact was originally a source approval only. The later
[`source_backed_execution_queue.md`](./source_backed_execution_queue.md)
implemented the ingestion, validation, loader, and coverage-gated route
execution path for the approved source boundary.

The repo still does not contain play-by-play, substitution, rotation, or local
stint tables. Lineup execution is limited to the approved upstream
`LeagueLineupViz` source boundary.

The approved upstream lineup table is a better fit for the current route
contract than roster membership because it exposes lineup-unit identity
(`GROUP_ID` / `GROUP_NAME`), team identity, unit minutes, efficiency metrics
including `OFF_RATING`, `DEF_RATING`, and `NET_RATING`, and a source-level
`MinutesMin` parameter for minimum-minute thresholds.

## Why roster membership is not lineup execution

The raw roster files identify season/team membership. They do not identify which
players shared the floor, when a unit started or ended, how many possessions or
minutes a unit played, or what scoring happened during that unit's stint.

Lineup queries ask for unit-level performance for 2-man, 3-man, 5-man, or
specific-player groups. Roster membership cannot reconstruct those groups or
their sample sizes.

## Approved source contract

The raw future dataset should be documented as
`data/raw/league_lineup_viz/{season}_{season_type_safe}.csv` before
implementation changes route behavior.

Minimum contract:

- source endpoint: `leaguelineupviz`, called through
  `nba_api.stats.endpoints.LeagueLineupViz`
- source grain: lineup-unit rows for a requested unit size and minimum-minute
  threshold
- normalized grain: one row per `season`, `season_type`, `team_id`,
  `unit_size`, `lineup_id`, and `minute_minimum`
- keys: `season`, `season_type`, `team_id`, `unit_size`, `lineup_id`,
  `minute_minimum`
- membership fields: source `GROUP_ID` and `GROUP_NAME`, normalized into
  `lineup_id`, `lineup_name`, `player_ids`, and `player_names`
- sample-size fields: `minutes`; possessions and games represented are not
  exposed by the approved minimum source and must remain unavailable unless a
  later implementation adds a separately approved enrichment source
- threshold field: `minute_minimum`, backed by the source `MinutesMin`
  parameter
- result metrics: `off_rating`, `def_rating`, `net_rating`, `pace`, `ts_pct`,
  and the additional rate fields exposed by the source
- trust fields: `source_endpoint`, `source_pull_date`, `source_schema_version`,
  `coverage_trusted`, and `coverage_validation_reason`

Route execution may only use a season/unit-size/minimum-minute slice when the
source schema matches the documented contract, lineup membership parses into the
expected `unit_size`, and coverage validation passes. Missing or untrusted
coverage must keep the current unsupported-data response instead of mixing
source-backed and placeholder behavior.

`LeagueDashLineups` may be evaluated later as a counting-stat or games-played
enrichment source, but it is not the approved minimum source for the current
route contract because `LeagueLineupViz` directly exposes the rating metrics and
minimum-minute filter needed by the lineup query surface.

## Current route boundary

- `parse_query()` and structured query execution keep routing lineup phrasing to
  `lineup_summary` or `lineup_leaderboard`.
- `lineup_summary.build_result()` and `lineup_leaderboard.build_result()` return
  trusted `league_lineup_viz` rows when coverage exists for the requested slice.
  Missing or untrusted coverage returns `NoResult(reason="unsupported")` with
  explicit lineup data notes.
- roster membership remains an identity/enrichment source only and must not be
  reused as a lineup-unit substitute.

## Implementation status

The source-backed implementation queue added the raw data contract, ingestion
path, validation, loader helpers, and coverage-gated route execution. Lineups
are now execution-backed for the approved source boundary. Any future
play-by-play, substitution, rotation, or stint-table expansion requires a new
source decision.
