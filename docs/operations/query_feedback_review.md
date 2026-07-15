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
   (bucket `nbatools-feedback`, prefix `query_feedback`) and writes the
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

4. **Fill the triage worksheet or admin overlay.**

   ```text
   outputs/query_feedback_exports/<run_id>/triage_decisions_template.csv
   ```

   `triage_decisions_template.csv` is the editable review worksheet. One
   row per group. Fill `review_status`, the chosen triage category,
   `linked_case_id` when a group becomes a QA case or planning item,
   `reviewer_notes`, `next_action`, and the engineering fix category from
   [Engineering fix categories](#engineering-fix-categories). The
   `/admin/feedback` console stores the same review decision as a mutable
   triage overlay beside the immutable feedback stream. See
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

### Engineering fix categories

After the product triage decision is chosen, add exactly one engineering
fix category to the worksheet `reviewer_notes` / `next_action` fields or to
the admin overlay `review_notes`. This category tells an agent where to start
and which validation path to use.

```text
review_status: new | reviewed | deferred | closed
triage_decision: bug | support_candidate | expected_unsupported | duplicate |
  no_action | needs_more_data | parser_routing_risk | ui_copy_issue
engineering_fix_category: parser_routing | backend_data |
  frontend_rendering | unsupported_future | ambiguous_clarification |
  typo_alias | corpus_expectation | stale_freshness |
  product_should_not_support
linked_case_or_issue: <QA case id, issue id, or planning pointer>
next_action: <smallest executable follow-up>
closure_evidence: <tests, Raw QA case/run, visual review, docs, or deferral>
```

The engineering category is not written into immutable source feedback
records. Source records remain immutable; persistent review state belongs in
the triage overlay described in [Mutable Triage Overlay](#mutable-triage-overlay).

## Feedback Category To Fix Path

Use this table after triage. It is intentionally a routing map, not a
replacement for the detailed runbooks it links to.

| Engineering category | Use when | Likely files touched | Required tests/checks | Optional tests/checks | Raw QA requirement | Frontend visual/render requirement | Route metadata/docs requirement | Feature promotion applies? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `parser_routing` | Query routes wrong, fails to route, drops a slot, or erodes an unsupported boundary. | Parser helpers, entity resolution, natural query routing. | `make test-parser`; `make test-query`; follow [`parser_routing_growth_guardrails.md`](parser_routing_growth_guardrails.md). | `make test-preflight` for high fan-in parser/routing changes. | Required when public behavior, route, status, reason, filters, or boundary changes. | Only if result copy/layout changes. | Update route input metadata and query docs when accepted inputs or boundaries change. | Yes if a previously unsupported capability becomes supported. |
| `backend_data` | Route is right, but calculation, filtering, data coverage, source trust, or result shape is wrong. | Command modules, shared command helpers, data/freshness utilities, data contracts. | `make test-engine`; run the affected Raw QA case or slice if query behavior changes. | `make test-query`; `make test-api`; `make test-preflight` for shared helpers or data contracts. | Required when the returned contract or public answer changes. | Only if renderer behavior changes. | Update result/data docs when contracts or coverage semantics move. | Yes for new supported data-backed capability. |
| `frontend_rendering` | Backend response is acceptable, but UI copy, chips, density, overflow, hierarchy, or rendering is confusing. | Frontend components, styles, API types/client if needed. | `npm --prefix frontend test`; `npm --prefix frontend run build`; `npm --prefix frontend run lint`. | Targeted review from [`frontend_visual_qa.md`](frontend_visual_qa.md). | Not required when backend result shape and behavior are unchanged. | Required for layout, overflow, hierarchy, or visible copy changes. | Update UI docs only when durable UI behavior changes. | Only if the UI change is part of a new supported capability. |
| `unsupported_future` | Valid stat-shaped demand is outside the current product boundary. | Usually none until a promotion is approved. | Record deferral or promotion preflight. | Raw QA unsupported-boundary guard if repeated demand risks drift. | Not required unless adding a boundary guard or promoting. | No, unless promotion changes rendering. | Document only durable product decisions. | Yes before support ships. |
| `ambiguous_clarification` | Query is valid-looking but needs clarification, not a silent broad answer. | Parser/routing, no-result/unsupported handling, possibly frontend clarification UI. | `make test-parser`; `make test-query`. | `make test-api`; frontend tests if clarification UI changes. | Required if public ambiguity behavior is pinned or changed. | Required only if clarification UI/copy changes. | Update docs/metadata if a new ambiguity reason or guidance shape ships. | Yes if ambiguity is resolved by adding supported capability. |
| `typo_alias` | Misspelling, nickname, abbreviation, or partial entity behavior is wrong or unclear. | Entity resolution, alias tables, parser helpers. | `make test-parser`; `make test-query`. | Targeted Raw QA case for public alias or typo boundary changes. | Required when accepted aliases or typo boundaries change. | No, unless UI copy changes. | Update query docs when alias support or typo policy changes. | Yes for fuzzy matching or broader alias policy. |
| `corpus_expectation` | Behavior is correct or intentionally changed, but a Raw QA expectation, slice, family tag, or review metadata is wrong. | Raw QA corpus, slice, or acceptance-family metadata only. | Targeted Raw QA case/slice from [`raw_query_answer_qa.md`](raw_query_answer_qa.md); check current terms in [`query_validation_map.md`](query_validation_map.md). | Full public acceptance slice when family metadata changes. | This is the work item. | No, unless the case exists to validate UI-derived copy/layout separately. | Update validation map only when durable scoreboard/current evidence changes. | Only if expectation change reflects a promoted capability. |
| `stale_freshness` | Answer is confusing because data is stale, freshness metadata is missing, or source coverage/R2 availability is wrong. | Freshness utilities, pipeline/source config, deployment/data docs, API freshness surfaces. | Relevant engine/API tests for freshness or data availability. | Deployment smoke or R2 verification when runtime data availability is involved. | Not required when refresh/freshness contract fixes the issue without changing query semantics. | Required only if freshness UI changes. | Update freshness/data docs when contract or coverage semantics change. | Yes for new data-backed support; no for routine refresh. |
| `product_should_not_support` | Product decision says the request should remain unsupported. | Parser guards and docs only if the current system answers too broadly. | Parser/query tests if a guard changes behavior. | Raw QA boundary case if drift risk exists. | Required only when adding or tightening a boundary guard. | No, unless unsupported copy changes. | Update query catalog/guide when the durable boundary changes. | No, unless later reversed into support. |

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
- Idempotent user-submission key shape:
  `query_feedback/submissions/<submission_uuid>.json`; the write uses an
  absent-object precondition, so retrying the same receipt cannot create a
  second accepted record
- Admission quota: at most 20 newly stored submissions per client/IP per rolling
  24 hours; HTTP 429 includes `Retry-After`, while a conditional replay returns
  the original deterministic feedback receipt without consuming another slot

The May 18, 2026 preview inspection verified historical records in bucket
`nbatools-data` under isolated prefix `query_feedback/preview` because the
dedicated feedback bucket was unavailable. That evidence does not satisfy the
current least-privilege contract; deployed feedback stays disabled until the
dedicated feedback credential tuple is configured. The historical key shape
was:

```text
query_feedback/preview/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json
```

Generated QA evidence and current scoreboard terminology are documented in
[`query_validation_map.md`](query_validation_map.md).

The endpoint is backend-owned. The frontend never receives R2 credentials and
does not write directly to storage.

Backend collection, export, and admin review use the dedicated
`QUERY_FEEDBACK_R2_ACCOUNT_ID`, `QUERY_FEEDBACK_R2_ACCESS_KEY_ID`, and
`QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY` tuple. They do not fall back to the
canonical-data `R2_*` credentials, and exact access-key/secret aliasing fails
closed. Keep canonical runtime data credentials read-only and scope the feedback
token only to the feedback bucket.

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
  --bucket nbatools-feedback \
  --prefix query_feedback \
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

Default export source under the least-privilege contract:

- bucket: `nbatools-feedback`
- prefix: `query_feedback`
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
2. Fill `review_status` with the same values used by the admin overlay:
   `new`, `reviewed`, `deferred`, or `closed`.
3. Fill `triage_decision` only after human review.
4. Add a `linked_case_id` when the group becomes a QA case, data issue, product
   issue, or planning item.
5. Add the engineering fix category from
   [Engineering fix categories](#engineering-fix-categories).
6. Use `reviewer_notes`, `next_action`, and closure evidence to record the
   manual decision.

Do not mutate source R2 records during this process. For persistent review
state, use the authenticated admin overlay workflow. The overlay updates only
the review object for the group; it does not update the original feedback
records.

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

## Do Not Add A Raw QA Case When

Not every feedback item becomes a Raw QA case. Do not add a Raw QA case for:

- duplicate feedback already covered by an existing case, issue, or planning
  item
- one-off malformed input outside the supported boundary
- frontend-only rendering bugs when backend route/status/result shape is
  unchanged
- stale data issues where a data refresh, coverage fix, or freshness contract
  is the actual fix
- product decisions that intentionally remain unsupported, unless boundary
  drift risk needs a guard
- feedback that has not been reproduced or classified

Add Raw QA only when it pins query-engine behavior: expected status, route,
reason, filters, result shape, sections, row counts, hard assertions, or an
unsupported-boundary guard. Use [`raw_query_answer_qa.md`](raw_query_answer_qa.md)
for the detailed harness workflow and [`query_validation_map.md`](query_validation_map.md)
for current evidence terminology.

## Triage Statuses

Use the same statuses in the exported worksheet and the admin triage overlay:

- `new`
- `reviewed`
- `deferred`
- `closed`

`reviewed` means the group has a final triage decision but follow-up may still
be pending. `deferred` means the next action is intentionally paused on product
decision, data availability, or missing repro. `closed` means the closure
evidence for the engineering category has been recorded.

## Triage Decisions

Use these product-level decisions in the admin overlay and in
`triage_decisions_template.csv`:

- `bug`
- `support_candidate`
- `expected_unsupported`
- `duplicate`
- `no_action`
- `needs_more_data`
- `parser_routing_risk`
- `ui_copy_issue`

The exporter still provides `suggested_triage` buckets such as `raw_qa_case`,
`parser_issue`, `data_issue`, `frontend_copy_case`, and `visual_qa_case`. Those
are sorting hints. The reviewer-owned `triage_decision` and engineering fix
category are the durable handoff.

## Closure Criteria

Close a group only when the worksheet or overlay records the evidence that
matches its engineering category:

| Engineering category | Closure evidence |
| --- | --- |
| `parser_routing` | Repro classified; targeted parser/query tests pass; Raw QA case added or updated when public behavior changes; parser/routing guardrails checked. |
| `backend_data` | Calculation/data fix verified by engine tests; affected Raw QA case or slice passes when public answer/contract changes; data/freshness contract updated when needed. |
| `frontend_rendering` | Frontend tests pass; frontend build and lint pass; visual/render review completed when layout, overflow, hierarchy, or visible copy changed. |
| `unsupported_future` | Product deferral or promotion preflight pointer recorded; no behavior change made unless promotion follows [`feature_promotion_rules.md`](feature_promotion_rules.md). |
| `ambiguous_clarification` | Ambiguous behavior reproduced and pinned; parser/query tests pass; Raw QA guard exists when public ambiguity behavior changes. |
| `typo_alias` | Alias or typo policy decision recorded; parser/query tests pass; Raw QA guard added when public alias or typo-boundary behavior changes. |
| `corpus_expectation` | Raw QA expectation, slice, or family metadata corrected; targeted case/slice passes; current evidence wording remains consistent with [`query_validation_map.md`](query_validation_map.md). |
| `stale_freshness` | Refresh, coverage, R2 availability, or freshness contract fix verified; API/UI checks pass when freshness surfaces changed; no unnecessary corpus case added. |
| `product_should_not_support` | Durable boundary decision recorded; query docs updated if boundary changed; Raw QA unsupported guard added only when drift risk exists. |

## Privacy and Retention

Do not add names, emails, user accounts, IP addresses, phone numbers, precise
device fingerprints, or session replay to feedback records. User notes are
capped and the UI asks users not to include personal information.

Recommended retention is 90 days for raw feedback records unless a record has
been converted into a QA case, data issue, or product planning artifact.
