# Phase C4 Finder Inventory

> **Role:** row-shape and renderer-boundary inventory for
> [`phase_c4_work_queue.md`](./phase_c4_work_queue.md), item 1.

This inventory records the current finder and finder-adjacent result shapes
that feed `frontend/src/components/FinderSection.tsx` or nearby event-list
surfaces. It is implementation guidance for the C4 player-game-finder renderer,
not a new API contract.

Evidence sources:

- `FinderResult` and `CountResult` in
  `src/nbatools/commands/structured_results.py`
- `player_game_finder.build_result()`
- `game_finder.build_result()`
- `top_player_games.build_result()` and `top_team_games.build_result()`
- grouped boolean and OR post-processing in
  `src/nbatools/commands/_natural_query_execution.py`
- query metadata construction in `src/nbatools/query_service.py`
- Current `FinderSection.tsx` and `ResultSections.tsx`
- Current query docs that route best-game queries to `top_player_games`

---

## Shared finder contract

Plain finder command results currently serialize through:

- `query_class: "finder"`
- `sections.finder: SectionRow[]`
- CLI/raw labeled section: `FINDER`

`FinderResult` stores one DataFrame named `games`; `to_dict()` emits it as the
`finder` section. It can carry `current_through`, metadata, notes, and caveats.

Query metadata can provide route and identity context:

- `route` names the selected route, such as `player_game_finder` or
  `game_finder`.
- `player_context` can identify the resolved player for player finder queries.
- `team_context` can identify the resolved team for team finder queries.
- `opponent_context` can identify the resolved opponent when an opponent slot
  resolves.
- `grouped_boolean_used` identifies grouped boolean execution, but the actual
  boolean expression is not currently emitted as structured display metadata.

The shared contract does not currently expose explicit display metadata for
matched threshold text, primary stat, sort key, sort direction, limit,
truncation state, or a stable event-card schema. C4 should therefore use
route-specific ownership for `player_game_finder` and preserve generic finder
fallbacks for other finder-shaped results.

---

## Representative row shapes

### Player game finder: `player_game_finder`

Typical `finder` columns:

```text
rank, game_date, game_id, season, season_type, player_name, player_id,
team_name, team_abbr, opponent_team_name, opponent_team_abbr, is_home,
is_away, wl, minutes, pts, reb, ast, stl, blk, fg3m, fg3a, tov,
plus_minus, efg_pct, ts_pct, clutch_events, clutch_seconds, usg_pct,
ast_pct, reb_pct, tov_pct
```

Reliable fields:

- `player_name` and `player_id` support player identity and headshots.
- `game_date`, `game_id`, `season`, and `season_type` identify the game.
- `team_name` / `team_abbr` identify the player's team for that row.
- `opponent_team_name` / `opponent_team_abbr` identify the opponent.
- `is_home` / `is_away` support home/away labels such as `vs BOS` or `at BOS`.
- `wl` supports result badges when present.
- Box-score, shooting, clutch, and sample-aware rate fields are already
  supplied as row values and can be promoted for display.
- `rank` is inserted after sorting and limiting; it is displayable but should
  not be treated as a new basketball fact.

Gaps:

- The loaded player-game data requires `team_id` and `opponent_team_id`, but
  `player_game_finder` does not currently emit those ids in `output_cols`.
  Team/opponent badges can use abbreviations/names, but logo URLs are not
  reliably available from row data.
- There is no explicit `primary_stat`, threshold, operator, sort key, or
  filter summary in the result. React should not rebuild copy such as
  `5+ threes` from the natural query string.
- `limit` and whether the result was truncated are not emitted.
- Grouped boolean execution preserves rows but does not expose the grouped
  boolean expression as display metadata.

C4 target:

- Route only `player_game_finder` to the new player-game-finder renderer.
- Build game cards from the supplied row fields and query metadata.
- Promote conservative stat fields already present in rows.
- Keep the full finder table visible below the cards.

### Team game finder: `game_finder`

Typical `finder` columns:

```text
rank, game_date, game_id, season, season_type, team_name, team_abbr,
opponent_team_name, opponent_team_abbr, is_home, is_away, wl, pts, reb,
ast, fg3m, fg3a, tov, plus_minus, fg_pct, fg3_pct, ft_pct, efg_pct, ts_pct
```

Reliable fields:

- `team_name` / `team_abbr` identify the subject team.
- `opponent_team_name` / `opponent_team_abbr`, home/away flags, `wl`, and
  box-score fields are present for game-card-style treatment.
- `metadata.team_context` and `metadata.opponent_context` may identify
  resolved teams for the query.

Why C4 should not own it:

- C4 is scoped to player game finder. Team game finder needs team-specific
  identity hierarchy and should stay on `FinderSection.tsx` until a later
  team/head-to-head phase gives it an explicit layout.
- Row-level ids are not emitted, so team logo coverage would be weaker than
  the team-specific layout should eventually provide.

### Grouped boolean player finder output

Grouped boolean filters execute through finder routes and return a
`FinderResult` after post-processing the primary DataFrame.

Reliable fields:

- When the routed command is `player_game_finder`, the final rows keep the
  player finder shape.
- Metadata can set `grouped_boolean_used: true`.
- OR-combined finder results are deduplicated, sorted by date when possible,
  and re-ranked when a `rank` column is present.

Gaps:

- The boolean condition tree is not emitted as a structured display object.
- OR-combined rows may include only the first result's column order plus any
  extra columns discovered later.

C4 target:

- Player-game-finder cards should render these rows as ordinary player finder
  cards.
- Do not synthesize boolean-condition copy in React.

### Count results with finder detail

Count intent can convert an underlying `FinderResult` into `CountResult`.

Current shape:

```text
query_class: "count"
sections.count: [{ count: <number> }]
sections.finder: [...]  # optional matching games detail
```

Why C4 should not own it:

- The primary result class is `count`, not `finder`.
- Count and occurrence layouts are scheduled for a later phase. C4 should not
  add a count renderer or reroute count detail through player finder cards.
- The existing fallback must keep rendering both the count and finder detail.

### Top-game routes: `top_player_games` and `top_team_games`

Best-game and highest-single-game queries are event-list adjacent, but they do
not currently use `FinderResult`.

Current shape:

- `top_player_games` returns `query_class: "leaderboard"` and
  `sections.leaderboard`.
- `top_team_games` returns `query_class: "leaderboard"` and
  `sections.leaderboard`.

Typical `top_player_games` row fields:

```text
rank, player_name, player_id, team_abbr, game_date, game_id, <stat>,
opponent_team_abbr, is_home, is_away, season, season_type
```

Typical `top_team_games` row fields:

```text
rank, team_name, team_abbr, team_id, game_date, game_id, <stat>,
opponent_team_abbr, is_home, is_away, wl, season, season_type
```

Why C4 should not own it by default:

- These routes are leaderboard-shaped and currently belong to
  `LeaderboardSection.tsx`.
- Moving them to game cards would require a deliberate route-specific
  expansion beyond `query_class: "finder"`.
- C4 may record the residual, but its runtime boundary should stay
  `player_game_finder` unless the queue is explicitly updated later.

---

## Renderer boundary guidance

C4 should introduce a dedicated player-game-finder renderer only for:

- `data.route === "player_game_finder"`, or
- `data.result.metadata.route === "player_game_finder"`

Everything else should remain on the existing generic paths for now,
including:

- `game_finder`
- `query_class: "count"` results with `sections.finder`
- `top_player_games`
- `top_team_games`
- unknown or future finder-shaped routes

This route boundary is intentionally narrower than `query_class: "finder"`.
It keeps C4 scoped to player-game UX and avoids leaking player-specific
layout decisions into team game finders, count/occurrence results, or
leaderboard-shaped top-game routes.

---

## Player-game-card priority guidance

Use this conservative hierarchy for C4:

1. **Player identity:** prefer row `player_id` and `player_name`; fall back to
   `metadata.player_context` and then text-only labels.
2. **Game identity:** prefer `game_date`, `game_id`, `season`, and
   `season_type` when present.
3. **Opponent context:** prefer `opponent_team_name` / `opponent_team_abbr`;
   use `is_home` / `is_away` only to label location, not to infer missing
   opponent data.
4. **Result context:** show `wl` when present; omit it when missing.
5. **Stat emphasis:** promote supplied row stats such as `pts`, `reb`, `ast`,
   `fg3m`, `stl`, `blk`, `minutes`, `plus_minus`, shooting percentages, and
   rate/clutch fields. Do not calculate new metrics.
6. **Detail preservation:** keep `DataTable` detail visible for all columns,
   including sparse, custom, or future fields.

---

## Residual API/result-contract gaps

- Additive row ids: emitting `team_id` and `opponent_team_id` from
  `player_game_finder` and `game_finder` would improve logo coverage.
- Display metadata: a structured filter summary, primary matched stat, sort
  key/direction, and limit/truncation metadata would let cards explain why a
  game matched without parsing query text.
- Top-game routing: product/design should decide whether
  leaderboard-shaped single-game routes stay leaderboard-first or eventually
  share a game-card renderer.
- Count detail: later count/occurrence phases should decide whether matching
  game detail uses compact cards, expandable rows, or generic tables.
