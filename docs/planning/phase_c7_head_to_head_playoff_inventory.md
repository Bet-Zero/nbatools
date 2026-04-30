# Phase C7 Head-to-Head and Playoff Inventory

> Inventory for
> [`phase_c7_work_queue.md`](./phase_c7_work_queue.md) item 1. This records
> current API/frontend row shapes and renderer boundaries for head-to-head and
> playoff layouts before C7 runtime work begins.

---

## Sources reviewed

- `docs/planning/phase_v5_component_layout_inventory.md`
- `docs/reference/result_contracts.md`
- `frontend/src/components/ResultSections.tsx`
- `frontend/src/components/TeamRecordSection.tsx`
- `frontend/src/components/PlayerComparisonSection.tsx`
- `frontend/src/components/ComparisonSection.tsx`
- `frontend/src/components/SummarySection.tsx`
- `frontend/src/components/LeaderboardSection.tsx`
- `frontend/src/test/ResultSections.test.tsx`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/player_compare.py`
- `src/nbatools/commands/team_compare.py`
- `src/nbatools/commands/playoff_history.py`
- `src/nbatools/commands/structured_results.py`
- `src/nbatools/query_service.py`

---

## Current ownership

| Family | Current query class | Current owner | Sections | C7 target |
| --- | --- | --- | --- | --- |
| Team matchup record | `comparison` | `TeamRecordSection.tsx` | `summary`, `comparison` | Preserve or refine as the team head-to-head answer layout |
| Player head-to-head comparison | `comparison` | `PlayerComparisonSection.tsx` | `summary`, `comparison` | Add head-to-head-aware treatment without weakening ordinary player comparisons |
| Team head-to-head comparison | `comparison` | `ComparisonSection.tsx` | `summary`, `comparison` | Route-aware head-to-head layout or explicit fallback decision |
| Matchup by decade | `comparison` | `ComparisonSection.tsx` | `summary`, `comparison` | Head-to-head history layout with decade detail |
| Playoff history | `summary` | `SummarySection.tsx` | `summary`, `by_season` | Playoff-history cards before detail tables |
| Playoff appearances, team scoped | `summary` | `SummarySection.tsx` | `summary`, `by_season` | Team postseason appearance summary |
| Playoff appearances leaderboard | `leaderboard` | `LeaderboardSection.tsx` | `leaderboard` | Playoff-specific ranking treatment |
| Playoff matchup history | `comparison` | `ComparisonSection.tsx` | `summary`, `comparison` | Playoff matchup/history layout |
| Playoff round record leaderboard | `leaderboard` | `LeaderboardSection.tsx` | `leaderboard` | Playoff round/record ranking treatment |
| Ordinary comparisons/summaries/leaderboards | existing generic or prior-phase owners | existing sections | Must remain unchanged unless explicitly owned by C7 |
| Unknown/future shapes | any | Generic fallback | any non-empty section | Must remain available as safety net |

`ResultSections.tsx` currently routes `team_matchup_record` comparison results
to `TeamRecordSection.tsx`. It routes all `player_compare` results to
`PlayerComparisonSection.tsx` whether or not metadata says the sample is
head-to-head. `team_compare`, `matchup_by_decade`, and
`playoff_matchup_history` use `ComparisonSection.tsx`; `playoff_history` and
team-scoped `playoff_appearances` use `SummarySection.tsx`; playoff
leaderboards use `LeaderboardSection.tsx`.

---

## Representative shapes

### Team matchup record

Route: `team_matchup_record`
Query class: `comparison`
Sections: `summary`, `comparison`

Representative rows:

```json
{
  "summary": [
    {
      "team_name": "Boston Celtics",
      "games": 4,
      "wins": 3,
      "losses": 1,
      "win_pct": 0.75,
      "pts_avg": 118.2
    },
    {
      "team_name": "Los Angeles Lakers",
      "games": 4,
      "wins": 1,
      "losses": 3,
      "win_pct": 0.25,
      "pts_avg": 109.8
    }
  ],
  "comparison": [
    {
      "metric": "wins",
      "Boston Celtics": 3,
      "Los Angeles Lakers": 1
    }
  ]
}
```

Useful fields:

- Identity: `metadata.teams_context` when available; row-level `team_name`
  fallback.
- Primary answer: `wins`, `losses`, `win_pct`, `games`.
- Context: metadata `season`, `start_season`, `end_season`, `season_type`,
  `start_date`, `end_date`, and caveats for home/away, wins/losses, and stat
  filters.
- Detail: `comparison` rows carry metric-level values with display-name
  columns.

Gaps:

- Summary rows do not consistently carry `team_id` or `team_abbr`; metadata is
  the reliable identity source.
- No game-list section is emitted for the underlying head-to-head games.
- `comparison` columns are display names, not stable ids.

### Player head-to-head comparison

Route: `player_compare`
Query class: `comparison`
Sections: `summary`, `comparison`
Metadata marker: `head_to_head_used: true`

Representative rows:

```json
{
  "summary": [
    {
      "player_name": "Nikola Jokic",
      "games": 3,
      "wins": 2,
      "losses": 1,
      "win_pct": 0.667,
      "minutes_avg": 35.2,
      "pts_avg": 28.4,
      "reb_avg": 12.1,
      "ast_avg": 9.3
    },
    {
      "player_name": "Joel Embiid",
      "games": 3,
      "wins": 1,
      "losses": 2,
      "win_pct": 0.333,
      "minutes_avg": 34.7,
      "pts_avg": 30.1,
      "reb_avg": 10.8,
      "ast_avg": 5.7
    }
  ],
  "comparison": [
    {
      "metric": "pts_avg",
      "Nikola Jokic": 28.4,
      "Joel Embiid": 30.1
    }
  ]
}
```

Useful fields:

- Identity: `metadata.players_context` for headshots; row-level
  `player_name` fallback.
- Primary answer: `games`, `wins`, `losses`, `win_pct`, and selected supplied
  averages/sums.
- Context: `metadata.head_to_head_used`, season/date filters, opponent/team
  filters, and caveat `"head-to-head: only games where both players faced each
  other"`.

Gaps:

- No per-game matchup detail section is emitted.
- Summary rows do not carry `player_id`; metadata is the reliable id source.
- `comparison` columns are display names.

### Team head-to-head comparison

Route: `team_compare`
Query class: `comparison`
Sections: `summary`, `comparison`
Metadata marker: `head_to_head_used: true`

Representative rows:

```json
{
  "summary": [
    {
      "team_name": "Boston Celtics",
      "games": 4,
      "wins": 3,
      "losses": 1,
      "win_pct": 0.75,
      "pts_avg": 118.2,
      "reb_avg": 45.1,
      "ast_avg": 28.4
    },
    {
      "team_name": "Los Angeles Lakers",
      "games": 4,
      "wins": 1,
      "losses": 3,
      "win_pct": 0.25,
      "pts_avg": 109.8,
      "reb_avg": 42.6,
      "ast_avg": 24.9
    }
  ],
  "comparison": [
    {
      "metric": "win_pct",
      "BOS": 0.75,
      "LAL": 0.25
    }
  ]
}
```

Useful fields:

- Identity: `metadata.teams_context` when supplied; row-level `team_name`
  fallback.
- Primary answer: record fields and selected supplied averages/sums.
- Context: `metadata.head_to_head_used`, season/date filters, home/away,
  wins/losses, `last_n`, and caveats.

Gaps:

- Current frontend routes `team_compare` through generic `ComparisonSection`.
- No game-list section is emitted.
- Row ids/abbreviations are not consistently present.

### Matchup by decade

Route: `matchup_by_decade`
Query class: `comparison`
Sections: `summary`, `comparison`

Representative rows:

```json
{
  "summary": [
    { "team_name": "Boston Celtics", "games": 18, "wins": 10, "losses": 8, "win_pct": 0.556 },
    { "team_name": "Los Angeles Lakers", "games": 18, "wins": 8, "losses": 10, "win_pct": 0.444 }
  ],
  "comparison": [
    {
      "decade": "1980s",
      "BOS_wins": 4,
      "BOS_losses": 2,
      "BOS_win_pct": 0.667,
      "LAL_wins": 2,
      "LAL_losses": 4,
      "LAL_win_pct": 0.333
    }
  ]
}
```

Useful fields:

- Identity: metadata team contexts when available; summary `team_name`
  fallback.
- Primary answer: summary record fields.
- Detail: decade rows with team-prefixed win/loss/win_pct columns.
- Context: season range and season type; caveats can mark playoff-only data.

Gaps:

- Decade rows are wide and dynamic; team columns are abbreviation-prefixed, not
  structured nested objects.
- No per-game detail rows are emitted.

### Playoff history

Route: `playoff_history`
Query class: `summary`
Sections: `summary`, `by_season`

Representative rows:

```json
{
  "summary": [
    {
      "team_name": "Boston Celtics",
      "season_start": "2019-20",
      "season_end": "2024-25",
      "season_type": "Playoffs",
      "games": 63,
      "wins": 39,
      "losses": 24,
      "win_pct": 0.619,
      "seasons_appeared": 6,
      "playoff_round": "Finals"
    }
  ],
  "by_season": [
    {
      "season": "2023-24",
      "games": 19,
      "wins": 16,
      "losses": 3,
      "win_pct": 0.842,
      "deepest_round": "Finals"
    }
  ]
}
```

Useful fields:

- Identity: `metadata.team_context` when natural/structured metadata resolves
  the team; row-level `team_name` fallback.
- Primary answer: `seasons_appeared`, record fields, `season_start`,
  `season_end`, `playoff_round` when filtered.
- Detail: `by_season` or decade-style rows reuse the `by_season` section.
- Caveats: round-data coverage before `2001-02`, opponent filters, and
  multi-season aggregation.

Gaps:

- No playoff-specific result class or section names exist; playoff history is a
  summary result.
- No series/bracket object is emitted.
- `by_decade` output also uses `by_season`, so the UI must infer the row grain
  from columns.

### Playoff appearances

Route: `playoff_appearances`
Query classes: `summary` when a team is supplied; `leaderboard` for all-team
rankings.
Sections: `summary` + `by_season`, or `leaderboard`

Representative team summary:

```json
{
  "summary": [
    {
      "team_name": "Boston Celtics",
      "appearances": 6,
      "round": "Playoffs",
      "season_start": "2019-20",
      "season_end": "2024-25"
    }
  ],
  "by_season": [
    {
      "season": "2023-24",
      "games": 19,
      "wins": 16,
      "losses": 3,
      "win_pct": 0.842
    }
  ]
}
```

Representative leaderboard row:

```json
{
  "rank": 1,
  "team_abbr": "BOS",
  "team_name": "Boston Celtics",
  "appearances": 6,
  "round": "Playoffs",
  "seasons": "2019-20 to 2024-25"
}
```

Useful fields:

- Identity: summary metadata/row `team_name`; leaderboard `team_abbr` and
  `team_name`.
- Primary answer: `appearances`, `round`, `season_start`/`season_end` or
  `season`/`seasons`.
- Detail: team-scoped `by_season` rows show games/record per season.

Gaps:

- Leaderboard rows do not include `team_id`.
- Team-scoped and all-team modes use different query classes for the same
  route.

### Playoff matchup history

Route: `playoff_matchup_history`
Query class: `comparison`
Sections: `summary`, `comparison`

Representative rows:

```json
{
  "summary": [
    { "team_name": "Boston Celtics", "games": 7, "wins": 4, "losses": 3, "win_pct": 0.571 },
    { "team_name": "Miami Heat", "games": 7, "wins": 3, "losses": 4, "win_pct": 0.429 }
  ],
  "comparison": [
    {
      "season": "2022-23",
      "round": "Conference Finals",
      "BOS_wins": 3,
      "BOS_losses": 4,
      "MIA_wins": 4,
      "MIA_losses": 3
    }
  ]
}
```

Useful fields:

- Identity: metadata team contexts when available; summary `team_name`
  fallback.
- Primary answer: summary record fields.
- Detail: `comparison` rows by season or by round with team-prefixed
  win/loss columns and `round`.
- Context: season range, optional round filter, playoff-only caveats.

Gaps:

- No explicit series winner or series count field exists.
- No game list or bracket detail is emitted.
- Dynamic team-prefixed columns require conservative display only.

### Playoff round record leaderboard

Route: `playoff_round_record`
Query class: `leaderboard`
Sections: `leaderboard`

Representative row:

```json
{
  "rank": 1,
  "team_name": "Boston Celtics",
  "team_abbr": "BOS",
  "team_id": 1610612738,
  "games_played": 42,
  "wins": 28,
  "losses": 14,
  "win_pct": 0.667,
  "round": "Finals",
  "seasons": "1980-81 to 2024-25",
  "season_type": "Playoffs"
}
```

Useful fields:

- Identity: `team_id`, `team_abbr`, `team_name`.
- Primary answer: configured target stat is one of `wins`, `losses`, or
  `win_pct`; `games_played` is sample context.
- Context: `round`, `season`/`seasons`, `season_type`.
- Caveats: round-data coverage and target stat label.

Gaps:

- The target stat is only present in caveats, not structured metadata.
- No minimum-games metadata is emitted beyond the filtered result set.

---

## Renderer boundary decisions for C7

Owned by C7:

- `team_matchup_record`, preserving the C5 team-record behavior while deciding
  whether its matchup path stays in `TeamRecordSection.tsx` or moves to a C7
  head-to-head owner.
- `player_compare` and `team_compare` only when metadata marks
  `head_to_head_used: true`.
- `matchup_by_decade`.
- `playoff_history`.
- `playoff_appearances` in both team-scoped summary mode and all-team
  leaderboard mode.
- `playoff_matchup_history`.
- `playoff_round_record`.

Preserve existing behavior:

- Ordinary `player_compare` continues through `PlayerComparisonSection.tsx`.
- Ordinary `team_compare` and unknown comparison-shaped routes remain on
  `ComparisonSection.tsx` unless C7 explicitly owns a head-to-head marker.
- Ordinary summary routes, non-playoff team summaries, and unknown
  summary-shaped routes keep their current owners.
- Ordinary leaderboards, occurrence leaderboards, top-game leaderboards, and
  record leaderboards keep their current owners.
- Unknown query classes and unknown section keys keep the generic fallback.

---

## Promoted-field candidates

| Shape | Primary fields | Secondary fields | Detail-only/default table fields |
| --- | --- | --- | --- |
| Team matchup record | `team_name`, `wins`, `losses`, `win_pct`, `games` | `pts_avg`, `reb_avg`, `ast_avg`, season/date filters, caveats | metric comparison rows |
| Player head-to-head comparison | `player_name`, `games`, `wins`, `losses`, `win_pct`, key averages | advanced averages/sums, metadata player identity, caveats | full metric comparison rows |
| Team head-to-head comparison | `team_name`, `games`, `wins`, `losses`, `win_pct`, key averages | metadata team identity, home/away/date filters, caveats | full metric comparison rows |
| Matchup by decade | summary records, decade labels | season range, season type, playoff-only caveat | wide team-prefixed decade columns |
| Playoff history | `team_name`, `seasons_appeared`, record, `season_start`, `season_end`, `playoff_round` | deepest round, opponent filters, coverage caveats | season/decade breakdown rows |
| Playoff appearances | `appearances`, `round`, team identity | season span, season records | by-season rows or full leaderboard rows |
| Playoff matchup history | summary records, `round`, `season` | round filters, season range, coverage caveats | team-prefixed season/round rows |
| Playoff round record leaderboard | rank, team identity, `wins`/`losses`/`win_pct`, `round` | `games_played`, season span, season type | unpromoted leaderboard columns |

---

## Edge cases to cover during implementation

- Metadata may have identity context even when rows lack ids/abbreviations.
- Head-to-head comparison columns use display names, so renderer logic should
  avoid assuming stable entity keys from column names.
- Player/team head-to-head comparison results do not include the underlying game
  list.
- `playoff_appearances` can be `summary` or `leaderboard` depending whether a
  team is supplied.
- `playoff_history` uses `by_season` for both season and decade breakdowns.
- Round labels can be long and round coverage can be missing before `2001-02`;
  coverage caveats need to remain visible.
- Playoff matchup and decade rows use dynamic team-prefixed columns.
- Mixed head-to-head and playoff matchup views must remain neutral except for
  identity badges.

---

## Residual contract gaps

- A dedicated playoff result class or section naming convention would make
  playoff rendering less route/column dependent.
- Head-to-head and playoff matchup routes would support richer layouts if they
  emitted a game-detail section for the exact sample.
- Playoff matchup history does not emit series-level objects, winners, or
  bracket structure; C7 should not invent them.
- Leaderboard target metrics for `playoff_round_record` are caveat-level rather
  than metadata-level.
- Comparison column keys are display labels; stable entity ids/keys would make
  future diff and winner treatments safer.
