# New Shapes Apply Report

Scope: frontend result shape work for Pattern 5 (Top Performances) and Pattern 10 (Rolling Stretch).

## Files Created

- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.module.css`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.module.css`
- `frontend/src/test/routeToPattern.test.ts`

## Files Modified

- `frontend/src/api/types.ts`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/resultShapes.ts`
- `frontend/src/test/ResultRenderer.test.tsx`
- `frontend/src/test/resultShapes.test.ts`

## Headline Templates

Top Performances:

- Player and team routes use: `The top {metric_phrase} {scope_phrase}: {leader_name} with {value}.`
- `pts` renders as `scoring games` with `points`.
- Triple-double intent renders as `triple-double games` with `PTS-REB-AST` when rows include `pts`, `reb`, and `ast`.
- Scope uses query wording such as `this season` when present, otherwise season metadata such as `in the 2025-26 regular season`.

Rolling Stretch:

- League-wide route uses: `Best {window_size}-game {metric_phrase} {scope_phrase}: {top_player} averaged {value} from {start} to {end}.`
- Named-player route uses: `{Player}'s best {window_size}-game {metric_phrase} {scope_phrase}: {value} from {start} to {end}.`
- Named-player detection uses resolved `metadata.player_context`.

## Routing Changes

- `top_player_games` now maps to `top_performances` with `subject: "player"`.
- `top_team_games` now maps to `top_performances` with `subject: "team"`.
- `player_stretch_leaderboard` now maps to `rolling_stretch`.
- Result shape classification now exposes `Top Performances` and `Rolling Stretch` as review-page groups.

## Test Coverage

Added or updated tests for:

- Top Performances player variant.
- Top Performances team variant.
- Top Performances triple-double composite metric variant.
- Rolling Stretch league-wide variant.
- Rolling Stretch named-player variant with optional game-log section.
- Route mapping for all three affected routes.
- Result shape classification for the two new shape groups.

Verification commands:

- `npm run build` passed.
- `npm test` passed: 17 files / 235 tests.
- `make test` initially failed because `pytest` was not on PATH.
- `make test PYTEST=.venv/bin/pytest` passed: 2639 passed / 1 xpassed.

## Decisions

- The new shapes do not sort or slice rows in the frontend. Backend order and caps remain authoritative.
- The `Showing top N of total` note renders only when total-count metadata is present and greater than the returned row count.
- Rolling Stretch renders a game-log section only when one of `best_window_game_log`, `window_game_log`, or `game_log` is present. Current live responses for the checked named-player query did not include game-level stretch rows, so the windows table is the live body.
- The current live triple-double top-games route returns broad top scoring rows with an unsupported-boundary note and no `reb`/`ast` payload. The component supports a composite triple-double display when execution-backed rows include the three stats, but it does not fabricate a triple-double value from incomplete live data.

## Review Checks

Local API/Vite servers were started and representative queries were executed against the local API used by the UI:

- `highest scoring games this season` -> `top_player_games` -> Top Performances, player variant, 10 rows.
- `biggest triple-double games this season` -> `top_player_games` -> Top Performances, player variant, 10 rows.
- `best 3-game scoring stretch this year` -> `player_stretch_leaderboard` -> Rolling Stretch, league-wide variant, 10 rows.
- `Booker hottest 4-game scoring stretch` -> `player_stretch_leaderboard` -> Rolling Stretch, named-player variant, 10 rows.

`/review` was opened against the local Vite/API servers, and API logs confirmed the review fixture request set was exercised. `/api/dev/fixtures` returned 402 fixtures, including top-games and rolling-stretch examples. Browser screenshot automation was limited in this environment: Playwright screenshot capture hit `ENOSPC`, Firefox immediate screenshots captured the loading state before async query completion, and Safari DOM extraction is blocked because "Allow JavaScript from Apple Events" is disabled. Render-level visual distinctions are therefore verified by component tests and route/shape classification:

- Top Performances renders `aria-label="Top performances result"` and table `aria-label="Top performances"`, not the Game Log table.
- Rolling Stretch renders `aria-label="Rolling stretch result"` and rolling-window tables, not the generic Leaderboard table.
