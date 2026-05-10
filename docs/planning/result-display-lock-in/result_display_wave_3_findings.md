# Result Display Lock-In Wave 3 Findings

## Summary

Wave 3 locked the game-log and entity-summary display families:

- Family 1 — Entity Summary
- Family 4 — Entity Summary + Recent Games
- Family 5 — Player Game Log
- Family 6 — Team Game Log
- Family 7 — Game Summary Log

The implementation preserved Wave 1 context/caveat and duplicate-detail behavior, and did not rebuild Comparison Panels, Team Record, Record By Decade, Matchup By Decade, Playoff History, or no-result behavior.

## Implemented

### Entity Summary

- Player summary heroes now build context from existing metadata and `applied_filters`.
- Opponent-quality, opponent, location, outcome, without-player, threshold, schedule/situation, role/position/period, date, and season context are preserved when the payload exposes them.
- Filtered player summaries with a populated `game_log` now compose the entity-summary hero with the matching game-log answer table.
- Broad single-season summaries without meaningful filters remain summary-only.

### Entity Summary + Recent Games

- Last-N player summaries keep the hero plus dense game-log table shape.
- Product UI caps only when rows exceed 12; review mode passes a display-mode prop so review rendering can show all rows.
- Existing Average/Total footers remain on summary-backed recent-game tables.

### Player Game Log

- Player game-log tables now prefer the locked dense column set: `#`, `Date`, `TM`, `Opp`, `W/L`, `MIN`, `PTS`, `REB`, `AST`, `FG`, `3P`, `FT`, `STL`, `BLK`, `TOV`, `+/-`, with optional `Score`, home/away marker, `TS%`, and `eFG%` when present.
- Backend player finder and summary game-log outputs now pass through FG/FT made-attempt fields and available percentage fields so the frontend can render useful shooting columns.
- Triple-double game logs highlight `PTS`, `REB`, and `AST`.

### Team Game Log

- Team game-log tables now prefer the locked team-first column set: `#`, `Date`, `Team`, `Opp`, `Score`, `W/L`, `PTS`, `Opp PTS`, `Margin`, `REB`, `AST`, `3PM`, `FG`, `3P`, `FT`, `TOV`, with optional `STL`, `BLK`, `ORB`, and `DRB`.
- `Opp PTS` and `Margin` are rendered from explicit fields when present and derived safely from score/margin fields when needed.
- Queried metric highlighting now supports multiple columns and safely highlights condition columns such as `Opp PTS` for opponents-under-threshold queries.

### Game Summary Log

- Game-summary strips now include `Record` and use `PPG`, `RPG`, and `APG` labels.
- Filtered game summaries keep the team game-log answer table when `game_log` rows exist.
- Summary-backed game logs keep Average/Total footer behavior.

### Row Cap

- `ResultTable` now supports reusable product row caps.
- Default game-log behavior is: 0-12 rows show all; 13+ rows show the first 12 with `Show all {N} games`, then allow collapse back to `Show first 12 games`.
- `ResultRenderer` accepts `displayMode="review"` and `ReviewPage` passes it for visible and capture render paths, so review pages can show full row sets.

## Validation

Passed:

- `npm test -- ResultRenderer.test.tsx routeToPattern.test.ts resultShapes.test.ts ReviewPage.test.tsx reviewScreenshots.test.ts LayoutPrimitives.test.tsx`
- `npm run build`
- `PATH="/Users/brenthibbitts/nba_tools/.venv/bin:$PATH" make test-engine`

Fixture/API checks:

- Fixture 44 returned `player_game_summary` with 11 `game_log` rows and opponent-quality metadata.
- Fixture 247 returned `player_game_summary` with exactly 5 `game_log` rows.
- Fixture 71 returned `player_game_finder` with 34 matching triple-double rows and a count phrase.
- Fixture 76 returned `game_finder` with 7 matching rows, `Opp PTS`, and a 7-0 count phrase.
- Fixture 51 returned `game_summary` with an 8-10 record, 18 `game_log` rows, and top-performer detail rows.

Visual note:

- Local browser visual automation was attempted. Headless Firefox could capture the app shell but captured before the async query settled; Safari DOM extraction was blocked by Safari's "Allow JavaScript from Apple Events" setting. The fixture review therefore used local query/API payload checks plus targeted renderer tests rather than completed screenshot artifacts.

## Remaining Risk

- Entity-summary hero context still depends on metadata already present in the response. If a backend route omits a meaningful filter from metadata and rows, the frontend does not invent it.
- Shooting columns render made-attempt values when the backend passes made/attempt fields. If a source only exposes percentages, the column falls back to a percentage display.
- Product row caps apply to game logs only through `GameLogResult`; other long tables can opt in later if a later wave requires it.

## Recommended Next Wave

Proceed to Wave 4 as planned. Wave 3 does not need a blocking follow-up, but later waves should preserve the `ResultTable` row-cap/display-mode and multi-highlight APIs when touching shared result patterns.
