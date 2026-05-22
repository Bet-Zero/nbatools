# Frontend Visual QA Wave 1 Checklist

## Scope

- Visual corpus: `qa/frontend_visual_qa_corpus.yaml`
- Internal route: `/visual-qa`
- Target viewports: desktop around `1280px`, mobile around `390px`
- Current corpus baseline: 20 cases, or 40 required desktop/mobile viewport
  reviews. The original 15 review cases remain in the checklist below.
- Render path: live `POST /query` requests through `ResultEnvelope` + `ResultRenderer`
- Stable selector pattern: `data-visual-case-id="<case_id>"`
- Recommended screenshot storage after manual capture:
  `outputs/frontend_visual_qa/<run_id>/screenshots/desktop/<case_id>.png`
  `outputs/frontend_visual_qa/<run_id>/screenshots/mobile/<case_id>.png`
- Recommended summary/report storage after manual review:
  `outputs/frontend_visual_qa/<run_id>/`

## Manual Capture Workflow

1. Start the local backend that serves `/query`.
2. Open `/visual-qa` through either the local production API shell
   (`http://127.0.0.1:8000/visual-qa`) or the frontend dev server
   (`http://127.0.0.1:5173/visual-qa`, or the current Vite-selected port).
3. Let all 20 cases finish loading through the live query path.
4. Capture the desktop pass at about `1280px` wide.
5. Capture the mobile pass at about `390px` wide.
6. Record pass/fail notes and any visual findings in this checklist or the follow-up review package.
7. Defer Playwright, screenshot diffing, and visual fixes until the manual baseline is reviewed.
8. After the preview mobile overflow fix, rerun the deployed preview at about
   `390px` wide before marking the preview boundary ready.

## Fix Wave 1 Findings

| Finding | Cases | Status | Follow-up check |
| --- | --- | --- | --- |
| FVQ-001 mobile dense table clipping | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck mobile `390px` cards for visible `PTS`, `Edge / Difference`, and `Series Result` columns. |
| FCQ/FVQ-002 filtered leaderboard hero context | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck hero copy for `led guards` / `led centers` and absence of generic `led the NBA` wording in filtered cases. |
| FVQ-003 preview mobile QA wrapper overflow | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4`, `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Fixed locally after preview blocker; preview rerun required after redeploy | Local production shell measured `pageWidth 390` at a 390px viewport with all five blocker cards inside the viewport and required result text present. Rerun preview manual QA after redeploy. |

## Case Checklist

| Case ID                                   | Query                                                          | Desktop capture | Mobile capture | Visual focus                                                                                            | Pass/fail notes       |
| ----------------------------------------- | -------------------------------------------------------------- | --------------- | -------------- | ------------------------------------------------------------------------------------------------------- | --------------------- |
| `guards_fg_percentage_leaders`            | What players have the best field goal percentage among guards? | required        | required       | Hero includes guard context; FG% header visibility; filter context still obvious before first row       | Preview overflow fixed locally: card stays inside 390px viewport; `guards` and `FG%` text present; preview rerun required. |
| `centers_rebound_leaders_wave4`           | Which centers have the most rebounds this season?              | required        | required       | Hero includes center context; RPG header visibility; hero/table alignment                               | Preview overflow fixed locally: card stays inside 390px viewport; `centers` and `RPG` text present; preview rerun required. |
| `fewest_points_allowed_team_leader`       | Which team has allowed the fewest points per game this season? | required        | required       | Fewest allowed hero wording; Opponent PTS Per Game header; defensive context stays obvious              | Pending manual review |
| `most_points_allowed_team_leaders_wave4`  | which teams allow the most points per game this season         | required        | required       | Most allowed hero wording; defensive framing; top-row readability                                       | Pending manual review |
| `opponent_ppg_leaders_wave4`              | opponent PPG leaders this season                               | required        | required       | Opponent PPG alias clarity; defensive header visibility; hero/header semantic alignment                 | Pending manual review |
| `personal_foul_leaders_wave4`             | personal fouls leaders this season                             | required        | required       | No-result primary message hierarchy; diagnostics remain secondary; PF shorthand not mistaken for answer | Pending manual review |
| `rookie_scoring_leaders_wave4`            | rookie scoring leaders this season                             | required        | required       | Unsupported rookie message prominence; clean wrapping; mobile readability                               | Pending manual review |
| `starter_assist_leaders_wave4`            | starter assist leaders this season                             | required        | required       | Starter/bench unsupported message prominence; long role wording wrap; diagnostics secondary             | Pending manual review |
| `bench_scoring_leaders_wave4`             | bench players scoring leaders this season                      | required        | required       | Bench unsupported boundary message; no-result balance; details remain secondary                         | Pending manual review |
| `celtics_bench_scoring_boundary_wave4`    | Celtics bench scoring this season                              | required        | required       | Team context with unsupported message; no-result hierarchy; chip spacing                                | Pending manual review |
| `record_when_jokic_triple_double`         | What is Denver's record when Nikola Jokic has a triple-double? | required        | required       | Triple-double chip proximity; summary-card hierarchy; primary record answer visibility                  | Pending manual review |
| `lakers_road_record_last_season`          | Lakers road record last season                                 | required        | required       | Away and Season 2024-25 chips; record headers; filtered hero/table cohesion                             | Pending manual review |
| `heat_knicks_playoff_series_record_wave4` | Heat Knicks playoff series record                              | required        | required       | Dense playoff table readability; `Series Result` visibility; summary/comparison separation              | Preview overflow fixed locally: card stays inside 390px viewport; `Series Result` text present; preview rerun required. |
| `lebron_durant_comparison_wave4`          | LeBron James vs Kevin Durant comparison                        | required        | required       | Two-player identity clarity; `Edge / Difference` visibility; mobile stacking/readability                | Preview overflow fixed locally: card stays inside 390px viewport; `Edge / Difference` text present; desktop 1280px spot-check remained inside viewport. |
| `biggest_scoring_games`                   | What were the biggest scoring games this season?               | required        | required       | 83-point outlier row visibility; `PTS` visibility; top-row wrapping at mobile width                     | Preview overflow fixed locally: card stays inside 390px viewport; `83` and `PTS` text present; desktop 1280px spot-check remained inside viewport. |
| `jokic_season_summary`                    | Jokic this season                                              | required        | required       | Player-summary hero hierarchy; Nikola Jokic season context; compact summary wrapping                    | Pending expansion review |
| `jokic_triple_double_finder`              | How often has Nikola Jokic recorded a triple-double this season? | required      | required       | Count-before-finder hierarchy; triple-double context; game-log table containment                        | Pending expansion review |
| `jokic_home_away_split`                   | Jokic home vs away this season                                 | required        | required       | Home/Away split context; comparison row readability; detailed metric containment                        | Pending expansion review |
| `curry_3_threes_streak`                   | Curry longest streak with at least 3 threes                    | required        | required       | Streak threshold/length hierarchy; span/status readability; compact streak table density                | Pending expansion review |
| `jokic_best_5_rebounding_stretch`         | Jokic best 5-game rebounding stretch this season               | required        | required       | Window/metric/date-span cohesion; best-window hero; rolling-stretch table readability                   | Pending expansion review |
