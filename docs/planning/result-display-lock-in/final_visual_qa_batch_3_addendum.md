# Result Display Lock-In — Final Visual QA Batch 3 Addendum

> Purpose: Batch 3 addendum for the final visual QA pass.
>
> Main running doc: `docs/planning/result-display-lock-in/final_visual_qa_notes.md`.
>
> Note: This addendum avoids rewriting the increasingly large main QA doc through the GitHub contents API. Final punch-list synthesis should read both files.

---

# Batch 3

Screenshots reviewed:

11. Comparison Panels
12. Team Record
13. Record By Decade
14. Record By Decade Leaderboard
15. Matchup By Decade

---

## Batch 3 verdict summary

| Screenshot / Family | Verdict | Priority |
|---|---|---|
| Comparison Panels | Pass with polish | Should fix |
| Team Record | Strong pass with table-width/detail-toggle cleanup | Should fix |
| Record By Decade | Pass with raw-toggle cleanup | Should fix |
| Record By Decade Leaderboard | Pass with context dedupe | Should fix |
| Matchup By Decade | Strong pass with raw-toggle cleanup | Should fix |

---

## 11. Comparison Panels

### Screenshot/query

- Family: Comparison Panels
- Query: `Jokic vs Embiid recent form`
- Fixture: 239

### What passes

- This is much better than the original version.
- Hero now matches `recent form` intent instead of defaulting to wins.
- Compact side-by-side cards are better than the prior oversized dashboards.
- Focused metric table is readable.
- `Show more metrics` exists, which matches the lock-in decision.
- Edge/difference copy is improved:
  - `Difference 2.0 MIN` for neutral minutes is good.
  - `+1.4 percentage points` for TS% is good.

### Issues

#### Internal note still product-facing

Current note:

```txt
sample_advanced_metrics: usg_pct, ast_pct, reb_pct, tov_pct recomputed from filtered sample
```

This should be hidden in product UI or humanized:

```txt
Advanced rate stats were recalculated using only this filtered sample.
```

#### Context is very thin

Context only shows:

```txt
Filter: Last N games: 10
```

That is acceptable, but a cleaner product label would be:

```txt
Window: Last 10 games
```

#### Record edge copy is still slightly clunky

Current row:

```txt
Record | 10-0 | 7-3 | Nikola Jokic +3 wins
```

This is not wrong, but better copy would be:

```txt
Nikola Jokić +3 wins
```

or:

```txt
Nikola Jokić has 3 more wins
```

The issue is minor.

### Follow-up

- Hide/humanize internal `sample_advanced_metrics` notes.
- Prefer `Window: Last 10 games` over `Filter: Last N games: 10` where possible.
- Optionally improve record edge copy readability.

### Status

Pass with polish.

---

## 12. Team Record

### Screenshot/query

- Family: Team Record
- Query: `What is the Celtics' record against playoff teams?`
- Fixture: 45

### What passes

This fixed the major semantic problem from the original review.

Hero now correctly says:

```txt
The Boston Celtics are 6-5 against 2024-25 playoff teams, a 54.5% win rate.
```

This preserves `against playoff teams` and no longer says `in the playoffs`.

Other passes:

- One-row table is right for this family.
- `W-L` highlight is correct.
- `Opponent Group` appears as its own column, which solves the misleading `Type` problem.
- `Show additional columns` is better than raw table wording.

### Issues

#### Table is horizontally clipped in screenshot

The right side of the table shows the next column cut off as `SEA...` / partial season. This may be expected if horizontal scroll exists, but it visually looks cut in the screenshot.

Potential fixes:

- reduce default columns in the visible one-row team record table
- ensure horizontal scroll affordance is obvious
- move less important context columns behind additional columns

#### Context wording is still awkward

Current:

```txt
Filter: VS: PLAYOFF TEAMS
Filter: Games vs 20 opponents (ATL, BOS, CHI, ...)
```

Preferred:

```txt
Opponent group: Playoff teams
Included opponents: 20 teams (ATL, BOS, CHI, ...)
```

### Follow-up

- Clean opponent-group context labels.
- Consider keeping one-row record table tighter by moving low-value context columns behind additional columns.
- Ensure table horizontal-scroll affordance is clear if columns exceed viewport.

### Status

Strong pass with table-width/context polish.

---

## 13. Record By Decade

### Screenshot/query

- Family: Record By Decade
- Query: `Warriors record by decade`
- Fixture: 236

### What passes

- Hero is clear.
- Context is clean and no longer mislabeled as caveat.
- Decade table is readable.
- `Win %` highlight is fine for a broad record-by-decade query.

### Issue

`Record Detail` still shows:

```txt
Show raw table
```

This should likely be hidden if duplicative, or relabeled if it exposes additional fields.

Preferred if kept:

```txt
Show record details
```

or:

```txt
Show additional columns
```

### Follow-up

- Rename or hide `Record Detail` raw toggle if product-facing/duplicative.

### Status

Pass with raw-toggle cleanup.

---

## 14. Record By Decade Leaderboard

### Screenshot/query

- Family: Record By Decade Leaderboard
- Query: `winningest team of the 2010s`
- Fixture: 237

### What passes

- Hero is strong:

```txt
The San Antonio Spurs won the most games in the 2010s, with 541 wins.
```

- Table is clean and readable.
- `Wins` highlight is correct.
- `Season Type` column is clearer than generic `Type`.

### Issue

Context duplicates season range:

```txt
Season range: 2010-11 to 2019-20
Filter: Season range: 2010-11 – 2019-20
```

Keep one.

### Follow-up

- Deduplicate season range context lines.

### Status

Pass with context dedupe.

---

## 15. Matchup By Decade

### Screenshot/query

- Family: Matchup By Decade
- Query: `Lakers vs Celtics by decade`
- Fixture: 238

### What passes

This is a strong output.

- Hero is excellent:

```txt
The Los Angeles Lakers lead the Boston Celtics 31-27 in regular-season games from 1996-97 through 2025-26.
```

- `Games` column was added and is useful.
- Table is readable.
- Context is clean.

### Issue

`Matchup Summary Detail` still shows:

```txt
Show raw table
```

If this is duplicative, hide it. If it exposes additional fields, relabel it.

Preferred:

```txt
Show matchup summary
```

or:

```txt
Show additional columns
```

### Follow-up

- Rename or hide `Matchup Summary Detail` raw toggle if product-facing/duplicative.

### Status

Strong pass with raw-toggle cleanup.

---

# Batch 3 punch list

## Should fix

1. **Internal note cleanup remains cross-cutting**
   - `sample_advanced_metrics...` appears in Comparison Panels too.
   - Same cleanup category as Batch 1/2.

2. **Context label cleanup**
   - `Filter: Last N games: 10` should ideally become `Window: Last 10 games`.
   - `VS: PLAYOFF TEAMS` should become `Opponent group: Playoff teams`.
   - `Games vs 20 opponents...` should become `Included opponents: 20 teams...`.

3. **Context deduplication**
   - Record By Decade Leaderboard repeats season range as both range and filter.
   - Same issue appeared in no-result/streak/playoff round outputs.

4. **Raw/detail toggle cleanup**
   - `Record Detail` still says `Show raw table`.
   - `Matchup Summary Detail` still says `Show raw table`.
   - This joins Batch 2 detail-toggle cleanup items.

5. **Table width / clipping polish**
   - Team Record one-row table clips right-side columns in screenshot.
   - Consider moving lower-value context columns behind additional columns or making horizontal scroll affordance clearer.

## Running final punch-list additions

Add these to the final focused fix candidates:

11. Team Record visible table width/clipping cleanup.
12. Human-friendly labels for `Last N games` / opponent group / included-opponents context.
13. Remaining `Show raw table` labels on record/matchup detail sections.
