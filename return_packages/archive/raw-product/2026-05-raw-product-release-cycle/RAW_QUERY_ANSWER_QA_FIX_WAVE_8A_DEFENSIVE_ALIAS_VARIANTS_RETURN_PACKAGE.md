# Raw Query Answer QA Fix Wave 8A: Defensive / Opponent-Points Alias Variants Return Package

## 1. Executive summary

- What was wrong: Three AQ-024 defensive variants were routing to supported surfaces but binding to team points. `gave up the fewest points per game` and `teams allowing the fewest points` used `stat=pts`; `held teams to under 100 points` used a `pts max` threshold.
- What changed: Added focused defensive/opponent-points leaderboard aliases and broadened opponent-points threshold extraction for `held teams`, `held opponents below`, `allowed under`, and `gave up under/fewer than` forms.
- Production code changed? yes.
- Tests added/updated: parser guardrails plus data-backed query regressions in `tests/test_natural_query_parser.py` and `tests/test_ui_failure_coverage.py`.
- Corpus updated: yes, the three AQ-024 cases are now manual-review `pass` with stronger hard assertions.
- Findings updated: yes, AQ-024 is marked fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260516T075849Z/report.md`.
- Remaining risk: The remaining 8 corpus failures are unrelated families: playoff phrasing, record/date/stat-context routing, personal-foul boundary, and single-team net-rating product decision.

## 2. Target behavior before/after

### team_gave_up_fewest_ppg_wave5

- Before: Query `Which team gave up the fewest points per game?` returned `season_team_leaders`, status `ok`, `stat=pts`, `ascending=true`, no applied filters, and ranked Brooklyn team scoring first.
- After: Returns `season_team_leaders`, status `ok`, `stat=opponent_pts_per_game`, `ascending=true`, no applied filters, and ranks Boston first by lowest opponent PPG.

### teams_allowing_fewest_points_wave5

- Before: Query `teams allowing the fewest points` returned `season_team_leaders`, status `ok`, `stat=pts`, `ascending=true`, no applied filters, and ranked Brooklyn team scoring first.
- After: Returns `season_team_leaders`, status `ok`, `stat=opponent_pts_per_game`, `ascending=true`, no applied filters, and ranks Boston first by lowest opponent PPG.

### lakers_held_teams_under_100_wave5

- Before: Query `What was the Lakers record when they held teams to under 100 points?` returned `team_record`, status `ok`, `stat=pts`, applied filter `pts max=99.9999`, and summarized an 0-8 Lakers scoring-under-100 sample.
- After: Returns `team_record`, status `ok`, `stat=opponent_pts`, applied filter `OPP PTS max=99.9999`, and matches the canonical held-opponents-under-100 sample: 7 games, 7 wins, 0 losses.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_leaderboard_utils.py` | production | Added defensive leaderboard aliases for `allow/allowing/gave up/giving up` fewest/most points variants. |
| `src/nbatools/commands/_parse_helpers.py` | production | Broadened opponent-points threshold extraction for `held teams`, below/under variants, and `gave up under/fewer than` forms while preserving scoring guardrails. |
| `src/nbatools/commands/season_team_leaders.py` | production | Added structured stat-alias parity for the new opponent-points leaderboard phrases. |
| `tests/test_natural_query_parser.py` | tests | Added parser coverage for target aliases and guardrails. |
| `tests/test_ui_failure_coverage.py` | tests | Added data-backed regressions for AQ-024 leaderboard and threshold behavior. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Marked target cases pass and added hard assertions for metadata/top rows/summary sample. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Marked AQ-024 fixed and updated latest run counts. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Added Fix Wave 8A status, harness paths, and next recommendation. |
| `docs/reference/query_catalog.md` | docs | Documented verified defensive wording variants. |
| `docs/reference/query_guide.md` | docs | Added user-facing examples for gave-up/allowing/held-teams defensive wording. |

## 4. Test coverage

- `test_gave_up_fewest_points_team_leaderboard_uses_opponent_ppg`: target fewest/gave-up leaderboard maps to `opponent_pts_per_game` ascending.
- `test_gave_up_most_points_team_leaderboard_uses_opponent_ppg_descending`: gave-up/most maps to `opponent_pts_per_game` descending.
- `test_teams_allowing_fewest_points_team_leaderboard_uses_opponent_ppg`: target allowing/fewest fragment maps to `opponent_pts_per_game` ascending.
- `test_held_teams_under_points_record_maps_to_opponent_points`: target held-teams record threshold maps to `opponent_pts max`.
- `test_team_scored_under_points_stays_team_points`: scoring-under guardrail remains team `pts`.
- Existing `test_opponent_ppg_leaders_route_to_team_leaderboard`, `test_bare_ppg_leaders_stays_player_leaderboard`, and `test_best_defensive_rating_stays_defensive_rating` guard prior behavior.
- `test_lakers_record_holding_teams_under_100_matches_opponents_alias`: data-backed held-teams wording matches canonical held-opponents semantics.
- `test_wave5_defensive_fewest_aliases_rank_opponent_ppg`: data-backed target leaderboard aliases rank Boston first by opponent PPG.
- Existing data-backed defensive tests continue covering fewest points allowed, most points allowed, opponent PPG, and Knicks allowed-under-110 behavior.

## 5. QA harness validation

Targeted AQ-024 command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case team_gave_up_fewest_ppg_wave5 --case lakers_held_teams_under_100_wave5 --case teams_allowing_fewest_points_wave5

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T075816Z
Cases: 3
Result statuses: {'ok': 3}
Expectation cases: {'pass': 3}
Suspicious flag cases: 0
Informational flag cases: 3
Verified outlier cases: 0
Failed case IDs: none
```

Adjacent defensive command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case fewest_points_allowed_team_leader --case most_points_allowed_team_leaders_wave4 --case opponent_ppg_leaders_wave4 --case knicks_allowed_under_110_record --case lakers_held_opponents_under_100_record

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T075832Z
Cases: 5
Result statuses: {'ok': 5}
Expectation cases: {'pass': 5}
Suspicious flag cases: 0
Informational flag cases: 5
Verified outlier cases: 0
Failed case IDs: none
```

Full corpus command/result:

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

Wrote raw query answer QA report: outputs/raw_query_answer_qa/20260516T075849Z
Cases: 243
Result statuses: {'error': 10, 'no_result': 33, 'ok': 200}
Expectation cases: {'fail': 8, 'pass': 235}
Suspicious flag cases: 3
Informational flag cases: 147
Verified outlier cases: 1
Failed case IDs: lakers_how_did_road_last_season_wave5, jokic_possessive_triple_double_record_wave5, curry_last_20_from_three_wave5, celtics_road_record_since_jan_1_wave5, best_second_round_record_since_2010_wave5, lakers_celtics_playoff_matchup_history_wave5, players_personal_fouls_wave5, warriors_net_rating_single_team_wave5
```

- Latest output path: `outputs/raw_query_answer_qa/20260516T075849Z/report.md`
- Expectation counts: cases `pass: 235`, `fail: 8`; checks `pass: 1315`, `fail: 25`.
- Remaining failed IDs: `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `celtics_road_record_since_jan_1_wave5`, `best_second_round_record_since_2010_wave5`, `lakers_celtics_playoff_matchup_history_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.
- Suspicious flags: 3, unchanged case family from the pre-fix Wave 5 run.

## 6. Standard validation

Focused parser tests:

```text
.venv/bin/pytest tests/test_natural_query_parser.py -k "held_teams_under or scored_under or gave_up_fewest or gave_up_most or teams_allowing_fewest or points_allowed_team_leaderboard or most_points_allowed or opponent_ppg_leaders or team_scoring_fewest or team_scoring_most or bare_ppg or defensive_rating" -n0
12 passed, 174 deselected in 10.98s
```

Focused data-backed query tests:

```text
.venv/bin/pytest tests/test_ui_failure_coverage.py -k "holding_teams_under_100 or wave5_defensive_fewest_aliases or points_allowed_leaderboard or most_points_allowed_leaderboard or opponent_ppg_leaders or knicks_record_allowing_under_110 or holding_opponents_under_100" -n0
8 passed, 108 deselected in 10.12s
```

Required parser/query targets:

```text
make PYTEST=.venv/bin/pytest test-parser
710 passed in 195.06s (0:03:15)

make PYTEST=.venv/bin/pytest test-query
729 passed in 322.36s (0:05:22)
```

Static/diff checks:

```text
.venv/bin/ruff check src/nbatools/commands/_leaderboard_utils.py src/nbatools/commands/_parse_helpers.py src/nbatools/commands/season_team_leaders.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py
All checks passed!

git diff --check
passed with no output
```

## 7. Updated findings / next recommendation

- AQ-024 status: fixed.
- Remaining failed IDs: `lakers_how_did_road_last_season_wave5`, `jokic_possessive_triple_double_record_wave5`, `curry_last_20_from_three_wave5`, `celtics_road_record_since_jan_1_wave5`, `best_second_round_record_since_2010_wave5`, `lakers_celtics_playoff_matchup_history_wave5`, `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`.
- Recommended next phase: fix AQ-029 playoff phrasing next, then the record/date/stat-context group (AQ-025 through AQ-028). Treat AQ-030 and AQ-031 as product-boundary cleanup/decision work.
