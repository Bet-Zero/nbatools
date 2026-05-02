# Result Display Map

> **Role:** The single source of truth for "what each query result should
> look like." Every route the engine can return has an entry below.
>
> **How to use:** When you run a real query that doesn't display the way
> you want, find its route's entry. Fill in `Currently shows`, fill in
> `Should show` (your curated intent), then file an agent task to make the
> displayed output match the intent. This doc is the spec; the section
> components in `frontend/src/components/` are the implementation.
>
> **How to find a route:** Run the query in the deployed UI, click the raw
> JSON toggle (or hit `/query` directly), and read the `route` field. That
> name maps to one of the entries below.

---

## How displays are wired

Each query response carries two fields that determine display:

- `query_class` — the broad family (one of: `summary`, `comparison`,
  `split_summary`, `finder`, `leaderboard`, `streak`, `count`).
- `route` — the specific routing within that class.

The frontend's `ResultSections.tsx` switch dispatches by `query_class`,
then refines by `route` (or by data-shape predicates) to pick a section
component. Each section component is responsible for rendering one or
more route's results.

---

## Status legend

- `[ ]` — neither `Currently shows:` nor `Should show:` filled in
- `[?]` — `Should show:` written but `Currently shows:` not yet observed against the deployed app
- `[~]` — both `Currently shows:` and `Should show:` filled in; fix is queued or in flight
- `[x]` — implementation matches `Should show:` and has been verified against the deployed app

Routes with intent already written but current display not yet observed
should be `[?]`, not `[ ]`. Mark them `[~]` once you've actually run the
queries and recorded what shows up today.

---

## Compound results — important

Some routes intentionally combine multiple result types in one display.
For example, `player_game_summary` ("Jokic last 10 games") should show
**both** a summary-stat block (totals/averages over the 10 games) **and**
the actual 10 game logs. Single-stat or single-section displays are wrong
for these routes — make sure the `Should show` section is explicit when
the answer requires multiple parts.

---

## Raw detail table policy

Raw `DataTable` sections are still valuable. They should not be deleted,
removed from responses, or treated as dead code. They are the inspection,
debugging, validation, export, and future advanced-view layer.

However, raw tables should **not** be part of the default visual answer.
For every route, polished cards/lists/charts should be the primary display,
and raw detail tables should be collapsed behind a consistent control
labeled **`Show raw table`** (closed) and **`Hide raw table`** (open). Use
this exact wording everywhere — do not vary the label per route or per
component.

Route entries may still mention which raw tables exist, but the default
expectation is:

- Keep raw table data and rendering support.
- Hide/collapse raw tables by default.
- Use one consistent reveal pattern across all result sections.
- Do not duplicate already-visible card/list content in an always-open
  table.
- The primary display must answer the query without requiring the user to
  open the raw table.

---

# Routes by query class

## summary

### `player_game_summary` `[~]`
- **Section component:** `PlayerSummarySection`
- **Example queries:**
  - `Jokic last 10 games`
  - `LeBron last 5 games`
  - `Curry this season`
- **Currently shows (4 stacked sections):**
  1. **Hero card:** player headshot (Avatar), team logo (TeamBadge), player name, three "hero" stats (PTS/REB/AST as averages), optional W-L record stat, supporting stats grid (StatBlock, 2 or 4 columns)
  2. **"Recent Games" card** (only if `game_log` section exists): scoring sparkline (line graph of points per game) + a list of game rows. **Hardcoded to show only the last 5 games** regardless of how many were requested. Each row shows: date, W/L badge, opponent logo, and exactly 4 stats: PTS / REB / AST / MIN
  3. **"Full Summary" data table:** raw DataTable dump of the `summary` section
  4. **"By Season" data table** (only if `by_season` section exists): DataTable dump of the `by_season` section
- **Should show:**
  1. **Player summary hero**
     - Player headshot
     - Player name
     - Team badge/logo when available
     - Query context: `Last 10 games`, `2025-26 Regular Season`, `2025 Playoffs`, `Career`, etc.
     - Main averages: PTS / REB / AST
     - Secondary averages when available: MIN, FG%, 3P%, FT%, TS% or eFG%, STL, BLK, TOV, +/-
     - Record/sample when available: W-L, win pct, game count
  2. **Full game log for last-N game queries**
     - For `last N games`, show all requested games, not only 5.
     - Each game row/card should show date, matchup (`vs DEN` / `at BOS`), opponent logo, W/L badge, score if available, and core box stats.
     - Core stats: PTS, REB, AST, MIN.
     - Extra stats when available: FG, 3P, FT, STL, BLK, TOV, +/-.
  3. **Season/career behavior**
     - For broad season/career summaries, do not dump every game by default.
     - Show the hero summary and, if useful, a short recent-games preview.
     - Full game logs should be shown by default only when the query asks for a game sample or game logs.
  4. **Raw tables**
     - Keep `Full Summary` and `By Season` tables available behind the shared collapsed raw-table/detail toggle.
     - Do not show raw tables open by default.
- **Bugs filed:** none yet (candidate: "Recent Games hardcoded to 5 games and 4 stat columns — should show all requested games and richer stats for `last N games` queries")
- **Notes:** Compound result. This route must show both summary stats AND full game logs when the query asks for a last-N sample. Single-stat or summary-only displays are wrong.

### `player_summary`-style routes for season averages `[?]`
- **Example queries:**
  - `Jokic this season`
  - `Curry career averages`
- **Should show:**
  - Player summary hero similar to `player_game_summary`.
  - Emphasize the season/career context and sample size.
  - Show season/career averages as the primary answer.
  - Do not show full game logs by default unless the query explicitly asks for games.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `team_record` `[~]`
- **Section component:** `TeamRecordSection`
- **Example queries:**
  - `Lakers record this season`
  - `Celtics record vs Bucks`
- **Currently shows (3 stacked sections):**
  1. **Hero card:** team logo (TeamBadge), team name (h2), primary record stat (large W-L display), supporting stats grid (StatBlock)
  2. **"Record Detail" data table:** raw DataTable dump of the `summary` section
  3. **"By Season" data table** (only if `by_season` section exists): DataTable dump of the `by_season` section, under "Team Record" / "By Season" headers
- **Should show:**
  1. **Single team record hero**
     - Team logo
     - Team name
     - Opponent logo/name when the query is opponent-scoped
     - Main record: W-L
     - Win percentage
     - Games/sample size
     - Context: season, regular season/playoffs, opponent, home/away, or other filter when applicable
  2. **Supporting team stats when available**
     - PPG
     - Opponent PPG if available
     - Net rating or +/- if available
     - REB
     - AST
     - 3PM
  3. **By-season behavior**
     - Show `By Season` as a collapsed/secondary detail when the query covers multiple seasons.
     - Do not clutter a single-season record query with an always-open duplicate table.
  4. **Raw tables**
     - Keep `Record Detail` and `By Season` tables available behind the shared collapsed raw-table/detail toggle.
     - Do not show raw tables open by default.

### `team_split_summary` `[?]`
- **Section component:** `SplitSummaryCardsSection` or `TeamSummarySection`
- **Example queries:**
  - `Lakers home vs away`
- **Should show:**
  - Team logo and team name.
  - Split type: home/away, wins/losses, before/after, regular/playoffs, etc.
  - Split cards for each bucket.
  - Each split card should show games, record, win pct, PPG, opponent PPG if available, net rating or +/-, REB, AST, and 3PM.
  - A difference/edge row is useful when there are exactly two buckets.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `game_summary` `[?]`
- **Example queries:**
  - `Lakers Celtics last night`
- **Should show:**
  - Game box-score style result.
  - Final score hero with team logos, team names, date, and W/L.
  - Location/home-away context when available.
  - Team stat comparison: FG%, 3P%, FT%, REB, AST, TOV, margin or +/-.
  - Top player performers when available: points leader, rebounds leader, assists leader.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `playoff_round_record` `[?]`
- **Section component:** `PlayoffSection`
- **Example queries:**
  - `Celtics record in second round`
- **Should show:**
  - Playoff round record card or leaderboard depending query shape.
  - Team logo/name, round, record, win pct, series/game count, and season/range context.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## comparison

### `player_compare` `[~]`
- **Section component:** `PlayerComparisonSection`
- **Example queries:**
  - `Jokic vs Embiid this season`
  - `LeBron vs MJ career`
- **Currently shows (4 stacked sections):**
  1. **Header section** (SectionHeader)
  2. **Side-by-side player blocks:** each block has player name (h3), supporting stats grid (StatBlock), optional record stat
  3. **"Player Summary Detail" data table:** raw DataTable dump of the `summary` section
  4. **"Metric Comparison" + "Full Metric Detail" data tables:** raw DataTable dumps of the `comparison` section (one with `highlight` styling)
- **Should show:**
  1. **Comparison header**
     - Player A vs Player B title.
     - Context: season/career, regular season/playoffs, games/sample size, and any filters.
  2. **Side-by-side player cards**
     - Headshot
     - Name
     - Team badge when relevant
     - Games/sample size
     - Record if available
     - PTS / REB / AST
     - MIN
     - TS% or eFG%
     - Usage if available
     - +/- if available
  3. **Metric comparison grid**
     - Metric label
     - Player A value
     - Player B value
     - Leader highlight
     - Difference/edge value, e.g. `Jokic +4.9 AST`
  4. **Career comparison behavior**
     - Clearly distinguish career averages from career totals.
     - Clearly identify regular season vs playoffs.
     - Show era/team context when available.
  5. **Raw tables**
     - Keep `Player Summary Detail` and `Full Metric Detail` tables available behind the shared collapsed raw-table/detail toggle.
     - Do not show raw tables open by default.

### `team_compare` `[?]`
- **Example queries:**
  - `Celtics vs Bucks this season`
- **Should show:**
  - Team A vs Team B header with team logos and context.
  - Side-by-side team cards showing record, win pct, games, PPG, opponent PPG, net rating or +/-, REB, AST, and 3PM.
  - Metric comparison grid with leader highlight and edge/delta.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `team_matchup_record` `[?]`
- **Section component:** `HeadToHeadSection`
- **Example queries:**
  - `Lakers vs Celtics head-to-head`
- **Should show:**
  - Matchup scoreboard style display.
  - Team A logo/name vs Team B logo/name.
  - Head-to-head context: season/range, regular season/playoffs, matchup sample.
  - Each team's matchup record, win pct, games, and average points if available.
  - Recent matchup list only if the data exists.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `player_on_off` `[?]`
- **Example queries:**
  - `Lakers on/off LeBron`
- **Should show:**
  - On/off split display with player identity and team context.
  - Separate `On` and `Off` cards.
  - Show minutes/possessions, net rating, offensive rating, defensive rating, pace, plus-minus, and primary box-score rates if available.
  - Include a clear difference/impact row: `On +X.X net rating`, etc.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## split_summary

### `player_split_summary` `[~]`
- **Section component:** `SplitSummaryCardsSection` or `SplitSummarySection`
- **Example queries:**
  - `Jokic home vs away`
  - `Curry in wins vs losses`
- **Should show:**
  - Player headshot, player name, and split type.
  - Split context: season, season type, game count, and filter.
  - Two or more split cards, one for each bucket.
  - Each split card should show bucket label, games, record if available, PTS, REB, AST, MIN, TS% or eFG%, 3P%, and +/- if available.
  - For two-bucket splits, show a small difference/edge row, e.g. `Home +3.2 PPG`, `Wins +5.1 AST`, `Away -2.4 +/-`.
  - Keep `Split Summary Detail` and `Split Comparison Detail` tables available behind the shared collapsed raw-table/detail toggle.
  - Do not show raw tables open by default.

---

## finder

### `player_game_finder` `[~]`
- **Section component:** `PlayerGameFinderSection`
- **Example queries:**
  - `games where Jokic had over 25 points and over 10 rebounds`
  - `Curry's 50-point games`
- **Should show:**
  1. **Finder summary header**
     - Player name/headshot when player-scoped.
     - Query condition, e.g. `25+ PTS, 10+ REB` or `50-point games`.
     - Count found, e.g. `12 games found`.
  2. **Game-log card/list display**
     - Date
     - Player headshot
     - Team badge
     - Opponent badge
     - Home/away
     - W/L
     - Score if available
     - Top-line stats: PTS, REB, AST, 3PM
     - Secondary stats when available: MIN, FG, 3P, FT, STL, BLK, TOV, +/-
  3. **Sort behavior**
     - If the query implies ranking/top performances, sort by the matching stat descending.
     - If the query is just a matching-game finder, default to most recent first.
  4. **Raw tables**
     - Keep `Player Game Detail` available behind the shared collapsed raw-table/detail toggle.
     - Do not show raw tables open by default.

### `game_finder` `[?]`
- **Example queries:**
  - `games where Lakers won by 20+`
- **Should show:**
  - Team/game equivalent of `player_game_finder`.
  - Count found and condition summary.
  - Game cards showing date, team, opponent, W/L, score/margin, and key team stats.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## leaderboard

### `season_leaders` `[~]`
- **Section component:** `LeaderboardSection`
- **Example queries:**
  - `most ppg in 2025 playoffs`
  - `top 10 scorers 2025-26`
  - `assists leaders this season`
- **Currently shows (2 stacked sections):**
  1. **Ranked list:** SectionHeader "Leaderboard" + "{N} entries" count. Per-row card with: rank (#1, #2, ...), identity mark (player headshot via Avatar, or team logo via TeamBadge), entity name, context chips (games played, season, season_type, team abbr, opponent if applicable, qualifier columns), one hero metric value (PTS/AST/PPG/etc.) on the right
  2. **"Full Leaderboard" data table:** DataTable of the same `leaderboard` rows. After PR #200 (in flight) hides system columns, this table shows the same content as the ranked list above — redundant by design until you decide otherwise
- **Should show:**
  1. **Ranked leaderboard list**
     - Rank
     - Player headshot or team logo
     - Entity name
     - Team abbreviation/logo for player rows when available
     - Main requested metric on the right, e.g. `32.4 PPG`, `11.2 AST`, `.645 TS%`
  2. **Context chips**
     - Games played
     - Season
     - Season type
     - Team
     - Qualifier/minimum when applicable
     - Opponent/playoff round/context when applicable
  3. **Metric companion context**
     - For percentage leaderboards, show makes/attempts when available, e.g. `.421 3P%` with `182/432 3P`.
     - For record leaderboards, show W-L when available.
  4. **Metric correctness**
     - The hero metric must match what the user asked for.
     - A query for `most PPG` must not accidentally feature games, wins, or another available numeric field as the primary metric.
  5. **Raw tables**
     - Keep `Full Leaderboard` available behind the shared collapsed raw-table/detail toggle.
     - Do not show raw tables open by default.
- **Bugs filed:** playoff min-games threshold (in flight), redundant Full Leaderboard table (decision: keep but hide by default)
- **Notes:** Most-used class. The raw leaderboard table is retained for inspection/export/future advanced views but should not be open by default.

### `season_team_leaders` `[~]`

- **Section component:** `LeaderboardSection` (same component as `season_leaders`)
- **Example queries:**
  - `best record since 2015`
  - `most wins by a team in a season`
- **Currently shows:** Same 2-section layout as `season_leaders` (ranked list + Full Leaderboard data table). For "best record" queries the hero metric is `win_pct`. **Wins and losses are not surfaced as context chips** because `contextItems` in `LeaderboardSection.tsx` doesn't know about them.
- **Should show:**
  - Same ranked leaderboard pattern as `season_leaders`, but team-first.
  - Each row should show rank, team logo, team name, season, and the requested metric.
  - For `best record`, hero metric should be win pct and context must show W-L.
  - For `most wins`, hero metric should be wins and context must show W-L and games.
  - Context chips should include record, games played, season type, and playoffs/regular season context.
  - Keep `Full Leaderboard` available behind the shared collapsed raw-table/detail toggle.
  - Do not show raw tables open by default.
- **Bugs filed:** playoff min-games threshold (in flight), wins/losses missing as context (in flight)

### `team_record_leaderboard` `[?]`
- **Example queries:**
  - `best home records this season`
- **Should show:**
  - Team leaderboard focused on record splits.
  - Each row should show rank, team logo, team name, record, win pct, games, and split context such as home/away.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `player_stretch_leaderboard` `[?]`
- **Example queries:**
  - `best 3-game scoring stretches this season`
- **Should show:**
  - Hybrid leaderboard/game-log display.
  - Each row should show rank, player headshot, player name, stretch length, date range, team, season, games included, and primary stretch metric such as `41.7 PPG`.
  - Supporting averages when available: REB, AST, TS%, MIN.
  - Optional expansion can show individual games inside the stretch.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `lineup_leaderboard` `[?]`
- **Example queries:**
  - `best 3-man units this season`
- **Should show:**
  - Lineup cards/list rather than generic table rows.
  - Each row should show rank, lineup members, team logo, minutes, games, possessions if available, season, and minimum threshold if applicable.
  - Primary metric should match the query: net rating, plus-minus, offensive rating, defensive rating, etc.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `lineup_summary` `[?]`
- **Example queries:**
  - `Lakers best lineup`
- **Should show:**
  - Team logo/name and lineup members.
  - Main lineup summary: minutes, games, net rating, offensive rating, defensive rating, pace, plus-minus, and any shooting/rebounding split available.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `player_occurrence_leaders` `[?]`
- **Section component:** `OccurrenceLeaderboardSection`
- **Example queries:**
  - `most 30-point games this season`
  - `most triple-doubles all-time`
- **Should show:**
  - Ranked occurrence leaderboard.
  - Each row should show rank, player headshot, player name, occurrence count as the hero metric, games played, season/range, team if relevant, threshold/condition, and season type.
  - Keep `Full Occurrence Detail` available behind the shared collapsed raw-table/detail toggle.

### `team_occurrence_leaders` `[?]`
- **Section component:** `OccurrenceLeaderboardSection`
- **Example queries:**
  - `most 120-point games this season`
- **Should show:**
  - Team-first occurrence leaderboard.
  - Each row should show rank, team logo, team name, occurrence count, season, games played, threshold/condition, and record when available.
  - Keep `Full Occurrence Detail` available behind the shared collapsed raw-table/detail toggle.

### `top_player_games` `[?]`
- **Example queries:**
  - `top 10 scoring games this season`
- **Should show:**
  - Ranked game-log leaderboard.
  - Each row should show rank, player headshot, player name, date, team/opponent, W/L, main metric, and supporting box-score stats.
  - Supporting stats should include REB, AST, MIN, FG, 3P, FT, STL, BLK, and TOV when available.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `top_team_games` `[?]`
- **Example queries:**
  - `top 10 team scoring games this season`
- **Should show:**
  - Team version of `top_player_games`.
  - Each row should show rank, team logo, team name, date, opponent, W/L, score, main metric, and supporting team stats.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## streak

### `player_streak_finder` `[?]`
- **Section component:** `StreakSection`
- **Example queries:**
  - `Jokic 25-point game streak`
- **Should show:**
  - Streak cards.
  - Each card should show player headshot, player name, streak condition, streak length as the hero value, active/completed badge, start date, end date, season, and regular/playoffs context.
  - During-streak averages should show when available: PTS, REB, AST, MIN, TS% or eFG%.
  - Keep `Full Streak Detail` available behind the shared collapsed raw-table/detail toggle.

### `team_streak_finder` `[?]`
- **Section component:** `StreakSection`
- **Example queries:**
  - `Lakers longest win streak`
- **Should show:**
  - Team streak cards.
  - Each card should show team logo, team name, streak type, length, active/completed badge, start/end dates, record/sample, and supporting stats when available.
  - Keep `Full Streak Detail` available behind the shared collapsed raw-table/detail toggle.

---

## count / playoff / other

### Playoff routes `[?]`
- **Section component:** `PlayoffSection`
- **Routes:** `playoff_appearances`, `playoff_history`, `playoff_matchup_history`, `playoff_round_record`
- **Example queries:**
  - `Lakers playoff history`
  - `Celtics vs Heat playoff matchups`
- **Should show:**
  - `playoff_history`: team logo/name, appearances, total playoff games, playoff record, win pct, titles/finals/conference finals if data exists, plus season breakdown with season, round reached, record, result/opponent when available.
  - `playoff_appearances`: leaderboard with rank, team logo, team name, appearances, era/range, seasons, and record if available.
  - `playoff_matchup_history`: matchup card with Team A vs Team B, series count, series record, game record, most recent series, and series list with year, round, winner, and series result.
  - `playoff_round_record`: team/round display with record, win pct, series/game count, and season/range context.
  - Keep all playoff raw detail tables available behind the shared collapsed raw-table/detail toggle.

---

## How to audit a route entry

For each entry above, follow this loop:

1. **Run the example queries in the deployed app.**
2. **Record what the UI shows now** in `Currently shows:`. Be specific —
   list every section that renders, what columns appear, what's missing.
3. **Write your curated intent** in `Should show:`. Be opinionated.
   Include section ordering, hero stats, what context chips to surface,
   what to hide.
4. **File any specific bugs** in `docs/planning/ui_bugs.md` and link them
   under `Bugs filed:`.
5. **Mark status `[~]`** when intent is written and fix is queued. Mark
   `[x]` once a PR has shipped that makes the display match the intent.

When the agent works a UI fix, it should reference this file's entry as
the spec — not invent its own interpretation of what the result should
look like.

---

## Working with this map

- Don't try to fill every entry in one sitting. Work through the routes
  you actually use first; let unused routes stay `[ ]` until you hit them.
- The most-used routes (`season_leaders`, `player_game_summary`,
  `team_record`, `player_compare`) are the highest leverage — getting
  those right covers most real usage.
- Compound routes (like `player_game_summary`) need explicit "show both
  X and Y" language in `Should show:` so agents don't pick one or the
  other.
- Update the entry as your taste evolves. The point is current truth, not
  historical record.

---

## Implementation priority

Recommended implementation order:

1. Add shared collapsed raw-table/detail toggle and apply it everywhere raw `DataTable` detail sections render.
2. Fix `player_game_summary` last-N behavior so all requested games can show.
3. Upgrade `season_leaders` and `season_team_leaders` metric/context handling.
4. Upgrade `team_record` hero/context and collapse duplicate details.
5. Upgrade `player_compare` comparison grid and edge/delta presentation.
6. Upgrade `player_game_finder` summary header, richer stat rows, and sort behavior.
7. Upgrade split summaries.
8. Then handle streak, occurrence, playoff, lineup, and lower-frequency routes.

---

## Cross-cutting display rules

These apply to every section and don't belong to any single route entry:

- Hide internal columns (`player_id`, `team_id`, `team_abbr` when
  redundant with `team_name`) from any rendered table.
- Raw detail tables are retained for every route but hidden/collapsed by
  default. They should render behind a consistent `Show raw table` / `View
  details` toggle so the clean display remains primary while the full
  underlying rows remain available for inspection, debugging, exports, or
  future advanced features.
- Identity treatment: every player row should show headshot if available,
  fall back to initials. Every team row should show logo if available,
  fall back to abbreviation badge.
- Mobile: every layout must work on a phone-sized viewport. Tables that
  need horizontal scroll should keep the identity column sticky.
- Numeric formatting: per-game averages to 1 decimal. Percentages as
  `.xxx` (not `xx.x%`). Counts as integers.
- Freshness: the freshness banner should always show on results, honestly
  reflecting `current_through`.
- Primary display must answer the query without requiring the raw table.
- Every ranked result must make the ranking metric visually obvious.
- Every filtered result must surface the filter context: season, season
  type, date range, opponent, home/away, playoff round, threshold, and
  sample size when available.
- Game-log results should show enough box-score context to be useful
  without opening raw JSON.
- Last-N game summaries must show all N games requested.
- Season/career summaries should not dump huge game logs unless the query
  explicitly asks for games.
