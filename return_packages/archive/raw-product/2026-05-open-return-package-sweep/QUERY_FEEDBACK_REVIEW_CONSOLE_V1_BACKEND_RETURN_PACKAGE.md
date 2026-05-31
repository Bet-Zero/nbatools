# Query Feedback Review Console V1 Backend Return Package

## Summary

Implemented the backend foundation for Query Feedback Review Console V1 and
Mutable Triage Overlay V1.

This wave adds shared feedback review grouping helpers, separate mutable
triage overlay storage, and gated admin API endpoints. It does not add the
frontend `/admin/feedback` console.

## What Changed

- Added `src/nbatools/query_feedback_review.py` for reusable feedback review
  behavior:
  - local/R2 feedback record loading
  - sanitizer-compatible normalization
  - smoke detection and suggested triage reuse
  - deterministic group ids
  - group summaries
  - overlay validation, read, write, and join helpers
- Updated `tools/export_query_feedback.py` to use the shared review helpers
  while preserving the existing export artifact workflow.
- Added gated FastAPI admin feedback endpoints.
- Added backend tests for overlay validation/storage, grouping reuse, admin
  gating, admin list/detail/read/write behavior, and export compatibility.
- Updated operations and planning docs for backend-only Wave 1 status.

## API Endpoints Added

Endpoint prefix: `/api/admin/feedback`

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/feedback/groups` | List grouped feedback with triage overlays joined. |
| `GET` | `/api/admin/feedback/groups/{group_id}` | Read one group with normalized source records and handoff summary. |
| `GET` | `/api/admin/feedback/groups/{group_id}/triage` | Read one group's mutable triage overlay. |
| `PUT` | `/api/admin/feedback/groups/{group_id}/triage` | Save/update one group's mutable triage overlay. |

List filters supported in Wave 1:

- `feedback_source` or `source`
- `feedback_type`
- `route`
- `status`
- `reason`
- `review_status`
- `triage_decision`
- `since`
- `until`
- `include_smoke`
- `limit`

## Triage Overlay Schema And Path

Overlay objects are stored separately from immutable source feedback records:

```text
<feedback_prefix>/_triage_overlay/groups/<group_id>.json
```

For the current preview prefix:

```text
query_feedback/preview/_triage_overlay/groups/qfg_<digest>.json
```

Schema fields:

- `schema_version`
- `group_id`
- `updated_at`
- `review_status`
- `triage_decision`
- `review_notes`
- `linked_case_or_issue`
- `reviewer_source`
- `source_record_ids`

Allowed `review_status` values: `new`, `reviewed`, `deferred`, `closed`.

Allowed `triage_decision` values: `bug`, `support_candidate`,
`expected_unsupported`, `duplicate`, `no_action`, `needs_more_data`,
`parser_routing_risk`, `ui_copy_issue`.

## Enable And Token Behavior

Admin feedback endpoints are disabled by default.

Enable with:

```text
NBATOOLS_ADMIN_FEEDBACK_ENABLED=true
NBATOOLS_ADMIN_TOKEN=<secret>
```

Behavior:

- Disabled endpoints return `404` with `admin_feedback_disabled`.
- If `NBATOOLS_ADMIN_TOKEN` is configured, requests must include
  `X-NBATools-Admin-Token`.
- Deployed preview/production environments require
  `NBATOOLS_ADMIN_TOKEN` when admin feedback endpoints are enabled.
- The frontend never receives R2 credentials.

## Tests Added Or Updated

Added:

- `tests/test_query_feedback_review.py`
- `tests/test_admin_feedback_api.py`

Updated:

- `tests/test_export_query_feedback.py`

Coverage includes:

- grouping helper compatibility with export behavior
- overlay validation enums and reviewed/closed decision requirement
- overlay read/write round trip through mocked R2 storage
- immutable source feedback records are not mutated by overlay writes
- admin endpoints disabled behavior
- admin token behavior
- deployed env token-configuration guard
- group list with overlay joined
- group detail response
- triage overlay read/save endpoints
- export workflow still read-only in mocked R2 mode

## Validation Results

| Command / check | Result |
| --- | --- |
| `.venv/bin/pytest tests/test_query_feedback.py tests/test_export_query_feedback.py tests/test_query_feedback_review.py tests/test_admin_feedback_api.py -n0` | Passed: 30 passed |
| `make test-api` | Failed in this shell because `pytest` is not on PATH |
| `make PYTEST=.venv/bin/pytest test-api` | Passed: 75 passed, 2954 deselected |
| `make PYTEST=.venv/bin/pytest test-output` | Passed: 339 passed |
| `.venv/bin/ruff check src/nbatools/api.py src/nbatools/query_feedback_review.py tools/export_query_feedback.py tests/test_export_query_feedback.py tests/test_query_feedback_review.py tests/test_admin_feedback_api.py` | Passed |
| `git diff --check` | Passed |
| Markdown lint | Not run - no `markdownlint` or `markdownlint-cli2` binary found on PATH |

## Privacy And Safety Notes

- Original feedback records remain immutable.
- Overlay writes use only the `_triage_overlay/groups/` path under the feedback
  prefix.
- Export remains read-only and does not write overlay records.
- Admin endpoints are explicitly disabled unless enabled by env var.
- Deployed admin access requires a token.
- No frontend code receives storage credentials.
- No query behavior, parser behavior, result contracts, QA corpus files, or
  feedback collection behavior were changed.

## Release Impact

Backend-only internal review foundation. The existing public query UI and
feedback submission behavior are unchanged. The existing
`make query-feedback-export` workflow remains the fallback review process.

## Remaining For Frontend Wave 2

- Add lazy `/admin/feedback` frontend route.
- Add typed frontend API client and response interfaces.
- Build grouped feedback list, filters, detail panel, triage editor, and
  handoff-copy panel.
- Run frontend tests, lint, and `npm --prefix frontend run build`.
- Update UI operations docs after the console is verified.
