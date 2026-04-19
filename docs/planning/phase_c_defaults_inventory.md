# Phase C Defaults Inventory

> **Purpose:** Catalog every implicit default in `_finalize_route` and its helper routers, map each to spec §15, and identify gaps.
>
> **Generated for:** Phase C item 1

---

## How to read this inventory

Each entry records:

- **Branch / route:** The routing branch and target route
- **Trigger condition:** When this branch fires
- **Implicit defaults applied:** What values the router fills in without user input
- **`notes` entry present?** Whether the branch documents the default via `notes`
- **Spec §15 mapping:** Which spec rule covers this default (or "undocumented")

---

## 1. Defaults in `_finalize_route` (natural_query.py)

### 1.1 Season-high — single player → `player_game_finder`

| Field | Value |
|---|---|
| **Trigger** | `season_high_intent` and `player` present (no player_a/player_b) |
| **Defaults** | `stat` → `"pts"` if not specified; `limit` → `top_n or 5`; `sort_by` → `"stat"`; `ascending` → `False` |
| **`notes`** | Yes: `"season_high: showing top single-game performances"` |
| **Spec §15** | §15.1 — "Season-high without player" covers league-wide; single-player variant undocumented in spec |

### 1.2 Season-high — league-wide → `top_player_games`

| Field | Value |
|---|---|
| **Trigger** | `season_high_intent` and no player/player_a/player_b |
| **Defaults** | `season` → `default_season_for_context(season_type)` if not set; `stat` → `"pts"`; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | §15.1 — "Season-high without player → league-wide top_player_games" |

### 1.3 Distinct player count → `player_occurrence_leaders`

| Field | Value |
|---|---|
| **Trigger** | `distinct_player_count` and (`occurrence_event` or stat+min_value) |
| **Defaults** | `limit` → `None` (no cap) |
| **`notes`** | Yes: `"distinct_count: counting distinct players meeting condition"` |
| **Spec §15** | Undocumented (not listed in §15.1 or §15.2) |

### 1.4 Team streak → `team_streak_finder`

| Field | Value |
|---|---|
| **Trigger** | `team` + `team_streak_request` + no other entity conflicts |
| **Defaults** | `limit` → `25`; streak params from `team_streak_request` dict |
| **`notes`** | No |
| **Spec §15** | §15.1 — "Streak query without explicit time → three-season window" (time default is upstream, not in this branch) |

### 1.5 Player split summary → `player_split_summary`

| Field | Value |
|---|---|
| **Trigger** | `split_type` + `player` (no player_a/player_b) |
| **Defaults** | None beyond what the parser already set |
| **`notes`** | No |
| **Spec §15** | Not applicable (no implicit defaults beyond parser-level) |

### 1.6 Team split summary → `team_split_summary`

| Field | Value |
|---|---|
| **Trigger** | `split_type` + `team` (no team_a/team_b) |
| **Defaults** | None beyond what the parser already set |
| **`notes`** | No |
| **Spec §15** | Not applicable |

### 1.7 Player compare → `player_compare`

| Field | Value |
|---|---|
| **Trigger** | `player_a` + `player_b` |
| **Defaults** | None — all fields passed through from parse state |
| **`notes`** | No |
| **Spec §15** | Not applicable |

### 1.8 Team matchup record → `team_matchup_record`

| Field | Value |
|---|---|
| **Trigger** | `team_a` + `team_b` + `record_intent` |
| **Defaults** | None — all fields passed through |
| **`notes`** | No |
| **Spec §15** | Not applicable |

### 1.9 Team compare → `team_compare`

| Field | Value |
|---|---|
| **Trigger** | `team_a` + `team_b` (no record_intent) |
| **Defaults** | None — all fields passed through |
| **`notes`** | No |
| **Spec §15** | Not applicable |

### 1.10 Player streak → `player_streak_finder`

| Field | Value |
|---|---|
| **Trigger** | `player` + `streak_request` (no player_a/player_b) |
| **Defaults** | `limit` → `25`; streak params from `streak_request` dict |
| **`notes`** | No |
| **Spec §15** | §15.1 — "Streak query without explicit time → three-season window" (time default is upstream) |

### 1.11 Top player games (keyword-based) → `top_player_games`

| Field | Value |
|---|---|
| **Trigger** | `"top"` + `"games"` in query, no player, has scoring/stat signal, no leaderboard_intent |
| **Defaults** | `season` → `default_season_for_context(season_type)`; `stat` → `"pts"`; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented (variant of season-high, string-match trigger) |

### 1.12 Top team games (keyword-based) → `top_team_games`

| Field | Value |
|---|---|
| **Trigger** | `"top team"` in query or `"top"` + `"team games"` in query |
| **Defaults** | `season` → `default_season_for_context(season_type)`; `stat` → `"pts"`; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

### 1.13 No-subject leaderboard — team → `season_team_leaders`

| Field | Value |
|---|---|
| **Trigger** | No player/team entities + (`leaderboard_intent` or `team_leaderboard_intent`) + `team_leaderboard_intent` is true |
| **Defaults** | `season` → `default_season_for_context(season_type)` if no season/range; `stat` → `detect_team_leaderboard_stat(q)` or `stat` or `"pts"`; `limit` → `top_n or 10`; `min_games` → `1`; ascending via `wants_ascending_leaderboard` + smart lower-is-better logic; fallback stat → `"pts"` for date-window/multi-season when stat is season-only |
| **`notes`** | Only on stat fallback: `"stat_fallback: {stat} not available with date window, using pts"` |
| **Spec §15** | §15.2 — "`<metric>` only, no subject → league-wide leaderboard" |

### 1.14 No-subject leaderboard — team via keyword → `season_team_leaders`

| Field | Value |
|---|---|
| **Trigger** | Same no-entity condition + `"team"` or `"teams"` in query text (not team_leaderboard_intent) |
| **Defaults** | Same as 1.13 but `stat` → `stat or "pts"` (no `detect_team_leaderboard_stat`) |
| **`notes`** | Only on stat fallback |
| **Spec §15** | §15.2 — same as 1.13 |

### 1.15 No-subject leaderboard — player → `season_leaders`

| Field | Value |
|---|---|
| **Trigger** | Same no-entity condition, not team_leaderboard_intent, no "team"/"teams" in query |
| **Defaults** | `season` → `default_season_for_context(season_type)` if no season/range; `stat` → `detect_player_leaderboard_stat(q)` or `stat` or `"pts"`; `limit` → `top_n or 10`; `min_games` → `1`; ascending via `wants_ascending_leaderboard` + smart lower-is-better logic; fallback stat → `"pts"` for multi-season/opponent contexts when stat is season-only |
| **`notes`** | Only on stat fallback |
| **Spec §15** | §15.2 — "`<metric>` only, no subject → league-wide leaderboard" |

### 1.16 Explicit finder/count — player → `player_game_finder`

| Field | Value |
|---|---|
| **Trigger** | (`finder_intent` or `count_intent`) + `player` |
| **Defaults** | `limit` → `None` if count_intent, else `25`; `sort_by` → `"stat"` if stat present, else `"game_date"`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Not a default route — explicit user intent drives this |

### 1.17 Explicit finder/count — team → `game_finder`

| Field | Value |
|---|---|
| **Trigger** | (`finder_intent` or `count_intent`) + `team` |
| **Defaults** | Same as 1.16 |
| **`notes`** | No |
| **Spec §15** | Not a default route — explicit user intent |

### 1.18 Player summary (default route) → `player_game_summary`

| Field | Value |
|---|---|
| **Trigger** | `player` + any of: `summary_intent`, `career_intent`, `range_intent`, "record"/"averages"/"average" in query, **OR** `(season or start_season or last_n)` with a long guard-clause list excluding opponent, date range, stat filter, occurrence_event, streak, season_high, split, and "games in" idiom |
| **Defaults** | The `<player> + <timeframe>` only → summary default. No stat/filter/opponent signals needed. All parse-state fields passed through. |
| **`notes`** | No |
| **Spec §15** | §15.2 — "`<player> + <timeframe>` only → summary" |

### 1.19 Team record (explicit) → `team_record`

| Field | Value |
|---|---|
| **Trigger** | `team` + `record_intent` (no team_a/team_b) |
| **Defaults** | None — explicit intent |
| **`notes`** | No |
| **Spec §15** | Not a default (explicit record_intent) |

### 1.20 Team summary → `game_summary`

| Field | Value |
|---|---|
| **Trigger** | `team` + any of: `summary_intent`, `career_intent`, `range_intent`, "record"/"averages"/"average" in query |
| **Defaults** | None beyond what the parser set |
| **`notes`** | No |
| **Spec §15** | Not applicable (explicit intent keywords) |

### 1.21 Fallback player → `player_game_finder`

| Field | Value |
|---|---|
| **Trigger** | `player` present, no other branch matched |
| **Defaults** | `limit` → `25`; `sort_by` → `"stat"` if stat, else `"game_date"`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented. This is the catch-all for any player query with a threshold, opponent, date range, etc. that didn't match a more specific route. Effectively `<player> + <threshold>` → finder (§15.2). |

### 1.22 Fallback team → `game_finder`

| Field | Value |
|---|---|
| **Trigger** | `team` present, no other branch matched |
| **Defaults** | `limit` → `25`; `sort_by` → `"stat"` if stat, else `"game_date"`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented. Catch-all for team queries with filters/thresholds. |

---

## 2. Defaults in helper routers

### 2.1 `try_playoff_record_route` (`_playoff_record_route_utils.py`)

#### 2.1.1 Playoff appearances → `playoff_appearances`

| Field | Value |
|---|---|
| **Trigger** | `playoff_appearance_intent` (no player_a/player_b) |
| **Defaults** | Season range → `resolve_career("Playoffs")` when all season params are None; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.2 Playoff matchup history → `playoff_matchup_history`

| Field | Value |
|---|---|
| **Trigger** | (`playoff_history_intent` or Playoffs+record_intent) + team_a + team_b |
| **Defaults** | Season range → `resolve_career("Playoffs")` when all None |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.3 Matchup by decade → `matchup_by_decade`

| Field | Value |
|---|---|
| **Trigger** | `by_decade_intent` + team_a + team_b |
| **Defaults** | Season range → `resolve_career(season_type)` when all None |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.4 Playoff history → `playoff_history`

| Field | Value |
|---|---|
| **Trigger** | `playoff_history_intent` + team (no team_a/team_b) |
| **Defaults** | Season range → `resolve_career("Playoffs")` when all None |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.5 Record by decade → `record_by_decade`

| Field | Value |
|---|---|
| **Trigger** | `by_decade_intent` + team (no team_a/team_b) |
| **Defaults** | Season range → `resolve_career(season_type)` when all None |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.6 Record by decade leaderboard → `record_by_decade_leaderboard`

| Field | Value |
|---|---|
| **Trigger** | `by_decade_intent` + (record/leaderboard intent) + no entities |
| **Defaults** | Season range → `resolve_career(season_type)` when all None; `stat` → `"wins"` (default), `"win_pct"` or `"losses"` by keyword; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.7 Playoff round record leaderboard → `playoff_round_record`

| Field | Value |
|---|---|
| **Trigger** | Playoffs + playoff_round_filter + record_intent + no entities |
| **Defaults** | Season range → `resolve_career("Playoffs")` when all None; `stat` → `"win_pct"` (default), `"wins"` or `"losses"` by keyword; `limit` → `top_n or 10`; `ascending` → `False` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.1.8 Playoff history with round filter → `playoff_history`

| Field | Value |
|---|---|
| **Trigger** | team + Playoffs + playoff_round_filter + record_intent |
| **Defaults** | Season range → `resolve_career("Playoffs")` when all None |
| **`notes`** | No |
| **Spec §15** | Undocumented |

### 2.2 `try_compound_occurrence_route` (`_occurrence_route_utils.py`)

#### 2.2.1 Compound occurrence — season default

| Field | Value |
|---|---|
| **Trigger** | compound_occurrence_conditions (≥2) + leaderboard/count/team intent |
| **Defaults** | `season` → `default_end_season(season_type)` when all season params are None |
| **`notes`** | No |
| **Spec §15** | §15.1 — "No season + any stat/filter signal → current season" |

#### 2.2.2 Compound occurrence — limit defaults

| Field | Value |
|---|---|
| **Trigger** | Various sub-branches within compound occurrence |
| **Defaults** | `limit` → `500` for single-player count / single-team count; `top_n or 10` for leaderboard |
| **`notes`** | No |
| **Spec §15** | Undocumented (implementation detail) |

### 2.3 Single occurrence leaderboard (`try_compound_occurrence_route`)

#### 2.3.1 Team occurrence leaderboard

| Field | Value |
|---|---|
| **Trigger** | `occurrence_leaderboard_intent` + occurrence_event + no player + team signal in query |
| **Defaults** | `season` → `default_end_season(season_type)` when all None; `stat` from occurrence_event or `"pts"`; `min_value` from event or `100`; `limit` → `top_n or 10` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.3.2 Player occurrence leaderboard (special event)

| Field | Value |
|---|---|
| **Trigger** | `occurrence_leaderboard_intent` + occurrence_event with `special_event` + no player |
| **Defaults** | `season` → `default_end_season(season_type)` when all None; `limit` → `top_n or 10` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

#### 2.3.3 Player occurrence leaderboard (stat threshold)

| Field | Value |
|---|---|
| **Trigger** | `occurrence_leaderboard_intent` + occurrence_event (stat-based) + no player |
| **Defaults** | `season` → `default_end_season(season_type)` when all None; `limit` → `top_n or 10` |
| **`notes`** | No |
| **Spec §15** | Undocumented |

### 2.4 `try_occurrence_count_route` (`_occurrence_route_utils.py`)

| Field | Value |
|---|---|
| **Trigger** | `count_intent` + occurrence_event with `special_event` + player |
| **Defaults** | `season` → `default_end_season(season_type)` when all None; `limit` → `500` (to ensure player is included) |
| **`notes`** | No |
| **Spec §15** | §15.2 — partially covered by "`<player> + <threshold>` only → occurrence / count" |

### 2.5 `try_record_leaderboard_route` (`_playoff_record_route_utils.py`)

| Field | Value |
|---|---|
| **Trigger** | `record_intent` + no entities |
| **Defaults** | `season` → `default_end_season(season_type)` when all None; `stat` → `"win_pct"` (default), `"wins"` or `"losses"` by keyword; `limit` → `top_n or 10`; ascending logic via `wants_ascending_leaderboard` + smart keyword matching; playoff_round_filter redirects to `playoff_round_record` route |
| **`notes`** | Empty list (returned but never populated) |
| **Spec §15** | Undocumented |

---

## 3. Cross-cutting defaults (applied upstream of `_finalize_route`)

These are not in `_finalize_route` itself but affect every route:

| Default | Where applied | Spec §15 |
|---|---|---|
| No season → `default_season_for_context(season_type)` → current season | Multiple branches in `_finalize_route` and helpers | §15.1 ✓ |
| `recent form` → `last_n = 10` | Parser-level (`_parse_helpers.py`) | §15.1 ✓ |
| Streak without time → three-season window | Streak command internals | §15.1 ✓ |
| Occurrence event stat/min_value propagation | Top of `_finalize_route` (occurrence_event → stat/min_value) | Not a user-facing default |

---

## 4. Gap analysis: Spec §15 vs. implementation

### §15.1 (already in place) — coverage check

| Spec rule | Implemented? | `notes` entry? |
|---|---|---|
| No season + stat/filter signal → current season | ✓ | No |
| `recent form` → `last_n = 10` | ✓ | No |
| Streak without time → three-season window | ✓ | No |
| Season-high without player → league-wide | ✓ | No |

### §15.2 (to formalize) — coverage check

| Spec rule | Implemented? | `notes` entry? | Notes |
|---|---|---|---|
| `<player> + <timeframe>` → summary | ✓ (branch 1.18) | No | Guard-clause list exists, well-commented |
| `<team> + <opponent-quality>` → record | Partial (needs opponent-quality detection) | No | Not yet a distinct route |
| `<player> + <threshold>` → occurrence/count | ✓ (fallback 1.21 routes to finder; occurrence count via 2.4) | No | Boundary between finder and occurrence unclear |
| `"best games" + <subject>` → ranked game logs | ✓ (season_high_intent, branch 1.1) | Yes (season_high) | Only for "season high" phrasing |
| `<team> + recently` → recent record/summary | ✓ (team summary with last_n) | No | No explicit "recently" → last_n default for teams |
| `<player> + recently` → recent stat line | ✓ (player summary with last_n) | No | Handled by "recent form" → last_n=10 |
| `<metric>` only → league-wide leaderboard | ✓ (branches 1.13–1.15) | No (only stat_fallback notes) | Works but no default-documentation note |
| `<player> + vs <team-quality>` → filtered summary | Not implemented | No | Opponent-quality filtering not yet shipped |

### Undocumented defaults (in code but not in spec)

| Default | Branch | Should be in spec? |
|---|---|---|
| Player season-high: stat → `"pts"`, limit → 5 | 1.1 | Yes |
| League-wide season-high: stat → `"pts"`, limit → 10 | 1.2, 1.11 | Yes |
| Distinct count: limit → None | 1.3 | No (implementation detail) |
| Streak finders: limit → 25 | 1.4, 1.10 | No (presentation detail) |
| Finder fallback: limit → 25, sort_by logic | 1.16–1.17, 1.21–1.22 | Partially (sort policy could be documented) |
| Leaderboard: limit → 10, min_games → 1 | 1.13–1.15 | Yes (product policy) |
| Leaderboard: smart ascending for lower-is-better stats | 1.13–1.15 | Yes (product policy) |
| Leaderboard: stat fallback → `"pts"` for unsupported contexts | 1.13–1.15 | Yes (already has notes) |
| Record leaderboard: stat → `"win_pct"` default | 2.5 | Yes |
| Playoff routes: season range → `resolve_career` when all None | 2.1.x | Yes (career-spanning default) |
| Top team games: stat → `"pts"`, limit → 10 | 1.12 | Yes |

---

## 5. Summary of findings

### Defaults with `notes` entries (3)

1. `season_high: showing top single-game performances` (branch 1.1)
2. `distinct_count: counting distinct players meeting condition` (branch 1.3)
3. `stat_fallback: {stat} not available ...` (leaderboard branches 1.13–1.15, record leaderboard 2.5)

### Defaults without `notes` entries that should have them (high priority for Phase C items 2–5)

1. **`<player> + <timeframe>` → summary** (branch 1.18) — most common underspecified pattern
2. **`<metric>` only → league-wide leaderboard** (branches 1.13–1.15) — second most common
3. **`<player> + <threshold>` → finder** (branch 1.21) — frequent shorthand
4. **Fallback team → game_finder** (branch 1.22) — common team shorthand
5. **League-wide season-high** (branch 1.2) — missing its notes entry
6. **Team summary** (branch 1.20) — explicit intent but no documentation
7. **Team/player streak finders** (branches 1.4, 1.10) — limit defaults
8. **All playoff/record helper routes** (section 2.1) — season-range defaults
9. **Leaderboard limit/min_games/ascending defaults** (branches 1.13–1.15)
10. **Record leaderboard stat/ascending defaults** (branch 2.5)

### Spec gaps to close in item 7

- §15.1 is incomplete — missing season-high stat default, leaderboard limit/min_games, streak limit
- §15.2 has items that are already implemented but not yet formalized with `notes`
- Several implemented defaults (top_player_games keyword trigger, record_by_decade, playoff routes) have no spec coverage at all
- Smart ascending for lower-is-better stats is product policy that should be documented
