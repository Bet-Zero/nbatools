# Phase C8 Mobile Inventory

> Inventory for
> [`phase_c8_work_queue.md`](./phase_c8_work_queue.md) item 1. This records
> the mobile verification fixtures and risk areas for the dedicated C8 mobile
> pass across redesigned Part 2 components.

---

## Sources reviewed

- `docs/operations/ui_guide.md`
- `docs/planning/component_experience_plan.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/*Section.tsx`
- `frontend/src/components/*Section.module.css`
- `frontend/src/test/ResultSections.test.tsx`

---

## Verification widths

Use these viewport widths as the shared C8 baseline:

| Width | Role | Why it matters |
| --- | --- | --- |
| 390px | phone | Catches single-column stacking, long-word wrapping, action/button overflow, and detail-table containment. |
| 768px | tablet | Catches two-column-to-one-column transitions and side-panel/shell behavior. |
| 1280px | desktop | Confirms C8 mobile fixes do not regress the intended desktop layout. |

When a component has a known breakpoint near a different width, verify one
sample just above and below that breakpoint. The primary pass should still
report against the three shared widths above so the phase stays comparable.

---

## Cross-surface checks

Every C8 item should keep these checks in mind:

- The document and app shell must not create horizontal page overflow.
- Dense `DataTable` content may scroll inside its own wrapper; it must not
  widen the whole result region.
- Section headers, context chips, copy/share buttons, and dev-tool controls
  must wrap or stack without overlapping nearby text.
- Missing identities, failed images, zero values, ties, sparse rows, and long
  labels must still leave the primary answer and detail table visible.
- Mixed player/team, head-to-head, playoff matchup, occurrence, and
  league-wide leaderboard surfaces remain neutral except for identity badges.
- React may promote only supplied values. Parser decisions, rankings, records,
  playoff interpretation, and filtering remain engine/API responsibilities.

---

## Fixture matrix

| Family | Owners | Representative route/query-class fixtures | Mobile risk areas | Existing coverage / C8 target |
| --- | --- | --- | --- | --- |
| App shell and query chrome | `AppShell`, `QueryBar`, `SampleQueries`, `FreshnessStatus`, `QueryHistory`, `SavedQueries`, `DevTools`, `ResultEnvelope` | Natural query with a long text value; structured query with long kwargs JSON; freshness with many season rows; long caveat/notes block | Shell columns, query/action wrapping, side-panel overflow, route/context chip wrapping, modal/dialog width | Existing component tests cover behavior; C8 should add focused mobile-safe markup tests only where CSS/structure changes. |
| Player summary | `PlayerSummarySection` | `player_game_summary` with `game_log`; sparse `game_log`; missing `player_id`; long player name | Hero identity/stat grid, sparkline width, recent-game strip, table containment | Existing C1 tests cover identity/sparse states; C8 should visually verify widths and add tests if markup changes. |
| Team summary | `TeamSummarySection` | `game_summary` with `team_context`; sparse stats; long team/opponent labels | Scoped team wash/stripe, logo/title wrapping, hero stat grid stacking | Existing C5 tests cover route ownership and fallbacks; C8 should focus on responsive CSS. |
| Team record | `TeamRecordSection` | `team_record` with opponent; zero games; missing record; long opponent name | Opponent badge/title wrapping, record/stat grid stacking, detail table visibility | Existing C5 tests cover missing record/long opponent; C8 should verify mobile stack. |
| Split summary | `SplitSummaryCardsSection`, `SplitSummarySection` | `team_split_summary`, `player_split_summary`, unknown split fallback; long custom bucket labels | Bucket card count placement, split comparison table width, scoped team treatment | Existing C5 tests cover owned/fallback paths; C8 should verify bucket labels at phone width. |
| Generic/player comparison | `PlayerComparisonSection`, `ComparisonSection` | Ordinary `player_compare`; ordinary `team_compare`; unknown comparison fallback; tied metrics | Side-by-side cards stacking, metric card labels, tie badges, full metric detail | Existing C3 tests cover ties/fallbacks; C8 should verify card/detail stacking. |
| Head-to-head | `HeadToHeadSection` | `team_matchup_record`; `player_compare` with `head_to_head_used`; `team_compare` with `head_to_head_used`; `matchup_by_decade` | Participant card stacking, tied records, missing identities, long team/player names, dynamic decade columns | Existing C7 tests cover owned routes, sparse rows, ties, and fallback preservation; C8 should verify phone/tablet layout. |
| Playoff summary/matchup | `PlayoffSection` | `playoff_history`; team-scoped `playoff_appearances`; `playoff_matchup_history`; sparse rows; long round labels | Postseason context chips, matchup cards, long round/series labels, dynamic team-prefixed columns | Existing C7 tests cover sparse/long labels and detail preservation; C8 should verify context/detail wrapping. |
| Generic leaderboard | `LeaderboardSection` | `season_leaders`; top player/team games; sparse unknown leaderboard | Ranked-row grid, metric block stacking, long metric labels, missing identity | Existing C2 tests cover identity/sparse rows; C8 should verify row grid at phone width. |
| Occurrence leaderboard | `OccurrenceLeaderboardSection` | `player_occurrence_leaders`; `team_occurrence_leaders`; long dynamic event label; missing identity | Event-count metric labels, context chips, neutral mixed-surface treatment | Existing C6 tests cover event labels and fallbacks; C8 should verify mobile metric placement. |
| Playoff leaderboard | `PlayoffSection` | `playoff_appearances` leaderboard; `playoff_round_record`; missing team identity; long round labels | Rank/identity/record/metric stacking, context wrap, full leaderboard table | Existing C7 tests cover sparse identity and long round labels; C8 should verify phone/tablet stack. |
| Player game finder | `PlayerGameFinderSection`, `FinderSection` | `player_game_finder`; generic `game_finder`; sparse finder row; long opponent/team labels | Game-card identity/opponent rows, stat grid, W/L badge, generic finder table | Existing C4 tests cover player finder/fallbacks; C8 should verify mobile card stack. |
| Streak | `StreakSection` | `player_streak_finder`; `team_streak_finder`; missing dates; missing streak length; long condition label | Condition/status badges, answer block, span/context stacking | Existing C6 tests cover sparse rows; C8 should verify phone/tablet layout. |
| Count | `CountSection` | Direct count result; count with finder/leaderboard detail; zero count; long query text | Count hero, query/context wrapping, optional detail visibility | Existing C6 tests cover zero/direct/detail cases; C8 should verify mobile wrapping. |
| Detail utilities | `DataTable`, `RawJsonToggle`, `CopyButton`, `ResultSections` fallback | Wide detail table; unknown section key; raw JSON open; copy link/query buttons | Horizontal table scroll, raw JSON containment, action wrapping, fallback card width | Existing tests cover rendering behavior; C8 should add visual/mobile assertions only when structure changes. |

---

## Suggested manual/browser fixtures

Use real queries when data is available; otherwise use structured responses or
test fixtures that match these payload shapes.

| Fixture | Widths | What to inspect |
| --- | --- | --- |
| `Jokic last 10 games` | 390 / 768 / 1280 | Player summary hero, sparkline, recent games, by-season/detail table containment. |
| `Celtics record 2024-25` | 390 / 768 / 1280 | Team record hero, scoped team accent, long context, record/detail table. |
| `Jokic vs Embiid this season` | 390 / 768 / 1280 | Player comparison cards, metric cards, detail tables. |
| `Celtics vs Lakers record 2024-25` | 390 / 768 / 1280 | Head-to-head participant stacking, neutral surface, tied/sparse record handling if present. |
| `Celtics playoff history since 2019` | 390 / 768 / 1280 | Playoff summary context chips, season breakdown table, long round labels if filtered. |
| `most playoff appearances since 2010` | 390 / 768 / 1280 | Playoff leaderboard rank/identity/metric stack and detail table. |
| `top 10 scorers 2024-25` | 390 / 768 / 1280 | Generic leaderboard row stack, metric label/value, full leaderboard table. |
| `most 40 point games 2024-25` | 390 / 768 / 1280 | Occurrence leaderboard dynamic label and event-count metric. |
| `Jokic 30 point streak` | 390 / 768 / 1280 | Streak answer block, status/context chips, streak detail. |
| `How many 50 point games did Luka have in 2024-25?` | 390 / 768 / 1280 | Count hero, long query/context wrapping, optional detail sections. |

---

## Automated-test targets

Automated tests should focus on structural guarantees that jsdom can verify:

- Owned routes still dispatch to the intended component after CSS/layout
  changes.
- Long names, long labels, sparse rows, missing identities, ties, zero values,
  and missing dates render without throwing.
- Detail sections remain present after any mobile-specific markup changes.
- Generic comparison, summary, leaderboard, finder, split, streak, and fallback
  paths remain available.

Pure layout assertions such as exact wrapping, overlap, and horizontal scroll
need browser verification. C8 implementation items should record those checks
in their PR bodies when they materially change CSS.

---

## Deferred beyond C8

- New data contracts for playoff series winners, bracket structure, or
  head-to-head game lists.
- First-run copy, starter-query strategy, keyboard shortcuts, and broader
  empty/error polish. Those belong to Track A Part 3.
- Production deployment/mobile performance issues tied to Vercel/R2 hosting.
  Those belong to Track B or later production hardening.
