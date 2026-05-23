# Query Feedback + Diagnostic Logging Preflight Return Package

## 1. Executive summary

- Recommended decision: add a small feedback/diagnostic loop before broader
  release, but keep it outside query-engine behavior and corpus expectations.
- Best v1 architecture: `POST /query-feedback` backend endpoint plus
  backend-owned durable storage. The frontend should only submit validated
  feedback payloads and never write directly to a privileged store.
- Storage recommendation: Firestore is not present today. The lightest safe v1
  store in the current stack is Cloudflare R2 with immutable per-record JSON
  objects in a dedicated feedback bucket or clearly isolated feedback prefix.
  Use Firestore only after a prerequisite setup wave if console triage and
  mutable review statuses are more important than lowest deployment risk.
- Automatic logging recommendation: log only negative/diagnostic events in v1:
  no-result, unsupported/filter-not-supported, engine error/unrouted, API
  request failures, frontend network failures, and slow queries over a threshold.
  Do not log every successful query.
- User feedback recommendation: add a compact "Report issue" action for
  successful answers and a stronger "Expected this to work?" action on
  no-result/unsupported/error states. Keep `/visual-qa` suppressed; keep
  `/review` suppressed by default to avoid QA-sweep noise.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

## 2. Current query flow

| Layer | Finding | Best insertion point |
|---|---|---|
| Frontend submit | `frontend/src/App.tsx` owns the product query flow. `QueryBar` calls `handleSubmit`, sample/history/saved-query actions also call `runQuery`, and URL state can auto-run `?q=` on load. | Product user-submitted feedback should be wired from `App.tsx`, where the full `QueryResponse`, query text, share URL, and surface state are available. |
| Frontend API client | `frontend/src/api/client.ts` sends same-origin `POST /query` and throws only for non-OK HTTP responses or invalid response bodies. Engine-level `result_status: "error"` still returns as a normal `QueryResponse`. | Add `postQueryFeedback()` in the API client. Frontend network/API exceptions can be submitted through this endpoint when the endpoint itself is reachable. |
| Frontend result state | `App.tsx` stores successful HTTP payloads in `result`, stores HTTP/network failures in `error`, and records only compact in-session history via `useQueryHistory`. | Automatic frontend logging belongs immediately after `postQuery` resolves for negative `QueryResponse` statuses, and inside `catch` for network/API errors. It must be best-effort and never block query UX. |
| Result envelope | `frontend/src/components/ResultEnvelope.tsx` receives full `QueryResponse` and renders route, status, reason, current-through date, notes/caveats, alternates, metadata-derived context, and applied filters. | Best place for successful-answer "Report issue" affordance is the result actions area near Copy Link/Copy Query/Copy JSON/Save Query, not inside route-specific renderers. |
| Result body | `frontend/src/components/results/ResultRenderer.tsx` routes all result rendering. If sections are empty and status is `no_result` or `error`, it renders `NoResultDisplay`. | Best place for no-result/error feedback is either a `feedbackAction` prop passed into `NoResultDisplay` or a small feedback block directly below the no-result renderer in `ResultRenderer`, because `ResultRenderer` still has the full `QueryResponse`. |
| No-result UI | `frontend/src/components/NoResultDisplay.tsx` renders title/message/guidance/details from reason, status, metadata, notes, and caveats. It does not currently receive query, route, or the full envelope. | If the button is visually inside the no-result card, pass an action node or callback from `ResultRenderer`; do not make `NoResultDisplay` reconstruct diagnostics from partial props. |
| Internal review | `frontend/src/ReviewPage.tsx` loads parser fixtures, runs many `postQuery` calls on demand, caches results in `localStorage`, then renders `ResultEnvelope` and `ResultRenderer` in review mode. | Suppress feedback by default on `/review`. Optionally allow an internal-only manual flag later, but automatic logging during review sweeps would pollute real-user diagnostics. |
| Visual QA | `frontend/src/VisualQaPage.tsx` auto-runs 15 live `/query` cases and renders result cards for screenshot/manual QA. | Suppress feedback entirely on `/visual-qa`; visual QA already has its own checklist workflow and should not create product feedback records. |
| Local API | `src/nbatools/api.py` exposes FastAPI `POST /query`, calls `execute_natural_query`, then `query_result_to_payload`. | Add FastAPI `POST /query-feedback`. For automatic backend diagnostics, call a shared `maybe_log_query_diagnostic(payload, timing, source)` after payload generation and before returning, swallowing storage failures. |
| Vercel API | `api/query.py` handles `POST /query`, calls `src/nbatools/vercel_functions.py::query_response`, which validates and calls `src/nbatools/api_handlers.py::natural_query_payload`. | Add `api/query_feedback.py`, a rewrite in `vercel.json`, and shared validation/persistence helpers so local FastAPI and Vercel functions behave the same. |
| Query service | `src/nbatools/query_service.py` parses, routes, executes, and wraps typed results in `QueryResult`. Expected failures map to `no_result`; unrouted/internal failures can map to `error`. | Do not write diagnostics here. Keeping logging in the API layer avoids side effects for CLI/tests and keeps core query logic UI/transport agnostic. |
| Response shape | Top-level payload has `ok`, `query`, `route`, `result_status`, `result_reason`, `current_through`, `confidence`, `intent`, `alternates`, `notes`, `caveats`, and `result`. `result.metadata` includes `query_text`, `route`, `query_class`, entity/date/filter slots, `unsupported_filters`, `applied_filters`, and answer phrases when available. | Store a sanitized compact snapshot: route/status/reason, selected metadata, applied/unsupported filters, section keys and row counts, notes/caveats, elapsed ms, and a short rendered/answer preview. Do not store full raw result tables by default. |

Recommendation on automatic logging location:

- Backend-side should be primary for processed query diagnostics because it has
  authoritative route/status/reason/metadata and cannot be bypassed by frontend
  bugs.
- Frontend-side should supplement backend logging for browser-visible failures
  the backend cannot see, especially network errors, non-JSON responses, and
  user-submitted "wrong/confusing" reports.
- Both should submit through the same backend-owned persistence path and include
  a dedupe key/request ID when available.

## 3. Storage/persistence options

| Option | Exists today? | Pros | Cons | Recommendation |
|---|---|---|---|---|
| Firestore | No. No Firebase/Firestore package, config, client setup, server credentials, rules, or env vars were found. | Good console review, document querying, status updates, and eventual internal triage UI. | Requires new provider setup, Python dependency, service account secret handling, IAM/rules decisions, and Vercel env configuration. | Good v1.5/v2 store, or v1 only if a prerequisite storage/config wave is accepted. |
| Cloudflare R2 per-record JSON | Yes for infrastructure: `boto3`, R2 config, Vercel env pattern, and deployment docs exist for runtime data. Feedback-specific bucket/prefix does not yet exist. | Lowest new dependency risk; backend-only credentials already match deployed shape; easy preview/prod parity; immutable record writes avoid JSONL append races. | Weak ad hoc querying; review statuses are awkward without an export/update script; same data bucket would mix operational feedback with product data unless isolated. | Recommended lightest safe v1. Prefer a separate feedback bucket and scoped token; acceptable bridge is an isolated `query_feedback/` prefix with explicit docs. |
| Backend JSONL/file log | No durable app log abstraction exists. | Simple locally; easy append semantics. | Vercel/serverless filesystem is not durable; concurrent writes and deploy instance churn make it unreliable. | Do not use for deployed v1 except local dev fallback. |
| Browser `localStorage` | Exists for saved queries and review cache. | Zero backend work; private to a browser. | Not durable across users/devices, not reviewable centrally, and can be cleared. | Not suitable for feedback collection. |
| Vercel/platform logs | Exists implicitly, not app-modeled. | No app storage code. | Not structured for triage, retention/access depends on platform, cannot support user notes/statuses well. | Use only as secondary operational evidence, not the feedback store. |
| External form/issue collector | Not integrated. | Fastest operational fallback; no app persistence. | Loses route/status/metadata unless manually copied; worse QA-corpus conversion. | Acceptable emergency fallback only. |

Concrete v1 storage path if R2 is chosen:

- Add env vars such as `QUERY_FEEDBACK_STORE=r2`,
  `QUERY_FEEDBACK_BUCKET_NAME=nbatools-feedback` or an explicitly approved
  fallback to `R2_BUCKET_NAME`, and `QUERY_FEEDBACK_PREFIX=query_feedback`.
- Store one object per record:
  `query_feedback/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json`.
- Keep objects immutable in v1. Review/export scripts can derive CSV/Markdown
  and future triage status overlays can live in a separate file/store if needed.
- Use backend credentials only. Do not expose R2 or Firestore write credentials
  to the frontend.

## 4. Recommended feedback schema

| Field | Required? | Source | Notes |
|---|---|---|---|
| `id` | yes | backend | Server-generated UUID/ULID or timestamp plus random suffix. |
| `query` | yes | frontend/backend | Raw user query text. Keep because this is the product improvement input; cap length. |
| `query_normalized_hash` | yes | backend | Privacy-light dedupe key from normalized query plus route/status/reason. |
| `created_at` | yes | backend | UTC ISO timestamp. |
| `environment` | yes | backend/env | `local`, `preview`, or `production`; include Vercel deployment URL/commit if available. |
| `source_page` | yes | frontend | `/`, `/review`, `/visual-qa`, or path. v1 should accept only `/` for user-submitted product feedback. |
| `feedback_source` | yes | frontend/backend | `automatic` or `user_submitted`. |
| `feedback_type` | yes | frontend/backend | One of `wrong_answer`, `expected_supported`, `confusing_answer`, `no_result`, `unsupported`, `error`, `ui_issue`, `other`. |
| `user_note` | no | frontend | Optional, max length such as 1000 chars. UI copy should say not to include personal info. |
| `route` | no | response | Top-level `QueryResponse.route`. |
| `status` | yes | response/frontend | `result_status` or frontend request-error status. |
| `reason` | no | response/frontend | `result_reason` or client/API error class. |
| `result_shape` | no | frontend/backend | Compact shape only: query class, section keys, row counts, or frontend `classifyResultShape` key if submitted by UI. |
| `metadata` | no | response/backend | Sanitized allowlist from `result.metadata`; include parser slots, confidence, intent, current-through, notes/caveats summaries. Do not store full result rows by default. |
| `unsupported_filters` | no | response metadata | Useful for product-boundary triage. |
| `applied_filters` | no | response metadata | Useful to diagnose date/filter drops and misunderstood conditions. |
| `answer_text_preview` | no | frontend/backend | Short preview from `metadata.answer_phrase`, `metadata.count_phrase`, rendered summary text, or first visible heading. Cap length; no full table dump. |
| `error_message` | no | frontend/backend | Sanitized first-line error message; cap length and avoid tracebacks in user-visible paths. |
| `elapsed_ms` | no | backend/frontend | Backend query duration and/or frontend request duration. |
| `request_id` / `trace_id` | no initially; recommended | backend | Not present today. Add when implementing to connect automatic and user-submitted records. |
| `anonymous_session_id` | no | frontend | Optional random local ID, not derived from IP/device/email and resettable; avoid if not needed. |
| `review_status` | yes | backend default | Default `new`; later values: `reviewing`, `accepted_bug`, `accepted_support_candidate`, `expected_unsupported`, `duplicate`, `added_to_corpus`, `closed`. |
| `triage_decision` | no | reviewer/export | `raw_qa_case`, `frontend_copy_case`, `visual_qa_case`, `data_issue`, `parser_issue`, `unsupported_family`, `no_action`. |
| `linked_case_id` | no | reviewer/export | QA corpus case ID, issue ID, or duplicate ID. |
| `reviewer_notes` | no | reviewer/export | Internal-only notes from export/triage workflow. |
| `schema_version` | yes | backend | Start at `1` so records can evolve safely. |

Privacy defaults:

- Do not collect names, emails, user accounts, IP addresses, precise device
  fingerprints, or session replay.
- If anonymous sessions are added, use a random non-identifying ID stored
  locally, not a hash of IP/user agent.
- Store only compact metadata and previews. Do not store full raw JSON by
  default because result tables can be large and may accidentally expand the
  retention surface.

## 5. Automatic diagnostic logging policy

| Event | Log automatically? | Why | Notes |
|---|---|---|---|
| `result_status == "no_result"` | yes | Core signal for failed/unsupported/confusing real queries. | Include route, reason, metadata, unsupported/applied filters, section shape, and elapsed ms. |
| `result_reason == "filter_not_supported"` | yes | Direct product-boundary candidate signal. | High priority for future support triage. |
| `result_reason == "unsupported"` | yes | Identifies unsupported combinations and potential roadmap families. | Include `unsupported_filters` and notes/caveats. |
| `result_reason == "no_data"` | yes | Could indicate expected coverage gaps or deployment/R2 data gaps. | Include current-through and relevant season/date metadata. |
| `result_reason == "unrouted"` | yes | Parser/query-surface gap. | Usually `result_status: "error"` in current envelope. |
| `result_status == "error"` | yes | Could be parser, route, data, or server issue. | Store sanitized error message; avoid full stack traces in feedback records. |
| `unsupported_filters` present | yes | Explicit slot-level signal for unsupported features. | Log even if status is not otherwise diagnostic. |
| Fallback/fallback-table result | maybe | Could indicate weak rendering or unclassified shape. | Log only if route/shape is known to be diagnostic; avoid noisy success logs. |
| HTTP 422 validation error | yes | Indicates bad client payload or malformed request path. | Backend can log compact request validation failure without full body beyond query field. |
| HTTP 500 from query endpoint | yes | Operational issue. | Backend and frontend can both emit; dedupe by request ID when added. |
| Frontend network/non-JSON error | yes, frontend-submitted | Backend may never receive the request. | Best effort only; failure to report must not replace the user's visible error. |
| Slow query over threshold | yes | Release risk on Vercel functions and R2 cold starts. | Start threshold at 8s warning and 15s high-severity, below the 60s Vercel max duration. |
| Successful `ok` query | no | Too noisy and raises privacy/retention surface. | User-submitted reports on successful answers are enough for v1. |

Dedup/rate-limit recommendation:

- v1 should not block launch on perfect dedup.
- Add a `query_normalized_hash` and review-time duplicate grouping.
- Add frontend best-effort throttling for automatic client-side reports, such
  as one automatic report per normalized query/status/reason per browser session.
- If Firestore is chosen, automatic logs can use deterministic daily document
  IDs plus counters. If R2 is chosen, keep immutable objects and dedupe in the
  export script.

## 6. User-submitted feedback UX

| Surface | Proposed UX | Notes |
|---|---|---|
| Successful answer on `/` | Add a small "Report issue" action near result actions. Modal/popover fields: type radios/dropdown (`This answer looks wrong`, `This is confusing`, `UI issue`, `Other`), optional note, submit. | Keep it visually secondary to Copy/Save. Default `feedback_type` should be `wrong_answer`. |
| No-result/unsupported on `/` | Add "Expected this to work?" or "Submit for review" in/under the no-result card. Type defaults from status/reason: `no_result`, `unsupported`, or `expected_supported`; optional note. | This is the highest-value manual feedback path. |
| Engine error on `/` | Show "Report error" after automatic logging. Optional note only. | Do not ask users to copy JSON; the payload already has route/status/reason/metadata. |
| Frontend/network error on `/` | Add "Report error" inside `ErrorBox` when `/query-feedback` is available. | Since no `QueryResponse` exists, submit query text, error message, source page, and request timing. |
| `/review` | Suppress in v1. | Review sweeps run many fixtures and cache results; automatic/user feedback here would pollute real-user data. |
| `/visual-qa` | Suppress. | Visual QA already produces checklist artifacts and request-error counts. |

Suggested copy:

- Button on answers: `Report issue`
- Successful-answer form title: `Report an issue with this answer`
- Type labels: `This answer looks wrong`, `This is confusing`, `There is a UI issue`, `Other`
- No-result prompt: `Expected this to work?`
- No-result action: `Submit for review`
- Error action: `Report error`
- Note label: `Optional note`
- Privacy hint: `Do not include personal information.`
- Success message: `Thanks. This query was saved for review.`
- Failure message: `Could not submit the report. Your query result is unchanged.`

## 7. Review/triage workflow

- V1 review method: no admin dashboard. Store records, then review through R2
  object listing/export script or Firestore console if Firestore is selected.
  The lightest R2 workflow is a script that exports new feedback records to
  Markdown and CSV grouped by `feedback_type`, `route`, `reason`, and
  `query_normalized_hash`.
- Triage statuses: `new`, `reviewing`, `accepted_bug`,
  `accepted_support_candidate`, `expected_unsupported`, `duplicate`,
  `added_to_corpus`, `closed`.
- How feedback becomes QA cases:
  - `raw_qa_case`: backend/parser/query behavior is wrong or needs a new
    unsupported-boundary guard.
  - `frontend_copy_case`: backend result is correct but rendered wording or
    hero copy is confusing/wrong.
  - `visual_qa_case`: layout, overflow, density, or visual hierarchy issue.
  - `data_issue`: source data freshness, missing R2 object, verified outlier,
    or coverage problem.
  - `parser_issue`: unrouted, ambiguous, or slot extraction mismatch.
  - `unsupported_family`: valid product demand outside current boundary.
  - `no_action`: expected unsupported behavior or non-actionable report.
- Deferred admin UI: defer `/review-feedback` until record volume makes manual
  export painful. A full triage dashboard should not block v1.

## 8. Implementation options

| Option | Scope | Value | Risk | Recommendation |
|---|---|---|---|---|
| A - frontend-only Firestore write | Add Firebase client config, frontend write calls, Firestore rules. | Fast for a prototype if Firebase already existed. | Exposes client write surface, requires careful public rules, harder to trust payloads, no privileged credentials but more abuse surface. | Not recommended. Firestore is not present and backend endpoint is safer. |
| B - backend feedback endpoint + Firestore | Add `POST /query-feedback`, server validation, Firestore admin/server client, env secrets, collection schema. | Best long-term reviewability and mutable triage statuses. | New provider/dependency/secrets; setup work before preview/prod. | Recommended only if a prerequisite Firestore setup wave is accepted. |
| C - backend endpoint writes JSONL/file | Add endpoint and append locally. | Minimal code locally. | Not durable on Vercel; append races; poor preview/prod parity. | Do not use for deployed v1. |
| D - external issue collector/form | Add link or simple form outside app. | Fastest operational fallback. | Loses structured diagnostics and QA conversion value. | Emergency fallback only. |
| E - hybrid backend diagnostics + frontend user feedback endpoint | Backend auto-logs negative outcomes; frontend submits user reports and browser-visible failures through same endpoint; backend writes durable store. | Captures both machine diagnostics and user judgment without logging all successes. | Needs schema, validation, storage, and suppression rules for review/visual QA. | Recommended v1 architecture, with R2 per-record JSON as the lightest current store. |

## 9. Recommended execution scope

- Exact goal: implement v1 query-feedback capture without changing query
  behavior. Add a backend-owned `POST /query-feedback` endpoint, R2-backed
  immutable feedback storage, a minimal product-page feedback UI, and
  best-effort automatic logging for no-result/unsupported/error/slow-query
  outcomes.
- Files likely to change:
  - `src/nbatools/query_feedback.py` or `src/nbatools/feedback_store.py` for
    schema validation, privacy filtering, IDs, hashes, and storage.
  - `src/nbatools/api.py` for local FastAPI endpoint and backend automatic
    diagnostic hook.
  - `src/nbatools/vercel_functions.py` for shared Vercel request handling and
    automatic diagnostics.
  - `api/query_feedback.py` for the Vercel function.
  - `vercel.json` for `/query-feedback` rewrite/function config and env.
  - `frontend/src/api/types.ts` and `frontend/src/api/client.ts` for feedback
    payload types and `postQueryFeedback`.
  - New `frontend/src/components/QueryFeedback*` component files.
  - `frontend/src/App.tsx`, and possibly `ResultRenderer.tsx`,
    `NoResultDisplay.tsx`, and `ErrorBox.tsx` for insertion points.
  - `.env.example` and `docs/operations/deployment.md` for feedback storage
    env/config.
  - Optional `docs/operations/query_feedback_review.md` and
    `tools/export_query_feedback.py` for review/export workflow.
- Storage/env requirements:
  - R2 v1: `QUERY_FEEDBACK_STORE=r2`,
    `QUERY_FEEDBACK_BUCKET_NAME`, `QUERY_FEEDBACK_PREFIX`, and scoped
    credentials. Prefer separate feedback bucket/token; only use the current
    `R2_BUCKET_NAME` with explicit approval and isolated prefix.
  - Firestore alternative: project ID, collection name, server credentials
    secret, dependency choice, and Vercel env vars.
- Tests to add:
  - Python unit tests for payload validation, metadata sanitization, hash/id
    generation, store-disabled behavior, and R2 client writes with mocks.
  - API tests for FastAPI/Vercel feedback endpoint success and validation
    failures.
  - Query endpoint tests proving automatic no-result/error diagnostics are
    best-effort and do not alter `QueryResponse`.
  - Frontend API-client tests for `postQueryFeedback`.
  - Frontend component tests for answer feedback, no-result submit-for-review,
    error reporting, success/failure states, and `/review`/`/visual-qa`
    suppression.
  - Privacy test asserting disallowed fields such as email/IP/user account are
    not stored by the sanitizer.
- Docs to update:
  - `docs/operations/deployment.md` for feedback store env and preview/prod
    setup.
  - New or existing operations doc for feedback review/export.
  - Do not update query catalog/current-state docs unless actual query support
    changes later through a separate QA-backed wave.
- Validation commands:
  - Python/API: `make test-api`; use `make test-preflight` if API/shared
    handler changes become broad.
  - Frontend: `cd frontend && npm run test` or focused Vitest files, then
    `cd frontend && npm run build` after source changes.
  - Deployment: run deployment smoke plus manual `/`, no-result, and error
    report submissions against preview with feedback writes enabled.
- Stop conditions:
  - Durable store credentials are not available in preview/prod.
  - Feedback submission failure breaks query execution or visible result UX.
  - Client-side privileged storage credentials would be required.
  - Implementation needs to store user emails, IPs, or other PII.
  - Automatic logging would include all successful queries by default.

## 10. Privacy/security notes

- PII policy: do not collect names, emails, accounts, IP addresses, precise
  fingerprints, or session replay. User note copy should explicitly ask users
  not to include personal information.
- Retention recommendation: start with 90 days for raw feedback records unless
  converted into QA cases. Keep derived QA cases permanently in the existing QA
  corpus once reviewed.
- Abuse/rate-limit recommendation: validate payload sizes, cap note/query/error
  lengths, reject unknown enum values, suppress `/review` and `/visual-qa`,
  add client-side automatic-log throttling, and add backend/store-level dedupe
  grouping by `query_normalized_hash`.
- Access control: all writes go through backend endpoint. Frontend must not
  receive R2 or Firestore privileged credentials. If Firestore is selected,
  use server credentials only; do not rely on permissive client write rules.

## 11. Validation performed

Files inspected:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF_RETURN_PACKAGE.md`
- `frontend/src/App.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/hooks/useQueryHistory.ts`
- `frontend/src/hooks/useSavedQueries.ts`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/vite.config.ts`
- `frontend/package.json`
- `src/nbatools/query_service.py`
- `src/nbatools/api.py`
- `src/nbatools/api_handlers.py`
- `src/nbatools/vercel_functions.py`
- `src/nbatools/vercel_http.py`
- `src/nbatools/data_source.py`
- `api/index.py`
- `api/query.py`
- `api/structured_query.py`
- `api/dev/fixtures.py`
- `api/review.py`
- `vercel.json`
- `.env.example`
- `.gitignore`
- `pyproject.toml`
- `docs/operations/deployment.md`
- `docs/operations/ui_guide.md`
- `docs/planning/phase_n1_work_queue.md`
- `docs/planning/phase_n2_frontend_deployment_inventory.md`
- `docs/planning/production_deployment_plan.md`

Commands/probes run:

```bash
sed -n '1,220p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md
sed -n '1,240p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md
sed -n '1,240p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md
sed -n '1,260p' return_packages/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF_RETURN_PACKAGE.md
sed -n '1,260p' frontend/src/ReviewPage.tsx
sed -n '260,620p' frontend/src/ReviewPage.tsx
sed -n '1,260p' frontend/src/api/client.ts
sed -n '1,320p' frontend/src/api/types.ts
sed -n '1,260p' frontend/src/components/ResultEnvelope.tsx
sed -n '260,620p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,260p' frontend/src/components/results/ResultRenderer.tsx
sed -n '1,260p' frontend/src/components/NoResultDisplay.tsx
sed -n '1,620p' frontend/src/App.tsx
sed -n '1,280p' frontend/src/VisualQaPage.tsx
sed -n '280,620p' frontend/src/VisualQaPage.tsx
sed -n '1,180p' frontend/src/main.tsx
sed -n '1,180p' frontend/vite.config.ts
sed -n '1,260p' src/nbatools/query_service.py
sed -n '260,1420p' src/nbatools/query_service.py
sed -n '1,280p' src/nbatools/api.py
sed -n '1,300p' src/nbatools/api_handlers.py
sed -n '1,320p' src/nbatools/vercel_functions.py
sed -n '1,300p' src/nbatools/vercel_http.py
sed -n '1,260p' api/query.py
sed -n '1,280p' api/index.py
sed -n '1,220p' api/structured_query.py
sed -n '1,220p' api/dev/fixtures.py
sed -n '1,220p' api/review.py
sed -n '1,360p' src/nbatools/data_source.py
sed -n '1,260p' .env.example
sed -n '1,320p' docs/operations/deployment.md
sed -n '1,240p' vercel.json
sed -n '1,220p' pyproject.toml
sed -n '1,220p' frontend/package.json
sed -n '1,180p' docs/operations/ui_guide.md
rg -n "FastAPI|@app|post\(|/query|structured-query|dev/fixtures|freshness|health" src api frontend -g '*.py' -g '*.ts' -g '*.tsx'
rg -n "firebase|firestore|FIREBASE|Firestore|DATABASE|DB_|sqlite|postgres|supabase|upstash|redis|KV|analytics|telemetry|event|feedback|sentry|logfire|R2_|DATA_SOURCE|LOCAL_DATA_ROOT|NBATOOLS_|VERCEL|AWS_|CLOUDFLARE|SECRET" --glob '!node_modules/**' --glob '!frontend/dist/**' --glob '!src/nbatools/ui/dist/**' --glob '!data/**' --glob '!outputs/**' --glob '!docs/archive/**' --glob '!return_packages/**'
find . -maxdepth 3 -type f \( -iname '*firebase*' -o -iname '*firestore*' -o -iname '*supabase*' -o -iname '*analytics*' -o -iname '*sentry*' -o -iname '*feedback*' \) -not -path './node_modules/*' -not -path './.git/*'
find api -maxdepth 2 -type f -print
git status --short
git diff --stat
git diff --check
perl -ne 'print if /[ \t]$/' return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_PREFLIGHT_RETURN_PACKAGE.md
wc -l return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_PREFLIGHT_RETURN_PACKAGE.md
.venv/bin/python -c "from nbatools.api_handlers import natural_query_payload; import json; queries=['personal foul leaders this season','who won mvp this season','Jokic last 10 games'];
for q in queries:
 p=natural_query_payload(q); print(json.dumps({'query':q,'http_like':'payload','ok':p['ok'],'route':p['route'],'result_status':p['result_status'],'result_reason':p['result_reason'],'metadata_keys':sorted((p.get('result') or {}).get('metadata',{}).keys()),'section_keys':sorted((p.get('result') or {}).get('sections',{}).keys())}, default=str))"
```

Probe findings:

- `personal foul leaders this season` returned `route: season_leaders`,
  `ok: false`, `result_status: no_result`, and
  `result_reason: filter_not_supported`, with `unsupported_filters` available
  in metadata.
- `who won mvp this season` returned `route: null`, `ok: false`,
  `result_status: error`, and `result_reason: unrouted`.
- `Jokic last 10 games` returned `route: player_game_summary`, `ok: true`,
  `result_status: ok`, and sections `summary`, `by_season`, and `game_log`.

Notes:

- No tests were run because this was a preflight-only investigation.
- No production code, frontend rendering, backend query behavior, tests, corpus,
  schema, Firestore writes, admin dashboards, or storage config were changed.
- I did not inspect repo-root `.env` secret values; only `.env.example`,
  deployment docs, and code/config references were inspected.
