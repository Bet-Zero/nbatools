# Weak Contract Decision Preflight Return Package

## 1. Executive summary

- Targets reviewed: `lineup_summary`, `player_on_off`, and single-team `playoff_appearances`.
- Biggest finding: `playoff_appearances` already returns a single-team `summary` + `by_season` backend result for queries like `Lakers playoff appearances`, but the frontend route mapping always expects `leaderboard`.
- Recommended next implementation: Option E, a tiny combined frontend cleanup for `lineup_summary` label keys and single-team `playoff_appearances`, with no `player_on_off` normalization.
- Should any production code change now? yes, in the next implementation wave; this preflight changed docs only.
- Highest-risk target: single-team `playoff_appearances`, because an `ok` result can currently render no visible content.
- Lowest-risk target: `player_on_off`, because current display behavior matches current backend rows.

## 2. Files inspected

| File | Why inspected | Key finding |
|---|---|---|
| `docs/planning/raw-product/RAW_QUERY_PRODUCT_MAP.md` | Current route/product map | Documents the targets as shipped routes and maps their current display families. |
| `docs/reference/result_contracts/core_result_table_contracts.md` | Locked result/table contracts | Identifies the three weak contracts and current Wave 2 behavior. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_1_RETURN_PACKAGE.md` | Wave 1 context | Confirms prior deferred display decisions and testing approach. |
| `return_packages/raw-product/CORE_RESULT_TABLE_CONTRACT_LOCK_WAVE_2_RETURN_PACKAGE.md` | Source weak-contract list | Names the three targets and recommends this decision preflight. |
| `src/nbatools/commands/natural_query.py` | Route selection | Routes lineup/on-off directly and delegates playoff appearance routing. |
| `src/nbatools/commands/_natural_query_execution.py` | Builder map | All three targets are mapped to production builders. |
| `src/nbatools/commands/_playoff_record_route_utils.py` | Playoff routing | Team-specific appearance queries still route to `playoff_appearances`. |
| `src/nbatools/commands/lineup_summary.py` | Lineup builder | Successful output is `SummaryResult(summary=rows)`. |
| `src/nbatools/commands/_lineup_execution.py` | Lineup row fields | Actual rows include `lineup_name` and `player_names`, not the synthetic `lineup` key used by current frontend fixture. |
| `src/nbatools/commands/player_on_off.py` | On/off builder | Successful output is `SummaryResult.summary` with one row per `presence_state`. |
| `src/nbatools/commands/playoff_history.py` | Appearance builder | `build_playoff_appearances_result()` returns `LeaderboardResult` without team and `SummaryResult` with team. |
| `src/nbatools/query_service.py` | Natural/structured facade | Single-team `playoff_appearances` is reachable through both natural and structured entrypoints. |
| `tests/test_core_result_table_contracts.py` | Backend section tests | Locks `player_on_off` summary rows and ranked `playoff_appearances` leaderboard rows. |
| `tests/test_source_backed_lineup_dataset.py` | Lineup execution tests | Confirms source-backed lineup summary returns real backend fields. |
| `tests/test_source_backed_on_off_dataset.py` | On/off execution tests | Confirms source-backed on/off summary rows can include `on` and `off`. |
| `tests/test_playoff_history_queries.py` | Playoff behavior tests | Confirms single-team playoff appearances are intended summary behavior. |
| `frontend/src/api/types.ts` | Route type union | Includes all three target routes. |
| `frontend/src/components/results/config/routeToPattern.ts` | Route mapping | `playoff_appearances` is leaderboard-only; `player_on_off` is split over `summary`; `lineup_summary` is entity summary. |
| `frontend/src/components/results/resultShapes.ts` | Shape classification | Classification follows route mapping and can misclassify single-team playoff appearances as leaderboard. |
| `frontend/src/components/results/ResultRenderer.tsx` | Pattern dispatch | Specific patterns do not fall back when their configured section is absent. |
| `frontend/src/components/results/patterns/EntitySummaryResult.tsx` | Lineup rendering | Recognizes `lineup`, `lineup_members`, and `members`, but not `lineup_name` or `player_names`. |
| `frontend/src/components/results/patterns/SplitResult.tsx` | On/off rendering | Current config cleanly renders `presence_state` rows. |
| `frontend/src/components/results/patterns/LeaderboardResult.tsx` | Appearance leaderboard rendering | Requires `leaderboard` rows, so it ignores single-team summary rows. |
| `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx` | Candidate summary renderer | Already handles `appearances` in the hero and `summary` + `by_season`, but needs a small appearances-mode/table tweak. |
| `frontend/src/test/routeToPattern.test.ts` | Mapping coverage | Locks current Wave 2 mappings. |
| `frontend/src/test/resultShapes.test.ts` | Shape coverage | Locks `lineup_summary` and `player_on_off` shapes. |
| `frontend/src/test/wave2SectionContracts.test.ts` | Section coverage | Does not cover the single-team `playoff_appearances` summary variant. |
| `frontend/src/test/wave2TableContracts.test.tsx` | Table smoke coverage | Uses synthetic `lineup` for lineup summary instead of actual backend keys. |

## 3. Target review: `lineup_summary`

Current behavior:

- Backend route `lineup_summary` returns `SummaryResult` with a `summary` section on successful trusted coverage.
- Local representative natural queries returned `NoResult(reason="unsupported")` because trusted `league_lineup_viz` coverage was unavailable.
- Actual source-backed row fields are `season`, `season_type`, `team_abbr`, `unit_size`, `lineup_id`, `lineup_name`, `player_ids`, `player_names`, `minute_minimum`, `minutes`, `off_rating`, `def_rating`, `net_rating`, `pace`, and `ts_pct`.

Frontend rendering:

- `routeToPattern.ts` maps to `entity_summary`.
- `EntitySummaryResult` renders lineup-aware hero text only when it finds `lineup`, `lineup_members`, or `members`.
- The current Wave 2 table test uses a synthetic `lineup` field, so it does not protect actual backend row keys.

Product assessment:

- A hero/card is enough for the raw product right now.
- A dedicated pattern is not needed until lineup support becomes a larger feature with multi-row breakdowns or richer trust/source context.
- The immediate risk is row-key mismatch, not lack of a dedicated pattern.

Recommendation:

- Keep `lineup_summary` as `entity_summary`.
- Add minimal frontend label support for `lineup_name`, pipe-delimited `player_names`, and metadata `lineup_members`.
- Defer a dedicated lineup summary pattern.

## 4. Target review: `player_on_off`

Current behavior:

- Backend route `player_on_off` returns `SummaryResult.summary` rows keyed by `presence_state` when trusted source coverage exists.
- Row fields are `season`, `season_type`, `player_name`, `team_abbr`, `team_name`, `presence_state`, `gp`, `minutes`, `plus_minus`, `off_rating`, `def_rating`, and `net_rating`.
- Local representative query `Jokic on off` routed correctly but returned unsupported because local on/off coverage was unavailable.

Frontend rendering:

- `routeToPattern.ts` maps to `SplitResult` with `sectionKey="summary"` and `bucketKey="presence_state"`.
- `SplitResult` renders understandable `On` / `Off` rows with `GP`, `ORtg`, `DRtg`, `Net`, `MIN`, and `+/-`.
- This differs from normal split summaries, which use `split_comparison`.

Product assessment:

- Current display is understandable and low risk.
- `summary` as table source is semantically inconsistent but harmless under the current contract.
- Normalizing now would create more contract churn than product value.

Recommendation:

- Keep the current `summary`-row contract.
- Document it as acceptable current behavior.
- Revisit only as part of a compatibility-preserving split-result cleanup.

## 5. Target review: `playoff_appearances` single-team variant

Current behavior:

- League-wide examples like `most playoff appearances` and `teams with most Finals appearances` return `leaderboard`.
- Single-team examples like `Lakers playoff appearances` and `Lakers Finals appearances` return `summary` plus `by_season`.
- Observed single-team `summary` fields: `team_name`, `appearances`, `round`, `season_start`, `season_end`.
- Observed single-team `by_season` fields: `season`, `games`, `wins`, `losses`, `win_pct`.

Frontend rendering:

- `routeToPattern.ts` maps all `playoff_appearances` results to `LeaderboardResult` over `sectionKey="leaderboard"`.
- The single-team result has no `leaderboard` section, so `LeaderboardResult` returns `null`.
- The result does not intentionally fall back; it can render as an empty result shell.

Product assessment:

- `Lakers playoff appearances` and `most playoff appearances` should be distinct shapes.
- The single-team variant is important now because it is already reachable and tested in backend behavior.
- Backend should not avoid returning it; UI should support it.

Recommendation:

- Add frontend support for the single-team summary variant.
- Prefer a small playoff-history/appearances mode over a new broad pattern.
- Show a hero with team, appearance count, round label, and season range, plus a table with `Season`, `Record`, `Games`, and `Win Pct`.

## 6. Decision matrix

| Target | Current behavior | Product risk | Options | Recommendation | Why | Implementation size | Test impact |
|---|---|---|---|---|---|---|---|
| `lineup_summary` | Backend summary rows use actual lineup fields like `lineup_name` and `player_names`; frontend entity summary recognizes only `lineup`, `lineup_members`, or `members`. | Medium. Source-backed rows can miss lineup-specific hero labeling once coverage exists. | Keep current and document; small frontend label support; backend alias fields; dedicated pattern later; mark out of UI scope. | Keep entity summary and add frontend label support for actual backend keys. | One-row hero/card is enough for raw product; row-key mismatch is the narrow issue. | Small frontend rendering change. | Add/update frontend table test with actual backend row keys. |
| `player_on_off` | Backend returns on/off bucket rows in `summary`; frontend split pattern reads `summary` with `bucketKey=presence_state`. | Low. Semantic inconsistency, but display and tests are aligned. | Keep current and document; frontend remap after backend change; backend normalize to `split_comparison`; dedicated pattern later; mark out of UI scope. | Keep current contract. | Normalization would create API/display churn without immediate product gain. | None now. | None now; future normalization would touch backend and frontend contract tests. |
| `playoff_appearances` single-team | Backend returns `summary` + `by_season`; frontend expects `leaderboard`. | High. Successful natural query can display no visible result. | Keep current and document; small frontend branch; backend avoid/normalize variant; dedicated pattern later; mark out of UI scope. | Support summary variant in UI. | User intent is direct answer plus season list, distinct from leaderboard intent. | Small frontend mapping/rendering change. | Add route mapping, shape, and table tests for summary variant while keeping leaderboard tests. |

## 7. Recommended implementation wave

Recommend Option E: a tiny combined cleanup for two low-scope frontend issues and
one explicit no-change decision.

Exact next scope:

- `lineup_summary`: update `EntitySummaryResult` lineup label resolution for
  `lineup_name`, pipe-delimited `player_names`, and metadata `lineup_members`.
- `playoff_appearances`: add a single-team summary display branch when
  `summary`/`by_season` exists and `leaderboard` does not.
- `player_on_off`: no code change; keep the current contract.

Why:

- This fixes the only confirmed ok-but-blank display risk.
- It keeps lineup support generic until data coverage and product use justify a
  dedicated pattern.
- It avoids backend section-shape migration for on/off.

## 8. Risks / stop conditions for implementation

- Stop if single-team `playoff_appearances` support turns into a broad playoff
  renderer redesign.
- Stop if implementation requires backend shape changes for
  `playoff_appearances`.
- Stop if lineup changes expand beyond label/context rendering into a dedicated
  pattern.
- Stop if `player_on_off` normalization would remove `summary` rows without a
  compatibility plan.
- Stop if frontend fixtures still do not match source-backed backend row fields.

## 9. Validation / confidence

Commands run:

- Representative query sweep through `.venv/bin/python` and
  `nbatools.query_service`.

Representative queries executed:

| Query | Route | Status | Sections |
|---|---|---|---|
| `lineup with Tatum and Jaylen Brown` | `lineup_summary` | `no_result` / `unsupported` | none |
| `net rating with Tatum and Jaylen Brown together` | `lineup_summary` | `no_result` / `unsupported` | none |
| `Jokic on off` | `player_on_off` | `no_result` / `unsupported` | none |
| `most playoff appearances` | `playoff_appearances` | `ok` | `leaderboard` |
| `teams with most Finals appearances` | `playoff_appearances` | `ok` | `leaderboard` |
| `Lakers playoff appearances` | `playoff_appearances` | `ok` | `summary`, `by_season` |
| `Lakers Finals appearances` | `playoff_appearances` | `ok` | `summary`, `by_season` |
| structured `playoff_appearances(team="LAL", start_season="1996-97", end_season="2024-25")` | `playoff_appearances` | `ok` | `summary`, `by_season` |

Limitations:

- Local trusted lineup and on/off datasets were unavailable, so successful row
  behavior for those targets was inferred from builders and source-backed tests.
- No production code was changed.
- No frontend browser render was executed.
