# Product Boundary Finalization Preflight Return Package

## 1. Executive summary

- Main root-cause families:
  - AQ-030: existing personal-foul unsupported boundary is too narrow; `players with most personal fouls this season` never reaches the boundary because `wants_leaderboard()` depends on a recognized leaderboard stat alias and `personal fouls` is intentionally not one.
  - AQ-031: league-wide team advanced-stat leaderboards support `net_rating`, but single-team advanced-stat scalar summaries have no product/result contract; `Warriors net rating this season` falls through to `game_finder`, which rejects `net_rating`.
- Which cases are true bugs:
  - `players_personal_fouls_wave5` is a boundary-routing bug against an already decided unsupported behavior.
  - `warriors_net_rating_single_team_wave5` is not a supported-route bug yet; it is a product-boundary decision plus an unhelpful current fallback route/reason.
- Which cases are product-boundary decisions:
  - Personal-foul leaderboards remain unsupported until a fouls-committed leaderboard contract is approved.
  - Single-team team-advanced scalar lookups should be explicitly unsupported for now.
- Recommended next execution:
  - Option A: one product-boundary cleanup wave that makes both cases return explicit `no_result` / `filter_not_supported` boundaries with stable metadata and guidance.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `players_personal_fouls_wave5` | `players with most personal fouls this season` | `<none>` / `error` / `unrouted` | Parser raises `ValueError`; query-service returns `NoResult(query_class=unknown, result_status=error, reason=unrouted)`. No metadata stat, no route, no unsupported filter, no sections. | Keep unsupported: `season_leaders` / `no_result` / `filter_not_supported`, `metadata.stat=pf`, `metadata.unsupported_filters=["personal_foul_leaderboard"]`, no sections. | `detect_personal_foul_leaderboard_boundary()` requires `wants_leaderboard(text)`. That helper returns false because `personal fouls` is not in the supported stat alias table, so the boundary branch never fires. |
| `warriors_net_rating_single_team_wave5` | `Warriors net rating this season` | `game_finder` / `no_result` / `unsupported` | Parser resolves `team=GSW`, `stat=net_rating`, `team_leaderboard_intent=True`, but route is `game_finder`. Execution rejects `net_rating` with notes `["Unsupported stat: net_rating"]`; no sections. | Explicit unsupported boundary now: route `game_summary` or another single-team summary boundary route, `no_result` / `filter_not_supported`, `metadata.team=GSW`, `metadata.stat=net_rating`, `metadata.unsupported_filters=["single_team_advanced_stat_summary"]`, no sections. | The data exists for season-level team net rating, and league-wide `season_team_leaders` supports it. There is no single-team scalar result contract, and `season_team_leaders` has no team-filtered single-row contract. |

## 3. Nearby working/boundary cases

| Case/query | Behavior | Why it matters |
|---|---|---|
| `personal_foul_leaders_wave4` / `personal fouls leaders this season` | `season_leaders` / `no_result` / `filter_not_supported`; `metadata.stat=pf`; `unsupported_filters=["personal_foul_leaderboard"]`. | Establishes the intended PF product boundary and no-broad-fallback behavior. |
| `turnover_leaders_wave4` / `Who averages the most turnovers per game this season?` | `season_leaders` / `ok`; `stat=tov`; leaderboard rows. | Shows ordinary supported box-score stat leaderboards work. |
| `steal_leaders_this_season`, `block_leaders_this_season` | `season_leaders` / `ok`; `stat=stl` or `blk`; leaderboard rows. | These are the recommended alternatives in the personal-foul no-result guidance. |
| `net_rating_team_leaders` / `What teams have the best net rating this year?` | `season_team_leaders` / `ok`; `stat=net_rating`; leaderboard rows. Top row is OKC with `net_rating=11.1`. | Confirms league-wide team net-rating leaderboard support exists. |
| `offensive_rating_team_leader` | `season_team_leaders` / `ok`; `stat=off_rating`; leaderboard rows. | Confirms team advanced leaderboards are supported when asked as rankings. |
| `def_rating_team_leaders_wave4` | `season_team_leaders` / `ok`; `stat=def_rating`; ascending true for best defensive rating. | Confirms advanced-stat direction handling exists for leaderboards. |
| `pace_team_leaders_wave4`, `fastest_pace_teams_wave5` | `season_team_leaders` / `ok`; `stat=pace`; leaderboard rows. | Confirms advanced team metric support is leaderboard-scoped, not scalar-scoped. |

## 4. Root-cause analysis

### Personal-foul leaderboard boundary

- Findings:
  - `qa/raw_query_answer_corpus.yaml` already expects `players_personal_fouls_wave5` to share the `personal_foul_leaderboard` unsupported boundary.
  - Latest full run `outputs/raw_query_answer_qa/20260516T112341Z/report.md` fails five checks for this case: status, route, reason, shape, and missing `metadata.unsupported_filters.0`.
  - Direct parse probe raises an unrouted `ValueError`.
  - Direct execution probe returns `result_status=error`, `result_reason=unrouted`, `route=None`, no sections.
- Existing support:
  - Raw player game data has a `pf` column.
  - `player_game_summary`, `player_game_finder`, `game_summary`, `game_finder`, `team_record`, and split modules accept `pf` for game/sample-level filtering or summaries.
  - `personal_foul_leaders_wave4` already returns a clean unsupported no-result with `metadata.stat=pf`.
- Gaps:
  - `STAT_ALIASES` and `season_leaders.ALLOWED_STATS` do not include personal-foul leaderboard support.
  - `detect_personal_foul_leaderboard_boundary()` is coupled to `wants_leaderboard()`, which requires a supported leaderboard stat alias for `most`-style phrases.
  - Docs say personal-foul leaderboards are unsupported, but the docs only name `personal fouls leaders this season`; they should include `players with most personal fouls` after the boundary variant is fixed.

### Single-team net-rating boundary

- Findings:
  - `Warriors net rating this season` parses with `team=GSW`, `stat=net_rating`, `season=2025-26`, `team_leaderboard_intent=True`, but routes to `game_finder`.
  - `game_finder.ALLOWED_STATS` is game-log scoped and does not include `net_rating`, so execution returns `no_result` / `unsupported`.
  - The current no-result note is generic: `Unsupported stat: net_rating`.
  - The corpus currently expects `ok` / `season_team_leaders` / `leaderboard_table`, but the query wording is a single-team scalar lookup, not a league ranking.
- Existing support:
  - `data/raw/team_season_advanced/2025-26_regular_season.csv` contains GSW `off_rating=113.8`, `def_rating=114.4`, `net_rating=-0.5`, `pace=100.05`.
  - `season_team_leaders.ALLOWED_STATS` supports `off_rating`, `def_rating`, `net_rating`, and `pace`.
  - League-wide advanced leaderboards work and are documented.
- Gaps:
  - No single-team advanced-stat scalar route/result contract exists.
  - `game_summary` summarizes game-log stats and does not merge season-level team advanced metrics.
  - `season_team_leaders` has no team filter, single-team row contract, or rank-preserving lookup contract.
  - Docs do not currently state the single-team advanced scalar boundary.

## 5. Product/data support

| Needed behavior | Available? | Source/route | Notes |
|---|---|---|---|
| Raw player personal fouls by game | Yes | `data/raw/player_game_stats/*`, column `pf` | Direct sample probe found `pf` fully populated for 2025-26 regular season rows. |
| Player PF game/sample summaries | Yes | `player_game_summary`, `player_game_finder`, related game/sample modules | This does not imply leaderboard support. |
| Player PF season leaderboard | No contract | `season_leaders` | `pf` is absent from `season_leaders.ALLOWED_STATS`; Wave 7A intentionally made this unsupported. |
| Personal-foul unsupported boundary | Partially | `natural_query` -> `season_leaders` with `unsupported_filters` | Works for `personal fouls leaders this season`; misses `players with most personal fouls this season`. |
| Team season net rating data | Yes | `data/raw/team_season_advanced/*`, `season_team_leaders` merge | GSW 2025-26 row has `net_rating=-0.5`. |
| League-wide team net-rating leaderboard | Yes | `season_team_leaders` | `net_rating_team_leaders` passes. |
| Single-team net-rating scalar summary | No contract | None | Would require new route behavior or `game_summary` advanced-metric merge plus docs/tests/UI review. |
| Clean single-team advanced unsupported boundary | No, recommended | Natural routing + `_unsupported_filter_note()` | Add `unsupported_filters=["single_team_advanced_stat_summary"]` and boundary-specific guidance. |

## 6. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| A | One product-boundary cleanup wave: personal fouls explicit unsupported; single-team net rating explicit unsupported. | Small, honest, aligns with current contracts, should close both remaining corpus failures with stronger no-result assertions. | Does not add a direct Warriors net-rating answer even though source data exists. | Low. Main risk is choosing the right unsupported route and not catching league-wide team leaderboards. | Recommended. |
| B | Support net rating if an existing route can cleanly filter to Warriors; keep personal fouls unsupported. | User value for AQ-031 if route exists. | No current `season_team_leaders` team-filtered/single-row contract exists; forcing a leaderboard would be misleading or incomplete. | Medium. Could return broad top-10 leaderboard that does not include GSW. | Not recommended now. |
| C | Support both. | Maximizes answer coverage. | Requires PF leaderboard stat contract and single-team advanced scalar contract. More docs, tests, and frontend review likely needed. | Medium-high. Expands two product surfaces while the goal is boundary finalization. | Not recommended for this wave. |
| D | Split AQ-030 cleanup from AQ-031 separate product decision/support. | Keeps decisions isolated. | Adds process overhead; AQ-031 already has enough evidence to choose explicit unsupported for now. | Low, but slower. | Use only if product owner wants to prioritize single-team advanced support immediately. |

## 7. Recommended execution scope

- Exact goal:
  - Close the final two Raw Query Answer QA failures by making both product boundaries explicit and stable, without adding new stat support or frontend rendering.
- Cases to fix:
  - `players_personal_fouls_wave5`
  - `warriors_net_rating_single_team_wave5`
- Cases to mark unsupported/no-result, if any:
  - Keep `players_personal_fouls_wave5` as `no_result` / `filter_not_supported` with `personal_foul_leaderboard`.
  - Change `warriors_net_rating_single_team_wave5` from expected `ok` to expected explicit unsupported: `no_result` / `filter_not_supported` with `single_team_advanced_stat_summary`.
- Files to change:
  - `src/nbatools/commands/_parse_helpers.py`: decouple the personal-foul boundary from supported stat alias detection for clear `personal fouls` + leaderboard/ranking phrasing.
  - `src/nbatools/commands/natural_query.py`: preserve the existing PF unsupported route; add a guarded single-team team-advanced scalar boundary before generic `game_finder` fallback.
  - `src/nbatools/commands/_natural_query_execution.py`: add a boundary-specific note for `single_team_advanced_stat_summary`.
  - `tests/test_natural_query_parser.py`: parser assertions for `players with most personal fouls this season` and `Warriors net rating this season`.
  - `tests/test_ui_failure_coverage.py`: data-backed no-result assertions for both target cases and adjacent guardrails.
  - `qa/raw_query_answer_corpus.yaml`: only after product decision implementation, update AQ-031 expectations to the explicit unsupported boundary; AQ-030 can keep its current expected unsupported assertions, possibly with `metadata.stat=pf`.
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`: mark AQ-030 fixed as unsupported boundary; mark AQ-031 fixed as expected unsupported.
  - `docs/reference/query_catalog.md` and `docs/reference/query_guide.md`: document the verified unsupported phrasing variants after tests pass.
- Tests to add:
  - Parser: PF phrase variant routes to `season_leaders` with `unsupported_filters=["personal_foul_leaderboard"]`.
  - Parser: single-team `net_rating`/`off_rating`/`def_rating`/`pace` scalar query routes to the chosen unsupported summary boundary, while league-wide `best net rating teams` stays `season_team_leaders`.
  - Execution: both target queries return no sections, `result_reason=filter_not_supported`, and stable metadata.
  - Adjacent guardrails: turnover/steal/block leaderboards still work; `net_rating_team_leaders`, `offensive_rating_team_leader`, `def_rating_team_leaders_wave4`, and `fastest_pace_teams_wave5` still work.
- Corpus updates:
  - Do not change AQ-030 to support PF.
  - Update AQ-031 from `ok` to the explicit unsupported boundary after implementation; this is a product-boundary correction, not accepting the current generic `game_finder` failure.
- Findings updates:
  - AQ-030: `fixed_as_expected_unsupported`.
  - AQ-031: `fixed_as_expected_unsupported`, with note that scalar support remains a future feature if a route/result contract is approved.
- Harness validation:
  - Targeted two-case harness.
  - Adjacent harness for `personal_foul_leaders_wave4`, turnover/steal/block leaderboards, and team advanced leaderboards.
  - Full 243-case corpus; expected result is 243 passing.
- Stop conditions:
  - Stop if implementation returns a broad points leaderboard, broad team leaderboard, or top-10 team net-rating leaderboard for a single-team scalar query.
  - Stop if league-wide team advanced leaderboards regress.
  - Stop if personal-foul phrasing starts executing a PF leaderboard without an approved stat/result contract.
  - Stop if the single-team advanced unsupported boundary requires frontend rendering changes or backend `answer_phrase` enrichment.
- Tiered validation recommendation:
  - Focused parser tests for the new boundary phrases.
  - Focused data-backed tests in `tests/test_ui_failure_coverage.py`.
  - Targeted and adjacent Raw Query Answer QA harness runs.
  - Because `natural_query.py` is high fan-in, run `make PYTEST=.venv/bin/pytest test-query`, then `make PYTEST=.venv/bin/pytest test-preflight` if the diff is broader than the boundary helpers.

## 8. Validation performed

Commands/probes run:

```text
rg -n "players_personal_fouls_wave5|warriors_net_rating_single_team_wave5|personal_foul_leaders_wave4|offensive_rating_team_leader|defensive_rating_team_leader|net rating|personal fouls|fouls" ...
```

Summary:

- Confirmed latest full report path and exact failed expectation checks.
- Confirmed docs already describe personal-foul leaderboards as unsupported and team advanced stats as leaderboard-supported.

```text
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case players_personal_fouls_wave5 --case warriors_net_rating_single_team_wave5
```

Summary:

- Output: `outputs/raw_query_answer_qa/20260516T153006Z/report.md`
- Cases: 2
- Result statuses: `{'error': 1, 'no_result': 1}`
- Expectation cases: `{'fail': 2}`
- Failed IDs: `players_personal_fouls_wave5`, `warriors_net_rating_single_team_wave5`

```text
.venv/bin/python -c "... parse_query/execute_natural_query probes ..."
```

Summary:

- `players with most personal fouls this season`: parse error; execution `NoResult`, `result_status=error`, `result_reason=unrouted`, `route=None`, no sections.
- `personal fouls leaders this season`: parse route `season_leaders`, `stat=pf`, `unsupported_filters=["personal_foul_leaderboard"]`; execution `no_result` / `filter_not_supported`.
- `Warriors net rating this season`: parse route `game_finder`, `team=GSW`, `stat=net_rating`; execution `no_result` / `unsupported`, notes `["Unsupported stat: net_rating"]`.
- `What teams have the best net rating this year?`: parse/execution `season_team_leaders` / `ok`, `stat=net_rating`, 10 leaderboard rows.
- `What team has the highest offensive rating this season?`: parse/execution `season_team_leaders` / `ok`, `stat=off_rating`, 10 leaderboard rows.

```text
.venv/bin/python -c "... data availability probe ..."
```

Summary:

- `data/raw/player_game_stats/2025-26_regular_season.csv` has `pf`; 26,651 non-null rows in the probe.
- `data/raw/team_season_advanced/2025-26_regular_season.csv` has GSW `games_played=82`, `wins=37`, `losses=45`, `off_rating=113.8`, `def_rating=114.4`, `net_rating=-0.5`, `pace=100.05`.

```text
sed/rg probes over:
src/nbatools/commands/natural_query.py
src/nbatools/commands/_parse_helpers.py
src/nbatools/commands/_leaderboard_utils.py
src/nbatools/commands/season_leaders.py
src/nbatools/commands/season_team_leaders.py
src/nbatools/commands/game_finder.py
src/nbatools/commands/game_summary.py
src/nbatools/commands/team_record.py
tests/test_natural_query_parser.py
tests/test_ui_failure_coverage.py
docs/reference/query_catalog.md
docs/reference/query_guide.md
docs/reference/result_contracts/core_result_table_contracts.md
```

Summary:

- No production code, tests, or corpus files were changed.
- This return package is the only intentional file change.
