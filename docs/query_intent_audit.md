# Query Intent Audit

**Scope:** Fine-grained mapping of every distinct query intent the system handles to the answer shape it currently produces, with gap analysis.

**Methodology:**

- Routing logic traced from `src/nbatools/commands/natural_query.py:_finalize_route`
- Handler data traced from every module under `src/nbatools/commands/`
- Intent constants from `src/nbatools/commands/_constants.py:ROUTE_TO_INTENT`
- Shape contracts from `docs/output_shapes.md` and `docs/determination_layer_audit.md`
- Example queries sourced from `outputs/parser_examples_full_sweep/results.csv` (402 cases, run `2026-04-26`)
- Query catalog: `docs/reference/query_catalog.md`

Sweep route distribution (ok-status examples): `season_leaders` 94, `player_game_summary` 52, `team_record` 35, `player_game_finder` 28, `player_occurrence_leaders` 16, `season_team_leaders` 13, `team_record_leaderboard` 10, `player_streak_finder` 10, `player_stretch_leaderboard` 8, `game_finder` 7, `player_compare` 4, `game_summary` 4, `team_compare` 4, `top_player_games` 6, `team_streak_finder` 5, `playoff_appearances` 3, `team_occurrence_leaders` 2, `playoff_history` 2, `playoff_round_record` 2, `playoff_matchup_history` 1, `record_by_decade` 1, `record_by_decade_leaderboard` 1, `matchup_by_decade` 1.

---

## Family: Single-Entity Performance

### Intent: Single-season player averages

- **What the user is asking:** "What are this player's stats for a specific season?" The implied answer is the standard season line: PPG/RPG/APG with shooting and advanced context.
- **Example queries:**
  - `Jokic this season`
  - `LeBron 2024-25 stats`
  - `How has Jayson Tatum played this season?`
  - `Jayson Tatum stats`
  - `What are Kevin Durant's averages this year?`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card showing player identity + one summary sentence (`<name> has averaged X pts, Y reb, Z ast in the 2025-26 regular season`) + compact metric chips (games, win%, FG%, TS%, USG%, etc.). No table.
- **Available data:** Handler produces `summary` (one aggregated row), `by_season` (one row per season in range, contains per-season splits), and optionally `game_log` (full filtered game log). The `by_season` and `game_log` sections are computed but not displayed in this shape.
- **Gap notes:** The user asks for season stats; they get exactly that via the summary row. However, there is no career-context comparison ("how does this compare to his previous seasons?"). The `by_season` table sits unused — if it were shown, the user could see the season in context of their career arc. For single-season intent, the absence of `by_season` is the primary gap.

---

### Intent: Career / all-time player averages

- **What the user is asking:** "What are this player's career averages across their entire NBA history?"
- **Example queries:**
  - `LeBron career`
  - `Kobe all-time stats`
  - `Jokic career averages`
  - `LeBron career regular season stats`
  - `How has Jokic done throughout his career?`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card with one summary sentence using the career context branch: `<name> has averaged X pts, Y reb, Z ast in his career`. Metric chips reflect career aggregates. No breakdown by season.
- **Available data:** Handler produces `summary` (one career-aggregate row) and `by_season` (one row per season). The `by_season` table is computed but not displayed in the Entity Summary shape.
- **Gap notes:** This is the most significant gap in the entire system. The user asking "LeBron career" almost certainly wants a season-by-season career breakdown table, not a single aggregated hero card. The `by_season` data is already computed and available in the `SummaryResult` but goes entirely unused here. The current shape shows career averages but gives no trajectory, no progression, no year-by-year comparison. Ideal answer: career summary hero + full `by_season` table.

---

### Intent: Season-range player averages

- **What the user is asking:** "What are this player's stats over a span of seasons?" (e.g., last 3 seasons, since a year, 2021-22 to 2023-24).
- **Example queries:**
  - `Jokic since 2021`
  - `Tatum from 2021-22 to 2023-24`
  - `LeBron last 3 seasons`
  - `Durant since 2022`
  - `Jokic playoff stats since 2021`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card with one aggregated row summarizing the entire range. Context branch reads `from 2021-22 to 2023-24`. No table.
- **Available data:** `by_season` contains one row per season in the range. `game_log` may be included if the range is short or last-N is used.
- **Gap notes:** Aggregating across a season range into a single number loses all trend information. A user asking "Jokic since 2021" likely wants to see season-by-season performance, not a 4-year average blob. The `by_season` data is computed but unused. Ideal answer: aggregated hero + `by_season` breakdown table.

---

### Intent: Recent-form summary (last N games, unfiltered)

- **What the user is asking:** "How has this player been playing recently?" The answer should be a short-window average plus the individual game log.
- **Example queries:**
  - `Jokic last 10`
  - `Luka last 5`
  - `Jokic recent form`
  - `LeBron last 15 games summary`
  - `Curry lately`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary + Recent Games** shape (when `isLastNPlayerSummary` detects the last-N signal)
- **Current answer structure:** Hero card (averages over last-N) + game log table showing the N individual games (date, team, opp, W/L, PTS, REB, AST, etc.).
- **Available data:** `summary` (aggregated averages), `game_log` (N individual games). `by_season` exists but has no separate entry for the last-N window.
- **Gap notes:** Shape is well-matched to intent. Minor issue: the frontend's `isLastNPlayerSummary` route classifier has to infer last-N from `metadata.window_size`, `metadata.last_n`, or by regex over query text — raw sweep JSON sometimes omits `window_size`, which means the same payload could display as Entity Summary (no game log) instead of Entity Summary + Recent Games. When that fallback fires, the game log disappears silently.

---

### Intent: Recent-form summary with context filter (last N + opponent/home/away/wins)

- **What the user is asking:** "How has this player been playing recently, specifically in a filtered context?" (e.g., last 5 road games, last 10 vs a team).
- **Example queries:**
  - `Luka last 5 vs OKC`
  - `Jokic last 10 away games`
  - `Tatum last 5 wins`
  - `luka w/o kyrie last 5`
  - `Jokic last 10 road games`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary + Recent Games** shape
- **Current answer structure:** Same as recent-form: hero card (averages over the filtered last-N sample) + game log table showing the filtered N games.
- **Available data:** Same sections as unfiltered recent-form. The filter context (opponent, home/away, opponent player) is only in metadata, not visually distinguished in the shape.
- **Gap notes:** The applied filters are not highlighted in the shape. A user asking "Luka last 5 vs OKC" gets a hero card that says "last 5 games" without visually flagging that these are specifically OKC games. The filter context appears only in metadata and caveats. Ideal answer: the filter conditions should be prominently visible in the hero context line.

---

### Intent: Full filtered-sample player summary (opponent, schedule context, opponent quality)

- **What the user is asking:** "How does this player perform under a specific condition?" (not a last-N window, but a whole-season filtered sample).
- **Example queries:**
  - `How has Jayson Tatum played against good teams this season?`
  - `Jokic against contenders 2024-25`
  - `Tatum clutch stats` (currently routes here unfiltered)
  - `LeBron as a starter stats`
  - `Jokic on 2 days rest`
  - `How has Anthony Davis rebounded when LeBron James was out?`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card with averages over the filtered sample. No game-log table (since this isn't classified as last-N). No comparison to the player's unfiltered baseline.
- **Available data:** `summary` (one aggregate row for the filtered sample), `by_season`, `game_log` (full filtered set, not shown unless last-N classified). Some filters (clutch, back-to-back, rest, role) are parsed and noted but execute unfiltered with an explicit note; others (opponent-quality, opponent-player, without-player) execute correctly.
- **Gap notes:** Three related gaps:
  1. **No baseline comparison.** The user asking "Tatum against good teams" presumably wants to compare to Tatum's overall numbers. The shape shows only the filtered sample, with no side-by-side. Ideal answer: filtered-sample summary + "vs overall" comparison chips.
  2. **Silently unfiltered context filters.** Clutch, period, back-to-back, rest, role, national TV queries route here, parse the filter, but return unfiltered results with only a text note. The shape gives no visual indication the filter did not apply. The hero sentence reads as if it's filtered when it isn't.
  3. **No game log for deep inspection.** The full filtered game log is available but not shown. When the sample is small (e.g., "Tatum in clutch situations"), showing individual games would be more informative than a single average row.

---

### Intent: Player summary vs specific opponent (head-to-head matchup stats)

- **What the user is asking:** "What are this player's stats when playing against a specific team?"
- **Example queries:**
  - `Jokic vs Lakers`
  - `LeBron averages vs Celtics career`
  - `Tatum vs Bucks this season`
  - `Jokic playoff stats vs Suns since 2021`
  - `Curry stats vs Lakers since 2021`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card with averages in the opponent-filtered sample. Opponent context appears in the metadata/caveats.
- **Available data:** `summary` (aggregated over opponent-filtered games), `by_season` (per-season in that matchup), `game_log` (full individual game log for that matchup). None but `summary` is displayed.
- **Gap notes:** For matchup-specific queries, the individual game log is usually exactly what the user wants — "show me every game Jokic played against the Lakers." The `game_log` is computed but discarded by the Entity Summary shape. Ideal answer: matchup hero (averages) + full game-log table of matchup games. The current shape treats this the same as a generic filtered summary, losing the "vs" context entirely in the visual presentation.

---

### Intent: Player stats vs opponent player (stats in games where opponent played)

- **What the user is asking:** "How does this player perform in games where a specific opponent player appeared?"
- **Example queries:**
  - `LeBron stats vs Kevin Durant`
  - `Jokic averages against Stephen Curry`
  - `Tatum vs Jaylen Brown stats`
- **Current route:** `player_game_summary` → `SummaryResult` → **Entity Summary** shape
- **Current answer structure:** Hero card with averages filtered to games where the opponent player appeared on the opposing team.
- **Available data:** Same sections as above. The opponent player filter is carried in metadata.
- **Gap notes:** Same as "vs specific opponent" — the game log would be more useful than a single aggregate row for this question type. Additionally, the "opponent player" concept is ambiguous: the system filters to games where that player appeared on the opposing team, which is not the same as direct defensive matchup data. The shape gives no visible indication of this semantic distinction.

---

### Intent: Team summary when player absent

- **What the user is asking:** "How does a team perform without a specific player?" (team-level, not player-level).
- **Example queries:**
  - `Suns when Booker out`
  - `Bucks when Giannis out`
  - `How do the Suns perform when Devin Booker didn't play?`
  - `Mavericks without Luka`
- **Current route:** `game_summary` → `SummaryResult` → **Game Summary Log** shape
- **Current answer structure:** Summary table showing team aggregates (W/L, pts, opp pts, ratings, etc.) for games without that player. Optional `by_season` and `top_performers` drawers.
- **Available data:** `summary` (team aggregates), `by_season` (per-season breakdown), `game_log` (individual game list — only included for last-N or small samples), `top_performers` (leading scorers/rebounders/assisters in that sample).
- **Gap notes:** The `game_log` section is suppressed for large samples. A user asking "Suns when Booker out" likely wants to see the actual list of games, not just aggregates. Also, `top_performers` data (who stepped up when Booker was out) is computed but rendered only as a drawer — this information is actually the most interesting part of the question and deserves prominent placement. Routing this through `game_summary` rather than through a team-record-like path loses the W-L record framing.

---

### Intent: Team period/context summary (with player absent, by season range, historical)

- **What the user is asking:** "How does this team perform in a specific sample?" (as opposed to record queries, which track wins/losses).
- **Example queries:**
  - `Celtics last 15 games summary`
  - `Lakers since 2020`
  - `Warriors career vs Celtics`
  - `Knicks playoff summary vs Heat since 1999`
- **Current route:** `game_summary` → `SummaryResult` → **Game Summary Log** shape
- **Current answer structure:** Team summary aggregates (W/L, scoring, ratings). `by_season` drawer when multi-season.
- **Available data:** Same as above. `game_log` included only for last-N or small samples.
- **Gap notes:** The `game_log` being conditionally suppressed means a user asking "Lakers last 10 games" gets the game log, but "Lakers since 2020" gets only aggregate rows despite both queries being in the same shape. The threshold (`<=5 games`) for including the game log is too restrictive for medium-sized samples.

---

## Family: Game Finder

### Intent: Player games matching threshold condition

- **What the user is asking:** "List the games where this player met a specific stat threshold." Returns a game-by-game list, sorted by date or stat.
- **Example queries:**
  - `Jokic over 30 points`
  - `Curry 5+ threes`
  - `Jokic between 20 and 30 points`
  - `LeBron away wins`
  - `Tatum vs Celtics games this season`
- **Current route:** `player_game_finder` → `FinderResult` → **Player Game Log** shape
- **Current answer structure:** Game log table (date, team, opp, W/L, stat columns) sorted by date. No headline sentence. Default `limit=25`.
- **Available data:** Handler produces `finder` section with full filtered game rows. No summary row. Output columns: `player_name`, `game_date`, `team_abbr`, `opponent_team_abbr`, `is_home/is_away`, `wl`, `pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `minutes`, `plus_minus`, shooting percentages.
- **Gap notes:** Shape is well-matched to intent. The `limit=25` cap silently drops excess games with no count or "see more." A user filtering "Jokic over 20 points career" expects to know the total count, not just the first 25. The count is not surfaced in the shape.

---

### Intent: Player games with boolean compound condition

- **What the user is asking:** "List games where this player met multiple threshold conditions simultaneously or in alternative."
- **Example queries:**
  - `Jokic over 25 points and over 10 rebounds`
  - `Jokic (over 25 points and over 10 rebounds) or over 15 assists`
  - `Celtics (over 120 points and over 15 threes) or under 10 turnovers`
  - `LeBron over 30 points or over 12 assists`
- **Current route:** `player_game_finder` (AND logic) or boolean OR execution path → `FinderResult` → **Player Game Log** shape. Boolean OR queries go through `_execute_or_query_build_result` / `_execute_grouped_boolean_build_result` in `_natural_query_execution.py`.
- **Current answer structure:** Same as threshold finder: game log table with stat columns.
- **Available data:** Same as above. For OR queries, the result is the union of multiple filter passes over the same data.
- **Gap notes:** For compound AND queries, the stat columns shown are fixed — the shape doesn't dynamically highlight which condition each game satisfied. A game satisfying "30 points AND 10 rebounds" looks the same as one satisfying only the points criterion. Ideal answer would include some indicator column of which conditions were met.

---

### Intent: Player occurrence count (how many games with condition)

- **What the user is asking:** "Count the number of games where this player met a condition" — expects a number, not a list.
- **Example queries:**
  - `How often has Nikola Jokić recorded a triple-double this season?`
  - `How often has Stephen Curry made 5 or more threes this year?`
  - `How many playoff games did Tatum have over 35 points?`
  - `count LeBron triple doubles since 2020`
  - `how many Jokic games with 30+ points and 10+ rebounds`
- **Current route:** `player_game_finder` with `count_intent=True`, `limit=None` → `FinderResult` → **Player Game Log** shape
- **Current answer structure:** Full game log table (all matching games, no cap when `count_intent`) with a summary strip showing the total count. The count appears in the summary strip as a header metric.
- **Available data:** Same as threshold finder but all rows are included. The `FinderResult` carries a total count.
- **Gap notes:** The user asked for a number. They get a full game table. The count is in the summary strip, but the primary answer — the number itself — is buried in table chrome. A count query should lead with the answer ("Jokic has had 47 triple-doubles since 2020") and make the game list secondary. This is a shape/intent mismatch: count intent should not produce the same visual as a list intent.

---

### Intent: Player season high / best single game

- **What the user is asking:** "What is this player's season-best game (for a stat)?" Expects 1–5 top rows.
- **Example queries:**
  - `Cade Cunningham season high`
  - `LeBron best game this season`
  - `Tatum highest scoring game this season`
  - `Jokic season high rebounds`
- **Current route:** `player_game_finder` with `sort_by="stat"`, `limit=5`, and a `season_high` note → **Player Game Log** shape
- **Current answer structure:** Game log table sorted by stat descending, showing top 5 games. Note: "season_high: showing top single-game performances."
- **Available data:** Same finder columns. The note surfaces via caveats in the ResultEnvelope.
- **Gap notes:** Reasonable shape for the intent. The note ("season_high: showing top single-game performances") is rendered as a caveat not in the primary table chrome. The user asking "Cade season high" probably just wants one row (the true season high), not 5 rows. The limit=5 is a reasonable safety net, but there's no visual emphasis on row 1 as "the" season high.

---

### Intent: Team games matching threshold condition

- **What the user is asking:** "List the games where this team met a stat threshold." Returns a game log.
- **Example queries:**
  - `How often have the Lakers held opponents under 100 points this year?`
  - `Lakers opponents under 100 this year`
  - `list Thunder games with 15+ threes`
  - `find Knicks games vs Heat since 2021`
  - `Celtics wins vs Bucks over 120 points`
- **Current route:** `game_finder` → `FinderResult` → **Team Game Log** shape
- **Current answer structure:** Team game log table (date, team, opp, W/L, relevant stat columns). Default `limit=25`.
- **Available data:** Handler columns: `team_abbr`, `game_date`, `opponent_team_abbr`, `is_home/is_away`, `wl`, `pts`, `reb`, `ast`, `fg3m`, `tov`, `plus_minus`, shooting percentages.
- **Gap notes:** Same cap-without-count issue as player finder. For queries like "how often have the Lakers held opponents under 100" — this phrasing implies a count answer, but routes to the game log shape. Count intent for team games routes through this same handler. The shape gives a table, not a number.

---

### Intent: Team games with compound boolean condition

- **What the user is asking:** "List team games meeting a multi-condition boolean expression."
- **Example queries:**
  - `Celtics (over 120 points and over 15 threes) or under 10 turnovers`
  - `Lakers (away and over 110 points) or vs Warriors`
- **Current route:** `game_finder` via boolean OR execution path → **Team Game Log** shape
- **Current answer structure:** Same team game log table.
- **Available data:** Same columns as team finder.
- **Gap notes:** Same as player boolean finder — no per-row condition-match indicator.

---

## Family: Top Games

### Intent: League-wide top player games by single stat

- **What the user is asking:** "What are the best individual player game performances (by a stat) this season?" Expects a ranked list across all players.
- **Example queries:**
  - `What were the biggest scoring games this season?`
  - `Which players had the best games by Game Score this year?`
  - `What are the most dominant games by plus-minus this season?`
  - `best scoring games this season`
  - `What are the biggest triple-double games this season?`
- **Current route:** `top_player_games` → `LeaderboardResult` → **Player Game Log** shape
- **Current answer structure:** Player game table sorted by stat descending. Default `limit=10`. No headline sentence (unlike leaderboards). Same visual as a finder game log but handler-ordered.
- **Available data:** Output rows include `rank`, `player_name`, `game_date`, `team_abbr`, `opponent_team_abbr`, `wl`, `pts`/`reb`/`ast`/targeted stat.
- **Gap notes:** The shape is **Player Game Log**, which is the same shape used for single-player filtered games. This creates a visual and semantic collision: a league-wide top-10 list looks identical to a single-player filtered finder list. The "who" column (player name) is the key differentiator, but the shape doesn't visually distinguish a "ranking across all players" from a "single-player game log." There's no hero sentence (unlike leaderboards), no count of total qualifying games, and no secondary stat context. Ideally this deserves its own "top performances" shape distinct from the single-player finder.

---

### Intent: Top team games by single stat (league-wide)

- **What the user is asking:** "What were the highest-scoring team games this season?"
- **Example queries:**
  - `top team games`
  - `highest scoring team games this season`
  - `best team games by plus-minus`
- **Current route:** `top_team_games` → `LeaderboardResult` → **Team Game Log** shape
- **Current answer structure:** Team game table sorted by stat descending. Default `limit=10`.
- **Available data:** Similar to team finder output but handler-ordered.
- **Gap notes:** Only 0 sweep fixtures exercised this route via natural language. The trigger conditions in `_finalize_route` are brittle: requires `"top team"` or `"top"` and `"team games"` literally. Many natural phrasings ("highest-scoring team games", "best team performances") don't hit this route and fall through to `season_team_leaders` instead. Same shape-collision issue as league-wide top player games.

---

## Family: Leaderboard

### Intent: Per-game stat leaderboard (current season)

- **What the user is asking:** "Who leads the league in [stat] per game this season?" Expects a ranked list of players or teams.
- **Example queries:**
  - `Who leads the NBA in points per game this season?`
  - `Which players have the most total rebounds this year?`
  - `Which centers have the most blocks this season?`
  - `top scorers this season`
  - `What team has the highest offensive rating this season?`
- **Current route:** `season_leaders` (players) or `season_team_leaders` (teams) → `LeaderboardResult` → **Leaderboard Table** shape
- **Current answer structure:** Ranked table (rank, player/team, stat value, games, team abbr for player leaderboards). Hero sentence: auto-generated from top row and metadata context. Default `limit=10`.
- **Available data:** Handler uses pre-aggregated per-game averages from the processed dataset. Rows include rank, entity identity, stat value, games played, season, season type.
- **Gap notes:** Shape is well-matched to intent. The one friction point: team leaderboards for advanced stats (off_rating, def_rating, net_rating, pace) are blocked in date-window and multi-season contexts, falling back silently to `pts` with a note. This is functionally correct but the stat fallback is invisible in the shape's visual output — the table just shows points without indicating it was substituted.

---

### Intent: Per-game stat leaderboard with contextual filter (home, opponent, wins)

- **What the user is asking:** "Who leads the league in [stat] specifically in home games / vs a team / in wins?"
- **Example queries:**
  - `Who scores the most at home this season?`
  - `best assisters in wins this season`
  - `top scorers vs Celtics last 3 seasons`
  - `highest plus minus vs Celtics since 2021`
  - `most steals in playoffs since 2010`
- **Current route:** `season_leaders` with `home_only`, `wins_only`, `opponent`, etc. → **Leaderboard Table** shape
- **Current answer structure:** Same ranked table. The applied filter context is only in metadata/notes, not in the table header or hero sentence.
- **Available data:** Same leaderboard rows; the game log filtering is applied before aggregation.
- **Gap notes:** Contextual filter is invisible in the shape. A user asking "top scorers at home" sees the same table layout as "top scorers overall" with no visual distinction that the sample is home-only. The applied filters should appear in the hero context or as a prominent sample-description.

---

### Intent: Per-game stat leaderboard with season range or "since" context

- **What the user is asking:** "Who has led in [stat] over a multi-season span?"
- **Example queries:**
  - `best rebounders last 3 seasons`
  - `top scorers since 2020`
  - `most steals in playoffs since 2010`
  - `best ts% last 3 seasons`
  - `best record since 2015`
- **Current route:** `season_leaders` with `start_season`/`end_season` → **Leaderboard Table** shape
- **Current answer structure:** Same ranked table. Hero context changes to reflect the range (e.g., "from 2020-21 to 2025-26").
- **Available data:** Handler aggregates across all seasons in the range.
- **Gap notes:** For per-game stats in multi-season ranges, the handler aggregates across seasons, which may be misleading for per-game averages (a player who played 3 seasons gets the same denominator treatment as one who played all 6). No "minimum games" or "seasons played" qualifier is visible. Also, advanced stats (off/def/net_rating) are blocked entirely for multi-season ranges, silently falling back to points.

---

### Intent: Position-filtered leaderboard

- **What the user is asking:** "Who leads among [position]?"
- **Example queries:**
  - `best ts% among centers this season`
  - `top scorers among guards since 2021`
  - `best rebounders among big men`
  - `Which centers have the most blocks this season?`
- **Current route:** `season_leaders` with `position` filter → **Leaderboard Table** shape
- **Current answer structure:** Ranked table filtered to the specified position. Position label appears in metadata, not in the table header.
- **Available data:** Same leaderboard rows, pre-filtered by position before ranking.
- **Gap notes:** Position filter is not labeled in the table header or hero sentence. The user sees "Top Scorers" not "Top Scorers (Centers)." The position applied should be visible.

---

### Intent: Last-N games leaderboard (rolling window)

- **What the user is asking:** "Who has been scoring the most over the last 10 games?" Rolling window over all players.
- **Example queries:**
  - `points leaders last 10`
  - `top scorers last 10 games`
  - `last 10 scoring leaders`
  - `best shot blocker last 10 games`
  - `best rim protector over the past month`
- **Current route:** `season_leaders` with `last_n` set → **Leaderboard Table** shape
- **Current answer structure:** Ranked table of players sorted by their per-game average over the last N games.
- **Available data:** Game-log-derived averages over the last-N window per player.
- **Gap notes:** The "last N games" context is in metadata but the table header says generic stat label with no "over last 10 games" qualifier visible. A user might not realize the ranking is rolling rather than season-wide. Also, this is a fundamentally different answer design from the single-entity "recent form" intent — here it's league-wide ranking, not one player's detailed game log. Both use different routes (season_leaders vs player_game_summary), which is correct, but the output shapes don't visually distinguish "ranking" from "form."

---

### Intent: Period-context leaderboard (quarter/half — currently unfiltered)

- **What the user is asking:** "Who scores the most in the 4th quarter?" Expects a filtered leaderboard by game period.
- **Example queries:**
  - `most 4th quarter points this season`
  - `Which players score the most in the 4th quarter this season?`
  - `4th quarter scoring leaders this season`
  - `Who averages the most points in the first half this season?`
- **Current route:** `season_leaders` with `quarter`/`half` detected → **Leaderboard Table** shape
- **Current answer structure:** Full-game leaderboard with a note: "quarter/half splits are not yet available in the current game-log data; results are unfiltered."
- **Available data:** No period-filtered data. Returns unfiltered season leaderboard.
- **Gap notes:** The user gets an unfiltered answer for a filtered question. The note exists but is rendered as metadata, not visually prominent in the shape. This is a category of "filter not applied silently with a caveat." The shape gives no indication the displayed ranking ignores the period context the user specified.

---

### Intent: Clutch leaderboard (currently unfiltered)

- **What the user is asking:** "Who performs best in clutch situations?"
- **Example queries:**
  - `Who has the best clutch field goal percentage this year?`
  - `best clutch performance this season`
  - `in clutch time` (boundary fragment, fallback to points leaderboard)
- **Current route:** `season_leaders` with `clutch=True` → **Leaderboard Table** shape
- **Current answer structure:** Unfiltered leaderboard with a note about requiring play-by-play clutch coverage.
- **Available data:** No clutch-filtered data in this route. Returns standard leaderboard.
- **Gap notes:** Same category as period-context leaderboard — silent non-filtration. The clutch filter is parser-recognized and route-propagated to `player_game_summary` and `player_game_finder` where it executes against trusted `player_game_clutch_stats`, but at the leaderboard route it remains unfiltered.

---

### Intent: Team record leaderboard (best/worst record in context)

- **What the user is asking:** "Which teams have the best record in a given context?"
- **Example queries:**
  - `best record since 2015`
  - `which teams had the most wins since 2010`
  - `What teams have the best record over the past month?`
  - `Which team has the best road record this year?`
  - `best record vs contenders` (unfiltered opponent quality)
- **Current route:** `team_record_leaderboard` → `LeaderboardResult` → **Leaderboard Table** shape
- **Current answer structure:** Ranked table of teams by win percentage or wins. `limit=10`. Hero sentence from first row.
- **Available data:** Handler produces rows with rank, team, record, games, win percentage, season type.
- **Gap notes:** Same shape as per-game stat leaderboard despite conceptually different content. A team record leaderboard should ideally show W-L records, not just a win_pct number — and the current shape can accommodate this, but whether the handler passes those columns depends on the result structure. Opponent-quality filter is noted as unfiltered for this route.

---

### Intent: Playoff-round record leaderboard (best finals/round record)

- **What the user is asking:** "Which team has the best record in the Finals / a specific playoff round?"
- **Example queries:**
  - `best finals record since 1980`
  - `best second round record`
  - `most Finals appearances since 1980`
  - `most conference finals appearances since 2000`
- **Current route:** `playoff_round_record` or `playoff_appearances` → `LeaderboardResult` → **Leaderboard Table** (frontend actually uses **Playoff Round Records** shape for these)
- **Current answer structure:** Ranked table with round, record, games, win_pct. Hero sentence from first row.
- **Available data:** Handler rows include rank, team, round, games, wins, losses, win_pct, seasons.
- **Gap notes:** Relatively well-matched. Coverage starts at `2001-02` for round semantics; queries for earlier eras return incomplete or no-result with a coverage note.

---

## Family: Occurrence Count

### Intent: Single-event occurrence leaderboard (player)

- **What the user is asking:** "Which players have had the most games with [stat threshold]?" Expects a ranked count.
- **Example queries:**
  - `most 40 point games since 2020`
  - `most triple doubles since 2020`
  - `most 15+ rebound games since 2018`
  - `most 5+ three games vs Lakers`
  - `Who has the most double-doubles recently?`
- **Current route:** `player_occurrence_leaders` → `LeaderboardResult` → **Leaderboard Table** shape
- **Current answer structure:** Ranked table of players by occurrence count. Hero sentence: e.g., "Nikola Jokić leads with 47 triple-doubles since 2020-21."
- **Available data:** Rows: rank, player_name, team_abbr, count (of qualifying games), season range.
- **Gap notes:** Shape is well-matched. The count column is the primary metric, which is correctly surfaced. Minor gap: no secondary column showing "in how many total games" — the denominator context (e.g., "47 triple-doubles in 320 games") would give useful proportion information.

---

### Intent: Compound occurrence leaderboard (player, multiple conditions)

- **What the user is asking:** "Which players have had the most games with [condition A AND condition B]?"
- **Example queries:**
  - `most games with 25+ points and 10+ assists since 2020`
  - `most games with 3+ steals and 2+ blocks`
  - `how many Jokic games with 30+ points and 10+ rebounds in playoffs since 2021`
  - `games with 40+ points and 5+ threes since 2022`
- **Current route:** `player_occurrence_leaders` (compound path) via `try_compound_occurrence_route` → **Leaderboard Table** shape
- **Current answer structure:** Same ranked table. Multi-condition event is described in a note/caveat. Single-player compound queries route through `player_game_finder` with count_intent instead.
- **Available data:** Same as single-event leaderboard but the qualifying condition is compound. The conditions are not repeated in the table rows.
- **Gap notes:** The compound condition is stated in metadata/notes but not in the table header or hero sentence. A user asking "most games with 30+ points and 10+ rebounds" should see the compound condition clearly stated above the ranking. Currently the hero reads like a single-stat leaderboard with no visual indication of compound logic.

---

### Intent: Single-event occurrence leaderboard (team)

- **What the user is asking:** "Which teams have had the most games with [stat threshold]?"
- **Example queries:**
  - `How often has a team scored 140 or more points this year?`
  - `how many teams scored 120+ this season`
  - `teams with the most games scoring 120+ and making 15+ threes since 2020`
- **Current route:** `team_occurrence_leaders` → `LeaderboardResult` → **Leaderboard Table** shape
- **Current answer structure:** Same ranked table but for teams. Only 2 sweep fixtures.
- **Available data:** Rows: rank, team, count (of qualifying games), season range.
- **Gap notes:** The query "How often has a team scored 140+ points this year?" sounds like it wants a count, not a ranking. This is the same count-vs-leaderboard semantic collision as player occurrence count. When the question asks "how often" for a specific unnamed team, it actually routes differently (through team_record or game_finder), not through team_occurrence_leaders.

---

### Intent: Distinct player count with threshold

- **What the user is asking:** "How many different players scored 40 points this season?" Expects a single number.
- **Example queries:**
  - `how many players scored 40 points this season`
  - `number of players with 10 assists this season`
  - `how many players have had a 40 point game this season?`
- **Current route:** `player_occurrence_leaders` with `distinct_count` note, `limit=None` → **Leaderboard Table** shape
- **Current answer structure:** Full ranked list of all qualifying players (no cap since `limit=None`). A note says "distinct_count: counting distinct players meeting condition."
- **Available data:** Every qualifying player with their count in the table.
- **Gap notes:** Significant shape mismatch. The user asked "how many" — a scalar answer. They get a full ranked table. The answer to their question (the row count of the table) is technically inferrable but not surfaced as a headline number. This is the most direct example of a count question getting a leaderboard answer. Ideal answer: "23 different players scored 40+ points this season" as a headline, with the table as optional detail.

---

## Family: Streaks

### Intent: Player longest streak of stat condition

- **What the user is asking:** "What is this player's longest consecutive-game streak where a condition was met?"
- **Example queries:**
  - `Jokic longest streak of 30 point games`
  - `Jokic longest 30-point streak`
  - `Curry longest streak with at least 3 threes`
  - `Jokic longest triple-double streak`
- **Current route:** `player_streak_finder` with `longest=True` → `LeaderboardResult` → **Streak Table** shape
- **Current answer structure:** Ranked streak table (condition, streak length, start date, end date, active/completed, record in those games, average stats over the streak). Hero sentence from first row.
- **Available data:** Rows: condition text, streak_length, start/end dates, is_active, games, record, per-stat averages over the streak window.
- **Gap notes:** Shape is well-matched to intent. The per-game averages within the streak are useful context and are included. Minor gap: the "games" sub-section (the actual game list within the top streak) is not exposed in the shape — there's no way to drill into which games made up the streak without the raw JSON toggle.

---

### Intent: Player N consecutive games with condition

- **What the user is asking:** "Did this player have N consecutive games with [condition]? Show me those streaks."
- **Example queries:**
  - `Jokic 5 straight games with 20+ points`
  - `LeBron 10 consecutive games with 25+ points`
  - `Celtics 5 straight games scoring 120+`
- **Current route:** `player_streak_finder` with `min_streak_length` set → **Streak Table** shape
- **Current answer structure:** Streak table showing all streaks meeting the minimum length. Same structure as longest streak.
- **Available data:** Same as longest streak, filtered to streaks of length ≥ N.
- **Gap notes:** Shape is reasonable. For short minimum thresholds (e.g., N=5) there could be many qualifying streaks; the `limit=25` cap applies here. No count of total qualifying streaks is surfaced.

---

### Intent: Player current / active streak

- **What the user is asking:** "Is this player currently on a streak of X?"
- **Example queries:**
  - `LeBron current 20+ point streak`
  - `Jokic active triple-double streak`
  - `Curry consecutive games with a made three`
- **Current route:** `player_streak_finder` → **Streak Table** shape (with `is_active` highlighted in the shape when row has `is_active=True`)
- **Current answer structure:** Streak table with an `is_active` status column. Active streaks show "Active" in the status field.
- **Available data:** Same streak rows. The `is_active` field is available per row.
- **Gap notes:** The active streak is not visually separated from historical streaks in the table — it's just another row with an "Active" status badge. If the user asks about a current streak, the ideally prominent answer is "Yes, Curry is currently on a 47-game streak of making a three" as a hero statement, not buried in a ranked table. The active streak may or may not be row 1 depending on its length relative to historical streaks.

---

### Intent: Team winning/losing streak

- **What the user is asking:** "What is this team's longest winning or losing streak?"
- **Example queries:**
  - `longest Lakers winning streak`
  - `longest Warriors home winning streak`
  - `Thunder losing streak`
- **Current route:** `team_streak_finder` → **Streak Table** shape
- **Current answer structure:** Same streak table format but for teams. Condition column shows "Win" or "Loss."
- **Available data:** Same structure as player streaks but for team records.
- **Gap notes:** Same active-streak visibility issue as player streaks. Well-matched otherwise.

---

### Intent: Team stat streak (consecutive games meeting a stat threshold)

- **What the user is asking:** "How many consecutive games has this team scored [threshold]+ points?"
- **Example queries:**
  - `Celtics 5 straight games scoring 120+`
  - `longest Bucks streak with 15+ threes`
  - `Thunder consecutive games with 110+ points`
- **Current route:** `team_streak_finder` with stat condition → **Streak Table** shape
- **Current answer structure:** Streak table showing team stat streaks. Condition column reflects the stat threshold.
- **Available data:** Same streak structure with team stat columns.
- **Gap notes:** Shape is well-matched. Same lack of game-level drill-down as player streaks.

---

## Family: Comparison

### Intent: Head-to-head player comparison (direct matchup stats)

- **What the user is asking:** "Who has better stats in games the two players faced each other?"
- **Example queries:**
  - `Jokic head-to-head vs Embiid since 2021`
  - `Kobe vs LeBron playoffs in 2008-09`
  - `Jokic h2h vs Embiid`
- **Current route:** `player_compare` with `head_to_head=True` → `ComparisonResult` → **Comparison Panels** shape
- **Current answer structure:** Two-panel hero (one per player), head-to-head hero sentence (e.g., "Joel Embiid leads Nikola Jokić 2-1 in this head-to-head sample"), metric comparison table showing both players' stats in shared games.
- **Available data:** `summary` rows (one per player), `comparison` rows (metric-by-metric list). The `head_to_head_used` flag in metadata.
- **Gap notes:** When no shared games exist in the requested scope, returns `no_match`. The game list for the head-to-head matchup (which specific games?) is not accessible in the shape — only aggregated stats.

---

### Intent: Parallel player performance comparison (same context, not head-to-head)

- **What the user is asking:** "How do these two players compare in terms of their own stats in the same time period?"
- **Example queries:**
  - `Jokic vs Embiid recent form`
  - `Jokic vs Embiid since 2021`
  - `Kobe vs LeBron career`
  - `LeBron vs Jordan comparison`
- **Current route:** `player_compare` (without head_to_head) → **Comparison Panels** shape
- **Current answer structure:** Two-panel hero showing each player's stats over the specified context, metric comparison table.
- **Available data:** Same as head-to-head but without the h2h filter. Both players' full-season stats in the same frame.
- **Gap notes:** The distinction between "head-to-head" and "parallel comparison" is in metadata (`head_to_head_used`) and the hero sentence, not in the shape structure. Both variants look identical in the UI. This is semantically correct but could be clearer — "how Jokic did in shared games" vs "how Jokic did in general, compared to how Embiid did in general" are very different questions with the same visual output.

---

### Intent: Head-to-head team comparison (matchup record)

- **What the user is asking:** "What is team A's record vs team B?" This is record-flavored, not stats-flavored.
- **Example queries:**
  - `Knicks head-to-head vs Heat since 1999`
  - `Lakers vs Celtics all-time record`
  - `Celtics record vs Bucks since 2020`
- **Current route:** When `record_intent` is detected → `team_matchup_record` → `ComparisonResult` → **Comparison Panels** shape (or `team_record` if only one team present)
- **Current answer structure:** Two-panel comparison showing each team's record in the matchup, metric comparison table.
- **Available data:** `ComparisonResult` rows include W-L, win_pct, pts averages per team.
- **Gap notes:** This intent is record-oriented ("what is their record") but routes to a comparison shape rather than the Team Record shape. The Comparison Panels shape was designed for stats comparison (metric rows with numeric edges), not for W-L record display. The shape can display the W-L data but the hero sentence ("Team A leads Team B 31-27") fits the Team Record family better. There's currently a routing ambiguity between `team_compare` and `team_matchup_record` — whether this is triggered depends on `record_intent` detection, which may not fire for "Lakers vs Celtics all-time record" if the word "record" isn't in the query.

---

### Intent: Parallel team stats comparison (same context, not head-to-head record)

- **What the user is asking:** "How do these two teams compare in performance stats over a period?"
- **Example queries:**
  - `Celtics vs Bucks from 2021-22 to 2023-24`
  - `Lakers vs Celtics since 2010`
  - `Celtics vs Bucks home`
- **Current route:** `team_compare` → **Comparison Panels** shape
- **Current answer structure:** Two-panel hero showing each team's stats, metric comparison table.
- **Available data:** `summary` rows (W-L, scoring, ratings per team), `comparison` metric rows.
- **Gap notes:** Well-matched to intent. Same semantic clarity issue as player comparison — the shape doesn't distinguish "head-to-head matchup stats" from "parallel same-period stats."

---

## Family: Records

### Intent: Single-team season record

- **What the user is asking:** "What is this team's record this season?" Expects W-L + win_pct.
- **Example queries:**
  - `Celtics record this year`
  - `Lakers record 2024-25`
  - `Warriors record in the playoffs`
  - `Celtics record since 2020`
  - `Lakers playoff record since 2015`
- **Current route:** `team_record` → `SummaryResult` → **Team Record** shape
- **Current answer structure:** Record hero (W-L, win_pct, game context). Optional `by_season` drawer for multi-season queries. Stats columns include pts_avg, opp_pts_avg, plus_minus, net_rating, rebounds, assists, threes.
- **Available data:** `summary` (one aggregated row), `by_season` (one per season when multi-season range).
- **Gap notes:** Shape is well-matched. For multi-season ranges ("Celtics record since 2020"), the `by_season` section provides year-by-year breakdown as a drawer. However, the initial display is still a single aggregated row — the user doesn't immediately see the season-by-season breakdown without expanding the drawer.

---

### Intent: Team conditional record (stat threshold condition)

- **What the user is asking:** "What is this team's record when [condition]?" (e.g., when scoring over 120, when opponent scores under 100).
- **Example queries:**
  - `What is the Knicks' record when they allow fewer than 110 points?`
  - `Celtics record when scoring 120+ since 2022`
  - `Lakers record in games with 15+ threes`
  - `What is Milwaukee's record when it wins the rebounding battle?`
- **Current route:** `team_record` → **Team Record** shape
- **Current answer structure:** Record hero with the applied threshold condition visible in metadata/notes.
- **Available data:** Same as standard team record.
- **Gap notes:** Condition is not visually prominent in the shape. The hero sentence reads "The Boston Celtics are 45-12 in the 2025-26 regular season" with no mention of the condition. The condition should be in the headline: "The Boston Celtics are 45-12 when scoring 120+ in the 2025-26 regular season."

---

### Intent: Team record without player (absence record)

- **What the user is asking:** "How does this team perform when [player] doesn't play?"
- **Example queries:**
  - `Lakers record without LeBron James`
  - `Warriors wins without Stephen Curry`
  - `Nuggets record when Murray out`
- **Current route:** `team_record` with `without_player` → **Team Record** shape
- **Current answer structure:** Record hero for the filtered sample. The `without_player` context appears in metadata.
- **Available data:** Same record sections. `by_season` available for multi-season absence records.
- **Gap notes:** The "without player" context should be prominently in the headline. The current hero sentence doesn't include it. Also, `game_summary` route handles team performance (not W-L) when player is absent — there's an overlap between `team_record` (routes to W-L) and `game_summary` (routes to performance stats) that is determined by whether `record_intent` or `without_player` triggers — the routing logic is fragile here (see `_finalize_route` lines around the `without_player` and `re.search(r"\b(?:without|w/o)\b", q)` check).

---

### Intent: Team record in schedule context (back-to-back, rest, one-possession, national TV — currently unfiltered)

- **What the user is asking:** "What is this team's record in [schedule context]?"
- **Example queries:**
  - `What is the Lakers' record on back-to-backs this season?`
  - `Lakers b2b record`
  - `Celtics one-possession record this season`
  - `What is the Lakers' record on national TV this season?`
  - `What team has the best record in one-possession games this season?`
- **Current route:** `team_record` (specific team) or `team_record_leaderboard` (league-wide) with schedule context noted → **Team Record** or **Leaderboard Table** shape
- **Current answer structure:** Full-season unfiltered record with a note: "back_to_back: filter detected but trustworthy schedule-context coverage is unavailable; results are unfiltered."
- **Available data:** No schedule-context filtered data for most of these queries. Returns full-season record.
- **Gap notes:** Same silent-non-filtration category. The user gets a complete-season record that does not answer the specific schedule-context question. The note is in metadata caveats, not in the shape's visual output. This is arguably the most misleading answer in the system: the shape looks like a normal record result with no visual indication the filter was not applied.

---

### Intent: Team record by decade (era-bucketed history)

- **What the user is asking:** "Show me how this team has performed decade by decade."
- **Example queries:**
  - `Warriors record by decade`
  - `Lakers record each decade since 1980`
- **Current route:** `record_by_decade` → `SummaryResult` → **Record By Decade** shape
- **Current answer structure:** Summary hero (overall range record) + decade breakdown table (decade, W-L, win_pct, games, seasons appeared).
- **Available data:** `summary` (overall record), `by_season` (one row per decade).
- **Gap notes:** Shape is well-matched. Only 1 sweep fixture.

---

### Intent: Record-by-decade leaderboard (winningest team in an era)

- **What the user is asking:** "Which team won the most in the [decade]?"
- **Example queries:**
  - `winningest team of the 2010s`
  - `most wins in the 1990s`
- **Current route:** `record_by_decade_leaderboard` → `LeaderboardResult` → **Record By Decade Leaderboard** shape
- **Current answer structure:** Ranked table per decade, `limit=10` per decade. Hero sentence from first row.
- **Available data:** Rows: rank, team, decade, target metric, W-L, games, win_pct, seasons, season type.
- **Gap notes:** Well-matched. Only 1 sweep fixture.

---

## Family: Splits

### Intent: Player home/away performance split

- **What the user is asking:** "How does this player's performance differ at home vs on the road?"
- **Example queries:**
  - `Jokic home vs away in 2025-26`
  - `Jokic home away split last 20 games`
  - `How does Anthony Edwards shoot in wins versus losses?`
  - `Anthony Edwards shooting in wins vs losses`
- **Current route:** `player_split_summary` → `SplitResult` → **Split Comparison** shape
- **Current answer structure:** Hero, split-bucket table (Home row, Away row with stats), optional edge chips highlighting biggest differences.
- **Available data:** `summary` (one aggregate row per bucket), optional `game_log` per bucket. Edge chips for up to 4 metrics.
- **Gap notes:** **Zero sweep fixtures in this family.** The shape exists in code and the parser routes to it, but no sweep example exercised a live result (all hit unsupported/no-result in the sweep context, likely data coverage gaps). This is a parser-recognized but execution-unverified intent. Also, the split summary was designed for home/away and wins/losses only (`ALLOWED_SPLITS` in `player_split_summary.py`); more granular splits (e.g., by quarter, by opponent tier) are not supported.

---

### Intent: Player wins/losses performance split

- **What the user is asking:** "How does this player perform differently in wins vs losses?"
- **Example queries:**
  - `Jokic wins vs losses`
  - `Tatum in wins and losses`
  - `Edwards shooting in wins versus losses`
- **Current route:** `player_split_summary` with `split_type=wins_losses` → **Split Comparison** shape
- **Current answer structure:** Same split table with Win/Loss buckets.
- **Available data:** Same as home/away split.
- **Gap notes:** Same as home/away split — zero live sweep fixtures.

---

### Intent: Team home/away performance split

- **What the user is asking:** "How does this team play differently at home vs on the road?"
- **Example queries:**
  - `Celtics home vs away`
  - `Lakers playoff home vs away since 2020`
  - `How do the Suns compare at home and away?`
- **Current route:** `team_split_summary` → **Split Comparison** shape
- **Current answer structure:** Same split structure but for team stats (ratings, scoring, etc.).
- **Available data:** Same sections. Team stats include off/def/net rating, pace, pts, reb, ast, efg_pct, ts_pct, fg3_pct.
- **Gap notes:** Zero live sweep fixtures. Same execution-coverage issue as player splits.

---

### Intent: Team wins/losses performance split

- **What the user is asking:** "How does this team perform differently in wins vs losses?"
- **Example queries:**
  - `Celtics wins vs losses`
  - `Warriors in wins and losses`
- **Current route:** `team_split_summary` with `split_type=wins_losses` → **Split Comparison** shape
- **Current answer structure:** Same split table with Win/Loss buckets.
- **Available data:** Same as team home/away split.
- **Gap notes:** Zero live sweep fixtures.

---

### Intent: Player on/off court team impact (currently unsupported)

- **What the user is asking:** "How much better or worse does the team play with this player on the floor vs off?"
- **Example queries:**
  - `Jokic on/off`
  - `Nikola Jokic on-off`
  - `Nuggets with and without Jokic` (routes to `team_record`, not `player_on_off`)
  - `What is the Nuggets' net rating with Nikola Jokić on the floor vs off the floor?`
- **Current route:** `player_on_off` → **On/Off Split** shape → returns `no_result` / `unsupported`
- **Current answer structure:** Message no-result with note about data unavailability.
- **Available data:** Handler exists (`player_on_off.py`), shape exists in frontend (`SplitResult.tsx`), but trusted `team_player_on_off_summary` data is not available for the requested scope in the sweep.
- **Gap notes:** Parser correctly recognizes and routes these queries. The data contract exists but coverage is absent. Zero live sweep fixtures. Note: "Nuggets with and without Jokic" routes to `team_record` (W-L perspective), not `player_on_off` (rating perspective) — these are different questions with overlapping surface phrasing.

---

## Family: Playoff / Era History

### Intent: Single-team complete playoff history

- **What the user is asking:** "Show me this team's full playoff history."
- **Example queries:**
  - `Lakers playoff history`
  - `Heat playoff history`
- **Current route:** `playoff_history` → **Playoff History** shape
- **Current answer structure:** Hero (total appearances, overall playoff record, range) + season-by-season table (season, appearances, round reached, W-L, win_pct).
- **Available data:** `summary` (aggregate row), `by_season` (one row per playoff appearance).
- **Gap notes:** Shape is well-matched. Two sweep fixtures. Coverage for round data starts at `2001-02`.

---

### Intent: Team vs team playoff matchup history

- **What the user is asking:** "What is the playoff head-to-head history between these two teams?"
- **Example queries:**
  - `Heat vs Knicks playoff history`
  - `Lakers playoff series record vs Celtics`
- **Current route:** `playoff_matchup_history` → **Playoff Matchup History** shape
- **Current answer structure:** Two-team hero with win counts, series-history table (season, round, winner, team-prefixed records).
- **Available data:** `summary` (one row per team), `comparison` (series-level rows).
- **Gap notes:** Shape is well-matched. One sweep fixture. The comparison between "playoff series record vs Celtics" (routed through the matchup handler) and "Celtics record vs Bucks since 2020" (routed through team_record) depends on whether `playoff_history_intent` fires — the routing is not robust to phrasing variations.

---

### Intent: Team playoff appearances / round appearances leaderboard

- **What the user is asking:** "Which teams have appeared in the Finals / a round most often?"
- **Example queries:**
  - `finals appearances`
  - `Warriors conference finals appearances`
  - `most Finals appearances since 1980`
  - `most conference finals appearances since 2000`
- **Current route:** `playoff_appearances` → **Leaderboard Table** / **Playoff Round Records** shapes
- **Current answer structure:** Ranked table of teams by appearances count. Hero sentence from first row.
- **Available data:** Rows: rank, team, round, appearances count, seasons.
- **Gap notes:** Three sweep fixtures. Coverage starts at round-data boundary.

---

### Intent: Team matchup history by decade

- **What the user is asking:** "Show the decade-by-decade record of two teams playing each other."
- **Example queries:**
  - `Lakers vs Celtics by decade`
  - `Celtics vs Lakers all decades`
- **Current route:** `matchup_by_decade` → **Matchup By Decade** shape
- **Current answer structure:** Two-team hero (overall matchup record) + decade table (decade, team-prefixed W-L, win_pct, scoring).
- **Available data:** `summary` (per-team overall), `comparison` (decade-bucketed).
- **Gap notes:** One sweep fixture. Well-matched to intent.

---

## Family: Lineup (Currently Unsupported)

### Intent: Specific-lineup performance summary

- **What the user is asking:** "How do specific players perform together as a lineup unit?"
- **Example queries:**
  - `lineups with LeBron and AD`
  - `lineup with Tatum and Brown together`
  - `2-man combos with Brunson and Hart`
  - `net rating with Tatum and Brown together` (routes to unsupported: unit_size=1 outside contract)
- **Current route:** `lineup_summary` → Message no-result (unsupported)
- **Current answer structure:** Message no-result: "lineup: trusted league_lineup_viz coverage is unavailable for the requested slice."
- **Available data:** Handler exists (`lineup_summary.py`). Shape would be **Fallback Tables**. Data contract requires trusted `league_lineup_viz` rows.
- **Gap notes:** Parser correctly recognizes and routes these queries. Data coverage is absent. Zero live sweep fixtures. The frontend fallback shape for this is **Fallback Tables** (generic section cards) — not a designed lineup-specific renderer.

---

### Intent: Best lineup leaderboard (units ranked by stat)

- **What the user is asking:** "Which lineup units have the best net rating / scoring?"
- **Example queries:**
  - `best 5-man lineups`
  - `best 5 man lineups`
  - `top 5-man units`
  - `best 3-man units with at least 200 minutes`
  - `top 2-man combos`
- **Current route:** `lineup_leaderboard` → Message no-result (unsupported)
- **Current answer structure:** Message no-result: "lineup: trusted league_lineup_viz coverage is unavailable."
- **Available data:** Handler exists (`lineup_leaderboard.py`). Would produce `LeaderboardResult`. Shape would be **Leaderboard Table**.
- **Gap notes:** Same as lineup summary — parser-ready, data-unavailable, zero live fixtures.

---

## Family: Rolling Stretch

### Intent: Best rolling N-game stretch leaderboard (league-wide)

- **What the user is asking:** "Which players have had the best rolling [N]-game stretch by [stat]?"
- **Example queries:**
  - `hottest 3-game scoring stretch this year`
  - `best 5-game stretch by Game Score`
  - `most efficient 10-game rolling stretch`
  - `3-game scoring stretch leaders this year`
  - `top 3-game scoring stretches this year`
- **Current route:** `player_stretch_leaderboard` → `LeaderboardResult` → **Leaderboard Table** shape
- **Current answer structure:** Ranked table of players by their best rolling N-game average. Hero sentence from first row.
- **Available data:** Rows: rank, player, team, window_size, metric, rolling average, start/end dates of the best window, games in window.
- **Gap notes:** Eight sweep fixtures. Shape is reasonable but uses the generic Leaderboard Table, which doesn't visually distinguish "rolling window leaderboard" from "season average leaderboard." The start/end dates of the best stretch window are important context (they tell you _when_ the hot stretch happened) but may not be prominently displayed in the current table columns. This intent deserves a purpose-built shape with a timeline component.

---

### Intent: Named player's best N-game stretch

- **What the user is asking:** "What was this player's best [N]-game stretch this season?"
- **Example queries:**
  - `Booker hottest 4-game scoring stretch`
  - `Jokic best 5-game scoring stretch`
  - `Curry best 3-game stretch this season`
- **Current route:** `player_stretch_leaderboard` with `player` set → **Leaderboard Table** shape
- **Current answer structure:** Ranked table showing that player's top N-game windows. `limit=10`.
- **Available data:** Same stretch rows filtered to one player.
- **Gap notes:** When a named player is specified, the intent is more like "show me this player's peak stretches" — a personal form chart. The generic leaderboard shape doesn't emphasize the stretch timeline or show the game-by-game arc within the stretch. Ideal answer: stretch hero (best window dates + average) + game log of that stretch window.

---

## Family: No-Result / Error

### Intent: Guided no-result (query had a result but nothing matched the filters)

- **What the user is asking:** A valid, supported query, but the applied filters returned zero games.
- **Example queries:**
  - `Jokic over 60 points this season` (no games matching)
  - `What's the Mavericks' record when Luka Dončić scores 35 or more?` (routes to no-match)
  - `What is the Suns' record when Kevin Durant leads the team in scoring?` (routes to player_game_summary, returns no-match)
- **Current route:** Handler returns `NoResult` with `reason=no_match` → **Guided No Result** shape
- **Current answer structure:** No-result card with title "No Matching Results", message, and 3–4 recovery suggestions.
- **Available data:** `result_reason`, `notes`, `caveats`, route/slot metadata from the failed query.
- **Gap notes:** Suggestions are hardcoded static arrays (not query-specific). A user whose "Jokic 60+ points" query fails doesn't need generic suggestions — they'd benefit from knowing what _did_ happen (e.g., "Jokic's season high is 47 points"). Query-aware recovery is not possible with the current architecture.

---

### Intent: Unsupported query (within the system's known limitations)

- **What the user is asking:** Something the system explicitly cannot answer.
- **Example queries:**
  - `Who's been the best catch-and-shoot shooter this season?` (unsupported boundary phrase)
  - `Which scorers have cooled off over their last 10 games?` (unrouted)
  - `What players have averaged a double-double over their last 15 games?` (unrouted)
  - `Who's been the best isolation defender over the past month?` (unrouted)
  - `How often has a player had 10+ assists and 0 turnovers this season?` (unrouted)
- **Current route:** `_unsupported_boundary_note` fires → `route=None` → **Message No Result** shape
- **Current answer structure:** "Unsupported Query" card with the specific reason in notes.
- **Available data:** Parser notes include the specific unsupported phrase.
- **Gap notes:** The unsupported note is machine-readable but the "Unsupported Query" card is a dead end. The boundary phrases in `_UNSUPPORTED_BOUNDARY_PHRASES` are hardcoded — new boundary cases are easy to add but must be explicitly enumerated. No fallback suggestion points to what the user _could_ ask instead.

---

### Intent: Ambiguous entity (multiple possible players/teams)

- **What the user is asking:** A valid query but the named entity resolves to multiple candidates.
- **Example queries:**
  - `Brown last 10` (multiple players named Brown)
  - `Williams clutch stats` (multiple Williams)
  - `Jackson blocks` (ambiguous)
  - `Johnson defense` (ambiguous)
- **Current route:** `entity_ambiguity` detected → `route=None` with `reason=ambiguous` → **Message No Result** shape
- **Current answer structure:** "Ambiguous Query" card with a note listing the candidates.
- **Available data:** `entity_ambiguity` carries type, candidates list, and source.
- **Gap notes:** The frontend has no disambiguation UI — it cannot present "Did you mean Jaylen Brown or Desmond Bane?" as a clickable selection. The ambiguous-entity path terminates in a dead-end message. Ideal answer: interactive candidate selection or "did you mean X?" with one-click confirmation.

---

### Intent: Ambiguous fragment (query recognized but intent unclear)

- **What the user is asking:** A short query where entity is known but the query type is not.
- **Example queries:**
  - `Celtics recently` (needs summary, finder, or record intent)
  - `Tatum vs Knicks` (needs summary or game-list intent)
  - `Jokic triple doubles` (needs count, list, or leaderboard intent)
  - `best games Booker` (needs a stat or player-game intent)
  - `Thunder clutch` (needs record, summary, or game-list intent)
- **Current route:** `_ambiguous_fragment_note` fires → `route=None` with `reason=ambiguous` → **Message No Result** shape
- **Current answer structure:** "Ambiguous Query" card with the specific fragment ambiguity reason.
- **Available data:** Parser notes include the detected pattern and the clarification needed.
- **Gap notes:** These are among the most actionable no-results — the system knows exactly what additional signal is needed. "Jokic triple doubles" fails because the system can't determine if the user wants a count, a list, or a leaderboard. The recovery message could specifically say "Try: 'how many Jokic triple doubles', 'list Jokic triple doubles', or 'most triple doubles leaderboard'."

---

### Intent: Coverage-gated unsupported (filter parsed but data not available)

- **What the user is asking:** A supported query type, but the required data coverage doesn't exist for the requested scope.
- **Example queries:**
  - `Jokic on/off` (requires trusted `team_player_on_off_summary`)
  - `Nuggets net rating with Jokic on the floor vs off the floor`
  - `best 5-man lineups` (requires trusted `league_lineup_viz`)
  - `LeBron as a starter stats` (when coverage is missing for the season)
- **Current route:** Handler returns `NoResult` with reason `unsupported` + coverage note → **Message No Result** shape
- **Current answer structure:** "Unsupported Query" card with the coverage note.
- **Available data:** The route and slot information is in metadata; the specific missing data source is named in the notes.
- **Gap notes:** The distinction between "this query type will never work" (true unsupported) and "this query type works but data is missing for this scope" (coverage-gated) is lost in the Message No Result shape — both display the same "Unsupported Query" card. Users cannot tell if they should try a different season, or if the feature is simply not built.

---

## Cross-Cutting Analysis

### Intents that share the same shape but want different answer designs

| Shared Shape                      | Intents                                         | Desired Answer Difference                                      |
| --------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| **Entity Summary**                | Single-season player stats                      | Hero only (current shape works)                                |
|                                   | Career / all-time averages                      | Hero + by_season career history table                          |
|                                   | Season-range averages                           | Hero + by_season breakdown table                               |
|                                   | Full filtered-sample (opponent, home)           | Hero + filtered game log + baseline comparison                 |
|                                   | Clutch / period / schedule-context (unfiltered) | Should show no-result or prominent warning, not a normal hero  |
| **Entity Summary + Recent Games** | Last-N form (unfiltered)                        | Current shape is appropriate                                   |
|                                   | Last-N form with context filter                 | Same shape but filter must be visually prominent               |
| **Player Game Log**               | Single-player threshold finder                  | Entity-scoped game list                                        |
|                                   | League-wide top-N games by stat                 | Cross-entity ranking — needs distinct "top performances" shape |
|                                   | Player occurrence count                         | Expects a scalar number, not a game list                       |
| **Leaderboard Table**             | Per-game stat leaderboard                       | Current shape works                                            |
|                                   | Occurrence count leaderboard                    | Count column is primary; current shape works                   |
|                                   | Distinct player count ("how many players…")     | Expects a scalar headline, not a full ranked table             |
|                                   | Rolling stretch leaderboard                     | Needs window start/end dates prominently                       |
|                                   | Period/clutch leaderboard (unfiltered)          | Should surface the unfiltered nature visually                  |
|                                   | Team record leaderboard                         | Wants W-L pairs, not just a single metric                      |
| **Team Record**                   | Season record                                   | Current shape works                                            |
|                                   | Conditional record                              | Condition must be in the headline sentence                     |
|                                   | Without-player record                           | Player absence must be in the headline sentence                |
|                                   | Schedule-context record (unfiltered)            | Should surface the unfiltered nature visually                  |
| **Comparison Panels**             | Head-to-head matchup stats                      | h2h sample is filtered; should be labeled                      |
|                                   | Parallel season stats                           | Independent samples; different framing needed                  |
|                                   | Team matchup record                             | W-L-oriented; comparison panel metric table is wrong shape     |

---

### Intents whose current shape doesn't match the question being asked

1. **"LeBron career"** → Entity Summary (one aggregate hero card). The question asks for career history; the data (`by_season`) exists but is not displayed. Shape gives no trajectory.

2. **"Jokic since 2021"** → Entity Summary (single aggregated average). The question spans multiple seasons; `by_season` data exists but is not displayed. User gets a 4-year mean that hides season-to-season variation.

3. **"Jokic vs Lakers"** → Entity Summary. The question implies a game list; the handler computes `game_log` but the shape discards it. User gets averages when they likely want individual game rows.

4. **"How many players scored 40 points this season?"** → Leaderboard Table. The question asks for a count; the answer is buried as a table row count with no scalar headline.

5. **"How often has Curry made 5+ threes this year?"** → Player Game Log (count mode). The question asks "how often" but the shape shows a game list. Count is in the summary strip but not the primary visual.

6. **"How many Celtics games with 120+ points since 2022?"** → Team Game Log (count mode). Same count-vs-list mismatch as above.

7. **"Tatum clutch stats"** → Entity Summary (unfiltered). The question asks for clutch stats; the answer is full-season unfiltered averages with a text note. Shape gives no visual indication filter wasn't applied.

8. **"Lakers on back-to-backs record"** → Team Record (unfiltered). Same as clutch — schedule filter is noted but visually invisible.

9. **"What is the Mavericks' offensive rating when Luka didn't play?"** → game_summary → returns no-result (`unsupported`). The question is supported-in-principle but routes to game_summary which doesn't expose offensive rating on the `without_player` path.

10. **"Jokic triple doubles"** → Ambiguous fragment. The question could mean "how many" (count), "list them" (finder), or "who leads in" (leaderboard). Current behavior is a dead-end no-result rather than a disambiguation question.

---

### Intents found in code with zero sweep fixtures (potential dead code or undocumented features)

| Route                  | Handler                                      | Shape             | Notes                                                                                                                                        |
| ---------------------- | -------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `player_split_summary` | `player_split_summary.py:build_result`       | Split Comparison  | Parser recognizes; handler exists; sweep returns no live fixtures (data coverage issues)                                                     |
| `team_split_summary`   | `team_split_summary.py:build_result`         | Split Comparison  | Same as above                                                                                                                                |
| `player_on_off`        | `player_on_off.py:build_result`              | On/Off Split      | All sweep examples return unsupported; data contract requires `team_player_on_off_summary` coverage                                          |
| `lineup_summary`       | `lineup_summary.py:build_result`             | Fallback Tables   | All sweep examples return unsupported; data contract requires `league_lineup_viz` coverage                                                   |
| `lineup_leaderboard`   | `lineup_leaderboard.py:build_result`         | Leaderboard Table | Same as lineup_summary                                                                                                                       |
| `top_team_games`       | `top_team_games.py:build_result`             | Team Game Log     | Route trigger is narrow (`"top team"` or `"top" + "team games"` literal); most natural phrasings fall through                                |
| `team_matchup_record`  | `team_record.py:build_matchup_record_result` | Comparison Panels | Route requires `record_intent` + two teams; many head-to-head record phrasings don't fire `record_intent` and fall to `team_compare` instead |

---

### Sweep queries that don't have a clean handler match

| Query                                                                   | Current Outcome                         | Why It Doesn't Fit                                                                                                                                   |
| ----------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Who scored the most points last night?`                                | Guided no-result                        | Data freshness: "last night" resolves to a date with no data                                                                                         |
| `Which scorers have cooled off over their last 10 games?`               | Unrouted error                          | "cooled off" is in `_UNSUPPORTED_BOUNDARY_PHRASES`; no route for trend/trajectory detection                                                          |
| `What players have averaged a double-double over their last 15 games?`  | Unrouted error                          | "averaged a double-double" is an unsupported boundary phrase; would require compound rolling average                                                 |
| `What is the Mavericks' offensive rating when Luka didn't play?`        | game_summary → unsupported              | Routes correctly but game_summary doesn't expose offensive rating on the without-player path                                                         |
| `Which team has the best net rating in its last 10 games?`              | season_team_leaders → unsupported       | Advanced rating stats blocked in date-window; fallback notes stat_fallback but returns no result                                                     |
| `Jokic triple doubles`                                                  | Ambiguous fragment                      | Ambiguous fragment pattern fires; could logically route to occurrence count or leaderboard                                                           |
| `best games Booker`                                                     | Ambiguous fragment                      | "best games" is ambiguous; could be season high finder or scoring leaderboard                                                                        |
| `Thunder clutch`                                                        | Ambiguous fragment                      | Team + clutch without record/summary/finder signal                                                                                                   |
| `in clutch time`                                                        | Leaderboard fallback with boundary note | Fragment with no entity, no stat; fallback to broad points leaderboard with two notes                                                                |
| `What team has the best record against top teams this year?`            | top_team_games → no_result              | `opponent_quality` detected, routes to `top_team_games` which doesn't support `win_pct` as stat                                                      |
| `Who averages the most assists against teams over .500?`                | season_team_leaders                     | Routed to team leaderboard despite player-first phrasing; opponent_quality filter not applied                                                        |
| `What is the Suns' record when Kevin Durant leads the team in scoring?` | player_game_summary → no_match          | "leads the team in scoring" is an unsupported boundary; routes to player summary for Durant, returns no match because no Suns games match the filter |
