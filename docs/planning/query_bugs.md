# Query Bug Log

Tracked query-surface bugs that exposed a reusable implementation pattern.

## 1. Season-Type-Blind Leaderboard Thresholds

- Status: In progress locally; fixed in code and covered by focused tests, awaiting deployed verification.
- Pattern: Leaderboard threshold helpers used regular-season default floors without considering `season_type`.
- Affected surfaces: Player season leaderboards, team season leaderboards, and player percentage volume floors.
- User-facing symptom: Playoff leaderboard queries like `most ppg in 2025 playoffs` silently filtered down to Finals teams because regular-season minimum-games and attempt floors excluded most playoff runs.
- Root cause: `_recommended_min_games` in both leaderboard modules and the percentage-stat attempt floors in the player leaderboard module were season-type-blind.
- Fix shape: Keep regular-season defaults unchanged, but use playoff-scaled minimum-games and attempt floors when `season_type` is playoffs.
- Regression coverage: Focused leaderboard unit tests plus end-to-end historical query regressions for playoff player/team queries and a regular-season control.
- Resolution note: Mark this entry resolved after PR merge, deployed `/query` verification, and a live playoff smoke query that shows non-Finals teams in the returned leaders.
