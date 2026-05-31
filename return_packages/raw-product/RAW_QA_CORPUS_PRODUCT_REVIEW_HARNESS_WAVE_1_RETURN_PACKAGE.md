# Raw QA Corpus Product Review Harness Wave 1 Return Package

Date: 2026-05-31

Status: Wave 1 complete; behavior-neutral metadata foundation and generated
product-review artifact implemented.

## Summary

Raw Query Answer QA now supports two explicit layers:

| Layer | Purpose | Status |
| --- | --- | --- |
| Layer A | Existing machine regression checks | Preserved and passing |
| Layer B | Family-level human + ChatGPT product review | Implemented; human review pending |

Existing query execution, parser/routing behavior, result behavior, frontend
rendering, corpus expectations, and release status were not changed.

## What Changed

Added:

- `qa/raw_query_answer_acceptance_families.yaml`
- acceptance metadata validation in `tools/raw_query_answer_qa.py`
- enforced proof for `acceptance.no_broad_fallback: true`
- `outputs/raw_query_answer_qa/<run_id>/product_review.md`
- `outputs/raw_query_answer_qa/<run_id>/product_review.json`
- focused harness tests
- `docs/operations/raw_query_answer_qa.md`

The existing artifacts remain:

```text
report.jsonl
report.md
summary.json
```

## Metadata Foundation

Validated per-case fields:

| Field | Validation |
| --- | --- |
| `acceptance.family` | Required non-empty registry ID when `acceptance` is present |
| `acceptance.variant` | Required enum: `canonical`, `short`, `sentence`, `synonym`, `inverse_sibling`, `nearby_unsupported`, or `typo_partial` |
| `acceptance.concept` | Optional non-empty string |
| `acceptance.review_required` | Optional boolean |
| `acceptance.review_role` | Optional enum: `representative`, `supporting`, `boundary`, or `decision` |
| `acceptance.public_surface` | Optional boolean |
| `acceptance.no_broad_fallback` | Optional boolean with enforced proof |
| `acceptance.sibling_of` | Optional case ID or list of case IDs; referenced IDs must exist |
| `acceptance.intent_model` | Optional non-empty string |
| `acceptance.qualifier_model` | Optional list of non-empty strings |

Existing `family`, `variant`, and `no_broad_fallback` tags remain valid during
the staged migration.

## Family Registry

Registry:

```text
qa/raw_query_answer_acceptance_families.yaml
```

Summary:

| Metric | Count |
| --- | ---: |
| Registered families | 17 |
| Public-surface families | 15 |
| Guardrail-only families | 2 |
| Acceptance-tagged corpus cases | 67 |
| Guarded `no_broad_fallback` cases | 48 |

The registry defines labels, public-surface status, required variants,
coverage questions, sibling families, optional explicit resolutions, and
product-decision rows.

## Representative Retags

Only four existing cases were retagged to prove the expanded metadata and
report shape:

| Case ID | Family | Concept | Variant | Review role |
| --- | --- | --- | --- | --- |
| `points_per_game_leader` | `leaderboards` | `player_season_per_game_leader` | `canonical` | `representative` |
| `lakers_record_with_luka_public_sweep` | `team_record_availability` | `whole_game_player_presence` | `canonical` | `representative` |
| `lakers_record_with_reaves_without_luka_public_sweep` | `team_record_availability` | `multi_player_availability_boundary` | `nearby_unsupported` | `boundary` |
| `pqa_player_stats_sentence_luka_played` | `player_stats_this_season` | `player_season_summary` | `sentence` | `representative` |

No corpus case, expectation, or saved slice was deleted or weakened.

## Product-Review Artifact

Targeted validation artifact:

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_public_acceptance/product_review.md
```

Structured companion:

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_public_acceptance/product_review.json
```

Generated artifact summary:

| Metric | Result |
| --- | --- |
| Families shown | 17 |
| Representative output cards | 4 |
| Unsupported / no-broad-fallback rows | 48 |
| Product-decision rows | 1 |
| Suspicious rows | 0 |
| Auto-promoted public-accepted families | 0 |

The one product-decision row makes the current split between `comparisons` and
`player_comparisons` acceptance tags visible for Wave 2 taxonomy review.

## Public Query Acceptance Result

Command:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --fail-on-expectation-failure \
  --run-id 20260531T064312Z_wave1_public_acceptance
```

Result:

| Metric | Result |
| --- | --- |
| Cases | 67 |
| Machine expectations | `pass: 67` |
| Failed case IDs | none |
| Suspicious rows | 0 |
| Informational flag cases | 23 |
| Verified outlier cases | 1 |

## Human Review Status

```text
human_review_pending
```

Wave 1 generated reviewable outputs but did not perform or claim the first
family-by-family human + ChatGPT review.

Current artifact posture:

- all 17 registered families are visible
- `team_record_availability` has a complete seven-variant matrix but still
  needs representative-output human review
- other families visibly retain missing variants or the taxonomy decision row
- all four representative cards remain `unreviewed`
- no family is marked public accepted

## No-Broad-Fallback Enforcement

`acceptance.no_broad_fallback: true` is no longer descriptive-only metadata.

Supported guarded cases require:

- one exact `expected_status`
- explicit `expected_route`
- filters, sections, row counts, or hard assertions proving scoped behavior

Unsupported guarded cases require:

- one exact non-`ok` status
- explicit `expected_route`, including `null` for unrouted cases
- an expected reason, empty sections, filters, or hard assertions proving the
  boundary

The harness fails metadata validation before query execution when proof is
missing. Existing 48 guarded cases validate successfully.

## Tests Added

Focused tests cover:

- extended acceptance metadata parsing and validation
- unknown acceptance-field rejection
- descriptive-only no-broad-fallback metadata rejection
- family registry loading
- validated `public_query_acceptance` slice loading
- `product_review.md` matrix, representative card, guard row, decision section,
  suspicious section, and ChatGPT handoff generation

## Validation

Passed:

```bash
.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0
```

Result: `23 passed`.

Passed:

```bash
.venv/bin/ruff check tools/raw_query_answer_qa.py tests/test_raw_query_answer_qa.py
.venv/bin/ruff format --check tools/raw_query_answer_qa.py tests/test_raw_query_answer_qa.py
git diff --check
```

Broader shared-harness safety run passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --fail-on-expectation-failure \
  --run-id 20260531T064312Z_wave1_full
```

Broader result:

| Metric | Result |
| --- | --- |
| Cases | 294 |
| Machine expectations | `pass: 294` |
| Failed case IDs | none |
| Suspicious rows | 0 |
| Informational flag cases | 166 |
| Verified outlier cases | 1 |

Markdown lint was not run because no `markdownlint`, `markdownlint-cli2`,
`mdl`, or `mdformat` command is installed or configured.

## Documentation Updated

- `AGENTS.md`
- `docs/index.md`
- `docs/operations/raw_query_answer_qa.md`
- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/reference/query_catalog.md`

## Release Impact

None. This wave is QA tooling, metadata, generated-artifact, test, and
documentation work only. It does not change release status or claim completed
Layer B product review.

## Review Declaration

```text
human_review_pending
```

## Next Wave Recommendation

Execute Wave 2 from
`docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md`:
roll the expanded metadata across the current public slice, review the
generated family matrix and representative outputs with ChatGPT, record user
decisions, and keep behavior fixes in separate bounded follow-up waves.
