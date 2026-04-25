# NBA Tools Current State Guide

> **Role: verified shipped behavior — the source of truth for what works today.**
> This doc is intentionally narrower than the roadmap. Only behavior that
> is implemented _and_ tested belongs here.
>
> Related docs:
>
> - [quick_query_guide.md](quick_query_guide.md) — quick-start examples
> - [query_guide.md](query_guide.md) — full query reference with CLI commands
> - [roadmap.md](../planning/roadmap.md) — planned / future capabilities

This guide describes the **current shipped behavior** of `nbatools`.

Use this document for:

- verified query types that currently exist in the repo
- currently supported language patterns
- current output/metric behavior
- current tested-state summary

Do **not** use this document for:

- planned capabilities
- speculative future UI behavior
- unverified broad claims
- roadmap sequencing

---

## Entry points

### Natural language (CLI)

    nbatools-cli ask "Jokic recent form"

### Structured CLI

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10

### HTTP API

    # POST /query with {"query": "Jokic recent form"}
    # POST /structured-query with {"route": "player_game_summary", "kwargs": {...}}
    # GET /health, GET /routes

### Web UI

    # Start the API (serves the built React UI at /)
    nbatools-api
    # Open http://localhost:8000 in a browser

The web UI is a React + TypeScript + Vite app that consumes the same API endpoints as any other client. It provides a query bar, sample query buttons, result tables for all query classes, a raw JSON toggle, query history, saved queries, and a Dev Tools panel for structured queries.

---

## Verified shipped query classes

The engine currently supports these major query classes.

### 1. Finder queries

Find games matching conditions. Returns a list of matching games with box-score columns.

- player game finder
- team game finder
- threshold-based matching (over / under / between)
- recent filtered windows (last N games)
- multi-condition filtering with boolean logic
- grouped boolean filtering (AND / OR / parentheses)
- season-high / best-game routing (e.g., "Cade Cunningham season high" routes to top single games)

Examples:

    nbatools-cli ask "Jokic under 20 points"
    nbatools-cli ask "Jokic between 20 and 30 points"
    nbatools-cli ask "Jokic last 10 games over 25 points and under 15 rebounds"
    nbatools-cli ask "Jokic over 25 points or over 10 rebounds"
    nbatools-cli ask "Jokic (over 25 points and over 10 rebounds) or over 15 assists"

### 2. Count queries

Count of games or occurrences matching conditions. Generated from finder results when count intent is detected.

- explicit count intent triggers: "how many", "count", "total", "number of"
- returns a single count value over the matched set

Examples:

    nbatools-cli ask "how many games did Jokic score over 30 points"
    nbatools-cli ask "how many Celtics wins this season"

### 3. Summary queries

Aggregated stats for one entity over a sample.

- player summaries
- team summaries
- filtered summaries (season, opponent, date range, last-N)
- recent form summaries
- matchup summaries (vs opponent)
- career / all-time summaries

Examples:

    nbatools-cli ask "Jokic recent form"
    nbatools-cli ask "Celtics last 15 games summary"
    nbatools-cli ask "Jokic s    nbatools-cli ask "Jokic s    nbatools-cli ask "Jokic s    nbatools-cli askon queries

Side-by-side stats for two entities.

- player vs play- player vs play- player vs play- player vs play- player vs play- player vshead phrasin- player vs play- pand multi-season comparisons

Examples:

    nbatools-cli ask "Jokic vs Embiid recent form"
    nbatools-cli ask "Kobe vs LeBron playoffs in 2008-09"
    nbatools-cli ask "Celtics vs Bucks fro    nbatools-cli ask "Celtics vs Bucks fro    nbath2h    nbatid"
    nbatools-cli ask "Lakers head-to-head vs Celtics"

### 5. Split queries

Summary stats broken down by home/away or wins/loSummary stats broken suSummary stats broken down by home/away or wiwithSummary stats bro
EEEEEEEEEEEEEEEEbaEEEEEEEEEEEEEEEEbaEEEEEEEEEEEEEEEEbaEEEEEEEEEEEEEEEEbaEEEE-cli ask "Jokic home away split last 20 games"
nbatools- nbatools- nbatools- ses"
nbato nbato nbato nbato nbato 5 points and over 10 rebounds) or over 15 assists"

### 6. Leaderboard queries

Ranked lists of entities by a statistic.

- player season leaders (averages)
- team season leaders (averages)
- top single-game play- top single-game play- top single-game play- top single-game play- top single-game play- top single-game play- top single-game play- top single-gamegames with multiple thresholds)

Examples:

    nbatools-cli ask     nbatools-cli ask     nbatools-cli ask     nbatools-cts% among players"
    nbatools-cli ask "most 30 point games"
    nbatools-cli ask "most games with 30+ points and 10+ rebounds"
    nbatools-cli ask "best offensiv    nbatools-cli asls-cli ask "teams with best efg%"
    nbatools-cli ask "teams with most threes"

### 7. Streak queries

Consecutive games meeting a condition.

- player threshold streaks
- player longest-streak queries
- made-three streaks
- triple-double streaks
- team winning / losing streaks
- team threshold streaks (scoring, threes, etc.)

Examples:

    nbatools-cli ask "Jokic 5 straight games with 20+ points"
    nbatools-cli ask "Jokic longest streak of 30 point games"
    nbatools-cli ask "Jokic consecutive games with a made three"
    nbatools-cli ask "Jokic longest triple-double streak"
    nbatools-cli ask "longest Lakers winning streak"
    nbatools-cli ask "Celtics 5 straight games scoring 120+"
    nbatools-cli ask "longest Bucks streak with 15+ threes"

### 8. Record / matchup-record queries

Win-loss record queries for teams.

- single team record over a time span
- team vs team head-to-head record
- team record leaderboard (best/worst records league-wide)
- record with opponent, home/away, and date filters
- record without a specified player (e.g., team record in games where the named player did not play)

Examples:

    nbatools-cli ask "Lakers record this season"
    nbatools-cli ask "Lakers record vs Celtics"
    nbatools-cli ask "best record this season"
    nbatools-cli ask "worst record since 2022-23"
    nbatools-cli ask "Lakers record without LeBron James"
    nbatools-cli ask "Warriors wins without Stephen Curry"

### 9. Playoff queries

Playoff history, appearances, round records, and decade buckets.

- single team playoff history/summary
- team playoff appearance counts
- team vs team playoff matchup history
- round-specific records (first round, conference finals, finals)
- record by decade for a team
- record by decade leaderboard (league-wide)
- matchup by decade

Examples:

    nbatools-cli ask "Lakers playoff history"
    nbatools-cli ask "most finals appearances"
    nbatools-cli ask "Lakers vs Celtics playoff history"
    nbatools-cli ask "best first r    nbatools-cli ask "best first  "Lakers record by decade"

---

## Query language support

### Explicit intent keywords

The parser detects explicit intent markers:

| Intent | Triggers | Intent | Triggers | Intent --------------| Intent | Triggers | Inten "list", "show", "find", "games where" |
| count | "how many", "count", "total", "number of" |
| summary | "summary", "averages", "avg", "how did", "how has"|
| leaderboard | "leaders", "who leads", "rank", "ranking" |
| record | "record", "wins", "losses", "w-l" |

### Threshold language

- `over` / `under` / `between`

Examples:

    Jokic over 25 points
    Jokic under 20 points
    Jokic between 20 and 30 points

### Stat name aliases

The parser recognizes natural-language stat phrasings beyond the standard shorthand:

- `field goal percentage`, `fg%` → fg_pct
- `3 point percentage`, `3-point percentage`, `three point percentage`, `3pt%` → fg3_pct
- `free throw percentage`, `ft%` → ft_pct
- leaderboard skill phrases such as `hottest from three`, `rim protector`,
  `playmaker`, and `offensive rebounder` map to supported box-score or
  percentage stats

These aliases work in both player and team leaderboard queries.

- `and` / `or` / parentheses

Examples:

    Jokic over 25 points and over 10 rebounds
    Jokic over 25 points or over 10 rebounds
    Jokic (over 25 points and over 10 rebounds) or over 15 assists

### Grouped boolean coverage

Grouped boolean logic currently works across:

- player finder queries
- team finder queries
- player summaries
- team summaries
- player split summaries
- team split summaries

### Coverage-gated context boundaries

Some parser-recognized context filters are execution-backed only on their
documented route boundaries. Unsupported routes keep explicit unfiltered-results
notes rather than silently pretending the filter ran.

- Clutch filters execute on `player_game_summary`, `player_game_finder`,
  `team_record`, and `season_leaders` when trusted `player_game_clutch_stats`
  / `team_game_clutch_stats` rows cover the requested slice. The definition is
  last five minutes of the fourth quarter or overtime, score within five.
  Missing or untrusted coverage keeps an explicit unfiltered-results note.
  Whole-game logs, period-only box-score rows, and season-level clutch
  dashboard aggregates are not used as clutch substitutes.
- Quarter / half / OT filters execute on `player_game_finder` and
  `team_record` when trusted `player_game_period_stats` /
  `team_game_period_stats` coverage exists for the requested slice. Broader
  route expansion is out of scope for the core finish line unless a future
  product queue reopens it.
- Schedule-context filters execute on `team_record` and
  `player_game_summary` when trusted `schedule_context_features` coverage
  exists. `nationally_televised` also requires trusted national-TV source
  coverage. Broader route expansion is out of scope for the core finish line
  unless a future product queue reopens it.
- Starter / bench role filters execute on `player_game_summary` and
  `player_game_finder` when trusted `player_game_starter_roles` rows cover the
  requested slice. Team-level bench semantics and broader route expansion are
  out of scope for the core finish line unless a future product queue reopens
  them.
- On/off queries execute on `player_on_off` when trusted
  `team_player_on_off_summary` rows cover the requested single-player slice.
  Missing or untrusted coverage, multi-player on/off requests, and slices
  outside the source contract return explicit unsupported/no-result responses.
  Whole-game `without_player` absence remains a separate game-log filter.
- Lineup queries execute on `lineup_summary` and `lineup_leaderboard` when
  trusted `league_lineup_viz` rows cover the requested season, season type,
  unit size, minimum-minute threshold, and lineup members. Missing or untrusted
  coverage, unsupported unit sizes, and slices outside the source contract
  return explicit unsupported/no-result responses. Roster membership remains an
  identity/enrichment source only, not lineup-unit execution.

### Date and window support

| Pattern           | Examples               |
| ----------------- | ---------------------- | ------------ | --------------- | ---------------------------- | ------------ | -------- | --- |
| season range      | `from 2020-21 t        | season range | `from 2020-21 t | season range `since 2020-21` |
| last N seasons    | `last 3 seasons`       |
| last N games      | `last 10 games`        | last N games | last N games w  | `in Ma                       | last N games | `        |
| since month       | `s                     | since month  | `s              | since month                  |
| rolling days      | `last 30 days`         |
| All-Star break    | `since All-Star break` |
| career / all-time | `career`, `all-time`   |
| season t          | season t               | seas`pl      | season t        | seaar                        | season t     | season t | s   |

### Opponent / matchup / head-to-head

| Pattern                         | Examples                                                                     |
| ------------------------------- | ---------------------------------------------------------------------------- |
| vs opponent (team)              | `Jokic vs Lakers`                                                            |
| vs opponent (player)            | `LeBron stats vs Kevin Durant`, `Jokic averages against Stephen Curry`       |
| without player                  | `Lakers record without LeBron`, `Warriors w/o Curry`, `Suns when Booker out` |
| summary vs opponent             | `Jokic summary vs Lakers`                                                    |
| head-to-head                    | `Jokic h2h vs Embiid`, `Lakers head-to-head vs Celtics`                      |
| single occurrence leaderboard   | `most 30 point games`                                                        |
| compound occurrence leaderboard | `most games with 30+ points and 10+ rebounds`                                |
| player occurrence count         | `how many 30 point games did Jokic have`                                     |
| distinct player count           | `how many players scored 40 points this season`                              |

### Entity resolution

The parser includes entity resolution with:

- **Player aliases**: 90+ curated nicknames and shorthand (bron → LeBron James, joker → Nikola Jokić, sga → Shai Gilgeous-Alexander, wemby → Victor Wembanyama, bronny → Bronny James)
- **Accent normalization**: nikola jokic → Nikola Jokić, luka doncic → Luka Dončić
- **Team aliases**: full team name/abbreviation/nickname mapping (hawks → ATL, lakers → LAL)
- **Ambiguity detection**: returns confidence levels (confident / ambiguous / none) with candidates; ambiguous results short-circuit to a no-result with metadata

---

## Structured routes

The query service exposes 25 structured routes:

**Player routes:**

- `player_game_summary`
- `player_game_finder`
- `player_streak_finder`
- `player_compare`
- `player_occurrence_leaders`
- `player_split_summary`

**Team routes:**

- `game_summary`
- `game_finder`
- `team_streak_finder`
- `team_compare`
- `team_occurrence_leaders`
- `team_split_summary`
- `team_record`
- `team_matchup_record`

**League-wide leaderboards:**

- `season_leaders`
- `season_team_leaders`

**Top games:**

- `top_player_games`
- `top_team_games`

**Record leaderboards:**

- `team_record_leaderboard`
- `playoff_round_record`

**Playoff routes:**

- `playoff_history`
- `playoff_appearances`
- `playoff_matchup_history`
- `record_by_decade`
- `record_by_decade_leaderboard`
- `matchup_by_decade`

---

## Metrics

### Core box-score metrics

- points, rebounds, assists, steals, blocks
- threes made, turnovers, plus/minus, minutes
- shooting splits

### Advanced shooting metrics

- eFG%, TS%

### Advanced player metrics

- USG%, AST%, REB%

These are recomputed from the filtered sample and appear in player summaries, comparisons, and split summaries.

---

## Exports

Available on both natural and structured query paths:

- `--csv`
- `--txt`
- `--json`

Examples:

    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form    nbatools-uts/jo    nbatoolrecent.json

---

## Web UI

The React frontend (`frontend/`) is a thin presentation layer over the API.

Current UI capabilities:

- text input for natural-language queries
- pre-filled sample query buttons
- result rendering for all query classes (summary, comparison, split, finder, leaderboard, streak)
- envelope metadata display (status, route, freshness, notes, caveats)
- no-result display with reason-specific messaging (no_match, no_data, unrouted, ambiguous, unsupported)
- raw JSON toggle
- in-session query history
- saved queries (localStorage persistence with load/save/export)
- shareable deep links via URL state
- Dev Tools panel for structured (route-based) queries

Build output lands in `src/nbatools/ui/dist/` and is served by FastAPI at `/`.

---

## Data Freshness

### Freshness status semantics

The engine uses four explicit freshness states:

- **fresh** — manifest complete, current_through is within 3 days.
- **stale** — manifest complete, current_through is older than 3 days.
- **unknown** — manifest or games data missing; freshness cannot be determined.
- **failed** — last refresh attempt recorded a failure.

### Pipeline CLI — refresh and auto-refresh

```bash
# One-shot refresh of the current season
nbatools-cli pipeline refresh

# Automated repeating refresh (durable local loop)
nbatools-cli pipeline auto-refresh --interval 6h
nbatools-cli pipeline auto-refresh --interval 30m --include-playoffs
```

The auto-refresh runner executes `pipeline refresh` on a repeating schedule, writes a `last_refresh.json` log after each attempt, and exits cleanly on Ctrl-C.

### Freshness API

`GET /freshness` returns a structured report:

```json
{
  "status": "fresh",
  "current_through": "2026-04-13",
  "checked_at": "2026-04-14T10:00:00",
  "seasons": [ ... ],
  "last_refresh_ok": true,
  "last_refresh_at": "2026-04-14T09:00:00",
  "last_refresh_error": null
}
```

### UI freshness indicator

The web UI displays a collapsible freshness panel with:

- status badge (fresh / stale / unknown / failed)
- current_through date
- expandable per-season details
- last refresh outcome
- auto-polls every 2 minutes

---

## Result contract

All structured result classes produce a `to_dict()` output that always includes `result_reason` (set to `null` for successful results). This key is never omitted.

### ResultStatus values

- `ok` — query executed and produced data
- `no_result` — query was understood but produced no usable output (expected failures)
- `error` — system-level execution failure (unrouted query, internal bug)

### ResultReason values

Each reason maps to a canonical status:

| Reason        | Status      | Meaning                                                        |
| ------------- | ----------- | -------------------------------------------------------------- |
| `no_match`    | `no_result` | Data exists, filters matched nothing                           |
| `no_data`     | `no_result` | Underlying season/type data file is unavailable                |
| `unsupported` | `no_result` | Invalid filter combination, unsupported stat, or unknown route |
| `ambiguous`   | `no_result` | Entity resolution found multiple matches                       |
| `unrouted`    | `error`     | Parser could not select a route                                |
| `error`       | `error`     | Unexpected internal exception                                  |

The mapping is enforced by `query_service.reason_to_status()`. Expected failures (conditions the user or data can cause) always produce `no_result`; only system-level failures produce `error`.

### Validation behavior

Unsupported filter combinations (e.g. `home_only + away_only`, `wins_only + losses_only`, invalid stat names) return a structured `NoResult` with `result_reason="unsupported"` and a descriptive note. They do not raise `ValueError` or produce HTTP error responses.

Invalid routes in the structured query endpoint return a `NoResult` with `result_reason="unsupported"` inside a normal response envelope.

---

## Current tested-state snapshot

- full suite: **1742 passing tests**
- 42 test files covering parser, routing, result contracts, CLI smoke, API, query service, and specialized query coverage
- test areas include: natural query parsing, explicit intent detection, leaderboard queries, streak queries, matchup queries, boolean parsing, occurrence/compound occurrence queries, playoff his- test areas include: natural query parsing, explicit intent detection, leuti- test areas include: nage- test areas include: natural query parres- test areas include: natural qud more

This count reflects the current repo state. It should be updated whenever the test surface changes materially.
