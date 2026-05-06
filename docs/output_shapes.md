# Output Shapes

This is the shape-level taxonomy for the current query-result body renderer.

Scope:

- The taxonomy starts at `frontend/src/components/results/ResultRenderer.tsx` and follows `frontend/src/components/results/config/routeToPattern.ts` through every dedicated pattern component.
- Shared chrome such as `ResultEnvelope` is intentionally not counted as a separate shape because it wraps every result the same way.
- Fixture counts come from the checked-in parser example sweep at `outputs/parser_examples_full_sweep/` using the 402-example manifest dated `2026-04-26T10:08:40.940353+00:00`.
- Sweep raw artifacts encode failures as sentinel `no_result` / `error` sections; those were normalized out here so the counts match what the frontend actually renders.
- Shapes with `0` fixtures are still real renderer shapes. Their listed queries are representative sweep prompts targeting that route family, but the current sweep resolved them into a no-result state instead of the live shape.

## Guided No Result

- Description: `NoResultDisplay` card with recovery suggestions.
- Components: `frontend/src/components/results/ResultRenderer.tsx`, `frontend/src/components/NoResultDisplay.tsx`.
- Sweep fixtures: `12`.
- Representative queries: `Who scored the most points last night?`; `What's the Mavericks' record when Luka Dončić scores 35 or more?`; `What is the Suns' record when Kevin Durant leads the team in scoring?`.
- Data fields read: top-level `result_status`, `result_reason`, `notes`, and `caveats`.
- Conditional sub-variants: `no_match`, `no_data`, and the default recoverable branch all keep the same card layout but swap the message copy and suggestion set.

## Message No Result

- Description: `NoResultDisplay` card without the suggestion grid.
- Components: `frontend/src/components/results/ResultRenderer.tsx`, `frontend/src/components/NoResultDisplay.tsx`.
- Sweep fixtures: `81`.
- Representative queries: `What team has played the best defense recently?`; `Which scorers have cooled off over their last 10 games?`; `Which team has the best net rating in its last 10 games?`.
- Data fields read: top-level `result_status`, `result_reason`, `notes`, and `caveats`.
- Conditional sub-variants: `unsupported`, `ambiguous`, `error`, and `empty_sections` all share the same card structure; only the copy and badge tone change.

## Entity Summary

- Description: single-player hero answer card with no table underneath.
- Components: `frontend/src/components/results/config/routeToPattern.ts`, `frontend/src/components/results/patterns/EntitySummaryResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `45`.
- Representative queries: `How has Jayson Tatum played against good teams this season?`; `How has Anthony Davis rebounded when LeBron James was out?`; `How does Jamal Murray score when Nikola Jokić is out?`.
- Data fields read: `result.sections.summary[0]`, `result.metadata.player_context`, `result.metadata.player`, `result.metadata.season`, `result.metadata.season_type`, `result.metadata.query_text`, optional disambiguation metadata, and the original `query` text.
- Conditional sub-variants: averages-present vs fallback summary sentence, explicit season-range vs career vs game-count context, and optional disambiguation note.

## Entity Summary + Recent Games

- Description: player summary hero stacked above a recent-games table.
- Components: `frontend/src/components/results/config/routeToPattern.ts`, `frontend/src/components/results/patterns/EntitySummaryResult.tsx`, `frontend/src/components/results/patterns/GameLogResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`.
- Sweep fixtures: `7`.
- Representative queries: `Luka last 5`; `Jokic last 10`; `luka w/o kyrie last 5`.
- Data fields read: `result.sections.summary`, `result.sections.game_log`, `result.metadata.window_size`, `result.metadata.stat`, `result.metadata.query_text`, and the original `query` text.
- Conditional sub-variants: the hero behaves like `Entity Summary`; the game-log block suppresses its summary strip and may or may not highlight a stat column depending on the resolved metric.

## Player Game Log

- Description: summary strip plus player-first game table.
- Components: `frontend/src/components/results/patterns/GameLogResult.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `34`.
- Representative queries: `What were the biggest scoring games this season?`; `Which players had the best games by Game Score this year?`; `What are the biggest triple-double games this season?`.
- Data fields read: `result.sections.finder` or `result.sections.leaderboard`, optional `result.sections.summary`, `result.metadata.stat`, `result.metadata.team_context`, `result.metadata.opponent_context`, and per-row player, team, date, opponent, score, result, and stat fields.
- Conditional sub-variants: `player_game_finder` and `top_player_games` share the same layout while changing row order and raw-detail title; the summary strip can come from a real summary row or derived context items.

## Team Game Log

- Description: summary strip plus team-first game table.
- Components: `frontend/src/components/results/patterns/GameLogResult.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `7`.
- Representative queries: `How often have the Lakers held opponents under 100 points this year?`; `Lakers opponents under 100 this year`; `Celtics (over 120 points and over 15 threes) or under 10 turnovers`.
- Data fields read: `result.sections.finder` or `result.sections.leaderboard`, optional `result.sections.summary`, `result.metadata.team_context`, `result.metadata.opponent_context`, and per-row date, team, opponent, score, W/L, and stat columns.
- Conditional sub-variants: `game_finder` and `top_team_games` share the same table shape; score and W/L columns only render when present.

## Game Summary Log

- Description: team game table with extra raw-detail drawers for adjacent sections.
- Components: `frontend/src/components/results/patterns/GameLogResult.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`.
- Sweep fixtures: `4`.
- Representative queries: `How do the Suns perform when Devin Booker didn't play?`; `Suns when Booker out`; `Bucks when Giannis out`.
- Data fields read: `result.sections.game_log`, fallback `result.sections.summary`, `result.sections.by_season`, `result.sections.top_performers`, `result.metadata.stat`, and team/opponent context metadata.
- Conditional sub-variants: the primary table can render from `game_log` or fall back to `summary`; extra drawers appear only for populated detail sections.

## Split Comparison

- Description: hero, split-bucket table, optional edge chips, and raw-detail drawers.
- Components: `frontend/src/components/results/patterns/SplitResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `0`.
- Representative queries: `How does Anthony Edwards shoot in wins vs losses?`; `How does Anthony Edwards shoot in wins versus losses?`; `Anthony Edwards shooting in wins vs losses`.
- Data fields read: `result.sections.split_comparison`, optional `result.sections.summary`, `result.metadata.split_type`, `result.metadata.season`, `result.metadata.season_type`, entity context metadata, and per-row bucket, record, and metric fields.
- Conditional sub-variants: player vs team subject identity, optional summary drawer, dynamic metric columns based on available data, and edge chips only when exactly two buckets have comparable numeric fields.

## On/Off Split

- Description: two-bucket on/off table using the split renderer with on/off-specific labels.
- Components: `frontend/src/components/results/patterns/SplitResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `0`.
- Representative queries: `What is the Nuggets' net rating with Nikola Jokić on the floor vs off the floor?`; `What is the Nuggets' net rating with Nikola Jokić on the floor versus off the floor?`; `Nuggets net rating Jokic on off`.
- Data fields read: `result.sections.summary`, entity context metadata, `presence_state` bucket values, and any on/off metric columns present on each row.
- Conditional sub-variants: fixed `presence_state` bucket labels, summary drawer intentionally suppressed, and the same dynamic metric-column expansion used by the generic split renderer.

## Streak Table

- Description: hero, ranked streak table, and highlighted raw detail.
- Components: `frontend/src/components/results/patterns/StreakResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `15`.
- Representative queries: `Jokic 5 straight games with 20+ points`; `Jokic longest streak of 30 point games`; `Jokic consecutive games with a made three`.
- Data fields read: `result.sections.streak`, player/team context metadata, and per-row `condition`, `streak_length`, `games`, `is_active`, `start_date`, `end_date`, record, and average-stat fields.
- Conditional sub-variants: player vs team identity, optional status/start/end/record columns, and optional average-stat columns depending on the streak payload.

## Playoff History

- Description: team playoff hero with a season-by-season history table.
- Components: `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `2`.
- Representative queries: `Lakers playoff history`; `Lakers playoff series record vs Celtics`. No third live hit in the current sweep.
- Data fields read: `result.sections.summary`, `result.sections.by_season`, team context metadata, and per-row appearance, title, finals, round, opponent, record, win percentage, and games fields.
- Conditional sub-variants: table rows come from `by_season` when present or fall back to `summary`; detail drawers appear only for populated sections.

## Playoff Round Records

- Description: ranked playoff-round leaderboard with a highlighted metric column.
- Components: `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `2`.
- Representative queries: `best finals record since 1980`; `best second round record`. No third live hit in the current sweep.
- Data fields read: `result.sections.leaderboard`, fallback `result.sections.summary` or `result.sections.by_season`, round metadata, and per-row rank, team, round, record, games, win percentage, and series counts.
- Conditional sub-variants: the highlighted metric is inferred from the available round-record fields; row source can shift between `leaderboard`, `summary`, and `by_season`.

## Playoff Matchup History

- Description: two-team playoff hero with a series-history table.
- Components: `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `1`.
- Representative queries: `Heat vs Knicks playoff history`. No second or third live hit in the current sweep.
- Data fields read: `result.sections.summary`, `result.sections.comparison`, `result.metadata.teams_context`, and per-row season, round, winner, series result, and team-prefixed record fields.
- Conditional sub-variants: the table prefers series rows and falls back to summary rows; team-specific record columns appear only when matching prefixed fields exist.

## Comparison Panels

- Description: head-to-head hero, subject panels, and metric comparison table.
- Components: `frontend/src/components/results/patterns/ComparisonResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `8`.
- Representative queries: `Jokic vs Embiid recent form`; `Jokic vs Embiid since 2021`; `Jokic head-to-head vs Embiid since 2021`.
- Data fields read: `result.sections.summary`, `result.sections.comparison`, `result.metadata.players_context`, `result.metadata.teams_context`, `result.metadata.head_to_head_used`, season/date metadata, and the summary/comparison metric rows.
- Conditional sub-variants: player vs team subjects, head-to-head vs generic comparison hero copy, optional metric table when only summary rows are present, and per-subject stat-chip sets based on available summary stats.

## Team Record

- Description: team record hero with a single-summary record table.
- Components: `frontend/src/components/results/patterns/RecordResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `35`.
- Representative queries: `What is the Celtics' record against playoff teams?`; `What is the Bucks' record when Giannis Antetokounmpo was out?`; `What is the Knicks' record when they allow fewer than 110 points?`.
- Data fields read: `result.sections.summary`, `result.sections.by_season`, team and opponent context metadata, the original `query`, and per-row record, win percentage, games, scoring, rating, rebound, assist, three-point, and season-type fields.
- Conditional sub-variants: opponent column appears only for matchup-scoped records; the by-season drawer appears only when `by_season` rows exist.

## Record By Decade

- Description: team hero plus decade breakdown table.
- Components: `frontend/src/components/results/patterns/RecordResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `1`.
- Representative queries: `Warriors record by decade`. No second or third live hit in the current sweep.
- Data fields read: `result.sections.summary`, `result.sections.by_season`, team context metadata, and per-row decade, seasons appeared, wins, losses, win percentage, games, and season-type fields.
- Conditional sub-variants: optional `seasons_appeared`, `games`, and `season_type` columns render only when present.

## Record By Decade Leaderboard

- Description: ranked decade leaderboard for team-record questions.
- Components: `frontend/src/components/results/patterns/RecordResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `1`.
- Representative queries: `winningest team of the 2010s`. No second or third live hit in the current sweep.
- Data fields read: `result.sections.leaderboard`, team context metadata, and per-row rank, team identity, decade, dynamic metric, record, games, win percentage, seasons, and season-type fields.
- Conditional sub-variants: the highlighted metric is inferred dynamically and duplicate optional columns are suppressed when they would repeat that metric.

## Matchup By Decade

- Description: two-team hero with a decade-by-decade matchup table.
- Components: `frontend/src/components/results/patterns/RecordResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/RawDetailToggle.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `1`.
- Representative queries: `Lakers vs Celtics by decade`. No second or third live hit in the current sweep.
- Data fields read: `result.sections.summary`, `result.sections.comparison`, `result.metadata.teams_context`, and per-row decade plus team-prefixed wins, losses, win percentage, and scoring columns.
- Conditional sub-variants: prefix detection uses real team abbreviations when available and falls back to generic matchup labels otherwise.

## Leaderboard Table

- Description: hero sentence over a ranked leaderboard table.
- Components: `frontend/src/components/results/patterns/LeaderboardResult.tsx`, `frontend/src/components/results/primitives/ResultHero.tsx`, `frontend/src/components/results/primitives/ResultTable.tsx`, `frontend/src/components/results/primitives/EntityIdentity.tsx`.
- Sweep fixtures: `146`.
- Representative queries: `Who leads the NBA in points per game this season?`; `Which players have the most total rebounds this year?`; `What team has the highest offensive rating this season?`.
- Data fields read: `result.sections.leaderboard`, `result.metadata.stat`, `result.metadata.metric`, `result.metadata.target_stat`, `result.metadata.target_metric`, `result.metadata.season`, `result.metadata.season_type`, `result.metadata.start_season`, `result.metadata.end_season`, `result.metadata.query_text`, optional disambiguation metadata, and row-level rank, entity identity, metric, and context columns.
- Conditional sub-variants: player vs team vs lineup/unknown entity identity, generic auto-detected metric vs explicit stretch/net-rating/appearance config, optional team-abbreviation column, and hero context that changes for season ranges, playoffs, or `since` phrases.

## Fallback Tables

- Description: plain section cards rendered by the generic fallback path.
- Components: `frontend/src/components/results/patterns/FallbackTableResult.tsx`, `frontend/src/components/DataTable.tsx`, `frontend/src/design-system` card and section-header primitives.
- Sweep fixtures: `0`.
- Representative queries: `lineups with LeBron and AD`; `lineup with LeBron and AD`; `LeBron and AD together lineups`.
- Data fields read: every populated section in `result.sections`; common label overrides exist for `summary`, `by_season`, `comparison`, `split_comparison`, `finder`, `leaderboard`, `streak`, and `game_log`.
- Conditional sub-variants: the number of cards and table columns depends entirely on which sections are populated and what each section's rows contain.

## Unclassified

- Description: catch-all bucket for a payload whose pattern stack does not map to the catalog.
- Components: `frontend/src/components/results/resultShapes.ts` only.
- Sweep fixtures: `0`.
- Representative queries: none; every current sweep fixture normalized into one of the named shapes above.
- Data fields read: whatever a future unmapped pattern would expose.
- Conditional sub-variants: not applicable until a new renderer branch ships.

## Summary Table

| Shape name                    | # fixtures | Component file(s)                                                    | Sub-variants                                                                            |
| ----------------------------- | ---------: | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Guided No Result              |         12 | `ResultRenderer.tsx`, `NoResultDisplay.tsx`                          | `no_match`, `no_data`, default recoverable                                              |
| Message No Result             |         81 | `ResultRenderer.tsx`, `NoResultDisplay.tsx`                          | `unsupported`, `ambiguous`, `error`, `empty_sections`                                   |
| Entity Summary                |         45 | `EntitySummaryResult.tsx`, `ResultHero.tsx`                          | average sentence fallback, context variants, optional disambiguation                    |
| Entity Summary + Recent Games |          7 | `EntitySummaryResult.tsx`, `GameLogResult.tsx`                       | hero variants plus metric-highlighted recent-game table                                 |
| Player Game Log               |         34 | `GameLogResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`        | finder vs top-games ordering, summary-strip source, optional score/W-L                  |
| Team Game Log                 |          7 | `GameLogResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`        | finder vs top-games ordering, optional score/W-L                                        |
| Game Summary Log              |          4 | `GameLogResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`        | `game_log` vs summary fallback, optional extra drawers                                  |
| Split Comparison              |          0 | `SplitResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`          | player vs team, optional summary drawer, two-bucket edge chips                          |
| On/Off Split                  |          0 | `SplitResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`          | fixed on/off labels, no summary drawer                                                  |
| Streak Table                  |         15 | `StreakResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`         | player vs team identity, optional status/date/record/stat columns                       |
| Playoff History               |          2 | `PlayoffHistoryResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx` | `by_season` vs summary fallback, optional drawers                                       |
| Playoff Round Records         |          2 | `PlayoffHistoryResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx` | dynamic highlighted metric, row-source fallback                                         |
| Playoff Matchup History       |          1 | `PlayoffHistoryResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx` | series rows vs summary fallback, team-prefixed record columns                           |
| Comparison Panels             |          8 | `ComparisonResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`     | player vs team, head-to-head vs generic comparison, optional metric table               |
| Team Record                   |         35 | `RecordResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`         | optional opponent column, optional by-season drawer                                     |
| Record By Decade              |          1 | `RecordResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`         | optional seasons/games/type columns                                                     |
| Record By Decade Leaderboard  |          1 | `RecordResult.tsx`, `ResultTable.tsx`                                | dynamic highlighted metric, duplicate-column suppression                                |
| Matchup By Decade             |          1 | `RecordResult.tsx`, `ResultTable.tsx`, `RawDetailToggle.tsx`         | real-team prefix detection vs generic fallback                                          |
| Leaderboard Table             |        146 | `LeaderboardResult.tsx`, `ResultTable.tsx`                           | player/team/lineup identity, generic vs custom metric config, context sentence variants |
| Fallback Tables               |          0 | `FallbackTableResult.tsx`, `DataTable.tsx`                           | section-card count and columns depend on populated sections                             |
| Unclassified                  |          0 | `resultShapes.ts`                                                    | reserved for future unmapped branches                                                   |
