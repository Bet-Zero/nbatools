# Raw Query Answer QA Findings

## Purpose

This doc tracks manual-review findings from Raw Query Answer QA harness runs.
The harness corpus is a product-answer review set, not a hard regression suite:
findings here should be grouped into fix families before implementation.

## Latest run

- Run ID: `20260513T084000Z_wave4b_full`
- Corpus size: 145 cases
- Output report path: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`
- Summary counts:
  - Result statuses: `ok: 127`, `no_result: 12`, `error: 6`
  - Expectation cases: `pass: 141`, `fail: 4`
  - Expectation checks: `pass: 716`, `fail: 10`
  - Failed case IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `anthony_edwards_wins_losses_split_no_match`
  - Manual review statuses: `unreviewed: 124`, `expected_unsupported: 8`, `pass: 12`, `verified_outlier: 1`
  - Answer text policies: `frontend_hero_expected: 76`, `requires_backend_answer_text: 10`, `no_answer_text_expected: 16`, `<unspecified>: 43`
  - Answer text statuses: `frontend_hero_expected: 74`, `backend_answer_text_present: 10`, `no_answer_text_expected: 16`, `not_required: 45`
  - Suspicious flag cases: 2
  - Suspicious flags: `expected_ok_returned_non_ok: 2`
  - Informational flag cases: 74
  - Informational flags: `frontend_hero_expected: 74`
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
| AQ-009 | P1 | Routing / data no-match | `anthony_edwards_last_10_summary_no_match`, `anthony_edwards_wins_losses_split_no_match` | routing_or_data_gap | open | Documented player last-N summary and wins/losses split forms return `no_result` / `no_match` for Anthony Edwards despite preserving the intended filters. Needs diagnosis to separate entity resolution, data coverage, and split/window execution. | player summary/split no-match diagnostics |
| AQ-010 | P1 | Stat/context filters | `kd_ts_top_defenses_missing_filters` | route_and_filter_drop | open | Abbreviation-heavy `KD TS% vs top defenses` routes to `player_game_finder`, returns 25 rows, and drops the top-defense opponent-quality context instead of producing a filtered summary. | stat alias + opponent-quality routing |
| AQ-011 | P1 | Defensive stat semantics | `knicks_allowed_under_110_record`, `fewest_points_allowed_team_leader` | stat_mapping_issue | fixed | Fixed in Raw Query Answer QA Fix Wave 4A. `allow fewer than 110` maps to `opponent_pts max` and Knicks return 35 games, 32-3. `allowed the fewest points per game` ranks `opponent_pts_per_game` ascending; Boston is top at about 107.159 opponent PPG. Latest run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`. | defensive/opponent-points stat mapping |
| AQ-012 | P1 | Date/context filters | `lakers_road_record_last_season` | missing_filter | open | `last season` is dropped while the road filter is preserved, so the result is a current-season road record rather than a last-season road record. | relative season parsing/filter preservation |
| AQ-013 | P1 | Record-when player condition | `boston_tatum_under_40_fg_record_missing_filter` | missing_filter | fixed | Fixed in Raw Query Answer QA Fix Wave 4A. Clear shooting percentage thresholds infer `fg_pct`, normalize `40%` / `40 percent` to 0.40, and Tatum under 40% returns 6 games, 4-2 with an applied `fg_pct max` filter. Latest run: `outputs/raw_query_answer_qa/20260513T072000Z_wave4a_full/report.md`. | percentage threshold parsing/execution |
| AQ-014 | P1 | Compound thresholds | `celtics_120_15_threes_count_missing_filter`, `jokic_30_points_10_assists_finder_misparsed` | missing_filter / stat_binding_issue | fixed | Fixed in Raw Query Answer QA Fix Wave 4B. Compound stat thresholds now use a route-consumed `conditions` list instead of duplicating the same filters into unsafe post-aggregate `extra_conditions`. Finder routes apply compound conditions before sorting/limiting. Celtics `120+ points` and `15+ threes` since 2022 returns count 125 with both applied filters; Jokic `30 points and 10 assists` returns 14 finder rows satisfying both thresholds. Latest run: `outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md`. | compound threshold parsing/execution |
| AQ-015 | P2 | Leaderboard context filters | `guards_fg_percentage_leaders` | missing_filter | open | `among guards` is ignored; the top row is Jaxson Hayes, indicating position context is not applied on this leaderboard. | position-filtered leaderboards |
| AQ-016 | P2 | Backend answer text quality | `players_40_point_count`, `players_10_assist_count`, `curry_5_threes_count`, `luka_40_point_count`, `wemby_5_blocks_count`, `teams_120_point_count_answer_text_review` | awkward_answer_text | open | Backend count phrases are present but sometimes too generic (`Result has recorded...`) or expose raw stat labels (`fg3ms`, `blks`, `pts`) instead of natural threshold phrasing. | count phrase generation |
| AQ-017 | P2 | Product boundary / stat coverage | `minutes_leaders_unsupported`, `biggest_team_three_point_games_boundary` | needs_product_decision | open | `minutes` is documented as a stat alias but leaderboard execution returns unsupported; team single-game threes wording is unrouted even though top-team-game scoring exists. Decide whether to support or document these as explicit boundaries. | product boundary / stat coverage |

## Notes

- The Celtics playoff-teams issue is fixed as of Wave 4; the Bam 83-point issue is closed as a verified official outlier as of Wave 5.
- Cases marked `expected_unsupported` in the corpus are product-boundary samples, not failures.
- AQ-006 and AQ-008 were resolved in Wave 6; AQ-003 is now a reclassified expected limitation rather than an open suspicious flag family.
- Exact frontend rendered-answer extraction is still deferred; targeted backend `answer_phrase` enrichment remains an optional future improvement for high-value direct-answer routes.
- The manual corpus should remain review-oriented. Promote only objective, stable failures into focused tests near the behavior they protect.
- Fix Wave 4A resolved AQ-011 and AQ-013 scalar semantics. Fix Wave 4B
  resolved AQ-014 compound threshold representation/execution.
- Expansion Wave 3 intentionally leaves expectation failures in place for cases
  that appear to expose real behavior gaps. Do not "green" those cases by
  encoding wrong current behavior unless product review decides they are
  unsupported boundaries.
