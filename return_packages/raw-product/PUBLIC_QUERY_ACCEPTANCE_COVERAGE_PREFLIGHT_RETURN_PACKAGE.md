# Public Query Acceptance Coverage Preflight Return Package

## What Was Done

- Reviewed the advertised query surface in `query_catalog.md` and
  `query_guide.md`.
- Reviewed Raw Product release/evidence docs, parser/routing guardrails, the
  natural-query decision matrix, the raw QA corpus, and existing harness slices.
- Designed a public-query acceptance coverage system for every advertised Raw
  Product family.
- Created the planning preflight:
  `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`

No production code, parser/routing behavior, frontend rendering, QA corpus
expectations, saved harness slices, or release status changed.

## Main Finding

The raw QA corpus has broad product coverage, and several saved slices protect
important route-priority and unsupported-boundary behavior. The gap is that no
system requires each advertised public family to have the same sibling phrase
matrix: canonical, short, natural sentence, synonym, inverse/sibling, nearby
unsupported, typo/partial, and no-broad-fallback assertions.

The recent team-record availability issue was a symptom of that design gap:
the corpus could pass canonical examples while missing obvious public variants.

## Recommended Strategy

Use one expectation source:

- Keep acceptance cases in `qa/raw_query_answer_corpus.yaml`.
- Add a saved slice `qa/harness_slices/public_query_acceptance.yaml`.
- Add lightweight per-case `acceptance` metadata for family, variant, and
  no-broad-fallback intent.

Do not create a separate public acceptance corpus. That would duplicate raw QA
expectations and risk drift.

## Proposed Coverage

The preflight proposes exact matrix cases for:

- player stats this season
- team records
- team record with/without player
- player summaries/recent form
- leaderboards
- top single-game performances
- count queries
- game finders
- splits
- streaks
- rolling stretches
- comparisons
- playoff history
- date/window filters
- unsupported subjective/narrative questions
- typo/partial entity behavior

The matrix names existing case IDs to reuse and new `pqa_*` case IDs to add in a
future execution wave. Unsupported rows include explicit no-broad-fallback
assertions.

## Future Execution Plan

1. Probe each proposed new query through the backend payload path.
2. Classify each as already matching, product bug, intentionally unsupported, or
   needs product decision.
3. Add or retag raw QA cases.
4. Add `qa/harness_slices/public_query_acceptance.yaml`.
5. Fix any discovered behavior gaps in PR-sized units before landing corpus
   expectations.
6. Validate with:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
git diff --check
```

If parser/routing or execution changes are needed, also run:

```bash
make test-parser
make test-query
make test-preflight
```

## Validation

Passed:

```bash
git diff --check
```

Because the two requested artifacts are new and untracked, direct `--no-index`
whitespace checks were also run against each new file. They produced no
whitespace diagnostics; the nonzero exit code is expected when comparing
`/dev/null` to a new file.

```bash
git diff --check --no-index -- /dev/null docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md
git diff --check --no-index -- /dev/null return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT_RETURN_PACKAGE.md
```

## Blocking Issues

None for preflight. The next wave should not add all proposed cases blindly.
Probe them first, then split true behavior failures into narrow fix waves rather
than weakening expectations to match current wrong-route behavior.
