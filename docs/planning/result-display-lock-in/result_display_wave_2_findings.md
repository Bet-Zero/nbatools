# Result Display Lock-In Wave 2 Findings

## Summary

Wave 2 locked the core leaderboard-style result displays:

- Family 17 — Leaderboard Table
- Family 18 — Top Performances
- Family 19 — Rolling Stretch
- Family 15 — Record By Decade Leaderboard
- Family 10 — Playoff Round Records

The work stayed focused on leaderboard-like components plus the narrow backend metadata needed to safely support rolling-stretch player deduplication. Game logs, entity summaries, comparison panels, Team Record, Matchup By Decade, Playoff Matchup History, and no-result behavior were not redesigned.

## Implemented

### Generic Leaderboard Table

- `LeaderboardResult` now uses direct player leaderboard copy such as `Luka Doncic led the NBA with 33.5 PPG in the 2025-26 regular season.`
- Existing team leaderboard copy remains specialized for record, wins, and losses.
- Queried metric highlighting remains driven by the selected metric column.

### Top Performances

- Top-performance heroes now include the player/team, metric value, opponent, date, and result context when available.
- Score renders in a separate `Score` column when the payload already contains team/opponent score fields.
- Supporting columns now adapt by queried metric:
  - scoring: `REB`, `AST`, `3PM`
  - rebounds: `PTS`, `AST`
  - assists: `PTS`, `REB`, `TOV`
  - 3PM: `PTS`, `3PA`

### Rolling Stretch

- The backend parser now exposes a safe stretch display mode:
  - named player queries -> `named_player`
  - explicit `which players` queries -> `players`
  - stretch/window leaderboard queries -> `windows`
- `player_stretch_leaderboard.build_result()` accepts `dedupe_players`; when true, it keeps only each player's best sorted window before applying the output limit.
- The frontend only dedupes when metadata says `stretch_display_mode: "players"`; otherwise it preserves all windows.
- Rolling stretch tables now include the required `Season` column in both league and named-player modes.

### Record By Decade Leaderboard

- `winningest` now maps to `Wins`, not `Win %`.
- The dense table keeps `#`, `Team`, `Decade`, queried metric, `W-L`, `Games`, `Win %`, `Seasons`, and `Type`.
- Backend interpretation strings such as `record by decade leaderboard (wins)` now render as Context instead of Caveats.

### Playoff Round Records

- Playoff round record heroes now use direct ranking copy, including round, record, win percentage mark, range, and games.
- Highlight selection is query-aware:
  - best record -> `Win Pct`
  - most wins -> `Wins`
  - most games -> `Games`
- Round-record tables now keep the required order: `#`, `Team`, `Round`, `Record`, `Games`, `Win Pct`, with optional `Wins`, `Seasons`, and `Series` when available.
- Real data limitations, such as unavailable pre-2001-02 round data, remain Caveats.

## Rolling-Stretch Dedupe Limitation

Deduplication is intentionally conservative. It only applies when natural query parsing can safely classify `which players` intent, or when a structured caller explicitly passes `dedupe_players=True`. Ambiguous stretch queries continue to show best windows, preserving valid repeated windows for the same player.

## Fixture Review

Checked through `/review` with a targeted fixture subset selected from the real `/api/dev/fixtures` list:

- Fixture 1: `Who leads the NBA in points per game this season?`
- Fixture 31: `What were the biggest scoring games this season?`
- Fixture 36: `Which players have the hottest 3-game scoring stretch this year?`
- Fixture 234: `best finals record since 1980`
- Fixture 237: `winningest team of the 2010s`

The rendered notes confirmed the intended Wave 2 display behavior:

- Fixture 1 hero: `Luka Doncic led the NBA with 33.5 PPG in the 2025-26 regular season.`
- Fixture 31 hero: `Bam Adebayo had the top scoring game this season with 83 points in a win against Washington Wizards on Mar 10.`
- Fixture 36 hero: `Luka Doncic had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.`
- Fixture 234 hero: `The Indiana Pacers have the best Finals record since 1980, going 10-5 (.667) across 15 games.`
- Fixture 237 hero: `The San Antonio Spurs won the most games in the 2010s, with 541 wins.`

## Validation

Passed:

- `npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts`
- `npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts LayoutPrimitives.test.tsx`
- `npm run build`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-parser`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" .venv/bin/pytest tests/test_player_stretch_leaderboard.py -n0`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-engine`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-query`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-api`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-preflight`

Environment note:

- Plain `make test-parser` failed because `pytest` was not on PATH in this shell. Rerunning the same Makefile target with `.venv/bin` prepended passed.

## Recommended Next Wave

Proceed to Wave 3 as planned: game logs and entity summaries. No Wave 2 blocking follow-up remains.
