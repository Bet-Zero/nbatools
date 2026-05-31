# Raw QA Corpus Product Review Harness Preflight Return Package

Date: 2026-05-31

Status: documentation-only preflight complete; execution not started.

## Summary

Created a concrete preflight for extending the Raw Query Answer QA workflow
from a machine regression harness into a two-layer regression and product-review
harness.

Durable design:

```text
docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md
```

No production code, parser/routing behavior, corpus cases, corpus expectations,
saved harness slices, frontend rendering, or release status changed.

## Current-State Findings

| Area | Finding |
| --- | --- |
| Corpus | `qa/raw_query_answer_corpus.yaml` has 294 cases |
| Existing public metadata | 67 cases have `acceptance.family` and `acceptance.variant`; 48 have `acceptance.no_broad_fallback` |
| Public slice | `qa/harness_slices/public_query_acceptance.yaml` has 67 cases across 17 tagged families |
| Latest targeted artifact | `outputs/raw_query_answer_qa/20260528T225801Z/report.md` records 67/67 machine expectation cases passing |
| Existing report strength | Case cards include route/status/shape, compact answer summaries, applied filters, section counts, and top rows |
| Main gap | The harness does not validate or emit `acceptance` metadata and does not generate a feature-family matrix |
| Review gap | The latest 67-case report records 54 `unreviewed` manual-review statuses |
| No-broad-fallback gap | `acceptance.no_broad_fallback` is descriptive metadata today, not an enforced validation contract |

The public slice is a useful regression gate. It is not yet a generated
product-review harness.

## Design Decision

Keep one Raw QA corpus and add two explicit workflow layers:

| Layer | Purpose | Output |
| --- | --- | --- |
| Layer A: Machine Regression | Route/status/shape assertions, hard assertions, saved slices, pass/fail gates | Existing `report.jsonl`, `report.md`, and `summary.json` |
| Layer B: Human Product Review | Feature-family coverage, representative answers, missing siblings, unsupported boundaries, product decisions, and human review state | Planned `product_review.md` and optional `product_review.json` |

The preflight proposes:

- extending per-case `acceptance` metadata
- adding `qa/raw_query_answer_acceptance_families.yaml`
- generating `outputs/raw_query_answer_qa/<run_id>/product_review.md`
- enforcing proof requirements for `acceptance.no_broad_fallback: true`
- requiring future corpus-wave return packages to declare whether the corpus
  itself was reviewed or only machine expectations passed

## Public-Accepted Rule

A family must not be called public accepted unless applicable canonical, short,
sentence, synonym, inverse/sibling, nearby unsupported, and typo/partial
variants are resolved; route/status/shape and no-broad-fallback proofs pass; and
representative outputs have been human-reviewed.

Machine regression, coverage completeness, human review, and public acceptance
remain separate statuses.

## Execution Waves

| Wave | Scope |
| --- | --- |
| Wave 1 | Add metadata foundation, family registry, `product_review.md`, validation, a small representative retag subset, focused tests, and the operations runbook |
| Wave 2 | Apply metadata to `public_query_acceptance`, generate the complete family matrix, send `product_review.md` to ChatGPT, and record product-review decisions |
| Wave 3 | Fix only reviewed behavior gaps in bounded PR-sized waves |

## Files Changed

- `docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md`
  - Added the durable preflight.
- `return_packages/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT_RETURN_PACKAGE.md`
  - Added this handoff receipt.
- `docs/index.md`
  - Added the new planning-doc index entry.

## Validation

Passed:

```bash
git diff --check
```

Passed with no whitespace diagnostics:

```bash
git diff --check --no-index -- /dev/null docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md
git diff --check --no-index -- /dev/null return_packages/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT_RETURN_PACKAGE.md
```

The `--no-index` checks return nonzero because each new file differs from
`/dev/null`; no whitespace diagnostics were emitted.

Markdown lint is not configured in this repo.

## Review Declaration

```text
machine_only
```

This preflight reviewed the workflow and existing artifacts. It did not rerun
the corpus, perform a new representative-output product review, or alter the
current release status.

## Immediate Next Action

Execute Wave 1 from the durable preflight. Keep it behavior-neutral: add the
metadata foundation, family registry, generated product-review artifact,
focused harness tests, and operations runbook before broad retagging.
