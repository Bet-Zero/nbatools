# Phase I On/Off Source Boundary

> Role: Phase I source decision and deferral artifact for
> [`phase_i_work_queue.md`](./phase_i_work_queue.md).

## Decision

The future `player_on_off` source path is approved:
`nba_api.stats.endpoints.TeamPlayerOnOffSummary`, normalized from the upstream
`teamplayeronoffsummary` endpoint.

This is a source approval only. Real `player_on_off` execution remains
unshipped until a later implementation queue builds the ingestion, validation,
loader, and coverage-gated route execution path. The current placeholder route
must stay in place until that work lands.

The repo still does not contain an on/off execution dataset under `data/`, and
it still does not contain play-by-play, substitution, rotation, or local stint
tables. Because of that, current route behavior must not change in this source
decision item.

The approved upstream split table is a better fit for the current route
contract than whole-game absence because it already exposes one row per
team/player/court-status split with the queried player identity, `COURT_STATUS`,
games represented, minutes, plus-minus, and `OFF_RATING`, `DEF_RATING`, and
`NET_RATING`.

## Why whole-game absence is not on/off

The existing `without_player` execution path removes entire games where a player
appeared. That answers a different question: team/player performance in games
where a player did not play at all.

On/off asks for possession- or stint-level performance while a player is on the
floor versus off the floor within the relevant sample. Whole-game absence cannot
recover that boundary because a game log row has no substitution times, stint
membership, possession counts, or on-court lineup state.

## Approved source contract

The raw future dataset should be documented as
`data/raw/team_player_on_off_summary/{season}_{season_type_safe}.csv` before
implementation changes route behavior.

Minimum contract:

- source endpoint: `teamplayeronoffsummary`, called through
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary`
- source grain: team-season split rows for players on court and off court
- normalized grain: one row per `season`, `season_type`, `team_id`,
  queried `player_id`, and `presence_state`
- source row groups:
  - `PlayersOnCourtTeamPlayerOnOffSummary`
  - `PlayersOffCourtTeamPlayerOnOffSummary`
- keys: `season`, `season_type`, `team_id`, `player_id`, `presence_state`
- queried player identity: source `VS_PLAYER_ID` / `VS_PLAYER_NAME`, normalized
  to `player_id` / `player_name`
- split field: source `COURT_STATUS`, normalized to `presence_state` values
  `on` and `off`
- sample-size fields: `gp` and `minutes`; possessions are not exposed by the
  approved source and must remain unavailable unless a later implementation
  adds a separately approved possession source
- result metrics: `plus_minus`, `off_rating`, `def_rating`, `net_rating`
- trust fields: `source_endpoint`, `source_pull_date`, `source_schema_version`,
  `coverage_trusted`, and `coverage_validation_reason`

Route execution may only use a player/team/season slice when both on-court and
off-court rows are present, the source schema matches the documented contract,
and coverage validation passes. Missing or untrusted coverage must keep the
current unsupported-data response instead of mixing source-backed and placeholder
behavior.

`TeamPlayerOnOffDetails` may be evaluated later as a counting-stat enrichment
source, but it is not the approved minimum source for the route contract because
the current on/off route requires rating-style split metrics.

## Current route boundary

- `parse_query()` and structured query execution keep routing on/off phrasing to
  `player_on_off`.
- `player_on_off.build_result()` remains a placeholder and returns a
  `NoResult(reason="unsupported")` with an explicit on/off data note.
- `without_player` remains a whole-game absence filter and must not be reused as
  an on/off substitute.

## Immediate next action after source approval

The next implementation queue should reopen Phase I implementation work by:

1. adding the raw/processed data contract to `docs/reference/data_contracts.md`
2. building the ingestion or derivation path
3. adding validation and loader helpers
4. replacing `player_on_off` placeholder execution with coverage-gated results

Until then, on/off is source-approved but not execution-backed or product
complete.
