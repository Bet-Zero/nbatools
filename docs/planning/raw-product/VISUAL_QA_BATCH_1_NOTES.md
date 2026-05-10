# Visual QA Batch 1 Notes

## Context

Visual QA pass after the Leaderboard Supporting Columns Wave 1 implementation.

Batch 1 screenshots reviewed:

1. Guided No Result
2. Message No Result
3. Entity Summary
4. Entity Summary + Recent Games
5. Player Game Log

Primary goal of this pass:

- Check whether the current result cards and tables look clean and readable.
- Identify visual density problems after the recent result/table work.
- Capture any answer-contract issues that show up visually.

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

## Batch 1 Issues Captured

| Priority | Area | Issue | Recommended Action |
|---|---|---|---|
| High | Entity Summary | Query asks for Denver record when Jokić has triple-double, but hero answers with Jokić season averages. | Investigate backend payload and hero selection for record-when player-condition summaries. |
| Low | Message No Result | Unsupported query displays `ERROR` severity. | Consider softer unsupported/no-result severity later. |
| Low | Entity Summary + Recent Games | Average/Total footer can get cramped on dense tables. | Review table footer density during later visual polish. |

## Recommended Follow-Up

The next implementation target from this batch should be narrow:

### Targeted Bug: Record-When Player Condition Hero

Investigate and fix the Entity Summary answer contract for queries like:

- `What is Denver's record when Nikola Jokić has a triple-double?`
- `What is the Knicks' record when Jalen Brunson doesn't play?`
- Similar team-record-with-player-condition summaries.

Do not redesign the Entity Summary shape broadly. First determine whether the backend payload already contains the required record fields and whether the issue is frontend hero priority or backend summary construction.
