# Raw QA Corpus Product Review Harness Preflight

Date: 2026-05-31

Status: Wave 1 metadata foundation and Wave 2A taxonomy-safe metadata rollout
implemented; Wave 2B probes and human product review remain pending.

## 1. Purpose

Redesign the Raw Query Answer QA workflow so the same curated corpus supports
two distinct jobs:

1. machine regression testing
2. human + ChatGPT product review of whether the corpus represents the public
   query surface

The existing harness is useful and should remain the regression foundation. The
missing layer is a generated product-review artifact that makes feature-family
coverage, representative answers, obvious sibling variants, unsupported
boundaries, and unresolved product decisions visible before a family is called
public accepted.

This preflight does not change production code, parser/routing behavior, corpus
cases, corpus expectations, saved slices, frontend rendering, or release
status.

## 2. Why This Work Is Needed

The Raw QA harness began as a manual-first answer-review tool. Its original
planning doc says the harness should support manual and ChatGPT review first,
with objective failures promoted into hard expectations over time.

That evolution succeeded at machine regression coverage, but product-review
discipline did not keep pace. A recent miss exposed the workflow gap:

```text
Lakers record with Luka
```

Nearby player-availability behavior existed in the corpus, and the corpus
passed, but this obvious sibling phrasing was absent until public use exposed
it. The defect was fixed later. The remaining issue is procedural: a clean
corpus run still does not answer whether the corpus contains the right examples
for the public surface.

The current durable docs correctly state that raw case count alone is not
enough. The artifact chain does not yet prove the stronger claim:

```text
Every public feature family has a reviewed, representative set of real-user
examples, including obvious siblings, inverse forms, and nearby unsupported
boundaries.
```

## 3. Current-State Inventory

### 3.1 Corpus

`qa/raw_query_answer_corpus.yaml` is a version-1 YAML corpus with 294 cases.

Required fields enforced by `tools/raw_query_answer_qa.py`:

| Field | Purpose |
| --- | --- |
| `id` | Stable case identifier |
| `query` | Natural-language input |
| `category` | Existing regression-oriented grouping |
| `priority` | Existing `p0`, `p1`, or `p2` review priority |
| `expected_status` | Required result-status expectation |

Existing optional expectation fields:

| Field | Purpose |
| --- | --- |
| `expected_route` | Route assertion |
| `expected_reason` | Result-reason assertion |
| `expected_shape` | Backend-approximation shape assertion |
| `expected_filters` | Applied-filter assertions |
| `expected_sections` | Required or empty section assertions |
| `expected_row_counts` | Exact row-count assertions |
| `hard_assertions` | Exact dot-path equality checks against the result payload |
| `review_notes` | Case-specific review context |

Existing review-oriented extensions:

| Field | Current behavior |
| --- | --- |
| `answer_text_policy` | Validates backend-answer-text, frontend-hero, or no-answer-text expectations |
| `manual_review` | Records status, tags, and notes; omitted cases normalize to `unreviewed` |
| `acceptance` | Present on 67 cases, but not validated or emitted by the harness |

The corpus currently has:

| Metric | Count |
| --- | ---: |
| Cases | 294 |
| Cases with `hard_assertions` | 140 |
| Cases with `answer_text_policy` | 249 |
| Cases with `manual_review` | 189 |
| Cases with `acceptance` | 67 |

The existing `acceptance` metadata currently uses only:

| Field | Tagged cases |
| --- | ---: |
| `acceptance.family` | 67 |
| `acceptance.variant` | 67 |
| `acceptance.no_broad_fallback` | 48 |

### 3.2 Saved Slices

The current saved slices under `qa/harness_slices/` are:

| Slice | Purpose |
| --- | --- |
| `basic_public_availability` | Team-record player-availability regression family |
| `defensive_aliases` | Defensive and opponent-points aliases |
| `natural_query_route_priority` | Collision, unsupported-boundary, and no-broad-fallback cases |
| `player_entity_stat_context` | Player entity, stat alias, count/finder, and recent context |
| `playoff_phrasing` | Playoff history, matchup, Finals, and round-record phrasing |
| `product_boundaries` | Explicit unsupported/no-result behavior |
| `public_query_acceptance` | Public-query acceptance seed and later hardening waves |
| `team_date_context` | Team records with date and recent context |

Saved slices are useful runnable subsets. They do not define a feature-family
contract or identify missing variants.

### 3.3 Current Harness Outputs

`tools/raw_query_answer_qa.py` currently writes:

```text
outputs/raw_query_answer_qa/<run_id>/report.jsonl
outputs/raw_query_answer_qa/<run_id>/report.md
outputs/raw_query_answer_qa/<run_id>/summary.json
```

The script supports:

- exact route/status/reason/shape assertions
- expected filters, sections, row counts, and hard assertions
- selected cases, saved slices, failure reruns, and run comparisons
- answer-text policies
- manual-review metadata
- suspicious, informational, and verified-outlier flags
- compact answer summaries and top rows for manual inspection

The Markdown report already includes useful query-review cards with:

- expected and actual route/status/shape information
- backend answer text when present
- compact answer summaries
- applied filters
- section counts
- representative top rows
- notes, caveats, and review flags

The latest `public_query_acceptance` report is:

```text
outputs/raw_query_answer_qa/20260528T225801Z/report.md
```

It records 67/67 expectation cases passing, 409 passing checks, 0 suspicious
flag cases, and 54 `unreviewed` manual-review statuses.

### 3.4 What The Current Report Does Not Show

The report is regression-readable, but it is not a product-review harness. It
does not:

- validate or emit `acceptance` metadata
- group results by `acceptance.family`
- distinguish regression category from public feature family
- show required variants per family
- highlight missing sibling or inverse variants
- identify which cases are representative outputs for human review
- turn `acceptance.no_broad_fallback` into an enforced assertion policy
- collect coverage questions per family
- collect product-decision rows
- prove that representative public examples were human-reviewed
- give the user an exact handoff block to send ChatGPT

The existing `family` field in `report.jsonl` comes from runtime query metadata.
It is not the public-acceptance family and cannot replace
`acceptance.family`.

## 4. Current Workflow Gap

### 4.1 Pass Counts Replaced Product Review

The current workflow has strong machine evidence:

- `public_query_acceptance` is a saved 67-case gate
- route/status/shape assertions pass
- release evidence records the clean targeted run

The reporting path compresses that evidence to a pass count. It does not
require someone to review whether the selected examples form a credible public
surface.

The latest public-acceptance slice contains 17 tagged families. Only
`team_record_availability` currently has all seven general-purpose variant
types represented. This does not mean every other family is defective: some
variants may be non-applicable or intentionally unsupported. It means the
current artifact cannot tell the difference between:

- covered
- intentionally unsupported
- not applicable
- missing
- needs a product decision

That ambiguity is the workflow defect.

### 4.2 Obvious Siblings Can Be Missed

The existing slice is a manually maintained case-ID list. Adding a canonical
case does not trigger a visible checklist for:

- search-bar fragment form
- full sentence form
- common synonym
- inverse filter
- adjacent supported route
- nearby unsupported route
- typo or partial entity behavior

The Luka availability miss was an example of an absent obvious sibling. Similar
omissions remain possible even when every selected case passes.

### 4.3 Readiness Evidence Is Too Compressed

`docs/reference/raw_product_release_status.md` correctly
says broad raw QA coverage without family-level phrasing coverage is not enough.
It then records public-query acceptance as `PASS` with a `67/67 passed`
artifact. That artifact proves machine expectations. It does not prove that
representative answers and coverage shape were reviewed by a human.

`docs/operations/raw_query_answer_qa.md` and
`docs/operations/query_validation_map.md` now document the generated
product-review workflow and current validation scoreboard. The pre-existing
matrix was not generated from the live corpus and could not expose later drift
automatically.

Future return packages should not treat raw count, slice count, or green checks
as sufficient product-review evidence.

## 5. Target Design: Two Layers

The Raw QA corpus remains one source of truth. The workflow gains two explicit
layers with separate statuses.

### 5.1 Layer A: Machine Regression

Purpose: prove that selected queries still behave according to stable engine
contracts.

Keep and strengthen:

- exact route/status/reason/shape assertions
- expected applied filters
- expected sections and empty-section assertions
- row counts where deterministic
- hard dot-path assertions
- answer-text policy checks
- saved slices
- failed-case reruns and comparisons
- `--fail-on-expectation-failure`

Layer A status:

```text
machine_regression: pass | fail
```

Layer A must stay runnable without human input.

### 5.2 Layer B: Human Product Review

Purpose: prove that the corpus examples represent the public query surface and
that representative outputs look correct to a product reviewer.

Add:

- a public feature-family registry
- feature-family coverage matrices
- required-variant completeness checks
- representative rendered answer outputs
- missing sibling/inverse checklists
- unsupported/no-broad-fallback rows
- product-decision rows
- explicit `needs human review` markers
- review questions for each family
- exact ChatGPT handoff instructions

Layer B statuses:

```text
coverage_review: complete | missing_variants | needs_product_decision
human_review: pending | reviewed_pass | reviewed_followup
```

A green Layer A run must not silently imply a green Layer B review.

## 6. Proposed Metadata Model

### 6.1 Per-Case Metadata

Extend the existing optional `acceptance` mapping. Do not retag cases in this
preflight.

```yaml
acceptance:
  public_surface: true
  family: team_record_availability
  concept: whole_game_player_presence
  variant: canonical
  review_required: true
  review_role: representative
  no_broad_fallback: true
  sibling_of: lakers_record_without_luka_public_sweep
  intent_model: team_record
  qualifier_model:
    - with_player
```

Field definitions:

| Field | Type | Purpose |
| --- | --- | --- |
| `public_surface` | boolean | Marks cases that participate in public-product acceptance |
| `family` | string | Stable public feature family |
| `concept` | string | Narrow capability or boundary within the family |
| `variant` | enum | Coverage-grid role |
| `review_required` | boolean | Requires representative human review before family acceptance |
| `review_role` | enum | `representative`, `supporting`, `boundary`, or `decision` |
| `no_broad_fallback` | boolean | Requires machine proof that scope was not silently widened |
| `sibling_of` | string or list | Links an inverse or adjacent route to another case ID |
| `intent_model` | string | Product-level main intent expected from the phrasing |
| `qualifier_model` | list of strings | Product-level qualifiers the case is meant to preserve or reject |

Allowed `variant` values:

```text
canonical
short
sentence
synonym
inverse_sibling
nearby_unsupported
typo_partial
```

Existing metadata remains valid during migration. New fields should become
required only for the public subset as it is retagged in Wave 2.

### 6.2 Family Registry

Per-case metadata cannot explain whether a missing variant is acceptable.
Add a planned registry:

```text
qa/raw_query_answer_acceptance_families.yaml
```

Proposed shape:

```yaml
version: 1
surface: public_query_acceptance
families:
  - id: team_record_availability
    label: Team record with or without player
    public_surface: true
    required_variants:
      - canonical
      - short
      - sentence
      - synonym
      - inverse_sibling
      - nearby_unsupported
      - typo_partial
    coverage_questions:
      - Do presence and absence wording stay on the team-record route?
      - Does compound availability fail cleanly without a broad record?
    product_decisions: []
```

Each family registry entry should define:

- family ID and display label
- whether the family is public
- required variants
- explicitly non-applicable variants with reasons
- intentionally unsupported variants with reasons
- coverage questions
- expected nearby sibling families
- open product decisions

The registry turns missing rows into a visible state instead of an inference.

### 6.3 No-Broad-Fallback Enforcement

`acceptance.no_broad_fallback: true` is descriptive today. Wave 1 should make it
an enforced metadata contract.

For supported cases, require:

- exact expected route
- exact expected status
- at least one distinctive proof that requested scope survived, such as an
  applied filter, metadata hard assertion, section assertion, or stable summary
  assertion

For unsupported or guarded cases, require:

- expected non-`ok` status
- expected reason where stable
- empty expected sections for no-result behavior
- stable `metadata.unsupported_filters` hard assertion when the route uses one

The harness should fail metadata validation when a no-broad-fallback case lacks
proof. It should not invent assertions automatically.

## 7. Proposed Product-Review Artifact

Wave 1 should add a generated artifact alongside the current reports:

```text
outputs/raw_query_answer_qa/<run_id>/product_review.md
```

The existing files remain:

```text
report.jsonl
report.md
summary.json
```

Optional structured companion:

```text
product_review.json
```

### 7.1 Required Sections

`product_review.md` should include:

1. Run metadata and review status
2. Feature-family summary
3. Variant coverage matrix
4. Missing sibling/inverse checklist
5. Representative outputs requiring human review
6. Unsupported and no-broad-fallback rows
7. Product decisions needed
8. Top suspicious rows
9. Human review worksheet
10. Exact ChatGPT handoff instructions

### 7.2 Feature-Family Summary

Required columns:

| Column | Meaning |
| --- | --- |
| Family | Public feature family |
| Public | Whether the family is part of the advertised surface |
| Cases | Tagged cases run |
| Machine pass/fail | Layer A result counts |
| Required variants | Registry contract |
| Covered variants | Variants represented by tagged cases |
| Missing variants | Unresolved omissions |
| Intentional unsupported | Documented boundaries |
| Human review | `pending`, `reviewed_pass`, or `reviewed_followup` |
| Public accepted | `yes` only when the full rule in §10 passes |

### 7.3 Representative Output Cards

For `review_required: true` cases, show:

- query text
- family, concept, and variant
- expected route/status/shape
- actual route/status/shape
- answer text or compact answer summary
- applied filters
- section names and row counts
- top rows capped to a small review-friendly number
- sibling links
- coverage question
- reviewer checkbox and notes placeholder

The artifact is review-oriented. It should not dump every full result table.
The existing JSONL and Markdown report remain available for drill-down.

### 7.4 Missing Variant Checklist

For each family, list every required variant with one state:

```text
covered
intentionally_unsupported
not_applicable
missing
needs_product_decision
```

Any `missing` or `needs_product_decision` row blocks `public accepted`.

### 7.5 Exact ChatGPT Handoff Block

The report should end with a copyable block similar to:

```text
Review this NBA Tools Raw QA product-review artifact as a product coverage
audit. Do not treat machine pass counts as sufficient. For each feature
family:
1. Decide whether the examples represent real public usage.
2. Flag missing canonical, short, sentence, synonym, sibling/inverse,
   nearby-unsupported, or typo/partial variants.
3. Review the representative answer outputs for wrong scope, misleading
   answers, and broad fallback.
4. Separate behavior bugs from corpus gaps and product decisions.
5. Return a family-by-family table with verdict, missing cases, suspicious
   outputs, and recommended next action.
```

## 8. Product-Review Workflow

### 8.1 Run

Generate Layer A and Layer B artifacts together:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --fail-on-expectation-failure
```

### 8.2 Review

The user opens:

```text
outputs/raw_query_answer_qa/<run_id>/product_review.md
```

The user sends that artifact, or its key sections, to ChatGPT. ChatGPT helps
identify corpus gaps, suspicious answers, and product decisions. The user owns
the final product decision.

### 8.3 Execute Follow-Up

Agents execute only the reviewed follow-up:

- corpus metadata additions
- small corpus case additions
- behavior fixes
- docs updates
- explicit product-decision records

Do not automatically mutate parser/routing behavior from generated review
suggestions.

Ownership rule:

```text
Machine regression = harness.
Product coverage triage = human + ChatGPT.
Approved follow-up execution = agent.
```

## 9. Required Return-Package Format For Corpus Waves

Every future Raw QA corpus wave return package must include these sections.

### 9.1 Feature-Family Coverage Table

| Family | Concepts touched | Variants before | Variants after | Machine gate | Human review | Public accepted |
| --- | --- | --- | --- | --- | --- | --- |

### 9.2 Cases Changed

| Case ID | Change type | Family | Concept | Variant | Why |
| --- | --- | --- | --- | --- | --- |

Allowed change types:

```text
added
reused
retagged
removed_only_by_explicit_separate_approval
```

Normal corpus waves must not delete or weaken existing cases.

### 9.3 Representative Outputs Reviewed

| Case ID | Query | Actual route/status/shape | Answer reviewed | Reviewer outcome |
| --- | --- | --- | --- | --- |

### 9.4 Gaps Intentionally Left

| Family | Missing or deferred variant | Reason | Follow-up |
| --- | --- | --- | --- |

### 9.5 Product Decisions Needed

| Family | Question | Current behavior | Decision owner | Next action |
| --- | --- | --- | --- | --- |

### 9.6 Behavior Failures Found

| Case ID | Failure type | Actual behavior | Expected behavior | Fix wave |
| --- | --- | --- | --- | --- |

### 9.7 Review Declaration

Every package must explicitly answer:

```text
Was the corpus itself reviewed for public-surface coverage, or did only the
machine expectations pass?
```

The answer must be one of:

```text
machine_only
human_review_pending
human_review_complete
human_review_complete_with_followup
```

## 10. Public-Accepted Definition

A feature family must not be called `public accepted` unless all applicable
conditions are satisfied:

- canonical phrase passes
- short/casual phrase passes or is intentionally unsupported
- natural sentence phrase passes or is intentionally unsupported
- synonym phrase passes or is intentionally unsupported
- inverse/sibling phrase passes where applicable
- nearby unsupported phrase returns a clean no-result or explicit unsupported
  response without broad fallback
- typo/partial entity behavior is tested where relevant
- route/status/shape assertions pass
- no-broad-fallback proof is present and passes
- representative outputs have been human-reviewed
- missing variants are resolved as covered, intentionally unsupported, or
  explicitly not applicable
- open product decisions are resolved or explicitly block acceptance

The statuses must remain separate:

```text
machine regression passed
coverage matrix complete
representative outputs human-reviewed
feature family public accepted
```

No one of these statements implies the others.

## 11. Docs And Rules To Update During Execution

Wave 1 should update durable workflow rules after the artifact exists.

| File | Planned update |
| --- | --- |
| `docs/operations/raw_query_answer_qa.md` | New runbook for Layer A runs, Layer B review, human + ChatGPT handoff, and return-package requirements |
| `docs/index.md` | Link the new operations runbook |
| `AGENTS.md` | Require product-review artifacts and corpus-review declarations for public corpus waves; prohibit readiness claims from counts alone |
| `docs/operations/raw_query_answer_qa.md` | Keep the verified harness workflow in the durable operations runbook |
| `docs/operations/raw_query_answer_qa.md` and `docs/operations/query_validation_map.md` | Separate the green Layer A gate from pending or completed Layer B product review and keep the current validation scoreboard durable |
| `docs/reference/raw_product_release_status.md` | Record machine regression and human product review as separate evidence rows without changing release status automatically |
| `docs/operations/parser_routing_growth_guardrails.md` | Add the family-registry and representative-human-review requirement for public feature promotion |
| `docs/reference/query_catalog.md` | Tighten the maintenance note so advertised families require both generated family coverage and reviewed representative outputs |

There is no existing `docs/operations/qa.md`. Prefer the workflow-specific
`docs/operations/raw_query_answer_qa.md` name.

## 12. Execution Plan

### Wave 1: Metadata Foundation And Report Artifact

Goal: make product review possible without changing query behavior.

Implement:

- add `qa/raw_query_answer_acceptance_families.yaml`
- extend `tools/raw_query_answer_qa.py` to validate and emit acceptance metadata
- generate `product_review.md` and optionally `product_review.json`
- add metadata validation for `no_broad_fallback` proof
- retag only a small representative subset across a few families
- add focused harness tests
- add `docs/operations/raw_query_answer_qa.md`
- update the durable docs and rules listed in §11 as appropriate

Do not:

- change production behavior
- change parser/routing behavior
- change frontend rendering
- add large corpus batches
- change release status

Acceptance:

- existing regression outputs remain available
- existing corpus cases still run
- product-review artifact groups cases by public family
- missing variants are visible
- representative answer cards are visible
- no-broad-fallback metadata validation fails incomplete tagged cases
- docs explain that machine pass does not equal public acceptance

### Wave 2: Public-Acceptance Metadata Rollout And Review

Goal: apply the Layer B model to the current public slice and perform the first
explicit coverage review.

Implement:

- retag `public_query_acceptance` cases with the full metadata structure
- define every public family in the registry
- mark required, intentionally unsupported, and non-applicable variants
- generate the complete feature-family matrix
- generate `product_review.md`
- send the report to ChatGPT for family-by-family product review
- record user decisions
- produce a corpus-wave return package using §9

Do not:

- hide gaps by marking them non-applicable without a reason
- add broad new case batches before reviewing the generated matrix
- change behavior as a side effect of metadata rollout

Acceptance:

- every public family appears in the generated matrix
- every required variant has an explicit state
- representative outputs have review outcomes
- behavior bugs, corpus gaps, and product decisions are separated

### Wave 3: Fix Reviewed Behavior Gaps

Goal: execute bounded fixes only for confirmed behavior defects.

For each approved gap:

1. write or retain the failing Raw QA case
2. fix the smallest production behavior surface
3. run the focused parser/query tests required by the touched area
4. rerun the closest Raw QA slice
5. rerun `public_query_acceptance`
6. regenerate and review `product_review.md`
7. update durable docs only after behavior is verified
8. write a PR-sized return package using §9

Corpus-only gaps and product decisions should remain separate PR-sized waves.

## 13. Validation Plan

This preflight is docs-only. Validate it with:

```bash
git diff --check
```

No Markdown lint command is currently configured in the repo. If a Markdown
lint tool is added later, include the new preflight and return package in that
check.

Wave 1 should add focused harness tests and run:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --fail-on-expectation-failure
git diff --check
```

## 14. Preflight Acceptance Checklist

- [x] Current corpus structure is inventoried.
- [x] Current slices and report artifacts are inventoried.
- [x] The workflow gap between regression passing and product review is explicit.
- [x] Layer A machine regression is preserved.
- [x] Layer B human product review is concrete.
- [x] Metadata additions are specified without changing cases.
- [x] `product_review.md` is specified.
- [x] Future corpus-wave return-package requirements are specified.
- [x] Public-accepted criteria are explicit.
- [x] Waves 1-3 are bounded.
- [x] No production code, parser/routing behavior, corpus expectations, frontend rendering, or release status changed.

## 15. Wave 1 Implementation Status

Wave 1 is implemented as behavior-neutral QA tooling and documentation work.

Added:

- `qa/raw_query_answer_acceptance_families.yaml`
- validated optional `acceptance` metadata in `tools/raw_query_answer_qa.py`
- enforced proof for `acceptance.no_broad_fallback: true`
- generated `product_review.md` and `product_review.json`
- four representative case retags to prove the metadata and report shape
- focused harness tests
- `docs/operations/raw_query_answer_qa.md`

The Layer A machine-regression artifacts remain available unchanged:

```text
report.jsonl
report.md
summary.json
```

Wave 1 does not mark families public accepted. The generated artifact exposes
missing variants, pending representative-output review, and product-decision
rows for Wave 2.

Validation artifact:

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_public_acceptance/product_review.md
```

The targeted Layer A run passed 67/67 machine expectations. Layer B remains
`human_review_pending`.

Broader harness safety artifact:

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_full/report.md
```

The full corpus passed 294/294 machine expectations with zero suspicious rows.

## 16. Wave 2A Implementation Status

Wave 2A is implemented as behavior-neutral metadata and corpus-organization
work.

Completed:

- collapsed the overlapping `player_comparisons` registry entry into
  `comparisons`
- reused and retagged `45` existing passing corpus rows
- expanded `public_query_acceptance` by `42` rows, from `67` to `109`
- filled the seven-variant matrix for all `14` public feature families
- marked only the five approved domain-specific typo-guard variants as not
  applicable for `typo_partial_entity_behavior`
- added pending representative-output review cards for every public feature
  family

Validation artifact:

```text
outputs/raw_query_answer_qa/20260531T073042Z_wave2a_taxonomy_safe_retags/product_review.md
```

Wave 2A does not mark families public accepted. Layer B remains
`human_review_pending`; Wave 2B probes and Wave 2C rendered-output review remain
separate follow-up work.
