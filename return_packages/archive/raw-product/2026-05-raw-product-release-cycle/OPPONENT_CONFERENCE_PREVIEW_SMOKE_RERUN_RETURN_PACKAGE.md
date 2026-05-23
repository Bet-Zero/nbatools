# Opponent-Conference Preview Smoke Rerun Return Package

## 1. Executive summary

- Preview URL:
  `https://nbatools-4vme9ylii-brents-projects-686e97fc.vercel.app`
- Preview status: `BLOCKED`
- Routes checked: `/`, `/review`, `/visual-qa`
- Supported opponent-conference queries checked: 4
- Guardrail queries checked: 2
- Regression smoke checked: 6
- Mobile spot-check: checked at 390px; blocked because the supported
  opponent-conference query rendered `NO RESULT` instead of a primary record.
- Blocking issues:
  - Supported opponent-conference `team_record` queries returned
    `no_result` / `no_data` instead of supported records.
  - `/visual-qa` loaded but reported one request error:
    `Failed to execute 'json' on 'Response': Unexpected end of JSON input`.
- Non-blocking notes:
  - The prompt contained `<PASTE_PREVIEW_URL_HERE>`; the checked URL was
    resolved from the latest ready Vercel deployment for `nbatools`.
  - `HEAD` returned `501` on `/review` and `/visual-qa`, but `GET` returned
    `200`; route validation is based on `GET`.
  - Manual UI checks used live rendered browser smoke plus API response
    inspection, not screenshot diff automation.
- Recommended next step: fix the deployed preview data/runtime path for
  trusted opponent-conference coverage, then redeploy and rerun this smoke.

## 2. Route validation

| Route | Result | Notes |
|---|---|---|
| `/` | Pass | GET 200. App shell loaded with the `nbatools` search UI; API online; no 404 or crash. |
| `/review` | Pass | GET 200. Parser Review route loaded with `402 fixtures available`; no 404 or crash. |
| `/visual-qa` | Fail | GET 200 and page was not blank gray, but the live page reported `Request errors 1` and showed `Failed to execute 'json' on 'Response': Unexpected end of JSON input`. |

## 3. Opponent-conference supported query validation

| Query | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|
| Celtics record against the East this season | Supported `team_record`; 52 games, `36-16`; East conference context visible. | `team_record`, `no_result`, reason `no_data`; metadata preserved `team=BOS`, `season=2025-26`, `opponent_conference=East`; `opponent_team_abbrs=null`. | Fail | Blocking. The UI showed `NO RESULT team record summary data unavailable`, not the expected supported record. |
| Lakers record against the West | Supported `team_record`; 52 games, `33-19`; West conference context visible. | `team_record`, `no_result`, reason `no_data`; metadata preserved `team=LAL`, `season=2025-26`, `opponent_conference=West`; `opponent_team_abbrs=null`. | Fail | Blocking. No broad full-season fallback was observed, but the supported result did not execute. |
| Lakers road record against West last season | Supported `team_record`; road + West + `2024-25` season context preserved. | `team_record`, `no_result`, reason `no_data`; metadata preserved `team=LAL`, `season=2024-25`, `opponent_conference=West`; applied filters included `Location=Away` and `Season=2024-25`. | Fail | Blocking. Context chips were preserved, but no supported record rendered. |
| Knicks record against Eastern Conference teams since January 1 | Supported `team_record`; East conference + date context preserved. | `team_record`, `no_result`, reason `no_data`; metadata preserved `team=NYK`, `season=2025-26`, `opponent_conference=East`, `start_date=2026-01-01`, `end_date=2026-04-12`. | Fail | Blocking. Date/conference context was preserved, but no supported record rendered. |

## 4. Guardrail validation

| Query | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|
| Celtics record against east coast teams | Geography phrase does not get treated as East conference support; no broad fake full-season record. | `team_record`, `no_result`, reason `filter_not_supported`; `unsupported_filters=["opponent_conference"]`; no result sections. | Pass | Guardrail held. UI showed unsupported-boundary copy rather than a fake record. |
| Celtics conference finals record | Conference Finals remains playoff-round/single-team playoff boundary behavior, not opponent-conference filtering. | `playoff_history`, `no_result`, reason `filter_not_supported`; `unsupported_filters=["single_team_playoff_round_record"]`. | Pass | Guardrail held. It did not route as an opponent-conference filter. |

## 5. Regression mini-smoke

| Query | Expected | Actual | Verdict | Notes |
|---|---|---|---|---|
| Who leads the NBA in points per game this season? | Supported query still answers. | `season_leaders`, `ok`; Luka Doncic shown first at about `33.48` PPG. | Pass | No obvious rendering break. |
| What is Denver's record when Nikola Jokic has a triple-double? | Supported query still answers. | `player_game_summary`, `ok`; summary row showed `24-10` in `34` games. | Pass | Special-event filter rendered. |
| Which team gave up the fewest points per game? | Supported query still answers. | `season_team_leaders`, `ok`; Boston Celtics shown first at about `107.16` opponent PPG. | Pass | Defensive/opponent-points route rendered. |
| Lakers Celtics playoff matchup history | Supported query still answers. | `playoff_matchup_history`, `ok`; summary included Lakers `6-7` in 13 games. | Pass | Matchup history rendered with expected caveats. |
| Warriors net rating this season | Unsupported boundary query refuses cleanly. | `game_summary`, `no_result`, reason `filter_not_supported`; `unsupported_filters=["single_team_advanced_stat_summary"]`. | Pass | No fake broad fallback observed. |
| players with most personal fouls this season | Unsupported boundary query refuses cleanly. | `season_leaders`, `no_result`, reason `filter_not_supported`; `unsupported_filters=["personal_foul_leaderboard"]`. | Pass | No fake supported leaderboard observed. |

## 6. Mobile spot-check

| Query | Verdict | Notes |
|---|---|---|
| Celtics record against the East this season | Fail | At 390px, page/body width stayed 390px with no horizontal overflow, but the primary supported answer was absent because the query rendered `NO RESULT` / `no_data`. |

## 7. Issues found

| Priority | Issue | Blocking? | Recommended action |
|---|---|---|---|
| P0 | Supported opponent-conference queries route to `team_record` but return `no_result` / `no_data`; resolved opponent team lists are `null` in preview metadata. | Yes | Verify the deployed `DATA_SOURCE=r2` data path includes trusted `2024-25` and `2025-26` team-conference membership coverage, then redeploy and rerun the supported smoke queries. |
| P1 | `/visual-qa` is reachable and not blank, but reports one request error with an unexpected-end-of-JSON response parse failure. | Yes | Inspect the failing live visual-QA request on the deployed preview, fix the empty/non-JSON response path, and rerun `/visual-qa`. |
| P2 | Prompt did not include the concrete preview URL. | No | Paste the intended preview URL in future handoffs, or continue resolving from Vercel deployment metadata when the URL is omitted. |

## 8. Final recommendation

- `BLOCKED`
- Next action: fix the preview deployment/data issue that prevents trusted
  opponent-conference records from resolving, confirm `/visual-qa` no longer
  reports a JSON parse error, redeploy, and rerun this smoke package.
