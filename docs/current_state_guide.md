# NBA Tools Current State Guide

This guide describes the **current shipped behavior** of `nbatools`.

It is intentionally narrower than the roadmap.

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

For future direction, see [docs/roadmap.md](roadmap.md).

---

## Entry points

### Natural language (CLI)

    nbatools-cli ask "Jokic recent form"

### Structured CLI

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10

### Web UI

    # Start the API (serves the built React UI at /)
    nbatools-api
    # Open http://127.0.0.1:8000

The web UI provides a query bar, sample query buttons, result tables, a raw JSON toggle, and a Dev Tools panel for structured queries. It is a React + TypeScript + Vite app that consumes the same API endpoints as any other client.

### HTTP API

    # POST /query with {"query": "Jokic recent form"}
    # POST /structured-query with {"route": "player_game_summary", "kwargs": {...}}
    # GET /health, GET /routes

---

## Verified shipped query classes

The repo currently supports these major query classes.

### 1. Finder queries

Current behavior includes:

- player game finder
- team game finder
- threshold-based matching games
- recent filtered windows
- multi-condition filtering
- grouped boolean filtering for finder-style queries

Examples:

    nbatools-cli ask "Jokic under 20 points"
    nbatools-cli ask "Jokic between 20 and 30 points"
    nbatools-cli ask "Jokic last 10 games over 25 points and under 15 rebounds"
    nbatools-cli ask "Jokic over 25 points or over 10 rebounds"

### 2. Summary queries

Current behavior includes:

- player summaries
- team summaries
- filtered summaries
- recent form summaries
- last-N summaries
- matchup summaries when supported by route/filter behavior

Examples:

    nbatools-cli ask "Jokic recent form"
    nbatools-cli ask "Celtics last 15 games summary"
    nbatools-cli ask "Jokic summary vs Lakers"

### 3. Comparison queries

Current behavior includes:

- player vs player comparison
- team vs team comparison
- recent-form comparison
- comparison pretty output and raw structured output
- head-to-head phrasing support at the parser/routing layer

Examples:

    nbatools-cli ask "Jokic vs Embiid recent form"
    nbatools-cli ask "Kobe vs LeBron playoffs in 2008-09"
    nbatools-cli ask "Celtics vs Bucks from 2021-22 to 2023-24"
    nbatools-cli ask "Jokic h2h vs Embiid"
    nbatools-cli ask "Lakers head-to-head vs Celtics"

### 4. Split queries

Current behavior includes:

- home vs away splits
- wins vs losses splits
- player split summaries
- team split summaries

Examples:

    nbatools-cli ask "Jokic home vs away in 2025-26"
    nbatools-cli ask "Jokic home away split last 20 games"
    nbatools-cli ask "Celtics wins vs losses"

### 5. Leaderboard queries

Current shipped leaderboard behavior includes:

- player season leaders
- team season leaders
- top single-game player performances
- top single-game team performances

Examples currently documented in the repo:

    nbatools-cli ask "top scorers this season"
    nbatools-cli ask "highest ts% among players"
    nbatools-cli ask "most 30 point games"
    nbatools-cli ask "best offensive teams"
    nbatools-cli ask "teams with best efg%"
    nbatools-cli ask "teams with most threes"

Note:

Leaderboard support exists in the current repo. Breadth and exact phrasing coverage should still be treated as something to verify by tests/examples before broadening docs claims further.

### 6. Streak queries

Current shipped streak behavior in the repo includes support for player and team streak routing.

Examples currently documented in the repo:

    nbatools-cli ask "Jokic 5 straight games with 20+ points"
    nbatools-cli ask "Jokic longest streak of 30 point games"
    nbatools-cli ask "Jokic consecutive games with a made three"
    nbatools-cli ask "Jokic longest triple-double streak"
    nbatools-cli ask "longest Lakers winning streak"
    nbatools-cli ask "Celtics 5 straight games scoring 120+"
    nbatools-cli ask "longest Bucks streak with 15+ threes"

Note:

Streak support is part of the current repo surface. Exact breadth should continue to be verified and tightened through focused tests and examples.

---

## Query language support

### Threshold language

Supported:

- `over`
- `under`
- `between`

Examples:

    Jokic over 25 points
    Jokic under 20 points
    Jokic between 20 and 30 points

### Multi-condition chaining

Supported:

- `and`
- `or`
- parentheses

Examples:

    Jokic last 10 games over 25 points and over 10 rebounds
    Celtics wins vs Bucks over 120 points and over 15 threes
    Jokic over 25 points or over 10 rebounds
    Jokic (over 25 points and over 10 rebounds) or over 15 assists
    Jokic over 25 points and (over 10 rebounds or over 15 assists)

### Grouped boolean coverage

Grouped boolean logic currently works across:

- player finder queries
- team finder queries
- player summaries
- team summaries
- player split summaries
- team split summaries

Examples:

    Jokic (over 25 points and over 10 rebounds) or over 15 assists
    Celtics (over 120 points and over 15 threes) or under 10 turnovers
    Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists

Not currently documented as supported for:

- player comparisons
- team comparisons

---

## Date and window support

The current repo includes support for date-aware natural query context.

Supported patterns currently present in the repo include:

- explicit season
- season range
- `last N games`
- `in <month>`
- `since <month>`
- `last <N> days`
- `since All-Star break`

Examples:

    nbatools-cli ask "top scorers in March"
    nbatools-cli ask "best offensive teams in March"
    nbatools-cli ask "teams with best efg% in March"
    nbatools-cli ask "best offensive teams since January"
    nbatools-cli ask "Jokic since All-Star break"
    nbatools-cli ask "best offensive teams since All-Star break"

Note:

These patterns are part of the current code surface. They should continue to be verified with focused tests/examples as the date-aware surface is hardened.

---

## Metrics

### Core box-score metrics

Current query/display support includes common box-score fields such as:

- points
- rebounds
- assists
- steals
- blocks
- threes made
- turnovers
- plus/minus
- minutes
- shooting splits

### Advanced shooting metrics

Current support includes:

- eFG%
- TS%

### Advanced player metrics

Current support includes:

- USG%
- AST%
- REB%

These appear in:

- player summaries
- player comparisons
- player split summaries
- pretty output
- raw structured output

These player rate metrics are recomputed from the filtered sample.

---

## Exports

Available on both natural and structured query paths:

- `--csv`
- `--txt`
- `--json`

Examples:

    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

---

## Pretty output

Current pretty output supports:

- summary headers
- comparison formatting
- split formatting
- section rules
- clearer metric labels
- advanced metric display:
  - eFG%
  - TS%
  - USG%
  - AST%
  - REB%

---

## Current tested-state snapshot

The repo currently documents:

- full suite: **206 passing tests**

Important distinction:

This document describes the current shipped surface and examples present in the repo.

Not every category above is necessarily described here as having the exact same level of test depth. When tightening or expanding a surface area, prefer to add targeted parser/smoke/unit coverage before broadening documentation claims.
