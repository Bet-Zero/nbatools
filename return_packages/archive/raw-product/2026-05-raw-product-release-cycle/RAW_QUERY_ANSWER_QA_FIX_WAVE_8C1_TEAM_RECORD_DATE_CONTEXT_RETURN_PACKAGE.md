# Raw Query Answer QA Fix Wave 8C1: Team Record Intent + Since-Date Windows Return Package

## 1. Executive summary

- What was wrong: `How did the Lakers do on the road last season?` preserved team/road/season context but routed to `game_finder`; `Celtics road record since January 1` treated `January 1` as a single-day date instead of a since-date window.
- What changed: added a guarded single-team `how did TEAM do` W/L record intent, and parsed `since/after/post <explicit calendar date>` before exact single-day date extraction.
- Production code changed? yes.
- Tests added/updated: parser route/date guardrails in `tests/test_natural_query_parser.py`; data-backed regressions and adjacent guards in `tests/test_ui_failure_coverage.py`.
- Corpus updated: yes, only the two Wave 8C1 target cases were marked pass and strengthened with stable summary assertions.
- Findings updated: yes, AQ-025 and AQ-027 are marked fixed; AQ-026/AQ-028 remain open.
- Latest harness run: `outputs/raw_query_answer_qa/20260516T101507Z/report.md`.
- Remaining risk: low. The route rule is limited to single-team `how did ... do` phrasing with no explicit list/count/leaderboard/stat request; date changes are limited to `since/after/post` explicit month-day forms.

## 2. Target behavior before/after

### lakers_how_did_road_last_season_wave5

- Before: parse route `game_finder`; route kwargs preserved `team=LAL`, `away_only=true`, `season=2024-25`; execution returned `game_finder` / `ok` with 25 finder rows. Failed expectations: expected route `team_record`, expected shape `team_record`, missing `summary`.
- After: parse/execution route `team_record`; status `ok`; filters `Location=Away`, `Season=2024-25`; sections `summary` and `by_season`; summary is 41 games, 19 wins, 22 losses.

### celtics_road_record_since_jan_1_wave5

- Before: parse/execution route `team_record`; status `ok`; date window was `2026-01-01 - 2026-01-01`; summary was 1 game, 1-0. Failed expectations: expected date filter `2026-01-01 - 2026-04-12`, expected `result.metadata.end_date=2026-04-12`.
- After: parse/execution route `team_record`; status `ok`; filters `Location=Away`, `Date range=2026-01-01 - 2026-04-12`; summary is 24 games, 16 wins, 8 losses.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_date_utils.py` | production | Add `since/after/post <month day>` window parsing before exact single-day date extraction. |
| `src/nbatools/commands/natural_query.py` | production | Add guarded single-team `how did TEAM do` team-record routing. |
| `tests/test_natural_query_parser.py` | tests | Add parser regressions for target phrasing, list/finder guardrails, exact-date, month-window, and All-Star since-window behavior. |
| `tests/test_ui_failure_coverage.py` | tests | Add data-backed target regressions and adjacent team/date guardrails. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Mark the two target cases pass and add hard assertions for stable record totals. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Update latest corpus counts and mark AQ-025/AQ-027 fixed. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Add Fix Wave 8C1 status and validation artifacts. |
| `docs/reference/query_catalog.md` | docs | Document verified `how did TEAM do` and `since January 1` record examples. |
| `docs/reference/query_guide.md` | docs | Add user-facing examples for the fixed team/date phrasing. |
| `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8C1_TEAM_RECORD_DATE_CONTEXT_RETURN_PACKAGE.md` | docs | This return package. |

## 4. Test coverage

- `test_how_did_team_do_road_last_season_routes_to_team_record`: target parser route and preserved LAL/road/2024-25 context.
- `test_team_road_game_list_phrasing_stays_finder`: list/scores guardrails remain `game_finder`.
- `test_team_record_since_explicit_calendar_date_uses_since_window`: target parser date window is `2026-01-01 - 2026-04-12`.
- `test_explicit_on_calendar_date_remains_single_day`: exact `on January 1 2026` stays one day.
- `test_month_window_remains_closed_month_range`: `in March` remains `2026-03-01 - 2026-03-31`.
- `test_since_all_star_break_remains_open_since_window`: All-Star break stays open-ended.
- `test_how_did_lakers_do_road_last_season_returns_team_record`: data-backed Lakers target returns 41 games, 19-22.
- `test_team_record_since_explicit_calendar_date_uses_current_data_window`: data-backed Celtics target returns 24 games, 16-8.
- `test_team_record_location_and_date_guardrails`: nearby Knicks/Thunder/Warriors/Knicks team-record location/date cases still execute.
- Existing date guardrails in `test_specific_date_top_scorer_uses_game_level_date_filtered_result` and `test_working_date_window_cases_still_preserve_date_filters` also passed.

## 5. QA harness validation

Targeted 8C1 command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_how_did_road_last_season_wave5 --case celtics_road_record_since_jan_1_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T101436Z
Cases: 2
Result statuses: {'ok': 2}
Expectation cases: {'pass': 2}
Suspicious flag cases: 0
Informational flag cases: 2
Verified outlier cases: 0
Failed case IDs: none
```

Adjacent team/date command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_road_record_last_season --case knicks_road_record --case thunder_since_all_star_record --case warriors_march_record --case knicks_record_in_march_wave5 --case specific_date_jan_1 --case best_offensive_teams_since_january

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T101449Z
Cases: 7
Result statuses: {'ok': 7}
Expectation cases: {'pass': 7}
Suspicious flag cases: 0
Informational flag cases: 5
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T101507Z
Cases: 243
Result statuses: {'error': 10, 'no_result': 32, 'ok': 201}
Expectation cases: {'fail': 4, 'pass': 239}
Suspicious flag cases: 2
Informational flag cases: 148
Verified outlier cases: 1
Failed case IDs: jokic_possessive_triple_double_record_wave5, curry_last_20_from_three_wave5, players_personal_fouls_wave5, warriors_net_rating_single_team_wave5
```

- Latest output path: `outputs/raw_query_answer_qa/20260516T101507Z/report.md`
- Expectation checks: `pass: 1343`, `fail: 13`
- Remaining failed IDs: `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`

## 6. Standard validation

Focused parser/query tests:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "how_did_team_do or road_game_list or since_explicit_calendar_date or explicit_on_calendar_date or month_window_remains or since_all_star_break or team_record_road_last_season or team_record_away_last_season or team_record_explicit_season_road" -n0
11 passed, 187 deselected in 16.54s

.venv/bin/pytest tests/test_ui_failure_coverage.py -k "how_did_lakers_do or since_explicit_calendar_date or team_record_location_and_date_guardrails or lakers_road_record_last_season or specific_date_top_scorer or working_date_window_cases" -n0
9 passed, 115 deselected in 14.16s
```

Required parser/query targets:

```text
make PYTEST=.venv/bin/pytest test-parser
722 passed in 462.12s (0:07:42)

make PYTEST=.venv/bin/pytest test-query
737 passed in 1095.92s (0:18:15)
```

Static/diff checks:

```text
.venv/bin/ruff check src/nbatools/commands/_date_utils.py src/nbatools/commands/natural_query.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
All checks passed!

git diff --check
passed with no output
```

## 7. Updated findings / next recommendation

- AQ-025 status: fixed.
- AQ-027 status: fixed.
- Remaining failed IDs: `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.
- Recommended next phase: Wave 8C2 for AQ-026/AQ-028 player/entity/stat context, then AQ-030/AQ-031 product-boundary cleanup/decision work.
