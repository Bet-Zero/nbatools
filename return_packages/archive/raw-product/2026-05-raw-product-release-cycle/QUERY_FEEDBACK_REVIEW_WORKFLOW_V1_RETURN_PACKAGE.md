# Query Feedback Review Workflow V1 Return Package

## 1. Executive summary

- What changed: added a read-only query feedback export/review workflow with
  local and R2 input modes, normalized record outputs, grouping, heuristic
  triage suggestions, a Markdown review report, and an editable triage template.
- Production code changed? no
- Frontend changed? no
- Query behavior changed? no
- R2 records mutated? no
- Export script: `tools/export_query_feedback.py`
- Outputs created: `feedback_review.md`, `feedback_records.csv`,
  `feedback_records.jsonl`, `summary.json`, and
  `triage_decisions_template.csv`
- Tests: `tests/test_export_query_feedback.py`
- Recommended next step: run first real feedback review export against the
  preview prefix, then manually fill the triage template.

## 2. Export workflow

| Capability | Implementation | Notes |
|---|---|---|
| R2 input | `load_r2_records()` lists and gets JSON objects using Cloudflare R2/S3 read APIs. | Uses `list_objects_v2` and `get_object` only. |
| Local input | `--local-dir` recursively reads local `*.json` files. | Used for tests, fixtures, and offline review. |
| Normalization | `normalize_record()` writes a fixed flat contract. | Keeps sanitized fields, compact metadata, result shape, and derived review fields. |
| Smoke filtering | `is_smoke_record()` marks smoke/test evidence. | Excluded by default, included with `--include-smoke`. |
| Grouping | `group_records()` groups by `query_normalized_hash`, then fallback fields. | Adds deterministic `qfg_<hash>` group ids. |
| Suggested triage | `suggest_triage()` applies documented heuristics. | Separate from reviewer-owned `triage_decision`. |
| Output writing | CSV, JSONL, summary JSON, Markdown, and triage CSV writers. | Writes under `outputs/query_feedback_exports/<run_id>/`. |
| Make target | `make query-feedback-export` | Thin wrapper around the exporter. |

## 3. CLI options

| Option | Purpose | Default |
|---|---|---|
| `--bucket` | R2 bucket to read. | `nbatools-data` |
| `--prefix` | R2 prefix to list. | `query_feedback/preview` |
| `--since` | Include records at or after `YYYY-MM-DD` or ISO timestamp. | none |
| `--until` | Include records at or before `YYYY-MM-DD` or ISO timestamp. | none |
| `--source` | Filter by `feedback_source`; repeatable/comma-separated. | all |
| `--feedback-type` | Filter by `feedback_type`; repeatable/comma-separated. | all |
| `--status` | Filter by stored status; repeatable/comma-separated. | all |
| `--route` | Filter by stored route; repeatable/comma-separated. | all |
| `--include-smoke` | Include smoke/test records while marking `is_smoke=true`. | false |
| `--exclude-smoke` | Explicit default smoke exclusion. | true |
| `--limit` | Cap exported records after filtering and smoke handling. | unlimited |
| `--local-dir` | Read local JSON records instead of R2. | unset |
| `--output-dir` | Base output directory. | `outputs/query_feedback_exports` |
| `--run-id` | Stable run output folder name. | UTC timestamp |

## 4. Output artifacts

| File | Purpose | Notes |
|---|---|---|
| `feedback_review.md` | Human review report. | Includes metadata, filters, counts, duplicate/high-priority groups, diagnostics, user reports, candidate buckets, and next actions. |
| `feedback_records.csv` | Spreadsheet-friendly normalized records. | One row per exported record. |
| `feedback_records.jsonl` | Machine-readable normalized records. | One JSON object per exported record. |
| `summary.json` | Automation summary. | Includes source mode, filters, counts, group count, high-priority group ids, triage counts, and output paths. |
| `triage_decisions_template.csv` | Editable review worksheet. | One row per group with blank reviewer-owned decision fields. |

## 5. Grouping/triage behavior

| Signal | Suggested triage | Notes |
|---|---|---|
| `status=error` and `reason=unrouted` | `parser_issue` | Candidate parser/routing review. |
| `status=no_result` and `reason=filter_not_supported` | `unsupported_family` | Candidate product-boundary review. |
| `status=no_result` and `reason=no_data` | `data_issue` | Candidate data coverage/freshness review. |
| `feedback_type=wrong_answer` | `raw_qa_case` | Candidate raw QA case after manual verification. |
| `feedback_type=confusing_answer` | `frontend_copy_case` | Candidate copy QA case after manual verification. |
| `feedback_type=ui_issue` | `visual_qa_case` | Candidate visual QA case after manual verification. |
| `feedback_source=automatic`, `status=ok`, `elapsed_ms >= 8000` | `performance_review` | Slow-query diagnostic. |
| smoke/test evidence | `no_action` | Excluded by default; storage evidence only. |
| duplicate group count >= 3 or user-submitted count >= 2 | `prioritize_review` modifier | Reviewer should inspect first. |

## 6. Validation

- `.venv/bin/pytest tests/test_export_query_feedback.py -q`:
  `7 passed`
- `.venv/bin/ruff check tools/export_query_feedback.py tests/test_export_query_feedback.py`:
  passed
- `git diff --check`: passed
- Optional real R2 export: not run in this pass; local fixture coverage and
  mocked R2 read-only coverage passed.

## 7. Files changed

| File | Change type | Why |
|---|---|---|
| `tools/export_query_feedback.py` | added | Read-only exporter, normalization, grouping, triage, and artifact writers. |
| `tests/test_export_query_feedback.py` | added | Local-mode and mocked R2 coverage for outputs, filtering, grouping, smoke policy, triage, privacy, and read-only behavior. |
| `docs/operations/query_feedback_review.md` | updated | Added command examples, output contract, filters, smoke policy, triage workflow, and QA conversion rules. |
| `Makefile` | updated | Added `query-feedback-export` convenience target. |
| `return_packages/raw-product/QUERY_FEEDBACK_REVIEW_WORKFLOW_V1_RETURN_PACKAGE.md` | added | Captures implementation and validation status. |

## 8. Current limitations

- No admin dashboard.
- No mutable triage overlay.
- Suggestions are heuristic.
- Corpus updates remain manual.

## 9. Next recommendation

Run first real feedback review export.
