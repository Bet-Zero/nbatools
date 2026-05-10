# Visual QA Batch 2 Notes

## Context

Visual QA pass after the Leaderboard Supporting Columns Wave 1 implementation.

Batch 2 screenshots reviewed:

1. Team Game Log
2. Game Summary Log
3. Streak Table
4. Playoff History
5. Playoff Round Records

Primary goal of this pass:

- Check whether game-log, streak, and playoff/history result patterns look clean and readable.
- Identify visual density problems.
- Capture copy/formatting inconsistencies.
- Capture any result/table issues before moving into targeted fixes.

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

## Batch 2 Issues Captured

| Priority | Area | Issue | Recommended Action |
|---|---|---|---|
| Medium | Streak Table | Rightmost columns are clipped / table is too dense. | Reduce default visible columns or move secondary stats behind `Show additional columns`. |
| Low | Playoff Round Records | Hero uses `.667` while table uses `66.7%`. | Standardize hero to percentage formatting. |
| Low | Playoff History | `Round unavailable` repeats heavily. | Consider shorter unavailable display later while keeping caveat. |

## Recommended Follow-Up

The next implementation target from this batch should be narrow:

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
