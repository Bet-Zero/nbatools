# Query Feedback Review Console V1 Preflight Return Package

## Summary

Created a preflight plan for a private/internal Query Feedback Review Console
V1 at `/admin/feedback` and a Mutable Triage Overlay V1.

The plan keeps original sanitized feedback records immutable, keeps
`make query-feedback-export` intact as the fallback workflow, and recommends
separate mutable group-level overlay records under:

```text
<feedback_prefix>/_triage_overlay/groups/<group_id>.json
```

## Files Created

- `docs/planning/raw-product/QUERY_FEEDBACK_REVIEW_CONSOLE_V1_PREFLIGHT.md`
- `return_packages/raw-product/QUERY_FEEDBACK_REVIEW_CONSOLE_V1_PREFLIGHT_RETURN_PACKAGE.md`

## Inputs Reviewed

- `docs/operations/query_feedback_review.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `src/nbatools/query_feedback.py`
- `tools/export_query_feedback.py`
- `tests/test_query_feedback.py`
- `tests/test_export_query_feedback.py`
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/InternalRoutes.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/QueryFeedback.test.tsx`
- `frontend/src/test/ReviewPage.test.tsx`
- `docs/operations/deployment.md`
- `Makefile`
- supporting inspection of `src/nbatools/api.py` and
  `src/nbatools/data_source.py`

## Current-System Findings

- Feedback collection writes immutable sanitized JSON records through
  `POST /query-feedback`.
- Current preview feedback records live in `nbatools-data` under
  `query_feedback/preview`; the durable recommendation remains a dedicated
  feedback bucket and `query_feedback` prefix.
- Export grouping is currently script-owned in `tools/export_query_feedback.py`
  and should be extracted into shared backend helpers before an API reuses it.
- Current frontend internal routes `/review` and `/visual-qa` are lazy-loaded
  through `frontend/src/InternalRoutes.tsx`; `/admin/feedback` should follow
  that pattern.
- Existing R2 helpers support list/get/put via boto3-compatible clients, but
  review-specific local/R2 helper functions should move out of the exporter.

## Planned API Shape

Recommended endpoint prefix: `/api/admin/feedback`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/feedback/groups` | List grouped feedback with overlay joined. |
| `GET` | `/api/admin/feedback/groups/{group_id}` | Read group detail and records. |
| `PUT` | `/api/admin/feedback/groups/{group_id}/triage` | Save mutable triage overlay. |
| `GET` | `/api/admin/feedback/groups/{group_id}/triage` | Read overlay only. |

## Privacy/Auth Boundary

V1 should be explicitly enabled and token-gated for deployed environments.
Recommended variables:

- `NBATOOLS_ADMIN_FEEDBACK_ENABLED=true`
- `NBATOOLS_ADMIN_TOKEN=<secret>`

The frontend must never receive R2 credentials.

## Validation

| Command / check | Result |
| --- | --- |
| `git diff --check` | Passed |
| Markdown lint | Not run - no `markdownlint` or `markdownlint-cli2` binary found on PATH |

## Release Impact

Preflight only. No production code, frontend rendering, backend behavior,
feedback storage behavior, export workflow, QA corpus expectations, or
return-package archive placement changed.

## Next Action

Execute either the one-prompt plan or the split Wave 1 backend foundation plan
from the preflight doc. Prefer the split plan if helper extraction plus API
plus frontend console becomes too large for one PR-sized unit.
