# Phase C5 Team And Split Layout Inventory

> **Role:** Planning inventory for Phase C5 team summary, team record, matchup
> record, and split-summary renderer work.
>
> This document records current structured result shapes and renderer ownership
> boundaries. It changes no runtime behavior.

---

## Sources Reviewed

- `docs/planning/phase_c5_work_queue.md`
- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/commands/game_summary.py`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/team_split_summary.py`
- `src/nbatools/commands/player_split_summary.py`
- `src/nbatools/commands/playoff_history.py`
- `src/nbatools/query_service.py`
- `frontend/src/api/types.ts`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/SplitSummarySection.tsx`

---

## Current Result Shapes

Phase C5 works across three structured result classes:

| Result class | Sections | Current generic owner | C5 route families |
| --- | --- | --- | --- |
| `summary` | `summary`, optional `by_season`, optional `game_log` | `SummarySection.tsx` except `player_game_summary` | `game_summary`, `team_record` |
| `comparison` | `summary`, `comparison` | `ComparisonSection.tsx` except `player_compare` | `team_matchup_record` only |
| `split_summary` | `summary`, `split_comparison` | `SplitSummarySection.tsx` | `team_split_summary`, and possibly `player_split_summary` for shared bucket layout |

`ResultSections.tsx` already protects player-specific owners for
`player_game_summary`, `player_compare`, and `player_game_finder`. C5 should
extend that route-aware dispatcher pattern instead of assigning all summaries,
all comparisons, or all split summaries to team-specific renderers.

---

## Team Summary: `game_summary`

**Shape:** `query_class: "summary"` with `summary` and optional `by_season`.

Representative `summary` row fields:

- Identity/context: `team_name`, `season_start`, `season_end`, `season_type`
- Record/sample: `games`, `wins`, `losses`, `win_pct`
- Team stats when present: `minutes_avg`, `minutes_sum`, `pts_avg`,
  `pts_sum`, `fgm_avg`, `fga_avg`, `fg3m_avg`, `fg3a_avg`, `ftm_avg`,
  `fta_avg`, `oreb_avg`, `dreb_avg`, `reb_avg`, `ast_avg`, `stl_avg`,
  `blk_avg`, `tov_avg`, `pf_avg`, `plus_minus_avg`, `efg_pct_avg`,
  `ts_pct_avg`, plus matching `_sum` fields for loaded numeric columns

Representative `by_season` fields:

- `season`, `games`, `wins`, `losses`
- Selected stat averages when present: `pts_avg`, `reb_avg`, `ast_avg`,
  `fg3m_avg`, `tov_avg`, `plus_minus_avg`, `efg_pct_avg`, `ts_pct_avg`

Stable identity source:

- `metadata.team_context` is the reliable source for `team_id`, `team_abbr`,
  and `team_name` when a single team was resolved.
- Summary rows currently carry `team_name` but do not consistently carry
  `team_id` or `team_abbr`.

C5 ownership:

- Owned by the new team-summary renderer when `data.route` or
  `data.result.metadata.route` is `game_summary`.
- Safe single-team scoped theming can use `metadata.team_context` when no
  multi-team or player context is present.

---

## Team Record: `team_record`

**Shape:** `query_class: "summary"` with `summary` and optional `by_season`.

Representative `summary` row fields:

- Identity/context: `team_name`, `season_start`, `season_end`, `season_type`
- Record/sample: `games`, `wins`, `losses`, `win_pct`
- Secondary stats when present: `pts_avg`, `reb_avg`, `ast_avg`, `fg3m_avg`,
  `stl_avg`, `blk_avg`, `tov_avg`, `plus_minus_avg`, `efg_pct_avg`,
  `ts_pct_avg`

Common filters and annotations:

- Opponent filters expose `metadata.opponent_context` when resolvable.
- Date windows, home/away, wins/losses, stat thresholds, clutch, period,
  schedule-context filters, and player-absence filters can appear as
  metadata, notes, or caveats depending on the route and query.

Stable identity source:

- `metadata.team_context` is reliable for the primary team.
- `metadata.opponent_context` is reliable for resolved opponent filters.
- Rows remain table-oriented and usually expose only `team_name` as identity.

C5 ownership:

- Owned by the team-summary/record renderer when `data.route` or
  `data.result.metadata.route` is `team_record`.
- Record values (`wins`, `losses`, `win_pct`, `games`) should be promoted
  before secondary stats. React should only display supplied values.

---

## Team Matchup Record: `team_matchup_record`

**Shape:** `query_class: "comparison"` with `summary` and `comparison`.

Representative `summary` row fields:

- One row per team with `team_name`, `games`, `wins`, `losses`, `win_pct`
- Secondary stat averages when present, including `pts_avg`, `reb_avg`,
  `ast_avg`, `fg3m_avg`, `tov_avg`, and `plus_minus_avg`

Representative `comparison` fields:

- `metric`
- One column per compared team using the display team name

Stable identity source:

- `metadata.teams_context` can provide stable team ids, abbreviations, and
  names for bounded team-vs-team contexts.
- The `comparison` table columns are display names, not stable ids.

C5 ownership:

- Route-specific C5 treatment may own only `team_matchup_record` among
  comparison results.
- Do not route all `query_class: "comparison"` results through team-record UI;
  `player_compare`, `team_compare`, playoff matchup routes, decade matchup
  routes, and unknown comparison-shaped results need their existing owners or
  generic fallback unless explicitly redesigned later.
- Matchup views should stay neutral overall, using identity badges or restrained
  accents rather than a single full-surface team theme.

---

## Team Split Summary: `team_split_summary`

**Shape:** `query_class: "split_summary"` with `summary` and
`split_comparison`.

Supported split labels today:

- `home_away`: bucket values `home`, `away`
- `wins_losses`: bucket values `wins`, `losses`

Representative `summary` row fields:

- `team_name`, `season_start`, `season_end`, `season_type`, `split`,
  `games_total`

Representative `split_comparison` row fields:

- Bucket/sample: `bucket`, `games`, `wins`, `losses`, `win_pct`
- Team stats: `pts_avg`, `reb_avg`, `ast_avg`, `stl_avg`, `blk_avg`,
  `fg3m_avg`, `tov_avg`, `efg_pct_avg`, `ts_pct_avg`, `plus_minus_avg`

Stable identity source:

- `metadata.team_context` is the primary identity source.
- `metadata.opponent_context` can exist for opponent-filtered splits.
- Bucket rows do not carry team identity.

C5 ownership:

- Owned by the split-summary redesign when `data.route` or
  `data.result.metadata.route` is `team_split_summary`.
- Bucket cards can promote `games`, `wins`, `losses`, `win_pct`, and supplied
  stat averages. Friendly bucket labels should be presentation-only mappings
  from the existing `bucket` values.

---

## Player Split Summary: `player_split_summary`

**Shape:** `query_class: "split_summary"` with `summary` and
`split_comparison`.

Supported split labels today:

- `home_away`: bucket values `home`, `away`
- `wins_losses`: bucket values `wins`, `losses`

Representative `summary` row fields:

- `player_name`, `season_start`, `season_end`, `season_type`, `split`,
  `games_total`

Representative `split_comparison` row fields:

- Bucket/sample: `bucket`, `games`, `wins`, `losses`, `win_pct`
- Box-score and rate stats: `minutes_avg`, `pts_avg`, `reb_avg`, `ast_avg`,
  `stl_avg`, `blk_avg`, `fg3m_avg`, `efg_pct_avg`, `ts_pct_avg`,
  `usg_pct_avg`, `ast_pct_avg`, `reb_pct_avg`, `plus_minus_avg`
- Additional grouped sample-aware advanced metrics may be merged into the same
  rows.

Stable identity source:

- `metadata.player_context` is the primary identity source.
- `metadata.team_context` or `metadata.opponent_context` can exist when the
  query includes team or opponent filters, but player-subject splits should not
  receive full-surface team theming by default.

C5 ownership:

- The split-summary layout can share bucket-card presentation across team and
  player split routes because both use `summary` plus `split_comparison`.
- Team-specific identity, logo, and scoped theme behavior applies only to
  `team_split_summary`. Player splits should remain neutral unless a later
  product decision assigns them a dedicated player-split owner.

---

## Playoff, Decade, And Unknown Fallbacks

Summary-shaped routes that should keep generic summary fallback during C5:

- `playoff_history`
- `record_by_decade`
- Any future or unknown `summary` result not explicitly owned by C5

Comparison-shaped routes that should keep existing comparison behavior during
C5 unless a later queue explicitly expands scope:

- `team_compare`
- `playoff_matchup_history`
- `matchup_by_decade`
- Unknown `comparison` results

Other non-C5 routes:

- `playoff_appearances`, `team_record_leaderboard`, `record_by_decade_leaderboard`,
  and occurrence routes are leaderboard or count-like work for later phases.
- `player_game_summary`, `player_compare`, and `player_game_finder` already
  have dedicated owners and must not regress.

Reasoning:

- Playoff and decade summaries share `team_name`, record fields, and
  `by_season`/decade tables, but they carry historical coverage caveats and
  playoff/era semantics that C5 is not redesigning.
- Unknown summary or split-shaped responses are safety-net cases. They should
  continue to render complete tables even if they do not receive designed
  cards.

---

## Field Priority For C5 Renderers

Team identity:

- Prefer `metadata.team_context.team_id`, `team_abbr`, and `team_name`.
- Fall back to row `team_name`, then metadata `team`, when identity context is
  absent.
- Use `metadata.teams_context` for matchup identity; do not infer stable ids
  from comparison display columns.

Opponent identity:

- Prefer `metadata.opponent_context`.
- Fall back to `metadata.opponent` or row opponent fields if present.

Record/sample:

- Promote `wins`, `losses`, `win_pct`, and `games` when present.
- Use `games_total` for split-summary sample size.
- Keep `season_start`, `season_end`, `season`, `season_type`, and
  `current_through` as context, not computed display state.

Headline team stats:

- Preferred team summary stats from existing rows: `pts_avg`, `reb_avg`,
  `ast_avg`, `fg3m_avg`, `tov_avg`, `plus_minus_avg`, `efg_pct_avg`,
  `ts_pct_avg`.
- Additional available detail stats can remain in tables.
- Do not synthesize pace, offensive rating, defensive rating, or unavailable
  advanced metrics in React.

Split buckets:

- Known values: `home`, `away`, `wins`, `losses`.
- Presentation labels may map these to "Home", "Away", "Wins", and "Losses".
- Unknown bucket labels should be title-cased or otherwise rendered plainly
  without changing the underlying row value.

Detail-only columns:

- Raw stat sums, rarely promoted box-score columns, playoff round/deepest-round
  fields, decade breakdown columns, caveats, and unrecognized fields should
  remain visible in `DataTable` detail sections.

---

## Residual API And Contract Gaps

These gaps should not block C5 frontend work, but they define what the layout
must avoid assuming:

- Team summary and record rows do not consistently include `team_id` or
  `team_abbr`; use metadata for identity and theming.
- Current team summaries do not emit pace, offensive rating, or defensive
  rating. C5 should narrow the visual target to supplied record and box-score
  metrics.
- Matchup comparison columns are display team names, not stable entity keys.
  Use `metadata.teams_context` for identity badges and keep the table for full
  metric detail.
- Split bucket rows do not emit per-bucket date ranges or richer bucket
  metadata. Bucket cards should use `bucket`, sample counts, record fields, and
  supplied stats only.
- Friendly split labels are not emitted by the engine. Frontend label mapping
  is acceptable as presentation formatting, not data semantics.
- Playoff and decade summaries use the same result classes as regular-season
  summaries, but their semantics and caveats are distinct. They should stay in
  fallback until a playoff-specific phase owns them.

---

## Recommended C5 Renderer Boundaries

Implement route checks in `ResultSections.tsx` or small route predicates:

- `isTeamSummaryRoute`: `game_summary`, `team_record`
- `isTeamMatchupRecordRoute`: `team_matchup_record`
- `isOwnedSplitSummaryRoute`: `team_split_summary`, optionally
  `player_split_summary` for shared neutral bucket-card layout

Keep these protections:

- `player_game_summary` continues to render through `PlayerSummarySection`.
- `player_compare` continues to render through `PlayerComparisonSection`.
- `player_game_finder` continues to render through `PlayerGameFinderSection`.
- Generic `SummarySection`, `ComparisonSection`, `SplitSummarySection`, and
  fallback rendering remain available for routes not explicitly owned by C5.
