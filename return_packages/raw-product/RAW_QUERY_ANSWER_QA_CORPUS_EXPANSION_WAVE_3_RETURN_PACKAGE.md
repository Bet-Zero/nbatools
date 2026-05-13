# Raw Query Answer QA Corpus Expansion Wave 3 Return Package

## 1. Executive summary

- What changed: expanded `qa/raw_query_answer_corpus.yaml` from 80 to 145 curated cases, added QA-only `answer_summary` report lines, updated Wave 3 findings and plan docs.
- Production code changed? no
- Tests changed? no hard tests changed; QA corpus/harness docs changed.
- Corpus size before/after: 80 -> 145
- Latest harness run: `outputs/raw_query_answer_qa/20260513T060001Z/report.md`
- Expectations: 137 pass, 8 fail; 695 checks pass, 17 checks fail
- Open suspicious flags: 3 cases, all `expected_ok_returned_non_ok`
- Informational flags: 73 cases, all `frontend_hero_expected`
- Verified outliers: 1 case, `top_performance_high_points`
- Main new finding families: stat/context mapping, date/context filters, compound thresholds, player no-match diagnostics, answer text quality, product-boundary decisions
- Recommended next step: group fixes by family before touching production behavior.

## 2. Corpus expansion summary

| Area | Cases added | Purpose |
|---|---:|---|
| Player leaderboards | 9 | Broaden stat coverage and phrasing for rebounds, assists, steals, FG%, FT%, usage, plus-minus, occurrences, and triple-doubles. |
| Team leaderboards / records | 13 | Cover ratings, scoring, threes, road records, FT%, date windows, and low/high scoring records. |
| Top performances | 5 | Add single-game threes, blocks, steals, plus-minus, named-player high game, and team threes boundary. |
| Player summaries | 7 | Cover last-N shorthand, opponent quality, teammate absence, career, and abbreviation-heavy stat/context phrasing. |
| Counts / finders | 7 | Add player threshold counts, distinct-team counts, compound team counts, and compact multi-stat finder phrasing. |
| Streaks / rolling stretches | 6 | Add player/team threshold streaks, triple-double streaks, efficiency rolling stretches, and team rolling unsupported boundary. |
| Playoff/history/era | 6 | Add conference finals, series record, round record, decade leaderboard, record-by-decade, and matchup-by-decade. |
| Splits/comparisons/boundaries | 12 | Cover player/team comparisons, wins/losses split, on/off unsupported, lineup unsupported, subjective duo boundary, and related review cases. |

Added-case category totals: `leaderboard: 9`, `player_summary: 7`, `team_leaderboard: 6`, `unsupported_boundary: 5`, `top_performances: 5`, `playoff_history: 5`, `team_record: 4`, `finder_count: 4`, `record_when_player_condition: 4`, `streak: 4`, `player_game_log_count: 3`, `split: 3`, `record_when_team_condition: 2`, `rolling_stretch: 2`, `team_record_leaderboard: 1`, `playoff_matchup_history: 1`.

Added-case tag totals: `stat_mapping: 34`, `context_filter: 21`, `phrasing_variant: 12`, `record_when: 8`, `unsupported_boundary: 6`, `top_performance: 6`, `playoff: 6`, `split: 5`, `streak: 4`, `date_filter: 3`, `opponent_quality: 2`, `rolling_stretch: 2`, `answer_text_policy: 1`, `subjective: 1`.

## 3. Strategy coverage

The expansion covered core surfaces/stat coverage across player/team leaderboards, top performances, summaries, records, finders/counts, streaks, rolling stretches, playoff/history, comparisons, and splits.

Phrasing variation includes full questions, search-bar fragments, shorthand forms, `who leads`, `most`, `best`, `highest`, `how often`, `record when`, `against`, `without`, `single-game`, and `this season` variants.

Context/filter assumptions include `last season`, March, since All-Star break, road/home, opponent quality, top defenses, playoff teams, season ranges, and decade/era filters.

Moderate complexity includes player record-when thresholds, team threshold records, player threshold counts, compound team counts, and compact multi-stat player finders.

Unsupported boundaries include minutes leaderboards, team rolling stretches, lineup/on-off coverage, subjective duo ranking, and team single-game threes.

## 4. Harness/report changes

Added `answer_summary` to JSONL and Markdown reports. It is a compact QA-only fact line derived from returned rows, for example count totals, top rows, summary records, or no-result reasons.

This does not change production backend `answer_phrase` or `count_phrase` metadata.

## 5. Latest run summary

- Run ID: `20260513T060001Z`
- Output path: `outputs/raw_query_answer_qa/20260513T060001Z/report.md`
- Case count: 145
- Result status counts: `ok: 126`, `no_result: 13`, `error: 6`
- Expectation pass/fail counts: cases `pass: 137`, `fail: 8`; checks `pass: 695`, `fail: 17`
- Suspicious flags: 3 cases, `expected_ok_returned_non_ok: 3`
- Informational flags: 73 cases, `frontend_hero_expected: 73`
- Verified outliers: 1 case, `top_performance_high_points: 1`
- Failed case IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `knicks_allowed_under_110_record`, `lakers_road_record_last_season`, `boston_tatum_under_40_fg_record_missing_filter`, `celtics_120_15_threes_count_missing_filter`, `jokic_30_points_10_assists_finder_misparsed`, `anthony_edwards_wins_losses_split_no_match`

## 6. New/updated findings

| Finding ID | Priority | Category | Case/query | Finding type | Status | Recommended fix family |
|---|---|---|---|---|---|---|
| AQ-009 | P1 | Routing/data no-match | `anthony_edwards_last_10_summary_no_match`; `anthony_edwards_wins_losses_split_no_match` | routing_or_data_gap | open | player summary/split no-match diagnostics |
| AQ-010 | P1 | Stat/context filters | `kd_ts_top_defenses_missing_filters` | route_and_filter_drop | open | stat alias + opponent-quality routing |
| AQ-011 | P1 | Defensive stat semantics | `knicks_allowed_under_110_record`; `fewest_points_allowed_team_leader` | stat_mapping_issue | open | defensive/opponent-points stat mapping |
| AQ-012 | P1 | Date/context filters | `lakers_road_record_last_season` | missing_filter | open | relative season parsing/filter preservation |
| AQ-013 | P1 | Record-when player condition | `boston_tatum_under_40_fg_record_missing_filter` | missing_filter | open | percentage threshold parsing/execution |
| AQ-014 | P1 | Compound thresholds | `celtics_120_15_threes_count_missing_filter`; `jokic_30_points_10_assists_finder_misparsed` | missing_filter / stat_binding_issue | open | compound threshold parsing/execution |
| AQ-015 | P2 | Leaderboard context filters | `guards_fg_percentage_leaders` | missing_filter | open | position-filtered leaderboards |
| AQ-016 | P2 | Backend answer text quality | multiple count cases | awkward_answer_text | open | count phrase generation |
| AQ-017 | P2 | Product boundary/stat coverage | `minutes_leaders_unsupported`; `biggest_team_three_point_games_boundary` | needs_product_decision | open | product boundary / stat coverage |

Short notes are recorded in `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`.

## 7. Manual review recommendations

Review first:

- Defensive stat mapping: `knicks_allowed_under_110_record`, `fewest_points_allowed_team_leader`
- Compound/percentage threshold parsing: `boston_tatum_under_40_fg_record_missing_filter`, `celtics_120_15_threes_count_missing_filter`, `jokic_30_points_10_assists_finder_misparsed`
- Documented forms returning no-match: `anthony_edwards_last_10_summary_no_match`, `anthony_edwards_wins_losses_split_no_match`
- Context/filter preservation: `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `guards_fg_percentage_leaders`
- Answer text quality: `players_40_point_count`, `players_10_assist_count`, `curry_5_threes_count`, `luka_40_point_count`, `wemby_5_blocks_count`, `teams_120_point_count_answer_text_review`

## 8. Validation

Limited harness run:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T055912Z
Cases: 20
Result statuses: {'error': 1, 'no_result': 1, 'ok': 18}
Expectation cases: {'pass': 20}
Suspicious flag cases: 0
Informational flag cases: 5
Verified outlier cases: 1
Failed case IDs: none
```

Full harness run:

```text
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260513T060001Z
Cases: 145
Result statuses: {'error': 6, 'no_result': 13, 'ok': 126}
Expectation cases: {'fail': 8, 'pass': 137}
Suspicious flag cases: 3
Informational flag cases: 73
Verified outlier cases: 1
Failed case IDs: anthony_edwards_last_10_summary_no_match, kd_ts_top_defenses_missing_filters, knicks_allowed_under_110_record, lakers_road_record_last_season, boston_tatum_under_40_fg_record_missing_filter, celtics_120_15_threes_count_missing_filter, jokic_30_points_10_assists_finder_misparsed, anthony_edwards_wins_losses_split_no_match
```

`git diff --check`:

```text
exit 0; no output
```

Ruff for changed tool:

```text
All checks passed!
```

## 9. Recommended next phase

Do not start with one-off fixes. Recommended grouped fix families:

- defensive/opponent-points stat mapping
- compound and percentage threshold parsing/execution
- relative date/context filter preservation
- player summary/split no-match diagnostics
- count phrase generation quality
- product-boundary decisions for documented stat aliases and team top-game variants

Frontend hero extraction and broad backend answer enrichment remain deferred unless explicitly scheduled as their own wave.
