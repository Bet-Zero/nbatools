# Return Package Dependency Cleanup Wave 1 Return Package

## Status

- Mode: execution.
- Date: 2026-05-23.
- Production code changed: no.
- Tests changed: no.
- QA corpus changed: no.
- Return packages moved, renamed, archived, or deleted: no.
- Release statuses changed: no.
- Product behavior changed: no.

## What Changed

Executed the docs-promotion cleanup recommended by:

```text
docs/planning/raw-product/RETURN_PACKAGE_DEPENDENCY_CLEANUP_PREFLIGHT.md
```

Created the durable release evidence summary:

```text
docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md
```

The summary promotes current release/readiness evidence facts into `docs/`
instead of relying on exact return-package paths as source-of-truth evidence.

## Evidence Promoted

The new durable evidence summary records:

- release/readiness statuses:
  `RELEASE_CANDIDATE_WITH_NOTES`, `PREVIEW_READY_WITH_NOTES`,
  `FEEDBACK_READY_WITH_NOTES`, and `PUBLIC_UI_READY_WITH_NOTES`
- backend raw QA evidence, including latest full run, case counts,
  expectation counts, failed IDs, suspicious flags, and division slices
- frontend-copy QA evidence, including selected corpus size, rendered count,
  missing records, and soft-check totals
- visual QA manual baseline evidence for 20 cases / 40 desktop-mobile reviews
- non-diffing screenshot artifact validation for `visual_qa_20_case_baseline`
- query feedback readiness and review/export workflow evidence
- parser/routing hardening and Waves 1-6 durable outcomes
- division boundary cleanup behavior and validation
- data/R2 deployment evidence for `raw/teams/team_conference_membership.csv`
- public UI readiness evidence
- bundle/lint/build/frontend-test cleanup evidence
- docs/return-package taxonomy evidence
- remaining deferred items

## Link Cleanup

Exact return-package paths were removed from durable docs and replaced with
durable docs, generated output artifacts, or inline evidence facts.

Primary replacement targets:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `docs/operations/query_feedback_review.md`
- `docs/operations/deployment.md`
- `docs/reference/result_contracts/core_result_table_contracts.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
- `docs/planning/raw-product/NATURAL_QUERY_EXTRACTION_PREFLIGHT.md`
- `docs/planning/raw-product/NATURAL_QUERY_DECISION_MAP_AND_TEST_MATRIX.md`
- `docs/planning/raw-product/NATURAL_QUERY_ROUTE_PRIORITY_SNAPSHOT_PREFLIGHT.md`
- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`

The cleanup also removed the two adjacent exact result-display package links
from durable result-display planning docs by pointing to the durable preflight
findings doc instead.

## Policy Updates

Updated `AGENTS.md` with an explicit return-package dependency rule:

- return packages are handoff/evidence receipts
- return packages are not durable source-of-truth docs
- durable facts must be promoted into `docs/`
- exact return-package links in durable docs are temporary active-workstream
  handoffs only
- workstream closure should clear or replace exact return-package dependencies
- archive sweeps are separate explicit passes
- package moves require an exact reference scan across `docs`, `README.md`, and
  `AGENTS.md`

Updated `docs/index.md` to list the new evidence summary and add the same
durable-doc dependency rule under Return Packages.

## Exact Reference Scan

Before this wave, from `HEAD`:

| Scan | Count |
| --- | ---: |
| Exact package path occurrences across `docs`, `README.md`, and `AGENTS.md` | 119 |
| Unique exact package paths | 40 |
| Files containing exact package paths | 18 |
| Unique Raw Product exact package paths | 39 |
| Unique result-display exact package paths | 1 |

After this wave:

| Scan | Count |
| --- | ---: |
| Exact package path occurrences across `docs`, `README.md`, and `AGENTS.md` | 0 |
| Unique exact package paths | 0 |
| Files containing exact package paths | 0 |

Commands:

```text
git grep -n -E "return_packages/(raw-product|result_display|review)/[A-Z0-9_]+_RETURN_PACKAGE\.md" HEAD -- docs README.md AGENTS.md
git grep -h -o -E "return_packages/(raw-product|result_display|review)/[A-Z0-9_]+_RETURN_PACKAGE\.md" HEAD -- docs README.md AGENTS.md | sort -u
rg -n "return_packages/(raw-product|result_display|review)/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md
rg --no-filename -o "return_packages/(raw-product|result_display|review)/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md | sort -u
```

## References Remaining

No exact return-package paths remain in `docs`, `README.md`, or `AGENTS.md`
under the strict package-path scan.

Non-exact references remain intentionally:

- `docs/index.md` contains a placeholder example path for future return-package
  prompts.
- the dependency-cleanup and archive-sweep preflights contain glob-like
  examples, package filenames, or historical inventory lists without exact
  package paths.
- return-package files themselves may still cite prior return packages as
  handoff provenance; this wave did not scan or rewrite return-package
  receipts.

## Validation

| Command / check | Result |
| --- | --- |
| Exact path scan, current worktree | Passed; 0 exact package paths in `docs`, `README.md`, or `AGENTS.md` |
| `git diff --check` | Passed |
| New-file whitespace checks | No diagnostics for the evidence summary or this return package |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |

No production, parser, frontend, API, QA, or test validation was required
because this wave changes documentation only.
