# Return Package Dependency Cleanup Preflight Return Package

## Status

- Mode: preflight only.
- Date: 2026-05-23.
- Production code changed: no.
- Tests changed: no.
- QA corpus changed: no.
- Return packages moved, renamed, archived, or deleted: no.
- Release statuses changed: no.

## What Changed

Created the dependency-cleanup preflight:

```text
docs/planning/raw-product/RETURN_PACKAGE_DEPENDENCY_CLEANUP_PREFLIGHT.md
```

The preflight documents the current durable-doc dependency on exact
`return_packages/raw-product/..._RETURN_PACKAGE.md` paths and defines a
docs-first cleanup strategy.

`docs/index.md` was also updated so the new planning doc is discoverable from
the docs index.

## Findings

Current exact-path scan found:

| Finding | Count |
| --- | ---: |
| Unique exact Raw Product return-package paths linked from durable docs | 39 |
| Durable docs with exact Raw Product return-package links | 16 |
| Active Raw Product package files after Archive Sweep Wave 1 | 40 |
| Adjacent exact `result_display` package-link docs | 2 |

The remaining dependency is not an archive problem by itself. Archive Sweep
Wave 1 correctly preserved linked packages. The next problem is that durable
docs are using package paths as evidence references.

## Cleanup Recommendation

Run a follow-up docs-promotion wave before moving any more packages:

1. Create `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`.
2. Promote the current evidence facts from package receipts into durable docs.
3. Replace exact return-package links in release, readiness, handoff, runbook,
   post-review, visual QA, natural-query, weak-contract, and leaderboard
   context docs.
4. Add explicit dependency rules to `AGENTS.md` and `docs/index.md`.
5. Re-run the exact-path scan.
6. Archive newly unlinked package receipts only in a later archive wave.

## Allowed Link Rule

Return-package links in durable docs should be temporary active-workstream
references only. They are not source-of-truth evidence links. At workstream
closure, durable facts must be promoted into `docs/`, exact package paths must
be cleared or replaced, and package receipts can then be archived in a separate
archive sweep.

## Validation Results

| Command / check | Result |
| --- | --- |
| `git diff --check` | Passed |
| New-file whitespace checks | No diagnostics for this return package or the preflight doc |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |

No production, parser, frontend, API, QA, or test validation is needed because
this preflight changes documentation only.
