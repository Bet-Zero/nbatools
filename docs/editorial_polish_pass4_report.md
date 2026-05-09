# Editorial Polish Pass 4 Report

This pass cleaned up hero-sentence prose without changing the underlying query
data or table/stat formatting contracts.

## Files touched per pattern

- Mono-font hero callouts:
  - `frontend/src/components/results/patterns/StreakResult.tsx`
  - `frontend/src/components/results/patterns/StreakResult.module.css`
  - `frontend/src/components/results/patterns/ComparisonResult.tsx`
  - `frontend/src/components/results/patterns/ComparisonResult.module.css`
  - `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
  - `frontend/src/components/results/patterns/PlayoffHistoryResult.module.css`
- Integer `.0` trimming in hero prose:
  - `frontend/src/components/tableFormatting.ts`
  - `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
  - `frontend/src/components/results/patterns/GameLogResult.tsx`
  - `frontend/src/components/results/patterns/LeaderboardResult.tsx`
  - `frontend/src/components/results/patterns/RecordResult.tsx`
  - `frontend/src/components/results/patterns/RollingStretchResult.tsx`
  - `frontend/src/components/results/patterns/StreakResult.tsx`
- Hero template rewrites:
  - `frontend/src/components/results/patterns/StreakResult.tsx`
  - `frontend/src/components/results/patterns/ComparisonResult.tsx`
  - `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
  - `frontend/src/components/results/patterns/RecordResult.tsx`
- Coverage:
  - `frontend/src/test/ResultRenderer.test.tsx`

## Template rewrites

Streak Table hero:

- Before: `Nikola Jokić [18 games callout] Nikola Jokić's completed 20+ pts streak from 2024-10-26 to 2024-12-08.`
- After: `Nikola Jokić scored 20+ points in 18 straight games from Oct 26 to Dec 8, 2024.`

Comparison Panels hero:

- Before: `Nikola Jokić vs Joel Embiid: [Nikola Jokić +3 Wins callout].`
- After: `Nikola Jokić has 10 wins to Joel Embiid's 7 in the 2025-26 regular season.`

Playoff Matchup History hero:

- Before: `Heat and Knicks have a playoff matchup history led by [19-16 callout] against 16-19.`
- After: `The Heat lead the Knicks 19-16 in their playoff history.`
- Tie fallback: `The Heat and Knicks are tied 18-18 in their playoff history.`

Record By Decade / Matchup By Decade:

- Removed the trailing `grouped by decade` clause from both hero templates.
- Example after: `The Golden State Warriors are 1,176-1,209 (49.3%) in the regular season from 1996-97 to 2025-26.`
- Example after: `The Los Angeles Lakers lead the Boston Celtics 31-27 in regular season games.`

## Integer-zero trimming

The `.0` trimming was applied at formatter level with
`formatProseValue()` in `frontend/src/components/tableFormatting.ts`. Hero
sentence builders now call that prose formatter instead of the table formatter
when writing flowing text. This applies to player/entity summary heroes, recent
games heroes, leaderboard prose values, record prose values, rolling-stretch
heroes, and streak threshold prose.

`GameLogResult` also applies `trimProseTrailingZeroes()` to backend-supplied
headline strings because those arrive as prebuilt prose rather than component
formatted numbers.

Tables and stat boxes still use `formatValue()` / `formatAverageValue()`, so
their one-decimal alignment behavior is unchanged.

## Mono-font scope

The hero-only `heroValue` styles in the streak, comparison, and playoff pattern
CSS modules now inherit the surrounding sentence font. Mono-font styling remains
in table cells, `Stat`/stat-box values, result tables, raw-data tables, and other
standalone numeric display surfaces.

## Verification

- `npm test` passed: 18 files, 244 tests.
- `npm run build` passed and refreshed `src/nbatools/ui/dist`.
- `make test-unit PYTEST=.venv/bin/pytest` passed: 2,289 passed, 1 xpassed.
- Live `/review` browser verification passed against
  `http://127.0.0.1:8014/review`. The expanded fixture page showed:
  - `Nikola Jokić scored 20+ points in 18 straight games from Oct 26 to Dec 8, 2024.`
  - `Nikola Jokić has 10 wins to Joel Embiid's 7 in the 2025-26 regular season.`
  - `The Heat lead the Knicks 19-16 in their playoff history.`
  - `Luka Dončić has averaged 34 points, 6 rebounds and 7 assists in his last 5 games.`
- The `/review` check also confirmed that loaded Record By Decade and Matchup
  By Decade heroes no longer include `grouped by decade`, and that spans inside
  hero sentence paragraphs do not compute to the mono font.
