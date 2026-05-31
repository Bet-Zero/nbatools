# Query Feedback Review Console V1 Frontend Return Package

## What Changed

Implemented the internal Query Feedback Review Console V1 at `/admin/feedback`.

Key files:

- `frontend/src/AdminFeedbackPage.tsx`
- `frontend/src/AdminFeedbackPage.module.css`
- `frontend/src/InternalRoutes.tsx`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/test/AdminFeedbackPage.test.tsx`
- `frontend/src/test/client.test.ts`
- `src/nbatools/api.py`
- `tests/test_api.py`

Docs updated:

- `docs/operations/query_feedback_review.md`
- `docs/operations/ui_guide.md`
- `docs/planning/raw-product/QUERY_FEEDBACK_REVIEW_CONSOLE_V1_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `docs/index.md`

## Frontend Route Behavior

`/admin/feedback` is now a lazy internal route through
`frontend/src/InternalRoutes.tsx` and `resolveRootView()` in
`frontend/src/main.tsx`.

The public `/` app remains eager/default. No public-facing navigation was added.
FastAPI now serves the same UI shell for `/admin/feedback`, matching `/review`
and `/visual-qa`, so production-like direct loads work.

## API Client And Types Added

Added TypeScript types for grouped feedback, normalized records, triage
overlays, filter state, list/detail responses, and triage save payloads.

Added typed client functions:

- `fetchAdminFeedbackGroups`
- `fetchAdminFeedbackGroupDetail`
- `fetchAdminFeedbackTriage`
- `saveAdminFeedbackTriage`

The Vite dev proxy now forwards `/api/admin/feedback` to the local FastAPI API.

## Console UI

The console renders:

- internal admin title/header
- token entry area
- loading, disabled, unauthorized, and error states
- filters for review status, triage decision, feedback source, feedback type,
  route, status, and reason
- grouped feedback list
- selected group detail with representative query, count, first/last seen,
  route/status/reason, unsupported filters, user notes, sources/types,
  suggested triage, and current overlay values
- triage editor
- copyable handoff summary

Grouping and triage suggestions remain backend-owned. The frontend fetches and
renders the API response; it does not compute grouping or business
classifications.

## Triage Save Behavior

The triage editor saves only the mutable overlay through:

`PUT /api/admin/feedback/groups/{group_id}/triage`

Editable fields:

- `review_status`
- `triage_decision`
- `review_notes`
- `linked_case_or_issue`
- `reviewer_source`

`reviewer_source` defaults to `admin_feedback_console`. Original feedback
records are not mutated.

## Token Handling

The console accepts an admin token when the API returns unauthorized. The token
is kept in React component state for the current page session and is sent as
`X-NBATools-Admin-Token` on admin feedback API requests.

No R2 credentials are exposed. No localStorage/sessionStorage persistence was
added for the admin token.

## Tests Added Or Updated

Added `frontend/src/test/AdminFeedbackPage.test.tsx` covering:

- `/admin/feedback` lazy route render
- unauthorized token state
- mocked group list rendering
- selected group detail loading
- triage overlay save
- handoff summary rendering/copy affordance
- filter request state

Updated `frontend/src/test/client.test.ts` for admin feedback client endpoint
URLs, query params, and token headers.

Updated `tests/test_api.py` so `/admin/feedback` is included in the internal UI
shell smoke coverage.

## Validation Results

Passed:

- `npm --prefix frontend test -- --run AdminFeedbackPage client`
  - 2 files, 24 tests passed
- `npm --prefix frontend run build`
- `npm --prefix frontend run lint`
- `make PYTEST=.venv/bin/pytest test-api`
  - 76 selected tests passed
- `git diff --check`

Initial `make test-api` without `PYTEST` failed because `pytest` was not on
PATH in this shell. The same Make target passed with `.venv/bin/pytest`.

## Privacy And Safety Notes

- Original sanitized feedback records remain immutable.
- Triage decisions are stored in separate overlay records.
- The console does not edit QA corpora.
- The console does not create parser rules.
- The console does not create GitHub issues.
- The console does not change query behavior, parser/routing behavior, feedback
  collection behavior, or result contracts.
- `make query-feedback-export` remains the fallback/batch review workflow.

## Release Impact

Query Feedback Review Console V1 frontend is implemented with notes. The review
workflow now has both:

- interactive internal UI at `/admin/feedback`
- existing terminal/export fallback through `make query-feedback-export`

This is an internal operations surface only and does not alter the public NBA
query product.

## Remaining V2 Ideas

- Date range and smoke-toggle controls in the console.
- Facet counts from the backend for filter menus.
- Records table/detail expansion for individual source records.
- Bulk triage actions.
- Export selected handoff summaries.
- Optional reviewer identity integration if a broader admin-auth architecture
  is later approved.
- Optional issue/corpus handoff generation after explicit human triage, without
  automatic mutation.
