# Result Display Family Review Lock-In Notes — Batch 6 Addendum

> Purpose: final-batch addendum for `docs/planning/result_display_family_review_lock_in.md`.
> This captures Families 16–19 from the final screenshot review batch.
> The final synthesis/implementation prompts should read both files:
>
> - `docs/planning/result_display_family_review_lock_in.md`
> - `docs/planning/result_display_family_review_lock_in_batch_6_addendum.md`

---

## Additional global lock-in rules from final batch

### G21 — Core leaderboard table pattern is working

The standard leaderboard shape is successful and should be treated as a locked
base pattern for leaderboards:

- hero sentence
- dense ranked table
- queried metric highlighted

This applies to season leaders, top performances, rolling stretches, record
leaderboards, playoff round records, and decade leaderboards.

### G22 — Game/window leaderboard heroes need event context

If the top row represents a specific game or stretch/window, the hero should
include the event context that makes the result meaningful:

- top performance: opponent, date, result/score when available
- rolling stretch: start/end dates and window size

### G23 — Query wording controls deduplication

For families that can produce overlapping or repeated rows, the query wording
should decide deduplication behavior.

For rolling stretches:

- `which players` → one best window per player by default
- `best stretches` / `best windows` → allow multiple windows, including the same player
- named-player query → show that player's windows

### G24 — Table width polish remains a shared requirement

Even strong leaderboard tables can show minor width problems, such as truncated
team abbreviations. Final implementation needs shared table column sizing and
minimum-width rules, not one-off route fixes.

---

# Batch 6 / Final Batch

Screenshots reviewed:

16. Matchup By Decade
17. Leaderboard Table
18. Top Performances
19. Rolling Stretch

---

## Family 16 — Matchup By Decade

### Example reviewed

- Query: `Lakers vs Celtics by decade`
- Fixture: 238
- Route/pattern shown: `matchup_by_decade` / `comparison`

### Verdict

Keep and refine. The two-team hero and decade-by-decade matchup table are
structurally good. Main fixes are context/caveat separation, adding total games
per decade, and hiding duplicate raw/detail toggles.

### Decisions

- Keep the two-team hero sentence plus decade-by-decade matchup table.
- Reviewed hero is directionally clear:
  - `The Los Angeles Lakers lead the Boston Celtics 31-27 in regular season games.`
- Prefer hero copy that includes the range when available:
  - `The Lakers lead the Celtics 31-27 in regular-season games from 1996-97 through 2025-26.`
- The caveat block currently contains normal context, not caveats:
  - `matchup history: LAL vs BOS by decade`
  - `across 1996-97 to 2025-26`
- Convert that to Context / Interpreted as.
- Required table columns:
  - Decade, Games, Team A W-L, Team A Win %, Team B W-L, Team B Win %
- The current table is missing total `Games` per decade; add it so each decade's sample size is clear.
- `Matchup Summary Detail` raw toggle should be hidden/removed when it duplicates the visible hero/table. Keep only if it exposes additional raw/debug-only fields.

### Lock-in rule

Matchup By Decade = two-team hero sentence + decade-by-decade matchup table. The
visible table should include total games per decade and should not use Caveats for
ordinary matchup/range context.

### Likely implementation areas

- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- matchup-by-decade table config
- matchup hero sentence builder
- context/caveat copy mapping
- raw/detail toggle visibility rules

---

## Family 17 — Leaderboard Table

### Example reviewed

- Query: `Who leads the NBA in points per game this season?`
- Fixture: 1
- Route/pattern shown: `season_leaders` / `leaderboard`

### Verdict

Lock as the core leaderboard pattern. This is one of the cleanest and most
successful families.

### Decisions

- Keep the hero sentence plus dense ranked leaderboard table.
- Keep the queried metric highlight. In this example, `PPG` is correctly highlighted.
- Improve hero wording slightly:
  - Current: `Luka Dončić scored the most points per game in the 2025-26 regular season, with 33.5 per game.`
  - Better: `Luka Dončić led the NBA with 33.5 PPG in the 2025-26 regular season.`
  - Alternative: `Luka Dončić led the NBA in scoring in 2025-26, averaging 33.5 points per game.`
- Required leaderboard columns:
  - `#`, Player/Team, Queried Metric, Season, Team, GP/Sample, Type
- Optional context:
  - qualified players only
  - minimum games/minutes
  - regular season/playoffs
- Qualification/minimum context belongs in Context, not Caveats.
- Fix shared table sizing so team abbreviations/names do not truncate awkwardly.

### Lock-in rule

Leaderboard Table = hero sentence + dense ranked leaderboard table + queried
metric highlighted. This is the base pattern for generic player/team
leaderboards.

### Likely implementation areas

- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- leaderboard hero sentence builder
- metric highlight mapping
- context/caveat copy mapping
- shared table column sizing

---

## Family 18 — Top Performances

### Example reviewed

- Query: `What were the biggest scoring games this season?`
- Fixture: 31
- Route/pattern shown: `top_player_games` / `leaderboard`

### Verdict

Keep and refine. The ranked single-game performance table is strong. The hero
should include more game context.

### Decisions

- Keep the top-performance hero plus ranked single-game performance table.
- Keep the queried metric highlight. In this example, `PTS` is correctly highlighted.
- Current hero is awkward:
  - `The top scoring games this season: Bam Adebayo with 83 points.`
- Better hero formats:
  - `Bam Adebayo had the top scoring game this season, scoring 83 points against the Wizards on Mar 10.`
  - `Bam Adebayo owns the top scoring game this season with 83 points.`
  - If result is available: `Bam Adebayo had the top scoring game this season with 83 points in a win over Washington on Mar 10.`
- Hero should include player, metric value, opponent, date, and result/score when available.
- Required table columns:
  - Rank, Player, Date, Opp, Result, Queried Metric, REB, AST, 3PM
- Supporting columns should adapt by queried metric:
  - scoring query → PTS, REB, AST, 3PM
  - rebounds query → PTS, REB, AST
  - assists query → PTS, REB, AST, TOV
  - 3PM query → PTS, 3PM, 3PA if available
- Optional table column:
  - Score

### Lock-in rule

Top Performances = top-performance hero + ranked single-game performance table.
The hero must include the specific game context, not just the player/value.

### Likely implementation areas

- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- top-game/performance column presets
- top-performance hero sentence builder
- metric-specific supporting stat config
- shared table column sizing

---

## Family 19 — Rolling Stretch

### Example reviewed

- Query: `Which players have the hottest 3-game scoring stretch this year?`
- Fixture: 36
- Route/pattern shown: `player_stretch_leaderboard` / `leaderboard`

### Verdict

Keep and add deduplication rules. The stretch hero and ranked table are strong,
but query wording should determine whether overlapping/same-player windows are
allowed.

### Decisions

- Keep the stretch hero plus ranked rolling-window table.
- Reviewed hero is strong:
  - `Best 3-game scoring stretch this season: Luka Dončić averaged 45.3 PPG from Mar 16 to Mar 19.`
- The table is readable and the queried metric `PPG` is highlighted correctly.
- Required columns:
  - Rank, Player, Window, Queried Metric, Start, End, Season
- Optional columns:
  - Team, Games, Opponents, Record, PTS total
- Current table can show overlapping windows and multiple rows for the same player. This may be mathematically correct but confusing depending on query wording.
- Default deduplication behavior:
  - `which players` → one best window per player
  - `best stretches` / `best windows` → allow multiple windows, including the same player
  - named-player query → show that player's windows
- Hero should clarify whether leaderboard is ranking players or windows.
  - Player-oriented: `{Player} had the hottest 3-game scoring stretch this season, averaging 45.3 PPG from Mar 16 to Mar 19.`
  - Window-oriented: `Best 3-game scoring stretch this season: {Player} averaged 45.3 PPG from Mar 16 to Mar 19.`

### Lock-in rule

Rolling Stretch = stretch hero + ranked rolling-window table. The renderer must
respect query wording for deduplication: players vs windows/stretches vs named
player.

### Likely implementation areas

- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- rolling stretch table config
- rolling stretch hero sentence builder
- deduplication mode selection from query intent/metadata
- metric highlight mapping

---

## Final batch open questions for final synthesis

- For Matchup By Decade, should total games be added as a required column even when both teams' W-L totals imply it?
- For Leaderboard Table, where should qualification/minimum rules be displayed when available?
- For Top Performances, should `Score` become required when available, or remain optional?
- For Rolling Stretch, can the parser/response metadata distinguish `which players` from `best windows/stretches`, or does the frontend need to infer it from query text/route metadata?
- Should all leaderboard-ish families share one column-sizing primitive/preset system?
