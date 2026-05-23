# Visual QA Corpus Expansion Return Package

## What changed

- Expanded the Visual QA corpus from 15 to 20 cases in both the JSON runtime
  corpus and its YAML companion.
- Preserved the original 15 cases and added one approved case for each preflight
  gap: player summary, count-plus-finder, player split, player streak, and
  rolling stretch.
- Refreshed the visual corpus provenance to raw QA and frontend-copy reports
  that contain all five selected source cases:
  - raw QA: `outputs/raw_query_answer_qa/20260517T070422Z/report.jsonl`
  - frontend-copy QA:
    `outputs/frontend_copy_qa/20260521T025916Z/frontend_copy_report.jsonl`
- Updated the internal `/visual-qa` page wording and focused page test counts
  from 15 to 20 cases.
- Updated the active Visual QA checklist and current release/readiness planning
  docs so the new 20-case corpus is not confused with the earlier accepted
  15-case preview evidence.

## Cases added

| Case ID | Query | Coverage family |
| --- | --- | --- |
| `jokic_season_summary` | `Jokic this season` | player summary |
| `jokic_triple_double_finder` | `How often has Nikola Jokic recorded a triple-double this season?` | count plus finder |
| `jokic_home_away_split` | `Jokic home vs away this season` | player split |
| `curry_3_threes_streak` | `Curry longest streak with at least 3 threes` | player streak |
| `jokic_best_5_rebounding_stretch` | `Jokic best 5-game rebounding stretch this season` | rolling stretch |

## Files changed

- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_visual_qa_corpus.yaml`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `docs/index.md`
- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `return_packages/raw-product/VISUAL_QA_CORPUS_EXPANSION_RETURN_PACKAGE.md`

`docs/operations/ui_guide.md` was not changed because it does not state a
Visual QA baseline count.

## Baseline before and after

| Baseline | Cases | Required viewports |
| --- | ---: | ---: |
| Before this wave | 15 | 30 desktop/mobile viewport reviews |
| After this wave | 20 | 40 desktop/mobile viewport reviews |

The current release/readiness docs keep the older 15-case preview checks
identified as pre-expansion evidence. The new five rows are marked for the next
manual desktop/mobile capture pass in the checklist.

## Validation results

| Command | Result |
| --- | --- |
| `cd frontend && npm test -- src/test/VisualQaPage.test.tsx` | passed: 1 file, 5 tests |
| `cd frontend && npm run build` | passed with the existing Vite large-chunk warning |
| `cd frontend && npm run lint` | passed with 0 errors and the existing `ReviewPage.tsx` `react-hooks/exhaustive-deps` warning |
| `git diff --check` | passed |

Markdown lint was not run. No repo-local Markdown lint command was found in the
checked scripts, and `markdownlint` was not installed on PATH.

## Frontend-copy and visual harness

`npm run qa:frontend-copy` was not run. This wave did not change production
result rendering, public result copy, frontend-copy expectations, or the
frontend-copy corpus; it only changed Visual QA corpus metadata, internal
Visual QA wording, focused page tests, and docs.

No dedicated Visual QA harness command was found in the frontend scripts or
Makefile. The focused `VisualQaPage` test was run for the manifest/page surface;
the live desktop/mobile `/visual-qa` review remains the manual next step.

## Scope checks

- Production frontend rendering changed: no.
- Backend behavior changed: no.
- Parser/routing behavior changed: no.
- Result contracts changed: no.
- Query support added: no.
- Frontend-copy expectations changed: no.
- `lakers_playoff_history` added: no. It remains deferred per the preflight.

## Release impact

The manual visual review load increases by 10 viewport reviews. Current
release/readiness docs now describe a 20-case Visual QA corpus while preserving
the older 15-case preview request-health evidence as historical pre-expansion
validation. There is no production behavior or contract impact.

## Next recommended action

Run `/visual-qa` for the full 20-case corpus at desktop around `1280px` and
mobile around `390px`, record the five expansion rows in the checklist, and
decide after that manual pass whether screenshot automation should adopt the
expanded corpus.
