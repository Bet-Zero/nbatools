# NBA Tools

NBA Tools is a natural-language NBA stats answer engine for stat-shaped questions across players, teams, records, splits, streaks, leaderboards, comparisons, and playoff history.

The goal: ask a stat-shaped NBA question in plain English and get a direct, correctly scoped answer backed by qualified data. Unsupported or unavailable conditions should be identified rather than silently replaced by a different question. Implementation and broader product acceptance are still in progress.

The same query engine is exposed through three surfaces: a public answer-first web UI, an HTTP API, and a CLI for development and power-user queries.

For agent execution, start with [AGENTS.md](AGENTS.md) and [ROADMAP.md](ROADMAP.md). The October 15 direction preserves the existing product, strengthens correctness and numerical acceptance, delivers shared interpretation, and establishes a bounded deployed-core checkpoint. This README is not the active execution queue or proof that every combination is verified.

---

## What you can ask

The engine is tuned for stat-shaped NBA questions in the following areas. Each area has examples and current limitations documented in [docs/reference/query_catalog.md](docs/reference/query_catalog.md) and [docs/reference/query_guide.md](docs/reference/query_guide.md). A listed family does not imply that every filter combination or source dataset is available.

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
    top scorers since January
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

## Current limitations and answer integrity

Subjective opinion/narrative questions and invented metric definitions are not statistical answers supplied by this engine. A genuinely ambiguous request needs clarification; an unavailable source or missing implementation must not produce a broader plausible answer.

Desired statistical capabilities that are not implemented or not backed by sufficient data remain unfinished work, not permanent product exclusions. The former static list of unsupported families is no longer maintained here because it included capabilities subsequently implemented. Consult the [query catalog](docs/reference/query_catalog.md), relevant [data contracts](docs/reference/data_contracts.md), and actual scoped verification for a particular request; do not infer every combination works from a family name.

Working historical scope is 1996-97 onward, with priority on the 21st century. Earlier history is optional. A career that begins before available coverage must be labeled with its covered span. Participation, injury/status, and simultaneous on-court presence are different facts; one cannot be silently substituted for another.

The working principle: forgive phrasing, do not invent meaning. No broad fallback answers for unsupported or low-confidence queries. See [parser/routing guardrails](docs/operations/parser_routing_growth_guardrails.md) and [feature promotion rules](docs/operations/feature_promotion_rules.md).

---

## Web UI quick start

The React frontend is served by FastAPI at `/`.

    nbatools-api              # http://127.0.0.1:8000

Public default at `/`: answer-first hero, scoped context chips, result table, freshness panel, query history, saved queries, and an explicit unsupported/no-result surface when a query falls outside the supported boundary.

The public page supports one request-scoped diagnostic mode:

- `/?debug=1` — restores route, query class, status, reason, JSON, and dev chrome for the same query.

The debug-rich `/review` page and the `/visual-qa` manual review harness are
local/preview operator surfaces. Production routing does not expose them; see
[deployment operations](docs/operations/deployment.md).

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

The [generated repository inventory](contracts/repository_inventory.json)
records the current structured-route count. `GET /routes` and
`nbatools-cli query routes` expose the live registered surface. Use
`route-help` for route-specific kwargs guidance before calling the generic
route executor.

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
- **comparison** — side-by-side stats for entities
- **split** — breakdowns over a selected sample
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

- curated player aliases and nicknames
- accent normalization (jokic → Jokić, doncic → Dončić)
- team name / abbreviation / nickname resolution
- ambiguity detection with confidence levels

### Stats and metrics

Common queryable stats: points, rebounds, assists, steals, blocks, threes made, turnovers, plus/minus, eFG%, TS%.

Player summaries, comparisons, and splits also show sample-aware USG%, AST%, REB%.

---

## QA and release status

Queue D was owner-accepted on 2026-07-21 for the then-documented product boundary
after the desktop/mobile review and final 17-check combined evidence run passed.
That historical decision is not broader product acceptance or verification of
subsequent changes. Manual feedback persistence remains deferred and disabled.
The October 15 Core-1 checkpoint is planned, not claimed complete.

Pointers:

- Verified shipped behavior: [docs/reference/current_state_guide.md](docs/reference/current_state_guide.md).
- Supported and explicitly unsupported query boundary: [docs/reference/query_catalog.md](docs/reference/query_catalog.md).
- Generated QA evidence scoreboard: [docs/operations/query_validation_map.md](docs/operations/query_validation_map.md).
- Parser/routing growth guardrails: [docs/operations/parser_routing_growth_guardrails.md](docs/operations/parser_routing_growth_guardrails.md).
- Feature promotion rules: [docs/operations/feature_promotion_rules.md](docs/operations/feature_promotion_rules.md).
- Deferred query-feedback review and activation runbook: [docs/operations/query_feedback_review.md](docs/operations/query_feedback_review.md).
- Queue D final acceptance receipt: [docs/audits/2026-07-21-queue-d-final-acceptance/README.md](docs/audits/2026-07-21-queue-d-final-acceptance/README.md).
- Docs index and category rules: [docs/index.md](docs/index.md).

### Current tested state

The test suite covers parser and routing behavior, result contracts, CLI and
API paths, the query service, frontend contracts, Raw QA harness behavior, and
specialized query areas. Use the test runner's collection output when an exact
current count is needed rather than freezing a volatile total into this guide.
A passing workflow or selected full suite does not establish that required
real-data tests executed; inspect the relevant executed/skipped results.

Run tests:

    make test
    nbatools-cli test

For release history, see [CHANGELOG.md](CHANGELOG.md).

---

## Data and deployment

### Refresh data

Fresh NBA acquisition and unattended refresh are parked under the October 4 owner
decision. Existing qualified-snapshot work may continue. These CLI capabilities
are not proof of an active scheduler and are not an instruction to operate the
owner's laptop as a data runner. Consult the runbook and current authorization
before refresh/publication.

    # One-shot refresh of the current season, when authorized/reachable
    nbatools-cli pipeline refresh

    # Repeating refresh command; not evidence an unattended runner is installed
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

The UI shows a collapsible freshness panel with status badge, current-through date, and per-season details. Snapshot coverage must not be advertised as unattended current data; metadata republication must preserve the underlying data's dates.

### Deployment

Deployed runtime is Cloudflare R2 (data) + Vercel (frontend + API). Vercel excludes `data/**`, so any data-backed feature must verify R2 availability before preview/production. The deployment runbook contains the data-backed feature promotion checklist, the missing-data clean `no_data` behavior rule, and R2/Vercel setup details:

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
