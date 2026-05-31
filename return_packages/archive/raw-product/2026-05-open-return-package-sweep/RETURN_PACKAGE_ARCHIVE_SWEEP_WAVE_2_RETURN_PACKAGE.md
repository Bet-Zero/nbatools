# Return Package Archive Sweep Wave 2 — Return Package

## Summary

Wave 2 of the Return Package Archive Sweep archived all remaining completed Raw
Product return packages after Return Package Dependency Cleanup Wave 1 eliminated
every exact return-package path reference from durable docs.

## Counts

| Count | Value |
| --- | ---: |
| Raw-product package files before Wave 2 | 42 |
| Files moved to archive in Wave 2 | 42 |
| Files left active after Wave 2 | 0 |
| Archive directory total files after Wave 2 (including manifest) | 122 |

## Destination

`return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`

## Exact Path Scan Result

Command:

```text
rg --no-filename -o "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md | sort -u
```

Result: **0 matches** — no exact return-package paths remained in docs,
`README.md`, or `AGENTS.md` before the Wave 2 move. All 42 active packages were
eligible for archival.

## Archive Manifest Update Summary

File updated:
`return_packages/archive/raw-product/2026-05-raw-product-release-cycle/ARCHIVE_MANIFEST.md`

Changes:
- Added Wave 2 archive scope entry (sweep date, candidate rule).
- Added Wave 2 count table.
- Added cumulative count table (121 total packages archived, 122 archive files).
- Relabeled Wave 1 sections with "Wave 1:" prefix for clarity.
- Added "Wave 2: Moved Packages" section listing all 42 files moved.
- Updated Docs Reference Validation section with Wave 2 scan result.
- Updated Validation table to show per-wave results.

## Files Changed Summary

| Operation | Count |
| --- | ---: |
| `git mv` (package moves) | 42 |
| Manifest update (`ARCHIVE_MANIFEST.md`) | 1 |
| New file (this return package) | 1 |
| **Total files changed** | **44** |

### Packages Moved (42)

- `APP_THEMING_TEST_DRIFT_FIX_RETURN_PACKAGE.md`
- `CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md`
- `CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md`
- `DIVISION_PHRASE_BOUNDARY_CLEANUP_RETURN_PACKAGE.md`
- `ENTITY_SUMMARY_RECORD_WHEN_FILTER_FOLLOWUP_RETURN_PACKAGE.md`
- `EXPANDED_VISUAL_QA_MANUAL_BASELINE_RETURN_PACKAGE.md`
- `FINAL_PUBLIC_UI_RELEASE_REVIEW_RETURN_PACKAGE.md`
- `FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md`
- `FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md`
- `FRONTEND_SCREENSHOT_VISUAL_QA_PREFLIGHT_RETURN_PACKAGE.md`
- `FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_2_RETURN_PACKAGE.md`
- `NATURAL_QUERY_CONSTANTS_EXTRACTION_WAVE_1_RETURN_PACKAGE.md`
- `NATURAL_QUERY_EXTRACTION_PREFLIGHT_RETURN_PACKAGE.md`
- `NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_COVERAGE_RETURN_PACKAGE.md`
- `OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`
- `OPPONENT_CONFERENCE_PREVIEW_SMOKE_RERUN_RETURN_PACKAGE.md`
- `OPPONENT_CONFERENCE_PROMOTION_RETURN_PACKAGE.md`
- `POST_REVIEW_HARDENING_CLOSURE_REFRESH_RETURN_PACKAGE.md`
- `QUERY_FEEDBACK_DIAGNOSTIC_LOGGING_V1_RETURN_PACKAGE.md`
- `QUERY_FEEDBACK_PREVIEW_R2_ENABLE_RETURN_PACKAGE.md`
- `QUERY_FEEDBACK_R2_RECORD_INSPECTION_RETURN_PACKAGE.md`
- `QUERY_FEEDBACK_REVIEW_WORKFLOW_V1_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_1_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_2_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_3_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_4_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_5_RETURN_PACKAGE.md`
- `RAW_PRODUCT_HARDENING_WAVE_6_RETURN_PACKAGE.md`
- `RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`
- `RAW_PRODUCT_RELEASE_PACKAGE_REFRESH_AFTER_R2_SYNC_FIX_RETURN_PACKAGE.md`
- `RAW_PRODUCT_RELEASE_READINESS_CHECKLIST_RETURN_PACKAGE.md`
- `RAW_QA_HARNESS_EFFICIENCY_WAVE_1_RETURN_PACKAGE.md`
- `RETURN_PACKAGE_ARCHIVE_SWEEP_WAVE_1_RETURN_PACKAGE.md`
- `RETURN_PACKAGE_DEPENDENCY_CLEANUP_PREFLIGHT_RETURN_PACKAGE.md`
- `RETURN_PACKAGE_DEPENDENCY_CLEANUP_WAVE_1_RETURN_PACKAGE.md`
- `REVIEWPAGE_EXHAUSTIVE_DEPS_WARNING_CLEANUP_RETURN_PACKAGE.md`
- `VISUAL_QA_CORPUS_EXPANSION_RETURN_PACKAGE.md`
- `VISUAL_QA_SCREENSHOT_ARTIFACT_VALIDATION_DOCS_REFRESH_RETURN_PACKAGE.md`
- `VISUAL_QA_TARGETED_FIX_WAVE_1_RETURN_PACKAGE.md`
- `VITE_INTERNAL_ROUTE_LAZY_SPLIT_RETURN_PACKAGE.md`
- `WEAK_CONTRACT_CLEANUP_WAVE_1_RETURN_PACKAGE.md`
- `WEAK_CONTRACT_DECISION_PREFLIGHT_RETURN_PACKAGE.md`

## Release Impact

Wave 2 changes only return-package organization. It does not change production
code, tests, QA corpus files, generated outputs, release statuses,
parser/routing behavior, frontend behavior, API behavior, data contracts, or
durable release/readiness docs.

## Validation

| Command / check | Result |
| --- | --- |
| Exact path scan (docs/README/AGENTS) | Passed — 0 matches before move |
| `git diff --check` | Passed |
| `git diff --cached --check` | Passed |
| Markdown lint | Not run — no linter found on PATH |
