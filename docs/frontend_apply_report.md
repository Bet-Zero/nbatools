# Frontend Apply Report — Query Intent Audit Display Pass

Scope: frontend display changes for backend patterns 1, 2, 3, 4, 6, and 8, plus unsupported-filter note text cleanup. New shape components for Patterns 5 and 10 were not added.

## Pattern 1 — Multi-period by-season breakdown

Files touched:

- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/EntitySummaryResult.module.css`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`

Changed:

- Entity Summary now renders a `ResultTable` for `sections.by_season` when `metadata.scope_kind` is `career`, `season_range`, `all_time`, or `decade`.
- `single_season` player summaries remain hero-only.
- By-season rows sort newest season first.
- Zero-game career-arc rows render with muted cells and dashes for average/stat columns.
- Multi-season Team Record now renders a body table for `by_season` rows; single-season records keep the existing layout.
- Playoff History and Record By Decade already rendered by-season/decade tables and were left as-is.

## Pattern 2 — Filter chips

Files touched:

- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/test/LayoutPrimitives.test.tsx`

Changed:

- `metadata.applied_filters` renders as Badge chips in the existing envelope context row.
- Empty or missing `applied_filters` renders nothing.
- Threshold filters are normalized for display, e.g. `pts min: 30.0001` becomes `Stat: 30+ PTS`.

Decision:

- Implemented chips in `ResultEnvelope`, not `ResultHero`, so all result shapes and no-result states can share one filter display path without adding route-specific hero wiring.

## Pattern 3 — Count-first headline

Files touched:

- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`
- `src/nbatools/query_service.py`
- `tests/test_backend_apply_patterns.py`

Changed:

- Leaderboards and game-log/finder shapes use `metadata.count_phrase` as the headline when both `primary_count` and `count_phrase` are present.
- The supporting table still renders below the headline.
- Backend count phrase text was cleaned up to avoid raw dict representations in the displayed sentence.

## Pattern 4 — Player + opponent summaries show game log

Files touched:

- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/test/ResultRenderer.test.tsx`

Changed:

- `player_game_summary` routes now compose Entity Summary + Game Log when `game_log` is populated and the response has `metadata.opponent_context` or an opponent team applied filter.
- The existing `GameLogResult` sorting handles matchup rows newest first.

## Pattern 6 — Active streak promotion

Files touched:

- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`

Changed:

- Streak headline now uses the first `is_active=true` row, even when it is not the first/longest row.
- Existing status badge rendering remains the active-row visual highlight in the table.

## Pattern 8 — Ambiguity recovery display

Files touched:

- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/NoResultDisplay.module.css`
- `frontend/src/api/types.ts`
- `frontend/src/test/UIComponents.test.tsx`
- `src/nbatools/query_service.py`
- `tests/test_backend_apply_patterns.py`

Changed:

- No-result rendering now receives metadata and displays:
  - `candidates` as a plain-text `Did you mean:` line.
  - `suggested_queries` as exact monospace query suggestions.
- Backend ambiguity metadata is now copied into response metadata so these fields reach the frontend.

Contract issue found and fixed:

- `candidates` / `suggested_queries` were being stored only on `NoResult.metadata`, then overwritten by `QueryResult.to_dict()` response metadata. They now flow through top-level response metadata.
- Fragment suggestions for triple-double ambiguity were also cleaned up to avoid raw dict text.

## Unsupported-filter note text

Files touched:

- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/commands/player_game_summary.py`
- Backend tests covering note text expectations.

Changed:

- Clutch, period, schedule-context, national-TV, opponent-quality, and role notes now say the filter is not supported with current data and suggest removing the filter or asking for a supported alternative.
- Removed stale "results are unfiltered" wording from source helpers.

## Verification

Commands run:

- `npm run build` — passed.
- `npm test` — passed, 16 files / 230 tests.
- `.venv/bin/pytest tests/test_backend_apply_patterns.py -n0` — passed, 38 tests.
- `make test PYTEST=.venv/bin/pytest` — passed, 2639 passed / 1 xpassed.

Representative API/review checks:

- Started local FastAPI and Vite servers and opened `/review`; the review fixture pass exercised the Vite page against the local API.
- Direct `/query` checks confirmed:
  - `LeBron career`: `scope_kind=career`, `by_season_rows=23`.
  - `Jokic vs Lakers career`: `applied_filters` includes opponent and season range, `game_log_rows=32`.
  - `how many Jokic games with 30+ points and 10+ rebounds since 2021`: `primary_count` and `count_phrase` present.
  - `Brown last 10`: `candidates` present in metadata.
  - `Jokic triple doubles`: `suggested_queries` present in metadata.

Safari blocked programmatic text extraction from `/review` because "Allow JavaScript from Apple Events" is disabled, so field-specific rendered-output assertions are covered by component tests and the API spot checks above.
