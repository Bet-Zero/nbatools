# Parser Specification

> **Purpose of this doc:** The component-by-component technical reference for the natural-query parser in `nbatools`. For each stage, this defines what it does, what it must support, what decisions need to be made, and how it connects to the next stage. For framing and design principles, see [`overview.md`](./overview.md). For example inputs and end-to-end traces, see [`examples.md`](./examples.md).
>
> **Scope:** This doc describes the parser's _design_ — components, contracts, and slot shapes. It is not a capability catalog. For the living inventory of what the parser currently supports, see [`docs/reference/query_catalog.md`](../../reference/query_catalog.md).

Where this spec notes parser-shipped but execution-partial behavior (for example, unfiltered context filters or placeholder on/off routes), the active continuation plan is [`parser_execution_completion_plan.md`](../../planning/parser_execution_completion_plan.md) and its current queue [`phase_g_work_queue.md`](../../planning/phase_g_work_queue.md). This file remains a current-state design reference, not a roadmap.

---

## Table of contents

1. [Pipeline overview](#1-pipeline-overview)
2. [Input normalization](#2-input-normalization)
3. [Entity resolution](#3-entity-resolution)
4. [Query classes and intent modifiers](#4-query-classes-and-intent-modifiers)
5. [Slot extraction](#5-slot-extraction)
6. [Time parsing](#6-time-parsing)
7. [Threshold and operator parsing](#7-threshold-and-operator-parsing)
8. [Context filters](#8-context-filters)
9. [Opponent-quality filters](#9-opponent-quality-filters)
10. [Absence and with-without logic](#10-absence-and-with-without-logic)
11. [On/off, lineup, and stretch support](#11-onoff-lineup-and-stretch-support)
12. [Occurrence queries](#12-occurrence-queries)
13. [Streak queries](#13-streak-queries)
14. [Playoff and historical queries](#14-playoff-and-historical-queries)
15. [Defaults for underspecified queries](#15-defaults-for-underspecified-queries)
16. [Ambiguity and confidence](#16-ambiguity-and-confidence)
17. [Canonical intermediate representation](#17-canonical-intermediate-representation)
18. [Glossary and vocabulary](#18-glossary-and-vocabulary)
19. [Evaluation strategy](#19-evaluation-strategy)
20. [Failure modes](#20-failure-modes)
21. [Logging and improvement loop](#21-logging-and-improvement-loop)

---

## 1. Pipeline overview

The parser lives in `src/nbatools/commands/natural_query.py` and its helper modules. It has two main phases:

```
raw text
   ↓
[1] normalization (normalize_text)
   ↓
[2] slot extraction (parallel) — _build_parse_state()
      ├── time: extract_season, extract_season_range, extract_since_season,
      │         extract_last_n_seasons, extract_last_n, extract_date_range,
      │         detect_career_intent, detect_season_type
      ├── entities: detect_player_resolved, detect_team_in_text,
      │             detect_opponent, detect_opponent_player, detect_without_player,
      │             extract_player_comparison, extract_team_comparison
      ├── stats: detect_stat, extract_threshold_conditions, extract_min_value
      ├── intent flags: wants_summary, wants_finder, wants_count,
      │                 wants_leaderboard, wants_team_leaderboard,
      │                 wants_split_summary, wants_recent_form,
      │                 detect_record_intent, detect_season_high_intent,
      │                 detect_distinct_player_count, detect_distinct_team_count,
      │                 wants_occurrence_leaderboard
      ├── contexts: detect_home_away, detect_wins_losses, detect_split_type,
      │             extract_position_filter, detect_head_to_head
      ├── structured: extract_occurrence_event, extract_compound_occurrence_event,
      │               extract_streak_request, extract_team_streak_request
      └── playoff/historical: detect_by_decade_intent, detect_playoff_history_intent,
                              detect_playoff_appearance_intent,
                              detect_playoff_round_filter, detect_by_round_intent
   ↓
parse state (dict with ~40 slots)
   ↓
[3] route selection — _finalize_route()
      Big if/elif chain that picks a route + route_kwargs based on slot combinations.
      Delegates specialized clusters to try_playoff_record_route,
      try_occurrence_count_route, try_compound_occurrence_route.
   ↓
parse state with route + route_kwargs + notes
   ↓
(handed off to stats engine via query_service.execute_natural_query)
```

Key architectural notes:

- **Slot extraction is parallel, not sequential.** `_build_parse_state` runs every detector and extractor on the normalized query independently. Later stages consume the combined state.
- **Intent is inferred, not declared.** There is no single "intent classification" step. The _combination of slot values and intent flags_ determines routing in `_finalize_route`.
- **The parse state is the canonical intermediate representation** (see §17).
- **OR clauses are handled separately** via `query_boolean_parser` and `_split_or_clauses`, with `_merge_inherited_context` carrying context into each clause.

---

## 2. Input normalization

Handle messy input before slot extraction runs. Centralized in `normalize_text()` in `_constants.py`.

### 2.1 Surface normalization

- lowercase / case-insensitive matching
- punctuation-insensitive matching
- whitespace collapse
- apostrophes (`Celtics'` → `celtics`)
- accent folding (`Dončić` → `doncic`)
- plural/singular handling where it matters
- hyphen variants (`back to back` / `back-to-back` / `b2b`)

### 2.2 Alias mapping

Common aliases should collapse to a canonical form before downstream parsing. Some are already handled in scattered detectors; a consolidated alias layer is a target for the normalization-consolidation phase (see expansion plan).

| Alias                                | Canonical form                    |
| ------------------------------------ | --------------------------------- |
| `vs`                                 | `against`                         |
| `w/`                                 | `with`                            |
| `w/o`                                | `without`                         |
| `out`, `inactive`, `absent`          | `did not play`                    |
| `last 10`                            | `last 10 games`                   |
| `3s`, `threes`, `3pm`                | `3-pointers made`                 |
| `ts`, `ts%`                          | `true shooting percentage`        |
| `ortg`                               | `offensive rating`                |
| `drtg`                               | `defensive rating`                |
| `netrtg`, `net`                      | `net rating`                      |
| `ppg`, `rpg`, `apg`                  | per-game stat forms               |
| `td`, `dd`                           | triple-double, double-double      |
| `boards`, `dimes`, `swipes`, `swats` | rebounds, assists, steals, blocks |
| `scoring`                            | `points`                          |

See the [living stat-alias inventory in `query_catalog.md` §2.6](../../reference/query_catalog.md) for what is currently recognized.

### 2.3 Tolerance requirements

The normalizer must tolerate:

- **typos**: `doncic`, `jokic`, `wemby`, `anteto`
- **abbreviations**: `SGA`, `AD`, `JJJ`, `CP3`, `KAT`
- **shorthand fragments**: `bucks record giannis out`
- **missing stopwords**: `most assists last 10`
- **informal spelling**: `steph 5+ 3s lately`

### 2.4 Output

After normalization, downstream extractors see a clean canonical string. Example:

```
Input:  "Celtics' record vs teams above .500 w/o Tatum"
Output: "celtics record against teams above .500 without tatum"
```

---

## 3. Entity resolution

Identify the real-world subject(s) the query references. Implemented across `_matchup_utils.py` and `entity_resolution.py`.

### 3.1 Entity types detected

- **player** — most common; subject, opponent, or absence filter
- **team** — subject, opponent, or context
- **opponent** — the team the subject is playing against (`detect_opponent`)
- **opponent_player** — opposing player in a matchup filter (`detect_opponent_player`)
- **teammate in absence filter** — referenced via `detect_without_player`
- **player comparison pair** — `extract_player_comparison` → (`player_a`, `player_b`)
- **team comparison pair** — `extract_team_comparison` → (`team_a`, `team_b`)
- **position group** — `extract_position_filter`
- **lineup / unit** — on/off and lineup placeholder routing are supported; real data-backed lineup execution is still future work (see §11)

### 3.2 Name reference styles

All of these should resolve:

- full names: `Shai Gilgeous-Alexander`
- short/first names: `Shai`, `LeBron`, `Steph`, `Jokic`
- last names: `Brunson`, `Curry`, `Tatum`
- nicknames: `Bron`, `AD`, `Wemby`, `KD`, `Dame`
- abbreviations: `SGA`, `CP3`, `JJJ`, `KAT`
- team shorthand: `Knicks`, `OKC`, `GSW`, `Nugs`, `Cavs`, `Sixers`
- diacritic-insensitive: `Jokic` / `Jokić`, `Doncic` / `Dončić`

90+ curated aliases are currently supported.

### 3.3 Ambiguous references

The existing `detect_player_resolved()` returns a resolution object with:

- `is_confident` — True if a single match is high-confidence
- `is_ambiguous` — True if multiple candidates exist
- `resolved` — the canonical name when confident
- `candidates` — the list of possible matches when ambiguous
- `source` — which resolver produced the result

When ambiguous and no other entity is resolved, `_finalize_route` short-circuits with a `format_ambiguity_message` prompt rather than silently guessing. This pattern should extend to future entity types.

Tie-break candidates when resolution produces multiple matches:

- nearby entity context (if `OKC` appears, `Williams` → Jalen Williams)
- recency / current-season activity
- team context from the rest of the query
- popularity as a final fallback

### 3.4 Output on the parse state

```json
{
  "player": "NIKOLA_JOKIC",
  "player_a": null,
  "player_b": null,
  "team": null,
  "team_a": null,
  "team_b": null,
  "opponent": null,
  "opponent_player": null,
  "without_player": null,
  "entity_ambiguity": null
}
```

When ambiguous:

```json
{
  "player": null,
  "entity_ambiguity": {
    "type": "player",
    "input": "brown last 10",
    "candidates": ["Jaylen Brown", "Bruce Brown"],
    "source": "surname_resolver"
  }
}
```

---

## 4. Query classes and intent modifiers

The repo uses a two-layer intent model:

- **Query classes** describe the shape of the answer (finder, count, summary, etc.).
- **Intent modifiers** are flag-level signals that combine with slots to select the specific route.

This is deliberately different from a flat "one intent enum" model. The combination of query class + modifiers + slot values lets the router handle many specific capabilities without exploding the intent enum.

### 4.1 Query classes

| Class         | Answers                                                            |
| ------------- | ------------------------------------------------------------------ |
| `finder`      | Game rows matching conditions                                      |
| `count`       | Count of games or occurrences matching a condition                 |
| `summary`     | Aggregated stats over a sample (player or team)                    |
| `comparison`  | Side-by-side stats for two entities                                |
| `split`       | Home/away or wins/losses breakdowns                                |
| `leaderboard` | Ranked lists (season leaders, occurrence leaders, top games)       |
| `streak`      | Consecutive games meeting a condition                              |
| `record`      | Team win-loss records with optional filters                        |
| `playoff`     | Playoff history, appearances, round records, matchup history       |
| `occurrence`  | Count of games where a stat threshold was met (single or compound) |

### 4.2 Intent modifiers (flags on the parse state)

| Flag                            | Signals                                                            |
| ------------------------------- | ------------------------------------------------------------------ |
| `summary_intent`                | User wants aggregated stats (`summary`, `averages`, `recent form`) |
| `finder_intent`                 | User wants matching game rows (`show me`, `list`, `find`)          |
| `count_intent`                  | User wants a count (`how many`, `count`, `number of`)              |
| `record_intent`                 | User wants win-loss (`record`, `win percentage`)                   |
| `leaderboard_intent`            | Player leaderboard (`top scorers`, `most 3s`)                      |
| `team_leaderboard_intent`       | Team leaderboard (`best offensive teams`)                          |
| `occurrence_leaderboard_intent` | Most X-point games (`most 40 point games`)                         |
| `season_high_intent`            | Best single games for a player (`season high`, `best game`)        |
| `distinct_player_count`         | Count of distinct players meeting condition                        |
| `distinct_team_count`           | Count of distinct teams meeting condition                          |
| `split_intent`                  | Home-vs-away or wins-vs-losses split                               |
| `range_intent`                  | Season range or date range specified                               |
| `career_intent`                 | Career / all-time scope                                            |
| `head_to_head`                  | H2H filter requested                                               |
| `by_decade_intent`              | Decade-bucketed result                                             |
| `playoff_appearance_intent`     | Counts playoff appearances                                         |
| `playoff_history_intent`        | Playoff-specific query                                             |
| `by_round_intent`               | Results bucketed by playoff round                                  |

### 4.3 Class × modifier examples

| Query                                   | Class                | Key modifiers                                  |
| --------------------------------------- | -------------------- | ---------------------------------------------- |
| `most points last 10`                   | `leaderboard`        | `leaderboard_intent`                           |
| `Jokic last 10`                         | `summary`            | `summary_intent` (inferred)                    |
| `biggest scoring games this season`     | `leaderboard`        | `season_high_intent` (league-wide)             |
| `Curry 5+ threes this season`           | `count`/`occurrence` | `occurrence_event` populated                   |
| `Mavericks record when Luka scores 35+` | `record`             | `record_intent` + threshold                    |
| `Celtics vs contenders`                 | `record` (default)   | `record_intent` + opponent-quality (future)    |
| `Edwards in wins vs losses`             | `split`              | `split_intent` + `split_type="wins_vs_losses"` |
| `Suns when Booker out`                  | `summary`/`record`   | `without_player` filter                        |
| `Nuggets Jokic on off`                  | `summary`            | `lineup_members` + `presence_state`; placeholder on/off route |
| `LeBron vs Durant career stats`         | `comparison`         | `career_intent` + player comparison            |
| `Jokic longest 30-point streak`         | `streak`             | `streak_request` populated                     |
| `Lakers vs Celtics playoff history`     | `playoff`            | `playoff_history_intent`                       |

### 4.4 Decision signals

Strong signals for selecting a class:

- **operator words** (`most`, `best`, `highest`, `leaders`, `top`) → `leaderboard`
- **`how many`, `count`, `number of`** → `count`
- **`record`, `win percentage`** → `record`
- **`how often`, threshold + count phrasing** → `occurrence`
- **`streak`, `N straight games`, `consecutive games`** → `streak`
- **`vs` / `against` with two named entities** → `comparison`
- **`home vs away`, `wins vs losses`** → `split`
- **`summary`, `recent form`, `averages`** → `summary`
- **`show me`, `list`, `find`, `which games`** → `finder`
- **`playoff`, `finals`, `conference finals`, `by decade`** → `playoff`
- **entity + timeframe only, no operator** → `summary` (default, see §15)

---

## 5. Slot extraction

All slots are extracted in parallel in `_build_parse_state()` and collected into a single parse state dict.

### 5.1 Slot taxonomy

**Time slots**

| Slot           | Source                                                                   | Values                            |
| -------------- | ------------------------------------------------------------------------ | --------------------------------- |
| `season`       | `extract_season`                                                         | `"2025-26"`                       |
| `start_season` | `extract_season_range`, `extract_since_season`, `extract_last_n_seasons` | `"2020-21"`                       |
| `end_season`   | `extract_season_range`, defaults                                         | `"2025-26"`                       |
| `start_date`   | `extract_date_range`                                                     | ISO date                          |
| `end_date`     | `extract_date_range`                                                     | ISO date                          |
| `season_type`  | `detect_season_type`                                                     | `"regular"` / `"playoffs"` / etc. |
| `last_n`       | `extract_last_n`                                                         | int (games)                       |
| `top_n`        | `extract_top_n`                                                          | int (ranking limit)               |

**Entity slots**

| Slot                   | Source                      | Values                       |
| ---------------------- | --------------------------- | ---------------------------- |
| `player`               | `detect_player_resolved`    | player ID                    |
| `player_a`, `player_b` | `extract_player_comparison` | two player IDs               |
| `team`                 | `detect_team_in_text`       | team code                    |
| `team_a`, `team_b`     | `extract_team_comparison`   | two team codes               |
| `opponent`             | `detect_opponent`           | team code                    |
| `opponent_player`      | `detect_opponent_player`    | player ID                    |
| `without_player`       | `detect_without_player`     | player ID                    |
| `position_filter`      | `extract_position_filter`   | e.g. `"guards"`, `"centers"` |

**Stat / threshold slots**

| Slot                   | Source                                                | Values                                 |
| ---------------------- | ----------------------------------------------------- | -------------------------------------- |
| `stat`                 | `detect_stat`                                         | canonical stat name                    |
| `min_value`            | `extract_threshold_conditions` or `extract_min_value` | numeric                                |
| `max_value`            | `extract_threshold_conditions`                        | numeric                                |
| `threshold_conditions` | `extract_threshold_conditions`                        | list of threshold dicts (primary)      |
| `extra_conditions`     | `extract_threshold_conditions`                        | list of threshold dicts (AND-combined) |

**Context / filter slots**

| Slot                       | Source                        | Values                                 |
| -------------------------- | ----------------------------- | -------------------------------------- |
| `home_only`, `away_only`   | `detect_home_away`            | bool                                   |
| `wins_only`, `losses_only` | `detect_wins_losses`          | bool                                   |
| `split_type`               | `detect_split_type`           | `"home_away"` / `"wins_losses"` / etc. |
| `head_to_head`             | `detect_head_to_head`         | bool                                   |
| `playoff_round_filter`     | `detect_playoff_round_filter` | round name                             |

**Structured-query slots**

| Slot                             | Source                              | Values              |
| -------------------------------- | ----------------------------------- | ------------------- |
| `occurrence_event`               | `extract_occurrence_event`          | event dict          |
| `compound_occurrence_conditions` | `extract_compound_occurrence_event` | list of event dicts |
| `streak_request`                 | `extract_streak_request`            | streak config       |
| `team_streak_request`            | `extract_team_streak_request`       | streak config       |

### 5.2 Required slots by query class

Each class has minimum slots that must be filled (directly or via defaults) for routing to succeed.

| Class         | Minimum slots                                                         | Commonly optional                         |
| ------------- | --------------------------------------------------------------------- | ----------------------------------------- |
| `finder`      | `player` or `team`; `season`/range/date window                        | `stat`, `min_value`, context filters      |
| `count`       | `player` or `team`; at least one threshold condition; time scope      | additional thresholds (AND/OR)            |
| `summary`     | `player` or `team`; time scope                                        | `stat`, opponent, context filters         |
| `comparison`  | two entities (`player_a`+`player_b` or `team_a`+`team_b`); time scope | context filters                           |
| `split`       | entity; `split_type`; time scope                                      | `stat`, opponent                          |
| `leaderboard` | `stat` (or `leaderboard_intent` + default); time scope                | `top_n`, `position_filter`, opponent      |
| `streak`      | entity; `streak_request` or `team_streak_request`                     | time scope                                |
| `record`      | `team` (single or vs matchup); time scope                             | `threshold_conditions`, opponent, context |
| `playoff`     | entity; at least one playoff modifier                                 | opponent, round filter, decade            |
| `occurrence`  | `occurrence_event` (stat + threshold); time scope                     | compound conditions                       |

When a required slot is missing and cannot be filled by defaults (§15), routing should return low confidence or request clarification rather than guess.

---

## 6. Time parsing

Time expressions are one of the top sources of parser failure. The repo already handles many.

### 6.1 Currently handled

| Form                            | Helper                     | Example           |
| ------------------------------- | -------------------------- | ----------------- |
| `this season`                   | default / `extract_season` | → current season  |
| explicit season (`2025-26`)     | `extract_season`           | `"2025-26"`       |
| season range (`from X to Y`)    | `extract_season_range`     | start + end       |
| since season / year             | `extract_since_season`     | start + end       |
| last N seasons                  | `extract_last_n_seasons`   | start + end       |
| career / all-time               | `detect_career_intent`     | start + end       |
| last N games                    | `extract_last_n`           | integer           |
| date range / month / since date | `extract_date_range`       | start + end dates |
| `recent form` → last 10         | `wants_recent_form`        | `last_n=10`       |
| season type (playoffs, regular) | `detect_season_type`       | string            |
| by-decade                       | `detect_by_decade_intent`  | flag              |

### 6.2 Partial / needing expansion

| Form                                     | Status                                      |
| ---------------------------------------- | ------------------------------------------- |
| `lately`, `recently`                     | Partial; maps to recent form inconsistently |
| `past month`, `last month`               | Partial; depends on date-range extraction   |
| `past 2 weeks`, `last couple weeks`      | Not reliable                                |
| `last night`, `tonight`, `yesterday`     | Not reliable                                |
| `since the All-Star break`               | Partial                                     |
| `before Christmas`, `after the deadline` | Partial                                     |

### 6.3 Decisions to lock down

These affect every query using fuzzy time words:

- Does `last 10` always mean games, not days? **(Current behavior: games.)**
- Does `this year` mean current season or calendar year? **(Current behavior: current season.)**
- What does `recently` / `lately` mean? **(Suggested default: last 10 games.)**
- Does `past month` mean rolling 30 days or current calendar month? **(Suggested default: rolling 30 days.)**

See §18 for the consolidated glossary.

---

## 7. Threshold and operator parsing

The repo already has a mature threshold system supporting compound boolean logic. This is one of its stronger existing capabilities.

### 7.1 Operator normalization

| Surface forms                                  | Canonical operator |
| ---------------------------------------------- | ------------------ |
| `30+`, `30 plus`, `30 or more`, `at least 30`  | `>=` 30            |
| `over 30`, `more than 30`                      | `>` 30             |
| `under 110`, `less than 110`, `fewer than 110` | `<` 110            |
| `between 20 and 30`, `20 to 30`                | range `[20, 30]`   |
| `exactly 10`                                   | `==` 10            |

Handled by `extract_threshold_conditions` which returns a list of condition dicts.

### 7.2 Compound conditions

**AND combination** — primary + extras in the parse state:

- `30+ points and 10+ rebounds` → `threshold_conditions[0]` (primary, sets `stat`/`min_value`) + `extra_conditions[0]`
- `25+ points and shot under 40%`
- `10+ rebounds in wins` → threshold + `wins_only`

**OR combination** — handled at a layer above via clause splitting:

- `over 30 points or over 12 assists` → split into two sub-clauses, each routed, then results unioned
- Handled by `_split_or_clauses` + `_combine_or_results`

**Grouped boolean with parentheses** — a third level:

- `(over 25 points and over 10 rebounds) or over 15 assists`
- Handled by `query_boolean_parser` → `expression_contains_boolean_ops`
- Routed through `_execute_grouped_boolean_build_result`

### 7.3 Threshold condition shape

Each condition in the parse state:

```json
{
  "stat": "pts",
  "min_value": 30,
  "max_value": null,
  "text": "30+ points"
}
```

The `text` field preserves the surface form for result display and debugging.

### 7.4 Context-bearing thresholds

A threshold can carry additional context:

- threshold inside a filter: `Jokic 30+ points vs Lakers`
- threshold inside a split: `10+ rebounds in wins`
- threshold inside a streak: `5 straight games with 30+ points`
- threshold inside a count: `how many 40-point games`

The threshold slot travels _with_ the rest of the parse state; it doesn't stand alone.

---

## 8. Context filters

**Status: partially shipped.** Home/away, wins/losses, season type, and playoff-round filters are execution-backed. Clutch, period, schedule, and role filters are parser-recognized and route-propagated today, with explicit unfiltered-results notes where backing data is still missing.

Define where or when within a game the stat applies.

### 8.1 Currently supported

**Location / schedule**

- `home`, `away` → `home_only` / `away_only`
- `clutch`, `in the clutch`, `clutch time`, `late-game` → `clutch`
  parse slot; current execution accepts the filter with an explicit
  unfiltered-results note because play-by-play clutch splits are not yet available
- `back-to-backs`, `b2b`, `second of a back-to-back` → `back_to_back=True`
- `rest advantage`, `rest disadvantage`, `on 2 days rest` → `rest_days`
  (`"advantage"`, `"disadvantage"`, or an integer day count)
- `one-possession games` → `one_possession=True`
- `nationally televised`, `on national TV` → `nationally_televised=True`
- `as starter`, `as a starter`, `starting`, `off the bench`, `bench`, `reserve` → `role`
  for player-context queries only; team-only phrasing like `Celtics bench scoring`
  is intentionally ignored
- `1st/2nd/3rd/4th quarter`, `first/second half`, `overtime`, `OT` → `quarter` / `half`
  parse slots; current game-log data does not expose period splits, so the engine
  accepts these filters with an explicit unfiltered-results note

Schedule-context slots above are parser-recognized and route-propagated; the
current query engine accepts them with an explicit unfiltered-results note
because schedule/context feature tables are not yet joined into route execution.

**Outcome**

- `wins`, `losses` → `wins_only` / `losses_only`

**Split combinations**

- `home vs away`, `wins vs losses` → `split_type` + `split_intent`

**Season type**

- `regular season`, `playoffs`, `postseason` → `season_type`

**Playoff rounds**

- `finals`, `conference finals`, `second round`, etc. → `playoff_round_filter`

### 8.2 Not yet fully shipped at the execution layer

- true clutch-filtered results backed by play-by-play data
- true quarter / half / overtime split execution from period-level data
- true schedule-context execution for `back_to_back`, `rest_days`, `one_possession`, and `nationally_televised`
- true starter / bench execution for the `role` slot

Parser recognition for these filters is shipped. The remaining gap is honest,
execution-level filtering rather than slot detection.

---

## 9. Opponent-quality filters

**Status: shipped for the core single-entity summary/finder/record routes plus stretch leaderboards.**
Opponent filters now accept the concrete quality buckets below. Execution-backed
resolution currently applies on `player_game_summary`, `player_game_finder`,
`game_summary`, `game_finder`, `team_record`, and `player_stretch_leaderboard`;
unsupported routes carry an explicit note when the bucket is recognized but not yet wired.

Supported surface forms:

- `against good teams`
- `against top teams`
- `against contenders`
- `against playoff teams`
- `against teams over .500`
- `against top-10 defenses`

### 9.1 Product-policy definitions

Shipped policy buckets:

- `good teams` → latest regular-season standings snapshot, `win_pct >= .500`
- `top teams`, `contenders` → latest regular-season standings snapshot, `conference_rank <= 6`
- `playoff teams` → latest regular-season standings snapshot, `conference_rank <= 10`
- `teams over .500` → latest regular-season standings snapshot, `win_pct > .500`
- `top-10 defenses` → latest regular-season team advanced table, top 10 by `def_rating`

### 9.2 Structured shape

Opponent-quality filters carry both the surface term and the resolved definition, so policy can change without re-parsing old queries:

```json
{
  "type": "opponent_quality",
  "surface_term": "contenders",
  "definition": {
    "metric": "conference_rank",
    "operator": "<=",
    "scope": "conference",
    "snapshot": "latest_regular_season",
    "source": "standings_snapshots",
    "value": 6
  }
}
```

---

## 10. Absence and with-without logic

Shipped via `detect_without_player`. Supports:

- `without X`
- `w/o X`
- `when X out`
- `when X was out` / `when X is out`
- `when X didn't play` / `when X did not play`
- `no X`
- `sans X`
- `minus X`

The detected player ID is stored in `without_player`. If the same player is also detected as the primary subject, the subject is cleared so the query routes to the team path (e.g., `Lakers record without LeBron` → team path, not player path).

Note: `X off` is deliberately **not** matched as absence — it is reserved for on/off court analysis (§11).

### 10.1 Distinguish carefully between absence concepts

These are structurally different and should not be conflated:

| Concept                             | Supported?                  |
| ----------------------------------- | --------------------------- |
| Player absent from game (DNP)       | ✅ via `without_player`     |
| Player off court during possessions | Parser/routing shipped; execution placeholder — see §11 |
| Player did not start                | Not supported               |
| Player played limited minutes       | Not supported               |

### 10.2 Negation forms to handle

All absence forms below are now shipped:

- `without X` ✅
- `w/o X` ✅
- `when X out` / `when X was out` / `when X is out` ✅
- `when X didn't play` / `when X did not play` ✅
- `no X`, `minus X`, `sans X` ✅

Remaining unsupported:

- `X off` — reserved for on/off (§11), NOT absence
- `not including playoffs`
- `non overtime games`

---

## 11. On/off, lineup, and stretch support

**Status: mixed.** Single-player on/off phrasing and lineup/unit phrasing route to dedicated placeholder paths with honest unsupported-data notes. Stretch/rolling-window leaderboards are fully shipped on top of whole-game player logs.

### 11.0 Current shipped surface

Shipped in Phase E items 8, 9, and 10:

- `on/off`
- `with X on the floor`
- `without X on the floor`
- `X on court`
- `X off court`
- `X sitting`
- `best 5-man lineups`
- `3-man units with 200+ minutes`
- `2-man combos`
- `lineup with X and Y`
- `with X and Y together`
- `hottest 3-game scoring stretch`
- `best 5-game stretch by Game Score`
- `most efficient 10-game rolling stretch`

These queries populate `lineup_members`, `presence_state`, `unit_size`, and `minute_minimum` as applicable, route to `player_on_off`, `lineup_summary`, or `lineup_leaderboard`, and return an honest note explaining that real on/off splits and lineup-unit stats require play-by-play, stint, or lineup tables that are not yet available.

Stretch queries populate `window_size` and `stretch_metric`, route to `player_stretch_leaderboard`, keep the intent in the `leaderboard` family, and return real rolling-window results over player game logs.

### 11.1 Target query types

| Query type                    | Example                                                         |
| ----------------------------- | --------------------------------------------------------------- |
| On/off split                  | `Jokic on/off`, `Nuggets with and without Jokic`                |
| Single-player presence filter | `with Curry on the floor`, `without Giannis`                    |
| Specific lineup               | `lineups with LeBron and AD`                                    |
| Ranked lineups                | `best 5-man lineups`, `best 3-man units with at least 200 mins` |
| Multi-player net rating       | `net rating with Tatum and Brown together`                      |
| Stretch leaderboard           | `hottest 3-game scoring stretch`, `best 5-game stretch by Game Score` |

### 11.2 New slots required

- `lineup_members` — list of player IDs
- `presence_state` — on-court / off-court / mixed
- `minute_minimum` — from query or product-policy default
- `unit_size` — 2-man, 3-man, 5-man
- `window_size` — integer rolling-window length for stretch queries
- `stretch_metric` — canonical metric ranked across the rolling window

### 11.3 Route behavior

- `player_on_off`, `lineup_summary`, and `lineup_leaderboard` are shipped parser/route surfaces with honest unsupported-data notes because play-by-play, stint, and lineup tables are still missing
- `player_stretch_leaderboard` is a shipped execution-backed route using full-game player logs
- stretch queries default to rolling average `game_score` when no metric is named; `efficient` maps to rolling `ts_pct`, and named shooting percentages are computed from rolling makes/attempts

### 11.4 Treat as dedicated subsystems

On/off and lineup data access patterns, defaults, and minute thresholds differ from basic player/team stat queries, so they stay in dedicated intent families with dedicated routes. Stretch queries remain in the `leaderboard` intent family, but they still need dedicated routing because rolling-window aggregation is distinct from season-wide ranking.

---

## 12. Occurrence queries

Count of games where a stat threshold was met. Already shipped in multiple forms.

### 12.1 Single-event occurrence

- `most 40 point games since 2020`
- `most 15+ rebound games`
- `most triple doubles since 2020`
- `most double doubles last 3 seasons`

Extracted via `extract_occurrence_event`, producing:

```json
{
  "stat": "pts",
  "min_value": 40,
  "special_event": null
}
```

Special events like `triple-double` / `double-double` produce an `occurrence_event` with a `special_event` key instead of a threshold.

### 12.2 Compound occurrence

- `most games with 25+ points and 10+ assists`
- `how many Jokic games with 30+ points and 10+ rebounds in playoffs since 2021`

Extracted via `extract_compound_occurrence_event` → `compound_occurrence_conditions`, a list of condition dicts.

### 12.3 Occurrence leaderboards

`wants_occurrence_leaderboard` signals that the query is asking for a ranked list of players/teams by occurrence count, not a single value. Routes to `player_occurrence_leaders` or similar.

### 12.4 Distinct-entity occurrence

- `how many players scored 40 points this season`
- `number of players with 10 assists this season`

Routes to `player_occurrence_leaders` with `limit=None` and a distinct-count note. Requires a stat + threshold. Phrasing without a threshold (`how many players played this season`) is not supported.

---

## 13. Streak queries

Consecutive games meeting a condition. Already shipped for both player and team.

### 13.1 Player streaks

- `Jokic 5 straight games with 20+ points`
- `Jokic longest streak of 30 point games`
- `Jokic consecutive games with a made three`
- `Jokic longest triple-double streak`

Extracted via `extract_streak_request`, producing:

```json
{
  "stat": "pts",
  "min_value": 30,
  "special_condition": null,
  "min_streak_length": null,
  "longest": true
}
```

Special patterns (e.g., triple-double streaks, made-three streaks) are handled via `STREAK_SPECIAL_PATTERNS`.

### 13.2 Team streaks

- `longest Lakers winning streak`
- `Celtics 5 straight games scoring 120+`
- `longest Bucks streak with 15+ threes`

Extracted via `extract_team_streak_request` → `TEAM_STREAK_SPECIAL_PATTERNS`.

### 13.3 Default time scope

When a streak query omits a time scope, the parser defaults to a three-season window ending at the current season. This default is applied in `_build_parse_state` and should be preserved.

---

## 14. Playoff and historical queries

A distinct cluster handled by `_playoff_record_route_utils.py` via `try_playoff_record_route`.

### 14.1 Playoff history

- `Lakers playoff history`
- `Celtics finals record`
- `Heat vs Knicks playoff history`
- `Lakers playoff series record vs Celtics`

Detected via `detect_playoff_history_intent`.

### 14.2 Playoff appearances

- `Warriors conference finals appearances`
- `most Finals appearances since 1980`
- `best finals record since 1980`

Detected via `detect_playoff_appearance_intent`.

### 14.3 By-round

- `best second round record`
- `LeBron record in the Finals`

Detected via `detect_by_round_intent` and `detect_playoff_round_filter`.

### 14.4 By-decade / era-bucket

- `Warriors record by decade`
- `winningest team of the 2010s`
- `Lakers vs Celtics by decade`

Detected via `detect_by_decade_intent`.

### 14.5 Record leaderboards

- `best record since 2015`
- `highest win percentage vs Lakers since 2018`

Handled via `try_record_leaderboard_route`.

---

## 15. Defaults for underspecified queries

Most real queries are underspecified. Without good defaults, the parser feels random.

Default rules are implemented as named functions in `_default_rules.py`. Each takes the parse state and returns `(should_fire, notes_message)`.

### 15.1 Defaults in place

| Pattern                                 | Behavior                                                   | Named rule / implementation          | `notes` prefix             |
| --------------------------------------- | ---------------------------------------------------------- | ------------------------------------ | -------------------------- |
| No season + any stat/filter signal      | `default_season_for_context(season_type)` → current season | `_build_parse_state` inline          | —                          |
| `recent form` / recent-form signals     | `last_n = 10`                                              | `_build_parse_state` inline          | —                          |
| Streak query without explicit time      | Three-season window ending at current                      | `streak_default_window()`            | `default:`                 |
| Season-high without player              | League-wide `top_player_games`                             | `_finalize_route` inline             | `season_high:`             |
| Season-high with player                 | `player_game_finder` sorted by stat desc                   | `_finalize_route` inline             | `season_high:`             |
| `<player> + <timeframe>` only           | Summary (stat line for the window)                         | `player_timeframe_summary_default()` | `default:`                 |
| `<metric>` only, no subject             | League-wide leaderboard                                    | `metric_only_leaderboard_default()`  | `default:`                 |
| `<player> + <threshold>` only           | `player_game_finder` (list matching games)                 | `player_threshold_finder_default()`  | `default:`                 |
| `<team> + <threshold>` only             | `game_finder` (list matching games)                        | `team_threshold_finder_default()`    | `default:`                 |
| Top player/team games (keyword)         | `top_player_games` / `top_team_games` ranked by stat       | `_finalize_route` inline             | `default:`                 |
| Stat fallback (season-advanced blocked) | Falls back to `pts` when stat unavailable in context       | `_finalize_route` inline             | `stat_fallback:`           |
| Leaderboard in date window              | Game-log derived (excludes season-advanced stats)          | `_finalize_route` inline             | `leaderboard_source:`      |
| Player summary/compare/split            | Sample-recomputed advanced metrics                         | `_finalize_route` inline             | `sample_advanced_metrics:` |

### 15.2 Defaults not yet formalized

These are recognized as desirable but not yet implemented:

| Pattern                            | Target default behavior                        | Status                                         |
| ---------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| `<team> + <opponent-quality>` only | `record` vs that opponent group                | Not yet shipped (opponent-quality routing TBD) |
| `"best games" + <subject>`         | Ranked game logs by default metric             | Partially covered by season-high routing       |
| `<player> + vs <team-quality>`     | Stat line summary filtered by opponent quality | Not yet shipped                                |

### 15.3 Worked examples

| Query                                    | Default parse                               | Named rule                         |
| ---------------------------------------- | ------------------------------------------- | ---------------------------------- |
| `Jokic last 10`                          | Summary for Jokic over his last 10 games    | `player_timeframe_summary_default` |
| `Curry 5+ threes`                        | Finder listing games Curry made 5+ threes   | `player_threshold_finder_default`  |
| `points leaders`                         | League-wide points leaderboard              | `metric_only_leaderboard_default`  |
| `Jokic 5 straight games with 20+ points` | Streak finder with three-season window      | `streak_default_window`            |
| `Lakers over 120 points`                 | Game finder listing Lakers 120+ point games | `team_threshold_finder_default`    |
| `highest scoring games this season`      | League-wide top single-game performances    | season-high inline                 |

### 15.4 Defaults are product policy

These affect every subsequent answer. They should be documented in §18 (Glossary) and changeable without rewriting parser code. Named functions in `_default_rules.py` make each rule inspectable and independently testable.

---

## 16. Ambiguity and confidence

Some queries genuinely have more than one reasonable parse. Handle this explicitly.

### 16.1 Entity-level ambiguity (shipped)

`detect_player_resolved` returns an ambiguous result when a reference matches multiple players. `_finalize_route` short-circuits with a clarification prompt via `format_ambiguity_message` when no other entity is resolved.

This pattern has been extended to:

- **Team references**: `resolve_team()` in `entity_resolution.py` returns a `team_resolution_confidence` signal (`confident` / `none`) that feeds into the parse-wide confidence score.
- **Stat references**: `resolve_stat()` validates stat aliases against the unified `STAT_ALIASES` dict and sets `stat_resolution_confidence` (`confident` / `none`).

Not yet extended to: ambiguous opponent references (deferred to Phase E).

### 16.2 Parse-level confidence (implemented)

The parse state carries a parse-wide `confidence` score (0.0–1.0), computed by `compute_parse_confidence()` in `_confidence.py`. The function uses a heuristic model — no ML.

**Scoring formula** (base = 0.70, clamped to [0.0, 1.0]):

| Signal                        | Effect               |
| ----------------------------- | -------------------- |
| Route is `None` / unsupported | −0.40 (early return) |
| Entity resolved (player/team) | +0.08                |
| No entity, not a leaderboard  | −0.05                |
| `entity_ambiguity` present    | −0.20                |
| Explicit intent flag set      | +0.10                |
| Default rule fired (`notes`)  | −0.08 per default    |
| Stat resolved (`confident`)   | +0.05                |
| Stat not resolved             | −0.03                |
| Team resolved (not in entity) | +0.04                |
| Timeframe specified           | +0.05                |
| No timeframe                  | −0.05                |
| Threshold present             | +0.05                |

**Confidence tiers:**

| Confidence         | Example                        | Behavior                                 |
| ------------------ | ------------------------------ | ---------------------------------------- |
| High (>0.85)       | `Jokic triple doubles` (0.90)  | Execute directly                         |
| Medium (0.60–0.85) | `Celtics recently` (0.80)      | Execute with best parse; show alternates |
| Low (<0.60)        | No route / unresolvable entity | Would prompt for clarification           |

### 16.3 Common ambiguous inputs

Verified routing as of Phase D implementation:

| Query                  | Route                | Confidence | Alternates                                 |
| ---------------------- | -------------------- | ---------- | ------------------------------------------ |
| `Celtics recently`     | `game_finder`        | 0.80       | —                                          |
| `Tatum vs Knicks`      | `player_game_finder` | 0.80       | `player_game_summary` (averages vs NYK)    |
| `Jokic triple doubles` | `player_game_finder` | 0.90       | — (high confidence, no alternates)         |
| `best games Booker`    | `player_game_finder` | 0.90       | — (high confidence, no alternates)         |
| `Thunder clutch`       | `game_finder`        | 0.80       | — (clutch filter not yet shipped; Phase E) |

### 16.4 Disambiguation strategy

1. Apply defaults (§15) to pick the most likely parse
2. If two parses are close in likelihood, return the top one with alternate surfaced as a "did you mean" option
3. Only prompt for clarification when genuinely ambiguous or a required slot is unresolvable

**Implementation:** `generate_alternates()` in `_confidence.py` checks known ambiguity patterns when confidence < 0.85 and returns up to 2 alternates. Each alternate is a dict:

```json
{
  "intent": "summary",
  "route": "player_game_summary",
  "description": "Jayson Tatum averages vs NYK",
  "confidence": 0.75
}
```

The React UI renders alternates as clickable "Did you mean?" chips via the `DidYouMean` component. The API surfaces them in the `QueryResponse` envelope.

**Anti-pattern**: silent wrong answers. Pretending the parse is certain when it isn't is worse than asking.

### 16.5 Tie-break rules when confidence is close

- Prefer the parse with fewer unfilled required slots
- Prefer the parse consistent with recent query context in the session
- Prefer the parse that matches the subject's typical query pattern

---

## 17. Canonical intermediate representation

The parse state produced by `_build_parse_state` → `_finalize_route` is the contract between parser and stats engine. Every query produces one of these.

### 17.1 Current parse state shape

The state dict includes the slots described in §5 plus:

- `normalized_query` — the cleaned query string
- `route` — the selected engine route name
- `route_kwargs` — dict of arguments for that route
- `notes` — optional list of parser-side notes for result display (includes `"default: …"` entries when a named default rule fired; see §15)
- `entity_ambiguity` — set when entity resolution short-circuited
- `intent` — `QueryIntent` value (e.g. `"summary"`, `"finder"`, `"leaderboard"`); populated by `route_to_intent()` in `_constants.py` at the end of `_finalize_route`
- `confidence` — parse-wide confidence score (0.0–1.0); computed by `compute_parse_confidence()` in `_confidence.py` (see §16.2)
- `alternates` — list of alternate interpretation dicts when confidence < 0.85; generated by `generate_alternates()` in `_confidence.py` (see §16.3–16.4); empty for high-confidence parses
- `stat_resolution_confidence` — `"confident"` or `"none"`, from `resolve_stat()`
- `team_resolution_confidence` — `"confident"` or `"none"`, from `resolve_team()`

### 17.2 `QueryIntent` enum values

The `QueryIntent` class in `_constants.py` defines these intent labels:

| Intent        | Value             | Route examples                                                          |
| ------------- | ----------------- | ----------------------------------------------------------------------- |
| `SUMMARY`     | `"summary"`       | `player_game_summary`, `game_summary`, `team_record`, `playoff_history` |
| `COMPARISON`  | `"comparison"`    | `player_compare`, `team_compare`, `team_matchup_record`                 |
| `FINDER`      | `"finder"`        | `player_game_finder`, `game_finder`                                     |
| `COUNT`       | `"count"`         | `player_game_finder` (with `count_intent=True`)                         |
| `SPLIT`       | `"split_summary"` | `player_split_summary`, `team_split_summary`                            |
| `LEADERBOARD` | `"leaderboard"`   | `season_leaders`, `top_player_games`, `player_occurrence_leaders`, `player_stretch_leaderboard` |
| `STREAK`      | `"streak"`        | `player_streak_finder`, `team_streak_finder`                            |
| `ON_OFF`      | `"on_off"`        | `player_on_off`                                                         |
| `LINEUP`      | `"lineup"`        | `lineup_summary`, `lineup_leaderboard`                                  |
| `UNSUPPORTED` | `"unsupported"`   | `None` route                                                            |

The `ROUTE_TO_INTENT` dict in `_constants.py` maps every route name to its intent. `route_to_intent(route, count_intent=...)` is the public lookup function.

### 17.3 Complete example

**Query:** `how many Jokic games with 30+ points and 10+ rebounds since 2021`

```json
{
  "normalized_query": "how many jokic games with 30+ points and 10+ rebounds since 2021",
  "player": "Nikola Jokić",
  "team": null,
  "count_intent": true,
  "stat": "pts",
  "min_value": 30.0,
  "max_value": null,
  "threshold_conditions": [
    {
      "stat": "pts",
      "min_value": 30.0,
      "max_value": null,
      "text": "30+ points"
    },
    {
      "stat": "reb",
      "min_value": 10.0,
      "max_value": null,
      "text": "10+ rebounds"
    }
  ],
  "extra_conditions": [
    {
      "stat": "reb",
      "min_value": 10.0,
      "max_value": null,
      "text": "10+ rebounds"
    }
  ],
  "start_season": "2021-22",
  "end_season": "2025-26",
  "season": null,
  "season_type": "Regular Season",
  "last_n": null,
  "route": "player_occurrence_leaders",
  "route_kwargs": {
    "conditions": [
      { "stat": "pts", "min_value": 30.0 },
      { "stat": "reb", "min_value": 10.0 }
    ],
    "season": null,
    "start_season": "2021-22",
    "end_season": "2025-26",
    "season_type": "Regular Season",
    "opponent": null,
    "home_only": false,
    "away_only": false,
    "wins_only": false,
    "losses_only": false,
    "start_date": null,
    "end_date": null,
    "limit": 500,
    "player": "Nikola Jokić"
  },
  "notes": [],
  "intent": "leaderboard",
  "confidence": 1.0,
  "alternates": []
}
```

### 17.4 Why a formalized canonical form matters

- **Debugging**: inspect the parse independently from the answer
- **Testing**: score parses slot-by-slot, not just end-to-end
- **Equivalence**: question and shorthand forms produce identical parse states → easy to verify
- **Evolution**: new intents and filters plug into the same shape
- **Cross-surface**: CLI, API, and UI all consume the same envelope

---

## 18. Glossary and vocabulary

Consolidated reference for fuzzy terms, aliases, and defaults. The canonical source of truth for these definitions lives in `src/nbatools/commands/_glossary.py` — this section mirrors that module and must be kept in sync.

### 18.1 Time-term definitions (suggested defaults — confirm at product level)

| Term                | Definition                                 | Current state |
| ------------------- | ------------------------------------------ | ------------- |
| `recently`          | Last 10 games                              | Supported     |
| `lately`            | Last 10 games                              | Supported     |
| `past month`        | Rolling 30 days                            | Supported     |
| `last month`        | Rolling 30 days                            | Supported     |
| `last couple weeks` | Rolling 14 days                            | Supported     |
| `past 2 weeks`      | Rolling 14 days                            | Supported     |
| `last night`        | Yesterday's date                           | Supported     |
| `yesterday`         | Yesterday's date                           | Supported     |
| `today`             | Today's date                               | Supported     |
| `tonight`           | Today's date                               | Supported     |
| `this year`         | Current season                             | Supported     |
| `this season`       | Current season                             | Supported     |
| `career`            | All regular-season + playoff games to date | Supported     |
| `last N`            | Last N **games** (not days)                | Supported     |

### 18.2 Opponent-quality definitions

| Term              | Definition                                              | Shipped |
| ----------------- | ------------------------------------------------------- | ------- |
| `good teams`      | Latest regular-season standings snapshot: win_pct ≥ .500 | Yes     |
| `winning teams`   | Latest regular-season standings snapshot: win_pct ≥ .500 | Yes     |
| `top teams`       | Latest regular-season standings snapshot: conference_rank ≤ 6 | Yes     |
| `contenders`      | Latest regular-season standings snapshot: conference_rank ≤ 6 | Yes     |
| `playoff teams`   | Latest regular-season standings snapshot: conference_rank ≤ 10 | Yes     |
| `teams over .500` | Latest regular-season standings snapshot: win_pct > .500 | Yes     |
| `top-10 defenses` | Latest regular-season team advanced table: top 10 by defensive rating | Yes     |
| `top-10 offenses` | Top 10 by offensive rating at query time                | No      |
| `elite defenses`  | Top 5 by defensive rating at query time                 | No      |
| `bad teams`       | Teams with win % < .400                                 | No      |

### 18.3 Subjective-term definitions

| Term                | Definition                                             | Shipped |
| ------------------- | ------------------------------------------------------ | ------- |
| `best games`        | Ranked by Game Score (default); by points if specified | No      |
| `biggest games`     | Ranked by points scored                                | No      |
| `best stretch`      | Stretch queries default to rolling average Game Score unless an explicit metric is named | Yes     |
| `hottest`           | Stretch queries rank the rolling per-game average of the requested stat; if no stat is named, they default to rolling average Game Score | Yes     |
| `efficient`         | Stretch queries without an explicit stat rank rolling True Shooting % | Yes     |
| `clutch`            | Last 5 min of 4th quarter or OT, score within 5        | No      |
| `all-around games`  | Undefined — not yet shipped                            | No      |
| `catch-and-shoot`   | Undefined — not yet shipped                            | No      |
| `transition scorer` | Undefined — not yet shipped                            | No      |

### 18.4 Metric aliases

See [`query_catalog.md` §2.6](../../reference/query_catalog.md) for the living inventory.

Canonical examples:

| User phrasing                         | Canonical metric |
| ------------------------------------- | ---------------- |
| `points`, `scoring`, `pts`            | `pts`            |
| `rebounds`, `boards`, `rebs`          | `reb`            |
| `assists`, `dimes`, `asts`            | `ast`            |
| `steals`, `swipes`                    | `stl`            |
| `blocks`, `swats`                     | `blk`            |
| `threes`, `3s`, `3pm`, `made threes`  | `fg3m`           |
| `true shooting`, `ts`, `ts%`          | `ts_pct`         |
| `effective field goal`, `efg`, `efg%` | `efg_pct`        |
| `field goal %`, `fg%`                 | `fg_pct`         |
| `3pt%`, `three-point percentage`      | `fg3_pct`        |
| `free throw %`, `ft%`                 | `ft_pct`         |
| `plus-minus`, `+/-`                   | `plus_minus`     |
| `turnovers`, `tos`, `tov`             | `tov`            |
| `triple-double`, `td`                 | `triple-double`  |
| `double-double`, `dd`                 | `double-double`  |

### 18.5 Relation aliases

| User phrasing                       | Canonical form       |
| ----------------------------------- | -------------------- |
| `vs`, `against`                     | `against`            |
| `w/`, `with`                        | `with`               |
| `w/o`, `without`, `minus`, `sans`   | `without`            |
| `out`, `inactive`, `DNP`            | `did not play`       |
| `on`, `on the floor`, `on court`    | `on court`           |
| `off`, `off the floor`, `off court` | `off court`          |

### 18.6 Default-behavior table

| Query shape                   | Default parse                          |
| ----------------------------- | -------------------------------------- |
| `<player> + <timeframe>`      | `summary`                              |
| `<team> + <opponent-quality>` | `record` vs that opponent group        |
| `<player> + <threshold>`      | `occurrence` / `count`                 |
| `<player> on/off`             | `player_on_off` (placeholder execution) |
| `best <N>-man lineups`        | `lineup_leaderboard` (placeholder execution) |
| `best <player> games`         | Ranked game logs by Game Score         |
| `hottest <N>-game stretch`    | `player_stretch_leaderboard`           |
| `<team> + recently`           | `summary` (team-level) + recent record |
| `<metric>` only, no subject   | `leaderboard` (league-wide)            |
| `<player> vs <team-quality>`  | `summary` filtered by opponent quality |

---

## 19. Evaluation strategy

Don't test only the happy path. The test harness should cover every failure mode.

### 19.1 Categories to include

- full natural questions
- search-style phrases
- compressed shorthand
- typo-filled inputs
- abbreviation-heavy inputs
- ambiguous inputs
- multi-filter queries
- queries with missing verbs
- word-order variants
- near-duplicate semantic equivalents
- compound boolean threshold queries
- streak queries
- occurrence queries
- playoff / historical queries

### 19.2 Equivalence groups

Queries within a group should produce identical parse states (modulo confidence). The harness should verify this explicitly.

Example equivalence group:

- `Who has the most points in the last 10 games?`
- `most points last 10 games`
- `points leaders last 10`
- `last 10 scoring leaders`
- `top scorers last 10 games`

All five should produce the same parse state.

See [`examples.md` §6](./examples.md) for complete equivalence groups.

### 19.3 Accuracy rubric

Score parses component-by-component:

| Component                  | Weight     |
| -------------------------- | ---------- |
| Entity resolution correct  | high       |
| Query class correct        | high       |
| Intent flags correct       | high       |
| Stat correct               | high       |
| Thresholds correct         | high       |
| Time scope correct         | medium     |
| Context filters correct    | medium     |
| Defaults applied correctly | medium     |
| Confidence calibrated      | low-medium |

A parser can be "almost right" in ways that still produce a bad answer. Component-level scoring catches these.

### 19.4 Test infrastructure

Align with the existing repo conventions (see [`AGENTS.md`](../../../AGENTS.md) for full detail):

| Scenario                          | Test command                                  |
| --------------------------------- | --------------------------------------------- |
| Parser helper change              | `make test-impacted`, then `make test-parser` |
| Routing logic change              | `make test-impacted`, then `make test-query`  |
| Core computation change           | `make test-impacted`, then `make test-engine` |
| Broad / cross-cutting change      | `make test-preflight`                         |
| Before merge / maximum confidence | `make test`                                   |

Parser and routing tests use pytest markers (`parser`, `query`) which combine with testmon for fast feedback during iteration.

---

## 20. Failure modes

Test these cases explicitly. These are where parsers crack.

### 20.1 Common failure patterns

- ambiguous player names (`Brown`, `Williams`, `Johnson`)
- vague time words (`recently`, `lately`)
- shorthand threshold syntax (`30+`, `5 or more`)
- missing verbs (`Giannis last 10`)
- reversed word order (`last 10 most points`)
- multiple filters in one query (`SGA vs top defenses last 5 in wins`)
- absence vs on/off confusion (`without Luka` vs `Luka off`)
- record vs summary confusion (`Celtics vs contenders`)
- "best games" interpretation (by what metric?)
- unsupported-but-plausible requests (requires clear failure rather than wrong answer)

### 20.2 Explicit failure-test cases

The harness should include these exact shorthand queries:

- `Brown last 10`
- `Celtics lately`
- `SGA vs good teams last 5`
- `Luka 35+ wins`
- `Jokic with Murray off`
- `best defense this month min 10 games`
- `Brunson no Randle playoffs`
- `Warriors record Curry 6+ threes`

### 20.3 The highest-priority failure mode

**Confident but inconsistent interpretations for short sports-style queries.**

If the same query shape produces different parses on different days, or if semantically equivalent queries produce different answers, users will lose trust fast. The harness should specifically measure consistency across equivalence groups.

---

## 21. Logging and improvement loop

Parser quality improves fastest when you can see what real users actually type.

### 21.1 What to log

- raw user query
- normalized query (post §2)
- parse state output (post §5)
- selected route + route_kwargs
- confidence score (once added)
- whether the user reformulated (submitted a new query within N seconds)
- whether the user clicked an alternate interpretation (once surfaced)
- explicit failure reason when unroutable

### 21.2 Watch for

- repeated reformulations (signals a bad first parse)
- low-confidence patterns at high volume (highest-leverage fixes)
- unsupported shorthand that shows up frequently (candidate new capabilities)
- aliases users actually use (feed back into §18 vocabulary)
- fuzzy terms users ask about most often (prioritize for policy decisions)

### 21.3 Feedback cadence

- **Weekly**: review top 20 low-confidence / unrouted queries; add coverage where patterns emerge
- **Monthly**: review new aliases that users have adopted
- **Quarterly**: re-run full evaluation suite to catch regressions

---

> **Next**: see [`examples.md`](./examples.md) for example queries, equivalence groups, end-to-end traces, and stress tests.
