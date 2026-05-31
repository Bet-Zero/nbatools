# Question-Form Player Comparison Routing Fix Return Package

Date: 2026-05-31

## Objective

Fix the Wave 2B behavior bug where:

```text
How do LeBron James and Kevin Durant compare this season?
```

routed to `player_game_summary`, returned only LeBron James, and dropped Kevin
Durant.

## Root Cause

`extract_player_comparison()` recognized `A vs B` and `Compare A and B`
phrasing, but it did not recognize question-form comparison phrasing:

```text
How do A and B compare ...
```

Because no two-player comparison was extracted, the later single-player
resolver selected the first confident player mention, LeBron James. Routing then
fell through to the normal player-summary default and ignored Kevin Durant.

## Behavior Before And After

| Query | Before | After |
| --- | --- | --- |
| `How do LeBron James and Kevin Durant compare this season?` | `player_game_summary` / `ok`; `summary: 1`, `by_season: 1`, `game_log: 60`; only LeBron James. | `player_compare` / `ok`; `summary: 2`, `comparison: 20`; both LeBron James and Kevin Durant. |
| `How has Luka Doncic played this season?` | `player_game_summary` / `ok`. | Still `player_game_summary` / `ok`; `summary: 1`, `by_season: 1`, `game_log: 64`. |
| `LeBron vs KD` | `player_compare` / `ok`; current silent simple-comparison default. | Unchanged: `player_compare` / `ok`; bare-`vs` product policy remains open. |

## Files Changed

- `src/nbatools/commands/_matchup_utils.py`
- `tests/test_natural_query_parser.py`
- `tests/test_natural_query_route_priority_snapshots.py`
- `tests/test_ui_failure_coverage.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/public_query_acceptance.yaml`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

## Implementation Summary

Added a narrow player-comparison extractor for question-form phrasing matching:

```text
how do <player A> and <player B> compare
```

The helper resolves both phrases through the existing player-resolution path,
rejects team phrases through the existing comparison-player resolver, and only
returns a comparison when both resolved players are confident and distinct.

No frontend code, comparison result contract, release status, subjective
unsupported behavior, or bare-`vs` policy changed.

## Corpus And Test Cases Added

Raw QA corpus:

- `question_form_lebron_durant_comparison_wave2b`
  - Query: `How do LeBron James and Kevin Durant compare this season?`
  - Family: `comparisons`
  - Concept: `player_stat_comparison`
  - Variant: `sentence`
  - Review role: `supporting`
  - Expected route: `player_compare`
  - Expected status: `ok`
  - Expected shape: `comparison`
  - Included in `public_query_acceptance`

Pytest coverage:

- Parser regression:
  - `test_question_form_player_comparison_route`
  - `test_question_form_player_summary_still_routes_to_summary`
- Route-priority snapshot:
  - `How do LeBron James and Kevin Durant compare this season?`
- Query-level data-backed regression:
  - `test_question_form_lebron_durant_comparison_preserves_both_players`

## Proof Both Players Are Preserved

Backend payload after the fix:

```text
route: player_compare
result_status: ok
metadata.player: LeBron James, Kevin Durant
metadata.players_context:
  - LeBron James
  - Kevin Durant
sections:
  summary: 2
  comparison: 20
```

The raw QA case hard-asserts:

- `result.metadata.players_context.0.player_name == LeBron James`
- `result.metadata.players_context.1.player_name == Kevin Durant`
- `result.sections.summary.0.player_name == LeBron James`
- `result.sections.summary.1.player_name == Kevin Durant`
- `result.sections.comparison.0.metric == games`
- `result.sections.comparison.0.LeBron James == 60.0`
- `result.sections.comparison.0.Kevin Durant == 78.0`

## Proof Player Summary Behavior Still Works

Focused parser proof:

```text
How has Luka Doncic played this season?
route: player_game_summary
player: Luka Doncic
player_a: None
player_b: None
```

Backend payload smoke after the fix:

```text
How has Luka Doncic played this season?
route: player_game_summary
result_status: ok
sections: summary: 1, by_season: 1, game_log: 64
```

The full `public_query_acceptance` raw QA slice also preserved the existing Luka
summary cases.

## Proof Bare `LeBron vs KD` Policy Was Not Changed

Backend payload smoke after the fix:

```text
LeBron vs KD
route: player_compare
result_status: ok
sections: summary: 2, comparison: 20
```

The Wave 2B docs still classify bare `LeBron vs KD` as product-decision
required. No corpus expectation was added for bare `LeBron vs KD`.

## Validation Results

Focused validation:

- `.venv/bin/pytest tests/test_natural_query_parser.py::test_question_form_player_comparison_route tests/test_natural_query_parser.py::test_question_form_player_summary_still_routes_to_summary -n0 -q`: `2 passed`
- `.venv/bin/pytest tests/test_natural_query_route_priority_snapshots.py::test_route_priority_collision_snapshot -n0 -q`: `26 passed`
- `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestP2BoundaryRoutingCleanup::test_question_form_lebron_durant_comparison_preserves_both_players -n0 -q`: `1 passed`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case question_form_lebron_durant_comparison_wave2b --fail-on-expectation-failure`: `1` case, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T081254Z`

Required validation:

- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure`: `110` cases, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T081624Z`
- `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure`: `49` cases, expectations `pass`; output `outputs/raw_query_answer_qa/20260531T081858Z`
- `make PYTEST=.venv/bin/pytest test-parser`: `791 passed`
- `make PYTEST=.venv/bin/pytest test-query`: `804 passed`
- `git diff --check`: passed
- `git diff --check --no-index /dev/null return_packages/raw-product/QUESTION_FORM_PLAYER_COMPARISON_ROUTING_FIX_RETURN_PACKAGE.md`: no whitespace warnings; exit code `1` is expected for a `/dev/null` comparison with file content

Markdown lint:

- `markdownlint` was not installed.
- `markdownlint-cli2` was not installed.
- No repo-local markdown lint target was found in `frontend/package.json`,
  `pyproject.toml`, or `Makefile`.

## Next Recommended Action

Make the bare `PLAYER vs PLAYER` product decision. The Wave 2B probe results
still recommend clarification / intent options for bare `LeBron vs KD`, and
that policy remains intentionally unchanged by this routing fix.
