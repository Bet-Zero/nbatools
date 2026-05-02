# Result Display Map

> **Role:** The single source of truth for "what each query result should
> look like." Every route the engine can return has an entry below.
>
> **How to use:** When you run a real query that doesn't display the way
> you want, find its route's entry. Fill in `Currently shows`, fill in
> `Should show` (your curated intent), then file an agent task to make the
> displayed output match the intent. This doc is the spec; the section
> components in `frontend/src/components/` are the implementation.
>
> **How to find a route:** Run the query in the deployed UI, click the raw
> JSON toggle (or hit `/query` directly), and read the `route` field. That
> name maps to one of the entries below.

---

## How displays are wired

Each query response carries two fields that determine display:

- `query_class` — the broad family (one of: `summary`, `comparison`,
  `split_summary`, `finder`, `leaderboard`, `streak`, `count`).
- `route` — the specific routing within that class.

The frontend's `ResultSections.tsx` switch dispatches by `query_class`,
then refines by `route` (or by data-shape predicates) to pick a section
component. Each section component is responsible for rendering one or
more route's results.

---

## Status legend

- `[ ]` — not audited yet (default)
- `[~]` — audited, intent written, fix in progress or queued
- `[x]` — audited, intent written, current display matches intent

---

## Compound results — important

Some routes intentionally combine multiple result types in one display.
For example, `player_game_summary` ("Jokic last 10 games") should show
**both** a summary-stat block (totals/averages over the 10 games) **and**
the actual 10 game logs. Single-stat or single-section displays are wrong
for these routes — make sure the `Should show` section is explicit when
the answer requires multiple parts.

---

# Routes by query class

## summary

### `player_game_summary` `[ ]`
- **Section component:** `PlayerSummarySection`
- **Example queries:**
  - `Jokic last 10 games`
  - `LeBron last 5 games`
  - `Curry this season`
- **Currently shows:** _fill in by running the query_
- **Should show:**
  - Hero block: player identity (headshot, name, team) + summary line ("Last 10 games")
  - Summary stats over the window: PTS / REB / AST / FG% / 3P% / FT% / MIN, displayed as averages (per game)
  - Game logs table: one row per game, columns for date, opponent, W/L, MIN, PTS, REB, AST, STL, BLK, TOV, FG, 3P, FT
  - Optional small visualizations: trend sparkline for primary stat
- **Bugs filed:** none yet
- **Notes:**

### `player_summary`-style routes for season averages `[ ]`
- **Example queries:**
  - `Jokic this season`
  - `Curry career averages`
- **Should show:** _TBD_

### `team_record` `[ ]`
- **Section component:** `TeamRecordSection`
- **Example queries:**
  - `Lakers record this season`
  - `Celtics record vs Bucks`
- **Currently shows:** _fill in_
- **Should show:** _TBD_

### `team_split_summary` `[ ]`
- **Section component:** `TeamSummarySection` (likely)
- **Example queries:**
  - `Lakers home vs away`
- **Should show:** _TBD_

### `game_summary` `[ ]`
- **Example queries:**
  - `Lakers Celtics last night`
- **Should show:** _TBD_

### `playoff_round_record` `[ ]`
- **Section component:** `PlayoffSection`
- **Example queries:**
  - `Celtics record in second round`
- **Should show:** _TBD_

---

## comparison

### `player_compare` `[ ]`
- **Section component:** `PlayerComparisonSection`
- **Example queries:**
  - `Jokic vs Embiid this season`
  - `LeBron vs MJ career`
- **Should show:** _TBD_ (likely two side-by-side player blocks with stat comparison)

### `team_compare` `[ ]`
- **Example queries:**
  - `Celtics vs Bucks this season`
- **Should show:** _TBD_

### `team_matchup_record` `[ ]`
- **Section component:** `HeadToHeadSection`
- **Example queries:**
  - `Lakers vs Celtics head-to-head`
- **Should show:** _TBD_

### `player_on_off` `[ ]`
- **Example queries:**
  - `Lakers on/off LeBron`
- **Should show:** _TBD_

---

## split_summary

### `player_split_summary` `[ ]`
- **Section component:** `SplitSummaryCardsSection` or `SplitSummarySection`
- **Example queries:**
  - `Jokic home vs away`
  - `Curry in wins vs losses`
- **Should show:** _TBD_ (likely two card-style split blocks)

---

## finder

### `player_game_finder` `[ ]`
- **Section component:** `PlayerGameFinderSection`
- **Example queries:**
  - `games where Jokic had over 25 points and over 10 rebounds`
  - `Curry's 50-point games`
- **Should show:** _TBD_ (game-log style list)

### `game_finder` `[ ]`
- **Example queries:**
  - `games where Lakers won by 20+`
- **Should show:** _TBD_

---

## leaderboard

### `season_leaders` `[ ]`
- **Section component:** `LeaderboardSection`
- **Example queries:**
  - `most ppg in 2025 playoffs`
  - `top 10 scorers 2025-26`
  - `assists leaders this season`
- **Currently shows:**
  - Designed view: ranked card per player with headshot, name, team chip, games played, season type, and one hero metric (PTS/AST/etc.)
  - Detail table below the designed view (now hidden after column-cleanup PR)
- **Should show:** _TBD — currently mostly correct, but for "best record" type queries the win/loss should appear as context_
- **Bugs filed:** playoff min-games threshold (running fix), redundant detail table
- **Notes:** leaderboard is the most-used class

### `season_team_leaders` `[ ]`
- **Section component:** `LeaderboardSection`
- **Example queries:**
  - `best record since 2015`
  - `most wins by a team in a season`
- **Should show:** _TBD — wins/losses chip alongside win% metric_
- **Bugs filed:** playoff min-games threshold (running fix), wins/losses missing as context

### `team_record_leaderboard` `[ ]`
- **Example queries:**
  - `best home records this season`
- **Should show:** _TBD_

### `player_stretch_leaderboard` `[ ]`
- **Example queries:**
  - `best 3-game scoring stretches this season`
- **Should show:** _TBD_

### `lineup_leaderboard` `[ ]`
- **Example queries:**
  - `best 3-man units this season`
- **Should show:** _TBD_

### `lineup_summary` `[ ]`
- **Example queries:**
  - `Lakers best lineup`
- **Should show:** _TBD_

### `player_occurrence_leaders` `[ ]`
- **Section component:** `OccurrenceLeaderboardSection`
- **Example queries:**
  - `most 30-point games this season`
  - `most triple-doubles all-time`
- **Should show:** _TBD_

### `team_occurrence_leaders` `[ ]`
- **Section component:** `OccurrenceLeaderboardSection`
- **Example queries:**
  - `most 120-point games this season`
- **Should show:** _TBD_

### `top_player_games` `[ ]`
- **Example queries:**
  - `top 10 scoring games this season`
- **Should show:** _TBD_

### `top_team_games` `[ ]`
- **Example queries:**
  - `top 10 team scoring games this season`
- **Should show:** _TBD_

---

## streak

### `player_streak_finder` `[ ]`
- **Section component:** `StreakSection`
- **Example queries:**
  - `Jokic 25-point game streak`
- **Should show:** _TBD_

### `team_streak_finder` `[ ]`
- **Section component:** `StreakSection`
- **Example queries:**
  - `Lakers longest win streak`
- **Should show:** _TBD_

---

## count / playoff / other

### Playoff routes `[ ]`
- **Section component:** `PlayoffSection`
- **Routes:** `playoff_appearances`, `playoff_history`, `playoff_matchup_history`, `playoff_round_record`
- **Example queries:**
  - `Lakers playoff history`
  - `Celtics vs Heat playoff matchups`
- **Should show:** _TBD_

---

## How to audit a route entry

For each entry above, follow this loop:

1. **Run the example queries in the deployed app.**
2. **Record what the UI shows now** in `Currently shows:`. Be specific —
   list every section that renders, what columns appear, what's missing.
3. **Write your curated intent** in `Should show:`. Be opinionated.
   Include section ordering, hero stats, what context chips to surface,
   what to hide.
4. **File any specific bugs** in `docs/planning/ui_bugs.md` and link them
   under `Bugs filed:`.
5. **Mark status `[~]`** when intent is written and fix is queued. Mark
   `[x]` once a PR has shipped that makes the display match the intent.

When the agent works a UI fix, it should reference this file's entry as
the spec — not invent its own interpretation of what the result should
look like.

---

## Working with this map

- Don't try to fill every entry in one sitting. Work through the routes
  you actually use first; let unused routes stay `[ ]` until you hit them.
- The most-used routes (`season_leaders`, `player_game_summary`,
  `team_record`, `player_compare`) are the highest leverage — getting
  those right covers most real usage.
- Compound routes (like `player_game_summary`) need explicit "show both
  X and Y" language in `Should show:` so agents don't pick one or the
  other.
- Update the entry as your taste evolves. The point is current truth, not
  historical record.

---

## Cross-cutting display rules

These apply to every section and don't belong to any single route entry:

- Hide internal columns (`player_id`, `team_id`, `team_abbr` when
  redundant with `team_name`) from any rendered table.
- Identity treatment: every player row should show headshot if available,
  fall back to initials. Every team row should show logo if available,
  fall back to abbreviation badge.
- Mobile: every layout must work on a phone-sized viewport. Tables that
  need horizontal scroll should keep the identity column sticky.
- Numeric formatting: per-game averages to 1 decimal. Percentages as
  `.xxx` (not `xx.x%`). Counts as integers.
- Freshness: the freshness banner should always show on results, honestly
  reflecting `current_through`.
