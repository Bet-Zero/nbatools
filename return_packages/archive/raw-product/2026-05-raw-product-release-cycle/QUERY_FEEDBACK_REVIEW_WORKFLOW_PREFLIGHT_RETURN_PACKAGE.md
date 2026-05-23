# Query Feedback Review Workflow Preflight Return Package

## 1. Executive summary

- Recommended decision: build a read-only Query Feedback Review Workflow V1
  around export, grouping, triage suggestions, and editable review artifacts.
- Best V1 scope: Option B - export script plus normalized outputs, Markdown
  review report, and a triage CSV template.
- Export outputs: Markdown review report, records CSV, normalized records JSONL,
  summary JSON, and editable triage decisions template CSV under
  `outputs/query_feedback_exports/<timestamp>/`.
- Triage workflow: group duplicate records, suggest review buckets, then require
  explicit human triage before converting anything into QA/product work.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

The existing feedback collection path is ready with notes and stores immutable
R2 JSON records under the verified preview fallback bucket/prefix:
`nbatools-data/query_feedback/preview`. V1 review tooling should not mutate or
delete those records. It should turn stored records into repeatable review
artifacts that can feed raw QA, frontend-copy QA, visual QA, data issues, parser
issues, unsupported-family promotion candidates, or no-action decisions.

## 2. Current feedback record shape

| Area | Finding | Notes |
|---|---|---|
| Schema version | `schema_version: 1` | Set by `src/nbatools/query_feedback.py`. Inspected preview records all used schema version 1. |
| Backend-generated fields | `id`, `created_at`, `schema_version`, `query_normalized_hash`, `source_page`, `environment`, `result_shape`, `metadata`, `notes`, `caveats`, `review_status`, `triage_decision` | `deployment` is added when Vercel deployment env fields are present. |
| Required submitted fields | `query`, `feedback_source`, `feedback_type` | `query` is required non-empty text capped at 500 chars. Source and type must match allowed enums. |
| Optional submitted/envelope fields | `route`, `status`, `reason`, `result_shape`, `metadata`, `notes`, `caveats`, `user_note`, `error_message`, `answer_text_preview`, `elapsed_ms` | Text fields are compacted and capped; missing values normalize to `null`, empty lists, or empty dicts depending on field. |
| `feedback_source` values | `automatic`, `user_submitted` | Frontend user reports submit `user_submitted`; backend diagnostics submit `automatic`. |
| `feedback_type` values | `wrong_answer`, `expected_supported`, `confusing_answer`, `no_result`, `unsupported`, `error`, `ui_issue`, `other` | Frontend defaulting maps errors to `error`, unsupported/no-result boundaries to `expected_supported` or `no_result`, and successful-answer reports to `wrong_answer` unless the user selects another type. |
| Route/status/reason | Optional compact text fields: `route`, `status`, `reason` | Current examples include `route=season_leaders`, `status=no_result`, `reason=filter_not_supported`; unrouted errors have `route=null`, `status=error`, `reason=unrouted`. |
| Metadata shape | Allowlisted compact dict | Includes supported diagnostic keys such as `applied_filters`, `answer_phrase`, `confidence`, `count_phrase`, `current_through`, date/season fields, entity contexts, `intent`, `metric`, `query_class`, `route`, `status`, `reason`, `stat`, `target_metric`, `target_stat`, and `unsupported_filters`. |
| Metadata privacy | Sanitizer drops disallowed fields and non-allowlisted metadata | Drops fields such as `email`, `name`, `ip`, `ip_address`, `user_id`, `account`, `phone`, `raw_result`, `result`, full raw result tables, and session replay fields. Lists, dicts, and text are capped. |
| Result shape | Compact dict with `query_class`, `section_keys`, and `section_row_counts` | Built from submitted `result_shape` or from result sections. It stores row counts only, not row bodies. |
| Notes/caveats | Lists of compact strings | Capped to 8 items. |
| User note | Optional compact text | Capped to 1000 chars. UI copy already asks users not to include personal information. |
| Error/answer previews | Optional compact text | `error_message` and `answer_text_preview` are capped to 500 chars. |
| Elapsed time | Optional non-negative number | Automatic slow query diagnostics use the 8000 ms warning threshold. |
| Review status default | `review_status: "new"` | Present in stored records. Because records are immutable in V1, this is not an in-place workflow state yet. |
| Triage decision support | `triage_decision: null` | Field exists, but there is no mutable R2 triage overlay or admin UI. V1 should use exported triage files instead of changing records. |
| Query hash support | `query_normalized_hash` | SHA-256 of lowercased whitespace-normalized query plus route/status/reason. This is the best first grouping key for duplicates. |
| Source page | Normalized path string, default `/` | Automatic diagnostics are suppressed for `/review` and `/visual-qa`; inspected records had no review/visual QA pollution. |
| Environment | `VERCEL_ENV`, `NBATOOLS_ENV`, `ENVIRONMENT`, or `local` | Preview records showed `environment=preview`. |
| Deployment | Optional dict with `vercel_url` and `vercel_git_commit_sha` | Present only when those env vars exist; it is compact deployment context, not user/device identity. |
| Storage key shape | `<prefix>/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json` | Verified preview shape is `query_feedback/preview/YYYY/MM/DD/<created_at_ms>_<short_random_id>.json`. |

## 3. Export/review requirements

| Requirement | Recommendation | Why |
|---|---|---|
| Storage input | Support both R2 prefix input and local folder input | R2 direct is needed for real launch review; local folder input is needed for tests, fixtures, offline review, and repeatable examples. |
| R2 bucket | Accept `--bucket`; current preview default should be `nbatools-data` | The dedicated feedback bucket is deferred; verified records are in the existing data bucket under isolated prefix `query_feedback/preview`. |
| R2 prefix | Accept `--prefix`; default to `query_feedback/preview` for current launch review | Keeps V1 aligned with the verified preview fallback. |
| Local input | Accept `--local-dir` containing downloaded JSON records | Lets tests avoid network/R2 credentials and lets reviewers re-run exports from archived snapshots. |
| No mutation | Read-only list/get only; never put/delete/copy R2 objects | Feedback records are immutable in V1. Original records must remain audit evidence. |
| No PII expansion | Export only sanitized record content and derived grouping fields | The exporter should not enrich records with user/device identity or raw result payloads. |
| Smoke handling | Exclude smoke records from launch review by default and count them separately | Preview smoke records are useful storage evidence but should not become product/QA backlog. |
| Duplicate handling | Group by normalized hash first, with fallback grouping | Review should triage repeated demand as a group instead of over-counting repeated automatic diagnostics. |
| Reportability | Produce Markdown for human review, CSV for spreadsheet triage, JSONL for machine reuse, and summary JSON for automation | This matches existing repo artifact conventions such as raw QA and frontend-copy QA reports. |
| Triage status | Export editable triage columns rather than changing source records | R2 records are immutable and there is no admin dashboard yet. |
| QA conversion | Suggest destinations and required fields; do not edit QA corpora automatically | QA corpora are curated contracts. Feedback is an input to triage, not a direct assertion. |
| Future admin UI | Defer | An admin dashboard is not needed for V1 and would add auth, mutation, and review-state complexity. |

## 4. CLI design

| Option | Purpose | Default |
|---|---|---|
| `--prefix query_feedback/preview` | R2 object prefix to list. | `query_feedback/preview` for the current preview workflow. |
| `--bucket nbatools-data` | R2 bucket to read. | `nbatools-data`, or explicit env-derived fallback if implementation chooses to read `QUERY_FEEDBACK_BUCKET_NAME` first. |
| `--since YYYY-MM-DD` or ISO timestamp | Include records at or after this created-at/object date boundary. | No lower bound. |
| `--until YYYY-MM-DD` or ISO timestamp | Include records before or at this boundary. | No upper bound. |
| `--source automatic,user_submitted` | Filter by `feedback_source`. | All sources. |
| `--feedback-type unsupported,error,no_result,...` | Filter by `feedback_type`. | All feedback types. |
| `--status no_result,error,ok` | Filter by stored `status`. | All statuses. |
| `--route season_leaders,team_record,...` | Filter by stored `route`. | All routes. |
| `--include-smoke` | Include records classified as smoke/test records in report groups. | False. |
| `--exclude-smoke` | Explicitly exclude smoke records. | True for launch review reports. |
| `--limit N` | Stop after N records after filtering, useful for probes. | Unlimited. |
| `--local-dir path` | Read JSON records from local files instead of R2. | Not set; R2 mode when absent. |
| `--output-dir path` | Base output directory. | `outputs/query_feedback_exports`. |
| `--run-id timestamp` | Optional stable output folder name for repeatable tests. | UTC timestamp like `20260518T123000Z`. |

Recommended command examples:

```bash
.venv/bin/python tools/export_query_feedback.py \
  --bucket nbatools-data \
  --prefix query_feedback/preview \
  --since 2026-05-18
```

```bash
.venv/bin/python tools/export_query_feedback.py \
  --local-dir tests/fixtures/query_feedback \
  --output-dir outputs/query_feedback_exports \
  --run-id fixture_smoke
```

Smoke-test filtering should classify a record as smoke/test evidence when any
of these are true:

- `query` contains `smoke` case-insensitively.
- `user_note` contains `Smoke test` or `smoke test` case-insensitively.
- `route` or `reason` is `smoke`.
- `feedback_type=other` with a direct endpoint smoke query.
- Future deployment/source labels explicitly identify smoke or test records.

Excluded smoke records should still be counted in `summary.json` as
`excluded_smoke_count`, but they should not appear in launch-review candidate
sections unless `--include-smoke` is passed.

## 5. Output design

| Output | Purpose | Notes |
|---|---|---|
| `outputs/query_feedback_exports/<timestamp>/feedback_review.md` | Human review report | Should include totals, grouped findings, high-priority groups, source/type/status/route breakdowns, smoke record count, automatic diagnostics, user-submitted reports, suggested triage buckets, and recommended next actions. |
| `outputs/query_feedback_exports/<timestamp>/feedback_records.csv` | Spreadsheet-friendly flat record export | One row per normalized record. Include core fields, smoke classification, group id, suggested triage, and compact metadata summaries. |
| `outputs/query_feedback_exports/<timestamp>/feedback_records.jsonl` | Machine-readable normalized records | One JSON object per record after filtering and normalization. Keep original sanitized record fields plus derived fields such as `group_id`, `is_smoke`, and `suggested_triage`. |
| `outputs/query_feedback_exports/<timestamp>/summary.json` | Automation summary | Include run id, filters, source mode, bucket/prefix/local dir, counts, output paths, duplicate group counts, excluded smoke count, high-priority group ids, and triage bucket counts. |
| `outputs/query_feedback_exports/<timestamp>/triage_decisions_template.csv` | Editable review worksheet | One row per group, not per raw record. Reviewer fills review status, final triage decision, linked case/issue id, notes, and next action. |

The Markdown report should include these sections:

- Run metadata and filters.
- Total records and excluded smoke records.
- Records by `feedback_source`.
- Records by `feedback_type`.
- Records by `status` and `reason`.
- Records by `route`.
- Duplicate groups.
- High-priority groups.
- Smoke-test records summary.
- Automatic diagnostics.
- User-submitted reports.
- Candidate raw QA cases.
- Candidate frontend-copy QA cases.
- Candidate visual QA cases.
- Unsupported-family candidates.
- Data issue candidates.
- Expected unsupported / no-action candidates.
- Recommended next actions.

Recommended normalized record fields:

- `id`
- `created_at`
- `schema_version`
- `feedback_source`
- `feedback_type`
- `query`
- `query_normalized`
- `query_normalized_hash`
- `source_page`
- `environment`
- `deployment_vercel_url`
- `deployment_vercel_git_commit_sha`
- `route`
- `status`
- `reason`
- `unsupported_filters`
- `metadata_summary`
- `result_query_class`
- `result_section_keys`
- `result_section_row_counts`
- `notes`
- `caveats`
- `user_note`
- `answer_text_preview`
- `error_message`
- `elapsed_ms`
- `review_status`
- `triage_decision`
- `is_smoke`
- `group_id`
- `suggested_triage`
- `triage_modifiers`
- `object_key`

## 6. Grouping and triage logic

Grouping should happen after filtering and smoke classification.

Primary grouping key:

```text
query_normalized_hash
```

Fallback grouping key when the hash is missing:

```text
normalized_query | route | status | reason | unsupported_filters | feedback_type
```

For each group, compute:

- `group_id`: deterministic short hash, such as `qfg_<12 hex chars>`.
- `count`.
- `first_seen`.
- `last_seen`.
- `representative_query`.
- `feedback_sources`.
- `feedback_types`.
- `routes`.
- `statuses`.
- `reasons`.
- `unsupported_filters`.
- `user_notes`.
- `record_ids`.
- `object_keys`.
- `suggested_triage`.
- `triage_modifiers`.

| Signal | Suggested triage | Notes |
|---|---|---|
| `status=error` and `reason=unrouted` | `parser_issue` | If representative queries describe a valid but unsupported product family, reviewer may change final decision to `unsupported_family`. |
| `status=no_result` and `reason=filter_not_supported` | `unsupported_family` or `expected_unsupported` | Use `unsupported_filters` and user notes to decide whether this is roadmap demand or an already-expected boundary. |
| `status=no_result` and `reason=no_data` | `data_issue` | Needs data freshness/source coverage review before treating it as parser or product scope. |
| `feedback_type=wrong_answer` | `raw_qa_case` | Candidate for backend/query behavior verification or a new guardrail case. |
| `feedback_type=confusing_answer` | `frontend_copy_case` | Candidate when backend output is likely correct but wording, hero text, or explanation is confusing. |
| `feedback_type=ui_issue` | `visual_qa_case` | Candidate for layout, overflow, density, hierarchy, or responsive rendering QA. |
| `feedback_source=automatic`, `status=ok`, and `elapsed_ms >= 8000` | `performance_review` | Export-only suggestion. Existing stored triage enum does not include this yet; do not mutate source records. |
| Duplicate count above threshold | `prioritize_review` modifier | Recommended threshold: 3 or more records in a group, or 2 or more user-submitted records. |
| `feedback_type=expected_supported` with unsupported/no-result state | `unsupported_family` modifier | Indicates a user thought the query should work even if the product boundary currently says no. |
| Smoke/test classification | `no_action` | Exclude from launch review by default; use only as storage/smoke evidence. |
| Existing `review_status` not `new` in future records | Preserve as input signal | Current V1 records are `new`; future overlay/admin workflows may set this elsewhere. |

The exporter should keep `suggested_triage` separate from reviewer-owned
`triage_decision`. Suggestions are heuristics and must not convert feedback into
QA failures automatically.

## 7. QA conversion workflow

- Raw QA candidates: use when the stored query may expose wrong backend/query
  behavior, a missing expected unsupported guardrail, wrong route/status/reason,
  wrong result shape, or a data-backed answer mismatch. Fields needed for a
  corpus case: stable case id, query, category, priority, expected status,
  expected route/reason/shape, expected sections, expected row counts, hard
  assertions if known, and review notes.
- Frontend-copy candidates: use when backend behavior appears acceptable but
  the rendered explanation, hero copy, no-result copy, filter chip wording, or
  table labels are confusing. Fields needed: linked backend case or query,
  category, review focus, expected semantic facts, expected filter-chip/table
  header fragments, and source backend run if promoted into the corpus.
- Visual QA candidates: use for layout, clipping, density, responsive behavior,
  visual hierarchy, or no-result/card presentation issues. Fields needed:
  query, category, viewport list, visual focus, desktop/mobile focus, and
  expected primary visual concerns.
- Unsupported-family candidates: use for repeated valid demand outside current
  product scope, especially `expected_supported` reports or automatic
  `filter_not_supported` groups with duplicate demand. Fields needed:
  representative query, phrase variants, current route/status/reason,
  unsupported filters, count, source mix, and product-boundary decision needed.
- Data issue candidates: use for `no_data`, missing R2/source coverage,
  freshness mismatches, suspicious source values, or verified data anomalies.
  Fields needed: query, route/status/reason, current-through date, seasons/dates
  involved, affected source/data object if known, observed behavior, expected
  behavior, and evidence path.
- No-action/expected unsupported: use for smoke records, duplicates of already
  tracked issues, known unsupported boundaries that are rendered correctly, or
  non-actionable records. Fields needed: rationale, linked existing case/issue
  if any, and reviewer notes.

The report should list candidates by destination, but conversion should remain
manual in V1. Do not automatically modify `qa/raw_query_answer_corpus.yaml`,
`qa/frontend_copy_corpus.yaml`, or `qa/frontend_visual_qa_corpus.json`.

## 8. Implementation options

| Option | Scope | Value | Risk | Recommendation |
|---|---|---|---|---|
| A - simple export script only | Read records and write flat CSV/JSONL. | Fastest path to inspect records. | Weak review workflow; duplicates and candidate buckets remain manual. | Too thin for launch feedback triage. |
| B - export script plus triage CSV template plus report | Read R2/local records, normalize, filter, group, suggest triage, and write Markdown/CSV/JSONL/summary/template outputs. | Best balance of repeatability, low production risk, and useful launch review. | Requires careful tests for grouping/filtering and clear docs so suggestions are not treated as facts. | Recommended V1. |
| C - export script plus automatic QA case generation drafts | Adds generated YAML/JSON draft cases for QA corpora. | Could speed later conversion. | High risk of treating untriaged feedback as assertions; generated cases may encode wrong expectations. | Defer. |
| D - admin page | Add UI for listing records, assigning statuses, and linking cases. | Best eventual reviewer ergonomics. | Requires auth, mutation model, overlay storage, UI work, and policy choices. | Defer until volume justifies it. |

## 9. Recommended execution scope

- Exact goal: implement Query Feedback Review Workflow V1 as operational
  tooling that reads immutable sanitized feedback records, writes review
  artifacts, and never changes query behavior or source feedback records.
- Files likely to change:
  - `tools/export_query_feedback.py`
  - `tests/test_export_query_feedback.py`
  - `docs/operations/query_feedback_review.md`
  - `Makefile` optionally, for `query-feedback-export`
- Tests to add:
  - Local fixture export creates Markdown, CSV, JSONL, summary JSON, and triage
    template.
  - R2 listing/get is mocked and uses only read operations.
  - Date filtering supports `YYYY-MM-DD` and ISO timestamps.
  - Source/type/status/route filters work independently and together.
  - Smoke records are excluded by default.
  - Smoke records are included with `--include-smoke`.
  - Grouping uses `query_normalized_hash` when present.
  - Fallback grouping works when hash is missing.
  - Suggested triage buckets match the documented heuristics.
  - Duplicate groups add the prioritize-review modifier above threshold.
  - Exported outputs do not include raw result rows or disallowed PII fields
    beyond already-sanitized record content.
  - No calls to R2 `put_object`, `delete_object`, or copy/mutation operations.
- Docs to update:
  - Expand `docs/operations/query_feedback_review.md` with the new command,
    output paths, filter semantics, smoke exclusion policy, triage template
    workflow, and QA conversion rules.
  - Do not update query catalog/current-state docs from feedback export alone.
- Validation commands:
  - `make test-output`
  - `.venv/bin/ruff check tools/export_query_feedback.py tests/test_export_query_feedback.py`
  - `git diff --check`
  - Optional real read-only preview export when credentials are available:
    `.venv/bin/python tools/export_query_feedback.py --bucket nbatools-data --prefix query_feedback/preview --since 2026-05-18`
- Stop conditions:
  - Implementation would need to mutate, delete, or rewrite R2 feedback records.
  - Implementation would require storing PII, raw result rows, IP/device
    identifiers, session replay, or frontend R2 credentials.
  - Export suggestions would be wired to automatically edit QA corpora.
  - Direct R2 credentials are unavailable and local fixture coverage is not yet
    in place.
  - Feedback schema mismatches are found and cannot be represented safely in
    normalized outputs.

## 10. Deferred ideas

- Admin dashboard.
- Mutable R2 triage overlay records under `query_feedback_triage/<record_id>.json`.
- Automatic corpus-case draft generation.
- GitHub issue creation.
- Feedback volume dashboards.
- Dedup/rate limiting improvements.
- Dedicated feedback bucket and scoped read/write token.
- Request/trace IDs to connect automatic diagnostics and user-submitted follow-up
  records from the same query event.

## 11. Validation performed

No production code, frontend rendering, backend query behavior, parser behavior,
feedback collection behavior, or QA corpora were changed during this preflight.
No R2 objects were listed, read, mutated, or deleted during this preflight; the
R2 conclusions here rely on the latest checked-in inspection evidence.

Post-write validation:

- `git diff --check` produced no whitespace errors.
- The explicit trailing-whitespace probe found no matches.
- `git status --short` showed only the new preflight return package.
- No test suite was run because this was a documentation/design-only preflight
  with no production, test, frontend, backend, parser, or corpus changes.

Files inspected:

- `return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_PREVIEW_R2_ENABLE_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_V1_RETURN_PACKAGE.md`
- `return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_PREFLIGHT_RETURN_PACKAGE.md`
- `docs/operations/query_feedback_review.md`
- `docs/operations/deployment.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `src/nbatools/query_feedback.py`
- `src/nbatools/data_source.py`
- `frontend/src/components/queryFeedbackPayload.ts`
- `frontend/src/api/types.ts`
- `qa/raw_query_answer_corpus.yaml`
- `qa/frontend_copy_corpus.yaml`
- `qa/frontend_visual_qa_corpus.json`
- `tools/raw_query_answer_qa.py`
- `tools/deployment_smoke.py`
- `tools/parser_examples_full_sweep.py`
- `tests/test_query_feedback.py`
- `tests/test_data_source.py`
- `tests/test_raw_query_answer_qa.py`
- `frontend/src/test/frontendCopyQaHarness.tsx`
- `Makefile`
- `pyproject.toml`
- `.gitignore`
- `return_packages/raw-product/`
- `tools/`
- `outputs/`

Commands/probes run:

```bash
git status --short
sed -n '1,260p' src/nbatools/query_feedback.py
sed -n '260,620p' src/nbatools/query_feedback.py
sed -n '620,980p' src/nbatools/query_feedback.py
sed -n '1,260p' docs/operations/query_feedback_review.md
sed -n '1,260p' frontend/src/components/queryFeedbackPayload.ts
sed -n '1,280p' return_packages/raw-product/QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md
sed -n '1,300p' return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_V1_RETURN_PACKAGE.md
sed -n '1,260p' return_packages/raw-product/QUERY_FEEDBACK_PREVIEW_R2_ENABLE_RETURN_PACKAGE.md
sed -n '1,260p' docs/operations/deployment.md
sed -n '1,220p' Makefile
sed -n '1,260p' pyproject.toml
rg --files tools qa outputs
sed -n '1,180p' qa/raw_query_answer_corpus.yaml
sed -n '1,180p' qa/frontend_copy_corpus.yaml
sed -n '1,180p' qa/frontend_visual_qa_corpus.json
sed -n '1,260p' tools/raw_query_answer_qa.py
sed -n '1,260p' tools/deployment_smoke.py
sed -n '1,260p' tools/parser_examples_full_sweep.py
rg -n "create_r2_client|list_objects_v2|get_object|boto3|R2Config|load_r2_config" src tools tests
sed -n '1,260p' src/nbatools/data_source.py
sed -n '1,260p' tests/test_query_feedback.py
sed -n '240,340p' tests/test_query_feedback.py
sed -n '1,260p' tests/test_data_source.py
sed -n '170,240p' frontend/src/api/types.ts
sed -n '1,340p' return_packages/raw-product/QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_PREFLIGHT_RETURN_PACKAGE.md
sed -n '480,530p' docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md
sed -n '130,230p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md
sed -n '180,215p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md
rg -n "frontend_copy_qa|frontend_copy_report|frontend visual|visual_qa|raw_query_answer_qa|report.jsonl|summary.json|report.md" tools frontend/src/test tests
sed -n '2100,2185p' tools/raw_query_answer_qa.py
sed -n '380,420p' frontend/src/test/frontendCopyQaHarness.tsx
sed -n '1,140p' tests/test_raw_query_answer_qa.py
rg -n "write_jsonl|write_markdown|summary" tools/raw_query_answer_qa.py frontend/src/test/frontendCopyQaHarness.tsx
ls return_packages/raw-product
sed -n '1,220p' .gitignore
git diff --check
git status --short
sed -n '1,220p' return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_PREFLIGHT_RETURN_PACKAGE.md
sed -n '220,520p' return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_PREFLIGHT_RETURN_PACKAGE.md
wc -l return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_PREFLIGHT_RETURN_PACKAGE.md
git diff --no-index --check /dev/null return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_PREFLIGHT_RETURN_PACKAGE.md
rg -n "[[:blank:]]$" return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_PREFLIGHT_RETURN_PACKAGE.md
```
