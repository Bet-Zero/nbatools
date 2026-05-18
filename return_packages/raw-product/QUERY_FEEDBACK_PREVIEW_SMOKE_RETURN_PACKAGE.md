# Query Feedback Preview Smoke Return Package

## 1. Executive summary

- Preview URL: `https://nbatools-hqoby638x-brents-projects-686e97fc.vercel.app` (resolved from Vercel deployment list because the prompt contained `<PASTE_PREVIEW_URL_HERE>`)
- Feedback readiness status: `BLOCKED`
- Endpoint smoke: `POST /query-feedback` returns HTTP 200 JSON with `ok=true` and `feedback_id`, but `stored=false` and `disabled=true`
- Successful-answer feedback: blocked by disabled feedback storage; the successful query itself returned `season_leaders` / `ok`
- No-result feedback: blocked by disabled feedback storage; the no-result query itself returned `season_leaders` / `no_result` / `filter_not_supported`
- Automatic diagnostic logging: query UX remained intact, but R2 diagnostic writes are blocked because feedback storage is disabled
- R2 object verification: not possible; no feedback object was written
- Suppression checks: `/review` and `/visual-qa` showed no feedback buttons and emitted no `/query-feedback` requests; `/visual-qa` ran 15 `/query` requests with `X-NBATools-Source-Page: /visual-qa`
- Blocking issues: deployed Vercel env does not include `QUERY_FEEDBACK_STORE`, `QUERY_FEEDBACK_BUCKET_NAME`, or `QUERY_FEEDBACK_PREFIX`
- Non-blocking notes: no admin dashboard, no full dedupe/rate limiting, no live frontend network-error path test, immutable R2 records need export/review workflow
- Recommended next step: configure feedback env for Preview with an isolated R2 bucket/prefix, redeploy, then rerun this smoke

## 2. Environment/storage validation

| Check | Result | Evidence |
|---|---|---|
| Current deployment resolved | Pass with note | `npx vercel ls nbatools --scope brents-projects-686e97fc` listed `https://nbatools-hqoby638x-brents-projects-686e97fc.vercel.app` as Ready. `vercel inspect` showed deployment `dpl_FPCrpozYJVfJRTbN8tuh9Zw8ngsq`, target `production`, created May 17, 2026 23:21:28 EDT. |
| `QUERY_FEEDBACK_STORE=r2` present | Fail | `npx vercel env list production` and `preview` listed only `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, and `DATA_SOURCE`. |
| `QUERY_FEEDBACK_BUCKET_NAME` set | Fail | Not present in Vercel env list for Production or Preview. |
| `QUERY_FEEDBACK_PREFIX` set | Fail | Not present in Vercel env list for Production or Preview. |
| R2 credentials server-side | Pass for data R2 credentials | Vercel env list shows encrypted `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY` for Production and Preview. |
| Frontend bundle credential exposure | Pass | Downloaded `/assets/index-Dv13Viki.js` and `/assets/index--MbHWniS.css`; `rg` found no `R2_`, `QUERY_FEEDBACK`, `ACCESS_KEY`, `SECRET`, or `cloudflarestorage` strings. |

## 3. Direct endpoint validation

| Request | Expected | Actual | Verdict |
|---|---|---|---|
| `POST /query-feedback` with safe user-submitted smoke payload | HTTP 200 JSON, `ok=true`, `stored=true`, `disabled=false`, `feedback_id` present | HTTP 200 JSON: `{"ok":true,"feedback_id":"qfb_20260518T032602381560Z_8c7672c7","stored":false,"disabled":true}` | Fail/blocking |

## 4. User feedback validation

| Surface | Query | Expected | Actual | Verdict |
|---|---|---|---|---|
| Successful-answer feedback | `Who leads the NBA in points per game this season?` | Query renders normally; `Report issue` writes user-submitted R2 record | Query API returned HTTP 200, `route=season_leaders`, `result_status=ok`, current through `2026-04-12`. Feedback write is blocked by disabled storage. | Blocked |
| No-result feedback | `players with most personal fouls this season` | Query renders no-result card; `Submit for review` writes user-submitted R2 record | Query API returned HTTP 200, `route=season_leaders`, `result_status=no_result`, `result_reason=filter_not_supported`, `unsupported_filters=["personal_foul_leaderboard"]`. Feedback write is blocked by disabled storage. | Blocked |

## 5. Automatic logging validation

| Query/event | Expected | Actual | Verdict |
|---|---|---|---|
| `players with most personal fouls this season` | Query response renders normally and creates automatic diagnostic R2 object | Query returned normal HTTP 200 no-result payload with `route=season_leaders`, `reason=filter_not_supported`; no R2 object can be written while storage is disabled. | Blocked for storage; query UX pass |
| `who won mvp this season` | Query response renders normally and creates automatic diagnostic R2 object | Query returned normal HTTP 200 error payload with `route=null`, `result_status=error`, `result_reason=unrouted`; no R2 object can be written while storage is disabled. | Blocked for storage; query UX pass |

## 6. R2 record inspection

| Record type | Object key | Sanitization verdict | Notes |
|---|---|---|---|
| Direct endpoint smoke | Not created | Not inspectable live | Endpoint returned `stored=false`, `disabled=true`. |
| User-submitted feedback | Not created | Not inspectable live | Storage disabled before UI/R2 validation could pass. |
| Automatic diagnostic | Not created | Not inspectable live | Storage disabled before diagnostic R2 validation could pass. |

## 7. Suppression validation

| Surface | Expected | Actual | Verdict |
|---|---|---|---|
| `/review` | No visible `Report issue` / `Submit for review` / `Report error`; no `/query-feedback` requests | Headless browser check found `feedbackButtons=[]`, `queryFeedbackRequests=0`, `queryRequests=0` | Pass |
| `/visual-qa` | No feedback buttons; visual QA runs; no feedback records/noise | Longer headless browser check found `feedbackButtons=[]`, `queryFeedbackRequests=0`, `queryRequests=15`, all `/query` responses HTTP 200, source pages `["/visual-qa"]`, progress `15 / 15 cases completed` | Pass |

## 8. Issues found

| Priority | Issue | Blocking? | Recommended action |
|---|---|---|---|
| P0 | Feedback storage is not enabled in the deployed Vercel environment. Required `QUERY_FEEDBACK_*` variables are absent. | Yes | Add `QUERY_FEEDBACK_STORE=r2`, `QUERY_FEEDBACK_BUCKET_NAME`, and `QUERY_FEEDBACK_PREFIX` to the intended Preview environment using a dedicated bucket or isolated prefix, then redeploy. |
| P0 | `/query-feedback` cannot write to R2 in the checked deployment. | Yes | Rerun direct endpoint smoke after env is configured and verify `stored=true`, `disabled=false`, plus object existence in R2. |
| P1 | Live R2 record sanitization could not be inspected. | Yes for readiness, no code issue proven | After enabling storage, inspect one direct, one user-submitted, and one automatic record for schema v1, compact metadata, no raw tables, and no PII fields. |
| P2 | Frontend network/non-JSON diagnostic path was not exercised manually. | No | Exercise only if a safe failure hook exists; do not break preview to force it. |

## 9. Final recommendation

- `BLOCKED`
- Next action: configure the feedback R2 env vars for the intended preview deployment, redeploy, and rerun the smoke until at least one user-submitted record and one automatic diagnostic record are verified in R2.
