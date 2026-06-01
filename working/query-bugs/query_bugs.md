# Query Bug Log

Tracked query-surface bugs that exposed a reusable implementation pattern.

## 1. Season-Type-Blind Leaderboard Thresholds

- Status: Resolved on 2026-05-02 after merge and live `/query` verification on the main Vercel deployment.
- Pattern: Leaderboard threshold helpers used regular-season default floors without considering `season_type`.
- Affected surfaces: Player season leaderboards, team season leaderboards, and player percentage volume floors.
- User-facing symptom: Playoff leaderboard queries like `most ppg in 2025 playoffs` silently filtered down to Finals teams because regular-season minimum-games and attempt floors excluded most playoff runs.
- Root cause: `_recommended_min_games` in both leaderboard modules and the percentage-stat attempt floors in the player leaderboard module were season-type-blind.
- Fix shape: Keep regular-season defaults unchanged, but use playoff-scaled minimum-games and attempt floors when `season_type` is playoffs.
- Regression coverage: Focused leaderboard unit tests plus end-to-end historical query regressions for playoff player/team queries and a regular-season control.
- Resolution note: Verified on `https://nbatools-git-main-brents-projects-686e97fc.vercel.app/query` with `most ppg in 2025 playoffs`, which returned non-Finals teams and expected stars including Giannis Antetokounmpo, Shai Gilgeous-Alexander, and Nikola Jokic in the top 10.
