# API Layer

The nbatools API is a thin local HTTP layer over the query service.
It is the first UI-facing backend surface — not the final UI.

## Running

```bash
# Via CLI
nbatools-cli serve
nbatools-cli serve --port 9000 --reload

# Via standalone script
nbatools-api
nbatools-api --port 9000 --reload

# Via uvicorn directly
uvicorn nbatools.api:app --reload
```

The server binds to `127.0.0.1:8000` by default.

## Endpoints

### `GET /health`

Lightweight health check.

```json
{ "status": "ok", "version": "0.7.0" }
```

### `GET /routes`

Lists all supported structured query routes.

```json
{ "routes": ["game_finder", "game_summary", "player_compare", ...] }
```

### `POST /query`

Execute a natural-language NBA query.

**Request:**

```json
{ "query": "Jokic last 10 games" }
```

**Response:**

```json
{
  "ok": true,
  "query": "Jokic last 10 games",
  "route": "player_game_summary",
  "result_status": "ok",
  "result_reason": null,
  "current_through": "2026-04-10",
  "notes": [],
  "caveats": [],
  "result": {
    "query_class": "summary",
    "result_status": "ok",
    "metadata": { ... },
    "sections": {
      "summary": [ { "PTS": 28.5, "AST": 10.2, ... } ]
    }
  }
}
```

### `POST /structured-query`

Execute a structured (route-based) query.

**Request:**

```json
{
  "route": "season_leaders",
  "kwargs": { "season": "2025-26", "stat": "PTS", "top_n": 10 }
}
```

**Response:** Same envelope shape as `/query`.

## Response envelope

Every query response has the same top-level shape:

| Field             | Type        | Description                                   |
| ----------------- | ----------- | --------------------------------------------- |
| `ok`              | bool        | `true` if the query produced a real result    |
| `query`           | string      | Original query text or synthetic description  |
| `route`           | string/null | Resolved route name                           |
| `result_status`   | string      | `"ok"`, `"no_result"`, or `"error"`           |
| `result_reason`   | string/null | `"no_match"`, `"no_data"`, `"unrouted"`, etc. |
| `current_through` | string/null | Latest game date covered by the data          |
| `notes`           | list[str]   | Semantic annotations                          |
| `caveats`         | list[str]   | Warnings or limitations                       |
| `result`          | dict        | Structured result from the query service      |

The `result` dict contains the output of `StructuredResult.to_dict()` — the same data the CLI renders, but as machine-readable JSON.

## Error responses

Invalid routes return:

```json
{
  "ok": false,
  "error": "invalid_route",
  "detail": "Unknown route 'bad'. Valid routes: [...]"
}
```

Unrouted natural queries return a normal envelope with `ok: false` and `result_status: "no_result"`.

## Architecture

```
 HTTP Client / React UI
         │
    ┌────▼─────┐
    │  FastAPI  │   src/nbatools/api.py
    │  (thin)   │
    └────┬─────┘
         │
    ┌────▼──────────────┐
    │  query_service.py │   execute_natural_query / execute_structured_query
    └────┬──────────────┘
         │
    ┌────▼──────────────┐
    │  commands/*        │   build_result functions, structured results
    └───────────────────┘
```

The API layer contains no business logic. It validates input, calls the query service, and serializes the result.

## What is now UI-callable

- Natural-language queries (any query the CLI `ask` command supports)
- All 25 structured routes (summaries, comparisons, finders, streaks, leaderboards, records, playoff, occurrence, by-decade)
- Route discovery
- Health checks

## What remains outside the API

- Data pipeline operations (pull, backfill, processing)
- Analysis scripts
- Export to file (CSV/TXT/JSON export is a CLI concern)
- Authentication, deployment, background jobs
