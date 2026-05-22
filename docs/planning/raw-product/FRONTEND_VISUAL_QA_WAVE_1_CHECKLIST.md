# Frontend Visual QA Wave 1 Checklist

## Scope

- Visual corpus: `qa/frontend_visual_qa_corpus.yaml`
- Internal route: `/visual-qa`
- Target viewports: desktop around `1280px`, mobile around `390px`
- Current corpus baseline: 20 cases, or 40 required desktop/mobile viewport
  reviews. The original 15 review cases remain in the checklist below.
- Render path: live `POST /query` requests through `ResultEnvelope` + `ResultRenderer`
- Stable selector pattern: `data-visual-case-id="<case_id>"`
- Repeatable screenshot artifact root:
  `outputs/visual_qa_screenshots/<run_id>/`
- Artifact capture command:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=<run_id>`
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
7. Use the artifact capture command below when the pass needs repeatable
   desktop/mobile screenshots and metrics.
8. After the preview mobile overflow fix, rerun the deployed preview at about
   `390px` wide before marking the preview boundary ready.

## Screenshot Artifact Capture

The manual baseline is reviewed. The first screenshot automation wave now adds
non-diffing artifact capture against the existing production-like `/visual-qa`
shell.

```bash
npm --prefix frontend run build
nbatools-api

npm --prefix frontend run qa:visual-screenshots -- \
  --base-url http://127.0.0.1:8000 \
  --run-id <run_id>
```

The canonical run writes `manifest.json`, `desktop_1280/metrics.json`,
`mobile_390/metrics.json`, one full-page PNG per viewport, and all 40 card PNGs
under `outputs/visual_qa_screenshots/<run_id>/`. It fails for incomplete case
loading, request errors, duplicate or missing selected case IDs, canonical case
count drift from 20, measured document-level horizontal overflow, or screenshot
capture failure. Repeated `--case <case_id>` filters are for local reruns, not
the canonical 20-case evidence set.

### Canonical Artifact Validation

- Validation date: 2026-05-22.
- Run ID: `visual_qa_20_case_baseline`.
- Command:
  `make visual-qa-screenshots VISUAL_QA_BASE_URL=http://127.0.0.1:8000 VISUAL_QA_RUN_ID=visual_qa_20_case_baseline`.
- Artifact root:
  `outputs/visual_qa_screenshots/visual_qa_20_case_baseline/`.
- Desktop artifact pass: `desktop_1280` captured 20/20 cases, request errors 0,
  statuses `ok: 15`, `no_result: 5`, `error: 0`, and document/body overflow
  `false`.
- Mobile artifact pass: `mobile_390` captured 20/20 cases, request errors 0,
  statuses `ok: 15`, `no_result: 5`, `error: 0`, and document/body overflow
  `false`.
- Manifest evidence: 20 desktop card screenshots and 20 mobile card
  screenshots are listed.
- PNG total: 42 expected captures, counting all card PNGs plus one page PNG per
  viewport.
- Deferred: screenshot diffing, committed PNG baselines, and CI gating.

## Expanded 20-Case Baseline Review

- Review date: 2026-05-22.
- Review surface: local production API shell at `/visual-qa`.
- Desktop pass: 20/20 cases reviewed at a `1280px` viewport; request errors 0;
  response statuses were `ok: 15`, `no_result: 5`, `error: 0`; viewport,
  document, and body widths all measured `1280px`.
- Mobile pass: 20/20 cases reviewed at a `390px` viewport; request errors 0;
  response statuses were `ok: 15`, `no_result: 5`, `error: 0`; viewport,
  document, and body widths all measured `390px`.
- Review result: all 40 required desktop/mobile viewport reviews passed. The
  page loaded, all cases rendered, answer-first hierarchy stayed visible,
  context/caveats stayed bounded, no document-level horizontal overflow was
  measured, and wide result tables stayed inside internal scrolling frames.
- Expansion cases passed their focused checks: Jokic summary hero hierarchy,
  Jokic triple-double count-before-finder layout, Jokic home/away split
  comparison readability, Curry three-threes streak hierarchy, and Jokic
  five-game rebounding stretch window/date-span cohesion.
- Blocking findings: none.

## Fix Wave 1 Findings

| Finding | Cases | Status | Follow-up check |
| --- | --- | --- | --- |
| FVQ-001 mobile dense table clipping | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck mobile `390px` cards for visible `PTS`, `Edge / Difference`, and `Series Result` columns. |
| FCQ/FVQ-002 filtered leaderboard hero context | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Confirmed and targeted in Fix Wave 1 | Recheck hero copy for `led guards` / `led centers` and absence of generic `led the NBA` wording in filtered cases. |
| FVQ-003 preview mobile QA wrapper overflow | `biggest_scoring_games`, `lebron_durant_comparison_wave4`, `heat_knicks_playoff_series_record_wave4`, `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Fixed and rechecked locally; deployed preview rerun passed after redeploy | Expanded local baseline measured `390px` viewport, document, and body widths with all 20 cards rendered; the earlier preview rerun passed the five mobile blocker cards. |

## Case Checklist

| Case ID                                   | Query                                                          | Desktop capture | Mobile capture | Visual focus                                                                                            | Pass/fail notes       |
| ----------------------------------------- | -------------------------------------------------------------- | --------------- | -------------- | ------------------------------------------------------------------------------------------------------- | --------------------- |
| `guards_fg_percentage_leaders`            | What players have the best field goal percentage among guards? | pass            | pass           | Hero includes guard context; FG% header visibility; filter context still obvious before first row       | Expanded baseline pass: guard context and FG% answer remain early; wide leaderboard stays in its table frame. |
| `centers_rebound_leaders_wave4`           | Which centers have the most rebounds this season?              | pass            | pass           | Hero includes center context; RPG header visibility; hero/table alignment                               | Expanded baseline pass: center context and RPG answer stay readable at desktop and mobile widths. |
| `fewest_points_allowed_team_leader`       | Which team has allowed the fewest points per game this season? | pass            | pass           | Fewest allowed hero wording; Opponent PTS Per Game header; defensive context stays obvious              | Expanded baseline pass: defensive answer framing and first row remain clear. |
| `most_points_allowed_team_leaders_wave4`  | which teams allow the most points per game this season         | pass            | pass           | Most allowed hero wording; defensive framing; top-row readability                                       | Expanded baseline pass: most-allowed wording stays distinct and table overflow remains internal on mobile. |
| `opponent_ppg_leaders_wave4`              | opponent PPG leaders this season                               | pass            | pass           | Opponent PPG alias clarity; defensive header visibility; hero/header semantic alignment                 | Expanded baseline pass: Opponent PPG meaning remains aligned from hero to table. |
| `personal_foul_leaders_wave4`             | personal fouls leaders this season                             | pass            | pass           | No-result primary message hierarchy; diagnostics remain secondary; PF shorthand not mistaken for answer | Expanded baseline pass: unsupported no-result answer leads and Details stays secondary. |
| `rookie_scoring_leaders_wave4`            | rookie scoring leaders this season                             | pass            | pass           | Unsupported rookie message prominence; clean wrapping; mobile readability                               | Expanded baseline pass: rookie boundary copy wraps cleanly without visual noise. |
| `starter_assist_leaders_wave4`            | starter assist leaders this season                             | pass            | pass           | Starter/bench unsupported message prominence; long role wording wrap; diagnostics secondary             | Expanded baseline pass: role-boundary copy remains primary and readable. |
| `bench_scoring_leaders_wave4`             | bench players scoring leaders this season                      | pass            | pass           | Bench unsupported boundary message; no-result balance; details remain secondary                         | Expanded baseline pass: bench boundary card stays compact and answer-first. |
| `celtics_bench_scoring_boundary_wave4`    | Celtics bench scoring this season                              | pass            | pass           | Team context with unsupported message; no-result hierarchy; chip spacing                                | Expanded baseline pass: team context and unsupported boundary hierarchy remain clear. |
| `record_when_jokic_triple_double`         | What is Denver's record when Nikola Jokic has a triple-double? | pass            | pass           | Triple-double chip proximity; summary-card hierarchy; primary record answer visibility                  | Expanded baseline pass: record answer stays early with triple-double context close by. |
| `lakers_road_record_last_season`          | Lakers road record last season                                 | pass            | pass           | Away and Season 2024-25 chips; record headers; filtered hero/table cohesion                             | Expanded baseline pass: Away and season context stay visible before the filtered record detail. |
| `heat_knicks_playoff_series_record_wave4` | Heat Knicks playoff series record                              | pass            | pass           | Dense playoff table readability; `Series Result` visibility; summary/comparison separation              | Expanded baseline pass: matchup answer stays readable and dense playoff detail remains contained. |
| `lebron_durant_comparison_wave4`          | LeBron James vs Kevin Durant comparison                        | pass            | pass           | Two-player identity clarity; `Edge / Difference` visibility; mobile stacking/readability                | Expanded baseline pass: player identities and edge/difference comparison stay legible on mobile. |
| `biggest_scoring_games`                   | What were the biggest scoring games this season?               | pass            | pass           | 83-point outlier row visibility; `PTS` visibility; top-row wrapping at mobile width                     | Expanded baseline pass: top-performance answer and PTS evidence remain visible without page overflow. |
| `jokic_season_summary`                    | Jokic this season                                              | pass            | pass           | Player-summary hero hierarchy; Nikola Jokic season context; compact summary wrapping                    | Expansion pass: Jokic identity, season context, and summary hero lead at both viewports. |
| `jokic_triple_double_finder`              | How often has Nikola Jokic recorded a triple-double this season? | pass          | pass           | Count-before-finder hierarchy; triple-double context; game-log table containment                        | Expansion pass: count answer comes before the finder detail and the game-log table scrolls internally. |
| `jokic_home_away_split`                   | Jokic home vs away this season                                 | pass            | pass           | Home/Away split context; comparison row readability; detailed metric containment                        | Expansion pass: Home/Away context and split comparison stay readable with contained detail. |
| `curry_3_threes_streak`                   | Curry longest streak with at least 3 threes                    | pass            | pass           | Streak threshold/length hierarchy; span/status readability; compact streak table density                | Expansion pass: threshold, streak length, and date span read as the answer before detail. |
| `jokic_best_5_rebounding_stretch`         | Jokic best 5-game rebounding stretch this season               | pass            | pass           | Window/metric/date-span cohesion; best-window hero; rolling-stretch table readability                   | Expansion pass: best-window hero keeps window, metric, and date span cohesive. |
