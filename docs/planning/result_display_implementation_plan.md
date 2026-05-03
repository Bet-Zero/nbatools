# Result Display Implementation Queue

> **Role:** Sequenced, PR-sized work items to make polished cards/lists the
> default output of every result display, while keeping every raw table
> available behind a collapsed toggle.
>
> **Source of truth:** [`result_display_map.md`](./result_display_map.md).
> Every fix below should match the `Should show:` intent for the route(s)
> it touches. If the map and this queue ever disagree, the map wins.
>
> **How to work this file:** Find the first unchecked item below. Review
> the reference docs it cites and the matching map entries. Execute per
> its acceptance criteria. Run the test commands. Check the item off,
> commit, open a PR, wait for CI, merge when green, then immediately move
> on to the next unchecked item and repeat. Continue working items in
> order without stopping until every item is checked `[x]` or you hit a
> genuine blocker. If blocked, leave the item marked `[~]` with an inline
> note and stop. Do not stop merely because one item finished — the
> default is to keep going.
>
> **Branching rule:** Every item branches off `main`, not off the docs
> branch this plan was first drafted on. Open one PR per item.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress (or blocked, with an inline note)
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## Reusable kickoff prompt

Paste this to start a continuous-loop session against this queue.

```text
Read docs/planning/result_display_implementation_plan.md and find the
first unchecked item. Open the route's matching entry in
docs/planning/result_display_map.md as your spec. Branch off main, execute
the item per its acceptance criteria, run the test commands, check the
item off, commit, open a PR, wait for CI, merge when green, then move
directly to the next unchecked item. Do not stop merely because one item
finished. Stop only on a genuine blocker (failing tests you cannot
resolve, an ambiguous decision that needs the user) — in which case mark
the item [~] with an inline note. Branch off main for every item. Use
focused pytest or focused npm tests per the AGENTS.md testing guidance,
not full local suites.
```

---

## In-flight reconciliation

Some related work was already shipped or is in flight. Items below
already account for this:

- **PR #200 (in flight)** — leaderboard column hiding + wins/losses
  context. Item 4 below covers any leaderboard polish remaining after
  #200 merges. Re-read the leaderboard section component before starting
  item 4 to see what's already there.
- **PR #199 (in flight)** — AGENTS.md test guidance. Item kickoff
  guidance in this file already follows the updated rules.
- **PR #201 (this PR's parent docs branch)** — adds the result display
  map and this queue. Items below assume this PR has merged.

---

## 1. `[x]` Add the shared `RawDetailToggle` primitive

**Why:** Every section component currently embeds raw `DataTable`
sections inline and always-open. Without a shared collapsed primitive,
the route-by-route polish work has nothing to compose against, and each
route would invent its own toggle. The `Show raw table` policy in the
map requires one consistent reveal pattern across every section.

**Scope:**

- Create `frontend/src/components/RawDetailToggle.tsx` and matching
  `RawDetailToggle.module.css`.
- Props:
  - `title: string`
  - `rows: SectionRow[]`
  - `highlight?: boolean`
  - `hiddenColumns?: Set<string>`
  - `defaultOpen?: boolean` (default `false`)
- Behavior:
  - Renders nothing when `rows.length === 0`.
  - Closed by default. Closed control labeled `Show raw table`. Open
    control labeled `Hide raw table`. Use these exact labels per the
    map's policy.
  - When open, renders a `DataTable` inside with the existing
    `highlight` and `hiddenColumns` behavior intact.
  - Keyboard accessible (toggle is a real `<button>`, focusable, aria
    state).
  - Mobile-clean (no overflow, no layout shift on toggle).
- Add a focused unit test covering: empty rows render nothing, closed
  state hides the table, open state shows it, hiddenColumns are
  respected when open.
- Do not yet wire it into any section component. That happens in item 2.

**Files likely touched:**

- `frontend/src/components/RawDetailToggle.tsx` (new)
- `frontend/src/components/RawDetailToggle.module.css` (new)
- `frontend/src/components/RawDetailToggle.test.tsx` (new)
- `docs/planning/result_display_implementation_plan.md` — check this
  item when complete

**Acceptance criteria:**

- Component exists, builds clean, tests pass.
- No other components changed (the wire-up is item 2).
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- RawDetailToggle`
- `cd frontend && npm run build`

**Reference docs:**

- `docs/planning/result_display_map.md` — "Raw detail table policy"
  section
- `frontend/src/components/DataTable.tsx`

---

## 2. `[x]` Wire `RawDetailToggle` into every existing always-open raw table

**Why:** Make the toggle live across every result page in one sweep,
rather than route-by-route. This delivers the map's "raw tables hidden by
default" rule everywhere with a single consistent treatment.

**Scope:**

- Replace every always-open raw `DataTable` rendered under a polished
  section with `<RawDetailToggle ... />`. Preserve existing `highlight`
  and `hiddenColumns` props.
- Affected components (verify by grepping
  `frontend/src/components/*Section.tsx` for `<DataTable`):
  - `PlayerSummarySection` — `Full Summary`, `By Season`
  - `TeamRecordSection` — `Record Detail`, `By Season`
  - `PlayerComparisonSection` — `Player Summary Detail`, `Metric
    Comparison`, `Full Metric Detail`
  - `LeaderboardSection` — `Full Leaderboard`
  - `OccurrenceLeaderboardSection` — equivalent detail tables
  - `TeamSummarySection`, `SplitSummaryCardsSection`, `StreakSection`,
    `PlayoffSection`, `HeadToHeadSection`, `PlayerGameFinderSection` —
    audit each and convert any always-open detail tables
- Do **not** change `renderFallback` in `ResultSections.tsx` — fallback
  paths exist for query classes with no designed view, and there the
  raw table IS the primary answer. Leave those as-is.
- Do not change backend response shape, do not delete `DataTable`, do
  not remove any data from any section.

**Files likely touched:**

- All `frontend/src/components/*Section.tsx` files listed above
- `docs/planning/result_display_implementation_plan.md` — check this item
  when complete

**Acceptance criteria:**

- No polished result page shows a raw detail table open by default.
- Every former raw detail table is reachable via `Show raw table` and
  contains the same data as before.
- `hiddenColumns` and `highlight` behavior preserved everywhere.
- Fallback rendering for query classes without a designed view is
  unchanged.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual: deploy the branch (or run locally) and confirm `Jokic last 10
  games`, `most ppg in 2025 playoffs`, `Lakers record this season`,
  `Jokic vs Embiid this season` all hide raw tables by default and
  reveal them on toggle.

**Reference docs:**

- `docs/planning/result_display_map.md` — "Raw detail table policy"
- Item 1's `RawDetailToggle` API

---

## 3. `[x]` Fix `player_game_summary` last-N truncation

**Why:** `RecentGames` in `PlayerSummarySection.tsx` is hardcoded to
`rows.slice(-5).reverse()` and shows only 4 stats per game. For
`Jokic last 10 games`-style queries, the user expects the full
requested set with richer per-game stats. Map entry calls this out
explicitly and is one of the most user-visible bugs.

**Scope:**

- In `PlayerSummarySection.tsx`'s `RecentGames` component:
  - Remove the `slice(-5)` truncation. Show all rows the backend
    returned, most recent first.
  - Cap defensively at, say, 30 rows to avoid pathological DOM sizes
    when a season query accidentally returns hundreds of games. If the
    backend returned more than the cap, render the first N and show a
    small "showing X of Y games" note.
  - Expand the per-row stat line beyond `pts/reb/ast/minutes`. Add at
    minimum FG, 3P, FT, STL, BLK, TOV when available in the row. Keep
    the existing card style; just fill in more stat tiles.
- Make the section header and count reflect the actual number of games
  rendered, e.g. `Recent Games (10)` — match the map's `Should show:`
  intent.
- Do not change the hero block or other sections in
  `PlayerSummarySection`. Other sections come in item 5.

**Files likely touched:**

- `frontend/src/components/PlayerSummarySection.tsx`
- `frontend/src/components/PlayerSummarySection.module.css` (only if
  layout adjustments needed for more stat tiles)
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `Jokic last 10 games` renders 10 game rows.
- `LeBron last 5 games` renders 5 game rows.
- `Curry this season` does not balloon — capped to 30, with a clear
  "showing 30 of N" note.
- Each game row shows date, W/L badge, opponent, score if available,
  and at least PTS/REB/AST/MIN/FG/3P/FT/STL/BLK/TOV when those fields
  are present.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- PlayerSummary`
- `cd frontend && npm run build`
- Manual: hit the deployed app with `Jokic last 10 games` and
  `LeBron last 5 games` after merge.

**Reference docs:**

- `docs/planning/result_display_map.md` — `player_game_summary` entry
- Existing `PlayerSummarySection.tsx`

---

## 4. `[x]` Leaderboard context completeness

**Why:** Leaderboards are the most-used class. After PR #200 merges
(playoff min-games threshold + initial column-hiding + wins/losses
context), some context still needs polish to match the map's
`Should show:` for `season_leaders` and `season_team_leaders`.

**Scope:**

- Re-read `LeaderboardSection.tsx` after PR #200 has merged. Identify
  any remaining gaps vs. the map's `Should show:` for `season_leaders`
  and `season_team_leaders`. Likely candidates:
  - When metric is `win_pct`, ensure the W-L chip shows in
    `contextItems` if not already added by #200.
  - When metric is a percentage stat (FG%, 3P%, FT%, TS%, eFG%) and a
    companion volume column is present (FGM/FGA, FG3M/FG3A, FTM/FTA),
    add a companion chip showing makes/attempts.
  - When the rendered "metric" priority picks the wrong column for the
    query intent (e.g., `most wins` should show wins as hero, not
    win_pct), wire `metadata.target_metric` (or equivalent) through so
    `metricColumn` honors the query intent rather than priority
    heuristics alone.
- If anything in this scope is already done by #200, skip with an
  inline note `[-]` (skipped, already shipped in #200) instead of
  duplicating.
- Add regression tests for any new behavior.

**Files likely touched:**

- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/LeaderboardSection.module.css` (only if
  layout)
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `best record since 2015` shows W-L context for each row.
- `most wins by a team in a season` shows wins as the hero metric and
  W-L plus games as context.
- `best fg%` (or similar) shows FGM/FGA companion when the row
  has it.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- Leaderboard`
- `cd frontend && npm run build`
- Manual: run the queries above against the deployed app after merge.

**Reference docs:**

- `docs/planning/result_display_map.md` — `season_leaders` and
  `season_team_leaders` entries
- PR #200 (read its merged diff first)

---

## 5. `[x]` `team_record` route polish

**Why:** Match the map's `Should show:` for `team_record`: tighter hero,
opponent-scoped context surfaced clearly, no duplicate detail blocks
(now that raw tables are toggled).

**Scope:**

- In `TeamRecordSection.tsx`:
  - Tighten hero to: team logo, team name, opponent logo+name when the
    query is opponent-scoped, primary record (W-L), win pct, sample
    size, season label, regular/playoff badge.
  - Add supporting team stats when present: PPG, opponent PPG, net
    rating or +/-, REB, AST, 3PM. Use `StatBlock` similar to existing
    treatment, just the right set of fields.
  - For multi-season queries, keep `By Season` available via the raw
    toggle. For single-season queries, the by-season block should not
    appear at all (the underlying `by_season` section may be empty
    anyway — confirm and gate on length).
- No change to backend response shape.

**Files likely touched:**

- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/TeamRecordSection.module.css`
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `Lakers record this season` renders hero with team identity, W-L,
  win pct, games, season label.
- `Celtics record vs Bucks` adds opponent identity to the hero.
- No always-open raw `DataTable` under the hero.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- TeamRecord`
- `cd frontend && npm run build`
- Manual: the example queries above against the deployed app.

**Reference docs:**

- `docs/planning/result_display_map.md` — `team_record` entry

---

## 6. `[ ]` `player_compare` route polish

**Why:** Match the map's `Should show:` for `player_compare`: cleaner
side-by-side cards, real metric-comparison grid with leader highlight
and edge/delta, no duplicated metric tables.

**Scope:**

- In `PlayerComparisonSection.tsx`:
  - Side-by-side player cards: headshot, name, team badge, sample
    size/games, record if available, plus PTS/REB/AST/MIN/TS%/+/-
    when present.
  - Build a real metric-comparison grid (component or inline): metric
    label, Player A value, Player B value, leader highlight, and an
    edge value such as `Jokic +4.9 AST`.
  - Career-vs-season distinction surfaced in the header context.
  - Keep `Player Summary Detail` and `Full Metric Detail` reachable
    only via the raw toggle.
- No backend changes.

**Files likely touched:**

- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/PlayerComparisonSection.module.css`
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `Jokic vs Embiid this season` shows two player cards with hero stats
  and a metric comparison grid with leader highlights and deltas.
- `LeBron vs MJ career` distinguishes career averages clearly in the
  header.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- PlayerComparison`
- `cd frontend && npm run build`
- Manual: example queries above.

**Reference docs:**

- `docs/planning/result_display_map.md` — `player_compare` entry

---

## 7. `[ ]` `player_game_finder` route polish

**Why:** Match the map's `Should show:` for `player_game_finder`: a
finder header with condition + count, richer per-game cards, sensible
default sort.

**Scope:**

- In `PlayerGameFinderSection.tsx`:
  - Add finder summary header: player identity (when player-scoped),
    condition string built from query metadata (e.g., `25+ PTS, 10+ REB`
    or `50-point games`), and a `N games found` count.
  - Per-row card: date, player headshot (when player-scoped), team
    badge, opponent badge with home/away prefix, W/L, score when
    available, PTS/REB/AST/3PM as primary; MIN/FG/3P/FT/STL/BLK/TOV
    when present.
  - Default sort: most recent first; if metadata indicates the query
    is ranked by a metric (e.g., "top scoring games"), sort by that
    metric descending.
- No backend changes.

**Files likely touched:**

- `frontend/src/components/PlayerGameFinderSection.tsx`
- `frontend/src/components/PlayerGameFinderSection.module.css`
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `games where Jokic had over 25 points and over 10 rebounds` renders a
  header with the condition and count, plus richer per-game cards.
- `Curry's 50-point games` renders correctly with the same shape.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- PlayerGameFinder`
- `cd frontend && npm run build`
- Manual: example queries.

**Reference docs:**

- `docs/planning/result_display_map.md` — `player_game_finder` entry

---

## 8. `[ ]` `player_split_summary` route polish

**Why:** Match the map's `Should show:` for `player_split_summary`:
real split cards with edge/delta, not just stacked tables.

**Scope:**

- In `SplitSummaryCardsSection.tsx` (or `SplitSummarySection.tsx` if
  that's where this route renders today — confirm by reading
  `ResultSections.tsx` `case "split_summary"`):
  - Split cards: per-bucket card showing bucket label, games, record
    when available, PTS/REB/AST/MIN/TS%/3P%/+/-.
  - For two-bucket splits (home vs away, wins vs losses, etc.) add a
    small difference row, e.g. `Home +3.2 PPG`.
  - Player identity in a header above the cards.

**Files likely touched:**

- `frontend/src/components/SplitSummaryCardsSection.tsx` and/or
  `SplitSummarySection.tsx`
- Matching CSS modules
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `Jokic home vs away` renders two split cards with stat tiles and a
  diff row.
- `Curry in wins vs losses` renders correctly with the same shape.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test -- Split`
- `cd frontend && npm run build`
- Manual: example queries.

**Reference docs:**

- `docs/planning/result_display_map.md` — `player_split_summary` entry

---

## 9. `[ ]` Streak, occurrence, and playoff section polish

**Why:** Cover the remaining higher-frequency designed sections. Each
is smaller in scope but should match its map entry's `Should show:`.

**Scope:**

- `StreakSection.tsx` — match map entries for `player_streak_finder`
  and `team_streak_finder`. Streak cards with hero length, active vs
  completed badge, date range, during-streak averages.
- `OccurrenceLeaderboardSection.tsx` — match
  `player_occurrence_leaders` and `team_occurrence_leaders`. Hero
  metric is the occurrence count; threshold/condition surfaced as a
  chip.
- `PlayoffSection.tsx` — match the map's `Playoff routes` entry for
  whichever of `playoff_appearances`, `playoff_history`,
  `playoff_matchup_history`, `playoff_round_record` are routed through
  this component. Per-route polish, not one mega-rewrite.
- These can be one PR if the changes per file are small, or split into
  three PRs if any one file's change is non-trivial. Use judgment.

**Files likely touched:**

- The three section files above and their CSS modules
- Frontend tests
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- `Jokic 25-point game streak` renders streak card per the map.
- `most 30-point games this season` renders the occurrence leaderboard
  per the map.
- `Lakers playoff history` renders a playoff history layout per the map.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual: example queries.

**Reference docs:**

- `docs/planning/result_display_map.md` — streak, occurrence, and
  playoff entries

---

## 10. `[ ]` Cross-cutting display rules sweep

**Why:** The map's "Cross-cutting display rules" section names rules
that should apply everywhere. Most are addressed by items above; this
item closes any remaining gaps in one targeted sweep.

**Scope:**

- Audit every section component and `DataTable` for compliance with:
  - Hide internal columns (`player_id`, `team_id`, redundant
    `team_abbr`).
  - Identity treatment: headshots/logos when available, fallback to
    initials/abbreviations.
  - Mobile responsiveness with sticky identity column on horizontally
    scrolling tables.
  - Numeric formatting: per-game stats to 1 decimal, percentages as
    `.xxx`, counts as integers.
  - Freshness banner appears on every result page.
- Fix any drifters in one PR (or split per area if the diff is large).

**Files likely touched:**

- Various `frontend/src/components/*Section.tsx`,
  `DataTable.tsx`, `tableFormatting.ts`
- `docs/planning/result_display_implementation_plan.md` — check this item

**Acceptance criteria:**

- A representative query for each query class passes a quick mobile QA
  pass.
- No section renders raw internal id columns by default.
- Numeric formatting consistent across surfaces.
- Build, typecheck, and tests pass.

**Tests to run:**

- `cd frontend && npm test`
- `cd frontend && npm run build`
- Manual: 1 query per class on phone-sized viewport.

**Reference docs:**

- `docs/planning/result_display_map.md` — "Cross-cutting display rules"

---

## 11. `[ ]` Reconcile map statuses and close out

**Why:** Self-propagating final task. After items 1-10, every audited
route entry in the map should reflect what shipped. This task closes
the loop and decides what's next.

**Scope:**

- For each route entry in `result_display_map.md`:
  - Re-run the example queries against the deployed app.
  - If the rendered display matches the entry's `Should show:`, mark
    the entry `[x]`.
  - If it does not, leave it `[~]` and add an inline note about the
    remaining gap.
- Sweep for any routes still `[?]` (intent written, current display not
  observed) and decide: either flip to `[x]` if intent now matches
  what's rendered, or `[~]` with a follow-up note.
- If meaningful gaps remain, draft a follow-up queue
  (`result_display_followup_queue.md`) listing only the remaining
  per-route work; otherwise, write a short retrospective at the bottom
  of this file noting the queue is closed.
- Update `docs/index.md` if needed.

**Files likely touched:**

- `docs/planning/result_display_map.md`
- `docs/planning/result_display_implementation_plan.md` — check this
  item, add closing retrospective if applicable
- `docs/planning/result_display_followup_queue.md` (new, only if
  needed)
- `docs/index.md`

**Acceptance criteria:**

- Every audited route in the map is `[x]` or `[~]` with a note.
- This file's items are all `[x]` (or `[-]` with notes).
- Either the queue is formally closed or a follow-up queue exists.

**Tests to run:**

- None (docs only)

**Reference docs:**

- `docs/planning/result_display_map.md`
- This file's items

---

## Appendix: progress tracking

When all items above are checked `[x]` (or `[-]` with notes), the queue
is complete. The retrospective on item 11 is the closure artifact.
