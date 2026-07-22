# API Layer

The nbatools API is the HTTP transport layer over the query service. Public
query endpoints stay thin; the local FastAPI application also hosts explicitly
gated operator-only feedback-review endpoints for development workflows.

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
  "kwargs": { "season": "2025-26", "stat": "PTS", "limit": 10 }
}
```

**Response:** Same envelope shape as `/query`.

### Query request validation

The machine-readable route/method/body/CORS/error inventory is
`contracts/public_http_routes.json`. FastAPI, the Vercel function package, and
the Vite development proxy are checked against that one contract. Wrong-method
and malformed-body responses are correlated JSON errors in both HTTP
transports. CORS preflight success is HTTP 200 in FastAPI and HTTP 204 in the
Vercel adapters; that explicit status difference does not change the allowed
public surface.

`POST /query` and `POST /structured-query` use one shared strict request
contract in both FastAPI and the Vercel functions:

- request objects reject unknown top-level fields instead of ignoring them
- `query` must be a non-blank string of at most 500 characters
- `route` must be a non-blank string of at most 64 characters
- `kwargs` must be a non-null JSON object when provided
- known structured routes reject missing, unknown, internal-only, and
  wrong-type kwargs before command execution; values are not type-coerced
- validation failures return HTTP 422 with
  `{ "ok": false, "error": "validation_error", "detail": "...", "request_id": "req_<opaque-id>" }`;
  the same ID is returned in `X-Request-ID`

The public admission contract is enforced before execution in both transports:

- whole-body limits: 4 KiB `/query`; 8 KiB `/structured-query`; 8 KiB
  `/query-feedback`
- aggregate JSON limits: depth 4 below the root request object, 64 object
  members, and 20 array elements
- season span: at most 30 resolved seasons; the complete supported 1996-97
  through 2025-26 range remains valid
- natural and structured queries share three execution slots, ten admitted
  requests per client/IP per rolling minute, and a 20-second response budget
- feedback accepts at most 20 newly stored submissions per client/IP per rolling
  24 hours if the deferred capability is activated; user retries reuse a UUID
  submission receipt and conditional write

Rate and concurrency rejections use HTTP `429` JSON plus `Retry-After`; timeout
uses HTTP `504`. Query clients do not retry automatically. These application
counters are per running process/serverless instance and are defense-in-depth,
not a substitute for equivalent global edge enforcement.

`POST /query-feedback` remains a fail-closed compatibility surface, but the
current public UI exposes no submission control and deployed persistence is
disabled. No automatic public query diagnostics are stored. Future activation
requires the separate privacy and deployment contract; it is not a current
release requirement.

### Authentication and local admin feedback

The contracted public routes—including query, freshness/readiness, and the
disabled feedback compatibility endpoint—do not implement user-account
authentication. CORS, request budgets, rate limits, and request IDs are
transport safeguards, not authentication; any platform or edge access policy
is a deployment responsibility.

Feedback review is a separate, local-only operator surface:

- the FastAPI development server can serve the `/admin/feedback` UI shell and
  `/api/admin/feedback/*` data endpoints; the public Vercel package has no
  functions or rewrites for them
- the data endpoints return `404 admin_feedback_disabled` unless
  `NBATOOLS_ADMIN_FEEDBACK_ENABLED` is true
- when `NBATOOLS_ADMIN_TOKEN` is configured, every admin data request must
  supply the same value in `X-NBATools-Admin-Token`; an enabled deployed
  FastAPI environment fails closed when the token is not configured
- local development may omit the token only after explicitly enabling the
  operator surface; the UI shell itself grants no feedback-data access
- the admin handlers read immutable feedback records and write only separate
  triage-overlay objects. They do not alter query execution or rewrite source
  feedback records

The authoritative route-placement boundary is
`contracts/public_http_routes.json`; operational enablement and storage rules
are documented in
[`query_feedback_review.md`](../operations/query_feedback_review.md).

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

### `GET /readiness`

Returns the strict schedule-aware deployment gate. Ready responses use HTTP
`200`; every blocker or unknown state uses HTTP `503`. The payload names the
season state, pinned runtime generation, required-slice evidence, the 24-hour
active-season lag budget, any blockers, and any narrowly scoped owner exception.

## Response envelope

Every query response has the same top-level shape:

| Field             | Type        | Description                                                                                                         |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------------------------- |
| `ok`              | bool        | `true` if the query produced a real result                                                                          |
| `query`           | string      | Original query text or synthetic description                                                                        |
| `route`           | string/null | Resolved route name                                                                                                 |
| `result_status`   | string      | `"ok"`, `"no_result"`, or `"error"`                                                                                 |
| `result_reason`   | string/null | Canonical reason code documented below, or `null` when status is `"ok"`                                                    |
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
| `filter_not_supported` | Parsed filter cannot be applied safely to the selected route or data |
| `ambiguous`     | Entity resolution found multiple matches |
| `ambiguous_query` | Recognized query has multiple valid intents |

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

Unexpected HTTP-layer failures use the same fail-closed public contract in
FastAPI and the Vercel adapters:

```json
{
  "ok": false,
  "error": "internal_error",
  "detail": "The request could not be completed. Try again later.",
  "request_id": "req_<opaque-id>"
}
```

The response also carries the same opaque ID in `X-Request-ID`. Internal
exception messages, paths, provider details, object keys, request bodies, and
raw query text are never copied into that public response. Server-side error
events contain only allowlisted correlation fields: event name, request ID,
route template, HTTP status, stable error code, and exception class. Validation
failures may retain the repository-owned actionable validation detail; raw
unexpected exception text may not.

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

Query business logic remains outside the API layer. The API owns transport
validation, admission limits, request correlation and operational outcomes,
the local admin-feedback gate, query-service calls, and response
serialization.

## What is now UI-callable

- Natural-language queries (any query the CLI `ask` command supports)
- All registered structured routes (summaries, comparisons, finders, streaks,
  leaderboards, records, playoff, occurrence, on/off, lineup, by-decade)
- Route discovery
- Health checks
- **Data freshness status** (`/freshness` endpoint — status, current_through, per-season details, last refresh outcome)
- **Release readiness status** (`/readiness` endpoint — schedule state, immutable generation, blockers, exception receipt)

## What remains outside the API

- Data pipeline operations (pull, backfill, processing) — stays CLI-only
- Auto-refresh runner (`pipeline auto-refresh`) — stays CLI-only
- Analysis scripts
- Export to file (CSV/TXT/JSON export is a CLI concern)
- Public user-account authentication and platform/edge access control
- Deployment and background jobs
