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
| Low | Message No Result | Unsupported query displays `ERROR` severity. | Consider softer unsupported/no-result severity later. | Batch 1 |
| Low | Entity Summary + Recent Games | Average/Total footer can get cramped on dense tables. | Review table footer density during later visual polish. | Batch 1 |
| Low | Playoff Round Records | Hero uses `.667` while table uses `66.7%`. | Standardize hero to percentage formatting. | Batch 2 |
| Low | Playoff History | `Round unavailable` repeats heavily. | Consider shorter unavailable display later while keeping caveat. | Batch 2 |

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

### 1. Player Game Log

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

Notes:

- No immediate visual action required.
- Keep an eye on very tall game-log outputs, but this is acceptable for now.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### 2. Entity Summary + Recent Games

Fixture:

- Shape: Entity Summary + Recent Games
- Query: `How has Jayson Tatum played against good teams this season?`
- Fixture ID shown: 44

Assessment:

- Strong layout.
- The flow is good:
  - context block
  - notes block
  - hero summary
  - supporting game table
  - average / total footer
- The note wording is much better than the older technical phrasing:
  - `Advanced rate stats were recalculated using only this filtered sample.`
- The table is readable and useful.

Minor concern:

- The Average / Total footer can get visually cramped on the far right, especially with compact values like FG splits.

Status:

- `PASS / MINOR WATCH ITEM`

Potential future improvement:

- Review footer alignment and density for tables with many stat columns.

---

### 3. Entity Summary

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

Priority:

- High.

Status:

- `FAIL / TARGETED BUG`

Recommended next action:

- Create a targeted investigation/fix for record-when player-condition summaries.
- Confirm the backend payload for this query includes record/team outcome fields.
- If the backend has the right fields, update the hero selection logic.
- If the backend does not include the right fields, fix the result builder/summary contract.

---

### 4. Message No Result

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

Potential future improvement:

- Consider using a softer status label such as `UNSUPPORTED` or `NO RESULT` instead of `ERROR` for intentional unsupported-query states.

---

### 5. Guided No Result

Fixture:

- Shape: Guided No Result
- Query: `Who scored the most points last night?`
- Fixture ID shown: 11

Assessment:

- Good no-result pattern.
- The structure is useful:
  - no matching rows
  - suggested queries
  - why this happened
  - suggested next steps
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

### 1. Team Game Log

Fixture:

- Shape: Team Game Log
- Query: `How often have the Lakers held opponents under 100 points this year?`
- Fixture ID shown: 76

Assessment:

- Looks good overall.
- The answer is direct and correct-looking:
  - `The Lakers have held opponents under 100 points 7 times this season, going 7-0.`
- The table columns are strong and trust-building:
  - `Date`
  - `Team`
  - `Opp`
  - `Score`
  - `W/L`
  - `PTS`
  - `Opp PTS`
  - `Margin`
  - `REB`
- Highlighting `Opp PTS` is appropriate for this query.

Status:

- `PASS / NO IMMEDIATE ACTION`

---

### 2. Game Summary Log

Fixture:

- Shape: Game Summary Log
- Query: `How do the Suns perform when Devin Booker didn't play?`
- Fixture ID shown: 51

Assessment:

- Very strong output.
- The structure works well:
  - query/context card
  - direct hero answer
  - summary stat cards
  - supporting game table
  - average/total footer
  - detail toggles
- The summary cards are useful:
  - `GP`
  - `Record`
  - `PPG`
  - `RPG`
  - `APG`
- The table is dense but still readable at this screenshot width.

Status:

- `PASS / NO IMMEDIATE ACTION`

Potential future watch item:

- Continue watching table density when several stat columns and average/total footer rows are present.

---

### 3. Streak Table

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

Observed problem area:

- Rightmost stat columns such as `3P` / additional stats are cut off.

Priority:

- Medium.

Status:

- `NEEDS VISUAL FIX`

Recommended fix direction:

- Reduce the default visible columns for `Streak Table`.
- Keep the trust-critical default columns:
  - `#`
  - `Streak`
  - `Length`
  - `Start`
  - `End`
  - `Games`
  - `Record`
  - primary metric, e.g. `PTS`
- Move lower-priority support stats behind `Show additional columns`, likely:
  - `REB`
  - `AST`
  - `MIN`
  - `3P`
  - `+/-`
- Avoid relying only on horizontal clipping/overflow as the primary solution.

---

### 4. Playoff History

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

- Consider a shorter display for unavailable round values, such as:
  - `—`
  - `Unavailable`
- Keep the caveat explaining the actual data limitation.

---

### 5. Playoff Round Records

Fixture:

- Shape: Playoff Round Records
- Query: `best finals record since 1980`
- Fixture ID shown: 234

Assessment:

- Looks good overall.
- The table is strong:
  - `#`
  - `Team`
  - `Round`
  - `Record`
  - `Games`
  - `Win Pct`
  - `Seasons`
- Context, caveats, and highlighted metric are clear.

Minor copy/formatting issue:

- Hero uses `.667`:
  - `going 10-5 (.667) across 15 games.`
- Table uses `66.7%`.
- These are mathematically equivalent, but mixed formatting feels inconsistent.

Priority:

- Low.

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
