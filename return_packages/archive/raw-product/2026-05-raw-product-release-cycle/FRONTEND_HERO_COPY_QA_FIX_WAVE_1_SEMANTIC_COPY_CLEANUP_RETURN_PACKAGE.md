# Frontend Hero / Copy QA Fix Wave 1: Semantic Copy Cleanup Return Package

## 1. Executive summary

- What was wrong: one guard-position leaderboard source case rendered as broad FG%; fewest-points-allowed hero copy said `most`; unsupported no-result primary messages were generic/stat-centric.
- What changed: fixed `among guards?` position parsing, exposed leaderboard `ascending` metadata, updated opponent-points leaderboard hero copy, and added boundary-specific no-result copy for unsupported filters.
- Production frontend rendering changed? yes.
- Backend behavior changed? yes.
- Tests added/updated: parser, data-backed query coverage, frontend rendering tests, no-result copy tests, raw/frontend QA corpus checks.
- Raw QA source run: `outputs/raw_query_answer_qa/20260515T021820Z/report.jsonl`
- Frontend-copy run: `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`
- Remaining risk: no screenshot/visual QA was run by design; no backend `answer_phrase` enrichment was added; no-result detail notes still include backend diagnostic `blocked:` IDs, but primary title/message copy is product-facing.

## 2. Findings addressed

| Finding | Cases | Status | Notes |
|---|---|---|---|
| FCQ-001 | `guards_fg_percentage_leaders` | Fixed | Exact query now returns `position_filter=guards`, an applied Position filter, and a guard-filtered top row. |
| FCQ-002 | `fewest_points_allowed_team_leader`; guardrails `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | Fixed | Hero copy uses `metadata.ascending` for `opponent_pts_per_game`. |
| FCQ-003 | `personal_foul_leaders_wave4`, `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4`; utility test for `team_bench_scoring` | Fixed | Primary no-result copy now names the unsupported product boundary. |

## 3. Behavior before/after

### FCQ-001 position filter source/visibility

- Before: `What players have the best field goal percentage among guards?` returned unfiltered FG% leaders, `position_filter=null`, no Position chip, top row `Jaxson Hayes`.
- After: same query returns `position_filter=guards`, applied filter `Position guards`, top row `Gary Payton II`, and frontend-copy soft checks pass.

### FCQ-002 opponent metric hero wording

- Before: fewest points allowed returned Boston first but hero said `most opponent pts per game`.
- After: fewest case renders `The Boston Celtics allowed the fewest points per game...`; most/opponent-PPG cases render `allowed the most points per game`.

### FCQ-003 unsupported no-result guidance

- Before: primary messages included `Pf is not available for this query.`, `Points is not available...`, and `Assists is not available...`.
- After: primary messages include `Personal-foul leaderboards are not supported yet.`, `Rookie leaderboards are not supported yet.`, `League-wide starter/bench leaderboards are not supported yet.`, and `Team bench-scoring summaries are not supported yet.`

## 4. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | Backend fix | Allow `among <position>?` punctuation boundary. |
| `src/nbatools/query_service.py` | Metadata | Expose executed `ascending` sort direction. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Frontend copy | Direction-aware opponent-points hero copy. |
| `frontend/src/components/noResultDisplayUtils.ts` | Frontend copy | Boundary-specific unsupported messages and `pf` humanization. |
| `frontend/src/components/NoResultDisplay.tsx` | Frontend copy | Boundary-specific no-result titles. |
| `frontend/src/test/*` | Tests/harness | Added renderer/copy tests and soft-check alternative support. |
| `qa/raw_query_answer_corpus.yaml` | QA corpus | Hard-assert guard position and opponent leaderboard direction metadata. |
| `qa/frontend_copy_corpus.yaml` | QA corpus | Fresh source run plus less brittle equivalent soft-check alternatives. |
| `docs/planning/raw-product/*` and `docs/reference/*` | Docs | Recorded fix status, latest runs, exact supported guard phrasing, and `ascending` metadata. |

## 5. Test coverage

- `tests/test_natural_query_parser.py`: exact guard FG% query, center TS%, and guard scorer `among` guardrails.
- `tests/test_ui_failure_coverage.py`: data-backed guard FG% position metadata/applied filter; opponent-points ascending true/false metadata.
- `frontend/src/test/ResultRenderer.test.tsx`: fewest and most points-allowed hero wording plus table header guardrails.
- `frontend/src/test/UIComponents.test.tsx`: personal-foul, rookie, role, and team bench-scoring no-result primary copy.
- `frontend/src/test/frontendCopyQaHarness.tsx`: soft-check alternatives for harmless wording variants.

## 6. QA validation

- Targeted raw QA:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case guards_fg_percentage_leaders --case centers_rebound_leaders_wave4`
  Result: `outputs/raw_query_answer_qa/20260515T021801Z`, 2 cases, statuses `ok: 2`, expectations `pass: 2`.
- Full raw QA:
  `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml`
  Result: `outputs/raw_query_answer_qa/20260515T021820Z`, 195 cases, statuses `ok: 165`, `no_result: 22`, `error: 8`, expectations `pass: 195`, suspicious flags `0`.
- Frontend-copy QA:
  `cd frontend && npm run qa:frontend-copy`
  Result: `outputs/frontend_copy_qa/20260515T024718Z`, 59 cases rendered, render failures `0`, missing backend records `0`, soft checks `pass: 156`, `fail: 0`, `not_checked: 0`.

## 7. Standard validation

- `make PYTEST=.venv/bin/pytest test-parser`: 705 passed in 154.50s.
- `make PYTEST=.venv/bin/pytest test-query`: 726 passed in 272.43s.
- `make PYTEST=.venv/bin/pytest test-api`: 50 passed in 5.42s.
- `make PYTEST=.venv/bin/pytest test-preflight`: 2803 passed, 1 xpassed in 560.26s.
- `.venv/bin/ruff check src/nbatools/commands/_parse_helpers.py src/nbatools/query_service.py tests/test_natural_query_parser.py tests/test_ui_failure_coverage.py`: all checks passed.
- `cd frontend && npm test -- src/test/ResultRenderer.test.tsx src/test/UIComponents.test.tsx src/test/frontendCopyQaReport.test.tsx`: 3 files passed, 90 tests passed.
- `cd frontend && npm run build`: passed; Vite emitted the existing large-chunk warning.
- `cd frontend && npm run lint`: passed with one existing warning in `frontend/src/ReviewPage.tsx` (`react-hooks/exhaustive-deps`).
- `git diff --check`: passed.

## 8. Next recommendation

- Manually review the latest frontend-copy report once more, focused on the three fixed families.
- Promote the FCQ cases into hard tests where they are now stable; this wave already added focused hard coverage for the core defects.
- Keep soft-check alternatives for accepted wording variants rather than exact hero sentence snapshots.
- Start screenshot/visual QA after semantic-copy review is accepted; this wave intentionally did not add Playwright or screenshots.
