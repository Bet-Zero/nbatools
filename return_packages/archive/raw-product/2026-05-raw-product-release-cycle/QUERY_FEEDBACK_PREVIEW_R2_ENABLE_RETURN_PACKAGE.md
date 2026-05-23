# Query Feedback Preview R2 Enable Return Package

## 1. Executive summary

- Preview URL: `https://nbatools-7kmhos2kn-brents-projects-686e97fc.vercel.app`
- Feedback readiness status: `BLOCKED`
- Env configured: Preview now has `QUERY_FEEDBACK_STORE`, `QUERY_FEEDBACK_BUCKET_NAME`, and `QUERY_FEEDBACK_PREFIX`; existing `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY` remain server-side Vercel env vars only.
- Direct endpoint: `PASS` for HTTP/API behavior; `POST /query-feedback` returned HTTP 200 JSON with `ok=true`, `stored=true`, `disabled=false`, and `feedback_id=qfb_20260518T040352495924Z_97fbf1fa`.
- Successful-answer feedback: `PASS` for UI/API behavior; submitted from the product page and returned HTTP 200 with `stored=true`, `disabled=false`, and `feedback_id=qfb_20260518T040941362163Z_87d312ad`.
- No-result feedback: `PASS` for UI/API behavior; submitted from the no-result card and returned HTTP 200 with `stored=true`, `disabled=false`, and `feedback_id=qfb_20260518T040943421608Z_5207620a`.
- Automatic diagnostics: `PARTIAL`; no-result and unrouted queries rendered normally, but automatic R2 objects cannot be verified without direct R2 read/list access because `/query` does not return diagnostic record IDs.
- R2 record inspection: `BLOCKED`; read-only R2 list/get escalation was rejected by the execution environment after endpoint writes succeeded.
- Suppression checks: `PASS`; `/review` first-10 sweep and `/visual-qa` 15-case sweep produced zero `/query-feedback` requests and no product feedback buttons.
- Blocking issues: live R2 object existence/content/sanitization inspection was not completed; automatic diagnostic object creation cannot be independently verified.
- Non-blocking notes: dedicated `nbatools-feedback` bucket was not reachable with the existing R2 token (`403`), so Preview was configured to use the existing R2 bucket with isolated prefix `query_feedback/preview`; no admin dashboard; no full rate limiting/dedupe beyond hash; immutable R2 records still need an export/review workflow.
- Recommended next step: run or approve one read-only R2 list/get under `query_feedback/preview` to inspect the direct, user-submitted, and automatic records; if records match the v1 sanitizer, reclassify as `FEEDBACK_READY_WITH_NOTES`.

## 2. Environment/storage validation

| Check | Result | Evidence |
|---|---|---|
| Dedicated feedback bucket availability | Not available | `nbatools-feedback` returned R2 `403` with the current token; `nbatools-data` was reachable. |
| Preview feedback env configured | Pass | `npx vercel env list preview --format json` listed `QUERY_FEEDBACK_STORE`, `QUERY_FEEDBACK_BUCKET_NAME`, and `QUERY_FEEDBACK_PREFIX` with target `preview`. |
| R2 credentials remain server-side | Pass | Vercel env list shows `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY` as Vercel env vars; no frontend-exposed R2 env vars were added. |
| Production env untouched for feedback | Pass | `npx vercel env list production --format json` did not list `QUERY_FEEDBACK_*` variables. |
| Preview deployment created | Pass | URL `https://nbatools-7kmhos2kn-brents-projects-686e97fc.vercel.app`; deployment id `dpl_9txAzH2A8VpK5Zy2F3pFpKvNgQcH`; target `preview`; status `Ready`; created May 18, 2026 00:01:34 EDT. |
| Health endpoint | Pass | `GET /health` returned `{"status":"ok","version":"0.7.0"}`. |
| Frontend R2 credential exposure | Pass | Downloaded preview HTML, JS, and CSS; search found no `R2_`, `QUERY_FEEDBACK`, `ACCESS_KEY`, `SECRET`, `cloudflarestorage`, `nbatools-data`, or `nbatools-feedback` strings. |
| Direct R2 object inspection | Blocked | Read-only R2 list/get escalation was rejected by the execution environment, so object key/content length/last modified were not verified. |

## 3. Direct endpoint validation

| Request | Expected | Actual | Verdict |
|---|---|---|---|
| `POST /query-feedback` with safe user-submitted smoke payload | HTTP 200 JSON, `ok=true`, `stored=true`, `disabled=false`, `feedback_id` present | HTTP 200 JSON: `ok=true`, `feedback_id=qfb_20260518T040352495924Z_97fbf1fa`, `stored=true`, `disabled=false` | Pass for endpoint/storage write response |

## 4. User feedback validation

| Surface | Query | Expected | Actual | Verdict |
|---|---|---|---|---|
| Successful-answer feedback | `Who leads the NBA in points per game this season?` | Query remains visible/unchanged; `Report issue` submission succeeds; R2 object created | Query returned HTTP 200, `route=season_leaders`, `result_status=ok`; UI submitted `Other` with the safe note; `/query-feedback` returned HTTP 200, `stored=true`, `disabled=false`, `feedback_id=qfb_20260518T040941362163Z_87d312ad`; query result remained visible | Pass for UI/API; R2 content inspection blocked |
| No-result feedback | `players with most personal fouls this season` | No-result card remains visible/unchanged; `Submit for review` succeeds; R2 object created | Query returned HTTP 200, `route=season_leaders`, `result_status=no_result`, `result_reason=filter_not_supported`, `unsupported_filters=["personal_foul_leaderboard"]`; `/query-feedback` returned HTTP 200, `stored=true`, `disabled=false`, `feedback_id=qfb_20260518T040943421608Z_5207620a`; no-result feedback action remained visible | Pass for UI/API; R2 content inspection blocked |

## 5. Automatic logging validation

| Query/event | Expected | Actual | Verdict |
|---|---|---|---|
| `players with most personal fouls this season` | Query UX remains normal; automatic diagnostic object created with unsupported/no-result metadata | Query returned HTTP 200, `route=season_leaders`, `result_status=no_result`, `result_reason=filter_not_supported`, `unsupported_filters=["personal_foul_leaderboard"]`; no manual feedback was submitted for this run | Partial; UX pass, automatic R2 object not directly verified |
| `who won mvp this season` | Query UX remains normal; automatic diagnostic object created with error/unrouted metadata | Query returned HTTP 200, `route=null`, `result_status=error`, `result_reason=unrouted`; no manual feedback was submitted | Partial; UX pass, automatic R2 object not directly verified |

## 6. R2 record inspection

| Record type | Object key | Sanitization verdict | Notes |
|---|---|---|---|
| Direct endpoint record | Not verified | Blocked | Endpoint returned `stored=true`, but direct R2 list/get was blocked before object key, content length, last modified, and JSON fields could be inspected. |
| Successful-answer user record | Not verified | Blocked | UI/API write returned `stored=true`; live record fields such as `feedback_source`, `feedback_type`, `schema_version`, `review_status`, and sanitized `result_shape` were not directly inspected. |
| No-result user record | Not verified | Blocked | UI/API write returned `stored=true`; live record fields such as `reason`, `unsupported_filters`, and lack of raw tables/PII were not directly inspected. |
| Automatic diagnostic record | Not verified | Blocked | `/query` responses matched automatic logging conditions, but `/query` does not expose diagnostic IDs and direct R2 inspection was blocked. |

## 7. Suppression validation

| Surface | Expected | Actual | Verdict |
|---|---|---|---|
| `/review` | No feedback buttons; review sweep creates no `/query-feedback` noise | Headless browser found `feedbackButtons=0`; running `Run first 10` produced ten `/query` HTTP 200 responses and `queryFeedbackRequests=0` | Pass |
| `/visual-qa` | No feedback buttons; visual QA completes 15 cases; no `/query-feedback` noise | Headless browser found `feedbackButtons=0`; `/visual-qa` reached `15 / 15 cases completed`; all 15 `/query` responses were HTTP 200; `queryFeedbackRequests=0` | Pass |

## 8. Issues found

| Priority | Issue | Blocking? | Recommended action |
|---|---|---|---|
| P0 | Live R2 object inspection was not completed. | Yes | Run/approve read-only R2 list/get for `query_feedback/preview` and inspect at least one direct, one user-submitted successful-answer, one user-submitted no-result, and one automatic diagnostic record. |
| P0 | Automatic diagnostic object creation cannot be independently verified from HTTP responses alone. | Yes | Inspect R2 records created by the no-result and unrouted `/query` requests, grouped by `feedback_source=automatic` and `query_normalized_hash`. |
| P1 | Dedicated `nbatools-feedback` bucket is not reachable with the existing token. | No for Preview fallback; yes for dedicated-bucket preference | Create a dedicated feedback bucket/token later, or keep using the isolated Preview prefix in the existing bucket until a scoped feedback bucket is provisioned. |
| P2 | No admin/export workflow exists for immutable R2 records. | No | Add export/review tooling before relying on records for regular triage. |

## 9. Final recommendation

- `BLOCKED`
- Next action: perform the read-only R2 record inspection for `query_feedback/preview`. The deployed endpoint/UI write path is enabled and returning `stored=true`, but feedback readiness should not be promoted until live records are inspected for schema v1, compact metadata only, no PII fields, no raw result tables, and automatic diagnostic coverage.
