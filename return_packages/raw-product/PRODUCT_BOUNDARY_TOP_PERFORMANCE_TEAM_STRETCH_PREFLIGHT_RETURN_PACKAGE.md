# Product Boundary Preflight: Top-Performance + Team Rolling Stretch Return Package

## 1. Executive summary

- AQ-006 recommendation: support now. Non-scoring single-game top-performance wording should route to existing `top_player_games` with `stat="ast"` / `stat="reb"` and keep the existing `top_performances` shape.
- AQ-008 recommendation: unsupported for now. Detect team-scoped rolling-stretch wording and return clean `no_result` / `filter_not_supported` guidance instead of player stretch rows.
- Can they be handled in one execution wave? yes, if AQ-008 is scoped to the unsupported guard. Full team rolling-stretch support should be a later feature wave.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. AQ-006 non-scoring top-performance investigation

| Query | Current route/status | Stat detected? | Existing support? | Notes |
|---|---|---|---|---|
| `What were the most assists in a game this season?` | `<none>` / `error` / `unrouted` | yes, `ast` | yes, direct `top_player_games(stat="ast")` works | `in a game` prevents normal leaderboard intent, but `detect_season_high_intent` does not recognize `most <stat> in a game`, so final routing raises unmapped-query `ValueError`. |
| `What were the most rebounds in a game this season?` | `<none>` / `error` / `unrouted` | yes, `reb` | yes, direct `top_player_games(stat="reb")` works | Same gap as assists. |
| `highest assist games this season` | `season_leaders` / `ok` | yes, `ast` | yes, but not currently used | This returns season assist leaders, not single-game assist performances. Current season-high regex only has scoring-specific `highest scoring games`. |
| `most rebounds by a player in a game this season` | `<none>` / `error` / `unrouted` | yes, `reb` | yes | Single-game wording is detected by `wants_leaderboard` as not a normal leaderboard, but not promoted into season-high/top-game routing. |
| `single-game assist leaders this season` | `season_leaders` / `ok` | yes, `ast` | yes, but not currently used | `leaders` forces season leaderboard routing despite the single-game modifier. |
| `single-game rebound leaders this season` | `season_leaders` / `ok` | yes, `reb` | yes, but not currently used | Same wrong-grain behavior as assist leaders. |

Direct structured/internal route evidence:

| Route probe | Status | Top rows |
|---|---|---|
| `top_player_games`, `season="2025-26"`, `stat="ast"`, `limit=3` | `ok` | Ryan Nembhard, DAL, 2026-04-12, 23 AST; Isaiah Collier, UTA, 2026-02-03, 22 AST; Josh Giddey, CHI, 2026-03-19, 19 AST |
| `top_player_games`, `season="2025-26"`, `stat="reb"`, `limit=3` | `ok` | Scottie Barnes, TOR, 2025-12-28, 25 REB; Andre Drummond, PHI, 2025-11-23, 24 REB; Jalen Duren, DET, 2025-11-05, 22 REB |

Assessment:

- Supporting AQ-006 is a small parser/routing addition.
- The backend support is already present in `src/nbatools/commands/top_player_games.py`; `ALLOWED_STATS` includes `ast` and `reb`.
- The output shape reuses the existing `LeaderboardResult` and existing top-performance route contract. No new result shape is needed.
- Frontend risk is low because `top_player_games` already maps to the `TopPerformancesResult` pattern and highlights the selected primary metric.

## 3. AQ-008 team rolling-stretch investigation

| Query | Current route/status | Team scope detected? | Existing support? | Notes |
|---|---|---|---|---|
| `best 5-game team scoring stretch this season` | `player_stretch_leaderboard` / `ok` | yes, generic `team_leaderboard_intent=true`; no concrete `team` entity | no team route | Returns player rows headed by Luka Doncic windows, not team windows. |
| `best team 5-game scoring stretch this season` | `player_stretch_leaderboard` / `ok` | yes, generic team scope | no team route | Same wrong-scope player result. |
| `which teams have the best 5-game scoring stretch this season` | `player_stretch_leaderboard` / `ok` | yes, generic team scope | no team route | `which teams` is not used by `_stretch_display_mode`; output is still player windows. |
| `best 5-game offensive stretch by a team` | `player_stretch_leaderboard` / `ok` | yes, generic team scope | no team route | Routes to player Game Score windows because `offensive stretch` does not map cleanly to a supported team rolling metric. |
| `best 5-game scoring stretch by team` | `player_stretch_leaderboard` / `ok` | yes, generic team scope | no team route | Same wrong-scope player result. |

Implementation evidence:

- No `team_stretch_leaderboard` command exists under `src/nbatools/commands/`.
- `player_stretch_leaderboard` is the only rolling-window route in `_natural_query_execution.py`, `query_service.VALID_ROUTES`, and `frontend/src/api/types.ts`.
- `frontend/src/components/results/config/routeToPattern.ts` maps only `player_stretch_leaderboard` to `rolling_stretch`.
- `frontend/src/components/results/patterns/RollingStretchResult.tsx` hardcodes league-table identity around player columns (`player_name`, `player_id`) and player hero wording.
- Team game logs are available through `load_team_games_for_seasons`, and a scratch read-only rolling calculation over `data/raw/team_game_stats/2025-26_regular_season.csv` produced plausible team windows. Example: Cleveland Cavaliers 5-game PTS average 135.2 ending 2025-11-12. This proves data feasibility, not product-ready support.

Assessment:

- Full AQ-008 support is medium complexity, not a safe tiny routing patch.
- A proper feature likely needs `team_stretch_leaderboard`, route registration, route metadata, backend result/table contract updates, frontend route type/mapping, and a team-aware rolling stretch table/hero.
- Unsupported/no-result is safer now because the current behavior gives a confident player answer to an explicitly team-scoped question.

## 4. Product value / complexity matrix

| Finding | User value | Implementation complexity | Existing backend support | Frontend/display risk | Recommended behavior |
|---|---:|---:|---|---|---|
| AQ-006 non-scoring single-game top performances | High | Low | High | Low | Support now through `top_player_games`. |
| AQ-008 team-scoped rolling stretch | Medium | Medium | Low | Medium | Return unsupported/no-result now; build full team route later if prioritized. |

## 5. Recommended product semantics

- Non-scoring single-game top performances: natural language that clearly asks for the most/highest/best single-game `ast` or `reb` performances should return `top_player_games` with the detected stat and the existing `top_performances` shape. This should include question, fragment, and shorthand forms such as `most assists in a game`, `highest assist games`, and `single-game rebound leaders`.
- Team rolling stretches: team-scoped rolling-window wording should not fall through to `player_stretch_leaderboard` rows. Until a team-backed route exists, return `no_result` with `result_reason="filter_not_supported"` and no sections.
- Unsupported/no-result wording policy: use the existing unsupported-filter pattern. A suggested marker is `unsupported_filters: ["team_rolling_stretch"]`, with a note like `team rolling-stretch leaderboards are not supported with current routes; try a player rolling stretch such as 'hottest 3-game scoring stretch' or a team single-game query such as 'top team scoring games this season'`.

## 6. Recommended execution scope

- Exact goal: Wave 6A should support AQ-006 non-scoring top-game routing and block AQ-008 wrong-scope team rolling-stretch output with an unsupported/no-result response.
- Files to change:
  - `src/nbatools/commands/_parse_helpers.py`: expand single-game/top-performance intent detection for stat-bearing non-scoring phrases; add or expose a targeted team-scoped stretch detector if needed.
  - `src/nbatools/commands/natural_query.py`: route recognized non-scoring single-game top-performance queries to `top_player_games`; add `unsupported_filters: ["team_rolling_stretch"]` when a rolling-stretch query has generic team scope.
  - `src/nbatools/commands/_natural_query_execution.py`: add a custom unsupported-filter note for `team_rolling_stretch`.
  - `src/nbatools/query_service.py`: only if metadata does not already preserve the new unsupported filter through existing plumbing.
  - `docs/reference/query_catalog.md`: document verified shipped AQ-006 support and AQ-008 unsupported boundary after tests pass.
  - `docs/reference/query_guide.md`: update shipped examples/boundary wording if the execution wave treats it as current behavior.
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`: mark AQ-006 fixed and AQ-008 fixed-as-expected-unsupported after harness validation.
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`: add Wave 6 status if that plan continues tracking these waves.
- Tests to add:
  - Parser tests proving `most assists in a game`, `most rebounds in a game`, `highest assist games`, and `single-game rebound leaders` route to `top_player_games` with `stat="ast"` / `stat="reb"`.
  - Regression tests proving `most assists this season` and ordinary `assist leaders` still route to season leaderboards.
  - Query-service tests proving AQ-006 returns `ok`, route `top_player_games`, `leaderboard` section, and the selected stat column.
  - Parser/query-service tests proving team-scoped rolling stretch returns `no_result` / `filter_not_supported`, carries `unsupported_filters=["team_rolling_stretch"]`, and returns no player leaderboard rows.
  - Regression tests proving existing player stretch queries such as `hottest 3-game scoring stretch this year` still execute normally.
- Corpus updates:
  - `most_assists_single_game`: expect `ok`, `top_player_games`, `top_performances`, section `leaderboard`, selected stat `ast`.
  - `most_rebounds_single_game`: expect `ok`, `top_player_games`, `top_performances`, section `leaderboard`, selected stat `reb`.
  - `team_5_game_scoring_stretch`: expect `no_result`, route likely `player_stretch_leaderboard` if using the unsupported-filter guard, reason `filter_not_supported`, shape `no_result` or backend approximation with no sections, and metadata `unsupported_filters=["team_rolling_stretch"]`.
- Findings updates:
  - AQ-006: `fixed`.
  - AQ-008: `fixed_as_expected_unsupported` unless a later product decision chooses full support.
- Harness validation:
  - Run targeted harness cases for `most_assists_single_game`, `most_rebounds_single_game`, and `team_5_game_scoring_stretch`.
  - Run the full raw QA harness and confirm no expectation failures.
  - Because the parser/routing layer is high fan-in, run `make test-parser`, `make test-query`, and `make test-preflight`.
- Stop conditions:
  - Stop if AQ-006 support requires a new result shape or frontend rendering change.
  - Stop if a regex change captures normal season leaderboards such as `most assists this season`.
  - Stop if AQ-008 still returns player rows for any explicit `team` / `teams` / `by team` stretch wording.
  - Stop if implementation starts building full team rolling-stretch support inside Wave 6A without an explicit product decision.

## 7. Risks and open decisions

- AQ-006 risks: broad intent regexes can steal ordinary season-leader queries; `single-game assist leaders` is semantically close to both a season leaderboard and a top-game leaderboard, so tests should lock the intended product boundary; existing `top_player_games` tie-breaks and `game_id` string normalization remain existing behavior, not part of this wave.
- AQ-008 risks: unsupported guard is less satisfying than a team answer, but it prevents a wrong-scope answer; full support needs decisions on metric semantics (`pts` average vs total, `off_rating` availability, `offensive stretch` wording), window deduplication per team vs all windows, date/last-N handling, and team-aware frontend display.
- Product decisions still open: whether to prioritize full `team_stretch_leaderboard`; whether `offensive stretch` should mean team points, offensive rating, net rating, or another metric; whether team rolling stretch rows should expose best-window game logs.

## 8. Validation performed

Commands/probes run:

```text
git status --short
```

Summary: worktree was clean before this return package was written.

```text
sed -n '1,240p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_5_VERIFIED_TOP_PERFORMANCE_OUTLIER_POLICY_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/TOP_PERFORMANCE_DATA_QUALITY_PREFLIGHT_RETURN_PACKAGE.md
sed -n '1,220p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '380,470p' docs/reference/query_catalog.md
sed -n '190,215p' docs/reference/query_catalog.md
sed -n '1,80p' docs/reference/query_guide.md
sed -n '190,215p' docs/reference/query_guide.md
sed -n '1,260p' docs/reference/result_contracts/core_result_table_contracts.md
```

Summary: confirmed AQ-006/AQ-008 are the remaining product-boundary findings and that existing shipped docs only advertise scoring single-game top performances and player rolling stretches.

```text
rg -n "most_assists_single_game|most_rebounds_single_game|team_5_game_scoring_stretch|top_performance|stretch" qa/raw_query_answer_corpus.yaml
rg -n "most_assists_single_game|most_rebounds_single_game|team_5_game_scoring_stretch" outputs/raw_query_answer_qa/20260513T025137Z/report.md
rg -n "most_assists_single_game|most_rebounds_single_game|team_5_game_scoring_stretch" outputs/raw_query_answer_qa/20260513T025137Z/report.jsonl
sed -n '405,475p' qa/raw_query_answer_corpus.yaml
sed -n '952,976p' qa/raw_query_answer_corpus.yaml
sed -n '865,910p' outputs/raw_query_answer_qa/20260513T025137Z/report.md
sed -n '2268,2305p' outputs/raw_query_answer_qa/20260513T025137Z/report.md
```

Summary: confirmed corpus/report expectations: AQ-006 is currently expected `error` / `unrouted`; AQ-008 is currently expected `ok` / `player_stretch_leaderboard` but marked for manual product decision because it is team-scoped wording.

```text
sed -n '1,120p' src/nbatools/commands/_parse_helpers.py
sed -n '1060,1135p' src/nbatools/commands/_parse_helpers.py
sed -n '1280,1370p' src/nbatools/commands/_parse_helpers.py
sed -n '360,760p' src/nbatools/commands/natural_query.py
sed -n '760,1075p' src/nbatools/commands/natural_query.py
sed -n '1240,1355p' src/nbatools/commands/natural_query.py
sed -n '1700,1815p' src/nbatools/commands/natural_query.py
sed -n '360,480p' src/nbatools/commands/_natural_query_execution.py
sed -n '1,260p' src/nbatools/commands/top_player_games.py
sed -n '1,260p' src/nbatools/commands/player_stretch_leaderboard.py
sed -n '1,240p' src/nbatools/commands/top_team_games.py
```

Summary: confirmed `detect_stat` handles `ast`/`reb`, `top_player_games` supports both stats, rolling-stretch parser always finalizes to `player_stretch_leaderboard`, and unsupported-filter execution can be reused for a clean no-result guard.

```text
rg --files src/nbatools/commands tests | rg "stretch|rolling|top_(player|team)_games|query|natural"
rg -n "team_stretch|team.*window|rolling.*team|player_stretch_leaderboard|top_player_games|top_team_games|season_high|single-game|single game" tests src docs/reference/query_catalog.md docs/reference/query_guide.md docs/reference/result_contracts/core_result_table_contracts.md
```

Summary: found `player_stretch_leaderboard` only; no team rolling-stretch command or route exists.

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c '<parse/execute probe for AQ-006 and AQ-008 query variants plus structured top_player_games AST/REB probes>'
```

Summary: exact query probes produced the route/status findings in sections 2 and 3. Direct `top_player_games` AST/REB probes returned `ok` with source-backed leaderboard rows.

```text
rg -n "player_stretch_leaderboard|rolling_stretch|Top Performances|team_name|Player|Team" frontend/src/components frontend/src/api src/nbatools/commands/structured_results.py src/nbatools/query_service.py
sed -n '100,330p' frontend/src/components/results/patterns/RollingStretchResult.tsx
sed -n '491,660p' frontend/src/components/results/patterns/RollingStretchResult.tsx
sed -n '190,208p' frontend/src/components/results/config/routeToPattern.ts
sed -n '50,75p' frontend/src/api/types.ts
```

Summary: confirmed current frontend route typing and rolling-stretch renderer are player-route/player-identity oriented.

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c '<scratch load_team_games_for_seasons rolling 5-game team PTS average probe>'
```

Summary: team-game data can support a future rolling calculation, but the app has no team route/result contract today. The scratch top row was Cleveland, 135.2 PTS per game over a 5-game window ending 2025-11-12.

```text
git status --short
```

Summary: still clean after read-only probes; only this return package was added afterward.
