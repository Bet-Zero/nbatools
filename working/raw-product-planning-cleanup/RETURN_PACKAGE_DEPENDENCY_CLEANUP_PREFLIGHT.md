# Return Package Dependency Cleanup Preflight

## 1. Scope

Mode: preflight only.

This document does not move, rename, archive, delete, or edit return packages.
It does not change production code, tests, QA corpus files, generated outputs,
release statuses, parser/routing behavior, frontend behavior, API behavior, or
data contracts.

The goal is to plan a cleanup for the current durable-doc dependency on exact
`return_packages/raw-product/..._RETURN_PACKAGE.md` paths. Return packages are
handoff receipts. Durable docs should carry the durable facts and should not
require exact return-package paths to stay in place.

## 2. Problem Statement

The first archive sweep correctly moved only doc-unlinked Raw Product return
packages. It preserved every package that current docs still linked by exact
path. That avoided broken links, but it exposed the remaining problem:
durable docs have started depending on return package locations as evidence
paths.

Current state after Archive Sweep Wave 1:

| Inventory item | Result |
| --- | ---: |
| Raw-product package files still active | 40 |
| Unique exact raw-product return-package paths linked from durable docs | 39 |
| Durable docs with exact raw-product return-package links | 16 |
| Archived raw-product Markdown files in the May 2026 archive directory | 80 |
| Adjacent exact `result_display` return-package links found in durable docs | 2 docs |

The 40 active package files are the 39 doc-linked packages plus
`RETURN_PACKAGE_ARCHIVE_SWEEP_WAVE_1_RETURN_PACKAGE.md`, which was created by
the archive sweep and is not currently linked by durable docs.

## 3. Evidence Reviewed

Required inputs inspected:

- `docs/index.md`
- `AGENTS.md`
- `archive/raw-product-planning-cleanup/legacy-return-package-plans/RETURN_PACKAGE_ARCHIVE_SWEEP_PREFLIGHT.md`
- Archive Sweep Wave 1 return package in `return_packages/raw-product/`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md`
- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`
- `docs/operations/query_feedback_review.md`

Reference scans used:

```text
rg -l "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md
rg --no-filename -o "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md | sort -u
rg -o "return_packages/(raw-product|result_display|review)/[A-Za-z0-9_./-]+" docs README.md AGENTS.md | sort -u
```

## 4. Direct-Link Inventory

These durable docs link directly to exact Raw Product return-package paths.

| Doc | Current dependency type | Cleanup direction |
| --- | --- | --- |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | Current release evidence table and supporting package list. | Promote facts into durable release evidence, then replace package paths with durable doc/output references. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | Current handoff evidence table. | Link to durable release evidence summary and output artifacts instead of package paths. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Release checklist evidence rows and later evidence notes. | Keep statuses unchanged, but replace package paths with durable evidence sections and output artifacts. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | Readiness checkpoint evidence notes. | Replace package paths with durable release evidence summary anchors. |
| `docs/operations/query_feedback_review.md` | Current preview feedback verification points to one package. | Promote the preview verification facts into the runbook and link release evidence summary only if needed. |
| `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md` | Closure evidence list for hardening waves. | Replace package-list evidence with durable closure facts and links to the docs created by those waves. |
| `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` | Inputs reviewed and closure evidence lists cite wave packages. | Replace wave-package inputs with durable outcome docs and a compact closure evidence summary. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Harness release-status context cites promotion and preview packages. | Replace with the release package, release evidence summary, and output reports. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Durable weak-contract and leaderboard-column contract. | Keep as the source of truth for current renderer behavior. |
| `docs/reference/query_catalog.md` and `docs/reference/query_guide.md` | Durable division-boundary references. | Keep as the source of truth for guarded `opponent_division` unsupported behavior. |
| `working/frontend-visual-qa-followups/VISUAL_QA_NOTES.md` | Visual follow-up notes cite older visual fix packages. | Promote findings into the notes or current visual checklist, then remove package paths. |
| `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md` | Corpus-expansion context cites public UI and hardening packages. | Replace with durable visual QA checklist and release evidence summary. |
| `docs/operations/frontend_visual_qa.md` | Durable screenshot workflow, visual QA baseline, and artifact-run rules. | Keep current as the operations runbook. |
| `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md` | Route-priority context cites a constants-extraction package. | Replace with durable route-priority snapshot and decision-map docs. |
| `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md` | Decision-map context cites extraction preflight package. | Replace with the durable extraction preflight doc. |

Adjacent finding outside this Raw Product cleanup set:

- `docs/planning/result-display-lock-in/result_display_preflight_findings.md`
  and
  `docs/planning/result-display-lock-in/result_display_lock_in_implementation_spec.md`
  directly cite
  `RESULT_DISPLAY_PREFLIGHT_RETURN_PACKAGE.md` in
  `return_packages/result_display/`.
  Apply the same rule in a separate result-display cleanup pass, or include it
  if the execution wave broadens from Raw Product to all return-package topics.

## 5. Temporary Versus Stale References

### Temporary active-workstream references

These references are temporary only because the current release/readiness docs
still use them as exact evidence paths. They should not remain source-of-truth
links after the cleanup wave:

- visual QA baseline and screenshot artifact packages
- preview manual QA rerun package
- opponent-conference promotion, preview smoke, and R2 sync fix packages
- query feedback implementation, preview R2 enable, R2 inspection, and review
  workflow packages
- final public UI release review package
- post-review hardening Waves 1-6 and closure refresh packages
- AppTheming test drift fix package
- division phrase boundary cleanup package
- Vite internal route lazy split package
- ReviewPage exhaustive-deps warning cleanup package
- frontend-copy QA expansion and harness efficiency packages

The durable facts from these packages already appear in parts of the release
docs. The execution wave should make the durable docs authoritative and remove
the exact package-path dependency.

### Stale evidence references

These references are historical context rather than active handoff evidence.
They should be replaced by durable doc references or compact inline summaries:

- core result table lock packages in weak-contract and leaderboard preflights
- weak-contract decision and cleanup packages in leaderboard preflight
- natural-query extraction and constants-extraction packages in route-priority
  and decision-map docs
- older visual QA targeted-fix and entity-summary follow-up packages in
  `VISUAL_QA_NOTES.md`
- visual QA corpus expansion and frontend screenshot preflight packages in the
  screenshot automation preflight
- public UI Wave 2 / hardening Wave 6 package links in the visual corpus
  expansion preflight

### References that should remain

No exact return-package path should remain in durable docs as a long-term
source-of-truth link.

Temporary exact links are allowed only when all of the following are true:

1. The workstream is actively open.
2. The return package is the immediate handoff input for the next wave.
3. The durable doc marks the link as temporary.
4. The doc names the cleanup trigger, such as "remove after release evidence
   summary is updated" or "remove when this preflight executes".

Return-package files themselves may continue to link to prior return packages
as part of handoff provenance. That is not the durable-doc dependency problem.

## 6. Facts To Promote Into Durable Docs

The cleanup should promote facts, not paths. The execution wave should ensure
the following facts live in durable docs before removing exact package links.

| Evidence family | Durable destination | Facts to preserve |
| --- | --- | --- |
| Backend Raw QA | Release package, readiness checklist, readiness checkpoint, release evidence summary | Latest full run path, case counts, expectation counts, failed IDs, suspicious flags, division-slice coverage. |
| Frontend-copy QA | Release package, readiness checklist, release evidence summary | Selected corpus size, source backend run, rendered count, failure count, soft-check totals, selected-coverage limitation. |
| Visual QA | Visual QA checklist and release evidence summary | 20-case / 40 viewport manual baseline, request errors 0, no blockers, artifact run id `visual_qa_20_case_baseline`, 20 desktop plus 20 mobile cards, statuses `ok: 15`, `no_result: 5`, `error: 0`, overflow false, 42 expected PNGs, no screenshot diffing or CI gate. |
| Preview manual QA | Release evidence summary and readiness checklist | `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker cases passed; status remains `PREVIEW_READY_WITH_NOTES`. |
| Opponent-conference / R2 | Deployment runbook, release evidence summary, readiness docs | Required R2 key `raw/teams/team_conference_membership.csv`, `ContentLength=4999`, `LastModified=2026-05-17T09:03:29+00:00`, MD5 metadata, deployment smoke `ok: true`, seven cases, zero failures, 15 East opponents. |
| Query feedback | Query feedback runbook and release evidence summary | `FEEDBACK_READY_WITH_NOTES`, preview bucket/prefix, user-submitted records found, automatic diagnostics found, sanitizer/privacy checks passed, no raw result rows/tables, `/review` and `/visual-qa` suppression, `make query-feedback-export` workflow outputs. |
| Public UI review | Release evidence summary and UI guide if needed | `/`, `/?debug=1`, `/review`, and `/visual-qa` route checks passed; 14 desktop public queries and 13 mobile 390px family checks passed; debug/details and feedback preservation passed; blocking issues none. |
| Post-review hardening | Post-review hardening plan, post-review notes, release evidence summary | Waves 1-6 complete; durable outcomes are guardrails, feature-promotion rules, Data/R2 checklist, feedback cadence, taxonomy, README/product positioning, homepage/product promise, public context de-duplication. |
| AppTheming test drift | Release evidence summary and readiness checklist | Test-only drift fixed; full frontend suite passed 25/25 files and 352/352 tests. |
| Division boundary cleanup | Release evidence summary, query docs if needed, readiness docs | Explicit division opponent phrases return `no_result` / `filter_not_supported`, `metadata.unsupported_filters=["opponent_division"]`, no division support added, targeted snapshots 65 passed, parser/query slices 776 passed each, raw QA slices 35/35 and 18/18 passed, `test-preflight` 2978 with 1 xpassed. |
| Build/lint cleanup | Release evidence summary and readiness docs | Vite internal `/review` and `/visual-qa` lazy split build passed and large-chunk warning cleared; ReviewPage exhaustive-deps cleanup lint passed with no warnings. |
| Weak/result-contract context | Result-contract docs and relevant preflights | The decision facts behind `lineup_summary`, `player_on_off`, single-team `playoff_appearances`, and leaderboard supporting columns; no package paths needed. |
| Natural-query extraction context | Natural-query extraction preflight and decision map | Current route-order preservation facts, collision/unsupported-boundary coverage needs, extraction candidate and stop conditions. |

## 7. Cleanup Strategy

Recommended execution approach:

1. Create a durable release evidence summary:
   `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
   This summary should collect the current evidence facts listed above and
   should reference durable docs and generated `outputs/` artifacts. It should
   not link to exact return-package paths.
2. Update the four release/readiness docs to link to the evidence summary and
   generated output artifacts instead of return-package files:
   - `RAW_PRODUCT_RELEASE_PACKAGE.md`
   - `RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
   - `RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
   - `RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
3. Update the feedback runbook so the preview verification facts are durable in
   `docs/operations/query_feedback_review.md`; remove the package path.
4. Update post-review and hardening docs so closure evidence is expressed as
   durable outcomes and durable doc references:
   - `RAW_PRODUCT_POST_REVIEW_NOTES.md`
   - `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`
5. Update stale-context preflight docs by replacing package paths with durable
   docs or inline summaries:
   - weak-contract and leaderboard preflight docs
   - natural-query route-priority / decision-map docs
   - visual QA notes and visual preflights
   - division cleanup preflight
   - raw query answer harness plan
6. Update `docs/index.md` Return Packages rules to add an explicit dependency
   rule: durable docs must not use exact return-package paths as source-of-truth
   evidence; temporary links require an active-workstream marker and cleanup
   trigger.
7. Update `AGENTS.md` documentation expectations with the same rule so future
   agents know to promote durable facts into `docs/` and clear temporary
   return-package links at closure.
8. Re-run the exact-path scan. The target for Raw Product durable docs is zero
   exact `return_packages/raw-product/..._RETURN_PACKAGE.md` paths, unless an
   explicitly marked temporary active-workstream exception remains.
9. Do not move or archive packages in this dependency-cleanup wave. Once durable
   docs no longer depend on exact paths, run a separate archive wave to move
   newly unlinked active packages into the existing May 2026 archive directory
   or a follow-up phase directory.

## 8. Allowed Return-Package Link Policy

Durable docs may not treat a return package as the source of truth for current
product behavior, release readiness, parser/routing policy, runbook behavior,
data contracts, result contracts, or UI behavior.

Allowed:

- Return packages can cite durable docs and generated `outputs/` artifacts.
- Return packages can cite prior return packages as handoff provenance.
- A durable planning doc can temporarily cite an exact return-package path only
  for an active, unfinished workstream and only with an explicit cleanup trigger.
- Archive manifests can list package filenames and archive locations as
  historical evidence organization records.

Not allowed:

- A current-state, runbook, release, handoff, checklist, policy, or contract doc
  using an exact return-package path as the only place where an evidence fact
  lives.
- A completed preflight or closed plan retaining exact package links after the
  durable facts have been promoted.
- Release docs maintaining "supporting return packages" lists as current
  source-of-truth evidence.

Closure rule:

```text
When a workstream closes, promote durable facts into docs, replace exact package
paths with durable docs or outputs, then archive completed package receipts in a
separate archive sweep.
```

## 9. Agent Convention Updates Needed

`AGENTS.md` should gain a short "Return Package Dependency Rule" under
Documentation expectations. The rule should say:

- Return packages are receipts, not durable docs.
- Durable docs must promote the validated facts they need instead of depending
  on exact return-package paths.
- Exact return-package links in durable docs are allowed only for temporary
  active-workstream handoffs, and the doc must name the cleanup trigger.
- At workstream closure, agents must clear or replace temporary exact links
  before archiving packages.
- Before moving or archiving return packages, agents must run an exact-path
  reference scan across `docs`, `README.md`, and `AGENTS.md`.

`docs/index.md` should add the same dependency rule to the Return Packages
category rules. Existing rules already say return packages are evidence and
durable behavior belongs under `docs/`; the missing explicit rule is that
durable docs should not keep exact return-package paths as long-term evidence
dependencies.

Future prompts that ask for a return package should also state whether the
package is temporary active-workstream evidence and which durable docs must be
updated before closure.

## 10. Follow-Up Execution Wave

Recommended next wave: **Return Package Dependency Cleanup Wave 1 - Docs
Promotion and Link Replacement**.

### Goals

- Promote current return-package-only evidence facts into durable docs.
- Replace exact Raw Product return-package paths in durable docs.
- Add the explicit AGENTS/docs-index convention.
- Leave all packages in place for this wave.
- Leave release statuses unchanged.

### Acceptance Criteria

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md` exists
  and records the promoted evidence facts without exact return-package paths.
- The Raw Product release package, handoff, readiness checklist, and checkpoint
  no longer depend on exact return-package paths.
- The query feedback runbook no longer points to a return package for current
  preview verification status.
- Completed/stale preflight and visual/natural-query context docs no longer use
  package paths as durable evidence.
- `AGENTS.md` and `docs/index.md` contain the explicit dependency rule.
- `rg --no-filename -o "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md | sort -u`
  returns no Raw Product paths, or only explicitly marked temporary exceptions
  with cleanup triggers.
- No production code, tests, QA corpus files, generated outputs, package moves,
  package deletes, or release status changes occur.

### Validation

- `git diff --check`
- markdown lint if available
- exact return-package reference scan across `docs`, `README.md`, and
  `AGENTS.md`

### Stop Conditions

Stop and re-plan if:

- a release status would need to change
- a package move/delete appears necessary in the docs-promotion wave
- evidence facts disagree across release docs and package receipts
- a durable fact cannot be verified from current docs, outputs, or package
  receipts
- the exact-path scan still shows unmarked return-package dependencies after
  cleanup
- markdown lint or `git diff --check` fails

## 11. Post-Cleanup Archive Wave

After the docs-promotion wave removes exact path dependencies, run a separate
archive wave:

1. Re-scan exact references across `docs`, `README.md`, and `AGENTS.md`.
2. Generate a move set of active Raw Product packages no longer linked by
   durable docs.
3. Move packages with `git mv` into
   `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`
   or a new clearly named follow-up phase directory.
4. Update the archive manifest.
5. Validate that no durable doc points to a missing path.

This archive wave should still delete nothing.

## 12. Preflight Validation

| Command / check | Result |
| --- | --- |
| `git diff --check` | Passed |
| New-file whitespace checks | No diagnostics for this preflight doc or its return package |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |

No production, parser, frontend, API, QA, or test validation is required
because this preflight changes documentation only.

## 13. Preflight Result

The direct return-package dependency problem is real and bounded. The cleanup
does not need product code, tests, QA corpus, release-status, or package-move
changes. It needs one docs-promotion wave followed by a separate archive wave.
