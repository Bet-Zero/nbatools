# Result Contracts Audit — Historical Snapshot

> **Status: historical audit (2025-04-16).**
> This document is a point-in-time audit of raw engine output against the
> target contracts in [result_contracts.md](../reference/result_contracts.md).
>
> Since this audit was written, the **structured result layer** has been
> implemented — all routes now produce first-class result objects
> (`SummaryResult`, `ComparisonResult`, `SplitSummaryResult`, `FinderResult`,
> `LeaderboardResult`, `StreakResult`, `CountResult`, `NoResult`) with
> consistent metadata, status, notes, and caveats. Many of the gaps
> documented below (missing section labels, missing metadata, no-result as
> an afterthought) have been resolved by that layer.
>
> This audit is retained for reference — it records the reasoning that
> motivated the structured result work. It should **not** be read as a
> description of current gaps.

## Purpose

This is an **audit of engine output behavior at a point in time** against the target contracts in [docs/reference/result_contracts.md](../reference/result_contracts.md). It is not a design doc and it is not a description of shipped contract compliance.

The goal is to measure how far the current raw/structured outputs are from the seven result classes and the shared metadata block, without changing product behavior. Nothing in this doc asserts that the engine already satisfies a contract; where the current code only partially aligns, that is called out explicitly.

Scope notes:

- No code changes in this pass.
- No refactors, feature expansion, or docs rewrites outside this file.
- "Raw output" here means the stdout text each command currently produces, which `natural_query._execute` and `cli_apps/queries._run_and_handle_exports` capture with `redirect_stdout`. That stdout blob is the engine's current transport. There is no in-memory result object being returned from any `run()` function.
- "Pretty output" means the transformed text produced by [format_output.py](../src/nbatools/commands/format_output.py) from that same raw blob.
- Exports (`--csv`, `--txt`, `--json`) are derived post-hoc from the same raw blob by `_write_csv_from_raw_output` / `_write_json_from_raw_output` in [natural_query.py](../src/nbatools/commands/natural_query.py) and [queries.py](../src/nbatools/cli_apps/queries.py). JSON export re-parses the CSV blocks back into dataframes.

Baseline observations that apply to every class below, and that are not repeated in each section:

- Every `run()` function emits results via `print(df.to_csv(index=False))`. Nothing returns a structured object.
- None of the commands emit `query_text`, `route` / `query_class`, `current_through`, `grouped_boolean_used`, `head_to_head_used`, or `notes / caveats` as per [result_contracts.md §4](../reference/result_contracts.md#4-shared-metadata-contract). These fields are missing universally.
- Resolved `date_window` (absolute start/end dates the engine actually used) is not emitted by any command, even though the engine computes it internally for `last N games`, `since <month>`, and `since All-Star break`.
- No command distinguishes `no_match`, `no_data`, `unrouted`, or `error`. The literal string `no matching games` is used for all empty-result paths.

---

## 1. Finder

Covers [player_game_finder.py](../src/nbatools/commands/player_game_finder.py), [game_finder.py](../src/nbatools/commands/game_finder.py), and the natural-query finder routes.

**Raw output shape today.** A bare CSV table written to stdout, with no leading section label. The column set for player finders is `rank, game_date, game_id, season, season_type, player_name, player_id, team_name, team_abbr, opponent_team_name, opponent_team_abbr, is_home, is_away, wl, minutes, pts, reb, ast, stl, blk, fg3m, fg3a, tov, plus_minus, efg_pct, ts_pct, usg_pct, ast_pct, reb_pct` (see [player_game_finder.py:224-257](../src/nbatools/commands/player_game_finder.py#L224-L257)). Empty result writes `no matching games` with no header.

**Stable section labels that already exist.** None. There is no `FINDER` label. The pretty formatter in [format_output.py:48-49](../src/nbatools/commands/format_output.py#L48-L49) identifies finder output by falling through to the `TABLE` default branch, and then uses the presence of a `rank` column to decide whether to render it as a ranked table.

**Metadata already present.** Per-row only: `game_date`, `season`, `season_type`, player/team identity, opponent identity, home/away, W/L. No header metadata.

**Metadata missing relative to the contract.**

- No header block at all — query text, route, resolved date window, opponent filter, home/away flag, W/L filter, grouped-boolean flag, truncation flag.
- No echo of the filter/context the user actually asked for (e.g. a query like `Jokic last 10 games over 25 points and under 15 rebounds` produces 10 rows but no record that the boolean expression was `over 25 points and under 15 rebounds`).
- No "sample size" or "count of matching games" field distinct from the row count; the consumer has to count rows itself.

**Is pretty formatting doing work that belongs in raw output?** Yes. `format_output._extract_sections` has to probe for the `rank` column to recognize this as a finder/leaderboard table, and `format_output.format_pretty_output` then picks a column subset and writes `Rows returned: N` — a value that only exists in pretty output. The column-ordering logic in [format_output.py:536-558](../src/nbatools/commands/format_output.py#L536-L558) is effectively raw-shape disambiguation living in a pretty renderer.

**Difficulty to align incrementally.** Low. Adding a `FINDER` section label and a small leading metadata CSV block is a handful of lines per command, and the stdout-text transport doesn't need to change. The `rank`-column signalling in the pretty formatter can then be removed.

---

## 2. Summary

Covers [player_game_summary.py](../src/nbatools/commands/player_game_summary.py), [game_summary.py](../src/nbatools/commands/game_summary.py), and the natural-query summary routes.

**Raw output shape today.** Two sections, both as CSV, separated by `SUMMARY` and `BY_SEASON` labels. The SUMMARY row carries the overall aggregates plus some per-row context (`player_name` / `team_name`, `season_start`, `season_end`, `season_type`, `games`, `wins`, `losses`, `win_pct`, the `_avg` and `_sum` box-score fields, and sample-aware `usg_pct_avg`, `ast_pct_avg`, `reb_pct_avg` for player summaries). BY_SEASON is a per-season breakdown with the same metric family. Empty result writes `SUMMARY\nno matching games`.

**Stable section labels that already exist.** `SUMMARY`, `BY_SEASON`. Both are in the "already stable" list in [project_conventions.md §6.4](../architecture/project_conventions.md#64-output-section-labels) and are referenced by [result_contracts.md §6](../reference/result_contracts.md#6-section-label-guidance).

**Metadata already present.** Span (`season_start`, `season_end`), `season_type`, games, wins/losses/win_pct, entity name. Sample-aware rate metrics are present for player summaries.

**Metadata missing relative to the contract.**

- No `query_text`, no `route`, no `current_through`.
- No resolved `date_window` when the request was `last N games` or `since <month>` — the engine filters on those but doesn't echo the absolute start/end dates it used.
- No `opponent_context` even when `Jokic summary vs Lakers` resolves through an opponent filter.
- No `player_id` / `team_id` — only name — so the SUMMARY row can't be joined against other data sources without string-matching.
- No `grouped_boolean_used` flag, even though grouped boolean filters are supported on summaries per [current_state_guide.md §grouped-boolean-coverage](../reference/current_state_guide.md#grouped-boolean-coverage).
- No `notes / caveats` field for the case where the sample-aware rate metric is recomputed from the filtered sample rather than a season average — which per [result_contracts.md §4](../reference/result_contracts.md#4-shared-metadata-contract) is the canonical example of a silent fallback that should become visible.

**Is pretty formatting doing work that belongs in raw output?** Partly. The raw SUMMARY row already contains every numeric value the pretty view prints. But the metric-label mapping (`pts_avg` → `PTS`, `efg_pct_avg` → `eFG%`, etc. in [format_output.py:157-186](../src/nbatools/commands/format_output.py#L157-L186)) and the `Record: 9-1` formatting live in the formatter. Those are presentation and are fine there. The one load-bearing thing that doesn't exist in raw output is any header identifying this as a `summary` result class.

**Difficulty to align incrementally.** Low-to-medium. This class is the closest to the contract today. The biggest wins are adding a stable metadata header above `SUMMARY`, surfacing resolved date windows, and marking sample-aware recomputation as a caveat.

---

## 3. Comparison

Covers [player_compare.py](../src/nbatools/commands/player_compare.py), [team_compare.py](../src/nbatools/commands/team_compare.py), and natural-query comparison routes including `vs`, `h2h`, and `head-to-head`.

**Raw output shape today.** Two sections: a `SUMMARY` CSV with one row per entity (containing `player_name`, `games`, `wins`, `losses`, `win_pct`, and the full `_avg` / `_sum` metric set including sample-aware rates), and a `COMPARISON` CSV with one row per metric and one column per entity (see [player_compare.py:319-351](../src/nbatools/commands/player_compare.py#L319-L351)).

**Stable section labels that already exist.** `SUMMARY`, `COMPARISON`. Both are stable.

**Metadata already present.** Per-entity identity and per-entity aggregates. The COMPARISON section is already a clean metric-vs-entities shape.

**Metadata missing relative to the contract.**

- The SUMMARY rows for a comparison do **not** include `season_start`, `season_end`, `season_type`, or any notion of the shared sample definition. The summary comparison raw output is structurally different from the player/team summary raw output in that respect. A consumer of the raw text cannot tell what time window the comparison covers.
- `head_to_head_used` is never emitted, even though [player_compare.py:268-282](../src/nbatools/commands/player_compare.py#L268-L282) literally branches on `head_to_head=True` and filters to same-game pairs. This is a significant gap: the contract calls this out specifically, and it is invisible in output today.
- No `sample_size_differs` indicator for the non-head-to-head case where entity A and entity B have different numbers of games in the sample.
- No opponent context, no date-window context, no route metadata.
- Grouped boolean context is correctly **not** in scope here per [result_contracts.md §3.3](../reference/result_contracts.md#33-comparison), so no gap there.

**Is pretty formatting doing work that belongs in raw output?** Partly. The pretty formatter reconstructs `Games: X vs Y`, `Record: ...`, `Win%: ...`, and the metric rows from the SUMMARY block. Those values are in raw. But the head-to-head distinction — which changes the meaning of the whole table — is only visible in the query string and is lost entirely on the way to the raw blob.

**Difficulty to align incrementally.** Medium. The SUMMARY rows need the same span fields the single-entity summary already has, a top-level metadata header needs to carry `head_to_head_used`, and the label `COMPARISON` is already stable. Plumbing the head-to-head flag from `natural_query` through to the emit point is the main non-trivial piece.

---

## 4. Split Summary

Covers [player_split_summary.py](../src/nbatools/commands/player_split_summary.py), [team_split_summary.py](../src/nbatools/commands/team_split_summary.py), and natural-query split routes.

**Raw output shape today.** Two sections: a `SUMMARY` CSV with one meta row (`player_name` / `team_name`, `season_start`, `season_end`, `season_type`, `split`, `games_total`) and a `SPLIT_COMPARISON` CSV with one row per bucket (`bucket`, `games`, `wins`, `losses`, `win_pct`, the `_avg` metric set, and sample-aware rates merged in from `compute_grouped_sample_advanced_metrics`). Empty result writes `SUMMARY\nno matching games`.

**Stable section labels that already exist.** `SUMMARY`, `SPLIT_COMPARISON`. Both are stable.

**Metadata already present.** Span, season type, split type, total games, bucket identity. This class is actually the best-carried split-type metadata in the engine today — `split` lives in the raw SUMMARY row as a machine-readable value.

**Metadata missing relative to the contract.**

- Same universal gaps: no `query_text`, no `route`, no `opponent_context`, no resolved `date_window`, no `grouped_boolean_used` (even though split summaries do support grouped boolean filtering per the current state guide).
- No per-bucket date range (buckets within the same sample can span the same window, but if a filter like `last 20 games` was applied, the resolved range is never echoed).
- The `split` field is a machine-safe enum (`home_away`, `wins_losses`), which is good — this is actually the one spot where a `split_type` field per [result_contracts.md §4](../reference/result_contracts.md#4-shared-metadata-contract) already exists in raw output.

**Is pretty formatting doing work that belongs in raw output?** Mostly no. The raw output already carries the canonical split enum. The pretty formatter maps `home_away` → `Home vs Away` and `wins` → `Wins` for display, which is presentation. The one load-bearing mapping is `_pretty_bucket_name` and `_pretty_split_name` in [format_output.py:139-154](../src/nbatools/commands/format_output.py#L139-L154); those are legitimate renderers.

**Difficulty to align incrementally.** Low. This is the closest class to target shape. The additive changes are a shared metadata header and the usual list of missing universal fields.

---

## 5. Leaderboard

Covers [season_leaders.py](../src/nbatools/commands/season_leaders.py), [season_team_leaders.py](../src/nbatools/commands/season_team_leaders.py), [top_player_games.py](../src/nbatools/commands/top_player_games.py), [top_team_games.py](../src/nbatools/commands/top_team_games.py), and natural-query leaderboard phrasing.

**Raw output shape today.** A bare CSV table with no leading section label. For `season_leaders`, columns are `rank, player_name, player_id, team_abbr, games_played, <target_stat>, season, season_type` (see [season_leaders.py:391-410](../src/nbatools/commands/season_leaders.py#L391-L410)). `season` and `season_type` are glued on to every row.

**Stable section labels that already exist.** None. Same detection hack as finder: the pretty formatter notices a `rank` column and routes through the ranked-table branch.

**Metadata already present.** Per-row: identity, games_played, season, season_type, and the ranking metric. `games_played` doubles as a qualifier field but its provenance (the merge with the season-advanced table vs the game-logs build) is not recorded.

**Metadata missing relative to the contract.**

- No header metadata at all — no query text, no `stat` being ranked, no `limit` / top-N value, no sort direction, no `min_games` qualifier that was applied, no FGA/FG3A/FTA minimum that was silently applied for percentage metrics in [season_leaders.py:298-306](../src/nbatools/commands/season_leaders.py#L298-L306).
- No resolved `date_window`, even though date-windowed leaderboards are a first-class feature and even though `_recommended_min_games` in [season_leaders.py:112-123](../src/nbatools/commands/season_leaders.py#L112-L123) quietly lowers the minimum-games threshold when a window is active.
- No `dataset source` provenance. [season_leaders.py:356-371](../src/nbatools/commands/season_leaders.py#L356-L371) builds from game logs and then optionally merges the advanced table; that distinction is exactly the [result_contracts.md §4](../reference/result_contracts.md#4-shared-metadata-contract) fallback case (`leaderboard metric not present in season-advanced table, derived from game logs`) and it is currently silent.
- No `notes / caveats` for the case where `ts_pct`, `usage_rate`, etc. came from the advanced table vs the basic one.

**Is pretty formatting doing work that belongs in raw output?** Yes, and visibly. `format_output._detect_value_column` in [format_output.py:77-136](../src/nbatools/commands/format_output.py#L77-L136) is an entire priority-list heuristic for guessing which column the leaderboard was ranked by — a fact that the raw output does not record. The pretty layer is reverse-engineering a value the engine already knew and discarded.

**Difficulty to align incrementally.** Medium. Adding a `LEADERBOARD` label and a metadata header are easy, but the most valuable gap to close — dataset provenance / fallback notes — requires threading a caveat from the merge branch in `season_leaders` out to the emit point. It is not hard in absolute terms; it is harder than the others because the fallback is currently implicit.

---

## 6. Streak

Covers [player_streak_finder.py](../src/nbatools/commands/player_streak_finder.py), [team_streak_finder.py](../src/nbatools/commands/team_streak_finder.py), and natural-query streak phrasing.

**Raw output shape today.** A bare CSV table with columns `rank, player_name, condition, streak_length, games, start_date, end_date, start_game_id, end_game_id, wins, losses, is_active, minutes_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, fg3m_avg, tov_avg, plus_minus_avg` (see [player_streak_finder.py:282-305](../src/nbatools/commands/player_streak_finder.py#L282-L305)). Empty result writes `no matching games` with no header.

**Stable section labels that already exist.** None.

**Metadata already present.** Per-streak: the `condition` column carries a hand-encoded threshold string (`pts>=20`, `triple_double`, `made_three`, `reb:10-15`). Start/end game IDs and dates are recorded. `is_active` flag is present. This class is actually the most self-descriptive of the label-less classes, because `condition` is doing most of the work a metadata block would do.

**Metadata missing relative to the contract.**

- The `condition` column is a flat string, not a machine-readable threshold definition. A UI would need to parse `pts>=20` to know what the stat, operator, and threshold were.
- `streak_mode` (longest vs. "N in a row") is not in raw output. The code branches on `longest` and `min_streak_length` but the result row doesn't carry which mode the user asked for.
- No season / season_type / date window.
- No opponent / home / away / W-L filter echo, even when the query contained one.
- Team streak finder has the same shape gap.
- Per-row player averages are present, but there is no per-game detail of the rows that satisfied the threshold, only aggregates. That is a separate design question and not strictly a contract gap, but worth noting.

**Is pretty formatting doing work that belongs in raw output?** Less than for finder/leaderboard. There is no streak-specific pretty renderer — streak output falls through the same `TABLE` / ranked-table branch as finder. The pretty layer doesn't invent streak-specific values, but it also doesn't present them well, because nothing upstream has labeled the shape.

**Difficulty to align incrementally.** Medium. The condition encoding is the trickiest piece: converting a flat `pts>=20` into structured `{stat: "pts", operator: "gte", value: 20}` is straightforward in the emit code but is a format change other code already depends on. A `STREAK` section label and a metadata header are cheap.

---

## 7. No-result / error-style

Covers the empty-state behavior of every command and the parser-level failure path in [natural_query.py](../src/nbatools/commands/natural_query.py).

**Raw output shape today.** A literal string. Summary/comparison/split paths print `SUMMARY\nno matching games`. Finder / leaderboard / streak paths print `no matching games` with no header. `_write_csv_from_raw_output` turns this into `message\nno matching games\n`. `_write_json_from_raw_output` turns it into `{"message": "no matching games"}`.

**Stable section labels that already exist.** None dedicated to the no-result class. `SUMMARY\nno matching games` is a piggyback on the summary label.

**Metadata already present.** Nothing beyond the literal message.

**Metadata missing relative to the contract.** Everything from [result_contracts.md §3.7](../reference/result_contracts.md#37-no-result--error-style-result):

- No `result_kind` enum — `no_match`, `no_data`, `unrouted`, `error` are indistinguishable in output. A query that routed and found nothing and a query that requested a season the engine does not have loaded are currently the same string.
- No `reason` code.
- No echoed `query_text`, no detected `route`, no partially-resolved filters so the user can see what the engine thought they meant.
- The parser-level `unrouted` path is not even a first-class empty result — it typically surfaces as an exception or a generic error, depending on the path.
- No differentiation between a finder that returned zero rows and a grouped-or query whose branches all returned zero rows (the latter is currently coerced to `no matching games\n` in `_combine_or_raw_outputs`).

**Is pretty formatting doing work that belongs in raw output?** Not really — the pretty layer just passes through `no matching games`. The issue isn't that pretty is inventing something; it's that raw has nothing to invent from.

**Difficulty to align incrementally.** Medium-hard in practice, mostly because this class does not exist in the code today — it has to be introduced, not tightened. Making it a first-class result requires (a) a stable `NO_RESULT` (or `ERROR`) section label and a small metadata block, (b) plumbing the query text and detected route down to the command's emit point, and (c) updating the export paths to understand the new shape. It is the highest-value gap for a UI — "no answer" is the case a UI most needs to render well — but it is also the least-scaffolded today.

---

## Gap summary

The gaps cluster into four groups, in decreasing order of how well the current code already supports them:

1. **Section labels.** `SUMMARY`, `BY_SEASON`, `COMPARISON`, `SPLIT_COMPARISON` are stable. `FINDER`, `LEADERBOARD`, `STREAK`, `NO_RESULT` / `ERROR` are missing. The pretty formatter currently detects unlabeled shapes by probing for a `rank` column, which is fragile and load-bearing. Adding the four missing labels is mostly additive.

2. **Per-row / per-class identity and context.** The summary/split classes carry span, season type, and entity name in raw output. Comparison is missing span fields. Finder, leaderboard, and streak carry identity per row but no class-level header. Most classes are missing `player_id` / `team_id` where they matter.

3. **Shared metadata block (contract §4).** Almost entirely missing across every class: `query_text`, `route`, resolved `date_window`, `opponent_context`, `grouped_boolean_used`, `head_to_head_used`, `current_through`, `notes / caveats`. These are universally absent from raw output and cannot be recovered by pretty or exports because they never exist upstream.

4. **Result transport.** The engine does not return structured results from `run()` — it prints CSV blobs to stdout that every downstream consumer re-parses. This is the deepest architectural gap and the one this audit explicitly recommends **not** tackling as part of incremental alignment. The contracts doc's own near-term guidance in [result_contracts.md §8.2](../reference/result_contracts.md#82-how-code-should-move-toward-these-contracts-without-a-rewrite) says to migrate opportunistically and avoid broad rewrites; moving off stdout transport is a broad rewrite.

One cross-cutting observation: the pretty formatter is doing a modest amount of work that should live in raw output, concentrated in two places — the `rank`-column detection and the leaderboard value-column detection. Both exist because the corresponding raw outputs lack a class label and lack a header identifying the ranking metric. Both become unnecessary the moment section labels and a small metadata header land.

---

## Recommended alignment order

Ordered from easiest / highest ROI to hardest. This is a sequencing suggestion, not a commitment.

1. **Add stable section labels for `FINDER`, `LEADERBOARD`, and `STREAK`.** One-line changes per command. Removes the `rank`-column hack in the pretty formatter. Makes the export-to-JSON path produce shaped-by-class payloads instead of bare row lists. No behavior change for users.

2. **Add a small shared metadata header above every command's existing sections.** Additive. A single `METADATA` (or similarly-named) CSV block at the top of each command's output carrying `query_text`, `route`, `season`, `season_type`, resolved `date_window`, entity IDs, `opponent`, and boolean flags. Every command's `run()` already has this information available.

3. **Echo `head_to_head_used` from `player_compare` / `team_compare`.** This is the one flag already computed that currently disappears. Belongs with step 2 but is worth calling out because the contract singles it out.

4. **Make `no-result` a first-class result class.** Introduce `NO_RESULT` (or `RESULT_KIND`) with `result_kind`, `reason`, `message`, and an echo of the resolved filters. Covers `no_match` vs `no_data` vs `unrouted` vs `error`. This is the highest-value gap for a future UI and the most visible gap today.

5. **Surface leaderboard dataset provenance as a `notes / caveats` entry.** When `season_leaders` derives a metric from game logs vs. from the season-advanced table, emit a machine-readable caveat. Same for the `fga_total`/`fg3a_total`/`fta_total` percentage-qualifier filters that currently apply silently.

6. **Surface the sample-aware recomputation caveat on player summaries and splits.** The rate metrics are recomputed from the filtered sample already; the caveat just needs to be emitted.

7. **Restructure the streak `condition` column into a machine-readable threshold definition.** Breaking change in raw shape — do this only when the streak class is already being touched for another reason.

8. **Move off stdout-as-transport.** Deliberately last. This is a real refactor and is explicitly out of scope for incremental alignment. The contracts are achievable without doing this.

---

## Recommended first implementation target

**Add stable section labels for `FINDER`, `LEADERBOARD`, and `STREAK`, plus a shared `METADATA` header block for every command.**

Rationale:

- Both changes are purely additive. No existing test needs its CSV assertions rewritten.
- Together they remove the pretty formatter's class-detection heuristics, which is the single clearest case of "pretty formatting doing work that should belong in raw structured output" in the current code.
- They create the scaffolding every later step in the alignment order needs. Caveats, head-to-head flags, resolved date windows, and the no-result class all slot into the header block once it exists.
- They do not require changing the result transport layer, so the stdout-capture architecture in `natural_query._execute_capture_raw` and `cli_apps/queries._run_and_handle_exports` continues to work unchanged.
- They are verifiable with a small number of new structured-output tests rather than a broad test rewrite, consistent with the testing guidance in [project_conventions.md §7](../architecture/project_conventions.md#7-testing-conventions).

This audit takes no position on when this work should happen. It only identifies what to do first when it does.
