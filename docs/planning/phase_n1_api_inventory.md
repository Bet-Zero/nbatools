# Phase N1 API Inventory

> **Role:** Reconnaissance artifact for Phase N1 item 4. This records the
> current `src/nbatools/api.py` surface before the Vercel Functions refactor.

Measured from the primary local worktree on Python 3.13.2.

---

## Vercel Constraints Checked

- Vercel Python Functions can be plain `BaseHTTPRequestHandler` handlers or
  ASGI/WSGI apps under `/api`; each function file becomes a separate function.
  Reference: [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).
- Python functions use the project root as the current working directory for
  relative file reads, not the function file directory. This matches the
  repo's local data-source assumption when `DATA_SOURCE=local`.
- Python bundles have no automatic tree shaking and have a 500 MB uncompressed
  bundle limit. The current checkout has about 279 MB in `data/`, 168 MB in
  `frontend/`, and 8.8 MB in `tests/`, so production functions should use
  `excludeFiles` for non-runtime folders and rely on `DATA_SOURCE=r2` instead
  of bundling local data.
- For Python, `maxDuration` is configured under the `functions` object in
  `vercel.json`. Current Vercel docs list Fluid Compute as enabled by default
  with a 300s Hobby default, but the Phase N1 kickoff still requires flagging
  anything over the older 10s Hobby safety bar. References:
  [duration config](https://vercel.com/docs/functions/configuring-functions/duration)
  and [function limits](https://vercel.com/docs/functions/limitations).

---

## Current FastAPI Surface

`src/nbatools/api.py` creates a module-level `FastAPI` app with title
`nbatools API`, version `nbatools.__version__`, and a thin set of handlers over
`nbatools.query_service`.

### Middleware

| Middleware | Configuration | Notes |
| --- | --- | --- |
| `CORSMiddleware` | `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` | Current comment says local-only/no deployment. Safe enough for a preview, but item 5 should leave a clear production-tightening note or wire an allowed-origin env var. |

### Startup and Lifespan Hooks

None. There are no `@app.on_event("startup")`, lifespan managers, or eager
dataframe loads in `api.py`.

### Routes and Mounts

| Method | Path | Handler signature | Response model/class | Data dependency | Stateless? | Vercel mapping recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/` | `ui() -> HTMLResponse` | `HTMLResponse` | Reads `src/nbatools/ui/dist/index.html` if present, else returns fallback HTML string | Yes | Keep only in the local FastAPI dev app for now. Production frontend/static hosting should be Phase N2's concern. |
| `GET` | `/assets/index-fallback.js` | `ui_fallback_asset() -> Response` | `Response`, `application/javascript` | Inline fallback JS string | Yes | Keep local-only with `/`; not worth a separate production function. |
| mount | `/assets` | `StaticFiles(directory=str(_assets))` when UI dist assets exist | Static file mount | `src/nbatools/ui/dist/assets` | Yes | Use Vercel static/frontend output instead of a Python function. Do not route this through serverless Python. |
| `GET` | `/health` | `health() -> HealthResponse` | `HealthResponse` | None | Yes | Lightweight function: `api/health.py`, or a shared ASGI app route if item 5 chooses grouped functions. |
| `GET` | `/freshness` | `freshness() -> FreshnessResponse` | `FreshnessResponse` | `build_freshness_info()` reads manifest/game/refresh-log data through `nbatools.data_source` | Behavior is stateless; warm process caches can reduce repeated data reads | Function: `api/freshness.py`. Set `DATA_SOURCE=r2` in Vercel env. Timeout risk is moderate. |
| `GET` | `/routes` | `routes() -> RoutesResponse` | `RoutesResponse` | `VALID_ROUTES` constant from `query_service` | Yes | Lightweight function: `api/routes.py`, or grouped with `/health`. |
| `POST` | `/query` | `natural_query(body: NaturalQueryRequest) -> QueryResponse` | `QueryResponse` | Natural parser, entity resolution, command execution, CSV/R2 reads via data source | Request behavior is stateless, but warm module caches matter materially | Heavy function: `api/query.py`. This is the primary timeout target. |
| `POST` | `/structured-query` | `structured_query(body: StructuredQueryRequest) -> QueryResponse` | `QueryResponse` | Route-specific command execution, CSV/R2 reads via data source | Request behavior is stateless, but route cost varies | Heavy function: `api/structured_query.py`. Shares most risks with `/query`. |

---

## Request and Response Models

The API owns only transport envelope models:

- `NaturalQueryRequest`: `query: str`
- `StructuredQueryRequest`: `route: str`, `kwargs: dict[str, Any]`
- `QueryResponse`: stable query envelope with status, route, notes, caveats,
  metadata fields, and `result`
- `ErrorResponse`: declared but not currently used by route decorators
- `HealthResponse`, `RoutesResponse`
- `SeasonFreshnessResponse`, `FreshnessResponse`

These models should stay shared by both the local FastAPI shim and Vercel
handlers so CLI/API/UI contracts do not fork.

---

## Global State and Caches

`api.py` itself has only static constants and the FastAPI app object. The
runtime-relevant state lives in imported modules:

- `query_service._player_identity_lookup` and `_team_identity_lookup` are
  `@lru_cache(maxsize=1)` lookups populated lazily from roster/team CSVs.
- `commands.entity_resolution._player_last_name_index` is a module-level lazy
  cache.
- `commands.data_utils` has several `@cache` dataframe loaders keyed by season,
  season type, and `data_source_cache_key()`.
- `data_source._DATA_SOURCE` caches the selected source object per process.
  In R2 mode, downloaded object bytes are written to the temp cache directory
  but the in-process downloaded-key set is what avoids repeat downloads during
  that invocation.

Conclusion: the current API is function-safe because request semantics do not
depend on mutable global state. It is not cold-start-cheap; warm process reuse
currently hides meaningful data-load cost.

---

## Cold-Start Measurements

Methodology: each local-mode row is the median of three fresh Python processes
that imported `nbatools.api`, instantiated `TestClient`, and made exactly one
request. The R2 rows are one fresh-process smoke measurement each using live
Cloudflare R2 and `DATA_SOURCE=r2`. These are local development measurements,
not Vercel timings.

| Mode | Endpoint | Import ms | First request ms | Total ms | Result |
| --- | --- | ---: | ---: | ---: | --- |
| `local` | `GET /health` | 873.5 | 19.7 | 894.0 | `200` |
| `local` | `GET /freshness` | 828.5 | 45.4 | 879.5 | `200` |
| `local` | `POST /query` with `Jokic last 10` | 715.8 | 1194.3 | 1916.6 | `200`, `player_game_summary` |
| `local` | `POST /structured-query` with `player_game_summary` | 600.9 | 177.6 | 741.7 | `200` |
| `r2` | `GET /freshness` | 2709.6 | 4858.9 | 7569.8 | `200`, `current_through=2026-04-04` |
| `r2` | `POST /query` with `Jokic last 10` | 3210.5 | 27322.2 | 30533.1 | `200`, `player_game_summary` |

### Timeout Read

- Local mode is comfortably below the 10s safety bar.
- R2 `/freshness` is below 10s but close enough that it needs real preview
  validation.
- R2 `/query` exceeded 10s by a lot in a cold local process. It should be
  treated as timeout-prone until item 5 either raises `maxDuration` for query
  functions, reduces first-request R2 downloads, or both.

---

## Recommended Refactor Shape

1. Hoist transport-independent API helpers into `src/nbatools/api_handlers.py`
   or similar:
   - request validation/coercion helpers
   - `_query_result_to_response`
   - `health_payload`, `routes_payload`, `freshness_payload`
   - `natural_query_payload`, `structured_query_payload`
2. Keep Pydantic models in a shared import location, either the existing
   `src/nbatools/api.py` if it stays as a local shim or a new
   `src/nbatools/api_models.py`.
3. Leave `src/nbatools/api.py` as the local development FastAPI app that also
   serves the bundled UI and fallback asset.
4. Add Vercel function files for production JSON routes:
   - `api/health.py` -> `/health`
   - `api/routes.py` -> `/routes`
   - `api/freshness.py` -> `/freshness`
   - `api/query.py` -> `/query`
   - `api/structured_query.py` -> `/structured-query`
5. Use `vercel.json` rewrites to preserve the existing public paths and
   configure:
   - `excludeFiles` for `data/**`, `tests/**`, `frontend/**`, caches, and other
     non-runtime folders
   - `maxDuration` for query-class functions; use at least the old Hobby maximum
     if Fluid Compute is not guaranteed
   - `DATA_SOURCE=r2` as an environment expectation, with R2 credentials supplied
     in the Vercel dashboard

The one-file-per-route approach keeps the production handlers explicit while
the shared helper module prevents response-shape drift between local FastAPI
and Vercel.

---

## Risks for Item 5

- **R2 cold query time:** the live R2 `/query` smoke took about 30.5s. This is
  the highest-priority deployment risk.
- **Bundle size:** bundling `data/` plus `frontend/` plus dependencies may
  approach or exceed Python's 500 MB uncompressed limit. Production functions
  should exclude local data and non-runtime frontend/test folders.
- **Static UI serving:** current root and `/assets` behavior is local-dev
  convenience. Vercel should serve the frontend separately rather than through
  Python serverless handlers.
- **Wildcard CORS:** current middleware allows any origin. That is acceptable
  for local development; production should either scope it or document why the
  API is intentionally public.
- **Response size:** finder/game-log-heavy query results can be large. Vercel's
  function payload limit should be checked in preview for the largest known
  query responses.
