# Raw Query Answer QA Product Review

## Run Metadata And Review Status

- Run ID: `composed-core`
- Scope: `custom_selection`
- Corpus: `qa/raw_query_answer_corpus.yaml`
- Cases run: `8`
- Source commit: `c88dab46e82b1d462bf2dec56f7fd9d9f1e2914a`
- Source tree clean: `True`
- Corpus SHA-256: `253041d1582fc55eb63f0ebde2eb86e93b9e9a1ecbc9cf9ded24c862c0833d23`
- Selected-case content SHA-256: `fd539c9736b210740f580fe8e8d04813d1153338e96d50de54db91d6aead724c`
- Review-output SHA-256: `100470adb9197788ba2638e3ce8063ec06b99d45b1715aa692494f26d5964a9d`
- Data generation: `legacy`
- Family registry surface: `public_query_acceptance`
- Machine regression: `pass`
- Coverage review: `missing_variants`
- Human review declaration: `human_review_pending`
- Closure integrity: `not_declared`

Machine regression passing does not mean coverage review, human review, or public acceptance is complete.

## Feature-Family Summary

| Family | Public | Cases | Machine pass/fail | Required variants | Covered variants | Missing variants | Coverage review | Human review | Public accepted |
|---|---|---:|---|---|---|---|---|---|---|
| Player stats this season | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Team records | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Team record with or without player | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Player summaries and recent form | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Leaderboards | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Top single-game performances | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Count queries | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Game finders | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Splits | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Streaks | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Rolling stretches | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Comparisons | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Playoff history | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Date and window filters | yes | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Unsupported subjective and narrative questions | no | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial | missing_variants | pending | no |
| Typo and partial-entity guardrails | no | 0 | 0 pass / 0 fail | canonical, short, sentence, synonym, inverse_sibling, nearby_unsupported, typo_partial |  | short, typo_partial | missing_variants | pending | no |

## Missing / Unchecked Variant Checklist

| Family | Variant | State | Cases | Reason |
|---|---|---|---|---|
| player_stats_this_season | canonical | missing |  |  |
| player_stats_this_season | short | missing |  |  |
| player_stats_this_season | sentence | missing |  |  |
| player_stats_this_season | synonym | missing |  |  |
| player_stats_this_season | inverse_sibling | missing |  |  |
| player_stats_this_season | nearby_unsupported | missing |  |  |
| player_stats_this_season | typo_partial | missing |  |  |
| team_records | canonical | missing |  |  |
| team_records | short | missing |  |  |
| team_records | sentence | missing |  |  |
| team_records | synonym | missing |  |  |
| team_records | inverse_sibling | missing |  |  |
| team_records | nearby_unsupported | missing |  |  |
| team_records | typo_partial | missing |  |  |
| team_record_availability | canonical | missing |  |  |
| team_record_availability | short | missing |  |  |
| team_record_availability | sentence | missing |  |  |
| team_record_availability | synonym | missing |  |  |
| team_record_availability | inverse_sibling | missing |  |  |
| team_record_availability | nearby_unsupported | missing |  |  |
| team_record_availability | typo_partial | missing |  |  |
| player_summaries_recent_form | canonical | missing |  |  |
| player_summaries_recent_form | short | missing |  |  |
| player_summaries_recent_form | sentence | missing |  |  |
| player_summaries_recent_form | synonym | missing |  |  |
| player_summaries_recent_form | inverse_sibling | missing |  |  |
| player_summaries_recent_form | nearby_unsupported | missing |  |  |
| player_summaries_recent_form | typo_partial | missing |  |  |
| leaderboards | canonical | missing |  |  |
| leaderboards | short | missing |  |  |
| leaderboards | sentence | missing |  |  |
| leaderboards | synonym | missing |  |  |
| leaderboards | inverse_sibling | missing |  |  |
| leaderboards | nearby_unsupported | missing |  |  |
| leaderboards | typo_partial | missing |  |  |
| top_single_game_performances | canonical | missing |  |  |
| top_single_game_performances | short | missing |  |  |
| top_single_game_performances | sentence | missing |  |  |
| top_single_game_performances | synonym | missing |  |  |
| top_single_game_performances | inverse_sibling | missing |  |  |
| top_single_game_performances | nearby_unsupported | missing |  |  |
| top_single_game_performances | typo_partial | missing |  |  |
| count_queries | canonical | missing |  |  |
| count_queries | short | missing |  |  |
| count_queries | sentence | missing |  |  |
| count_queries | synonym | missing |  |  |
| count_queries | inverse_sibling | missing |  |  |
| count_queries | nearby_unsupported | missing |  |  |
| count_queries | typo_partial | missing |  |  |
| game_finders | canonical | missing |  |  |
| game_finders | short | missing |  |  |
| game_finders | sentence | missing |  |  |
| game_finders | synonym | missing |  |  |
| game_finders | inverse_sibling | missing |  |  |
| game_finders | nearby_unsupported | missing |  |  |
| game_finders | typo_partial | missing |  |  |
| splits | canonical | missing |  |  |
| splits | short | missing |  |  |
| splits | sentence | missing |  |  |
| splits | synonym | missing |  |  |
| splits | inverse_sibling | missing |  |  |
| splits | nearby_unsupported | missing |  |  |
| splits | typo_partial | missing |  |  |
| streaks | canonical | missing |  |  |
| streaks | short | missing |  |  |
| streaks | sentence | missing |  |  |
| streaks | synonym | missing |  |  |
| streaks | inverse_sibling | missing |  |  |
| streaks | nearby_unsupported | missing |  |  |
| streaks | typo_partial | missing |  |  |
| rolling_stretches | canonical | missing |  |  |
| rolling_stretches | short | missing |  |  |
| rolling_stretches | sentence | missing |  |  |
| rolling_stretches | synonym | missing |  |  |
| rolling_stretches | inverse_sibling | missing |  |  |
| rolling_stretches | nearby_unsupported | missing |  |  |
| rolling_stretches | typo_partial | missing |  |  |
| comparisons | canonical | missing |  |  |
| comparisons | short | missing |  |  |
| comparisons | sentence | missing |  |  |
| comparisons | synonym | missing |  |  |
| comparisons | inverse_sibling | missing |  |  |
| comparisons | nearby_unsupported | missing |  |  |
| comparisons | typo_partial | missing |  |  |
| playoff_history | canonical | missing |  |  |
| playoff_history | short | missing |  |  |
| playoff_history | sentence | missing |  |  |
| playoff_history | synonym | missing |  |  |
| playoff_history | inverse_sibling | missing |  |  |
| playoff_history | nearby_unsupported | missing |  |  |
| playoff_history | typo_partial | missing |  |  |
| date_window_filters | canonical | missing |  |  |
| date_window_filters | short | missing |  |  |
| date_window_filters | sentence | missing |  |  |
| date_window_filters | synonym | missing |  |  |
| date_window_filters | inverse_sibling | missing |  |  |
| date_window_filters | nearby_unsupported | missing |  |  |
| date_window_filters | typo_partial | missing |  |  |
| unsupported_subjective_narrative | canonical | missing |  |  |
| unsupported_subjective_narrative | short | missing |  |  |
| unsupported_subjective_narrative | sentence | missing |  |  |
| unsupported_subjective_narrative | synonym | missing |  |  |
| unsupported_subjective_narrative | inverse_sibling | missing |  |  |
| unsupported_subjective_narrative | nearby_unsupported | missing |  |  |
| unsupported_subjective_narrative | typo_partial | missing |  |  |
| typo_partial_entity_behavior | canonical | not_applicable |  | Domain-specific typo guards belong to their owning feature families. |
| typo_partial_entity_behavior | short | missing |  |  |
| typo_partial_entity_behavior | sentence | not_applicable |  | Domain-specific typo guards belong to their owning feature families. |
| typo_partial_entity_behavior | synonym | not_applicable |  | Domain-specific typo guards belong to their owning feature families. |
| typo_partial_entity_behavior | inverse_sibling | not_applicable |  | Domain-specific typo guards belong to their owning feature families. |
| typo_partial_entity_behavior | nearby_unsupported | not_applicable |  | Domain-specific typo guards belong to their owning feature families. |
| typo_partial_entity_behavior | typo_partial | missing |  |  |

## Representative Outputs Requiring Human Review

_None tagged yet._
## Unsupported / No-Broad-Fallback Rows

| Case | Family | Variant | Expected status | Actual route/status/shape | Machine expectation |
|---|---|---|---|---|---|
| k08_pair_missing_zero |  |  | no_result | team_record / no_result / no_result | pass |

## Product Decisions Needed

_None._

## Suspicious Rows

| Case | Family | Flags |
|---|---|---|
| k08_pair_missing_nonempty |  | missing_backend_answer_text |
| k08_s4_team_with |  | missing_backend_answer_text |
| k08_s4_team_without |  | missing_backend_answer_text |
| k08_s4_player_with |  | missing_backend_answer_text |
| k08_s4_player_without |  | missing_backend_answer_text |

## Human Review Worksheet

### Player stats this season

- Coverage questions: `['Do player-season fragments, sentences, and aliases stay on the player summary route?', 'Do unresolved player names fail cleanly without a broad summary?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Team records

- Coverage questions: `['Do single-team record phrasings preserve location, season, opponent, conference, and division qualifiers?', 'Do matchup and no-subject division leaderboard siblings route intentionally while mixed conference-plus-division and playoff division siblings avoid broad fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Team record with or without player

- Coverage questions: `['Do presence and absence wording stay on the team-record route?', 'Does compound or unresolved availability fail cleanly without a broad record?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Player summaries and recent form

- Coverage questions: `['Do recent-form and last-N phrases preserve player summary scope?', 'Do comparison siblings and unresolved player names avoid broad fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Leaderboards

- Coverage questions: `['Do stat aliases and filters remain attached to the requested leaderboard?', 'Do top-single-game and unsupported-stat siblings avoid default-points fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Top single-game performances

- Coverage questions: `['Do single-game phrases remain distinct from per-game season leaderboards?', 'Do stat typos fail cleanly without falling back to scoring games?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Count queries

- Coverage questions: `['Do count fragments retain the requested player, event, and window?', 'Do unsupported broad-count and typo forms avoid unrelated answers?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Game finders

- Coverage questions: `['Do finder fragments and sentences retain all threshold and context filters?', 'Do empty samples and unresolved players avoid broad finder results?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Splits

- Coverage questions: `['Do player and team split qualifiers route to the intended split result?', 'Do unsupported role combinations and unresolved players fail cleanly?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Streaks

- Coverage questions: `['Do longest/current streak phrases preserve thresholds and player scope?', 'Do subjective trend and typo forms avoid broad streak or finder fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Rolling stretches

- Coverage questions: `['Do rolling-window phrases preserve player, metric, and window size?', 'Do unsupported team and unresolved-player forms fail cleanly?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Comparisons

- Coverage questions: `['Do objective comparison phrases remain separate from subjective winner questions?', 'Do team, player, and matchup comparison siblings route intentionally?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Playoff history

- Coverage questions: `['Do history, matchup, appearance, and round phrases preserve playoff scope?', 'Do opponent-quality siblings and unresolved teams avoid broad playoff fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Date and window filters

- Coverage questions: `['Do exact dates, month windows, relative windows, and date anchors stay attached?', 'Do malformed or unsupported anchors avoid full-scope fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Unsupported subjective and narrative questions

- Coverage questions: `['Do subjective and narrative questions decline cleanly?', 'Does wording variation avoid accidental leaderboard or summary fallback?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

### Typo and partial-entity guardrails

- Coverage questions: `['Do unresolved entities fail clearly instead of widening query scope?', 'Which typo and partial-name forms should remain unsupported by product decision?']`
- [ ] Examples represent real public usage.
- [ ] Representative outputs have correct scope and answer shape.
- [ ] Missing variants are resolved or recorded as follow-up.
- Reviewer notes:

## What To Send ChatGPT

Send ChatGPT this file:

`outputs/required_data_validation/acquired_data/composed-participation-stage/rawqa/composed-core/product_review.md`

Use this exact instruction block:

```text
Review this NBA Tools Raw QA product-review artifact as a product coverage
audit. Do not treat machine pass counts as sufficient. For each feature
family:
1. Decide whether the examples represent real public usage.
2. Flag missing canonical, short, sentence, synonym, sibling/inverse,
   nearby-unsupported, or typo/partial variants.
3. Review the representative answer outputs for wrong scope, misleading
   answers, and broad fallback.
4. Separate behavior bugs from corpus gaps and product decisions.
5. Return a family-by-family table with verdict, missing cases, suspicious
   outputs, and recommended next action.
```
