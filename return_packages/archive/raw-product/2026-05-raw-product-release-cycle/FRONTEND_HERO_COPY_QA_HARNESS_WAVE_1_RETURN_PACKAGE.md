# Frontend Hero / Copy QA Harness Wave 1 Return Package

## 1. Executive summary

- What changed: added a selected frontend-copy QA corpus, a Vitest/jsdom report harness that renders real `ResultEnvelope` plus `ResultRenderer` components from backend QA JSONL rows, an intentional npm runner, and harness-plan documentation.
- Production frontend rendering changed? no.
- Backend behavior changed? no.
- Tests added/updated: added `frontend/src/test/frontendCopyQaReport.test.tsx` and harness utility coverage for corpus loading, backend record matching, representative rendering, and gated report generation.
- Selected frontend-copy cases: 59.
- Latest frontend-copy run: `outputs/frontend_copy_qa/20260514T153729Z/`.
- Render failures: 0.
- Soft check failures: 5 report-only misses; not treated as test failures.
- Recommended next step: manually review `frontend_copy_report.md`, starting with the five soft-check misses and then the highest-risk families.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `qa/frontend_copy_corpus.yaml` | Added | Defines the Wave 1 selected 59-case frontend-copy review subset, source backend run, review focus, and lightweight semantic fragments. |
| `frontend/src/test/frontendCopyQaHarness.tsx` | Added | Loads the corpus and backend JSONL, rehydrates `QueryResponse`, renders actual frontend result components, extracts visible copy, runs soft checks, and writes JSONL/Markdown/summary reports. |
| `frontend/src/test/frontendCopyQaReport.test.tsx` | Added | Provides harness tests and the gated report-writing test path used by the npm runner. |
| `frontend/package.json` | Updated | Adds `npm run qa:frontend-copy` as the intentional report-generation command. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Documents the frontend-copy QA approach, corpus path, output path, latest run, and review process. |
| `return_packages/raw-product/FRONTEND_HERO_COPY_QA_HARNESS_WAVE_1_RETURN_PACKAGE.md` | Added | Summarizes this wave. |

## 3. Selected frontend-copy corpus

- Corpus path: `qa/frontend_copy_corpus.yaml`
- Source backend run: `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl`
- Case count: 59
- Category coverage: team record, player summary, record-when, without-player, splits, top performances, player leaderboards, team leaderboards, playoff history, playoff matchup/history, comparison, and no-result/unsupported boundaries.
- Notable substitutions: none. All selected IDs matched the backend QA JSONL.

The corpus intentionally uses lightweight fragments such as entity names, filter phrases, and metric labels. It does not lock exact hero sentences for every case.

## 4. Harness behavior

- Input: `qa/frontend_copy_corpus.yaml` plus `outputs/raw_query_answer_qa/20260514T125056Z/report.jsonl`.
- Rendering method: Vitest/jsdom renders `ResultEnvelope` and `ResultRenderer` with `displayMode="review"` from rehydrated frontend `QueryResponse` objects.
- Extracted fields: shape/pattern, full visible text, hero text, supporting text, envelope badges, context chips, applied filter chips, headings, table headers, first table row text, no-result title/message/details/suggestions, and rendered notes/caveats.
- Report outputs: `frontend_copy_report.jsonl`, `frontend_copy_report.md`, and `summary.json` under `outputs/frontend_copy_qa/<run_id>/`.
- Soft checks: report-only checks for configured visible fragments, table header fragments, filter chip fragments, and absent fragments.
- Limitations: jsdom does not validate visual hierarchy, wrapping, overlap, screenshots, or responsive layout. Soft-check misses are review cues, not confirmed defects.

## 5. Latest frontend-copy run summary

- Run ID: `20260514T153729Z`
- Output path: `outputs/frontend_copy_qa/20260514T153729Z/`
- Cases: 59
- Rendered successfully: 59
- Render failures: 0
- Missing backend records: 0
- Soft check counts: `pass: 151`, `fail: 5`, `not_checked: 0`
- Cases needing manual review: all 59 selected cases are marked `unreviewed`

Report-only soft-check misses in the latest run:

- `guards_fg_percentage_leaders`: `filter_chip_fragment: guards`
- `fewest_points_allowed_team_leader`: `semantic_fact: points allowed`
- `most_points_allowed_team_leaders_wave4`: `semantic_fact: points allowed`
- `opponent_ppg_leaders_wave4`: `semantic_fact: points per game`
- `personal_foul_leaders_wave4`: `semantic_fact: Unavailable Metric`

## 6. Report review plan

- Highest-priority categories to review first: team defensive/opponent leaderboards, unsupported/no-result guidance, record-when conditions, playoff matchup phrasing, and comparison labels.
- What ChatGPT/user should look for: hero facts that contradict rows, missing critical filters, wrong season/window context, misleading defensive/opponent metric wording, no-result guidance that is too generic, and table labels that do not match the requested stat.
- How findings should be recorded: treat soft-check misses as leads only; confirm from the Markdown/JSONL report, then group confirmed defects by frontend-copy family before changing rendering code or promoting hard tests.

## 7. Validation

Commands run:

```bash
cd frontend && npm test -- src/test/frontendCopyQaReport.test.tsx
```

Result: 1 test file passed, 4 tests passed.

```bash
cd frontend && npm run qa:frontend-copy
```

Result: 1 test file passed, 4 tests passed. Generated latest report at `outputs/frontend_copy_qa/20260514T153729Z/`.

```bash
cd frontend && npm test -- src/test/ResultRenderer.test.tsx src/test/UIComponents.test.tsx
```

Result: 2 test files passed, 80 tests passed.

```bash
cd frontend && npm run build
```

Result: passed. Vite emitted the existing large-chunk warning for the built JS bundle.

```bash
git diff --check
```

Result: passed.

## 8. Next recommendation

- Should we review the generated report manually next? yes.
- Should we expand the frontend-copy corpus? not yet. Review Wave 1 first, then expand only the families with confirmed issues or thin coverage.
- Should any findings be promoted to hard tests yet? no. The five soft-check misses are unreviewed report cues, not confirmed regressions.
