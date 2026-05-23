# Entity Summary Record-When Filter Follow-Up Return Package

## 1. Executive summary

- What was wrong after Wave 1: the visual recheck showed `The Nuggets are 43-22 when Nikola Jokić records a triple-double this season.`
- Root cause: the live backend aggregation was already filtered, but `/review` could reuse an old cached pre-fix payload under the `v1` review-cache namespace. That stale payload had the unfiltered 65-game `43-22` sample, and the Wave 1 frontend hero wording rendered it as a record answer.
- What changed: review-cache namespace bumped to `v2`, special-event metadata is exposed through the existing applied-filter chip path, and backend/frontend regressions now lock the filtered `34` game, `24-10` result.
- Production code changed? yes.
- Tests added/updated: backend summary aggregation unit coverage, query-service metadata coverage, needs-data UI failure regression, ResultRenderer hero regression, ResultEnvelope special-event chip coverage, and ReviewPage cache-version coverage.
- Docs updated: `docs/planning/raw-product/VISUAL_QA_NOTES.md`.
- Remaining risk: screenshots still need regeneration from a freshly run `/review` sweep; an already-open page can still display old in-memory results until rerun/reload.

## 2. Reproduction evidence

- Query text: `What is Denver's record when Nikola Jokić has a triple-double?`
- Route: `player_game_summary`
- Sections: `summary` 1 row, `by_season` 1 row, `game_log` 34 rows
- Pre-fix observed record: `43-22`, matching the unfiltered 65-game Denver/Jokić season sample
- Filtered sample game count: 34 triple-double games
- Corrected record: `24-10`, `win_pct=0.706`
- `special_event` present:
  - parsed `route_kwargs.special_event = "triple_double"`
  - parsed `occurrence_event = {"special_event": "triple_double"}`
  - response metadata `occurrence_event = {"special_event": "triple_double"}`
  - response metadata `applied_filters` includes `Special Event: Triple Double`
- Summary/game-log alignment: summary `games=34`, `wins=24`, `losses=10`; game log has 34 rows with 24 wins and 10 losses.

## 3. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/query_service.py` | Production update | Adds special-event applied-filter metadata so the existing chip path can show `Special Event: Triple Double`. |
| `frontend/src/ReviewPage.tsx` | Production update | Bumps review result cache namespace from `v1` to `v2` so stale unfiltered cached payloads are not reused. |
| `tests/test_player_game_summary_filters.py` | Test update | Adds data-free aggregation regression proving special-event summaries compute W-L from filtered rows. |
| `tests/test_query_service.py` | Test update | Verifies the exact record-when query propagates `special_event` and exposes applied-filter metadata. |
| `tests/test_ui_failure_coverage.py` | Test update | Strengthens needs-data regression for the exact Denver/Jokić query: 34 games, 24-10, not 65 games or 43-22. |
| `frontend/src/test/ResultRenderer.test.tsx` | Test update | Verifies the record-when hero uses filtered W-L fields and does not fall back to player-average wording. |
| `frontend/src/test/LayoutPrimitives.test.tsx` | Test update | Verifies the existing envelope chip renderer displays special-event filters. |
| `frontend/src/test/ReviewPage.test.tsx` | Test update | Updates review-cache expectations to the `v2` namespace. |
| `docs/planning/raw-product/VISUAL_QA_NOTES.md` | Doc update | Records the follow-up finding, fix, and screenshot regeneration need. |
| `return_packages/raw-product/ENTITY_SUMMARY_RECORD_WHEN_FILTER_FOLLOWUP_RETURN_PACKAGE.md` | New return package | Captures evidence, files, behavior, and validation. |

## 4. Behavior after fix

- Entity Summary hero: `The Nuggets are 24-10 when Nikola Jokić records a triple-double this season.`
- Summary record fields: `games=34`, `wins=24`, `losses=10`, `win_pct=0.706`.
- Filter/special-event metadata: metadata includes `occurrence_event={"special_event": "triple_double"}` and an applied filter chip payload `Special Event: Triple Double`.
- Normal player summary behavior: unchanged; broad player summaries still use the normal player-average Entity Summary hero.

## 5. Validation

Backend:

| Command | Result |
|---|---|
| `.venv/bin/pytest tests/test_player_game_summary_filters.py tests/test_query_service.py::TestMetadataPreservation::test_record_when_player_special_event_metadata_exposes_filter tests/test_ui_failure_coverage.py::TestWithoutPlayer::test_record_when_player_special_event_filters_summary_and_game_log -n0` | Passed: 4 tests. |
| `make PYTEST=.venv/bin/pytest test-query` | Passed: 681 tests in 200.62s. |

Frontend:

| Command | Result |
|---|---|
| `npm test -- ResultRenderer.test.tsx` from `frontend/` | Passed: 1 file, 53 tests. |
| `npm test -- ResultRenderer.test.tsx LayoutPrimitives.test.tsx ReviewPage.test.tsx` from `frontend/` | Passed: 3 files, 83 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. |

Always:

| Command | Result |
|---|---|
| `git diff --check` | Passed. |

## 6. Screenshot recommendation

Regenerate the Entity Summary screenshot again from a fresh `/review` run. The cache namespace bump prevents reuse of the stale `v1` payload, but an already-open review page should still be rerun or reloaded before capture.
