# Public Query Acceptance Wave 2B Availability Shorthand Return Package

## Summary

Wave 2B fixed the remaining public-query acceptance failures for
single-player team-record availability shorthand and synonym phrasing.

Production behavior changed only for team-record availability routing:

- `w/ PLAYER` is recognized as a with-player whole-game availability filter
  when a team-record intent is present.
- `with PLAYER available` is recognized as with-player availability when a
  team win/record intent is present.
- Count/finder wording for `How many games did the Lakers win with Reaves
  available?` now keeps the answer subject as the Lakers team record rather
  than Austin Reaves player rows.

No compound multi-player availability support, fuzzy typo correction, frontend
rendering, or result-contract change was added.

## Behavior Before And After

| Query | Before | After |
|---|---|---|
| `Lakers record w/ Luka` | `player_game_summary` / `ok`; Luka Dončić player subject | `team_record` / `ok`; `with_player=Luka Dončić`; Lakers team subject; summary + game log |
| `How many games did the Lakers win with Reaves available?` | `player_game_finder` / `ok`; Austin Reaves player rows | `team_record` / `ok`; `with_player=Austin Reaves`; `wins_only=true`; Lakers team subject; 36 wins |

## Exact Cases Fixed

Added to `qa/raw_query_answer_corpus.yaml` with `acceptance.family`,
`acceptance.variant`, and `acceptance.no_broad_fallback=true`:

- `pqa_availability_short_lakers_w_luka`
- `pqa_availability_synonym_reaves_available`

Added both case IDs to `qa/harness_slices/public_query_acceptance.yaml`.

The public acceptance slice now contains 62 cases.

## Files Changed

- `src/nbatools/commands/_matchup_utils.py`
  - Added `w/ PLAYER` and `with PLAYER available` to whole-game presence
    detection.
  - Added the same patterns to unresolved with-player availability detection.
- `src/nbatools/commands/natural_query.py`
  - Clears the detected player for team-record availability when the query has
    record intent or narrow win-only availability intent.
  - Runs team-record availability routing before player/team finder count
    routing so win-count wording stays on the team-record path.
  - Preserves unsupported multi-player and unresolved availability guards.
- `tests/test_ui_failure_coverage.py`
  - Added parser and data-backed execution coverage for the two target
    phrasings.
- `qa/raw_query_answer_corpus.yaml`
  - Added the two target raw QA cases and acceptance metadata.
- `qa/harness_slices/public_query_acceptance.yaml`
  - Added the two target case IDs.
- `docs/reference/query_catalog.md`
  - Documented the supported `w/ PLAYER` and available-player phrasings.
- `docs/reference/query_guide.md`
  - Added the supported examples to the player-availability team-record guide.
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`
  - Recorded Wave 2B results and validation.
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_AVAILABILITY_SHORTHAND_RETURN_PACKAGE.md`
  - This return package.

## Tests, Corpus, And Slices Changed

Tests added:

- `test_detect_with_player_shorthand`
- `test_detect_with_player_available_form`
- `test_route_team_record_with_player_presence_shorthand`
- `test_route_team_record_with_player_available_win_count`
- `test_single_player_presence_shorthand_executes_with_team_subject`
- `test_single_player_available_win_count_executes_with_team_subject`

Raw QA cases added:

- `pqa_availability_short_lakers_w_luka`
- `pqa_availability_synonym_reaves_available`

Harness slices changed:

- `public_query_acceptance`

`basic_public_availability`, `natural_query_route_priority`, and
`product_boundaries` were not changed; they were rerun to prove existing
availability behavior and no-broad-fallback guards were preserved.

## Validation Results

Passed:

```bash
.venv/bin/pytest tests/test_ui_failure_coverage.py::TestWithoutPlayer -n0
```

Result: 51 passed in 93.71s.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111333Z`; 62 cases,
expectation cases `pass: 62`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111713Z`; 7 cases, expectation
cases `pass: 7`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T111713Z`; 49 cases, expectation
cases `pass: 49`, failed case IDs none.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result: 782 passed in 205.01s.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result: 798 passed in 342.73s.

Passed:

```bash
git diff --check
```

Result: no whitespace diagnostics.

The new untracked return-package file was also checked directly:

```bash
git diff --check --no-index -- /dev/null return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_AVAILABILITY_SHORTHAND_RETURN_PACKAGE.md
```

Result: no whitespace diagnostics; exit code 1 is expected for a `/dev/null`
comparison against a new file.

## Proof Existing Availability Behavior Was Preserved

The focused availability tests and raw QA slices preserved these baselines:

| Query | Preserved behavior |
|---|---|
| `Lakers record with Luka` | `team_record` / `ok`; `with_player=Luka Dončić`; Lakers team subject; 64 games, 43-21 |
| `Lakers record with Reaves` | `team_record` / `ok`; `with_player=Austin Reaves`; Lakers team subject; 51 games, 36-15 |
| `Lakers record without Luka` | `team_record` / `ok`; `without_player=Luka Dončić`; Lakers team subject; 18 games, 10-8 |
| `Lakers record with Reaves without Luka` | `team_record` / `no_result` / `filter_not_supported`; `unsupported_filters=["multi_player_availability"]`; empty sections |
| `Lakers record without Luk` | `team_record` / `no_result` / `filter_not_supported`; `unsupported_filters=["unresolved_player_availability"]`; empty sections |

The `basic_public_availability` slice remained green at 7/7 cases. The
`natural_query_route_priority` + `product_boundaries` combined run remained
green at 49/49 cases, preserving Wave 2A no-broad-fallback guards.

## Intentionally Left For Later Waves

Wave 2B did not address:

- `pqa_count_short_lebron_triple_doubles`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_streak_sentence_curry_3_threes`

Product-decision cases still open:

- `pqa_comparison_typo_kevn_durant`
- `pqa_typo_synonym_stephn_averages`
