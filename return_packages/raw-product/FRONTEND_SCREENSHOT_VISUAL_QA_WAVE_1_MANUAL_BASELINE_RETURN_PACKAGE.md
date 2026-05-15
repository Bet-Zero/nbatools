# Frontend Screenshot / Visual QA Wave 1: Manual Baseline Return Package

## 1. Executive summary

- What changed: added a 15-case visual QA corpus, a dev/internal `/visual-qa` page that renders live cases through `ResultEnvelope` + `ResultRenderer`, a manual capture checklist doc, and focused harness tests.
- Production rendering changed? no
- Backend behavior changed? no
- Playwright added? no
- Visual QA route/page: `/visual-qa` via `frontend/src/VisualQaPage.tsx`
- Visual corpus: `qa/frontend_visual_qa_corpus.yaml`
- Screenshot artifacts created? no
- Manual browser validation performed? yes
- Recommended next step: capture desktop/mobile screenshots from `/visual-qa`, review the manual baseline, and defer Playwright/diffing until after that review.

## 2. Files changed

| File                                                               | Change type       | Why                                                                                                                             |
| ------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `qa/frontend_visual_qa_corpus.yaml`                                | New corpus        | Stores the 15 approved visual QA cases, query text, viewport targets, and visual-focus notes.                                   |
| `frontend/src/visualQaCases.ts`                                    | New loader/config | Imports the repo-level corpus into the frontend and exposes shared visual QA constants.                                         |
| `frontend/src/VisualQaPage.tsx`                                    | New internal page | Runs live `/query` calls, renders each case through the existing product result components, and exposes stable capture targets. |
| `frontend/src/VisualQaPage.module.css`                             | New styles        | Provides the internal QA layout, checklist, and review-card styling without touching product render components.                 |
| `frontend/src/main.tsx`                                            | Route wiring      | Adds `/visual-qa` while keeping `/review` and the default app route intact.                                                     |
| `frontend/src/test/VisualQaPage.test.tsx`                          | New tests         | Verifies corpus rendering, loading/error stability, screenshot-button plumbing, and route wiring.                               |
| `frontend/vite.config.ts`                                          | Config update     | Allows the frontend/Vitest environment to read the repo-level `qa/` corpus safely.                                              |
| `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md` | New checklist doc | Captures the manual desktop/mobile screenshot workflow and per-case review checklist.                                           |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md`    | Doc update        | Adds the Visual QA Wave 1 setup, workflow, and output-artifact plan.                                                            |
| `docs/index.md`                                                    | Doc index update  | Registers the new checklist doc in the planning index.                                                                          |

## 3. Visual QA corpus

| Case ID                                   | Category                         | Viewports                    | Visual focus                                                                    |
| ----------------------------------------- | -------------------------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| `guards_fg_percentage_leaders`            | `position_filtered_leaderboard`  | `desktop_1280`, `mobile_390` | Guards chip proximity, FG% header visibility, filter context visibility         |
| `centers_rebound_leaders_wave4`           | `position_filtered_leaderboard`  | `desktop_1280`, `mobile_390` | Centers context, RPG header visibility, hero/table cohesion                     |
| `fewest_points_allowed_team_leader`       | `team_defense_leaderboard`       | `desktop_1280`, `mobile_390` | Fewest-allowed hero wording, opponent metric header, defensive framing          |
| `most_points_allowed_team_leaders_wave4`  | `team_defense_leaderboard`       | `desktop_1280`, `mobile_390` | Most-allowed hero wording, opponent metric header, defensive framing            |
| `opponent_ppg_leaders_wave4`              | `team_defense_leaderboard`       | `desktop_1280`, `mobile_390` | Opponent PPG alias clarity, defensive header visibility, hero/header alignment  |
| `personal_foul_leaders_wave4`             | `unsupported_stat_leaderboard`   | `desktop_1280`, `mobile_390` | No-result message hierarchy, diagnostic de-emphasis, PF shorthand not misread   |
| `rookie_scoring_leaders_wave4`            | `unsupported_role_leaderboard`   | `desktop_1280`, `mobile_390` | Unsupported rookie message prominence, clean wrapping, mobile readability       |
| `starter_assist_leaders_wave4`            | `unsupported_role_leaderboard`   | `desktop_1280`, `mobile_390` | Starter/bench unsupported message prominence, long role wording wrap            |
| `bench_scoring_leaders_wave4`             | `unsupported_role_leaderboard`   | `desktop_1280`, `mobile_390` | Bench unsupported boundary message, no-result balance, secondary details        |
| `celtics_bench_scoring_boundary_wave4`    | `unsupported_team_role_boundary` | `desktop_1280`, `mobile_390` | Team context with unsupported message, chip spacing, no-result hierarchy        |
| `record_when_jokic_triple_double`         | `record_when_condition`          | `desktop_1280`, `mobile_390` | Triple-double chip proximity, summary-card hierarchy, primary record visibility |
| `lakers_road_record_last_season`          | `team_record_filtered`           | `desktop_1280`, `mobile_390` | Away/season chips, record table headers, filtered hero/table cohesion           |
| `heat_knicks_playoff_series_record_wave4` | `playoff_matchup_history`        | `desktop_1280`, `mobile_390` | Dense playoff table readability, round/season visibility, section separation    |
| `lebron_durant_comparison_wave4`          | `player_comparison`              | `desktop_1280`, `mobile_390` | Two-player identity clarity, dense comparison rows, mobile stacking             |
| `biggest_scoring_games`                   | `top_performances`               | `desktop_1280`, `mobile_390` | 83-point outlier visibility, wide headers, top-row wrapping                     |

## 4. Visual QA page behavior

- Route: `/visual-qa`
- Data source: live `POST /query` calls through the existing frontend API client
- Render method: one case card per approved case, each using `ResultEnvelope` plus `ResultRenderer` with no test-only props
- Capture target selectors: `data-visual-case-id="<case_id>"`
- Screenshot/checklist workflow: use the page for manual review at `1280px` and `390px`, record notes in the checklist doc, and optionally use the current-viewport ZIP button for browser-side capture
- Limitations:
  - requires a local backend on `127.0.0.1:8000` for live `/query` responses
  - does not add Playwright, screenshot diffing, or pixel baselines
  - this run validated the page manually in-browser but did not persist a screenshot artifact under `outputs/`

## 5. Artifact/output plan

- Checklist: `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- Screenshots: store manual captures under `outputs/frontend_visual_qa/<run_id>/screenshots/desktop/` and `outputs/frontend_visual_qa/<run_id>/screenshots/mobile/`
- Report: this return package plus any follow-up manual findings package after screenshot review
- Where manual captures should be stored: `outputs/frontend_visual_qa/<run_id>/`

## 6. Validation

- VisualQaPage tests:
  `cd frontend && npm test -- src/test/VisualQaPage.test.tsx --run`
  Result: passed, `4/4` tests.
- Requested frontend tests:
  `cd frontend && npm test -- src/test/VisualQaPage.test.tsx src/test/reviewScreenshots.test.ts src/test/ReviewPage.test.tsx --run`
  Result: passed, `15/15` tests across `3` files.
- review screenshot tests:
  included in the requested frontend test command above; `1/1` passed.
- ReviewPage tests:
  included in the requested frontend test command above; `10/10` passed.
- build:
  `cd frontend && npm run build`
  Result: passed. Vite emitted the existing large-chunk warning for the main JS bundle (`544.90 kB` > `500 kB`).
- lint:
  `cd frontend && npm run lint`
  Result: passed after the VisualQaPage hook fix. One existing warning remains in `frontend/src/ReviewPage.tsx` about ref cleanup (`react-hooks/exhaustive-deps`).
- git diff --check:
  `git diff --check`
  Result: passed with no output.
- manual local `/visual-qa` validation:
  Performed.
  Local servers started with:
  `source .venv/bin/activate && uvicorn nbatools.api:app --reload --host 127.0.0.1 --port 8000`
  `cd frontend && npm run dev -- --host 127.0.0.1`
  Opened `http://127.0.0.1:5173/visual-qa` in the integrated browser.
  Confirmed:
  - heading `Frontend Visual QA Wave 1` is visible
  - route label `Internal route: /visual-qa` is visible
  - `15` `data-visual-case-id` capture targets are present
  - page reaches `15 / 15 cases completed`
  - screenshot button becomes enabled with `15 cards are ready for viewport ZIP capture`
  - `Desktop focus` appears `15` times and `Mobile focus` appears `15` times

## 7. Next recommendation

- Should the user capture screenshots next? yes
- Which viewports? desktop around `1280px` and mobile around `390px`
- Which cases should be reviewed first? start with `heat_knicks_playoff_series_record_wave4`, `lebron_durant_comparison_wave4`, `fewest_points_allowed_team_leader`, `personal_foul_leaders_wave4`, `bench_scoring_leaders_wave4`, `celtics_bench_scoring_boundary_wave4`, and `biggest_scoring_games`
- Should Playwright wait until after manual review? yes
