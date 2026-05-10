# Raw Query Product Map

> **Purpose:** Practical documentation of the current query-to-answer system: how natural language questions are routed, what structured results they produce, and how results are displayed in tables and cards. This is a discovery-only map—no design changes, no new feature recommendations.

> **Audience:** Development team, future UI designers, and product thinkers. For: understanding what currently works, identifying gaps, planning incremental improvements.

---

## 1. Execution Pipeline: Query → Route → Result → Display

All user questions follow this path:

1. **Natural Language → Parse State** (parser, `natural_query.py`)
   - Intent detection, entity resolution, filter extraction
   - Output: structured dict with parsed slots

2. **Parse State → Route Selection** (`_finalize_route` in `natural_query.py`)
   - Decision logic maps parsed slots to a specific backend route
   - Default rules apply for underspecified queries
   - Output: route name + route_kwargs dict

3. **Route → Command Execution** (command modules in `src/nbatools/commands/`)
   - Route handler loads data, applies filters, computes aggregates
   - Output: structured result object (SummaryResult, FinderResult, LeaderboardResult, etc.)

4. **Result → Display Pattern** (`routeToPattern.ts` in frontend)
   - Frontend receives result JSON, classifies it by route
   - Maps route to pattern config stack (e.g., entity_summary + game_log)
   - Output: ordered array of PatternConfig objects

5. **Pattern → Table + Cards** (pattern components in `frontend/src/components/results/patterns/`)
   - Pattern renderers build React UI: heroes, tables, drawers, chips
   - Output: user sees formatted tables, summaries, and context

---

## 2. Backend Routes (Current Inventory)

### 2.1 Complete Route List

| Route | Primary Intent | Example Query | Query Class | Status |
|---|---|---|---|---|
| `player_game_summary` | Player season/range summary with game log | "Luka last 10 games" | summary | shipped |
| `player_game_finder` | Player game list with threshold | "Curry 5+ threes" | finder | shipped |
| `player_on_off` | Player on/off presence split | "Jokic impact when on/off floor" | split | shipped |
| `player_split_summary` | Player split breakdown (by position, location, etc.) | "LeBron splits by location" | split | shipped |
| `player_streak_finder` | Player consecutive-game stat streaks | "Giannis longest scoring streak" | streak | shipped |
| `player_compare` | Two-player stat comparison | "Giannis vs Embiid" | comparison | shipped |
| `player_stretch_leaderboard` | Named player or league rolling window performance | "LeBron best 10-game stretch" | leaderboard | shipped |
| `player_occurrence_leaders` | Count of players meeting condition | "How many 40-point games" | leaderboard | shipped |
| `game_finder` | Team game list with threshold | "Lakers 100+ points" | finder | shipped |
| `game_summary` | Team season/range summary with game log | "Celtics last 5 games" | summary | shipped |
| `team_record` | Team W/L record with optional breakdown | "Sixers record vs .500 teams" | record | shipped |
| `team_split_summary` | Team split breakdown | "Suns splits by location" | split | shipped |
| `team_streak_finder` | Team consecutive-game streaks | "Warriors longest win streak" | streak | shipped |
| `team_compare` | Two-team stat comparison | "Heat vs Nets" | comparison | shipped |
| `team_matchup_record` | Two-team head-to-head record | "Dubs vs Lakers head-to-head" | record | shipped |
| `season_leaders` | League-wide player leaderboard | "Top scorers this season" | leaderboard | shipped |
| `season_team_leaders` | League-wide team leaderboard | "Best defensive rating" | leaderboard | shipped |
| `top_player_games` | Top single-game performances league-wide | "Highest scoring games this season" | leaderboard | shipped |
| `top_team_games` | Top team single-game performances | "Biggest team scoring nights" | leaderboard | shipped |
| `team_record_leaderboard` | Team record by season ranked | (implicit, playoff-triggered) | leaderboard | shipped |
| `playoff_history` | Team playoff appearance history | "Spurs playoff history" | record | shipped |
| `playoff_appearances` | Ranked team playoff appearance leaderboard | "Most playoff appearances all-time" | leaderboard | shipped |
| `playoff_matchup_history` | Two-team playoff matchup history | "Celtics vs Lakers playoffs" | record | shipped |
| `playoff_round_record` | Team round-by-round playoff leaderboard | (implicit) | leaderboard | shipped |
| `record_by_decade` | Team record breakdown by decade | "Spurs record by decade" | record | shipped |
| `record_by_decade_leaderboard` | Ranked team decade performance | "Best 1980s records" | leaderboard | shipped |
| `matchup_by_decade` | Two-team matchup by decade | "Celtics vs Lakers by decade" | record | shipped |
| `lineup_summary` | Named lineup stat card | "Big 3 on-court stats" | summary | shipped |
| `lineup_leaderboard` | Named lineup performance ranking | "Luka + Kyrie best games" | leaderboard | shipped |

**Status key:**
- **shipped:** Route is production-ready, fully testable, expected to work
- **fallback-supported:** Route exists but returns generic fallback tables when real pattern not available
- **unsupported-boundary:** Route is recognized but data/logic not implemented; user gets no-result with note

All routes above are **shipped** (mapped in `_get_build_result_map()` in `_natural_query_execution.py`).

### 2.2 Route → Intent Mapping

The parser maps parsed slots to one of these **higher-level intents** before selecting a route:

| Intent | Routes | Triggered By |
|---|---|---|
| Summary | `player_game_summary`, `game_summary` | Player/team + timeframe, no stat filter |
| Finder | `player_game_finder`, `game_finder` | Player/team + threshold (min/max value) |
| Leaderboard | `season_leaders`, `season_team_leaders`, `top_player_games`, `top_team_games`, `player_occurrence_leaders`, `playoff_appearances`, etc. | Leaderboard intent keyword OR metric-only + no entity |
| Streak | `player_streak_finder`, `team_streak_finder` | Streak keyword (e.g., "consecutive", "streak") |
| Split | `player_split_summary`, `team_split_summary`, `player_on_off` | Split keyword (e.g., "by location", "on/off") |
| Comparison | `player_compare`, `team_compare` | Two entities named |
| Record | `team_matchup_record`, `team_record` | Record intent keyword (e.g., "record", "head-to-head") |
| Playoff | `playoff_history`, `playoff_matchup_history`, `playoff_round_record`, `record_by_decade`, etc. | Playoff keyword + record/leaderboard intent |
| Lineup | `lineup_summary`, `lineup_leaderboard` | Named lineup + explicit unit context |

---

## 3. Data Scope and Default Rules

### 3.1 Season Defaults

**Regular season:**
- Default: **2025-26** (latest playable regular season)
- Explicit season: honored as-is (e.g., "2024-25")
- Season range: both start and end must be specified
- Last N games: windowed queries over current/prior seasons

**Playoff season:**
- Default: **2024-25** (latest completed playoff season; note 2025-26 playoffs not yet loaded)
- Activated by keywords: "playoff", "playoffs", "postseason"
- Career/all-time playoff: **1996-97 to 2024-25**

**Career/all-time:**
- Keyword: "career", "all-time", "all time"
- Regular season: **1996-97 to 2025-26**
- Playoffs: **1996-97 to 2024-25**
- Code path: `resolve_career(season_type)` in `_seasons.py`

**Fuzzy timeframe → last-N conversion:**
- "recent" → `last_n=10` (default in `_build_parse_state`)
- "last 5 games" → `last_n=5`
- "last 2 weeks" → parsed to approximate game count (via `extract_last_n` helpers)

### 3.2 Default Rules by Route

Underspecified queries use **named default policies** (in `_default_rules.py`):

| Policy | Condition | Action | Code |
|---|---|---|---|
| Player + timeframe → summary | Player named + season/last-N, no stat/opponent/threshold | Route to `player_game_summary` | `player_timeframe_summary_default()` |
| Metric only → leaderboard | Stat detected, no player/team entity | Route to `season_leaders` (player) or `season_team_leaders` (team) | `metric_only_leaderboard_default()` |
| Player + threshold → finder | Player + min/max value, no explicit intent | Route to `player_game_finder` | `player_threshold_finder_default()` |
| Team + threshold → finder | Team + min/max value, no explicit intent | Route to `game_finder` | `team_threshold_finder_default()` |
| Streak + no season → 3-season window | Streak query, no explicit season | Apply 3-season range ending at default season | `streak_default_window()` |

### 3.3 Season Type Detection

| Input Pattern | Detected Type |
|---|---|
| "playoff", "playoffs", "postseason" | **Playoffs** |
| All other queries (default) | **Regular Season** |

See `detect_season_type()` in `_parse_helpers.py`.

### 3.4 Opponent Quality Filters (Phase G / Partial Support)

Queries like "against good teams" or "vs .500 teams" can add opponent-quality context when supported:

| Phrase | Detected Value |
|---|---|
| "against/vs good teams" | `opponent_quality: "good_teams"` |
| "against/vs contenders" | `opponent_quality: "contenders"` |
| "against/vs top-10 defenses" | `opponent_quality: "top_defenses"` |
| "against/vs teams over .500" | `opponent_quality: "over_500"` |

**Supported routes for opponent_quality:**
- `player_game_summary`, `player_game_finder`, `player_stretch_leaderboard`
- `game_summary`, `game_finder`, `team_record`

Other routes ignore `opponent_quality` (transport is blocked, no-result returned if user specifies it on unsupported route).

Code: `_SUPPORTED_OPPONENT_QUALITY_ROUTES` in `_natural_query_execution.py`.

---

## 4. Route → Result Shape → Table Pattern Mapping

### 4.1 Result Shapes (Frontend Classification)

The frontend's `classifyResultShape()` function in `resultShapes.ts` categorizes results by shape:

| Result Shape Key | Name | Description | Pattern Stack |
|---|---|---|---|
| `entity_summary` | Entity Summary | Player/team hero card | Single entity_summary pattern |
| `entity_summary_with_gamelog` | Entity Summary + Game Log | Player hero + recent games | entity_summary + game_log |
| `game_log_player_table` | Player Game Log | Summary strip + game table | game_log (mode: player) |
| `game_log_team_table` | Team Game Log | Summary strip + game table | game_log (mode: team) |
| `game_log_team_detail` | Game Summary Log | Team game table + detail drawers | game_log + detail sections |
| `split_table` | Split Comparison | Hero + split bucket table | split pattern |
| `on_off_split` | On/Off Split | Two-bucket on/off comparison | split (on/off mode) |
| `streak_table` | Streak Table | Hero + ranked streak list | streak pattern |
| `playoff_history` | Playoff History | Team + season table | playoff_history pattern |
| `playoff_round_record` | Playoff Round Records | Round leaderboard | playoff_history (round_record mode) |
| `playoff_matchup_history` | Playoff Matchup History | Two-team + series table | playoff_history (matchup mode) |
| `comparison` | Comparison Panels | Hero + subject panels + metric table | comparison pattern |
| `team_record` | Team Record | Hero + record table | record pattern (team_record mode) |
| `record_by_decade` | Record By Decade | Hero + decade table | record pattern (record_by_decade mode) |
| `record_by_decade_leaderboard` | Record By Decade Leaderboard | Ranked decade leaderboard | record pattern (record_by_decade_leaderboard mode) |
| `matchup_by_decade` | Matchup By Decade | Two-team + decade table | record pattern (matchup_by_decade mode) |
| `leaderboard_table` | Leaderboard Table | Hero sentence + ranked table | leaderboard pattern |
| `top_performances` | Top Performances | League-wide single-game table | top_performances pattern |
| `rolling_stretch` | Rolling Stretch | Rolling-window leaderboard | rolling_stretch pattern |
| `fallback_table` | Fallback Tables | One plain data card per section | fallback_table pattern |
| `no_result_guided` | Guided No Result | Message + recovery chips | no-result message |
| `no_result_message` | Message No Result | Message only | no-result message |

### 4.2 Route → PatternConfig Mapping (from `routeToPattern.ts`)

| Route | Pattern Stack | Primary Section | Summary Section | Detail Sections | Display Mode |
|---|---|---|---|---|---|
| `player_game_summary` | entity_summary + game_log* | summary, game_log | summary | — | player |
| `player_game_finder` | game_log | finder | — | — | player |
| `game_finder` | game_log | finder | — | — | team |
| `game_summary` | game_log | game_log | summary | top_performers | team |
| `top_player_games` | top_performances | leaderboard | — | — | player |
| `top_team_games` | top_performances | leaderboard | — | — | team |
| `player_split_summary` | split | — | — | — | player |
| `team_split_summary` | split | — | — | — | team |
| `player_on_off` | split | summary | summary | — | player (on/off) |
| `player_streak_finder` | streak | streak | — | — | — |
| `team_streak_finder` | streak | streak | — | — | — |
| `playoff_history` | playoff_history | — | — | — | history |
| `playoff_round_record` | playoff_history | — | — | — | round_record |
| `playoff_matchup_history` | playoff_history | — | — | — | matchup |
| `player_compare` | comparison | — | — | — | player |
| `team_compare` | comparison | — | — | — | team |
| `team_matchup_record` | comparison | — | — | — | team (h2h) |
| `team_record` | record + game_log* | — | — | — | team_record |
| `record_by_decade` | record | — | — | — | record_by_decade |
| `record_by_decade_leaderboard` | leaderboard | leaderboard | — | — | — |
| `matchup_by_decade` | record | — | — | — | matchup_by_decade |
| `season_leaders` | leaderboard | leaderboard | — | — | — |
| `season_team_leaders` | leaderboard | leaderboard | — | — | — |
| `team_record_leaderboard` | leaderboard | leaderboard | — | — | — |
| `player_occurrence_leaders` | leaderboard | leaderboard | — | — | — |
| `team_occurrence_leaders` | leaderboard | leaderboard | — | — | — |
| `player_stretch_leaderboard` | rolling_stretch | leaderboard | — | — | — |
| `playoff_appearances` | leaderboard | leaderboard | — | — | — |
| `lineup_summary` | entity_summary | summary | — | — | — |
| `lineup_leaderboard` | leaderboard | leaderboard | — | — | — |

*\* Conditional: `game_summary` + `game_log` only shown if rows present; `team_record` stacks game_log only if game_log rows exist in result.*

---

## 5. Table Pattern Inventory

### 5.1 Pattern Component Mapping

The frontend defines pattern renderers in `frontend/src/components/results/patterns/`:

| Component File | Pattern Type | Pattern Name | Routes | Row Type | Primary Section |
|---|---|---|---|---|---|
| `EntitySummaryResult.tsx` | `entity_summary` | Entity Summary Card | player_game_summary, lineup_summary, playoff_history | hero card | summary |
| `GameLogResult.tsx` | `game_log` | Game Log Table | player_game_summary, player_game_finder, game_finder, game_summary, team_record | game record | game_log (or finder) |
| `LeaderboardResult.tsx` | `leaderboard` | Ranked Leaderboard | season_leaders, season_team_leaders, team_record_leaderboard, player_occurrence_leaders, team_occurrence_leaders, playoff_appearances, lineup_leaderboard | ranked row | leaderboard |
| `TopPerformancesResult.tsx` | `top_performances` | Single-Game Leaderboard | top_player_games, top_team_games | single-game record | leaderboard |
| `RollingStretchResult.tsx` | `rolling_stretch` | Rolling-Window Leaderboard | player_stretch_leaderboard | window record | leaderboard |
| `SplitResult.tsx` | `split` | Split Breakdown Table | player_split_summary, team_split_summary, player_on_off | split bucket row | (varies) |
| `StreakResult.tsx` | `streak` | Streak Table | player_streak_finder, team_streak_finder | streak record | streak |
| `PlayoffHistoryResult.tsx` | `playoff_history` | Playoff History / Record | playoff_history, playoff_matchup_history, playoff_round_record | playoff record | (varies by mode) |
| `RecordResult.tsx` | `record` | Team Record / Matchup Record | team_record, team_matchup_record, record_by_decade, matchup_by_decade | record row | (varies by mode) |
| `ComparisonResult.tsx` | `comparison` | Comparison Panels | player_compare, team_compare, team_matchup_record | metric row | (varies) |
| `FallbackTableResult.tsx` | `fallback_table` | Generic Fallback | any unmatched route | generic row | (any) |

### 5.2 Table Pattern Details

#### A. Game Log Table (`GameLogResult.tsx`)

**Purpose:** Display game-by-game record for a player or team.

**Row type:** Game record (player stats or team box score)

**Variants:**
- **Player mode**: Player-first game log (columns: date, opponent, stat1, stat2, ..., game_score)
- **Team mode**: Team game log (columns: date, opponent, pts_for, pts_against, result, ...)

**Default visible columns (player mode):**
- date, opponent, pts, reb, ast, fg%, 3p%, game_score

**Default visible columns (team mode):**
- date, opponent, W/L, pts_for, pts_against, diff, net_rating

**Hidden/detail columns:**
- Full box score (FG, 3P, FT, TOV, PF, etc.) accessible via drawer
- Plus-minus, pace, advanced metrics

**Summary strip behavior:**
- Shows season-to-date or filtered averages above table (if `showSummaryStrip: true`)
- Summary strips display: avg pts, avg reb, avg ast, FG%, season record

**Row cap:**
- Default: no hard cap; shows all rows
- Finder queries: limit to 25 games (configurable via route_kwargs["limit"])

**Highlighted metric:**
- Game-by-game sorting: typically by date (most recent first)
- Finder queries: sorted by specified stat (descending unless ascending flag set)

**Product concerns:**
- Columns hardcoded for common stats; new stats require component updates
- No row grouping by season or playoff/regular split
- Detail drawer is opt-in; users must know to click row for full box score

#### B. Leaderboard Table (`LeaderboardResult.tsx`)

**Purpose:** Ranked list of leaders in a stat or occurrence count.

**Row type:** Ranked leaderboard row (player/team name + metric + rank)

**Variants:**
- **League-wide**: All players/teams ranked
- **Single-entity**: Top games/stretches by a single player
- **By position**: Guards, forwards, centers filtered
- **By stat**: Points, rebounds, assists, etc.
- **By occurrence**: Count of games meeting threshold (e.g., "40-point games")

**Default visible columns:**
- Rank, name, metric (stat or count)

**Hidden/detail columns:**
- Games played (min_games), per-game average, season

**Row cap:**
- Default: limit to 10 (configurable via route_kwargs["limit"])
- Finder-style queries: no cap, show all matches

**Footer/summary behavior:**
- League average typically shown at bottom
- No aggregation rows (no sum/total)

**Highlighted metric:**
- Primary metric column typically color-coded or bold
- Rank column left-aligned

**Product concerns:**
- No filtering UI within the table; pre-filtered by route
- Metric label is static (e.g., "PPG"); new metrics require route-specific config
- Position filtering must happen at parse time, not client-side

#### C. Split Table (`SplitResult.tsx`)

**Purpose:** Compare performance across two buckets (e.g., home/away, on/off floor).

**Row type:** Split bucket row (bucket name + aggregated stats)

**Variants:**
- **Location split**: Home vs Away
- **Outcome split**: Wins vs Losses
- **On/Off split**: Player on floor vs off floor
- **Position split**: Player's record at different positions
- **Role split**: Starter vs bench

**Default visible columns:**
- Bucket name, games, pts, reb, ast, FG%, net_rating

**Hidden/detail columns:**
- Full box score metrics, TOV, PF, usage rate, true_shooting%

**Summary/primary detail:**
- Usually 2–3 bucket rows with edge-case chips showing deltas ("3 pt. better on floor")
- Comparison chips highlight largest differences

**Row cap:**
- Typically 2–3 rows (one per bucket)
- No pagination

**Footer behavior:**
- None; comparison happens inline via chips

**Product concerns:**
- Metric selection is route-specific; no client-side customization
- Edge chips are hardcoded for key stats; new metrics may not render
- Bucket labels are not client-editable

#### D. Streak Table (`StreakResult.tsx`)

**Purpose:** Ranked list of consecutive-game stat or W/L streaks.

**Row type:** Streak record (streak start date, length, stat range or W/L, opponent)

**Variants:**
- **Stat streak**: Consecutive games meeting a threshold (e.g., "20+ points")
- **Win/loss streak**: Consecutive wins or losses
- **Game count streak**: Named player's best 10-game scoring stretch

**Default visible columns:**
- Streak start date, length (# games), stat range (min-max or W/L), end date

**Hidden/detail columns:**
- Game-by-game breakdown (if streak is short enough)
- Opponent sequence

**Highlighted metric:**
- "Length" column is usually the primary rank metric
- One specific streak may be highlighted if it's a tie or record

**Row cap:**
- Default: limit to 25 streaks

**Product concerns:**
- Game-by-game detail drawer is computationally expensive for long streaks
- Streak definition is fixed per query (can't change threshold client-side)

#### E. Leaderboard / Single-Game Table (`TopPerformancesResult.tsx`)

**Purpose:** Rank single-game performances league-wide.

**Row type:** Single-game performance (player/team + date + stats)

**Variants:**
- **Scoring**: Top 10 highest-scoring games
- **Custom stat**: Top 10 games by custom metric (rebounds, Game Score, etc.)

**Default visible columns:**
- Rank, player/team, date, opponent, pts (or other stat), other stats

**Hidden/detail columns:**
- Full box score, plus-minus

**Row cap:**
- Default: limit to 10

**Product concerns:**
- Limited stat flexibility; scoring is the primary default
- No client-side filtering by position or team

#### F. Playoff History Table (`PlayoffHistoryResult.tsx`)

**Purpose:** Team playoff record broken down by season or matchup.

**Row type:** Playoff season record (season + record + opponent)

**Variants:**
- **History mode**: Season-by-season record
- **Round record mode**: Round-by-round leaderboard
- **Matchup mode**: Two teams' playoff series history

**Default visible columns:**
- Season, W-L record, round reached (or opponent)

**Hidden/detail columns:**
- Finals appearance flag, champion status

**Row cap:**
- No hard cap; shows all seasons

**Product concerns:**
- Limited to team-level records; player-level playoff records not supported
- Matchup mode only works for two pre-selected teams (no search)

#### G. Record Table (`RecordResult.tsx`)

**Purpose:** Team record with optional breakdown (by decade, by matchup).

**Row type:** Record row (season or decade + W/L + pct)

**Variants:**
- **Team record**: Single team's season record
- **Record by decade**: Ranked decades by winning %
- **Matchup by decade**: Two teams' decade-by-decade series

**Default visible columns:**
- Season or decade, wins, losses, win_pct

**Hidden/detail columns:**
- Finals status, tournament results

**Row cap:**
- No hard cap for decade/season breakdown
- Leaderboard mode: limit to 10

**Product concerns:**
- Decade definition is hardcoded (1980s, 1990s, 2000s, etc.); no customization
- Matchup mode requires pre-selected teams (no dynamic team picker)

#### H. Comparison Table (`ComparisonResult.tsx`)

**Purpose:** Side-by-side or head-to-head stat comparison of two entities.

**Row type:** Metric row (stat name + player_a value + player_b value + delta)

**Variants:**
- **Player comparison**: Two-player stat comparison
- **Team comparison**: Two-team stat comparison
- **Head-to-head**: Two teams' game-by-game matchup record

**Default visible columns:**
- Metric name, value_a, value_b, delta (color-coded)

**Highlighted metric:**
- Largest deltas highlighted in color

**Row cap:**
- No hard cap; shows all parsed metrics

**Product concerns:**
- Metrics are hardcoded per comparison type (no custom metric selection)
- Head-to-head matchup table is separate from metric table (two tables stacked)

#### I. Fallback Table (`FallbackTableResult.tsx`)

**Purpose:** Generic plain-text table for unclassified or error results.

**Row type:** Generic data row (varies by section)

**Behavior:**
- One table per populated result section
- Columns auto-derived from row keys
- No special formatting, no detail drawers

**Row cap:**
- No limit; shows all rows

**Product concerns:**
- Indicates a route/result has no real pattern definition
- Used when route matches no case in `routeToPattern`
- No guaranteed schema; columns may vary unpredictably

---

## 6. Result Shape Inventory

### 6.1 Categorized Result Shapes

**No-Result (Error/Empty) Shapes:**
- `no_result_guided`: Message + recovery suggestion chips (e.g., "Try this instead: ...")
- `no_result_message`: Plain message (e.g., "No data found for this query")

**Single-Entity Shapes:**
- `entity_summary`: Player/team hero card (e.g., "Luka Dončić — 33.2 PPG this season")
- `entity_summary_with_gamelog`: Entity hero + recent game log (e.g., player card + last 10 games)

**Game Log Shapes:**
- `game_log_player_table`: Player-first game table with summary strip
- `game_log_team_table`: Team-first game table with summary strip
- `game_log_team_detail`: Team game table with expandable game detail sections (e.g., top performers, box score)

**Ranking/Leaderboard Shapes:**
- `leaderboard_table`: League-wide ranked leaderboard (e.g., top scorers)
- `top_performances`: Single-game performance leaderboard (e.g., highest-scoring games)
- `rolling_stretch`: Rolling-window leaderboard (e.g., best 10-game stretches)

**Comparison Shapes:**
- `split_table`: Split-bucket comparison with edge chips (e.g., home/away, on/off, by position)
- `on_off_split`: Two-bucket on/off split with comparison chips
- `comparison`: Two-entity comparison panels + metric table (e.g., Giannis vs Embiid)

**Streak Shapes:**
- `streak_table`: Ranked streak leaderboard with highlighted best streak

**Playoff Shapes:**
- `playoff_history`: Team playoff history table (season-by-season)
- `playoff_round_record`: Playoff round leaderboard (by round)
- `playoff_matchup_history`: Two-team playoff series history

**Record Shapes:**
- `team_record`: Team record hero + single season/summary record row
- `record_by_decade`: Team record breakdown by decade
- `record_by_decade_leaderboard`: Ranked decade leaderboard
- `matchup_by_decade`: Two-team decade-by-decade matchup

**Unclassified:**
- `fallback_table`: Generic plain table (indicates pattern not recognized)
- `unclassified`: Route has no result rows; not mapped to any shape

---

## 7. Data Scope and Query Behavior Rules

### 7.1 Season Scope Resolution

**Single-season query:**
```
"Jokic 2024-25" → season=2024-25, start_season=None, end_season=None
```

**Season range query:**
```
"LeBron 2020-25" → season=None, start_season=2020-21, end_season=2024-25
```

**Last-N-games query:**
```
"Curry last 10" → last_n=10, season=default (2025-26)
```

**Career/all-time query:**
```
"Jokic career" → season=None, start_season=1996-97, end_season=2025-26
"LeBron playoff career" → season=None, start_season=1996-97, end_season=2024-25
```

**Fuzzy recent query:**
```
"Giannis recent" → last_n=10 (default in _build_parse_state), season=2025-26
"Celtics recent form" → last_n=10, season=2025-26
```

**Code references:**
- `extract_season()` in `_parse_helpers.py`
- `extract_season_range()` in `_parse_helpers.py`
- `extract_last_n()` in `_parse_helpers.py`
- `resolve_seasons()` in `_seasons.py`
- `default_end_season()` in `_seasons.py`

### 7.2 Implicit Defaults (When Scope is Underspecified)

| Query Type | Parsed State | Route | Default Applied |
|---|---|---|---|
| Player name only | player, no season/timeframe | player_game_finder | 2025-26 regular season, limit 25 |
| Team name only | team, no season/timeframe | game_finder | 2025-26 regular season, limit 25 |
| Stat keyword only | stat, no player/team | season_leaders | 2025-26 regular season, stat=pts, limit 10 |
| "LeBron" | player, default policy fires | player_game_summary | 2025-26 regular season, no limit |
| "playoffs LeBron" | player, playoff keyword | player_game_summary | 2024-25 playoffs, no limit |
| "LeBron career" | player, career intent | player_game_summary | 1996-97 to 2025-26, no limit |

### 7.3 Season Type Rules

| Keyword(s) | Detected Type | Default Season |
|---|---|---|
| (none / default) | Regular Season | 2025-26 |
| "playoff", "playoffs", "postseason" | Playoffs | 2024-25 |

**Detection code:** `detect_season_type()` in `_parse_helpers.py`

---

## 8. Scalability and Risk Assessment

### 8.1 Concrete Scalability Risks

#### Risk 1: Route-Specific Display Logic in Frontend

**File:** `frontend/src/components/results/config/routeToPattern.ts`

**Issue:** Pattern selection is hard-coded by route name. Adding a new route requires editing `routeToPattern()` function. If the new route needs a different table pattern, code duplication is likely.

**Evidence:**
```typescript
case "player_game_summary":
  return [...]; // Specific pattern stack
case "player_game_finder":
  return [...]; // Similar but different pattern stack
// ... 28+ cases in a long switch statement
```

**Impact:** As routes grow, this function becomes a maintenance bottleneck. Testing new routes requires updating and re-testing pattern logic.

**Mitigation:** Consider declarative route-to-pattern config (JSON/TOML) instead of code switch.

---

#### Risk 2: Fallback Table Over-Usage

**File:** `frontend/src/components/results/config/routeToPattern.ts` (default case)

**Issue:** Any route not matched in `routeToPattern()` defaults to `fallback_table` pattern. This is a catch-all that doesn't validate route quality.

**Evidence:**
```typescript
default:
  return [{ type: "fallback_table" }];
```

**Possible unmatched routes:**
- Routes added to backend but not added to `routeToPattern` switch
- Routes intentionally returning generic data (placeholder implementations)
- Prototype/experimental routes

**Impact:** Users can't distinguish between "well-defined query" and "this route is not implemented yet." No signal difference between unfinished work and intentional generics.

**Mitigation:**
- Audit all 30+ routes to ensure they're in `routeToPattern` (find missing routes)
- Add a `route` check in `classifyResultShape()` to warn on unmapped routes
- Document which routes intentionally use `fallback_table`

---

#### Risk 3: Table Column Sets Hardcoded Per Component

**Files:** `frontend/src/components/results/patterns/GameLogResult.tsx`, `LeaderboardResult.tsx`, etc.

**Issue:** Visible columns and sort order are hardcoded in each pattern component. Adding a new stat or metric requires updating component code.

**Evidence:**
```typescript
// GameLogResult.tsx
const DEFAULT_COLUMNS = ['date', 'opponent', 'pts', 'reb', 'ast', 'fg%', '3p%'];
// If new stat is needed, this array must be updated + tested
```

**Impact:**
- New stats require code changes
- Different user preferences can't be accommodated without new route variants
- Column width/alignment issues emerge on new stats without explicit testing

**Mitigation:**
- Column config could be passed via route metadata or result sections
- Frontend could infer columns from result row schema (discovery-based rendering)

---

#### Risk 4: Result Sections + Pattern Config Tightly Coupled

**Issue:** Pattern configs reference specific `sectionKey` values (e.g., `game_log`, `summary`, `leaderboard`). Backend section names must match frontend keys exactly.

**Evidence:**
```typescript
// routeToPattern.ts
case "player_game_summary":
  return [
    { type: "entity_summary", sectionKey: "summary" },
    { type: "game_log", sectionKey: "game_log", ... }
  ];
```

If backend route returns sections named differently (`games` instead of `game_log`), frontend rendering fails silently.

**Impact:**
- Mismatches between backend section names and frontend sectionKey cause invisible breakage
- Refactoring section names is risky (requires coordinated frontend + backend changes)
- Testing doesn't catch name mismatches easily (result just appears empty)

**Mitigation:**
- Frontend schema validation or strict typing for sectionKey
- Backend contract docs listing all section names per route
- Automated tests that verify section names match

---

#### Risk 5: Data Scope Defaults Distributed Across Files

**Files:**
- `_default_rules.py` (4 named policies)
- `_parse_helpers.py` (season-type detection, default_season_for_context)
- `_seasons.py` (resolve_career, resolve_since_year, etc.)
- `_build_parse_state()` in `natural_query.py` (fuzzy "recent" → last_n=10)

**Issue:** Default scope rules are not centralized. Changes to default season require edits across multiple files. Future maintainers may not realize all the places defaults are applied.

**Impact:**
- Inconsistent defaults if one file is updated but another is missed
- Difficult to audit all defaults in one place
- Tests may not cover all default scenarios

**Mitigation:**
- Centralized defaults configuration (e.g., DEFAULTS = { "current_season": "2025-26", "current_playoff_season": "2024-25", ... })
- Single source of truth for default rules
- Integration tests verifying default behavior across all routes

---

#### Risk 6: No Execution Coverage for Some Routes

**Issue:** Some routes have been defined and tested at the parser level, but execution (command modules) may not be production-ready.

**Example:** Occurrence routes, opponent-quality routes, period/quarter/role filters — these are Phase G/Phase H work-in-progress. Parser recognizes them, but execution is incomplete.

**Evidence:** Code in `_natural_query_execution.py` has feature gates:
```python
_PHASE_G_CLUTCH_TRANSPORT_ROUTES = { ... }
_PHASE_G_PERIOD_TRANSPORT_ROUTES = { ... }
```

**Impact:**
- User can ask a well-formed query, get routed to a real route, but receive no-result due to missing feature
- Frontend may show misleading "no data" instead of "feature not available yet"

**Mitigation:**
- Audit which routes have incomplete execution
- Mark incomplete routes in documentation
- Return explicit `ResultStatus: unsupported` instead of empty results

---

#### Risk 7: Multi-Route Output Patterns Not Validated

**Issue:** Some routes stack multiple patterns (e.g., `team_record` → `record + game_log` if rows present). The frontend assumes result sections align with pattern config.

**Evidence:**
```typescript
case "team_record":
  return data.result?.sections?.game_log?.length
    ? [
        { type: "record", mode: "team_record" },
        { type: "game_log", ... }
      ]
    : [{ type: "record", mode: "team_record" }];
```

If backend logic changes and `game_log` section is missing when expected, frontend pattern mismatch occurs.

**Impact:**
- Conditional pattern stacking creates complexity
- Easy for backend refactors to break frontend rendering unexpectedly

**Mitigation:**
- Explicit validation: pattern renderers should check for required sections before rendering
- Fail gracefully: missing section → show placeholder or skip pattern, not white-screen

---

### 8.2 Product Quality Gaps by Table Pattern

| Table Pattern | What Works | Gaps / Weak Points | Data / Columns Missing | Needs Decision | Should Lock/Revise |
|---|---|---|---|---|---|
| **Player Game Log** | Core game records, date-sorted, summary strip | No season grouping; detail drawer UX unclear | Play-by-play, advanced metrics only available client-side after full fetch | Column width for new stats? | Lock for now; defer advanced stat support |
| **Team Game Log** | Scores, W/L, date-sorted, summary strip | Same as player; plus-minus not visible by default | Advanced team metrics (pace, four-factors) | Should hidden metrics be searchable? | Lock; defer advanced metrics |
| **Leaderboard** | Rank-sorted, league-wide top-10 by default | No filtering UI (no position, no team pre-filter) | Rank stability (time-on-list), appearance count | Filter behavior: client-side or route-level? | Audit; probably lock core 10 routes |
| **Split Comparison** | Buckets, edge chips for deltas | Hard to spot tiny differences; no trend over season | Trend data (split performance over time) | Which splits are primary? | Revise UI for clarity; document supported splits |
| **Streak Table** | Ranked streaks, length highlighted | Game-by-game detail drawer slow for long streaks | Definition / starting point not always clear to user | Should users be able to change threshold? | Lock definitions; document in result note |
| **Top Performances** | Top 10 ranked by stat | Stat is fixed (usually PPG); no client filtering | Per-game context (opponent level, home/away) | Support multi-stat ranking (Game Score, PER)? | Lock single-stat variant first |
| **Playoff History** | Season-by-season table | Opponent names could be clearer; limited to teams | Player-level playoff records | Extend to players? | Lock teams; defer players |
| **Team Record** | W/L hero + summary | Decade/era breakdown unclear without context | Era/decade boundaries, playoff-only records | Standard eras (80s, 90s, etc.)? | Lock current; document era rules |
| **Comparison (Player/Team)** | Metric side-by-side with delta | Large metric list not scannable; no grouping | Metric categories (offense, defense, efficiency) | Sort order: alphabetical, by delta, by category? | Audit metric count; consider grouping |

---

## 9. Implementation Priorities and Next Steps

### 9.1 Recommended Next Phase: "Lock Core Patterns"

**Scope:** Establish stable contracts for the top 8 routes currently in use, ensuring frontend and backend patterns are well-tested and documented.

**Why this phase:**
- The system is functional but has no guarantees on pattern stability
- New features (Phase H+) will depend on these cores being solid
- No existing test coverage on pattern contracts (frontend ↔ backend section names)

**What to do (sequenced):**

1. **Audit Route-Pattern Mapping (2 hours)**
   - Verify all 30 routes are in `routeToPattern` switch
   - List any routes that fall through to `fallback_table`
   - Document which routes intentionally use fallback (if any)
   - **Output:** List of unmapped routes + audit report

2. **Create Pattern Contract Tests (4 hours)**
   - For each of top 8 routes, write frontend test verifying section names match pattern config
   - Test that pattern configs render without errors
   - Test that missing sections degrade gracefully
   - **Output:** New test suite in `frontend/src/test/resultShapes.test.ts`

3. **Document Locked Patterns (3 hours)**
   - For each top 8 route, write a one-page pattern spec:
     - Route name, result shape, table component
     - Expected section names
     - Visible columns, hidden columns
     - Row cap, sort order, edge cases
   - **Output:** `docs/reference/pattern_contracts.md` with tables for each

4. **Align Backend Section Names (2 hours)**
   - Verify backend modules return sections matching pattern config expectations
   - Fix any mismatches (e.g., section named "games" but pattern expects "game_log")
   - Add comment in route handler documenting section schema
   - **Output:** Updated command modules with explicit section documentation

5. **Create End-to-End Pattern Tests (3 hours)**
   - E2E tests: query → route → result → pattern → rendered HTML
   - At least one test per top 8 routes
   - Verify table renders, columns are present, sort order is correct
   - **Output:** New E2E test in `frontend/src/test/ResultRenderer.test.tsx`

**Success criteria:**
- All 30 routes have a named pattern (no fallback-table edges cases)
- Contract docs exist for top 8 routes
- Pattern tests pass (section names, column presence, rendering)
- Developers know which routes are "locked" and safe to rely on

**Rough estimate:** 14 hours total for small team.

---

### 9.2 Phase After: "Unblock Phase H Execution"

Once core patterns are locked:

1. **Audit Phase G/H incomplete features** (opponent_quality, clutch, period, role, etc.)
2. **Implement missing data in commands** (filters, aggregations that currently return empty)
3. **Expand pattern coverage** to support new filtered results
4. **Add UX patterns for unsupported signals** (e.g., "Clutch filter not supported on this route yet")

---

### 9.3 Longer-term Improvements (Post-Lock)

- **Column configuration schema:** Allow routes to declare column preferences, reduce frontend hardcoding
- **Declarative pattern config:** Move `routeToPattern` to JSON/TOML, enable non-engineers to add routes
- **Client-side filtering:** Add UI for position, team, stat in leaderboard rows (currently route-level only)
- **Metric grouping:** Organize comparison metric tables by category (offense, defense, etc.)
- **Historic trend support:** Add mini-charts in split/streak tables showing metric trend over season

---

## 10. Validation and Confidence Notes

### 10.1 Files Inspected

✅ Inspected and cross-referenced:
- `src/nbatools/commands/natural_query.py` — 1750+ lines, route finalization logic, all 28+ route assignments
- `src/nbatools/commands/_natural_query_execution.py` — 300+ lines, build_result map, phase feature gates
- `src/nbatools/commands/_default_rules.py` — Named default policies
- `src/nbatools/commands/_parse_helpers.py` — Season detection, defaults
- `src/nbatools/commands/_seasons.py` — Season resolution, career ranges
- `frontend/src/components/results/config/routeToPattern.ts` — 200+ lines, route→pattern mapping
- `frontend/src/components/results/resultShapes.ts` — 100+ lines, result shape definitions
- `frontend/src/components/results/patterns/*` — 10 pattern components (GameLogResult, LeaderboardResult, etc.)
- `docs/architecture/parser/examples.md` — Query examples
- `docs/determination_layer_audit.md` — Scope defaults, result metadata contracts

### 10.2 Limitations

- **No execution depth:** Did not inspect each command module's implementation (e.g., `player_game_summary.py`, `season_leaders.py`). Assume they work as documented; did not verify data correctness.
- **No data audit:** Did not verify actual data output. Assume CSV data is loaded correctly.
- **Frontend render depth:** Did not inspect CSS/styling; focus was on table schema and data flow.
- **Parser equivalence not verified:** Parser behavior inferred from code; did not run full test suite on examples.
- **Phase G/H feature gates:** Some features (clutch, period, role) are marked as phase-gated but execution not audited.

### 10.3 What Would Verify This Map

- Run parser-examples sweep (if artifacts exist in outputs/): compare expected routes to actual
- Run live queries on each of 30 routes, screenshot results, verify pattern classification
- Review test coverage for each route (unit tests should exist in tests/)
- Inspect actual rendered HTML for 3–5 key routes

---

## Appendix: Constants and Reference

### A. Season Constants

```python
EARLIEST_SEASON = "1996-97"
LATEST_REGULAR_SEASON = "2025-26"
LATEST_PLAYOFF_SEASON = "2024-25"
```

Source: `src/nbatools/commands/_seasons.py`

### B. Query Classes

| Query Class | Meaning | Routes |
|---|---|---|
| `summary` | Player/team averages over period | player_game_summary, game_summary |
| `finder` | Game list matching filters | player_game_finder, game_finder |
| `leaderboard` | Ranked top N | season_leaders, season_team_leaders, top_player_games, etc. |
| `streak` | Consecutive-game streaks | player_streak_finder, team_streak_finder |
| `split` | Breakdown by bucket | player_split_summary, team_split_summary, player_on_off |
| `comparison` | Two-entity comparison | player_compare, team_compare |
| `record` | W/L or matchup record | team_record, playoff_history, etc. |
| `playoff` | Playoff-specific queries | playoff_history, playoff_matchup_history, etc. |
| `lineup` | Named unit queries | lineup_summary, lineup_leaderboard |
| `occurrence` | Count or distinct-player queries | player_occurrence_leaders, team_occurrence_leaders |

### C. Feature Transport Sets (Phase G/H Incomplete Features)

```python
_SUPPORTED_OPPONENT_QUALITY_ROUTES = {
    "player_game_summary",
    "player_game_finder",
    "player_stretch_leaderboard",
    "game_summary",
    "game_finder",
    "team_record",
}

_PHASE_G_CLUTCH_TRANSPORT_ROUTES = {
    "player_game_summary",
    "player_game_finder",
    "team_record",
    "season_leaders",
}

_PHASE_G_PERIOD_TRANSPORT_ROUTES = {
    "player_game_finder",
    "team_record",
}

_PHASE_G_ROLE_TRANSPORT_ROUTES = {
    "player_game_summary",
    "player_game_finder",
}

_PHASE_H_SCHEDULE_CONTEXT_ROUTES = {
    "player_game_summary",
    "team_record",
}
```

Source: `src/nbatools/commands/_natural_query_execution.py`

---

**End of Raw Query Product Map**
