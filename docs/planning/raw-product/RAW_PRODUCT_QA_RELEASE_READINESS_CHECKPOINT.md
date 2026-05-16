# Raw Product QA Release Readiness Checkpoint

## 1. Executive summary

- Backend raw QA status: clean for the current 243-case corpus.
- Frontend-copy QA status: clean for the selected 59-case rendered-copy corpus.
- Visual QA status: 15-case manual baseline completed; targeted mobile/table and
  filtered-leaderboard hero fixes were verified locally.
- Deploy parity status: `/visual-qa` now follows the same local and deployed SPA
  shell routing path as `/review`; preview validation remains pending until a
  preview URL exists.
- Release-readiness verdict: backend product QA is release-ready for the
  currently supported and intentionally unsupported corpus boundaries. Treat a
  deploy-preview check, frontend-copy rerun, and full raw corpus rerun as the
  final release checklist before shipping.

## 2. Backend Raw Query Answer QA

- Corpus size: 243 cases.
- Latest run:
  `outputs/raw_query_answer_qa/20260516T221654Z/report.md`.
- Pass/fail: expectation cases `pass: 243`; failed case IDs: none.
- Result statuses: `ok: 202`, `no_result: 32`, `error: 9`.
- Expectation checks: `pass: 1368`.
- Suspicious flags: 0.
- Informational flags: `frontend_hero_expected: 149`.
- Verified outliers: `top_performance_high_points: 1`.
- Manual review statuses: `pass: 35`, `expected_unsupported: 27`,
  `verified_outlier: 1`, `unreviewed: 180`.

Main coverage areas:

- player/entity summaries
- team records and team record leaderboards
- record-when player/team conditions
- without-player conditions
- player and team leaderboards
- top performances
- splits, comparisons, matchup records, and head-to-head summaries
- rolling stretches and streaks
- playoff history, playoff matchup history, playoff appearances, and playoff
  round/appearance leaderboards
- date/window filters, including last-N, month windows, explicit seasons,
  since-date windows, and since All-Star context
- opponent-quality, position, role, stat alias, and defensive/opponent-points
  phrasing guardrails
- explicit unsupported-boundary behavior

Recent fix waves:

- Corpus Expansion Wave 5: 195 to 243 cases.
- Fix Wave 8A: defensive/opponent-points alias variants.
- Fix Wave 8B: playoff phrasing routing.
- Fix Wave 8C1: team record intent and since-date windows.
- Fix Wave 8C2: player entity and stat-context routing.
- Fix Wave 8D: product-boundary finalization.

## 3. Coverage map

Supported/query-covered areas:

- Player/entity summaries: current-season, career, last-N, opponent-quality,
  home/away, wins/losses, role context, availability context, and selected stat
  contexts.
- Team records: overall, home/away, road, date windows, explicit seasons,
  opponent-quality, scoring thresholds, opponent-points thresholds, and
  `how did TEAM do` W/L summary phrasing.
- Record-when conditions: player stat thresholds, special events such as
  triple-doubles, player shooting thresholds, team scoring thresholds, and team
  opponent-points thresholds.
- Without-player conditions: single-player absence record and player summary
  contexts where source coverage exists.
- Leaderboards: standard player stats, percentage/advanced aliases that are
  execution-backed, position-filtered player leaderboards, team stat
  leaderboards, team advanced leaderboards, and team record leaderboards.
- Team advanced leaderboards: league-wide net rating, offensive rating,
  defensive rating, and pace leaderboards are supported.
- Top performances: player single-game points, assists, rebounds, threes,
  blocks, steals, plus-minus, team scoring games, and named-player best-game
  phrasing.
- Splits: player/team home-away and wins-losses splits, player comparisons,
  team comparisons, and matchup record/comparison routes.
- Rolling stretches/streaks: player rolling stretch leaderboards and player/team
  streak queries covered by existing route contracts.
- Playoff history: single-team playoff history, appearances, finals/conference
  finals appearance leaderboards, round-record leaderboards, and era/decade
  records.
- Playoff matchup history: explicit team-pair playoff history, series history,
  matchup history, and Finals matchup history phrasing.
- Playoff round/appearance leaderboards: best round records and most round or
  Finals appearances, including since-year filters.
- Comparisons: full-name player comparisons, recent player comparisons, team
  comparisons, and guarded game-log/stat-vs-player interpretations.
- Date/window filters: explicit dates, closed month windows, since-date windows,
  latest-season defaults, last season, 2024-25 explicit season, last-N windows,
  and since All-Star.
- Opponent-quality/defensive-stat aliases: playoff-team/good-team buckets,
  top-defense context, points allowed, opponent PPG, `gave up`, `allowing`, and
  `held teams/opponents under` variants.
- Unsupported boundaries: unsupported surfaces are expected to return explicit
  `no_result` / `filter_not_supported` or otherwise expected corpus statuses
  instead of broad plausible answers.

## 4. Explicit unsupported boundaries

These surfaces are intentionally guarded by the corpus as unsupported behavior.
They are not current product failures.

- Personal-foul leaderboards:
  - Current behavior: returns `no_result` / `filter_not_supported` with
    `unsupported_filters=["personal_foul_leaderboard"]`; variants preserve
    `metadata.stat=pf` where parsed.
  - Why unsupported: personal fouls committed need an approved leaderboard stat
    contract before being exposed as a supported ranking.
  - Future support path: approve the stat contract, add execution-backed PF
    leaderboard behavior, then promote the current boundary cases into support
    expectations.
- Single-team advanced-stat scalar summaries:
  - Current behavior: single-team net/offensive/defensive rating and pace
    summary phrasing returns `single_team_advanced_stat_summary` unsupported
    metadata; league-wide team advanced leaderboards remain supported.
  - Why unsupported: there is no approved route/result contract for a single
    team advanced-stat scalar answer or rank-preserving lookup.
  - Future support path: add a dedicated summary or team-advanced lookup
    contract with stable sections, metadata, and frontend rendering.
- Rookie leaderboards:
  - Current behavior: returns an explicit unsupported-filter no-result.
  - Why unsupported: rookie status is not part of the trusted current
    leaderboard filter contract.
  - Future support path: add trusted rookie metadata, parser slots, execution
    filtering, and docs/tests.
- League-wide starter/bench leaderboards:
  - Current behavior: returns explicit unsupported-filter no-results for
    starter/bench leaderboard phrasing.
  - Why unsupported: league-wide role filters need source-backed role
    classification and a route contract.
  - Future support path: define role coverage, minimums, and stat contracts,
    then add execution-backed filters.
- Team bench scoring summaries:
  - Current behavior: returns explicit unsupported-filter no-results for team
    bench scoring/points.
  - Why unsupported: team bench scoring requires role-scoped team aggregation
    that is not part of the current team summary contract.
  - Future support path: define a team bench/unit scoring dataset or derived
    aggregation and expose stable summary sections.
- Opponent-conference filters:
  - Current behavior: returns explicit `opponent_conference` unsupported-filter
    no-results instead of broad full-season records.
  - Why unsupported: complete, trusted team-conference metadata and route
    semantics are not yet approved.
  - Future support path: add conference metadata coverage, season-aware joins,
    and filter preservation tests.
- Single-team playoff round records:
  - Current behavior: single-team Finals/conference-finals record phrasing
    returns explicit unsupported-filter no-results.
  - Why unsupported: current route/result contracts support round leaderboards
    and matchup history, but not single-team round records; pre-2001 round
    labels are also unreliable for some historical cases.
  - Future support path: approve single-team playoff round-record semantics,
    coverage requirements, and fallback behavior for unreliable round labels.
- Subjective queries such as clutch, cooled-off, best defender, MVP candidate,
  best player lately, and similar opinion/trend requests:
  - Current behavior: returns unsupported or no-result responses rather than
    inventing metric definitions.
  - Why unsupported: these require product-approved definitions and source
    coverage before becoming answerable.
  - Future support path: define metric-backed semantics and source coverage for
    each family, then add parser, execution, and copy contracts.
- Multi-player availability and on/off or lineup membership:
  - Current behavior: multi-player availability, on/off, and lineup membership
    forms return explicit unsupported/no-result responses.
  - Why unsupported: trusted stint/lineup data and multi-player availability
    semantics are outside the current product contract.
  - Future support path: add a dedicated lineup/stint dataset with documented
    grain, join keys, trust fields, and fallback behavior.
- Team rolling-stretch leaderboards:
  - Current behavior: team-scoped rolling-stretch wording returns explicit
    unsupported-filter no-results.
  - Why unsupported: current rolling-stretch support is player-oriented and no
    team route/result contract has been approved.
  - Future support path: define team rolling-window metrics, sections, and
    route behavior.
- Minutes leaderboards and team single-game threes:
  - Current behavior: guarded as product-boundary/stat-coverage decisions rather
    than current failures.
  - Why unsupported: these need explicit stat/route coverage decisions before
    being promoted.
  - Future support path: approve the stat contracts and add targeted route,
    output, frontend, and corpus coverage.

## 5. Verified outliers / data-quality notes

- The current verified outlier is `top_performance_high_points`.
- The specific allowlisted row is Bam Adebayo's 83-point game on
  2026-03-10, tracked in `qa/verified_outliers.yaml` as
  `bam_adebayo_83_points_2026_03_10`.
- The QA harness still detects high-point top-performance rows. Rows matching
  the allowlist move into the verified-outlier bucket; new high-point rows that
  are not allowlisted remain suspicious flags.
- A future data-quality review is triggered when a new extreme top-performance
  row appears, the allowlisted row no longer matches local source data, official
  source evidence changes, or a suspected impossible/statistically inconsistent
  row appears in QA output.
- Verified outliers are displayed as source data, not suppressed or capped.

## 6. Frontend-copy QA status

- Selected case count: 59.
- Latest clean run path:
  `outputs/frontend_copy_qa/20260515T224620Z/frontend_copy_report.md`.
- Status: 59 rendered successfully, 0 render failures, 0 soft-check failures.
- Earlier semantic-copy clean run:
  `outputs/frontend_copy_qa/20260515T024718Z/frontend_copy_report.md`.

Fixed findings:

- Position filter visibility/source: guard-filtered leaderboard phrasing now
  carries `position_filter=guards` and renders the applied Position filter.
- Opponent-points hero wording: fewest/most allowed-points leaderboards render
  according to executed direction instead of implying best defense incorrectly.
- Unsupported no-result guidance: personal-foul, rookie, league-wide
  starter/bench, and team bench-scoring unsupported filters have specific
  no-result copy.
- Filtered leaderboard hero context: position-filtered heroes use guard/center
  context instead of generic `led the NBA` wording.

Remaining limitations:

- The frontend-copy corpus is selected, not the full backend corpus.
- The harness uses DOM text extraction from rendered components; it is not a
  full visual review.
- Exact frontend copy should become hard assertions only for targeted,
  stable regressions.

## 7. Visual QA status

- A 15-case manual visual baseline exists for `/visual-qa`.
- Desktop and mobile review completed for the approved baseline set.
- Mobile dense table clipping was fixed for top performances, comparisons, and
  playoff matchup tables.
- Filtered leaderboard hero wording was fixed for guard/center examples.
- The current no-result card baseline was accepted.
- `/visual-qa` route status: implemented locally and in Vercel rewrite config
  with parity to `/review`.

Remaining limitations:

- There is no Playwright screenshot automation or screenshot diffing yet.
- Local route parity was validated, but deployed preview `/visual-qa`
  validation still needs to be done when a preview URL is available.
- Manual screenshots should be refreshed if the 15-case baseline is used as a
  release artifact.

## 8. Validation strategy going forward

- Tier 1: targeted tests plus targeted/adjacent harness runs, `ruff`, and
  `git diff --check`.
- Tier 2: `make test-parser` when parser, entity, date, or routing recognition
  changes.
- Tier 3: `make test-query` when execution behavior, query-service contracts,
  route outputs, or structured API payload semantics change.
- Tier 4: `make test-preflight`, frontend-copy QA, and visual QA at release or
  major checkpoint boundaries.
- Full raw corpus: required before closing any corpus expansion wave or fix
  wave that changes query behavior, product boundaries, or expectations.
- Frontend changes: require the relevant frontend tests and `cd frontend &&
  npm run build` so FastAPI-served assets stay current.

## 9. Recommended next options

Recommended order:

1. Option C - Release-readiness checklist.
2. Option A - Frontend-copy corpus expansion.
3. Option B - Promote one unsupported family into real support.
4. Option D - Harness/tooling efficiency improvements.

### Option A - Frontend-copy corpus expansion

- Why: backend QA now has a clean 243-case corpus, while frontend-copy QA still
  covers a selected 59-case rendered subset.
- Scope: expand by high-risk families first: summary heroes, leaderboards,
  unsupported/no-result cards, playoff history, comparisons, date-window
  summaries, and record-when outputs.
- When to choose: choose this when the next risk is user-facing interpretation
  and copy quality rather than backend route correctness.

### Option B - Promote one unsupported family into real support

- Candidates:
  - opponent-conference filters
  - rookie leaderboards
  - single-team advanced-stat scalar summaries
  - personal-foul leaderboards
  - bench/starter role leaderboards
- Recommended first candidate: opponent-conference filters, because they are a
  common sports-query shape and already have explicit guardrails preventing
  broad full-season fallbacks.
- Required contract work: document dataset source/coverage, route semantics,
  structured result shape, metadata/applied-filter keys, frontend rendering
  needs, no-match behavior, and migration from `expected_unsupported` corpus
  expectations to supported assertions.

### Option C - Release-readiness checklist

- What it would include:
  - deploy preview check
  - `/visual-qa` preview validation
  - smoke query set across supported and unsupported boundaries
  - frontend-copy rerun
  - full raw corpus rerun
  - docs review for current-state accuracy
- When to choose: choose this next if the goal is to ship the current supported
  product boundary without adding new capability.

### Option D - Harness/tooling efficiency improvements

- Wave tags for targeted corpus selection.
- Harness slices by family/category/manual-review tag.
- Run-new-cases-only mode for corpus expansion waves.
- Saved adjacent case groups for fix waves.
- Validation command presets that line up with the tiered strategy above.
- When to choose: choose this when iteration cost starts slowing future corpus
  or fix waves.
