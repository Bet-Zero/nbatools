# Query Feedback Review Runbook

This runbook covers v1 query feedback and diagnostic logging review.

## Storage

- Endpoint: `POST /query-feedback`
- Store: Cloudflare R2 per-record JSON objects
- Default bucket: `nbatools-feedback`
- Default prefix: `query_feedback`
- Object key shape:
  `query_feedback/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json`

Current preview status as of the May 18, 2026 R2 inspection is
`FEEDBACK_READY_WITH_NOTES`. Preview records were verified in bucket
`nbatools-data` under isolated prefix `query_feedback/preview` because the
dedicated feedback bucket was unavailable. The verified preview key shape is:

```text
query_feedback/preview/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json
```

Evidence is recorded in
`return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`.

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

## Export Workflow

V1 does not include an admin dashboard. Use the read-only exporter to turn
immutable feedback records into review artifacts:

```bash
.venv/bin/python tools/export_query_feedback.py \
  --bucket nbatools-data \
  --prefix query_feedback/preview \
  --since 2026-05-18
```

For offline review or tests, point the same tool at a local directory of JSON
records:

```bash
.venv/bin/python tools/export_query_feedback.py \
  --local-dir tests/fixtures/query_feedback \
  --output-dir outputs/query_feedback_exports \
  --run-id fixture_review
```

The exporter only lists and reads records. It must not call `put_object`,
`delete_object`, `copy_object`, or any other mutation operation against R2.
It also does not edit QA corpora, query behavior, parser behavior, frontend
rendering, or feedback collection.

Default export source for the current preview workflow:

- bucket: `nbatools-data`
- prefix: `query_feedback/preview`
- output base: `outputs/query_feedback_exports`
- smoke/test records: excluded unless `--include-smoke` is passed

Each run writes artifacts under:

```text
outputs/query_feedback_exports/<run_id>/
```

If `--run-id` is omitted, the run id is a UTC timestamp.

## Export Outputs

| File | Purpose |
|---|---|
| `feedback_review.md` | Human-readable review report with run metadata, filters, counts, duplicate groups, priority groups, smoke summary, diagnostics, user reports, candidate buckets, and next actions. |
| `feedback_records.csv` | One normalized flat row per exported record for spreadsheet inspection. |
| `feedback_records.jsonl` | One normalized JSON object per exported record for machine reuse. |
| `summary.json` | Run metadata, filters, source mode, counts, group counts, high-priority group ids, triage bucket counts, and output paths. |
| `triage_decisions_template.csv` | One editable row per group for reviewer-owned status, final decision, linked case id, notes, and next action. |

The normalized records include only sanitized record content and derived review
fields. They do not include raw result rows, full result tables, IP addresses,
device identifiers, accounts, names, emails, phone numbers, or session replay.

## Filter Semantics

The exporter supports these filters:

- `--since`: include records at or after a `YYYY-MM-DD` or ISO timestamp.
- `--until`: include records at or before a `YYYY-MM-DD` or ISO timestamp.
  Date-only `--until` values include the full UTC day.
- `--source`: filter by `feedback_source`; accepts repeated or comma-separated
  values such as `automatic,user_submitted`.
- `--feedback-type`: filter by `feedback_type`.
- `--status`: filter by stored result status.
- `--route`: filter by stored route.
- `--limit`: cap exported records after filters and smoke handling.
- `--include-smoke`: include smoke/test records while still marking
  `is_smoke=true`.
- `--exclude-smoke`: explicit default; exclude smoke/test records from launch
  review candidates.

Filters can be combined. Source/type/status/route filters match stored values
exactly.

## Smoke Exclusion Policy

Smoke/test evidence is excluded from launch-review candidate sections by
default and counted in `summary.json` as `excluded_smoke_count`.

A record is classified as smoke/test evidence when any of these are true:

- `query` contains `smoke`.
- `user_note` contains `Smoke test` or `smoke test`.
- `route` is `smoke`.
- `reason` is `smoke`.
- `feedback_type=other` with a direct endpoint smoke query.
- a future source, environment, or deployment label clearly identifies
  smoke/test evidence.

Use `--include-smoke` only when verifying storage or diagnostic evidence. Smoke
records should normally receive `no_action`.

## Grouping and Suggested Triage

Records are grouped after filtering and smoke classification.

Primary grouping key:

```text
query_normalized_hash
```

Fallback grouping key when the hash is missing:

```text
normalized_query | route | status | reason | unsupported_filters | feedback_type
```

Each group gets a deterministic `group_id`, representative query, first/last
seen timestamps, source/type/route/status/reason sets, unsupported filters,
record ids, object keys, a heuristic `suggested_triage`, and optional
`triage_modifiers`.

Duplicate demand adds `prioritize_review` when a group has at least three
records, or at least two user-submitted records.

| Signal | Suggested triage |
|---|---|
| `status=error` and `reason=unrouted` | `parser_issue` |
| `status=no_result` and `reason=filter_not_supported` | `unsupported_family` |
| `status=no_result` and `reason=no_data` | `data_issue` |
| `feedback_type=wrong_answer` | `raw_qa_case` |
| `feedback_type=confusing_answer` | `frontend_copy_case` |
| `feedback_type=ui_issue` | `visual_qa_case` |
| `feedback_source=automatic`, `status=ok`, `elapsed_ms >= 8000` | `performance_review` |
| smoke/test evidence | `no_action` |

`suggested_triage` is separate from reviewer-owned `triage_decision`. It is a
heuristic sorting aid, not automatic QA truth.

## Triage Template Workflow

Use `triage_decisions_template.csv` as the editable review worksheet.

1. Sort by `suggested_triage`, `count`, and `prioritize_review`.
2. Fill `review_status` as the review progresses.
3. Fill `triage_decision` only after human review.
4. Add a `linked_case_id` when the group becomes a QA case, data issue, product
   issue, or planning item.
5. Use `reviewer_notes` and `next_action` to record the manual decision.

Do not mutate source R2 records during this process. If mutable triage state is
needed later, build a separate authenticated overlay workflow.

## QA Conversion Rules

Feedback is input to review, not automatic QA truth. Convert only accepted,
reviewed groups into curated artifacts.

- `raw_qa_case`: create or update raw query-answer QA only after verifying the
  expected status, route, reason, shape, sections, and row-count assertions.
- `frontend_copy_case`: use when backend behavior is acceptable but rendered
  wording, no-result copy, filter chips, labels, or explanation text needs a
  copy assertion.
- `visual_qa_case`: use for layout, clipping, density, responsive behavior,
  hierarchy, or visual rendering issues.
- `unsupported_family`: use for repeated valid demand outside current product
  scope; make an explicit product-boundary decision before promotion.
- `data_issue`: use for missing source coverage, freshness mismatches, R2
  availability, or verified data anomalies.
- `no_action`: use for smoke records, duplicates of tracked issues, expected
  unsupported behavior, or non-actionable records.

Do not automatically modify `qa/raw_query_answer_corpus.yaml`,
`qa/frontend_copy_corpus.yaml`, or `qa/frontend_visual_qa_corpus.json`.

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
