# Source-Backed Execution Queue

> **Role:** Active master-plan continuation after
> [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md).
>
> This queue turns the approved source paths for the remaining core capability
> families into coverage-gated execution:
>
> - clutch: `PlayByPlayV3` plus local score-state derivation
> - on/off: `TeamPlayerOnOffSummary`
> - lineups: `LeagueLineupViz`
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the listed
> test commands. Check the item off, commit. Repeat. The final item must update
> [`master_completion_plan.md`](./master_completion_plan.md) to either name the
> next active continuation or state that the whole plan is done.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped, with an inline product decision explaining why

---

## Guardrails

- Do not replace placeholder or unfiltered fallback behavior until the backing
  source dataset is ingested, validated, loadable, and tested.
- Keep coverage gates explicit. Missing, incomplete, or untrusted source
  coverage must return the current honest placeholder or unfiltered note.
- Do not approximate possession-level or lineup-unit behavior from whole-game
  game logs, roster membership, period box scores, or season-level aggregates.
- Keep route implementations in command modules and shared helpers, not CLI
  wrappers or frontend code.
- Update current-state docs only after behavior is implemented and verified.

---

## 1. `[x]` Build the on/off source dataset path

**Why:** `player_on_off` has an approved upstream split source, but no local
dataset, validation, or loader exists yet.

**Scope:**

- Add a pipeline/backfill path for `TeamPlayerOnOffSummary`.
- Normalize source `PlayersOnCourtTeamPlayerOnOffSummary` and
  `PlayersOffCourtTeamPlayerOnOffSummary` rows into
  `data/raw/team_player_on_off_summary/{season}_{season_type_safe}.csv`.
- Implement schema and coverage validation for required fields, both
  `presence_state` values, and rating metrics.
- Add loader helpers that return trusted rows only and expose clear missing
  coverage reasons.
- Keep `player_on_off` route behavior unchanged in this item.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `docs/reference/data_contracts.md`
- `tests/`

**Acceptance criteria:**

- The on/off source dataset can be rebuilt for a requested season and season
  type.
- Validation rejects missing required columns, duplicate keys, missing on/off
  pairs, and untrusted coverage.
- Loader helpers expose trusted rows and explicit coverage failures.
- No `player_on_off` route returns real split results yet.

**Tests to run:**

- `make test-engine`
- `make test-impacted`

**Reference docs to consult:**

- [`phase_i_on_off_source_boundary.md`](./phase_i_on_off_source_boundary.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

**Completion note:** Added the `team_player_on_off_summary` source dataset path
for the approved `TeamPlayerOnOffSummary` source: normalization/backfill,
schema and coverage validation, loader helpers, raw CLI command, and focused
dataset tests. `player_on_off` route behavior is unchanged and still returns
the existing unsupported-data placeholder until item 2 wires coverage-gated
execution.

---

## 2. `[x]` Wire coverage-gated `player_on_off` execution

**Why:** After the on/off dataset exists, the placeholder route should return
real structured on/off rows only when trusted source coverage exists.

**Scope:**

- Replace `player_on_off` placeholder execution with source-backed execution.
- Support current parser slots: `lineup_members`, `presence_state`, `season`,
  `season_type`, and team context when supplied.
- Preserve explicit unsupported/no-result behavior for missing coverage,
  ambiguous teams, unsupported multi-player on/off, and slices outside the
  dataset contract.
- Update query catalog/current-state docs only for verified shipped behavior.

**Files likely touched:**

- `src/nbatools/commands/player_on_off.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/query_service.py`
- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `tests/`

**Acceptance criteria:**

- Supported on/off queries return structured on/off results instead of the
  placeholder response when trusted rows exist.
- Missing/untrusted coverage still returns an honest unsupported/no-result
  response.
- Whole-game `without_player` behavior is unchanged and remains separate.
- Docs describe only the verified supported on/off boundary.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-output`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

**Completion note:** Replaced the `player_on_off` placeholder with
coverage-gated execution over trusted `team_player_on_off_summary` rows for the
approved single-player source boundary. Missing files, untrusted coverage,
unsupported multi-player on/off, and slices outside the source contract keep
explicit unsupported/no-result responses. Updated current-state/query docs and
planning rollups to reflect the shipped on/off boundary.

---

## 3. `[x]` Build the lineup source dataset path

**Why:** `lineup_summary` and `lineup_leaderboard` have an approved upstream
lineup-unit source, but no local dataset, validation, or loader exists yet.

**Scope:**

- Add a pipeline/backfill path for `LeagueLineupViz`.
- Normalize source rows into
  `data/raw/league_lineup_viz/{season}_{season_type_safe}.csv`.
- Parse `GROUP_ID` / `GROUP_NAME` into stable membership fields.
- Preserve `unit_size`, `minute_minimum`, minutes, and rating metrics.
- Implement schema and coverage validation for required fields, membership
  count, and trusted source coverage.
- Add loader helpers that support specific lineup lookup and leaderboard
  retrieval.
- Keep lineup route behavior unchanged in this item.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `docs/reference/data_contracts.md`
- `tests/`

**Acceptance criteria:**

- The lineup source dataset can be rebuilt for requested seasons, season types,
  unit sizes, and minute thresholds.
- Validation rejects missing required columns, duplicate keys, membership-count
  mismatches, and untrusted coverage.
- Loader helpers expose trusted lineup rows and explicit coverage failures.
- `lineup_summary` and `lineup_leaderboard` remain placeholders until item 4.

**Tests to run:**

- `make test-engine`
- `make test-impacted`

**Reference docs to consult:**

- [`phase_j_lineup_source_boundary.md`](./phase_j_lineup_source_boundary.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

**Completion note:** Added the `league_lineup_viz` source dataset path for the
approved `LeagueLineupViz` source: normalization/backfill, raw CLI command,
schema and coverage validation, stricter loader checks, trusted-row selection
helpers for lineup lookup and leaderboard retrieval, and focused dataset tests.
`lineup_summary` and `lineup_leaderboard` route behavior is unchanged and still
returns the existing unsupported-data placeholder until item 4 wires
coverage-gated execution.

---

## 4. `[x]` Wire coverage-gated lineup execution

**Why:** After the lineup dataset exists, lineup routes should return real
structured results only when trusted source coverage exists.

**Scope:**

- Replace `lineup_summary` and `lineup_leaderboard` placeholder execution with
  source-backed execution.
- Support current parser slots: `lineup_members`, `unit_size`, and
  `minute_minimum`.
- Preserve explicit unsupported/no-result behavior for missing coverage,
  unsupported unit sizes, ambiguous members, and queries outside the dataset
  contract.
- Update query catalog/current-state docs only for verified shipped behavior.

**Files likely touched:**

- `src/nbatools/commands/lineup_summary.py`
- `src/nbatools/commands/lineup_leaderboard.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `tests/`

**Acceptance criteria:**

- Supported specific-lineup and lineup-leaderboard queries return structured
  lineup-unit results when trusted rows exist.
- Missing/untrusted coverage still returns honest unsupported/no-result
  responses.
- Roster membership is not used as lineup execution.
- Docs describe only the verified supported lineup boundary.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-output`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)
- [`docs/architecture/parser/examples.md`](../architecture/parser/examples.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

**Completion note:** Replaced the `lineup_summary` and `lineup_leaderboard`
placeholders with coverage-gated execution over trusted `league_lineup_viz`
rows for the approved lineup-unit source boundary. Missing files, untrusted
coverage, unsupported unit sizes, and unmatched slices keep explicit
unsupported/no-result responses. Updated current-state/query/parser docs and
the master-plan rollup to reflect the shipped lineup boundary.

---

## 5. `[x]` Build the play-by-play source path for clutch

**Why:** Clutch execution needs event-grain data and score-state validation
before any route can honestly filter to clutch windows.

**Scope:**

- Add a `PlayByPlayV3` ingestion/backfill path for normalized
  `play_by_play_events`.
- Validate source schema, game coverage, score-state parseability, and event
  ordering.
- Add loader helpers that expose trusted game event rows and explicit coverage
  failures.
- Keep clutch route behavior unchanged in this item.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `docs/reference/data_contracts.md`
- `tests/`

**Acceptance criteria:**

- Play-by-play events can be rebuilt for requested seasons and season types.
- Validation rejects missing required fields, duplicate event keys, unparseable
  clocks/scores, and incomplete game coverage.
- Loader helpers expose trusted event rows and explicit coverage failures.
- Existing clutch queries still keep the unfiltered-results note.

**Tests to run:**

- `make test-engine`
- `make test-impacted`

**Reference docs to consult:**

- [`clutch_source_boundary.md`](./clutch_source_boundary.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)
- [`phase_f_execution_gap_inventory.md`](./phase_f_execution_gap_inventory.md)

**Completion note:** Added the raw `play_by_play_events` source dataset path
for the approved `PlayByPlayV3` source: normalization/backfill, raw CLI
command, schema validation, score/clock parseability checks, event-order
validation, loader helpers for trusted rows and coverage failures, and focused
dataset tests. Existing clutch query behavior is unchanged and still keeps the
explicit unfiltered-results note until derived clutch aggregates and route
execution are implemented.

---

## 6. `[x]` Derive clutch player-game and team-game stats

**Why:** Routes should consume validated clutch aggregates, not raw event rows
directly.

**Scope:**

- Derive `player_game_clutch_stats` and `team_game_clutch_stats` from trusted
  play-by-play rows using the NBA clutch definition: last five minutes of the
  fourth quarter or overtime, score within five.
- Implement validation for clutch-window selection, sample size fields, and
  aggregate consistency.
- Add loader helpers for trusted player/team clutch rows.
- Keep clutch route behavior unchanged in this item.

**Files likely touched:**

- `src/nbatools/commands/pipeline/`
- `src/nbatools/commands/data_utils.py`
- `docs/reference/data_contracts.md`
- `tests/`

**Acceptance criteria:**

- Derived clutch datasets can be rebuilt from trusted play-by-play events.
- Validation covers clock/period boundaries, score-margin boundaries, duplicate
  keys, and missing trusted coverage.
- Loader helpers expose trusted player/team rows and explicit coverage failures.
- Existing clutch queries still keep the unfiltered-results note.

**Tests to run:**

- `make test-engine`
- `make test-impacted`

**Reference docs to consult:**

- [`clutch_source_boundary.md`](./clutch_source_boundary.md)
- [`docs/reference/data_contracts.md`](../reference/data_contracts.md)

**Completion note:** Added the processed `player_game_clutch_stats` and
`team_game_clutch_stats` derivation path from trusted `play_by_play_events`:
clutch-window filtering, event-derived point aggregation, schema validation,
loader helpers for trusted clutch rows and coverage failures, a processing CLI
command, and focused dataset tests. Existing clutch route behavior is unchanged
and still keeps the explicit unfiltered-results note until item 7 wires
coverage-gated route execution.

---

## 7. `[x]` Wire coverage-gated clutch execution

**Why:** After clutch aggregates exist, transported clutch routes should stop
returning unfiltered results only where trusted clutch coverage exists.

**Scope:**

- Wire clutch filtering into the supported initial route boundary:
  `player_game_summary`, `player_game_finder`, `team_record`, and
  `season_leaders`.
- Preserve explicit unfiltered-results notes for unsupported routes and
  missing/untrusted coverage.
- Update query catalog/current-state docs only for verified shipped behavior.

**Files likely touched:**

- `src/nbatools/commands/player_game_summary.py`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/season_leaders.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `docs/reference/query_catalog.md`
- `docs/reference/current_state_guide.md`
- `tests/`

**Acceptance criteria:**

- Supported clutch queries return filtered structured results when trusted
  clutch rows exist.
- Missing/untrusted coverage and unsupported routes keep honest fallback notes.
- Whole-game logs, period-only box scores, and season-level clutch aggregates
  are not used as clutch substitutes.
- Docs describe only the verified supported clutch boundary.

**Tests to run:**

- `make test-query`
- `make test-engine`
- `make test-output`
- `make test-phase-smoke`
- `make test-smoke-queries`

**Reference docs to consult:**

- [`clutch_source_boundary.md`](./clutch_source_boundary.md)
- [`docs/architecture/parser/specification.md`](../architecture/parser/specification.md)
- [`docs/reference/query_catalog.md`](../reference/query_catalog.md)

**Completion note:** Wired the supported clutch route boundary to trusted
derived clutch rows: `player_game_summary`, `player_game_finder`,
`team_record`, and `season_leaders` now consume `player_game_clutch_stats` /
`team_game_clutch_stats` when coverage exists. Missing or untrusted clutch
coverage keeps the explicit unfiltered-results note, and unsupported routes
still do not fabricate clutch filtering from whole-game or period-only data.
Updated current-state/query/parser docs and the master-plan rollup to reflect
the shipped clutch boundary.

---

## 8. `[ ]` Close the master-plan implementation blockers

**Why:** Once clutch, on/off, and lineups are execution-backed or explicitly
out of scope by documented product decision, the master plan needs a single
truthful completion answer.

**Scope:**

- Audit `master_completion_plan.md`, parser docs, query catalog, current-state
  guide, and data contracts for the final supported boundaries.
- If every required core capability family is product/capability complete or
  explicitly out of scope, update the master plan to say the whole plan is done.
- If meaningful core capability work remains, update the master plan to name
  exactly one next active continuation.
- Update `docs/index.md` for any new continuation or closure state.

**Acceptance criteria:**

- The master plan names exactly one active continuation or states that the whole
  plan is done.
- No core family remains in an open-ended deferral state.
- Current-state docs do not overstate unsupported behavior.

**Tests to run:**

- None for docs-only closure.
- If smoke inventory changes, run `make test-phase-smoke` and
  `make test-smoke-queries`.

**Reference docs to consult:**

- [`master_completion_plan.md`](./master_completion_plan.md)
- [`source_approval_route_expansion_queue.md`](./source_approval_route_expansion_queue.md)
- [`parser_execution_completion_plan.md`](./parser_execution_completion_plan.md)
