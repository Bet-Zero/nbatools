# Raw Query Answer QA Corpus Expansion Wave 5 Return Package

## 1. Executive summary

- What changed: expanded `qa/raw_query_answer_corpus.yaml` by 48 curated Wave 5 cases, from 195 to 243 total cases.
- Production code changed? no
- Tests changed? no
- Corpus size before/after: 195 -> 243
- Latest harness run: `outputs/raw_query_answer_qa/20260516T072725Z/report.md`
- Expectations: `pass: 232`, `fail: 11`
- Open suspicious flags: 3 (`expected_ok_returned_non_ok`)
- Informational flags: 147 (`frontend_hero_expected`)
- Verified outliers: 1 (`top_performance_high_points`)
- Main new finding families: defensive alias variants, record-intent phrasing, date/stat context preservation, playoff phrase variants, unsupported-boundary wording, and single-team advanced-stat product boundary.
- Recommended next step: grouped backend cleanup, starting with defensive aliases and playoff phrase routing before frontend-copy expansion or release-readiness.

## 2. Corpus expansion summary

| Area | Cases added | Purpose |
|---|---:|---|
| Supported-route phrasing variants | 12 | Exercise `which player`, `who had`, `who averaged`, `leaders in`, `worst`, `gave up`, `held teams to`, and `versus` wording without expanding product scope. |
| Date/window/context combinations | 9 | Protect last-N, since-date, since-All-Star, month, last-season, explicit-season, home/away, and in-wins context preservation. |
| Playoff/history phrasing | 8 | Cover adjacent playoff matchup forms, series history, Finals matchup history, since-year round/appearance queries, and single-team round-record boundaries. |
| Comparison edge cases | 7 | Guard full-name player comparisons, recent/last-N comparisons, team comparisons, team matchup records, and game-log/stats-vs-player non-comparison behavior. |
| Unsupported boundaries | 7 | Keep rookie, bench, team-bench, personal-foul, opponent-conference, clutch, and cooled-off asks from broad fallback answers. |
| Advanced/stat aliases | 5 | Cover true shooting, net rating, pace, opponent PPG, and points-allowed phrasing variants. |

New Wave 5 tag totals include `phrasing_variant: 20`, `context_filter: 17`, `stat_alias: 15`, `date_filter: 9`, `unsupported_boundary: 9`, `no_broad_fallback: 9`, `playoff: 8`, `defensive_stat: 7`, `comparison: 7`, and `matchup: 7`.

## 3. Strategy coverage

- Supported-route phrasing variants: added direct question and fragment forms across player/team leaderboards, team records, player summaries, and record-when conditions.
- Date/window/context combinations: added last 10, last 20, since All-Star, since January 1, March, last season, explicit 2024-25, home/road, and in-wins contexts.
- Playoff/history phrasing: added playoff history, playoff series history, Finals history, conference-finals appearances since 2000, second-round record since 2010, and single-team round-record boundaries.
- Comparison edge cases: added compare-and, full-name vs full-name, last-N player comparison, recent-form comparison, team comparison, team matchup record, and game-log/stats-vs-player guardrails.
- Unsupported boundaries: added rookie/bench/team-bench, personal-foul, opponent-conference, subjective clutch, and cooled-off cases.
- Advanced/stat aliases: added TS%, net rating, pace, opponent points per game, and defensive allowed-points variants.

## 4. Latest run summary

- Run ID: `20260516T072725Z`
- Output path: `outputs/raw_query_answer_qa/20260516T072725Z/report.md`
- Case count: 243
- Result status counts: `ok: 200`, `no_result: 33`, `error: 10`
- Expectation pass/fail counts: `pass: 232`, `fail: 11`
- Expectation check counts: `pass: 1304`, `fail: 28`
- Suspicious flags: 3 cases, `expected_ok_returned_non_ok: 3`
- Informational flags: 147 cases, `frontend_hero_expected: 147`
- Verified outliers: 1 case, `top_performance_high_points: 1`
- Failed case IDs: `team_gave_up_fewest_ppg_wave5`, `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, `lakers_held_teams_under_100_wave5`, `curry_last_20_from_three_wave5`, `celtics_road_record_since_jan_1_wave5`, `best_second_round_record_since_2010_wave5`, `lakers_celtics_playoff_matchup_history_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`, `teams_allowing_fewest_points_wave5`

## 5. New/updated findings

| Finding ID | Priority | Category | Case/query | Finding type | Status | Recommended fix family |
|---|---|---|---|---|---|---|
| AQ-024 | P1 | Defensive stat aliases | `team_gave_up_fewest_ppg_wave5`; `lakers_held_teams_under_100_wave5`; `teams_allowing_fewest_points_wave5` | stat_mapping_issue | open | defensive/opponent-points stat mapping |
| AQ-025 | P2 | Team record phrasing | `lakers_how_did_road_last_season_wave5` | route_mismatch | open | summary-vs-finder intent routing |
| AQ-026 | P1 | Record-when player condition | `jokic_possessive_triple_double_record_wave5` | routing_or_data_gap | open | player/team context resolution |
| AQ-027 | P1 | Date/window context | `celtics_road_record_since_jan_1_wave5` | missing_filter | open | date-window parsing/filter preservation |
| AQ-028 | P2 | Player stat context | `curry_last_20_from_three_wave5` | missing_filter | open | stat alias + context preservation |
| AQ-029 | P1 | Playoff/history phrasing | `best_second_round_record_since_2010_wave5`; `lakers_celtics_playoff_matchup_history_wave5` | route_and_season_type_issue | open | playoff round/matchup routing |
| AQ-030 | P2 | Unsupported stat alias boundary | `players_personal_fouls_wave5` | unsupported_no_result_policy | open | product boundary / stat coverage |
| AQ-031 | P2 | Advanced metric product boundary | `warriors_net_rating_single_team_wave5` | needs_product_decision | open | product boundary / stat coverage |

Notes:

- AQ-024 is the densest new cluster and should be fixed as a family, not as three isolated strings.
- AQ-029 affects documented playoff route families; fix adjacent phrasing and hyphenated round parsing together.
- AQ-031 should start with a product decision before implementation: scalar team advanced-stat summary vs explicit unsupported boundary.

## 6. Manual review recommendations

P1 first:

- AQ-024 defensive aliases: review `team_gave_up_fewest_ppg_wave5`, `lakers_held_teams_under_100_wave5`, and `teams_allowing_fewest_points_wave5`.
- AQ-026 player record-when: review `jokic_possessive_triple_double_record_wave5`, especially the unexpected `team=WAS` metadata.
- AQ-027 date parsing: review `celtics_road_record_since_jan_1_wave5` and decide expected `since January 1` semantics.
- AQ-029 playoff phrasing: review `best_second_round_record_since_2010_wave5` and `lakers_celtics_playoff_matchup_history_wave5`.

P2 next:

- AQ-025 record intent: review whether `How did the Lakers do...` should be a summary route or finder route.
- AQ-028 stat context: review whether `from three` on player last-N summaries must bind `fg3m`.
- AQ-030 unsupported boundary: review personal-foul wording variants for specific no-result guidance.
- AQ-031 product decision: decide single-team net-rating behavior before adding support.

## 7. Validation

Limited harness run:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --limit 30
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T071937Z
Cases: 30
Result statuses: {'error': 1, 'no_result': 2, 'ok': 27}
Expectation cases: {'pass': 30}
Suspicious flag cases: 0
Informational flag cases: 6
Verified outlier cases: 1
Failed case IDs: none
```

Full harness run:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml
Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T072725Z
Cases: 243
Result statuses: {'error': 10, 'no_result': 33, 'ok': 200}
Expectation cases: {'fail': 11, 'pass': 232}
Suspicious flag cases: 3
Informational flag cases: 147
Verified outlier cases: 1
Failed case IDs: team_gave_up_fewest_ppg_wave5, lakers_how_did_road_last_season_wave5, jokic_possessive_triple_double_record_wave5, lakers_held_teams_under_100_wave5, curry_last_20_from_three_wave5, celtics_road_record_since_jan_1_wave5, best_second_round_record_since_2010_wave5, lakers_celtics_playoff_matchup_history_wave5, players_personal_fouls_wave5, warriors_net_rating_single_team_wave5, teams_allowing_fewest_points_wave5
```

`git diff --check`:

```text
passed with no output
```

Optional ruff:

```text
not run; no Python/tool source files changed.
```

## 8. Recommended next phase

Do grouped backend cleanup before visual automation. Start with AQ-024 defensive alias variants and AQ-029 playoff phrase routing because they are supported-route gaps. Then handle AQ-025/AQ-026 record-intent routing and AQ-027/AQ-028 context preservation. Treat AQ-030/AQ-031 as product-boundary/decision work. After those are fixed or explicitly deferred, rerun the 243-case corpus; if clean, move to frontend-copy corpus expansion or a release-readiness checklist.
