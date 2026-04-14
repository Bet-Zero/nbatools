# NBA Tools

NBA Tools is a query-first NBA stats engine with a natural-language interface, a CLI, an HTTP API, and a React web UI.

It powers three surfaces — a CLI for development and power-user queries, a FastAPI HTTP layer, and a React + TypeScript + Vite web UI — all backed by the same query engine.

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
    nbatools-cli ask "most 30 point game    nbanbatools-cli ask "most games with 30+ points and 10+ rebounds"
    nbatools-cli ask "best offensive teams"
    nbatools-cli ask "teams with best efg%"

### Date-aware queries

    nbatools-cli ask "top scorers in March"
    nbatools-cli ask "best offensive teams since January"
    nbatools-    nba "Jokic since All-Star    nbatools-    nls-cli ask "Jokic last 3 seasons"
    nbatools-    nba "Jokic since All-Sic longest streak of 30 point games"
    nbatools-cli a    nbatools-cli a    nbatools-cli a    nbatoba    nbatools-cli a    nbatools-cli a    nbak"
    nbatools-cli ask "Celtics 5 s    nbatools-cli ask "Celtics 5 s    nbatools-clioo    nbatools-cli ask "Celtics 5 s    nbat"
    nbatools-cli ask "Celtics wins vs losses"

### Records and playoff history

    nbatools-cli ask "Lakers record this season"
    nbatools-cli ask "Lakers record vs Celtics"
    nbatools-cli ask "best record this season"
    nbatools-cli ask "Lakers playoff history"
    nbatools-cli ask     nbatools-cli ask     nbatools-cli ask     nbatools-cli ask     nbatools-cli ask     nbatoos-cli ask "Laker    nbatools-cli ask     nbatools-cli ask       nbatools-cli ask     nbatools-cli ask nd     nbatools-cli ask  nb    nbatools-cli ask     nbatools-cli ask er 12 assists"
    nbatools-cli ask "Jokic (over 25 points and over 10 rebounds) or over 15 assists"

### Count queries

    nbatools-cli ask "how many games did Jokic score over 30 points"
    nbatools-cli ask "how many Celtics wins this season"

---

## Current Capabilities

### Query classes

The engine supports these query classes:

- **finder** — games matching conditions
- **count** — count of matching games/occurrences
- **summary** — aggregated stats- **summary** — aggregated stats- **summar-si- **summary** — aggregated ssplit** — home/away or wins/losses breakdowns
- **leaderboard** — ranked lists (season leaders, - **leaderboard** — ranked lists (season le�� consecutive games meeting a condition
- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **r, - **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **rec- **reon /- **rec- **rec-
- last N games / recent form
- home / away / wins / losses
- opponent / - opponent / - opponent / - opponent / - opponent / - o Ja- ary- opponent / - opponenws (last 30 days)
- since All-Star break
- career / all-time
- p- p- p- p- p- p- p- p- p- p- p- p- p- p- itions (over / under / between) with boolean chaining

### Entity resolution

- 90+ curated player aliases and nicknames
- accent normalization (jokic → Jokić, doncic → Dončić)
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


   nbatools-cli ask "Jokicon   nbatools-cli ask "JokicoI provides pipeline and analysis commands:

### `raw` — Pull data from the NBA API

    nbatools-cli raw pull-teams --season 2024-25
    nba    nba    nba    -p    nba    nba    nba    -p    nba    nba    nba    -p    nba    nba    nba    -p    nba    nba  nbatools-cli raw pull-schedule --season 2024-25
    nbatools-cli raw pull-rosters --season 2024-25
    nbatools-cli raw pull-standi    nbatools-cli raw pull-standi    nbatools-cl r    nbatools-cli raw pull-standi    nbatool-cli raw pull-team-season-    nbatools-cli raw pull-standi    nbatools-cli raw pull-standi    nbatools-cl r    nbatools-cli raw pull-st — Build features from raw data

    nbatools-cli processing validate-raw --season 2024-25
    nbatools-cli processing build-team-game-features --season 2024-25
    nbatools-cli processing build-game-features --season 2024-25
    nbatools-cli processing build-player-game-features --season 2024-25
    nbatools-cli processing build-league-season-stat    nbatools-cli processing build-leagucessing analyze-3pt-battles --season 2024-25

### `ops` — ### `ops` — ### `ops` — ### `ops` �ps backfill-season --season 2024-25
    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatools-cli    nbatoolsm LAL
    nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nba sho    nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nba sho    nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nba sho    nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nba sho    nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nba sho    nbatoo    nbatoo    nbatoo    nbatoo    nbaks     nbatoo    nbatoo    nbatoo    nbatoo    nbatoo    nbditable mode with dev dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run tests
pytest

# Frontend dev (hot reload) — two terminals:
# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Terminal 1:# Te Build frontend for production
cd frontend && npm run build
# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands iub# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands iub# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands in src/nbatools/u# Output lands iub# Output lands in src/nbes

---

## Current Tested State

- full suite: **1650 passing tests**
- coverage spans parser, routing, result contracts, CLI smoke, API, query service, and specialized query areas

For release history, see `CHANGELOG.md`.
