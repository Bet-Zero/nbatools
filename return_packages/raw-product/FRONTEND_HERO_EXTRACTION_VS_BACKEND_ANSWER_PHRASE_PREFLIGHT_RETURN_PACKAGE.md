# Frontend Hero Extraction vs Backend Answer Phrase Preflight Return Package

## 1. Executive summary

- AQ-003 classification: expected architecture limitation in the QA harness, plus a useful API/product enrichment opportunity. It is not a production rendering bug.
- Recommended path: hybrid staged path. First reclassify `missing_backend_answer_text` so frontend-only heroes are informational, then add targeted backend canonical answer phrases/facts for high-value record routes.
- Should frontend extraction be built now? no.
- Should backend answer phrases be enriched now? yes, but only targeted and after the harness flag is made policy-aware.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

Primary answer: answer QA does not need exact frontend-rendered hero text right now. The frontend is intentionally responsible for final display copy across most result patterns. Backend metadata should become the source of truth for canonical answer facts or phrase candidates where API/CLI consumers need a direct answer, especially record-style summary routes. Exact frontend rendered-copy extraction should be deferred until visual/copy QA is a product goal.

Latest full QA run checked: `outputs/raw_query_answer_qa/20260513T040809Z/report.md`. It has 80 cases, all expectations passing, and 22 `missing_backend_answer_text` flags. The report already tags those flags with `frontend_hero_extraction`.

## 2. Missing answer text inventory

Grouped inventory:

| Route | Shape hint | Frontend result pattern | Categories | Cases |
|---|---|---|---|---:|
| `player_game_summary` | `entity_summary` | `EntitySummaryResult` plus optional `GameLogResult` | `record_when_player_condition`, `player_summary` | 7 |
| `team_record` | `team_record` | `RecordResult` plus optional `GameLogResult` | `team_record`, `record_when_team_condition`, `without_player_condition` | 11 |
| `playoff_history` | `playoff_history` | `PlayoffHistoryResult` history mode | `playoff_history` | 1 |
| `playoff_appearances` | `leaderboard_table` | `PlayoffHistoryResult` appearances mode or `LeaderboardResult` | `playoff_history` | 2 |
| `player_split_summary` | `entity_summary` | `SplitResult` | `split` | 1 |

Notes on shape hints:

- `lakers_finals_appearances` is a single-team `playoff_appearances` result with `summary` and `by_season`, so the frontend uses `PlayoffHistoryResult` appearances mode. The harness shape hint is `leaderboard_table` because its backend approximation treats `playoff_appearances` as a leaderboard route before checking sections.
- `jokic_home_away_split` is rendered by `SplitResult`; the harness shape hint is `entity_summary` because `player_split_summary` is not modeled precisely by the backend approximation.

| Case ID | Route | Shape hint | Category | Frontend hero likely? | Backend phrase feasible? | Notes |
|---|---|---|---|---|---|---|
| `record_when_jokic_triple_double` | `player_game_summary` | `entity_summary` | `record_when_player_condition` | yes | High | Pattern: `EntitySummaryResult` plus `GameLogResult`. Summary row has `24-10` in 34 games; metadata has team/player/event. Good candidate for canonical record-when phrase. |
| `celtics_record_playoff_teams` | `team_record` | `team_record` | `team_record` | yes | High | Pattern: `RecordResult`. Summary row has `33-21` in 54 games; metadata has opponent-quality filter. Good `team_record` phrase candidate. |
| `celtics_record_teams_made_playoffs` | `team_record` | `team_record` | `team_record` | yes | High | Same as playoff-teams variant. Phrase should use canonical opponent-quality filter label, not infer playoff competition. |
| `celtics_playoff_record` | `team_record` | `team_record` | `team_record` | yes | High | Summary row has `6-5`, 11 games, `season_type=Playoffs`. Easy canonical record phrase. |
| `lakers_playoff_history` | `playoff_history` | `playoff_history` | `playoff_history` | yes | Medium | Pattern: `PlayoffHistoryResult`. Summary row has W-L, games, range, and appearances fields. Feasible, but frontend copy includes richer postseason wording. Lower priority than record routes. |
| `jokic_season_summary` | `player_game_summary` | `entity_summary` | `player_summary` | yes | Medium | Pattern: `EntitySummaryResult` plus `GameLogResult`. Backend can state PTS/REB/AST over games, but this duplicates frontend average-copy logic. Not first-wave. |
| `tatum_recent_form` | `player_game_summary` | `entity_summary` | `player_summary` | yes | Medium | Recent-form context comes from query/window metadata and summary rows. Feasible but not record-critical. |
| `tatum_good_teams` | `player_game_summary` | `entity_summary` | `player_summary` | yes | Medium | Needs opponent-quality filter wording. Feasible, but frontend already handles this display from applied filters. |
| `celtics_overall_record` | `team_record` | `team_record` | `team_record` | yes | High | Simple record phrase from summary row and season metadata. High-value API answer. |
| `lakers_good_teams_record` | `team_record` | `team_record` | `team_record` | yes | High | Same as opponent-quality team record. High-value because answer is W-L. |
| `lakers_held_opponents_under_100_record` | `team_record` | `team_record` | `record_when_team_condition` | yes | High | Summary row has `7-0`; metadata has `stat=opponent_pts`, `max_value=99.9999`. Good threshold phrase candidate. |
| `celtics_scored_over_120_record` | `team_record` | `team_record` | `record_when_team_condition` | yes | High | Summary row has `23-0`; metadata has `stat=pts`, `min_value=120.0001`. Good threshold phrase candidate. |
| `thunder_sga_30_record` | `player_game_summary` | `entity_summary` | `record_when_player_condition` | yes | High | Pattern: record-when branch in `EntitySummaryResult`. Metadata has team/player/stat/min threshold. High-value canonical W-L answer. |
| `warriors_curry_6_threes_record` | `player_game_summary` | `entity_summary` | `record_when_player_condition` | yes | High | Same record-when player condition, with `stat=fg3m`. High-value. |
| `denver_jokic_10_assists_record` | `player_game_summary` | `entity_summary` | `record_when_player_condition` | yes | High | Same record-when player condition, with `stat=ast`. High-value. |
| `suns_without_booker_shorthand` | `team_record` | `team_record` | `without_player_condition` | yes | High | Pattern: `RecordResult` plus `GameLogResult`. Backend already has analogous `game_summary` answer phrase for `suns_without_booker`; `team_record` should likely match that canonical answer family. |
| `bucks_without_giannis` | `team_record` | `team_record` | `without_player_condition` | yes | High | Same without-player team record. High-value because users ask for a direct W-L answer. |
| `knicks_without_brunson` | `team_record` | `team_record` | `without_player_condition` | yes | High | Same without-player team record. |
| `lakers_without_lebron` | `team_record` | `team_record` | `without_player_condition` | yes | High | Same without-player team record. |
| `lakers_finals_appearances` | `playoff_appearances` | `leaderboard_table` | `playoff_history` | yes | Medium | Frontend pattern is `PlayoffHistoryResult` appearances mode, not leaderboard. Backend can phrase appearances count, round, and range. Lower priority than record routes. |
| `most_finals_appearances_since_1980` | `playoff_appearances` | `leaderboard_table` | `playoff_history` | yes | Medium | Frontend pattern is `LeaderboardResult`. Backend can phrase top team and count, but generic leaderboard hero already does this from rows. |
| `jokic_home_away_split` | `player_split_summary` | `entity_summary` | `split` | yes | Low/Medium | Frontend pattern is `SplitResult`. Hero is mostly contextual; the real answer is the split table and edge chips. Avoid first-wave backend wording. |

## 3. Frontend hero/text generation inventory

| Component/file | Routes/patterns | Hero source | Centralized? | Extractable? | Notes |
|---|---|---|---|---|---|
| `frontend/src/components/results/primitives/ResultHero.tsx` | All hero-using patterns | Receives a `sentence` ReactNode prop | Primitive only | Not by itself | Central display shell only. It does not build answer copy. |
| `frontend/src/components/results/ResultRenderer.tsx` | All frontend result routes | Chooses pattern stack through `routeToPattern` | Route dispatch centralized | Medium via rendered React | It can be rendered in jsdom/SSR, but it does not expose answer text helpers. |
| `frontend/src/components/results/config/routeToPattern.ts` | All route to pattern mapping | No answer text | Yes for mapping | Easy | Determines whether a route gets entity, record, split, leaderboard, playoff, game-log, etc. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | `player_game_summary`, `lineup_summary` | Builds summary hero from `summary[0]`, metadata, applied filters, and query text | No | Hard without rendering or refactor | Includes a special record-when-player branch that prioritizes team W-L over player averages when query text asks for record. |
| `frontend/src/components/results/patterns/RecordResult.tsx` | `team_record`, `record_by_decade`, `record_by_decade_leaderboard`, `matchup_by_decade` | Builds W-L, context, opponent group, without-player, and win-rate sentences from summary rows and metadata | No | Hard without rendering or refactor | This is the largest match for AQ-003 flagged cases. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | `playoff_history`, `playoff_appearances`, `playoff_round_record`, `playoff_matchup_history` | Builds postseason sentences from summary/leaderboard rows and metadata | No | Hard without rendering or refactor | Some sentence builders return React fragments with highlighted spans, not plain strings. |
| `frontend/src/components/results/patterns/SplitResult.tsx` | `player_split_summary`, `team_split_summary`, `player_on_off` | Builds contextual split sentence from entity, split type, season metadata | No | Medium/Hard | Real user answer is often in table and edge chips, not just the hero sentence. |
| `frontend/src/components/results/patterns/ComparisonResult.tsx` | `player_compare`, `team_compare`, `team_matchup_record` | Builds hero from summary rows, comparison metric rows, and head-to-head state | No | Hard | Branching copy depends on recent form, wins, and edge calculations. |
| `frontend/src/components/results/patterns/GameLogResult.tsx` | `game_summary`, `player_game_finder`, `game_finder`, stacked logs | Uses `metadata.count_phrase` first, then `metadata.answer_phrase`; otherwise no hero and may show a summary strip | Partially | Easy for backend phrases | This is the main frontend consumer of backend answer metadata. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | `season_leaders`, `season_team_leaders`, `team_record_leaderboard`, occurrence leaders, `playoff_appearances` leaderboard mode, `lineup_leaderboard` | Uses `metadata.count_phrase` when `primary_count` exists; otherwise builds top-row hero from leaderboard rows | No | Medium | Backend count phrases are honored. Ordinary leaderboard hero is frontend-built. |
| `frontend/src/components/results/patterns/TopPerformancesResult.tsx` | `top_player_games`, `top_team_games` | Builds hero from first leaderboard row, selected metric, scope, and game context | No | Medium/Hard | Useful for visual copy QA, but not relevant to current missing-backend flags. |
| `frontend/src/components/results/patterns/StreakResult.tsx` | `player_streak_finder`, `team_streak_finder` | Builds streak hero from top row and threshold metadata | No | Medium/Hard | Frontend-only hero today. |
| `frontend/src/components/results/patterns/RollingStretchResult.tsx` | `player_stretch_leaderboard` | Builds league or named-player stretch hero from top row and metric metadata | No | Medium/Hard | Frontend-only hero today. |
| `frontend/src/components/results/patterns/FallbackTableResult.tsx` | Unmapped fallback | Table sections only | N/A | N/A | No canonical hero behavior. |

Conclusion: hero text is spread across pattern components, with only the visual hero card centralized. Exact extraction without browser rendering is not currently easy or safe because most sentence builders are non-exported functions inside TSX files, some return ReactNode fragments, and several depend on local formatter/helper logic plus route pattern selection.

## 4. Backend answer phrase inventory

| Route | Current phrase support | Feasible enrichment? | Needed fields | Notes |
|---|---|---|---|---|
| Count-intent routes generally | `query_service._build_count_phrase()` sets `metadata.count_phrase` when count intent is converted to `CountResult` | Existing | `primary_count`, parsed entity/stat/threshold metadata, optional games | Latest report shows backend phrases for `player_game_finder`, `game_finder`, and occurrence count cases. |
| `game_summary` | `query_service._add_game_summary_answer_metadata()` sets `metadata.answer_phrase`, `primary_count`, `record`, `record_wins`, `record_losses` | Existing, should be kept | `summary[0]`: games, wins, losses, pts_avg; metadata team and `without_player` | This is the only current backend `answer_phrase` route. It is used by `GameLogResult`. |
| `team_record` | None | High | `summary[0]`: team, games, wins, losses, win_pct, pts_avg; metadata team, season, season_type, applied filters, `without_player`, stat thresholds, opponent quality | Highest-value target. W-L answer is direct and useful to API/CLI. |
| `player_game_summary` record-when variants | None | High | `summary[0]`: games, wins, losses, win_pct; metadata team, player, stat threshold or `occurrence_event` | High-value target when query asks for team record conditioned on player performance. |
| `player_game_summary` ordinary player summaries | None | Medium | `summary[0]`: games, PTS/REB/AST averages; metadata player, filters, season/window | Feasible, but duplicates `EntitySummaryResult` average wording. Lower priority. |
| `playoff_history` | None | Medium | `summary[0]`: team, games, wins, losses, seasons/appearances, range, titles/finals if present | Feasible simple phrase, but frontend has richer postseason copy. |
| `playoff_appearances` | None | Medium | Single-team: summary appearances/round/range. Leaderboard: first row team/appearances/round/range. | Useful later, especially single-team appearances. Not first-wave unless product wants postseason answer text. |
| `player_split_summary`, `team_split_summary`, `player_on_off` | None | Low/Medium | summary row, split comparison rows, split type, edge facts | Avoid first-wave. The answer is a comparison table and edge chips rather than a single canonical phrase. |
| `season_leaders`, `season_team_leaders`, `team_record_leaderboard` | Count phrases only when count-intent converted | Low/Medium | first leaderboard row and selected metric | Frontend already builds top-row hero. Backend phrase could help API, but not part of AQ-003 flagged family except `playoff_appearances`. |
| `top_player_games`, `top_team_games` | None | Low | first leaderboard row, selected metric, game context | Not needed for current AQ-003. Latest top-performance issues are closed except verified outlier reporting. |
| `player_streak_finder`, `team_streak_finder`, `player_stretch_leaderboard`, comparisons | None | Low/Medium | top row, threshold/window/context, comparison edge logic | Defer. Frontend has pattern-specific copy and tests. |

Existing convention:

- Backend phrase generation currently lives in `src/nbatools/query_service.py`, not in command modules.
- The only phrase helpers are `_build_count_phrase()` and `_add_game_summary_answer_metadata()`.
- Command modules return structured results; they do not currently own user-facing answer phrases.
- `QueryResult.to_dict()` replaces the result object's metadata with query-service metadata, so future phrase enrichment should be added in query-service metadata construction or a dedicated helper called from query service.

Impact assessment:

- Targeted backend phrases improve API/CLI quality because consumers can show a direct canonical answer without reproducing React logic.
- Broad backend phrase parity would duplicate frontend component logic and increase drift risk.
- Backend should not try to be the exact visual hero source of truth. It should provide canonical answer facts and optional plain answer phrases for direct-answer routes.

## 5. Option comparison

| Option | Value for QA | Complexity | Divergence risk | Frontend risk | Backend/API value | Recommendation |
|---|---|---|---|---|---|---|
| Option A - Frontend rendered-answer extraction harness | High for exact visual copy QA | High | Low if it renders the same components, Medium if fixture plumbing drifts | Medium | Low | Defer. It answers a different question: rendered copy parity, not backend answer trust. |
| Option B - Extract pure frontend hero builders | High | High | Low/Medium after refactor, High during migration | High | Low | Defer. This touches frontend architecture only to serve QA extraction and risks churn in stable rendering components. |
| Option C - Backend `answer_phrase` enrichment | Medium/High for direct-answer routes | Medium | Medium if frontend copy remains separate | Low | High | Do targeted enrichment for record-style summaries. Do not chase exact frontend wording. |
| Option D - Hybrid canonical facts/phrases plus optional rendered QA later | High | Medium | Low/Medium | Low now, Medium later if rendered harness is added | High | Recommended. Reclassify harness first, then enrich high-value backend answer facts/phrases, then add frontend extraction only for visual-copy regressions. |

## 6. Recommended execution scope

- Exact goal: make AQ-003 policy-aware and then add canonical backend direct-answer metadata for the highest-value record-style summaries without trying to mirror every frontend hero.
- Files likely to change:
  - `tools/raw_query_answer_qa.py`
  - `qa/raw_query_answer_corpus.yaml`
  - `tests/test_raw_query_answer_qa.py`
  - `src/nbatools/query_service.py`
  - possibly a new helper under `src/nbatools/commands/` or `src/nbatools/` if phrase/fact builders grow beyond a few functions
  - `tests/test_query_service.py` or focused data-backed query tests for enriched phrases
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
  - `docs/reference/query_catalog.md` only if shipped user-visible query contract changes are claimed
- Harness changes:
  - Replace unconditional P0/P1 summary `missing_backend_answer_text` suspicion with an explicit corpus policy.
  - Recommended policy field: `answer_text_policy: requires_backend_answer_text | frontend_hero_expected | no_answer_text_expected`.
  - Treat `frontend_hero_expected` as informational, not suspicious.
  - Keep a flag when `requires_backend_answer_text` is missing or when a route known to be backend-answer-backed regresses.
- Corpus/findings changes:
  - Mark the current 22 cases as `frontend_hero_expected` unless targeted backend phrase work is part of the same change.
  - For `game_summary` without-player and any newly enriched `team_record` / record-when cases, use `requires_backend_answer_text`.
  - Mark AQ-003 as expected/deferred for rendered frontend extraction and partially addressed once harness policy lands.
- Tests to add:
  - Harness unit tests in `tests/test_raw_query_answer_qa.py` for all three answer text policies.
  - Query-service tests for targeted `answer_phrase` / canonical facts on `team_record`, player record-when summaries, and without-player records.
  - Existing frontend tests remain sufficient unless rendered extraction is implemented.
- Stop conditions:
  - Stop before importing React components into the Python harness.
  - Stop before requiring exact frontend hero text as a corpus assertion.
  - Stop backend phrase enrichment if it requires reimplementing complex frontend-only edge logic for splits, comparisons, streaks, or rolling windows.
  - Stop if phrase generation begins to alter result sections or route behavior.

Recommended route priority for backend enrichment:

1. `team_record` for overall records, opponent-quality records, playoff records, threshold record-when, and without-player records.
2. `player_game_summary` only when the query is a record-when-player-condition answer and the summary row has W-L fields.
3. `game_summary` keep existing support and consider sharing the record phrase helper so without-player answers are consistent.
4. `playoff_appearances` single-team mode if postseason direct answers become a near-term priority.
5. `playoff_history` simple summary phrase after records are done.

Do not prioritize ordinary player summaries or split summaries in the first backend phrase wave.

## 7. Recommended AQ-003 policy

- Is it suspicious, informational, or expected? Expected/informational for frontend-rendered hero routes. Suspicious only when the corpus explicitly requires backend answer text or when a backend-answer-backed route regresses.
- How should reports display it?
  - Rename or supplement the current flag with an informational status such as `frontend_hero_only_answer_text`.
  - Keep `missing_backend_answer_text` only for `answer_text_policy=requires_backend_answer_text`.
  - Display the reason as a limitation, not an answer-trust finding, when frontend hero coverage is expected.
- Which cases should still fail or flag?
  - Cases with `requires_backend_answer_text` and no backend phrase.
  - Cases where the backend phrase exists but contradicts hard assertions in summary/count rows.
  - Count/finder cases where the route convention is to expose `count_phrase`.
  - `game_summary` direct-answer cases where existing `answer_phrase` disappears.
- What should be deferred?
  - Exact frontend hero snapshots.
  - Rendered React extraction for the full corpus.
  - Backend phrase parity for complex visual patterns: splits, comparisons, streaks, rolling stretches, top performances.

Corpus treatment recommendation:

- Yes, corpus cases should distinguish:
  - `requires_backend_answer_text`
  - `frontend_hero_expected`
  - `no_answer_text_expected`
- Prefer a single enum over three independent booleans to avoid contradictory states.
- Current 22 AQ-003 cases should initially be `frontend_hero_expected`.
- Promote only targeted enriched routes to `requires_backend_answer_text` after implementation and tests.

Findings treatment recommendation:

- Keep AQ-003 open as an expected limitation until harness policy is implemented.
- After harness policy lands, mark AQ-003 as partially addressed for QA classification.
- Keep frontend rendered-answer extraction deferred unless visual copy regressions become the explicit goal.

## 8. Risks / open decisions

- Frontend extraction risks:
  - Requires Node/Vitest/jsdom or SSR plumbing around `ResultRenderer`.
  - Several sentence builders are private TSX functions and some return ReactNode fragments.
  - Full-corpus rendered extraction would add cross-language moving parts to a currently simple Python harness.
  - Exact copy snapshots can become noisy and brittle if UI wording changes without data behavior changing.
- Backend phrase risks:
  - Broad phrase parity duplicates frontend logic and can drift.
  - Phrase wording may look like a product commitment if it is too polished or too broad.
  - Query-service phrase helpers can become a second presentation layer if not scoped to canonical facts.
- Product wording risks:
  - `answer_phrase` should be treated as a canonical plain answer, not necessarily the exact hero copy.
  - For split/comparison routes, a single sentence can understate the answer because the table/edge chips carry the detail.
- Future work:
  - Consider structured `answer_facts` for records: `{entity, record, wins, losses, games, win_pct, condition, context}`.
  - Add rendered frontend extraction only for a small copy-regression set, not the entire raw QA corpus by default.
  - If backend phrases are added, document them as API metadata fields and keep tests near query-service payload behavior.

## 9. Validation performed

Commands/probes run:

- `git status --short`
  - Summary: clean before package creation.
- `rg -n "missing_backend_answer_text|Case ID|Suspicious|AQ-003" outputs/raw_query_answer_qa/20260513T040809Z/report.md`
  - Summary: report shows 22 suspicious flag cases, all `missing_backend_answer_text`, all suggested tag `frontend_hero_extraction`.
- `node -e '...' outputs/raw_query_answer_qa/20260513T040809Z/report.jsonl`
  - Summary: extracted all 22 flagged cases with route, shape hint, category, query, sections, and phrase fields.
- `node -e '...' outputs/raw_query_answer_qa/20260513T040809Z/report.jsonl`
  - Summary: grouped flagged cases by route, shape hint, and category.
- `node -e '...' outputs/raw_query_answer_qa/20260513T040809Z/report.jsonl`
  - Summary: extracted summary-row and metadata fields for the 22 flagged cases.
- `node -e '...' outputs/raw_query_answer_qa/20260513T040809Z/report.jsonl`
  - Summary: found only 5 cases with backend answer text in the current report: count phrases for count/finder-style cases and one `game_summary` answer phrase.
- `rg -n "AQ-003|missing_backend_answer_text|frontend_hero|answer_phrase|count_phrase|answer text|hero" docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md docs/reference/result_contracts/core_result_table_contracts.md docs/reference/query_catalog.md`
  - Summary: planning docs already classify AQ-003 as deferred/expected and state that frontend hero extraction is deferred.
- `sed -n '1,220p' tools/raw_query_answer_qa.py` and `sed -n '748,785p' tools/raw_query_answer_qa.py`
  - Summary: harness uses only backend `metadata.answer_phrase` / `metadata.count_phrase`; missing answer text is flagged for P0/P1 ok summary-style routes.
- `rg -n "answer_phrase|count_phrase|ResultHero|sentence=|heroSentence|Sentence(" frontend/src/components/results frontend/src/components`
  - Summary: hero generation is spread across pattern components. Only `GameLogResult` and `LeaderboardResult` consume backend phrases.
- `sed` probes on:
  - `frontend/src/components/results/ResultRenderer.tsx`
  - `frontend/src/components/results/config/routeToPattern.ts`
  - `frontend/src/components/results/resultShapes.ts`
  - `frontend/src/components/results/primitives/ResultHero.tsx`
  - `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
  - `frontend/src/components/results/patterns/RecordResult.tsx`
  - `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
  - `frontend/src/components/results/patterns/SplitResult.tsx`
  - `frontend/src/components/results/patterns/GameLogResult.tsx`
  - `frontend/src/components/results/patterns/LeaderboardResult.tsx`
  - `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
  - `frontend/src/components/results/patterns/ComparisonResult.tsx`
  - `frontend/src/components/results/patterns/StreakResult.tsx`
  - Summary: confirmed route pattern mapping, hero sources, and backend phrase consumption points.
- `rg -n "answer_phrase|count_phrase|primary_count" src/nbatools -g'*.py'`
  - Summary: backend phrase support exists only in `query_service.py`.
- `sed` probes on:
  - `src/nbatools/query_service.py`
  - `src/nbatools/commands/team_record.py`
  - `src/nbatools/commands/player_game_summary.py`
  - `src/nbatools/commands/game_summary.py`
  - `src/nbatools/commands/playoff_history.py`
  - `src/nbatools/commands/structured_results.py`
  - Summary: command modules return structured rows; phrase metadata is query-service-owned today.
- `rg -n "team_record|player_game_summary|playoff_history|playoff_appearances|player_split_summary|record when|without|summary" docs/reference/query_catalog.md`
  - Summary: query catalog confirms current shipped summary, record, split, playoff, without-player, opponent-quality, and threshold query surfaces.

No production code, tests, frontend rendering, or corpus expectations were changed during this preflight. No test suite was run because the requested output was research plus a return package only.
