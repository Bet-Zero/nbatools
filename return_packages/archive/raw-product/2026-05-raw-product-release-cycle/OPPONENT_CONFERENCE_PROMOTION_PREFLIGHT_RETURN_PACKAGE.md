# Opponent-Conference Promotion Preflight Return Package

## 1. Executive summary

- Recommended decision: data-contract first; keep opponent-conference filters as
  explicit unsupported behavior until complete trusted conference membership
  metadata exists.
- Main blocker/supporting evidence: `team_record` can already filter by an
  explicit list of opponent abbreviations, but `data/raw/teams/teams_reference.csv`
  has only 2 active rows (`ATL`, `BOS`) and no complete 30-team East/West
  mapping. `team_history_reference.csv` has identity ranges but no conference
  or division fields.
- Promotion ready? no
- Production code changed? no
- Tests changed? no
- Corpus changed? no

The best next step is Option D: add and document a season-aware
team-conference metadata contract, then promote the parser/execution route only
after the metadata validates for the intended seasons.

## 2. Current unsupported cases

| Case ID | Query | Current route/status | Current expected behavior | Notes |
|---|---|---|---|---|
| `celtics_against_east_record_wave4` | `Celtics record against the East this season` | `team_record` / `no_result`; reason `filter_not_supported` | `expected_status: no_result`; `expected_route: team_record`; `expected_reason: filter_not_supported`; `expected_shape: no_result`; no sections; hard assertion `result.metadata.unsupported_filters.0 == opponent_conference` | Raw QA passes. Metadata has `team=BOS`, `season=2025-26`, `unsupported_filters=["opponent_conference"]`. Frontend-copy selected: yes. |
| `lakers_record_against_west_wave5` | `Lakers record against the West` | `team_record` / `no_result`; reason `filter_not_supported` | `expected_status: no_result`; `expected_route: team_record`; `expected_reason: filter_not_supported`; `expected_shape: no_result`; no sections; hard assertion `result.metadata.unsupported_filters.0 == opponent_conference` | Raw QA passes. Metadata has `team=LAL`, `season=2025-26`, `unsupported_filters=["opponent_conference"]`. Frontend-copy selected: yes. |

Both selected frontend-copy cases currently render the explicit unsupported copy:
`Unavailable Filter` with message `Opponent-conference record filters are not
supported yet.`

## 3. Data support

| Data source | Complete? | Seasons covered | Notes |
|---|---|---|---|
| `data/raw/teams/teams_reference.csv` | No | Not season-scoped; current file has only 2 active rows | Columns include `conference` and `division`, but only `ATL` and `BOS` are present, both `East`. This cannot safely compute East/West opponent lists. |
| `data/raw/teams/team_history_reference.csv` | No for conferences | Historical identity ranges only | 54 identity rows with `team_id`, season range, abbreviation, name, city, and franchise label. No `conference` or `division` fields. |
| `data/raw/team_game_stats/{season}_regular_season.csv` | Complete for game/opponent abbreviations | Verified 2024-25 and 2025-26 each have 30 teams, 30 opponent abbreviations, and 2460 team-game rows | Good execution substrate once a conference mapping exists. Does not contain opponent conference labels. |
| `data/raw/standings_snapshots/{season}_regular_season.csv` | Complete for standings rows, not conferences | Verified 2024-25 and 2025-26 each have 30 rows | Contains `conference_rank`, `division_rank`, `games_back`, and records, but no conference label. Inferring conferences from rank ordering would be brittle and is not a documented contract. |
| `src/nbatools/commands/entity_resolution.py` team aliases | Yes for abbreviation normalization | Current active abbreviations plus historical aliases | Useful for normalizing team references, but not a team-conference source. |

Answers to the data questions:

- Complete 30-team current conference mapping: no.
- Covers 2024-25 and 2025-26: no trusted conference mapping covers those
  seasons.
- Historical conference membership needed: yes for unrestricted historical
  phrasing; no only if the product explicitly limits support to current-era
  seasons with documented coverage.
- Current-era mapping enough for current-season and last-season queries: yes in
  principle, but the current repo does not have a complete current-era mapping.
- Team abbreviations normalized consistently: game logs and entity resolution
  use canonical abbreviations consistently enough for execution once a mapping
  exists.
- Opponent lists can be computed safely: not from current trusted data.

## 4. Execution support

| Capability | Exists? | Evidence | Gap |
|---|---|---|---|
| Filter `team_record` by a list of opponents | Yes | `team_record._apply_game_filters` accepts `opponent: str | list[str] | tuple[str, ...]`; `data_utils.build_opponent_mask` uses `.isin(...)`; probe returned BOS 2025-26 vs `ATL/NYK` as 8 games, 3-5. | No resolver from `East`/`West` to a validated opponent list. |
| Preserve season/date/location filters with opponent list | Yes | Probe returned LAL 2024-25 road vs `GSW/LAC` and NYK since `2026-01-01` vs `BOS/CLE`; caveats preserved road/date plus opponent list. | Needs tests for conference-derived lists, not only direct lists. |
| Preserve caveats for opponent filters | Partial | Current caveat says `record filtered to games vs ATL, NYK` or similar. | Promotion should add a clearer conference label instead of exposing only a long 15-team list. |
| Preserve metadata/applied filters for direct opponents | Partial | `query_service._build_applied_filters` exposes `Opponent` when `opponent` is present. | For a list, current value would be a Python list; a promotion needs `metadata.opponent_conference` plus an `Opponent conference` applied filter/chip. |
| Current natural-language guard | Yes for unsupported boundary | Parser sets `route_kwargs.unsupported_filters=["opponent_conference"]`; execution returns `no_result` / `filter_not_supported`. | The parser stores only a boolean `opponent_conference_boundary`, not normalized `East`/`West`. |
| Variant detection | Partial | Current detector catches `against the East`, `vs East teams`, `against Eastern Conference teams`, and `versus Western Conference opponents`. | It also overmatches `east coast teams` because it sees `against east`; support work must tighten this. |

Would this work after a trusted resolver is added?

- `Celtics record against East this season`: yes, as `team_record` with
  `opponent` set to the East list and `opponent_conference=East`.
- `Lakers road record against West last season`: yes, because `away_only`,
  relative season, and opponent-list filtering already compose.
- `Knicks record against Eastern Conference teams since January 1`: yes, because
  date filtering and opponent-list filtering already compose.

## 5. Parser/result contract proposal

This is a proposal for a later implementation after metadata is complete.

- Supported phrases:
  - `against the East`
  - `against East teams`
  - `against Eastern Conference teams`
  - `vs the West`
  - `versus Western Conference teams`
  - `against Western Conference opponents`
- Unsupported phrases:
  - divisions, unless a division membership contract is approved at the same
    quality level
  - historical seasons outside the approved conference membership coverage
  - ambiguous geography such as `east coast teams` or `west coast teams`
  - playoff-round phrases such as `conference finals`, which remain playoff
    round semantics, not opponent-conference filters
- Route: `team_record` for single-team regular-season record summaries.
- Parser slots:
  - `opponent_conference: "East" | "West"`
  - no `unsupported_filters` for supported coverage
  - preserve existing `team`, `season`, `start_date`, `end_date`, `home_only`,
    `away_only`, stat thresholds, and outcome filters
- Execution kwargs:
  - resolve conference membership to `opponent=[...]` only after validating the
    selected season coverage
  - preserve `opponent_conference` separately for metadata/copy
- Metadata:
  - `metadata.opponent_conference: "East" | "West"`
  - `metadata.opponents: [...]` or `metadata.opponent_team_abbrs: [...]`
  - `metadata.applied_filters` includes
    `{"label": "Opponent conference", "value": "East", "kind": "conference"}`
- Sections:
  - same as current `team_record`: `summary` and `by_season`
  - no broad full-season fallback when coverage is missing or the resolved list
    is empty
- Frontend-copy expectations:
  - visible filter/copy should communicate `vs East`, `vs West`, `Eastern
    Conference`, or `Western Conference`
  - supported cases should render normal record summary copy/tables
  - unsupported coverage gaps should still render no-result guidance instead of
    an unfiltered team record

## 6. Implementation options

| Option | Scope | Value | Risk | Recommendation |
|---|---|---|---|---|
| A | Support current-season/current-era opponent-conference filters only | High for common current search-bar queries; low UI novelty because `team_record` already renders summaries | Medium. Requires a complete current-era mapping, explicit season coverage boundaries, and parser tightening | Not ready now. Good follow-up after Option D validates 2024-25 and 2025-26 coverage. |
| B | Support all seasons covered by complete historical team metadata | Highest long-term value and cleanest semantics for historical queries | High. Needs historical conference realignment, franchise/season ranges, validation against all game-log seasons, and fallback behavior | Defer. Do not block current-era support on this unless product wants unrestricted historical phrasing. |
| C | Keep unsupported until team-conference metadata is completed | Safest for release-candidate boundary; prevents broad false records | Low product improvement | Recommended current product state. Existing unsupported expectations should remain. |
| D | Add data contract first, no parser support yet | Builds the prerequisite safely and makes a later promotion straightforward | Low to medium. Requires data-source decision, docs, and validation tests but no behavior change | Recommended next execution item. |

## 7. Recommended execution scope

- Exact goal: add a documented, validated team-conference membership source
  before promoting any query behavior.
- Files likely to change:
  - new data file, preferably `data/raw/teams/team_conference_membership.csv`
    or another explicitly approved reference table with season ranges
  - `docs/reference/data_catalog.md`
  - `docs/reference/data_contracts.md`
  - data validation tests
  - later promotion only: `src/nbatools/commands/_parse_helpers.py`,
    `src/nbatools/commands/natural_query.py`,
    `src/nbatools/commands/_natural_query_execution.py`,
    `src/nbatools/commands/data_utils.py`,
    `src/nbatools/query_service.py`, parser/query-service/UI failure tests,
    raw corpus, frontend-copy corpus, query docs
- Data contract:
  - grain: one row per `team_id` plus effective season range, or one row per
    `season` + `team_id`
  - required fields: `team_id`, `team_abbr`, `conference`, `season_start`,
    `season_end` or `season`, `source`, and `coverage_trusted`
  - expected values: exactly `East` or `West` for supported rows
  - validation: for every supported season, exactly 30 active teams and exactly
    15 teams per conference; every `team_abbr` appears in the relevant
    `team_game_stats` file; no null `conference`; no duplicate team-season rows
  - fallback: if coverage is missing or untrusted for a requested season, return
    `no_result` / `filter_not_supported` or `unsupported_data`, not an
    unfiltered record
- Tests to add:
  - data contract tests for coverage and abbreviation consistency
  - parser tests for accepted East/West phrases and rejected `east coast teams`
  - parser tests proving promoted cases no longer carry
    `unsupported_filters=["opponent_conference"]` within covered seasons
  - execution tests for current season, last season, road/home plus conference,
    and date window plus conference
  - query-service metadata tests for `opponent_conference`, `opponents`, and
    applied filter chips
  - guardrail tests for unsupported/untrusted seasons
- Corpus cases to update/add after support is implemented:
  - flip `celtics_against_east_record_wave4` from unsupported to `ok`
  - flip `lakers_record_against_west_wave5` from unsupported to `ok`
  - add `Celtics record against Eastern Conference teams`
  - add `Lakers road record against West last season`
  - add `Knicks record against Eastern Conference teams since January 1`
  - keep or add an unsupported guard such as `Celtics record against east coast
    teams` or a season outside approved coverage
- Frontend-copy cases to update/add after support is implemented:
  - one supported East record summary
  - one supported West phrase variant
  - one combined context case if selected coverage budget allows
  - one unsupported boundary/coverage case if applicable
- Validation commands:
  - `make test-parser`
  - `make test-query`
  - `make test-api` if `query_service.py` or response metadata changes
  - raw harness target slice for migrated/new opponent-conference cases
  - `cd frontend && npm run qa:frontend-copy` if frontend-copy corpus changes
  - `git diff --check`
- Stop conditions:
  - conference mapping is incomplete, has fewer than 30 teams, or does not
    validate to 15 East and 15 West teams for each supported season
  - requested season is outside trusted coverage
  - parser cannot distinguish conference phrases from geography phrases like
    `east coast teams`
  - implementation would return an unfiltered full-season record on any
    unsupported or missing-coverage path

## 8. If not ready

- Blocking issue: no complete trusted 30-team conference mapping exists in the
  current data contract.
- Required prerequisite: create and validate a season-aware
  team-conference membership dataset, then document coverage and fallback
  behavior before changing parser or execution behavior.
- Product boundary status: keep the current explicit unsupported boundary and
  release-candidate-with-notes status. No current docs need to be weakened.
- Better next promotion candidate if data-contract work is not chosen:
  single-team advanced-stat scalar summaries, because league-wide team advanced
  data already exists and the remaining work is primarily route/result/copy
  contract design rather than missing team membership metadata.

## 9. Validation performed

Files inspected:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md`
- `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md`
- `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `docs/reference/data_catalog.md`
- `docs/reference/data_contracts.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/frontend_copy_corpus.yaml`
- `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`
- `outputs/raw_query_answer_qa/20260517T033806Z/report.md`
- `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`
- `return_packages/raw-product/RAW_QUERY_ANSWER_QA_FIX_WAVE_8D_PRODUCT_BOUNDARY_FINALIZATION_RETURN_PACKAGE.md`
- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/team_record.py`
- `src/nbatools/commands/data_utils.py`
- `src/nbatools/commands/entity_resolution.py`
- `src/nbatools/commands/_natural_query_execution.py`
- `src/nbatools/query_service.py`
- `tests/test_natural_query_parser.py`
- `tests/test_ui_failure_coverage.py`
- `tests/test_query_service.py`
- `data/raw/teams/teams_reference.csv`
- `data/raw/teams/team_history_reference.csv`
- `data/raw/team_game_stats/2024-25_regular_season.csv`
- `data/raw/team_game_stats/2025-26_regular_season.csv`
- `data/raw/standings_snapshots/2024-25_regular_season.csv`
- `data/raw/standings_snapshots/2025-26_regular_season.csv`

Commands/probes run:

- `rg` searches for opponent-conference references across docs, corpus, outputs,
  source, and tests.
- `sed` reads of the release package, readiness checklist, findings, query docs,
  data docs, source modules, tests, and report excerpts.
- YAML/JSONL probe to extract opponent-conference raw corpus cases and latest
  report metadata.
- Data probe:
  - `teams_reference rows 2`
  - `active rows 2`
  - `conferences {'East': 2}`
  - 2024-25 team-game stats: 2460 rows, 30 teams, 30 opponents, 0 missing
    opponent abbreviations
  - 2025-26 team-game stats: 2460 rows, 30 teams, 30 opponents, 0 missing
    opponent abbreviations
  - 2024-25 and 2025-26 standings snapshots: 30 rows each, no conference column
- Execution probe with direct opponent lists:
  - BOS 2025-26 vs `ATL/NYK`: 8 games, 3-5
  - LAL 2024-25 road vs `GSW/LAC`: 4 games, 3-1
  - NYK since `2026-01-01` vs `BOS/CLE`: 3 games, 2-1
- Parser probe for phrase variants:
  - `Celtics record against Eastern Conference teams`
  - `Lakers record against Western Conference teams`
  - `Celtics record vs East teams`
  - `Lakers record versus Western Conference opponents`
  - `Celtics record against east coast teams`

Validation after creating this return package:

- `git diff --check`: passed
- Trailing-whitespace scan for this return package: passed with no matches
