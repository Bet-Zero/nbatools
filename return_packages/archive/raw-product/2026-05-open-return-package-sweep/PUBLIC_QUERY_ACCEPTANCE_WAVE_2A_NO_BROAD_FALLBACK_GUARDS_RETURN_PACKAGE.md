# Public Query Acceptance Wave 2A No-Broad-Fallback Guards Return Package

## What Changed

Wave 2A fixed six unresolved/bad-fragment public-query failures that were
previously broadening into successful leaderboard answers.

Changed behavior is limited to unsupported boundary guards. This wave did not
add fuzzy typo correction, new feature support, frontend changes, release-status
changes, or weakened expectations.

## Root Cause

Several public query families had positive route defaults without an earlier
guard for unresolved user fragments. When a team, stat, date, or player-like
fragment failed resolution, the remaining words still matched a broad route:

- record phrasing became a full team record leaderboard
- misspelled stat phrasing became the default points leaderboard
- misspelled or unsupported date wording became a full-scope leaderboard
- unresolved player stretch phrasing became a league-wide stretch leaderboard

The existing unsupported-filter execution path was correct; the missing piece
was narrow parser guard detection before broad defaults.

## Behavior Before And After

| Case ID | Query | Before | After | No-broad-fallback proof |
|---|---|---|---|---|
| `pqa_team_record_typo_celtcs` | `Celtcs record this season` | `team_record_leaderboard` / `ok` | `team_record_leaderboard` / `no_result` / `filter_not_supported` | `unsupported_filters=["unresolved_team"]`, empty sections |
| `pqa_typo_team_lakeers_record` | `Lakeers record this season` | `team_record_leaderboard` / `ok` | `team_record_leaderboard` / `no_result` / `filter_not_supported` | `unsupported_filters=["unresolved_team"]`, empty sections |
| `pqa_leaderboard_stat_typo_pionts` | `Who leads the NBA in pionts per game this season?` | `season_leaders` / `ok` | `season_leaders` / `no_result` / `filter_not_supported` | `unsupported_filters=["unresolved_stat"]`, empty sections |
| `pqa_date_typo_marhc` | `top scorers in Marhc` | `season_leaders` / `ok` | `season_leaders` / `no_result` / `filter_not_supported` | `unsupported_filters=["unresolved_date"]`, empty sections |
| `pqa_date_unsupported_since_trade_deadline` | `best offensive teams since the trade deadline` | `season_team_leaders` / `ok` | `season_team_leaders` / `no_result` / `filter_not_supported` | `unsupported_filters=["unsupported_date_anchor"]`, empty sections |
| `pqa_stretch_typo_bookr` | `Bookr hottest 4-game scoring stretch` | `player_stretch_leaderboard` / `ok` | `player_stretch_leaderboard` / `no_result` / `filter_not_supported` | `unsupported_filters=["unresolved_player"]`, empty sections |

## Exact Cases Fixed

Added to `qa/raw_query_answer_corpus.yaml` with `acceptance.family`,
`acceptance.variant`, and `acceptance.no_broad_fallback=true`:

- `pqa_team_record_typo_celtcs`
- `pqa_typo_team_lakeers_record`
- `pqa_leaderboard_stat_typo_pionts`
- `pqa_date_typo_marhc`
- `pqa_date_unsupported_since_trade_deadline`
- `pqa_stretch_typo_bookr`

Added the same six case IDs to
`qa/harness_slices/public_query_acceptance.yaml`.

The public acceptance slice now contains 60 cases.

## Files Changed

- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `tests/test_natural_query_parser.py`
- `tests/test_ui_failure_coverage.py`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/public_query_acceptance.yaml`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2A_NO_BROAD_FALLBACK_GUARDS_RETURN_PACKAGE.md`

No `docs/reference/query_guide.md` or `docs/reference/query_catalog.md` update
was needed because this wave only enforces existing unsupported boundaries.

## Validation Results

Passed:

```bash
.venv/bin/pytest tests/test_natural_query_parser.py::test_public_query_bad_fragments_do_not_broad_fallback tests/test_ui_failure_coverage.py::TestP2BoundaryRoutingCleanup::test_public_query_bad_fragment_guards_return_no_result -n0
```

Result: 12 passed.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T101541Z`; 60 cases,
expectation cases `pass: 60`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T101716Z`; 7 cases,
expectation cases `pass: 7`, failed case IDs none.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T101716Z`; 49 cases,
expectation cases `pass: 49`, failed case IDs none.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-parser
```

Result: 782 passed in 333.20s.

Passed:

```bash
make PYTEST=.venv/bin/pytest test-query
```

Result: 792 passed in 383.36s.

Passed:

```bash
git diff --check
```

Result: no whitespace diagnostics.

The new untracked return-package file was also checked directly:

```bash
git diff --check --no-index -- /dev/null return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2A_NO_BROAD_FALLBACK_GUARDS_RETURN_PACKAGE.md
```

Result: no whitespace diagnostics; exit code 1 is expected for a `/dev/null`
comparison against a new file.

Markdown lint was not run because `markdownlint` is not installed in this
workspace.

## Proof No Broad Fallback Remains

For each fixed case, both parser tests and raw QA assertions require:

- the same route family where relevant
- `result_status=no_result`
- `result_reason=filter_not_supported`
- the specific `unsupported_filters` value
- no result sections

Manual backend payload probes after the guard change returned:

| Query | Route | Status | Reason | Unsupported filter |
|---|---|---|---|---|
| `Celtcs record this season` | `team_record_leaderboard` | `no_result` | `filter_not_supported` | `unresolved_team` |
| `Lakeers record this season` | `team_record_leaderboard` | `no_result` | `filter_not_supported` | `unresolved_team` |
| `Who leads the NBA in pionts per game this season?` | `season_leaders` | `no_result` | `filter_not_supported` | `unresolved_stat` |
| `top scorers in Marhc` | `season_leaders` | `no_result` | `filter_not_supported` | `unresolved_date` |
| `best offensive teams since the trade deadline` | `season_team_leaders` | `no_result` | `filter_not_supported` | `unsupported_date_anchor` |
| `Bookr hottest 4-game scoring stretch` | `player_stretch_leaderboard` | `no_result` | `filter_not_supported` | `unresolved_player` |

Supported sibling probes stayed supported:

| Query | Preserved behavior |
|---|---|
| `Booker hottest 4-game scoring stretch` | `player_stretch_leaderboard` / `ok` |
| `hottest 3-game scoring stretch this year` | `player_stretch_leaderboard` / `ok` |
| `best record this season` | `team_record_leaderboard` / `ok` |
| `top scorers in March` | `season_leaders` / `ok` with March date window |

## Intentionally Left For Later Waves

Wave 2A did not address:

- `pqa_availability_short_lakers_w_luka`
- `pqa_availability_synonym_reaves_available`
- `pqa_count_short_lebron_triple_doubles`
- `pqa_split_unsupported_celtics_bench_home_away`
- `pqa_streak_sentence_curry_3_threes`

Product-decision cases still open:

- `pqa_comparison_typo_kevn_durant`
- `pqa_typo_synonym_stephn_averages`

## Next Recommended Fix Waves

1. Availability shorthand and synonym routing for `w/ PLAYER` and
   `TEAM wins with PLAYER`.
2. Player-specific count shorthand route correction.
3. Bench split unsupported-boundary priority.
4. Sentence-form streak route priority.
5. Product decision on typo-tolerant player resolution.
