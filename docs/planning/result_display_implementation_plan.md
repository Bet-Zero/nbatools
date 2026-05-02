# Result Display Map — Implementation Plan

## Goal

Implement the display rules from:

- `docs/planning/result_display_map.md`

Primary goal:

> Make polished cards/lists the default output, while keeping every raw table available behind a collapsed toggle.

This plan should **not** remove raw table logic. It should hide raw tables by default everywhere while preserving them as an inspection/debug/export/future advanced-view layer.

---

## Phase 1 — Shared Raw Table Toggle

### Objective

Create one reusable component for raw/detail table sections so every route handles tables the same way.

### New component

Create something like:

```txt
frontend/src/components/RawDetailToggle.tsx
frontend/src/components/RawDetailToggle.module.css
```

Possible props:

```ts
type RawDetailToggleProps = {
  title: string;
  rows: SectionRow[];
  highlight?: boolean;
  hiddenColumns?: Set<string>;
  defaultOpen?: boolean;
};
```

### Behavior

- Renders nothing if rows are empty.
- Shows a compact collapsed control by default.
- Button text:
  - Closed: `Show raw table`
  - Open: `Hide raw table`
- Shows the table only when opened.
- Keeps existing `DataTable` behavior unchanged inside the toggle.
- Supports `highlight`.
- Supports `hiddenColumns`.
- Must be keyboard accessible.
- Must work on mobile.

### Key rule

Do **not** change backend response data.
Do **not** delete `DataTable`.
Do **not** remove detail sections from result components.

Only wrap raw tables in the shared collapsed component.

---

## Phase 2 — Replace Always-Open Raw Tables

### Objective

Find every component that renders a raw/detail `DataTable` under a polished result and wrap it with the shared toggle.

Likely files:

```txt
frontend/src/components/PlayerSummarySection.tsx
frontend/src/components/TeamRecordSection.tsx
frontend/src/components/PlayerComparisonSection.tsx
frontend/src/components/LeaderboardSection.tsx
frontend/src/components/PlayerGameFinderSection.tsx
frontend/src/components/SplitSummaryCardsSection.tsx
frontend/src/components/StreakSection.tsx
frontend/src/components/OccurrenceLeaderboardSection.tsx
frontend/src/components/PlayoffSection.tsx
frontend/src/components/HeadToHeadSection.tsx
frontend/src/components/TeamSummarySection.tsx
```

Also check fallback/general components:

```txt
frontend/src/components/SummarySection.tsx
frontend/src/components/ComparisonSection.tsx
frontend/src/components/FinderSection.tsx
frontend/src/components/SplitSummarySection.tsx
frontend/src/components/CountSection.tsx
frontend/src/components/ResultSections.tsx
```

### Implementation rule

Where code currently does this:

```tsx
<SectionHeader title="Full Summary" />
<DataTable rows={summary} />
```

Change to:

```tsx
<RawDetailToggle title="Full Summary" rows={summary} />
```

Where code currently does this:

```tsx
<DataTable rows={leaderboard} highlight hiddenColumns={SYSTEM_COLUMNS} />
```

Change to:

```tsx
<RawDetailToggle
  title="Full Leaderboard"
  rows={leaderboard}
  highlight
  hiddenColumns={SYSTEM_COLUMNS}
/>
```

### Acceptance criteria

- No polished result page shows raw tables open by default.
- Every previous raw table can still be opened.
- Existing hidden column behavior still works.
- Existing highlighted table behavior still works.
- No query loses access to underlying detail rows.

---

## Phase 3 — `player_game_summary` Last-N Fix

### Objective

Fix the biggest obvious display bug:

> `Recent Games` is hardcoded to show only 5 games even when the user asks for 10.

### Target file

```txt
frontend/src/components/PlayerSummarySection.tsx
```

### Current issue

The current recent games logic slices to 5:

```tsx
const visibleRows = rows.slice(-5).reverse();
```

### Desired behavior

For last-N queries:

- Show all requested game-log rows returned by the backend.
- Reverse/order them cleanly so most recent is first.
- Keep the count accurate.
- Do not truncate to 5 unless the query is a broad season/career summary.

### Implementation options

Simpler first pass:

- If `game_log.length <= 20`, show all rows.
- If huge game log, show a preview with an expansion control.

Better second pass:

- Read metadata/query context and distinguish:
  - last-N query → show all N
  - season/career query → preview only

For the first implementation pass, the acceptable safe version is:

> Show all `game_log` rows up to a reasonable cap, and do not hardcode 5.

### Acceptance criteria

- `Jokic last 10 games` shows 10 games if backend returns 10.
- `LeBron last 5 games` shows 5 games.
- Game rows still show date, W/L, opponent, PTS, REB, AST, MIN.
- Raw summary tables remain hidden behind toggle.

---

## Phase 4 — Leaderboard Context Fixes

### Objective

Make leaderboard rows answer the query better without opening raw tables.

### Target file

```txt
frontend/src/components/LeaderboardSection.tsx
```

### Fixes

#### 1. Record context

For team record leaderboards, show wins/losses as context.

Example:

```txt
#1 2015-16 Warriors
.890 Win Pct
73-9 · 82 games · Regular Season
```

#### 2. Requested metric should stay primary

The hero metric should match the query route/metric when available.

Avoid cases where the visual metric becomes the wrong numeric field just because it appears first.

#### 3. Percentage companion context

Already partially exists. Make sure this works cleanly for:

- win pct → W-L
- FG% → FGM/FGA
- 3P% → 3PM/3PA
- FT% → FTM/FTA

### Acceptance criteria

- `best record since 2015` shows W-L context.
- `most wins by a team in a season` shows wins as the hero metric and W-L/games as context.
- `most ppg` shows PPG/PTS metric, not games or sample size.
- Raw leaderboard table is hidden by default but openable.

---

## Phase 5 — High-Usage Route Polish

After Phase 1–4, move route-by-route.

### 5A — `team_record`

Target:

```txt
frontend/src/components/TeamRecordSection.tsx
```

Improve:

- context display
- opponent-scoped record display
- secondary stats if available
- raw tables collapsed

### 5B — `player_compare`

Target:

```txt
frontend/src/components/PlayerComparisonSection.tsx
```

Improve:

- metric comparison cards
- edge/delta display
- career vs season context
- raw tables collapsed

### 5C — `player_game_finder`

Target:

```txt
frontend/src/components/PlayerGameFinderSection.tsx
```

Improve:

- finder summary header
- richer stat rows
- sorting behavior
- raw table collapsed

---

## Phase 6 — Secondary Route Coverage

Once the main routes feel good, apply the same standards to:

```txt
SplitSummaryCardsSection.tsx
StreakSection.tsx
OccurrenceLeaderboardSection.tsx
PlayoffSection.tsx
HeadToHeadSection.tsx
TeamSummarySection.tsx
```

Main rule:

> Keep their current polished display, but collapse raw tables and add missing context chips/stats where the display map calls for it.

---

## Validation Plan

### Run checks

Use whatever scripts exist in the repo, likely:

```bash
npm run build
npm run typecheck
npm run lint
```

If the repo has frontend-specific commands, use those instead.

### Manual UI queries to test

Run these in the app:

```txt
Jokic last 10 games
LeBron last 5 games
Curry this season
most ppg in 2025 playoffs
top 10 scorers this season
best record since 2015
most wins by a team in a season
Lakers record this season
Celtics record vs Bucks
Jokic vs Embiid this season
games where Jokic had over 25 points and over 10 rebounds
```

For each query verify:

- polished result appears first
- raw table is hidden by default
- raw table can be opened
- no detail data disappeared
- mobile layout does not break
- no obvious duplicate open tables remain

---

## Suggested First Agent Task

Use this as the first implementation task. Do not combine it with every route polish change.

```md
# Task: Implement collapsed raw detail tables across result displays

## Repo / Branch

Repo: Bet-Zero/nbatools  
Branch: docs/result-display-map

## Source of truth

Read and follow:

- docs/planning/result_display_map.md
- docs/planning/result_display_implementation_plan.md

Pay special attention to:

- Raw detail table policy
- Cross-cutting display rules
- Implementation priority

## Goal

Create a reusable collapsed raw table/detail component and replace always-open raw DataTable detail sections across result display components.

The goal is NOT to remove raw tables. The goal is to keep them available but hidden by default.

## Required behavior

- Raw/detail tables must be collapsed by default.
- A user must be able to reveal each table with a consistent toggle.
- The table data must remain available.
- Existing DataTable behavior must remain intact.
- Existing `highlight` behavior must remain intact.
- Existing `hiddenColumns` behavior must remain intact.
- Polished cards/lists should remain the primary display.

## Files to inspect

- frontend/src/components/ResultSections.tsx
- frontend/src/components/DataTable.tsx
- frontend/src/components/PlayerSummarySection.tsx
- frontend/src/components/TeamRecordSection.tsx
- frontend/src/components/PlayerComparisonSection.tsx
- frontend/src/components/LeaderboardSection.tsx
- frontend/src/components/PlayerGameFinderSection.tsx
- frontend/src/components/SplitSummaryCardsSection.tsx
- frontend/src/components/StreakSection.tsx
- frontend/src/components/OccurrenceLeaderboardSection.tsx
- frontend/src/components/PlayoffSection.tsx
- frontend/src/components/HeadToHeadSection.tsx
- frontend/src/components/TeamSummarySection.tsx
- Also inspect fallback/general sections that render DataTable directly.

## Implementation steps

1. Create a shared component, likely:
   - frontend/src/components/RawDetailToggle.tsx
   - frontend/src/components/RawDetailToggle.module.css

2. Component should accept:
   - title
   - rows
   - highlight
   - hiddenColumns
   - defaultOpen, default false

3. Component should:
   - render nothing for empty rows
   - show a collapsed button/control by default
   - show DataTable only after opening
   - be keyboard accessible
   - work on mobile

4. Replace always-open raw detail DataTable sections with RawDetailToggle.

5. Do not change backend query response shape.

6. Do not delete DataTable.

7. Do not remove raw table data access.

## Acceptance criteria

- No raw detail table is open by default in the main polished result routes.
- Every former raw detail table can still be opened.
- Existing hidden column behavior still works.
- Existing highlighted table behavior still works.
- Build/typecheck/lint pass, or document exact failures if unrelated.

## Validation commands

Run the project’s available validation commands. At minimum, try:

npm run build
npm run typecheck
npm run lint

If a command does not exist, record that clearly.

## Manual verification queries

Use the app or available query harness to check:

- Jokic last 10 games
- LeBron last 5 games
- Curry this season
- most ppg in 2025 playoffs
- top 10 scorers this season
- best record since 2015
- Lakers record this season
- Jokic vs Embiid this season
- games where Jokic had over 25 points and over 10 rebounds

For each, verify:

- polished result is visible by default
- raw table is hidden by default
- raw table can be opened
- no data disappears

## Return package

Create a markdown return package under:

return_packages/result_display/

Include:

- files changed
- summary of implementation
- raw table toggle behavior
- validation commands run and results
- manual queries tested and results
- any routes/components not fully covered
- any follow-up recommendations
```

---

## Recommendation

Start with the first agent task only.

Do **not** ask the agent to fix all visual route polish in the same pass. The raw table toggle is clean, scoped, and high-value. Then the next task can be `player_game_summary` plus leaderboard fixes.
