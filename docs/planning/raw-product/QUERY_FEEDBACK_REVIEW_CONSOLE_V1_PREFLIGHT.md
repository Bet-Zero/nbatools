# Query Feedback Review Console V1 Preflight

## 1. Scope

Mode: preflight only.

This document plans a private/internal Query Feedback Review Console V1 at
`/admin/feedback` and a Mutable Triage Overlay V1. It does not change
production code, frontend rendering, backend behavior, feedback storage
behavior, export workflow, admin UI, return-package placement, or QA corpus
expectations.

Core product decision: original sanitized feedback records remain immutable.
Reviewer state is written to separate mutable overlay records and joined at
read time.

## 2. Current System Summary

Current feedback collection is backend-owned through `POST /query-feedback`.
The browser never receives R2 credentials. Feedback storage is disabled unless
`QUERY_FEEDBACK_STORE=r2` and the feedback bucket/prefix credentials are
configured.

Current record storage:

| Item | Current value |
| --- | --- |
| Default store | Cloudflare R2 |
| Dedicated bucket recommendation | `nbatools-feedback` |
| Current preview bucket/prefix | `nbatools-data` / `query_feedback/preview` |
| Default prefix | `query_feedback` |
| Key shape | `query_feedback/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json` |
| Preview key shape | `query_feedback/preview/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json` |

Current feedback record schema is `schema_version: 1` and includes:

- identity and timing: `id`, `created_at`
- feedback taxonomy: `feedback_source`, `feedback_type`
- query grouping fields: `query`, `query_normalized_hash`
- surface/environment: `source_page`, `environment`, optional `deployment`
- query outcome: `route`, `status`, `reason`
- compact diagnostics: `result_shape`, allowlisted `metadata`, `notes`,
  `caveats`, `user_note`, `answer_text_preview`, `error_message`, `elapsed_ms`
- initial review placeholders: `review_status: new`, `triage_decision: null`

The sanitizer in `src/nbatools/query_feedback.py` drops disallowed PII and raw
result/table fields. Existing tests cover validation, sanitizer behavior,
disabled store behavior, mocked R2 writes, automatic diagnostic best-effort
behavior, and suppression for `/review` and `/visual-qa`.

## 3. Current Export Grouping Logic

The read-only exporter in `tools/export_query_feedback.py` currently owns the
review grouping workflow:

- reads local JSON records via `--local-dir` or R2 objects via
  `--bucket`/`--prefix`
- normalizes records with compact metadata and result-shape summaries
- filters by date, source, feedback type, status, route, smoke inclusion, and
  limit
- excludes smoke records by default
- groups records by `query_normalized_hash` when present, otherwise by a
  fallback key built from normalized query, route, status, reason,
  unsupported filters, and feedback type
- derives deterministic group ids with `qfg_<12_hex_digest>`
- adds group-level fields such as count, first/last seen, representative query,
  sources, types, routes, statuses, reasons, unsupported filters, user notes,
  record ids, object keys, suggested triage, and modifiers
- writes `feedback_review.md`, `feedback_records.csv`,
  `feedback_records.jsonl`, `summary.json`, and
  `triage_decisions_template.csv`

The grouping logic can be reused by an API endpoint, but it should not remain
script-only. V1 should extract shared, side-effect-free helpers from the
exporter into a backend module such as `src/nbatools/query_feedback_review.py`.
The exporter should call those helpers so the console and
`make query-feedback-export` share grouping semantics.

## 4. R2 And Local Read/Write Helpers

Available helpers:

- `src/nbatools/data_source.py` provides `R2Config`, `load_r2_config()`, and
  `create_r2_client()`.
- `src/nbatools/query_feedback.py` provides feedback-specific env loading via
  `load_feedback_store_config()` and object writes via
  `store_feedback_record()`.
- `tools/export_query_feedback.py` has read helpers for local JSON trees and
  R2 list/get flows, but those helpers currently live in a CLI script.

Recommended V1 helper split:

- keep collection/write helpers in `query_feedback.py`
- add review read/group/overlay helpers in `query_feedback_review.py`
- keep exporter read-only by having it call shared read/group helpers and its
  existing artifact writers
- support dependency injection of R2 clients in helper functions for tests

## 5. Triage Overlay Storage

Recommended overlay storage path:

```text
<feedback_prefix>/_triage_overlay/groups/<group_id>.json
```

For the current preview prefix, that becomes:

```text
query_feedback/preview/_triage_overlay/groups/qfg_<digest>.json
```

For the dedicated production feedback bucket/prefix, that becomes:

```text
query_feedback/_triage_overlay/groups/qfg_<digest>.json
```

Rationale:

- the overlay lives beside the immutable feedback stream without changing it
- group-level decisions match the current export worksheet grain
- one object per group avoids rewriting a monolithic review file
- deterministic group ids keep overlay lookup stable as new duplicate records
  join a group
- the `_triage_overlay` prefix is easy to exclude from raw feedback reads

Stop and redesign if group ids prove unstable for material real cases. V1 must
not store overlay decisions by list position, export run id, or raw object key
only.

## 6. Proposed Overlay Schema

File: `<prefix>/_triage_overlay/groups/<group_id>.json`

```json
{
  "schema_version": 1,
  "group_id": "qfg_0123456789ab",
  "review_status": "new",
  "triage_decision": null,
  "review_notes": "",
  "linked_case_or_issue": "",
  "updated_at": "2026-05-23T00:00:00.000Z",
  "updated_by": "local_admin",
  "feedback_prefix": "query_feedback/preview",
  "record_ids_snapshot": ["qfb_..."],
  "object_keys_snapshot": ["query_feedback/preview/2026/05/18/...json"]
}
```

Allowed `review_status` values:

- `new`
- `reviewed`
- `deferred`
- `closed`

Allowed `triage_decision` values:

- `bug`
- `support_candidate`
- `expected_unsupported`
- `duplicate`
- `no_action`
- `needs_more_data`
- `parser_routing_risk`
- `ui_copy_issue`

Validation rules:

- `group_id` must match the requested group id.
- `review_status` is required and must be one of the allowed values.
- `triage_decision` may be `null` only when status is `new` or `deferred`.
- `review_notes` and `linked_case_or_issue` are optional strings with caps.
- client-supplied `updated_at`, `updated_by`, snapshots, and prefix are ignored
  or overwritten by the backend.
- overlay writes never update immutable feedback records.

## 7. Proposed Backend API

Recommended endpoint prefix: `/api/admin/feedback`.

V1 privacy/auth boundary: these endpoints are private/internal. Require an
admin token in an environment variable before enabling them in deployed
environments. Recommended env vars:

- `NBATOOLS_ADMIN_FEEDBACK_ENABLED=true`
- `NBATOOLS_ADMIN_TOKEN=<secret>`

For local development, allow the endpoints when explicitly enabled and require
`X-NBATools-Admin-Token` if `NBATOOLS_ADMIN_TOKEN` is set. If the console is
requested while disabled, return `404` or a simple disabled state rather than
exposing data. Do not rely on route obscurity alone for deployed previews.

Proposed endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/feedback/groups` | List grouped feedback with overlay joined. |
| `GET` | `/api/admin/feedback/groups/{group_id}` | Return group detail, records, and current overlay. |
| `PUT` | `/api/admin/feedback/groups/{group_id}/triage` | Validate and save mutable overlay for one group. |
| `GET` | `/api/admin/feedback/groups/{group_id}/triage` | Read overlay only for one group. |

List query parameters:

- `since`, `until`
- `source`
- `feedback_type`
- `route`
- `status`
- `reason`
- `review_status`
- `triage_decision`
- `include_smoke`
- `limit`

The list response should include groups, counts/facets for filters, and source
metadata. The detail response should include the group summary, normalized
records, immutable object keys, current overlay, and a prebuilt handoff summary
string suitable for copy/export to ChatGPT or an agent.

## 8. Frontend Route Design

Add `/admin/feedback` as a new internal root view, parallel to `/review` and
`/visual-qa`.

Recommended route behavior:

- add an `AdminFeedbackRoute` lazy boundary in `frontend/src/InternalRoutes.tsx`
- update `resolveRootView()` in `frontend/src/main.tsx` to route
  `/admin/feedback` to that boundary
- serve the UI shell for `/admin/feedback` from FastAPI, matching the existing
  internal route pattern
- keep the public `/` app eager/default

Lazy loading should be used. The console is internal, data-heavy, and not part
of the public answer path. This matches the existing route-level split that
keeps `/review` and `/visual-qa` outside the public entry chunk.

Recommended UI layout:

- top toolbar: source status, refresh, filter chips, copy/export action
- left or top filter rail: review status, triage decision, source, feedback
  type, route, status, reason, date range, smoke toggle
- grouped feedback list: group id, count, representative query, source/type
  badges, route/status/reason, first/last seen, suggested triage, overlay
  status/decision
- detail panel: representative query, records table, user notes, answer/error
  previews, unsupported filters, metadata summary, object keys
- triage editor: `review_status`, `triage_decision`, `review_notes`,
  `linked_case_or_issue`, save state, validation errors
- handoff panel: copy selected group summary for ChatGPT/agent handoff

The frontend should fetch and render backend-provided records. It should not
compute grouping, triage suggestions, or business classifications client-side.

## 9. Exact Files Likely To Change

Backend:

- `src/nbatools/query_feedback_review.py` (new shared read/group/overlay module)
- `src/nbatools/query_feedback.py` (only if shared config/constants need small
  extraction)
- `src/nbatools/api.py` (admin feedback endpoints and shell route)
- `tools/export_query_feedback.py` (reuse shared grouping helpers; keep export
  artifact workflow intact)

Backend tests:

- `tests/test_query_feedback_review.py` (new helper and overlay tests)
- `tests/test_query_feedback.py` (only if shared config behavior changes)
- `tests/test_export_query_feedback.py` (ensure export output/grouping stays
  stable after helper extraction)
- `tests/test_api.py` or `tests/test_query_feedback.py` (admin endpoint tests,
  depending on current test organization)

Frontend:

- `frontend/src/main.tsx`
- `frontend/src/InternalRoutes.tsx`
- `frontend/src/AdminFeedbackPage.tsx` (new)
- `frontend/src/AdminFeedbackPage.module.css` (new)
- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts`

Frontend tests:

- `frontend/src/test/AdminFeedbackPage.test.tsx` (new)
- `frontend/src/test/client.test.ts`
- `frontend/src/test/ReviewPage.test.tsx` only if shared route tests are
  reorganized

Docs:

- `docs/operations/query_feedback_review.md` after implementation only, to
  document the shipped console and keep export fallback instructions
- `docs/operations/deployment.md` after implementation only, to document admin
  env vars and token boundary
- return package for the implementation wave

## 10. Tests Needed

Backend helper tests:

- normalize and group fixture records exactly like current exporter
- exclude `_triage_overlay` objects while listing feedback records
- join overlay records onto grouped feedback
- return empty/default overlay when no overlay object exists
- validate allowed status/decision values
- reject status/decision mismatches and oversized notes
- write overlay object to the recommended key without mutating immutable
  feedback records
- support local fixture mode and mocked R2 list/get/put flows

API tests:

- admin endpoints are unavailable when disabled
- token is required when configured
- list endpoint returns grouped records with overlays and filter facets
- list filters by status/decision/source/type/route/reason
- detail endpoint returns records and handoff summary
- triage save endpoint validates and persists overlay
- query feedback collection endpoint remains unchanged

Exporter regression tests:

- existing export artifact contract remains unchanged
- grouping ids and smoke filtering remain stable after helper extraction
- exporter remains read-only in mocked R2 mode

Frontend tests:

- `/admin/feedback` routes to the lazy admin console
- client helpers call the proposed endpoints and surface useful errors
- console renders grouped feedback and empty/error/loading states
- filters update the API request, not client-side regrouping
- detail panel loads selected group detail
- save form validates required fields and calls the triage endpoint
- copy/export handoff text uses backend-provided summary

## 11. Validation Commands

Preflight validation:

```text
git diff --check
markdownlint docs/planning/raw-product/QUERY_FEEDBACK_REVIEW_CONSOLE_V1_PREFLIGHT.md return_packages/raw-product/QUERY_FEEDBACK_REVIEW_CONSOLE_V1_PREFLIGHT_RETURN_PACKAGE.md
```

If `markdownlint` is not available, record that explicitly.

Implementation validation, if executed later:

```text
make test-output
make test-api
npm --prefix frontend run lint
npm --prefix frontend test -- --run AdminFeedbackPage client
npm --prefix frontend run build
git diff --check
```

Use `make test-preflight` instead of `make test-impacted` if the helper
extraction touches high fan-in API or shared query-feedback behavior beyond the
bounded review/export surface.

## 12. Stop Conditions

Stop implementation and return to planning if any of these are true:

- V1 requires mutating existing feedback records.
- Stable group ids cannot be guaranteed for meaningful duplicate groups.
- Admin privacy cannot be bounded for deployed preview/production.
- Overlay writes would need broad bucket permissions beyond the feedback
  bucket/prefix.
- The exporter contract would need to change or the fallback workflow would
  become non-functional.
- The frontend would need to compute grouping or triage business logic.
- The implementation would require QA corpus expectation changes.
- Feedback records contain data the console should not display under the
  current sanitizer/privacy contract.

## 13. One-Prompt Execution Plan

Safe if scoped to V1 and no stop condition appears:

1. Extract exporter record loading, normalization, filtering, grouping, and
   summary data helpers into `src/nbatools/query_feedback_review.py`.
2. Update `tools/export_query_feedback.py` to call the shared helpers while
   preserving artifact names, fields, grouping ids, smoke behavior, and
   read-only R2 behavior.
3. Add overlay schema validation and R2/local test seams in the shared module.
4. Add FastAPI admin endpoints under `/api/admin/feedback` and a shell route
   for `/admin/feedback`, gated by explicit admin env config.
5. Add frontend API types/client methods.
6. Add a lazy `AdminFeedbackPage` route with grouped list, filters, detail,
   triage editor, and copy/export handoff panel.
7. Add backend, exporter, API, frontend client, route, and page tests.
8. Rebuild frontend so `src/nbatools/ui/dist/` stays current.
9. Update operations docs only for verified shipped behavior.
10. Create the implementation return package.

## 14. Split Execution Plan

Use this split if the one-prompt change is too large:

Wave 1: Shared backend grouping and overlay foundation.

- Extract shared helpers from the exporter.
- Preserve export outputs exactly.
- Add overlay schema helpers and tests.
- Do not add frontend.

Wave 2: Admin API.

- Add gated admin endpoints.
- Add list/detail/overlay tests with mocked storage.
- Keep export fallback untouched.

Wave 3: Frontend console.

- Add lazy `/admin/feedback` route.
- Add page, client types, filters, detail, save, and copy/export UI.
- Run frontend lint/tests/build.

Wave 4: Docs and release evidence.

- Update `docs/operations/query_feedback_review.md` and
  `docs/operations/deployment.md` for verified shipped behavior.
- Create the implementation return package.
