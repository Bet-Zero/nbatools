# UI Guide

## Overview

nbatools ships a React + TypeScript + Vite single-page UI.
The frontend source lives in `frontend/` and builds into `src/nbatools/ui/dist/`,
which the FastAPI server serves at `GET /`.

## Running locally

### Production-like (API serves built assets)

```bash
# 1. Build the frontend (once, or after changes)
cd frontend && npm run build

# 2. Start the API (serves the built UI at /)
nbatools-api              # default: http://127.0.0.1:8000
nbatools-api --port 9000  # custom port
nbatools-api --reload     # auto-reload during development

# Or via uvicorn directly:
uvicorn nbatools.api:app --reload
```

Then open **http://127.0.0.1:8000** in a browser.

### Development (two terminals, hot reload)

```bash
# Terminal 1: API server
uvicorn nbatools.api:app --reload

# Terminal 2: Vite dev server with API proxy
cd frontend && npm run dev
```

The Vite dev server proxies `/health`, `/routes`, `/query`, and `/structured-query`
to the API at `http://127.0.0.1:8000`. Open **http://localhost:5173** for hot
module replacement during frontend development.

## What the UI does

- **Query bar** — type a natural-language NBA query and press Enter or click Query. Includes a clear (✕) button and shows "Running…" state during queries.
- **Keyboard shortcuts** — `Cmd+K` / `Ctrl+K` focuses and selects the query input, Escape clears active query text from the input, and up/down arrows recall in-session query history from the input.
- **Sample buttons** — pre-filled example queries with a label, click to run immediately.
- **Empty state** — welcome screen with tips shown before the first query.
- **Result envelope** — shows query metadata with clear visual hierarchy:
  - **Status badge** — color-coded pill (Success/No Result/Error)
  - **Route + query class** — displayed as pills
  - **Data freshness** — "Data through" date prominently shown
  - **Context chips** — player, team, season, opponent, split type
  - **Notes** — blue-bordered info block
  - **Caveats** — orange/yellow-bordered warning block
- **First-run freshness** — before a query result exists, freshness renders as
  a top banner with fresh/stale/unknown/failed state guidance. Result-level
  freshness remains in the result envelope after a query returns.
- **Player summaries** — `player_game_summary` responses use a dedicated renderer with player identity, hero stats, record/secondary stats, a scoring trend and recent-game strip when `game_log` is present, plus full summary and by-season detail.
- **Stat help** — compact stat labels such as PTS, REB, AST, eFG%, TS%, USG%, 3PM, and +/- expose nonintrusive title/accessibility help through the shared Stat primitive.
- **Motion polish** — empty, loading, error, and result surfaces use restrained token-driven entry transitions; hero stat values can opt into reduced-motion-aware settling motion through the shared Stat primitive.
- **Leaderboards** — `leaderboard` query-class responses use ranked rows with player/team identity marks, a prominent metric value, wrapped context/qualifier metadata, restrained #1 emphasis, and a full detail table below.
- **Player comparisons** — `player_compare` responses use side-by-side player cards, metric comparison cards, and full summary/comparison detail tables while keeping mixed-player styling neutral.
- **Head-to-head results** — matchup routes promote both participants, supplied records/samples, season/date context, and neutral identity accents before the supporting detail tables.
- **Playoff results** — playoff history, matchup, appearance, and round-record routes use postseason-specific cards/rankings with supplied team identity, round/season context, records, and full detail tables.
- **Player game finders** — `player_game_finder` responses use game cards with player identity, opponent context, W/L badges, supplied stat values, secondary context chips, and a full detail table below.
- **Streaks** — `player_streak_finder` and `team_streak_finder` responses use answer-first streak cards with identity, condition, length, active/completed status, supplied span context, and full streak detail.
- **Counts** — `count` query-class responses render the supplied count as the primary answer, then keep count rows and any underlying finder/leaderboard/detail sections visible below.
- **Occurrence leaderboards** — `player_occurrence_leaders` and `team_occurrence_leaders` leaderboard responses use event-count rankings that promote the supplied occurrence metric while preserving full leaderboard detail.
- **Data tables** — renders generic result payloads as readable tables. Layout adapts to the result type (generic summary, comparison, finder, streak, split, and fallback sections). Entity columns (player names, teams) are bolded; rank columns are highlighted.
- **Copy buttons** — copy the query text, full JSON response, or shareable link to clipboard, with accessible success/failure feedback and a non-secure-context fallback.
- **Copy Link** — copies the current URL with query state, so the result can be shared or bookmarked.
- **Raw JSON** — toggle to inspect the full API response.
- **URL-driven state** — the active query is stored in the URL (`?q=...` for natural queries, `?route=...&kwargs=...` for structured queries). Refreshing the page re-runs the query. Browser back/forward navigates across prior query states.
- **Query history** — in-session history with:
  - Status dots (green/yellow/red)
  - Query class and route labels
  - Query count
  - Keyboard-activatable query labels with query-specific accessible names
  - **Run** button — immediately re-executes the query
  - **Edit** button — populates the input bar for modification without running
  - **Save** button — saves a history entry into Saved Queries when available
  - Time-ago display
  - Not persisted across sessions
- **Saved queries** — persisted local shortcuts with pinned ordering, tag
  filters that expose pressed state, query-specific run/load/pin/edit/delete
  action names, JSON import/export, and visible import failure feedback.
- **No-result / error display** — friendly messages for empty results (with suggestions) and errors.
- **Dev Tools panel** — collapsible structured-query interface for calling `POST /structured-query` with a route selector and kwargs JSON input.
- **Health indicator** — live green/red dot showing API connectivity and version.

## Mobile and dense-output behavior

The UI is designed to remain usable from phone widths through desktop:

- The main workspace uses a two-column result/sidebar layout on desktop and
  stacks into one column below 900px. Outer padding tightens below 640px.
- Result actions and section-header actions wrap instead of overlapping; the
  main result action buttons become full-width around 520px.
- Result chrome, saved-query controls, query history, save dialogs, raw JSON,
  and dev tools are explicitly contained on phone widths. Long saved-query
  labels, tags, route badges, JSON keys/values, and structured kwargs wrap or
  scroll inside their own panels instead of widening the page.
- First-run freshness banner content wraps inside the top status region and
  keeps stale, unknown, and failed states visible before the first query.
- Phase P1 verified the first-run path against 360x740, 390x844, 768x1024, and
  1280x900 layout targets. Query input remains the first focus target; with an
  empty query, Tab advances to the first starter-query button because the submit
  button is disabled until text exists.
- Keyboard shortcuts are scoped away from dialogs, raw JSON, and structured
  kwargs editing so they do not interrupt focused text or developer-output
  inspection.
- Route/status metadata, context chips, long entity names, playoff round
  labels, event-count labels, and saved/dev-tool text wrap inside their regions.
- Redesigned card grids generally collapse to one column around 720-760px, with
  identity rows and ranked-row metric blocks stacking on phone widths.
- Phase P3 verified card-heavy result renderers at 390x844: player/team
  summaries, team records, split cards, player and team comparisons,
  head-to-head matchups, streaks, and playoff history keep page width fixed
  while detail tables scroll inside their own wrappers.
- Full detail tables remain visible for every result family. Wide tables scroll
  horizontally inside their own framed table wrapper instead of widening the
  app shell; the table primitive sizes wide content to the internal scroll
  region and keeps the page width fixed on phone viewports.
- Raw JSON and structured-query kwargs stay inside their panels. Long JSON keys
  and values can wrap, while the panel itself also supports internal scrolling.

Remaining Part 3 polish should focus on first-run onboarding, starter-query
curation, freshness/banner presentation, keyboard shortcuts, transitions,
loading/error copy, copy/share affordances, and a browser screenshot pass across
real phone/tablet/desktop fixtures.

## How it works

```
Browser (index.html)
  │
  ├─ GET  /           → serves the HTML page (same origin)
  ├─ GET  /health     → version badge
  ├─ GET  /routes     → populates the Dev Tools route dropdown
  ├─ POST /query      → natural-language queries
  └─ POST /structured-query → structured/route-based queries
```

All communication is same-origin fetch calls — no CORS issues, no proxy needed.
CORS middleware is enabled for flexibility if someone wants to open the HTML file separately.

## Result types rendered

| Route / query_class             | Sections displayed                                                                 |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| `player_game_summary` / summary | Player hero, Game Log trend/recent games when present, Full Summary, By Season     |
| `game_summary` / summary        | Team hero, record/headline stats when present, Full Summary, By Season             |
| `team_record` / summary         | Record-first team card, opponent identity when present, Record Detail, By Season   |
| generic summary                 | Summary, By Season (if present)                                                    |
| `player_compare` / comparison   | Player Comparison, Metric Comparison, Player Summary Detail, Full Metric Detail     |
| `team_matchup_record`, head-to-head `player_compare`/`team_compare`, `matchup_by_decade` / comparison | Head-to-head card, Participant Detail, Metric Detail |
| `playoff_history`, team-scoped `playoff_appearances` / summary | Playoff history/appearance card, Postseason Summary Detail, Season Breakdown |
| `playoff_matchup_history` / comparison | Playoff matchup card, Postseason Summary Detail, Series Detail |
| generic comparison              | Summary/Players, Comparison                                                        |
| `player_game_finder` / finder   | Player Games, Player Game Detail                                                   |
| generic finder                  | Matching Games                                                                     |
| `team_split_summary` / split_summary | Team split hero, bucket cards, Split Summary Detail, Split Comparison Detail    |
| `player_split_summary` / split_summary | Player split hero, bucket cards, Split Summary Detail, Split Comparison Detail |
| generic split_summary           | Summary, Split Comparison                                                          |
| generic leaderboard             | Ranked Leaderboard, Full Leaderboard detail table                                  |
| `player_occurrence_leaders` / leaderboard | Occurrence Leaderboard, Full Occurrence Detail                           |
| `team_occurrence_leaders` / leaderboard | Occurrence Leaderboard, Full Occurrence Detail                             |
| `playoff_appearances`, `playoff_round_record` / leaderboard | Playoff leaderboard rankings, Full Playoff Leaderboard |
| `player_streak_finder` / streak | Streak cards, Full Streak Detail                                                   |
| `team_streak_finder` / streak   | Streak cards, Full Streak Detail                                                   |
| count                           | Count answer, Count Detail, optional matching/detail sections                       |
| unknown streak/leaderboard routes | Generic fallback or generic leaderboard path                                      |
| (no result)                     | Status message with reason                                                         |

`PlayerSummarySection.tsx` owns only `player_game_summary` rendering. Team
record, split, playoff, and unknown routes continue through their route-specific
or generic paths so player-specific layout choices do not leak into other
summary-shaped responses.

`LeaderboardSection.tsx` owns `query_class: "leaderboard"` rendering. It
promotes only fields already present in `sections.leaderboard`: rank, a
player/team/entity label, one best available ranked metric, and secondary
metadata such as games played, season, team, game date, opponent, result, and
qualifier fields. Ranking, filters, qualifiers, and metric computation remain
engine/API responsibilities. The full `DataTable` detail stays visible below
the ranked rows so unpromoted columns and sparse/unknown leaderboard shapes are
still inspectable.

`OccurrenceLeaderboardSection.tsx` owns only leaderboard results whose route is
`player_occurrence_leaders` or `team_occurrence_leaders`. It promotes the
dynamic supplied event-count column, row rank, player/team identity, games
played, season/date filters, and qualifier context. It does not parse the
event definition, rank rows, or calculate qualifying games in React. Ordinary
season leaders, top-game leaderboards, record leaderboards, and unknown
leaderboard-shaped responses stay on `LeaderboardSection.tsx`.

`PlayerComparisonSection.tsx` owns only comparison results whose route is
`player_compare`. It promotes supplied summary rows into player cards and
supplied comparison rows into metric cards, but it does not calculate new NBA
facts, choose routes, or transform generic comparison payloads. Full summary
and comparison `DataTable` detail remains visible below the promoted layout.
Ordinary team comparisons and unknown comparison-shaped routes continue through
`ComparisonSection.tsx`.

`HeadToHeadSection.tsx` owns `team_matchup_record`, `matchup_by_decade`, and
only those `player_compare` / `team_compare` responses whose metadata marks
`head_to_head_used: true`. It promotes supplied participant identity,
records/samples, season/date context, and selected supplied stat values while
keeping mixed-player and mixed-team surfaces neutral except for row-level
identity accents. It does not calculate records, winners, game lists, or
comparison metrics in React. The full participant summary, metric, finder, and
unknown detail sections stay visible below the matchup card.

`PlayerGameFinderSection.tsx` owns only finder results whose route is
`player_game_finder`. It promotes supplied finder rows into player game cards
with player identity, date/rank context, opponent badges, home/away labels,
W/L badges, supplied stat values, and secondary context chips. It does not
parse thresholds, reconstruct natural-query intent, calculate new metrics, or
take over team game finders, count detail, top-game leaderboards, or unknown
finder-shaped routes. The full finder `DataTable` detail remains visible below
the cards.

`TeamSummarySection.tsx` owns summary results whose route is `game_summary`.
It promotes supplied team identity, season/sample context, record, and headline
stat values into a team hero card, then keeps the full summary and by-season
tables visible. Playoff summaries route to `PlayoffSection.tsx`, while unknown
summary-shaped routes remain on `SummarySection.tsx`.

`TeamRecordSection.tsx` owns `team_record` results.
Single-team records use scoped team treatment only when `team_context` marks a
safe single-team result; opponent identity is shown as a badge or text fallback.
Record math is not computed in React; the renderer displays only supplied wins,
losses, win percentage, sample size, and secondary stats. Full summary and
by-season detail tables remain visible.

`PlayoffSection.tsx` owns playoff routes: `playoff_history`,
`playoff_appearances`, `playoff_matchup_history`, and `playoff_round_record`.
Summary and comparison routes promote supplied postseason team identity,
appearance counts, records, round/series/season context, and neutral matchup
cards. Playoff leaderboard routes promote supplied ranks, team identity,
appearance or record metrics, round labels, season span, and qualifier context.
It does not infer playoff series, winners, round hierarchy, rankings, or target
metrics; the engine/API must supply those values. Full postseason summary,
season, series, and leaderboard detail tables remain visible.

`SplitSummaryCardsSection.tsx` owns `team_split_summary` and
`player_split_summary` results. It renders the entity context first, then bucket
cards for supplied split rows such as home/away, wins/losses, or custom bucket
labels. Bucket labels are formatted for display without changing the underlying
payload. Full split summary and split-comparison detail tables remain visible,
and unknown split-shaped routes continue through `SplitSummarySection.tsx`.

`StreakSection.tsx` owns only `player_streak_finder` and
`team_streak_finder` streak results. It promotes the supplied streak length or
game count, condition label, entity identity, active/completed status, record,
date span, and selected average stats. It does not reconstruct game-level
streak events or calculate streak lengths. Unknown streak-shaped routes stay on
the generic fallback renderer.

`CountSection.tsx` owns `query_class: "count"` results. It promotes the
supplied count value, metadata query text, entity context, season/date/filter
context, and route label, then keeps `Count Detail` and any non-count detail
sections visible below. It does not derive count values, parse events, or infer
missing matching games.

## Identity imagery and team theming

Phase V4 adds presentation-only identity treatment for players and teams:

- Player headshots render only from stable `player_id` values supplied by the
  API. Missing ids or failed image loads fall back to the initials avatar.
- Team logos render only from stable `team_id` values. Known abbreviations use
  `frontend/src/styles/team-colors.json` for badge colors; unknown or
  historical abbreviations fall back to neutral text badges.
- Result-level team color is scoped to a safe single-team context from
  `team_context`. Player-subject, multi-team, comparison, and league-wide
  leaderboard results remain neutral.
- Leaderboard rows may show player avatars or team badges as identity accents,
  but the leaderboard surface itself remains neutral for mixed league-wide
  contexts.
- Occurrence leaderboards stay neutral except for row-level identity accents;
  row-level team abbreviations must not apply full-surface team theming.
- Player-comparison rows may show player avatars and small team badges, but the
  surface does not split into team-colored sides or apply result-level team
  theming.
- Player-game-finder cards may show player avatars plus small team/opponent
  badges, but player-subject finder pages remain neutral and do not derive
  result-level team theming from row-level teams or opponents.
- Team summaries and single-team records may use scoped result-level team
  treatment only when metadata identifies one safe team context.
- Head-to-head and playoff matchup results stay neutral except for each
  participant's identity badge and restrained row/card accents; the layout must
  not imply full-surface ownership by either side.
- Playoff leaderboards stay neutral for league-wide rankings. Row-level team
  badges provide identity only; they do not apply full-surface team theming.
- Team split summaries may use scoped team treatment for the hero when the
  metadata supplies a safe single-team context. Player split summaries stay
  neutral except for player identity imagery.
- Team color treatment is limited to identity surfaces: badges, a subtle result
  stripe, and a light surface wash. Buttons, body copy, table text, and global
  action states keep the design-system colors.
- Tables remain horizontally scrollable for dense results. Player avatars and
  team logo marks have fixed dimensions so image loading and fallback states do
  not change row height.

Useful Phase V4 visual checks:

- Player result: `Jokic last 10 games`
- Single-team result: `Celtics record 2024-25`
- Multi-team comparison: `Celtics vs Lakers record 2024-25`
- League leaderboard: `top 10 scorers 2024-25`

Player-summary edge-case fallbacks:

- Missing `player_id` keeps the initials avatar and does not attempt a headshot.
- Missing or one-row `game_log` keeps recent-game context but omits the scoring
  sparkline until at least two point values are available.
- Long player names and dense stat values wrap within the player-summary card
  while full summary rows remain available in the detail table.

Leaderboard edge-case fallbacks:

- Missing `player_id` keeps a player initials avatar; missing `team_id` keeps a
  team abbreviation badge.
- Unknown or historical team abbreviations render as neutral badges unless a
  known abbreviation supplies color tokens.
- Sparse leaderboard rows without player/team identity keep text-only entity
  labels and still expose the full row in the detail table.
- If no ranked metric is available, the row still renders rank/entity/context
  without inventing a value; `games_played` is promoted only as the final
  fallback.
- Long entity names, long metric labels, and qualifier text wrap within the
  ranked row; mobile rows stack the metric below identity/context.
- Unknown query classes and unknown section keys bypass leaderboard rendering
  and continue through the generic fallback renderer.

Player-comparison edge-case fallbacks:

- `metadata.players_context` supplies player ids for headshots when available.
  Missing ids, missing context, or failed images fall back to initials.
- Row-level team fields render small team badges when present. Missing or
  unknown team ids keep neutral abbreviation/text badges, and no team colors are
  applied to the whole comparison surface.
- Sparse rows still render player identity cards and the full detail tables for
  supplied summary/comparison rows. Missing optional stats simply omit the
  promoted stat block.
- Metric cards emphasize leaders only for whitelisted numeric,
  higher-is-better metrics already supplied by the response. Ties show a tie
  badge; ambiguous, missing, custom, or nonnumeric rows render without leader
  emphasis.
- Long player names, long team labels, and long custom metric labels are
  constrained within their cards. At mobile widths, player cards and metric
  cards stack to preserve detail.
- Non-player comparison routes remain on the generic `ComparisonSection.tsx`
  path.

Player-game-finder edge-case fallbacks:

- Row-level `player_id` supplies player headshots when available. Missing ids
  or failed images fall back to initials.
- Row-level team and opponent fields render small badges when present. Missing
  team ids keep abbreviation/text badges without logos.
- Cards promote supplied numeric stat fields only. They prioritize common
  player-game stats such as PTS, REB, AST, FG3M, steals, blocks, turnovers, and
  attempts, then fall back to custom numeric fields without parsing query text.
- Secondary context chips show supplied season, season type, minutes,
  plus-minus, and clutch fields when present. Missing context simply omits the
  chip.
- Missing W/L, opponent, team, or promoted stats still leaves a readable player
  card and the full detail table.
- Long player names, long opponent/team labels, and long custom stat labels are
  constrained within cards. At mobile widths, game cards and stat grids stack.
- `game_finder`, count results with finder detail, top-game leaderboards, and
  unknown finder-shaped routes remain on their existing renderers.

Team-summary and team-record edge-case fallbacks:

- Missing team ids or logos use team abbreviation/name badges and still show
  the supplied team title.
- Missing wins/losses omits the promoted record stat instead of inventing a
  record, while the detail table remains visible.
- Missing opponent identity on team records renders the available opponent text
  as a neutral badge when present.
- Long team and opponent names are constrained within badges/headings; mobile
  layouts stack identity, title, and stat groups to avoid overlap.
- Unknown summary routes and generic comparison routes remain on their fallback
  renderers.

Head-to-head and playoff edge-case fallbacks:

- Missing player/team ids keep initials avatars or neutral team abbreviation
  badges. Row-level names, metadata identity context, or generated participant
  labels keep the card readable.
- Missing wins/losses omits the promoted record instead of inventing a result.
  If only a supplied game/sample count exists, the renderer shows that sample
  size and keeps the detail table visible.
- Tied records remain neutral. The UI displays the supplied tied record without
  creating a winner label or assigning ownership to either participant.
- Missing dates, season ranges, round labels, or opponent filters simply omit
  those context chips. Supplied chips wrap and do not widen the result region.
- Long player/team names, long round labels, and long dynamic series columns
  wrap inside cards. At mobile widths, identity, context, record, and metric
  regions stack vertically.
- Playoff matchup/history rows do not include series winners or bracket objects
  today; `PlayoffSection.tsx` does not infer them. Dynamic team-prefixed
  columns remain available in the detail table.
- Playoff leaderboard rows without team identity render a text fallback such
  as "Playoff Entry 2"; sparse rows still expose the full leaderboard table.
- Ordinary comparisons, ordinary leaderboards, occurrence leaderboards,
  unknown summary routes, and unknown fallback sections remain available for
  shapes not explicitly owned by C7.

Split-summary edge-case fallbacks:

- Missing team or player identity falls back to the supplied row/entity label,
  then to "Team" or "Player".
- Missing wins/losses omits the record stat for that bucket. Sparse buckets
  still show their label, supplied game count when available, and the detail
  table below.
- Long custom bucket labels wrap within the bucket card. At mobile widths, the
  bucket count stacks below the label.
- Unknown split routes remain on the generic `SplitSummarySection.tsx` path.

Streak/count/occurrence edge-case fallbacks:

- Streak rows with missing player/team ids keep initials or text badge identity.
  Missing `condition` falls back to "Streak"; missing length shows a neutral
  streak answer instead of inventing a value.
- Missing streak dates or game counts omit the span panel rather than leaving an
  empty visual block. The full streak detail table remains visible.
- Long player/team names, long streak conditions, and long date values wrap
  inside cards. At mobile widths, identity, status, answer, and span/context
  regions stack.
- Count results can be zero and may have no finder detail. The count answer and
  count detail table still render; optional finder or custom detail sections
  appear only when supplied by the response.
- Long count query text, route labels, and context chips wrap inside the count
  card without widening the result region.
- Occurrence leaderboard rows without identity render a text-only "Occurrence
  Entry" label and still expose the full detail table.
- Occurrence event labels are formatted from supplied dynamic column names
  without threshold parsing. Long compound labels wrap inside the metric column;
  at mobile widths the event-count block stacks below identity/context.
- Ordinary leaderboards, finder routes, unknown streak routes, and generic
  fallback sections remain available for shapes not explicitly owned by C6.

## File locations

- Frontend source: `frontend/` (React + TypeScript + Vite)
- Build output: `src/nbatools/ui/dist/` (served by FastAPI)
- API serving: `src/nbatools/api.py` → `GET /` + `/assets` static mount
- Vite config: `frontend/vite.config.ts` (proxy + build output path)
- Player summary renderer: `frontend/src/components/PlayerSummarySection.tsx`
- Leaderboard renderer: `frontend/src/components/LeaderboardSection.tsx`
- Player comparison renderer:
  `frontend/src/components/PlayerComparisonSection.tsx`
- Player game finder renderer:
  `frontend/src/components/PlayerGameFinderSection.tsx`
- Team summary renderer:
  `frontend/src/components/TeamSummarySection.tsx`
- Team record renderer:
  `frontend/src/components/TeamRecordSection.tsx`
- Head-to-head renderer:
  `frontend/src/components/HeadToHeadSection.tsx`
- Playoff renderer:
  `frontend/src/components/PlayoffSection.tsx`
- Team/player split card renderer:
  `frontend/src/components/SplitSummaryCardsSection.tsx`
- Streak renderer: `frontend/src/components/StreakSection.tsx`
- Count renderer: `frontend/src/components/CountSection.tsx`
- Occurrence leaderboard renderer:
  `frontend/src/components/OccurrenceLeaderboardSection.tsx`
- Generic summary fallback: `frontend/src/components/SummarySection.tsx`
- Generic split fallback: `frontend/src/components/SplitSummarySection.tsx`

## Tech stack

- React 19, TypeScript, Vite
- Vitest + Testing Library for frontend tests
- Typed API client: `frontend/src/api/client.ts` + `types.ts`
- Components: `frontend/src/components/`
- Design-system primitives: `frontend/src/design-system/`
- Hooks: `frontend/src/hooks/`
- Tests: `frontend/src/test/`

## Design-system primitives

Reusable frontend primitives live in `frontend/src/design-system/` and are
exported from the barrel import:

```tsx
import { Badge, Button, Card, DataTable, SectionHeader } from "../design-system";
```

These primitives are presentation-only. They own token-driven layout, spacing,
color, type, borders, radii, shadows, and accessible fallback structure. Feature
components still own query behavior, API response interpretation, NBA-specific
value formatting, metric selection, and route-specific labels.

| Primitive | Purpose | Variant guidance |
| --------- | ------- | ---------------- |
| `Button` | Text buttons for submit, copy, toggle, and destructive actions | Use `primary` for the main action in a zone, `secondary` for ordinary actions, `ghost` for low-emphasis tools, and `danger` only for destructive actions. Sizes are `sm` and `md`; `loading` disables and marks the button busy. |
| `IconButton` | Icon-only buttons with required accessible labels | Use when the visible control is an icon. Always provide `aria-label`; the icon node is decorative. |
| `Card` | Tokenized surface with depth, padding, and system tone | `depth` maps to `elevated`, `card`, or `input`; `tone` is for UI/system states, not team identity. |
| `SectionHeader` | Section title row with optional eyebrow, count, and actions | Feature components provide labels and counts; the primitive owns alignment and wrapping. |
| `ResultEnvelopeShell` | Slot layout for result metadata, query text, context, notices, alternates, and children | Keep status, route, freshness, notes, caveats, and alternate-query behavior in `ResultEnvelope`. |
| `Badge` | Compact chip for statuses, tags, routes, and context | Use `success`, `warning`, `danger`, and `info` for UI/system states; use `win` and `loss` only for sports outcome semantics; use `accent` sparingly for route/context emphasis. |
| `Stat` | Single label/value/context display with mono numeric value styling | Pass already-computed values only. The primitive does not calculate NBA metrics or trends. |
| `StatBlock` | Responsive grid of `Stat` items | Feature wrappers choose which stats appear and in what order. |
| `Skeleton`, `SkeletonText`, `SkeletonBlock` | Loading placeholders | Use to approximate upcoming content while preserving feature-level loading copy and state. |
| `DataTable` | Generic table shell for supplied columns, rows, alignment, highlight, and cell classes | It does not format NBA values or infer player/team/rank columns; `components/DataTable.tsx` remains the NBA-specific wrapper. |
| `Avatar` | Player/person fallback identity mark | Use existing names only. Real image source integration remains Phase V4. |
| `TeamBadge` | Team fallback identity mark with `--team-primary` / `--team-secondary` hooks | Use team colors only as contextual identity accents, not button colors or body text. Real logo source integration remains Phase V4. |

### Primitive examples

```tsx
<Button variant="primary" loading={isSubmitting}>
  Query
</Button>

<Badge variant="success" uppercase>
  fresh
</Badge>

<SectionHeader title="Leaderboard" count={`${rows.length} entries`} />

<StatBlock
  stats={[
    { label: "PTS", value: "28.4", semantic: "accent" },
    { label: "REB", value: "11.2" },
  ]}
  columns={2}
/>
```

```tsx
<DataTable
  rows={rows}
  columns={[
    {
      key: "player",
      header: "Player",
      render: (row) => row.player,
    },
  ]}
/>
```

The generic table example above intentionally renders supplied values as-is.
NBA-specific header formatting, percentage formatting, entity-column detection,
and highlight choices belong in feature wrappers outside `design-system/`.

### Primitive checklist

Before adding or consuming a primitive:

- Import from `frontend/src/design-system/index.ts`, not a deep path, unless a
  test needs a CSS module.
- Keep parser, query, filtering, analytics, and NBA metric logic outside the
  primitive.
- Use existing tokens for colors, spacing, typography, borders, radii, shadows,
  and motion.
- Keep team colors contextual through `--team-primary` / `--team-secondary`;
  do not apply team colors to global actions or dense table text.
- Add or update focused tests when a feature component migrates to a primitive.

## Frontend file structure

```
frontend/src/
  api/
    types.ts             # TypeScript interfaces for API envelope, result types, query history
    client.ts            # Typed fetch wrappers (fetchHealth, postQuery, fetchFreshness, etc.)
  components/
    QueryBar.tsx          # Text input + submit
    SampleQueries.tsx     # Pre-filled example query buttons
    EmptyState.tsx        # Welcome state shown before first query
    QueryHistory.tsx      # In-session query history list
    FreshnessStatus.tsx   # Collapsible freshness panel (status, current_through, details)
    ResultEnvelope.tsx    # Envelope metadata (status, route, notes, caveats)
    ResultSections.tsx    # Dispatcher — routes to per-query-class renderers
    SummarySection.tsx    # Summary + By Season tables
    TeamSummarySection.tsx # Team summary hero + detail tables
    ComparisonSection.tsx # Players + Comparison tables
    TeamRecordSection.tsx # Team record cards + detail tables
    HeadToHeadSection.tsx # Head-to-head matchup cards + detail tables
    PlayoffSection.tsx    # Playoff history/matchup/leaderboard layouts + detail tables
    SplitSummarySection.tsx # Summary + Split Comparison tables
    SplitSummaryCardsSection.tsx # Team/player split bucket cards + detail tables
    FinderSection.tsx     # Matching Games table with count
    LeaderboardSection.tsx # Generic leaderboard ranked rows + detail table
    OccurrenceLeaderboardSection.tsx # Occurrence event-count ranked rows + detail
    StreakSection.tsx      # Player/team streak cards + detail table
    CountSection.tsx       # Count answer card + detail sections
    DataTable.tsx         # NBA-specific wrapper over the generic table primitive
    NoResultDisplay.tsx   # No-result and error state display
    RawJsonToggle.tsx     # Raw JSON toggle
    CopyButton.tsx        # Copy-to-clipboard button
    DevTools.tsx          # Structured query panel (route selector + kwargs)
    Loading.tsx           # Loading status with skeleton preview
    ErrorBox.tsx          # Error display
  design-system/
    Avatar.tsx            # Player/person fallback identity mark
    Badge.tsx             # Status/context chip primitive
    Button.tsx            # Button and IconButton primitives
    Card.tsx              # Tokenized surface primitive
    DataTable.tsx         # Generic table shell primitive
    ResultEnvelopeShell.tsx # Result-envelope slot layout primitive
    SectionHeader.tsx     # Section heading/count/action primitive
    Skeleton.tsx          # Skeleton, SkeletonText, SkeletonBlock primitives
    Stat.tsx              # Single stat display primitive
    StatBlock.tsx         # Stat grid primitive
    TeamBadge.tsx         # Team fallback identity mark
    index.ts              # Barrel export for primitives and prop types
  hooks/
    useQueryHistory.ts    # In-session query history state hook
    useUrlState.ts        # URL search-param sync for shareable deep links
  test/
    setup.ts             # Vitest + jest-dom setup
    client.test.ts       # API client tests
    DataTable.test.tsx   # DataTable component tests
    ResultSections.test.tsx # Result rendering tests for all query classes
    UIComponents.test.tsx # EmptyState, NoResult, Loading, ErrorBox tests
    FreshnessStatus.test.tsx # Freshness panel rendering and status display tests
    useUrlState.test.ts  # URL state parsing, building, and hook behavior tests
  App.tsx                # Main app component — wires state + components
  App.module.css         # App shell styles
  main.tsx               # React entry point
```

## Running frontend tests

```bash
cd frontend
npm test          # run once
npm run test:watch  # watch mode
```

## URL state model

The app stores query state in URL search params so every result is linkable:

| Param    | Purpose                            | Example                                |
| -------- | ---------------------------------- | -------------------------------------- |
| `q`      | Natural-language query text        | `?q=Jokic+last+10+games`               |
| `route`  | Structured route name (dev tools)  | `?route=season_leaders`                |
| `kwargs` | Structured kwargs JSON (dev tools) | `&kwargs=%7B%22stat%22%3A%22pts%22%7D` |

**Behavior:**

- On submit: a new browser history entry is pushed with the query in the URL.
- On page load: if the URL contains query params, the query auto-runs.
- Browser back/forward: navigates across prior queries, re-running each.
- Copy Link button: copies the shareable URL to clipboard.
- Natural and structured params are mutually exclusive in the URL.

## App shell layout notes

The Phase V3 shell is slot-based: `App.tsx` still owns query state, URL state,
API calls, saved-query state, and dialog mounting, while
`components/AppShell.tsx` owns the page regions for header, freshness, query,
main results, and secondary panels.

Responsive expectations for future frontend work:

- Keep primary query/result controls in the main region; saved queries, history,
  and dev tools belong in the secondary panel area.
- Long query text and dense results should stay inside their region. Tables
  remain horizontally scrollable through the data-table wrapper instead of
  forcing the whole page wider.
- Section-header actions should wrap at mobile widths. Avoid adding fixed-width
  controls to shell regions unless they also have a mobile wrapping rule.
- Core first-run and non-result panels should remain explicitly contained at
  narrow phone widths: use `width: 100%`, `min-width: 0`, token padding, and
  wrapping action rows for long details, starter queries, suggestions, and
  retry controls.
- Freshness and API status are shell chrome, but their fetching and semantics
  remain in `App.tsx` and `FreshnessStatus.tsx`.

## Out of scope (intentional)

- Authentication / user accounts
- Database or persistence
- Production deployment / hosting
- Client-side routing library (URL state is managed with native History API)
- State management libraries
- Raw JSON toggle persistence in URL
