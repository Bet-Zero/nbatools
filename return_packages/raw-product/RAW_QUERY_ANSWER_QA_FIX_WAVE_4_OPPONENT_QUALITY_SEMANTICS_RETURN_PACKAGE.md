# Raw Query Answer QA Fix Wave 4: Opponent-Quality / Playoff-Team Semantics Return Package

## 1. Executive summary

- What was wrong: `What is the Celtics' record against playoff teams?` was parsed as `season_type=Playoffs`, so `team_record` aggregated playoff games instead of regular-season games against the playoff-team opponent bucket.
- Root cause: `detect_season_type()` treated any `playoff`, `playoffs`, or `postseason` token as actual playoff competition before opponent-quality semantics were considered.
- What changed: playoff-team opponent-quality phrases now stay `Regular Season` unless the query also contains explicit playoff-competition wording; phrase variants such as `postseason teams` and `teams that made the playoffs` map to the existing `playoff teams` bucket.
- Production code changed? yes.
- Tests added/updated: parser tests, opponent-quality propagation tests, and needs-data UI failure regressions.
- Corpus updated: target case now hard-asserts `54` games / `33-21`; added phrase-variant and playoff-record guard cases.
- Findings updated: AQ-001 is marked fixed.
- Latest harness run: `outputs/raw_query_answer_qa/20260512T124917Z/report.md`
- Remaining risk: the `playoff teams` bucket still uses the existing glossary policy, `conference_rank <= 10` from latest regular-season standings; frontend-only answer text remains a separate flagged family.

## 2. Reproduction evidence

- Query: `What is the Celtics' record against playoff teams?`
- Before: route `team_record`, status `ok`, parsed `season_type=Playoffs`, applied filter `Opponent quality=playoff teams`, result `2024-25 Playoffs`, `11` games, `6-5`.
- After: route `team_record`, status `ok`, parsed/result metadata `season_type=Regular Season`, applied filter `Opponent quality=playoff teams`, result `2025-26 Regular Season`, `54` games, `33-21`, `.611`.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | production | Added playoff-team opponent-quality detection, protected explicit playoff wording, and mapped phrase variants. |
| `tests/test_natural_query_parser.py` | tests | Added parser guards for Regular Season opponent-quality phrases and actual Playoffs phrases. |
| `tests/test_phase_e_opponent_quality_filters.py` | tests | Added route-kwargs propagation guard for `teams that made the playoffs`. |
| `tests/test_ui_failure_coverage.py` | tests | Added needs-data regressions for AQ-001, Tatum companion, and Celtics playoff-record guard. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Updated AQ-001 hard assertions and added phrase-variant/playoff-record guard cases. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | docs | Marked AQ-001 fixed and updated latest run counts/path. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | docs | Added Fix Wave 4 status and latest harness outputs. |
| `docs/reference/query_catalog.md` | docs | Documented the boundary between opponent-quality playoff-team phrases and actual playoff phrases. |

## 4. Behavior after fix

- Celtics record against playoff teams: `team_record`, `Regular Season`, `playoff teams` quality filter, `54` games, `33-21`.
- Teams-that-made-playoffs phrase: maps to `playoff teams`, remains `Regular Season`.
- Tatum/player companion: `player_game_summary`, `Regular Season`, `playoff teams` quality filter, `12` games in the current regular-season sample.
- Actual playoff record/history phrases: `Celtics playoff record` stays `team_record` with `Playoffs`; `Lakers playoff history` stays `playoff_history`.
- Opponent-quality definitions: unchanged; `playoff teams` remains the existing standings-snapshot top-10 conference policy.

## 5. Test coverage

- `tests/test_natural_query_parser.py`: proves playoff-team opponent-quality phrases stay Regular Season; phrase variants map to `playoff teams`; explicit `playoff record`, `record in the playoffs`, and `playoff history` stay Playoffs.
- `tests/test_phase_e_opponent_quality_filters.py`: proves the phrase variant propagates into `route_kwargs` as `opponent_quality=playoff teams` with Regular Season.
- `tests/test_ui_failure_coverage.py`: proves AQ-001 returns `54/33/21`, Tatum companion uses a 12-game regular-season sample, and Celtics playoff record still returns `11/6/5` Playoffs.

## 6. QA harness validation

- Targeted command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case celtics_record_playoff_teams`
- Targeted result: `outputs/raw_query_answer_qa/20260512T124856Z/report.md`; 1 case, status `ok`, expectation cases `pass: 1`, failed IDs `none`.
- Phrase/guard command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case celtics_record_teams_made_playoffs --case celtics_playoff_record`
- Phrase/guard result: `outputs/raw_query_answer_qa/20260512T124905Z/report.md`; 2 cases, status `ok: 2`, expectation cases `pass: 2`, failed IDs `none`.
- Full command: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
- Full result: `outputs/raw_query_answer_qa/20260512T124917Z/report.md`; 80 cases, result statuses `ok: 69`, `no_result: 5`, `error: 6`, expectation cases `pass: 80`, expectation checks `pass: 401`, failed IDs `[]`.
- Suspicious flags: `playoff_teams_playoff_season_type` is gone. Current flags are `missing_backend_answer_text: 22` and `top_performance_high_points: 1`; total suspicious flag cases are 23 because two new passing corpus cases are summary-style cases without backend answer text.

## 7. Standard validation

Backend:

- `make PYTEST=.venv/bin/pytest test-parser` -> `626 passed in 76.06s`.
- `.venv/bin/pytest tests/test_ui_failure_coverage.py::TestOpponentQualityPlayoffTeamSemantics -n0` -> `3 passed in 5.07s`.
- `.venv/bin/pytest tests/test_phase_e_opponent_quality_filters.py -n0` -> `5 passed in 6.68s`.
- `make PYTEST=.venv/bin/pytest test-query` -> `695 passed in 173.81s`.
- `make PYTEST=.venv/bin/pytest test-preflight` -> `2677 passed, 1 xpassed in 361.08s`.

Harness:

- Targeted and full harness commands/results are listed in section 6.

Always:

- `git diff --check` -> no output.

Optional:

- `.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py tests/test_natural_query_parser.py tests/test_phase_e_opponent_quality_filters.py tests/test_ui_failure_coverage.py` -> `All checks passed!`

Note: bare `make test-parser` failed in this shell because `pytest` is not on PATH; the Make targets passed when run with `PYTEST=.venv/bin/pytest`.

## 8. Updated findings / next fix family recommendation

- AQ-001 status: fixed.
- Remaining highest-priority findings: AQ-002 top-performance data quality, AQ-006 non-scoring single-game top-performance product decision, AQ-008 team-scoped rolling-stretch product decision, and frontend answer-text extraction.
- Recommended next fix family: top-performance data quality for the Bam Adebayo 83-point outlier, unless product-boundary decisions should be resolved first.
