# Result Display Lock-In — Final Visual QA Batch 4 Addendum

> Purpose: Batch 4 addendum for the final visual QA pass.
>
> Main running doc: `docs/planning/result-display-lock-in/final_visual_qa_notes.md`.
> Batch 3 addendum: `docs/planning/result-display-lock-in/final_visual_qa_batch_3_addendum.md`.
>
> Note: Final punch-list synthesis should read all three QA files.

---

# Batch 4

Screenshots reviewed:

16. Leaderboard Table
17. Top Performances
18. Rolling Stretch

Only 18 shapes/screenshots were present in the latest review page. The missing reviewed family was confirmed afterward: **Playoff History** / standalone team playoff history is no longer rendering as a success shape because Fixture 228 currently falls into a no-result/unsupported output.

---

## Batch 4 verdict summary

| Screenshot / Family | Verdict | Priority |
|---|---|---|
| Leaderboard Table | Pass with internal-note cleanup | Should fix |
| Top Performances | Strong pass with internal-note cleanup | Should fix |
| Rolling Stretch | Strong pass with minor context/metric-label polish | Should fix |
| Playoff History / Fixture 228 | **Regression: now unsupported** | **Must fix** |

---

## 16. Leaderboard Table

### Screenshot/query

- Family: Leaderboard Table
- Query: `Who leads the NBA in points per game this season?`
- Fixture: 1

### What passes

- Hero is strong:

```txt
Luka Dončić led the NBA with 33.5 PPG in the 2025-26 regular season.
```

- Table is clean and readable.
- `PPG` is highlighted correctly.
- Ranking table shape is locked and useful.

### Issue

Internal default note is still product-facing:

```txt
default: <metric> only → league-wide leaderboard
```

This should be hidden in product UI or rewritten as normal context if needed. In this case, it likely does not need to be shown at all.

### Follow-up

- Hide or humanize parser/default notes in leaderboard outputs.

### Status

Pass with internal-note cleanup.

---

## 17. Top Performances

### Screenshot/query

- Family: Top Performances
- Query: `What were the biggest scoring games this season?`
- Fixture: 31

### What passes

This is a strong output.

- Hero includes player, metric value, opponent, date, and result context:

```txt
Bam Adebayo had the top scoring game this season with 83 points in a win against Washington Wizards on Mar 10.
```

- Table is clean and readable.
- `PTS` is highlighted correctly.
- Supporting columns `REB`, `AST`, `3PM` are appropriate for scoring games.

### Issue

Internal note is product-facing:

```txt
season_high: league-wide top single-game performances
```

This is not awful, but it is still implementation/parser-style language. Prefer hiding it, or humanize it:

```txt
Showing league-wide single-game scoring performances.
```

### Follow-up

- Hide or humanize `season_high` / parser-style notes in product UI.

### Status

Strong pass with internal-note cleanup.

---

## 18. Rolling Stretch

### Screenshot/query

- Family: Rolling Stretch
- Query: `Which players have the hottest 3-game scoring stretch this year?`
- Fixture: 36

### What passes

This is a strong output.

- Deduplication works: each player appears once for the `Which players` wording.
- Hero is strong and player-oriented:

```txt
Luka Dončić had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.
```

- Table is clean and readable.
- `PPG` is highlighted correctly.

### Issue

Context says:

```txt
Metric: PTS
```

But the displayed/ranked metric is `PPG`. For rolling scoring stretches, context should say either:

```txt
Metric: PPG
```

or:

```txt
Metric: Scoring average
```

### Follow-up

- Align rolling-stretch context metric label with displayed metric (`PPG`) rather than raw source metric (`PTS`).

### Status

Strong pass with minor context/metric-label polish.

---

## 19. Playoff History / Fixture 228 regression

### Screenshot/query

- Family: Playoff History
- Query: `Lakers playoff history`
- Fixture: 228

### Confirmed current output

Fixture 228 is still present in the 402-fixture run, but it no longer renders the standalone Playoff History success shape.

Current status/chips:

```txt
NO RESULT
playoff history
summary
unsupported
```

Current no-result card:

```txt
Unsupported Query
This query combination is not supported by the engine.
```

Current detail:

```txt
No columns to parse from file
```

### Why this matters

This is not just a review-page grouping issue. It is a real regression or data-loading/parser issue because the fixture still runs but falls into unsupported/no-result instead of rendering the Playoff History table.

Earlier expected family shape:

- standalone Playoff History hero
- season-by-season playoff table
- clear caveat about unavailable pre-2001-02 round data when applicable

### Expected behavior

`Lakers playoff history` should render as a successful Playoff History result, similar to the earlier reviewed output:

- historical team hero
- season-by-season playoff history table
- readable round/result labels
- real caveat for unavailable historical round-level data

### Likely investigation areas

This appears more backend/data/parser-side than visual-renderer-side.

Investigate:

- playoff history command/parser
- source playoff history data file/path
- fixture/result payload for Fixture 228
- route/pattern classification for `playoff_history + summary`
- whether recent changes caused the fixture to invoke a parser expecting columns that are now missing

### Follow-up

- Restore Fixture 228 as a successful Playoff History output, or document why the source data/support was intentionally removed.
- Confirm Playoff History returns as a distinct success shape in the review page after the fix, unless intentionally merged with another successful playoff table shape.

### Status

**Fail / must-fix regression.**

---

# Batch 4 punch list

## Must fix

1. **Fixture 228 Playoff History regression**
   - `Lakers playoff history` now returns unsupported/no-result.
   - Detail: `No columns to parse from file`.
   - Restore successful standalone Playoff History output.

## Should fix

2. **Internal note cleanup remains cross-cutting**
   - `default: <metric> only → league-wide leaderboard`
   - `season_high: league-wide top single-game performances`
   - Same class as `sample_advanced_metrics...`, `leaderboard_source...`, and streak default notes.

3. **Rolling-stretch context metric label**
   - `Metric: PTS` should become `Metric: PPG` or `Metric: Scoring average` when the visible ranked metric is PPG.

---

# Running final punch-list additions

Add these to the final focused fix candidates:

14. Hide/humanize leaderboard/top-performance parser notes.
15. Align rolling-stretch context metric labels with visible metric.
16. **Must fix:** restore Fixture 228 Playoff History success output / investigate `No columns to parse from file` regression.
