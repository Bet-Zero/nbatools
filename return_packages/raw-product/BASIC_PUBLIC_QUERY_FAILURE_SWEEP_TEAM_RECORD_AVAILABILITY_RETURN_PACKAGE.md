# Basic Public Query Failure Sweep: Team Record Availability Return Package

## Summary

Implemented the narrow team-record player-availability fix documented in
`docs/planning/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_PREFLIGHT.md`.

Production behavior changed only for team-record availability variants:

- single-player whole-game presence now routes to `team_record`
- compound with/without availability returns explicit unsupported/no-result
- unresolved availability player names return explicit no-result instead of a
  broad team record

Frontend rendering, feedback systems, release status, and unrelated QA
expectations were not changed.

## Root Cause

The parser resolved `with Luka` / `with Reaves` as the primary player entity
before the team-record route could claim the query. That made team-record
presence questions route to `player_game_summary`, producing plausible player
summary answers instead of Lakers team-record answers.

Mixed availability like `with Reaves without Luka` was not covered by the
existing multi-player availability boundary, so it also escaped to a player
summary. Partial unresolved absence names like `without Luk` were silently
dropped, allowing the broad Lakers full-season `team_record` route to execute.

## Behavior Before / After

| Query | Before | After |
|---|---|---|
| `Luka stats this season` | `player_game_summary` / `ok` | Preserved: `player_game_summary` / `ok` |
| `Lakers record without Luka` | `team_record` / `ok`; absence filter; game log | Preserved: `team_record` / `ok`; `without_player=Luka Dončić`; game log |
| `Lakers record with Luka` | `player_game_summary` / `ok`; Luka subject | Fixed: `team_record` / `ok`; `with_player=Luka Dončić`; Lakers subject; game log |
| `Lakers record with Reaves` | `player_game_summary` / `ok`; Reaves subject | Fixed: `team_record` / `ok`; `with_player=Austin Reaves`; Lakers subject; game log |
| `Lakers record with Reaves without Luka` | `player_game_summary` / `ok`; plausible wrong-scope answer | Fixed: `team_record` / `no_result` / `filter_not_supported`; `unsupported_filters=["multi_player_availability"]`; empty sections |
| `Lakers record without Luk` | `team_record` / `ok`; broad 82-game Lakers record | Fixed: `team_record` / `no_result` / `filter_not_supported`; `unsupported_filters=["unresolved_player_availability"]`; empty sections |
| `Who had the most rebounds in a game this year?` | `top_player_games` / `ok` | Preserved: `top_player_games` / `ok` |

## Files Changed

- `src/nbatools/commands/_matchup_utils.py`
  - Added whole-game `with_player` detection.
  - Added unresolved availability-fragment detection.
  - Guarded negative play phrases so `doesn't play` remains absence, not
    presence.
- `src/nbatools/commands/data_utils.py`
  - Added `filter_with_player()` using player game appearances and team game
    IDs.
- `src/nbatools/commands/team_record.py`
  - Added `with_player` execution for single-team records.
  - Added game-log output and caveat for presence-filtered team records.
  - Rejected simultaneous `with_player` and `without_player` at execution
    level as unsupported.
- `src/nbatools/commands/natural_query.py`
  - Added `with_player`, unresolved availability fields, and team-record
    presence routing before player-summary routing.
  - Extended multi-player availability guard to mixed `with` + `without`
    phrasing.
  - Added unresolved availability guard with no broad fallback.
- `src/nbatools/commands/_natural_query_execution.py`
  - Added no-result note for unresolved availability players.
- `src/nbatools/query_service.py`
  - Added `with_player` and `unresolved_availability_player` metadata.
  - Added `With player` applied-filter display metadata.
- `tests/test_ui_failure_coverage.py`
  - Added parser and data-backed execution coverage for presence, mixed
    availability, unresolved typo, and preserved absence behavior.
- `tests/test_natural_query_unsupported_boundary_snapshots.py`
  - Added no-broad-fallback snapshots for mixed availability and unresolved
    availability.
- `qa/raw_query_answer_corpus.yaml`
  - Added exact public-sweep cases for all seven user-discovered queries.
- `qa/harness_slices/basic_public_availability.yaml`
  - Added a focused raw QA slice for this sweep.
- `qa/harness_slices/natural_query_route_priority.yaml`
  - Added the new route-priority public-sweep cases.
- `qa/harness_slices/product_boundaries.yaml`
  - Added compound and unresolved availability boundary cases.
- `docs/reference/query_catalog.md`
  - Documented validated single-player whole-game presence team records and
    the compound availability boundary.
- `docs/reference/query_guide.md`
  - Added player-availability team-record examples.
- `docs/planning/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_PREFLIGHT.md`
  - Marked execution complete and pointed to this return package.

## Tests / Corpus / Slices Added

Raw QA case IDs:

- `luka_stats_this_season_public_sweep`
- `lakers_record_without_luka_public_sweep`
- `lakers_record_with_luka_public_sweep`
- `lakers_record_with_reaves_public_sweep`
- `lakers_record_with_reaves_without_luka_public_sweep`
- `lakers_record_without_luk_public_sweep`
- `most_rebounds_single_game_this_year_public_sweep`

Harness slice added:

- `qa/harness_slices/basic_public_availability.yaml`

Existing harness slices updated:

- `natural_query_route_priority`
- `product_boundaries`

## Validation Results

Passed:

```bash
.venv/bin/python -m py_compile src/nbatools/commands/natural_query.py src/nbatools/commands/_matchup_utils.py src/nbatools/commands/data_utils.py src/nbatools/commands/team_record.py src/nbatools/query_service.py src/nbatools/commands/_natural_query_execution.py
```

Passed:

```bash
.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer -n0
```

Result: 45 passed.

Passed:

```bash
.venv/bin/pytest tests/test_natural_query_unsupported_boundary_snapshots.py -n0
```

Result: 26 passed.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result: 776 passed.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result: 786 passed.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Latest result: `outputs/raw_query_answer_qa/20260523T133611Z`; 7 cases,
expectation cases `pass: 7`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice product_boundaries --fail-on-expectation-failure
```

Latest result: `outputs/raw_query_answer_qa/20260523T133611Z`; 20 cases,
expectation cases `pass: 20`, failed case IDs none.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-preflight
```

Result: 3001 passed, 1 xpassed.

Passed:

```bash
git diff --check
```

Direct `--no-index` whitespace checks were also run against the two new
untracked files:

```bash
git diff --check --no-index -- /dev/null qa/harness_slices/basic_public_availability.yaml
git diff --check --no-index -- /dev/null return_packages/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_RETURN_PACKAGE.md
```

Both produced no whitespace diagnostics. The nonzero exit code is expected for
`--no-index` comparisons between `/dev/null` and a new file.

## Preservation Proof

Preserved working cases:

- `Luka stats this season`
  - raw QA: `luka_stats_this_season_public_sweep`
  - expected `player_game_summary` / `ok`
- `Lakers record without Luka`
  - raw QA: `lakers_record_without_luka_public_sweep`
  - expected `team_record` / `ok`, `Without player = Luka Dončić`, game log
- `Who had the most rebounds in a game this year?`
  - raw QA: `most_rebounds_single_game_this_year_public_sweep`
  - expected `top_player_games` / `ok`, `stat=reb`
- Existing without-player cases remained covered through
  `tests/test_ui_failure_coverage.py::TestWithoutPlayer`, `make test-query`,
  and `make test-preflight`.
- Existing multi-player unsupported cases remained covered through
  `tests/test_natural_query_unsupported_boundary_snapshots.py`,
  `product_boundaries`, and `make test-preflight`.

## No Broad Fallback Proof

- `Lakers record with Reaves without Luka`
  - returns `team_record` / `no_result` / `filter_not_supported`
  - `metadata.unsupported_filters=["multi_player_availability"]`
  - `sections={}`
  - raw QA case:
    `lakers_record_with_reaves_without_luka_public_sweep`
- `Lakers record without Luk`
  - returns `team_record` / `no_result` / `filter_not_supported`
  - `metadata.unsupported_filters=["unresolved_player_availability"]`
  - `metadata.unresolved_availability_player="luk"`
  - `sections={}`
  - raw QA case: `lakers_record_without_luk_public_sweep`

## Release Impact

Release status was not changed. This is a narrow public-query correctness fix
with docs and QA coverage. It improves current public behavior by removing
plausible wrong-scope answers for common Lakers availability phrasing.

## Next Recommended Action

Keep compound multi-player availability unsupported until there is a dedicated
product contract for multiple presence/absence filters. If that becomes a
product goal, start with a preflight defining exact semantics, metadata, result
shape, and data trust rules before adding support.
