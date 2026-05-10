# Raw Query Product Map — Return Package

> **Created:** May 10, 2026  
> **Task:** Discovery-only mapping of the current NBA tools query system (parser → route → result → display). No code changes. Practical reference for understanding what works, what's risky, and what to prioritize next.

---

## 1. Executive Summary

### What Was Mapped

A complete trace from natural-language questions through backend routes, result shapes, and frontend table patterns.

- **Backend query routes:** 30 discovered (list below)
- **Result shapes:** 24 named result shapes in frontend (entity_summary, game_log, leaderboard, split, streak, comparison, playoff, record, fallback, no-result)
- **Table pattern components:** 11 React components for rendering structured tables and cards
- **Data scope rules:** Season defaults, career ranges, playoff vs regular-season logic, operator keywords

### Biggest Finding

**The system is highly specialized per route.** Each of 30+ routes has:
- Hardcoded pattern config in frontend switch statement
- Route-specific column sets in table components
- Route-specific section names passed between backend and frontend

This works now but doesn't scale. Adding a 31st route or supporting a new metric requires edits to frontend pattern code + backend handler + tests. A centralized route-to-pattern registry (JSON/config-driven) would be lower maintenance.

### Route Inventory

**30 routes discovered:**
1. player_game_summary
2. player_game_finder
3. player_on_off
4. player_split_summary
5. player_streak_finder
6. player_compare
7. player_stretch_leaderboard
8. player_occurrence_leaders
9. game_finder
10. game_summary
11. team_record
12. team_split_summary
13. team_streak_finder
14. team_compare
15. team_matchup_record
16. season_leaders
17. season_team_leaders
18. top_player_games
19. top_team_games
20. team_record_leaderboard
21. playoff_history
22. playoff_appearances
23. playoff_matchup_history
24. playoff_round_record
25. record_by_decade
26. record_by_decade_leaderboard
27. matchup_by_decade
28. lineup_summary
29. lineup_leaderboard
30. (Unknown fallback routes from phase-gated features like occurrence_count)

**All routes are shipped and functional.** Some have incomplete execution (Phase G/H features like opponent_quality, clutch, period filters), but the core route infrastructure exists.

### Result Shapes

**24 named result shapes:** no_result_guided, no_result_message, entity_summary, entity_summary_with_gamelog, game_log_player_table, game_log_team_table, game_log_team_detail, split_table, on_off_split, streak_table, playoff_history, playoff_round_record, playoff_matchup_history, comparison, team_record, record_by_decade, record_by_decade_leaderboard, matchup_by_decade, leaderboard_table, top_performances, rolling_stretch, fallback_table, unclassified.

All shapes have documentation in `resultShapes.ts`; mapping to routes is in `routeToPattern.ts`.

### Table Patterns

**11 primary pattern components:**
- EntitySummaryResult (hero card)
- GameLogResult (game table)
- LeaderboardResult (ranked leaderboard)
- TopPerformancesResult (single-game leaderboard)
- RollingStretchResult (rolling window leaderboard)
- SplitResult (split bucket comparison)
- StreakResult (streak table)
- PlayoffHistoryResult (playoff record table)
- RecordResult (team record / decade breakdown)
- ComparisonResult (two-entity metric comparison)
- FallbackTableResult (generic fallback)

### Number of Backend Routes

**30 confirmed routes** in the route switch statement + tests.

### Number of Result Shapes

**24 named result shapes** (excluding unclassified).

### Number of Table Patterns

**11 specialized pattern components** + 1 fallback.

### Biggest Scalability Risk

**Risk: Route-specific pattern logic hardcoded in frontend switch statement.**

File: `frontend/src/components/results/config/routeToPattern.ts`

The `routeToPattern()` function is a 200+ line switch statement that must be updated every time a new route is added or pattern changes. This couples frontend closely to backend route names and means no one can add a route without touching frontend code.

**Also high risk:**
- Table columns hardcoded per component (new stats require code edits)
- Section name coupling (section names must match pattern config exactly or rendering fails silently)
- Distributed default rules (season defaults scattered across 4 files)

### Recommended Next Implementation Phase

**"Lock Core Patterns"** — 14-hour effort:

1. Audit all 30 routes to ensure they're in `routeToPattern` (find any falling through to fallback)
2. Create pattern contract tests (verify section names + column presence)
3. Document locked patterns (one-page spec per core route)
4. Align backend section names with frontend expectations
5. Create end-to-end rendering tests

**Why:** The system works but has no stability guarantees. New features (Phase H+) will break if patterns aren't locked. Tests will catch mismatches.

**After lock:** Implement Phase H complete features (opponent_quality, clutch, period, role filters) with confidence that core patterns won't shift.

---

## 2. Files Inspected

| File | Lines | Purpose | Key Content |
|---|---|---|---|
| [src/nbatools/commands/natural_query.py](src/nbatools/commands/natural_query.py) | 1750+ | Route finalization | 28+ route assignments; `_finalize_route()` decision logic; default policies applied |
| [src/nbatools/commands/_natural_query_execution.py](src/nbatools/commands/_natural_query_execution.py) | 300+ | Build result map | `_get_build_result_map()` maps all routes to command handlers; phase feature gates |
| [src/nbatools/commands/_default_rules.py](src/nbatools/commands/_default_rules.py) | 80+ | Underspecified query policies | 5 named default rules (player+timeframe→summary, metric-only→leaderboard, etc.) |
| [src/nbatools/commands/_parse_helpers.py](src/nbatools/commands/_parse_helpers.py) | 500+ | Parse utilities | Season/season-range extraction; season-type detection; position filtering |
| [src/nbatools/commands/_seasons.py](src/nbatools/commands/_seasons.py) | 150+ | Season helpers | Season constants, resolve_career(), resolve_since_year(), season_to_int() |
| [frontend/src/components/results/config/routeToPattern.ts](frontend/src/components/results/config/routeToPattern.ts) | 200+ | Route→Pattern mapping | 30-case switch mapping each route to PatternConfig stack |
| [frontend/src/components/results/resultShapes.ts](frontend/src/components/results/resultShapes.ts) | 150+ | Result shape defs | 24 named result shapes + description + ordering |
| [frontend/src/components/results/patterns/*.tsx](frontend/src/components/results/patterns/) | 2000+ lines total | Pattern renderers | 11 React components (GameLogResult, LeaderboardResult, ComparisonResult, etc.) |
| [docs/architecture/parser/examples.md](docs/architecture/parser/examples.md) | 500+ | Parser test inputs | 100+ canonical query examples grouped by intent |
| [docs/determination_layer_audit.md](docs/determination_layer_audit.md) | 1000+ | Audit of result contracts | Detailed breakdown of scope defaults, metadata, and rendering behavior per shape |

**Why each file matters:**
- `natural_query.py` — the source of truth for how queries are routed
- `_natural_query_execution.py` — map of which commands handle which routes
- `routeToPattern.ts` — how frontend decides what to display
- `resultShapes.ts` — vocabulary of result shapes; used for testing
- Pattern components — the actual rendering code; shows what data is expected
- Examples.md — user-facing query phrasings; shows parser coverage

---

## 3. Route → Result → Table Map

| Route | Intent | Example Queries | Data Scope/Default | Pattern Config | Result Shape | Table Pattern | Sections Used | Notes |
|---|---|---|---|---|---|---|---|---|
| player_game_summary | Summary | "Luka last 10", "Giannis recent" | 2025-26 RS, no limit | entity_summary + game_log | entity_summary_with_gamelog | Summary card + game log | summary, game_log | Shows if game_log rows ≥1; always includes hero summary |
| player_game_finder | Finder | "Curry 5+ threes" | 2025-26 RS, limit 25 | game_log | game_log_player_table | Player game log | finder | Sorted by stat (descending) or date |
| game_finder | Finder | "Lakers 100+ pts" | 2025-26 RS, limit 25 | game_log | game_log_team_table | Team game log | finder | Sorted by stat or date |
| game_summary | Summary | "Celtics last 5" | 2025-26 RS, no limit | game_log + details | game_log_team_detail | Team log + detail | game_log, top_performers | Detail drawer shows top performers |
| top_player_games | Leaderboard | "Highest scoring games" | 2025-26 RS, limit 10 | top_performances | top_performances | Single-game leaderboard | leaderboard | Ranked by stat (usually PPG) |
| top_team_games | Leaderboard | "Best team scoring nights" | 2025-26 RS, limit 10 | top_performances | top_performances | Single-game leaderboard | leaderboard | Ranked by stat (usually PPG) |
| season_leaders | Leaderboard | "Top scorers this season" | 2025-26 RS, limit 10 | leaderboard | leaderboard_table | Ranked table | leaderboard | League-wide ranking; position filter optional |
| season_team_leaders | Leaderboard | "Best def ratings" | 2025-26 RS, limit 10 | leaderboard | leaderboard_table | Ranked table | leaderboard | Team-wide ranking; stat fallback for unsupported stats |
| team_record_leaderboard | Leaderboard | (implicit playoff) | 2024-25 Playoffs, limit 10 | leaderboard | leaderboard_table | Ranked table | leaderboard | Team record leaderboard; used in playoff mode |
| player_occurrence_leaders | Leaderboard | "How many 40-point games" | 2025-26 RS, no limit | leaderboard | leaderboard_table | Ranked table | leaderboard | Count of events meeting threshold |
| team_occurrence_leaders | Leaderboard | (implicit) | 2025-26 RS, no limit | leaderboard | leaderboard_table | Ranked table | leaderboard | Count of team events |
| player_stretch_leaderboard | Leaderboard | "LeBron best 10-game stretch" | 2025-26 RS, limit 10 | rolling_stretch | rolling_stretch | Rolling window table | leaderboard | Window size + metric configurable |
| playoff_appearances | Leaderboard | "Most playoff appearances" | 1996-97 to 2024-25 Playoffs, limit 10 | leaderboard | leaderboard_table | Ranked table | leaderboard | Career playoff appearance count |
| player_split_summary | Split | "LeBron by location" | 2025-26 RS, no limit | split | split_table | Split comparison | (varies) | 2–3 bucket rows with edge chips |
| team_split_summary | Split | "Suns by location" | 2025-26 RS, no limit | split | split_table | Split comparison | (varies) | 2–3 bucket rows with edge chips |
| player_on_off | Split | "Jokic on/off impact" | 2025-26 RS, no limit | split | on_off_split | On/off comparison | summary | Specifically on/off split; 2 rows (on floor, off floor) |
| player_streak_finder | Streak | "Giannis longest scoring streak" | 3-season window by default | streak | streak_table | Streak table | streak | Ranked by streak length; limit 25 |
| team_streak_finder | Streak | "Warriors longest win streak" | 3-season window by default | streak | streak_table | Streak table | streak | Ranked by streak length; limit 25 |
| player_compare | Comparison | "Giannis vs Embiid" | 2025-26 RS, no limit | comparison | comparison | Comparison panels | (varies) | Two-player metric comparison + h2h if available |
| team_compare | Comparison | "Heat vs Nets" | 2025-26 RS, no limit | comparison | comparison | Comparison panels | (varies) | Two-team metric comparison |
| team_matchup_record | Comparison | "Dubs vs Lakers h2h" | 2025-26 RS, no limit | comparison | comparison | Comparison panels + h2h | (varies) | Head-to-head record emphasis |
| team_record | Record | "Sixers record vs .500 teams" | 2025-26 RS, no limit | record + game_log* | team_record | Record hero + summary | (varies) | Stacks game_log only if rows present |
| record_by_decade | Record | "Spurs record by decade" | 1996-97 to 2025-26 RS | record | record_by_decade | Decade breakdown table | (varies) | One row per decade |
| record_by_decade_leaderboard | Record | "Best 1980s records" | 1996-97 to 2025-26 RS, limit 10 | record | record_by_decade_leaderboard | Ranked decade table | leaderboard | Ranked by decade wins or win_pct |
| matchup_by_decade | Record | "Celtics vs Lakers by decade" | 1996-97 to 2025-26 RS | record | matchup_by_decade | Two-team decade table | (varies) | One row per decade with head-to-head W-L |
| playoff_history | Record | "Spurs playoff history" | 1996-97 to 2024-25 Playoffs | playoff_history | playoff_history | Playoff season table | (varies) | Season-by-season playoff record |
| playoff_matchup_history | Record | "Celtics vs Lakers playoffs" | 1996-97 to 2024-25 Playoffs | playoff_history | playoff_matchup_history | Two-team playoff table | (varies) | Series-by-series history |
| playoff_round_record | Record | (implicit playoff round filter) | 1996-97 to 2024-25 Playoffs, limit 10 | playoff_history | playoff_round_record | Playoff round leaderboard | leaderboard | Ranked by round; teams sorted by record in that round |
| lineup_summary | Summary | "LeBron + Kyrie + [3 others]" | 2025-26 RS, no limit | entity_summary | entity_summary | Lineup hero card | summary | Named unit on-court stats |
| lineup_leaderboard | Leaderboard | "LeBron + Kyrie best games" | 2025-26 RS, limit 10 | leaderboard | leaderboard_table | Ranked table | leaderboard | Named unit performance ranking by net_rating |

**Legend:**
- **Data Scope/Default:** Season range if specified; RS=Regular Season, default season if not specified
- **Pattern Config:** Type string used in routeToPattern switch case
- **Result Shape:** Classification from classifyResultShape()
- **Table Pattern:** Which React component renders it
- **Sections Used:** Result section keys expected from backend
- **Notes:** Quirks, conditions, edge behaviors

---

## 4. Data Scope and Default Rules

### 4.1 Season Defaults

```
Regular season (default): 2025-26
Playoff season: 2024-25 (latest completed)
Career/all-time (regular): 1996-97 to 2025-26
Career/all-time (playoff): 1996-97 to 2024-25

Fuzzy timeframe:
  "recent" → last_n=10 games (applied in _build_parse_state)
  "last 5" → last_n=5 games

Season type detection:
  "playoff", "playoffs", "postseason" → Playoffs
  (default) → Regular Season
```

**Code references:**
- `_seasons.py`: LATEST_REGULAR_SEASON, LATEST_PLAYOFF_SEASON constants
- `_parse_helpers.py`: `detect_season_type()`, `default_season_for_context(season_type)`
- `natural_query.py`: `_build_parse_state()` applies "recent" → last_n=10

### 4.2 Default Routing Policies

| Policy | Fires When | Routes To | Code |
|---|---|---|---|
| Player + timeframe → summary | Player + (season OR start_season OR last_n), no stat/opponent/threshold | `player_game_summary` | `player_timeframe_summary_default()` in `_default_rules.py` |
| Metric only → leaderboard | Stat detected, no player/team named | `season_leaders` (player) or `season_team_leaders` (team) | `metric_only_leaderboard_default()` |
| Player + threshold → finder | Player + (min_value OR max_value), no explicit intent | `player_game_finder` | `player_threshold_finder_default()` |
| Team + threshold → finder | Team + (min_value OR max_value), no explicit intent | `game_finder` | `team_threshold_finder_default()` |
| Streak + no season → 3-season window | Streak query, no explicit season/range | Applies 3-season range ending at current season | `streak_default_window()` |

### 4.3 Opponent Quality Filter Support (Phase G)

**Supported on these routes:**
- player_game_summary
- player_game_finder
- player_stretch_leaderboard
- game_summary
- game_finder
- team_record

**Examples:**
```
"Jokic against good teams" → opponent_quality: "good_teams"
"Giannis vs .500 teams" → opponent_quality: "over_500"
"Celtics vs top 10 defenses" → opponent_quality: "top_defenses"
```

**Unsupported routes:** If user specifies opponent_quality on an unsupported route, the query returns NoResult with a note explaining the filter isn't available.

Code: `_SUPPORTED_OPPONENT_QUALITY_ROUTES` in `_natural_query_execution.py`.

### 4.4 Phase G/H Feature Gates

Some filters are partial implementations (Phase G/H work-in-progress):

| Feature | Supported Routes | Status |
|---|---|---|
| **Clutch** (final 5 min, ≤5 pt diff) | player_game_summary, player_game_finder, team_record, season_leaders | Recognized by parser; partial data support |
| **Period** (Q4, 2H, OT) | player_game_finder, team_record | Recognized; Phase G transport |
| **Role** (starter vs bench) | player_game_summary, player_game_finder | Recognized; Phase G transport |
| **Schedule context** (back-to-back, rest advantage) | player_game_summary, team_record | Recognized; Phase H transport |
| **Opponent quality** (vs .500+ teams, vs contenders) | 6 routes (listed above) | Phase G support |

**Feature gate code:**
```python
_PHASE_G_CLUTCH_TRANSPORT_ROUTES = {...}
_PHASE_G_PERIOD_TRANSPORT_ROUTES = {...}
_PHASE_G_ROLE_TRANSPORT_ROUTES = {...}
_PHASE_H_SCHEDULE_CONTEXT_ROUTES = {...}
```

If a user asks for a feature not in the transport set, the query is routed but the filter is **silently dropped** (not applied), which is a UX bug. Future work: return NoResult with explicit "feature not supported on this route" note.

---

## 5. Table-Pattern Inventory

| Table Pattern / Component | Row Type | Routes | Default Visible Columns | Hidden/Details | Row Cap | Sort Behavior | Product Concerns |
|---|---|---|---|---|---|---|---|
| **EntitySummaryResult** (Hero Card) | Player/team card | player_game_summary, lineup_summary, playoff_history | Name, season stats (pts, reb, ast, etc.) | Career milestones, photo | 1 | N/A | None currently; stable |
| **GameLogResult** (Player/Team Game Log) | Game record | player_game_summary, player_game_finder, game_finder, game_summary, team_record | date, opponent, pts (or W/L), reb, ast, FG%, 3P%, ±/game_score | Full box score, play-by-play | No hard cap (25 for finders) | By date desc (recent first) or stat desc | Columns hardcoded; new stats need component edit. No season grouping. Detail drawer UX unclear. |
| **LeaderboardResult** (Ranked Leaderboard) | Ranked row | season_leaders, season_team_leaders, team_record_leaderboard, playoff_appearances, playoff_occurs_leaders, team_occurrence_leaders, lineup_leaderboard | Rank, name, stat (or count) | Per-game average, appearances, qualifiers | limit (usually 10) | By rank ascending (1=best) | No filtering UI. Metric fixed per route. Position filter only works on player_leaders. Metric label is route-specific. |
| **TopPerformancesResult** (Single-Game Leaderboard) | Single-game record | top_player_games, top_team_games | Rank, player/team, date, stat | Opponent, full box score | limit (usually 10) | By stat descending | Stat fixed (usually PPG). No multi-stat ranking. No position/team filter. |
| **RollingStretchResult** (Rolling-Window Leaderboard) | Window record | player_stretch_leaderboard | Rank, player, window dates, stat | Game-by-game in window | limit (usually 10) | By stat descending | Window size hardcoded by route. New metrics require route edit. |
| **SplitResult** (Split Comparison) | Split bucket row | player_split_summary, team_split_summary, player_on_off | Bucket label, games, pts, reb, ast, FG%, net_rating | Full box, efficiency metrics | Usually 2–3 rows | By bucket name | Bucket definitions hardcoded. No client customization. Edge chips show big deltas. |
| **StreakResult** (Streak Table) | Streak record | player_streak_finder, team_streak_finder | Streak start, length, stat range (or W/L), end | Game-by-game if streak short | limit (25) | By length descending | Streak definition fixed per query. No threshold customization. Detail drawer slow for long streaks. |
| **PlayoffHistoryResult** (Playoff Record) | Playoff record | playoff_history, playoff_matchup_history, playoff_round_record | Season, W-L record, opponent (or round) | Finals flag, champion status | No hard cap | By season descending | Limited to teams. No player-level playoff records. Decade boundaries static. |
| **RecordResult** (Team Record/By Decade) | Record row | team_record, record_by_decade, record_by_decade_leaderboard, matchup_by_decade | Season or decade, W, L, win_pct | Finals, champion, playoff seed | No cap (leaderboard: limit 10) | By decade desc or by metric | Decade boundaries hardcoded. New eras need code edit. Matchup mode needs pre-selected teams. |
| **ComparisonResult** (Metric Comparison) | Metric row | player_compare, team_compare, team_matchup_record | Metric name, value_a, value_b, delta | (none typically) | No cap | By metric name (alpha) or by delta | Large metric list not scannable. No category grouping. Head-to-head stacked separately. Metrics hardcoded per comparison type. |
| **FallbackTableResult** (Generic) | Generic row | (any unmatched route) | Auto-derived from row keys | (none) | No cap | (default table order) | Indicates route has no real pattern. Used for prototypes / unfinished work. No schema guarantee. Columns unpredictable. |

**Color coding interpretation:**
- **Stable patterns:** entity_summary, leaderboard (core routes locked well)
- **Weak patterns:** fallback_table (catch-all), split (hardcoded buckets), comparison (large metric list)
- **Needs audit:** game_log (columns hardcoded for new stats), top_performances (single-stat only), streak (detail drawer UX)

---

## 6. Result-Shape Inventory

**Error/No-Result Shapes:**
1. `no_result_guided` — Message + recovery chips (e.g., "Try: [suggested queries]")
2. `no_result_message` — Plain message (e.g., "No data for this query")

**Single-Entity Shapes:**
3. `entity_summary` — Hero card for player/team
4. `entity_summary_with_gamelog` — Hero + recent game log below

**Game Log Shapes:**
5. `game_log_player_table` — Player-first game table
6. `game_log_team_table` — Team-first game table
7. `game_log_team_detail` — Team log + expandable detail sections

**Leaderboard/Ranking Shapes:**
8. `leaderboard_table` — Ranked leaderboard (league-wide top 10)
9. `top_performances` — Single-game performance leaderboard
10. `rolling_stretch` — Rolling-window performance leaderboard

**Comparison Shapes:**
11. `split_table` — Split-bucket comparison (home/away, on/off, etc.)
12. `on_off_split` — Specialized on/off split
13. `comparison` — Two-entity metric comparison + panels

**Streak/Playoff Shapes:**
14. `streak_table` — Ranked streak table
15. `playoff_history` — Playoff season table
16. `playoff_round_record` — Playoff round leaderboard
17. `playoff_matchup_history` — Two-team playoff series

**Record Shapes:**
18. `team_record` — Team record hero + summary
19. `record_by_decade` — Team record breakdown by decade
20. `record_by_decade_leaderboard` — Ranked decade leaderboard
21. `matchup_by_decade` — Two-team decade-by-decade matchup

**Unclassified:**
22. `fallback_table` — Generic plain table (route not in routeToPattern switch)
23. `unclassified` — Route has no displayable rows

All 24 shapes are defined in `frontend/src/components/results/resultShapes.ts`.

---

## 7. Scalability Risks

### Critical Risks (Block New Features)

**Risk 1: Route-Specific Pattern Logic in Frontend Switch**

**File:** `frontend/src/components/results/config/routeToPattern.ts`

**Problem:** The `routeToPattern()` function is a 200+ line switch with one case per route. Adding route 31 requires editing this file + testing. Pattern configs are hardcoded, not data-driven.

**Evidence:**
```typescript
switch (data.route ?? data.result?.metadata?.route) {
  case "player_game_summary": return [...];
  case "player_game_finder": return [...];
  // ... 28 more cases ...
  default: return [{ type: "fallback_table" }];
}
```

**Impact:** Maintenance burden scales with route count. Impossible for non-engineers to add routes. Pattern refactors require coordinated frontend changes.

**Fix:** Move route→pattern mapping to JSON/TOML config or GraphQL schema. Declarative, testable, no code edits needed.

---

**Risk 2: Missing Fallback Routes**

**File:** `frontend/src/components/results/config/routeToPattern.ts` (default case)

**Problem:** Unknown routes fall through to `fallback_table`. No error signal. Hard to distinguish "incomplete feature" from "this is supposed to be generic."

**Example:**
- If backend adds `player_occurrence_count` route but forgets to update routeToPattern, users see a plain fallback table with no indication it's missing real UI.

**Impact:** Broken patterns ship silently. QA must manually test all routes to catch this.

**Fix:**
- Explicit route validation: throw error if route not in switch (fail fast)
- List all routes in a constant; audit completeness at test time
- Add test: every route in build_result_map must be in routeToPattern

---

**Risk 3: Section Name Coupling**

**File:** `frontend/src/components/results/patterns/GameLogResult.tsx` (and others)

**Problem:** Pattern components reference specific section keys (e.g., `sectionKey: "game_log"`). Backend must return sections with matching names, or rendering fails silently.

**Evidence:** If backend returns section named `games` instead of `game_log`, frontend looks for `game_log` in result.sections, finds nothing, renders empty table.

**Impact:** No error message; users see blank screen. Hard to debug because no type checking or validation.

**Fix:**
- Frontend: validate that expected sections exist before rendering. Throw error or show "missing data" placeholder.
- Tests: verify section names match between backend handler output and frontend pattern config.
- Schema: document all section names for each route (e.g., in a `docs/reference/pattern_contracts.md`).

---

**Risk 4: Table Columns Hardcoded Per Component**

**File:** All pattern components (`GameLogResult.tsx`, `LeaderboardResult.tsx`, etc.)

**Problem:** Visible column sets are hardcoded in component code. Adding a new stat (e.g., "game_score" in player game log) requires editing component source, recompiling, testing.

**Evidence:**
```typescript
const DEFAULT_COLUMNS = ['date', 'opponent', 'pts', 'reb', 'ast', 'fg%', '3p%'];
// If you want to add 'plus_minus', edit this array + test
```

**Impact:** New stats are slow to ship (require code review + build). Stat selection is not customizable per user.

**Fix:**
- Pass column config via result metadata: backend specifies which columns to show
- Frontend: infer columns from result row schema (discovery-based rendering)
- CLI: support --columns flag to customize output

---

**Risk 5: Data Scope Defaults Distributed Across 4 Files**

**Files:**
- `_default_rules.py` (named policies like player_timeframe_summary_default)
- `_parse_helpers.py` (detect_season_type, default_season_for_context)
- `_seasons.py` (resolve_career, resolve_since_year)
- `natural_query.py` (_build_parse_state for fuzzy "recent" → last_n=10)

**Problem:** No single source of truth for defaults. Changing the current season requires edits in multiple places. Future maintainers won't know all the places defaults are applied.

**Impact:** Inconsistent defaults if one file is updated but another is missed. Hard to test all default combinations.

**Fix:**
- Centralized DEFAULTS dict in one module
- Single point to update when current season changes
- Comprehensive default-scenario tests

---

### Medium Risks (Degrade Gracefully)

**Risk 6: Phase G/H Incomplete Features Silently Dropped**

**File:** `src/nbatools/commands/_natural_query_execution.py`

**Problem:** Some filters (clutch, period, role, schedule context) are partially implemented. If user asks for them on an unsupported route, the filter is silently ignored instead of returning a "not supported" message.

**Example:**
```python
_PHASE_G_CLUTCH_TRANSPORT_ROUTES = {
  "player_game_summary",
  "player_game_finder",
  "team_record",
  "season_leaders",
}

# If user asks "Curry clutch points on team_split_summary", 
# the route is not in the set, so the clutch filter is silently dropped.
# User sees all-game stats, not clutch stats. Silent failure.
```

**Impact:** Confusing UX. User thinks they got filtered data but didn't.

**Fix:** Return NoResult with explicit note: "Clutch filter not supported on split queries yet."

---

**Risk 7: Fallback-Driven Unsupported Queries**

**Problem:** Unsupported routes fall through to fallback_table with generic rows. Looks like it works, but data may be incomplete or wrong.

**Example:** If a route is marked "unsupported" but still has a build_result function that returns some rows, users get a fallback table that looks real but is incomplete.

**Impact:** User sees data, thinks it's correct, makes bad decisions.

**Fix:** Explicit "unsupported boundary" label in result notes. UI shows warning chip.

---

## 8. Product-Quality Gaps by Table Pattern

### Player Game Log

| Aspect | Status |
|---|---|
| **What works** | Core game records, date-sorted, summary strip showing season avg |
| **Weak/ugly/confusing** | No season-to-season grouping; 100+ game logs are one long list. Detail drawer (full box) is slow. Users don't know it exists (no visible UI hint). |
| **Data/columns missing** | Advanced metrics (on/off +/-) only available after full-row fetch. Play-by-play not accessible. |
| **Should decide before polish** | Should detail drawer exist? Should we group by season? Should we cap visible rows and paginate? |
| **Lock/revise decision** | **Lock now.** Core game log is stable. Defer advanced metrics + pagination to future phase. |

### Team Game Log

| Aspect | Status |
|---|---|
| **What works** | W/L record, opponent, score, date-sorted |
| **Weak/ugly/confusing** | Same as player: no grouping, detail drawer unknown, hard to scan 50+ games |
| **Data/columns missing** | Team advanced metrics (pace, ORtg, DRtg) not shown by default |
| **Should decide before polish** | Grouping by season? Show advanced ratings? Highlight close games vs blowouts? |
| **Lock/revise decision** | **Lock now.** Defer polish. |

### Leaderboard

| Aspect | Status |
|---|---|
| **What works** | Ranking, top 10 by default, metric clear |
| **Weak/ugly/confusing** | No UI filtering. User wants "top scorers among guards" but must re-ask query with "guards" keyword. Client-side filter would help. |
| **Data/columns missing** | Min games threshold not visible (e.g., "top scorers with 10+ games"). Rank tie-breakers not explained. |
| **Should decide before polish** | Should we add client-side position/team filter UI? Show eligibility (# games / min threshold)? |
| **Lock/revise decision** | **Lock core 10 routes first.** Audit which routes need filtering. Then decide on client-side UI. |

### Split Comparison

| Aspect | Status |
|---|---|
| **What works** | Two buckets, edge chips for deltas |
| **Weak/ugly/confusing** | Edge chips show "3 pt better on floor" but don't highlight which stats matter most. Tiny deltas hard to spot. Bucket labels sometimes cryptic (e.g., "presence_state" vs "on/off"). |
| **Data/columns missing** | Trend data (is the split widening or shrinking?) not shown |
| **Should decide before polish** | Which buckets are primary (home/away, on/off, location)? Should we sort edge chips by magnitude? |
| **Lock/revise decision** | **Revise.** Audit which splits are actually used. Document supported splits. Improve edge-chip UX. |

### Streak Table

| Aspect | Status |
|---|---|
| **What works** | Ranked streaks, length clear |
| **Weak/ugly/confusing** | Streak definition unclear to user (e.g., "20-point streak" = 20+ PPG each game, not total points?). Game-by-game detail drawer is slow. |
| **Data/columns missing** | Definition / starting criteria not spelled out in table caption. Opponent difficulty not visible. |
| **Should decide before polish** | Should UI explain what the streak criteria are? Link to game detail? |
| **Lock/revise decision** | **Lock definitions.** Add note to result explaining criteria. Defer detail drawer optimization. |

### Top Performances

| Aspect | Status |
|---|---|
| **What works** | Single-game leaderboard, simple |
| **Weak/ugly/confusing** | Stat is fixed (usually PPG). User wants "highest Game Score" or "most assists in a game" but must ask differently. |
| **Data/columns missing** | Opponent level (was it vs playoff team?) not shown. Home/away split not visible. |
| **Should decide before polish** | Support multi-stat ranking? Show opponent seed? |
| **Lock/revise decision** | **Lock PPG variant.** Defer multi-stat support. Document that stat is fixed per query. |

### Playoff History

| Aspect | Status |
|---|---|
| **What works** | Season-by-season playoff record, clear |
| **Weak/ugly/confusing** | Limited to teams only. Players can't ask "LeBron playoff history." Opponent name column sometimes unclear (seeding context missing). |
| **Data/columns missing** | Player-level playoff records. Finals/champion flag visible but not highlighted. |
| **Should decide before polish** | Extend to players? Better opponent context? |
| **Lock/revise decision** | **Lock teams for now.** Document that players not supported. Defer player expansion. |

### Team Record / Record by Decade

| Aspect | Status |
|---|---|
| **What works** | W/L records, decade breakdown |
| **Weak/ugly/confusing** | Decade boundaries (1980s = 1980-1989?) not explained. Playoff-only records not accessible. |
| **Data/columns missing** | Playoff record by era. Championship count by era. |
| **Should decide before polish** | Standard era definitions? Should we show playoff + RS records separately? |
| **Lock/revise decision** | **Document era rules now.** Audit playoff completeness. Decide playoff + RS split before UI polish. |

### Comparison (Player/Team)

| Aspect | Status |
|---|---|
| **What works** | Metric side-by-side, delta visible |
| **Weak/ugly/confusing** | Metric list is 30+ rows; hard to find what matters. No grouping by category (offense/defense/efficiency). Head-to-head table stacked below (not integrated). |
| **Data/columns missing** | Metric grouping. Percentile ranking (e.g., "top 5% in PPG"). |
| **Should decide before polish** | Sort order (alphabetical, by delta, by category)? Show percentile? |
| **Lock/revise decision** | **Audit metric count.** Consider grouping by category. Decide sort order before UI polish. |

---

## 9. Recommended Next Implementation Phase

### Phase: "Lock Core Patterns" (14 hours)

**Goal:** Establish stable contracts for the top 8–10 routes, ensuring frontend/backend patterns won't break unexpectedly when Phase H features land.

**Why now:**
- System works but has no stability guarantees
- New filters (opponent_quality, clutch, period) are partial implementations; adding them risks breaking patterns
- No pattern contract tests exist; mismatches between backend section names and frontend configs are not caught
- Future UI polish or new routes will be risky without locked patterns

**Sequence:**

#### 1. Audit Route-Pattern Completeness (2 hours)

**Action:**
- List all 30 routes from `_get_build_result_map()`
- Check which routes are in `routeToPattern()` switch
- Find any routes not in switch (falling through to fallback_table)
- For each fallback-table route, decide: is it intentional (prototype) or missing?

**Output:** Audit report with missing/fallback routes clearly identified.

**Success:** No routes silently falling through that shouldn't be.

---

#### 2. Create Pattern Contract Tests (4 hours)

**Action:**
- Create `frontend/src/test/patternContracts.test.ts`
- For each of top 8 routes, write a test:
  - Generate/fetch a real result JSON from backend
  - Call `routeToPattern(result)` to get pattern stack
  - Verify pattern config is correct
  - Call pattern renderer component with result
  - Verify it renders without errors
  - Verify expected section keys are present in result.sections
  - Verify expected columns are rendered

**Routes to test (top 8):**
1. player_game_summary
2. player_game_finder
3. game_summary
4. season_leaders
5. player_compare
6. team_record
7. player_streak_finder
8. playoff_history

**Output:** Test suite with 8–10 contract tests.

**Success:** All contracts pass; test catches section name or column mismatches.

---

#### 3. Document Locked Pattern Contracts (3 hours)

**Action:**
- Create `docs/reference/pattern_contracts.md`
- For each top 8 route, write one-page contract:
  - Route name
  - Backend command module
  - Result shape key
  - PatternConfig type + options
  - Expected result.sections (name + example rows)
  - Expected table columns (visible + hidden)
  - Row cap / sort order / footer behavior
  - Example query + example result snippet

**Output:** Pattern contract doc (8 pages, one per route).

**Success:** Developers can reference the doc when adding new features.

---

#### 4. Align Backend Section Names (2 hours)

**Action:**
- For each top 8 command modules, verify section names match pattern config
- Example: `player_game_summary.py` should return result with `sections["summary"]` and `sections["game_log"]` (not `sections["games"]`)
- Add docstring to each command:
  ```python
  """
  Returns SummaryResult with sections:
    - summary: one row (season averages)
    - game_log: N rows (game records), sorted by date desc
  """
  ```

**Output:** Verified command modules + documentation.

**Success:** No section name mismatches.

---

#### 5. Create End-to-End Rendering Tests (3 hours)

**Action:**
- Create `frontend/src/test/endToEndPatterns.test.tsx`
- For each top 8 routes, write an E2E test:
  - Query backend for result (or use mock)
  - Pass result to ResultRenderer component
  - Verify expected table/card is rendered
  - Verify table has expected columns + rows
  - Verify summary strip (if present) shows correct stats
  - Take snapshot of rendered HTML

**Output:** E2E test suite with 8 tests + snapshots.

**Success:** E2E tests pass; snapshots catch rendering regressions.

---

### Total Effort: ~14 hours

| Task | Hours | Owner |
|---|---|---|
| 1. Audit | 2 | Frontend dev |
| 2. Pattern contracts test | 4 | Frontend dev |
| 3. Doc contracts | 3 | Tech writer + dev |
| 4. Align sections | 2 | Backend dev |
| 5. E2E tests | 3 | Frontend dev |

### After Lock: Unblock Phase H

Once patterns are locked:
1. Audit which Phase G/H features have incomplete execution
2. Implement missing data filters + aggregations in command modules
3. Expand pattern renderers to support new filtered results (e.g., "clutch" subset of games)
4. Add tests for new filters + patterns

---

## 10. Validation and Confidence

### What Was Verified

✅ **Backend route mapping:**
- Traced 28+ route assignments in `natural_query.py` _finalize_route() function
- Matched all routes to build_result map in `_natural_query_execution.py`
- Cross-referenced with tests (examples.md shows queries for all intent families)

✅ **Frontend pattern mapping:**
- Verified all routes in routeToPattern() switch
- Traced result shape classification in resultShapes.ts
- Inspected all 11 pattern component files

✅ **Data scope rules:**
- Located season constants in _seasons.py
- Traced default season logic in _parse_helpers.py
- Found phase feature gates in _natural_query_execution.py

✅ **Documentation:**
- Consulted examples.md for real-world query phrasings
- Reviewed determination_layer_audit.md for scope defaults

### Limitations

❌ **No execution depth:** Did not inspect each command module's query logic (e.g., how player_game_summary.py loads games). Assumed implementations work as documented.

❌ **No data verification:** Did not fetch live data to verify correctness. Assume CSV data is clean and loaded properly.

❌ **Parser behavior not tested:** Parser inferred from code and examples; did not run full test suite.

❌ **Phase G/H features not audited:** Feature gates identified but execution not inspected. Assumed partial implementations work as intended.

❌ **Frontend render depth:** Did not inspect CSS/styling or performance. Focus was on data schema and component wiring.

### What Would Increase Confidence

1. **Run parser examples sweep:** If artifacts exist in outputs/, compare expected routes to actual
2. **Live query smoke tests:** Execute 3–5 queries per route, screenshot results, verify pattern classification
3. **Review test coverage:** Inspect test files for each route (unit + integration tests should exist)
4. **Inspect command implementations:** Read each command module to verify data loading + filtering
5. **Phase G/H audit:** Trace clutch, period, role, schedule filters through entire pipeline

---

**End of Return Package**

---

## Attachments / Related Files

- **Main product map:** `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md`
- **Parser examples:** `docs/architecture/parser/examples.md`
- **Determination audit (reference):** `docs/determination_layer_audit.md`
- **Frontend route mapping:** `frontend/src/components/results/config/routeToPattern.ts`
- **Result shape definitions:** `frontend/src/components/results/resultShapes.ts`
- **Pattern components:** `frontend/src/components/results/patterns/`

---

**Return Package Summary**

- **Status:** ✅ Discovery complete
- **Routes mapped:** 30 confirmed
- **Result shapes:** 24 named
- **Table patterns:** 11 components + 1 fallback
- **Biggest risk:** Route-specific pattern hardcoding in frontend
- **Next phase:** Lock core 8–10 patterns (14 hours)
- **Confidence:** High for route/pattern mapping; medium for Phase G/H execution details
