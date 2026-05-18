# Query Feedback Review Runbook

This runbook covers v1 query feedback and diagnostic logging review.

## Storage

- Endpoint: `POST /query-feedback`
- Store: Cloudflare R2 per-record JSON objects
- Default bucket: `nbatools-feedback`
- Default prefix: `query_feedback`
- Object key shape:
  `query_feedback/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json`

The endpoint is backend-owned. The frontend never receives R2 credentials and
does not write directly to storage.

If `QUERY_FEEDBACK_STORE` is unset or empty, feedback storage is disabled. The
endpoint returns JSON with `ok: true`, `stored: false`, and `disabled: true` so
the product UI can fail softly without changing query behavior.

## Record Schema

V1 records use `schema_version: 1` and include:

- `id`
- `created_at`
- `feedback_source`: `automatic` or `user_submitted`
- `feedback_type`: `wrong_answer`, `expected_supported`,
  `confusing_answer`, `no_result`, `unsupported`, `error`, `ui_issue`, or
  `other`
- `query`
- `query_normalized_hash`
- `source_page`
- `environment`
- `route`, `status`, `reason`
- compact `result_shape` with section keys and row counts
- sanitized `metadata`
- capped `notes`, `caveats`, `user_note`, `answer_text_preview`, and
  `error_message`
- `elapsed_ms` when available
- `review_status: new`
- `triage_decision: null`

The sanitizer stores compact allowlisted metadata only. It drops top-level or
metadata fields such as `email`, `name`, `ip`, `user_id`, `account`, `phone`,
and full raw result payloads.

## Listing and Export

V1 does not include an admin dashboard. Review records through the R2 console,
`rclone`, `aws s3` configured for the R2 endpoint, or a later export script.

Typical review flow:

1. List objects under `query_feedback/YYYY/MM/DD/`.
2. Download a day or date range of JSON records.
3. Group by `feedback_type`, `route`, `reason`, and `query_normalized_hash`.
4. Triage duplicate hashes together.
5. Convert accepted records into QA cases, data issues, product-boundary notes,
   or no-action decisions.

## Triage Statuses

Use these statuses in exported review notes or a future triage UI:

- `new`
- `reviewing`
- `accepted_bug`
- `accepted_support_candidate`
- `expected_unsupported`
- `duplicate`
- `added_to_corpus`
- `closed`

## Triage Decisions

- `raw_qa_case`: backend/parser/query behavior should change or be guarded by
  a new expectation.
- `frontend_copy_case`: backend result is correct, but rendered wording or
  product copy is confusing or wrong.
- `visual_qa_case`: layout, overflow, density, or visual hierarchy issue.
- `data_issue`: freshness, missing R2 object, source coverage, or verified data
  anomaly.
- `parser_issue`: unrouted, ambiguous, or slot extraction mismatch.
- `unsupported_family`: valid demand outside the current product boundary.
- `no_action`: expected unsupported behavior, duplicate, or non-actionable
  report.

## Privacy and Retention

Do not add names, emails, user accounts, IP addresses, phone numbers, precise
device fingerprints, or session replay to feedback records. User notes are
capped and the UI asks users not to include personal information.

Recommended retention is 90 days for raw feedback records unless a record has
been converted into a QA case, data issue, or product planning artifact.
