# Frontend-Copy QA Expansion Wave 1 Return Package

## 1. Executive summary

- What changed: expanded `qa/frontend_copy_corpus.yaml` from 59 to exactly 100 selected frontend-copy QA cases, refreshed the source backend run to the latest clean 243-case raw QA run, and added loose semantic/fragment soft checks for the added cases.
- Production code changed? no.
- Frontend rendering changed? no.
- Tests/harness changed: `qa:frontend-copy` now gates on render failures, missing backend records, soft-check failures, and unchecked soft checks.
- Frontend-copy corpus size before/after: 59 -> 100 selected cases.
- Source backend run: `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`.
- Latest frontend-copy run: `outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.md`.
- Backend safety loop: all requested slices passed with no failed IDs and no unexpected comparison failures reported.
- Remaining risk: selected DOM-copy coverage only, not all 243 raw backend cases and not visual layout/screenshot QA.
- Note: the prompt described 41 added IDs, but the enumerated list contained 40 unique IDs. To satisfy the exact 100-case acceptance criterion, this wave also selected adjacent Wave 5 supported-leaderboard case `which_player_assist_leaders_wave5`. No listed ID was missing or substituted.

## 2. Corpus expansion summary

| Bucket | Cases added | Purpose |
|---|---:|---|
| Supported leaderboard copy | 7 | Position-filtered, advanced-stat, defensive-stat, and question/fragment leaderboard phrasing. |
| Defensive/team allowed/opponent PPG copy | 5 | Allowed/gave-up/opponent-points copy and defensive threshold record phrasing. |
| Team record date/window copy | 5 | Road/home, last season, since-date, month, explicit season, and last-10 record context. |
| Player/entity/stat context copy | 5 | Possessive triple-double, threes/from-three, All-Star, wins context, and bench role copy. |
| Playoff/history copy | 6 | Matchup/history variants, Finals/history wording, appearance leaderboards, and second-round records. |
| Playoff unsupported boundary copy | 2 | Single-team Finals/conference-finals record unsupported boundaries. |
| Comparison copy | 5 | Imperative comparison, last-10/recent comparison, team comparison, and head-to-head record copy. |
| Unsupported boundary copy | 6 | Personal fouls, single-team advanced scalar, rookie leaderboard, team bench, opponent-West, and clutch/subjective boundaries. |

## 3. Soft-check coverage

| Family | Checks added | Why |
|---|---|---|
| Position/filtered leaderboards | Position fragments, stat abbreviations, filter chips, and absent `led the NBA` checks. | Protects filtered leaderboard heroes from sounding league-wide. |
| Advanced/stat leaderboards | TS%, eFG%, APG, BPG, and loose stat-name alternatives. | Verifies metric binding without hardcoding full hero sentences. |
| Defensive/opponent points | Allowed/gave-up/opponent points fragments plus absent scored-the-fewest/most checks where appropriate. | Guards against offensive wording for defensive metrics. |
| Team/date records | Team, record, season/date/window, and location filter fragments. | Verifies context survives from backend metadata into rendered DOM copy. |
| Player/entity/stat context | Player identity, metric/context fragments, and role/window phrasing. | Covers table-only and hero summary shapes. |
| Playoff/history | Team pair, playoff/series/Finals/round, era, and unsupported boundary fragments. | Guards high-risk matchup and round wording. |
| Comparisons | Compared entities, last-10/recent context, and `Edge / Difference` table header. | Verifies comparison shape and primary context. |
| Unsupported boundaries | No-result title/message/detail fragments and broad-fallback absent checks where useful. | Ensures unsupported product boundaries do not render as success copy. |

## 4. Gating behavior

- What now fails `qa:frontend-copy`: selected case count not equal to 100, rendered successes not equal to 100, render failures > 0, missing backend records > 0, soft-check failures > 0, or soft-check `not_checked` > 0.
- Why: the command should not write a report that looks operationally green while selected rendered-copy cases are missing, failing, or unchecked.
- Any exceptions: none. All 100 selected cases have checked soft checks.

## 5. Backend safety validation

| Slice | Result |
|---|---|
| `defensive_aliases` | 8 cases; statuses `ok: 8`; expectation cases `pass: 8`; failed IDs none. |
| `playoff_phrasing` | 12 cases; statuses `ok: 9`, `no_result: 3`; expectation cases `pass: 12`; failed IDs none. |
| `team_date_context` | 9 cases; statuses `ok: 9`; expectation cases `pass: 9`; failed IDs none. |
| `player_entity_stat_context` | 9 cases; statuses `ok: 9`; expectation cases `pass: 9`; failed IDs none. |
| `product_boundaries` | 11 cases; statuses `ok: 8`, `no_result: 3`; expectation cases `pass: 11`; failed IDs none. |
| Full raw corpus | Not rerun; frontend-copy source uses existing clean 243/243 run `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`. |

## 6. Frontend-copy validation

- Command: `npm run qa:frontend-copy` from `frontend/`.
- Report path: `outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.md`.
- Selected cases: 100.
- Rendered successfully: 100.
- Render failures: 0.
- Missing backend records: 0.
- Soft-check pass/fail/not_checked: `304/0/0`.
- Notable report findings: the first gated run rendered 100/100 but exposed five too-narrow fragments; those were revised to use DOM-visible abbreviations/window labels and rerun cleanly.

## 7. Standard validation

| Command | Result |
|---|---|
| `npm run qa:frontend-copy` | Passed; 1 test file, 4 tests; report `outputs/frontend_copy_qa/20260517T051450Z/frontend_copy_report.md`. |
| `npm test -- src/test/frontendCopyQaReport.test.tsx` | Passed; 1 test file, 4 tests. |
| `npm run lint` | Passed with 0 errors and 1 existing warning in `frontend/src/ReviewPage.tsx` for `react-hooks/exhaustive-deps`. |
| `git diff --check` | Passed with no output. |

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/frontend_copy_corpus.yaml` | Corpus update | Refresh source backend run and expand selected frontend-copy cases to 100 with soft checks. |
| `frontend/src/test/frontendCopyQaReport.test.tsx` | Harness test update | Gate frontend-copy QA on selected count, render/missing failures, soft-check failures, and unchecked cases. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Docs update | Record 100-case frontend-copy status, latest report, source run, and gating behavior. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | Docs update | Record 100-case frontend-copy checkpoint and remaining DOM-copy limitations. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Docs update | Record frontend-copy expansion wave status and updated next-wave framing. |
| `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_1_RETURN_PACKAGE.md` | New return package | Capture scope, validation, files changed, and next recommendation. |

## 9. Next recommendation

Choose frontend-copy expansion wave 2 for streak/finder/count shapes. The highest remaining DOM-copy gaps are streak tables, rolling stretches, finder/count outputs, game-summary logs, record-by-decade shapes, and team split/on-off no-result surfaces.
