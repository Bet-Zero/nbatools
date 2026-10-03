# AGENTS.md

Instructions for coding agents working in `Bet-Zero/nbatools`.

## Project goal

NBA Tools is a web-based NBA statistics search app. A person asks a normal
basketball-statistics question in ordinary language and gets the correct,
properly scoped answer. The shared engine also serves the API and CLI.

**Deliver useful answers. Do not mistake making an unsupported answer safe for
implementing the requested capability.**

## Owner delegation and completion policy

Owner direction updated 2026-10-02. This section supersedes older instructions
that make routine query review, technical prioritization, phase selection, or
build-versus-refuse decisions an owner dependency. It changes the workflow,
not the truth of historical evidence or the current implementation.

- The owner supplies product intent and may contribute examples. Agents own
  input generation, diagnosis, data research, implementation, numerical
  verification, regression coverage, prioritization, and routine coordination.
- For a desired, coherent question, `unsupported`, `filter_not_supported`,
  `unrouted`, missing data, or a safer refusal means **capability unfinished**.
  A containment repair can be recorded separately, but cannot close the feature
  or count as an answered question.
- A genuinely correct zero count or empty search result is an answer, not a
  refusal. Verify data coverage and the calculation before accepting it.
- Negative tests are for genuinely invalid requests, unresolved ambiguity,
  unsupported data conditions, or explicit product exclusions. A legitimate
  feature missing from today's implementation is not a bad input. Keep its
  temporary safety regression separate from its open delivery requirement.
- Current-boundary documents and historical `expected_unsupported` cases
  describe what exists, not a permanent veto on implementing desired features.
  Preserve protections until their replacement is implemented and verified.
- Clarify genuinely ambiguous meaning; do not invent metrics, silently omit
  clauses, substitute subjects, or force people to memorize special wording.
  Normal shorthand, punctuation, aliases, and grammatical variation are not
  reasons to label a clear request invalid.
- Ask the owner only about genuinely unresolved product intent, necessary
  account access/consent, meaningful new spending, or consequential actions
  outside authorization. Resolve implementation questions from the repo and
  verified data. Bring a recommendation with any real owner decision.

## Task-based work queues

`ROADMAP.md` defines the product direction. The current temporary coordination
file is `working/nba-tools-completion-program/README.md`; use it until the
completion program closes, then retain the continuing direction in the roadmap.
This pointer is for active execution, not evidence of shipped behavior.

The working loop is:

```text
collect desired questions -> verify answers -> group gaps by cause
-> implement capability -> verify unfamiliar variants and real results
-> retain regression checks -> merge/deploy -> continue
```

1. Check the current branch, open PRs, queue, and relevant existing code before
   adding anything. Do not create a second workflow or parallel source of truth.
2. Start the next unfinished delivery unit. Reproduce its concrete examples;
   do not restart a whole-project audit or request a new owner query battery.
3. Group common causes, but keep PRs coherent and reviewable. Fix reusable
   behavior instead of hardcoding names, query strings, or expected answers.
4. The maker implements; a checker independently verifies meaningful query,
   calculation, or data-semantic changes. A self-review is not independent.
   Checker findings must identify a reproducible defect or material missing
   evidence. Optional cleanup is non-blocking.
5. Repair actionable findings directly. Do not send routine maker/checker
   disagreements or review prompts through the owner. If a separate checker
   cannot be invoked, leave one exact handoff and continue independent work;
   never fabricate its approval.
6. Update the same queue with what actually landed, remaining blockers, and the
   exact next action. Continue through authorized work without a fresh prompt
   at every task boundary. A session limit requires a resumable handoff, not a
   new planning phase or an unsupported promise of background execution.

### Completion-level rule

A desired capability is complete only when natural input reaches the intended
computation; all meaningful requested conditions are honored; the answer and
its presentation are correct; applicable automated/independent checks pass;
and the deployed path is verified when changed. Parser recognition, route
registration, containment, documentation, deferral, and green test totals are
not substitutes. Report implementation and deployment separately when only
one is complete. A blocked delivery item stays open with a concrete dependency;
work on other independent items continues.

## Working style and architecture

- Prefer targeted, reusable changes. No rewrite, new framework, extra receipt
  system, or general cleanup project without a concrete delivery benefit.
- Keep core logic UI-agnostic and transport-agnostic. CLI wrappers are thin;
  React fetches and renders. Computation, filtering, and parsing belong in the
  engine, not the frontend or CLI entrypoints.
- Keep parsing/routing, command computation, data processing, and formatting
  separated. `natural_query.py` orchestrates; substantial computation belongs
  in command/helper modules. Avoid duplicate branches and silent player/team
  behavior forks when touching shared behavior.
- Support full questions, search fragments, and compressed shorthand. Read
  `docs/operations/parser_routing_growth_guardrails.md` for route-collision
  and parser-structure details. Apply those guards without turning temporary
  unsupported states into the product goal.
- Preserve public contracts unless intentionally extending them; update all
  affected consumers. Follow `docs/operations/feature_promotion_rules.md`.
- Do not claim shipped behavior from docs alone. Keep `query_catalog.md` and
  relevant current-state/reference docs aligned with verified changes.

## Data placement and dataset-structure rule

Preserve the raw/processed/derived lifecycle and each dataset's grain. Do not
silently repurpose canonical data, mix game/period/stint grains, or add ad hoc
files without consumers and a contract. New or extended data needs a source,
grain, join keys, coverage/trust rules, storage location, consumer, and honest
missing-data behavior, documented in `docs/reference/data_contracts.md`.

Use the configured data source, not laptop-only paths for runtime datasets.
Use a fixed code revision and one immutable data generation for comparisons.
Test data is not NBA evidence. Never publish fixtures as real stats, fabricate
coverage, or infer complete history from a partial dataset. Follow
`docs/operations/deployment.md` for generation publication and deployed checks.

## Testing expectations

Tests protect delivery; test totals are not product-completion scores.

- While iterating, use a focused test file or the relevant existing Make target:
  `test-parser`, `test-query`, `test-engine`, `test-api`, or `test-output`.
- Use `make test-impacted` only for small localized changes. Testmon is serial,
  does not track data/environment/dynamic-import changes, and can select too
  much. Stop it after 60 seconds without useful progress; use focused tests or
  a parallel domain/preflight run instead.
- High fan-in changes (`natural_query.py`, `query_service.py`, parser core,
  API, shared fixtures) need broad candidate validation with
  `make test-preflight` or `make test`, as appropriate. Do not rerun overlapping
  full suites after every small edit. Reuse evidence for unchanged code/data.
- `make test-unit` / `make test-ci-fast` exclude `needs_data` and `slow`.
  `make test-preflight` excludes `slow`; `make test` selects the full suite.
  Selection is not execution: disclose skips and unavailable data.
- Use the committed fixture for behavioral checks. Verify numeric answers with
  qualified real data and independently calculated expectations, including
  scope, counts, ordering, thresholds, and displayed values. Backend `ok`, a
  changed fingerprint, or a second agent agreeing is not enough on its own.
- Run relevant Raw QA cases during iteration; run the full failing gate at
  meaningful query/data integration checkpoints. The canonical command is
  `make raw-query-answer-qa`; report-only runs are not passes. On real data,
  verify each change with a `scope: targeted` R2 run of its cases and
  `needs_data` tests (minutes), and keep the `scope: full` run (Raw QA alone is
  30-40 minutes) for batches and merge points. Never wait idle on a run: keep
  building the next change while it works.
- Existing refusal regressions stay until verified support intentionally
  replaces them. Do not mass-relabel cases, weaken assertions, hide failures,
  or make desired-answer tests expect refusal to obtain a green result.
- Frontend changes require build, lint, and tests; rebuild the FastAPI-served
  assets. Inspect actual rendered output for changed layout/copy. Unchanged
  renderers do not require a fresh owner screenshot tour.
- Docs-only changes require `make docs-governance` and `git diff --check`.
  Do not run a remote full NBA corpus solely for a documentation edit.

## CI testing policy

The workflow is `.github/workflows/ci.yml`; command details are in `Makefile`
and `CONTRIBUTING.md`. Preserve these independent checks:

- `lint`, `docs-governance`, and `frontend-verify` (locked install/build/lint/test);
- `frontend-security`: production-scoped audit, strict and blocking;
- `frontend-security-dev`: whole-tree advisory audit, informational;
- `test-fast`: data-free test selection on every PR;
- `test-full`: full suite selection on main pushes, nightly, and dispatch.

Do not remove the full-suite backstop, suppress failures, increase audit
thresholds, or bypass blocking checks. Dev-tool advisories are not zero-risk;
they are maintenance rather than automatic product-work blockers under the
existing scoped policy. Ordinary CI remains secret-free. Real-data validation
uses the existing manual `r2-real-data-validation.yml` workflow and dedicated
`r2-validation` environment. Never duplicate or print credentials, move them
into ordinary CI, or widen their scope to repair a wiring error. These docs do
not change workflow triggers, permissions, secrets, or branch protection.

### Merge policy

Use one PR per logical delivery unit. Before merging, require all applicable
blocking checks, not just lint and test-fast, and the relevant independent
semantic review. Routine docs/maintenance do not need a separate owner review.
After acceptance, merge and continue the authorized queue. Do not bypass checks
because GitHub technically permits a merge. A red advisory-only check must be
reported as such, not confused with a blocking failure.

## Documentation and evidence

Current behavior belongs in `docs/reference/`, architecture in
`docs/architecture/`, runbooks/policy in `docs/operations/`, retained historical
audits in `docs/audits/`. Keep the docs index current when adding/moving docs.
Use `docs/operations/working_and_archive_policy.md` for task-artifact lifecycle.
Keep one active queue rather than several conflicting status narratives.

### Raw QA product-review rule

Inspect representative outputs and the generated product review for relevant
public capability changes. Record machine verification and independent agent
review separately. Historical human acceptance stays historical. Never write
`human_review_complete`, a named human reviewer, or an owner acceptance receipt
for work a human did not review.

The older Raw QA schema/runbooks retain human-review/closure fields. They still
mean what they say; they no longer assign routine capability review to the
owner under the 2026-10-02 delegation. Record agent verification in the PR/active
queue without inventing a schema value. Legacy `human_review_pending` alone is
not a routine engineering stop. Do not bypass genuine data, numerical, or
regression failures. Human launch/branding decisions remain separate.

### Owner updates

Lead with: **Now answers; Still unfinished; Verification; Next; Needed from
you (normally nothing).** Explain actual examples in basketball language.
Containment may be mentioned as a limitation removed, never celebrated as a
completed desired feature. Keep technical receipts in the PR, not in owner
homework. Report attempted/blocked work honestly.

## graphify

When available, use the existing graph for relevant code navigation: scoped
query/path/explain before a full report. Use its wiki index for broad navigation.
Expected dirty graph output is not itself a blocker. Refresh the graph after
code changes when the tool is available; do not make installation or graph
cleanup a new dependency for this delivery program.
