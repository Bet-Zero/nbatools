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

# Batch 2

Screenshots reviewed:

6. Team Game Log
7. Game Summary Log
8. Streak Table
9. Playoff Round Records
10. Playoff Matchup History

---

## Batch 2 verdict summary

| Screenshot / Family | Verdict | Priority |
|---|---|---|
| Team Game Log | Pass with minor context polish | Should fix |
| Game Summary Log | Pass with minor detail-toggle/row-cap confirmation | Should fix / Confirm |
| Streak Table | Pass-ish, but threshold/status/internal-note polish needed | Should fix |
| Playoff Round Records | Pass with minor context dedupe | Should fix |
| Playoff Matchup History | Strong pass with minor raw-toggle cleanup | Should fix |

---

## 6. Team Game Log

### Screenshot/query

- Family: Team Game Log
- Query: `How often have the Lakers held opponents under 100 points this year?`
- Fixture: 76

### What passes

- Hero is strong and answers the query directly:

```txt
The Lakers have held opponents under 100 points 7 times this season, going 7-0.
```

- Team-first game table is readable.
- `Opp PTS` and `Margin` are included.
- `Opp PTS` is highlighted, which correctly reflects the condition.
- `Show additional columns` is better than `Show raw table`.

### Issue

Context says:

```txt
Metric: PTS
Filter: OPP: <= 100 PTS
```

For this query, the metric/context should make the opponent-points meaning clearer. `Metric: PTS` alone is slightly misleading because the condition is about opponent points.

Preferred context:

```txt
Metric: Opponent points
Filter: Opp PTS <= 100
```

### Follow-up

- Improve context label for opponent-stat conditions so it does not imply team PTS.

### Status

Pass with minor context polish.

---

## 7. Game Summary Log

### Screenshot/query

- Family: Game Summary Log
- Query: `How do the Suns perform when Devin Booker didn't play?`
- Fixture: 51

### What passes

- Hero is strong:

```txt
The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG.
```

- Summary strip is much improved and includes Record.
- Team game-log table is readable.
- `Opp PTS` and `Margin` are included.
- Average/Total footer rows are useful and readable.
- `Game Detail` uses `Show additional columns`, which is better than raw wording.

### Issues / confirmations

- Review mode shows all 18 rows. That is acceptable for review mode if product mode still caps long logs.
- `Top Performers Detail` still uses `Show raw table`. If this exposes a separate hidden section, it may be acceptable, but the label should probably be less debuggy if it is user-facing.

Preferred label if retained:

```txt
Show top performers
```

or

```txt
Show top performer details
```

### Follow-up

- Confirm product mode caps 18-row game summaries with `Show all 18 games`.
- Rename `Top Performers Detail` toggle if it remains user-facing.

### Status

Pass with minor cleanup.

---

## 8. Streak Table

### Screenshot/query

- Family: Streak Table
- Query: `Jokic 5 straight games with 20+ points`
- Fixture: 201

### What passes

- Dense streak table is readable.
- Length column is present and the table is useful.
- The streak condition is visible as `20+ PTS`.

### Issues

#### Hero still loses the 5-game threshold meaning

Current hero:

```txt
Nikola Jokić scored 20+ points in 18 straight games from Oct 26 to Dec 8, 2024.
```

This is not terrible, but the query says `5 straight games`. The hero should clarify whether it is showing the longest streak of at least 5 games or all qualifying 5+ streaks.

Preferred hero if minimum-threshold query:

```txt
Nikola Jokić has 15 streaks of 5+ straight games with 20+ points. His longest was 18 games, from Oct 26 to Dec 8, 2024.
```

Or:

```txt
Nikola Jokić's longest 20+ point streak of at least 5 games was 18 games, from Oct 26 to Dec 8, 2024.
```

#### Status column is repetitive

Every visible row says `COMPLETED`. Earlier lock-in rule said Status should show only when active/current/mixed statuses exist. If every row is completed, hide the Status column.

#### Internal default note is product-facing

Current note:

```txt
default: player streak uses three-season window when no season specified
```

This should be either context in human wording or hidden from product UI.

Preferred copy if shown:

```txt
Because no season was specified, this search used the last three seasons.
```

#### Context duplicates filter/range

Context repeats season range as both `Season range` and `Filter: Season range`.

### Follow-up

- Make streak hero threshold-aware for `5+` / minimum streak queries.
- Hide `Status` when every row has the same completed status.
- Humanize or hide internal default note.
- Deduplicate season range context.

### Status

Pass-ish, but should fix threshold/status/internal-note polish.

---

## 9. Playoff Round Records

### Screenshot/query

- Family: Playoff Round Records
- Query: `best finals record since 1980`
- Fixture: 234

### What passes

- Hero is excellent:

```txt
The Indiana Pacers have the best Finals record since 1980, going 10-5 (.667) across 15 games.
```

- Table is clean and readable.
- `WIN PCT` highlight is correct.
- Caveat is now a real caveat and worded well.
- `Show additional columns` is better than raw table wording.

### Issue

Context duplicates season range:

```txt
Season range: 1980-81 to 2025-26
Filter: Season range: 1980-81 – 2025-26
```

Keep one.

### Follow-up

- Deduplicate season range context lines.

### Status

Pass with minor context cleanup.

---

## 10. Playoff Matchup History

### Screenshot/query

- Family: Playoff Matchup History
- Query: `Heat vs Knicks playoff history`
- Fixture: 229

### What passes

This is one of the strongest outputs in the updated set.

- Context and caveat are separated correctly.
- Hero now clearly states both game record and series record:

```txt
The Heat lead the Knicks 19-16 in playoff games. Their playoff series record is tied 3-3.
```

- Table includes `Winner` and `Series Result` directly.
- `Round unavailable` is much clearer than an unexplained dash.
- Games column is useful.

### Issue

`Postseason Summary Detail` still shows `Show raw table`. If this is not duplicative, it can remain, but the label should be less debuggy if product-facing.

Preferred:

```txt
Show postseason summary
```

or hide it if it duplicates the hero/table.

### Follow-up

- Rename or hide `Postseason Summary Detail` raw toggle if product-facing/duplicative.

### Status

Strong pass with minor raw-toggle cleanup.

---

# Batch 2 punch list

## Should fix

1. **Opponent-stat context labels**
   - Team Game Log should say `Metric: Opponent points` / `Filter: Opp PTS <= 100`, not generic `Metric: PTS`.

2. **Streak threshold-aware hero**
   - Preserve `5 straight games` / minimum threshold meaning in hero copy.

3. **Hide repetitive Streak Status column**
   - If all rows are `Completed`, hide Status.

4. **Humanize/hide internal default notes**
   - `default: player streak uses three-season window when no season specified`
   - Similar internal notes should not appear raw in product UI.

5. **Context deduplication**
   - Season range appears twice in Streak Table and Playoff Round Records.
   - Date/range/filter duplicates from Batch 1 remain part of the same cleanup category.

6. **Raw/detail toggle label cleanup**
   - `Top Performers Detail` should not say `Show raw table` if user-facing.
   - `Postseason Summary Detail` should not say `Show raw table` if user-facing or duplicative.

## Confirm

7. **Product row cap for 18-row Game Summary Log**
   - Review mode showing all rows is fine.
   - Product mode should cap with `Show all 18 games`.

---

# Running final punch-list candidates

The following items may become the final focused fix prompt after all screenshot batches are reviewed:

1. Fix `without player` team-record intent routing/hero.
2. Product/debug separation for internal notes.
3. Context deduplication and context label cleanup.
4. Hard unsupported query copy polish.
5. No-result suggestion chip visual polish.
6. Confirm product-vs-review row cap behavior.
7. Opponent-stat context label cleanup.
8. Streak threshold-aware hero.
9. Hide repetitive streak Status column.
10. Raw/detail toggle label cleanup for remaining detail sections.
