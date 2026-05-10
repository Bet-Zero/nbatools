# Result Display Lock-In — Final Visual QA Notes

> Purpose: running punch-list from the post-implementation visual QA pass.
>
> Scope: this is **not** a new redesign spec. The 19 display families are implemented for the lock-in scope. This doc captures final visual QA findings, regressions, copy polish, and small follow-up fixes discovered from updated screenshots.
>
> Workflow:
>
> 1. Review updated screenshots in batches.
> 2. Record pass/fail/polish notes here.
> 3. After all batches are reviewed, turn this into a focused final punch-list prompt.
>
> Source implementation docs:
>
> - `result_display_lock_in_implementation_spec.md`
> - `result_display_wave_1_findings.md`
> - `result_display_wave_2_findings.md`
> - `result_display_wave_3_findings.md`
> - `result_display_wave_4_findings.md`
> - `result_display_wave_5_findings.md`

---

## Overall QA posture

The updated outputs are significantly improved after Waves 1–5. This final pass should focus on:

- wrong-answer intent bugs
- product/debug separation
- noisy internal notes
- context duplication
- small copy polish
- visual readability regressions

Do **not** reopen broad redesign unless a family is clearly answering the wrong question.

---

# Batch 1

Screenshots reviewed:

1. Player Game Log
2. Entity Summary + Recent Games
3. Entity Summary
4. Message No Result
5. Guided No Result

---

## Batch 1 verdict summary

| Screenshot / Family | Verdict | Priority |
|---|---|---|
| Player Game Log | Pass, confirm product row cap | Confirm |
| Entity Summary + Recent Games | Pass with polish | Should fix |
| Entity Summary | **Fail: wrong answer intent** | **Must fix** |
| Message No Result | Pass-ish, copy polish | Should fix |
| Guided No Result | Pass with product/debug cleanup | Should fix |

---

## 1. Player Game Log

### Screenshot/query

- Family: Player Game Log
- Query: `How often has Nikola Jokić recorded a triple-double this season?`
- Fixture: 71

### What passes

- Dense table is much better than the original output.
- PTS/REB/AST highlight for triple-doubles is correct.
- FG is now included.
- `Show additional columns` is better than `Show raw table`.

### Issue / confirmation needed

The screenshot is from review mode and shows all 34 rows. That may be intentional because review mode should show full rows, but product mode should still cap this at 12 rows with `Show all 34 games`.

### Follow-up

- Confirm product mode caps this result while review mode can continue showing all rows.

### Status

Pass if product mode row cap works.

---

## 2. Entity Summary + Recent Games

### Screenshot/query

- Family: Entity Summary + Recent Games
- Query: `How has Jayson Tatum played against good teams this season?`
- Fixture: 44

### What passes

- Hero now says `in 11 games against good teams this season`.
- Game log is visible under the hero.
- Context moved out of caveats.
- Table is useful.
- Average/Total rows are useful.

### Issues

#### Internal note is too developer-facing

Current note:

```txt
sample_advanced_metrics: usg_pct, ast_pct, reb_pct, tov_pct recomputed from filtered sample
```

Preferred product copy:

```txt
Advanced rate stats were recalculated using only this filtered sample.
```

Alternative: hide this note in product UI and keep it only in review/debug mode.

#### Context is slightly duplicated / awkward

Current context:

```txt
Filter: VS: GOOD TEAMS
Filter: Games vs 19 opponents (ATL, BOS, CHA, ...)
```

Preferred context:

```txt
Opponent group: Good teams
Included opponents: 19 teams (ATL, BOS, CHA, ...)
```

### Follow-up

- Humanize or hide internal `sample_advanced_metrics` notes.
- Clean up duplicated/awkward filter context labels.

### Status

Pass with polish.

---

## 3. Entity Summary

### Screenshot/query

- Family: Entity Summary
- Query: `What is the Knicks' record when Jalen Brunson doesn't play?`
- Fixture: 57

### Issue

This output is answering the wrong question.

The query asks for the Knicks' record when Brunson does not play, but the answer says:

```txt
Jalen Brunson has averaged 26 points, 3.3 rebounds and 6.8 assists in the 2025-26 regular season.
```

That is Brunson's own average, not the Knicks' record without him.

### Expected behavior

This should be a team record / game-summary style answer, centered on the Knicks outcome.

Example hero:

```txt
The Knicks are X-X in games without Jalen Brunson this season.
```

If matching game rows exist, show the Knicks game-log table under the hero.

### Notes

The header chips show both `PLAYER Jalen Brunson` and `TEAM NYK`, which is useful context. But the answer must center the team result.

### Follow-up

- Fix routing/hero intent for `team record when player doesn't play` style queries.
- Ensure `without player` team queries do not fall through to player-average summary heroes.
- Prefer Team Record / Game Summary Log behavior when the asked stat is team record/performance without a player.

### Status

**Fail — must fix.**

---

## 4. Message No Result

### Screenshot/query

- Family: Message No Result
- Query: `Which scorers have cooled off over their last 10 games?`
- Fixture: 19

### What passes

- This can reasonably remain a hard unsupported/unrecognized query if `cooled off` is not supported.
- The output no longer shows a misleading table.

### Issue

Primary copy is too generic and harsh:

```txt
Query Error
An error occurred while processing the query.
```

Better user-facing copy:

```txt
I couldn't interpret “cooled off” as a supported stat query yet.
```

Optional only if supported:

```txt
Try asking for players whose PPG dropped over their last 10 games, or recent scoring leaders.
```

### Follow-up

- Improve hard-unrecognized-query copy.
- Avoid generic `An error occurred...` as the main message when the issue is unsupported query language.
- Product UI should be less debuggy than review/debug status chips.

### Status

Pass-ish, copy polish needed.

---

## 5. Guided No Result

### Screenshot/query

- Family: Guided No Result
- Query: `Who scored the most points last night?`
- Fixture: 11

### What passes

Primary message is good:

```txt
No NBA games matched Apr 11, 2026.
```

Suggestions are relevant. Raw ISO date is gone. `Why this happened` is better than `Details`.

### Issues

#### Context duplication

Current context includes duplicate date meaning:

```txt
Date range: Apr 11, 2026
Filter: Date range: Apr 11, 2026
```

Keep one.

#### Suggestion chip style feels developer-y

The `Try one of these` suggestions render like black code snippets. They are readable, but visually they feel like code rather than user query chips.

#### Internal notes still visible in product-style output

Current `Why this happened` includes internal notes:

```txt
default: <metric> only → league-wide leaderboard
leaderboard_source: game-log derived (season-advanced stats excluded in date window)
```

Preferred product details should be limited to:

```txt
No games matched the specified filters.
```

The internal parser/source notes should be hidden in product UI or shown only in review/debug mode.

### Follow-up

- Deduplicate no-result context lines.
- Restyle suggestion chips to look like query suggestions, not code snippets.
- Hide internal parser/source notes from product-facing `Why this happened`; keep them only in debug/review if needed.

### Status

Pass with product/debug cleanup.

---

# Batch 1 punch list

## Must fix

1. **Fixture 57 wrong answer intent**
   - Query: `What is the Knicks' record when Jalen Brunson doesn't play?`
   - Current answer gives Brunson averages.
   - Expected answer gives Knicks record/performance without Brunson.

## Should fix

2. **Humanize or hide internal notes**
   - `sample_advanced_metrics...`
   - `leaderboard_source...`
   - `default: <metric> only → league-wide leaderboard`

3. **Deduplicate context lines**
   - Guided No Result repeats date range.
   - Good-teams context has awkward duplicate filter wording.

4. **Improve hard error copy**
   - Replace generic `Query Error / An error occurred...` for unsupported natural-language concepts with clearer unsupported-query copy.

5. **Restyle no-result suggestion chips**
   - Suggestions should feel like clickable/user query suggestions, not code snippets.

## Confirm

6. **Product row cap for large player game logs**
   - Review mode can show all rows.
   - Product mode should cap at 12 with `Show all {N} games`.

---

# Running final punch-list candidates

The following items may become the final focused fix prompt after all screenshot batches are reviewed:

1. Fix `without player` team-record intent routing/hero.
2. Product/debug separation for internal notes.
3. Context deduplication and context label cleanup.
4. Hard unsupported query copy polish.
5. No-result suggestion chip visual polish.
6. Confirm product-vs-review row cap behavior.
