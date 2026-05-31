# Public Query Acceptance Wave 2B Probes Return Package

Date: 2026-05-31

## Objective

Execute Wave 2B from
`docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md` by
probing product-decision and semantics-risk queries before changing behavior or
adding expectations.

## Files Created

- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBES_RETURN_PACKAGE.md`

## Files Updated

- `docs/index.md` to index the new durable planning doc.

## Behavior And Corpus Changes

- Production code changed: no.
- Parser/routing behavior changed: no.
- Frontend rendering changed: no.
- Release status changed: no.
- Corpus expectations changed: no.
- Public-accepted families changed: no.

## Probe Method

All probes ran through the backend payload path:

```text
nbatools.query_service.execute_natural_query(query)
nbatools.api_handlers.query_result_to_payload(result)
```

This is the same `QueryResponse` envelope path used by the API/UI layer.

## Required Probe Outcomes

| Query | Route | Status | Reason | Classification |
| --- | --- | --- | --- | --- |
| `LeBron vs KD` | `player_compare` | `ok` |  | Product decision required. |
| `How do LeBron James and Kevin Durant compare this season?` | `player_game_summary` | `ok` |  | Behavior bug. |
| `Who are the MVP candidates?` |  | `error` | `unrouted` | Semantic cleanup candidate; acceptable unsupported behavior for now. |
| `who has cooled off lately` |  | `error` | `unrouted` | Semantic cleanup candidate; acceptable unsupported behavior for now. |
| `how many players played this season` |  | `error` | `unrouted` | Acceptable unsupported behavior; semantic cleanup candidate. |
| `most rebunds in a game this season` |  | `error` | `unrouted` | Semantic cleanup candidate. |
| `Lakeers playoff history` |  | `error` | `unrouted` | Semantic cleanup candidate. |

Detailed per-probe route, status, reason, result shape, sections, filters, top
rows, scope preservation, broad-fallback review, and classification are recorded
in `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`.

## Product Decision Recommendation

For bare `LeBron vs KD`, recommend option 1: clarification / intent options.

Reason:

- The current result is a plausible `player_compare` answer.
- The query is still ambiguous under the documented natural-search boundary.
- Public-accepting the silent default would choose one interpretation before the
  product has decided between simple comparison, player head-to-head games,
  team matchup history, and playoff matchup history.

No expected-ok corpus row should be added for bare `LeBron vs KD` until this
policy is accepted.

## Behavior Bug

`How do LeBron James and Kevin Durant compare this season?` currently routes to
`player_game_summary`, returns only LeBron James, and drops Kevin Durant.

This is not a product decision. It is a comparison routing bug. Do not encode
the current result as expected.

## Safe Corpus Addition State

No required probe is a safe expected-ok corpus addition in its current behavior.

Future safe additions:

- Add `How do LeBron James and Kevin Durant compare this season?` after the
  route is fixed to `player_compare`.
- Add bare `LeBron vs KD` only after the bare-`vs` product decision is made and
  the expected route/status/reason shape matches that decision.

## Validation

Completed:

- Backend payload probes: passed.
- `git diff --check`: passed for tracked diff state.
- `git diff --check --no-index /dev/null docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`: no whitespace warnings; exit code `1` is expected for a `/dev/null` comparison with file content.
- `git diff --check --no-index /dev/null return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBES_RETURN_PACKAGE.md`: no whitespace warnings; exit code `1` is expected for a `/dev/null` comparison with file content.

Markdown lint:

- `markdownlint` was not installed.
- `markdownlint-cli2` was not installed.
- No markdown lint command was available locally without installing tools.

## Next Action

1. Fix the question-form comparison parser/routing bug.
2. Add a regression for the fixed query with expected route `player_compare`,
   status `ok`, and both players present in metadata/sections.
3. Make the bare `PLAYER vs PLAYER` product decision. Recommended decision:
   clarification / intent options.
4. Run a separate semantic-cleanup wave for recognizable unsupported concepts
   that currently return `error` / `unrouted`.
