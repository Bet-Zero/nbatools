# Record / Date / Stat-Context Routing Preflight Return Package

## 1. Executive summary

- Main root-cause families: team summary intent phrasing, auxiliary-word team alias collision, explicit-date `since` window semantics, and standalone player stat-context preservation.
- Which cases are true bugs: `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, and `celtics_road_record_since_jan_1_wave5` are supported-route bugs. `curry_last_20_from_three_wave5` is supportable with existing data, but needs a narrower product/parser decision because generic stat-only player queries currently route to finder.
- Which cases are product-boundary/expectation decisions: none need to become unsupported. The only decision is how narrowly to define standalone `from three` on a player last-N summary; the current corpus expectation is viable without frontend changes or backend answer phrase enrichment.
- Recommended next execution: Option B, split into Wave 8C1 for team record/date intent and Wave 8C2 for player record/stat context.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `lakers_how_did_road_last_season_wave5` | `How did the Lakers do on the road last season?` | `game_finder` / `ok` | Preserves `team=LAL`, `away_only=true`, `season=2024-25`; returns 25 finder rows. | `team_record` / `ok`, `summary` and `by_season`; road filter and 2024-25 relative season preserved. Stable data-backed assertion: Lakers road record in 2024-25 is 41 games, 19-22. | `how did X do` does not trigger summary/record intent. With no `record` token and no summary intent, single-team fallback is `game_finder`. |
| `jokic_possessive_triple_double_record_wave5` | `What was Jokic's record in games with a triple-double?` | `player_game_summary` / `no_result` / `no_match` | Resolves `player=Nikola Jokic` and `special_event=triple_double`, but also resolves `team=WAS` from the auxiliary word `was`; filtering Jokic to Washington returns no rows. | `player_game_summary` / `ok`, `summary` plus 34-row `game_log`, special-event filter. Minimum safe desired behavior is `team=None`; explicit current-team inference to DEN is not required for the data result. | Team alias table contains `was -> WAS`, and the parser scans the full query for team aliases. Existing WAS guard only clears `was out`, not question auxiliaries. |
| `celtics_road_record_since_jan_1_wave5` | `Celtics road record since January 1` | `team_record` / `ok` | Preserves team and road, but parses date as `2026-01-01 - 2026-01-01`; returns 1 game, 1-0. | `team_record` / `ok`, date window `2026-01-01 - 2026-04-12`, 24 games, 16-8. | `_extract_explicit_calendar_date` runs before the `since <month>` branch and treats all month-day phrases as single-day dates, even when preceded by `since` or `after`. |
| `curry_last_20_from_three_wave5` | `Curry last 20 games from three` | `player_game_summary` / `ok` | Correct player and last-20 sample; returns `summary`, `by_season`, and 20-row `game_log`; `summary.fg3m_avg=4.05`, but metadata has `stat=None`. | Keep `player_game_summary` and last-20 rows, expose `metadata.stat=fg3m` or equivalent structured stat context. | Standalone `from three` is only recognized in percentage-threshold parsing, not as made-threes context. A naive generic stat alias would risk changing player stat/timeframe queries from summary to finder. |

## 3. Nearby working cases

| Case/query | Behavior | Why it matters |
|---|---|---|
| `lakers_road_record_last_season`: `Lakers road record last season` | `team_record` / `ok`; road and `2024-25`; summary 41 games, 19-22. | Confirms team-record execution, road filter, and `last season` resolution are already correct. |
| `knicks_road_record`: `What is the Knicks road record this season?` | `team_record` / `ok`; away filter; summary 42 games. | Shows question form works when the explicit `record` token is present. |
| `team_road_record_leaders`: `Which teams have the best road record this year?` | `team_record_leaderboard` / `ok`; away filter. | Confirms road intent does not require wording changes outside the failing phrase family. |
| `worst_road_record_wave5`: `Who has the worst road record this season?` | `team_record_leaderboard` / `ok`; away filter and ascending/descending semantics are preserved. | Adjacent Wave 5 phrasing passes because `record` is explicit. |
| `record_when_jokic_triple_double`: `What is Denver's record when Nikola Jokic has a triple-double?` | `player_game_summary` / `ok`; `team=DEN`, special-event filter; 34 games, 24-10. | Confirms triple-double record-when execution is already supported. |
| `Jokic's record in games with a triple-double` direct probe | `player_game_summary` / `ok`; no team alias collision; 34 games. | Isolates the failing trigger to `What was`, not possessive player syntax itself. |
| `What is Jokic's record in games with a triple-double?` direct probe | `player_game_summary` / `ok`; no `WAS`; 34 games. | Confirms `what was` specifically collides with the Wizards abbreviation alias. |
| `jokic_triple_double_count` | `player_game_finder` count / `ok`; special-event filter; 34 finder rows. | Confirms special-event detection and data rows exist independent of summary route. |
| `thunder_since_all_star_record` | `team_record` / `ok`; start date `2026-02-16`, end `None`; 26 games. | Shows open-ended team-record date filtering works when the parser produces an open window. |
| `warriors_march_record` and `knicks_record_in_march_wave5` | `team_record` / `ok`; closed March window `2026-03-01 - 2026-03-31`. | Month-window parsing and team-record execution are healthy. |
| `specific_date_jan_1` | `top_player_games` / `ok`; exact single-day filter `2026-01-01 - 2026-01-01`. | The execution wave must preserve explicit `on January 1` single-day behavior while changing `since January 1`. |
| `best_offensive_teams_since_january` | `season_team_leaders` / `ok`; start date `2026-01-01`, end `None`. | Shows existing `since January` open-window support, but metadata currently labels only the start date. |
| `curry_5_threes_finder` | `player_game_finder` / `ok`; `stat=fg3m`, threshold `5.0`. | Made-threes aliases already work for threshold/finder intent. |
| `curry_5_threes_count` | Count with finder / `ok`; `fg3m min` filter. | Confirms count/finder threes behavior should be guarded during any stat-context change. |
| `curry_home_away_last_20_split_wave4` | `player_split_summary` / `ok`; last-20 window preserved. | Last-N player context is stable in non-stat summary surfaces. |
| `most_threes_single_game` | `top_player_games` / `ok`; `stat=fg3m`; Stephen Curry top row has 12 threes. | Top-performance threes aliases are healthy and should not be affected. |

## 4. Root-cause analysis

### Team record intent phrasing

- Findings: `How did the Lakers do on the road last season?` parses with `summary_intent=false`, `record_intent=false`, `team=LAL`, `away_only=true`, and `season=2024-25`. The route then falls through to the final single-team `game_finder` branch.
- Existing support: explicit record forms already pass, including `Lakers road record last season`, `Lakers away record last season`, `Knicks road record`, and road-record leaderboards.
- Gaps: `wants_summary()` recognizes some `how did X perform/play/...` forms, but not `how did X do` where `do` is the verb. A focused phrasing expansion should route team + how-did-do + no threshold/list/count intent to `team_record`, not `game_summary` or `game_finder`.

### Possessive player/team record-when

- Findings: the route and special-event detection are already correct. The failure comes from incorrect team context: `team=WAS` is inferred from the word `was` in `What was...`.
- Existing support: `What is Denver's record when Nikola Jokic has a triple-double?` returns 34 games, 24 wins, 10 losses. Direct probes without `was` also return 34 games with `team=None`.
- Gaps: team resolution needs a guard for auxiliary `was` in question text, or a safer abbreviation policy for `WAS`. Current code has a one-off `was out` guard but not a general `what was` guard. Do not infer DEN unless the execution wave explicitly decides metadata needs current-team context; the player-only route already produces the desired rows.

### Date-window team record

- Findings: `since January 1` produces `start_date=2026-01-01` and `end_date=2026-01-01`. Direct structured execution with `end_date=2026-04-12` returns the expected 24-game, 16-8 Celtics road sample.
- Existing support: `since All-Star break`, `since January`, and month windows all execute; exact-date top-performance queries correctly remain single-day filters.
- Gaps: `extract_date_range()` must distinguish `since/after/post <explicit calendar date>` from `on <explicit calendar date>`. The target expectation wants the end date closed to current data coverage (`current_through=2026-04-12`), not merely an open `None` end in metadata.

### Player stat context / from three

- Findings: player, last-N, route, and result sections are correct. The only failed assertion is `result.metadata.stat == fg3m`.
- Existing support: made-threes threshold/count/finder forms use `fg3m`; `from three over 40%` maps to `fg3_pct` in percentage-threshold context; the summary section already includes `fg3m_avg` and `fg3m_sum`.
- Gaps: standalone `from three` is not a general alias. Adding `three` globally would likely perturb many routes. A safer implementation is a narrow stat-context detector for player last-N summary phrasing, preserving `player_game_summary` while exposing `stat=fg3m`.

## 5. Product/data support

| Needed behavior | Available? | Source/route | Notes |
|---|---|---|---|
| Team road record summary for Lakers 2024-25 | yes | `team_record` | Existing passing case returns 41 games, 19-22. |
| `How did X do` summary intent | partial | parser/routing | Filters and data are available; only intent selection is wrong. |
| Jokic triple-double record summary | yes | `player_game_summary` | Existing route returns 34 games, 24-10 with or without explicit DEN when `WAS` is absent. |
| Avoid `was` auxiliary as Washington team | partial | `entity_resolution.py` / parser guards | Existing alias is useful for `WAS` shorthand but unsafe in question auxiliaries. |
| Celtics road record since Jan. 1 through current data | yes | `team_record` | Direct structured probe with `2026-01-01 - 2026-04-12` returns 24 games, 16-8. |
| Exact `on January 1` single-day behavior | yes and must preserve | `top_player_games` date parsing | Existing `specific_date_jan_1` should remain a guardrail. |
| Curry last-20 summary with three-point context | yes | `player_game_summary` | The summary already contains `fg3m_avg=4.05` and `fg3m_sum=81`; metadata lacks only the stat context. |
| Frontend rendering changes | no | existing result contracts | Existing `team_record` and `entity_summary` contracts cover the desired sections. |
| Backend answer phrase enrichment | no | QA policy | All four target cases use `frontend_hero_expected`; no backend answer text is required. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| Option A - One combined execution wave | Fix all four cases together. Likely touches `_parse_helpers.py`, `_date_utils.py`, `entity_resolution.py`, `natural_query.py`, parser/query/data-backed tests, corpus, and findings docs. | Fastest path to reducing the corpus from 6 failures to 2. One targeted harness pass can close AQ-025 through AQ-028. | Mixes team intent, date parsing, team alias resolution, and player stat-context routing in one PR. Any regression is harder to isolate. | Medium-high because parser/date/entity changes are high fan-in. | Not safest. Use only if time pressure is higher than isolation needs. |
| Option B - Split 8C1/8C2 | Wave 8C1: `lakers_how_did_road_last_season_wave5`, `celtics_road_record_since_jan_1_wave5`. Wave 8C2: `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`. | Keeps team/date changes separate from player/entity/stat-context changes. Easier targeted tests and rollback. Fits the observed root-cause families. | Requires two PR-sized units and two harness cycles. | Medium for 8C1 due date utility; medium for 8C2 due entity/stat routing. Lower combined operational risk than Option A. | Recommended. |
| Option C - Fix obvious gaps, defer ambiguous product decisions | Fix `how did`, `since Jan 1`, and `was` alias collision; defer Curry `from three` if product semantics are not accepted. | Lowest short-term parser risk. Avoids changing player stat/timeframe route policy. | Leaves the corpus failing and does not meet current AQ-028 expectation. Requires an explicit product-boundary note for a supportable query. | Low-medium. | Use only if the product decision is that standalone `from three` should not bind stat context on summaries. |

## 7. Recommended execution scope

- Exact goal: close AQ-025 through AQ-028 without frontend changes, backend answer-phrase enrichment, or expectation weakening.
- Cases to fix: all four target cases, split across two execution waves.
- Cases to mark unsupported/no-result, if any: none.
- Files to change:
  - Wave 8C1: likely `src/nbatools/commands/_parse_helpers.py`, `src/nbatools/commands/_date_utils.py`, possibly `src/nbatools/commands/natural_query.py` if current-through closure belongs outside the date helper.
  - Wave 8C2: likely `src/nbatools/commands/entity_resolution.py` or a parser guard in `natural_query.py`, plus a narrow stat-context detector/default in `_parse_helpers.py`, `_default_rules.py`, or `natural_query.py`.
  - Tests/docs/corpus after verified behavior: `tests/test_natural_query_parser.py`, `tests/test_query_service.py`, `tests/test_ui_failure_coverage.py`, `qa/raw_query_answer_corpus.yaml`, `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`, `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`, and relevant query catalog/guide entries.
- Tests to add:
  - Parser guards for `How did the Lakers do on the road last season?` -> `team_record`, away, `2024-25`.
  - Parser/date guards for `since January 1` -> start `2026-01-01`, end current data anchor, while `on January 1 2026` remains single-day.
  - Data-backed `team_record` regressions for Lakers 19-22 and Celtics 24-game, 16-8 road sample.
  - Parser guard that `What was Jokic's...` does not resolve `team=WAS`; keep `special_event=triple_double`.
  - Data-backed Jokic summary regression: 34 games, 24-10, 34 game-log rows, all triple doubles.
  - Parser/query guard for `Curry last 20 games from three`: route `player_game_summary`, `last_n=20`, `stat=fg3m`, no threshold filter.
  - Guardrails: `specific_date_jan_1`, `best_offensive_teams_since_january`, `WAS record ...` shorthand if intended to remain supported, `Curry 5+ threes`, and `Nikola Jokic assists since All-Star break`.
- Corpus updates: after targeted data-backed tests pass, mark the four cases `pass` and add stable hard assertions. Do not relax existing expectations.
- Findings updates: mark AQ-025 through AQ-028 fixed only after target and nearby harness cases pass.
- Harness validation:
  - Targeted: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case <four target ids>`
  - Nearby guardrails: include the nearby cases listed in section 3 for the active wave.
  - Full 243-case corpus after both waves.
- Stop conditions:
  - If fixing `since January 1` changes exact-date `on January 1 2026`, stop and narrow the date parser.
  - If the WAS guard breaks intentional `WAS` abbreviation queries, stop and add context-sensitive filtering instead of removing the alias outright.
  - If `from three` requires broad player stat-only route changes, stop and make the product decision explicit before touching expectations.

## 8. Validation performed

- Read prior packages: Wave 8A defensive aliases, Wave 8B playoff routing, and Wave 5 corpus expansion return packages.
- Read QA artifacts: `outputs/raw_query_answer_qa/20260516T084330Z/report.md` and `report.jsonl`.
- Read planning/reference docs: `RAW_QUERY_ANSWER_QA_FINDINGS.md`, `RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`, `query_catalog.md`, `query_guide.md`, and `core_result_table_contracts.md`.
- Inspected likely code paths: `natural_query.py`, `_parse_helpers.py`, `_default_rules.py`, `_date_utils.py`, `_natural_query_execution.py`, `team_record.py`, `player_game_summary.py`, `player_game_finder.py`, `query_service.py`, and `entity_resolution.py`.
- Inspected nearby tests: `tests/test_natural_query_parser.py`, `tests/test_ui_failure_coverage.py`, and `tests/test_query_service.py`.
- Ran report extraction probe:

```text
.venv/bin/python - <<'PY'
# Loaded outputs/raw_query_answer_qa/20260516T084330Z/report.jsonl,
# selected the four target IDs, and printed query, route/status,
# metadata, sections, sample rows, and failed checks.
PY
```

- Ran direct parse/execution probe:

```text
.venv/bin/python - <<'PY'
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

queries = [
    "How did the Lakers do on the road last season?",
    "What was Jokic's record in games with a triple-double?",
    "Curry last 20 games from three",
    "Celtics road record since January 1",
]
# Printed parse state, route_kwargs, execution route/status,
# metadata filters, and section counts for each query.
PY
```

- Ran variant and structured support probe:

```text
.venv/bin/python - <<'PY'
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query

# Probed Jokic variants with and without "was"; Lakers how-did variants;
# Celtics since-Jan variants; Curry from-three/threes variants.
# Also executed structured Jokic special-event summary with team=None and DEN,
# plus Celtics road team_record from 2026-01-01 to 2026-04-12.
PY
```

- Key probe summaries:
  - Lakers failing query: `game_finder` / `ok`; `away_only=true`, `season=2024-25`; no summary intent.
  - Jokic failing query: `player_game_summary` / `no_result`; `player=Nikola Jokic`, `special_event=triple_double`, wrong `team=WAS`.
  - Jokic without `was`: `player_game_summary` / `ok`; 34 games, 24-10.
  - Celtics failing query: `team_record` / `ok`; wrong end date `2026-01-01`.
  - Celtics direct closed date: `team_record` / `ok`; 24 games, 16-8 for `2026-01-01 - 2026-04-12`.
  - Curry failing query: `player_game_summary` / `ok`; last-20 rows present; `stat=None` despite `fg3m_avg=4.05`.

- No tests were run; this was preflight only.
- No production, test, corpus, or frontend files were changed.
