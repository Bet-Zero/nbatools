# Public Query Acceptance Coverage Wave 1 Return Package

## Summary

Implemented the first probe/seed wave for the public-query acceptance coverage
system planned in
`docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`.

This wave changed only QA corpus metadata, safe passing corpus cases, a saved
harness slice, and planning/return-package docs. It did not change production
code, parser/routing behavior, frontend rendering, or release status.

## Counts

| Metric | Count |
|---|---:|
| Proposed new `pqa_*` cases probed | 36 |
| New safe `pqa_*` cases added | 21 |
| Existing cases reused and retagged | 33 |
| Total added/retagged into acceptance slice | 54 |
| Deferred as behavior failures | 11 |
| Product decision required | 2 |
| Not added as duplicate of sufficient case | 2 |
| `public_query_acceptance` slice case count | 54 |

## Files Changed

- `qa/raw_query_answer_corpus.yaml`
  - Added 21 safe passing `pqa_*` cases.
  - Added lightweight `acceptance` metadata to the 54 included slice cases.
- `qa/harness_slices/public_query_acceptance.yaml`
  - Added the saved public acceptance slice.
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_PREFLIGHT.md`
  - Added Wave 1 results, family coverage, deferred cases, validation, and next
    recommended fix waves.
- `return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_WAVE_1_RETURN_PACKAGE.md`
  - This handoff receipt.

## Slice Coverage

Every case in `public_query_acceptance` has `acceptance.family` and
`acceptance.variant`. Sibling, unsupported, and typo/partial guards also include
`acceptance.no_broad_fallback=true`.

| Family | Slice cases |
|---|---:|
| `player_stats_this_season` | 6 |
| `team_records` | 5 |
| `team_record_availability` | 6 |
| `player_summaries_recent_form` | 3 |
| `leaderboards` | 2 |
| `top_single_game_performances` | 4 |
| `count_queries` | 3 |
| `game_finders` | 4 |
| `splits` | 2 |
| `streaks` | 3 |
| `rolling_stretches` | 3 |
| `comparisons` | 1 |
| `playoff_history` | 4 |
| `date_window_filters` | 2 |
| `unsupported_subjective_narrative` | 5 |
| `typo_partial_entity_behavior` | 1 |

## New Cases Added

| Case ID | Classification |
|---|---|
| `pqa_player_stats_sentence_luka_played` | Safe supported expectation. |
| `pqa_player_stats_synonym_luka_averages` | Safe supported expectation. |
| `pqa_player_stats_typo_jokc` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_team_record_short_celtics_record` | Safe supported expectation. |
| `pqa_availability_sentence_luka_plays` | Safe supported expectation. |
| `pqa_player_recent_typo_tatm` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_top_games_synonym_single_game_rebounds` | Safe supported expectation. |
| `pqa_top_games_stat_typo_rebunds` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_count_unsupported_players_played` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_count_typo_jokc_triple_doubles` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_finder_sentence_tatum_35_5_threes` | Safe supported route with `no_match`; no broad fallback. |
| `pqa_finder_synonym_show_lakers_home_losses` | Safe supported expectation. |
| `pqa_finder_typo_curr_5_threes` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_split_typo_jokc_home_away` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_streak_typo_jok_longest` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_stretch_sentence_game_score` | Safe supported expectation. |
| `pqa_comparison_subjective_better_jokic_embiid` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_playoff_typo_lakeers_history` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_subjective_short_mvp_candidates` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_subjective_typo_defnder` | Safe unsupported/no-broad-fallback expectation. |
| `pqa_typo_short_jokc_stats` | Safe unsupported/no-broad-fallback expectation. |

## Proposed But Not Added

These cases were probed but not added because Wave 1 did not change behavior
and did not encode wrong current behavior as acceptable.

| Case ID | Probe result | Classification | Next action |
|---|---|---|---|
| `pqa_team_record_typo_celtcs` | `team_record_leaderboard` / `ok` | Behavior failure | Add unresolved team typo guard for record phrasing. |
| `pqa_availability_short_lakers_w_luka` | `player_game_summary` / `ok` | Behavior failure | Extend presence routing to `w/ PLAYER`. |
| `pqa_availability_synonym_reaves_available` | `player_game_summary` / `ok` | Behavior failure | Extend team availability routing for `TEAM wins with PLAYER`. |
| `pqa_leaderboard_stat_typo_pionts` | `season_leaders` / `ok` | Behavior failure | Guard misspelled stat words from broad leaderboard fallback. |
| `pqa_count_short_lebron_triple_doubles` | `player_occurrence_leaders` / `ok` | Behavior failure | Route player-specific special-event count shorthand to player count/finder semantics. |
| `pqa_split_unsupported_celtics_bench_home_away` | `team_split_summary` / `ok` | Behavior failure | Preserve bench-scoring unsupported boundary before split routing. |
| `pqa_streak_sentence_curry_3_threes` | `player_game_finder` / `ok` | Behavior failure | Preserve sentence-form `longest streak` wording on streak route. |
| `pqa_stretch_typo_bookr` | `player_stretch_leaderboard` / `ok` | Behavior failure | Do not drop unresolved named-player fragments into broad stretch leaderboards. |
| `pqa_comparison_typo_kevn_durant` | `player_compare` / `ok` | Product decision required | Decide whether typo-tolerant player resolution is supported. |
| `pqa_date_unsupported_since_trade_deadline` | `season_team_leaders` / `ok` | Behavior failure | Unsupported date anchors must not be ignored into full-scope leaderboards. |
| `pqa_date_typo_marhc` | `season_leaders` / `ok` | Behavior failure | Misspelled date/month filters must not be ignored into broad leaderboards. |
| `pqa_typo_sentence_tatm_recent` | `None` / `error` / `unrouted` | Duplicate | Covered by `pqa_player_recent_typo_tatm`. |
| `pqa_typo_synonym_stephn_averages` | `player_game_summary` / `ok` | Product decision required | Decide whether typo-tolerant player resolution is supported. |
| `pqa_typo_team_lakeers_record` | `team_record_leaderboard` / `ok` | Behavior failure | Add unresolved team typo guard for record phrasing. |
| `pqa_typo_partial_kevn_comparison` | `player_compare` / `ok` | Duplicate of product-decision case | Covered by the `pqa_comparison_typo_kevn_durant` decision path. |

## Validation Results

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073054Z`; 54 cases,
expectation cases `pass: 54`, failed case IDs none, suspicious flag cases 0.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice basic_public_availability --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073305Z`; 7 cases, expectation
cases `pass: 7`, failed case IDs none, suspicious flag cases 0.

Passed:

```bash
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice natural_query_route_priority --slice product_boundaries --fail-on-expectation-failure
```

Result: `outputs/raw_query_answer_qa/20260528T073305Z`; 49 cases, expectation
cases `pass: 49`, failed case IDs none, suspicious flag cases 0.

Parser/query/preflight tests were not run because this wave did not change
production parser, routing, or execution behavior.

Passed:

```bash
git diff --check
```

Because the new slice and this return package are untracked until staged, direct
`--no-index` whitespace checks were also run against them. They produced no
whitespace diagnostics; the nonzero exit code is expected when comparing
`/dev/null` to a new file.

```bash
git diff --check --no-index -- /dev/null qa/harness_slices/public_query_acceptance.yaml
git diff --check --no-index -- /dev/null return_packages/raw-product/PUBLIC_QUERY_ACCEPTANCE_COVERAGE_WAVE_1_RETURN_PACKAGE.md
```

Markdown lint availability:

- `markdownlint`: not found
- `markdownlint-cli2`: not found
- `mdl`: not found
- `mdformat`: not found

## Next Recommended Fix Waves

1. Typo/partial no-broad-fallback guards for unresolved team, stat, date, and
   named-player fragments.
2. Availability phrase expansion for `w/ PLAYER` and `TEAM wins with PLAYER`.
3. Player-specific shorthand count routing for special events such as `count
   LeBron triple doubles since 2020`.
4. Route-priority fixes for bench-scoring split phrasing and sentence-form
   streak wording.
5. Product decision on whether typo-tolerant player resolution is intentionally
   supported for cases such as `Kevn Durant` and `Stephn Curry`.
