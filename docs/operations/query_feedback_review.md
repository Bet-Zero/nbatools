# Query Feedback Review Runbook

This runbook covers v1 query feedback and diagnostic logging review.

## Weekly Beta Feedback Review Cadence

This is the primary workflow for the runbook. During beta and early launch,
the goal is to keep collected feedback from becoming a junk drawer by
reviewing it on a regular cadence with explicit ownership. The durable working
rule for that cadence is:

```text
identify the risk
  -> write it down
  -> decide whether it needs immediate guardrails
  -> create a bounded plan
  -> execute the smallest safe hardening pass
```

The sections below the cadence are the operational reference (record
schema, exporter filters, grouping, QA conversion, retention). Use the
cadence as the entry point; reach into the reference sections as the
cadence calls for them.

### When to run

- **Weekly during beta / early launch.** Pick a fixed weekday and run the
  routine on that day each week, even when traffic is light. A small
  empty-handed pass is preferred over skipping the week.
- **Immediately after any larger public test, demo, or user group trial.**
  This is a non-negotiable post-event trigger: traffic spikes are the
  highest-signal feedback the project gets, and waiting for the next
  weekly slot loses context.
- **On demand when an incident or single high-priority report surfaces.**
  An ad-hoc run does not replace the next weekly run.

### Routine — six steps

1. **Run the export.**

   ```bash
   make query-feedback-export
   ```

   This is the canonical command. It invokes the read-only exporter
   (`tools/export_query_feedback.py`) with the runbook's default source
   (bucket `nbatools-data`, prefix `query_feedback/preview`) and writes the
   review artifacts under `outputs/query_feedback_exports/<run_id>/`. The
   raw `python tools/export_query_feedback.py …` invocation shown in the
   [Export Workflow](#export-workflow) section is the underlying form and
   is appropriate when filters or alternate sources are needed; the
   Makefile target is what the weekly cadence uses.

2. **Open the primary handoff artifact.**

   ```text
   outputs/query_feedback_exports/<run_id>/feedback_review.md
   ```

   `feedback_review.md` is the human-readable review report. It contains
   run metadata, filters, counts, duplicate groups, priority groups, smoke
   summary, diagnostics, user reports, candidate buckets, and next
   actions. Treat it as the canonical input to triage.

3. **Send `feedback_review.md` (or the key sections) to ChatGPT for product
   triage.** The user is the one who sends the artifact — see
   [Ownership model](#ownership-model) below. ChatGPT helps classify each
   group into the triage categories listed in
   [Triage categories](#triage-categories) below. ChatGPT is not the final
   judge; it is a triage helper.

4. **Fill the triage worksheet.**

   ```text
   outputs/query_feedback_exports/<run_id>/triage_decisions_template.csv
   ```

   `triage_decisions_template.csv` is the editable review worksheet. One
   row per group. Fill `review_status`, the chosen triage category,
   `linked_case_id` when a group becomes a QA case or planning item,
   `reviewer_notes`, and `next_action`. See
   [Triage Template Workflow](#triage-template-workflow) for the field
   conventions and [Triage Statuses](#triage-statuses) for the status
   vocabulary.

5. **Classify each group into one triage category.** Use the eight
   categories in [Triage categories](#triage-categories). The category is
   the product-level decision; the existing operational triage decisions
   in the [Triage Decisions](#triage-decisions) section are the
   follow-up action that flows from the category.

6. **Convert only reviewed, verified findings into downstream work.** A
   triage category alone does not modify QA, parser, frontend, or data
   artifacts; an agent is then asked to execute the follow-up after
   triage is complete. See [QA Conversion Rules](#qa-conversion-rules) for
   the bar each follow-up must clear. Do not mutate
   `qa/raw_query_answer_corpus.yaml`,
   `qa/frontend_copy_corpus.yaml`,
   `qa/frontend_visual_qa_corpus.json`, parser behavior, or feedback
   collection automatically from this routine.

### Triage categories

Every group in `feedback_review.md` is classified into exactly one of the
following eight categories. These are the product-level triage labels and
are the durable contract for what the routine produces.

| Category | When to use | Typical follow-up |
| --- | --- | --- |
| `bug` | The system gave a wrong answer, crashed, or otherwise misbehaved against its own contract. | `raw_qa_case` plus the fix work it implies (backend, parser, data, or frontend depending on the bug). |
| `support_candidate` | Repeated valid demand for a stat-shaped query the product does not yet answer. | Treat as a future feature promotion candidate; record under planning, do not promote casually. The promotion path is governed by [`feature_promotion_rules.md`](feature_promotion_rules.md). |
| `expected_unsupported` | The product correctly declined to answer (out of scope, low confidence, geography phrase, subjective phrase, etc.). | `no_action`; optionally add an unsupported-boundary raw QA case if the boundary is at risk of drifting. |
| `duplicate` | The group restates a finding already captured under another group, an existing QA case, or an open planning item. | `no_action`; cross-reference the original in `reviewer_notes`. |
| `no_action` | Smoke/test evidence, non-actionable report, or already-resolved behavior. | `no_action`; record why. |
| `needs_more_data` | The group cannot be triaged from the export alone; the reviewer needs a repro, a wider query window, additional records, or a closer look at the result payload. | Re-run the export with broader filters, request a repro, or escalate; do not promote to QA without resolution. |
| `parser_routing_risk` | The phrasing suggests a wrong-route, collision, or unsupported-boundary erosion risk, even when the specific record's behavior was acceptable. | Cross-reference against [`parser_routing_growth_guardrails.md`](parser_routing_growth_guardrails.md) (route collision rule §5, unsupported-boundary regression rule §6); convert to a guardrail-shaped raw QA case if applicable. |
| `ui_copy_issue` | Backend behavior is acceptable but rendered wording, copy, chips, or layout is confusing, duplicative, or misleading. | `frontend_copy_case` or `visual_qa_case` depending on whether the issue is copy or layout. |

The eight categories are the primary triage labels for the routine. The
[Triage Decisions](#triage-decisions) and [Triage Statuses](#triage-statuses)
sections below describe the follow-up actions and progress states; they
remain in place as the operational vocabulary for the worksheet.

### Ownership model

The cadence has an explicit ownership split. It exists so an agent is never
the only product judge during early beta.

- **User** runs `make query-feedback-export` and opens
  `feedback_review.md`.
- **User** sends `feedback_review.md` (or the key sections) to ChatGPT.
  The user chooses what to send and is responsible for redaction if any
  is needed.
- **ChatGPT** helps classify each group into one of the eight triage
  categories above, surfaces duplicates, and flags parser/routing risks.
  ChatGPT does not modify any file in the repo and does not have final
  product judgment.
- **User** records the final triage decision in
  `triage_decisions_template.csv`. The decision is product judgment, not
  algorithmic.
- **Agents** execute follow-up work (raw QA cases, frontend-copy cases,
  visual QA cases, data issues, planning items, parser/routing guardrail
  cases) **only after triage is complete** for the relevant groups, and
  only when the triage row names the agent's work explicitly via
  `linked_case_id` and `next_action`.

The hard rule:

```text
Triage = human + ChatGPT.
Execution = agent.
Agents do not triage.
```

A passing weekly run produces a triage worksheet with one row per group, a
chosen category per row, and a clear `next_action`. It does not produce
file changes by itself; those come from the agent execution step that
runs after the worksheet is complete.

### What a passing weekly run looks like

- A run id under `outputs/query_feedback_exports/`.
- `feedback_review.md` opened and reviewed.
- `triage_decisions_template.csv` filled: every group has a triage
  category, a `review_status`, and a `next_action`.
- High-priority groups (duplicate demand, user-submitted volume, parser/
  routing risk) have a `linked_case_id` or an explicit planning pointer.
- Follow-up work, if any, is queued for agent execution as a separate
  step.

### What this routine intentionally does not do

- It does not mutate source R2 records. The exporter is read-only.
- It does not modify QA corpora, parser rules, frontend renderers, data
  files, or the feedback collection endpoint.
- It does not automatically promote a `support_candidate` into shipped
  support. Promotion follows
  [`feature_promotion_rules.md`](feature_promotion_rules.md).
- It does not delegate product judgment to an agent.

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

Generated QA evidence and current scoreboard terminology are documented in
[`query_validation_map.md`](query_validation_map.md).

The endpoint is backend-owned. The frontend never receives R2 credentials and
does not write directly to storage.

If `QUERY_FEEDBACK_STORE` is unset or empty, feedback storage is disabled. The
endpoint returns JSON with `ok: true`, `stored: false`, and `disabled: true` so
the product UI can fail softly without changing query behavior.

## Mutable Triage Overlay

Backend foundation for the Feedback Review Console stores reviewer decisions in
separate mutable overlay objects. Source feedback records remain immutable.

Overlay object key shape:

```text
<feedback_prefix>/_triage_overlay/groups/<group_id>.json
```

For the current preview prefix, this is:

```text
query_feedback/preview/_triage_overlay/groups/qfg_<digest>.json
```

Overlay records use `schema_version: 1` and include:

- `group_id`
- `updated_at`
- `review_status`
- `triage_decision`
- `review_notes`
- `linked_case_or_issue`
- `reviewer_source`
- `source_record_ids`

Allowed `review_status` values are `new`, `reviewed`, `deferred`, and
`closed`. Allowed `triage_decision` values are `bug`, `support_candidate`,
`expected_unsupported`, `duplicate`, `no_action`, `needs_more_data`,
`parser_routing_risk`, and `ui_copy_issue`.

The overlay is joined to grouped feedback at review-read time. It is not
written into the original feedback record.

## Admin Feedback API

Admin review is available through a private frontend console at
`/admin/feedback` and backend endpoints under `/api/admin/feedback` when
explicitly enabled. `make query-feedback-export` remains the fallback review
workflow for terminal/offline review.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/feedback/groups` | List grouped feedback with triage overlays joined. |
| `GET` | `/api/admin/feedback/groups/{group_id}` | Read one group with normalized source records and a handoff summary. |
| `GET` | `/api/admin/feedback/groups/{group_id}/triage` | Read the mutable triage overlay for a group. |
| `PUT` | `/api/admin/feedback/groups/{group_id}/triage` | Save or update the mutable triage overlay for a group. |

Enable and token gate:

```text
NBATOOLS_ADMIN_FEEDBACK_ENABLED=true
NBATOOLS_ADMIN_TOKEN=<secret>
```

If `NBATOOLS_ADMIN_FEEDBACK_ENABLED` is unset or false, the admin endpoints
return a disabled `404` response. If `NBATOOLS_ADMIN_TOKEN` is set, callers
must send it in `X-NBATools-Admin-Token`. Deployed preview/production
environments require `NBATOOLS_ADMIN_TOKEN` when the admin endpoints are
enabled. The browser never receives R2 credentials.

The `/admin/feedback` console supports entering or pasting the admin token
after an unauthorized API response. The token is kept in React component state
for the current page session and sent only as `X-NBATools-Admin-Token` on admin
feedback API requests. The console does not store R2 credentials and does not
add public-facing navigation.

## Admin Feedback Console

Open `/admin/feedback` after building the frontend and starting the API. The
route is lazy-loaded like `/review` and `/visual-qa`; `/` remains the eager
public app.

The console can:

- list grouped feedback records from `/api/admin/feedback/groups`
- filter by review status, triage decision, feedback source, feedback type,
  route, status, and reason
- load selected group detail and the current triage overlay
- show representative query, count, first/last seen, route/status/reason,
  unsupported filters, user notes, sources/types, suggested triage, and saved
  overlay values
- save group-level triage overlays through
  `/api/admin/feedback/groups/{group_id}/triage`
- render and copy a handoff summary for ChatGPT or agent review

Overlay saves are mutable review decisions. They are written beside the
immutable feedback stream under `_triage_overlay` and do not update original
feedback records. The console does not edit QA corpora, create parser rules,
create GitHub issues, or change query/parser/result behavior.

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

Use the read-only exporter as a fallback or batch-review workflow to turn
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
