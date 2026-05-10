# Final Visual QA Punch List Findings

Date: 2026-05-10

## Summary

Status: complete for the listed final Result Display Lock-In punch list.

The two must-fix regressions are resolved:

- Fixture 57 now routes to `team_record` and answers the Knicks' record without Jalen Brunson, with an 8-row team game log attached.
- Fixture 228 now returns `playoff_history` successfully, with summary and 21 season rows.

The remaining polish work was kept to the locked result-display surface: product-facing note cleanup, context deduplication and label cleanup, unsupported-query copy, raw/detail toggle labels, streak hero/status polish, team-record table width reduction, review shape classification, and row-cap confirmation.

## Must-Fix Findings

### Fixture 57 - Knicks Without Brunson

Prior behavior:

- Query: `What is the Knicks' record when Jalen Brunson doesn't play?`
- The query routed through the player summary path and answered with Jalen Brunson's own averages.

New behavior:

- The parser now recognizes `doesn't play` and `does not play` as player-absence language.
- The route is `team_record`.
- The backend result carries `without_player: Jalen Brunson`.
- The result includes a team `game_log` section when matching absence-filtered rows exist.
- The frontend renders the Team Record hero and supporting game-log table instead of a player-average summary.

Evidence:

- Target fixture payload: `team_record`, `ok`, sections `summary: 1`, `by_season: 1`, `game_log: 8`.
- Summary evidence: New York Knicks, `3-5`, 8 games, `without_player=Jalen Brunson`.
- Renderer regression test verifies the hero does not contain `Jalen Brunson has averaged`.

### Fixture 228 - Lakers Playoff History

Prior behavior:

- Query: `Lakers playoff history`
- Review output regressed to unsupported/no-result with `No columns to parse from file`.

New behavior:

- The natural query returns `playoff_history`, `ok`.
- The result includes a historical team summary and season-by-season playoff history table.
- Caveats remain available for round-level data coverage limits.

Evidence:

- Target fixture payload: `playoff_history`, `ok`, sections `summary: 1`, `by_season: 21`.
- Summary evidence: Los Angeles Lakers, 21 postseason rows, 2 caveats.
- Backend regression coverage was added for the natural-query result contract.

## Polish Findings

### Internal Note Cleanup

Parser/debug notes are now filtered or rewritten before product display:

- `sample_advanced_metrics:` becomes `Advanced rate stats were recalculated using only this filtered sample.`
- `season_high:` becomes `Showing league-wide single-game scoring performances.`
- `default: player streak uses three-season window when no season specified` becomes `Because no season was specified, this search used the last three seasons.`
- `default: <metric> only...` and `leaderboard_source:...` are hidden from product-facing notes.

### Context Deduplication

Result envelope context now skips repeated date and season range applied filters when the same range is already displayed as first-class context.

Opponent-list caveats are promoted to a single `Included opponents` context item, avoiding duplicated raw `VS` and expanded-list context.

### Context Label Cleanup

The reviewed label changes are implemented:

- `Last N games: 10` -> `Window: Last 10 games`
- `VS: PLAYOFF TEAMS` -> `Opponent group: Playoff Teams`
- `Games vs 20 opponents (...)` -> `Included opponents: 20 teams (...)`
- opponent-points thresholds -> `Filter: Opp PTS <= 100`
- opponent-points metric -> `Metric: Opponent points`
- rolling scoring stretch metric -> `Metric: PPG`

### Unsupported-Query Copy

The hard unsupported cooled-off query now surfaces specific copy:

`I couldn't interpret "cooled off" as a supported stat query yet.`

It is treated as an unsupported query, not a generic processing error, and does not invent unsupported alternatives.

### Raw/Detail Toggle Labels

Remaining raw-table labels were cleaned where safe:

- top performers -> `Show top performer details`
- postseason summary -> `Show postseason summary`
- record detail -> `Show record details`
- matchup summary -> `Show matchup summary`
- generic supplemental detail remains `Show additional columns`

### Streak Table Polish

Fixture 201 now has enough metadata to preserve the requested minimum streak length in the hero.

The all-completed `Status` column is hidden. Status remains visible when rows are active or mixed.

### Team Record Table Width

Fixture 45 keeps the required core team-record columns and suppresses the lower-value season column when an opponent group is present. This reduces clipping risk without changing the core Team Record contract.

### Row Cap Confirmation

Product-mode game logs still cap at the first 12 rows with total-count expansion controls:

- Fixture 71 shape: 34 backend rows, `Show all 34 games`.
- Fixture 51 shape: 18 backend rows, `Show all 18 games`.

Review mode remains uncapped for visual QA.

## Fixture Review Notes

| Fixture ID | Query/family | Status | Notes |
|---:|---|---|---|
| 1 | Leaderboard Table | Passing | `season_leaders`, `ok`, 10 leaderboard rows. |
| 11 | Guided No Result | Passing | `season_leaders`, `no_result`, no rows. |
| 19 | Message No Result / cooled off | Passing | Unrouted hard unsupported copy is specific to `cooled off`. |
| 31 | Top Performances | Passing | `top_player_games`, `ok`, 10 leaderboard rows. |
| 36 | Rolling Stretch | Passing | `player_stretch_leaderboard`, `ok`, 10 leaderboard rows; metric context is PPG. |
| 44 | Entity Summary + Recent Games | Passing | `player_game_summary`, `ok`, summary/by-season/game-log stack. |
| 45 | Team Record | Passing | `team_record`, `ok`; table width reduced by hiding season when opponent group is present. |
| 51 | Game Summary Log | Passing | `game_summary`, `ok`, 18 game-log rows; product cap label confirmed. |
| 57 | Knicks without Brunson | Passing | `team_record`, `ok`, Knicks 3-5 without Brunson, 8 game-log rows. |
| 71 | Player Game Log | Passing | `player_game_finder`, `ok`, 34 finder rows; product cap label confirmed. |
| 76 | Team Game Log | Passing | `game_finder`, `ok`, 7 finder rows. |
| 201 | Streak Table | Passing | `player_streak_finder`, `ok`, 15 streak rows, `min_streak_length=5`. |
| 228 | Playoff History | Passing | `playoff_history`, `ok`, 21 season rows. |
| 229 | Playoff Matchup History | Passing | `playoff_matchup_history`, `ok`, summary and comparison rows. |
| 234 | Playoff Round Records | Passing | `playoff_round_record`, `ok`, 7 leaderboard rows. |
| 236 | Record By Decade | Passing | `record_by_decade`, `ok`, summary and by-season rows. |
| 237 | Record By Decade Leaderboard | Passing | `record_by_decade_leaderboard`, `ok`, 10 leaderboard rows. |
| 238 | Matchup By Decade | Passing | `matchup_by_decade`, `ok`, summary and comparison rows. |
| 239 | Comparison Panels | Passing | `player_compare`, `ok`, summary and comparison rows. |

## Validation

| Command/check | Result | Notes |
|---|---|---|
| `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer tests/test_playoff_history_queries.py::TestPlayoffHistoryResultContracts -n0` | Passed | 23 passed. |
| `npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts LayoutPrimitives.test.tsx UIComponents.test.tsx` | Passed | 7 files, 123 tests. |
| `npm run build` | Passed | Vite build succeeded; standard chunk-size warning only. |
| `env PATH=/Users/brenthibbitts/nba_tools/.venv/bin:$PATH make test-query` | Passed | 680 passed. |
| `env PATH=/Users/brenthibbitts/nba_tools/.venv/bin:$PATH make test-engine` | Passed | 728 passed, 1 xpassed. |
| Target fixture payload sweep | Passed | Fixtures 1, 11, 19, 31, 36, 44, 45, 51, 57, 71, 76, 201, 228, 229, 234, 236, 237, 238, and 239 checked. |
| `git diff --check` | Passed | No whitespace errors. |

## Remaining Risks

No unfinished punch-list scope remains. The only validation note is the existing Vite chunk-size warning, which did not block the production build.

## Verdict

All reviewed result-display families in this final punch-list pass the targeted final visual QA checks.
