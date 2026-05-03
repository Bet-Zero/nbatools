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

## 1. `[ ]` `game_summary` and `game_finder` game displays

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

- `cd frontend && npm test -- ResultSections TeamSummary Finder`
- `cd frontend && npm run build`

---

## 2. `[ ]` Aggregate `team_compare` display

**Route:** `team_compare`

**Why:** Head-to-head `team_compare` paths use `HeadToHeadSection`, but
aggregate team comparisons still fall back to generic comparison tables.

**Acceptance criteria:**

- Aggregate team comparison responses render a team-first header,
  side-by-side team cards, record/win-pct/games context, core team stats,
  and metric deltas with leader treatment.
- Head-to-head behavior keeps using `HeadToHeadSection`.
- Raw summary/comparison rows remain behind `RawDetailToggle`.
- `result_display_map.md` reflects the shipped behavior.

**Suggested tests:**

- `cd frontend && npm test -- ResultSections Comparison`
- `cd frontend && npm run build`

---

## 3. `[ ]` `player_on_off` split display

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

- `cd frontend && npm test -- ResultSections Count`
- `cd frontend && npm run build`

---

## 4. `[ ]` Lineup displays

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

- `cd frontend && npm test -- ResultSections Leaderboard`
- `cd frontend && npm run build`

---

## 5. `[ ]` `player_stretch_leaderboard` display

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

- `cd frontend && npm test -- ResultSections Leaderboard`
- `cd frontend && npm run build`

---

## 6. `[ ]` Top game leaderboards

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

- `cd frontend && npm test -- ResultSections Leaderboard`
- `cd frontend && npm run build`
