# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog:
https://keepachangelog.com/en/1.0.0/

---

## [Unreleased]

### Fixed

- A player's name now reaches that player instead of one whose alias it
  contains. "karl anthony towns" answered with Carmelo Anthony, and
  "Tim Hardaway Jr" / "Jaren Jackson Jr" without the period answered with the
  father; names now match regardless of hyphens and suffix or initial periods.
  Curated full names such as Karl-Anthony Towns now win over the shorter alias
  inside them even when the loaded data does not cover that player. Names typed with
  their diacritics no longer break comparisons ("Luka Dončić vs Nikola Jokić
  last 10 games" lost its second player), and "X vs Y 2025-26" no longer reads
  the season as a misspelled name.
- Removed `.github/workflows/data-backed-validation.yml`, which duplicated the
  pre-existing `r2-real-data-validation.yml` against repository secrets that
  were never created. The R2 credential is held as secrets on the
  `r2-validation` GitHub Environment deliberately, so that ordinary CI stays
  secret-free and the values reach only the one job that names that environment.
  The duplicate failed on every run and the failures were read as a credential
  problem rather than as a second workflow looking in the wrong place.
- The data-backed validation path no longer reads `toJSON(secrets)`. Doing so got
  every run held for manual approval with zero jobs created, so nothing it
  reported could be read.

### Changed

- `r2-real-data-validation.yml` now runs its gates as parallel jobs behind a
  `preflight` that verifies the credential once and pins a single immutable
  generation for all of them. Run 1 proved the need: as sequential steps the Raw
  QA corpus took 42m30s of a 45-minute budget, so the filter execution sweep was
  cancelled at pair 54 of 521 and the data-backed tests never ran. Sequencing
  also buried the sweep behind 43 minutes of Raw QA; in parallel it reports in
  under ten minutes.

### Added

- `tests/test_r2_validation_workflow_policy.py` — governance for the one
  workflow that reads the R2 credential: it must declare
  `environment: r2-validation` (omitting it makes every secret empty and the
  failure look like missing data), it must stay the only workflow referencing
  those secrets, its secret-to-variable mapping cannot drift from the engine's
  `REQUIRED_R2_ENV_VARS`, both validation gates must stay enforced, evidence must
  upload on failure, and its credential check cannot print a value. Verified
  against ten simulated regressions, including both faults that actually
  occurred.
- `r2-real-data-validation.yml` now also runs the `needs_data` suite against the
  pinned generation, informationally — roughly 1000 tests that had never run
  anywhere automated.

---

## [0.8.0] - 2026-09-27

The first release cut since the `0.7.0` initial structure. Counts are taken
from the generated
[repository inventory](contracts/repository_inventory.json) and the
[public HTTP route contract](contracts/public_http_routes.json), both of which
CI checks for drift.

### Added

**Web application and HTTP layer**

- FastAPI service exposing seven public routes — `GET /health`, `/freshness`,
  `/readiness`, `/routes` and `POST /query`, `/structured-query`,
  `/query-feedback` — with per-route request-size admission control
- React + TypeScript + Vite frontend (165 source files) served from the same
  service, consuming the shared `QueryResponse` envelope
- Result-pattern renderer with a route-to-pattern registry, shared display
  primitives, freshness panel, query history and saved queries
- Cloudflare R2 deployment path: immutable data generations, atomic
  publication, an active-generation pointer, and a schedule-aware readiness
  gate

**Query surface**

- 30 structured routes spanning player and team summaries, finders,
  leaderboards, comparisons, splits, streaks, occurrence counts, rolling
  stretches, playoff history, matchup history and decade records
- 8 structured result types and 8 result reasons as the shared output contract
- Context filters — clutch, quarter, half, starter/bench role, back-to-back,
  rest days, one-possession games, nationally televised — execution-backed on
  the route families that can apply them
- Opponent filters — conference, division, quality — and availability filters
  for whole-game teammate presence and absence
- 21 documented dataset specifications with lifecycle layer, grain, join keys
  and trust/coverage semantics

**Validation and evidence**

- Raw QA corpus harness: 361 curated cases, 16 registered acceptance families,
  8 named slice selectors, and a generated product-review artifact
- Filter execution sweep, comparing each filtered question against its
  unfiltered control to detect filters that are displayed but never applied
- Parser examples full sweep over the documented example set
- Exploratory query review for input-only phrasing snapshots
- Frontend copy QA, visual QA screenshot capture, and a browser release review
  with accessibility checks
- Generated repository inventory with a CI drift check, plus a durable-doc
  governance check
- Policy-bound production monitoring on a two-hour schedule, with latency
  thresholds and a bounded retry rule

### Changed

- CI split into independent verdicts: `lint`, `docs-governance`,
  `frontend-verify`, `frontend-security`, `test-fast` (Python 3.11/3.12/3.13)
  and `test-full`, so a dependency advisory can no longer mark code
  verification skipped
- Raw QA and the filter execution sweep now fail closed: the named Make target
  fails on expectation failures, and a sweep with no comparable rows reports
  `NO_SIGNAL` instead of false success
- Test suite grown to 4413 collected tests

### Fixed

**Trust boundaries — answers that were confident and wrong**

- Ranking questions must name their metric. `best NBA teams this season` no
  longer returns a points-per-game leaderboard, `rookie leaders` no longer
  ranks by an unrequested metric, and requested aggregation wording is no
  longer discarded (`total points leaders` and `minutes per game leaders` now
  answer what was asked or refuse)
- A fragment naming only a context — `Williams clutch stats`,
  `stats against winning teams` — no longer falls back to a league-wide points
  leaderboard badged with the requested filter
- Filters the selected route cannot execute are refused rather than displayed
  as applied over an unfiltered answer
- A trailing question mark no longer flips the subject of a team query
  (`Lakers record against the Celtics?` was answering for Boston)
- Unique first names resolve automatically, so common single-name queries no
  longer need hand-listing
- Unanswerable shapes — championships and "rings", future schedule, awards —
  refuse instead of returning a nearest-match answer
- No silent season substitution: a season with no data is refused or caveated
  rather than answered with a different year
- Compound questions are executed whole or refused. A question naming several
  things at once — a threshold, an event condition and a ranking intent — can no
  longer have part of itself dropped on the way to an answer.
  `teams with most games scoring 120+ and making 15+ threes since 2020` returned
  a three-pointers-per-game leaderboard; it now counts the games matching both
  conditions. A game-level condition is only accepted by a route that can apply
  one, so "15+ threes" can no longer become a filter on a season average
- `was` is no longer read as Washington when it is an ordinary English verb, so
  `most 40-point games while the player was injured` stopped answering about the
  Wizards. `was record this season` still resolves the Wizards
- `while X was out` reads as the same absence as `when X was out`, so
  `Lakers leading scorer while LeBron was out` no longer switches its subject to
  LeBron
- Injury and other unmodelled conditions are recognised only so they can be
  refused by name; nothing infers them from missed games or any other proxy

**Operations**

- The blocking dependency-security gate is scoped to dependencies that ship to a
  browser. Development-only advisories are reported by a separate non-blocking
  job instead of holding CI red for weeks at a time
- Production monitor targets the stable production alias rather than a
  disposable per-deployment host
- Development-only dependency advisories remediated by lockfile-only updates
  (`brace-expansion`, `@humanfs/node`, `@vitest/mocker`)

### Known limitations

- Clutch datasets, a curated champions reference table, and team bench-scoring
  aggregation are not built; queries that need them refuse honestly
- 1036 of 4413 tests require the local NBA dataset and are skipped wherever it
  is absent, including CI

---

## [0.7.0] - 2026-04-09

### Added
- Grouped boolean query support using:
  - `and`
  - `or`
  - parentheses `(...)`
- Support for grouped boolean logic across:
  - Player game finder
  - Team game finder
  - Player game summary
  - Team game summary
  - Player split summary (home/away, wins/losses)
  - Team split summary (home/away, wins/losses)
- Full boolean expression parsing with:
  - Nested conditions
  - Operator precedence
  - Tree-based evaluation (`AndNode`, `OrNode`, `ConditionNode`)
- New module:
  - `query_boolean_parser.py`
- Sample-aware advanced metrics (v2):
  - USG%
  - AST%
  - REB%
  - Correctly recomputed from filtered game samples
- Safe dataframe injection pattern:
  - Commands accept `df` overrides for filtered subsets
- JSON export support for all commands

### Changed
- Advanced metrics upgraded from season averages → sample-aware recomputation
- Natural query engine now routes grouped boolean queries through:
  - Base dataset loaders
  - Boolean evaluation tree
  - Filtered dataframe execution
- Split summary commands updated to support injected filtered datasets
- Output consistency improved across:
  - summaries
  - splits
  - comparisons

### Fixed
- Incorrect advanced metric values when filtering subsets (USG%, AST%, REB%)
- Boolean queries returning empty results due to missing base dataset loading
- Split summaries incorrectly applying filters twice
- Edge cases in OR query merging and deduplication

### Tests
- Added grouped boolean smoke tests for:
  - Player summary
  - Player split summary
  - Team summary
  - Team split summary
- Added formula tests for advanced metrics v2
- Added boolean parser unit tests
- Test suite expanded to 125 passing tests

---

## [0.6.0] - 2026-04-08

### Added
- Boolean query parsing (`and`, `or`)
- OR query merging for finder queries
- Initial grouped boolean support (finder only)
- Natural language parsing improvements

---

## [0.5.0]

### Added
- Natural query CLI (`nbatools-cli ask`)
- Player comparisons
- Team comparisons
- Split summaries (home/away, wins/losses)

---

## [0.4.0]

### Added
- Advanced metrics v1 (USG%, TS%, eFG%)

---

## [0.3.0]

### Added
- Player and team summaries
- Finder commands
- CLI test harness

---

## [0.2.0]

### Added
- Core CLI structure
- Data loading pipelines

---

## [0.1.0]

### Initial release
