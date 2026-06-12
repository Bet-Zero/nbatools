# NBA Tools

NBA Tools is a natural-language NBA stats answer engine for stat-shaped questions across players, teams, records, splits, streaks, leaderboards, comparisons, and playoff history.

Ask a stat-shaped NBA question in plain English; get a direct, scoped answer backed by verified data. When a question falls outside the current supported boundary, the engine returns an explicit unsupported or no-result response instead of inventing an answer.

The same query engine is exposed through three surfaces: a public answer-first web UI, an HTTP API, and a CLI for development and power-user queries.

---

## What you can ask

The engine is tuned for stat-shaped NBA questions in the following areas. Each area has accepted phrasings documented in [docs/reference/query_catalog.md](docs/reference/query_catalog.md) and [docs/reference/query_guide.md](docs/reference/query_guide.md).

### Player summaries and recent form

    Jokic recent form
    Jokic summary vs Lakers
    Jokic career summary
    Jokic last 3 seasons

### Team summaries, records, and splits

    Celtics last 15 games summary
    Lakers record this season
    Lakers record vs Celtics
    Celtics wins vs losses
    Jokic home vs away in 2025-26

### Leaderboards

    top scorers this season
    highest ts% among players
    most 30 point games
    most games with 30+ points and 10+ rebounds
    best offensive teams
    teams with best efg%

### Comparisons and head-to-head

    Jokic vs Embiid recent form
    Jokic h2h vs Embiid
    Lakers head-to-head vs Celtics
    Kobe vs LeBron playoffs in 2008-09
    Celtics vs Bucks from 2021-22 to 2023-24

### Streaks

    Jokic longest streak of 30 point games
    Jokic 5 straight games with 20+ points
    longest Lakers winning streak
    Celtics 5 straight games scoring 120+

### Date-aware windows

    top scorers in March
    best offensive teams since January
    Jokic since All-Star break

### Game finders and boolean filters

    Jokic over 25 points and over 10 rebounds
    Jokic over 25 points or over 10 rebounds
    Jokic (over 25 points and over 10 rebounds) or over 15 assists

### Count queries

    how many games did Jokic score over 30 points
    how many Celtics wins this season

### Playoff history

    Lakers playoff history
    most finals appearances
    Lakers vs Celtics playoff history
    Lakers record by decade

---

## What is intentionally unsupported

The product has explicit boundaries. When a question falls outside them, the engine returns an explicit unsupported, no-result, or `filter_not_supported` response rather than a broad plausible answer.

- Subjective, opinion, or narrative questions (best defender, MVP candidate, clutch, cooled off, best player lately).
- Inference beyond available data, including invented metric definitions for terms the product has not approved.
- Query families that are still being evaluated against the promotion path (see [docs/operations/feature_promotion_rules.md](docs/operations/feature_promotion_rules.md)).
- Specific guarded families that are out of scope for the current release — for example personal-foul leaderboards, rookie leaderboards, league-wide starter/bench leaderboards, team bench scoring, opponent-conference history outside trusted current-era coverage, single-team playoff round records, multi-player availability, lineup summaries/leaderboards where trusted coverage is unavailable, on/off surfaces where trusted data is unavailable, team rolling-stretch leaderboards, minutes leaderboards, and team single-game threes. The durable supported and unsupported boundary lives in [docs/reference/query_catalog.md](docs/reference/query_catalog.md).

The working principle: forgive phrasing, do not invent meaning. No broad fallback answers for unsupported or low-confidence queries. See [docs/operations/parser_routing_growth_guardrails.md](docs/operations/parser_routing_growth_guardrails.md).

---

## Web UI quick start

The React frontend is served by FastAPI at `/`.

    nbatools-api              # http://127.0.0.1:8000

Public default at `/`: answer-first hero, scoped context chips, result table, freshness panel, query history, saved queries, and an explicit unsupported/no-result surface when a query falls outside the supported boundary.

Diagnostics surfaces (preserved, not removed):

- `/?debug=1` — restores route, query class, status, reason, JSON, and dev chrome for the same query.
- `/review` — debug-rich review page.
- `/visual-qa` — manual visual QA harness over the accepted baseline cases.

For frontend dev workflow, component reference, and hot-reload setup, see [docs/operations/ui_guide.md](docs/operations/ui_guide.md).

---

## Developer surfaces

### CLI — natural-language ask

    nbatools-cli ask "Jokic recent form"
    nbatools-cli ask "top scorers this season"
    nbatools-cli ask "Lakers playoff history"

Help:

    nbatools-cli --help
    nbatools-cli ask --help

### CLI — structured query

For full control over filters and windows, use the structured query interface:

    nbatools-cli query player-game-summary --player "Nikola Jokić" --season 2025-26 --last-n 10
    nbatools-cli query season-leaders --season 2025-26 --stat pts --limit 10 --min-games 20
    nbatools-cli query top-player-games --season 2005-06 --stat pts --limit 10
    nbatools-cli query player-game-finder --player "Kobe Bryant" --season 2005-06 --stat pts --min-value 40
    nbatools-cli query game-finder --team BOS --season 2025-26 --home-only --wins-only

Explicit CLI wrappers are convenience commands and may cover a focused subset of the structured surface. For full route coverage, list and execute the shared engine/API routes directly:

    nbatools-cli query routes
    nbatools-cli query routes --details
    nbatools-cli query route-help team_record
    nbatools-cli query route team_record --kwargs-json '{"team":"LAL","season":"2025-26"}'

30 structured engine/API routes are available through `GET /routes` and `nbatools-cli query routes`. Use `route-help` for route-specific kwargs guidance before calling the generic route executor.

### HTTP API

    nbatools-api              # http://127.0.0.1:8000

The same query engine is exposed over HTTP. The freshness endpoint returns a structured freshness report:

    GET /freshness

API layer details: [docs/architecture/api_layer.md](docs/architecture/api_layer.md).

### Exports

    nbatools-cli ask "Jokic recent form" --txt outputs/jokic_recent.txt
    nbatools-cli ask "top scorers in March" --csv outputs/top_scorers_march.csv
    nbatools-cli ask "Jokic vs Embiid recent form" --json outputs/jokic_embiid_recent.json

### Query classes (engine surface)

The engine supports these query classes:

- **finder** — games matching conditions
- **count** — count of matching games/occurrences
- **summary** — aggregated stats over a sample
- **comparison** — side-by-side stats for two entities
- **split** — home/away or wins/losses breakdowns
- **leaderboard** — ranked lists (season leaders, occurrence leaders, top games)
- **streak** — consecutive games meeting a condition
- **record** — team win-loss records with optional filters
- **playoff** — playoff history, appearances, round records, matchup history

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
- accent normalization (jokic → Jokić, doncic → Dončić)
- team name / abbreviation / nickname resolution
- ambiguity detection with confidence levels

### Stats and metrics

Common queryable stats: points, rebounds, assists, steals, blocks, threes made, turnovers, plus/minus, eFG%, TS%.

Player summaries, comparisons, and splits also show sample-aware USG%, AST%, REB%.

---

## QA and release status

Current release status: `RELEASE_CANDIDATE_WITH_NOTES` / `PREVIEW_READY_WITH_NOTES` / `FEEDBACK_READY_WITH_NOTES` / `PUBLIC_UI_READY_WITH_NOTES`.

Pointers:

- Verified shipped behavior: [docs/reference/current_state_guide.md](docs/reference/current_state_guide.md).
- Supported and explicitly unsupported query boundary: [docs/reference/query_catalog.md](docs/reference/query_catalog.md).
- Generated QA evidence scoreboard: [docs/operations/query_validation_map.md](docs/operations/query_validation_map.md).
- Parser/routing growth guardrails: [docs/operations/parser_routing_growth_guardrails.md](docs/operations/parser_routing_growth_guardrails.md).
- Feature promotion rules: [docs/operations/feature_promotion_rules.md](docs/operations/feature_promotion_rules.md).
- Query feedback review runbook (weekly beta cadence): [docs/operations/query_feedback_review.md](docs/operations/query_feedback_review.md).
- Docs index and category rules: [docs/index.md](docs/index.md).

### Current tested state

- Python pytest collection: **3,100+ test items** across 80 test files
- coverage spans parser, routing, result contracts, CLI smoke, API, query service, frontend contracts, Raw QA harness behavior, and specialized query areas

Run tests:

    make test
    nbatools-cli test

For release history, see [CHANGELOG.md](CHANGELOG.md).

---

## Data and deployment

### Refresh data

    # One-shot refresh of the current season
    nbatools-cli pipeline refresh

    # Automated repeating refresh
    nbatools-cli pipeline auto-refresh --interval 6h

### Pipeline stages

The pipeline orchestrates: raw data pulls → validation → feature builds → manifest update.

Individual stages are also available via CLI command groups:

- `nbatools-cli raw` — pull data from the NBA API
- `nbatools-cli processing` — build features from raw data
- `nbatools-cli ops` — backfill, inventory, manifest management

Pipeline runbook: [docs/operations/pipeline_runbook.md](docs/operations/pipeline_runbook.md).

### Freshness

    GET /freshness    # returns structured freshness report

The UI shows a collapsible freshness panel with status badge, current-through date, and per-season details.

### Deployment

Deployed runtime is Cloudflare R2 (data) + Vercel (frontend + API). Vercel excludes `data/**`, so any data-backed feature must verify R2 sync before preview/production. The deployment runbook contains the data-backed feature promotion checklist, the missing-data clean `no_data` behavior rule, and R2/Vercel setup details:

[docs/operations/deployment.md](docs/operations/deployment.md).

---

## Setup

Requirements:

- Python 3.11 or newer. CI covers Python 3.11, 3.12, and 3.13.
- Node 22 for frontend work (`.nvmrc`). The frontend lockfile also supports compatible Node 20.19+ and 24+ ranges, but CI uses Node 22.

    # Install in editable mode with dev dependencies
    pip install -e ".[dev]"

    # Install frontend dependencies
    cd frontend && npm install && cd ..

    # Build frontend for production
    cd frontend && npm run build
    # Output lands in src/nbatools/ui/dist/ and is served by FastAPI

    # Run tests
    make test

    # Frontend dev (hot reload) — two terminals:
    # Terminal 1: API server
    uvicorn nbatools.api:app --reload
    # Terminal 2: Vite dev server with proxy
    cd frontend && npm run dev
