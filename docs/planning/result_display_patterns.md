# Result Display Patterns — Architecture

> **Role:** The implementation architecture for result display. The
> [`result_display_map.md`](./result_display_map.md) describes *what*
> each route should show. This doc describes *how* the code is
> structured to render it consistently across all routes.
>
> **Adopted:** 2026-05-03. Replaces the previous one-component-per-route
> approach.

---

## Why this exists

The previous approach had one section component per route family
(`PlayerSummarySection`, `LeaderboardSection`, `PlayerGameFinderSection`,
`TopGamesSection`, `LineupSection`, etc. — 16 components and growing).
Each component was a fresh design pass, so adjacent routes drifted apart
visually even though their results had similar shape. Card-per-row
layouts crept into routes that should have been tabular. Hero treatments
diverged. Spacing, identity treatment, and chip rules were
re-invented per file.

The pattern-based approach makes consistency structural rather than
aspirational: routes that share an output shape share rendering code, so
they can't drift.

---

## The patterns

A small number of result patterns covers most of the engine's routes.
Each pattern is a single React component that consumes a typed config
and renders a result page in the StatMuse-baseline shape (sentence hero
+ dense answer table — see
[`result_display_map.md`](./result_display_map.md) "Default answer
pattern").

### Initial set

The initial pattern set is intentionally small. Add patterns as concrete
need emerges, not speculatively.

1. **`EntitySummaryResult`** — single-subject summary (one player, one
   team, one lineup). Hero card + averages strip. No row list.
   *Routes:* `team_record`, broad `player_game_summary` season/career
   variants, `lineup_summary`, `playoff_round_record`.

2. **`GameLogResult`** — list of games matching a player or team.
   Hero summary strip + dense game-log table with
   `Average`/`Total` footer rows.
   *Routes:* `player_game_summary` (last-N variant), `player_game_finder`,
   `game_finder`, `top_player_games`, `top_team_games`,
   `game_summary` (single-game variant treated as a 1-row game-log).

3. **`LeaderboardResult`** — ranked list of N entities by a queried
   metric. Hero sentence + dense leaderboard table with the queried
   metric column visually emphasized.
   *Routes:* `season_leaders`, `season_team_leaders`,
   `team_record_leaderboard`, `player_stretch_leaderboard`,
   `player_occurrence_leaders`, `team_occurrence_leaders`,
   `lineup_leaderboard`, `playoff_appearances`.

4. **`ComparisonResult`** — exactly two subjects, side-by-side
   comparison with metric-by-metric edge.
   *Routes:* `player_compare`, `team_compare`, `team_matchup_record`,
   `playoff_matchup_history`. **Deferred until other patterns are
   stable** — comparisons are the most complex shape and should be
   built last.

5. **`SplitResult`** — same subject, multiple buckets (home vs away,
   wins vs losses, on vs off).
   *Routes:* `player_split_summary`, `team_split_summary`,
   `player_on_off`.

6. **`StreakResult`** — streak events with hero length, date range, and
   during-streak averages.
   *Routes:* `player_streak_finder`, `team_streak_finder`.

7. **`PlayoffHistoryResult`** — playoff resume / season-by-season
   playoff record (treated as its own pattern because the per-season
   structure with round-reached + result is distinct from a leaderboard).
   *Routes:* `playoff_history`.

8. **`FallbackTableResult`** — generic raw-table renderer for any route
   that does not yet have a dedicated pattern. Always available so new
   engine routes do not break the UI before a pattern exists.

### Composition

Compound results stack patterns vertically. The route's config picks
which patterns to render and in what order.

Example — `player_game_summary` for `Jokic last 10 games`:

```
EntitySummaryResult (hero sentence + summary strip)
GameLogResult       (game log table with Average/Total footers)
```

Example — `player_compare` if you want both a metric grid AND
season-by-season breakdowns:

```
ComparisonResult    (metric grid)
LeaderboardResult   (per-season ranked rows for each player, optional)
```

Composition is opt-in per route. Most routes use exactly one pattern.

---

## File layout

```
frontend/src/components/results/
  ResultRenderer.tsx                  # entrypoint; reads route, picks pattern(s)

  patterns/
    EntitySummaryResult.tsx
    GameLogResult.tsx
    LeaderboardResult.tsx
    ComparisonResult.tsx              # build last
    SplitResult.tsx
    StreakResult.tsx
    PlayoffHistoryResult.tsx
    FallbackTableResult.tsx

  primitives/                         # shared building blocks used by patterns
    ResultShell.tsx                   # outer container, freshness banner placement
    ResultHero.tsx                    # colored hero card with sentence + illustration
    ResultTable.tsx                   # styled answer table (extends DataTable)
    EntityIdentity.tsx                # inline headshot/logo + name treatment
    ContextChipRow.tsx                # disambiguation note, season chips, etc.
    StatStrip.tsx                     # horizontal stat tile row (used in summary heroes)
    MetricRow.tsx                     # one row of the comparison metric grid
    GameLogRow.tsx                    # game-log table row
    RankedRow.tsx                     # leaderboard table row
    RawDetailToggle.tsx               # already exists; kept for genuinely-secondary tables

  config/
    routeToPattern.ts                 # the route → pattern mapping
    statPresets.ts                    # per-pattern default column sets
    metricLabels.ts                   # display labels for stat keys
```

`ResultSections.tsx` (the current router) is replaced by
`ResultRenderer.tsx`. The 16 existing section components get deleted as
their routes are migrated to patterns.

---

## The route → pattern mapping

`config/routeToPattern.ts` is the single config file that wires every
engine route to one or more patterns plus per-route configuration.

Sketch:

```ts
type PatternConfig =
  | { type: "entity_summary"; ... }
  | { type: "game_log"; ... }
  | { type: "leaderboard"; ... }
  | { type: "comparison"; ... }
  | { type: "split"; ... }
  | { type: "streak"; ... }
  | { type: "playoff_history"; ... }
  | { type: "fallback_table" };

export function routeToPattern(data: QueryResponse): PatternConfig[] {
  const route = data.route;
  switch (route) {
    case "player_game_summary":
      return isLastNSample(data)
        ? [entitySummaryFor(data), gameLogFor(data)]
        : [entitySummaryFor(data)];
    case "player_game_finder":   return [gameLogFor(data)];
    case "season_leaders":       return [leaderboardFor(data)];
    case "season_team_leaders":  return [leaderboardFor(data)];
    case "player_compare":       return [comparisonFor(data)];
    case "player_split_summary": return [splitFor(data)];
    // ...
    default:                     return [{ type: "fallback_table" }];
  }
}
```

`ResultRenderer.tsx` reads the array of `PatternConfig` and stacks the
matching pattern components in order.

This file is *built incrementally as patterns ship*, not pre-written
when no patterns exist.

---

## Configuration discipline

Each pattern's config should be tightly scoped. Avoid flag creep — if a
pattern needs more than ~6-8 configuration knobs, the abstraction is
probably too broad and should be split into two patterns.

Per-pattern config should describe **what data goes where**, not **how
it looks**. Visual treatment lives in the pattern itself; routes do not
override visual treatment.

Good config knobs:

- which `sections` key contains the rows
- which columns to feature as primary vs secondary
- which metric to highlight as the queried column
- whether to show rank
- whether to render footer Average/Total rows
- the title/sentence template

Bad config knobs:

- spacing overrides
- color overrides
- "show as cards instead of rows"
- visual variant flags

If a route needs a different visual treatment, it needs a different
pattern. Configuration is for content, not chrome.

---

## What replaces what

| Old | New |
|-----|-----|
| `ResultSections.tsx` (route-by-route switch) | `ResultRenderer.tsx` + `routeToPattern.ts` |
| `LeaderboardSection.tsx`, `OccurrenceLeaderboardSection.tsx` | `LeaderboardResult.tsx` |
| `PlayerSummarySection.tsx`, `TeamSummarySection.tsx`, `TeamRecordSection.tsx` | `EntitySummaryResult.tsx` |
| `PlayerGameFinderSection.tsx`, `FinderSection.tsx`, top-game components | `GameLogResult.tsx` |
| `PlayerComparisonSection.tsx`, `ComparisonSection.tsx`, `HeadToHeadSection.tsx` | `ComparisonResult.tsx` |
| `SplitSummaryCardsSection.tsx`, `SplitSummarySection.tsx` | `SplitResult.tsx` |
| `StreakSection.tsx` | `StreakResult.tsx` |
| `PlayoffSection.tsx` | `PlayoffHistoryResult.tsx` (and `LeaderboardResult` for playoff_appearances) |
| `SummarySection.tsx`, `CountSection.tsx` (fallback paths) | `FallbackTableResult.tsx` |

Old components are deleted as their routes migrate. No long-tail of
half-dead components.

---

## Migration approach

**Build patterns one at a time. Migrate routes that fit. Validate.
Then build the next pattern.**

Do not pre-build the whole pattern set before any route is migrated.
That's the same "spec everything before validating anything" trap that
produced the recent polish regression.

For each pattern:

1. Build the pattern component against the StatMuse-baseline spec for
   one of its target routes (the simplest one).
2. Write the route → pattern mapping for that one route.
3. Wire `ResultRenderer.tsx` to pick the new pattern when that route
   appears.
4. Ship and validate against the deployed app.
5. If it feels right, migrate other routes that fit the pattern — no
   pattern code changes, just config additions.
6. If it doesn't feel right, fix the pattern *now* before more routes
   depend on it.
7. Once the pattern is stable across all routes that map to it, delete
   the old per-route components those routes used to use.
8. Move to the next pattern.

The order is in the implementation queue
([`result_display_implementation_plan.md`](./result_display_implementation_plan.md)).

---

## Risks and mitigations

**Premature pattern abstraction.** Risk: building a pattern that doesn't
fit reality, then having to retrofit it. Mitigation: ship one route per
pattern before migrating others.

**Configuration creep.** Risk: each new route adds another flag until
the pattern is unmaintainable. Mitigation: enforce the ~6-8 knob ceiling
per pattern. If you need a new flag for visual variation, build a new
pattern instead.

**Migration limbo.** Risk: half the routes use old components, half use
new patterns, the codebase has both forever. Mitigation: each pattern
PR explicitly deletes the old components for routes it has fully
absorbed. No "we'll clean it up later."

**Routes that don't fit.** Risk: forcing a route into a pattern it
shouldn't use, recreating the original card-on-tabular-data regression.
Mitigation: `FallbackTableResult` is always available. Better to fall
back than to force-fit. Add a new pattern only when 2+ routes need a
shape no existing pattern covers.
