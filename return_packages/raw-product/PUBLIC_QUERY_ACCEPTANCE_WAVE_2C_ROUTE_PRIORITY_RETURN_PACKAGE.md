# Public Query Acceptance Wave 2C Route Priority Return Package

## Summary

Wave 2C fixed the last three Wave 1 public-query acceptance route-priority
behavior failures:

- player-specific special-event count shorthand
- team bench-scoring split adjacency
- sentence-form longest-streak phrasing

Production behavior changed only for those three route-priority boundaries. No
fuzzy typo correction, frontend rendering, result-contract change, or new
feature support was added.

## Behavior Before And After

| Query | Before | After |
|---|---|---|
| `count LeBron triple doubles since 2020` | `player_occurrence_leaders` / `ok`; broad occurrence-leaderboard semantics | `player_game_finder` / `ok`; `player=LeBron James`; count + finder sections; 31 triple-doubles |
| `Celtics bench scoring home vs away` | `team_split_summary` / `ok`; broad Celtics home/away split | `game_finder` / `no_result` / `filter_not_supported`; `unsupported_filters=["team_bench_scoring"]`; empty sections |
| `What is Curry's longest streak with at least 3 threes?` | `player_game_finder` / `ok`; ordinary threshold finder rows | `player_streak_finder` / `ok`; `player=Stephen Curry`; streak section; longest 14-game `fg3m>=3` streak |

## Exact Cases Fixed

Added to `qa/raw_query_answer_corpus.yaml` with `acceptance.family`,
`acceptance.variant`, and `acceptance.no_broad_fallback=true`:

- `pqa_count_short_lebron_triple_doubles`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_streak_sentence_curry_3_threes`

Added all three case IDs to `qa/harness_slices/public_query_acceptance.yaml`.

The public acceptance slice now contains 65 cases.

## Files Changed

- `src/nbatools/commands/_occurrence_route_utils.py`
  - Deferred single-player special-event count routing to the generic
    `player_game_finder` count path instead of `player_occurrence_leaders`.
- `src/nbatools/commands/natural_query.py`
  - Moved the team bench-scoring unsupported boundary ahead of team split
    routing so bench/home-away phrasing cannot broaden into `team_split_summary`.
- `src/nbatools/commands/_parse_helpers.py`
  - Stripped trailing sentence punctuation before streak-pattern matching so
    question-form longest-streak phrasing resolves to `player_streak_finder`.
- `tests/test_occurrence_queries.py`
  - Updated count shorthand expectation to `player_game_finder`.
- `tests/test_natural_streak_queries.py`
  - Added sentence-form Curry threes streak parser test.
- `tests/test_natural_query_parser.py`
  - Added Wave 2C route-priority parser coverage and bench/home-away boundary
    param case.
- `tests/test_ui_failure_coverage.py`
  - Added data-backed Wave 2C execution coverage and bench/home-away boundary
    param case.
- `qa/raw_query_answer_corpus.yaml`
  - Added the three target raw QA cases and acceptance metadata.
- `qa/harness_slices/public_query_acceptance.yaml`
  - Added the three target case IDs.
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`
  - Recorded Wave 2C results and validation.
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2C_ROUTE_PRIORITY_RETURN_PACKAGE.md`
  - This return package.

No `docs/reference/query_guide.md` or `docs/reference/query_catalog.md` update
was needed because this wave only corrected route priority for already
documented supported/unsupported boundaries.

## Tests, Corpus, And Slices Changed

Tests added/updated:

- `test_count_triple_doubles_routes_to_player_finder`
- `test_parse_player_longest_threes_streak_sentence_form`
- `test_public_query_wave_2c_route_priority`
- `test_public_query_wave_2c_count_short_lebron_triple_doubles`
- `test_public_query_wave_2c_bench_split_boundary`
- `test_public_query_wave_2c_streak_sentence_curry_threes`

Raw QA cases added:

- `pqa_count_short_lebron_triple_doubles`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_streak_sentence_curry_3_threes`

Harness slices changed:

- `public_query_acceptance`

`basic_public_availability`, `natural_query_route_priority`, and
`product_boundaries` were rerun to prove Wave 2A and 2B behavior stayed green.

## Validation Results

Passed:

```bash
.venv/bin/pytest tests/test_natural_query_parser.py::test_public_query_wave_2c_route_priority tests/test_natural_streak_queries.py::test_parse_player_longest_threes_streak_sentence_form tests/test_occurrence_queries.py::TestOccurrenceCountRouting::test_count_triple_doubles_routes_to_player_finder -n0
```

Result: 5 passed in 88.30s.

Passed:

```bash
.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_public_query_wave_2c_count_short_lebron_triple_doubles tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_public_query_wave_2c_bench_split_boundary tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_public_query_wave_2c_streak_sentence_curry_threes -n0
```

Result: 3 passed in 111.20s.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T120746Z`; 65 cases,
expectation cases `pass: 65`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T120750Z`; 7 cases,
expectation cases `pass: 7`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T120753Z`; 49 cases,
expectation cases `pass: 49`, failed case IDs none.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result: 786 passed in 1578.55s.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result: 803 passed in 2006.10s.

Passed:

```bash
git diff --check
```

Result: no whitespace diagnostics.

## Proof Wave 2C Behavior

Verification probes through `execute_natural_query()` and `parse_query()`
confirmed the target behavior:

| Query | Route | Status / reason | Scope proof | Subject/result proof |
|---|---|---|---|---|
| `count LeBron triple doubles since 2020` | `player_game_finder` | `ok` / `-` | `Special Event=Triple Double`; season range `2020-21 – 2025-26` | LeBron James subject; count 31; finder rows 31 |
| `Celtics bench scoring home vs away` | `game_finder` | `no_result` / `filter_not_supported` | `unsupported_filters=["team_bench_scoring"]` | `team=BOS`; empty sections |
| `What is Curry's longest streak with at least 3 threes?` | `player_streak_finder` | `ok` / `-` | `fg3m>=3`; longest streak | Stephen Curry subject; streak length 14 |

## Proof Waves 2A And 2B Stayed Green

The focused Wave 2C raw QA reruns preserved these adjacent baselines:

| Slice | Preserved behavior |
|---|---|
| `basic_public_availability` | 7/7 cases green; availability shorthand/synonym routing unchanged |
| `natural_query_route_priority` + `product_boundaries` | 49/49 cases green; Wave 2A no-broad-fallback guards unchanged |
| `public_query_acceptance` | 62 prior Wave 1/2A/2B cases remain green alongside the 3 new Wave 2C cases |

Supported sibling probes also stayed supported:

| Query | Preserved behavior |
|---|---|
| `How often has Nikola Jokic recorded a triple-double this season?` | `player_game_finder` / `ok`; count + finder |
| `Celtics bench scoring this season` | `game_finder` / `no_result`; `team_bench_scoring` |
| `Curry longest streak with at least 3 threes` | `player_streak_finder` / `ok` |
| `Lakers record w/ Luka` | `team_record` / `ok`; Wave 2B availability shorthand preserved |
| `Celtcs record this season` | `team_record_leaderboard` / `no_result`; Wave 2A typo guard preserved |

## Remaining Public Query Acceptance Items

Wave 2C closed the last three Wave 1 deferred route-priority behavior
failures. These cases are fixed, not remaining:

- `pqa_count_short_lebron_triple_doubles`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_streak_sentence_curry_3_threes`

No other Wave 1 public-query acceptance behavior failures remain open after
Waves 2A, 2B, and 2C.

The only remaining public-query acceptance items are product-decision cases
still open for typo-tolerant player resolution:

- `pqa_comparison_typo_kevn_durant`
- `pqa_typo_synonym_stephn_averages`
