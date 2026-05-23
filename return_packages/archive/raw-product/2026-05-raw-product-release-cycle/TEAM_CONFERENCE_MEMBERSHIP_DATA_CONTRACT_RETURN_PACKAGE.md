# Team Conference Membership Data Contract Return Package

## 1. Executive summary

- What changed: Added a season-aware team-conference membership data contract,
  a data-layer loader/helper, focused validation tests, and docs/planning
  updates.
- Production query behavior changed? no
- Parser behavior changed? no
- Corpus expectations changed? no
- Data file added: `data/raw/teams/team_conference_membership.csv`
- Seasons covered: `2024-25`, `2025-26`
- Validation status: passed
- Remaining promotion blocker: opponent-conference parser/execution promotion,
  metadata/copy behavior, and raw/frontend-copy corpus migration remain future
  work.

## 2. Data contract

| Field | Meaning | Required? | Notes |
|---|---|---|---|
| `season` | NBA season label | yes | Current trusted coverage: `2024-25`, `2025-26`. |
| `team_abbr` | Canonical team abbreviation for that season | yes | Unique with `season`; must match `team_game_stats`. |
| `team_id` | Stable NBA team id | yes for current rows | Validated against `team_game_stats` team identity. |
| `conference` | Team conference | yes | Exactly `East` or `West`. |
| `division` | Team division | yes for current rows | Included for future division support; current rows validate to five teams per division. |
| `source` | Source decision for the row | yes | Current value is manually curated: `manual_current_nba_alignment_2026-05-17`. |
| `coverage_trusted` | Whether the row can be used by future coverage-gated execution | yes | Stable boolean/0-1 value; current rows are trusted. |

## 3. Coverage summary

| Season | Teams | East | West | Trusted? |
|---|---:|---:|---:|---|
| `2024-25` | 30 | 15 | 15 | yes |
| `2025-26` | 30 | 15 | 15 | yes |

## 4. Validation rules

- Required columns exist: passed.
- No duplicate `season` + `team_abbr` rows: passed.
- No null conference values: passed.
- Conference values are only `East` or `West`: passed.
- Each trusted season has exactly 30 teams: passed.
- Each trusted season has exactly 15 East teams: passed.
- Each trusted season has exactly 15 West teams: passed.
- Every trusted `team_abbr` exists in the matching `team_game_stats` file:
  passed.
- Every `team_game_stats` team abbreviation has a trusted membership row:
  passed.
- `team_id` values match `team_game_stats` identities: passed.
- Division values are non-empty and validate to five teams per division:
  passed.

## 5. Files changed

| File | Change type | Why |
|---|---|---|
| `.gitignore` | updated | Keeps local data ignored by default while allowing the small membership contract CSV to be versioned. |
| `data/raw/teams/team_conference_membership.csv` | added | New manually curated season-aware conference membership table. |
| `src/nbatools/commands/data_utils.py` | updated | Added minimal data-layer loading and lookup helpers; no query wiring. |
| `tests/test_team_conference_membership_data.py` | added | Validates the data contract and helper behavior against 2024-25 and 2025-26 data. |
| `docs/reference/data_catalog.md` | updated | Documents the new file, grain, coverage, source, validation rules, and fallback principle. |
| `docs/reference/data_contracts.md` | updated | Adds the formal dataset contract and future-use boundary. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | updated | Records that opponent-conference remains unsupported while the data prerequisite now exists. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | updated | Records that AQ-023 remains expected unsupported and parser/execution promotion is future work. |

## 6. Tests / validation

Data validation tests:

```text
$ .venv/bin/pytest tests/test_team_conference_membership_data.py -q
bringing up nodes...
bringing up nodes...

..............                                                           [100%]
14 passed in 4.01s
```

Ruff:

```text
$ .venv/bin/ruff check src/nbatools/commands/data_utils.py tests/test_team_conference_membership_data.py
All checks passed!
```

Git diff whitespace check:

```text
$ git diff --check
```

No output; no whitespace errors reported.

Optional probe counts:

```text
$ .venv/bin/python -c "import pandas as pd; df=pd.read_csv('data/raw/teams/team_conference_membership.csv'); trusted=df[df['coverage_trusted'].astype(str).str.lower().isin(['true','1'])]; [print(f'{season} {conference} count = {len(trusted[(trusted.season==season)&(trusted.conference==conference)])}') for season in ['2024-25','2025-26'] for conference in ['East','West']]"
2024-25 East count = 15
2024-25 West count = 15
2025-26 East count = 15
2025-26 West count = 15
```

## 7. Current product behavior

- Opponent-conference filters remain unsupported.
- Existing unsupported corpus cases remain unchanged.
- No user-facing support was added.

## 8. Next recommendation

Preflight or execute opponent-conference parser/execution promotion now that
the current-era data contract validates. Stop promotion if future expansion
uncovers missing or untrusted coverage; missing coverage must remain
unsupported/no-result rather than falling back to a broad full-season record.
