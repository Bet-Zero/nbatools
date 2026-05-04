# Result Display Follow-up Queue

This queue continues from `result_display_implementation_plan.md` item 11.
It contains only the route-level display gaps left after the first result
display implementation pass.

## Queue Rules

- Branch off `main` for every item.
- Use the matching route entry in `result_display_map.md` as the spec.
- Keep the frontend thin: render response data, do not add business logic
  or query parsing in React.
- If a route needs data not present in the API response, add it to the
  engine/API contract first.
- After frontend source changes, run `cd frontend && npm run build`.
- Use focused tests for the changed component(s), not full local suites.
- When an item is complete, check it off, commit, open a PR, wait for CI,
  merge when green, then continue to the next unchecked item.

---

## 1. `[x]` `game_summary` and `game_finder` game displays

**Routes:** `game_summary`, `game_finder`

**Why:** Both routes still use team-summary or generic finder/table
rendering. The map expects game-first displays that answer score/matchup
queries without opening raw rows.

**Acceptance criteria:**

- `game_summary` shows a final-score style result with both teams, logos,
  date/context, W/L, team stat comparison, and top performers when the
  response includes those rows.
- `game_finder` shows game cards with team, opponent, date, W/L,
  score/margin, condition/count context, and key team stats.
- Raw tables remain behind `RawDetailToggle`.
- The map entries for both routes are updated to `[x]` if shipped, or
  remain `[~]` with a narrower note if any data gap blocks full display.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 2. `[x]` Aggregate `team_compare` display

**Route:** `team_compare`

**Why:** Head-to-head `team_compare` paths need the same pattern renderer
coverage as aggregate team comparisons instead of falling back to generic
comparison tables.

**Acceptance criteria:**

- Aggregate team comparison responses render a team-first header,
  side-by-side team cards, record/win-pct/games context, core team stats,
  and metric deltas with leader treatment.
- Head-to-head behavior stays covered by `ComparisonResult` in head-to-head
  mode.
- Raw summary/comparison rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 3. `[x]` `player_on_off` split display

**Route:** `player_on_off`

**Why:** On/off results have no dedicated frontend branch and do not show
the expected `On`/`Off` cards or impact row.

**Acceptance criteria:**

- On/off responses render player/team identity, `On` and `Off` cards,
  minutes/possessions when available, offensive/defensive/net rating,
  pace, plus-minus, and primary box-score rates.
- A clear difference/impact row identifies the larger side, e.g.
  `On +7.4 net rating`.
- Raw rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 4. `[x]` Lineup displays

**Routes:** `lineup_leaderboard`, `lineup_summary`

**Why:** Lineup routes currently fall through to generic rendering. The map
expects lineup members, team context, minutes/games/possessions, and lineup
rating metrics to be primary.

**Acceptance criteria:**

- `lineup_leaderboard` shows ranked lineup rows/cards with members, team,
  minutes, games, possessions when available, season/minimum context, and
  the requested metric.
- `lineup_summary` shows a lineup summary hero/card with team, members,
  minutes, games, net/offensive/defensive rating, pace, plus-minus, and
  relevant splits when present.
- Raw rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 5. `[x]` `player_stretch_leaderboard` display

**Route:** `player_stretch_leaderboard`

**Why:** Stretch leaderboards use generic leaderboard rows and do not make
stretch length, date range, or included games visually obvious.

**Acceptance criteria:**

- Stretch leaderboard rows/cards show rank, player headshot/name, stretch
  length, date range, team, season, games included, and requested stretch
  metric.
- Supporting averages include REB, AST, TS%, and MIN when present.
- Optional game expansion is supported only if the response includes the
  necessary rows; otherwise the map should note the data gap.
- Raw rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 6. `[x]` Top game leaderboards

**Routes:** `top_player_games`, `top_team_games`

**Why:** Top-game leaderboards use generic leaderboard rows. The map
expects game-log leaderboard displays with date, matchup, W/L, score, and
box-score context.

**Acceptance criteria:**

- `top_player_games` shows ranked game rows/cards with player headshot,
  date, team/opponent, W/L, requested metric, and supporting player stats.
- `top_team_games` shows ranked game rows/cards with team logo/name, date,
  opponent, W/L, score, requested metric, and supporting team stats.
- Raw rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 7. `[x]` `game_summary` top performers

**Route:** `game_summary`

**Why:** Item 1 added team game cards and a `game_log` section for team
summary results, but the route still does not return player leader rows.
The map's remaining `[~]` note is specifically about top player
performers.

**Acceptance criteria:**

- Add engine/API support for top player performer rows when the requested
  game or game sample can be tied to player box-score data.
- Render points/rebounds/assists leaders in the game-summary display when
  those rows are present.
- Keep the behavior explicit when player performer data is unavailable;
  do not synthesize player leaders client-side.
- Update `result_display_map.md` to `[x]` for `game_summary` if the full
  display ships, or leave `[~]` with a narrower coverage note.

**Suggested tests:**

- focused pytest for the command/API contract changed
- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## Closeout Additions — 2026-05-04

These items were added by the `result_display_implementation_plan.md` item
11 reconciliation pass. They are the remaining `[~]` entries in
`result_display_map.md` after the first pattern-based renderer pass shipped
and the deployed main app was audited.

## 8. `[ ]` StatMuse-baseline player summaries

**Routes:** `player_game_summary`

**Why:** Last-N player summaries now compose `EntitySummaryResult` and
`GameLogResult`, but the map's locked baseline calls for a sentence-style
hero, one dense game-log answer table, and `Average` / `Total` footer rows
inside that table. The current first-pass result still leans on summary-stat
hero treatment and retained raw details.

**Acceptance criteria:**

- Last-N player summaries render one sentence-style player hero without stat
  tiles or chip rows.
- The game-log table is the primary open answer table, with all requested
  games and `Average` / `Total` footer rows.
- Redundant single-season `Full Summary` / `By Season` raw dumps are removed
  or moved into true secondary answer tables only when they add information.
- `result_display_map.md` marks `player_game_summary` `[x]` or narrows the
  remaining gap.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 9. `[ ]` StatMuse-baseline leaderboards

**Routes:** `season_leaders`, `season_team_leaders`

**Why:** `LeaderboardResult` is wired and functional, but the two highest-use
leaderboard routes still need the locked StatMuse baseline: a sentence hero,
disambiguation note when useful, dense answer table open by default, visually
highlighted queried metric, and no redundant raw leaderboard dump.

**Acceptance criteria:**

- Player and team leaderboards render a sentence-style hero for the #1 result.
- The answer table is dense, open by default, and highlights the queried
  metric column.
- Metric selection is correct for `ppg`, wins, win pct, and common team stats.
- Raw detail is removed when it duplicates the answer table.
- `result_display_map.md` marks `season_leaders` and
  `season_team_leaders` `[x]` or narrows any remaining route-specific gap.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 10. `[ ]` Record and historical fallback displays

**Routes:** `team_record`, `record_by_decade`,
`record_by_decade_leaderboard`, `matchup_by_decade`

**Why:** These routes return useful structured sections in the deployed app,
but they currently fall through to `FallbackTableResult`. The user-facing
answer should surface team identities, records, win pct, decade/range context,
and dense record or matchup tables without forcing raw-table reading.

**Acceptance criteria:**

- `team_record` has a dedicated record display with team logo, W-L, win pct,
  games/sample, filters, and collapsed supporting details.
- `record_by_decade` shows an identity header and decade table.
- `record_by_decade_leaderboard` shows a dense ranked historical leaderboard
  with the requested metric highlighted.
- `matchup_by_decade` shows a team-vs-team historical matchup header and
  decade comparison table.
- Raw sections remain available behind the shared collapsed raw-table toggle
  when they add debug/detail value.
- `result_display_map.md` marks these routes `[x]` or narrows any remaining
  route-specific gap.

**Suggested tests:**

- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`

---

## 11. `[ ]` Data-backed on/off and lineup verification

**Routes:** `player_on_off`, `lineup_leaderboard`, `lineup_summary`

**Why:** The deployed route examples are recognized, but they return
`no_result` / `unsupported` because the current data layer lacks trusted
play-by-play, stint, or lineup coverage for those slices. The frontend must
continue to render honest no-result states until the engine/API can return
trusted rows; once that happens, the row-bearing displays need deployment
verification.

**Acceptance criteria:**

- Do not synthesize on/off or lineup values in React.
- If engine/API coverage remains unavailable, keep the no-result messaging
  explicit and leave the map `[~]` with the data-coverage reason.
- If trusted rows become available, verify `player_on_off` through
  `SplitResult`, `lineup_leaderboard` through `LeaderboardResult`, and add or
  map a dedicated `lineup_summary` display as needed.
- `result_display_map.md` reflects the shipped behavior after verification.

**Suggested tests:**

- focused pytest for any engine/API contract changed
- `cd frontend && npm test -- ResultRenderer`
- `cd frontend && npm run build`
