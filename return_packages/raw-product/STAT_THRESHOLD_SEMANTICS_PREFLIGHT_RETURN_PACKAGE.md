# Stat / Threshold Semantics Preflight Return Package

## 1. Executive summary

- Main root-cause families: defensive/opponent-points alias gaps, percentage threshold parsing/normalization gaps, and inconsistent compound-threshold representation across finder/count routes.
- Which cases are true bugs: `knicks_allowed_under_110_record`, `fewest_points_allowed_team_leader`, `boston_tatum_under_40_fg_record_missing_filter`, `celtics_120_15_threes_count_missing_filter`, and `jokic_30_points_10_assists_finder_misparsed`.
- Which cases are product-boundary decisions: broad shorthand families such as `25/10/10`, `30-10 games`, and arbitrary compact multi-stat forms should remain scoped until a tested condition-list model covers them. The five target cases are inside or adjacent to documented support and should not be silently treated as unsupported.
- Recommended next execution: Option B, split into PR-sized waves. First fix scalar stat/threshold semantics for defensive points allowed and percentages. Then fix compound condition representation/count conversion/finder parsing as a dedicated wave.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `knicks_allowed_under_110_record` | `What is the Knicks record when they allow fewer than 110 points?` | `team_record` / `ok` | Parses `stat=pts`, `max_value=109.9999`; applied filter is `pts max`; summary is Knicks 8-18 over 26 games, which is their record when scoring under 110. | Parse and execute `stat=opponent_pts`, `max_value=109.9999`; current data gives Knicks 32-3 over 35 games when opponents score under 110. | `extract_opponent_points_allowed_conditions()` handles `allowed under N` and `gave up fewer than N`, but not `allow fewer than N`; the generic threshold parser captures `fewer than 110 points` as team `pts`. |
| `fewest_points_allowed_team_leader` | `Which team has allowed the fewest points per game this season?` | `season_team_leaders` / `ok` | Routes as `stat=pts`, `ascending=True`; top row is Brooklyn because it ranks lowest team scoring, not opponent scoring. | Rank `opponent_pts_per_game` ascending; current data-derived top row is Boston at 107.159 opponent PPG. | Team leaderboard aliases lack points-allowed terms, and `season_team_leaders` has no `opponent_pts`/`opponent_pts_per_game` stat even though team game logs can derive it. |
| `boston_tatum_under_40_fg_record_missing_filter` | `What's Boston's record when Jayson Tatum shoots under 40%?` | `player_game_summary` / `ok` | No threshold parsed, no applied filters; returns all 16 Tatum/Boston games in current data, 13-3. | Infer `fg_pct max < 0.40`; current structured probe with `max_value=0.3999` returns 6 games, 4-2. | The parser does not infer FG% from `shoots under N%`; percent-valued thresholds are not normalized. A related probe, `FG% under 40%`, parsed `fg_pct max=39.9999`, which executes as effectively unfiltered against 0.xx data. |
| `celtics_120_15_threes_count_missing_filter` | `how many Celtics games with 120+ points and 15+ threes since 2022` | `team_occurrence_leaders` / `ok` as `CountResult` | Parse has `route_kwargs.conditions=[pts>=120, fg3m>=15]`, but also keeps `extra_conditions=[fg3m>=15]`. Execution first builds the correct compound leaderboard, then post-filters the aggregate row on missing `fg3m`, becomes `NoResult`, and count conversion returns `0`. Applied filters and count phrase expose only `pts min` plus season. | Return the compound count from the occurrence leader row. Direct structured `team_occurrence_leaders` with the same conditions returns 125 Celtics games over 2022-23 to 2025-26. Applied filters should expose both thresholds. | Compound occurrence routes consume `conditions`, but generic threshold parsing also leaves the second condition in `extra_conditions`; `_apply_extra_conditions_to_result()` is unsafe on aggregate occurrence leaderboards. Metadata also ignores `route_kwargs.conditions`. |
| `jokic_30_points_10_assists_finder_misparsed` | `Jokic games with 30 points and 10 assists` | `player_game_finder` / `no_result` | `compound_occurrence_conditions` detects `pts>=30` and `ast>=10`, but finder routing ignores it. `detect_stat()` leaves `stat=ast`, `occurrence_event` supplies `min_value=30`, so execution filters `ast>=30` and returns no-match. | Finder should preserve `pts>=30` and `ast>=10`; a direct execution probe with primary `pts>=30` plus extra `ast>=10` returns matching Jokic rows. | Compact bare thresholds are detected only by occurrence parsing, not by `threshold_conditions`; the compound occurrence route is count/leaderboard-oriented and does not feed finder/summary routes. |

## 3. Nearby working cases

| Case ID / Query | Behavior | Why it matters |
|---|---|---|
| `lakers_held_opponents_under_100_record` | `team_record` / `ok`; `stat=opponent_pts`, `max=99.9999`; summary is Lakers 7-0 over 7 games. | Confirms opponent-points execution and record summarization already work when the parser chooses `opponent_pts`. |
| `lakers_held_opponents_under_100_count` | `game_finder` count/finder; `OPP PTS max`; count 7 and finder rows include `opponent_pts`. | Confirms team finder/count can derive and expose opponent points. |
| `celtics_scored_over_120_record` | `team_record` / `ok`; `pts min=120.0001`; summary is Celtics 23-0 over 23 games. | Confirms single team scoring threshold records work. |
| `Curry 5+ threes this season` | `player_game_finder` / `ok`; `fg3m min=5.0`; 17 finder rows in current data. | Confirms compact single-stat player thresholds work. |
| `players_40_point_count` | `player_occurrence_leaders` / `ok`; `pts min=40.0`; count 47. | Confirms single-stat occurrence counts work. |
| `players_10_assist_count` | `player_occurrence_leaders` / `ok`; `ast min=10.0`; count 114. | Confirms single-stat assist threshold binding works outside compact multi-stat finder phrasing. |
| `teams_120_point_count_answer_text_review` | `team_occurrence_leaders` / `ok`; `pts min=120.0`; count 10 distinct teams. | Confirms single-stat team occurrence count path works. |
| `Jokic over 30 points and over 10 rebounds and over 10 assists` | `player_game_finder` / `ok`; primary `pts`, extras `reb` and `ast`; 10 rows. | Confirms operator-based multi-condition finder parsing/execution works, though filters are applied through the post-result `extra_conditions` path. |
| `Celtics games with 120+ points and 15+ threes` | `game_finder` / `ok`; primary `pts`, extra `fg3m`; 21 rows for current season. | Confirms non-count finder compound thresholds can work today, but the applied filter metadata only exposes the primary threshold. |
| Structured `team_occurrence_leaders` with `conditions=[pts>=120, fg3m>=15]` and `team=BOS` | `LeaderboardResult` / `ok`; row has `games_pts_120+_fg3m_15+=125`. | Confirms the command has enough execution support; the natural count failure is orchestration/post-processing. |

## 4. Root-cause analysis

### Defensive / opponent-points stat mapping

- Findings:
  - `held opponents under N`, `allowed under N`, `gave up fewer than N`, and similar phrases are explicitly handled.
  - `allow fewer than N points` is not handled, so the generic threshold parser wins and binds `points` to team `pts`.
  - Team leaderboard wording `allowed the fewest points per game` falls through to normal team scoring (`pts_per_game`) with ascending sort.
- Existing support:
  - `team_record`, `game_finder`, and `game_summary` can execute `opponent_pts`.
  - `team_record` and `game_finder` derive opponent points from team game rows.
- Gaps:
  - Add defensive alias patterns for present-tense `allow/allowing/allows fewer than`.
  - Add team leaderboard aliases and execution support for `opponent_pts` / `opponent_pts_per_game`.
  - Decide naming in result rows. `opponent_pts_per_game` is clearer than overloading `pts_per_game`.

### Percentage threshold parsing/execution

- Findings:
  - `shoots under 40%` parses no stat and no threshold.
  - `FG% under 40%` parses `fg_pct max=39.9999`, which is the wrong scale for stored `fg_pct` values.
  - `shoots under .400 FG%` was not parsed in the direct probe.
- Existing support:
  - `fg_pct`, `fg3_pct`, `ft_pct`, `efg_pct`, and `ts_pct` aliases exist.
  - Player and team finder/summary commands can filter percentage columns when values are on the 0.xx scale.
- Gaps:
  - Threshold parsing needs percent-token awareness and stat-aware normalization: `40%` and `40 percent` should become `0.40`; `.400` should remain `0.400`.
  - Field-goal shooting phrasing should infer `fg_pct` for `shoots/shooting under N%` and `from the field`; three-point and free-throw variants should remain explicit (`3PT%`, `from three`, `FT%`, `free throw`).

### Compound threshold parsing/execution

- Findings:
  - Operator-based conditions (`over 30 points and over 10 rebounds`) become `threshold_conditions` plus `extra_conditions` and can execute on finder routes.
  - Compact occurrence-style conditions (`30 points and 10 assists`) become `compound_occurrence_conditions`, but finder routes do not consume them.
  - Compound occurrence count routes consume `conditions`, but the duplicate `extra_conditions` post-filter can turn a valid aggregate result into `NoResult`, then `CountResult(0)`.
- Existing support:
  - `player_occurrence_leaders` and `team_occurrence_leaders` already support a `conditions` list with AND semantics.
  - `player_game_finder` and `game_finder` can filter multiple stats through primary plus post-execution extra conditions, but this is weaker than command-level condition-list filtering.
- Gaps:
  - One canonical condition representation is needed per route family.
  - Occurrence routes should not receive duplicate post-aggregate `extra_conditions` for conditions they already consumed.
  - Finder routes need either native condition-list support or a safe pre-limit filtering path. Post-filtering after a route-level `limit` can miss qualifying rows.

## 5. Data/model support

| Needed stat/filter | Available? | Source/derivation | Notes |
|---|---|---|---|
| Team points scored (`pts`) | yes | `data/raw/team_game_stats/*` | Already used by team records, finders, and leaders. |
| Opponent points for team games (`opponent_pts`) | yes, derivable | `pts - plus_minus`, or join the opponent team row in the same `game_id` | Existing `team_record`, `game_finder`, `game_summary`, and `top_team_games` already derive it in places. |
| Points allowed per game leaderboard | yes, needs command support | Aggregate derived `opponent_pts` from `team_game_stats` | `season_team_leaders` currently aggregates team stats but not opponent points. |
| Player FG% (`fg_pct`) | yes | `player_game_stats` column and `add_advanced_pct_columns()` fallback | Stored on 0.xx scale. |
| Team FG% / 3P% / FT% | yes | `team_game_stats` columns and derived aggregates in `season_team_leaders` | Stored/derived on 0.xx scale. |
| Player points/assists/rebounds | yes | `player_game_stats` | Enough for `30 points and 10 assists` and triple-double-like filters. |
| Team threes made (`fg3m`) | yes | `team_game_stats` | Enough for 120+ points and 15+ threes. |
| Compound occurrence count | yes | `player_occurrence_leaders` / `team_occurrence_leaders` `conditions` parameter | Natural orchestration is the weak point, not data availability. |
| Finder compound filters | partially | Primary stat/min/max plus `extra_conditions`; no native route condition list | Works for some cases, but post-limit filtering is a correctness risk. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| A | One combined wave: defensive aliases, percentage thresholds, and compound thresholds | One coordinated parser pass; all five failing cases can be addressed together | Mixes small stat-binding fixes with higher-risk route/execution changes; harder to review and bisect | High | Do not choose unless a single owner can add focused tests across parser, query, engine, and QA harness in one PR-sized unit. |
| B | Split waves: defensive/opponent-points, percentage thresholds, compound thresholds | Keeps scalar mapping fixes separate from condition-list architecture; lower regression risk; easier CI/debug | Requires multiple PRs and staged corpus/findings updates | Medium | Recommended. Defensive and percentage can be one scalar semantics wave if kept focused; compound should be separate. |
| C | Fix defensive now; mark compound unsupported until a real condition-list model exists | Safest short-term behavior for misleading compound outputs | Would conflict with documented compound occurrence/count examples and working adjacent finder cases; leaves high-value natural phrasing broken | Medium | Use only for compact finder forms if the next implementation cannot avoid post-limit/post-aggregate filtering risks. Do not mark documented compound count examples unsupported. |

## 7. Recommended execution scope

- Exact goal:
  - Restore stat/threshold semantics without broadening unrelated product boundaries.
  - Use route-native execution where available. Do not rely on misleading unfiltered or post-aggregate results.

- Cases to fix:
  - Scalar wave:
    - `knicks_allowed_under_110_record`
    - `fewest_points_allowed_team_leader`
    - `boston_tatum_under_40_fg_record_missing_filter`
  - Compound wave:
    - `celtics_120_15_threes_count_missing_filter`
    - `jokic_30_points_10_assists_finder_misparsed`

- Cases to mark unsupported, if any:
  - None of the five target cases should be marked unsupported by default.
  - If finder routes cannot safely apply compact compound filters before limiting, return an explicit `filter_not_supported` only for compact multi-stat finder forms and document the stop condition. Do not return a misleading `ast>=30` no-match.

- Files to change:
  - Defensive scalar wave:
    - `src/nbatools/commands/_parse_helpers.py`
    - `src/nbatools/commands/_leaderboard_utils.py`
    - `src/nbatools/commands/season_team_leaders.py`
    - possibly `src/nbatools/query_service.py` metadata labels if `opponent_pts_per_game` needs a display/filter label
  - Percentage scalar wave:
    - `src/nbatools/commands/_parse_helpers.py`
    - `src/nbatools/commands/_constants.py` only if adding narrowly scoped shooting aliases is necessary
  - Compound wave:
    - `src/nbatools/commands/natural_query.py`
    - `src/nbatools/commands/_occurrence_route_utils.py`
    - `src/nbatools/commands/_natural_query_execution.py`
    - `src/nbatools/query_service.py`
    - `src/nbatools/commands/player_game_finder.py` and `src/nbatools/commands/game_finder.py` if implementing native condition-list filtering before limit

- Tests to add:
  - Parser:
    - `allow fewer than 110 points` -> `opponent_pts max`
    - `allowed the fewest points per game` -> team leaderboard `opponent_pts` or `opponent_pts_per_game`
    - `shoots under 40%` -> `fg_pct max ~= 0.3999`
    - `FG% under 40%`, `shoots below 40 percent`, `FG% under .400`, and `3PT% over 40%`
    - `Jokic games with 30 points and 10 assists` -> preserves both conditions
  - Engine/query service:
    - `season_team_leaders` fixture for opponent PPG leaderboard sorting ascending
    - `player_game_summary` fixture proving `fg_pct max=0.3999` filters rows
    - `team_occurrence_leaders` natural count conversion returns the entity row count for compound conditions and does not apply duplicate extras
    - `player_game_finder` compact compound execution applies both `pts` and `ast`
  - Existing relevant tests to extend:
    - `tests/test_explicit_intent_queries.py`
    - `tests/test_natural_query_parser.py`
    - `tests/test_query_service.py`
    - `tests/test_compound_occurrence_queries.py`
    - `tests/test_season_team_leaders.py`
    - `tests/test_ui_failure_coverage.py` only for high-level regression coverage if needed

- Corpus updates:
  - After behavior is verified, update `qa/raw_query_answer_corpus.yaml` expectations only where current expectations are incomplete:
    - Add hard assertions for `knicks_allowed_under_110_record` if the current dataset result is accepted (`35 games`, `32 wins`, `3 losses` from the probe).
    - Add expected filter/value for `boston_tatum_under_40_fg_record_missing_filter` if stable (`fg_pct max` around `0.3999`) and optionally hard assert current `6 games`, `4 wins`, `2 losses`.
    - Add hard assertion for `celtics_120_15_threes_count_missing_filter` if the current dataset result is accepted (`125`).
    - Keep backend answer phrase quality as a separate AQ-016-style concern unless the execution wave explicitly owns count phrase semantics.

- Findings updates:
  - Update `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` after each wave with fixed run IDs and any residual limitations.
  - Do not mark product completion from parser-only fixes; include execution-backed run evidence.

- Harness validation:
  - Focused QA run for the five targets:
    - `.venv/bin/python tools/raw_query_answer_qa.py --case knicks_allowed_under_110_record --case fewest_points_allowed_team_leader --case boston_tatum_under_40_fg_record_missing_filter --case celtics_120_15_threes_count_missing_filter --case jokic_30_points_10_assists_finder_misparsed`
  - Adjacent QA run:
    - include `lakers_held_opponents_under_100_record`, `celtics_scored_over_120_record`, `lakers_held_opponents_under_100_count`, `curry_5_threes_finder`, `players_40_point_count`, `players_10_assist_count`, `teams_120_point_count_answer_text_review`
  - Local test command guidance:
    - Parser-only iteration: `make test-parser`
    - Query/service execution changes: `make test-query`
    - Command execution changes: `make test-engine`
    - Cross-cutting final check for these high fan-in parser/query changes: `make test-preflight`

- Stop conditions:
  - Stop if a fix requires adding frontend business logic.
  - Stop if a compound finder fix cannot apply all filters before row limiting or otherwise prove no qualifying rows are lost.
  - Stop if percentage support would treat ambiguous bare percentages as FG% outside clear shooting/from-field contexts.
  - Stop if points-allowed leaderboard cannot expose a distinct metric column without confusing it with team scoring.

## 8. Risks / open decisions

- Parser ambiguity risks:
  - `shoots under 40%` should default to FG% only for player/team shooting contexts. Avoid mapping all bare percentages to FG%.
  - `allow fewer than N points` should map to opponent points, while `score fewer than N points` must remain team points.
  - Compact forms like `30-10`, `25/10/10`, and `30 and 10` are not equivalent to explicit `30 points and 10 assists` without more disambiguation.

- Execution/regression risks:
  - Applying `extra_conditions` after a finder's row limit can miss rows. Native condition-list filtering or delayed limiting is safer.
  - Applying `extra_conditions` after occurrence leader aggregation is unsafe and caused the Celtics count to become `0`.
  - Percentage thresholds on the wrong scale silently look successful because all 0.xx values are less than 40.

- Product decisions:
  - `points allowed` should use opponent PPG, not defensive rating, unless the query says defensive rating/defense.
  - Backend count phrase enrichment should remain separate from this wave unless explicitly scheduled. The semantic fix should at least avoid wrong counts and wrong applied filters.
  - Decide whether to expose `opponent_pts_per_game` in docs/catalog as a supported team leaderboard stat alias.

- Data caveats:
  - Opponent points are derivable from team game logs; no new dataset is needed.
  - Percent columns are already in raw player/team game stats or derivable through existing helpers.
  - Current data is through `2026-04-12`; hard corpus count assertions should be tied to the current QA dataset state.

## 9. Validation performed

Commands/probes run:

- `git status --short`: clean before the return package edit.
- Read planning/report/corpus artifacts:
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
  - `return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_3_RETURN_PACKAGE.md`
  - `qa/raw_query_answer_corpus.yaml`
  - `outputs/raw_query_answer_qa/20260513T060001Z/report.md`
  - `outputs/raw_query_answer_qa/20260513T060001Z/report.jsonl`
- Inspected parser/execution files:
  - `src/nbatools/commands/natural_query.py`
  - `src/nbatools/commands/_parse_helpers.py`
  - `src/nbatools/commands/_occurrence_route_utils.py`
  - `src/nbatools/commands/_natural_query_execution.py`
  - `src/nbatools/query_service.py`
  - `src/nbatools/commands/team_record.py`
  - `src/nbatools/commands/game_finder.py`
  - `src/nbatools/commands/player_game_finder.py`
  - `src/nbatools/commands/player_game_summary.py`
  - `src/nbatools/commands/team_occurrence_leaders.py`
  - `src/nbatools/commands/player_occurrence_leaders.py`
  - `src/nbatools/commands/season_team_leaders.py`
  - `src/nbatools/commands/top_team_games.py`
- Direct query probes with `parse_query()`, `execute_natural_query()`, and `query_result_to_payload()` for the five target cases plus nearby working cases.
- Structured execution probes:
  - `player_game_summary` with `fg_pct max=0.3999` for Tatum/Boston: 6 games, 4-2.
  - `team_record` with Knicks `opponent_pts max=109.9999`: 35 games, 32-3.
  - `team_occurrence_leaders` with Celtics `conditions=[pts>=120, fg3m>=15]`: 125.
  - `player_game_finder` with Jokic primary `pts>=30` plus extra `ast>=10`: matching rows returned.
- Data/model probes:
  - Read `data/raw/player_game_stats/2025-26_regular_season.csv` header: includes `fg_pct`, `fg3m`, `pts`, `ast`.
  - Read `data/raw/team_game_stats/2025-26_regular_season.csv` header: includes `pts`, `fg3m`, `plus_minus`.
  - Derived 2025-26 opponent PPG from team logs; top five were Boston, Oklahoma City, Detroit, Houston, and New York.

No production code, tests, or QA corpus expectations were changed.
