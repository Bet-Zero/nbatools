# Frontend Visual QA Wave 1 Checklist

## Scope

- Visual corpus: `qa/frontend_visual_qa_corpus.yaml`
- Internal route: `/visual-qa`
- Target viewports: desktop around `1280px`, mobile around `390px`
- Render path: live `POST /query` requests through `ResultEnvelope` + `ResultRenderer`
- Stable selector pattern: `data-visual-case-id="<case_id>"`
- Recommended screenshot storage after manual capture:
  `outputs/frontend_visual_qa/<run_id>/screenshots/desktop/<case_id>.png`
  `outputs/frontend_visual_qa/<run_id>/screenshots/mobile/<case_id>.png`
- Recommended summary/report storage after manual review:
  `outputs/frontend_visual_qa/<run_id>/`

## Manual Capture Workflow

1. Start the local backend that serves `/query`.
2. Start the frontend dev server and open `/visual-qa`.
3. Let all 15 cases finish loading through the live query path.
4. Capture the desktop pass at about `1280px` wide.
5. Capture the mobile pass at about `390px` wide.
6. Record pass/fail notes and any visual findings in this checklist or the follow-up review package.
7. Defer Playwright, screenshot diffing, and visual fixes until the manual baseline is reviewed.

## Fix Wave 1 Findings

| Finding | Cases | Status | Follow-up check |
| --- | --- | --- | --- |
| FVQ-001 mobile dense table clipping | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck mobile `390px` cards for visible `PTS`, `Edge / Difference`, and `Series Result` columns. |
| FCQ/FVQ-002 filtered leaderboard hero context | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck hero copy for `led guards` / `led centers` and absence of generic `led the NBA` wording in filtered cases. |

## Case Checklist

| Case ID                                   | Query                                                          | Desktop capture | Mobile capture | Visual focus                                                                                            | Pass/fail notes       |
| ----------------------------------------- | -------------------------------------------------------------- | --------------- | -------------- | ------------------------------------------------------------------------------------------------------- | --------------------- |
| `guards_fg_percentage_leaders`            | What players have the best field goal percentage among guards? | required        | required       | Hero includes guard context; FG% header visibility; filter context still obvious before first row       | Fix Wave 1 targeted: hero should say `led guards`, not `led the NBA` |
| `centers_rebound_leaders_wave4`           | Which centers have the most rebounds this season?              | required        | required       | Hero includes center context; RPG header visibility; hero/table alignment                               | Fix Wave 1 targeted: hero should say `led centers`, not `led the NBA` |
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
| `heat_knicks_playoff_series_record_wave4` | Heat Knicks playoff series record                              | required        | required       | Dense playoff table readability; `Series Result` visibility; summary/comparison separation              | Fix Wave 1 targeted: mobile table keeps Season, Round, Winner, Series Result visible |
| `lebron_durant_comparison_wave4`          | LeBron James vs Kevin Durant comparison                        | required        | required       | Two-player identity clarity; `Edge / Difference` visibility; mobile stacking/readability                | Fix Wave 1 targeted: mobile table keeps Metric, both players, and Edge / Difference visible |
| `biggest_scoring_games`                   | What were the biggest scoring games this season?               | required        | required       | 83-point outlier row visibility; `PTS` visibility; top-row wrapping at mobile width                     | Fix Wave 1 targeted: mobile table keeps Rank, Player, Date, and PTS visible |
