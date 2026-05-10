# Visual QA Notes

## Purpose

Living visual QA notes for the raw NBA query product.

This doc collects screenshot-review notes from the `/review` page after the result/table contract and leaderboard-column work.

Primary goals:

- Check whether result cards and tables look clean and readable.
- Identify visual density problems.
- Capture answer-contract issues that appear during visual review.
- Keep all screenshot QA notes in one place instead of scattering batch-specific docs.

## Review Context

Recent related work before this visual QA pass:

- Raw Query Product Map
- Core Result/Table Contract Lock Wave 1
- Core Result/Table Contract Lock Wave 2
- Weak Contract Cleanup Wave 1
- Leaderboard Supporting Columns Wave 1

## Running Issue Summary

| Priority | Area | Issue | Recommended Action | Source Batch |
|---|---|---|---|---|
| High | Entity Summary | Query asks for Denver record when Jokić has triple-double, but hero answers with Jokić season averages. | Investigate backend payload and hero selection for record-when player-condition summaries. | Batch 1 |
| Medium | Streak Table | Rightmost columns are clipped / table is too dense. | Reduce default visible columns or move secondary stats behind `Show additional columns`. | Batch 2 |
| Medium | Team Record | Single-row record table is too wide and clips the rightmost column at review width. | Reduce default visible columns or move lower-priority context fields behind additional columns. | Batch 3 |
| Low | Message No Result | Unsupported query displays `ERROR` severity. | Consider softer unsupported/no-result severity later. | Batch 1 |
| Low | Entity Summary + Recent Games | Average/Total footer can get cramped on dense tables. | Review table footer density during later visual polish. | Batch 1 |
| Low | Playoff Round Records | Hero uses `.667` while table uses `66.7%`. | Standardize hero to percentage formatting. | Batch 2 |
| Low | Playoff History / Matchup History | `Round unavailable` repeats heavily in historical playoff rows. | Consider shorter unavailable display later while keeping caveat. | Batch 2 / Batch 3 |
| Low | Comparison Panels | Record mini-card appears to duplicate wording like `win pct pct`. | Clean up comparison card record sublabel formatting. | Batch 3 |
| Low | Leaderboard Table | Some team/abbreviation text can truncate awkwardly in narrow cells, e.g. `P...`. | Review entity-cell width/abbreviation behavior during table polish. | Batch 4 |

---

# Batch 1

## Screenshots Reviewed

1. Guided No Result
2. Message No Result
3. Entity Summary
4. Entity Summary + Recent Games
5. Player Game Log

## Overall Batch Verdict

Most of Batch 1 looks visually solid. The dark-card layout, spacing, table styling, context blocks, and no-result states are generally working.

The main issue found in this batch is not a styling problem. It is a wrong-answer / wrong-hero issue in the Entity Summary shape.

## Screenshot Notes

### Player Game Log

Fixture:

- Shape: Player Game Log
- Query: `How often has Nikola Jokić recorded a triple-double this season?`
- Fixture ID shown: 71

Assessment:

- Looks good overall.
- The table is readable.
- The highlighted `PTS`, `REB`, and `AST` block works well for a triple-double query.
- `Show additional columns` makes sense here.
- The large row count is acceptable because the user asked a count/finder-style question and seeing every matching game builds trust.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Entity Summary + Recent Games

Fixture:

- Shape: Entity Summary + Recent Games
- Query: `How has Jayson Tatum played against good teams this season?`
- Fixture ID shown: 44

Assessment:

- Strong layout.
- The flow is good: context block, notes block, hero summary, supporting game table, average / total footer.
- The note wording is much better than the older technical phrasing:
  - `Advanced rate stats were recalculated using only this filtered sample.`
- The table is readable and useful.

Minor concern:

- The Average / Total footer can get visually cramped on the far right, especially with compact values like FG splits.

Status:

- `PASS / MINOR WATCH ITEM`

---

### Entity Summary

Fixture:

- Shape: Entity Summary
- Query: `What is Denver's record when Nikola Jokić has a triple-double?`
- Fixture ID shown: 83

Observed answer:

> Nikola Jokić has averaged 27.7 points, 12.9 rebounds and 10.7 assists in the 2025-26 regular season.

Problem:

This does not answer the user question.

The user asked for Denver's record when Jokić records a triple-double. The result card answers with Jokić's season averages instead.

Expected product behavior should be closer to:

> The Nuggets are X-Y when Nikola Jokić records a triple-double this season.

Possible root causes to investigate:

- Wrong hero template selected.
- Wrong route classification or route-to-result contract.
- Summary row contains the right record fields but `EntitySummaryResult` prioritizes player average fields.
- `player_game_summary` / `entity_summary` is being reused too generically for record-when queries.

Status:

- `FAIL / TARGETED BUG`

Recommended next action:

- Create a targeted investigation/fix for record-when player-condition summaries.
- Confirm the backend payload for this query includes record/team outcome fields.
- If the backend has the right fields, update the hero selection logic.
- If the backend does not include the right fields, fix the result builder/summary contract.

---

### Message No Result

Fixture:

- Shape: Message No Result
- Query: `Which scorers have cooled off over their last 10 games?`
- Fixture ID shown: 19

Assessment:

- Visually solid.
- The unsupported message is clearer than a generic error state.
- The text is understandable:
  - `I couldn't interpret "cooled off" as a supported stat query yet.`

Minor concern:

- The top badge says `ERROR`, while the body says `Unsupported Query`.
- This may feel harsher than necessary if the product simply does not support the query yet.

Status:

- `PASS / MINOR COPY-SEVERITY WATCH ITEM`

---

### Guided No Result

Fixture:

- Shape: Guided No Result
- Query: `Who scored the most points last night?`
- Fixture ID shown: 11

Assessment:

- Good no-result pattern.
- The structure is useful: no matching rows, suggested queries, why this happened, suggested next steps.
- The card provides enough explanation without feeling like a crash.

Status:

- `PASS / NO IMMEDIATE ACTION`

## Batch 1 Recommended Follow-Up

### Targeted Bug: Record-When Player Condition Hero

Investigate and fix the Entity Summary answer contract for queries like:

- `What is Denver's record when Nikola Jokić has a triple-double?`
- `What is the Knicks' record when Jalen Brunson doesn't play?`
- Similar team-record-with-player-condition summaries.

Do not redesign the Entity Summary shape broadly. First determine whether the backend payload already contains the required record fields and whether the issue is frontend hero priority or backend summary construction.

---

# Batch 2

## Screenshots Reviewed

1. Team Game Log
2. Game Summary Log
3. Streak Table
4. Playoff History
5. Playoff Round Records

## Overall Batch Verdict

Batch 2 is mostly strong. The game-log outputs and playoff-history outputs are readable and feel close to product-ready.

Main issues found:

1. `Streak Table` is horizontally cramped and rightmost columns are clipped.
2. `Playoff Round Records` hero uses `.667` while the table uses `66.7%`.
3. `Playoff History` repeats `Round unavailable` heavily, which is technically clear but visually repetitive.

## Screenshot Notes

### Team Game Log

Fixture:

- Shape: Team Game Log
- Query: `How often have the Lakers held opponents under 100 points this year?`
- Fixture ID shown: 76

Assessment:

- Looks good overall.
- The answer is direct and correct-looking:
  - `The Lakers have held opponents under 100 points 7 times this season, going 7-0.`
- The table columns are strong and trust-building: `Date`, `Team`, `Opp`, `Score`, `W/L`, `PTS`, `Opp PTS`, `Margin`, `REB`.
- Highlighting `Opp PTS` is appropriate for this query.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Game Summary Log

Fixture:

- Shape: Game Summary Log
- Query: `How do the Suns perform when Devin Booker didn't play?`
- Fixture ID shown: 51

Assessment:

- Very strong output.
- The structure works well: query/context card, direct hero answer, summary stat cards, supporting game table, average/total footer, detail toggles.
- The summary cards are useful: `GP`, `Record`, `PPG`, `RPG`, `APG`.
- The table is dense but still readable at this screenshot width.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Streak Table

Fixture:

- Shape: Streak Table
- Query: `Jokic 5 straight games with 20+ points`
- Fixture ID shown: 201

Assessment:

- Functionally strong.
- The hero answer is much better than earlier versions:
  - `Nikola Jokić has 15 streaks of 5+ straight games with 20+ points. The longest was 18 games, from Oct 26 to Dec 8, 2024.`
- Context and notes are clear.
- The issue is table density.

Problem:

- The table is too wide for the container.
- The rightmost columns are visibly clipped in the screenshot.
- The visible clipped area makes the table feel broken even though the underlying data appears fine.
- Rightmost stat columns such as `3P` / additional stats are cut off.

Status:

- `NEEDS VISUAL FIX`

Recommended fix direction:

- Reduce the default visible columns for `Streak Table`.
- Keep the trust-critical default columns: `#`, `Streak`, `Length`, `Start`, `End`, `Games`, `Record`, primary metric, e.g. `PTS`.
- Move lower-priority support stats behind `Show additional columns`, likely `REB`, `AST`, `MIN`, `3P`, `+/-`.
- Avoid relying only on horizontal clipping/overflow as the primary solution.

---

### Playoff History

Fixture:

- Shape: Playoff History
- Query: `Lakers playoff history`
- Fixture ID shown: 228

Assessment:

- Looks good overall.
- The hero answer is clean:
  - `From 1996-97 through 2024-25, the Lakers made the playoffs 21 times and went 165-115.`
- The context and caveat blocks are clear.
- The table is readable.
- The `Show postseason summary` button is clearer than a raw-table label.

Watch item:

- `Round unavailable` repeats heavily.
- This is accurate given the caveat, but visually it dominates the table.

Status:

- `PASS / WATCH ITEM`

Potential future improvement:

- Consider a shorter display for unavailable round values, such as `—` or `Unavailable`.
- Keep the caveat explaining the actual data limitation.

---

### Playoff Round Records

Fixture:

- Shape: Playoff Round Records
- Query: `best finals record since 1980`
- Fixture ID shown: 234

Assessment:

- Looks good overall.
- The table is strong: `#`, `Team`, `Round`, `Record`, `Games`, `Win Pct`, `Seasons`.
- Context, caveats, and highlighted metric are clear.

Minor copy/formatting issue:

- Hero uses `.667`:
  - `going 10-5 (.667) across 15 games.`
- Table uses `66.7%`.
- These are mathematically equivalent, but mixed formatting feels inconsistent.

Status:

- `PASS / MINOR COPY FIX`

Recommended copy fix:

- Standardize hero to percentage format, matching the table:
  - `The Indiana Pacers have the best Finals record since 1980, going 10-5, a 66.7% win rate, across 15 games.`

## Batch 2 Recommended Follow-Up

### Targeted Visual Fix: Streak Table Default Columns

Do not redesign the streak result broadly.

Investigate `StreakResult` / streak table column selection and adjust default visible columns so the table does not clip at standard review width.

Recommended default column set:

- `#`
- `Streak`
- `Length`
- `Start`
- `End`
- `Games`
- `Record`
- primary metric, e.g. `PTS`

Secondary columns should be moved behind `Show additional columns` unless a query specifically needs them visible.

Secondary candidates:

- `REB`
- `AST`
- `MIN`
- `3P`
- `+/-`

### Secondary Polish Items

- Standardize playoff round record hero percentage formatting.
- Consider shorter display for unavailable playoff round values in historical tables.

---

# Batch 3

## Screenshots Reviewed

1. Playoff Matchup History
2. Comparison Panels
3. Team Record
4. Record By Decade
5. Record By Decade Leaderboard

## Overall Batch Verdict

Batch 3 is visually strong overall. The record-by-decade and matchup/comparison layouts are in good shape. The main issue is a table-density problem in the Team Record shape, where a single-row table is still wide enough to clip at the right edge.

Main issues found:

1. `Team Record` table is too wide and clips the rightmost column at review width.
2. `Comparison Panels` record mini-card appears to duplicate wording like `win pct pct`.
3. `Playoff Matchup History` repeats `Round unavailable`, same historical-data watch item as Playoff History.

## Screenshot Notes

### Playoff Matchup History

Fixture:

- Shape: Playoff Matchup History
- Query: `Heat vs Knicks playoff history`
- Fixture ID shown: 229

Assessment:

- Looks good overall.
- The hero answer is strong:
  - `The Heat lead the Knicks 19-16 in playoff games. Their playoff series record is tied 3-3.`
- The table columns are useful and readable: `Season`, `Round`, `Winner`, `Series Result`, team records, `Games`.
- Context and caveats are clear.
- The `Show postseason summary` button is clearer than a raw-table label.

Watch item:

- `Round unavailable` repeats in several rows.
- This is acceptable because the caveat explains it, but the repeated text visually weighs down historical tables.

Status:

- `PASS / WATCH ITEM`

Potential future improvement:

- Use a shorter unavailable marker in the row itself while keeping the caveat explanatory.

---

### Comparison Panels

Fixture:

- Shape: Comparison Panels
- Query: `Jokic vs Embiid recent form`
- Fixture ID shown: 239

Assessment:

- Looks good overall.
- The hero sentence directly explains the comparison.
- Subject cards work well and create a good side-by-side comparison.
- The metric comparison table is readable.
- `Show more metrics` is a good control and keeps the default table from being too tall.

Minor issue:

- The Record mini-card appears to display duplicated wording such as:
  - `100.0% win pct pct`
- This is likely a small label/suffix formatting issue.

Status:

- `PASS / MINOR LABEL FIX`

Recommended fix:

- Clean up record-card sublabel formatting so it does not duplicate `pct`.

---

### Team Record

Fixture:

- Shape: Team Record
- Query: `What is the Celtics' record against playoff teams?`
- Fixture ID shown: 45

Assessment:

- The hero answer is good:
  - `The Boston Celtics are 6-5 against 2024-25 playoff teams, a 54.5% win rate.`
- The context block is clear and useful.
- The table content is useful, but the table is too wide.

Problem:

- The right edge of the single-row table is clipped at review width.
- The final visible header appears cut off as `ST...` or similar.
- This makes the result feel less polished even though the result itself is useful.

Possible cause:

- The default visible columns include too many fields for a single-summary record table:
  - `Team`
  - `W-L`
  - `Games`
  - `Win %`
  - `PPG`
  - `+/-`
  - `REB`
  - `AST`
  - `3PM`
  - `Opponent Group`
  - likely season/status context at the far right

Status:

- `NEEDS VISUAL FIX`

Recommended fix direction:

- Reduce default visible columns for `Team Record` single-summary tables.
- Keep trust-critical default columns:
  - `Team`
  - `W-L`
  - `Games`
  - `Win %`
  - `PPG`
  - `+/-`
  - `Opponent Group`, when the query is opponent-group based
- Move lower-priority support stats behind `Show additional columns`, likely:
  - `REB`
  - `AST`
  - `3PM`
  - season/status fields if already present in chips/context

Priority:

- Medium.

---

### Record By Decade

Fixture:

- Shape: Record By Decade
- Query: `Warriors record by decade`
- Fixture ID shown: 236

Assessment:

- Looks good overall.
- The hero answer is clean:
  - `The Golden State Warriors are 1,176-1,209 (49.3%) in the regular season from 1996-97 to 2025-26.`
- The decade table is readable and not too dense.
- The highlighted `Win %` column works well.
- The `Show record details` button is clearer than a raw-table label.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Record By Decade Leaderboard

Fixture:

- Shape: Record By Decade Leaderboard
- Query: `winningest team of the 2010s`
- Fixture ID shown: 237

Assessment:

- Looks good overall.
- The hero answer is direct:
  - `The San Antonio Spurs won the most games in the 2010s, with 541 wins.`
- The leaderboard columns are strong and well-balanced:
  - `#`
  - `Team`
  - `Decade`
  - `Wins`
  - `W-L`
  - `Games`
  - `Win %`
  - `Seasons`
  - `Season Type`
- No obvious clipping at review width.
- The route-specific leaderboard column work appears to have helped here.

Status:

- `PASS / NO IMMEDIATE ACTION`

## Batch 3 Recommended Follow-Up

### Targeted Visual Fix: Team Record Default Columns

Investigate `RecordResult` / `TeamRecord` table column selection and reduce default visible columns for single-summary team record tables.

Recommended default column set:

- `Team`
- `W-L`
- `Games`
- `Win %`
- `PPG`
- `+/-`
- condition/context column when directly relevant, e.g. `Opponent Group`

Secondary candidates to move behind `Show additional columns`:

- `REB`
- `AST`
- `3PM`
- season/status context already visible in chips/context

### Secondary Polish Items

- Clean up duplicate `pct` wording in Comparison Panels record-card sublabels.
- Consider shorter unavailable round display for Playoff Matchup History rows.

---

# Batch 4

## Screenshots Reviewed

1. Matchup By Decade
2. Leaderboard Table
3. Top Performances
4. Rolling Stretch

## Overall Batch Verdict

Batch 4 is strong overall. The core leaderboard, top-performance, rolling-stretch, and matchup-by-decade outputs look clean and readable at review width. The leaderboard-supporting-column work appears to have improved consistency without making the default leaderboard too crowded.

Main issue found:

1. `Leaderboard Table` has a minor entity-cell truncation issue for some team abbreviations/text, visible as `P...` in the table.

## Screenshot Notes

### Matchup By Decade

Fixture:

- Shape: Matchup By Decade
- Query: `Lakers vs Celtics by decade`
- Fixture ID shown: 238

Assessment:

- Looks good overall.
- The hero answer is clear:
  - `The Los Angeles Lakers lead the Boston Celtics 31-27 in regular-season games from 1996-97 through 2025-26.`
- The context card is clean.
- The table is compact and readable.
- The columns are well chosen:
  - `Decade`
  - `Games`
  - `LAL W-L`
  - `LAL Win %`
  - `BOS W-L`
  - `BOS Win %`
- The `Show matchup summary` button is clear.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Leaderboard Table

Fixture:

- Shape: Leaderboard Table
- Query: `Who leads the NBA in points per game this season?`
- Fixture ID shown: 1

Assessment:

- Looks good overall.
- The hero answer is direct:
  - `Luka Dončić led the NBA with 33.5 PPG in the 2025-26 regular season.`
- The route-specific supporting columns are useful and not too crowded:
  - `Season`
  - `TM`
  - `GP`
  - `Type`
- The primary metric highlight works well.
- The table feels cleaner than earlier dynamic-column versions.

Minor issue:

- Some team/entity text can truncate awkwardly in narrow cells, visible as `P...` for Philadelphia rows.
- Since the team badge already shows `PHI`, the extra truncated text may not add much value.

Status:

- `PASS / MINOR ENTITY-CELL POLISH`

Potential future improvement:

- For team abbreviation cells, avoid duplicating the abbreviation after the badge if it risks truncation.
- Or give the abbreviation/text cell enough width to avoid awkward `P...` display.

---

### Top Performances

Fixture:

- Shape: Top Performances
- Query: `What were the biggest scoring games this season?`
- Fixture ID shown: 31

Assessment:

- Looks good overall.
- The hero answer is direct and useful:
  - `Bam Adebayo had the top scoring game this season with 83 points in a win against Washington Wizards on Mar 10.`
- The note is clean:
  - `Showing league-wide single-game scoring performances.`
- The table columns are well balanced:
  - `Rank`
  - `Player`
  - `Date`
  - `Opp`
  - `Result`
  - `PTS`
  - `REB`
  - `AST`
  - `3PM`
- Highlighting `PTS` is appropriate.
- No obvious clipping.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### Rolling Stretch

Fixture:

- Shape: Rolling Stretch
- Query: `Which players have the hottest 3-game scoring stretch this year?`
- Fixture ID shown: 36

Assessment:

- Looks good overall.
- The hero answer is clear:
  - `Luka Dončić had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.`
- The table is compact and readable.
- The columns are well chosen:
  - `Rank`
  - `Player`
  - `Window`
  - primary metric, e.g. `PPG`
  - `Start`
  - `End`
  - `Season`
- Highlighting the primary metric works well.

Status:

- `PASS / NO IMMEDIATE ACTION`

## Batch 4 Recommended Follow-Up

No new high-priority fixes from this batch.

### Minor Entity-Cell Polish

For generic leaderboard tables, consider cleaning up team abbreviation display so rows do not show awkward truncated text like `P...` after a badge that already contains the abbreviation.

This is lower priority than the already-captured medium-priority table-density issues:

1. Streak Table default columns.
2. Team Record default columns.
