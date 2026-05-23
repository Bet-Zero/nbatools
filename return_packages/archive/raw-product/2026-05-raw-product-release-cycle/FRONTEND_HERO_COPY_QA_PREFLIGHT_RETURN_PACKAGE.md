# Frontend Hero / Copy QA Preflight Return Package

## 1. Executive summary

- Recommended approach: use a hybrid frontend-copy QA layer. Start with rendered DOM text extraction for a selected 40-60 case subset from the clean backend QA corpus, then keep screenshot/manual review as a separate visual QA pass.
- Should we test all 195 cases now? no. The first frontend-copy corpus should be shape-by-shape and risk-based, not exhaustive.
- Should we build frontend extraction now? no. This preflight only defines the next layer.
- Should we use screenshots now? no. Screenshots are useful after text extraction proves stable, especially for hierarchy, wrapping, and visual emphasis.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

The existing backend corpus is clean enough to become the source of frontend-review payloads. The first QA layer should validate facts and labels that can be read from rendered UI: hero sentence, supporting copy, applied filters, no-result guidance, and table headers. It should not start with full-page snapshots or exact copy locks across all 195 cases.

Recommended next step after this preflight: build a small frontend-copy extraction harness that renders `ResultEnvelope` and `ResultRenderer` against saved backend QA output, emits `frontend_copy_report.jsonl` and `frontend_copy_report.md`, and classifies findings as semantic failures, polish issues, product decisions, or visual/layout issues.

## 2. Current frontend copy architecture

Hero generation is not centralized. `ResultHero` is a shared display primitive, but the actual sentence/copy logic is spread across result pattern components. Most pattern helpers are already close to pure helper functions, but many are file-local and embedded in React components.

| Component | Routes/shapes | Hero/copy source | Extractable? | Risk |
|---|---|---|---|---|
| `ResultRenderer` | All rendered query responses, no-result dispatch | Selects pattern through `routeToPattern(data)` or shows `NoResultDisplay`; no direct hero copy except fallback behavior | Yes, by rendering the whole result | Medium. Dispatch mistakes can hide the right pattern or show fallback/no-result copy |
| `ResultEnvelope` | All responses around the result body | Builds status/route/query copy, context items, notes, caveats, and applied filter chips from `metadata` and `applied_filters`; does not use backend answer phrases | Yes | High for filter/context QA because chips may be the only visible place where some filters appear |
| `ResultHero` primitive | All pattern heroes using the shared primitive | Receives `sentence: ReactNode`; does not generate facts itself | Yes | Low by itself; risk lives in callers |
| `EntitySummaryResult` | `player_game_summary`, `lineup_summary` | File-local helpers build summary, record-when player-condition, lineup, average, and filter/context phrases from rows, metadata, and query; no backend phrase | Yes | High. Record-when and filtered summaries can mislead if record/count/context is omitted |
| `RecordResult` | `team_record`, `record_by_decade`, `record_by_decade_leaderboard`, `matchup_by_decade` | File-local helpers build record, decade, leaderboard, and matchup sentences from rows, metadata, and query; no backend phrase | Yes | High. Opponent group, playoff-team, without-player, last-season, and decade phrasing carry user-facing semantics |
| `LeaderboardResult` | `season_leaders`, `season_team_leaders`, `team_record_leaderboard`, `player_occurrence_leaders`, `team_occurrence_leaders`, `lineup_leaderboard`, ranked `playoff_appearances` | Uses first row, inferred metric config, route options, and sometimes backend `metadata.count_phrase`; table labels are route/metric driven | Yes | High. Metric labels, position filters, count leaderboards, and defensive/opponent metrics are easy to mislabel |
| `TopPerformancesResult` | `top_player_games`, `top_team_games` | Builds headline from first row, inferred metric, subject, metadata, and query; no backend phrase | Yes | High. Metric units, date/opponent facts, team vs player subject, and verified outlier handling need review |
| `ComparisonResult` | `player_compare`, `team_compare`, `team_matchup_record` | Builds edge, wins, recent-form, and head-to-head sentences from comparison rows and metadata; no backend phrase | Yes | High. Winner/edge wording, head-to-head vs comparison mode, and window labels can contradict rows |
| `PlayoffHistoryResult` | `playoff_history`, single-team `playoff_appearances`, `playoff_round_record`, `playoff_matchup_history` | Builds ReactNode hero fragments for history, appearances, round records, and matchups from rows and metadata; no backend phrase | Yes, but exact text extraction crosses React fragments | High. Game/series/round distinction, era coverage, and unavailable round boundaries are high-risk |
| `GameLogResult` | `player_game_finder`, `game_finder`, `game_summary`, stacked game-log displays | Uses backend `metadata.count_phrase` or `metadata.answer_phrase` when present; otherwise summary strip plus table only | Yes | Medium-high. Backend phrase quality is known to be uneven, but frontend must not hide or distort it |
| `SplitResult` | Split summaries and on/off summaries | Builds split hero and edge chips from summary rows and metadata; no backend phrase | Yes | Medium. Split labels and window/context copy need semantic checks |
| `StreakResult` | Player/team streaks | Builds active/completed/min-streak sentence from rows and metadata; no backend phrase | Yes | Medium-high. Active vs completed selection and threshold phrasing are easy to misread |
| `RollingStretchResult` | `player_stretch_leaderboard` and named-player stretch views | Builds named-player or league stretch sentence from rows, metadata, and query; no backend phrase | Yes | Medium-high. Window size, metric unit, and named-player vs leaderboard mode are important |
| `NoResultDisplay` and `noResultDisplayUtils` | `no_result`, `error`, unsupported and empty-section output | Builds title, message, details, suggested queries, and next steps from status, reason, metadata, notes, and caveats | Yes | High. Unsupported/no-result guidance must be precise and must not imply unsupported filters work |
| `FallbackTableResult` | Unmapped section shapes | Generic section/table labels from section keys | Yes | Low-medium. Useful as a guardrail that unmapped routes are visible, but not a primary hero/copy target |

React-fragment copy appears most visibly in `PlayoffHistoryResult` hero sentences and in several supporting UI blocks. `ResultHero` accepts `ReactNode`, so a future extractor should read rendered text from the DOM rather than trying to call every helper directly.

Components most suitable for later pure-helper extraction are `EntitySummaryResult`, `RecordResult`, `LeaderboardResult`, `TopPerformancesResult`, `ComparisonResult`, `StreakResult`, `RollingStretchResult`, and `SplitResult`. `PlayoffHistoryResult` can also be refactored, but its ReactNode sentence fragments make DOM-based extraction the safer first step.

High-risk copy areas are record-when player conditions, opponent/playoff-team filters, without-player filters, defensive/opponent metric leaderboards, top-performance outliers, playoff series/game wording, comparison edge labels, and unsupported/no-result guidance.

## 3. Existing frontend test coverage

| Test file | What it covers | Gaps |
|---|---|---|
| `frontend/src/test/ResultRenderer.test.tsx` | Broad visible-copy and result-pattern integration coverage. It asserts hero text, labels, table headers, no-result behavior, top performances, leaderboards, team records, summaries, splits, streaks, comparisons, playoff history, and several Wave 4 cases. | Fixtures are hand-built, not sourced from the 195-case backend QA corpus. It does not produce review reports and does not systematically compare rendered facts to backend corpus expectations. |
| `frontend/src/test/resultShapes.test.ts` | Shape classification for core routes and no-result details used by review tooling. | Focuses on classification, not hero/copy semantics. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Table header contracts for Wave 1 routes, including game logs, team records, leaderboards, occurrence leaders, top performances, and rolling stretches. | Does not validate hero/supporting copy or corpus-backed facts. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Table/header contracts for splits, on/off, streaks, comparisons, playoff history, decade records, lineup summaries, and lineup leaderboards. | Does not validate the full rendered narrative against corpus expectations. |
| `frontend/src/test/UIComponents.test.tsx` | `NoResultDisplay` behavior, including date no-match, unsupported cooled-off query, metric unavailable guidance, ambiguous queries, caveats, and hidden parser internals. | Not tied to the current backend QA corpus and does not cover every unsupported boundary now represented there. |
| `frontend/src/ReviewPage.tsx` plus related tests | Existing manual review flow, shape grouping, API fixture execution, caching, and screenshot download support. | Uses `/api/dev/fixtures` from parser examples, not the 195-case QA corpus. It is useful for manual visual review but is not yet a corpus-backed frontend-copy harness. |

## 4. QA strategy options

### Presentation outputs by checkability

| Output | Machine-checkable now | Best reviewed manually | Too brittle for exact testing |
|---|---:|---:|---:|
| Hero headline / main answer sentence | Yes, through rendered DOM text and selected semantic assertions | Yes, for tone and emphasis | Full exact copy across all cases |
| Supporting subtitle/context line | Yes, if extracted as text near the result shell/envelope | Yes | Whitespace and punctuation-level snapshots |
| Result title/header | Yes | Low need | Low brittleness if role/text based |
| Applied filter chips | Yes, from envelope chip text | Yes, for visual prominence | CSS class or chip order if not semantically required |
| Table columns | Yes, through column headers | Low need | Pixel layout or full-table snapshots |
| Table row labels/top row facts | Yes, for selected key cells | Yes, for scan quality | All row values for all 195 cases |
| No-result/unsupported copy | Yes | Yes, for guidance quality | Exact full card text when suggestions evolve |
| Warning/caveat notes | Yes | Yes | Exact ordering when multiple notes are non-semantic |
| Comparison labels | Yes | Yes | Exact edge sentence if facts are otherwise clear |
| Playoff/history phrasing | Partly. Entity, round, series/game, appearances, and era can be checked | Yes, because phrasing nuance matters | Exact React-fragment sentence snapshots |
| Record-when phrasing | Yes, especially entity, record, condition, and season | Yes | Full sentence exactness before helper copy stabilizes |
| Leaderboard metric labels | Yes | Low need | Exact decorative text |
| Top-performance metric labels | Yes | Yes for outlier cases | Full table snapshot |

### Options

| Option | Value | Complexity | Brittleness | Recommendation |
|---|---|---|---|---|
| Option A: Render selected API payloads in Vitest/jsdom | High. Reuses existing React test setup and can extract visible DOM text, headings, chips, and table headers from actual components. | Medium. The harness needs to rehydrate saved backend QA JSONL into a `QueryResponse`-like object or use saved API payload fixtures. | Medium if it asserts full text; lower if it emits reports and only promotes stable semantic checks. | Use as the primary Stage 2 path. Start report-first, not hard-test-first. |
| Option B: Add a Node/TS script for frontend copy extraction | High for repeatable batch reports and CI-friendly artifacts. It can emit `frontend_copy_report.jsonl` and markdown without turning every issue into a test. | Medium-high. TSX rendering outside Vitest needs Vite/Vitest setup, `tsx`, or a small test-runner wrapper. | Medium. Same DOM text brittleness risks as Option A, plus script setup drift. | Good follow-on or implementation form of Option A. Prefer a Vitest-backed script/test utility first. |
| Option C: Use `ReviewPage` screenshot/manual workflow | Medium-high for visual QA. It catches hierarchy, wrapping, density, and screenshot-only defects. | Low-medium because `ReviewPage` already exists, but it currently uses parser fixtures, not the QA corpus. | Low for manual review, high for exact screenshot diffing. | Use later for visual/manual batches. Do not make it the first hard QA layer. |
| Option D: Hybrid curated corpus plus rendered text report plus optional screenshots | Highest. Separates semantic copy QA from visual QA and avoids overfitting all 195 cases immediately. | Medium. Requires a selected corpus, a renderer/extractor, and report output. | Controlled. Stable facts can become tests while polish remains report/manual. | Recommended. Start with 40-60 high-value cases, then expand if findings justify it. |

The existing `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl` contains enough route/status/metadata/section data to drive a renderer after light rehydration into the frontend `QueryResponse` envelope. If exact API-envelope fidelity becomes important, the backend QA harness can later add an explicit `api_payload` field, but that should not be part of this preflight.

## 5. Recommended frontend-copy corpus

Do not start with all 195 cases. Start with a 40-60 case representative subset that exercises each high-risk frontend pattern and failure boundary. The table below gives a practical first pass; it can be trimmed to about 50 cases if setup cost matters.

| Category | Suggested cases | Why |
|---|---|---|
| Team record | `celtics_record_playoff_teams`, `lakers_road_record_last_season`, `thunder_since_all_star_record`, `celtics_regular_season_record_vs_playoff_teams_wave4` | Covers playoff-team filters, road/season context, date context, and regular-season opponent grouping. |
| Player game summary | `jokic_season_summary`, `tatum_good_teams`, `luka_last_5_summary`, `sga_playoff_teams_last_season_wave4`, `jokic_assists_since_all_star_wave4` | Exercises base summary, opponent quality, last-N, last-season playoff-team filters, and metric-specific summaries. |
| Record-when conditions | `record_when_jokic_triple_double`, `lakers_held_opponents_under_100_record`, `knicks_allowed_under_110_record`, `boston_tatum_under_40_fg_record_missing_filter`, `warriors_curry_3_threes_record` | High-risk sentence family where record, condition, threshold, and unsupported/missing filter behavior must be clear. |
| Without-player conditions | `suns_without_booker_shorthand`, `knicks_without_brunson`, `lakers_without_lebron` | Ensures without-player filters appear visibly and do not get lost in generic record copy. |
| Player split summary | `jokic_home_away_split`, `curry_home_away_last_20_split_wave4`, `anthony_edwards_wins_losses_split_no_match`, `brunson_wins_losses_split_wave4` | Covers split labels, windows, no-match split output, and wins/losses framing. |
| Top performances | `biggest_scoring_games`, `most_threes_single_game`, `most_blocks_single_game`, `plus_minus_single_game`, `top_team_scoring_games` | Includes the verified outlier plus metric/unit variants and player vs team top-game displays. |
| Season leaders | `points_per_game_leader`, `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4`, `turnover_rate_leader_wave4`, `most_30_point_games` | Covers basic leaderboards, position filters, rate metrics, and occurrence-count labels. |
| Season team leaders | `offensive_rating_team_leader`, `fewest_points_allowed_team_leader`, `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4`, `team_road_record_leaders` | Exercises team metric labels, defensive/opponent wording, and record leaderboard columns. |
| Playoff history | `lakers_playoff_history`, `lakers_finals_appearances`, `most_finals_appearances_since_1980`, `best_second_round_record`, `spurs_playoff_history_since_2000_wave4` | Covers single-team history, appearances, ranked appearances, round records, and era filters. |
| Playoff matchup/history by era | `heat_knicks_playoff_history`, `lakers_celtics_playoff_history`, `heat_knicks_playoff_series_record_wave4`, `lakers_celtics_by_decade`, `warriors_lakers_by_decade_wave4` | Exercises matchup phrasing, series vs game wording, and decade matchup copy. |
| Comparison | `jokic_embiid_recent_comparison`, `tatum_brown_last10_comparison_wave4`, `celtics_bucks_range_comparison`, `warriors_lakers_this_season_comparison_wave4`, `lebron_durant_comparison_wave4`, `lakers_celtics_h2h_record_wave4` | Covers player/team comparisons, recent windows, date ranges, season context, career/current comparison, and head-to-head record copy. |
| No-result and unsupported boundaries | `most_points_last_night`, `top_scorer_feb_14_2026_wave4`, `cooled_off_last_10`, `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_against_east_record_wave4`, `personal_foul_leaders_wave4` | Ensures no-match, date boundary, unsupported analysis, unsupported filters, and unavailable metrics get specific guidance. |

Expansion rule: after the first report, add cases only for result families with real findings or thin coverage. The 112 informational `frontend_hero_expected` cases are useful as the eventual candidate pool, not as the first hard test set.

## 6. Proposed pass/fail rubric

- Semantic pass: rendered UI includes the correct entity, primary record/count/value, requested condition or filter, season/window/context, and table metric label. No-result or unsupported output explains the actual boundary without implying support for unavailable filters.
- Semantic fail: rendered UI contradicts structured facts, uses the wrong entity, wrong record/count/value, wrong season/window, wrong metric label, wrong playoff vs regular-season framing, or hides a critical filter needed to understand the result.
- Exact text mismatch: only a failure for deliberately promoted stable fixtures. In the report phase, exact wording differences should be informational unless they change meaning.
- Polish issue: copy is awkward, repetitive, too generic, or visually weak but still factually correct and not misleading.
- Product decision: the UI exposes an unresolved product boundary, such as whether a metric/filter should be supported, whether a backend phrase should exist, or whether an outlier needs explicit surfacing.
- Visual/layout issue: text is semantically correct but wraps, truncates, overlaps, appears in the wrong hierarchy, or is not prominent enough. These should be reviewed through screenshots or manual ReviewPage batches, not exact text tests.

Concrete frontend-copy standards:

- Good: hero includes the requested entity and the core answer fact.
- Good: hero or nearby supporting copy includes critical filters such as last season, last 10, road/home, playoff teams, without player, position, round, or matchup.
- Good: table headers match the requested stat family and do not rename defensive/opponent metrics into the wrong direction.
- Good: unsupported/no-result guidance names the unavailable metric/filter or no-data boundary when the backend provides it.
- Bad: hero says "this season" when the query asked last season.
- Bad: hero implies regular-season data when the query requested playoff context, or the reverse.
- Bad: unsupported copy is generic when a precise unsupported filter exists.
- Bad: a top-performance or leaderboard table uses a wrong metric label even if the rows are correct.
- Bad: a verified outlier is made to look like a normal stable claim without any review marker in the QA report.

## 7. Recommended execution scope

- Exact goal: render a curated backend QA subset through the actual frontend components and generate a report of visible copy, table shape, chips, no-result guidance, and semantic review flags.
- Files likely to change in the next implementation stage: a new frontend extraction utility or Vitest report test, likely under `frontend/src/test/` or `tools/`; optional selected-case config under `qa/`; no production component changes unless findings are later fixed.
- New artifacts to create later: `qa/frontend_copy_corpus.yaml` or a selected case-id list, `outputs/frontend_copy_qa/<run_id>/frontend_copy_report.jsonl`, `outputs/frontend_copy_qa/<run_id>/frontend_copy_report.md`, and optionally `summary.json`.
- Tests to add later: after report review, promote only stable high-risk failures into hard tests in `ResultRenderer.test.tsx`, `UIComponents.test.tsx`, or table-contract tests. Do not snapshot full pages.
- Harness/report outputs: case id, query, backend route/status/reason, pattern shape, rendered hero text, envelope/context chips, result headings, table aria labels, column headers, selected top-row labels/values, no-result title/message/guidance, notes/caveats, source backend report run id, and review classification.
- Stop conditions: stop before changing backend behavior, corpus expectations, or production rendering; stop if extraction requires adding test-only props to production components; stop if exact text churn dominates semantic findings; stop after the first 40-60 cases and review findings by family before expanding.

Recommended stages:

1. Stage 1: preflight decision doc only. This return package is that artifact.
2. Stage 2: build a small rendered frontend-copy harness using the existing Vitest/jsdom setup or a Vitest-backed Node/TS report runner.
3. Stage 3: start with 40-60 selected cases from `qa/raw_query_answer_corpus.yaml` and `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl`.
4. Stage 4: generate `frontend_copy_report.jsonl`, `frontend_copy_report.md`, and optional summary JSON. Do not add screenshots in the first pass unless text extraction misses a major class of issues.
5. Stage 5: review findings by family: hero fact mismatch, filter/chip mismatch, table label mismatch, no-result guidance mismatch, visual/copy polish, and product decision.
6. Stage 6: promote only stable high-risk semantic failures into hard frontend tests.

## 8. Risks / open decisions

- Extraction risks: React fragments can split meaningful sentences across nodes; table, card, and chip text may duplicate the same fact; DOM order may not match visual order; without stable semantic selectors, extractors can become coupled to incidental markup.
- Snapshot brittleness risks: full-page text snapshots will fail on harmless copy polish. Exact assertions should be reserved for stable high-risk facts and labels.
- UI/rendering risks: jsdom cannot validate wrapping, truncation, overlap, hierarchy, color, screenshots, or responsive layout. Those need ReviewPage or Playwright/manual visual review later.
- Data synchronization risks: `report.jsonl` is generated output and can become stale relative to the corpus or engine. Frontend-copy reports should record the source backend QA run id and should not silently mix payloads from different runs.
- Corpus scope risk: testing all 195 cases immediately may generate noise and discourage targeted fixes. The first pass should optimize for high-risk family coverage.
- Backend phrase risk: `GameLogResult` renders backend `answer_phrase` and `count_phrase` when present. Frontend QA can verify display and context, but phrase-generation quality may remain a backend/product issue.
- ReviewPage risk: the current review route consumes parser examples through `/api/dev/fixtures`, not the backend QA corpus. It is a good visual tool, but it is not yet the corpus-backed frontend-copy QA layer.

Open decisions for the next implementation stage:

- Whether the selected frontend-copy corpus should live in a new `qa/frontend_copy_corpus.yaml` or as a section/list inside a harness config.
- Whether the backend QA harness should add an exact `api_payload` field, or whether the frontend harness should keep rehydrating from the existing JSONL fields.
- Which fields become hard failures in the first automated run: recommended hard candidates are route/status, hero entity/value/context, applied filter chips, table column headers, and no-result reason/message family.
- Whether verified outlier status should be surfaced in the rendered UI or only in the QA report. This is a product decision, not a frontend-only test decision.

## 9. Validation performed

No production code, frontend rendering, tests, corpus expectations, or backend behavior were changed.

Files inspected:

- `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_7A_P2_BOUNDARY_ROUTING_CLEANUP_RETURN_PACKAGE.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `qa/raw_query_answer_corpus.yaml`
- `tools/raw_query_answer_qa.py`
- `outputs/raw_query_answer_qa/20260514T125056Z/report.md`
- `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl`
- `docs/reference/result_contracts/core_result_table_contracts.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/results/resultShapes.ts`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/FallbackTableResult.tsx`
- `frontend/src/components/results/primitives/ResultHero.tsx`
- `frontend/src/components/results/primitives/ResultTable.tsx`
- `frontend/src/components/results/primitives/ResultShell.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/noResultDisplayUtils.ts`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/test/ResultRenderer.test.tsx`
- `frontend/src/test/resultShapes.test.ts`
- `frontend/src/test/wave1TableContracts.test.tsx`
- `frontend/src/test/wave2TableContracts.test.tsx`
- `frontend/src/test/UIComponents.test.tsx`
- `frontend/package.json`
- `frontend/vite.config.ts`
- `src/nbatools/api_handlers.py`

Commands and probes run:

```bash
git status --short
sed -n '1,240p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_7A_P2_BOUNDARY_ROUTING_CLEANUP_RETURN_PACKAGE.md
sed -n '1,240p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,520p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '1,220p' outputs/raw_query_answer_qa/20260514T125056Z/report.md
sed -n '1,80p' outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl
sed -n '1,260p' tools/raw_query_answer_qa.py
rg --files frontend/src/components/results
sed -n '1,260p' docs/reference/result_contracts/core_result_table_contracts.md
sed -n '1,260p' docs/reference/query_catalog.md
sed -n '1,220p' docs/reference/query_guide.md
sed -n '1,260p' frontend/src/components/results/ResultRenderer.tsx
sed -n '1,260p' frontend/src/components/results/resultShapes.ts
sed -n '1,260p' frontend/src/components/results/config/routeToPattern.ts
sed -n '1,220p' frontend/src/components/results/primitives/ResultHero.tsx
sed -n '1,260p' frontend/src/components/results/primitives/ResultTable.tsx
sed -n '1,220p' frontend/src/components/results/primitives/ResultShell.tsx
sed -n '1,1120p' frontend/src/components/results/patterns/EntitySummaryResult.tsx
sed -n '1,1280p' frontend/src/components/results/patterns/RecordResult.tsx
sed -n '1,1220p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '1,760p' frontend/src/components/results/patterns/TopPerformancesResult.tsx
sed -n '1,920p' frontend/src/components/results/patterns/ComparisonResult.tsx
sed -n '1,980p' frontend/src/components/results/patterns/PlayoffHistoryResult.tsx
sed -n '1,1250p' frontend/src/components/results/patterns/GameLogResult.tsx
sed -n '1,760p' frontend/src/components/results/patterns/SplitResult.tsx
sed -n '1,760p' frontend/src/components/results/patterns/StreakResult.tsx
sed -n '1,760p' frontend/src/components/results/patterns/RollingStretchResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/FallbackTableResult.tsx
sed -n '1,360p' frontend/src/components/NoResultDisplay.tsx
sed -n '1,760p' frontend/src/components/noResultDisplayUtils.ts
sed -n '1,980p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,860p' frontend/src/ReviewPage.tsx
sed -n '1,300p' frontend/src/api/types.ts
sed -n '1,220p' frontend/src/api/client.ts
sed -n '1,120p' src/nbatools/api_handlers.py
sed -n '1,3960p' frontend/src/test/ResultRenderer.test.tsx
sed -n '1,760p' frontend/src/test/resultShapes.test.ts
sed -n '1,860p' frontend/src/test/wave1TableContracts.test.tsx
sed -n '1,860p' frontend/src/test/wave2TableContracts.test.tsx
sed -n '50,370p' frontend/src/test/UIComponents.test.tsx
sed -n '1,260p' frontend/package.json
sed -n '1,260p' frontend/vite.config.ts
rg -n "applied_filters|Applied|filter" frontend/src/components frontend/src/ReviewPage.tsx
rg -n "fixtures|dev/fixtures|fetchDevFixtures|ReviewPage" src frontend/src
rg -n "<ResultHero|function .*Sentence|function .*Headline|function .*Columns|ariaLabel=|<ResultTable|<RawDetailToggle|<Badge" frontend/src/components/results/patterns frontend/src/components/ResultEnvelope.tsx frontend/src/components/NoResultDisplay.tsx
rg -n "getByText\\(|getByRole\\(\"columnheader|columnheader|NoResultDisplay|ResultRenderer|classifyResultShape" frontend/src/test
rg -n "answer_text_policy: frontend_hero_expected|answer_text_policy: no_answer_text_expected|answer_text_policy: requires_backend_answer_text|status: verified_outlier|category:" qa/raw_query_answer_corpus.yaml
wc -l qa/raw_query_answer_corpus.yaml outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl frontend/src/test/ResultRenderer.test.tsx frontend/src/components/results/config/routeToPattern.ts
```

No test suite was run because this was a documentation-only preflight artifact with no production, test, or corpus changes.
