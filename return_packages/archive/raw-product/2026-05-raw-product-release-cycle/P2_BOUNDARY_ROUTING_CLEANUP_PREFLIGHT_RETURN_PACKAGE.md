# P2 Boundary / Routing Cleanup Preflight Return Package

## 1. Executive summary

- Main root-cause families:
  - AQ-018: position leaderboards have partial support, but noun-prefix forms such as `Which centers have...` do not populate `position_filter`; role/rookie/team-bench forms are not execution-backed and currently broaden.
  - AQ-019: player comparison support exists, but full-name `LeBron James vs Kevin Durant comparison` is not extracted as `player_a/player_b`.
  - AQ-022: personal-foul leaderboard phrasing is not a supported stat leaderboard and currently falls back to points.
  - AQ-023: opponent-conference phrasing is not parsed or execution-backed and currently falls back to full-season team record.
- Which cases are true bugs:
  - `centers_rebound_leaders_wave4`: data-backed position support exists, but the parser misses the position in this phrasing.
  - `lebron_durant_comparison_wave4`: `player_compare` exists and nearby alias-only comparisons work; full-name comparison extraction is the gap.
  - The broad-answer fallbacks for unsupported role/rookie/PF/conference cases are product-boundary bugs because they return plausible but wrong answers.
- Which cases are product-boundary decisions:
  - `rookie_scoring_leaders_wave4`, `bench_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, `personal_foul_leaders_wave4`, `celtics_against_east_record_wave4`.
- Recommended next execution:
  - Option C: support the two low-risk shipped surfaces now, and mark the unsupported boundaries explicit `no_result` responses. Defer real rookie/role/team-bench/PF/conference support until each has a route/data contract.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `centers_rebound_leaders_wave4` | `Which centers have the most rebounds this season?` | `season_leaders` / `ok` | Returns a 10-row rebound leaderboard with no applied filters; metadata `position_filter=null`; top row Nikola Jokic. | Keep `season_leaders` / `ok`, but apply a center position filter and expose `metadata.position_filter`. Prefer canonical existing group value `centers` unless the corpus deliberately wants singular `center`. | `season_leaders` can filter positions, but `extract_position_filter` only recognizes `among/by/for` forms, not leading noun phrases like `Which centers...`. |
| `rookie_scoring_leaders_wave4` | `rookie scoring leaders this season` | `season_leaders` / `ok` | Returns broad points leaders; metadata has no rookie filter, role, unsupported filter, or applied filter; top row Luka Doncic. | `no_result` with `filter_not_supported` until rookie leaderboards have an approved roster/experience contract and result semantics. | Parser does not detect rookie context; metric-only leaderboard default fires. Roster `experience_years` exists, but rosters are currently documented primarily as enrichment/future roster-aware filters. |
| `bench_scoring_leaders_wave4` | `bench players scoring leaders this season` | `season_leaders` / `ok` | Returns broad points leaders; metadata `role=null`; top row Luka Doncic. | `no_result` with `filter_not_supported` until league-wide role leaderboards are supported. | `detect_role` only runs when a player/comparison entity exists, so league role context is dropped before route execution can block it. |
| `starter_assist_leaders_wave4` | `starter assist leaders this season` | `season_leaders` / `ok` | Returns broad assist leaders; metadata `role=null`; top row Nikola Jokic. | `no_result` with `filter_not_supported` until league-wide role leaderboards are supported. | Same as bench leaderboard: starter context is not parsed outside player routes. |
| `celtics_bench_scoring_boundary_wave4` | `Celtics bench scoring this season` | `game_finder` / `ok` | Returns Celtics team game scoring rows sorted by points; metadata `team=BOS`, `stat=pts`, `role=null`; top row is a 148-point team game. | `no_result` with `filter_not_supported` for team bench scoring. | Team-only bench semantics are documented out of scope, but the parser drops `bench` and executes a broad team finder. |
| `lebron_durant_comparison_wave4` | `LeBron James vs Kevin Durant comparison` | `player_game_finder` / `ok` | Treats LeBron as the player and Kevin Durant as `opponent_player`; returns three LeBron game rows against Durant's team. | `player_compare` / `ok` with `summary` and `comparison` sections. | `extract_player_comparison` is alias-map based; aliases include `lebron` and `durant`, but not full names. Full-name resolver is used later by single-player detection, after comparison extraction has already failed. |
| `personal_foul_leaders_wave4` | `personal fouls leaders this season` | `season_leaders` / `ok` | `stat` is not recognized, so the leaderboard default uses `pts` and returns points leaders. | Prefer `no_result` with `unsupported` or `filter_not_supported` until PF leaderboard support is approved; do not fall back to points. | Personal fouls are present in player game logs but not in `STAT_ALIASES`, `_LEADERBOARD_ONLY`, `season_leaders.ALLOWED_STATS`, or `_build_from_game_logs` aggregation. |
| `celtics_against_east_record_wave4` | `Celtics record against the East this season` | `team_record` / `ok` | Returns full-season Celtics record, 56-26 over 82 games; metadata has no opponent or opponent group. | `no_result` with `filter_not_supported` until opponent-conference filters are approved and backed by complete team conference metadata. | Parser has opponent-quality buckets and direct opponent filters, but no `East/West` opponent-conference slot. Team game logs can filter opponent lists, but current team conference reference data is incomplete. |

## 3. Nearby working cases

| Case ID / Query | Behavior | Why it matters |
|---|---|---|
| `best ts% among centers this season` | Routes to `season_leaders`, applies `position_filter=centers`, returns caveat `filtered to position group: centers`. | Confirms backend position filtering is already data-backed when the parser passes the position group. |
| `top scorers among guards since 2021` | Routes to `season_leaders`, applies `position_filter=guards`, returns multi-season position-filtered leaderboard. | Confirms multi-season position filtering is already supported for documented `among` phrasing. |
| `guard scoring leaders this season` | Routes to `season_leaders` and passes corpus light checks, but metadata `position_filter=null`. | This is not truly working; it shows nearby corpus cases are under-asserted and should be hardened when the parser fix ships. |
| `Nikola Jokic as a starter this season` | Routes to `player_game_summary` with `role=starter`; returns summary/game log. | Named-player starter/bench role context is the shipped role boundary. |
| `Malik Monk off the bench this season` | Routes to `player_game_summary` with `role=bench`; returns summary/game log. | Confirms role parsing/execution exists only for player-context routes. |
| `LeBron vs Durant` | Routes to `player_compare`, returns `summary` and `comparison`. | Confirms comparison command and alias-based extraction work. |
| `Jokic vs Embiid recent form` | Routes to `player_compare` with `last_n=10`. | Confirms comparison routing handles player aliases plus trailing context. |
| `Jayson Tatum vs Jaylen Brown last 10 games` | Routes to `player_compare`, returns two summary rows and metric comparison. | Existing Wave 4 passing comparison case. |
| `turnover leaders this season` | Routes to `season_leaders`, `stat=tov`, returns turnover leaderboard. | Confirms normal stat leaderboards work when the alias is supported. |
| `steal leaders this season` | Routes to `season_leaders`, `stat=stl`, returns steal leaderboard. | Confirms supported defensive box-score stat aliases work. |
| `Celtics record against playoff teams last season` | Routes to `team_record` with structured `opponent_quality`, returns a filtered 52-game record. | Confirms opponent-quality filters are available, but they are not the same as opponent-conference filters. |
| `Tatum vs top defenses` | Routes to `player_game_summary` with `opponent_quality=top-10 defenses`. | Confirms structured opponent buckets are execution-backed on supported single-entity routes. |

## 4. Root-cause analysis

### Position/role-filtered leaderboards

- Findings:
  - `season_leaders.build_result(..., position=...)` supports position groups and filters through `data/raw/rosters/{season}.csv`.
  - Natural parsing supports `among centers`, `among guards`, `by guards`, and `for centers`.
  - Natural parsing does not support leading noun-prefix forms such as `centers rebound leaders`, `guard scoring leaders`, `forwards FG% leaders`, or question form `Which centers have...`.
  - The latest report only fails `centers_rebound_leaders_wave4` because that case has a hard assertion on `metadata.position_filter`. Several nearby Wave 4 position cases pass only because their expectations are light.
  - Role contexts are deliberately scoped to player-context routes in docs and parser behavior. League/team role leaderboards currently broaden.
- Existing support:
  - Data: rosters include `position` and `experience_years`.
  - Execution: `season_leaders` supports `position`; `player_game_summary` and `player_game_finder` support `role` when trusted `player_game_starter_roles` coverage exists.
  - Role data: `data/raw/player_game_starter_roles/2025-26_regular_season.csv` has 32,047 trusted rows and 1,225 unique games in the local data.
- Gaps:
  - Position parser needs noun-prefix/question-form coverage and corpus/test assertions should check metadata for all position cases.
  - Rookie leaderboards need either explicit unsupported routing now or a new roster-experience contract and season leaderboard filter later.
  - League-wide bench/starter leaderboards need a `season_leaders` role filter design before support.
  - Team bench scoring needs a new team bench aggregation shape; a team game finder is not a valid substitute.

### Player comparison routing

- Findings:
  - Exact failing phrase: `LeBron James vs Kevin Durant comparison`.
  - `LeBron vs Durant` works because both are in the curated alias map.
  - `LeBron James vs Kevin Durant` and `LeBron James vs Kevin Durant comparison` fail because full names are resolved by the later single-player resolver, not by `extract_player_comparison`.
  - `Compare LeBron James and Kevin Durant` currently resolves only LeBron and routes to `player_game_summary`.
- Existing support:
  - `player_compare` route and result contract are shipped.
  - Existing tests and corpus cases cover alias-based player comparisons and last-N comparisons.
- Gaps:
  - Comparison extraction should use full-name entity resolution, not only `PLAYER_ALIASES`.
  - Guardrails should preserve player-vs-player-as-opponent routes when the text has a player plus intervening stats/finder words, such as `Jokic stats vs Embiid` or `show Jokic games vs Embiid`.

### Personal-foul stat boundary

- Findings:
  - `personal foul leaders`, `personal fouls leaders`, and `foul leaders` all route to points leaders today.
  - `players with the most fouls` is unrouted at parse time, which is safer than the current leaderboard fallback.
  - `season_leaders.build_result(stat="pf")` raises `ValueError: Unsupported stat 'pf'`.
- Existing support:
  - Raw player, team, and period game stats include `pf`.
  - Several command modules support `pf` in game-level summaries/finders.
- Gaps:
  - `season_leaders` does not aggregate `pf_total` or `pf_per_game`.
  - Natural stat alias tables do not map personal fouls to `pf`.
  - Product semantics need a decision: `personal fouls` means fouls committed, while `fouls` alone can be confused with fouls drawn.

### Opponent-conference filters

- Findings:
  - `Celtics record against Eastern Conference teams`, `Celtics record against the East`, `Celtics record against Western Conference teams`, and `Lakers record against the East` all return full-season records.
  - `team_record` can filter a list of opponent team abbreviations, but parser/execution do not create such a list for `East` or `West`.
  - `data/raw/teams/teams_reference.csv` has `conference` and `division` columns but currently only two rows in the local checkout: ATL and BOS.
- Existing support:
  - Direct opponent filtering is supported.
  - Opponent-quality buckets are supported using standings snapshots and team advanced data.
  - Team game logs include opponent team IDs/abbreviations.
- Gaps:
  - No parser slot for opponent conference.
  - No complete, documented team-conference metadata contract for historical and current seasons.
  - Need a metadata/filter representation such as `opponent_group={"type":"conference","value":"East"}` or an `opponent` list plus `applied_filters` display.

## 5. Data/model support

| Needed behavior | Available? | Source/route | Notes |
|---|---|---|---|
| Position-filtered player leaderboard | Yes, with parser gaps | `season_leaders(position=...)`, `data/raw/rosters/{season}.csv` | Already works for documented `among centers` and `among guards` forms. |
| Rookie leaderboard | Partially available, not shipped | `data/raw/rosters/{season}.csv` has `experience_years` | Roster contract currently describes enrichment/future roster-aware filters, not rookie leaderboard execution. |
| League bench/starter leaderboard | Data available, not shipped | `player_game_starter_roles` plus `player_game_stats` | Requires role-aware `season_leaders` design, coverage policy, caveats, and tests. |
| Team bench scoring | Data available in pieces, not shipped | `player_game_starter_roles` plus player game logs, probably new command/helper | Needs team-scoped bench aggregation and result contract; cannot be represented by team game rows. |
| Full-name player comparison | Yes | `player_compare` route plus entity resolver | Parser extraction gap only. |
| Personal-foul leaderboard | Raw data available, not shipped | `player_game_stats.pf`; `season_leaders` lacks PF aggregation/alias | Need product wording decision before support. |
| Opponent-conference team record | Partially available, not shipped | `team_game_stats.opponent_team_abbr`; incomplete `data/raw/teams/teams_reference.csv` | Needs complete team conference mapping and historical semantics. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| Option A | One combined P2 cleanup wave: comparison routing, PF support/block, opponent-conference support/block, all position/role support/block. | Can take the corpus from 187/195 to 195/195 in one PR-sized push if tightly scoped to boundaries. | Mixes true support, unsupported boundaries, and possible data/model work; higher chance of broad parser regressions. | Medium-high. | Not preferred unless limited to parser support plus explicit blockers only. |
| Option B | Split waves: 7A boundary cleanup; 7B player comparison; 7C actual position/conference support if approved. | Lowest regression risk and clean review history. | Leaves one or two obvious small fixes for later and prolongs the failing corpus state. | Low. | Good if time is not a concern. |
| Option C | Support obvious small fixes now and boundary the rest. Support position noun-prefix leaderboards and full-name player comparisons; return explicit unsupported/no-result for rookie, bench/starter league, team bench, personal fouls, and opponent conference. | Resolves all eight failures without new data contracts; matches current product truth; high user value by removing broad wrong answers. | Requires careful parser guardrails and corpus updates; actual rookie/role/PF/conference support remains deferred. | Medium-low. | Recommended. |

## 7. Recommended execution scope

- Exact goal:
  - Move the remaining eight Wave 6B failures from broad wrong answers or route mismatch to either supported, execution-backed results or explicit product-boundary `no_result`s.
- Cases to fix:
  - `centers_rebound_leaders_wave4`: support noun-prefix/question-form position leaderboards through existing `season_leaders(position=...)`.
  - `lebron_durant_comparison_wave4`: route full-name `A vs B comparison` to `player_compare`.
- Cases to mark unsupported/no-result, if any:
  - `rookie_scoring_leaders_wave4`: unsupported filter, e.g. `rookie_leaderboard`.
  - `bench_scoring_leaders_wave4`: unsupported filter, e.g. `role_leaderboard`.
  - `starter_assist_leaders_wave4`: unsupported filter, e.g. `role_leaderboard`.
  - `celtics_bench_scoring_boundary_wave4`: unsupported filter, e.g. `team_bench_scoring`.
  - `personal_foul_leaders_wave4`: unsupported stat boundary, unless a product decision explicitly approves PF leaderboard support in the same wave.
  - `celtics_against_east_record_wave4`: unsupported filter, e.g. `opponent_conference`.
- Files to change:
  - `src/nbatools/commands/_parse_helpers.py`: position prefix extraction; optional unsupported-boundary detectors for rookie, role leaderboard, personal foul leaderboard, opponent conference.
  - `src/nbatools/commands/_matchup_utils.py`: full-name player comparison extraction through resolver-aware logic.
  - `src/nbatools/commands/natural_query.py`: wire new parser slots to route kwargs and unsupported filters.
  - `src/nbatools/commands/_natural_query_execution.py`: user-facing messages for new unsupported filter IDs.
  - Possibly `src/nbatools/commands/_leaderboard_utils.py` if stat/boundary detection is cleaner there.
  - Do not change frontend rendering or backend answer phrase enrichment.
- Tests to add:
  - Parser tests for `Which centers have the most rebounds`, `guard scoring leaders`, `forwards FG% leaders`, and `point guard assist leaders` setting `position`.
  - Data-backed query-service or UI-failure tests proving position metadata/caveats and no broad fallback.
  - Parser and data-backed tests for `LeBron James vs Kevin Durant comparison` routing to `player_compare`.
  - Guardrails for `Jokic stats vs Embiid` / `show Jokic games vs Embiid` staying player-game routes.
  - Unsupported-boundary tests for rookie, bench players, starter leaders, Celtics bench scoring, personal fouls, and Celtics against East.
- Corpus updates:
  - Update target expectations after behavior changes.
  - Harden existing nearby position cases with `result.metadata.position_filter` assertions so they do not continue to pass as broad leaderboards.
  - Align the center expected value with the existing canonical position group contract (`centers`) unless implementation deliberately standardizes singular metadata.
- Findings updates:
  - Mark AQ-018 partially fixed: position noun-prefix support fixed; role/rookie/team-bench fixed as expected unsupported.
  - Mark AQ-019 fixed.
  - Mark AQ-022 fixed as expected unsupported unless PF support is explicitly approved.
  - Mark AQ-023 fixed as expected unsupported unless opponent-conference support is approved.
- Harness validation:
  - Targeted QA run for the eight failed cases.
  - Adjacent targeted run for nearby position and comparison cases.
  - Full 195-case QA run.
  - Standard local tests based on touched area: `make test-parser`, `make test-query`, then `make test-preflight` because `natural_query.py` and parser routing are high fan-in.
- Stop conditions:
  - Stop before implementing actual rookie, league role, team bench, PF, or opponent-conference support unless a product decision approves the needed contract in the wave.
  - Stop if full-name comparison extraction starts changing player-vs-player-as-opponent routes.
  - Stop if a position filter lacks roster coverage for a target season and would silently broaden; return no-match or explicit unsupported instead.
  - Stop if opponent-conference support would require ad hoc incomplete team metadata.

## 8. Risks / open decisions

- Parser ambiguity risks:
  - Full-name comparisons must not hijack `PLAYER stats/games vs PLAYER` routes.
  - Position words at query start can be ordinary nouns in other contexts; constrain to leaderboard/stat wording.
  - `East` and `West` can describe conference, geography, or team nicknames in historical contexts.
- Execution/regression risks:
  - Existing position tests use plural canonical values (`centers`, `guards`); the target corpus currently expects singular `center`.
  - Setting `role` outside player routes will intentionally convert broad results into unsupported boundaries; update docs/tests together.
  - `unsupported_filters` currently yields `filter_not_supported`; PF corpus currently expects `unsupported`, so choose reason semantics deliberately.
- Product decisions:
  - Should PF leaderboards be supported as fouls committed, or should all foul phrasing stay unsupported until fouls-drawn language is modeled?
  - Should rookie leaderboards be supported from roster `experience_years=0`, and if so what is the season/eligibility trust contract?
  - Should league role leaderboards and team bench scoring be a supported product surface?
  - Should opponent-conference filters support current-season only, historical seasons, relocated teams, and division filters?
- Data caveats:
  - `player_game_starter_roles` is authoritative for player-context role execution, but role-aware leaderboards are not opted into that contract today.
  - `data/raw/teams/teams_reference.csv` is incomplete in the local checkout, so opponent-conference filtering should not be supported from it yet.

## 9. Validation performed

Commands/probes run:

```text
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_6B_PLAYOFF_MATCHUP_ROUND_BOUNDARIES_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_6A_DEFENSIVE_ALIAS_COMPLETION_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_4_RETURN_PACKAGE.md
sed -n '1,220p' outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.md
rg -n -C 12 '<eight case ids>' qa/raw_query_answer_corpus.yaml
rg -n '<eight case ids>' outputs/raw_query_answer_qa/20260514T113039Z_wave6b_full/report.jsonl
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
rg -n 'position_filter|role|rookie|bench|starter|personal foul|fouls|against the East|Eastern Conference|comparison' docs/reference/query_catalog.md docs/reference/query_guide.md docs/reference/result_contracts/core_result_table_contracts.md
```

Direct parser/execution probes were run with `.venv/bin/python -c` using:

```text
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
```

Target case summaries:

```text
centers_rebound_leaders_wave4: parse route season_leaders, stat reb, position_filter None; execution ok leaderboard with no applied filters.
rookie_scoring_leaders_wave4: parse route season_leaders, stat pts, role/position None; execution ok broad points leaderboard.
bench_scoring_leaders_wave4: parse route season_leaders, stat pts, role None; execution ok broad points leaderboard.
starter_assist_leaders_wave4: parse route season_leaders, stat ast, role None; execution ok broad assists leaderboard.
celtics_bench_scoring_boundary_wave4: parse route game_finder, team BOS, stat pts, role None; execution ok team game table.
lebron_durant_comparison_wave4: parse route player_game_finder, player LeBron James, opponent_player Kevin Durant; execution ok finder with three rows.
personal_foul_leaders_wave4: parse route season_leaders, parsed stat None but route stat pts; execution ok broad points leaderboard.
celtics_against_east_record_wave4: parse route team_record, team BOS, no opponent/opponent_quality; execution ok full-season 56-26 record.
```

Nearby probe summaries:

```text
best ts% among centers this season: supported position-filtered season_leaders, metadata position_filter centers.
top scorers among guards since 2021: supported multi-season position-filtered season_leaders, metadata position_filter guards.
guard scoring leaders this season: broad unfiltered season_leaders, showing nearby corpus expectations are light.
Nikola Jokic as a starter this season: player_game_summary with role starter.
Malik Monk off the bench this season: player_game_summary with role bench.
LeBron vs Durant: player_compare ok.
LeBron James vs Kevin Durant: player_game_finder, same full-name extraction gap.
Jokic vs Embiid recent form: player_compare ok with last_n 10.
personal foul leaders this season: broad points leaderboard.
players with the most fouls: parse ValueError/unrouted, safer than broad fallback.
turnover leaders this season: supported season_leaders stat tov.
steal leaders this season: supported season_leaders stat stl.
Celtics record against Eastern Conference teams: full-season team_record, no opponent filter.
Celtics record against playoff teams last season: supported opponent_quality team_record, filtered 52-game sample.
```

Implementation/data files inspected:

```text
src/nbatools/commands/natural_query.py
src/nbatools/commands/_parse_helpers.py
src/nbatools/commands/_default_rules.py
src/nbatools/commands/_leaderboard_utils.py
src/nbatools/commands/_matchup_utils.py
src/nbatools/commands/season_leaders.py
src/nbatools/commands/season_team_leaders.py
src/nbatools/commands/team_record.py
src/nbatools/commands/data_utils.py
src/nbatools/commands/_natural_query_execution.py
src/nbatools/query_service.py
docs/reference/data_contracts.md
docs/reference/data_catalog.md
data/raw/rosters/2025-26.csv
data/raw/player_game_starter_roles/2025-26_regular_season.csv
data/raw/teams/teams_reference.csv
data/raw/standings_snapshots/2025-26_regular_season.csv
```

Data support spot checks:

```text
data/raw/rosters/2025-26.csv: 530 rows; position and experience_years present; 90 rows with experience_years=0.
data/raw/player_game_starter_roles/2025-26_regular_season.csv: 32,047 rows; 32,047 trusted rows; 1,225 unique games.
data/raw/player_game_stats/2025-26_regular_season.csv: includes pf.
data/raw/teams/teams_reference.csv: only 2 rows locally, despite conference/division columns.
season_leaders.build_result(stat="pf"): ValueError unsupported stat.
```

No production code, tests, corpus expectations, frontend rendering, or backend answer phrase enrichment were changed in this preflight.
