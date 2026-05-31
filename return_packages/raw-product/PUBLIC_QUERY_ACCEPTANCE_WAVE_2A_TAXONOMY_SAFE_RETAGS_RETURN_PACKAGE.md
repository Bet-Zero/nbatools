# Public Query Acceptance Wave 2A Taxonomy And Safe Retags Return Package

Date: 2026-05-31

Status: complete; behavior-neutral metadata rollout only.

## Scope

Wave 2A resolves the comparison-family overlap and fills the public-query
acceptance matrix with existing passing corpus rows.

This wave does not change production code, parser/routing behavior, query
results, frontend rendering, release status, or existing route/status/reason
expectations. It does not add a new query row or mark a family public accepted.

## Comparison Taxonomy Changes

- adopted one public family: `comparisons`
- removed the overlapping `player_comparisons` public registry entry
- changed `player_summaries_recent_form.sibling_families` to `comparisons`
- retagged `pqa_comparison_typo_kevn_durant` to `comparisons` with concept
  `comparison_entity_resolution`
- added concept `subjective_comparison_boundary` to
  `pqa_comparison_subjective_better_jokic_embiid`
- replaced `lebron_durant_comparison_wave4` as the recent-form inverse sibling
  with `tatum_brown_last10_comparison_wave4`
- retained one explicit product decision for the Wave 2B bare-`vs` probe:
  `LeBron vs KD`

## Existing Cases Retagged

| Family | Variant | Existing case |
| --- | --- | --- |
| `player_stats_this_season` | `inverse_sibling` | `luka_40_point_count` |
| `team_records` | `synonym` | `lakers_road_record_last_season` |
| `player_summaries_recent_form` | `short` | `luka_last_10_summary_wave5` |
| `player_summaries_recent_form` | `sentence` | `tatum_good_teams` |
| `player_summaries_recent_form` | `synonym` | `kd_ts_top_defenses_missing_filters` |
| `player_summaries_recent_form` | `inverse_sibling` | `tatum_brown_last10_comparison_wave4` |
| `player_summaries_recent_form` | `nearby_unsupported` | `best_player_lately_ambiguous` |
| `leaderboards` | `short` | `leaders_in_steals_wave5` |
| `leaderboards` | `sentence` | `centers_rebound_leaders_wave4` |
| `leaderboards` | `synonym` | `true_shooting_leaders_phrase_wave5` |
| `leaderboards` | `inverse_sibling` | `most_assists_single_game` |
| `top_single_game_performances` | `short` | `most_rebounds_single_game` |
| `top_single_game_performances` | `inverse_sibling` | `rebound_leaders_this_season` |
| `top_single_game_performances` | `nearby_unsupported` | `biggest_team_three_point_games_boundary` |
| `count_queries` | `sentence` | `celtics_120_15_threes_count_missing_filter` |
| `count_queries` | `synonym` | `players_10_assist_count` |
| `count_queries` | `inverse_sibling` | `jokic_30_10_10_finder` |
| `game_finders` | `short` | `curry_5_threes_finder` |
| `game_finders` | `inverse_sibling` | `anthony_edwards_last_10_summary_no_match` |
| `game_finders` | `nearby_unsupported` | `celtics_bench_scoring_boundary_wave4` |
| `splits` | `short` | `celtics_wins_losses_split` |
| `splits` | `sentence` | `anthony_edwards_wins_losses_split_no_match` |
| `splits` | `synonym` | `curry_home_away_last_20_split_wave4` |
| `splits` | `inverse_sibling` | `knicks_road_record` |
| `streaks` | `short` | `lakers_win_streak` |
| `streaks` | `synonym` | `thunder_110_point_streak` |
| `streaks` | `inverse_sibling` | `curry_5_threes_count` |
| `rolling_stretches` | `short` | `booker_4_game_scoring_stretch` |
| `rolling_stretches` | `synonym` | `efficient_10_game_stretch` |
| `rolling_stretches` | `nearby_unsupported` | `team_net_rating_stretch_unsupported` |
| `comparisons` | `canonical` | `lebron_durant_comparison_wave4` |
| `comparisons` | `short` | `jokic_embiid_recent_comparison` |
| `comparisons` | `sentence` | `compare_lebron_durant_wave5` |
| `comparisons` | `synonym` | `celtics_bucks_comparison_this_season_wave5` |
| `comparisons` | `inverse_sibling` | `lebron_stats_vs_durant_wave5` |
| `comparisons` | `nearby_unsupported` | `pqa_comparison_subjective_better_jokic_embiid` |
| `comparisons` | `typo_partial` | `pqa_comparison_typo_kevn_durant` |
| `playoff_history` | `short` | `lakers_finals_appearances` |
| `playoff_history` | `sentence` | `lakers_celtics_playoff_matchup_history_wave5` |
| `playoff_history` | `synonym` | `heat_knicks_playoff_series_record_wave4` |
| `date_window_filters` | `short` | `luka_last_5_summary` |
| `date_window_filters` | `sentence` | `specific_date_jan_1` |
| `date_window_filters` | `synonym` | `jokic_since_all_star_break` |
| `unsupported_subjective_narrative` | `sentence` | `cooled_off_last_10` |
| `unsupported_subjective_narrative` | `inverse_sibling` | `tatum_clutch_stats` |

The same rows also received review-clarity metadata where applicable:
`concept`, `review_role`, `sibling_of`, `public_surface`,
`no_broad_fallback`, `intent_model`, and `qualifier_model`.

## Family Registry And Matrix

| Metric | Before | After |
| --- | ---: | ---: |
| Registered families | `17` | `16` |
| Public feature families | `15` | `14` |
| Guardrail families | `2` | `2` |
| `public_query_acceptance` cases | `67` | `109` |
| Public-accepted families | `0` | `0` |

The registry now marks only these
`typo_partial_entity_behavior.not_applicable_variants`:

- `canonical`
- `sentence`
- `synonym`
- `inverse_sibling`
- `nearby_unsupported`

Reason: domain-specific typo guards belong to their owning feature families.
No public feature gap is hidden with `not_applicable`.

Families still missing required variants: none.

`comparisons` remains `needs_product_decision` because bare player-vs-player
phrasing has not been probed or assigned a product policy.

## Generated Artifact

```text
outputs/raw_query_answer_qa/20260531T073042Z_wave2a_taxonomy_safe_retags/product_review.md
```

Generated state:

- machine regression: `pass`
- expectation cases: `109/109`
- suspicious rows: `0`
- missing variants: none
- human review declaration: `human_review_pending`
- public-accepted families: `0`

## Files Changed

| File | Change |
| --- | --- |
| `qa/raw_query_answer_corpus.yaml` | Safe existing-case retags and review-clarity metadata |
| `qa/raw_query_answer_acceptance_families.yaml` | Comparison-family collapse, comparison concepts, approved typo-guard non-applicable variants |
| `qa/harness_slices/public_query_acceptance.yaml` | Added `42` reused case IDs |
| `tests/test_raw_query_answer_qa.py` | Updated registry and slice-count assertions |
| `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md` | Recorded Wave 2A completion state and continuation |
| `docs/planning/raw-product/RAW_QA_CORPUS_PRODUCT_REVIEW_HARNESS_PREFLIGHT.md` | Recorded Wave 2A implementation status |

`docs/index.md` does not need an update because no durable docs were added or
moved.

## Validation

| Command | Result |
| --- | --- |
| Existing-row baseline harness over all `45` proposed retags | `45/45` expectation cases passed before metadata edits |
| `.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0` | `23 passed` |
| `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --run-id 20260531T073042Z_wave2a_taxonomy_safe_retags --fail-on-expectation-failure` | `109/109` expectation cases passed; failed IDs none |
| `git diff --check` | clean |
| Markdown lint | unavailable: no repo-local or PATH `markdownlint`, `markdownlint-cli2`, or `mdl` command |

## Review State And Next Action

Review state: `human_review_pending`.

No public family was marked accepted. Human rendered-output review has not
run.

Next recommended action: execute Wave 2B probes first, especially the bare
`LeBron vs KD` product-decision case, then run the separate Wave 2C rendered
frontend review.
