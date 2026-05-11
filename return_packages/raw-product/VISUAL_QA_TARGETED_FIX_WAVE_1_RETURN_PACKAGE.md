# Visual QA Targeted Fix Wave 1 Return Package

## 1. Executive summary

- Targets addressed: Entity Summary record-when player condition, Streak Table
  density, Team Record density, playoff round record percentage copy, and
  comparison record-card `win pct` copy.
- Production code changed? yes, frontend and backend.
- Tests added/updated: frontend renderer/table-contract fixtures and a backend
  needs-data regression covering special-event record-when summaries.
- Docs updated: `docs/planning/raw-product/VISUAL_QA_NOTES.md` and
  `docs/reference/result_contracts/core_result_table_contracts.md`.
- Main product improvement: the Denver/Jokić triple-double query now answers
  the Nuggets record, and the two clipped table shapes default to narrower
  trust-critical columns with support stats behind `Show additional columns`.
- Any target deferred: historical playoff `Round unavailable` repetition and
  generic leaderboard entity-cell truncation remain deferred low-priority
  polish items.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/player_game_summary.py` | Production update | Adds `special_event` filtering so summary/game-log rows for triple-double summaries are actually condition-filtered. |
| `src/nbatools/commands/natural_query.py` | Production update | Propagates player summary `special_event` route kwargs for record-when player-condition summaries. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Production update | Gives record-when player-condition summaries team-record hero priority over player average hero wording. |
| `frontend/src/components/results/patterns/StreakResult.tsx` | Production update | Limits default average/stat columns to the requested or primary streak metric. |
| `frontend/src/components/results/patterns/RecordResult.tsx` | Production update | Narrows Team Record summary defaults and leaves secondary fields to the detail drawer. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Optional polish | Formats playoff round record hero win percentage as table-style percentage wording. |
| `frontend/src/components/results/patterns/ComparisonResult.tsx` | Optional polish | Changes record-card context from `win pct` wording to `win rate`. |
| `frontend/src/test/ResultRenderer.test.tsx` | Test update | Covers record-when hero priority, narrowed Streak/Team Record defaults, detail drawers, and optional copy polish. |
| `frontend/src/test/wave1TableContracts.test.tsx` | Test update | Locks narrower Team Record visible columns and verifies hidden support stats remain available in additional columns. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Test update | Locks narrower Streak visible columns and verifies the detail drawer appears for hidden support stats. |
| `tests/test_ui_failure_coverage.py` | Test update | Adds backend regression for the Denver/Jokić triple-double record query. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Doc update | Documents the new Entity Summary priority and narrower Team Record/Streak table contracts. |
| `docs/planning/raw-product/VISUAL_QA_NOTES.md` | Doc update | Adds Fix Wave 1 status for fixed/deferred visual QA targets. |
| `return_packages/raw-product/VISUAL_QA_TARGETED_FIX_WAVE_1_RETURN_PACKAGE.md` | New return package | Records implementation, validation, and screenshot follow-up recommendation. |

## 3. Target outcomes

### Entity Summary record-when player condition

- Previous behavior: `What is Denver's record when Nikola Jokić has a triple-double?`
  rendered a player average hero and the backend `player_game_summary` payload
  was not filtering to triple-double games.
- Root cause: `special_event` was detected in parse metadata but was not passed
  into `player_game_summary`; the frontend then used the normal player-average
  Entity Summary hero even when team record fields were present.
- New behavior: the backend summary/game-log rows are filtered to qualifying
  triple-double games, and the hero renders team-record wording such as
  `The Nuggets are 24-10 when Nikola Jokić records a triple-double this season.`
- Tests added/updated: backend needs-data regression in
  `tests/test_ui_failure_coverage.py`; frontend renderer fixture in
  `ResultRenderer.test.tsx`.
- Remaining risk: broader record-when phrasing variants should continue to be
  covered through the existing query slice; screenshot recheck is still needed.

### Streak Table density

- Previous behavior: Streak tables rendered every available average/support stat
  by default, causing clipping at review width.
- New default columns: `#`, optional entity column when not pinned, `Streak`,
  `Length`, conditional `Status`, `Start`, `End`, `Games`, `Record`, and one
  requested/primary metric such as `PTS`.
- Additional/hidden columns: secondary stats such as `REB`, `AST`, `MIN`,
  `TS%`, `eFG%`, `3PM`, and `+/-` remain available through
  `Show additional columns`.
- Tests added/updated: `ResultRenderer.test.tsx` and
  `wave2TableContracts.test.tsx`.
- Remaining risk: mobile visual QA should confirm the detail drawer is usable
  for long streak tables.

### Team Record density

- Previous behavior: single-summary Team Record tables defaulted to support
  stats and duplicated season/status context, clipping the right edge.
- New default columns: `Team`, `W-L`, `Games`, `Win %`, `PPG`, `+/-`, and
  directly relevant context such as `Opponent Group`, `Home/Away`, or
  `Opponent`.
- Additional/hidden columns: `REB`, `AST`, `3PM`, optional support stats, and
  duplicated season/status context remain available through
  `Show additional columns`.
- Tests added/updated: `ResultRenderer.test.tsx` and
  `wave1TableContracts.test.tsx`.
- Remaining risk: record-by-decade and record-by-decade leaderboard were not
  changed; broad preflight remained green.

### Optional polish

- What was changed: playoff round record heroes now use percentage win-rate
  wording, and comparison record-card context uses `win rate`.
- What was deferred: historical playoff `Round unavailable` repetition and
  generic leaderboard entity-cell truncation.

## 4. Validation

| Command | Result |
|---|---|
| `npm test -- ResultRenderer.test.tsx wave1TableContracts.test.tsx wave2TableContracts.test.tsx resultShapes.test.ts routeToPattern.test.ts` from `frontend/` | Passed: 5 files, 97 tests. |
| `npm run build` from `frontend/` | Passed; Vite emitted the existing large-chunk warning. |
| `make PYTEST=.venv/bin/pytest test-query` | Passed after final production edits: 681 tests. |
| `make PYTEST=.venv/bin/pytest test-engine` | Passed: 728 tests, 1 xpassed. |
| `make PYTEST=.venv/bin/pytest test-preflight` | Passed after final production edits: 2650 tests, 1 xpassed. |
| `git diff --check` | Passed. |

## 5. Visual QA recommendation

Regenerate screenshots after this wave.

Recheck:

- Entity Summary: `What is Denver's record when Nikola Jokić has a triple-double?`
- Streak Table: `Jokic 5 straight games with 20+ points`
- Team Record: `What is the Celtics' record against playoff teams?`
- Playoff Round Records, because optional hero percentage copy changed.
- Comparison Panels, because optional record-card sublabel copy changed.
