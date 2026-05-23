# Raw Product Preview Manual QA Return Package

## 1. Executive summary

- Preview URL:
  `https://nbatools-n6h31ww6e-brents-projects-686e97fc.vercel.app`
- Preview readiness status: `BLOCKED`
- Routes checked: `/`, `/review`, `/visual-qa`
- Smoke queries checked: 6
- Mobile spot checks: 5
- Blocking issues: mobile `/visual-qa` cards overflow horizontally at ~390px,
  clipping primary result answers in the visible viewport.
- Non-blocking notes:
  - The prompt contained `<PASTE_PREVIEW_URL_HERE>`; the checked URL was the
    latest successful GitHub/Vercel deployment target from
    `2026-05-16T23:21:04Z`.
  - `/review` loads and does not 404, but its fixture area was still in the
    initial `0 / 0 loaded` / loading state during this route check.
  - Query smoke was run through the deployed UI deep-link path (`?q=`), which
    exercises the same live app rendering and `/query` API.
  - Existing known limitations still apply: manual visual QA is not automated
    screenshot diffing, and frontend-copy coverage is selected coverage only.
- Recommended next step: fix the mobile horizontal overflow/clipping on
  `/visual-qa`, redeploy, then rerun this preview manual QA.

## 2. Route validation

| Route | Result | Notes |
|---|---|---|
| `/` | Pass | App shell loaded; query input was visible; no 404. |
| `/review` | Pass | Route returned the app shell and rendered the Parser Review page; no 404. Fixture area showed `0 / 0 loaded` / loading during this check. |
| `/visual-qa` | Pass | Route returned the app shell; page was not blank gray; no YAML/JSON parse error; 15 visual QA cards rendered; 15 live `/query` POSTs were issued; run completed `15 / 15`; backend statuses were `ok 10 / no result 5 / error 0`; request errors were `0`. |

## 3. Query smoke validation

| Query | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|
| Who leads the NBA in points per game this season? | Supported result | `ok`, route `season_leaders`; Luka Doncic shown as 33.5 PPG leader. | Pass | No obvious wrong route, missing key answer, desktop overflow, or broken rendering. |
| What is Denver's record when Nikola Jokic has a triple-double? | Supported result | `ok`, route `player_game_summary`; Nuggets shown as `24-10` when Jokic records a triple-double. | Pass | Special-event context and answer were visible. |
| Which team gave up the fewest points per game? | Supported result | `ok`, route `season_team_leaders`; Celtics shown at 107.2 opponent PPG. | Pass | Defensive/opponent-points route was correct. |
| Lakers Celtics playoff matchup history | Supported result | `ok`, route `playoff_matchup_history`; Celtics lead playoff games `7-6`, series record tied `1-1`. | Pass | Matchup history rendered with caveat and series table. |
| Warriors net rating this season | Unsupported boundary | `no_result`, route `game_summary`, reason `filter_not_supported`; copy says single-team net rating summaries are unsupported. | Pass | No fake broad leaderboard or crash. |
| players with most personal fouls this season | Unsupported boundary | `no_result`, route `season_leaders`, reason `filter_not_supported`; copy says personal-foul leaderboards are unsupported. | Pass | No fake supported leaderboard or crash. |

## 4. Mobile spot checks

| Case | Verdict | Notes |
|---|---|---|
| `biggest_scoring_games` | Fail | Live result loaded as `top_player_games / ok`, and Bam Adebayo / `83` / `PTS` content was present, but at ~390px the `/visual-qa` card overflowed horizontally and clipped the primary answer/table in the visible viewport. |
| `lebron_durant_comparison_wave4` | Fail | Live result loaded as `player_compare / ok`, and both player identities were present, but the mobile viewport showed horizontal overflow and clipped comparison content. |
| `heat_knicks_playoff_series_record_wave4` | Fail | Live result loaded as `playoff_matchup_history / ok`, with Heat/Knicks playoff context present, but the mobile viewport clipped the result card content horizontally. |
| `guards_fg_percentage_leaders` | Fail | Live result loaded as `season_leaders / ok`; guard filter context was visible and the hero mentions guards, but the primary answer and table area were clipped horizontally at ~390px. |
| `centers_rebound_leaders_wave4` | Fail | Live result loaded as `season_leaders / ok`; center filter context was visible and the hero mentions centers, but the primary answer and table area were clipped horizontally at ~390px. |

## 5. Issues found

| Priority | Issue | Blocking? | Recommended action |
|---|---|---|---|
| P0 | `/visual-qa` mobile layout overflows horizontally at ~390px, causing primary answer/result card text to be clipped in the visible viewport for the required mobile spot-check cases. | Yes | Fix the mobile width/min-width/overflow behavior in the `/visual-qa` wrapper and/or rendered result containers, redeploy, then rerun the preview route, smoke, and mobile checks. |
| P3 | The prompt's preview URL field was still a placeholder. | No | Continue using the latest deployment URL from GitHub/Vercel metadata when the explicit URL is missing, or paste the intended preview URL in the handoff. |

## 6. Final recommendation

- `BLOCKED`
- Next action: fix the mobile `/visual-qa` clipping, redeploy, and rerun Raw
  Product Preview Manual QA before treating the current boundary as
  preview-ready.
