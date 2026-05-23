# Result Display Lock-In Implementation Spec

> Status: synthesized implementation spec from the 19-family screenshot review.
>
> Source decision logs:
>
> - `../result_display_family_review_lock_in.md` — Families 1–15 and global rules G1–G20
> - `../result_display_family_review_lock_in_batch_6_addendum.md` — Families 16–19 and global rules G21–G24
>
> Purpose: turn the screenshot-review decision logs into one implementation-ready source of truth for result display UI, copy, table behavior, no-result behavior, and validation.

---

## 0. Non-negotiable implementation principles

### P1 — Implement by display family/pattern, not one route at a time

There are hundreds of query fixtures, but the visible outputs collapse into 19 reviewed display families. Do not build bespoke UI for every query route unless a route truly cannot fit a shared family pattern.

### P2 — The visible answer must be the useful answer

The user should not need to open raw/detail tables to get the core answer. Raw/detail toggles are allowed only when they expose additional fields not already present in the answer table, or when they are intentionally debug-only.

### P3 — Hero sentence comes first and must preserve intent

Every successful result should lead with a clear sentence that answers the user’s actual query. It must preserve the query’s filters and basketball meaning exactly.

Bad example:

```txt
The Celtics are 6-5 in the 2024-25 playoffs.
```

For query:

```txt
What is the Celtics' record against playoff teams?
```

Good example:

```txt
The Celtics are 6-5 against playoff teams in 2024-25, a 54.5% win rate.
```

### P4 — Context is not caveat

Use `Context` / `Interpreted as` for normal query interpretation:

- date range
- season range
- opponent group
- metric
- qualified players
- aggregation method
- matchup pair
- filter expansion

Use `Caveat` only for actual limitations:

- missing data
- approximation
- unavailable columns
- degraded/partial answer
- ambiguity the system could not resolve

### P5 — Dense tables are good when engineered correctly

The review confirmed dense tables are the strongest pattern for most stat outputs. Do not replace them with card spam. Instead, fix table sizing, column presets, row limits, highlights, and footer logic.

### P6 — Parser/debug chrome is not product UI

Parser review pages may show route names, fixture IDs, query class, status chips, and debug metadata. User-facing output should hide those details by default.

---

## 1. Shared global rules to implement

### 1.1 Context / caveat separation

Create or adjust the display logic so normal query interpretation is rendered as Context, not Caveats.

Required labels:

- `Context`
- `Interpreted as`
- `Filter`
- `Data note` / `Caveat` only for actual limitation

Acceptance criteria:

- No yellow/error-style caveat box for ordinary date ranges, opponent groups, metric names, or aggregation descriptions.
- Data limitations like unavailable playoff round data remain caveats.

### 1.2 Raw/detail toggle suppression

Raw/detail toggles should be hidden when they duplicate the visible answer table.

Acceptance criteria:

- If `Game Detail`, `Player Game Detail`, `Season Breakdown Detail`, `Record Detail`, etc. contain the same row set and fields already visible, hide the toggle.
- If extra non-visible fields exist, use `Show additional columns` instead of `Show raw table` when appropriate.
- Debug/parser mode may still expose raw tables if useful.

### 1.3 Shared table engineering

Dense answer tables must remain readable.

Acceptance criteria:

- Wide tables scroll horizontally rather than crushing values.
- Identity/date columns have readable minimum widths.
- Numeric columns have consistent minimum widths.
- Team/player names and abbreviations should not truncate awkwardly.
- Important semantic columns should not wrap into unreadable fragments.

### 1.4 Metric highlight mapping

The queried metric should be visually emphasized.

Examples:

- scoring leaders → PPG / PTS
- winningest → Wins
- best record → Win %
- opponents under 100 → Opp PTS
- streaks → Length
- rolling stretch → PPG / queried metric

### 1.5 Row limits and show-all behavior

For game logs and long answer tables:

- 0–12 rows: show all rows.
- 13+ rows: product UI should show a capped view with `Show all {N}` or a fixed-height scrollable viewport.
- Preferred default: show first 12 rows plus `Show all {N} games`.
- Parser review pages may show all rows if helpful for fixture QA.

### 1.6 Footer rows

Average/Total footers are good but need column-specific behavior.

Acceptance criteria:

- Average footer: per-game averages for core numeric columns.
- Total footer: simple counting totals.
- Shooting totals: show only when readable; otherwise omit or move to an additional detail section.

### 1.7 Missing data labels

Do not use unexplained `—` in important semantic columns.

Use:

- `Unavailable`
- `Unknown`
- `Not available`
- `Round unavailable`

Especially for playoff round/result columns.

### 1.8 Comparison edge direction metadata

Comparison edge logic must know whether higher, lower, or neutral is better.

Examples:

- Higher better: PTS, REB, AST, STL, BLK, FG%, TS%, +/-, wins
- Lower better: losses, TOV depending context
- Neutral/contextual: games, MIN, USG%

Acceptance criteria:

- Do not render bad copy like `Jokić +3 losses` when he has fewer losses.
- Use `Difference` for neutral metrics rather than `Edge`.
- Win percentage differences should use readable copy, e.g. `+30.0 percentage points`.

---

## 2. Family lock-in specs

## Family 1 — Entity Summary

Pattern: sentence hero, with game-log table when the summary is based on a filtered game subset.

Example reviewed: `How has Jayson Tatum played against good teams this season?`

Required behavior:

- Hero sentence must include meaningful filters like `against good teams`.
- Include sample size when available.
- If the result summarizes a filtered set of games, include the matching game-log answer table unless the route explicitly opts out as summary-only.
- Normal filter explanations belong in Context, not Caveats.

Good hero:

```txt
Jayson Tatum has averaged 23.0 points, 9.5 rebounds and 5.5 assists in 12 games against good teams this season.
```

Likely files:

- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- summary/context builders

---

## Family 2 — Message No Result

Pattern: hard unsupported no-result.

Required behavior:

- Use only for truly unsupported cases with no safe obvious recovery path.
- Do not expose backend column names in primary copy.
- Technical details can remain in debug/details mode.

Bad copy:

```txt
Column 'def_rating' not available
```

Good copy:

```txt
Defensive rating is not available in the current dataset.
```

If nearby alternatives exist, prefer Guided No Result instead.

Likely files:

- `NoResultDisplay`
- no-result reason/copy mapping
- recovery suggestion generation

---

## Family 3 — Guided No Result

Pattern: valid query, empty result, with explanation and suggested next steps.

Required behavior:

- Explain the specific failed filter/date/range.
- Use readable dates instead of raw ISO ranges.
- Suggestions should be query-specific when possible.

Good example:

```txt
No NBA games matched Apr 11, 2026.
```

Contextual suggestions:

- previous NBA game day
- next NBA game day
- scoring leaders this season
- nearby supported metrics

Likely files:

- `NoResultDisplay`
- date/range formatter
- recovery suggestion generation

---

## Family 4 — Entity Summary + Recent Games

Pattern: sentence hero + dense player game-log table + Average/Total footer.

Example reviewed: `Luka last 5`

Required player game-log columns:

```txt
#, Date, TM, Opp, W/L, MIN, PTS, REB, AST, FG, 3P, FT, STL, BLK, TOV, +/-
```

Optional:

```txt
Score, home/away marker, TS%, eFG%
```

Acceptance criteria:

- Show all requested rows for last-N queries.
- Keep Average and Total footer rows.
- Do not hide the game log behind raw table.

Likely files:

- `EntitySummaryResult.tsx`
- `GameLogResult.tsx`
- game-log column presets
- footer generation

---

## Family 5 — Player Game Log

Pattern: count/condition hero + dense player game-log table.

Example reviewed: `How often has Nikola Jokić recorded a triple-double this season?`

Required behavior:

- Hero should include count.
- Visible table should list matching games.
- Large logs need show-all/capped behavior.
- Full player box-score columns should include FG and FT when available.

Required columns:

```txt
#, Date, TM, Opp, W/L, MIN, PTS, REB, AST, FG, 3P, FT, STL, BLK, TOV, +/-
```

Likely files:

- `GameLogResult.tsx`
- game-log row limit/show-all behavior
- raw/detail toggle visibility rules

---

## Family 6 — Team Game Log

Pattern: count/record hero + dense team-first game-log table.

Example reviewed: `How often have the Lakers held opponents under 100 points this year?`

Required behavior:

- Hero should include count and record when available.
- Table must surface and emphasize the condition column.
- For `opponents under 100`, add/highlight `Opp PTS`.

Required columns:

```txt
#, Date, Team, Opp, Score, W/L, PTS, Opp PTS, Margin, REB, AST, 3PM, FG, 3P, FT, TOV
```

Optional:

```txt
STL, BLK, ORB, DRB
```

Likely files:

- `GameLogResult.tsx`
- team game-log column presets
- condition-column detection/highlighting

---

## Family 7 — Game Summary Log

Pattern: hero sentence + compact summary strip + dense team game-log table.

Example reviewed: `How do the Suns perform when Devin Booker didn't play?`

Required behavior:

- Keep compact summary strip.
- Summary strip should include record, not only GP/PTS/REB/AST.

Preferred strip:

```txt
GP 18 | Record 8-10 | PPG 103.8 | RPG 43.1 | APG 21.7
```

Required columns: same as Team Game Log.

Footer behavior must follow global footer rules.

Likely files:

- `GameLogResult.tsx`
- summary strip primitive
- footer generation
- table sizing CSS

---

## Family 8 — Streak Table

Pattern: threshold-aware hero + ranked streak table.

Example reviewed: `Jokic 5 straight games with 20+ points`

Required behavior:

- Hero must clarify whether query means at least 5, exactly 5, or longest streak of 5+.
- Highlight `Length`.
- Show Status only if active/current/mixed statuses exist.

Required columns:

```txt
#, Streak/Condition, Length, Start, End, Games, Record, PTS, REB, AST
```

Optional:

```txt
Status, MIN, 3PM, +/-, FG, 3P, FT
```

Likely files:

- `StreakResult.tsx`
- streak sentence builder
- threshold metadata mapping
- streak table config

---

## Family 9 — Playoff History

Pattern: historical hero + season-by-season playoff table.

Required hero:

```txt
From {start_season} through {end_season}, the {team} made the playoffs {appearances} times and went {wins}-{losses}.
```

Optional:

```txt
They reached the Finals {finals_count} times and won {titles} titles.
```

Required columns:

```txt
Season, Result/Round Reached, Record, Win Pct, Games
```

Optional:

```txt
Opponent, Series Result, Seed, Coach
```

Required caveat copy when applicable:

```txt
Round-level data is unavailable before 2001-02, so those seasons are included in totals but not round breakdowns.
```

Likely files:

- `PlayoffHistoryResult.tsx`
- playoff hero builder
- round/result label mapping
- caveat/context copy mapping

---

## Family 10 — Playoff Round Records

Pattern: ranking hero + dense ranked playoff table.

Example reviewed: `best finals record since 1980`

Good hero:

```txt
The Indiana Pacers have the best Finals record since 1980, going 10-5 (.667) across 15 games.
```

Required columns:

```txt
#, Team, Round, Record, Games, Win Pct
```

Optional:

```txt
Seasons, Series, Titles/Wins if available
```

Highlight rules:

- best record → Win Pct
- most wins → Wins
- most games → Games

Likely files:

- `PlayoffHistoryResult.tsx`
- `LeaderboardResult.tsx` if shared
- playoff leaderboard config

---

## Family 11 — Playoff Matchup History

Pattern: matchup hero + explicit series-result table.

Required behavior:

- Hero must clarify whether record is games or series.
- Table must show winner/result directly.
- Users should not infer winners by comparing mirrored records.

Required columns:

```txt
Season, Round, Winner, Series Result
```

Optional:

```txt
Team A Record, Team B Record, Games
```

Good values:

```txt
Heat won 4-3
Knicks won 3-2
```

Likely files:

- `PlayoffHistoryResult.tsx`
- playoff matchup table config
- winner/result derivation

---

## Family 12 — Comparison Panels

Pattern: intent-aware hero + compact subject summaries + focused metric comparison table.

Required behavior:

- Rebuild/simplify from large duplicated panels.
- Hero must match query intent.
- Recent form should lead with performance averages/context, not wins unless asked.
- Default metric table should show about 8–12 core rows.
- Deeper metrics go behind `Show more metrics`.

Default player comparison rows:

```txt
Games, Record, PTS, REB, AST, MIN, FG%, 3P%, FT%, STL, BLK, TOV, +/-, TS%/eFG% if available
```

Likely files:

- `ComparisonResult.tsx`
- comparison hero builder
- metric direction metadata
- show-more metric grouping

---

## Family 13 — Team Record

Pattern: intent-accurate hero + one-row record table.

Example reviewed: `What is the Celtics' record against playoff teams?`

Required behavior:

- Preserve filter meaning exactly.
- Do not say `in the playoffs` for `against playoff teams`.
- `Type` must describe actual game population, not opponent group.

Required columns:

```txt
Team, W-L, Games, Win %, PPG, +/-, REB, AST, 3PM
```

Optional:

```txt
Season Type, Opponent Group, Season, Home/Away, Opponent
```

Likely files:

- `RecordResult.tsx`
- team record hero builder
- season type vs opponent group labeling

---

## Family 14 — Record By Decade

Pattern: team hero + decade breakdown table.

Required columns:

```txt
Decade, Seasons, W-L, Win %, Games
```

Optional:

```txt
Wins, Losses, Type
```

Highlight rules:

- record by decade → Win % acceptable
- most wins by decade → Wins
- best decade → Win %
- worst decade → Win % ascending or Losses depending query

Likely files:

- `RecordResult.tsx`
- decade record table config
- metric highlight mapping

---

## Family 15 — Record By Decade Leaderboard

Pattern: leaderboard hero + dense ranked table with queried metric highlighted.

Required columns:

```txt
#, Team, Decade, Queried Metric, W-L, Games, Win %, Seasons, Type
```

Highlight rules:

- winningest → Wins
- best record → Win %
- most losses → Losses

Likely files:

- `LeaderboardResult.tsx`
- decade leaderboard config
- metric highlight mapping

---

## Family 16 — Matchup By Decade

Pattern: two-team hero + decade-by-decade matchup table.

Good hero:

```txt
The Lakers lead the Celtics 31-27 in regular-season games from 1996-97 through 2025-26.
```

Required columns:

```txt
Decade, Games, Team A W-L, Team A Win %, Team B W-L, Team B Win %
```

Acceptance criteria:

- Add total Games per decade.
- Matchup/range interpretation belongs in Context, not Caveats.

Likely files:

- `ComparisonResult.tsx`
- matchup-by-decade table config
- matchup hero builder

---

## Family 17 — Leaderboard Table

Pattern: core generic leaderboard pattern.

Good hero:

```txt
Luka Dončić led the NBA with 33.5 PPG in the 2025-26 regular season.
```

Required columns:

```txt
#, Player/Team, Queried Metric, Season, Team, GP/Sample, Type
```

Optional context:

```txt
qualified players only, minimum games/minutes, regular season/playoffs
```

Acceptance criteria:

- This is the base pattern for generic player/team leaderboards.
- Queried metric is highlighted.
- Qualification/minimum context belongs in Context, not Caveats.

Likely files:

- `LeaderboardResult.tsx`
- leaderboard hero builder
- metric highlight mapping
- table sizing presets

---

## Family 18 — Top Performances

Pattern: top-performance hero + ranked single-game performance table.

Required behavior:

- Hero must include player, metric value, opponent, date, and result/score when available.

Good hero:

```txt
Bam Adebayo had the top scoring game this season, scoring 83 points against the Wizards on Mar 10.
```

Required columns:

```txt
Rank, Player, Date, Opp, Result, Queried Metric, REB, AST, 3PM
```

Metric-specific support columns:

- scoring query → PTS, REB, AST, 3PM
- rebounds query → PTS, REB, AST
- assists query → PTS, REB, AST, TOV
- 3PM query → PTS, 3PM, 3PA if available

Optional:

```txt
Score
```

Likely files:

- `LeaderboardResult.tsx`
- top-game/performance column presets
- top-performance hero builder

---

## Family 19 — Rolling Stretch

Pattern: stretch hero + ranked rolling-window table.

Required columns:

```txt
Rank, Player, Window, Queried Metric, Start, End, Season
```

Optional:

```txt
Team, Games, Opponents, Record, PTS total
```

Deduplication rules:

- `which players` → one best window per player
- `best stretches` / `best windows` → allow multiple windows, including same player
- named-player query → show that player's windows

Hero should clarify player-oriented vs window-oriented ranking.

Player-oriented:

```txt
Luka Dončić had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.
```

Window-oriented:

```txt
Best 3-game scoring stretch this season: Luka Dončić averaged 45.3 PPG from Mar 16 to Mar 19.
```

Likely files:

- `LeaderboardResult.tsx`
- rolling stretch table config
- rolling stretch hero builder
- deduplication mode selection

---

## 3. Implementation waves

### Wave 0 — Preflight only

Goal: inspect current code and map exact files/functions to this spec. No code changes.

Deliverable:

```txt
docs/planning/result-display-lock-in/result_display_preflight_findings.md
```

Questions to answer:

- Which components render each family?
- Where are hero sentences built?
- Where are caveats/context built?
- Where are raw/detail toggles rendered?
- Where are table columns configured?
- Where are metric labels/highlights handled?
- Where can row caps/show-more be added?
- Where can rolling-stretch dedupe happen?
- Which fixtures should be regenerated after each wave?

### Wave 1 — Shared display rules

Implement cross-cutting rules first:

- context vs caveat separation
- raw/detail duplicate suppression
- shared table width/min-width rules
- metric highlight mapping
- readable date/range formatting
- no unexplained dashes in semantic columns
- no developer copy in no-result cards

### Wave 2 — Core leaderboard patterns

Implement and verify:

- Leaderboard Table
- Top Performances
- Rolling Stretch
- Record By Decade Leaderboard
- Playoff Round Records

### Wave 3 — Game logs and entity summaries

Implement and verify:

- Entity Summary
- Entity Summary + Recent Games
- Player Game Log
- Team Game Log
- Game Summary Log

### Wave 4 — Records, comparisons, playoff history

Implement and verify:

- Team Record
- Record By Decade
- Matchup By Decade
- Comparison Panels
- Playoff History
- Playoff Matchup History

### Wave 5 — No-result behavior

Implement and verify:

- Message No Result
- Guided No Result

---

## 4. Validation requirements

Each implementation wave must return:

- changed files
- implementation summary
- fixture IDs reviewed
- screenshot paths or visual QA notes
- commands/tests run
- known limitations
- docs updated

Minimum targeted fixtures by family:

```txt
1, 11, 14, 31, 36, 44, 45, 51, 71, 76, 201, 229, 234, 236, 237, 238, 239, 247
```

Use the reviewed family screenshots as visual targets. Passing tests alone is not enough.

---

## 5. Open questions to resolve during preflight or implementation

1. Should parser review pages keep the current large debug/context card exactly, or should parser/debug chrome be visually separated from product-output screenshots?
2. Should `EntitySummaryResult` always compose with `GameLogResult` when a `game_log` section exists, or only for specific routes/metadata flags?
3. Should `good teams` expansion list show all teams behind a detail disclosure, or only summarize as `19 opponents` in primary context?
4. For large game logs, should final product UI use `Show first 12 + Show all` or fixed-height scrollable table viewport?
5. Should duplicated answer-table raw toggles be removed entirely or replaced with `Show additional columns` when extra fields exist?
6. For shooting columns in footer rows, should totals be omitted by default or moved to additional shooting-summary detail?
7. For streak queries, can metadata distinguish exact streak length from minimum streak length?
8. For playoff matchup history, should the hero prefer game record, series record, or show both when both are available?
9. For comparison tables, should the default primary metric cutoff be 8, 10, or 12 rows?
10. For `record against playoff teams`, should the visible table include both `Season Type` and `Opponent Group` whenever both concepts are present?
11. For Top Performances, should `Score` become required when available or remain optional?
12. For Rolling Stretch, can parser/response metadata distinguish `which players` from `best windows/stretches`, or does frontend need to infer from query text/route metadata?
13. Should all leaderboard-ish families share one column-sizing primitive/preset system?

---

## 6. Recommended defaults unless preflight finds blockers

- Use `Show first 12 + Show all` for long game logs.
- Remove duplicate raw/detail toggles entirely unless extra fields exist.
- Summarize long filter expansions in primary context and put full lists behind details.
- Use 10–12 primary comparison rows by default, with `Show more metrics` for deeper rows.
- Show both game and series record for playoff matchup history when both are available.
- Keep `Score` optional for Top Performances, but render it when available.
- Prefer backend/query metadata for rolling-stretch dedupe mode; fallback to frontend route/query-intent inference.
- Use shared table column-sizing presets for all leaderboard-ish families.

---

## 7. Definition of done

This effort is done when:

- All 19 families have an intentional locked display pattern.
- The visible output contains the useful answer without relying on raw table toggles.
- Normal context is no longer shown as caveats.
- Hero copy preserves query intent and basketball meaning.
- Game logs, leaderboards, comparisons, records, playoff history, and no-results pass targeted fixture visual review.
- New behavior is documented in this folder or follow-up implementation notes.
