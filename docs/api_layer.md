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

### `GET /freshness`

Returns structured data freshness status — current_through, manifest state, per-season classification, and last refresh outcome.

**Response:**

```json
{
  "status": "fresh",
  "current_through": "2026-04-13",
  "checked_at": "2026-04-14T10:00:00",
  "seasons": [
    {
      "season": "2025-26",
      "season_type": "Regular Season",
      "status": "fresh",
      "current_through": "2026-04-13",
      "raw_complete": true,
      "processed_complete": true,
      "loaded_at": "2026-04-14T09:00:00"
    }
  ],
  "last_refresh_ok": true,
  "last_refresh_at": "2026-04-14T09:00:00",
  "last_refresh_error": null
}
```

**Status values:** `fresh`, `stale`, `unknown`, `failed`.

- **fresh**: manifest complete and current_through is within 3 days.
- **stale**: manifest complete but current_through is older than 3 days.
- **unknown**: manifest or games data missing — cannot determine freshness.
- **failed**: last refresh attempt recorded a failure.

## Response envelope

Every query response has the same top-level shape:

| Field             | Type        | Description                                                                                                         |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------------------------- |
| `ok`              | bool        | `true` if the query produced a real result                                                                          |
| `query`           | string      | Original query text or synthetic description                                                                        |
| `route`           | string/null | Resolved route name                                                                                                 |
| `result_status`   | string      | `"ok"`, `"no_result"`, or `"error"`                                                                                 |
| `result_reason`   | string/null | `"no_match"`, `"no_data"`, `"unrouted"`, `"ambiguous"`, `"unsupported"`, `"error"`, or `null` when status is `"ok"` |
| `current_through` | string/null | Latest game date covered by the data                                                                                |
| `notes`           | list[str]   | Semantic annotations                                                                                                |
| `caveats`         | list[str]   | Warnings or limitations                                                                                             |
| `result`          | dict        | Structured result from the query service                                                                            |

The `result` dict contains the output of `StructuredResult.to_dict()` — the same data the CLI renders, but as machine-readable JSON. The `result_reason` key is **always present** in `to_dict()` output (set to `null` for successful results).

### Reason → status mapping

Expected failures produce `result_status: "no_result"`:

| `result_reason` | Meaning |
| --------------- | ------- |
| `no_match`      | Data exists, filters matched nothing |
| `no_data`       | Season/type data file unavailable |
| `unsupported`   | Invalid filter combination, unsupported stat, or unknown route |
| `ambiguous`     | Entity resolution found multiple matches |

System-level failures produce `result_status: "error"`:

| `result_reason` | Meaning |
| --------------- | ------- |
| `unrouted`      | Query could not be parsed/routed |
| `error`         | Unexpected internal exception |

This mapping is enforced by `query_service.reason_to_status()`.

## Error responses

Invalid routes return a normal envelope with a structured `NoResult`:

```json
{
  "ok": false,
  "result_status": "no_result",
  "result_reason": "unsupported",
  "notes": ["Unknown route 'bad'. Valid routes: [...]"],
  "result": {
    "query_class": "no_result",
    "result_status": "no_result",
    "result_reason": "unsupported"
  }
}
```

Unsupported filter combinations (e.g. both `home_only` and `away_only`) also return a normal envelope with `result_reason: "unsupported"` and a descriptive note — they do not raise HTTP errors.

Unrouted natural queries return a normal envelope with `ok: false` and `result_status: "error"`.

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
- **Data freshness status** (`/freshness` endpoint — status, current_through, per-season details, last refresh outcome)

## What remains outside the API

- Data pipeline operations (pull, backfill, processing) — stays CLI-only
- Auto-refresh runner (`pipeline auto-refresh`) — stays CLI-only
- Analysis scripts
- Export to file (CSV/TXT/JSON export is a CLI concern)
- Authentication, deployment, background jobs
