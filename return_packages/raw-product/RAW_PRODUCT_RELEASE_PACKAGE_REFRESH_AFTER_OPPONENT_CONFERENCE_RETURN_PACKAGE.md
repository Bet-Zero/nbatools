# Raw Product Release Package Refresh After Opponent-Conference Promotion Return Package

## 1. Executive summary

- What changed: refreshed the Raw Product release package, readiness/checkpoint
  docs, harness plan status, and findings inventory after opponent-conference
  team-record filters were promoted.
- Production code changed? no
- Tests changed? no
- Corpus changed? no
- Release package updated: yes,
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- Current release status: `RELEASE_CANDIDATE_WITH_NOTES`
- Latest backend QA:
  `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246/246
  expectation cases passed; suspicious flags 0.
- Latest frontend-copy QA:
  `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125
  selected cases rendered; soft checks `480/0/0`.
- Supported boundary update: current-era East/West opponent-conference
  `team_record` filters are supported for trusted seasons `2024-25` and
  `2025-26`.
- Recommended next step: preview smoke rerun for opponent-conference support.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | release package refresh | Records supported opponent-conference boundary, narrower unsupported boundaries, latest QA artifacts, promotion package, and validation counts. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | readiness refresh | Adds opponent-conference support status, latest frontend-copy source, data/parser/query validation summaries, and updated unsupported guardrails. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | checkpoint refresh | Updates supported coverage map, recent fix-wave summary, validation counts, and remaining unsupported boundary wording. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | harness status refresh | Points current status at the 246-case raw QA run, refreshed frontend-copy report, promotion package, and latest validation summaries. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_FINDINGS.md` | findings refresh | Moves AQ-023 to supported for trusted seasons and updates frontend-copy findings to the latest 125-case run. |
| `return_packages/raw-product/RAW_PRODUCT_RELEASE_PACKAGE_REFRESH_AFTER_OPPONENT_CONFERENCE_RETURN_PACKAGE.md` | return package | Captures this docs-only release-package refresh. |

## 3. Boundary update summary

| Area | Previous status | Current status | Notes |
|---|---|---|---|
| Opponent-conference filters | Expected unsupported/no-result or no broad fallback. | Supported for `team_record` in trusted seasons `2024-25` and `2025-26`. | Resolves East/West opponent lists from `data/raw/teams/team_conference_membership.csv`. |
| Missing/untrusted conference coverage | Unsupported/no-result. | Unsupported/no-result. | Returns `conference_coverage` instead of a broad full-season record. |
| Geography phrases | Unsupported/no-result. | Unsupported/no-result. | Phrases such as `east coast teams` and `west coast teams` stay outside the conference contract. |
| Divisions | Unsupported/no-result. | Unsupported/no-result. | Division values exist in the data contract for future use but are not promoted. |
| Conference Finals phrasing | Playoff-round boundary. | Playoff-round boundary. | `conference finals` remains single-team playoff-round phrasing, not opponent-conference filtering. |

## 4. QA artifact refresh

| Artifact | Previous | Current |
|---|---|---|
| Raw QA report | `outputs/raw_query_answer_qa/20260517T033806Z/report.md` / 243 cases | `outputs/raw_query_answer_qa/20260517T070422Z/report.md` / 246 cases |
| Raw corpus size | 243 | 246 |
| Frontend-copy report | `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md` |
| Promotion return package | none | `return_packages/raw-product/OPPONENT_CONFERENCE_PROMOTION_RETURN_PACKAGE.md` |
| Data validation | 14 passed in the data-contract setup package | 15 passed for `tests/test_team_conference_membership_data.py` |
| Parser validation | 747 passed in the prior readiness block | 751 passed with `make PYTEST=.venv/bin/pytest test-parser` |
| Query validation | not listed in the release package | 752 passed with `make PYTEST=.venv/bin/pytest test-query` |

## 5. Validation

- `git diff --check`: passed.
- Markdown lint: not run.

## 6. Next recommendation

Preview smoke rerun for opponent-conference support.
