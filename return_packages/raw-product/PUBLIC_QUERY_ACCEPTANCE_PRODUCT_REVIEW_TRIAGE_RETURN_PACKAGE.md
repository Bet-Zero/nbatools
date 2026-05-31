# Public Query Acceptance Product Review Triage Return Package

Date: 2026-05-31

Status: documentation-only triage complete; Wave 2 execution not started.

## Summary

Created the durable Wave 2 triage plan:

```text
docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md
```

No production code, parser/routing behavior, query result behavior, frontend
rendering, release status, corpus expectations, or public-acceptance claims
changed.

## Artifact Reviewed

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_public_acceptance/product_review.md
```

| Metric | Result |
| --- | --- |
| Cases | `67` |
| Families | `17` |
| Complete variant matrices | `1`: `team_record_availability` |
| Families with missing variants | `16` |
| Machine regression | `pass` |
| Human review | `human_review_pending` |
| Public-accepted families | `0` |
| Suspicious rows | `0` |

## Main Decisions

1. Collapse `comparisons` and `player_comparisons` into one public
   `comparisons` family.
2. Move typo and partial-name comparison behavior under concept
   `comparison_entity_resolution`.
3. Probe bare `LeBron vs KD` before deciding whether natural search should
   clarify, choose a documented default, or return a clean unsupported result.
4. Keep the generic typo guardrail family narrow: feature-specific typo
   variants belong to the owning public family.
5. Keep current `error` / `unrouted` expectations during metadata rollout and
   split semantic normalization into a later bounded cleanup wave.

## Representative Output Review

The four generated representative cards look scope-correct from backend
structured output. All still need public frontend rendered review.

The main rendering risks are:

- hero copy is frontend-derived, not backend-provided
- `64`-row team and player game logs may be visually heavy
- compound availability no-result copy must render as a clean unsupported
  boundary

## Wave 2 Shape

| Wave | Scope |
| --- | --- |
| Wave 2A | Comparison taxonomy migration and safe retags of existing passing cases |
| Wave 2B | Probe genuinely new phrasings and classify safe additions, bugs, or product decisions |
| Wave 2C | Human frontend rendered-output review and regenerated `product_review.md` |
| Follow-up fixes | Separate PR-sized waves only for confirmed behavior defects |

## Files Changed

- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md`
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE_RETURN_PACKAGE.md`
- `docs/index.md`

## Validation

Run for this docs-only pass:

```bash
git diff --check
```

Markdown lint availability was checked. No `markdownlint`,
`markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH.

## Review Declaration

```text
human_review_pending
```

## Immediate Next Action

Execute Wave 2A from the durable triage plan. Resolve the comparison taxonomy
first, then apply only safe metadata retags of existing passing corpus rows.
