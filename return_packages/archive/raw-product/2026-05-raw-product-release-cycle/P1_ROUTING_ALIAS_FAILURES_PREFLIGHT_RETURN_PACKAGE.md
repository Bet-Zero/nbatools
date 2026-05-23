# P1 Routing / Alias Failures Preflight Return Package

## 1. Executive summary

- Main root-cause families:
  - Defensive/opponent-points aliases are incomplete. Existing execution support for `opponent_pts_per_game` works, but two common phrases do not reach it.
  - Playoff matchup routing requires explicit `vs` / `versus`; adjacency phrasing such as `Heat Knicks playoff series record` collapses to one detected team.
  - Single-team Finals/conference-finals record phrasing is not a safe one-line routing fix. Current docs say entity-specific Finals record splits are outside the shipped surface, and the round extractor is currently unreliable on numeric CSV `game_id` values unless IDs are zero-padded before slicing.
- Which cases are true bugs:
  - `most_points_allowed_team_leaders_wave4`: true stat-alias bug; wrong metric.
  - `opponent_ppg_leaders_wave4`: true route/stat-alias bug; wrong entity surface and wrong metric.
  - `heat_knicks_playoff_series_record_wave4`: true matchup-routing phrase gap; the matchup route works for `Heat vs Knicks playoff history`.
  - `warriors_finals_record_since_2015_wave4`: true wrong-answer bug in current behavior because it returns a broad regular-season team record.
  - `celtics_conference_finals_record_wave4`: route bug, but product support needs approval before making it an ok result.
- Which cases are product-boundary decisions:
  - `bulls_finals_record_wave4`: current data has Bulls playoff games from the Finals era, but no reliable round code for those 1996-97/1997-98 rows. Treat as no-result/product-boundary unless a round data backfill or inference design is approved.
  - Single-team round-record queries generally need a decision: keep unsupported per current docs, or approve `playoff_history` with `playoff_round` as the shipped entity-specific route after fixing round extraction.
- Recommended next execution:
  - Option C: execute defensive alias completion first, then run a dedicated playoff data/routing wave. Do not combine all P1 work into one patch.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `bulls_finals_record_wave4` | `Bulls Finals record` | Parse: `route=team_record`, `season_type=Regular Season`, `team=CHI`, `playoff_round_filter=04`, route kwargs regular-season `team_record` with no season. Execution/report: `team_record` / `no_result`, reason `unsupported`, no sections. | No answer rows. Notes say `Provide either --season or both --start-season and --end-season`. Expectation failures: status, route, shape, missing `leaderboard`, metadata `season_type`. | Do not return regular-season team record. Safest current product behavior is clean no-result for unsupported or unavailable single-team round records. If product approves support, desired route should be `playoff_history` with `playoff_round=04`, not `playoff_round_record` leaderboard. | Finals phrase sets `playoff_round_filter` but does not force playoff semantics. Also, Bulls Finals seasons in current data are pre-2001 round-coverage rows, so current data cannot reliably identify those games as Finals. |
| `warriors_finals_record_since_2015_wave4` | `Warriors Finals record since 2015` | Parse: `route=team_record`, `season_type=Regular Season`, `team=GSW`, `start_season=2015-16`, `end_season=2025-26`, `playoff_round_filter=04`. Execution/report: `team_record` / `ok`, sections `summary` 1 and `by_season` 11. | Wrong answer: broad regular-season Warriors record, `537-338`, 875 games. Expectation failures: route, shape, missing `leaderboard`, metadata `season_type`. | Never return regular-season record. If product approves single-team round records, desired shape is likely `playoff_history` summary/by_season with `playoff_round=04`; zero-padded game-id probe found GSW Finals since 2015 as 28 games, 17-11 across 2015-16, 2016-17, 2017-18, 2018-19, 2021-22. | Same routing gap as Bulls, plus since-year parsing works but is applied to the wrong season type. Existing round extraction is unsafe without zero-padding. |
| `celtics_conference_finals_record_wave4` | `Celtics conference finals record` | Parse: `route=team_record`, `season_type=Regular Season`, `team=BOS`, `playoff_round_filter=03`. Execution/report: `team_record` / `no_result`, reason `unsupported`, no sections. | No answer rows with generic season guidance. Expectation failures: status, route, shape, missing `leaderboard`, metadata `season_type`. | Clean unsupported/no-result unless entity-specific playoff-round records are approved. If approved, likely `playoff_history` with `playoff_round=03`; zero-padded probe found BOS conference-finals rows as 61 games, 30-31 across 10 seasons. | Conference-finals phrase sets a round filter but not playoff season semantics. The current expected `playoff_round_record` conflicts with the route contract because that route is a ranked team leaderboard. |
| `heat_knicks_playoff_series_record_wave4` | `Heat Knicks playoff series record` | Parse: `route=playoff_history`, `season_type=Playoffs`, `team=NYK`, `team_a=None`, `team_b=None`, route kwargs single-team history. Execution/report: `playoff_history` / `ok`, sections `summary` 1 and `by_season` 13. | Wrong entity grain: Knicks playoff history, `64-69`, not Heat/Knicks matchup. Expectation failures: route, shape, missing `comparison`. | Desired route is `playoff_matchup_history`, same result family as passing `Heat vs Knicks playoff history`: summary 2 rows and comparison 6 rows. | Team comparison extraction only recognizes `vs` / `versus`; adjacency team-team phrasing is not promoted to `team_a`/`team_b`. |
| `most_points_allowed_team_leaders_wave4` | `which teams allow the most points per game this season` | Parse: `route=season_team_leaders`, `team_leaderboard_intent=True`, `stat=pts`, `ascending=False`. Execution/report: `season_team_leaders` / `ok`, leaderboard 10 rows. | Wrong metric: ranks team scoring PPG; top row Denver at `122.073 pts_per_game`. Expectation failure: metadata `stat`, expected `opponent_pts_per_game`. | Desired route stays `season_team_leaders`, stat `opponent_pts_per_game`, descending for `most`. | Team aliases cover `fewest/least/points allowed` variants but not `allow the most points per game`. Earlier player stat fallback binds `points per game` to `pts`; team stat detection does not override it. |
| `opponent_ppg_leaders_wave4` | `opponent PPG leaders this season` | Parse: `route=season_leaders`, `team_leaderboard_intent=False`, `stat=pts`. Execution/report: `season_leaders` / `ok`, player leaderboard 10 rows. | Wrong surface and metric: ranks player scoring PPG; top row Luka Doncic. Expectation failures: route and metadata `stat`. | Desired route is `season_team_leaders`, stat `opponent_pts_per_game`. Default sort should be descending unless product decides bare `opponent PPG leaders` means best/lowest. | Missing `opponent ppg` team leaderboard alias. Bare `ppg` is recognized as player `pts`, so metric-only default chooses player `season_leaders`. |

## 3. Nearby working cases

| Case ID / Query | Behavior | Why it matters |
|---|---|---|
| `lakers_playoff_history` / `Lakers playoff history` | Passes as `playoff_history`, `ok`, sections `summary` and `by_season`. | Single-team playoff history route works when the query names playoff history directly. |
| `spurs_playoff_history_since_2000_wave4` / `Spurs playoff history since 2000` | Passes as `playoff_history`; since-year range is preserved. | Since-year parsing itself is not the blocker for playoff history. |
| `heat_knicks_playoff_history` / `Heat vs Knicks playoff history` | Passes as `playoff_matchup_history`, comparison 6 rows. | Matchup execution works when `team_a` and `team_b` are extracted. |
| `lakers_celtics_playoff_history` / `Lakers vs Celtics playoff history` | Passes as `playoff_matchup_history`, summary 2 and comparison 2. | Existing `vs` matchup parser path is healthy. |
| `lakers_celtics_series_record` / `Lakers playoff series record vs Celtics` | Passes under current corpus as `playoff_history` with opponent filter `BOS`, not `playoff_matchup_history`. | There is an unresolved product ambiguity: `series record vs` currently means single-team history with opponent filter, while adjacency `Heat Knicks playoff series record` expects matchup history. |
| `best_finals_record_since_1980` / `best Finals record since 1980` | Passes as `playoff_round_record` leaderboard. | League-wide round-record route exists, but current rows are suspect until game-id round extraction is fixed. |
| `most_conference_finals_appearances_wave4` / `most conference finals appearances` | Passes as `playoff_appearances` leaderboard. | Round phrase detection exists for appearance leaderboards. |
| `lakers_finals_appearances` / `Lakers Finals appearances` | Passes as `playoff_appearances`, single-team summary/by_season. | Single-team round appearances have an approved route distinct from single-team round records. |
| `fewest_points_allowed_team_leader` / `Which team has allowed the fewest points per game this season?` | Passes as `season_team_leaders`, stat `opponent_pts_per_game`, Boston top row. | Wave 4A execution support and ascending sort for low opponent PPG are already in place. |
| `def_rating_team_leaders_wave4` / `best defensive rating teams this season` | Passes as `season_team_leaders`, stat `def_rating`, ascending. | Team defensive-stat route selection works for known team aliases. |
| `lakers_held_opponents_under_100_record` / `What is the Lakers record when they held opponents under 100 points?` | Passes as `team_record`, stat `opponent_pts`, threshold filter. | Opponent-points threshold parsing is separate and already works. |

## 4. Root-cause analysis

### Playoff round phrase routing

- Findings:
  - `finals` and `conference finals` are detected as `playoff_round_filter`, but they do not force `season_type=Playoffs`.
  - The current fallback sends single-team `Finals record` / `conference finals record` queries to `team_record`.
  - `Warriors Finals record since 2015` is the highest-risk current behavior because it returns an authoritative-looking but wrong regular-season answer.
  - Current Wave 4 expectations point single-team round-record cases at `playoff_round_record`, but `docs/reference/result_contracts/core_result_table_contracts.md` describes `playoff_round_record` as a ranked team leaderboard.
  - `docs/reference/query_catalog.md` explicitly lists `Celtics finals record` outside the shipped playoff/era-history surface and says entity-specific Finals records require an approved playoff-round record data contract.
- Existing support:
  - `detect_playoff_round_filter()` maps `finals` to `04` and `conference finals` to `03`.
  - `build_playoff_history_result()` accepts `playoff_round` for a single team.
  - `build_playoff_round_record_result()` exists for league-wide round leaderboards.
- Gaps:
  - Product contract mismatch for single-team round records: unsupported per docs versus expected ok in Wave 4 corpus.
  - Round extraction needs a fix before any new round-record support is trustworthy; CSV `game_id` values are numeric-like and lose the leading `00`, while `_add_round_column()` slices `str(game_id)[6:8]`.
  - Bulls Finals cannot be answered from current round fields because the Bulls relevant Finals seasons are in pre-2001 rows with unknown round coverage.

### Playoff matchup phrase routing

- Findings:
  - `Heat Knicks playoff series record` detects only `team=NYK`, not `team_a=MIA`, `team_b=NYK`.
  - Existing `Heat vs Knicks playoff history` routes and executes correctly as `playoff_matchup_history`.
  - Existing `Lakers playoff series record vs Celtics` is intentionally expected as single-team `playoff_history` with opponent filter in the current corpus, though its manual note already questions whether it should become matchup history.
- Existing support:
  - `build_playoff_matchup_history_result()` returns the desired `summary` and `comparison` sections.
  - `try_playoff_record_route()` routes to `playoff_matchup_history` when `playoff_history_intent` and both `team_a`/`team_b` are present.
- Gaps:
  - `extract_team_comparison()` only handles `vs` / `versus`.
  - There is no narrow parser rule for two adjacent team aliases in playoff-series/history context.
  - Product semantics for `TEAM playoff series record vs TEAM` remain ambiguous relative to adjacency forms.

### Defensive/opponent-points aliases

- Findings:
  - `opponent_pts_per_game` execution is present and verified by the passing `fewest_points_allowed_team_leader` case.
  - `which teams allow the most points per game this season` is routed to the right team route but wrong stat (`pts`).
  - `opponent PPG leaders this season` routes to player `season_leaders` because `ppg` is a player alias and `opponent ppg` is not a team alias.
- Existing support:
  - `season_team_leaders.ALLOWED_STATS` exposes `opponent_pts_per_game`.
  - `season_team_leaders.build_result()` derives `opponent_pts_per_game` from opponent points totals.
  - `TEAM_LEADERBOARD_STAT_ALIASES` already maps `fewest points allowed`, `points allowed`, `opponent points per game`, and `opp pts` variants.
  - Natural sort logic already treats `opponent_pts_per_game` as lower-is-better, with `fewest/least/lowest/best` ascending and `most/highest/worst` descending.
- Gaps:
  - Missing aliases: `allow the most points per game`, `allows the most points per game`, `allowed the most points per game`, `most points allowed`, `opponent ppg`.
  - `wants_team_leaderboard()` depends on `detect_team_leaderboard_stat()` for team-stat shorthand without the word `team`, so `opponent ppg` must be in team aliases, not only command-level structured aliases.

## 5. Data/model support

| Needed behavior | Available? | Source/route | Notes |
|---|---|---|---|
| Team opponent PPG leaderboard | Yes | `season_team_leaders.build_result(stat="opponent_pts_per_game")` | Already used by passing `fewest_points_allowed_team_leader`; next fix is alias/routing only. |
| Most/fewest opponent PPG sort direction | Yes | `natural_query.py` lower-is-better logic | `fewest/least/lowest/best` -> ascending; `most/highest/worst` -> descending. |
| `opponent PPG` shorthand | Partially | Parser aliases | Execution supports canonical stat, but parser lacks shorthand mapping. |
| Playoff matchup history between Heat and Knicks | Yes | `build_playoff_matchup_history_result(team_a="MIA", team_b="NYK")` | Current data returns MIA 19-16 and NYK 16-19 over 35 games, comparison 6 seasons. |
| `Heat Knicks` adjacency team pair extraction | No | `_matchup_utils.extract_team_comparison()` | Current parser requires `vs` / `versus`; adjacency phrase is not recognized. |
| League-wide playoff round record leaderboards | Partially | `build_playoff_round_record_result()` | Route exists, but current round extraction is suspect due non-zero-padded `game_id` slicing. |
| Single-team playoff round records | Not shipped / needs decision | Potentially `build_playoff_history_result(playoff_round=...)` | Internal builder can filter by round, but query docs mark entity-specific Finals records outside the shipped surface. Needs product approval and round extraction fix. |
| Bulls Finals record | Not reliably available | Current playoff game logs | Bulls 1996-97/1997-98 playoff rows exist, but round codes are unknown in current coverage. A round-level answer needs backfill/inference beyond a parser fix. |
| Warriors Finals since 2015 | Available after round extraction fix | Playoff game logs with zero-padded `game_id` | Read-only zfill probe found 28 games, 17 wins, 11 losses across five Finals appearances. Current unpadded helper returns distorted data. |
| Celtics conference-finals record | Available after round extraction fix | Playoff game logs with zero-padded `game_id` | Read-only zfill probe found 61 games, 30 wins, 31 losses across 10 conference-finals seasons. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| Option A - combined P1 wave | Defensive aliases plus playoff round/matchup routing/data in one execution | Fixes all six target cases in one wave if successful. | Mixes a small alias patch with a product/data-contract decision and a likely round-extraction fix. High chance of scope creep or misleading "green" playoff expectations. | High | Not recommended. |
| Option B - split waves: playoff first, defensive second | Wave 6A playoff round/matchup; Wave 6B defensive aliases | Keeps families separate and addresses P1 playoff wrong-answer risk first. | Playoff scope is not ready for direct implementation because single-team round records conflict with docs and round extraction is suspect. | Medium-high | Acceptable only after a product decision on single-team round records. |
| Option C - defensive alias direct execution first, playoff dedicated wave next | Wave 6A defensive/opponent-points alias completion; Wave 6B playoff product/data/routing execution | Delivers two true bugs quickly with low blast radius. Avoids entangling defensive aliases with playoff data-contract work. Lets playoff wave start from explicit decisions. | Leaves playoff P1 failures open for one more wave. | Low for Wave 6A, medium for Wave 6B | Recommended. |

## 7. Recommended execution scope

- Exact goal:
  - Immediate Wave 6A: complete defensive/opponent-points alias coverage for the two AQ-021 cases without changing result contracts.
  - Follow-up Wave 6B: resolve AQ-020 with an explicit product decision, round-extraction fix if support is approved, and narrow matchup phrase routing.

- Cases to fix:
  - Wave 6A:
    - `most_points_allowed_team_leaders_wave4`
    - `opponent_ppg_leaders_wave4`
  - Wave 6B:
    - `heat_knicks_playoff_series_record_wave4`
    - `warriors_finals_record_since_2015_wave4`, only if single-team round records are approved.
    - `celtics_conference_finals_record_wave4`, only if single-team round records are approved.

- Cases to mark unsupported/no-result, if any:
  - `bulls_finals_record_wave4` should be marked as a clean no-result/product-boundary unless a pre-2001 round backfill or inference contract is approved.
  - If product keeps current docs, all single-team round-record cases (`bulls_finals_record_wave4`, `warriors_finals_record_since_2015_wave4`, `celtics_conference_finals_record_wave4`) should become clean unsupported/no-result rather than `team_record` fallbacks. This should be a documented product decision, not expectation weakening.

- Files to change:
  - Wave 6A likely production files:
    - `src/nbatools/commands/_leaderboard_utils.py`
    - `src/nbatools/commands/season_team_leaders.py` only if structured alias parity for `opponent ppg` is added.
  - Wave 6A docs/findings:
    - `docs/reference/query_catalog.md`
    - `docs/reference/query_guide.md` if adding user-facing examples.
    - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
  - Wave 6B likely production files:
    - `src/nbatools/commands/playoff_history.py` for `game_id` zero-padding in round extraction.
    - `src/nbatools/commands/_playoff_record_route_utils.py` for approved single-team round-record handling.
    - `src/nbatools/commands/_matchup_utils.py` or a playoff-specific parser helper for adjacent team-team playoff series phrasing.
    - `src/nbatools/commands/natural_query.py` only for integration points if existing helper boundaries require it.
  - Wave 6B docs/findings:
    - `docs/reference/query_catalog.md`
    - `docs/reference/result_contracts/core_result_table_contracts.md` if single-team round-record shape is approved.
    - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`

- Tests to add:
  - Wave 6A:
    - Parser tests in `tests/test_natural_query_parser.py` for:
      - `which teams allow the most points per game this season` -> `season_team_leaders`, `stat=opponent_pts_per_game`, `ascending=False`.
      - `opponent PPG leaders this season` -> `season_team_leaders`, `stat=opponent_pts_per_game`.
      - Existing scoring guardrail remains `Which teams score the most points this season?` -> `stat=pts`.
    - Data-backed query test in `tests/test_ui_failure_coverage.py` or closest existing raw-QA coverage file proving returned rows expose `opponent_pts_per_game`.
  - Wave 6B:
    - Unit tests for zero-padded playoff round extraction.
    - Parser tests for adjacency matchup: `Heat Knicks playoff series record` -> `playoff_matchup_history`.
    - Regression test preserving or intentionally changing `Lakers playoff series record vs Celtics` according to product decision.
    - Execution tests for approved single-team round records, or unsupported/no-result tests if not approved.

- Corpus updates:
  - Wave 6A: no expectation changes should be needed; existing desired expectations for AQ-021 should pass after code change. Manual review status may be updated after harness validation.
  - Wave 6B:
    - `heat_knicks_playoff_series_record_wave4` expectation can stay as-is if adjacency matchup is supported.
    - Single-team round-record cases need product-aligned expectations:
      - If supported: change expected route/shape from `playoff_round_record` to the approved single-team route, likely `playoff_history` with `summary`/`by_season`, and add hard assertions only where data is reliable.
      - If unsupported: change to `no_result` / `filter_not_supported` or `no_match` with explicit notes and manual-review status.

- Findings updates:
  - Mark AQ-021 fixed after Wave 6A passes targeted and full harness validation.
  - Split AQ-020 into at least two tracked entries if helpful:
    - Playoff matchup adjacency routing.
    - Single-team playoff round-record product/data support.
  - Add a note that Bulls Finals is a data boundary with current round coverage.

- Harness validation:
  - Wave 6A targeted:
    - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id <wave6a_targeted> --case most_points_allowed_team_leaders_wave4 --case opponent_ppg_leaders_wave4 --case fewest_points_allowed_team_leader --case def_rating_team_leaders_wave4 --case team_scoring_leaders`
  - Wave 6A full:
    - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id <wave6a_full>`
  - Wave 6B targeted:
    - Include all AQ-020 cases plus nearby working cases: `heat_knicks_playoff_history`, `lakers_celtics_playoff_history`, `lakers_celtics_series_record`, `best_finals_record_since_1980`, `most_finals_appearances_since_1980`, `lakers_finals_appearances`, `most_conference_finals_appearances_wave4`, `spurs_playoff_history_since_2000_wave4`.
  - Standard tests:
    - Wave 6A: focused parser/data-backed tests first; `make test-query` is sufficient if touched area stays parser/routing plus existing command support.
    - Wave 6B: `make test-query` and `make test-engine`; use `make test-preflight` if round extraction or result contracts change broadly.

- Stop conditions:
  - Do not ship any playoff "fix" that returns regular-season records for round phrases.
  - Do not ship single-team round-record support until round extraction is corrected and the route/shape is documented.
  - Do not mark Bulls Finals as ok unless pre-2001 round data is backfilled or explicitly inferred with a documented contract.
  - Do not make broad adjacent-team parsing that changes ordinary two-team comparison/query behavior outside playoff series/history contexts.
  - Do not change frontend rendering or add backend answer phrase enrichment in these waves.

## 8. Risks / open decisions

- Parser ambiguity risks:
  - `opponent PPG leaders` could mean worst defenses (highest opponent PPG) or best defenses (lowest opponent PPG). Current leaderboard convention implies descending unless the user says `fewest`, `lowest`, or `best`.
  - Adjacent team-team parsing can overmatch city/team words in ordinary prose. Keep it limited to playoff series/history/matchup contexts and exactly two confident team entities.
  - `TEAM playoff series record vs TEAM` currently has a passing single-team-with-opponent expectation. Changing it to matchup history is a product decision, not a side effect.

- Execution/regression risks:
  - Fixing playoff round extraction with `zfill(10)` will change existing playoff appearances and round-record rows that currently pass mostly route/shape expectations. Those changes are probably correctness improvements but require targeted expected-row review.
  - `playoff_round_record` leaderboards currently may have distorted counts because unpadded `game_id` slicing reads the game number as a round code.
  - Adding team aliases must not steal player PPG leaderboards such as `PPG leaders this season`; only opponent/allowed phrasing should route to team leaders.

- Product decisions:
  - Whether single-team `Finals record` / `conference finals record` should remain unsupported per current docs or become supported as `playoff_history` with a round filter.
  - Whether `Bulls Finals record` should remain no-result until data is backfilled, or whether older playoff rows should be inferred from another source.
  - Whether `series record vs` should mean one team's playoff history against an opponent or a two-sided matchup history.

- Data caveats:
  - Round data before 2001-02 is documented as unavailable. The Bulls case depends on those older round labels.
  - Latest playoff data in the existing reports ends at 2024-25 for playoff routes; `since 2015` parsing may produce an end season of 2025-26, but playoff execution resolves to available playoff seasons.

## 9. Validation performed

- Read and inspected:
  - `return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_4_RETURN_PACKAGE.md`
  - `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_5_CONTEXT_FILTER_NO_MATCH_RETURN_PACKAGE.md`
  - `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_4A_SCALAR_STAT_THRESHOLD_SEMANTICS_RETURN_PACKAGE.md`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
  - `qa/raw_query_answer_corpus.yaml`
  - `tools/raw_query_answer_qa.py`
  - `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md`
  - `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.jsonl`
  - `docs/reference/query_catalog.md`
  - `docs/reference/query_guide.md`
  - `docs/reference/result_contracts/core_result_table_contracts.md`

- Exact read-only artifact probes:
  - `rg -n "AQ-020|AQ-021|bulls_finals_record_wave4|warriors_finals_record_since_2015_wave4|celtics_conference_finals_record_wave4|heat_knicks_playoff_series_record_wave4|most_points_allowed_team_leaders_wave4|opponent_ppg_leaders_wave4" docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_4_RETURN_PACKAGE.md outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md qa/raw_query_answer_corpus.yaml`
  - `sed -n '3100,3235p' qa/raw_query_answer_corpus.yaml`
  - `sed -n '3438,3485p' qa/raw_query_answer_corpus.yaml`
  - `sed -n '6630,7295p' outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.md`
  - JSONL extraction with `python3 -c` over `outputs/raw_query_answer_qa/20260513T214500Z_wave4_full/report.jsonl` for the six target cases and nearby passing cases.

- Direct parser/execution probes:
  - `.venv/bin/python -c ...` using `parse_query()` and `execute_natural_query()` for:
    - `Bulls Finals record`
    - `Warriors Finals record since 2015`
    - `Celtics conference finals record`
    - `Heat Knicks playoff series record`
    - `which teams allow the most points per game this season`
    - `opponent PPG leaders this season`
    - `best finals record since 2001`
    - `most conference finals appearances since 2000`
    - `Lakers playoff series record vs Celtics`
    - `Heat vs Knicks playoff history`
    - `Which team has allowed the fewest points per game this season?`
  - Results matched the Wave 4 report for target failures.

- Data/model probes:
  - `.venv/bin/python -c ...` direct calls to `build_playoff_history_result()`, `build_playoff_matchup_history_result()`, and `build_playoff_round_record_result()`.
  - `.venv/bin/python -c ...` zero-padded game-id round calculation using `load_team_games_for_seasons()` to validate round-extraction support:
    - GSW Finals since 2015: 28 games, 17-11.
    - BOS conference finals: 61 games, 30-31.
    - CHI Finals: 0 reliable round-coded games in current coverage.
    - MIA/NYK playoff matchup: 35 games each side, MIA 19-16, NYK 16-19.

- Code inspection:
  - `src/nbatools/commands/_leaderboard_utils.py`
  - `src/nbatools/commands/season_team_leaders.py`
  - `src/nbatools/commands/_parse_helpers.py`
  - `src/nbatools/commands/_matchup_utils.py`
  - `src/nbatools/commands/_playoff_record_route_utils.py`
  - `src/nbatools/commands/playoff_history.py`
  - `src/nbatools/commands/natural_query.py`
  - `src/nbatools/commands/_natural_query_execution.py`

- Tests/harness:
  - Not run. This was preflight-only; no production code, tests, corpus expectations, or frontend files were changed.
