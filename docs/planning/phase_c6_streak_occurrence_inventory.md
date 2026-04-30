# Phase C6 Streak and Occurrence Inventory

> Inventory for
> [`phase_c6_work_queue.md`](./phase_c6_work_queue.md) item 1. This records
> the current API/frontend row shapes and renderer boundaries for streak,
> count, and occurrence layouts before C6 runtime work begins.

---

## Sources reviewed

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/StreakSection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/components/FinderSection.tsx`
- `frontend/src/test/ResultSections.test.tsx`
- `src/nbatools/commands/player_streak_finder.py`
- `src/nbatools/commands/team_streak_finder.py`
- `src/nbatools/commands/player_occurrence_leaders.py`
- `src/nbatools/commands/team_occurrence_leaders.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/query_service.py`
- Count/occurrence/streak tests under `tests/`

---

## Current ownership

| Family | Current query class | Current owner | Sections | C6 target |
| --- | --- | --- | --- | --- |
| Player streak | `streak` | `StreakSection.tsx` | `streak` | Route-aware streak cards before detail table |
| Team streak | `streak` | `StreakSection.tsx` | `streak` | Same streak card model, with team identity and neutral fallbacks |
| Finder-derived count | `count` | `ResultSections.tsx` generic fallback | `count`, optional `finder` | Dedicated count-answer renderer with finder detail preserved |
| Occurrence count | `count` | `ResultSections.tsx` generic fallback | `count` | Dedicated count-answer renderer; no invented event detail |
| Player occurrence leaderboard | `leaderboard` | `LeaderboardSection.tsx` | `leaderboard` | Route-aware event-count leaderboard treatment |
| Team occurrence leaderboard | `leaderboard` | `LeaderboardSection.tsx` | `leaderboard` | Route-aware event-count leaderboard treatment |
| Ordinary leaderboard/finder routes | `leaderboard` / `finder` | Existing leaderboard/finder renderers | existing sections | Must remain unchanged unless explicitly owned by C6 |
| Unknown/future shapes | any | Generic fallback | any non-empty section | Must remain available as safety net |

`ResultSections.tsx` currently routes all `query_class: "streak"` results to
`StreakSection.tsx`, all `query_class: "leaderboard"` results to
`LeaderboardSection.tsx`, and has no explicit `count` case. That means count
results fall through to the generic fallback renderer.

---

## Representative shapes

### Player streak

Route: `player_streak_finder`
Query class: `streak`
Sections: `streak`

Representative row:

```json
{
  "rank": 1,
  "player_name": "Nikola Jokic",
  "condition": "pts>=30",
  "streak_length": 5,
  "games": 5,
  "start_date": "2025-01-01",
  "end_date": "2025-01-10",
  "start_game_id": "0022400001",
  "end_game_id": "0022400005",
  "wins": 4,
  "losses": 1,
  "is_active": 0,
  "minutes_avg": 35.4,
  "pts_avg": 32.6,
  "reb_avg": 11.2,
  "ast_avg": 8.4,
  "fg3m_avg": 1.2,
  "plus_minus_avg": 6.0
}
```

Useful fields:

- Identity: `player_name` in each row; `metadata.player_context` when natural
  query metadata resolves the player.
- Primary answer: `streak_length`, `condition`, `start_date`, `end_date`.
- Context: `games`, `wins`, `losses`, `is_active`, `rank`.
- Secondary stats: `minutes_avg`, `pts_avg`, `reb_avg`, `ast_avg`, `stl_avg`,
  `blk_avg`, `fg3m_avg`, `tov_avg`, `plus_minus_avg`.
- Detail-only fields: `start_game_id`, `end_game_id`, any stat averages not
  promoted.

Gaps:

- Streak rows do not carry `player_id`; player imagery should use
  `metadata.player_context` when available and fall back to initials/text.
- `condition` is a flat display string, not a structured condition object.
- There is no per-game streak section. The UI must not reconstruct game-level
  pills beyond the supplied span fields.
- Streak mode (`longest`, minimum length, current-vs-longest) is not exposed as
  a dedicated metadata field beyond route kwargs/notes.

### Team streak

Route: `team_streak_finder`
Query class: `streak`
Sections: `streak`

Representative row:

```json
{
  "rank": 1,
  "team_name": "Boston Celtics",
  "condition": "wins",
  "streak_length": 4,
  "games": 4,
  "start_date": "2025-02-01",
  "end_date": "2025-02-08",
  "start_game_id": "0022400100",
  "end_game_id": "0022400104",
  "wins": 4,
  "losses": 0,
  "is_active": 1,
  "pts_avg": 121.5,
  "reb_avg": 45.0,
  "ast_avg": 28.0,
  "fg3m_avg": 15.2,
  "plus_minus_avg": 9.5,
  "efg_pct_avg": 0.58,
  "ts_pct_avg": 0.62
}
```

Useful fields:

- Identity: `team_name` in each row; `metadata.team_context` when metadata
  resolves the team.
- Primary answer: `streak_length`, `condition`, `start_date`, `end_date`.
- Context: `games`, `wins`, `losses`, `is_active`, `rank`.
- Secondary stats: `pts_avg`, `reb_avg`, `ast_avg`, `stl_avg`, `blk_avg`,
  `fg3m_avg`, `tov_avg`, `plus_minus_avg`, `efg_pct_avg`, `ts_pct_avg`.
- Caveats: team streak builder can add multi-season, opponent, home-only, or
  away-only caveats.

Gaps:

- Streak rows do not consistently expose `team_id` or `team_abbr`; use
  `metadata.team_context` first, then row name/text fallbacks.
- No opponent identity is present in the streak row even when an opponent filter
  applies; opponent context is metadata/caveat-level only.
- No per-game values inside the streak span are emitted.

### Finder-derived count

Routes: usually `player_game_finder` or `game_finder` with count intent
Query class: `count`
Sections: `count`, optional `finder`

Representative response sections:

```json
{
  "count": [{ "count": 2 }],
  "finder": [
    { "rank": 1, "game_date": "2025-01-15", "player_name": "Stephen Curry", "pts": 42 },
    { "rank": 2, "game_date": "2025-01-20", "player_name": "Stephen Curry", "pts": 35 }
  ]
}
```

Useful fields:

- Primary answer: `sections.count[0].count`.
- Identity/context: metadata follows the underlying route and can include
  `player_context`, `team_context`, `opponent_context`, season/date filters,
  split/filter fields, and `query_text`.
- Detail: `sections.finder` is the original finder rows and should remain
  visible below the count answer when present.

Gaps:

- `count` is implemented by `CountResult` and TypeScript accepts it, but the
  conceptual result-contract docs still list seven core classes and do not yet
  promote count to a full conceptual class.
- The `count` section has only the count value; any event/filter label must come
  from metadata, caveats, notes, or the query text.
- Current UI has no dedicated `count` route and displays the section key as a
  generic table label.

### Occurrence count

Routes: `player_occurrence_leaders` or `team_occurrence_leaders` with count
intent
Query class: `count`
Sections: `count`

Representative response sections:

```json
{
  "count": [{ "count": 12 }]
}
```

Useful fields:

- Primary answer: `sections.count[0].count`.
- Route boundary: the top-level route and metadata route remain
  `player_occurrence_leaders` or `team_occurrence_leaders`.
- Identity/context: metadata can include `player_context` or `team_context`
  when the counted entity resolves.
- Caveats/notes may describe opponent, home/away, win/loss, multi-season, or
  compound-occurrence filters.

Gaps:

- Occurrence counts do not include finder detail rows per qualifying game.
- The occurrence event label is not included in the `count` section. The UI can
  display the count and context, but should not invent the event definition.

### Player occurrence leaderboard

Route: `player_occurrence_leaders`
Query class: `leaderboard`
Sections: `leaderboard`

Representative row:

```json
{
  "rank": 1,
  "player_name": "Nikola Jokic",
  "team_abbr": "DEN",
  "games_played": 72,
  "games_pts_30+_reb_10+_ast_10+": 12,
  "season": "2024-25",
  "season_type": "Regular Season"
}
```

Other event-count column examples:

- `games_pts_30+`
- `games_fg3m_5+`
- `games_pts_30+_reb_10+`
- `triple doubles`
- `double doubles`
- `qualifying_games`

Useful fields:

- Identity: `player_name`, optional `team_abbr`; metadata can supply
  `player_context` only for single-player count-style queries, not league-wide
  leaderboards.
- Primary metric: dynamic event-count column after excluding `rank`,
  identity/context columns, `games_played`, `season`, `seasons`, and
  `season_type`.
- Context: `games_played`, `season` or `seasons`, `season_type`.
- Caveats: opponent filters, multi-season aggregation, special-event
  definitions, compound occurrence conditions, home/away, wins/losses.

Gaps:

- Output rows group by `player_id`, but `player_id` is not emitted in
  `out_cols`; headshots should use initials unless a later engine/API change
  adds ids.
- The event definition is encoded as a dynamic column label rather than
  structured metadata.
- No expandable per-player game list is emitted for the qualifying games.

### Team occurrence leaderboard

Route: `team_occurrence_leaders`
Query class: `leaderboard`
Sections: `leaderboard`

Representative row:

```json
{
  "rank": 1,
  "team_abbr": "BOS",
  "games_played": 82,
  "games_pts_120+_fg3m_15+": 18,
  "season": "2024-25",
  "season_type": "Regular Season"
}
```

Useful fields:

- Identity: `team_abbr` preferred, falling back to `team_name` if the source
  lacks abbreviation.
- Primary metric: dynamic event-count column using the same exclusion strategy
  as player occurrence leaderboards.
- Context: `games_played`, `season` or `seasons`, `season_type`.
- Caveats: opponent filters, multi-season aggregation, compound occurrence
  conditions, home/away, wins/losses.

Gaps:

- Rows do not emit `team_id`; team logos should rely on abbreviation/name
  fallback unless metadata supplies a single-team context.
- The event definition is a dynamic column label, not structured metadata.
- No expandable per-team game list is emitted.

---

## Renderer boundary decisions for C6

Owned by C6:

- `query_class: "streak"` for `player_streak_finder` and `team_streak_finder`.
- `query_class: "count"` for finder-derived counts and occurrence counts.
- `query_class: "leaderboard"` only when route is `player_occurrence_leaders`
  or `team_occurrence_leaders`.

Preserve existing behavior:

- Ordinary `season_leaders`, `season_team_leaders`, top-game leaderboards,
  record leaderboards, playoff leaderboards, and unknown leaderboard-shaped
  routes continue through the existing generic leaderboard layout unless a C6
  item explicitly owns them.
- `player_game_finder` continues through `PlayerGameFinderSection.tsx` when it
  is a finder result, and `game_finder` continues through `FinderSection.tsx`.
- Unknown query classes and unknown section keys keep the generic fallback.
- C5 team summary/record/split renderers remain untouched.

---

## Promoted-field candidates

| Shape | Primary fields | Secondary fields | Detail-only/default table fields |
| --- | --- | --- | --- |
| Player streak | `streak_length`, `condition`, `start_date`, `end_date`, `player_name`/`metadata.player_context` | `games`, `wins`, `losses`, `is_active`, `pts_avg`, `reb_avg`, `ast_avg`, `minutes_avg`, `fg3m_avg`, `plus_minus_avg` | `rank`, game ids, all unpromoted averages |
| Team streak | `streak_length`, `condition`, `start_date`, `end_date`, `team_name`/`metadata.team_context` | `games`, `wins`, `losses`, `is_active`, `pts_avg`, `reb_avg`, `ast_avg`, `fg3m_avg`, `efg_pct_avg`, `ts_pct_avg`, `plus_minus_avg` | `rank`, game ids, all unpromoted averages |
| Count | `count` | metadata `query_text`, entity context, season/date/filter context | `finder` detail rows when present |
| Player occurrence leaderboard | dynamic event-count column, `rank`, `player_name` | `team_abbr`, `games_played`, `season`/`seasons`, `season_type`, caveats | every leaderboard row in full detail table |
| Team occurrence leaderboard | dynamic event-count column, `rank`, `team_abbr`/`team_name` | `games_played`, `season`/`seasons`, `season_type`, caveats | every leaderboard row in full detail table |

---

## Edge cases to cover during implementation

- Streak rows with missing `condition`, missing `start_date`/`end_date`, or
  missing `streak_length` should fall back to text/detail without throwing.
- Long player names, team names, and condition labels must wrap within streak
  cards on mobile.
- `is_active` is numeric today (`0`/`1`), not a boolean.
- Count values can be zero and may have no finder detail.
- Count routes may be finder-derived or occurrence-derived; only finder-derived
  counts can preserve matching-game detail today.
- Occurrence leaderboard event labels can be long dynamic column names.
- Occurrence leaderboards can be league-wide and should remain neutral; do not
  use full-surface team theming from row-level team abbreviations.
- Missing player ids/team ids are expected in occurrence rows.

---

## Residual contract gaps

- Count should eventually be reconciled with `docs/reference/result_contracts.md`
  as either a first-class result class or a documented derived finder/leaderboard
  specialization.
- Streak results would support better visualizations if the API emitted a
  per-game streak-detail section or structured condition metadata. C6 should
  not block on that; it can ship a span/card layout from current rows.
- Occurrence leaderboards would be easier to render if the event definition and
  metric key were metadata fields instead of dynamic columns. C6 can infer the
  event-count column conservatively from current rows, but should preserve the
  full detail table.
- Occurrence count results currently lose the source leaderboard row and do not
  include qualifying game detail. The count renderer should display the answer
  and documented context without implying expandable detail exists.
