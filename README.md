# NBA Tools

NBA Tools is a query-first NBA stats engine with a natural-language interface, a CLI, an HTTP API, and a React web UI.

It supports:

- player and team game finders
- player and team summaries
- player and team comparisons
- split summaries
- player and team season leaderboards
- matchup / head-to-head queries
- date-aware natural queries
- player and team streak queries
- CSV / TXT / JSON exports
- web UI for browser-based querying

---

## Quick Start

Natural-language query:

    nbatools-cli ask "Jokic recent form"

Structured query:

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10

Web UI:

    nbatools-api              # starts the API + serves the UI at http://127.0.0.1:8000

Run tests:

    pytest
    pytest -q

---

## What You Can Ask

### Leaderboards

    nbatools-cli ask "top scorers this season"
    nbatools-cli ask "highest ts% among players"
    nbatools-cli ask "most 30 point games"
    nbatools-cli ask "best offensive teams"
    nbatools-cli ask "teams with best efg%"
    nbatools-cli ask "teams with most threes"

### Matchups and head-to-head

    nbatools-cli ask "Jokic vs Lakers"
    nbatools-cli ask "Jokic summary vs Lakers"
    nbatools-cli ask "Jokic h2h vs Embiid"
    nbatools-cli ask "Lakers head-to-head vs Celtics"
    nbatools-cli ask "Celtics h2h vs Bucks home"

### Date-aware queries

    nbatools-cli ask "top scorers in March"
    nbatools-cli ask "best offensive teams since January"
    nbatools-cli ask "teams with best efg% in March"
    nbatools-cli ask "Jokic since All-Star break"
    nbatools-cli ask "best offensive teams since All-Star break"

### Streaks

    nbatools-cli ask "Jokic 5 straight games with 20+ points"
    nbatools-cli ask "Jokic longest streak of 30 point games"
    nbatools-cli ask "Jokic longest triple-double streak"
    nbatools-cli ask "longest Lakers winning streak"
    nbatools-cli ask "Celtics 5 straight games scoring 120+"
    nbatools-cli ask "longest Bucks streak with 15+ threes"

### Splits

    nbatools-cli ask "Jokic home vs away in 2025-26"
    nbatools-cli ask "Celtics wins vs losses"

### Boolean queries

    nbatools-cli ask "Jokic over 25 points and over 10 rebounds"
    nbatools-cli ask "Jokic over 30 points or over 12 assists"
    nbatools-cli ask "Jokic (over 25 points and over 10 rebounds) or over 15 assists"
    nbatools-cli ask "Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists"
    nbatools-cli ask "Celtics wins vs losses (over 120 points and over 15 threes) or under 10 turnovers"

---

## Current Capabilities

### Natural query routing

The natural query layer can route to:

- player game finder
- team game finder
- player summary
- team summary
- player comparison
- team comparison
- player split summary
- team split summary
- player season leaders
- team season leaders
- player streaks
- team streaks

### Filters and context

Supported natural query context includes:

- season
- season range
- last N games
- home / away
- wins / losses
- opponent filters
- head-to-head phrasing
- month windows (`in March`)
- open-ended month windows (`since January`)
- rolling date windows (`last 30 days`)
- `since All-Star break`

### Stats and metrics

Common queryable stats include:

- points
- rebounds
- assists
- steals
- blocks
- threes made
- turnovers
- plus/minus
- eFG%
- TS%

Player summaries, comparisons, and split summaries also show:

- USG%
- AST%
- REB%

These player rate metrics are recomputed from the filtered sample.

---

## Exports

Natural query exports:

    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

Structured query exports:

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --json outputs/player_summary.json

---

## Command Groups

Beyond `ask` and `query`, the CLI provides pipeline and analysis commands:

### `raw` — Pull data from the NBA API

    nbatools-cli raw pull-teams --season 2024-25
    nbatools-cli raw pull-player-game-stats --season 2024-25
    nbatools-cli raw pull-team-game-stats --season 2024-25
    nbatools-cli raw pull-schedule --season 2024-25
    nbatools-cli raw pull-rosters --season 2024-25
    nbatools-cli raw pull-standings-snapshots --season 2024-25
    nbatools-cli raw pull-games --season 2024-25
    nbatools-cli raw pull-team-season-advanced --season 2024-25
    nbatools-cli raw pull-player-season-advanced --season 2024-25

### `processing` — Build features from raw data

    nbatools-cli processing validate-raw --season 2024-25
    nbatools-cli processing build-team-game-features --season 2024-25
    nbatools-cli processing build-game-features --season 2024-25
    nbatools-cli processing build-player-game-features --season 2024-25
    nbatools-cli processing build-league-season-stats --season 2024-25
    nbatools-cli processing analyze-3pt-battles --season 2024-25

### `ops` — Pipeline operations

    nbatools-cli ops backfill-season --season 2024-25
    nbatools-cli ops backfill-range --start-season 2020-21 --end-season 2024-25
    nbatools-cli ops inventory --season 2024-25
    nbatools-cli ops show-team-history --team LAL
    nbatools-cli ops update-manifest
    nbatools-cli ops show-manifest

### `analysis` — Analysis commands

    nbatools-cli analysis battle-summary --season 2024-25

### Utility commands

    nbatools-cli version         # Show installed version
    nbatools-cli test            # Run the full test suite
    python -m nbatools version   # Also works as a module

---

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run tests
pytest

# Frontend dev (hot reload) — two terminals:
# Terminal 1: API server
uvicorn nbatools.api:app --reload
# Terminal 2: Vite dev server
cd frontend && npm run dev
# Open http://localhost:5173

# Build frontend for production
cd frontend && npm run build
# Output lands in src/nbatools/ui/dist/ and is served by the API

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Pre-commit hooks (after git init)
pre-commit install
```

---

## CI

GitHub Actions runs lint (ruff) and tests (pytest) on push and PR against `main`,
across Python 3.11, 3.12, and 3.13. See `.github/workflows/ci.yml`.

---

## Documentation

- `docs/index.md`
- `docs/quick_query_guide.md`
- `docs/current_state_guide.md`
- `docs/ui_guide.md`
- `QUERY_GUIDE.md`

---

## Current Tested State

- full suite: **206 passing tests**
- parser and CLI smoke coverage are green
- docs reflect the current shipped query surface

For release history, see `CHANGELOG.md`.
