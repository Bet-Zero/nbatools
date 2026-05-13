# Raw Query Answer QA Findings

## Purpose

This doc tracks manual-review findings from Raw Query Answer QA harness runs.
The harness corpus is a product-answer review set, not a hard regression suite:
findings here should be grouped into fix families before implementation.

## Latest run

- Run ID: `20260513T044523Z`
- Corpus size: 80 cases
- Output report path: `outputs/raw_query_answer_qa/20260513T044523Z/report.md`
- Summary counts:
  - Result statuses: `ok: 70`, `no_result: 6`, `error: 4`
  - Expectation cases: `pass: 80`
  - Expectation checks: `pass: 409`
  - Failed case IDs: `[]`
  - Manual review statuses: `unreviewed: 64`, `expected_unsupported: 8`, `pass: 7`, `verified_outlier: 1`
  - Answer text policies: `frontend_hero_expected: 22`, `requires_backend_answer_text: 5`, `no_answer_text_expected: 10`, `<unspecified>: 43`
  - Answer text statuses: `frontend_hero_expected: 22`, `backend_answer_text_present: 5`, `no_answer_text_expected: 10`, `not_required: 43`
  - Suspicious flag cases: 0
  - Suspicious flags: `{}`
  - Informational flag cases: 22
  - Informational flags: `frontend_hero_expected: 22`
  - Verified outlier cases: 1
  - Verified outliers: `top_performance_high_points: 1`

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

## Notes

- The Celtics playoff-teams issue is fixed as of Wave 4; the Bam 83-point issue is closed as a verified official outlier as of Wave 5.
- Cases marked `expected_unsupported` in the corpus are product-boundary samples, not failures.
- AQ-006 and AQ-008 were resolved in Wave 6; AQ-003 is now a reclassified expected limitation rather than an open suspicious flag family.
- Exact frontend rendered-answer extraction is still deferred; targeted backend `answer_phrase` enrichment remains an optional future improvement for high-value direct-answer routes.
- The manual corpus should remain review-oriented. Promote only objective, stable failures into focused tests near the behavior they protect.
