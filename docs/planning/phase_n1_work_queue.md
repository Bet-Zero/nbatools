# Phase N1 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase N1 of
> [`production_deployment_plan.md`](./production_deployment_plan.md) —
> _Backend refactor for Vercel + R2 data sync._
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit. Repeat. When every item above is
> checked, work the final meta-task.

---

## Status legend

- `[ ]` — not started
- `[~]` — in progress
- `[x]` — complete and merged
- `[-]` — skipped (with inline note explaining why)

---

## 1. `[ ]` Sign up for Cloudflare R2 and provision the data bucket

**Why:** Before any code can sync to R2, the bucket needs to exist and the
developer needs API credentials. This is a one-time setup item that gates
everything else.

**Scope:**

- Sign up for Cloudflare account if needed (free)
- Create an R2 bucket named `nbatools-data` (or document an alternative
  name)
- Create an R2 API token with read/write to that bucket only
- Document the credentials securely in the developer's environment (1Password
  or equivalent — never commit to repo)
- Verify upload works from the developer's machine using `aws s3` CLI with R2
  endpoint, or `rclone`, or any S3-compatible tool
- Document the bucket name, endpoint URL, and credential names in
  `docs/operations/deployment.md` (new file)

**Files likely touched:**

- `docs/operations/deployment.md` (new)
- `.env.example` — add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` placeholders

**Acceptance criteria:**

- R2 bucket exists and is empty
- API token has correct scope (read/write to the one bucket only)
- Developer can upload a test file via CLI and download it back
- Credentials are documented in `.env.example` as placeholders
- Setup is documented in `deployment.md` so it's reproducible

**Tests to run:**

- None (configuration only)

**Reference docs:**

- [Cloudflare R2 docs](https://developers.cloudflare.com/r2/)
- [Cloudflare R2 S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/)

---

## 2. `[ ]` Add `pipeline sync-r2` CLI command

**Why:** This is the first half of the hybrid data sync — the developer-side
push. It takes the local `data/` directory (or whichever subset is needed for
production) and uploads it to R2.

**Scope:**

- Add a new CLI subcommand: `nbatools-cli pipeline sync-r2`
- The command reads R2 credentials from environment variables
- It walks the data directory and uploads files to R2 with matching paths
- It uses content hashing (e.g., comparing local md5 to R2's etag) to skip
  files that haven't changed — incremental syncs should be fast
- Shows a progress indicator (file count, bytes uploaded)
- Reports a summary at the end (X files synced, Y skipped, Z bytes uploaded)
- Handles common errors (network failure, auth failure, missing creds) with
  clear messages
- Has a `--dry-run` flag that shows what would be uploaded without actually
  uploading

**Files likely touched:**

- `src/nbatools/cli_apps/pipeline_app.py` — register new command
- `src/nbatools/commands/sync_r2.py` (new) — implementation
- `tests/test_sync_r2.py` (new) — unit tests with mocked R2 client
- `pyproject.toml` — add `boto3` dependency (S3-compatible client works for R2)

**Acceptance criteria:**

- `nbatools-cli pipeline sync-r2 --dry-run` prints what would be uploaded
- `nbatools-cli pipeline sync-r2` actually uploads to R2
- Re-running the command immediately after re-syncing skips all unchanged
  files (incremental works)
- Errors produce clear messages, not stack traces
- Unit tests cover: success path, partial failure, credential missing, dry-run
- The R2 bucket contains a verifiable copy of the data directory after a
  successful sync

**Tests to run:**

- `make test-impacted`
- Manual: `nbatools-cli pipeline sync-r2 --dry-run` then full sync

**Reference docs:**

- Item 1's `deployment.md` for credential setup
- AGENTS.md "Command-layer rule" — keep CLI thin, real logic in `commands/`

---

## 3. `[ ]` Add R2-backed data loader to the engine

**Why:** Second half of the hybrid sync — the production-read side. The
deployed app needs to read from R2 instead of the local filesystem.

**Scope:**

- Add a new data-loading module that fetches files from R2 on demand
- Use a configurable abstraction: a `DATA_SOURCE` env var that's either
  `local` (filesystem, current behavior) or `r2` (cloud)
- Local mode is unchanged — developer experience continues to work as today
- R2 mode reads from R2 lazily and caches in-memory or to a local temp dir
  for the lifetime of the function invocation
- Handle the case where R2 is unreachable: clear error message, no silent
  fallback to stale data
- The abstraction is consumed by whatever currently reads from the data
  directory (probably one or two main entry points in the engine)

**Files likely touched:**

- `src/nbatools/data_source.py` (new) — abstraction layer
- `src/nbatools/commands/` — wherever data loading currently happens, route
  through the new abstraction
- `tests/test_data_source.py` (new) — unit tests for both modes

**Acceptance criteria:**

- `DATA_SOURCE=local` (default) preserves current behavior exactly — no test
  regressions
- `DATA_SOURCE=r2` reads data from R2 successfully
- Switching modes is purely an env-var change, no code change
- R2-mode handles unavailability with a clear error, not silent degradation
- Unit tests cover both modes
- All existing tests still pass with `DATA_SOURCE=local`

**Tests to run:**

- `make test-impacted`
- `make test-engine`
- Manual: run the API locally with `DATA_SOURCE=r2` and verify queries return
  the same results as `DATA_SOURCE=local`

**Reference docs:**

- AGENTS.md "Working style" — preserve existing behavior unless task requires
  change

---

## 4. `[ ]` Reconnaissance: audit FastAPI app for Vercel Functions refactor

**Why:** Before refactoring, we need to know what we're refactoring. Vercel
Functions are stateless function handlers, not a long-running server. The
current `nbatools.api` likely has app-startup code, shared state, route
decorators, and middleware that need to be reorganized.

**Scope:**

- Walk through `src/nbatools/api.py` and document:
  - Every route, its method, its handler signature
  - All FastAPI middleware in use
  - All app-startup hooks
  - Any global state (dataframes loaded once, caches, etc.)
- Document:
  - Which routes are stateless (easy to convert)
  - Which routes depend on shared in-memory state (need rethinking)
  - Cold-start cost: how long does it take to load the data and respond to
    a first request?
- Produce an inventory in `docs/planning/phase_n1_api_inventory.md`
- Recommend an approach: which routes become individual functions, which can
  share a function file, what shared utilities can be hoisted to module
  level

**Files likely touched:**

- `docs/planning/phase_n1_api_inventory.md` (new)
- No code changes — reconnaissance only

**Acceptance criteria:**

- Inventory documents every route in the current API
- Cold-start cost is measured and documented
- A concrete refactor approach is recommended with clear file-by-file
  mapping
- Risks (timeout-prone routes, state-dependent routes) are flagged

**Tests to run:**

- None (reconnaissance only)

**Reference docs:**

- `src/nbatools/api.py` — current state
- [Vercel Python Functions docs](https://vercel.com/docs/functions/runtimes/python)

---

## 5. `[ ]` Refactor API to Vercel Functions structure

**Why:** Convert the FastAPI long-running server into Vercel-compatible
function handlers. Use the inventory from item 4 as the punchlist.

**Scope:**

- Create `api/` directory in repo root (Vercel convention) with one Python
  file per route or logical route group
- Each function file exports a handler that Vercel can invoke
- Shared imports and utilities live in a module that all handlers import
  from (kept in `src/nbatools/` for consistency with existing layout)
- Data loading uses the abstraction from item 3 — handlers configure
  `DATA_SOURCE=r2` from env vars in production
- Local development workflow still works: `nbatools-api` (or equivalent)
  still starts a local server for development, even though production runs
  via Vercel Functions
- Add a `vercel.json` configuration file with route mappings, function
  config (memory, max duration), and env var declarations

**Files likely touched:**

- `api/` directory (new) — one file per route group
- `src/nbatools/api.py` — may shrink significantly or become a local-dev-only
  shim
- `vercel.json` (new)
- `pyproject.toml` — Vercel function dependencies
- `tests/test_api.py` — adapt to test handler functions directly, not via
  FastAPI test client (or keep the client and have it route to the new
  handlers)

**Acceptance criteria:**

- Every route from item 4's inventory has a corresponding function handler
- Local development still works: developer can run the API locally with
  hot reload
- All existing API tests pass against the refactored handlers
- `vercel.json` correctly maps URLs to function files
- Cold-start cost is measured for the refactored functions; if any handler
  exceeds the 10s free-tier timeout, it's flagged for follow-up

**Tests to run:**

- `make test-api`
- `make test-impacted`
- Manual: run the local dev server, exercise each route via curl or browser

**Reference docs:**

- Item 4's inventory
- [Vercel Python Functions](https://vercel.com/docs/functions/runtimes/python)
- AGENTS.md "Frontend-layer rule" — keep frontend a thin presentation layer;
  the refactor must not push business logic into the frontend

---

## 6. `[ ]` Verify deployed-mode works end-to-end against R2

**Why:** Before declaring the backend ready for Part 2, verify that the
combination of (Vercel Functions + R2 data source + production env vars)
actually works. This is the integration test for items 1-5.

**Scope:**

- Deploy the refactored backend to Vercel (preview deployment, not
  production yet)
- Set environment variables in Vercel: R2 credentials, `DATA_SOURCE=r2`
- Sync data to R2 using `pipeline sync-r2`
- Hit several representative API endpoints against the preview deployment:
  - A simple query (`/query` with `Jokic last 10`)
  - A leaderboard query
  - A complex multi-filter query
  - The `/freshness` endpoint
- Measure cold-start time and warm response time for each
- Document results in `phase_n1_e2e_results.md`

**Files likely touched:**

- `docs/planning/phase_n1_e2e_results.md` (new)
- Possibly `vercel.json` if config tweaks are needed
- Possibly handler files if any failed

**Acceptance criteria:**

- Preview deployment is reachable
- All 4+ test queries return the same results as local mode
- Cold-start time is documented; if any route exceeds 5s cold-start, it's
  flagged
- No timeouts, no errors, no auth failures
- Results document is committed

**Tests to run:**

- Manual end-to-end testing against the preview URL

**Reference docs:**

- Vercel deployment docs
- Item 1's R2 setup

---

## 7. `[ ]` Phase N1 retrospective and Phase N2 handoff

**Why:** Self-propagating final task. Captures learnings and drafts the next
queue.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals
- Document any issues that should be remembered (e.g., "this Vercel quirk
  bit us, watch for it again in Phase N2")
- Draft `phase_n2_work_queue.md` with concrete items for frontend deployment
  - custom domain + production cutover
- Update `production_deployment_plan.md` if any scope adjustments are
  needed based on N1 learnings

**Files likely touched:**

- `docs/planning/phase_n1_work_queue.md` — check this item, add retrospective
- `docs/planning/phase_n2_work_queue.md` (new)
- `docs/planning/production_deployment_plan.md` (if scope change)

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, residuals
- `phase_n2_work_queue.md` exists with concrete items
- The final item of N2 drafts N3
- This item is checked off

**Tests to run:**

- None (docs only)

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase N1 is complete. The draft of
`phase_n2_work_queue.md` from item 7 is the handoff artifact.

If any item is skipped (`[-]`), note the reason inline so the reason
survives in git history.
