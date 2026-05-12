# Raw Query Answer QA Findings

## Purpose

This doc tracks manual-review findings from Raw Query Answer QA harness runs.
The harness corpus is a product-answer review set, not a hard regression suite:
findings here should be grouped into fix families before implementation.

## Latest run

- Run ID: `20260512T105201Z`
- Corpus size: 78 cases
- Output report path: `outputs/raw_query_answer_qa/20260512T105201Z/report.md`
- Summary counts:
  - Result statuses: `ok: 67`, `no_result: 5`, `error: 6`
  - Expectation cases: `pass: 78`
  - Expectation checks: `pass: 384`
  - Failed case IDs: `[]`
  - Manual review statuses: `unreviewed: 64`, `expected_unsupported: 7`, `needs_product_decision: 3`, `pass: 2`, `semantics_issue: 1`, `data_quality_question: 1`
  - Suspicious flag cases: 21
  - Suspicious flags: `missing_backend_answer_text: 20`, `playoff_teams_playoff_season_type: 1`, `top_performance_high_points: 1`

## Finding summary

| Finding ID | Priority | Category | Query / Case ID | Finding type | Status | Notes | Recommended fix family |
|---|---|---|---|---|---|---|---|
| AQ-001 | P1 | Team record / opponent quality | `celtics_record_playoff_teams` | semantics_issue | open | Query asks for record against playoff teams, but metadata uses `season_type: Playoffs`; likely intent is regular-season record against teams that made playoffs. | opponent-quality semantics |
| AQ-002 | P1 | Top performances | `biggest_scoring_games` | data_quality_question | open | Top player scoring row is Bam Adebayo with 83 points on 2026-03-10; record as suspicious until source data is audited. | top-performance data quality |
| AQ-003 | P2 | Backend answer text / frontend hero | Many P0/P1 summary routes | expected limitation | deferred | 21 cases flagged as missing backend answer text. This is expected for Wave 2 because frontend-rendered hero extraction is deferred, not a production bug by itself. | frontend hero extraction |
| AQ-004 | P1 | Record-when team condition | `lakers_held_opponents_under_100_record` | needs_followup | fixed | Fixed in Raw Query Answer QA Fix Wave 1. `team_record` now computes opponent-points threshold summaries from the filtered sample: Lakers held opponents under 100 returns 7 games, 7 wins, 0 losses, matching the companion count/finder sample. Latest run: `outputs/raw_query_answer_qa/20260512T085014Z/report.md`. | record-when conditions |
| AQ-005 | P1 | Availability / multi-player condition | `lakers_lebron_ad_both_play` | missing_filter | fixed_as_expected_unsupported | Fixed in Raw Query Answer QA Fix Wave 2. Multi-player availability record queries now return `no_result` / `filter_not_supported` with guidance instead of an unfiltered full-season `team_record`. Latest run: `outputs/raw_query_answer_qa/20260512T100442Z/report.md`. | unsupported/no-result policy |
| AQ-006 | P2 | Top performances | `most_assists_single_game`, `most_rebounds_single_game` | needs_product_decision | needs_manual_review | Non-scoring single-game top-performance wording is currently unrouted. Decide whether these should route to `top_player_games` with `ast`/`reb` or remain unsupported with guidance. | unsupported/no-result policy |
| AQ-007 | P2 | Date handling | `specific_date_jan_1` | missing_filter | fixed | Fixed in Raw Query Answer QA Fix Wave 3. Explicit calendar-date top-scorer wording now parses `January 1 2026`, preserves the date filter, and routes to game-level `top_player_games` instead of unfiltered season leaders. Latest run: `outputs/raw_query_answer_qa/20260512T105201Z/report.md`. | data freshness/date handling |
| AQ-008 | P2 | Rolling stretch / team scope | `team_5_game_scoring_stretch` | needs_product_decision | needs_manual_review | Team-scoped rolling-stretch wording currently routes to `player_stretch_leaderboard`. Decide whether team rolling stretches are supported or should return an unsupported/no-result response. | unsupported/no-result policy |

## Notes

- The Celtics playoff-teams issue and Bam 83-point issue are recorded only; Wave 3 intentionally does not fix them.
- Cases marked `expected_unsupported` in the corpus are product-boundary samples, not failures.
- The manual corpus should remain review-oriented. Promote only objective, stable failures into focused tests near the behavior they protect.
