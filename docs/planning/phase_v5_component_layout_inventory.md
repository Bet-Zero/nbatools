# Phase V5 Component Layout Inventory

> **Role:** Readiness inventory for Track A Part 2 component-layout work.
> This records the current renderer owners, available structured data, identity
> coverage, and gaps before Phase C1 starts player-summary layout work.

---

## Goal

Part 2 should replace generic table-first result rendering with purpose-built
layouts without moving query parsing, filtering, or analytics into React. This
inventory names the current owners and the data contracts those layouts can
consume today.

This document changes no runtime behavior.

---

## Sources Reviewed

- `docs/planning/component_experience_plan.md`
- `docs/reference/result_contracts.md`
- `docs/planning/phase_v5_part1_completion_audit.md`
- `src/nbatools/query_service.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/api.py`
- `frontend/src/api/types.ts`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/SplitSummarySection.tsx`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- Representative structured queries through `execute_natural_query()`.

---

## Current Renderer Ownership

| Query class / family | Current owner | Current sections | Notes for Part 2 |
| --- | --- | --- | --- |
| `summary` - player summary | `SummarySection.tsx` | `summary`, optional `by_season` | Same renderer also handles team summary, team record summaries, and playoff summaries. C1 should split the player-summary experience by route or metadata, while preserving a generic summary fallback. |
| `summary` - team summary / record | `SummarySection.tsx` | `summary`, optional `by_season` | Has `team_context` in metadata for single-team theming and logo use. Current summary rows do not include pace, offensive rating, or defensive rating. |
| `summary` - playoff summary | `SummarySection.tsx` | `summary`, optional `by_season` | Playoff routes currently reuse the summary class and rely on caveats for coverage limits. There is no playoff-specific renderer. |
| `leaderboard` | `LeaderboardSection.tsx` | `leaderboard` | Handles player, team, top-game, record, occurrence, and playoff leaderboards. Rows are table-ready but not yet card/rank-row ready by contract. |
| `comparison` | `ComparisonSection.tsx` | `summary`, `comparison` | Handles player, team, head-to-head, playoff matchup, and decade matchup comparisons. The `comparison` table uses display names as metric columns. |
| `split_summary` | `SplitSummarySection.tsx` | `summary`, `split_comparison` | Handles player and team splits. Bucket rows are ready for side-by-side layout, but labels are still raw bucket values. |
| `finder` | `FinderSection.tsx` | `finder` | Handles player and team game finders. Current rows are game-card-ready for many fields, but filter intent is not structured for display. |
| `streak` | `StreakSection.tsx` | `streak` | Handles player and team streak finders. Current rows have streak spans and aggregates, but not per-game values inside each streak. |
| `count` | `ResultSections.tsx` fallback | `count`, optional `finder` | No dedicated count renderer. Count intent currently falls through to generic section rendering. |
| Unknown / future classes | `ResultSections.tsx` fallback | Any non-empty section | Uses `Card`, `SectionHeader`, and `DataTable` as a safety net. Part 2 should shrink this fallback surface over time, not remove it prematurely. |

Every explicit section renderer still uses the NBA-specific `DataTable`
wrapper as its primary result body. `SummarySection` adds a small `StatBlock`
for the first numeric summary fields, but the query-class experience is still
table-first.

---

## Identity And Context Coverage

### Metadata

The API response already exposes the identity fields Part 1 added:

- `player_context`: `{ player_id, player_name }`
- `players_context`: array of player contexts for bounded comparisons
- `team_context`: `{ team_id, team_abbr, team_name }`
- `teams_context`: array of team contexts for bounded team comparisons
- `opponent_context`: opponent team identity when an opponent slot resolves

`ResultEnvelope.tsx` consumes singular player, team, and opponent context for
metadata chips. Plural `players` and `teams` still render as joined text, even
when plural context arrays are present.

Scoped team theming is intentionally guarded by `resolveScopedTeamTheme()`: it
only applies when there is a safe single-team subject and no player subject or
multi-team context.

### Rows

`DataTable.tsx` can render player and team identity directly when rows expose
the expected fields:

- Player cells use `player_name` or `player`, plus `player_id` when present.
- Team cells use `team`, `team_name`, `team_abbr`, `opponent`,
  `opponent_team_name`, or `opponent_team_abbr`.
- Team logo resolution can use `team_id` / `opponent_team_id` when present,
  but falls back to abbreviation/name when ids are missing.

Representative current row coverage:

| Result family | Useful identity fields present today | Gaps for designed layouts |
| --- | --- | --- |
| Player summary | `metadata.player_context`; summary row has `player_name` | No summary-row `player_id`, team id, team abbreviation, or latest team context. |
| Team summary / record | `metadata.team_context`; summary row has `team_name` | Summary row does not consistently carry `team_id` or `team_abbr`; metadata is the reliable identity source. |
| Player leaderboard | Rows include `player_name`, `player_id`, and `team_abbr` | Often no `team_id`; ranking metric is a column, not explicit metadata. |
| Team leaderboard | Rows usually include `team_abbr` and `team_name`; some routes include `team_id` | Playoff/record leaderboard routes vary in id coverage. |
| Comparison | Metadata exposes `players_context` or `teams_context`; summary rows have display names | Comparison metric columns are display names, not stable ids. |
| Finder | Player finder rows include `player_name`, `player_id`, team/opponent names and abbreviations | Finder row projections do not consistently include `team_id` or `opponent_team_id`. |
| Streak | Rows include `player_name` or team display fields depending route | No per-game identity detail inside a streak span. |
| Split | Metadata exposes single player/team context; rows expose bucket values | Bucket labels need presentation mapping; row identity is mostly metadata-driven. |
| Count | Metadata follows the underlying route; entity count can include a `finder` detail section | No dedicated count identity or event contract beyond underlying result sections. |
| Playoff | Metadata exposes team context for team-scoped routes; rows expose team names/abbreviations in leaderboards | No dedicated playoff identity/series contract; historical coverage caveats matter. |

---

## First C1 Player-Summary Data Needs

C1 can start a real player-summary layout with current data, but the full
planned experience needs one engine/API addition.

Ready now:

- Hero identity: `metadata.player_context.player_id` and `player_name` support
  a prominent headshot and name.
- Hero stats: `summary[0]` exposes `pts_avg`, `reb_avg`, `ast_avg`, `games`,
  `wins`, `losses`, `win_pct`, shooting splits, minutes, plus-minus, and
  sample-aware rate metrics.
- Season breakdown: `by_season` exists for collapsible detail.
- Freshness and caveats: `current_through`, `notes`, and `caveats` already flow
  through the query envelope.

Needed for the full C1 target:

| Need | Category | Reason |
| --- | --- | --- |
| A game-by-game series for the queried sample, at least `game_date`, `game_id`, opponent identity, `wl`, `pts`, `reb`, `ast`, and minutes | Engine output + API/result-contract | The planned scoring sparkline and recent-game context should not be reconstructed client-side or fetched with a second hidden query. |
| Resolved sample date window for `last N`, `since`, and similar filters | Engine output | Metadata currently shows `start_date` / `end_date` as `null` for representative `last 10` player summaries. |
| Optional latest/team-at-sample context for player summaries | API/result-contract | A player hero may need a small team badge, but player-subject results should remain neutrally themed unless a product decision changes the scoped-team guard. |
| Stable metric priority for summary hero stats | Frontend-only | The renderer can choose `pts_avg`, `reb_avg`, `ast_avg`, record, and shooting splits from existing fields without engine computation. |
| Route-specific player summary ownership | Frontend-only | `SummarySection` needs a player-summary branch or child component keyed by route/metadata so team and playoff summaries do not inherit player-specific layout. |

Recommended C1 starting point: build the player-summary card structure from
current `summary`, `by_season`, and `player_context`, and schedule the
game-series section before claiming the sparkline portion of C1 complete.

---

## Query-Family Gaps

| Family | Frontend-only gaps | API/result-contract gaps | Engine-output gaps | Deferred / later-phase gaps |
| --- | --- | --- | --- | --- |
| Player summary | New route-aware player summary component; metric priority; responsive hero/stat layout; by-season disclosure | Define a `game_log` / `recent_games` style section if the layout includes a sparkline; optional player-team context | Emit game-by-game series for the exact summary sample; emit resolved date windows | First-run copy and broader loading/error polish belong to Part 3 |
| Leaderboard | Ranked-row layout; #1 emphasis; compact mobile rows; stat-value prominence | Explicit ranking metric, sort direction, limit, and qualifier metadata would avoid column inference | Some routes need consistent team ids and dataset/qualifier caveats | Advanced charts are optional unless they materially improve comprehension |
| Comparison | Side-by-side cards; difference highlighting; mobile stacking; plural identity rendering | Stable entity keys for comparison columns would be stronger than display-name columns | Sample-size-differs and full sample-span metadata are not consistently surfaced in rows | Complex multi-entity comparisons beyond two entities can remain table-biased initially |
| Finder | Game-card list; opponent/home-away/W-L hierarchy; mobile tap targets | Structured filter/threshold summary for display | Finder row projections should include team and opponent ids consistently | Full saved/share interaction polish belongs to Part 3 |
| Team summary / record | Team hero card, record callout, scoped team accent use | Team summary contract should name which advanced team metrics are available | Current team summaries lack pace, offensive rating, and defensive rating named in the Part 2 plan | If advanced team metrics stay unavailable, document a narrower layout target before C5 |
| Streak | Streak hero card; span visualization; mobile timeline/pill layout | Structured condition object instead of only a flat `condition` string | Per-game values inside the streak span are absent | Distribution charts can wait until the basic streak layout is proven useful |
| Split | Side-by-side split cards; friendly bucket labels; mobile stacking | Optional per-bucket context labels if buckets expand beyond current enums | Per-bucket date ranges are not emitted | Additional split types can reuse the same layout later |
| Occurrence / count | Dedicated `count` renderer; occurrence leaderboard cards; expandable detail affordance | Occurrence event definition should be explicit; `count` is in TypeScript but not in the target result-contract class list | Ranked occurrence leaderboards do not include expandable game lists per entity; single-entity counts can include a `finder` detail section | Expansion UI can be phased after the primary count/leaderboard treatment |
| Playoff | Dedicated playoff summary/leaderboard/comparison layouts; caveat placement | Playoff-specific result class or section contract does not exist | Series/round/bracket data is not consistently shaped for a custom playoff layout | Pre-2001-02 round coverage limits remain a documented product caveat |

---

## Handoff Notes For Phase C1

- Keep `ResultSections.tsx` as the dispatcher. Add query-class or route-specific
  child components behind it rather than moving result interpretation into
  `App.tsx`.
- Keep `DataTable.tsx` as a residual detail renderer, but avoid using it as the
  primary visual answer for redesigned classes.
- Use `Avatar`, `TeamBadge`, `Card`, `Stat`, `StatBlock`, `SectionHeader`, and
  `DataTable` primitives from Part 1. Do not create one-off visual primitives
  unless repeated layout pressure justifies them.
- Preserve the API boundary: if the player summary layout needs a sparkline or
  exact sample window, add that data to the structured result rather than
  deriving it in React.
- Keep multi-player, multi-team, and player-subject results neutral unless the
  metadata indicates a safe single-team context.
