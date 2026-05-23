# Return Package Archive Sweep Preflight Return Package

## Status

- Mode: preflight only.
- Preflight date: 2026-05-23.
- Existing return packages moved, renamed, archived, or deleted: no.
- Production code changed: no.
- Tests changed: no.
- Release statuses changed: no.
- Durable release/readiness docs changed: no.

## What Was Created

- `docs/planning/raw-product/RETURN_PACKAGE_ARCHIVE_SWEEP_PREFLIGHT.md`
- `return_packages/raw-product/RETURN_PACKAGE_ARCHIVE_SWEEP_PREFLIGHT_RETURN_PACKAGE.md`

`docs/index.md` was intentionally not updated in this pass because the request
allowed only the preflight doc and return package to change.

## Inventory Findings

| Check | Result |
| --- | --- |
| Files in `return_packages/raw-product/` | 117 Markdown files |
| Subdirectories in `return_packages/raw-product/` | 0 |
| Unique raw-product package paths linked from docs | 39 |
| Docs/files with exact raw-product package references | 17 |
| Root `archive/` directory | Absent |

The flat raw-product package directory now contains multiple completed
workstreams: Raw QA fix/corpus waves, release readiness and handoff waves,
opponent-conference/R2 evidence, query feedback evidence, frontend-copy and
visual QA evidence, public result UI productization, post-review hardening, and
small deferred cleanup packages.

## Active Evidence Decision

Keep current release/readiness evidence in
`return_packages/raw-product/` for now. The release package, handoff,
readiness checklist, readiness checkpoint, post-review notes, hardening plan,
and query-feedback runbook still link to exact package paths.

The safest first archive execution should move only packages that are not
linked from current docs.

## Recommended Destination

Use:

```text
return_packages/archive/raw-product/2026-05-raw-product-release-cycle/
```

This keeps return-package artifacts under the `return_packages/` ownership
boundary, avoids introducing a new root `archive/` directory, and actually
reduces noise in the active raw-product package directory.

Do not use `archive/return_packages/raw-product/<date-or-phase>/` unless the
repo first makes a broader taxonomy decision and updates `docs/index.md`.

Keeping all packages in place plus adding an index is acceptable only as an
interim fallback; it does not solve the active-directory clutter problem.

## Execution Plan Summary

Future sweep:

1. Re-run package inventory and exact docs-link scans.
2. Generate a linked-package manifest from `docs`, `README.md`, and
   `AGENTS.md`.
3. Generate an archive-candidate manifest as package files minus linked files.
4. Create `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`.
5. Move only doc-unlinked candidates with `git mv`.
6. Add an archive manifest in the destination.
7. Confirm no docs point to missing package paths.
8. Run `git diff --check` and markdown lint if available.

Optional second stage:

- Move currently linked release/readiness evidence only after those docs are
  superseded, retired, or updated in the same commit.

## Docs Requiring Link Updates If Linked Packages Move

If the first sweep moves only doc-unlinked packages, no docs need link updates.

If linked packages move, update these candidates in the same execution wave:

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

## Policy Recommendation

- Keep active current release evidence, active preflights, and runbook-linked
  packages in `return_packages/raw-product/`.
- Archive completed, superseded, or doc-unlinked packages after a wave series,
  release cycle, or workstream closes.
- Never delete release, QA baseline, handoff, unsupported-boundary, or
  validation-history evidence automatically.
- Use short copied summaries for trivial typo/link/cosmetic doc changes.
- Keep committed return packages for meaningful execution waves, release
  evidence, QA checkpoints, promotion decisions, parser/routing guardrails,
  deployment/data evidence, and durable-doc changes.

## Stop Conditions

Stop a future archive execution if:

- the move set contains any docs-linked package without same-commit link
  updates
- current release/readiness docs would lose evidence paths
- release statuses would need to change
- code, tests, QA corpus, or generated outputs would need to change
- a root archive namespace would need to be introduced without taxonomy review
- reference scans disagree about the linked package set
- validation fails

## Validation

| Command / check | Result |
| --- | --- |
| `git diff --check` | Passed |
| New-file whitespace checks | `git diff --no-index --check /dev/null <new-file>` produced no whitespace diagnostics for both new Markdown files |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |
