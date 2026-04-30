# Component Experience Plan

> **Role: Track A Part 2 plan for the product polish master plan.** Builds
> opinionated, designed layouts for every query class, replacing the
> generic-table approach with purpose-built component experiences.
>
> Whole-plan completion authority is
> [`product_polish_master_plan.md`](./product_polish_master_plan.md). This
> doc covers Track A Part 2 only.

---

## Goal

Every query class — summary, leaderboard, comparison, finder, streak,
record, split, playoff, occurrence, count, head-to-head — gets a real
designed layout that fits its specific data shape. Hero stat treatments
where there's a hero stat. Charts and sparklines where they aid
comprehension. Card-based result envelopes throughout. Mobile responsive on
every layout.

By the end of this plan, the product no longer renders any query result as
a generic table dump. Every result feels designed for the question that
produced it.

---

## Why this comes after Part 1

Part 2 builds on every primitive Part 1 ships. Specifically:

- The Card and StatBlock primitives are the building blocks for nearly
  every component layout
- The DataTable primitive handles the residual cases where tabular display
  is genuinely the right choice
- The Avatar (player headshot) and TeamBadge primitives are used in nearly
  every layout
- The team-color theming system applies automatically only for safe
  single-team contexts; mixed player, comparison, leaderboard, and
  multi-team views stay neutral except for identity badges

Building Part 2 against finished primitives is fast and consistent.
Building it against partial primitives means each component invents its
own pieces and the design fragments.

---

## Scope of query classes

Each of these gets its own opinionated layout. The order roughly matches
how often they're used and how much they benefit from a designed layout:

1. **Player summary** (`Jokic last 10`, `Embiid this season`) — most used.
   Hero PPG/REB/AST treatment. Player headshot prominent. Win/loss record.
   Sparkline of game-by-game scoring. Secondary stat block with shooting
   percentages. By-season collapsible.

2. **Leaderboard** (`top scorers this season`) — high frequency. Ranked
   rows with player headshots and team logos. Stat value prominent on the
   right. The #1 row gets emphasis. Tabular numerals for clean alignment.

3. **Player comparison** (`Jokic vs Embiid this season`) — high signal
   when used. Side-by-side cards with prominent headshots and team badges.
   Difference highlights between the two columns. Mixed-player views stay
   neutral unless a later product decision explicitly expands scoped color.

4. **Player game finder** (`Curry 5+ threes`, `LeBron best games`) — list
   of game cards rather than table rows. Each card shows opponent, date,
   W/L, key stats. Tappable cards on mobile.

5. **Team summary** (`Lakers this season`) — like player summary but with
   team-level stat treatment. Team logo prominent. Record callout. Pace,
   off/def rating hero stats.

6. **Team record** (`Lakers record vs Celtics`) — record callout
   prominent. Win-loss visual representation. Sample-size note when
   filters reduced the sample.

7. **Streak** (`Jokic longest 30-point streak`) — streak length as the
   hero. Visual representation of the games in the streak as a row of
   pills or cells with stat values.

8. **Split** (`Celtics home away`) — side-by-side comparison treatment
   like player comparison, but for the same entity across split contexts.

9. **Occurrence count** (`most 40-point games this season`) — hybrid of
   leaderboard and finder. Ranked players with their counts, expandable to
   show the actual games.

10. **Head-to-head** (`Lakers vs Celtics this season`) — matchup-card
    treatment with both team identities visible, series record, and
    individual game list. Avoid full-surface team-color splits in mixed-team
    views; use logos/badges and restrained accents instead.

11. **Playoff history** — series-and-rounds treatment. Likely the most
    custom layout since playoff data has unique shape (series, rounds,
    bracket position).

12. **Anything else** that emerges from the parser's surface — handled
    case-by-case in late phases.

---

## Phase structure

Each query class gets one or two phases depending on complexity. High-use
classes go first.

### Phase C1 — Player summary layout

Goal: redesign the player summary result. Hero stats, headshot, sparkline
chart of game-by-game points across the queried timeframe, secondary stat
block, by-season expandable. Mobile responsive.

Status: complete. `PlayerSummarySection.tsx` owns only `player_game_summary`
responses and preserves the generic summary fallback for team, playoff, and
unknown summary routes. Player-summary API responses now expose an additive
`game_log` section for the exact filtered sample, and the UI uses that section
for the scoring sparkline/recent-games context without a hidden refetch.

### Phase C2 — Leaderboard layout

Goal: redesign leaderboard results into ranked-row cards with imagery,
the stat value prominent, the #1 row emphasized.

Status: complete. `LeaderboardSection.tsx` owns `query_class: "leaderboard"`
rendering with ranked rows, player/team identity accents, promoted metric
values, wrapped context/qualifier metadata, restrained #1 emphasis, and a full
detail table. Ranking, filtering, qualifiers, and metric computation remain in
the engine/API; sparse or unusual leaderboard rows degrade through conservative
field inspection and the detail table.

### Phase C3 — Player comparison layout

Goal: side-by-side comparison cards with player/team identity, neutral mixed
context treatment, and difference highlighting.

Status: complete. `PlayerComparisonSection.tsx` owns only `player_compare`
responses, promotes supplied summary rows into player identity cards, promotes
supplied metric rows into comparison cards with conservative leader/tie
emphasis, preserves full detail tables, and keeps team, matchup, playoff,
decade, and unknown comparison-shaped routes on the generic fallback.

### Phase C4 — Player game finder layout

Goal: list of game cards instead of table rows.

Status: active. Phase C4 starts with a finder row-shape inventory because
`query_class: "finder"` covers player game finders plus team game finders,
count detail, grouped boolean outputs, and future finder-shaped routes that
must keep the generic fallback until their later phases.

### Phase C5 — Team summary, team record, split layouts

Goal: bundle three closely-related team-context layouts — summary, record,
and split — since they share visual patterns. Reduces phase count without
losing scope.

### Phase C6 — Streak and occurrence layouts

Goal: bundle these because both are "events over time" shapes that benefit
from similar visual treatments.

### Phase C7 — Head-to-head and playoff layouts

Goal: matchup card and playoff history — the two most custom shapes.

### Phase C8 — Mobile pass for every component

Goal: dedicated phase to verify and fix every redesigned component on
mobile. Each component gets explicit mobile acceptance criteria during
its phase, but a final pass is worth doing once everything ships.

### Phase C9 — Retrospective and Part 3 handoff

Goal: capture learnings, draft `first_run_and_polish_plan.md` (Track A
Part 3) and `phase_p1_work_queue.md` (Part 3's first queue).

---

## Done definition for Track A Part 2

Part 2 is done when:

1. Every query class listed above has a purpose-built layout that uses
   primitives from Part 1
2. No query class falls back to a generic data-table treatment as its
   primary rendering
3. Charts appear where they aid comprehension (sparklines on summaries,
   distribution charts on streaks, etc.) — not gratuitously, but where
   they matter
4. Every component has explicit mobile acceptance criteria met
5. Team-color theming applies automatically for safe single-team contexts,
   while mixed player/team views remain neutral except for identity badges
6. All existing tests pass — no functional regression
7. Visual quality bar met: every result feels designed for its question.
   The product no longer feels like "tables but dark mode"

---

## Visual quality bar for Part 2

This is what separates Part 2 from "we just put tables in cards":

- Hero stats use the stat-hero typography scale and feel like the answer
  to the question
- Player headshots and team logos thread through naturally — they're not
  decorative, they're part of the information hierarchy
- Charts and sparklines render at appropriate sizes — not tiny
  afterthoughts, not so big they dominate
- Tabular numerals make stat columns align beautifully
- Team colors add personality where they belong (single-team context cards)
  but never overwhelm or imply a winner in mixed-team views
- Layouts feel intentional — every element has a reason to be where it is
- Mobile layouts adapt the design rather than just shrinking it

---

## Phase queue handoff

Phase C1's queue was drafted by Phase V5's retrospective (the final phase
of Part 1): [`phase_c1_work_queue.md`](./phase_c1_work_queue.md). Each
subsequent phase's queue is drafted by the prior phase's retrospective.
