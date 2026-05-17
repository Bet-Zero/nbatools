# Raw Product Preview Manual QA Rerun Return Package

## 1. Executive summary

- Preview URL:
  `https://nbatools-fuq06rg4y-brents-projects-686e97fc.vercel.app`
- Preview readiness status: `PREVIEW_READY_WITH_NOTES`
- Routes checked: `/`, `/review`, `/visual-qa`
- Smoke queries checked: 6
- Mobile blocker cases rechecked: 5
- Blocking issues: none
- Non-blocking notes:
  - The prompt still contained `<PASTE_NEW_PREVIEW_URL_HERE>`; the checked URL
    was resolved from the latest ready Vercel deployment for the current
    `main` commit, deployment `dpl_GMnXTzb47h9UxG2DVv6yRS23FqXz`.
  - Manual visual QA is still measurement/spot-check based, not automated
    screenshot diffing.
  - Existing selected frontend-copy coverage limitations still apply.
- Recommended next step: mark this preview boundary ready with notes and
  continue the next release-readiness action.

## 2. Route validation

| Route | Result | Notes |
|---|---|---|
| `/` | Pass | App shell loaded with the `nbatools` homepage/search UI; HTTP 200; no 404 or crash; desktop page/body width stayed at 1280px. |
| `/review` | Pass | Parser Review route loaded; HTTP 200; no 404 or crash; desktop page/body width stayed at 1280px. |
| `/visual-qa` | Pass | HTTP 200; page was not blank gray; no YAML/JSON parse error page; 15 visual QA cards rendered; run completed `15 / 15`; backend statuses were `ok 10 / no result 5 / error 0`; request errors were `0`; mobile page/body width stayed at 390px. |

## 3. Mobile blocker recheck

| Case | Verdict | Notes |
|---|---|---|
| `biggest_scoring_games` | Pass | At 390px, page/body width stayed 390px; card measured 378px wide; result column measured 364px wide; `83` and `PTS` were present and horizontally visible. |
| `lebron_durant_comparison_wave4` | Pass | At 390px, card and result column stayed within viewport; `Edge / Difference` was horizontally visible. |
| `heat_knicks_playoff_series_record_wave4` | Pass | At 390px, card and result column stayed within viewport; `Series Result` was horizontally visible. |
| `guards_fg_percentage_leaders` | Pass | At 390px, card and result column stayed within viewport; guard filter context remained readable and `FG%` was visible. |
| `centers_rebound_leaders_wave4` | Pass | At 390px, card and result column stayed within viewport; center filter context remained readable and `RPG` was visible. |

## 4. Query smoke validation

| Query | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|
| Who leads the NBA in points per game this season? | Supported result | `ok`, route `season_leaders`; Luka Doncic shown as the PPG leader at about `33.5` PPG. | Pass | No obvious wrong route, missing key answer, desktop overflow, or broken rendering. |
| What is Denver's record when Nikola Jokic has a triple-double? | Supported result | `ok`, route `player_game_summary`; Denver shown as `24-10` in 34 Jokic triple-double games. | Pass | Key record answer was visible. |
| Which team gave up the fewest points per game? | Supported result | `ok`, route `season_team_leaders`; Boston Celtics shown at about `107.2` opponent PPG. | Pass | Defensive/opponent-points route was correct. |
| Lakers Celtics playoff matchup history | Supported result | `ok`, route `playoff_matchup_history`; Celtics shown leading playoff games `7-6`, with Lakers/Celtics Finals series rows visible. | Pass | Matchup history rendered without desktop overflow or crash. |
| Warriors net rating this season | Unsupported boundary | `no_result`, route `game_summary`, reason `filter_not_supported`; unsupported copy was visible. | Pass | No fake broad leaderboard or generic crash/error. |
| players with most personal fouls this season | Unsupported boundary | `no_result`, route `season_leaders`, reason `filter_not_supported`; unsupported copy was visible. | Pass | No fake supported leaderboard or generic crash/error. |

## 5. Issues found

| Priority | Issue | Blocking? | Recommended action |
|---|---|---|---|
| P3 | The rerun prompt did not include the concrete preview URL. | No | Paste the intended preview URL in future handoffs, or continue resolving it from Vercel deployment metadata when explicit URL text is missing. |
| P3 | Manual visual QA remains spot-check/measurement based rather than screenshot-diff automated. | No | Keep this as a known limitation until the planned visual QA automation wave. |

## 6. Final recommendation

- `PREVIEW_READY_WITH_NOTES`
- Next action: mark the post-fix preview rerun as passed, keep the non-blocking
  notes attached, and continue the next release-readiness step.
