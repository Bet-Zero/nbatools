# Raw Query Answer QA Findings

## Purpose

This doc tracks manual-review findings from Raw Query Answer QA harness runs.
The harness corpus is a product-answer review set, not a hard regression suite:
findings here should be grouped into fix families before implementation.

## Latest run

- Run ID: `20260516T072725Z`
- Corpus size: 243 cases
- Output report path:
  `outputs/raw_query_answer_qa/20260516T072725Z/report.md`
- Summary counts:
  - Result statuses: `ok: 200`, `no_result: 33`, `error: 10`
  - Expectation cases: `pass: 232`, `fail: 11`
  - Expectation checks: `pass: 1304`, `fail: 28`
  - Failed case IDs: `team_gave_up_fewest_ppg_wave5`,
    `lakers_how_did_road_last_season_wave5`,
    `jokic_possessive_triple_double_record_wave5`,
    `lakers_held_teams_under_100_wave5`,
    `curry_last_20_from_three_wave5`,
    `celtics_road_record_since_jan_1_wave5`,
    `best_second_round_record_since_2010_wave5`,
    `lakers_celtics_playoff_matchup_history_wave5`,
    `players_personal_fouls_wave5`,
    `warriors_net_rating_single_team_wave5`,
    `teams_allowing_fewest_points_wave5`
  - Manual review statuses: `unreviewed: 180`, `expected_unsupported: 26`,
    `pass: 26`, `routing_issue: 4`, `semantics_issue: 3`,
    `missing_filter: 2`, `needs_product_decision: 1`,
    `verified_outlier: 1`
  - Answer text policies: `frontend_hero_expected: 150`,
    `requires_backend_answer_text: 10`, `no_answer_text_expected: 40`,
    `<unspecified>: 43`
  - Answer text statuses: `frontend_hero_expected: 147`,
    `backend_answer_text_present: 10`, `no_answer_text_expected: 40`,
    `not_required: 46`
  - Suspicious flag cases: 3
  - Suspicious flags: `expected_ok_returned_non_ok: 3`
  - Informational flag cases: 147
  - Informational flags: `frontend_hero_expected: 147`
  - Verified outlier cases: 1
  - Verified outliers: `top_performance_high_points: 1`

## Expansion Wave 3 summary

Expansion Wave 3 grew the curated corpus from 80 to 145 cases. It did not
change production query behavior, frontend rendering, backend answer metadata,
or source data. The wave added broad stat coverage, phrasing variants, context
filters, moderate condition complexity, and unsupported-boundary samples.

New review signals are grouped into these families:

- stat/context mapping gaps: position filters, defensive allowed-points wording,
  percentage thresholds, and abbreviation-heavy metric/context forms
- date/context filter preservation: relative `last season` wording
- compound threshold handling: multi-condition counts and compact player finder
  phrases
- routing/data no-match gaps: documented player summary/split examples that
  return no-result for Anthony Edwards
- answer text quality: backend count phrases that are present but too generic
  or expose raw stat labels

## Corpus Expansion Wave 4 summary

Expansion Wave 4 grew the curated corpus from 145 to 195 cases. It did not
change production query behavior, frontend rendering, backend answer metadata,
or source data. The wave was narrower than Wave 3 and focused on P2/deeper
coverage rather than broad surface repetition.

Coverage strategy:

- Position/role/context aliases: 12 added cases for position-filtered
  leaderboards, rookie/bench/starter leaderboard boundaries, and named-player
  starter/bench role contexts.
- Splits/comparisons: 10 added cases for player/team home-away and wins-losses
  splits, player/team comparisons, head-to-head matchup records, and on/off
  unsupported guidance.
- Playoff/history/era: 10 added cases for Finals/conference-finals record
  phrasing, playoff appearances/history, series-record phrasing, since-year and
  decade era queries, and regular-season vs playoff-team guardrails.
- Stat aliases/advanced metrics: 10 added cases for eFG%, turnovers,
  personal fouls, pace, defensive rating, points allowed/opponent PPG, AST%,
  and turnover rate.
- Context/filter combinations: 5 added cases for explicit road season records,
  East/West-style opponent context, opponent-quality last season, since
  All-Star plus stat, and explicit-date no-match behavior.
- Unsupported/product boundaries: 3 added cases for subjective defensive,
  award, and lineup coverage boundaries.

New review signals are grouped into these families:

- position/role-filtered leaderboards and role/team-scope broad fallbacks
- player comparison phrasing routing
- playoff round-record and playoff matchup-record phrasing
- defensive/opponent-points alias coverage
- unsupported stat aliases falling back to points
- opponent-conference context filters falling back to full-season records

## Corpus Expansion Wave 5 summary

Expansion Wave 5 grew the curated corpus from 195 to 243 cases. It did not
change production query behavior, frontend rendering, backend answer metadata,
harness logic, or source data. The wave focused on supported-route phrasing
variants, date/window/context combinations, playoff/history phrasing,
comparison guardrails, unsupported-boundary variants, and advanced/stat aliases.

Latest Wave 5 run:

- Run ID: `20260516T072725Z`
- Output path:
  `outputs/raw_query_answer_qa/20260516T072725Z/report.md`
- Cases: 243
- Result statuses: `ok: 200`, `no_result: 33`, `error: 10`
- Expectation cases: `pass: 232`, `fail: 11`
- Expectation checks: `pass: 1304`, `fail: 28`
- Suspicious flag cases: 3
- Suspicious flags: `expected_ok_returned_non_ok: 3`
- Informational flag cases: 147
- Informational flags: `frontend_hero_expected: 147`
- Verified outlier cases: 1
- Verified outliers: `top_performance_high_points: 1`

New review signals are grouped into these families:

- defensive phrasing variants that still bind to team points instead of
  opponent points: `gave up the fewest`, `held teams to under`, and
  `teams allowing the fewest`
- record/summary intent variants: `How did the Lakers do...` routes to a game
  finder, and possessive `Jokic's record...` returns no-result despite the
  triple-double condition
- context preservation: `since January 1` is treated as a single-day window,
  and `Curry ... from three` preserves last-20 but drops the three-point stat
  context
- playoff phrasing variants: hyphenated `second-round` falls into regular
  season record leaderboards, and `playoff matchup history` misses the playoff
  matchup-history route
- unsupported-boundary variant coverage: `players with most personal fouls`
  is unrouted instead of the personal-foul unsupported boundary
- product decision: single-team advanced metric phrasing such as
  `Warriors net rating this season` currently returns unsupported; decide
  whether this should become a scalar/team-summary route or remain a documented
  boundary

## Finding summary

| Finding ID | Priority | Category | Query / Case ID | Finding type | Status | Notes | Recommended fix family |
|---|---|---|---|---|---|---|---|
| AQ-001 | P1 | Team record / opponent quality | `celtics_record_playoff_teams` | semantics_issue | fixed | Fixed in Raw Query Answer QA Fix Wave 4. `against playoff teams` and phrase variants now stay in Regular Season opponent-quality context unless explicit playoff-competition wording is present. Target case returns 2025-26 regular-season `54` games, `33-21`; latest run: `outputs/raw_query_answer_qa/20260512T124917Z/report.md`. | opponent-quality semantics |
| AQ-002 | P1 | Top performances | `biggest_scoring_games` | verified_official_outlier | closed_verified | Fixed in Raw Query Answer QA Fix Wave 5. Bam Adebayo's 83-point game on 2026-03-10 was traced to raw player/team source rows and external official-source spot checks; `top_player_games` exposes the source data correctly. QA now uses `qa/verified_outliers.yaml` to classify this as a verified official outlier while preserving open high-point suspicious flags for new/unverified rows. Latest run: `outputs/raw_query_answer_qa/20260513T025137Z/report.md`. | top-performance data quality |
| AQ-003 | P2 | Backend answer text / frontend hero | Many P0/P1 summary routes | expected limitation | partially_addressed / reclassified_expected_limitation | Fix Wave 7A added `answer_text_policy` and reclassified the 22 frontend-hero routes as informational `frontend_hero_expected` instead of suspicious `missing_backend_answer_text`. Latest run `outputs/raw_query_answer_qa/20260513T044523Z/report.md` has 0 suspicious flags and 22 informational frontend-hero limitations. Exact frontend-rendered hero extraction remains deferred; targeted backend `answer_phrase` enrichment for high-value record-style routes remains a future wave. | answer text policy / targeted backend answer enrichment |
| AQ-004 | P1 | Record-when team condition | `lakers_held_opponents_under_100_record` | needs_followup | fixed | Fixed in Raw Query Answer QA Fix Wave 1. `team_record` now computes opponent-points threshold summaries from the filtered sample: Lakers held opponents under 100 returns 7 games, 7 wins, 0 losses, matching the companion count/finder sample. Latest run: `outputs/raw_query_answer_qa/20260512T085014Z/report.md`. | record-when conditions |
| AQ-005 | P1 | Availability / multi-player condition | `lakers_lebron_ad_both_play` | missing_filter | fixed_as_expected_unsupported | Fixed in Raw Query Answer QA Fix Wave 2. Multi-player availability record queries now return `no_result` / `filter_not_supported` with guidance instead of an unfiltered full-season `team_record`. Latest run: `outputs/raw_query_answer_qa/20260512T100442Z/report.md`. | unsupported/no-result policy |
| AQ-006 | P2 | Top performances | `most_assists_single_game`, `most_rebounds_single_game` | supported_now | fixed | Fixed in Raw Query Answer QA Fix Wave 6. Natural non-scoring single-game top-performance queries now route to `top_player_games` with `stat=ast` / `stat=reb` and keep the existing `top_performances` shape. | top-performance routing |
| AQ-007 | P2 | Date handling | `specific_date_jan_1` | missing_filter | fixed | Fixed in Raw Query Answer QA Fix Wave 3. Explicit calendar-date top-scorer wording now parses `January 1 2026`, preserves the date filter, and routes to game-level `top_player_games` instead of unfiltered season leaders. Latest run: `outputs/raw_query_answer_qa/20260512T105201Z/report.md`. | data freshness/date handling |
| AQ-008 | P2 | Rolling stretch / team scope | `team_5_game_scoring_stretch` | fixed_as_expected_unsupported | fixed_as_expected_unsupported | Fixed in Raw Query Answer QA Fix Wave 6. Team-scoped rolling-stretch wording no longer returns player windows; it returns `no_result` / `filter_not_supported` with `unsupported_filters=["team_rolling_stretch"]` until a team rolling route/result contract exists. | unsupported/no-result policy |
| AQ-009 | P1 | Routing / data no-match | `anthony_edwards_last_10_summary_no_match`, `anthony_edwards_wins_losses_split_no_match` | routing_or_data_gap | fixed | Fixed in Raw Query Answer QA Fix Wave 5. Data-backed full-name player resolution now wins before broad single-token nickname aliases, so `Anthony Edwards last 10 games summary` returns a 10-game `player_game_summary`, and `How does Anthony Edwards shoot in wins versus losses?` returns a `player_split_summary` with wins/losses buckets. Latest run: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`. | player summary/split no-match diagnostics |
| AQ-010 | P1 | Stat/context filters | `kd_ts_top_defenses_missing_filters` | route_and_filter_drop | fixed | Fixed in Raw Query Answer QA Fix Wave 5. `top defenses` now maps to the existing `top-10 defenses` opponent-quality bucket in `against` / `vs` / `versus` context, and player + stat + opponent-quality queries route to `player_game_summary` unless explicit finder/count wording is present. `KD TS% vs top defenses` returns a 23-game Kevin Durant summary with TS% and the quality filter preserved. Latest run: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`. | stat alias + opponent-quality routing |
| AQ-011 | P1 | Defensive stat semantics | `knicks_allowed_under_110_record`, `fewest_points_allowed_team_leader` | stat_mapping_issue | fixed | Fixed in Raw Query Answer QA Fix Wave 4A. `allow fewer than 110` maps to `opponent_pts max` and Knicks return 35 games, 32-3. `allowed the fewest points per game` ranks `opponent_pts_per_game` ascending; Boston is top at about 107.159 opponent PPG. Latest run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`. | defensive/opponent-points stat mapping |
| AQ-012 | P1 | Date/context filters | `lakers_road_record_last_season` | missing_filter | fixed | Fixed in Raw Query Answer QA Fix Wave 5. Singular `last season` resolves to the previous latest regular season (`2024-25` when latest is `2025-26`) and preserves road/away location filters. The Lakers road record last season returns 41 games, 19 wins, and 22 losses with explicit relative-season metadata/filter context. Latest run: `outputs/raw_query_answer_qa/20260513T094000Z_wave5_full/report.md`. | relative season parsing/filter preservation |
| AQ-013 | P1 | Record-when player condition | `boston_tatum_under_40_fg_record_missing_filter` | missing_filter | fixed | Fixed in Raw Query Answer QA Fix Wave 4A. Clear shooting percentage thresholds infer `fg_pct`, normalize `40%` / `40 percent` to 0.40, and Tatum under 40% returns 6 games, 4-2 with an applied `fg_pct max` filter. Latest run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`. | percentage threshold parsing/execution |
| AQ-014 | P1 | Compound thresholds | `celtics_120_15_threes_count_missing_filter`, `jokic_30_points_10_assists_finder_misparsed` | missing_filter / stat_binding_issue | fixed | Fixed in Raw Query Answer QA Fix Wave 4B. Compound stat thresholds now use a route-consumed `conditions` list instead of duplicating the same filters into unsafe post-aggregate `extra_conditions`. Finder routes apply compound conditions before sorting/limiting. Celtics `120+ points` and `15+ threes` since 2022 returns count 125 with both applied filters; Jokic `30 points and 10 assists` returns 14 finder rows satisfying both thresholds. Latest run: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`. | compound threshold parsing/execution |
| AQ-015 | P2 | Leaderboard context filters | `guards_fg_percentage_leaders` | missing_filter | fixed | Position-filtered leaderboards preserve the existing `position_filter` metadata and applied filter. Frontend Copy QA Fix Wave 1 fixed the exact `among guards?` punctuation/source case so it now returns `position_filter=guards` instead of a broad FG% leaderboard. Latest run: `outputs/raw_query_answer_qa/20260515T021820Z/report.md`. | position-filtered leaderboards |
| AQ-016 | P2 | Backend answer text quality | `players_40_point_count`, `players_10_assist_count`, `curry_5_threes_count`, `luka_40_point_count`, `wemby_5_blocks_count`, `teams_120_point_count_answer_text_review` | awkward_answer_text | open | Backend count phrases are present but sometimes too generic (`Result has recorded...`) or expose raw stat labels (`fg3ms`, `blks`, `pts`) instead of natural threshold phrasing. | count phrase generation |
| AQ-017 | P2 | Product boundary / stat coverage | `minutes_leaders_unsupported`, `biggest_team_three_point_games_boundary` | needs_product_decision | open | `minutes` is documented as a stat alias but leaderboard execution returns unsupported; team single-game threes wording is unrouted even though top-team-game scoring exists. Decide whether to support or document these as explicit boundaries. | product boundary / stat coverage |
| AQ-018 | P2 | Position/role-filtered leaderboards | `centers_rebound_leaders_wave4`, `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4` | missing_filter / unsupported_no_result_policy | fixed_partial_support_and_expected_unsupported | Fixed in Wave 7A. Noun-prefix/question-form position leaderboards now apply `position_filter` through the existing `season_leaders` position contract. Rookie, league-wide role, and team bench-scoring forms now return `no_result` / `filter_not_supported` with explicit `unsupported_filters` instead of broad player/team tables. Latest run: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`. | position/role-filtered leaderboards |
| AQ-019 | P2 | Player comparison routing | `lebron_durant_comparison_wave4` | route_mismatch | fixed | Fixed in Wave 7A. Full-name comparison phrasing such as `LeBron James vs Kevin Durant comparison` and `Compare LeBron James and Kevin Durant` routes to `player_compare`, while player-game forms such as `Jokic game log vs Embiid` remain player finder/opponent-player queries. Latest run: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`. | comparison routing / player-vs-player intent |
| AQ-020 | P1 | Playoff round and matchup phrasing | `bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`, `heat_knicks_playoff_series_record_wave4` | route_and_season_type_issue | fixed_as_expected_unsupported | Fixed in Raw Query Answer QA Fix Wave 6B. Adjacent `Heat Knicks playoff series record` now routes to `playoff_matchup_history` with MIA/NYK and passes as a matchup result. Single-team Finals/conference-finals record phrasing no longer falls through to regular-season `team_record`; it returns `no_result` / `filter_not_supported` with `unsupported_filters=["single_team_playoff_round_record"]`. Bulls Finals remains unsupported because current pre-2001 round labels are not reliable. Latest run: `outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.md`. | playoff round/matchup routing |
| AQ-021 | P1 | Defensive stat aliases | `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | stat_mapping_issue / route_mismatch | fixed | Fixed in Raw Query Answer QA Fix Wave 6A. `allow the most points per game`, `most points allowed`, and `opponent PPG leaders` now bind to team opponent-points semantics via `season_team_leaders` with `opponent_pts_per_game`; the current highest opponent-PPG top row is Utah. Latest run: `outputs/raw_query_answer_qa/20260514T050631Z/report.md`. | defensive/opponent-points stat mapping |
| AQ-022 | P2 | Unsupported stat alias boundary | `personal_foul_leaders_wave4` | unsupported_no_result_policy | fixed_as_expected_unsupported | Fixed in Wave 7A as an explicit product boundary. `personal fouls leaders` now returns `no_result` / `filter_not_supported` with `unsupported_filters=["personal_foul_leaderboard"]` instead of falling back to points. Actual PF leaderboard support remains deferred pending a stat contract decision. Latest run: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`. | product boundary / stat coverage |
| AQ-023 | P2 | Opponent conference filters | `celtics_against_east_record_wave4` | missing_filter / unsupported_no_result_policy | fixed_as_expected_unsupported | Fixed in Wave 7A as an explicit product boundary. `against the East/West` record phrasing now returns `no_result` / `filter_not_supported` with `unsupported_filters=["opponent_conference"]` instead of a full-season record. Actual opponent-conference support remains deferred until complete team-conference metadata exists. Latest run: `outputs/raw_query_answer_qa/20260514T125056Z/report.md`. | context filter preservation |
| AQ-024 | P1 | Defensive stat aliases | `team_gave_up_fewest_ppg_wave5`, `lakers_held_teams_under_100_wave5`, `teams_allowing_fewest_points_wave5` | stat_mapping_issue | open | Wave 5 found remaining defensive phrasing variants that bind to team points rather than opponent points. `gave up the fewest points per game` and `teams allowing the fewest points` return `season_team_leaders` with `stat=pts` ascending; `held teams to under 100` applies `pts max` rather than `OPP PTS max`. | defensive/opponent-points stat mapping |
| AQ-025 | P2 | Team record phrasing | `lakers_how_did_road_last_season_wave5` | route_mismatch | open | `How did the Lakers do on the road last season?` preserves road and 2024-25 filters but routes to `game_finder` with finder rows instead of the expected record-summary `team_record` shape. | summary-vs-finder intent routing |
| AQ-026 | P1 | Record-when player condition | `jokic_possessive_triple_double_record_wave5` | routing_or_data_gap | open | Possessive `Jokic's record in games with a triple-double` returns `no_result` on `player_game_summary` with team context `WAS`, despite preserving the triple-double filter. The non-possessive canonical Jokic triple-double record case remains supported. | player/team context resolution |
| AQ-027 | P1 | Date/window context | `celtics_road_record_since_jan_1_wave5` | missing_filter | open | `since January 1` on a team record is parsed as a single-day `2026-01-01 - 2026-01-01` date range rather than an open-ended `2026-01-01 - current_through` window. | date-window parsing/filter preservation |
| AQ-028 | P2 | Player stat context | `curry_last_20_from_three_wave5` | missing_filter | open | `Curry last 20 games from three` preserves the last-20 window but does not expose `stat=fg3m` or equivalent three-point context in metadata. | stat alias + context preservation |
| AQ-029 | P1 | Playoff/history phrasing | `best_second_round_record_since_2010_wave5`, `lakers_celtics_playoff_matchup_history_wave5` | route_and_season_type_issue | open | Hyphenated `second-round` routes to regular-season `team_record_leaderboard` instead of playoff round records; `Lakers Celtics playoff matchup history` routes to `team_compare` and returns no-result instead of `playoff_matchup_history`. Adjacent `playoff series history` and `playoff history` variants still pass. | playoff round/matchup routing |
| AQ-030 | P2 | Unsupported stat alias boundary | `players_personal_fouls_wave5` | unsupported_no_result_policy | open | `players with most personal fouls this season` is unrouted (`error` / `unrouted`) rather than using the explicit personal-foul unsupported boundary (`no_result` / `filter_not_supported`). It does not broaden to points, but the boundary guidance is less specific than the fixed `personal fouls leaders` phrase. | product boundary / stat coverage |
| AQ-031 | P2 | Advanced metric product boundary | `warriors_net_rating_single_team_wave5` | needs_product_decision | open | `Warriors net rating this season` returns `no_result` / `unsupported` on `game_finder` with `stat=net_rating`. Decide whether single-team advanced metric scalar summaries are in scope or should become a documented unsupported boundary with specific guidance. | product boundary / stat coverage |

## Frontend Copy QA Findings

Latest frontend-copy run:

- Run ID: `20260515T024718Z`
- Source backend run:
  `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- Report:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- Selected cases: 59
- Rendered successfully: 59
- Render failures: 0
- Soft checks: `pass: 156`, `fail: 0`, `not_checked: 0`

| Finding ID | Priority | Category | Cases | Status | Notes |
|---|---|---|---|---|---|
| FCQ-001 | P1 | Position filter source/visibility | `guards_fg_percentage_leaders` | fixed | Parser/backend now recognizes the exact `field goal percentage among guards?` phrasing as `position_filter=guards`; raw QA hard-asserts the position metadata/applied filter, and frontend-copy renders `Position guards`. |
| FCQ-002 | P1 | Opponent-points leaderboard hero wording | `fewest_points_allowed_team_leader`; guardrails `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | fixed | `season_team_leaders` metadata now exposes executed `ascending`; leaderboard hero copy renders fewest/most allowed-points wording according to that direction. |
| FCQ-003 | P2 | Unsupported/no-result guidance specificity | `personal_foul_leaders_wave4`, `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4`; utility coverage also includes `team_bench_scoring` | fixed | No-result primary copy now uses boundary-specific messages for personal-foul, rookie, league-wide starter/bench, and team bench-scoring unsupported filters instead of generic stat-unavailable copy. |

## Notes

- The Celtics playoff-teams issue is fixed as of Wave 4; the Bam 83-point issue is closed as a verified official outlier as of Wave 5.
- Cases marked `expected_unsupported` in the corpus are product-boundary samples, not failures.
- AQ-006 and AQ-008 were resolved in Wave 6; AQ-003 is now a reclassified expected limitation rather than an open suspicious flag family.
- AQ-020 was resolved in Wave 6B: playoff matchup adjacency is fixed, while
  single-team playoff round records are explicitly unsupported until a route
  and round-data contract is approved. Bulls Finals-era round labels remain a
  documented data boundary.
- Wave 7A resolved the remaining eight Wave 6B failures. The 195-case corpus
  now has 195 expectation passes, zero suspicious flags, and no failed case IDs.
- Corpus Expansion Wave 5 intentionally leaves 11 expectation failures in the
  expanded 243-case corpus for newly exposed review families. The original
  195 clean cases were preserved.
- Exact frontend rendered-answer extraction is still deferred; targeted backend `answer_phrase` enrichment remains an optional future improvement for high-value direct-answer routes.
- The manual corpus should remain review-oriented. Promote only objective, stable failures into focused tests near the behavior they protect.
- Fix Wave 4A resolved AQ-011 and AQ-013 scalar semantics. Fix Wave 4B
  resolved AQ-014 compound threshold representation/execution. Fix Wave 5
  resolved AQ-009, AQ-010, and AQ-012, bringing the 145-case corpus to
  145/145 expectation passes with zero suspicious flags.
- Expansion Wave 3 intentionally leaves expectation failures in place for cases
  that appear to expose real behavior gaps. Do not "green" those cases by
  encoding wrong current behavior unless product review decides they are
  unsupported boundaries.
- Corpus Expansion Wave 4 intentionally leaves 14 expectation failures in place
  for new P2/deeper coverage cases that expose product gaps or product-decision
  boundaries. The original 145 clean cases remain preserved.
