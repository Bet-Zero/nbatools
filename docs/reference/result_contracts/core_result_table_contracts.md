# Core Result/Table Contracts

This reference locks the current Wave 1 route -> result shape -> table pattern
contracts used by the React result renderer. It documents current behavior only:
no visual redesign, no route-registry redesign, and no new query capability.

Source files:

- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/resultShapes.ts`
- `frontend/src/components/results/patterns/*Result.tsx`
- `src/nbatools/commands/structured_results.py`

## Shared Table Behavior

| Pattern family | Current visible-column behavior | Hidden/detail behavior | Row cap | Footer/total behavior | Highlight behavior |
|---|---|---|---|---|---|
| Entity Summary | Hero sentence from `summary[0]`; optional `by_season` table for multi-period scopes with `Season`, `GP`, optional `W-L`, and available average/rate columns. | No raw detail drawer. | Hero row is single-row; by-season has no frontend cap. | None. | None. |
| Player Game Log | `#`, optional `Player`, `Date`, `TM`, location marker, `Opp`, optional `Score`, optional `W/L`, then available `MIN`, `PTS`, `REB`, `AST`, `FG`, `3P`, `FT`, `STL`, `BLK`, `TOV`, `+/-`, `TS%`, `eFG%`. | Finder routes show a raw-detail toggle when rows contain additional fields. Player summary game logs do not set a raw-detail title. | Product mode initially shows 12 rows with a "Show all" toggle; review mode has no cap. Backend finder routes may also limit rows. | If a `summary` row is supplied to `GameLogResult`, `Average` and `Total` footer rows render for supported stat columns. | Metric columns from route metadata/stat filters are highlighted when present. |
| Team Game Log | `#`, `Date`, `Team`, location marker, `Opp`, optional `Score`, optional `W/L`, then available `PTS`, `Opp PTS`, `Margin`, `REB`, `AST`, `3PM`, `FG`, `3P`, `FT`, `TOV`, `STL`, `BLK`, `ORB`, `DRB`. | Finder, game summary, and stacked team-record game logs can show raw/detail toggles when configured and additional fields exist. | Product mode initially shows 12 rows with a "Show all" toggle; review mode has no cap. Backend finder routes may also limit rows. | If a `summary` row is supplied, `Average` and `Total` footer rows render for supported stat columns. | Metric columns from route metadata/stat filters are highlighted when present. |
| Team Record | Summary table: `Team`, `W-L`, available `Games`, `Win %`, `PPG`, `+/-`, `REB`, `AST`, `3PM`, context columns (`Season Type`, `Opponent Group`, `Season`, `Home/Away`, `Opponent`), then available optional stats (`Opp PPG`, `Net`, `STL`, `BLK`, `TOV`, `eFG%`, `TS%`). Optional by-season table adds `Season`, `Games`, `W-L`, and available season stats. | Raw-detail toggles appear when summary or by-season rows include additional fields beyond displayed columns. | No frontend cap for record tables. Optional stacked game log uses the game-log 12-row product cap. | None. | Summary record column is highlighted; by-season highlights `win_pct`. |
| Leaderboard | `#`, entity label (`Player`, `Team`, or `Name`), primary metric, then dynamically selected supporting columns from row keys. Current behavior -- needs product decision: supporting columns are inferred, not route-declared. | No raw detail drawer. | No frontend cap. Backend limit is route-specific, usually 10. | None. | Primary metric column is highlighted. |
| Top Performances | `Rank`, `Player` or `Team`, `Date`, `Opp`, `Result`, optional `Score`, primary metric, then supporting stats. For points, supporting stats prefer `REB`, `AST`, `3PM` when present. | No raw detail drawer. | No frontend cap. Backend limit is route-specific, usually 10. | Optional note: "Showing top N of total" when result metadata exposes a larger total. | Primary metric column is highlighted. |
| Rolling Stretch | League/named-window table: `Rank`, `Player`, `Window`, primary stretch metric, `Start`, `End`, `Season`, plus up to two supporting window columns. Named-player payloads can also render `Best Window Games` with `Date`, `Opp`, `Result`, and available game stats. | No raw detail drawer. Named-player mode can show a second game-log table from `best_window_game_log`, `window_game_log`, or `game_log`. | No frontend cap. Backend limit is route-specific, usually 10. | Optional note: "Showing top N of total" when result metadata exposes a larger total. | `stretch_value` is highlighted; named-player best-window game log highlights the requested metric when present. |

## Wave 1 Route Contracts

| Route | PatternConfig | Result shape | Required sections | Optional sections | Table family / mode | Expected row type | Examples |
|---|---|---|---|---|---|---|---|
| `player_game_summary` | Default: `{ type: "entity_summary", sectionKey: "summary" }`. With qualifying game rows: add `{ type: "game_log", sectionKey: "game_log", summaryKey: "summary", showSummaryStrip: false }`. | `entity_summary` or `entity_summary_with_gamelog`. | `summary` | `by_season`, `game_log` | Entity Summary; optional Player Game Log. | `summary`: one player aggregate row. `game_log`: player game row. | "Curry this season"; "Jokic last 10 games"; "Tatum against good teams" |
| `player_game_finder` | `{ type: "game_log", sectionKey: "finder", mode: "player", rawDetailTitle: "Player Game Detail" }` | `game_log_player_table` | `finder` | None currently. | Player Game Log. | Player game row matching threshold/filter. | "Curry 5+ threes"; "Jokic 20+ rebounds" |
| `game_finder` | `{ type: "game_log", sectionKey: "finder", mode: "team", rawDetailTitle: "Game Detail" }` | `game_log_team_table` | `finder` | None currently. | Team Game Log. | Team game row matching threshold/filter. | "Lakers 120+ points"; "Celtics allowed under 100" |
| `game_summary` | `{ type: "game_log", sectionKey: "game_log", summaryKey: "summary", mode: "team", rawDetailTitle: "Game Detail", detailSectionKeys: ["top_performers"] }` | `game_log_team_detail` | `game_log` | `summary`, `by_season`, `top_performers` | Game Summary Log, team mode. | `game_log`: team game row. `top_performers`: player performance detail row. | "Celtics last 5 games"; "Lakers this season" |
| `team_record` | Default: `{ type: "record", mode: "team_record" }`. With `game_log` rows: add `{ type: "game_log", sectionKey: "game_log", summaryKey: "summary", mode: "team", showSummaryStrip: false, rawDetailTitle: "Game Detail" }`. | `team_record` | `summary` | `by_season`, `game_log` | Team Record; optional stacked Team Game Log. | `summary`: one team record aggregate row. `game_log`: team game row, currently produced for without-player filters and similar supported record contexts. | "Sixers record vs .500 teams"; "Knicks record without Brunson" |
| `season_leaders` | `{ type: "leaderboard", sectionKey: "leaderboard" }` | `leaderboard_table` | `leaderboard` | None currently. | Leaderboard. | Ranked player season aggregate row. | "Top scorers this season"; "Most rebounds in 2025 playoffs" |
| `season_team_leaders` | `{ type: "leaderboard", sectionKey: "leaderboard" }` | `leaderboard_table` | `leaderboard` | None currently. | Leaderboard. | Ranked team season aggregate row. | "Team assists leaders"; "Most wins by a team" |
| `top_player_games` | `{ type: "top_performances", sectionKey: "leaderboard", subject: "player" }` | `top_performances` | `leaderboard` | None currently. | Top Performances, player subject. | Ranked single-player game row. | "Highest scoring games this season"; "Most threes in a game" |
| `top_team_games` | `{ type: "top_performances", sectionKey: "leaderboard", subject: "team" }` | `top_performances` | `leaderboard` | None currently. | Top Performances, team subject. | Ranked single-team game row. | "Highest team scoring games"; "Most team points this season" |
| `player_occurrence_leaders` | `{ type: "leaderboard", sectionKey: "leaderboard" }` | `leaderboard_table` | `leaderboard` | None currently. | Leaderboard. | Ranked player occurrence-count row. | "Most 40-point games"; "Players with the most 10-assist games" |
| `team_occurrence_leaders` | `{ type: "leaderboard", sectionKey: "leaderboard" }` | `leaderboard_table` | `leaderboard` | None currently. | Leaderboard. | Ranked team occurrence-count row. | "Teams with the most 120-point games"; "Most games allowing under 100" |
| `player_stretch_leaderboard` | `{ type: "rolling_stretch", sectionKey: "leaderboard" }` | `rolling_stretch` | `leaderboard` | `best_window_game_log`, `window_game_log`, `game_log` for named-player detail when present. | Rolling Stretch. | Ranked rolling-window row; optional named-player game row detail. | "Best 10-game scoring stretch"; "LeBron best 10-game stretch" |

## Current Weak Contracts

- Leaderboard supporting columns are inferred from row keys and display-order rules. This is current behavior -- needs product decision if per-route columns should become explicit.
- Game-log product row cap is frontend-level (`12` rows) while backend finder limits are route-specific. This is current behavior -- needs product decision if pagination or row caps should change.
- Detail drawers are opt-in by pattern config and only appear when undisplayed row fields exist. This is current behavior -- needs product decision if detail drawers should remain.
- `fallback_table` remains available for unmatched routes, but Wave 1 routes are explicitly guarded from fallback use.
- `routeToPattern` remains a route-specific switch statement. This wave intentionally did not convert it to a registry.
