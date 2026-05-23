# Query Feedback + Diagnostic Logging V1 Return Package

## 1. Executive summary

- What changed: added backend-owned query feedback capture, R2-backed storage
  plumbing, best-effort negative-event diagnostics, product-page feedback UI,
  source-page suppression, tests, and operations docs.
- Production query behavior changed? no.
- Parser behavior changed? no.
- Frontend rendering changed? yes; product `/` now has compact feedback actions.
- Storage implemented: R2 per-record immutable JSON writer with disabled mode
  when feedback env is absent.
- Automatic logging implemented: backend negative diagnostics plus frontend
  browser-visible `/query` request failures.
- User feedback UI implemented: successful-answer `Report issue` and
  no-result/error `Submit for review` / `Report error`.
- Preview/prod env required: `QUERY_FEEDBACK_STORE=r2`,
  `QUERY_FEEDBACK_BUCKET_NAME`, `QUERY_FEEDBACK_PREFIX`, and R2 credentials.
- Remaining risk: no admin dashboard, no full rate limiting/dedupe beyond hash,
  and live R2 object smoke was not run because local validation used disabled
  mode plus mocked R2 writes.

## 2. Architecture

| Layer | Implementation | Notes |
|---|---|---|
| Backend schema/store | `src/nbatools/query_feedback.py` | Validates, sanitizes, hashes, builds records, writes R2 JSON, supports disabled mode. |
| Local API | `POST /query-feedback` in `src/nbatools/api.py` | Returns JSON for success, disabled, validation, and storage failure. |
| Vercel API | `api/query_feedback.py` + `vercel.json` rewrite | Shares the same handler path as local API. |
| Backend diagnostics | `maybe_log_query_diagnostic()` after `/query` payload generation | Best effort; failures are swallowed before returning query payloads. |
| Frontend client | `postQueryFeedback()` in `frontend/src/api/client.ts` | Same-origin JSON POST; no storage credentials in frontend. |
| Frontend UI | `QueryFeedbackButton` and payload helpers | Product page only; review/visual QA do not pass feedback actions. |

## 3. Feedback schema

| Field | Stored? | Notes |
|---|---|---|
| `id`, `created_at`, `schema_version` | yes | Backend generated; `schema_version=1`. |
| `feedback_source`, `feedback_type` | yes | Restricted to allowed v1 enums. |
| `query`, `query_normalized_hash` | yes | Query capped at 500 chars; hash groups duplicates. |
| `source_page`, `environment`, `deployment` | yes | Compact source/deploy context only. |
| `route`, `status`, `reason` | yes | Compact result envelope fields. |
| `result_shape` | yes | Section keys and row counts only; no rows. |
| `metadata` | yes | Allowlisted compact metadata only. |
| `notes`, `caveats`, `user_note` | yes | Capped summaries and optional user note. |
| `answer_text_preview`, `error_message`, `elapsed_ms` | yes | Capped diagnostic previews. |
| `review_status`, `triage_decision` | yes | Defaults to `new` and `null`. |
| PII-like fields / raw result tables | no | Explicitly dropped by sanitizer. |

## 4. Automatic logging policy

| Event | Logged? | Notes |
|---|---|---|
| `result_status == no_result` | yes | Backend best effort. |
| `result_status == error` | yes | Backend best effort. |
| `filter_not_supported`, `unsupported`, `no_data`, `unrouted` | yes | Backend best effort. |
| `unsupported_filters` present | yes | Backend best effort. |
| Slow query over 8000ms | yes | Logged as diagnostic `other`. |
| Successful `ok` query | no | Not logged unless slow/diagnostic. |
| `/review` and `/visual-qa` | no | Suppressed by source-page header/presentation path. |
| Frontend network/non-JSON `/query` failure | yes | Frontend best effort through `/query-feedback`. |

## 5. User feedback UX

| Surface | Behavior | Notes |
|---|---|---|
| Successful answer on `/` | `Report issue` action opens feedback dialog. | Types: wrong, confusing, UI issue, other. |
| No-result/unsupported on `/` | `Submit for review` action inside no-result display. | Defaults from result status/reason. |
| Error result on `/` | `Report error` action. | Query result remains unchanged if feedback fails. |
| `/review` | Hidden. | No feedback action passed into result renderer. |
| `/visual-qa` | Hidden. | Uses same no-feedback rendering path. |

## 6. Storage/deployment config

- Store: Cloudflare R2 per-record JSON.
- Bucket/prefix: default `nbatools-feedback` / `query_feedback`.
- Required env: `QUERY_FEEDBACK_STORE=r2`, `QUERY_FEEDBACK_BUCKET_NAME`,
  `QUERY_FEEDBACK_PREFIX`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`.
- Disabled behavior: unset/empty feedback store returns JSON with
  `ok: true`, `stored: false`, `disabled: true`.
- Privacy/retention: no intentional names, emails, IPs, accounts, phones,
  device fingerprints, or session replay; recommend 90-day raw retention unless
  converted into QA/product artifacts.

## 7. Tests and validation

- Python tests: `.venv/bin/pytest tests/test_query_feedback.py -q` passed
  `11 passed`.
- API tests: `.venv/bin/pytest tests/test_api.py -q` passed `41 passed`.
- Vercel handler tests: `.venv/bin/pytest tests/test_vercel_functions.py -q`
  passed `11 passed`.
- Ruff: `.venv/bin/ruff check ...` passed.
- Frontend tests:
  `npm test -- src/test/QueryFeedback.test.tsx src/test/client.test.ts`
  passed `19 passed`.
- Frontend lint: `npm run lint` passed with the existing
  `ReviewPage.tsx` `react-hooks/exhaustive-deps` warning.
- Frontend build: `npm run build` passed with the existing Vite large-chunk
  warning.
- R2/mock storage validation: mocked R2 `put_object` test passed.
- Manual local feedback smoke: disabled-mode endpoint returned 200 JSON with
  `stored: false`, `disabled: true` for successful, no-result, and simulated
  frontend-error payloads.
- Git static check: `git diff --check` passed.

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/query_feedback.py` | added | Feedback schema, sanitizer, R2 store, automatic diagnostics. |
| `src/nbatools/api.py` | updated | Local `/query-feedback` endpoint and `/query` diagnostic hook. |
| `src/nbatools/vercel_functions.py` | updated | Shared Vercel feedback and diagnostic handlers. |
| `src/nbatools/vercel_http.py` | updated | CORS allows source-page header. |
| `api/query.py` | updated | Pass source-page header into diagnostics. |
| `api/query_feedback.py` | added | Vercel `/query-feedback` function. |
| `vercel.json` | updated | Function config and rewrite for `/query-feedback`. |
| `frontend/src/api/types.ts` | updated | Feedback payload/response types. |
| `frontend/src/api/client.ts` | updated | Source-page header and `postQueryFeedback()`. |
| `frontend/src/App.tsx` | updated | Product feedback actions and frontend error diagnostic logging. |
| `frontend/src/components/QueryFeedback.tsx` | added | Compact feedback dialog/action. |
| `frontend/src/components/QueryFeedback.module.css` | added | Feedback dialog styles. |
| `frontend/src/components/queryFeedbackPayload.ts` | added | Frontend compact payload builders. |
| `frontend/src/components/NoResultDisplay.*` | updated | Optional feedback action slot. |
| `frontend/src/components/results/ResultRenderer.tsx` | updated | Passes optional no-result/error feedback action. |
| `tests/test_query_feedback.py` | added | Backend schema/store/API/diagnostic tests. |
| `tests/test_vercel_functions.py` | updated | Vercel feedback handler coverage. |
| `frontend/src/test/QueryFeedback.test.tsx` | added | Feedback UI tests. |
| `frontend/src/test/client.test.ts` | updated | Feedback client/source header tests. |
| `frontend/src/test/AppTheming.test.tsx` | updated | API-client mock includes feedback function. |
| `frontend/src/test/FirstRun.test.tsx` | updated | API-client mock includes feedback function. |
| `.env.example` | updated | Feedback env documentation. |
| `docs/operations/deployment.md` | updated | Feedback deployment/privacy config. |
| `docs/operations/query_feedback_review.md` | added | Review/export/triage runbook. |
| `docs/index.md` | updated | Added new operations doc. |

## 9. Current limitations

- No admin dashboard yet.
- R2 immutable records need export/review workflow.
- No full dedupe/rate limiting yet beyond `query_normalized_hash`.
- Feedback should not be interpreted as QA pass/fail until triaged.
- Live R2 object creation was not smoke-tested in this local pass.

## 10. Next recommendation

Preview feedback smoke test with `QUERY_FEEDBACK_STORE=r2` enabled against a
dedicated feedback bucket, then add an export/triage script once records exist.
