# Raw Product Release Package Return Package

## 1. Executive summary

- What changed: created the final Raw Product release package and updated the
  existing readiness/checkpoint/harness/index docs to point at it.
- Production code changed? no
- Tests changed? no
- Corpus changed? no
- Release package doc:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- Recommended release status: `RELEASE_CANDIDATE_WITH_NOTES`
- Latest backend QA:
  `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`; 243/243
  expectation cases passing.
- Latest frontend-copy QA:
  `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`; 125/125
  selected cases rendered with soft checks `475/0/0`.
- Latest preview QA:
  `PREVIEW_READY_WITH_NOTES` from
  `return_packages/raw-product/RAW_PRODUCT_PREVIEW_MANUAL_QA_RERUN_RETURN_PACKAGE.md`.
- Recommended next step: unsupported-family promotion preflight.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | Added | Final release package for the current supported and explicitly unsupported Raw Product boundary. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | Updated | Points to the release package, updates status to `RELEASE_CANDIDATE_WITH_NOTES`, and records the latest preview rerun as `PREVIEW_READY_WITH_NOTES`. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | Updated | Points to the release package, latest 125-case frontend-copy status, latest preview status, and next roadmap options. |
| `docs/planning/raw-product/RAW_QUERY_ANSWER_QA_HARNESS_PLAN.md` | Updated | Adds the current release package status, latest QA artifacts, and next roadmap options. |
| `docs/index.md` | Updated | Adds the new release package to the planning index. |
| `return_packages/raw-product/RAW_PRODUCT_RELEASE_PACKAGE_RETURN_PACKAGE.md` | Added | Captures scope, validation, files changed, and next recommendation for this docs-only pass. |

## 3. Release package summary

| Area | Status | Evidence |
|---|---|---|
| Backend Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T033806Z/report.jsonl`; 243 cases; failed IDs none; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T054758Z/frontend_copy_report.md`; 125 rendered; failures 0; soft checks `475/0/0`. |
| Visual QA | `ACCEPTED_WITH_MANUAL_LIMITATION` | 15-case manual baseline plus preview mobile blocker rerun evidence. |
| Preview QA | `PREVIEW_READY_WITH_NOTES` | `/`, `/review`, `/visual-qa`, six smoke queries, and five mobile blocker cases passed. |
| Supported boundary | `DOCUMENTED` | New release package groups supported player/team summaries, records, leaderboards, top performances, finders/counts, streaks, stretches, splits, playoff history, comparisons, date/window filters, and defensive aliases. |
| Unsupported boundary | `DOCUMENTED_AND_GUARDED` | New release package lists the explicit unsupported families, expected behavior, reason, and future support path. |
| Known limitations | `DOCUMENTED` | Selected frontend-copy coverage, manual visual QA, preview notes, guarded unsupported surfaces, and existing frontend warnings are recorded. |

## 4. Current product boundary

Supported families:

- Player summaries, team records, record-when conditions, no-player/without-player
  conditions.
- Player, team, and team advanced leaderboards.
- Top performances, finder/count outputs, streaks, rolling stretches, and
  splits.
- Playoff history, playoff matchup history, playoff round/appearance
  leaderboards, and comparisons.
- Date/window filters and defensive/opponent-points aliases.

Unsupported families:

- Personal-foul leaderboards.
- Single-team advanced-stat scalar summaries.
- Rookie leaderboards.
- League-wide starter/bench leaderboards.
- Team bench scoring.
- Opponent-conference filters.
- Single-team playoff round records.
- Subjective/trend queries such as clutch/cooled off.
- Multi-player availability.
- Lineup summaries/leaderboards where trusted coverage is unavailable.
- On/off surfaces where trusted data is unavailable.
- Team rolling-stretch leaderboards.
- Minutes leaderboards.
- Team single-game threes.

Future support candidates:

- Opponent-conference filters.
- Single-team advanced-stat scalar summaries.
- Rookie leaderboards.
- Personal-foul leaderboards.
- Bench/starter role leaderboards.
- Lineup/on-off support only after source coverage and result contracts are
  approved.

## 5. Validation

- `git diff --check`: passed for tracked doc edits.
- New-file trailing-whitespace scan: passed with no matches for the new release
  package and return package files.
- Markdown lint: not run; `markdownlint` and `markdownlint-cli2` were not
  available in the environment.

## 6. Next recommendation

Choose: unsupported-family promotion preflight.

Start with one explicit unsupported family, document the source/data contract
and result contract, then migrate the relevant boundary corpus cases from
expected unsupported behavior into execution-backed support.
