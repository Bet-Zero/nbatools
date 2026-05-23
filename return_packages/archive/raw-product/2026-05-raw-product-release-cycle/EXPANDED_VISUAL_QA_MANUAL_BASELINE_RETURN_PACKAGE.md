# Expanded Visual QA Manual Baseline Return Package

## Status

- Review date: 2026-05-22.
- Review mode: manual desktop/mobile `/visual-qa` baseline review for the
  expanded 20-case corpus.
- Review result: `PASS_WITH_MANUAL_LIMITATION`.
- Production code changed: no.
- Blocking visual issues: none.
- Reviewed baseline: 20/20 cases at desktop and 20/20 cases at mobile, 40
  viewport reviews total.

## Scope

This review rechecked the full Visual QA corpus after the baseline expanded from
15 to 20 cases. It covered the original 15 cases and these five expansion cases:

- `jokic_season_summary`
- `jokic_triple_double_finder`
- `jokic_home_away_split`
- `curry_3_threes_streak`
- `jokic_best_5_rebounding_stretch`

`/visual-qa` was reviewed through the local production API shell with a desktop
viewport around `1280px` and a mobile viewport around `390px`.

## Method

- Started the local FastAPI shell for `/visual-qa` and `/query`.
- Captured the expanded corpus with a temporary local headless browser review
  script and inspected the full-page and per-card desktop/mobile screenshots.
- Reviewed answer hierarchy, context/caveat density, request health, document
  width, table containment, the five expansion-case visual focuses, and the
  original 15 cases for regressions.
- No repository visual QA harness command was found for this review pass, so
  the capture script was kept temporary and only the docs evidence remains in
  the repo.

Temporary review artifacts were written outside the repo under
`/private/tmp/expanded_visual_qa_manual_baseline/`, including metrics JSON and
desktop/mobile screenshots.

## Baseline Result

| Viewport | Cases reviewed | Request errors | Backend status counts | Width measurements | Result |
|---|---:|---:|---|---|---|
| Desktop `1280x900` | 20/20 | 0 | `ok: 15`, `no_result: 5`, `error: 0` | viewport `1280px`; document client/scroll `1280px`; body client/scroll `1280px` | pass |
| Mobile `390x844` | 20/20 | 0 | `ok: 15`, `no_result: 5`, `error: 0` | viewport `390px`; document client/scroll `390px`; body client/scroll `390px` | pass |

The page loaded at both viewports, the run-progress UI reached 20/20 completed
cases, loaded responses reached 20, and there was no document-level horizontal
overflow at either viewport.

## Desktop Findings

- Result answers stayed visible early across successful result cards.
- Context chips and caveats stayed close to the answer without duplicating the
  full diagnostic payload.
- The five unsupported/no-result cards still led with product-facing no-result
  messaging and kept Details secondary.
- Wide finder and leaderboard tables stayed inside their result frames. The
  widest desktop examples included `jokic_triple_double_finder`,
  `guards_fg_percentage_leaders`, `biggest_scoring_games`, and
  `jokic_home_away_split`.

## Mobile Findings

- The document and body stayed at the `390px` viewport width, so no prior
  QA-wrapper/card overflow regression returned.
- Answer-first hierarchy remained readable before dense table detail.
- Wide tables used internal horizontal scrolling rather than widening the page.
  Mobile examples with contained wide table frames included
  `guards_fg_percentage_leaders`, `fewest_points_allowed_team_leader`,
  `most_points_allowed_team_leaders_wave4`,
  `opponent_ppg_leaders_wave4`, `lakers_road_record_last_season`,
  `jokic_triple_double_finder`, `jokic_home_away_split`, and
  `curry_3_threes_streak`.
- Long internal QA case IDs can wrap on narrow cards, but the result content
  stays intact and no blocker was found.

## Case Review

| Case | Desktop finding | Mobile finding |
|---|---|---|
| `guards_fg_percentage_leaders` | Pass: guard filter context, FG% answer, and first rows are visible. | Pass: answer remains early and the wide leaderboard scrolls inside its table frame. |
| `centers_rebound_leaders_wave4` | Pass: center context and RPG answer stay aligned with the table. | Pass: center answer stays readable and dense detail remains contained. |
| `fewest_points_allowed_team_leader` | Pass: defensive framing and fewest-allowed answer are clear. | Pass: top answer remains clear and the defensive table frame stays within the card. |
| `most_points_allowed_team_leaders_wave4` | Pass: most-allowed wording stays distinct from ordinary scoring leadership. | Pass: answer text remains clear and wide detail scrolls internally. |
| `opponent_ppg_leaders_wave4` | Pass: Opponent PPG alias and table semantics agree. | Pass: defensive answer remains readable before internally scrolling detail. |
| `personal_foul_leaders_wave4` | Pass: unsupported no-result answer leads over diagnostics. | Pass: no-result message wraps cleanly and Details stays secondary. |
| `rookie_scoring_leaders_wave4` | Pass: rookie boundary message is prominent and not mistaken for a result table. | Pass: unsupported message remains readable without card overflow. |
| `starter_assist_leaders_wave4` | Pass: role-boundary no-result hierarchy remains clear. | Pass: long role copy stays readable and diagnostics remain secondary. |
| `bench_scoring_leaders_wave4` | Pass: bench unsupported boundary remains compact and answer-first. | Pass: no-result card balance stays intact at narrow width. |
| `celtics_bench_scoring_boundary_wave4` | Pass: team context and unsupported answer hierarchy remain visible. | Pass: chip spacing and no-result copy stay readable. |
| `record_when_jokic_triple_double` | Pass: primary Denver record answer stays near triple-double context. | Pass: record answer remains early with supporting context below it. |
| `lakers_road_record_last_season` | Pass: Away and Season 2024-25 context lead the filtered record detail. | Pass: record answer remains readable and the wider detail table stays contained. |
| `heat_knicks_playoff_series_record_wave4` | Pass: playoff matchup answer and comparison detail remain separated. | Pass: dense playoff content remains readable without document overflow. |
| `lebron_durant_comparison_wave4` | Pass: both player identities and comparison detail are clear. | Pass: comparison content remains readable in the mobile stack. |
| `biggest_scoring_games` | Pass: top-performance answer and PTS evidence remain visible. | Pass: 83-point outlier evidence stays readable and table width does not widen the page. |
| `jokic_season_summary` | Pass: Jokic identity, season context, and summary hero lead. | Pass: summary hero stays compact before season detail. |
| `jokic_triple_double_finder` | Pass: count-before-finder hierarchy and triple-double context are clear. | Pass: count answer remains first and the game-log table scrolls internally. |
| `jokic_home_away_split` | Pass: Home/Away split context and comparison rows are readable. | Pass: split chips and primary metrics stay readable with contained detail. |
| `curry_3_threes_streak` | Pass: threshold, streak length, and span/status read as one answer. | Pass: streak hierarchy remains compact and detailed rows stay contained. |
| `jokic_best_5_rebounding_stretch` | Pass: best-window hero keeps window, metric, and date span cohesive. | Pass: five-game stretch answer stays readable before rolling detail. |

## Expansion Case Verdict

The five newly approved visual QA cases passed their documented focus:

- `jokic_season_summary`: player-summary hero hierarchy and compact season
  context passed.
- `jokic_triple_double_finder`: count-before-finder answer order and game-log
  containment passed.
- `jokic_home_away_split`: split context, comparison readability, and detail
  containment passed.
- `curry_3_threes_streak`: threshold, streak length, and span/status hierarchy
  passed.
- `jokic_best_5_rebounding_stretch`: best-window hero and
  window/metric/date-span cohesion passed.

## Original 15 Regression Check

No regression was found in the original 15-case baseline:

- The earlier dense-table and mobile-wrapper risk cases remained contained.
- Filtered guard/center leaderboard context stayed visible.
- Defensive leaderboard framing stayed intact.
- Record, playoff, comparison, and top-performance cards stayed answer-first.
- The five expected no-result boundary cards kept diagnostics secondary.

## Docs Updated

- `docs/planning/raw-product/FRONTEND_VISUAL_QA_WAVE_1_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`

## Validation

| Validation | Result |
|---|---|
| Manual desktop `/visual-qa` baseline at `1280px` | pass, 20/20 cases reviewed |
| Manual mobile `/visual-qa` baseline at `390px` | pass, 20/20 cases reviewed |
| Request error check | pass, 0 request errors at both viewports |
| Document/body width check | pass, no desktop or mobile document-level horizontal overflow measured |
| `git diff --check` | pass |

## Release Impact

- The Visual QA manual baseline is now reviewed for the full 20-case local
  corpus across desktop and mobile.
- The baseline remains manual evidence with no screenshot-diff automation.
- The older deployed preview request-health evidence still covers the
  pre-expansion 15-case preview route; this pass adds the expanded local
  desktop/mobile evidence.

## Next Recommended Action

Use the 20-case local baseline as the current manual Visual QA evidence and keep
the next Visual QA investment on repeatable automation or a future preview
refresh when deployed `/visual-qa` evidence needs to match the expanded corpus.
