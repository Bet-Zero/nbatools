# Return Package Archive Sweep Preflight

## 1. Scope

This is a preflight only. It does not move, rename, archive, delete, or edit
existing return packages. It does not change production code, tests, release
statuses, product behavior, parser/routing behavior, frontend behavior, or
durable release/readiness docs.

The goal is to plan a safe cleanup for completed Raw Product return packages so
point-in-time evidence artifacts stop competing visually with durable
source-of-truth docs.

Current recommendation:

1. Use `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`
   as the first archive destination.
2. Keep current release/readiness evidence in
   `return_packages/raw-product/` until the release package, handoff,
   readiness checklist, and checkpoint no longer depend on those exact paths or
   are updated in the same sweep.
3. Make the first execution sweep only for packages that are not linked by
   current docs.
4. Do not delete return packages.

## 2. Evidence Reviewed

Required inputs inspected:

- `docs/index.md`
- `AGENTS.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `return_packages/raw-product/`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`

Supporting context inspected:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`
- `docs/operations/query_feedback_review.md`
- `docs/archive/`
- `return_packages/`

## 3. Inventory Summary

Current `return_packages/raw-product/` state:

| Inventory check | Result |
| --- | --- |
| Markdown files directly under `return_packages/raw-product/` | 117 |
| Subdirectories under `return_packages/raw-product/` | 0 |
| Unique raw-product return packages linked from docs | 39 |
| Raw-product docs/files with exact `return_packages/raw-product/...` links | 17 |
| Root-level `archive/` directory | Absent |
| Existing return-package topics | `raw-product`, `result_display`, `review` |

Filename-prefix inventory:

| Prefix | Count |
| --- | ---: |
| `RAW_*` | 44 |
| `FRONTEND_*` | 14 |
| `VISUAL_*` | 8 |
| `QUERY_*` | 7 |
| `OPPONENT_*` | 5 |
| `NATURAL_*` | 5 |
| `FRONT_*` | 4 |
| `FINAL_*` | 3 |
| `DIVISION_*` | 3 |
| `WEAK_*` | 2 |
| `VITE_*` | 2 |
| `PRODUCT_*` | 2 |
| `LEADERBOARD_*` | 2 |
| `CORE_*` | 2 |
| Single-file prefixes | 14 |

The directory is acting as a flat history of multiple workstreams:

- raw query answer QA harness, corpus, and fix waves
- release readiness, release package, preview QA, and handoff waves
- opponent-conference promotion and R2 preview evidence
- query feedback implementation, preview, inspection, and workflow evidence
- visual QA, frontend-copy QA, and public result UI evidence
- post-review hardening Waves 1-6
- deferred preflights and small cleanup evidence such as Vite and
  `ReviewPage` cleanup packages

## 4. Exact-Path Link Findings

Docs currently link directly to Raw Product return packages by exact path.
Moving linked packages without updating those docs would break useful evidence
links.

Docs with exact raw-product package references:

| Doc | Exact references |
| --- | ---: |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | 31 |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | 17 |
| `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` | 17 |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | 15 |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | 11 |
| `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md` | 7 |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | 5 |
| `docs/planning/raw-product/LEADERBOARD_SUPPORTING_COLUMNS_PREFLIGHT.md` | 4 |
| `docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md` | 3 |
| `docs/planning/raw-product/VISUAL_QA_SCREENSHOT_AUTOMATION_PREFLIGHT.md` | 3 |
| `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md` | 3 |
| `docs/index.md` | 2 |
| `docs/planning/raw-product/WEAK_CONTRACT_DECISION_PREFLIGHT.md` | 2 |
| `docs/planning/raw-product/VISUAL_QA_NOTES.md` | 2 |
| `docs/operations/query_feedback_review.md` | 1 |
| `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md` | 1 |
| `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md` | 1 |

`docs/index.md` references the directory and an example path, not a specific
package. It does not need a link update for package moves unless the taxonomy is
changed.

## 5. Active Evidence Bucket

These packages are current release/readiness evidence and should stay active in
`return_packages/raw-product/` unless the same execution sweep updates every
current release/readiness doc that links to them:

- `APP_THEMING_TEST_DRIFT_FIX_RETURN_PACKAGE.md`
- `DIVISION_PHRASE_BOUNDARY_CLEANUP_RETURN_PACKAGE.md`
- `EXPANDED_VISUAL_QA_MANUAL_BASELINE_RETURN_PACKAGE.md`
- `FINAL_PUBLIC_UI_RELEASE_REVIEW_RETURN_PACKAGE.md`
- `FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md`
- `FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md`
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
- `REVIEWPAGE_EXHAUSTIVE_DEPS_WARNING_CLEANUP_RETURN_PACKAGE.md`
- `VISUAL_QA_SCREENSHOT_ARTIFACT_VALIDATION_DOCS_REFRESH_RETURN_PACKAGE.md`
- `VITE_INTERNAL_ROUTE_LAZY_SPLIT_RETURN_PACKAGE.md`

Reason: these packages are cited by current release package, handoff,
readiness checklist, readiness checkpoint, post-review closure docs, or the
feedback review runbook as evidence for the current `*_WITH_NOTES` boundary.

## 6. Current-Docs Linked Support Bucket

These packages are not all current release evidence, but current docs still
link to them by exact path. They can be archived later only if those docs are
updated in the same sweep or explicitly retired:

- `CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md`
- `CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md`
- `ENTITY_SUMMARY_RECORD_WHEN_FILTER_FOLLOWUP_RETURN_PACKAGE.md`
- `FRONTEND_SCREENSHOT_VISUAL_QA_PREFLIGHT_RETURN_PACKAGE.md`
- `FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_2_RETURN_PACKAGE.md`
- `NATURAL_QUERY_CONSTANTS_EXTRACTION_WAVE_1_RETURN_PACKAGE.md`
- `NATURAL_QUERY_EXTRACTION_PREFLIGHT_RETURN_PACKAGE.md`
- `NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_COVERAGE_RETURN_PACKAGE.md`
- `VISUAL_QA_CORPUS_EXPANSION_RETURN_PACKAGE.md`
- `VISUAL_QA_TARGETED_FIX_WAVE_1_RETURN_PACKAGE.md`
- `WEAK_CONTRACT_CLEANUP_WAVE_1_RETURN_PACKAGE.md`
- `WEAK_CONTRACT_DECISION_PREFLIGHT_RETURN_PACKAGE.md`

Reason: exact links appear in current planning docs such as weak-contract,
leaderboard supporting columns, visual QA, route-priority, decision-map, or raw
QA harness docs.

## 7. Archival Candidate Bucket

The safest first archive candidate set is:

```text
all return_packages/raw-product/*.md
minus every exact package path linked from docs/, README.md, and AGENTS.md
```

With the current inventory, that means 78 unlinked packages are historical or
completed evidence and are safe candidates for a later archive execution wave,
provided the execution wave re-runs the reference scan first.

Candidate categories:

- completed Raw QA fix and corpus expansion waves that are now summarized by
  durable release/readiness docs
- older release refresh packages superseded by the current release package and
  handoff
- earlier preview/manual QA packages superseded by current rerun evidence
- completed frontend hero/copy QA waves whose durable outcome is represented in
  current release docs or frontend-copy evidence
- completed visual QA deployment/parity/interim packages not directly linked by
  current docs
- preflight packages that have already been executed or superseded and are not
  linked by current docs
- small one-off cleanup packages not cited by current docs

Do not hard-code this candidate set from memory during execution. Generate it
from the current file inventory and current docs link scan immediately before
moving anything.

## 8. Destination Decision

Recommended destination:

```text
return_packages/archive/raw-product/2026-05-raw-product-release-cycle/
```

Why this destination:

- Keeps return-package artifacts under `return_packages/`, matching the
  taxonomy that says return packages live under `return_packages/`.
- Avoids creating a new root-level `archive/` namespace. This checkout has
  `docs/archive/`, but no root `archive/`.
- Reduces active-looking clutter in `return_packages/raw-product/`.
- Leaves `docs/archive/` reserved for documentation artifacts, not handoff
  receipts.
- Supports future topic archives such as
  `return_packages/archive/result_display/<phase>/`.

Rejected destination:

```text
archive/return_packages/raw-product/<date-or-phase>/
```

Reason: a root `archive/` directory does not currently exist. Adding it would
require a broader repo taxonomy decision and `docs/index.md` update.

Interim fallback:

```text
keep packages in place and add index/category docs
```

Reason to avoid as the primary path: an index helps navigation, but it does not
remove completed evidence packages from the active raw-product return-package
directory.

## 9. Exact Execution Plan

Recommended future execution wave:

1. Re-run inventory:
   - `ls -1 return_packages/raw-product`
   - `find return_packages/raw-product -mindepth 1 -maxdepth 1 -type d -print`
2. Re-run exact-path reference scan:
   - `rg -n "return_packages/raw-product/" docs README.md AGENTS.md`
   - `rg --no-filename -o "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\\.md" docs README.md AGENTS.md | sort -u`
3. Generate two manifests:
   - `active-linked-packages.txt`: exact package paths linked from docs.
   - `archive-candidates.txt`: raw-product package files not in the linked
     manifest.
4. Create destination directory:
   - `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`
5. Move only `archive-candidates.txt` files with `git mv`.
6. Add a short archive manifest in the destination that records:
   - sweep date
   - source directory
   - destination directory
   - candidate-generation rule
   - moved package list
   - docs intentionally not updated because the first sweep moved only
     doc-unlinked packages
7. Re-run exact-path scan and confirm no docs point to missing package paths.
8. Run validation:
   - `git diff --check`
   - markdown lint if available
9. Commit as one docs/artifact-organization PR-sized unit.

Second-stage optional sweep:

1. Only after the current release package/handoff/readiness docs are retired,
   superseded, or updated, move the active release evidence packages into the
   same archive phase directory or a follow-up phase directory.
2. Update every exact docs link in the same commit.
3. Do not rewrite package content unless the archive move creates broken links
   that readers still need.

## 10. Docs That Would Need Link Updates

If the first sweep moves only currently doc-unlinked packages, no durable docs
need link updates.

If any currently linked package is moved, update the relevant docs in the same
execution wave. The link-update candidates are:

- `docs/operations/query_feedback_review.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/planning/raw-product/WEAK_CONTRACT_DECISION_PREFLIGHT.md`
- `docs/planning/raw-product/LEADERBOARD_SUPPORTING_COLUMNS_PREFLIGHT.md`
- `docs/planning/raw-product/DIVISION_PHRASE_BOUNDARY_CLEANUP_PREFLIGHT.md`
- `docs/planning/raw-product/VISUAL_QA_SCREENSHOT_AUTOMATION_PREFLIGHT.md`
- `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md`
- `docs/planning/raw-product/VISUAL_QA_NOTES.md`
- `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md`
- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`

`docs/index.md` should be updated only if the archive taxonomy changes beyond
the already documented return-package archive cadence.

## 11. Archive Policy

What stays active:

- current release/readiness evidence linked by active release docs
- active preflight packages for work that has not yet executed
- the newest package for an open deferred item until its durable doc is updated
  or the item is closed
- any package explicitly named by current runbooks or planning authorities

What gets archived:

- completed wave packages after the wave series, release cycle, or workstream
  closes
- superseded release refresh packages after a newer durable release doc carries
  the current state
- preflight packages after their execution package and durable docs supersede
  them, unless current docs still link to them
- package series that are useful history but no longer active handoff evidence

What never gets deleted:

- release evidence
- QA baseline evidence
- packages used by release-readiness, handoff, runbook, or policy docs
- packages that explain why a feature stayed unsupported
- packages that record validation commands or failure history useful for future
  regression analysis

When to use short copied summaries instead of committed return packages:

- trivial typo fixes
- one-link corrections
- cosmetic doc wording changes
- small internal comments that do not alter behavior, policy, release status,
  validation evidence, runbooks, contracts, or QA corpus expectations

Committed return packages remain appropriate for meaningful execution waves,
release evidence, QA checkpoints, promotion decisions, parser/routing guardrail
work, deployment/data evidence, and anything that changes durable docs.

## 12. Stop Conditions

Stop and re-plan if:

- the candidate move set includes any package linked by docs and the sweep is
  not also updating those links
- current release/readiness docs would lose evidence paths
- a package referenced by a runbook or active planning doc is included in the
  archive move set unintentionally
- executing the move would require release-status changes
- executing the move would require production code, tests, QA corpus, or
  generated output changes
- a new root archive namespace is needed before the repo taxonomy is updated
- reference scans disagree about the active linked package set
- `git diff --check` fails after the archive move
- markdown lint, if available, reports issues in edited Markdown files

## 13. Preflight Validation

Validation run for this preflight:

| Command / check | Result |
| --- | --- |
| `git diff --check` | Passed |
| New-file whitespace checks | `git diff --no-index --check /dev/null <new-file>` produced no whitespace diagnostics for both new Markdown files |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |

No production, parser, frontend, API, or test-suite validation is required
because this preflight creates documentation only and does not alter behavior.
