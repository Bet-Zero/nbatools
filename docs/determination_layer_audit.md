# Determination Layer Audit

This audit covers every result shape listed in `docs/output_shapes.md` except
`Unclassified`. It is documentation-only. The query path reviewed is:

- `src/nbatools/api.py:natural_query`
- `src/nbatools/query_service.py:execute_natural_query`
- `src/nbatools/commands/natural_query.py:parse_query`
- `src/nbatools/commands/_natural_query_execution.py:_get_build_result_map`
- `src/nbatools/query_service.py:_build_query_metadata`
- `src/nbatools/api_handlers.py:query_result_to_payload`
- `frontend/src/components/results/config/routeToPattern.ts:routeToPattern`
- shape-specific renderers under `frontend/src/components/results/patterns/`

Raw sweep references are the fixtures classified in `docs/output_shapes.md`.
Current API behavior can expose fields that raw sweep JSON did not include,
because CLI/export serialization and API serialization do not preserve exactly
the same sections.

### Shape: Guided No Result
**Sweep fixtures:** 12
**Primary handler / source files:** `src/nbatools/query_service.py:execute_natural_query`, `src/nbatools/structured_results.py:NoResult`, `frontend/src/components/NoResultDisplay.tsx:stateProfile`, `frontend/src/components/results/ResultRenderer.tsx:ResultRenderer`

**1. Phrasing**
- Phrasing is produced in the frontend by `NoResultDisplay.tsx:stateProfile`.
- It is static by `reason` and `status`, not dynamically constructed from the
  failed query.
- Raw sweep examples include:
  - `No Matching Results` with message `No games or records matched the query filters.`
  - `Data Not Available` with message `Data is not available for requested scope.`
  - `Unsupported Query` with message `This query type is not supported yet.`
- Conditional branches are `error`, `no_match`, `no_data`, `unrouted`,
  `ambiguous`, `unsupported`, and `empty_sections`. Guided behavior is the
  subset where `suggestions` is non-empty.

**2. Field Selection**
- No tabular body fields are displayed. The body is a no-result card with
  `title`, `label`, `message`, optional `notes`, optional `caveats`, and
  suggestions.
- Field selection is entirely frontend-driven in `NoResultDisplay.tsx`.
- Suggestions are hardcoded static arrays. They are not pulled from the handler.
- Suggestions appear for `no_match`, `no_data`, and the default fallback. They
  do not appear for `error`, `unrouted`, `ambiguous`, or `unsupported`.

**3. Tie Handling**
- No ranked entries are produced, so no tie rule exists.

**4. Qualifiers**
- No display-level qualifier exists.
- Upstream handlers may have applied filters before returning no rows, but the
  no-result shape does not surface threshold values as a formal eligibility
  rule unless they are present in notes or metadata.

**5. Truncation**
- No rows are truncated.
- Suggestion counts are capped by hardcoded arrays: recoverable suggestions have
  four entries, no-data suggestions have three entries, and default suggestions
  have three entries.
- Notes and caveats are displayed as received by the frontend.

**6. Context**
- API metadata is attached by `query_service.py:_build_query_metadata` and then
  serialized by `QueryResult.to_dict`.
- Typical fields include `query_text`, `route`, `query_class`, `season`,
  `season_start`, `season_end`, `season_type`, date fields, stat thresholds,
  entity slots, `current_through`, `data_freshness`, `confidence`, `intent`,
  `notes`, and `caveats` when available.
- This shape often has route/slot context even though no result rows exist.
  The frontend no-result card displays notes and caveats, but not all metadata.

**7. Disambiguation**
- Ambiguity is detected before execution in `query_service.py:execute_natural_query`
  by checking parsed player/team ambiguities.
- Ambiguous inputs produce a `NoResult` with reason `ambiguous`; the frontend
  maps that to the `Ambiguous Query` profile. That profile is normally a
  message no-result rather than a guided no-result because it has no suggestions.
- If parser resolution chooses one entity, the user sees the chosen answer with
  no clarification prompt unless metadata notes happen to describe the choice.

**8. Scope Defaults**
- Scope defaults are inherited from parser and handler logic even though the
  result is empty.
- Default season comes from `src/nbatools/commands/_parse_helpers.py:default_season_for_context`:
  `2025-26` for regular-season context and `2024-25` for playoff context.
- Default `season_type` is `Regular Season` unless playoff/postseason wording is
  detected by `detect_season_type`.
- Date terms are anchored by `query_service.py:_parse_date_range_for_metadata`
  and `_date_utils.extract_date_range`; stale data anchors use
  `metadata.current_through`.

### Shape: Message No Result
**Sweep fixtures:** 81
**Primary handler / source files:** `src/nbatools/query_service.py:execute_natural_query`, `src/nbatools/commands/_natural_query_execution.py:_build_unsupported_result`, `src/nbatools/structured_results.py:NoResult`, `frontend/src/components/NoResultDisplay.tsx:stateProfile`

**1. Phrasing**
- Phrasing is produced by `NoResultDisplay.tsx:stateProfile`, with handler notes
  shown below the static card text.
- The card headline is static by status/reason. Handler notes are dynamically
  constructed by the handler that rejected the query.
- Raw sweep examples include:
  - `Unsupported Query` for unsupported advanced/date/team combinations.
  - `Query Error` for unrouted parser failures.
  - `No Matching Results` when a routed handler returns zero rows but no
    suggestions are shown.
- Conditional phrasing branches are the same as Guided No Result. Message No
  Result is the subset with no suggestion list.

**2. Field Selection**
- No tabular fields are rendered. The frontend displays the static message,
  optional notes, and optional caveats.
- Handler-specific notes come from sources such as
  `_natural_query_execution.py:_build_unsupported_result`,
  `player_on_off.py:build_on_off_note`, and no-row branches in individual
  command handlers.
- The frontend does not derive body fields from the failed route.

**3. Tie Handling**
- No ranked entries are produced, so no tie rule exists.

**4. Qualifiers**
- Qualifier failures are handler-specific and are not normalized at the shape
  layer.
- Examples include trusted-source requirements for on/off data in
  `player_on_off.py:build_result`, unsupported rolling/date advanced
  combinations in leaderboard handlers, and no matching rows after stat/date
  filters in finder handlers.

**5. Truncation**
- No rows are truncated.
- Notes and caveats are passed through without a shape-level cap.

**6. Context**
- Metadata is populated by `query_service.py:_build_query_metadata`, then
  serialized into `result.metadata`.
- For ambiguous entities, `execute_natural_query` creates a `NoResult` carrying
  `entity_ambiguity`, but `QueryResult.to_dict` replaces result metadata with
  service metadata. The user-facing result is therefore mainly the ambiguous
  card plus notes, not a structured candidate list.
- Unsupported routes usually include route, season, season type, stat slots, and
  notes/caveats if the route reached a handler.

**7. Disambiguation**
- Player and team ambiguity is handled before route execution in
  `query_service.py:execute_natural_query`.
- The frontend shows `Ambiguous Query` with a generic message. It does not render
  a selection UI or both possible answers.
- If parser aliases resolve to a single ID, downstream handlers receive the
  resolved ID and no visible ambiguity branch runs.

**8. Scope Defaults**
- Defaults match the parser path: regular season defaults to `2025-26`; playoff
  context defaults to `2024-25`; omitted season type defaults to
  `Regular Season`.
- For unsupported routes, defaults may still be present in metadata because they
  are finalized before execution.

### Shape: Entity Summary
**Sweep fixtures:** 45
**Primary handler / source files:** `src/nbatools/commands/player_game_summary.py:build_result`, `src/nbatools/structured_results.py:SummaryResult`, `frontend/src/components/results/patterns/EntitySummaryResult.tsx:summarySentence`, `frontend/src/components/results/config/routeToPattern.ts:routeToPattern`

**1. Phrasing**
- Phrasing is produced in `EntitySummaryResult.tsx:summarySentence`.
- It is dynamically constructed from the first summary row, metadata, and the
  query text.
- Raw sweep examples imply frontend sentences such as:
  - `Jayson Tatum has averaged 22.9 points, 9.1 rebounds and 5.1 assists in the 2025-26 regular season.`
  - `LeBron James has averaged ... in his career.`
  - `Kevin Durant has averaged ... from 2018-19 to 2025-26.`
- The sentence includes only the available `pts_avg`, `reb_avg`, and `ast_avg`
  values. If none exist, it falls back to
  `<name> has a summary available<context>.`
- Context branches are, in order: last-N wording, `this season`, `career`,
  season range, single season, then games count.

**2. Field Selection**
- The displayed summary card shows identity, the headline average sentence, and
  compact metric chips from the summary row.
- The headline uses `pts_avg`, `reb_avg`, and `ast_avg`. Additional metric chips
  are selected inside `EntitySummaryResult.tsx` from summary-row fields such as
  games, wins/losses, minutes, shooting percentages, and advanced averages when
  present.
- The handler computes a wider summary row in
  `player_game_summary.py:_build_summary_row`, including games, wins, losses,
  win percentage, average and sum box-score stats, and available advanced stats.
- `by_season` is computed by the handler but the `entity_summary` pattern does
  not display it as a table.
- Current API serialization may include `sections.game_log` from
  `SummaryResult.to_dict`, but the `entity_summary` route pattern ignores that
  table unless the query is classified as last-N.

**3. Tie Handling**
- No ranked list is displayed, so no tie rule exists for the shape.
- If the underlying sample includes multiple games on the same date, that does
  not affect the displayed single summary row.

**4. Qualifiers**
- No default minimum games, attempts, or minutes threshold is applied by
  `player_game_summary.py:build_result`.
- Explicit stat thresholds from the query are applied by `_apply_filters`.
- Specialized filters such as opponent, home/away, wins/losses, clutch, role,
  schedule strength, without-player, and opponent-player are applied only when
  parsed.

**5. Truncation**
- The displayed summary is one row.
- `by_season` is all matching seasons. Any API `game_log` section is the full
  filtered sample unless the query itself applied `last_n`.
- There is no `see more` or truncation notice in the frontend pattern.

**6. Context**
- Metadata comes from `query_service.py:_build_query_metadata`.
- Common fields are `query_text`, `route`, `query_class`, `season`,
  `season_start`, `season_end`, `season_type`, parsed date range, player,
  opponent/team filters, stat thresholds, `current_through`, `data_freshness`,
  `confidence`, `intent`, and `player_context`.
- `player_context` is added for API responses when a resolved player ID exists.
  Raw sweep JSON can omit this identity context because CLI/export metadata has
  a narrower field order.

**7. Disambiguation**
- Player resolution happens in `natural_query.py` helpers and is checked in
  `query_service.py:execute_natural_query`.
- Ambiguous unresolved names return a no-result before
  `player_game_summary.py:build_result` runs.
- `EntitySummaryResult.tsx:disambiguationNote` can display metadata keys such as
  `disambiguation_note`, `interpreted_as`, or `interpretation`, but the reviewed
  service metadata path does not consistently populate those keys for ordinary
  resolved player summaries.

**8. Scope Defaults**
- If no season is specified, parser finalization defaults player summaries to
  the regular-season default (`2025-26`) unless historical/career wording is
  detected.
- `season_type` defaults to `Regular Season`.
- `recent` wording defaults to `last_n=10` in `natural_query.py:_build_parse_state`
  when no number is supplied.
- Playoff wording changes the default season context to `2024-25 Playoffs`.

### Shape: Entity Summary + Recent Games
**Sweep fixtures:** 7
**Primary handler / source files:** `src/nbatools/commands/player_game_summary.py:build_result`, `src/nbatools/structured_results.py:SummaryResult`, `frontend/src/components/results/config/routeToPattern.ts:isLastNPlayerSummary`, `frontend/src/components/results/patterns/EntitySummaryResult.tsx:summarySentence`, `frontend/src/components/results/patterns/GameLogResult.tsx:GameLogResult`

**1. Phrasing**
- The summary sentence is produced by `EntitySummaryResult.tsx:summarySentence`.
- It is dynamic and uses the same average template as Entity Summary, with a
  last-N context branch from `metadata.window_size`, `metadata.last_n`, or a
  regex over `metadata.query_text`.
- Raw sweep examples imply frontend sentences such as:
  - `Luka Dončić has averaged 34 points, 6 rebounds and 7 assists in his last 5 games.`
  - `Nikola Jokić has averaged 24 points, 13.6 rebounds and 12.7 assists in his last 10 games.`
  - `Jayson Tatum has averaged ... in his last 5 games.`
- If no averages are present, it falls back to
  `<name> has a summary available in his last N games.`

**2. Field Selection**
- The top summary card uses the same fields as Entity Summary.
- The recent-games body is rendered by `GameLogResult.tsx` from
  `sections.game_log`, using player-game-log columns: rank, player, date, team,
  location, opponent, score if available, W/L, and available stat columns such
  as minutes, points, rebounds, assists, threes, steals, blocks, shooting splits,
  turnovers, and plus-minus.
- The handler determines available columns through
  `player_game_summary.py:GAME_LOG_COLUMNS` and `_build_game_log_section`.
- The frontend hides columns that are absent from the API rows; it does not add
  computed basketball fields.

**3. Tie Handling**
- No ranked tie rule exists for the summary card.
- The recent-games table is not metric-ranked. `GameLogResult.tsx:orderedRows`
  sorts by `game_date` descending when `preserveOrder` is false. Same-date ties
  return `0` from the comparator, so they preserve incoming order as an
  incidental JavaScript stable-sort behavior.
- The handler builds the game log sorted by `game_date` and `game_id` ascending,
  so same-date display order after frontend sorting is inherited rather than
  explicitly designed.

**4. Qualifiers**
- No minimum games, attempts, or minutes threshold is applied beyond the user
  requested last-N sample.
- Explicit filters from the query are applied by `player_game_summary.py:_apply_filters`.
- The shape requires the frontend route classifier to identify the query as
  last-N; otherwise any API `game_log` is ignored by the Entity Summary shape.

**5. Truncation**
- The list length is capped by `last_n` in the handler.
- If the user says `last 5`, five games are selected. If the user says
  `recent` without a number, parser defaults to `last_n=10`.
- There is no additional frontend cap and no `see more` affordance.

**6. Context**
- Metadata fields match Entity Summary, with last-N slots when present.
- `routeToPattern.ts:isLastNPlayerSummary` also infers last-N from query text if
  `metadata.window_size` is missing.
- Raw sweep JSON for the seven classified fixtures did not include
  `window_size` and did not include `sections.game_log`; current API responses
  for the same query family do include `sections.game_log`.

**7. Disambiguation**
- Same player-resolution path as Entity Summary.
- Ambiguous names stop before handler execution and render a no-result rather
  than a summary plus choices.

**8. Scope Defaults**
- Same as Entity Summary, plus parser default `last_n=10` for unnumbered recent
  phrasing.
- The default season is still applied before selecting the most recent N games,
  so recent means recent within the default or specified season scope, not
  necessarily all-time recent.

### Shape: Player Game Log
**Sweep fixtures:** 34
**Primary handler / source files:** `src/nbatools/commands/player_game_finder.py:build_result`, `src/nbatools/commands/top_player_games.py:build_result`, `frontend/src/components/results/config/routeToPattern.ts:routeToPattern`, `frontend/src/components/results/patterns/GameLogResult.tsx:GameLogResult`

**1. Phrasing**
- This shape has no headline sentence. `GameLogResult.tsx` renders a table and,
  when configured, a compact summary strip.
- Phrasing is mostly static section chrome such as table titles and summary
  labels.
- Raw sweep examples display rows such as:
  - Top player game: `Bam Adebayo`, `2026-03-10`, `83` points.
  - Finder result: matching player game rows with date, team, opponent, W/L, and
    stats.
- Conditional branches are route-based: `top_player_games` preserves handler
  order, while `player_game_finder` is displayed as a date-sorted finder table.

**2. Field Selection**
- Default visible columns are selected in `GameLogResult.tsx:tableColumns`.
- Player mode can show rank, player, date, team, location, opponent, score, W/L,
  minutes, points, rebounds, assists, threes, steals, blocks, field-goal,
  three-point, free-throw composites, turnovers, and plus-minus.
- Handler output columns are controlled by `player_game_finder.py:OUTPUT_COLUMNS`
  and `top_player_games.py` output construction.
- Fields are hardcoded by shape in the frontend, but only present API columns are
  rendered. Composite shooting columns are frontend presentation built from
  made/attempt/percentage columns.

**3. Tie Handling**
- `player_game_finder.py:build_result` sorts date queries by `game_date` and
  `game_id` descending. Stat-sorted finder queries sort by requested stat and
  then `game_date`; no player-name or game-ID tiebreaker is added for equal stat
  and date.
- `top_player_games.py:build_result` sorts by `[stat, game_date, player_name]`
  with metric direction controlled by `ascending`; for descending top games,
  equal stat values are ordered by earlier `game_date` first, then player name
  alphabetically.
- `GameLogResult.tsx` preserves handler order for `top_player_games`. For
  finder routes it re-sorts by `game_date` descending unless `preserveOrder` is
  true.

**4. Qualifiers**
- Finder qualifiers come from parsed query filters: player, team, opponent,
  home/away, wins/losses, dates, stat thresholds, clutch, role, and schedule
  strength.
- `top_player_games.py` only supports raw box-score stat columns listed in its
  stat maps; unsupported derived stats return no-result/unsupported.
- There is no default minimum games, attempts, or minutes threshold for either
  player-game-log route.

**5. Truncation**
- `player_game_finder.py:build_result` defaults to `limit=25`.
- `top_player_games.py:build_result` defaults to `limit=10`.
- Rows beyond the cap are silently omitted. The frontend does not show total
  available rows or a `see more` affordance.

**6. Context**
- Metadata includes route, query class, season/range, season type, date range,
  stat and threshold slots, player/team/opponent slots, `current_through`,
  freshness, notes, caveats, and resolved identity contexts when available.
- Top-game routes rely on metadata metric/stat fields for table highlighting,
  but the table also infers visible stats from row keys.
- Raw sweep metadata is narrower than current API metadata and may omit identity
  contexts.

**7. Disambiguation**
- Player ambiguity is checked in `query_service.py:execute_natural_query` before
  calling the finder or top-game handler.
- Ambiguous names return a no-result. The game-log table never displays multiple
  candidate players as a disambiguation mechanism.

**8. Scope Defaults**
- Season defaults to `2025-26` regular season unless the parser detects
  historical, range, career, or playoff wording.
- Date phrases are converted before execution and applied by handler filters.
- No default date window is applied to ordinary finder queries. Recent wording
  can set `last_n`, but top-game routes default to the whole parsed season scope.

### Shape: Team Game Log
**Sweep fixtures:** 7
**Primary handler / source files:** `src/nbatools/commands/game_finder.py:build_result`, `src/nbatools/commands/top_team_games.py:build_result`, `frontend/src/components/results/patterns/GameLogResult.tsx:GameLogResult`

**1. Phrasing**
- This shape has no dynamic headline sentence. It renders a team game table and
  optional summary strip through `GameLogResult.tsx`.
- Raw sweep examples include a Lakers finder row such as `2026-01-21`,
  opponent `CLE`, result `L`, and `99` points.
- Conditional route branches mirror Player Game Log: `top_team_games` preserves
  handler order; `game_finder` is treated as a finder table.

**2. Field Selection**
- Team mode columns in `GameLogResult.tsx:tableColumns` include date, team,
  location, opponent, score when present, W/L, and available team stat columns.
- Handler columns come from `game_finder.py:OUTPUT_COLUMNS` and
  `top_team_games.py` output construction.
- Fields are shape-hardcoded in the frontend and constrained by row keys.

**3. Tie Handling**
- `game_finder.py:build_result` uses the same sort shape as player finder:
  date/game ID for date sorting, or stat/date for stat sorting, with no final
  team-name tiebreaker for equal stat/date.
- `top_team_games.py:build_result` sorts by `[stat, game_date, team_name]`;
  descending stat ties use earlier date first, then team name alphabetically.
- Frontend date sorting can override finder handler order but preserves
  top-team handler order.

**4. Qualifiers**
- Finder filters include team, opponent, home/away, wins/losses, dates, and stat
  thresholds.
- Top-team-game routes support only stats present in the handler's team game
  data mappings.
- No default minimum games, attempts, or minutes threshold exists.

**5. Truncation**
- `game_finder.py:build_result` defaults to `limit=25`.
- `top_team_games.py:build_result` defaults to `limit=10`.
- Extra rows are silently omitted.

**6. Context**
- Metadata includes route, season/range, season type, date range, team/opponent
  slots, stat thresholds, current-through freshness, and identity contexts where
  resolved.
- Similar player-game-log metadata may include `player_context`; this shape uses
  team-oriented context fields instead.

**7. Disambiguation**
- Team ambiguity is checked before handler execution in
  `query_service.py:execute_natural_query`.
- Ambiguous team references produce a no-result, not a table with alternatives.

**8. Scope Defaults**
- Regular-season team game logs default to `2025-26`; playoff wording defaults
  to `2024-25 Playoffs`.
- No default recent window is applied unless the natural query parser sets
  `last_n` or a date range.

### Shape: Game Summary Log
**Sweep fixtures:** 4
**Primary handler / source files:** `src/nbatools/commands/game_summary.py:build_result`, `src/nbatools/structured_results.py:SummaryResult`, `frontend/src/components/results/config/routeToPattern.ts:routeToPattern`, `frontend/src/components/results/patterns/GameLogResult.tsx:GameLogResult`

**1. Phrasing**
- This shape has no custom lead sentence. It renders through
  `GameLogResult.tsx` with table/detail-section chrome.
- Raw sweep examples for `game_summary` contained `summary` and `by_season`
  sections rather than a displayed game log, so the frontend would fall back to
  the summary section for the main table.
- Conditional behavior is in `routeToPattern.ts`, where `game_summary` uses
  `fallbackSectionKey: "summary"` and detail drawers for `summary`,
  `by_season`, and `top_performers`.

**2. Field Selection**
- `game_summary.py:_build_summary_row` computes team summary fields such as
  games, wins, losses, win percentage, average points, opponent points, rebounds,
  assists, turnovers, plus-minus, shooting percentages, offensive rating,
  defensive rating, net rating, and pace when available.
- `game_summary.py:_build_game_log_section` uses `GAME_LOG_COLUMNS` for detailed
  rows when the handler includes a game log.
- The handler includes `game_log` only for last-N queries, date-window queries,
  or samples with five or fewer total games. Otherwise current raw outputs can
  have only summary/by-season tables.
- Frontend columns are determined by `GameLogResult.tsx` and available row keys.

**3. Tie Handling**
- No ranked list is displayed.
- When a game log is present, frontend finder sorting is by `game_date`
  descending, with same-date order inherited from the handler.

**4. Qualifiers**
- No minimum games, attempts, or minutes threshold is applied.
- Filters are parsed query filters: team, opponent, date range, home/away,
  wins/losses, stat thresholds, and schedule-strength filters.

**5. Truncation**
- The summary shape itself is not capped.
- `game_log` is conditionally included, not truncated by a separate display cap.
  The main implicit cap is the handler rule that omits detailed game rows unless
  the sample is last-N, date-windowed, or small enough (`<=5` games).
- There is no frontend notice that detailed game rows were omitted.

**6. Context**
- Metadata includes route, query class, season/range, season type, team/opponent
  filters, date range, stat thresholds, current-through freshness, notes, and
  team identity context when available.
- This shape can have rich computed context but a sparse displayed body if only
  `summary` and `by_season` are serialized.

**7. Disambiguation**
- Team ambiguity is handled before `game_summary.py:build_result` runs.
- The frontend does not offer a clarification UI inside the summary-log shape.

**8. Scope Defaults**
- Defaults are regular season `2025-26` unless playoff or historical wording is
  detected.
- No default date range is applied to ordinary team summary queries.
- `recent` or explicit last-N wording sets `last_n` before handler execution.

### Shape: Split Comparison
**Sweep fixtures:** 0
**Primary handler / source files:** `src/nbatools/commands/player_split_summary.py:build_result`, `src/nbatools/commands/team_split_summary.py:build_result`, `frontend/src/components/results/patterns/SplitResult.tsx:splitSentence`

**1. Phrasing**
- No live sweep fixture exercised this shape.
- Intended frontend phrasing is produced by `SplitResult.tsx:splitSentence`.
- It is dynamically constructed as
  `<entity>'s <split label> split for <context>.`
- Split labels come from the route configuration, for example `Home/Away` or
  `Wins/Losses`. If no entity or context is present, the sentence omits that
  part rather than asking a clarification question.

**2. Field Selection**
- Handler summary rows include identity, season/range, season type, split name,
  and total games.
- Split detail rows include bucket, games, wins, losses, win percentage, and
  average stats. Player splits can include advanced metrics merged from
  per-game samples.
- `SplitResult.tsx` displays fixed table metric candidates such as games,
  possessions, offensive/defensive/net rating, pace, points, rebounds, assists,
  minutes, threes, true shooting, effective field goal percentage, three-point
  rate, and plus-minus when those row keys exist.
- Fields are a combination of handler-produced rows and frontend hardcoded
  metric candidates.

**3. Tie Handling**
- Split rows are not ranked.
- Bucket order is explicit in the handlers: home before away, and wins before
  losses.
- Edge chips compare two buckets only. If the absolute difference is below
  `0.05`, `SplitResult.tsx:splitEdges` treats it as no meaningful edge and does
  not display that metric as a leader.

**4. Qualifiers**
- `player_split_summary.py:ALLOWED_SPLITS` allows `home_away` and `wins_losses`.
  Team split uses the same conceptual split set.
- No default minimum games, attempts, or minutes threshold is applied.
- Explicit query filters and optional `last_n` are applied before splitting.

**5. Truncation**
- The shape is naturally capped by the split bucket count: two buckets for
  home/away or wins/losses.
- Edge chips are capped at four metrics by `SplitResult.tsx:splitEdges`.
- There is no `see more` behavior.

**6. Context**
- Metadata is populated by `query_service.py:_build_query_metadata`, with route,
  season/range, season type, entity slots, opponent/team filters, stat filters,
  and current-through freshness.
- The split handlers also put split identity in the summary rows, not only in
  metadata.

**7. Disambiguation**
- Player/team ambiguity is handled before the split handler runs.
- The split renderer has no disambiguation UI.

**8. Scope Defaults**
- Parser defaults match other summary routes: `2025-26 Regular Season` unless
  playoff or historical wording changes context.
- If `last_n` is present, the handler filters to the most recent N games inside
  that season scope before splitting.

### Shape: On/Off Split
**Sweep fixtures:** 0
**Primary handler / source files:** `src/nbatools/commands/player_on_off.py:build_result`, `src/nbatools/commands/player_on_off.py:build_on_off_note`, `frontend/src/components/results/patterns/SplitResult.tsx:splitSentence`

**1. Phrasing**
- No live sweep fixture exercised this shape. Sweep on/off-style inputs reviewed
  as no-result/unsupported because trusted source coverage was unavailable for
  the requested scope.
- Intended frontend phrasing is the `SplitResult.tsx` split sentence with an
  `On/Off` label: `<player>'s on/off split for <context>.`
- Unsupported coverage phrasing is produced by
  `player_on_off.py:build_on_off_note` and rendered as Message No Result.

**2. Field Selection**
- Handler rows use `player_on_off.py:RESULT_COLUMNS`: season, season type,
  player name, team abbreviation, team name, presence state, games played,
  minutes, plus-minus, offensive rating, defensive rating, and net rating.
- `SplitResult.tsx` renders available metrics from its fixed candidate list.
- The on/off route configuration uses `sectionKey: "summary"` and suppresses
  the summary detail drawer title.

**3. Tie Handling**
- On/off rows are not ranked.
- Handler output is sorted by season, team, player, and presence state. That is
  ordering, not metric tie-breaking.

**4. Qualifiers**
- The handler requires trusted lineup-derived rows from
  `src/nbatools/commands/data_utils.py:trusted_lineup_rows`.
- It requires exactly one lineup member and a parsed presence state.
- If the source is missing or trust coverage is absent, it returns an
  unsupported no-result with a coverage note.
- There is no minimum games or minutes threshold beyond trusted-source
  availability.

**5. Truncation**
- No list cap is applied.
- The expected result has one or two presence-state rows depending on available
  source rows.

**6. Context**
- Metadata comes from the service path and includes route, player, season,
  season type, current-through freshness, notes, and caveats.
- Source trust and coverage explanations are carried in notes/caveats for
  unsupported cases rather than normalized metadata fields.

**7. Disambiguation**
- Player ambiguity is resolved before the handler. Ambiguous names render a
  no-result instead of an on/off split.
- Ambiguous lineup-member wording is not clarified in the frontend; the handler
  requires a concrete parsed player.

**8. Scope Defaults**
- Default season is the regular-season default (`2025-26`) unless playoff or
  historical wording changes it.
- Trusted lineup data may use its own available coverage after the parser scope
  is resolved; unsupported cases report coverage limitations rather than
  widening scope.

### Shape: Streak Table
**Sweep fixtures:** 15
**Primary handler / source files:** `src/nbatools/commands/player_streak_finder.py:build_result`, `src/nbatools/commands/team_streak_finder.py:build_result`, `frontend/src/components/results/patterns/StreakResult.tsx:streakSentence`

**1. Phrasing**
- Phrasing is produced by `StreakResult.tsx:streakSentence` from the first row.
- It is dynamic: `<length>-game <entity> <active/completed> <condition> streak from <start> to <end>.`
- Raw sweep examples include:
  - `18-game Nikola Jokić ... 20+ points streak from 2024-10-26 to 2024-12-08.`
  - Team winning or losing streak rows with condition text and start/end dates.
- Conditional branches add `active` when `is_active` is true and `completed`
  when false. If dates are absent, the date phrase is omitted.

**2. Field Selection**
- Frontend columns come from `StreakResult.tsx`: rank, entity, condition,
  length, optional status, start date, end date, games, record, and available
  averages such as points, rebounds, assists, minutes, true shooting, effective
  field goal percentage, threes, and plus-minus.
- Handler rows include streak identity fields (`start_game_id`, `end_game_id`,
  `start_date`, `end_date`, `streak_length`, `games`, `is_active`) and average
  stats from the streak sample.
- Fields are handler-produced and frontend-selected from a fixed candidate list.

**3. Tie Handling**
- Handlers sort by `streak_length` descending and `end_date` descending.
- There is no explicit entity-name, start-date, or game-ID tiebreaker after
  length/end-date ties.
- For `longest` queries, handlers keep all rows matching the maximum length
  before the final limit is applied, so tied longest streaks can appear together
  until the cap cuts them off.

**4. Qualifiers**
- Qualifiers are the parsed streak condition: stat threshold/range or special
  condition such as triple-double, made three, wins, or losses.
- `min_streak_length` is applied only if parsed.
- There is no default minimum games threshold beyond the streak condition
  itself.

**5. Truncation**
- Both player and team streak handlers default to `limit=25`.
- Rows beyond the cap are silently omitted.
- This differs from leaderboard routes that default to 10 and from playoff
  history routes that return all rows.

**6. Context**
- Metadata includes route, query class, player or team slots, season/range,
  season type, stat threshold slots, `current_through`, freshness, confidence,
  notes, caveats, and identity context when resolved.
- The display condition is mostly carried in row fields, not solely metadata.

**7. Disambiguation**
- Player/team ambiguity is checked before handler execution.
- Ambiguous inputs render a no-result rather than candidate streak tables.

**8. Scope Defaults**
- Streak queries with no explicit time scope default in
  `natural_query.py:_build_parse_state` to a three-season window ending at the
  context default season.
- Regular-season default end season is `2025-26`; playoff default is `2024-25`.
- `season_type` defaults to `Regular Season`.

### Shape: Playoff History
**Sweep fixtures:** 2
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_playoff_history_result`, `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx:historySentence`

**1. Phrasing**
- Phrasing is produced in `PlayoffHistoryResult.tsx:historySentence`.
- It is dynamic from the first summary row and metadata context.
- Raw sweep examples imply sentences such as:
  - `Los Angeles Lakers has 21 playoff appearances across 1996-97 to 2024-25, going 165-115 with ...`
  - Round-filtered history adds the round into the context when present.
- Conditional branches add record text, title/finals counts when fields exist,
  and either range, single-season, or generic playoff context.

**2. Field Selection**
- Handler summary fields include team name, season start/end, `Playoffs`
  season type, games, wins, losses, win percentage, seasons appeared, and
  optional playoff round.
- The body table uses `by_season`: season, games, wins, losses, win percentage,
  deepest round for season mode, or decade, games, wins, losses, seasons
  appeared, and win percentage for decade mode.
- Frontend column selection is hardcoded in `PlayoffHistoryResult.tsx`.

**3. Tie Handling**
- The team-specific playoff history shape is not ranked.
- `by_season` rows are sorted by season ascending. Decade rows are sorted by
  decade ascending. No metric tie rule is needed.

**4. Qualifiers**
- The handler filters to playoff data and optional team, opponent, and round.
- Round data relies on round-coded playoff coverage. The handler defines
  `ROUND_DATA_START_SEASON = "2001-02"` and round code mappings in
  `playoff_history.py`.
- No minimum games threshold is applied to team-specific history.

**5. Truncation**
- Team playoff history returns all matching seasons or decades.
- No frontend cap or `see more` behavior exists.

**6. Context**
- Metadata includes playoff route, team context, season range, season type
  `Playoffs`, optional opponent/round slots, current-through freshness, and
  notes/caveats.
- Round coverage caveats are handler notes/caveats rather than a distinct
  structured metadata policy field.

**7. Disambiguation**
- Team ambiguity is handled before `build_playoff_history_result`.
- Ambiguous teams render no-result. The playoff history shape never displays
  candidate teams.

**8. Scope Defaults**
- Playoff wording defaults season context to `2024-25 Playoffs` unless a range
  or all-time/historical phrasing widens scope.
- Team playoff history can use explicit range, decade grouping, opponent, or
  round filters from the parser.

### Shape: Playoff Round Records
**Sweep fixtures:** 2
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_playoff_round_record_result`, `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx:roundRecordSentence`

**1. Phrasing**
- Phrasing is produced by `PlayoffHistoryResult.tsx:roundRecordSentence`.
- It is dynamic from the first leaderboard row.
- Raw sweep examples imply sentences such as:
  - `Indiana Pacers owns 66.7% finals playoff mark (10-5) across 15 games.`
  - A wins query would use the same template with wins as the metric phrase.
- Conditional branches choose metric value from `win_pct`, `wins`, `losses`, or
  `games_played` and include record/games text when fields exist.

**2. Field Selection**
- Handler rows include rank, team name, round, games played, wins, losses,
  win percentage, seasons, and sometimes series-related fields.
- Frontend columns are fixed in `PlayoffHistoryResult.tsx` for round-record
  mode: rank, team, round, record, seasons, games, win percentage, and series
  fields when present.
- Target metric is handler-selected from parsed stat slots, defaulting to
  `win_pct` when no explicit target is supplied.

**3. Tie Handling**
- Handler sorting is by target metric, then `games_played`, then `team_name`.
- Direction depends on the target metric. For normal top records, target is
  descending, games played is descending, and team name is ascending.
- This is an explicit tiebreaker, unlike most game-log and streak shapes.

**4. Qualifiers**
- The default minimum games is `max(1, len(seasons) // 5)`.
- Filters include playoff round, team, opponent, and season/range.
- Round data starts at the handler's round-data coverage boundary for reliable
  round semantics.

**5. Truncation**
- Default `limit=10`.
- Rows beyond the limit are silently omitted.

**6. Context**
- Metadata includes route, playoff season type, season/range, team/opponent
  slots, round slot, target metric/stat, current-through freshness, notes, and
  caveats.
- Unlike general playoff history, this shape's body rows carry rank and metric
  context directly.

**7. Disambiguation**
- Team ambiguity is checked before execution.
- Ambiguous team or opponent names produce no-result; the round-record table
  never presents candidate entities.

**8. Scope Defaults**
- Playoff default season context is `2024-25` unless explicit range/all-time
  wording changes it.
- If no round is specified, the handler can aggregate across parsed/default
  round scope according to route slots.

### Shape: Playoff Matchup History
**Sweep fixtures:** 1
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_playoff_matchup_history_result`, `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx:matchupSentence`

**1. Phrasing**
- Phrasing is produced by `PlayoffHistoryResult.tsx:matchupSentence`.
- It is dynamically constructed from two team names and summary records.
- The raw sweep Heat/Knicks matchup implies:
  - `Miami Heat and New York Knicks have a playoff matchup history led by 19-16 against 16-19.`
- If records are absent, the fallback is
  `<team A> and <team B> have playoff matchup history available.`

**2. Field Selection**
- Handler summary rows contain one row per team with games, wins, losses, and
  win percentage.
- The comparison section is grouped by season or round depending on query slots.
  It includes season, round, winner/result when available, and team-prefixed
  record fields.
- Frontend columns are fixed in `PlayoffHistoryResult.tsx` for matchup mode.

**3. Tie Handling**
- The matchup history display is not a ranked leaderboard.
- Season rows are ordered by the handler's comparison construction, normally
  chronological by season. There is no explicit tie rule.
- Headline "led by" compares the first two summary records. If records are tied,
  the current sentence still uses the first summary row rather than a special
  tied branch.

**4. Qualifiers**
- Filters require two resolved teams and playoff data.
- Optional round and season/range filters are applied by the handler.
- No minimum games threshold is applied.

**5. Truncation**
- No list cap is applied. All matching matchup rows are returned.
- No `see more` behavior exists.

**6. Context**
- Metadata includes playoff route, two-team context, season/range, season type,
  optional round, current-through freshness, notes, and caveats.
- Raw sweep metadata may not include the richer API `teams_context`, but the
  renderer can infer names from rows when metadata is sparse.

**7. Disambiguation**
- Team ambiguity is handled before the matchup handler executes.
- Ambiguous team names return no-result. The shape does not show both possible
  matchups.

**8. Scope Defaults**
- Playoff matchup defaults to `2024-25 Playoffs` unless the parser detects an
  explicit range, all-time wording, decade grouping, or round.

### Shape: Comparison Panels
**Sweep fixtures:** 8
**Primary handler / source files:** `src/nbatools/commands/player_compare.py:build_result`, `src/nbatools/commands/team_compare.py:build_result`, `frontend/src/components/results/patterns/ComparisonResult.tsx:ComparisonResult`

**1. Phrasing**
- Phrasing is produced inside `ComparisonResult.tsx`.
- It is dynamic from summary rows, comparison metric rows, and metadata
  entities.
- Raw sweep examples imply:
  - `Nikola Jokić vs Joel Embiid: Nikola Jokić +8 Wins.` for recent-form
    comparison where games tie but wins differ.
  - For head-to-head rows, a branch such as
    `Joel Embiid leads Nikola Jokić 2-1 in this head-to-head sample.`
- Conditional branches are head-to-head record first, then first non-tied metric
  edge, then a generic comparison title with context.

**2. Field Selection**
- Subject cards use the two summary rows. They show record/sample context and up
  to eight metrics from a fixed candidate list.
- The comparison table uses handler-provided metric rows. Player comparison
  metrics include games, wins, losses, win percentage, minutes, points, rebounds,
  assists, steals, blocks, threes, plus-minus, effective field goal percentage,
  true shooting, usage, assist percentage, rebound percentage, and stat sums.
- Team comparison has a similar but team-oriented fixed metric list without the
  player advanced-percent set.
- The frontend derives value columns from row keys other than `metric` and then
  computes a display-only edge column.

**3. Tie Handling**
- Handlers do not sort ranked entries; they produce two summary rows and a fixed
  metric list.
- Frontend edge detection treats values within `1e-9` as tied.
- Lower is better only for `losses` and `tov_avg`; all other numeric metrics are
  treated as higher-is-better.
- If the first comparison metrics tie, the hero advances to the next metric
  with a leader. If all tie, it falls back to a generic sentence.

**4. Qualifiers**
- No default minimum games, attempts, or minutes threshold is applied.
- Parsed filters can include season/range, last-N, head-to-head, home/away,
  wins/losses, opponent/team context, and stat thresholds.
- If one compared entity has no rows, the handler can still return a zeroed
  summary row rather than no-result, unless both entities are empty.

**5. Truncation**
- Comparison panels are capped structurally at two subjects.
- Metric rows are a fixed handler list, not user-limited.
- No `see more` behavior exists.

**6. Context**
- Metadata includes route, query class, season/range, season type, compared
  entities, head-to-head flag when parsed, last-N/date filters, current-through
  freshness, and identity contexts.
- Comparison rows carry metric labels and values; metadata does not enumerate
  the metric policy.

**7. Disambiguation**
- Both compared entities are resolved before handler execution.
- Ambiguous player or team names render no-result before the comparison panel is
  built.

**8. Scope Defaults**
- Default comparison scope is `2025-26 Regular Season`.
- Recent wording can set `last_n=10` by default.
- Playoff wording switches the default context to `2024-25 Playoffs`.

### Shape: Team Record
**Sweep fixtures:** 35
**Primary handler / source files:** `src/nbatools/commands/team_record.py:build_team_record_result`, `src/nbatools/commands/team_record.py:build_matchup_record_result`, `frontend/src/components/results/patterns/RecordResult.tsx:teamRecordSentence`

**1. Phrasing**
- Phrasing is produced by `RecordResult.tsx:teamRecordSentence`.
- It is dynamically constructed from the first summary row and metadata context.
- Raw sweep examples imply:
  - `The Boston Celtics are 6-5 in the 2024-25 playoffs, a 54.5% win rate.`
  - Team-versus-opponent records add an opponent phrase when an opponent row or
    metadata field is present.
- Conditional branches add context from `this season`, single season, season
  range, playoffs/regular season, and opponent.

**2. Field Selection**
- Handler summary fields include team name, season start/end, season type,
  games, wins, losses, win percentage, points average, opponent points average,
  plus-minus average, net rating, rebounds, assists, and threes when available.
- `RecordResult.tsx` displays team, optional opponent, W-L, games, win
  percentage, points, opponent points, plus-minus, net rating, rebounds,
  assists, threes, and season type when those keys exist.
- `by_season` is available for multi-season records.

**3. Tie Handling**
- The ordinary team-record shape is not ranked.
- Matchup records compare two teams but do not apply a sort tiebreaker; the
  handler returns the requested team first and opponent second.

**4. Qualifiers**
- No default minimum games threshold is applied for a specific team's record.
- Parsed filters include team, opponent, season/range, season type, home/away,
  date range, and good/bad team filters where supported.
- No attempts or minutes qualifier exists.

**5. Truncation**
- Specific team records return one summary row plus all applicable by-season
  rows.
- No display cap or `see more` behavior exists.

**6. Context**
- Metadata includes route, team/opponent slots, season/range, season type,
  date range, current-through freshness, notes, caveats, and team identity
  context.
- Similar leaderboard record routes include rank/metric context in rows; this
  shape does not.

**7. Disambiguation**
- Team ambiguity is resolved before `team_record.py` executes.
- Ambiguous team references produce no-result. The record renderer has no
  clarification UI.

**8. Scope Defaults**
- Default team-record scope is `2025-26 Regular Season`.
- Playoff wording defaults to `2024-25 Playoffs`.
- If no opponent, date, or home/away scope is supplied, the whole season scope
  is used.

### Shape: Record By Decade
**Sweep fixtures:** 1
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_record_by_decade_result`, `frontend/src/components/results/patterns/RecordResult.tsx:decadeSentence`

**1. Phrasing**
- Phrasing is produced by `RecordResult.tsx:decadeSentence`.
- It is dynamic from the summary row and metadata context.
- Raw sweep example implies:
  - `The Golden State Warriors are 1175-1205 (49.4%) from 1996-97 to 2025-26 in the regular season, grouped by decade.`
- Conditional branches include single season, season range, playoffs, and
  regular-season context.

**2. Field Selection**
- Summary fields are team name, games, wins, losses, win percentage, season
  start/end, and season type.
- The displayed decade table includes decade, seasons appeared when present,
  W-L, win percentage, games, and season type.
- Fields are determined by `build_record_by_decade_result` and
  `RecordResult.tsx` decade-column rules.

**3. Tie Handling**
- This is not a ranked list.
- Decade rows are ordered chronologically by decade. No metric tie rule exists.

**4. Qualifiers**
- Requires a resolved team and decade grouping.
- No minimum games threshold is applied.
- Regular-season or playoff filtering is controlled by parsed season type.

**5. Truncation**
- All matching decades are returned.
- No display cap or `see more` behavior exists.

**6. Context**
- Metadata includes route, team context, season range, season type, current
  through/freshness, notes, and caveats.
- Decade identity is stored in rows, not metadata.

**7. Disambiguation**
- Team ambiguity is handled before execution.
- The shape does not display candidate teams.

**8. Scope Defaults**
- The default end season is `2025-26` for regular season and `2024-25` for
  playoffs.
- Decade grouping uses the parsed or default season range; historical wording
  can widen the range.

### Shape: Record By Decade Leaderboard
**Sweep fixtures:** 1
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_record_by_decade_leaderboard_result`, `frontend/src/components/results/patterns/RecordResult.tsx:decadeLeaderboardSentence`

**1. Phrasing**
- Phrasing is produced by `RecordResult.tsx:decadeLeaderboardSentence`.
- It is dynamic from the first row and target metric.
- Raw sweep example implies:
  - `The San Antonio Spurs won the most games in the 2010s, with 541 wins.`
- Conditional metric branches exist for wins, losses, win percentage, games, and
  generic metric labels.

**2. Field Selection**
- Handler rows include rank, team, decade, games played/games, wins, losses,
  win percentage, season type, and sometimes seasons.
- Frontend columns include rank, team, decade, target metric, W-L, games,
  win percentage, seasons, and season type while suppressing duplicate metric
  columns.
- Target metric comes from parsed stat/metric slots and handler defaults.

**3. Tie Handling**
- Handler sorting is by decade, target metric, games played, and team name.
- Ranks restart within each decade.
- Equal target and games values fall to team name alphabetically.

**4. Qualifiers**
- The handler groups by decade and metric. No broad minimum games threshold is
  documented as a shared rule for this shape.
- Parsed season type and range determine which games are included.

**5. Truncation**
- Default `limit=10` is applied per decade, not globally.
- If multiple decades are included, total returned rows can exceed 10.
- Rows beyond each decade cap are silently omitted.

**6. Context**
- Metadata includes route, metric/stat, season/range, season type, current
  through/freshness, notes, and caveats.
- The decade value is row-level context rather than a top-level metadata field.

**7. Disambiguation**
- Team names in rows are produced from grouped data. If a query specifies a team
  or opponent, ambiguity is handled before execution.
- Leaderboard rows do not include clarification choices.

**8. Scope Defaults**
- Regular-season decade leaderboards default to the latest regular-season
  context unless all-time/range wording widens scope.
- Playoff wording switches to the playoff default end season.

### Shape: Matchup By Decade
**Sweep fixtures:** 1
**Primary handler / source files:** `src/nbatools/commands/playoff_history.py:build_matchup_by_decade_result`, `frontend/src/components/results/patterns/RecordResult.tsx:matchupDecadeSentence`

**1. Phrasing**
- Phrasing is produced by `RecordResult.tsx:matchupDecadeSentence`.
- It is dynamic from the first two summary rows.
- Raw sweep example implies:
  - `The Los Angeles Lakers lead the Boston Celtics 31-27 in regular season games, grouped by decade.`
- Conditional branches are first team leads, second team leads, or tied.

**2. Field Selection**
- Summary rows include each team record in the full matchup scope.
- Comparison rows are decade buckets with team-prefixed wins, losses, win
  percentage, and points-per-game fields where available.
- Frontend columns are fixed in `RecordResult.tsx` for matchup-by-decade mode.

**3. Tie Handling**
- The headline explicitly handles tied overall records.
- Decade rows are chronological. There is no metric-ranked tie rule within the
  table.

**4. Qualifiers**
- Requires two resolved teams.
- Filters include season/range and season type.
- No minimum games threshold is applied.

**5. Truncation**
- All matching decade rows are returned.
- No display cap or `see more` behavior exists.

**6. Context**
- Metadata includes route, two-team context, season/range, season type,
  current-through freshness, notes, and caveats.
- Decade grouping is represented in rows.

**7. Disambiguation**
- Both teams are resolved before handler execution.
- Ambiguous team names return no-result, not multiple matchup candidates.

**8. Scope Defaults**
- Defaults match record-by-decade: latest regular-season end season unless
  playoff or historical/range wording changes the scope.

### Shape: Leaderboard Table
**Sweep fixtures:** 146
**Primary handler / source files:** `src/nbatools/commands/season_leaders.py:build_result`, `src/nbatools/commands/season_team_leaders.py:build_result`, `src/nbatools/commands/team_record.py:build_record_leaderboard_result`, `src/nbatools/commands/player_occurrence_leaders.py:build_result`, `src/nbatools/commands/team_occurrence_leaders.py:build_result`, `src/nbatools/commands/player_stretch_leaderboard.py:build_result`, `src/nbatools/commands/playoff_history.py:build_playoff_appearances_result`, `src/nbatools/commands/playoff_history.py:build_playoff_round_record_result`, `frontend/src/components/results/patterns/LeaderboardResult.tsx:leaderboardSentence`

**1. Phrasing**
- Phrasing is produced in `LeaderboardResult.tsx:leaderboardSentence`.
- It is dynamically constructed from the first row, entity kind, inferred metric,
  metric verb, and metadata context.
- Raw sweep examples imply:
  - `Luka Dončić scored the most points per game in the 2025-26 regular season, with 33.5 per game.`
  - `The Denver Nuggets had the most offensive rating in the 2025-26 regular season, with 120.8.`
  - Win-percentage team records use special copy such as highest/lowest win
    rate instead of the generic metric sentence.
- Conditional branches include player vs team entity, wins/losses/win
  percentage special cases, missing metric fallback, and context from season,
  date range, playoffs, or all-time wording.

**2. Field Selection**
- Frontend columns are selected by `LeaderboardResult.tsx`: rank, entity, the
  inferred metric column, then available display columns in `DISPLAY_ORDER`.
- Metric inference checks explicit props, metadata `stat`, `metric`,
  `target_stat`, `target_metric`, query hints, and then row-key priority.
- Handler rows differ by route:
  - `season_leaders.py` emits player, games played, target metric, context
    columns, season/range, and season type.
  - `season_team_leaders.py` emits team equivalents.
  - Occurrence leaders emit occurrence counts plus games played and season
    context.
  - Stretch leaders emit window size, stretch metric, start/end dates, and
    stretch value.
  - Record/playoff leaderboards emit wins/losses/win percentage/rank context.
- The frontend hides internal IDs and duplicate metric columns.

**3. Tie Handling**
- `season_leaders.py:build_result` sorts by target metric, games played, and
  player name. Metric direction follows top/bottom intent; games played is
  descending; player name is ascending.
- `season_team_leaders.py:build_result` sorts by target metric, games played,
  and team name.
- `team_record.py:build_record_leaderboard_result` sorts by target metric,
  games played, and team name.
- `player_occurrence_leaders.py` sorts by occurrence count, games played, and
  player name.
- `team_occurrence_leaders.py` sorts by occurrence count, games played, and team
  abbreviation/name.
- `player_stretch_leaderboard.py` sorts by stretch value, end date, and player
  name.
- Frontend does not resort leaderboard rows. It trusts handler order.

**4. Qualifiers**
- Player season leaders apply `_apply_default_guardrails` in
  `season_leaders.py`:
  count stats usually require 10 games, percentage and advanced rate stats
  usually require 20 games, date/opponent scoped samples can require 1 or 3
  games, playoff samples use smaller thresholds, and shooting percentage
  metrics have attempt floors.
- Team season leaders apply similar but not identical guardrails in
  `season_team_leaders.py`; team percentage attempt floors are larger than
  player floors.
- Team record leaderboards use `min_games=max(1, len(seasons))`.
- Occurrence leaderboards default to `DEFAULT_MIN_GAMES=1`.
- Stretch leaderboards require a positive `window_size`.
- Playoff round records use `max(1, len(seasons) // 5)`.
- These qualifier values vary by handler and are not centralized in one shared
  leaderboard policy.

**5. Truncation**
- Most leaderboard handlers default to `limit=10`.
- Stretches, occurrence leaders, season leaders, team leaders, record leaders,
  playoff appearances, and playoff round records all silently omit rows beyond
  the cap.
- Record-by-decade leaderboard applies `limit=10` per decade rather than
  globally.
- The frontend does not show total available rows or a `see more` affordance.

**6. Context**
- Metadata includes route, query class, season/range, season type, date range,
  stat/metric slots, min/max thresholds, entity filters, current-through
  freshness, confidence, intent, notes, caveats, and identity context where
  relevant.
- Row-level context differs by handler. Some leaderboards include `season` or
  `seasons`; others include date ranges, window starts/ends, or decade.
- The frontend infers the display metric from both metadata and rows, so missing
  metadata can still produce a table but can alter the headline metric.

**7. Disambiguation**
- For entity-filtered leaderboards, ambiguity is resolved before execution.
- League-wide leaderboards do not need entity disambiguation unless the query
  includes team, opponent, or player filters.
- No leaderboard shape displays clarification options.

**8. Scope Defaults**
- League/player/team leaderboards default to `2025-26 Regular Season`.
- Playoff leaderboards default to `2024-25 Playoffs`.
- Date-window or last-N wording narrows the sample before grouping.
- Default sort direction is top/highest unless parsed language asks for lowest,
  fewest, worst, or bottom.

### Shape: Fallback Tables
**Sweep fixtures:** 0
**Primary handler / source files:** `frontend/src/components/results/config/routeToPattern.ts:routeToPattern`, `frontend/src/components/results/patterns/FallbackTableResult.tsx:FallbackTableResult`, `frontend/src/components/DataTable.tsx:DataTable`, representative handlers `src/nbatools/commands/lineup_summary.py:build_result` and `src/nbatools/commands/lineup_leaderboard.py:build_result`

**1. Phrasing**
- No live sweep fixture exercised this shape.
- Fallback tables have no generated lead sentence. `FallbackTableResult.tsx`
  renders one card per non-empty section with a static section label.
- Labels are mapped by `SECTION_LABELS`; otherwise section keys are converted to
  display text.

**2. Field Selection**
- `FallbackTableResult.tsx` passes each row set to `DataTable.tsx`.
- `DataTable.tsx` auto-selects columns from `Object.keys(rows[0])`, hides ID
  columns such as `player_id`, `team_id`, `opponent_team_id`, `start_game_id`,
  and `end_game_id`, and applies generic identity-column handling.
- There are no shape-specific basketball columns. The output is whatever the
  handler serialized, minus generic hidden/internal columns.

**3. Tie Handling**
- No fallback-level sorting or tie-breaking exists.
- Row order is entirely inherited from the handler.
- Representative lineup leaderboard sorting is by the selected metric
  descending in `lineup_leaderboard.py`; no additional universal fallback
  tiebreaker is applied by the frontend.

**4. Qualifiers**
- Fallback has no display-level qualifiers.
- Representative lineup routes depend on trusted lineup rows from
  `data_utils.py:trusted_lineup_rows`, unit-size support, minute minimum filters,
  and handler-specific metric availability.

**5. Truncation**
- Fallback does not cap rows.
- Any cap is handler-specific. For example, `lineup_leaderboard.py` defaults to
  `limit=10`; lineup summary is naturally scoped by requested lineup.
- The frontend does not indicate hidden rows beyond a handler cap.

**6. Context**
- Metadata is the normal service metadata envelope.
- Fallback does not interpret metadata for a lead sentence or specialized
  context chips beyond generic result-envelope display.

**7. Disambiguation**
- Disambiguation is parser/handler-level only.
- The fallback renderer does not provide any clarification UI.

**8. Scope Defaults**
- Defaults are route-specific. Representative lineup routes use parser season
  defaults and trusted-source coverage; `trusted_lineup_rows` can default to the
  latest end season when none is supplied.
- Fallback itself does not define season, season type, date, or limit defaults.

## Cross-cutting observations

### Verification spot-checks
- Leaderboard Table: raw sweep `top PPG` has Luka Dončić first with
  `pts_per_game=33.484375` and 10 rows. That matches
  `season_leaders.py:build_result` default `limit=10`, metric-desc sorting, and
  the frontend's inferred player leaderboard sentence.
- Entity Summary + Recent Games: raw sweep `Luka last 5` has summary games `5`
  and averages `34/6/7`, but raw JSON includes only `summary` and `by_season`.
  Current API serialization includes a 5-row `game_log`; the discrepancy comes
  from `SummaryResult.to_sections_dict` omitting game logs while
  `SummaryResult.to_dict` includes them.
- Player Game Log: raw sweep top-player-game output has Bam Adebayo first with
  83 points on `2026-03-10`. That matches `top_player_games.py:build_result`
  sorting by requested stat and the frontend `preserveOrder` route config.
- Streak Table: raw sweep Jokic 20+ points streak has length `18`, start
  `2024-10-26`, and end `2024-12-08`. That matches the player streak handler's
  contiguous-game construction and length-desc/end-date-desc sort.
- Game Summary Log: raw sweep `game_summary` examples expose only summary and
  by-season sections for larger samples. That matches the handler condition that
  only includes `game_log` for last-N, date-windowed, or `<=5` game samples, and
  the frontend fallback to the summary section.

### Inconsistencies
- List caps differ without a shared rule: most leaderboards default to 10,
  player/team game finders default to 25, streak tables default to 25, top game
  logs default to 10, record-by-decade leaderboards default to 10 per decade,
  and history/record summaries often return all rows.
- Tie handling differs by handler. Season leaderboards use metric, games played,
  then name; top games use metric, earlier date, then name; streaks use length
  and end date only; game finders often have no final entity tiebreaker; summary
  and history tables usually have no tie concept.
- Qualifier floors are handler-local. Player leaders, team leaders, occurrence
  leaders, record leaders, playoff round records, and stretch leaders all define
  eligibility differently.
- Raw sweep/CLI output and current API output diverge for summary game logs:
  `SummaryResult.to_sections_dict` omits `game_log`, but API `to_dict` includes
  it. This affects the observed Entity Summary + Recent Games shape.
- Some shapes have dynamic headlines; others with comparable user importance
  have no lead sentence. Leaderboards, summaries, records, playoffs, streaks,
  and comparisons have hero copy; game-log and fallback-table shapes mostly do
  not.
- Context richness varies by consumer path. API metadata can include resolved
  identity contexts, while raw sweep export metadata can omit them.
- Record-by-decade leaderboard truncates per decade, while other leaderboard
  shapes truncate globally.

### Implicit / incidental behavior
- Same-date ordering in frontend game logs relies on stable-sort preservation of
  incoming handler order when the comparator returns `0`.
- Finder rows can be re-sorted by the frontend even after handlers rank and cap
  them, so display order is a mix of handler and frontend decisions.
- Leaderboard headlines infer metrics from row keys when metadata is missing,
  so phrasing can change if handler column names change.
- Entity Summary + Recent Games shape classification can come from regex over
  query text when explicit last-N metadata is absent.
- Ambiguity candidate metadata created on the `NoResult` object is not preserved
  as a displayed structured candidate list in the final API payload.
- Game Summary Log silently changes body shape based on sample size: large
  samples display summary fallback, while small/date/last-N samples can display
  detailed games.
- Generic fallback tables inherit row order, field order, qualifiers, and caps
  from whichever handler produced the data.

### Missing rules
- No shared truncation policy exists for list-like shapes.
- No shared tiebreaking policy exists for ranked tables.
- No shared eligibility/qualifier policy exists across leaderboard-like shapes.
- No display policy explains when a shape should have a headline sentence versus
  table-only output.
- No normalized context policy defines which metadata fields every comparable
  shape must expose.
- No frontend disambiguation policy exists; ambiguous inputs become no-result
  messages instead of candidate-selection displays.
- No normalized "rows omitted" or total-count field is displayed when handlers
  silently cap output.
- No explicit policy defines whether raw/CLI export sections should match API
  sections for summary-style results.

### Top recommendations
1. Define one truncation policy by result family: leaderboards, game logs,
   streaks, summaries, history tables, and fallback tables.
2. Define a shared ranked-table tiebreaking policy, including final stable keys
   such as entity name and game ID/date.
3. Centralize qualifier policy for leaderboard-like handlers, or document why
   player, team, occurrence, record, playoff, and stretch thresholds differ.
4. Decide whether current API and raw/CLI export should serialize the same
   sections for `SummaryResult`, especially `game_log`.
5. Define a minimum context contract for every result shape, including identity
   context, season scope, season type, date range, metric, qualifiers, and data
   freshness.
6. Decide which shapes require a user-facing lead sentence and which are
   intentionally table-only.
7. Add an explicit policy for capped results: whether to expose total available
   rows, cap values, and "showing top N" language.
8. Decide whether ambiguous inputs should show candidate choices in metadata and
   UI, or remain generic no-result messages.
9. Define whether handler order or frontend sorting owns display order for every
   game-log-like shape.
10. Document coverage/trust semantics for unsupported data families such as
   on/off and lineup-derived fallback shapes so no-result behavior is deliberate
   rather than incidental.
