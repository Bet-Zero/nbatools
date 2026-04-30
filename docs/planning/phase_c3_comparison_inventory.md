# Phase C3 Comparison Inventory

> **Role:** row-shape and renderer-boundary inventory for
> [`phase_c3_work_queue.md`](./phase_c3_work_queue.md), item 1.

This inventory records the current comparison result shapes that feed
`frontend/src/components/ComparisonSection.tsx`. It is implementation guidance
for the C3 player-comparison renderer, not a new API contract.

Evidence sources:

- `ComparisonResult` in `src/nbatools/commands/structured_results.py`
- `player_compare.build_result()`
- `team_compare.build_result()`
- `team_record.build_matchup_record_result()`
- `playoff_history.build_matchup_by_decade_result()`
- `playoff_history.build_playoff_matchup_history_result()`
- `query_service` metadata identity resolution
- Current `ComparisonSection.tsx` and `ResultSections.tsx`

---

## Shared result contract

All comparison-shaped command results currently serialize through:

- `query_class: "comparison"`
- `sections.summary: SectionRow[]`
- `sections.comparison: SectionRow[]`
- CLI/raw labeled sections: `SUMMARY` and `COMPARISON`

The shared `ComparisonResult` container does not currently expose explicit
metadata for comparison entity type, primary metric priority, display order, or
which comparison rows are safe for leader/tie emphasis. The C3 frontend should
therefore use route-specific ownership for `player_compare` and preserve the
generic comparison fallback for other routes.

Query metadata can provide identity context:

- `players_context` for two resolved players in comparison queries
- `teams_context` for two resolved teams in team comparison queries
- `player_context` / `team_context` when only one entity resolves

For structured-query calls, metadata is built from kwargs such as `player_a`,
`player_b`, `team_a`, and `team_b`. For natural queries, the same response
envelope carries query-level route and identity context when resolution
succeeds.

---

## Representative row shapes

### Player comparison: `player_compare`

Typical `summary` columns:

```text
player_name, games, wins, losses, win_pct, minutes_avg, pts_avg, reb_avg,
ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, plus_minus_avg, efg_pct_avg,
ts_pct_avg, usg_pct_avg, ast_pct_avg, reb_pct_avg, pts_sum, reb_sum, ast_sum
```

Typical `comparison` columns:

```text
metric, <player_a display name>, <player_b display name>
```

Reliable fields:

- `summary[].player_name` is the row entity label.
- `summary[]` contains sample-size, record, per-game box-score, shooting,
  plus-minus, sample-aware rate, and total fields.
- `comparison[].metric` is a metric key such as `games`, `win_pct`,
  `pts_avg`, `reb_avg`, `ast_avg`, `efg_pct_avg`, `ts_pct_avg`, `usg_pct_avg`,
  or `pts_sum`.
- The two value columns in `comparison` are display names from the request.
- `metadata.players_context` is the reliable source for `player_id` values and
  resolved player names when both players resolve.
- `metadata.head_to_head_used`, route caveats, season/window fields, opponent,
  and notes/caveats carry comparison context.

Gaps:

- Summary rows do not include `player_id`, current/latest team id, team
  abbreviation, or team name.
- The comparison value column names are display names, not stable ids.
- There is no explicit response field naming the two comparison column keys or
  mapping each summary row to a metadata identity object.
- There is no ranked/primary metric metadata. C3 should choose visual priority
  conservatively from known summary/comparison fields.

C3 target:

- Route `player_compare` only to the new player-comparison renderer.
- Build player identity from `metadata.players_context` when available and
  fall back to `summary[].player_name`.
- Render summary cards and metric comparison from existing values.
- Keep full summary and comparison tables visible.

### Team comparison: `team_compare`

Typical `summary` columns:

```text
team_name, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, stl_avg,
blk_avg, fg3m_avg, tov_avg, plus_minus_avg, efg_pct_avg, ts_pct_avg, pts_sum,
reb_sum, ast_sum
```

Typical `comparison` columns:

```text
metric, <team_a display token>, <team_b display token>
```

Reliable fields:

- `summary[].team_name` is the row entity label.
- `metadata.teams_context` can provide resolved team ids, abbreviations, and
  names when both teams resolve.
- Head-to-head, home/away, win/loss, opponent, date-window, and last-N filters
  are reflected through metadata and caveats.

Why C3 should not own it:

- Team comparison needs a team-specific comparison treatment, not player cards.
- Team color scoping is more delicate in two-team views and belongs to a later
  team/head-to-head phase.
- Keeping it on `ComparisonSection.tsx` avoids accidentally styling team,
  matchup, and playoff comparison routes as player-vs-player results.

### Team matchup record: `team_record.build_matchup_record_result()`

Typical `summary` columns:

```text
team_name, games, wins, losses, win_pct, pts_avg, reb_avg, ast_avg, fg3m_avg,
tov_avg, plus_minus_avg
```

Typical `comparison` columns:

```text
metric, <TEAM_A token>, <TEAM_B token>
```

Reliable fields:

- `summary[].team_name` is the row entity label.
- `comparison[].metric` includes record rows plus selected game-average stats.
- Caveats describe matchup-only sample semantics and filters.

Why C3 should not own it:

- This is a head-to-head/matchup record shape, not a player comparison.
- Later head-to-head/team-record phases can render matchup records with team
  identities, series context, and game-list treatment.

### Matchup by decade: `playoff_history.build_matchup_by_decade_result()`

Typical `summary` columns:

```text
team_name, games, wins, losses, win_pct
```

Typical `comparison` columns:

```text
decade, <TEAM_A>_wins, <TEAM_A>_losses, <TEAM_A>_win_pct,
<TEAM_B>_wins, <TEAM_B>_losses, <TEAM_B>_win_pct
```

Reliable fields:

- `summary` is team-record shaped.
- `comparison` is not `metric + entity columns`; each row is a decade bucket
  with dynamic team-prefixed columns.

Why C3 should not own it:

- The comparison rows are bucket records rather than metric rows.
- A future playoff/head-to-head renderer should handle decade or series
  breakdowns explicitly.

### Playoff matchup history: `playoff_history.build_playoff_matchup_history_result()`

Typical `summary` columns:

```text
team_name, games, wins, losses, win_pct
```

Typical `comparison` columns when grouped by season:

```text
season, round, <TEAM_A>_wins, <TEAM_A>_losses, <TEAM_B>_wins,
<TEAM_B>_losses
```

Typical `comparison` columns when grouped by round:

```text
round, <TEAM_A>_wins, <TEAM_A>_losses, <TEAM_B>_wins, <TEAM_B>_losses
```

Reliable fields:

- `summary` is team-record shaped.
- `comparison` rows are playoff buckets, not generic metric rows.
- Caveats may include playoff round coverage limitations.

Why C3 should not own it:

- Playoff matchup history needs a playoff-specific layout and coverage
  treatment.
- Applying player-comparison cards or metric leader emphasis here would confuse
  the route boundary.

---

## Renderer boundary guidance

C3 should introduce a dedicated player-comparison renderer only for:

- `data.route === "player_compare"`, or
- `data.result.metadata.route === "player_compare"`

Everything else with `query_class: "comparison"` should remain on
`ComparisonSection.tsx` for now, including:

- `team_compare`
- `team_matchup_record`
- `matchup_by_decade`
- `playoff_matchup_history`
- `playoff_round_record` comparison-shaped paths if routed as comparison later
- unknown or future comparison-shaped routes

This route boundary is intentionally narrower than `query_class: "comparison"`.
It keeps C3 scoped to player-vs-player UX and avoids leaking player-specific
layout decisions into team or playoff comparisons.

---

## Player-comparison metric priority guidance

Use this conservative hierarchy for C3:

1. **Player identity:** prefer `metadata.players_context` in response order;
   fall back to `summary[].player_name`.
2. **Card top-line stats:** prefer `pts_avg`, `reb_avg`, `ast_avg`, then
   `games`, `wins`/`losses`, `win_pct`, `minutes_avg`, and selected efficiency
   fields when present.
3. **Comparison metric rows:** consume rows from `sections.comparison` as-is.
   The `metric` field is the label/key; the two player display-name columns are
   values.
4. **Difference emphasis:** presentation may compare existing numeric values to
   mark a leader or tie. It should not compute new NBA metrics or change sort
   order.
5. **Secondary context:** use metadata season/window, `head_to_head_used`,
   opponent, notes, and caveats as context. Do not infer unavailable context.
6. **Detail tables:** always keep summary and comparison tables available for
   unpromoted fields and exact values.

Metric rows that should remain detail-safe rather than visually overpromoted:

- missing or nonnumeric values
- rows where both values are null/empty
- unknown custom metric labels
- totals/rates whose "better" direction is ambiguous without a product decision

For first implementation, it is acceptable to visually emphasize direct numeric
differences for standard positive-is-better metrics and to show ties/sparse rows
without leader emphasis.

---

## Residual API/result-contract gaps

These gaps should not block C3 frontend work, but they should guide future
engine/API improvements:

- `ComparisonResult.metadata` does not name `entity_type`, comparison column
  keys, primary metric priority, or whether higher values are always better for
  a metric.
- Player summary rows do not carry `player_id` or team context. The UI must
  join to `metadata.players_context` by response order/name when available.
- Team summary rows do not consistently carry `team_id` or `team_abbr`; team
  comparison remains generic until a team-specific phase.
- Comparison rows use display names as value columns, which can be awkward for
  stable mapping if aliases or duplicate names ever appear.
- Playoff and decade comparison routes use bucket-shaped rows under the same
  `comparison` section name, so route-specific boundaries are required.
