# Result Display Implementation Queue (Pattern-Based)

> **Role:** Sequenced, PR-sized work items to migrate result rendering
> from one-component-per-route to the pattern-based architecture
> described in [`result_display_patterns.md`](./result_display_patterns.md).
>
> **Spec source of truth:** [`result_display_map.md`](./result_display_map.md)
> defines the StatMuse-baseline answer shape every pattern is built to
> match. [`result_display_patterns.md`](./result_display_patterns.md)
> defines the code architecture. This file is the build sequence.
>
> **Adopted:** 2026-05-03. Replaces the earlier route-by-route polish
> queue.
>
> **How to work this file:** Find the first unchecked item below.
> Implement it per its acceptance criteria. Ship it (one PR per item),
> validate against the deployed app, then move to the next item.
>
> **Important:** Do **not** run this as a continuous autonomous loop.
> Each item ships, the user looks at the result against the deployed
> app, decides whether the pattern is right, and only then does the
> next item start. Visual quality cannot be verified by tests; it
> requires human eyes between items.
>
> **Branching rule:** Every item branches off `main`. One PR per item.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress (or paused for user validation)
- `[x]` — complete and merged
- `[-]` — skipped (with inline note)

---

## Guiding principle

Build one pattern at a time. Migrate the routes that fit. Validate
against the deployed app. Then build the next pattern.

Do not pre-build all patterns before any route uses them. Do not
migrate all routes for a pattern before the pattern itself is validated
on at least one route. The earlier polish loop failed because it
shipped 18 PRs of visual change without a human checking quality
between them — this queue is structured to prevent that.

---

## Phase 1 — Substrate

Get the shared primitives and renderer scaffolding in place that all
patterns will depend on.

### 1. `[x]` Add result primitives + ResultRenderer scaffold

**Why:** Every pattern composes the same set of primitives (hero card,
result table, identity inline, etc.). Build them once, share across
patterns. Establish the new render path before any pattern is built.

**Scope:**

- Create `frontend/src/components/results/` directory structure per
  [`result_display_patterns.md`](./result_display_patterns.md) "File
  layout" section.
- Implement primitives:
  - `ResultShell` — outer container, freshness banner placement, mobile
    padding
  - `ResultHero` — colored hero card; props: `subjectIllustration`,
    `sentence`, `disambiguationNote?`, `tone` (color theme)
  - `ResultTable` — styled answer table (extends or wraps the existing
    `DataTable`); supports queried-column highlight, footer rows
    (`<tfoot>` for Average/Total), inline cell content
  - `EntityIdentity` — inline headshot/logo + name treatment used inside
    table cells
  - Move `RawDetailToggle` into `results/primitives/` (already exists
    at `frontend/src/components/RawDetailToggle.tsx`)
- Add `ResultRenderer.tsx` — entry component; reads route, calls
  `routeToPattern(data)`, renders the returned pattern array.
- Add `config/routeToPattern.ts` with `default → [{type: "fallback_table"}]`.
  No real route mappings yet — those land with each pattern PR.
- Add `patterns/FallbackTableResult.tsx` — generic raw-table renderer
  used until other patterns migrate routes off it.
- Wire `ResultRenderer` into the result-display path so every result
  hits the new code path. Initially every result will render as the
  fallback table; that is correct.

**Files likely touched:**

- All new files under `frontend/src/components/results/`
- `frontend/src/App.tsx` (or wherever results are currently rendered)
  to swap in `ResultRenderer`
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this
  item

**Acceptance criteria:**

- Every query routes through `ResultRenderer` and renders via
  `FallbackTableResult` (a plain table). Content unchanged; a
  short-term regression in *polish* is expected and acceptable —
  patterns land in subsequent items.
- Existing section components are still in the tree but no longer
  reachable from `ResultRenderer`. They will be deleted as their routes
  migrate.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual: deploy and verify any query renders without errors.

**User validation gate:**

After merge, confirm the deployed app still functions before item 2
starts. Expect every query to look like a raw table dump — that is
intentional and short-term.

---

## Phase 2 — Build patterns one at a time

Each item below builds one pattern, migrates its target routes, ships,
and pauses for user validation before the next item.

### 2. `[x]` `LeaderboardResult` + migrate `season_leaders`, `season_team_leaders`

**Why:** Most-used class. Cleanest StatMuse reference (`most ppg in
2025 playoffs`). If this pattern can't be made to feel right, the
architecture itself is wrong and we want to know early.

**Scope:**

- Build `patterns/LeaderboardResult.tsx`:
  - Hero card: sentence-style answer using the leaderboard's #1 row
    ("{leader} {verb} the most {metric_label} in the {context}, with
    {value}.")
  - Disambiguation note slot (rendered when present in metadata)
  - Answer table: rank, inline headshot/logo, name, **queried metric
    column highlighted**, season, team, supporting per-game stats,
    scrollable long-tail columns
- Add `routeToPattern.ts` mappings for `season_leaders` and
  `season_team_leaders` returning `LeaderboardResult`.
- Delete `LeaderboardSection.tsx`. Decide on `OccurrenceLeaderboardSection.tsx`:
  if occurrence routes fit `LeaderboardResult` cleanly, migrate them in
  this PR; otherwise leave them on the fallback for item 4.

**Acceptance criteria:**

- `most ppg in 2025 playoffs` matches the StatMuse reference shape:
  sentence hero + dense table with PPG column highlighted.
- `best record since 2015` shows the team-first variant with W-L
  context.
- No card-per-row layout. No redundant secondary table. The leaderboard
  table IS the answer.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual: run both example queries against the deployed app.

**User validation gate:**

Run `most ppg in 2025 playoffs` and `best record since 2015`. If the
pattern feels right, proceed to item 3. If not, iterate on
`LeaderboardResult` before any other pattern is built.

---

### 3. `[x]` `EntitySummaryResult` + `GameLogResult` + migrate `player_game_summary`

**Why:** First compound-pattern test. `player_game_summary` for last-N
queries needs *both* an entity summary hero AND a game-log table — the
composition model from
[`result_display_patterns.md`](./result_display_patterns.md). Validates
that composition works as designed.

**Scope:**

- Build `patterns/EntitySummaryResult.tsx`:
  - Hero card with subject illustration + sentence + optional
    disambiguation
  - Optional small "summary strip" of headline averages below the
    sentence (single horizontal row, not a stat block)
- Build `patterns/GameLogResult.tsx`:
  - Compact summary strip of key averages over the window
  - Game-log table: date, inline headshot, name, team, vs/@, opp, MIN,
    PTS, REB, AST, STL, BLK, FG, 3P, FT, TOV, +/-
  - `<tfoot>` footer rows for `Average` and `Total`
- Add `routeToPattern.ts` mapping for `player_game_summary`:
  - Last-N variant → `[entity_summary, game_log]`
  - Broad season/career variant → `[entity_summary]`
- Delete `PlayerSummarySection.tsx`.

**Acceptance criteria:**

- `Jokic last 10 games` matches the StatMuse reference: sentence hero +
  dense game-log table with Average/Total footer rows. No "Recent
  Games" cards.
- `Curry this season` (or similar broad query) shows just the entity
  summary, no game log.
- Visibly belongs to the same family as `LeaderboardResult` from item
  2 (consistent shell, hero treatment, table styling).
- Build, typecheck, and tests pass.

**User validation gate:**

Run `Jokic last 10 games`, `LeBron last 5 games`, and a broad season
query. Pattern feels right? Proceed.

---

### 4. `[x]` Migrate the rest of the leaderboard family

**Why:** Now that `LeaderboardResult` is validated, batch-migrate the
remaining leaderboard-family routes to it via config additions only.
No new pattern code unless a route exposes a real gap.

**Scope:**

- Add `routeToPattern.ts` mappings for:
  - `team_record_leaderboard`
  - `player_stretch_leaderboard`
  - `player_occurrence_leaders` (if not already in item 2)
  - `team_occurrence_leaders`
  - `lineup_leaderboard`
  - `playoff_appearances`
- Per-route config tweaks (which columns are primary, which is
  highlighted). No pattern code changes.
- Delete now-orphaned per-route components.

**Acceptance criteria:**

- All listed routes render via `LeaderboardResult` with appropriate
  per-route columns.
- No routes lose access to data they previously had visible.
- Build, typecheck, tests pass.

**User validation gate:** representative query per migrated route.

---

### 5. `[x]` Migrate the game-log family

**Scope:**

- Add `routeToPattern.ts` mappings for:
  - `player_game_finder`
  - `game_finder`
  - `top_player_games`
  - `top_team_games`
  - `game_summary` (single-game = 1-row game log)
- Per-route config tweaks.
- Delete `PlayerGameFinderSection.tsx` and other orphaned game-log
  components.

**User validation gate:** `games where Jokic had over 25 points and 10
rebounds`, `Curry's 50-point games`, `top 10 scoring games this season`.

---

### 6. `[x]` `SplitResult` + migrate split routes

**Why:** Splits have a distinct shape (multi-bucket comparison of one
subject) that doesn't fit `LeaderboardResult` or `GameLogResult`.

**Scope:**

- Build `patterns/SplitResult.tsx`:
  - Hero card with subject + split-type sentence
  - One bucket card or table-row per bucket showing per-bucket stats
  - Diff/edge row when exactly two buckets
- Mappings for `player_split_summary`, `team_split_summary`,
  `player_on_off`.
- Delete `SplitSummaryCardsSection.tsx`, `SplitSummarySection.tsx`.

**User validation gate:** `Jokic home vs away`, `Lakers on/off LeBron`.

---

### 7. `[x]` `StreakResult` + migrate streak routes

**Scope:**

- Build `patterns/StreakResult.tsx`:
  - Hero card with subject + streak-type sentence
  - Streak length as the dominant value
  - Date range, active/completed badge
  - During-streak averages
- Mappings for `player_streak_finder`, `team_streak_finder`.
- Delete `StreakSection.tsx`.

**User validation gate:** representative streak queries.

---

### 8. `[ ]` `PlayoffHistoryResult` + migrate playoff routes

**Scope:**

- Build `patterns/PlayoffHistoryResult.tsx`:
  - Hero card with team + summary sentence (appearances, championships,
    etc.)
  - Season-by-season table: season, round reached, record, result,
    opponent
- Mappings for `playoff_history`, `playoff_round_record`,
  `playoff_matchup_history`.
- Delete `PlayoffSection.tsx`.

**User validation gate:** `Lakers playoff history`,
`Celtics vs Heat playoff matchups`.

---

### 9. `[ ]` `ComparisonResult` + migrate comparison routes (LAST)

**Why:** Comparisons are the most complex shape. Built last so the
pattern set is stable and the hardest case has the benefit of all prior
pattern lessons.

**Scope:**

- Build `patterns/ComparisonResult.tsx`:
  - Header with both subjects
  - Side-by-side subject cards with hero stats per subject
  - Metric grid: rows = metrics, columns = subjects + edge/delta
- Mappings for `player_compare`, `team_compare`,
  `team_matchup_record`.
- Delete `PlayerComparisonSection.tsx`, `ComparisonSection.tsx`,
  `HeadToHeadSection.tsx`, `TeamSummarySection.tsx`.

**User validation gate:** `Jokic vs Embiid this season`,
`Celtics vs Bucks`, `Lakers vs Celtics head-to-head`.

---

## Phase 3 — Cleanup and close

### 10. `[ ]` Delete dead per-route components and `ResultSections.tsx`

**Why:** Once every route maps to a pattern (or to `FallbackTableResult`
intentionally), old components and the old router are dead code.

**Scope:**

- Verify no imports remain to the old per-route section components.
- Delete `frontend/src/components/ResultSections.tsx`.
- Delete any orphaned section components.
- Delete CSS modules for deleted components.
- Update `docs/operations/ui_guide.md` if it referenced the old
  components.

**Acceptance criteria:**

- `git grep "PlayerSummarySection\|LeaderboardSection"` and similar
  return zero results outside this doc / git history.
- Build, tests pass.

---

### 11. `[ ]` Reconcile map statuses and close out

**Why:** Self-propagating final task. Ensure
[`result_display_map.md`](./result_display_map.md) entries reflect
shipped reality.

**Scope:**

- For every route entry in the map, run the example queries against the
  deployed app.
- Mark entries `[x]` when rendering matches the entry's `Should show:`.
  Mark `[~]` with a follow-up note if a gap remains.
- If meaningful gaps remain, draft `result_display_followup_queue.md`.
  Otherwise close this plan with a short retrospective at the bottom of
  this file.

---

## Appendix: progress tracking

When all items above are checked `[x]` (or `[-]` with notes), the queue
is complete. The architecture in
[`result_display_patterns.md`](./result_display_patterns.md) is the
ongoing reference for any future result-rendering work.
