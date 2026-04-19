# Phase B Alias Inventory

> **Role:** Reconnaissance artifact for Phase B item 1. Catalogs every alias/mapping source in the codebase, documents which detectors consume each, and identifies divergences between tables.
>
> **Produced by:** Phase B item 1 audit.
>
> **Consumed by:** Items 2–9 of the Phase B work queue.

---

## 1. Parser-layer alias sources

These are the user-facing alias dicts that resolve natural-language phrases to canonical stat names at parse time.

### 1.1 `STAT_ALIASES` — general stat aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_constants.py` (lines 22–141) |
| **Type** | `dict[str, str]` |
| **Size** | ~80 keys |
| **Purpose** | Primary stat resolution for `detect_stat()`, threshold extraction, and boolean parser |

**Canonical stats covered:** `pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `tov`, `minutes`, `fg_pct`, `fg3_pct`, `ft_pct`, `efg_pct`, `ts_pct`, `plus_minus`, `usg_pct`, `ast_pct`, `reb_pct`, `tov_pct`, `off_rating`, `def_rating`, `net_rating`, `pace`

**Consumers:**

| Consumer | File | Matching method |
|---|---|---|
| `detect_stat()` | `_parse_helpers.py:472` | Word-boundary regex (`(?<!\w)...(?!\w)`) |
| `detect_stat()` | `query_boolean_parser.py:49` | Exact equality (`normalized == key`) |
| `extract_threshold_conditions()` | `_parse_helpers.py:523` | Via `STAT_PATTERN` regex |
| `parse_boolean_filter()` | `query_boolean_parser.py:86` | Via `STAT_PATTERN` regex |
| `_build_parse_state()` | `natural_query.py:239` | Via `detect_stat(q)` |

**Notable:** Two separate `detect_stat()` functions exist with different matching strategies (see §3.1).

---

### 1.2 `STAT_PATTERN` — regex for stat matching in thresholds

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_constants.py` (lines 144–161) |
| **Type** | Compiled regex alternation string |
| **Purpose** | Used in threshold extraction regex patterns |

**Relationship to `STAT_ALIASES`:** Must be manually kept in sync. The pattern is a hand-maintained regex alternation of `STAT_ALIASES` keys. There is no automatic derivation.

**Consumers:**

| Consumer | File |
|---|---|
| `extract_threshold_conditions()` | `_parse_helpers.py:523` |
| `parse_boolean_filter()` | `query_boolean_parser.py:86–106` |

**Keys present in `STAT_ALIASES` but missing from `STAT_PATTERN`:** `scored`, `scoring`, `scores`, `rebounded`, `rebounding`, `assisted` (verbal forms added in Phase A).

**Risk:** Any key added to `STAT_ALIASES` but not to `STAT_PATTERN` will be resolvable by `detect_stat()` but invisible to threshold extraction and boolean parsing.

---

### 1.3 `LEADERBOARD_STAT_ALIASES` — player leaderboard aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_leaderboard_utils.py` (lines 7–116) |
| **Type** | `dict[str, str]` |
| **Size** | ~90 keys |
| **Purpose** | Stat detection for player leaderboard queries |

**Canonical stats covered:** Same as `STAT_ALIASES` plus: `games_30p`, `games_40p`, `games_20p`, `games_10a`, `games_10r` (occurrence-count stats)

**Consumers:**

| Consumer | File | Matching method |
|---|---|---|
| `detect_player_leaderboard_stat()` | `_leaderboard_utils.py:221` | Word-boundary regex via `_matches_loose_phrase()` |
| `_build_parse_state()` | `natural_query.py:250` | Via `detect_player_leaderboard_stat(q)` |

**Keys unique to this dict (not in `STAT_ALIASES`):**

| Key | Canonical | Why missing from STAT_ALIASES |
|---|---|---|
| `assists per game`, `rebounds per game`, `points per game`, `steals per game`, `blocks per game`, `turnovers per game` | respective base stats | "per game" forms are leaderboard-specific phrasing |
| `30-point games`, `30 point games`, `40-point games`, etc. | `games_30p`, `games_40p`, `games_20p`, `games_10a`, `games_10r` | Occurrence-count stats only make sense for leaderboards |
| `scorers`, `rebounders`, `shot blockers`, `shot-blockers` | respective stats | Noun-agent forms (leaderboard-specific phrasing) |
| `ppg`, `rpg`, `apg`, `spg`, `bpg` | respective stats | Per-game abbreviations |
| `ts pct`, `efg pct`, `ast pct`, `reb pct`, `tov pct`, `usg pct` | respective `_pct` stats | Space-separated pct forms |

**Keys present here AND in `STAT_ALIASES` (overlap):** `scoring`, `scores`, `rebounding`, `rebounds`, `assists`, `steals`, `steal`, `blocks`, `block`, `turnovers`, `turnover`, `plus minus`, `plus/minus`, `plus_minus`, `+/-`, and all percentage/rating full-name forms. These are independently maintained — not derived from `STAT_ALIASES`.

---

### 1.4 `TEAM_LEADERBOARD_STAT_ALIASES` — team leaderboard aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_leaderboard_utils.py` (lines 118–211) |
| **Type** | `dict[str, str]` |
| **Size** | ~80 keys |
| **Purpose** | Stat detection for team leaderboard queries |

**Canonical stats covered:** `off_rating`, `def_rating`, `fg3m`, `fg3_pct`, `fg_pct`, `ft_pct`, `efg_pct`, `ts_pct`, `net_rating`, `pace`, `stl`, `blk`, `tov`, `plus_minus`, `wins`, `losses`, `win_pct`, `pts`, `reb`, `ast`

**Consumers:**

| Consumer | File | Matching method |
|---|---|---|
| `detect_team_leaderboard_stat()` | `_leaderboard_utils.py:225` | Word-boundary regex via `_matches_loose_phrase()` |
| `_build_parse_state()` | `natural_query.py:252` | Via `detect_team_leaderboard_stat(q)` |

**Unique characteristics:** Contains team-contextual phrasings (`best offensive teams`, `fastest teams`, `most wins`, `best road record`, etc.) that have no equivalent in any other alias source. Also uniquely maps to `wins`, `losses`, and `win_pct` canonical stats.

---

### 1.5 `_COMPOUND_STAT_MAP` — compound occurrence aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_occurrence_route_utils.py` (lines 97–126) |
| **Type** | `dict[str, str]` |
| **Size** | 21 keys |
| **Purpose** | Stat resolution for compound occurrence parsing ("30 points and 10 rebounds") |

**Canonical stats covered:** `pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `tov` (basic box-score stats only)

**Consumers:**

| Consumer | File |
|---|---|
| `_parse_single_threshold()` | `_occurrence_route_utils.py:129` |
| `extract_compound_occurrence_event()` | `_occurrence_route_utils.py:170` (via `_parse_single_threshold`) |

**Keys unique to this dict:** `three-pointers`, `three-pointer` (not in `STAT_ALIASES`)

**Keys missing vs `STAT_ALIASES`:** `minutes`, all percentage stats (`fg_pct`, `fg3_pct`, `ft_pct`, `efg_pct`, `ts_pct`), all advanced stats (`usg_pct`, `ast_pct`, `reb_pct`, `tov_pct`, `off_rating`, `def_rating`, `net_rating`), `plus_minus`, `pace`, and all verbal forms (`scored`, `scoring`, `scores`, `rebounded`, `rebounding`, `assisted`)

---

### 1.6 Inline stat patterns in `extract_occurrence_event()`

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_occurrence_route_utils.py` (lines 57–92) |
| **Type** | Hardcoded regex pattern lists |
| **Purpose** | Single occurrence event detection ("40-point games", "games with 5+ threes") |

**Two separate pattern lists:**

1. **`stat_event_patterns`** (line ~57) — `"NUMBER STAT games"` form
2. **`games_with_patterns`** (line ~71) — `"games with NUMBER STAT"` form

Both inline their stat-matching regexes. Neither uses `STAT_ALIASES`, `_COMPOUND_STAT_MAP`, or any shared alias source.

**Stats recognized inline:** `pts` (via `point|pts|scoring`), `reb` (via `rebound|reb|rebounds`), `ast` (via `assist|ast|assists`), `stl` (via `steal|stl|steals`), `blk` (via `block|blk|blocks`), `fg3m` (via `three|3pm|threes|3s|three-pointer|fg3m`), `tov` (via `turnover|tov|turnovers`)

**Unique patterns not in any dict:** `dishing` → `ast`, `grabbing` → `reb` (in `games_with_patterns`)

**Risk:** Adding an alias to `STAT_ALIASES` does not automatically extend these inline patterns.

---

### 1.7 `_POSITION_GROUP_PATTERNS` — position filter aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/_parse_helpers.py` (lines 72–86) |
| **Type** | `dict[str, str]` |
| **Purpose** | Resolve position-related phrases to position groups |

**Mapping:**

| Aliases | Canonical group |
|---|---|
| `guards`, `guard`, `point guards`, `shooting guards` | `guards` |
| `forwards`, `forward`, `small forwards`, `power forwards` | `forwards` |
| `centers`, `center` | `centers` |
| `bigs`, `big men`, `big man` | `bigs` |
| `wings`, `wing` | `wings` |

**Consumer:** `extract_position_filter()` in `_parse_helpers.py:89`

**Not a stat alias** — included for completeness. Out of scope for the stat-alias consolidation in items 2–6.

---

### 1.8 `ROUND_ALIASES` — playoff round aliases

| Attribute | Value |
|---|---|
| **File** | `src/nbatools/commands/playoff_history.py` (lines 53–73) |
| **Type** | `dict[str, str]` |
| **Purpose** | Resolve round names to playoff round codes |

**Mapping:** `first round`/`1st round`/`round 1`/`round one` → `01`; `second round`/`2nd round`/`round 2`/`round two`/`semifinals`/`semis` → `02`; `conference finals`/`conf finals`/etc. → `03`; `finals`/`the finals`/`nba finals`/`championship` → `04`

**Consumers:** `resolve_round_filter()` in `playoff_history.py:104`; `detect_playoff_round_filter()` in `_playoff_record_route_utils.py:93`

**Not a stat alias** — included for completeness. Out of scope for the stat-alias consolidation.

---

## 2. Engine-layer `ALLOWED_STATS` dicts

These are **downstream validation** dicts. They accept canonical stat names (or near-canonical) and map to DataFrame column names. They serve a different purpose from parser-layer aliases but contain some user-facing aliases that duplicate parser work.

### Overview table

| Module | File | Type | Size | Notable features |
|---|---|---|---|---|
| `season_leaders` | `season_leaders.py:12` | `dict` | ~80 keys | Richest — includes user-facing aliases (`scoring→pts_per_game`, `ppg→pts_per_game`), occurrence stats, advanced metrics |
| `season_team_leaders` | `season_team_leaders.py:12` | `dict` | ~75 keys | Similar to `season_leaders`; includes `offense→off_rating`, `winning percentage`, record stats |
| `player_game_finder` | `player_game_finder.py:12` | `dict` | ~22 keys | Canonical-only identity mapping; includes advanced stats |
| `player_game_summary` | `player_game_summary.py:20` | `dict` | ~22 keys | Same as `player_game_finder` |
| `top_player_games` | `top_player_games.py:8` | `dict` | ~15 keys | Basic box-score only; no advanced stats |
| `top_team_games` | `top_team_games.py:8` | `dict` | ~17 keys | Basic box-score + `oreb`/`dreb`; no advanced stats |
| `game_finder` (team) | `game_finder.py:11` | `dict` | ~20 keys | Includes `efg_pct`, `ts_pct`; no advanced rate stats |
| `game_summary` (team) | `game_summary.py:13` | `dict` | ~20 keys | Includes `efg_pct`, `ts_pct` |
| `player_split_summary` | `player_split_summary.py:17` | `dict` | ~23 keys | Includes most advanced stats except `tov_pct` |
| `team_split_summary` | `team_split_summary.py:10` | `dict` | ~20 keys | Includes `efg_pct`, `ts_pct` |
| `player_occurrence_leaders` | `player_occurrence_leaders.py:84` | `set` | 18 keys | Set (not dict); canonical names only |
| `team_occurrence_leaders` | `team_occurrence_leaders.py:82` | `set` | 18 keys | Same as player occurrence |
| `player_streak_finder` | `player_streak_finder.py:7` | (re-import) | — | Re-imports from `player_game_finder` |

### Notable duplication with parser layer

`season_leaders.ALLOWED_STATS` and `season_team_leaders.ALLOWED_STATS` contain user-facing aliases (e.g., `scoring→pts_per_game`, `ppg→pts_per_game`, `rebound→reb_per_game`) that duplicate work already done by `STAT_ALIASES` and `LEADERBOARD_STAT_ALIASES` at the parser layer. If the parser correctly resolves to a canonical stat name, the engine shouldn't need to re-resolve user-facing phrases. This creates a maintenance burden where aliases must be added in multiple places.

---

## 3. Divergences and fragmentation issues

### 3.1 Duplicate `detect_stat()` functions with different matching

Two independent `detect_stat()` implementations exist:

| Location | Matching method | Behavior difference |
|---|---|---|
| `_parse_helpers.py:472` | Word-boundary regex (`(?<!\w)key(?!\w)`) | Matches `key` as a word within longer text |
| `query_boolean_parser.py:49` | Exact equality (`normalized == key`) | Only matches when the entire normalized text IS the key |

The `_parse_helpers` version is used at the general parse layer. The `query_boolean_parser` version is used only within boolean condition parsing (where the text is already split into condition fragments). The behavioral divergence is **intentional** — boolean parser receives pre-split condition text, so exact matching is correct. But having two functions with the same name importing from the same dict is confusing.

### 3.2 `STAT_PATTERN` drift from `STAT_ALIASES`

`STAT_PATTERN` is manually maintained and does NOT include:
- `scored`, `scoring`, `scores` (verbal forms added in Phase A)
- `rebounded`, `rebounding` (verbal forms added in Phase A)
- `assisted` (verbal form added in Phase A)

These keys exist in `STAT_ALIASES` but cannot be matched by threshold/boolean patterns that use `STAT_PATTERN`. This means `extract_threshold_conditions("scored 30+ points")` cannot match the stat via the regex, though `detect_stat("scored")` would correctly resolve to `pts`.

### 3.3 Keys in `LEADERBOARD_STAT_ALIASES` but not in `STAT_ALIASES`

| Key category | Examples | Impact |
|---|---|---|
| Per-game abbreviations | `ppg`, `rpg`, `apg`, `spg`, `bpg` | `detect_stat("ppg")` returns `None`; only leaderboard detection finds it |
| Per-game phrases | `points per game`, `assists per game`, etc. | Same — invisible to general stat detection |
| Noun-agent forms | `scorers`, `rebounders`, `shot blockers` | Only resolve in leaderboard context |
| Space-separated pct forms | `ts pct`, `efg pct`, `ast pct`, etc. | Only resolve in leaderboard context |
| Occurrence-count stats | `30-point games`, `40-point games`, etc. | Leaderboard-specific; arguably correct to exclude from general alias |

**Practical impact:** A query like `"who has the most ppg"` works because it hits the leaderboard path, but `"Jokic ppg"` (a summary query) would NOT resolve the stat via `detect_stat()`.

### 3.4 `_COMPOUND_STAT_MAP` vs `STAT_ALIASES` gaps

`_COMPOUND_STAT_MAP` is a minimal subset of `STAT_ALIASES` covering only basic box-score stats. It is missing:
- All percentage stats
- All advanced stats
- All verbal forms (`scored`, `scoring`, `rebounded`, `rebounding`, `assisted`)
- `minutes`, `plus_minus`, `pace`

**Practical impact:** Compound occurrence queries with percentage or advanced stats (e.g., "games with 60%+ fg% and 30+ points") cannot parse.

### 3.5 Inline patterns in `extract_occurrence_event()` are isolated

The inline regex patterns in `extract_occurrence_event()` are completely independent of any alias dict. They:
- Cannot be extended by adding to `STAT_ALIASES`
- Contain unique aliases (`dishing` → `ast`, `grabbing` → `reb`) not in any dict
- Must be updated separately whenever stat recognition changes

### 3.6 `season_leaders` / `season_team_leaders` contain parser-layer aliases

These engine modules contain user-facing alias entries (e.g., `scoring→pts_per_game`) that duplicate parser-layer resolution. If the parser resolves `scoring` → `pts` and the leaderboard route passes `pts` to `season_leaders`, the engine's re-resolution is unnecessary. But if the parser misses an alias that the engine catches, the system works by accident rather than by design.

---

## 4. Summary: consolidation opportunities for items 2–9

### High priority (items 2–3)

1. **Merge `STAT_ALIASES` and `LEADERBOARD_STAT_ALIASES`** into a single dict (or have leaderboard dict explicitly extend the base) — eliminate the drift where aliases must be added in two places
2. **Auto-generate `STAT_PATTERN`** from the alias dict keys — eliminate manual sync requirement

### Medium priority (items 5–6, 8–9)

3. **Normalize text once at pipeline entry** — eliminate per-detector `normalize_text` calls
4. **Consolidate threshold extraction** — one code path instead of multiple
5. **Make `_COMPOUND_STAT_MAP` derive from the unified alias dict** — eliminate its isolated subset
6. **Consider making `extract_occurrence_event()` consume the alias dict** — eliminate inline regex duplication

### Lower priority / deferred

7. **Clean up engine-layer `ALLOWED_STATS` duplication** — remove user-facing aliases from `season_leaders.ALLOWED_STATS` after confirming the parser always resolves before reaching the engine
8. **Deduplicate `detect_stat()` functions** — either merge into one with a mode parameter, or rename the boolean parser's version to clarify its different semantics

---

## Appendix: complete alias coverage matrix

Cross-reference of which canonical stats are resolvable from which alias source.

| Canonical stat | `STAT_ALIASES` | `LEADERBOARD_STAT_ALIASES` | `TEAM_LEADERBOARD_STAT_ALIASES` | `_COMPOUND_STAT_MAP` | `extract_occurrence_event()` inline |
|---|---|---|---|---|---|
| `pts` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `reb` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ast` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stl` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `blk` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `fg3m` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `tov` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `minutes` | ✓ | — | — | — | — |
| `fg_pct` | ✓ | ✓ | ✓ | — | — |
| `fg3_pct` | ✓ | ✓ | ✓ | — | — |
| `ft_pct` | ✓ | ✓ | ✓ | — | — |
| `efg_pct` | ✓ | ✓ | ✓ | — | — |
| `ts_pct` | ✓ | ✓ | ✓ | — | — |
| `plus_minus` | ✓ | ✓ | ✓ | — | — |
| `usg_pct` | ✓ | ✓ | — | — | — |
| `ast_pct` | ✓ | ✓ | — | — | — |
| `reb_pct` | ✓ | ✓ | — | — | — |
| `tov_pct` | ✓ | ✓ | — | — | — |
| `off_rating` | ✓ | ✓ | ✓ | — | — |
| `def_rating` | ✓ | ✓ | ✓ | — | — |
| `net_rating` | ✓ | ✓ | ✓ | — | — |
| `pace` | ✓ | — | ✓ | — | — |
| `wins` | — | — | ✓ | — | — |
| `losses` | — | — | ✓ | — | — |
| `win_pct` | — | — | ✓ | — | — |
| `games_30p` | — | ✓ | — | — | — |
| `games_40p` | — | ✓ | — | — | — |
| `games_20p` | — | ✓ | — | — | — |
| `games_10a` | — | ✓ | — | — | — |
| `games_10r` | — | ✓ | — | — | — |

### Verbal forms coverage

| Verbal form | `STAT_ALIASES` | `LEADERBOARD_STAT_ALIASES` | `_COMPOUND_STAT_MAP` | Inline occurrence |
|---|---|---|---|---|
| `scored` | ✓ | — | — | — |
| `scoring` | ✓ | ✓ | — | ✓ (inline regex) |
| `scores` | ✓ | ✓ | — | — |
| `rebounded` | ✓ | — | — | — |
| `rebounding` | ✓ | ✓ | — | — |
| `assisted` | ✓ | — | — | — |
| `scorers` | — | ✓ | — | — |
| `rebounders` | — | ✓ | — | — |
| `dishing` | — | — | — | ✓ (inline only) |
| `grabbing` | — | — | — | ✓ (inline only) |

### Per-game abbreviation coverage

| Abbreviation | `STAT_ALIASES` | `LEADERBOARD_STAT_ALIASES` | `TEAM_LEADERBOARD_STAT_ALIASES` |
|---|---|---|---|
| `ppg` | — | ✓ | — |
| `rpg` | — | ✓ | — |
| `apg` | — | ✓ | — |
| `spg` | — | ✓ | — |
| `bpg` | — | ✓ | — |
