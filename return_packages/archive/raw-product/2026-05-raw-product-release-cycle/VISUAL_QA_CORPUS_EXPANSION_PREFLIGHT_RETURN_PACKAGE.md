# Visual QA Corpus Expansion Preflight Return Package

## 1. Executive Summary

- Mode: preflight only.
- Goal handled: plan the next Visual QA corpus expansion for public/mobile
  result coverage after Raw Product public UI hardening and parser boundary
  cleanup.
- Preflight output:
  `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md`.
- Recommended execution wave: add five supported public result cases and grow
  the manual desktop/mobile baseline from 15 cases / 30 viewport reviews to 20
  cases / 40 viewport reviews.
- Core additions recommended:
  `jokic_season_summary`, `jokic_triple_double_finder`,
  `jokic_home_away_split`, `curry_3_threes_streak`, and
  `jokic_best_5_rebounding_stretch`.
- Deferred candidate: `lakers_playoff_history`. It is useful single-team
  postseason coverage, but the current visual corpus already has playoff
  matchup history and the final public release review already spot-checked the
  Lakers history query on desktop/mobile.
- Production code changed? no.
- Frontend rendering changed? no.
- Backend/parser/routing/result-contract behavior changed? no.
- QA corpus files changed? no.
- New query support added? no.

## 2. Findings

### 2.1 Current Corpus Shape

The current visual corpus has 15 desktop/mobile cases:

| Current risk bucket | Cases |
| --- | ---: |
| Position-filtered player leaderboards | 2 |
| Team defense leaderboards | 3 |
| Guarded unsupported/no-result states | 5 |
| Record answers | 2 |
| Playoff matchup history | 1 |
| Player comparison | 1 |
| Top performances | 1 |

This baseline still targets important Wave 1 risks, especially filtered
leaderboard context, no-result hierarchy, and dense tables. It does not yet
cover several public answer-first renderer families through `/visual-qa`.

### 2.2 Under-Covered Public/Mobile Families

The preflight identified five missing high-value families for the first add
wave:

1. Player season summary.
2. Count plus finder/game log.
3. Player split.
4. Player streak.
5. Rolling stretch.

Single-team playoff history is under-covered rather than fully missing because
the visual corpus already includes playoff matchup history and release review
evidence already checked `Lakers playoff history`.

### 2.3 Candidate Duplication Check

The five recommended visual additions are not already present in
`qa/frontend_visual_qa_corpus.json`. Their queries are already supported and
already represented elsewhere:

| Recommended visual case | Existing QA coverage |
| --- | --- |
| `jokic_season_summary` | Same ID in raw QA and frontend-copy QA. |
| `jokic_triple_double_finder` | Same query covered as `jokic_triple_double_count` in raw QA and frontend-copy QA. |
| `jokic_home_away_split` | Same ID in raw QA and frontend-copy QA. |
| `curry_3_threes_streak` | Same ID in raw QA and frontend-copy QA. |
| `jokic_best_5_rebounding_stretch` | Same query covered as `jokic_5_game_rebound_stretch` in raw QA and frontend-copy QA. |

The optional `lakers_playoff_history` case is also already in raw QA and
frontend-copy QA.

## 3. Recommended Execution Scope

The preflight doc contains the exact five visual corpus objects to add, with
desktop and mobile visual focus text for each case.

Execution should:

1. Add those five entries to both visual corpus files.
2. Refresh visual corpus source-run metadata if the add wave relies on a newer
   frontend-copy report than the current visual corpus provenance names.
3. Update `VisualQaPage` internal 15-case wording.
4. Update `VisualQaPage` tests for the approved ID set and 20-case counts.
5. Keep result rendering, backend behavior, parser/routing, and result
   contracts unchanged.

No frontend-copy corpus or harness update is recommended. The preflight found
the intended cases are already selected in `qa/frontend_copy_corpus.yaml`; the
Visual QA wave should stop and split if it discovers public copy or rendering
work is needed.

## 4. Files Created

| File | Purpose |
| --- | --- |
| `docs/planning/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT.md` | Inventory, gap analysis, exact five-case execution recommendation, validation plan, and stop conditions. |
| `return_packages/raw-product/VISUAL_QA_CORPUS_EXPANSION_PREFLIGHT_RETURN_PACKAGE.md` | Handoff summary for this docs-only preflight. |

No production, frontend rendering, backend, parser, result-contract, or QA
corpus file was changed in this preflight.

## 5. Materials Reviewed

- `docs/planning/raw-product/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/operations/ui_guide.md`
- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_visual_qa_corpus.yaml`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `frontend/src/visualQaCases.ts`
- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_WAVE_2_RETURN_PACKAGE.md`
- `return_packages/raw-product/FINAL_PUBLIC_UI_RELEASE_REVIEW_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_6_RETURN_PACKAGE.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/frontend_copy_corpus.yaml`

## 6. Validation

Validation performed for this preflight:

```bash
git diff --check
```

Result: passed after the new docs were marked intent-to-add so the check covered
their markdown content.

Markdown lint discovery:

```bash
command -v markdownlint
command -v markdownlint-cli2
```

Result: no installed `markdownlint` or `markdownlint-cli2` command was
available. The repo search found no repo-local markdown lint target to run.

## 7. Scope Check

Acceptance criteria status:

| Criterion | Status |
| --- | --- |
| No production code change | Met |
| No frontend rendering change | Met |
| No backend/parser/routing/result-contract change | Met |
| No QA corpus file change | Met |
| Preflight doc created | Met |
| Return package created | Met |
| Recommended execution wave is concrete | Met |
| Exact visual focus per recommended case documented | Met |
| `git diff --check` passes | Met |
