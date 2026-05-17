# Opponent-Conference Promotion Return Package

## 1. Executive summary

- What changed: promoted current-era East/West opponent-conference filters for `team_record` queries using `data/raw/teams/team_conference_membership.csv`.
- Production behavior changed? yes
- Parser behavior changed? yes
- Corpus changed: yes; 2 unsupported cases migrated to supported and 3 raw cases added.
- Frontend-copy changed: yes; the 2 selected opponent-conference cases now expect supported record copy.
- Supported seasons: `2024-25`, `2025-26`
- Latest raw QA run: `outputs/raw_query_answer_qa/20260517T070422Z/report.md`
- Latest frontend-copy run: `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- Remaining risk: support is intentionally limited to trusted current-era conference coverage; historical seasons, divisions, and geography phrases remain unsupported.

## 2. Supported contract

- Supported phrases: `against the East`, `against East teams`, `against Eastern Conference teams`, `vs the West`, `vs West teams`, `versus Western Conference teams`, `against Western Conference opponents`.
- Supported seasons: `2024-25`, `2025-26`.
- Unsupported phrases: `east coast teams`, `west coast teams`, divisions, `conference finals`, `Eastern Conference Finals`, `Western Conference Finals`.
- Missing coverage behavior: returns `no_result` / `filter_not_supported` with `unsupported_filters=["conference_coverage"]`; it does not execute a broad full-season team record.
- Metadata/applied filters: `metadata.opponent_conference` exposes `East` or `West`; `metadata.opponent_team_abbrs` exposes the resolved 15-team list; applied filters include `Opponent conference`.
- Subject-team handling: the resolved list keeps all 15 conference members, including the subject team when applicable; this has no effect because teams do not play themselves.

## 3. Data resolution

| Season | Conference | Teams resolved | Trusted? |
|---|---|---:|---|
| `2024-25` | East | 15 | yes |
| `2024-25` | West | 15 | yes |
| `2025-26` | East | 15 | yes |
| `2025-26` | West | 15 | yes |

## 4. Target behavior before/after

### celtics_against_east_record_wave4

- Before: `team_record` / `no_result` with `unsupported_filters=["opponent_conference"]`.
- After: `team_record` / `ok`, `team=BOS`, `opponent_conference=East`, 52 games, 36 wins, 16 losses.

### lakers_record_against_west_wave5

- Before: `team_record` / `no_result` with `unsupported_filters=["opponent_conference"]`.
- After: `team_record` / `ok`, `team=LAL`, `opponent_conference=West`, 52 games, 33 wins, 19 losses.

## 5. New/updated cases

| Case ID | Query | Expected behavior | Notes |
|---|---|---|---|
| `celtics_against_east_record_wave4` | `Celtics record against the East this season` | Supported `team_record` | Migrated from unsupported. |
| `lakers_record_against_west_wave5` | `Lakers record against the West` | Supported `team_record` | Migrated from unsupported. |
| `lakers_road_record_against_west_last_season` | `Lakers road record against West last season` | Supported `team_record` | Conference + road + relative season. |
| `knicks_record_against_east_since_january_1` | `Knicks record against Eastern Conference teams since January 1` | Supported `team_record` | Conference + date window. |
| `celtics_against_east_coast_teams_guard` | `Celtics record against east coast teams` | Unsupported/no-result | Geography guard; no broad fallback. |

## 6. Tests and validation

- Data tests: `.venv/bin/pytest tests/test_team_conference_membership_data.py -q` -> 15 passed.
- Parser tests: `make PYTEST=.venv/bin/pytest test-parser` -> 751 passed.
- Targeted raw QA: `outputs/raw_query_answer_qa/20260517T070340Z`; 5 cases, all expectations passed.
- Product-boundaries slice: `outputs/raw_query_answer_qa/20260517T070358Z`; 11 cases, all expectations passed.
- Full raw QA: `outputs/raw_query_answer_qa/20260517T070422Z`; 246 cases, all expectations passed, 0 suspicious flags.
- Frontend-copy QA: `cd frontend && npm run qa:frontend-copy` -> 4 tests passed; report `outputs/frontend_copy_qa/20260517T071053Z`.
- Frontend build: `cd frontend && npm run build` passed with the existing Vite large-chunk warning.
- Ruff: `.venv/bin/ruff check <changed_python_files_and_tests>` -> passed.
- `test-query`: bare `make test-query` failed before execution because `pytest` was not on PATH; `make PYTEST=.venv/bin/pytest test-query` passed 752 tests.
- `git diff --check`: passed.

## 7. Files changed

| File | Change type | Why |
|---|---|---|
| `src/nbatools/commands/_parse_helpers.py` | parser | Extract normalized `East`/`West`; guard east/west coast geography. |
| `src/nbatools/commands/natural_query.py` | parser/routing | Route supported team-record opponent-conference filters and preserve geography unsupported behavior. |
| `src/nbatools/commands/_natural_query_execution.py` | execution | Resolve conference to trusted 15-team opponent lists; block missing coverage. |
| `src/nbatools/commands/data_utils.py` | data helper | Add trusted-coverage validation option to `get_teams_by_conference`. |
| `src/nbatools/commands/team_record.py` | typing | Reflect list opponent support in the public signature. |
| `src/nbatools/query_service.py` | metadata | Expose `opponent_conference`, resolved team list, and applied filter chip. |
| `tests/*` | tests | Parser, data, query-service, and UI no-result/support coverage. |
| `qa/raw_query_answer_corpus.yaml` | corpus | Migrate 2 cases and add 3 cases. |
| `qa/frontend_copy_corpus.yaml` | frontend-copy corpus | Migrate selected supported-copy expectations and source latest raw run. |
| `frontend/src/test/frontendCopyQaReport.test.tsx` | test | Update expected frontend-copy source run path. |
| `docs/reference/*` | docs | Document supported query/data contract boundary. |
| `docs/planning/raw-product/*` | planning docs | Refresh release/readiness/finding status and artifact paths. |

## 8. Current product boundary update

- Opponent-conference current-era filters: supported for `team_record` in trusted seasons `2024-25` and `2025-26`.
- Still unsupported: seasons outside trusted coverage, divisions, geography phrases like `east coast teams`, and playoff round phrases such as `conference finals`.
- Future support path: add trusted historical conference membership or a separate division/geography contract before expanding beyond current-era East/West support.

## 9. Next recommendation

Release package refresh. The support boundary, corpus, frontend-copy source run, and readiness docs changed, so a release-package refresh is the next highest-signal follow-up.
