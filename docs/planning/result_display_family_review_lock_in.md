# Result Display Family Review Lock-In Notes

> Purpose: running decision log for the 19 result-display family screenshots.
> This file captures user-approved visual/content decisions after each review
> batch so the final implementation prompts are based on written decisions, not
> chat memory.
>
> Workflow:
> 1. Review screenshots in batches.
> 2. Add decisions here after each batch.
> 3. After all 19 families are reviewed, convert this doc into implementation
>    prompts / acceptance criteria.
>
> Important screenshot note: screenshot review captures may suppress player
> headshots/logos for easier image generation. Missing headshots in screenshots
> should not be treated as a real-site bug unless confirmed separately.

---

## Global lock-in rules discovered so far

### G1 — Review by family/pattern, not individual query

The project has hundreds of query fixtures, but they collapse into a smaller
number of visual families. Decisions should be made at the family/pattern level
and then applied across all routes that map into that pattern.

### G2 — Do not write implementation prompts after each batch

Collect all family decisions first. Write implementation prompts only after all
19 families are reviewed, unless a single issue blocks further review or is a
safe global fix.

### G3 — Debug/parser chrome is allowed in parser review, not product UI

Parser review pages may show status chips, route names, query class, fixture
numbers, and freshness/debug metadata. User-facing result UI should not expose
route/query-class/debug labels by default.

### G4 — Normal filters are context, not caveats

Do not label ordinary interpreted filters as `CAVEATS`. Examples like `vs good
teams`, `season 2025-26`, or `last 10 games` are query context. Reserve
`CAVEATS` for actual uncertainty, data limitations, approximation, or degraded
answers.

### G5 — No-result copy must be human-first

Primary no-result copy should not expose developer/backend terms like column
names unless in debug/details mode. Translate technical causes into user-facing
language and, where possible, suggest a nearby supported query.

### G6 — Suggestions should be contextual

Generic suggestions are acceptable as a fallback, but no-result flows should
prefer query-specific suggestions based on the failed filter/reason.

### G7 — Game logs are a core answer table pattern

Game logs should be visible by default when the query asks for last-N games,
matching games, `how often` with game instances, games where a condition
happened, or top games. The game-log table is the answer table, not a hidden raw
detail.

### G8 — Large answer tables need intentional row limits

Small samples should show all rows. Medium/large game logs should not make the
page feel endless by default. Product UI should use either `Show first 10/12 +
Show all` or a fixed-height table viewport; parser review may still show all
rows when useful.

### G9 — Raw/detail toggles should not duplicate the visible answer table

Only show a raw/detail toggle when it exposes additional fields not already
visible in the answer table. If the content is not truly raw/debug data, prefer a
clearer label such as `Show additional columns` over `Show raw table`.

### G10 — Compact summary strips are allowed when they add value

The sentence hero remains primary, but a compact summary strip is allowed when
it adds high-value context such as GP, record, PPG, RPG, APG, Opp PPG, margin,
or other route-critical aggregate context. Avoid large stat-tile grids.

### G11 — Dense tables need table-engineering rules

Answer tables must support clean horizontal scrolling. Columns should not
compress until values become unreadable. Identity/date columns should remain
readable, numeric columns should keep consistent minimum widths, and wide tables
should degrade by scrolling rather than wrapping or crushing values.

### G12 — Footer rows need column-specific rules

Average and Total rows are useful, but not every column should show both.
Average footers should show core per-game averages. Total footers should show
simple counting totals. Shooting totals should only show when readable; otherwise
omit them or move them to additional details.

### G13 — Important semantic cells should not use unexplained dashes

A dash (`—`) is acceptable only when the missing meaning is obvious. For important
semantic columns like playoff round/result, use readable labels such as
`Unavailable`, `Unknown`, or `Not available`, or provide the real semantic value.

---

# Batch 1

Screenshots reviewed:

1. Entity Summary
2. Message No Result
3. Guided No Result

---

## Family 1 — Entity Summary

### Example reviewed

- Query: `How has Jayson Tatum played against good teams this season?`
- Fixture: 44
- Route/pattern shown: `player_game_summary` / `summary`

### Verdict

Keep the broad sentence-hero direction, but this family is not locked yet. It is
missing important filter wording and should include game logs when the summary
is based on a filtered game subset.

### Decisions

- The one-sentence hero direction is good.
- The sentence must include every meaningful interpreted filter.
  - Bad: `Jayson Tatum has averaged 23 points, 9.5 rebounds and 5.5 assists this season.`
  - Better: `Jayson Tatum has averaged 23.0 points, 9.5 rebounds and 5.5 assists against good teams this season.`
  - Best when sample size is available: `Jayson Tatum has averaged 23.0 points, 9.5 rebounds and 5.5 assists in 12 games against good teams this season.`
- If the query summarizes a filtered set of games, include the matching game-log
  answer table below the hero unless the route explicitly opts out as
  summary-only.
- `vs good teams` should be presented as context/filter interpretation, not as a
  caveat.
- Screenshot headshot/avatar absence should be ignored for this review because
  screenshots may intentionally suppress headshots/logos.

### Lock-in rule

Entity Summary should answer with a clear sentence hero, then include a dense
answer table when the query implies an underlying game set/window/filter. The
hero sentence must not drop filters like `against good teams`.

### Likely implementation areas

- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- summary sentence builders / context builders

---

## Family 2 — Message No Result

### Example reviewed

- Query: `What team has played the best defense recently?`
- Fixture: 14
- Route/class shown: `season_team_leaders` / `leaderboard`
- Status: unsupported / no result

### Verdict

Keep the family, but narrow its usage and improve copy.

### Decisions

- Use Message No Result only for hard unsupported cases where there is no safe
  obvious recovery path.
- Do not expose developer wording in the primary message.
  - Bad: `Column 'def_rating' not available`
  - Better: `Defensive rating is not available in the current dataset.`
- Technical details may remain in debug/details mode, but not as the main user
  explanation.
- This specific example probably deserves a guided no-result or fallback
  suggestion because `best defense recently` has reasonable nearby alternatives
  like opponent points allowed or opponent FG%.

### Lock-in rule

Message No Result = hard unsupported with no obvious next step. User-facing copy
must explain the limitation plainly, without backend implementation terms.

### Likely implementation areas

- `NoResultDisplay`
- no-result reason/copy mapping
- recovery suggestion generation

---

## Family 3 — Guided No Result

### Example reviewed

- Query: `Who scored the most points last night?`
- Fixture: 11
- Route/class shown: `season_leaders` / `leaderboard`
- Status: no match / no result

### Verdict

Keep the family. It should become the default no-result pattern for valid but
empty queries, but suggestions need to be more query-specific.

### Decisions

- Guided No Result is the right shape for valid queries that produce no rows.
- The primary explanation should name the specific failed filter/date/range when
  possible.
  - Better: `No NBA games matched Apr 11, 2026.`
- Avoid raw ISO date ranges in primary user-facing copy. Prefer readable date
  formatting like `Apr 11, 2026` or `Apr 1–12, 2026`.
- Suggested next steps should be contextual when possible.
  - For date no-results: `Try the previous NBA game day`, `Try the next NBA game day`, `Show scoring leaders this season`.
  - For missing metric no-results: suggest nearby supported metrics.
- Generic suggestions like spelling/range/filter broadening should remain only
  as fallbacks.

### Lock-in rule

Guided No Result = default valid-but-empty pattern. It must explain the specific
reason and provide query-specific recovery suggestions where possible.

### Likely implementation areas

- `NoResultDisplay`
- date/range display formatting
- recovery suggestion generation
- parser/query metadata for failure reason

---

# Batch 2

Screenshots reviewed:

4. Entity Summary + Recent Games
5. Player Game Log
6. Team Game Log

---

## Family 4 — Entity Summary + Recent Games

### Example reviewed

- Query: `Luka last 5`
- Fixture: 247
- Route/pattern shown: `player_game_summary` / `summary`

### Verdict

Mostly keep and use as a reference family. This is close to the intended
sentence-hero plus dense game-log baseline, but the table needs a fuller
box-score column set.

### Decisions

- Keep the sentence hero. The reviewed sentence is clear:
  - `Luka Dončić has averaged 34 points, 6 rebounds and 7 assists in his last 5 games.`
- Keep the dense game-log table directly under the hero.
- Keep `Average` and `Total` footer rows inside the same table.
- For last-N player summaries, show all requested rows.
- The current table is too thin for a game-log answer because it only shows the
  core counting stats.
- Required player game-log columns for this family:
  - `#`, Date, TM, Opp, W/L, MIN, PTS, REB, AST, FG, 3P, FT, STL, BLK, TOV, +/-
- Optional columns when available:
  - Score, home/away marker, TS%, eFG%

### Lock-in rule

Entity Summary + Recent Games = hero sentence + dense game-log answer table +
Average/Total footer. For last-N windows, show all requested games and include a
full useful player box-score column set.

### Likely implementation areas

- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- game-log column preset/config
- footer row generation

---

## Family 5 — Player Game Log

### Example reviewed

- Query: `How often has Nikola Jokić recorded a triple-double this season?`
- Fixture: 71
- Route/pattern shown: `player_game_finder` / `count`

### Verdict

Keep the pattern, but add display limits for large logs and avoid duplicate raw
toggles when the visible answer table already contains the game rows.

### Decisions

- Keep the count-style hero sentence:
  - `Nikola Jokić has recorded 34 triple-doubles this season.`
- Keep the dense game-log answer table.
- The reviewed table has a stronger box-score column set than Family 4, but it
  should still include FG and FT when available for consistency.
- Large logs should not take over the entire product page by default.
- Row-count behavior:
  - 0–12 rows: show all rows.
  - 13+ rows: product UI should show a capped view with either `Show first 10/12 + Show all` or a fixed-height scrollable viewport.
  - Preferred product behavior: show first 12 rows plus `Show all {N} games`.
  - Parser review pages may show all rows if that is useful for fixture QA.
- Required player game-log columns:
  - `#`, Date, TM, Opp, W/L, MIN, PTS, REB, AST, FG, 3P, FT, STL, BLK, TOV, +/-
- If the visible answer table already uses the same row set as `Player Game
  Detail`, do not show a redundant `Show raw table` toggle unless that toggle
  exposes additional raw/debug-only fields.

### Lock-in rule

Player Game Log = count/condition hero + dense game-log answer table. Small logs
show all rows; large logs are capped with a clear show-all affordance. Raw/detail
toggles should not duplicate the visible answer table.

### Likely implementation areas

- `frontend/src/components/results/patterns/GameLogResult.tsx`
- game-log row limiting / show-all behavior
- game-log column presets
- raw/detail toggle visibility rules

---

## Family 6 — Team Game Log

### Example reviewed

- Query: `How often have the Lakers held opponents under 100 points this year?`
- Fixture: 76
- Route/pattern shown: `game_finder` / `count`

### Verdict

Keep and refine. This is close to locked: the hero answers the query well and
the table is useful, but condition-specific columns should be emphasized.

### Decisions

- Keep the count + record hero sentence:
  - `The Lakers have held opponents under 100 points 7 times this season, going 7-0.`
- Keep the team-first game-log answer table open by default.
- Add/ensure columns that make the defensive condition explicit:
  - Opp PTS
  - Margin
- For condition-based logs, visually emphasize the queried condition column.
  - `opponents under 100` → highlight `Opp PTS`
  - `50-point games` → highlight PTS
  - `10+ assists` → highlight AST
  - `triple-doubles` → highlight the PTS/REB/AST condition columns or add a condition indicator
- Required team game-log columns:
  - `#`, Date, Team, Opp, Score, W/L, PTS, Opp PTS, Margin, REB, AST, 3PM, FG, 3P, FT, TOV
- Optional team game-log columns when available:
  - STL, BLK, ORB, DRB
- For defensive/team result queries, prioritize available defensive context such
  as Opp PTS, Opp FG%, forced turnovers, and margin.
- If `Game Detail` duplicates the visible answer table, remove the redundant raw
  toggle or only show it when it exposes additional raw/debug-only fields.

### Lock-in rule

Team Game Log = count/record hero + dense team-first game-log table. The table
must surface and emphasize the condition that made each game match.

### Likely implementation areas

- `frontend/src/components/results/patterns/GameLogResult.tsx`
- team game-log column preset/config
- condition-column detection/highlighting
- raw/detail toggle visibility rules

---

# Batch 3

Screenshots reviewed:

7. Game Summary Log
8. Streak Table
9. Playoff History

---

## Family 7 — Game Summary Log

### Example reviewed

- Query: `How do the Suns perform when Devin Booker didn't play?`
- Fixture: 51
- Route/pattern shown: `game_summary` / `summary`

### Verdict

Keep the family. The overall structure is right, but table width, footer
formatting, summary-strip content, and duplicate raw/detail toggles need cleanup.

### Decisions

- Keep the hero sentence:
  - `The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG.`
- Keep a compact summary strip below the hero.
- The summary strip should include the record, not only GP/PTS/REB/AST.
  - Preferred strip: `GP 18 | Record 8-10 | PPG 103.8 | RPG 43.1 | APG 21.7`
- Keep the team game-log answer table because the query asks how the team
  performed in a filtered game set.
- The table needs clean horizontal scrolling and minimum column widths; current
  dense columns can become unreadable/crushed.
- Required team game-summary-log columns:
  - `#`, Date, Team, Opp, Score, W/L, PTS, Opp PTS, Margin, REB, AST, 3PM, FG, 3P, FT, TOV
- Footer rows should stay, but follow column-specific rules:
  - Average footer: per-game averages for core numeric columns.
  - Total footer: totals for simple counting columns.
  - Shooting totals: only show makes-attempts if readable; otherwise omit or move to additional details.
- `Game Detail` raw toggle should be removed/hidden when it duplicates the
  visible game-log answer table.
- `Top Performers Detail` may remain hidden if not otherwise surfaced; ideally,
  top performers should become a small secondary section only when relevant.

### Lock-in rule

Game Summary Log = hero sentence + compact summary strip + dense team game-log
answer table. The table must remain readable under real stat volume, and raw
toggles should not duplicate visible answer-table rows.

### Likely implementation areas

- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/EntitySummaryResult.tsx` or summary strip primitive
- answer-table CSS / horizontal scroll handling
- footer row generation
- raw/detail toggle visibility rules

---

## Family 8 — Streak Table

### Example reviewed

- Query: `Jokic 5 straight games with 20+ points`
- Fixture: 201
- Route/pattern shown: `player_streak_finder` / `streak`

### Verdict

Strong family. Keep the structure and refine wording/columns. This is close to
locked.

### Decisions

- Keep the hero + ranked streak table pattern.
- The reviewed hero sentence is strong but should preserve the `5 straight games`
  threshold interpretation.
  - Current: `Nikola Jokić scored 20+ points in 18 straight games from Oct 26 to Dec 8, 2024.`
  - Better when the query means at least 5: `Nikola Jokić has 15 streaks of 5+ straight games with 20+ points. His longest was 18 games, from Oct 26 to Dec 8, 2024.`
  - Better when showing longest-only: `Nikola Jokić's longest 20+ point streak of at least 5 games was 18 games, from Oct 26 to Dec 8, 2024.`
- Highlight the main streak length column.
- Show Status only when at least one row is active/ongoing/current or when row
  statuses are mixed. If every row is `Completed`, the Status column is noise.
- Required streak table columns:
  - `#`, Streak/Condition, Length, Start, End, Games, Record, PTS, REB, AST
- Optional streak table columns:
  - Status, MIN, 3PM, +/-, FG, 3P, FT
- The threshold/minimum should be clear in the hero and/or table context.
  - Examples: `20+ PTS`, `5+ games minimum`
- Remove/hide the raw `Full Streak Detail` toggle when it duplicates the visible
  streak answer table, unless it exposes additional raw/debug-only fields.

### Lock-in rule

Streak Table = threshold-aware hero sentence + ranked streak table. The hero must
clarify exact/minimum interpretation, and the table should emphasize Length.

### Likely implementation areas

- `frontend/src/components/results/patterns/StreakResult.tsx`
- streak sentence builder
- streak table column config
- condition/threshold metadata mapping
- raw/detail toggle visibility rules

---

## Family 9 — Playoff History

### Example reviewed

- Query/example family: Playoff History
- Pattern shown: `PlayoffHistoryResult`

### Verdict

Keep the structure, but improve semantic clarity. This family needs better hero
wording, caveat wording, round/result labels, and duplicate raw-toggle handling.

### Decisions

- Keep the hero + season-by-season playoff table pattern.
- Improve hero wording:
  - Current style: `{Team} have 21 playoff appearances across 1996-97 to 2024-25 Playoffs, going 165-115.`
  - Better: `From 1996-97 through 2024-25, the Lakers made the playoffs 21 times and went 165-115.`
- If titles/finals data exists, optionally add:
  - `They reached the Finals {finals_count} times and won {titles} titles.`
- Caveat is legitimate when round data is unavailable. Keep it, but write it
  more clearly:
  - `Round-level data is unavailable before 2001-02, so those seasons are included in totals but not round breakdowns.`
- Avoid unexplained dashes in important semantic columns like Round/Result.
  Use `Unavailable`, `Unknown`, `Not available`, or a true semantic result.
- The table should answer how far the team went when data allows.
- Required playoff history columns:
  - Season, Result/Round Reached, Record, Win Pct, Games
- Optional playoff history columns:
  - Opponent, Series Result, Seed, Coach
- If only Finals/not-Finals data is available, rename the column to match what
  the data actually means rather than implying full round coverage.
- Remove/hide `Postseason Summary Detail` and `Season Breakdown Detail` raw
  toggles when they duplicate visible answer-table data. Keep only if they expose
  additional raw/debug-only fields.

### Lock-in rule

Playoff History = clear historical hero sentence + season-by-season playoff
table. Missing round data must be labeled explicitly, not shown as unexplained
dashes.

### Likely implementation areas

- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- playoff hero sentence builder
- playoff table column labels/value mapping
- caveat/context copy mapping
- raw/detail toggle visibility rules

---

## Open questions for final synthesis

- Should parser review pages keep the current large debug/context card exactly,
  or should they be visually separated from product-output screenshots?
- Should `EntitySummaryResult` always compose with `GameLogResult` when a
  `game_log` section exists, or only for specific routes / metadata flags?
- Should `good teams` expansion list show all teams behind a detail disclosure,
  or only summarized as `19 opponents` in primary context?
- For large game logs, should product UI use `Show first 12 + Show all` or a
  fixed-height scrollable table viewport?
- Should duplicated answer-table raw toggles be removed entirely or replaced
  with `Show additional columns` when extra fields exist?
- For shooting columns in footer rows, should totals be omitted by default or
  moved to an additional shooting-summary detail?
- For streak queries, how should the parser/metadata distinguish exact streak
  length (`exactly 5`) from minimum streak length (`5+`)?
