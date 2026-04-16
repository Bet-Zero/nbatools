# NBA Tools

NBA Tools is a query-first NBA stats engine with a natural-language interface, a CLI, an HTTP API, and a React web UI.

It powers three surfaces -- a CLI for development and power-user queries, a FastAPI HTTP layer, and a React + TypeScript + Vite web UI -- all backed by the same query engine.

---

## Quick Start

Natural-language query:

    nbatools-cli ask "Jokic recent form"

Structured query:

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10

Web UI:

    nbatools-api              # starts the API + serves the UI at http://127.0.0.1:8000

Run tests:

    make test

---

## What You Can Ask

### Summaries and recent form

    nbatools-cli ask "Jokic recent form"
    nbatools-cli ask "Celtics last 15 games summary"
    nbatools-cli ask "Jokic summary vs Lakers"
    nbatools-cli ask "Jokic career summary"

### Comparisons and head-to-head

    nbatools-cli ask "Jokic vs Embiid recent form"
    nbatools-cli ask "Jokic h2h vs Embiid"
    nbatools-cli ask "Lakers head-to-head vs Celtics"
    nbatools-cli ask "Kobe vs LeBron playoffs in 2008-09"
    nbatools-cli ask "Celtics vs Bucks from 2021-22 to 2023-24"

### Leaderboards

    nbatools-cli ask "top scorers this season"
    nbatools-cli ask "highest ts% among players"
    nbatools-cli ask "most 30 point games"
    nbatools-cli ask "most games with 30+ points and 10+ rebounds"
    nbatools-cli ask "best offensive teams"
    nbatools-cli ask "teams with best efg%"

### Streaks

    nbatools-cli ask "Jokic longest streak of 30 point games"
    nbatools-cli ask "Jokic 5 straight games with 20+ points"
    nbatools-cli ask "longest Lakers winning streak"
    nbatools-cli ask "Celtics 5 straight games scoring 120+"

### Splits

    nbatools-cli ask "Jokic home vs away in 2025-26"
    nbatools-cli ask "Jokic home away split last 20 games"
    nbatools-cli ask "Celtics wins vs losses"

### Date-aware queries

    nbatools-cli ask "top scorers in March"
    nbatools-cli ask "best offensive teams since January"
    nbatools-cli ask "Jokic since All-Star break"
    nbatools-cli ask "Jokic last 3 seasons"

### Game finders and boolean filters

    nbatools-cli ask "Jokic over 25 points and over 10 rebounds"
    nbatools-cli ask "Jokic over 25 points or over 10 rebounds"
    nbatools-cli ask "Jokic (over 25 points and over 10 rebounds) or over 15 assists"

### Count queries

    nbatools-cli ask "how many games did Jokic score over 30 points"
    nbatools-cli ask "how many Celtics wins this season"

### Records and playoff history

    nbatools-cli ask "Lakers record this season"
    nbatools-cli ask "Lakers record vs Celtics"
    nbatools-cli ask "best record this season"
    nbatools-cli ask "Lakers playoff history"
    nbatools-cli ask "most finals appearances"
    nbatools-cli ask "Lakers vs Celtics playoff history"
    nbatools-cli ask "Lakers record by decade"

---

## Current Capabilities

### Query classes

The engine supports these query classes:

- **finder** -- games matching conditions
- **count** -- count of matching games/occurrences
- **summary** -- aggregated stats over a sample
- **comparison** -- side-by-side stats for two entities
- **split** -- home/away or wins/losses breakdowns
- **leaderboard** -- ranked lists (season leaders, occurrence leaders, top games)
- **streak** -- consecutive games meeting a condition
- **record** -- team win-loss records with optional filters
- **playoff** -- playoff history, appearances, round records, matchup history

### Filters and windows

- season / season range / last N seasons
- last N games / recent form
- home / away / wins / losses
- opponent / head-to-head
- month / since month / last 30 days
- since All-Star break
- career / all-time
- playoffs
- threshold conditions (over / under / between) with boolean chaining (and / or / parentheses)

### Entity resolution

- 90+ curated player aliases and nicknames
- accent normalization (jokic -> Jokić, doncic -> Dončić)
- team name / abbreviation / nickname resolution
- ambiguity detection with confidence levels

### Stats and metrics

Common queryable stats: points, rebounds, assists, steals, blocks, threes made, turnovers, plus/minus, eFG%, TS%.

Player summaries, comparisons, and splits also show sample-aware USG%, AST%, REB%.

---

## Exports

    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

---

## Web UI

The React frontend is served by FastAPI at `/`.

    nbatools-api              # http://127.0.0.1:8000

Features: query bar, sample query buttons, result tables for all query classes, raw JSON toggle, query history, saved queries, freshness status panel, and a Dev Tools panel for structured queries.

For development with hot reload, see `docs/ui_guide.md`.

---

## Data Pipeline

### Refresh data

    # One-shot refresh of the current season
    nbatools-cli pipeline refresh

    # Automated repeating refresh
    nbatools-cli pipeline auto-refresh --interval 6h

### Pipeline stages

The pipeline orchestrates: raw data pulls -> validation -> feature builds -> manifest update.

Individual stages are also available via CLI command groups:

- `nbatools-cli raw` -- pull data from the NBA API
- `nbatools-cli processing` -- build features from raw data
- `nbatools-cli ops` -- backfill, inventory, manifest management

### Freshness

    GET /freshness    # returns structured freshness report

The UI shows a collapsible freshness panel with status badge, current-through date, and per-season details.

---

## Structured CLI Queries

For full control, use the structured query interface:

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10
    nbatools-cli query season-leaders --season 2025-26 --stat pts --limit 10 --min-games 20
    nbatools-cli query top-player-games --season 2005-06 --stat pts --limit 10
    nbatools-cli query player-game-finder --player "Kobe Bryant" --season 2005-06 --stat pts --min-value 40
    nbatools-cli query game-finder --team BOS --season 2025-26 --home-only --wins-only

26 structured routes are available. Run `nbatools-cli query --help` for the full list.

---

## Setup

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Build frontend for production
cd frontend && npm run build
# Output lands in src/nbatools/ui/dist/ and is served by FastAPI

# Run tests
make test

# Frontend dev (hot reload) -- two terminals:
# Terminal 1: API server
uvicorn nbatools.api:app --reload
# Terminal 2: Vite dev server with proxy
cd frontend && npm run dev
```

---

## Current Tested State

- full suite: ~**1,684 test functions** across 42 test files
- coverage spans parser, routing, result contracts, CLI smoke, API, query service, and specialized query areas

For release history, see `CHANGELOG.md`.
