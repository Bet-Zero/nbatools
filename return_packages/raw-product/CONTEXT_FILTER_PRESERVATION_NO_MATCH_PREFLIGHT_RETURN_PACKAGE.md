# Context / Filter Preservation + No-Match Diagnostics Preflight Return Package

## 1. Executive summary

- Main root-cause families:
  - Full-name player resolution bug: `Anthony Edwards` resolves to `Carmelo Anthony`.
  - Relative season parsing gap: `last season` is not mapped to `2024-25`.
  - Opponent-quality surface gap plus route-shape issue: `top defenses` is not recognized as `top-10 defenses`, and player stat-context wording defaults to a finder instead of a summary.
- Which cases are true bugs:
  - `anthony_edwards_last_10_summary_no_match`
  - `anthony_edwards_wins_losses_split_no_match`
  - `lakers_road_record_last_season`
  - `kd_ts_top_defenses_missing_filters`, if product accepts `top defenses` as shorthand for `top-10 defenses` and treats `KD TS% vs top defenses` as a summary question.
- Which cases are product-boundary/expectation decisions:
  - KD route shape is the only decision point. The filter loss is a real parser gap for a reasonable shorthand, but the expected `player_game_summary` shape should be explicitly affirmed.
- Recommended next execution:
  - Option A, one combined backend/parser wave, with three small fixes and targeted tests.
- Production code changed? no
- Tests changed? no
- Corpus changed? no

## 2. Target case reproduction

| Case ID | Query | Current route/status | Current behavior | Expected/desired behavior | Root cause hypothesis |
|---|---|---|---|---|---|
| `anthony_edwards_last_10_summary_no_match` | `Anthony Edwards last 10 games summary` | `player_game_summary` / `no_result` | Parser resolves player as `Carmelo Anthony`; 2025-26 has 0 Carmelo rows. Window filter is preserved. | Resolve `Anthony Edwards`; return summary + game_log for last 10 games. | Entity resolution checks broad `anthony -> Carmelo Anthony` before recognizing the full player name. |
| `anthony_edwards_wins_losses_split_no_match` | `How does Anthony Edwards shoot in wins versus losses?` | `player_split_summary` / `no_result` | Parser resolves player as `Carmelo Anthony`; split filters are preserved. | Resolve `Anthony Edwards`; return summary + split_comparison. | Same full-name player resolution bug. Split execution itself works. |
| `kd_ts_top_defenses_missing_filters` | `KD TS% vs top defenses` | `player_game_finder` / `ok` | `TS%` maps to `ts_pct`, but `top defenses` is not parsed as opponent quality. Route returns top TS% game rows with no quality filter. | Prefer `player_game_summary`, preserve `opponent_quality=top-10 defenses`, expose summary/game_log with `ts_pct_avg`. | `detect_opponent_quality` only matches `top-10 defenses` / `top 10 defenses`; stat-only player wording falls through to finder. |
| `lakers_road_record_last_season` | `Lakers road record last season` | `team_record` / `ok` | Road filter is preserved; season stays default `2025-26`, returning 25-16 away. No season applied-filter chip. | Resolve `last season` to `2024-25`; return Lakers 19-22 away record and expose explicit season context. | No singular relative-season parser for `last season`; applied-filter metadata only exposes season ranges, not explicit single-season context. |

## 3. Nearby behavior probes

| Query | Behavior | Why it matters |
|---|---|---|
| `Ant Edwards last 10 games` | `player_game_summary` / `ok`; Anthony Edwards, 10 games, 5-5, 25.5 PPG. | Confirms data and last-N summary execution are fine when entity resolution is correct. |
| `Ant Edwards wins vs losses` | `player_split_summary` / `ok`; summary + 2 split buckets over 61 games. | Confirms player win/loss split is supported for Anthony Edwards. |
| `Anthony Edwards season summary` | `player_game_summary` / `no_result`; resolves to Carmelo Anthony. | Confirms the no-match is not last-N-specific. |
| `Jokic wins vs losses` | `player_split_summary` / `ok`; summary + split_comparison. | Confirms the split route is supported generally. |
| `Kevin Durant TS% this season` | `player_game_finder` / `ok`; stat `ts_pct`; no quality filter. | Confirms TS% alias parsing works, but stat-only player wording defaults to finder. |
| `Kevin Durant against top defenses` | `player_game_summary` / `ok`; no opponent-quality filter. | Confirms `top defenses` phrase is not recognized even without TS%. |
| `Kevin Durant against top-10 defenses` | `player_game_summary` / `ok`; quality filter applied, 23 games, 26.696 PPG, .663 TS%. | Confirms top-defense execution works when parser recognizes the phrase. |
| `KD TS% vs top 10 defenses` | `player_game_finder` / `ok`; quality filter applied, 23 finder rows sorted by `ts_pct`. | Confirms exact `top 10` parsing and finder execution support opponent quality. |
| `Tatum against playoff teams this season` | `player_game_summary` / `ok`; quality filter applied. | Known passing player opponent-quality summary behavior. |
| `Lakers road record this season` | `team_record` / `ok`; 2025-26 away record 25-16. | Current default-season behavior matches the failing result. |
| `Lakers 2024-25 road record` | `team_record` / `ok`; 2024-25 away record 19-22. | Confirms execution and data are available for the intended last-season answer. |
| `Lakers away/home record last season` | `team_record` / `ok`; still uses `2025-26`. | Confirms the relative season phrase is dropped independent of location synonym. |

## 4. Root-cause analysis

### Anthony Edwards summary/no-match

- Findings:
  - `resolve_player_in_query("Anthony Edwards")` returns `Carmelo Anthony`, source `nickname`.
  - `PLAYER_FULL_NAME_ALIASES` does not contain `anthony edwards`.
  - `PLAYER_NICKNAME_ALIASES` contains `anthony -> Carmelo Anthony` and `edwards -> Anthony Edwards`; the broader first-name alias wins before data-driven last-name fallback.
  - Current 2025-26 data has 61 Anthony Edwards rows for MIN and 0 Carmelo Anthony rows.
  - `Ant Edwards last 10 games` returns the intended summary and game log.
- Existing support:
  - `player_game_summary` supports last-N summaries.
  - Anthony Edwards current-season data exists.
- Gaps:
  - Full-name entity matching should prefer an exact full-name/data-backed candidate before single-token nickname aliases inside that full name.

### Anthony Edwards win/loss split

- Findings:
  - Same `Anthony Edwards -> Carmelo Anthony` resolution failure.
  - `Ant Edwards wins vs losses` returns `player_split_summary` with `summary` and `split_comparison`.
  - `Jokic wins vs losses` also passes.
- Existing support:
  - Player win/loss splits are supported by parser and execution.
  - The corpus example is documented in `docs/reference/query_catalog.md`.
- Gaps:
  - This is not an unsupported split boundary. It is an entity-resolution bug.

### KD TS% top defenses

- Findings:
  - `TS%` and `true shooting` correctly map to `ts_pct`.
  - `top-10 defenses` and `top 10 defenses` map to `opponent_quality.surface_term=top-10 defenses`.
  - `top defenses` does not map to opponent quality.
  - Opponent-quality execution uses `team_season_advanced` defensive rating rank and is supported for `player_game_summary` and `player_game_finder`.
  - With exact `top 10 defenses`, finder execution applies the filter. With no stat, summary execution applies the filter.
  - With stat + player + context, route selection defaults to `player_game_finder`.
- Existing support:
  - `player_game_summary` includes `ts_pct_avg` and supports opponent-quality filtering.
  - `player_game_finder` supports `ts_pct` sorting and opponent-quality filtering.
- Gaps:
  - Parser should accept `top defenses` as a shorthand for `top-10 defenses`, if approved.
  - Route selection needs a policy for player + stat + opponent-quality context. For this corpus case, summary is the better direct-answer shape.

### Lakers road record last season

- Findings:
  - `LATEST_REGULAR_SEASON` is `2025-26`, so `last season` should resolve to `2024-25`.
  - Current parse keeps `season=2025-26`; `start_season` and `end_season` remain null.
  - Road/away and home filters are preserved correctly.
  - `Lakers 2024-25 road record` returns 41 games, 19 wins, 22 losses.
  - Current applied-filter metadata only emits `kind=season` for `start_season` + `end_season`, not a single explicit `season`.
- Existing support:
  - `team_record` supports location + explicit season.
  - 2024-25 team data exists.
- Gaps:
  - Singular relative season parser is missing.
  - Explicit single-season metadata needs to be represented when the query explicitly asks for a season-like context.

## 5. Implementation options

| Option | Scope | Pros | Cons | Risk | Recommendation |
|---|---|---|---|---|---|
| A | One combined wave for all four cases. | Small, related parser/context fixes; fastest path to 145/145; shared validation run is simple. | Touches entity resolution, parser defaults, query metadata, and docs/corpus in one PR-sized unit. | Medium, because route default changes can affect nearby stat-only player queries. | Recommended, with narrow route condition and focused tests. |
| B | Split into three waves: season/location; Anthony no-match; KD stat/opponent-quality. | Lowest regression risk per PR; easier review if any decision is contentious. | More overhead; leaves known 4-case failure state longer. | Low per wave. | Use only if KD route shape needs product review first. |
| C | Fix Lakers/KD, mark Anthony split unsupported. | Avoids split work. | Incorrect: Anthony split is supported when the entity resolves correctly. Would hide a real bug. | High product risk. | Not recommended. |

## 6. Recommended execution scope

- Exact goal:
  - Make the four remaining Wave 4B failures pass without weakening expectations.
- Cases to fix:
  - `anthony_edwards_last_10_summary_no_match`
  - `anthony_edwards_wins_losses_split_no_match`
  - `kd_ts_top_defenses_missing_filters`
  - `lakers_road_record_last_season`
- Cases to mark unsupported/no-result, if any:
  - None recommended.
- Files to change:
  - `src/nbatools/commands/entity_resolution.py`
  - `src/nbatools/commands/_parse_helpers.py`
  - `src/nbatools/commands/_seasons.py` or a new small helper in `_parse_helpers.py` for singular relative-season resolution
  - `src/nbatools/commands/natural_query.py`
  - `src/nbatools/commands/_default_rules.py` if the KD route policy is implemented as a named default
  - `src/nbatools/query_service.py` for explicit single-season applied filter metadata
  - `qa/raw_query_answer_corpus.yaml` after behavior is fixed, to add hard assertions/manual review status
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
  - `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`
  - `docs/reference/query_catalog.md`
  - `docs/reference/query_guide.md` if user-facing relative-season or `top defenses` examples are added
- Tests to add:
  - Entity resolution:
    - `resolve_player_in_query("Anthony Edwards") == "Anthony Edwards"`
    - guard `resolve_player_in_query("anthony") == "Carmelo Anthony"` if that alias remains intentional
  - Parser:
    - `parse_query("Anthony Edwards last 10 games summary")["player"] == "Anthony Edwards"`
    - `parse_query("How does Anthony Edwards shoot in wins versus losses?")["player"] == "Anthony Edwards"`
    - `parse_query("Lakers road record last season")["season"] == "2024-25"`
    - `parse_query("KD TS% vs top defenses")` preserves `stat=ts_pct`, `opponent_quality.surface_term=top-10 defenses`, and routes to `player_game_summary`
  - Query service/data-backed:
    - Anthony last-10 returns summary + 10 game_log rows.
    - Anthony wins/losses split returns summary + split_comparison.
    - Lakers last-season road record returns 19-22, season 2024-25, location filter, and season filter metadata.
    - KD TS/top-defenses returns summary + game_log and quality filter metadata.
- Corpus updates:
  - Keep current expectations.
  - Add hard assertions after fixes:
    - Anthony last 10 `summary.0.player_name`, `summary.0.games == 10`.
    - Anthony split `summary.0.player_name`, `summary.0.games_total == 61`, split buckets `wins` and `losses`.
    - Lakers `summary.0.season_start == 2024-25`, `wins == 19`, `losses == 22`.
    - KD `summary.0.player_name == Kevin Durant`, `game_log` row count 23 if stable, quality filter present.
  - Set target manual review statuses to `pass` when verified.
- Findings updates:
  - Close AQ-009, AQ-010, AQ-012 if targeted and full harness pass.
- Harness validation:
  - Targeted:
    - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id <run_id> --case anthony_edwards_last_10_summary_no_match --case kd_ts_top_defenses_missing_filters --case lakers_road_record_last_season --case anthony_edwards_wins_losses_split_no_match`
  - Adjacent:
    - Include `luka_last_5_summary`, `tatum_playoff_teams_summary`, `jokic_home_away_split`, `celtics_wins_losses_split`, `knicks_road_record`, and any exact `top-10 defenses` cases.
  - Full:
    - `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id <run_id>_full`
  - Standard tests:
    - `make test-parser`
    - `make test-query`
    - `make test-preflight` because `natural_query.py`, entity resolution, and `query_service.py` are high fan-in.
- Stop conditions:
  - Stop and escalate if product does not want `top defenses` to mean `top-10 defenses`.
  - Stop and split the wave if KD route-shape change causes broad stat-only player finder regressions.
  - Stop if explicit single-season applied-filter metadata causes unacceptable UI chip churn.

## 7. Risks / open decisions

- Parser ambiguity risks:
  - Changing full-name resolution order should not break intentional single-token aliases like `anthony -> Carmelo Anthony`.
  - `top defenses` should only be treated as opponent-quality context when introduced by `against`, `vs`, or `versus`; otherwise it can collide with team defensive leaderboard wording.
- Execution/regression risks:
  - Moving player + stat + opponent-quality queries to summary could affect users who expected top game logs for stat-only phrases. Keep explicit finder/list wording on `player_game_finder`.
  - Adding explicit season filter metadata may add chips to more results than expected if implemented too broadly.
- Product decisions:
  - Confirm that `top defenses` is an accepted shorthand for `top-10 defenses`.
  - Confirm that `KD TS% vs top defenses` should be a summary, not a sorted finder.
- Data caveats:
  - Opponent-quality top-defense buckets come from latest regular-season `team_season_advanced` defensive rating rank.
  - Current 2025-26 data is through `2026-04-12`; 2024-25 data is available for the Lakers road-record check.

## 8. Validation performed

Commands/probes run:

```bash
rg -n "anthony_edwards_last_10_summary_no_match|kd_ts_top_defenses_missing_filters|lakers_road_record_last_season|anthony_edwards_wins_losses_split_no_match" qa/raw_query_answer_corpus.yaml outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.md outputs/raw_query_answer_qa/20260513T084000Z_wave4b_full/report.jsonl
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_4B_COMPOUND_THRESHOLD_REPRESENTATION_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_4A_SCALAR_STAT_THRESHOLD_SEMANTICS_RETURN_PACKAGE.md
sed -n '1,220p' return_packages/raw-product/RAW_QUERY_ANSWER_QA_CORPUS_EXPANSION_WAVE_3_RETURN_PACKAGE.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md
sed -n '1,260p' docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md
sed -n '1728,1808p' qa/raw_query_answer_corpus.yaml
sed -n '1988,2022p' qa/raw_query_answer_corpus.yaml
sed -n '2530,2565p' qa/raw_query_answer_corpus.yaml
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --run-id 20260513T_wave5_preflight_targets --case anthony_edwards_last_10_summary_no_match --case kd_ts_top_defenses_missing_filters --case lakers_road_record_last_season --case anthony_edwards_wins_losses_split_no_match
```

Direct parse/execution probes run with `.venv/bin/python - <<'PY' ... PY` covered:

- Anthony Edwards target and nearby queries:
  - `Anthony Edwards last 10 games summary`
  - `Anthony Edwards season summary`
  - `Anthony Edwards last 10 games`
  - `Ant Edwards last 10 games`
  - `Anthony Edwards recent games`
  - `Anthony Edwards game log this season`
  - `Anthony Edwards splits in wins and losses`
  - `Anthony Edwards in wins vs losses`
  - `Ant Edwards wins vs losses`
  - `Ant Edwards shooting in wins vs losses`
  - `Jokic splits in wins and losses`
  - `Jokic wins vs losses`
- KD target and nearby queries:
  - `Kevin Durant true shooting this season`
  - `Kevin Durant TS% this season`
  - `Kevin Durant against top defenses`
  - `Kevin Durant true shooting against top defenses`
  - `KD TS% vs top defenses`
  - `KD TS% vs top 10 defenses`
  - `Kevin Durant true shooting against top-10 defenses`
  - `Kevin Durant against top-10 defenses`
  - `Jokic against top-10 defenses`
  - `best shooting vs top 10 defenses`
  - `Tatum against playoff teams this season`
- Lakers target and nearby queries:
  - `Lakers road record this season`
  - `Lakers road record last season`
  - `Lakers away record last season`
  - `Lakers home record last season`
  - `Lakers 2024-25 road record`

Targeted harness reproduction:

- Output path: `outputs/raw_query_answer_qa/20260513T_wave5_preflight_targets/report.md`
- Cases: 4
- Result statuses: `no_result: 2`, `ok: 2`
- Expectation cases: `fail: 4`
- Failed IDs: `anthony_edwards_last_10_summary_no_match`, `kd_ts_top_defenses_missing_filters`, `lakers_road_record_last_season`, `anthony_edwards_wins_losses_split_no_match`

Key probe summaries:

- `resolve_player_in_query("Anthony Edwards") -> Carmelo Anthony`; `resolve_player_in_query("Ant Edwards") -> Anthony Edwards`.
- 2025-26 Anthony Edwards rows: 61; 2025-26 Carmelo Anthony rows: 0.
- `Ant Edwards last 10 games` returns summary + by_season + 10 game_log rows.
- `Ant Edwards wins vs losses` returns summary + split_comparison.
- `KD TS% vs top defenses` returns finder rows with no quality filter.
- `KD TS% vs top 10 defenses` returns finder rows with the quality filter.
- `Kevin Durant against top-10 defenses` returns a summary with 23 games and the quality filter.
- `Lakers road record last season` returns 2025-26 away record 25-16.
- `Lakers 2024-25 road record` returns 2024-25 away record 19-22.
