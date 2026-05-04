# Result Display Map

> **Role:** The single source of truth for "what each query result should
> look like." Every route the engine can return has an entry below.
>
> **How to use:** When you run a real query that doesn't display the way
> you want, find its route's entry. Fill in `Currently shows`, fill in
> `Should show` (your curated intent), then file an agent task to make the
> displayed output match the intent. This doc is the spec; the pattern
> components in `frontend/src/components/results/` are the implementation.
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

The frontend's `ResultRenderer.tsx` entry point dispatches by `route` through
`results/config/routeToPattern.ts`. Each mapped route returns one or more
pattern configs (`LeaderboardResult`, `GameLogResult`, `ComparisonResult`,
etc.). Unmapped routes intentionally fall through to `FallbackTableResult`.

---

## Status legend

- `[ ]` — neither `Currently shows:` nor `Should show:` filled in
- `[?]` — `Should show:` written but `Currently shows:` not yet observed against the deployed app
- `[~]` — both `Currently shows:` and `Should show:` filled in; fix is queued or in flight
- `[x]` — implementation matches `Should show:` and has been verified against the deployed app

Routes with intent already written but current display not yet observed
should be `[?]`, not `[ ]`. Mark them `[~]` once you've actually run the
queries and recorded what shows up today.

> **Closeout audit — 2026-05-04.** The route entries below were reconciled
> against the deployed main URL
> `https://nbatools-git-main-brents-projects-686e97fc.vercel.app`. Examples
> that no longer route to their documented entry were replaced with stable
> route examples or marked with the remaining gap.

---

## Compound results — important

Some routes intentionally combine multiple result types in one display.
For example, `player_game_summary` ("Jokic last 10 games") should show
**both** a summary-stat block (totals/averages over the 10 games) **and**
the actual 10 game logs. Single-stat or single-section displays are wrong
for these routes — make sure the `Should show` section is explicit when
the answer requires multiple parts.

---

## Default answer pattern (StatMuse baseline)

Adopted 2026-05-03. Every route's `Should show:` should match this
pattern unless the route entry explicitly opts out with a reason.

**Two parts: a sentence-style hero card, then one dense table.**

### Hero card (always present)

- Colored background (per-route or per-domain hue is fine).
- Subject illustration or headshot on the left (player headshot, team
  logo, or a small composite for multi-subject queries).
- One plain-English sentence stating the headline answer.
  - Game/season summary: *"Nikola Jokić has averaged 26.7 points, 12.5
    rebounds and 9.4 assists in his last 10 games."*
  - Leaderboard: *"Giannis Antetokounmpo scored the most points per game
    in the 2025 playoffs, with 33.0 per game."*
  - Record: *"The Lakers are 31-12 this season."*
- No stat tiles, no chip rows, no stacked metric blocks. Just the
  sentence.
- Optional small disambiguation note directly under the hero when the
  parser picked one of multiple plausible interpretations:
  *"Interpreted as: most ppg by a player in 2025 playoffs."*

### Answer table (almost always present)

- One tight, dense table. **The table is the answer**, not a secondary
  detail layer.
- One row per result entity (one game in a game log, one player or team
  in a leaderboard, one matchup in a matchup history, etc.).
- Inline headshot/logo per row, not a separate card.
- The queried metric column gets visual emphasis (subtle background tint
  on the column, slightly bolder).
- Right-aligned numbers for scanning, left-aligned identity columns.
- Horizontal scroll for long-tail columns rather than wrapping.
- For game logs and similar windowed results, add `Average` and `Total`
  footer rows inside the same table.
- No card-per-row layouts for tabular data. Cards are reserved for the
  hero only.
- No redundant secondary tables below the answer table.

### Multi-layer / compound queries

The product supports queries beyond StatMuse's coverage (multi-filter,
boolean-combined, compound). These may require additional sections
beyond the hero + answer table, but those additions should feel cohesive
with the baseline:

- Additional context appears as new rows in the same table, additional
  footer rows, or a small secondary section *below* the answer table —
  not as a different visual style.
- If a route genuinely needs a different shape (e.g., side-by-side
  comparisons, multi-bucket splits), the route entry's `Should show:`
  must call that out explicitly with a concrete description.

### Goal

Match StatMuse's answer shape as a baseline, then iterate per route to
exceed it where the product's deeper queries warrant it. The baseline is
the floor, not the ceiling.

---

## Raw detail table policy

Under the StatMuse baseline, the **answer table is the primary display**
— it should not be hidden behind a toggle. Raw `DataTable` sections that
are *secondary* to the answer (e.g., a `by_season` breakdown when the
query is single-season, a `comparison` detail dump when the hero
comparison is sufficient) may still be collapsed behind a consistent
control labeled **`Show raw table`** (closed) / **`Hide raw table`**
(open). Use this exact wording.

Rules of thumb:

- The table that *is* the answer (game log, leaderboard, finder list)
  is open by default.
- Tables that contain the same content as the hero in tabular form are
  redundant and should be removed entirely, not just hidden.
- Tables that contain genuinely additional / drill-down data may live
  behind the toggle.
- Never delete `DataTable` itself; it remains the substrate for both
  always-open answer tables and toggled detail tables.

---

# Routes by query class

> **Pre-baseline notice.** Most route entries below were written before
> the StatMuse-baseline pattern was adopted on 2026-05-03. Their
> `Should show:` text describes card-per-row layouts, chip rows, and
> stat-tile heroes that are now superseded by the baseline pattern.
> Routes whose `Should show:` has been rewritten against the StatMuse
> baseline are marked `[~]` and have an explicit `Reference:` line. All
> other route entries should be considered stale until they are
> rewritten against the baseline. The agent should default to the
> baseline pattern (sentence hero + dense answer table) for any route
> whose entry has not yet been rewritten.

## summary

### `player_game_summary` `[~]`
- **Pattern:** `EntitySummaryResult` / `GameLogResult`
- **Example queries:**
  - `Jokic last 10 games`
  - `LeBron last 5 games`
  - `Curry this season`
- **Reference:** StatMuse for `jokic stats last 10 games`. Hero card with
  player illustration on the left and the sentence
  *"Nikola Jokić has averaged 26.7 points, 12.5 rebounds and 9.4 assists
  in his last 10 games."* Below it, one dense game-log table with rank,
  inline headshot, name, date, team, vs/@, opponent, then MIN / PTS /
  REB / AST / STL / BLK / FG… columns. Footer rows for `Average` and
  `Total` inside the same table.
- **Currently shows (shipped, does NOT match the StatMuse baseline):**
  1. Player summary hero with stacked stat tiles (PTS/REB/AST as
     individual hero stats), record stat, and supporting stats grid.
  2. "Recent Games" cards — one card per game with header, meta block,
     and stat tiles. Card-per-row layout for tabular data.
  3. `Full Summary` and `By Season` raw tables behind a toggle.
- **Should show (locked to StatMuse baseline):**
  1. **Hero card.** Colored background, player illustration/headshot on
     the left, one-sentence answer:
     *"{player} has averaged {pts_avg} points, {reb_avg} rebounds and
     {ast_avg} assists in {games} games."*
     For the `last N games` form, the sentence should specify the window
     ("in his last 10 games"). For broader season/career queries, swap
     the window phrase ("this season", "in his career"). No stat tiles,
     no chip rows, no stacked metrics under the sentence.
  2. **Game-log table.** Open by default, dense rows. Columns:
     - `#` (rank within the window, 1..N)
     - Inline headshot
     - Player name
     - Date
     - Team abbr (with logo)
     - Home/away marker (`vs` / `@`)
     - Opponent abbr (with logo)
     - MIN, PTS, REB, AST, STL, BLK, FG, 3P, FT, TOV (and +/- when
       available, scrollable)
     - Footer rows: `Average`, `Total`
  3. **Behavior for non-last-N queries.** For broad `this season` /
     `career` summaries that have no requested per-game window, omit the
     game-log table. The hero sentence stands alone, optionally followed
     by a `By Season` answer table when multi-season is implied.
  4. **Raw tables.** Remove the redundant `Full Summary` and (when
     single-season) `By Season` raw tables. They duplicate content
     already in the hero/answer table. If a `by_season` breakdown is
     genuinely additional context, render it as a secondary answer
     table below the primary game log, not as a hidden raw dump.
- **Bugs filed:** current shipped UI ≠ baseline; tracked under
  StatMuse-baseline rebuild work.
- **Notes:** Compound result. The hero answers the summary part; the
  game-log table answers the per-game part. Both are required when the
  query asks for a sample window.

### `player_summary`-style routes for season averages `[x]`
- **Pattern:** `EntitySummaryResult` via `player_game_summary`
- **Example queries:**
  - `Jokic this season`
  - `Curry career averages`
- **Currently shows (shipped):**
  - Same player summary hero as `player_game_summary`, emphasizing season/career context and sample size.
  - Raw summary/by-season rows stay available behind collapsed raw-table toggles.
- **Should show:**
  - Player summary hero similar to `player_game_summary`.
  - Emphasize the season/career context and sample size.
  - Show season/career averages as the primary answer.
  - Do not show full game logs by default unless the query explicitly asks for games.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `team_record` `[~]`
- **Pattern:** `FallbackTableResult` (pending dedicated record pattern)
- **Example queries:**
  - `Lakers record this season`
  - `Celtics record vs Bucks`
- **Currently shows (deployed 2026-05-04):**
  1. The deployed route returns `summary` and `by_season` sections.
  2. The frontend intentionally falls through to `FallbackTableResult`
     because `team_record` is not yet mapped to a dedicated record pattern.
  3. No record hero, team-logo treatment, or collapsed record-detail
     treatment ships after the legacy per-route section removal.
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
- **Follow-up:** `result_display_followup_queue.md` tracks the record/fallback
  pattern work.

### `team_split_summary` `[x]`
- **Pattern:** `SplitResult`
- **Example queries:**
  - `Lakers home vs away`
- **Currently shows (shipped):**
  - Team identity hero with split context, bucket cards, games/record/win pct, core stats, and two-bucket edge chips.
  - `Split Summary Detail` and `Split Comparison Detail` raw tables retained behind collapsed raw-table toggles.
- **Should show:**
  - Team logo and team name.
  - Split type: home/away, wins/losses, before/after, regular/playoffs, etc.
  - Split cards for each bucket.
  - Each split card should show games, record, win pct, PPG, opponent PPG if available, net rating or +/-, REB, AST, and 3PM.
  - A difference/edge row is useful when there are exactly two buckets.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `game_summary` `[x]`
- **Example queries:**
  - `Celtics summary 2024-25`
  - `Celtics recent form`
- **Currently shows (shipped):**
  - `GameLogResult` renders `game_log` rows as a dense team game table with team/opponent identity, date, home/away matchup, W/L, score when available, margin, and core team stats.
  - Aggregate-only summaries fall back to a team/opponent summary hero with record/sample and team stat context.
  - When the game sample can be matched to player box-score rows, supplied top-performer rows remain available in the route's detail sections.
  - When player box-score rows are unavailable or cannot be matched, the engine reports an explicit caveat instead of synthesizing client-side leaders.
- **Should show:**
  - Game box-score style result.
  - Final score hero with team logos, team names, date, and W/L.
  - Location/home-away context when available.
  - Team stat comparison: FG%, 3P%, FT%, REB, AST, TOV, margin or +/-.
  - Top player performers when available: points leader, rebounds leader, assists leader.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `playoff_round_record` `[x]`
- **Pattern:** `PlayoffHistoryResult`
- **Example queries:**
  - `best second round record`
  - `best finals record since 1980`
- **Currently shows (shipped):**
  - `PlayoffHistoryResult` renders playoff round/team context, record/win pct/sample stats, season/range context, and collapsed raw playoff details.
- **Should show:**
  - Playoff round record card or leaderboard depending query shape.
  - Team logo/name, round, record, win pct, series/game count, and season/range context.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## comparison

### `player_compare` `[x]`
- **Pattern:** `ComparisonResult`
- **Example queries:**
  - `Jokic vs Embiid this season`
  - `LeBron vs MJ career`
- **Currently shows (shipped):**
  1. Comparison header with player identities and query context.
  2. Side-by-side player cards with headshots, team context, sample/record, PTS/REB/AST, and supporting stats when available.
  3. Metric comparison grid with leader/delta treatment.
  4. `Player Summary Detail` and `Full Metric Detail` raw tables retained behind the shared collapsed raw-table toggle.
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

### `team_compare` `[x]`
- **Example queries:**
  - `Celtics vs Bucks this season`
- **Currently shows (shipped):**
  - Head-to-head-flavored `team_compare` responses render through `ComparisonResult` in head-to-head mode.
  - Aggregate team comparison responses render through `ComparisonResult` with team logos/names, side-by-side team panels, record/win-pct/games context, core stats, metric deltas, and collapsed raw detail.
- **Should show:**
  - Team A vs Team B header with team logos and context.
  - Side-by-side team cards showing record, win pct, games, PPG, opponent PPG, net rating or +/-, REB, AST, and 3PM.
  - Metric comparison grid with leader highlight and edge/delta.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `team_matchup_record` `[x]`
- **Pattern:** `ComparisonResult`
- **Example queries:**
  - `Lakers vs Celtics all-time record`
  - `Lakers vs Celtics matchup record since 2010`
- **Currently shows (shipped):**
  - `ComparisonResult` renders a matchup hero with team logos/names, participant record/sample stats, metric rows, and collapsed detail tables.
- **Should show:**
  - Matchup scoreboard style display.
  - Team A logo/name vs Team B logo/name.
  - Head-to-head context: season/range, regular season/playoffs, matchup sample.
  - Each team's matchup record, win pct, games, and average points if available.
  - Recent matchup list only if the data exists.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `player_on_off` `[~]`
- **Example queries:**
  - `Jokic on/off`
  - `Lakers on/off LeBron`
- **Currently shows (deployed 2026-05-04):**
  - Route recognition works, but deployed examples return `no_result` with
    an `unsupported` reason because the current data layer lacks trusted
    play-by-play or lineup-stint coverage.
  - `SplitResult` is mapped for row-bearing `player_on_off` responses, but
    the deployed app cannot yet verify the card/impact display against live
    rows.
- **Should show:**
  - Dedicated on/off split display with player identity, player headshot
    fallback, and team badge/context.
  - Separate `On` and `Off` cards when both split rows are returned;
    single-state queries render the available split card.
  - Cards show games, minutes, possessions, offensive rating, defensive
    rating, net rating, pace, plus-minus, and primary box-score rates when
    those fields are present in the response.
  - When both `On` and `Off` rows include net rating, an impact row
    identifies the larger side, e.g. `On +X.X net rating`; plus-minus is
    used as the fallback comparison metric.
  - Raw split rows remain available behind the shared collapsed
    `RawDetailToggle`.
- **Follow-up:** data-backed verification remains open in
  `result_display_followup_queue.md`.

---

## split_summary

### `player_split_summary` `[x]`
- **Pattern:** `SplitResult`
- **Example queries:**
  - `Jokic home vs away`
  - `Curry in wins vs losses`
- **Currently shows (shipped):**
  - Player identity hero with split context, bucket cards, games/record, core and efficiency stats, and two-bucket edge chips.
  - `Split Summary Detail` and `Split Comparison Detail` raw tables retained behind collapsed raw-table toggles.
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

### `player_game_finder` `[x]`
- **Pattern:** `GameLogResult`
- **Example queries:**
  - `games where Jokic had over 25 points and over 10 rebounds`
  - `Curry's 50-point games`
- **Currently shows (shipped):**
  - Player finder header with headshot, condition/threshold chips, count found, season/range context, rich game-card list, recent/ranked sorting, and collapsed `Player Game Detail`.
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

### `game_finder` `[x]`
- **Example queries:**
  - `games where Lakers won by 20+`
- **Currently shows (shipped):**
  - `GameLogResult` renders team game rows with team/opponent identity, date, home/away matchup, W/L, score when available, margin, and key team stats.
  - `Game Detail` remains available behind the shared collapsed raw-table toggle.
- **Should show:**
  - Team/game equivalent of `player_game_finder`.
  - Count found and condition summary.
  - Game cards showing date, team, opponent, W/L, score/margin, and key team stats.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

---

## leaderboard

### `season_leaders` `[~]`
- **Pattern:** `LeaderboardResult`
- **Example queries:**
  - `most ppg in 2025 playoffs`
  - `top 10 scorers 2025-26`
  - `assists leaders this season`
- **Reference:** StatMuse for `most ppg in 2025 playoffs`. Hero card
  with the #1 player's illustration and the sentence
  *"Giannis Antetokounmpo scored the most points per game in the 2025
  playoffs, with 33.0 per game."* Subtitle directly under the hero:
  *"Interpreted as: most ppg by a player in 2025 playoffs."* Below it,
  one dense leaderboard table with rank, inline headshot, name, the
  queried metric column visually highlighted (subtle background tint),
  then SEASON, TM, GP, MPG, RPG, APG, SPG, BPG, FG… as supporting
  columns.
- **Currently shows (shipped, does NOT match the StatMuse baseline):**
  1. Ranked card list — one card per row with rank, identity, context
     chips, and one hero metric value. Card-per-row layout for tabular
     data.
  2. `Full Leaderboard` raw table behind a toggle.
- **Should show (locked to StatMuse baseline):**
  1. **Hero card.** Colored background, illustration of the #1 entity
     on the left, one-sentence answer:
     *"{leader} {verb} the most {metric_label} in the {season}
     {season_type}, with {value} per game."*
     Verb varies: "scored" for points, "averaged" for per-game stats,
     "had" for counts. No stat tiles under the sentence.
  2. **Disambiguation note (when applicable).** Small subtitle directly
     under the hero when the parser picked one of several possible
     interpretations: *"Interpreted as: most ppg by a player in 2025
     playoffs."* Skip when the query was unambiguous.
  3. **Leaderboard table.** Open by default, dense rows. Columns:
     - `#` (rank)
     - Inline headshot (player) or logo (team)
     - Entity name
     - **Queried metric column** (visually emphasized — subtle
       background tint, slightly bolder)
     - Season
     - Team abbr (with logo) for player rows
     - Games played
     - Supporting per-game stats (MPG, RPG, APG, SPG, BPG)
     - Shooting columns (FG, 3P, FT) — scrollable to the right
  4. **Metric correctness.** The queried metric must be the highlighted
     column. A query for `most PPG` must not accidentally feature
     games or wins as the primary metric.
  5. **Raw tables.** Remove the redundant `Full Leaderboard` raw table.
     The leaderboard table above is the answer table — adding a second
     raw dump below is redundant.
- **Bugs filed:** current shipped UI ≠ baseline; tracked under
  StatMuse-baseline rebuild work.
- **Notes:** Most-used class. Visual quality of this route disproportionately
  shapes the felt quality of the whole product.

### `season_team_leaders` `[~]`

- **Pattern:** `LeaderboardResult`
- **Example queries:**
  - `best team ppg this season`
  - `team assists leaders this season`
- **Should show (locked to StatMuse baseline):**
  - Same hero + leaderboard-table pattern as `season_leaders`, but
    team-first.
  - Hero sentence variants:
    - For `best record`: *"The {team} had the best record since {year},
      going {wins}-{losses} ({win_pct})."*
    - For `most wins`: *"The {team} won the most games in a season since
      {year}, with {wins} wins."*
  - Leaderboard table columns: rank, inline team logo, team name, the
    queried metric column highlighted, plus W-L, GP, season, season type
    (regular season / playoffs).
  - Same metric-correctness rule as `season_leaders`: a query for
    `most wins` features wins, not win pct.
  - Remove the redundant `Full Leaderboard` raw table — the leaderboard
    table above is the answer.
- **Bugs filed:** current shipped UI ≠ baseline; tracked under
  StatMuse-baseline rebuild work.

### `team_record_leaderboard` `[x]`
- **Example queries:**
  - `best record since 2015`
  - `most home wins over the last 10 seasons`
- **Currently shows (shipped):**
  - `LeaderboardResult` renders team-ranked rows with logo/name, requested record metric, W-L/games context, split context when present, and collapsed raw detail.
- **Should show:**
  - Team leaderboard focused on record splits.
  - Each row should show rank, team logo, team name, record, win pct, games, and split context such as home/away.
  - Keep raw tables available behind the shared collapsed raw-table/detail toggle.

### `player_stretch_leaderboard` `[x]`
- **Example queries:**
  - `best 3-game scoring stretches this season`
- **Currently shows (shipped):**
  - Dedicated stretch leaderboard rows/cards.
  - Each row shows rank, player headshot/name, team badge, stretch length, date range, season, games included, and the primary stretch metric such as `41.7 PPG`.
  - Supporting averages render when present: REB, AST, TS%, and MIN.
  - Optional game expansion renders behind a collapsed `Stretch Games` raw-detail toggle when the response includes `window_games`, `game_log`, or `games` rows.
  - Current execution returns stretch windows but not per-game expansion rows or supporting averages by default; the display is ready for those fields when the response adds them.
  - Raw leaderboard rows remain available behind the shared collapsed `RawDetailToggle`.

### `lineup_leaderboard` `[~]`
- **Example queries:**
  - `best 3-man units this season`
- **Currently shows (deployed 2026-05-04):**
  - Route recognition works, but the deployed example returns `no_result`
    with an `unsupported` reason because trusted `league_lineup_viz`
    coverage is unavailable for the requested slice.
  - `LeaderboardResult` is mapped for row-bearing `lineup_leaderboard`
    responses, but deployed data cannot yet verify the lineup rows.
- **Should show:**
  - Dedicated ranked lineup rows/cards rather than generic table rows.
  - Each row shows rank, lineup members, team badge, season, unit size,
    minute-minimum context, minutes, and games/possessions when those fields
    are present in the response.
  - Primary metric follows the requested/stat-backed metric when present,
    with default fallback to net rating and related lineup rating fields.
  - Raw leaderboard rows remain available behind the shared collapsed
    `RawDetailToggle`.
- **Follow-up:** data-backed verification remains open in
  `result_display_followup_queue.md`.

### `lineup_summary` `[~]`
- **Example queries:**
  - `lineup with Tatum and Jaylen Brown`
- **Currently shows (deployed 2026-05-04):**
  - Route recognition works, but the deployed example returns `no_result`
    with an `unsupported` reason because trusted lineup coverage is
    unavailable.
  - If row-bearing `lineup_summary` data is returned, the route currently
    falls through to `FallbackTableResult`; it is not mapped to a dedicated
    lineup summary pattern after the legacy cleanup.
- **Should show:**
  - Dedicated lineup summary hero/card with team badge/name and lineup
    members.
  - Main lineup summary shows unit size, season, minute-minimum context,
    minutes, games, possessions, net/offensive/defensive rating, pace,
    plus-minus, and shooting/rebounding split fields when present.
  - Raw summary rows remain available behind the shared collapsed
    `RawDetailToggle`.
- **Follow-up:** pattern mapping and data-backed verification remain open in
  `result_display_followup_queue.md`.

### `player_occurrence_leaders` `[x]`
- **Pattern:** `LeaderboardResult`
- **Example queries:**
  - `most 50 point games since 2020`
  - `how many Jokic games with 30+ points and 10+ rebounds since 2021`
  - `most triple-doubles all-time`
- **Currently shows (shipped):**
  - `LeaderboardResult` renders ranked player occurrence rows with headshots, event count hero metric, games/season/team/threshold context, and collapsed detail.
- **Should show:**
  - Ranked occurrence leaderboard.
  - Each row should show rank, player headshot, player name, occurrence count as the hero metric, games played, season/range, team if relevant, threshold/condition, and season type.
  - Keep `Full Occurrence Detail` available behind the shared collapsed raw-table/detail toggle.

### `team_occurrence_leaders` `[x]`
- **Pattern:** `LeaderboardResult`
- **Example queries:**
  - `teams with most 130 point games since 2020`
  - `how many Celtics games with 120+ points and 15+ threes since 2022`
- **Currently shows (shipped):**
  - `LeaderboardResult` renders team occurrence rows with logo/name, occurrence count hero metric, season/games/condition/record context when present, and collapsed detail.
- **Should show:**
  - Team-first occurrence leaderboard.
  - Each row should show rank, team logo, team name, occurrence count, season, games played, threshold/condition, and record when available.
  - Keep `Full Occurrence Detail` available behind the shared collapsed raw-table/detail toggle.

### `top_player_games` `[x]`
- **Example queries:**
  - `highest scoring games this season`
  - `season high games`
- **Currently shows (shipped):**
  - Dedicated ranked player-game leaderboard cards.
  - Each row shows rank, player headshot/name, team badge, date, opponent/location, W/L when available, requested metric, and supporting box-score stats.
  - Supporting stats include REB, AST, MIN, FG, 3P, FT, STL, BLK, and TOV when available.
  - Raw rows remain available behind the shared collapsed `RawDetailToggle`.

### `top_team_games` `[x]`
- **Example queries:**
  - `top team scoring games this season`
  - `top team games`
- **Currently shows (shipped):**
  - Dedicated ranked team-game leaderboard cards.
  - Each row shows rank, team badge/name, date, opponent/location, W/L, score when available, requested metric, and supporting team stats.
  - Raw rows remain available behind the shared collapsed `RawDetailToggle`.

---

## streak

### `player_streak_finder` `[x]`
- **Pattern:** `StreakResult`
- **Example queries:**
  - `Jokic 25-point game streak`
- **Currently shows (shipped):**
  - `StreakResult` renders player streak rows with headshot, condition, streak length, active/completed badge, start/end dates, season/season-type context, supporting averages, and collapsed `Full Streak Detail`.
- **Should show:**
  - Streak cards.
  - Each card should show player headshot, player name, streak condition, streak length as the hero value, active/completed badge, start date, end date, season, and regular/playoffs context.
  - During-streak averages should show when available: PTS, REB, AST, MIN, TS% or eFG%.
  - Keep `Full Streak Detail` available behind the shared collapsed raw-table/detail toggle.

### `team_streak_finder` `[x]`
- **Pattern:** `StreakResult`
- **Example queries:**
  - `longest Lakers winning streak`
  - `longest Lakers winning streak 2024-25`
- **Currently shows (shipped):**
  - `StreakResult` renders team streak rows with logo/name, streak type/condition, length, active/completed badge, span/context, record/supporting stats, and collapsed `Full Streak Detail`.
- **Should show:**
  - Team streak cards.
  - Each card should show team logo, team name, streak type, length, active/completed badge, start/end dates, record/sample, and supporting stats when available.
  - Keep `Full Streak Detail` available behind the shared collapsed raw-table/detail toggle.

---

## count / playoff / other

### `record_by_decade` `[~]`
- **Pattern:** `FallbackTableResult`
- **Example queries:**
  - `Lakers by decade`
- **Currently shows (deployed 2026-05-04):**
  - The route returns `summary` and `by_season` sections, then falls through
    to `FallbackTableResult`.
- **Should show:**
  - Historical team record display grouped by decade.
  - Team logo/name, covered season range, total record/win pct, and one
    dense decade table with decade, seasons, wins, losses, win pct, games,
    and season-type context.
  - Raw sections remain available behind the shared collapsed raw-table
    toggle when they add debug/detail value.
- **Follow-up:** historical record display work is tracked in
  `result_display_followup_queue.md`.

### `record_by_decade_leaderboard` `[~]`
- **Pattern:** `FallbackTableResult`
- **Example queries:**
  - `most wins by decade since 1980`
  - `winningest team of the 2010s`
- **Currently shows (deployed 2026-05-04):**
  - The route returns a `leaderboard` section, then falls through to
    `FallbackTableResult`.
- **Should show:**
  - Dense historical leaderboard grouped by decade.
  - Rank, team logo/name, highlighted requested metric, decade, W-L, games,
    win pct, season range, and season type.
  - The primary display must make the decade and requested metric obvious
    without opening raw JSON.
- **Follow-up:** historical record display work is tracked in
  `result_display_followup_queue.md`.

### `matchup_by_decade` `[~]`
- **Pattern:** `FallbackTableResult`
- **Example queries:**
  - `Lakers vs Celtics by decade`
- **Currently shows (deployed 2026-05-04):**
  - The route returns `summary` and `comparison` sections, then falls
    through to `FallbackTableResult`.
- **Should show:**
  - Historical matchup display grouped by decade.
  - Team A vs Team B identity header, overall matchup record, covered season
    range, and a dense decade-by-decade comparison table with each team's
    wins, games, win pct, and average points when available.
  - Raw sections remain available behind the shared collapsed raw-table
    toggle when they add debug/detail value.
- **Follow-up:** historical matchup display work is tracked in
  `result_display_followup_queue.md`.

### Playoff routes `[x]`
- **Pattern:** `PlayoffHistoryResult` / `LeaderboardResult`
- **Routes:** `playoff_appearances`, `playoff_history`, `playoff_matchup_history`, `playoff_round_record`
- **Example queries:**
  - `Lakers playoff history`
  - `knicks vs heat playoff history since 1999`
  - `most playoff appearances by team`
- **Currently shows (shipped):**
  - `PlayoffHistoryResult` and `LeaderboardResult` route playoff responses to playoff-specific layouts with team identity, record/appearance/matchup context, season breakdown or series list when present, and collapsed playoff detail tables.
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
  default. They should render behind a consistent `Show raw table` / `Hide
  raw table` toggle so the clean display remains primary while the full
  underlying rows remain available for inspection, debugging, exports, or
  future advanced features.
- Identity treatment: every player row should show headshot if available,
  fall back to initials. Every team row should show logo if available,
  fall back to abbreviation badge.
- Mobile: every layout must work on a phone-sized viewport. Tables that
  need horizontal scroll should keep the identity column sticky.
- Numeric formatting: per-game averages to 1 decimal. Percentages as
  `xx.x%`, matching the shipped `DataTable`/stat formatting contract.
  Counts as integers.
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
