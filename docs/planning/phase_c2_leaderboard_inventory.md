# Phase C2 Leaderboard Inventory

> **Role:** row-shape and metric-priority inventory for
> [`phase_c2_work_queue.md`](./phase_c2_work_queue.md), item 1.

This inventory records the current leaderboard result shapes that feed
`frontend/src/components/LeaderboardSection.tsx`. It is implementation
guidance for the C2 renderer, not a new API contract.

Evidence sources:

- `LeaderboardResult` in `src/nbatools/commands/structured_results.py`
- `season_leaders.build_result()`
- `season_team_leaders.build_result()`
- `player_occurrence_leaders.build_result()`
- `team_occurrence_leaders.build_result()`
- `top_player_games.build_result()`
- `top_team_games.build_result()`
- Local read-only samples from 2024-25 Regular Season data

---

## Shared result contract

All leaderboard-shaped command results currently serialize through:

- `query_class: "leaderboard"`
- `sections.leaderboard: SectionRow[]`
- CLI/raw labeled section: `LEADERBOARD`

The shared `LeaderboardResult` container does not currently expose explicit
metadata for ranked metric, sort direction, limit, qualifier threshold, or row
entity type. The C2 frontend should therefore use conservative row inspection
for presentation while keeping full table detail visible.

---

## Representative row shapes

### Player season leaders: `season_leaders`

Sample columns for `season="2024-25", stat="pts", limit=3`:

```text
rank, player_name, player_id, team_abbr, games_played, pts_per_game, season, season_type
```

Reliable fields:

- `rank`
- `player_name`
- `player_id` for headshot identity
- `team_abbr` as a current/latest team context label
- `games_played`
- one dynamic ranked metric column, e.g. `pts_per_game`, `fg3_pct`,
  `games_30p`, `usg_pct`
- `season` or `seasons`
- `season_type`

Notes:

- `team_id` is not consistently emitted for player season leaders.
- Count-style metrics from `season_leaders` use dynamic columns such as
  `games_30p`; they are still player season leaderboard rows, not occurrence
  rows.
- Caveats/notes may describe game-log-derived samples, clutch filtering, date
  windows, multi-season aggregation, or opponent filters.

### Team season leaders: `season_team_leaders`

Sample columns for `season="2024-25", stat="pts", limit=3`:

```text
rank, team_name, team_abbr, team_id, games_played, pts_per_game, season, season_type
```

Reliable fields:

- `rank`
- `team_name`
- `team_abbr`
- `team_id` for logo identity
- `games_played`
- one dynamic ranked metric column, e.g. `pts_per_game`, `win_pct`,
  `off_rating`, `pace`
- `season` or `seasons`
- `season_type`

Notes:

- This is the strongest row shape for team identity.
- Advanced team metrics may come from season-advanced data when available; date
  windows and multi-season paths fall back to game-log-derived subsets and
  should rely on existing caveats.

### Player occurrence leaders: `player_occurrence_leaders`

Sample columns for `season="2024-25", stat="pts", min_value=30, limit=3`:

```text
rank, player_name, team_abbr, games_played, games_pts_30+, season, season_type
```

Reliable fields:

- `rank`
- `player_name`
- `team_abbr` when the source rows include it
- `games_played`
- one dynamic occurrence-count column, e.g. `games_pts_30+`,
  `games_pts_30+_reb_10+`, `triple doubles`
- `season` or `seasons`
- `season_type`

Gaps:

- `player_id` is not emitted, so headshot rendering must fall back to initials
  unless a later engine/API item adds the id.
- The occurrence event definition is encoded in the dynamic count-column name;
  there is no structured event metadata in `LeaderboardResult`.

### Team occurrence leaders: `team_occurrence_leaders`

Sample columns for `season="2024-25", stat="pts", min_value=120, limit=3`:

```text
rank, team_abbr, games_played, games_pts_120+, season, season_type
```

Reliable fields:

- `rank`
- a team grouping column, usually `team_abbr`
- `games_played`
- one dynamic occurrence-count column, e.g. `games_pts_120+`,
  `games_pts_120+_fg3m_15+`
- `season` or `seasons`
- `season_type`

Gaps:

- `team_id` and `team_name` are not guaranteed. Team badge/logo rendering must
  tolerate abbreviation-only rows.
- The event definition is encoded in the dynamic count-column name.

### Top player games: `top_player_games`

Sample columns for `season="2024-25", stat="pts", limit=3`:

```text
rank, player_name, player_id, team_abbr, game_date, game_id, pts,
opponent_team_abbr, is_home, is_away, season, season_type
```

Notes:

- These rows are ranked games, not aggregate entity leaderboards.
- They still carry player identity and a dynamic ranked stat value.
- Game context fields (`game_date`, `game_id`, opponent, home/away) should be
  secondary context or detail table columns in C2. A more game-card-specific
  treatment belongs to later finder/game-card phases.

### Top team games: `top_team_games`

Sample columns for `season="2024-25", stat="pts", limit=3`:

```text
rank, team_name, team_abbr, team_id, game_date, game_id, pts,
opponent_team_abbr, is_home, is_away, wl, season, season_type
```

Notes:

- These rows are ranked games, not aggregate team leaderboards.
- They carry strong team identity plus game context.
- The C2 row layout should render them without throwing and keep the detail
  table visible, but it should not over-specialize top-game rows at the expense
  of season leaderboards.

---

## Other leaderboard-shaped routes

Several routes map to `query_class: "leaderboard"` or return
`LeaderboardResult` but are not the primary C2 target:

- `player_stretch_leaderboard`
- `lineup_leaderboard`
- `team_record_leaderboard`
- `record_by_decade_leaderboard`
- playoff leaderboard paths such as `playoff_appearances` and round records

C2 should keep these rows rendering via generic, sparse-safe logic and the full
detail table. If a row shape lacks clear player/team identity or a single
ranked metric, it should degrade to rank + best available label + detail table
rather than attempting route-specific business logic.

---

## Metric priority guidance

Use this conservative hierarchy for the first C2 implementation:

1. **Rank:** prefer `rank`; fallback to row index only for display if `rank` is
   absent.
2. **Entity label:** prefer `player_name`, then `team_name`, then `team_abbr`,
   then lineup/member labels if present, then the first non-system string field.
3. **Identity assets:** use `player_id` for `Avatar`; use `team_id` plus
   `team_abbr`/`team_name` for `TeamBadge`; use abbreviation-only badge fallback
   when ids are missing.
4. **Ranked metric value:** prefer the first non-identity, non-context numeric
   metric after `games_played`; for occurrence rows, prefer the dynamic
   `games_*` or event-label count column; for top-game rows, prefer the
   requested stat column such as `pts`.
5. **Secondary metadata:** use `games_played`, `season`/`seasons`,
   `season_type`, `team_abbr`, `game_date`, opponent, W/L, and caveats as
   context rather than primary values.
6. **Detail table:** always keep `DataTable` detail visible for columns not
   promoted into the ranked row.

System/context columns that should not become the primary ranked metric:

- `rank`
- `player_id`
- `team_id`
- `player_name`
- `team_name`
- `team_abbr`
- `season`
- `seasons`
- `season_type`
- `game_id`
- `game_date`
- `is_home`
- `is_away`
- `wl`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`

`games_played` is context for most leaderboards. It can be the primary metric
only when no better dynamic metric exists or when a route clearly ranks by games
played.

---

## Residual API/result-contract gaps

These gaps should not block C2 frontend work, but they should guide future
engine/API improvements:

- `LeaderboardResult.metadata` does not name the ranked metric, requested stat,
  sort direction, limit, or qualifier thresholds.
- Player occurrence rows do not emit `player_id`.
- Team occurrence rows do not guarantee `team_id` or `team_name`.
- Top-game rows share `query_class: "leaderboard"` with aggregate leaderboards,
  even though their best future UI may be closer to game-card/finder layouts.
- Dynamic event-count columns encode event definitions in display column names
  instead of a structured event object.

The C2 renderer should therefore stay additive and tolerant: promote obvious
rank/entity/value fields, keep full details visible, and avoid claiming more
semantic certainty than the row provides.
