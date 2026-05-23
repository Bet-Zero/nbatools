# Raw Product Release Candidate Handoff Return Package

## 1. Executive summary

- What changed: created the final Raw Product release-candidate handoff and
  updated the planning/index docs to point at it as the current handoff-complete
  state.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.
- Handoff doc:
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`.
- Release status: `RELEASE_CANDIDATE_WITH_NOTES`.
- Preview status: `PREVIEW_READY_WITH_NOTES`.
- Recommended next step: pause/ship current release candidate.

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | new handoff doc | Consolidate final release-candidate status, validation evidence, product boundary, deployment/data notes, known limitations, final checklist, and next roadmap. |
| `docs/index.md` | index update | Add the final handoff doc to the active Raw Product planning references and mark the current state as handoff complete with notes. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | release package update | Point to the handoff doc, mark handoff complete, and shift next roadmap ordering to post-handoff work. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_READINESS_CHECKLIST.md` | checklist update | Point to the handoff doc and mark final handoff complete with notes. |
| `docs/planning/raw-product/RAW_PRODUCT_QA_RELEASE_READINESS_CHECKPOINT.md` | checkpoint update | Point to the handoff doc, mark Option G complete, and reorder next options after handoff. |
| `return_packages/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF_RETURN_PACKAGE.md` | new return package | Summarize this docs-only handoff work and validation. |

## 3. Handoff summary

| Area | Status | Evidence |
|---|---|---|
| Raw QA | `PASS` | `outputs/raw_query_answer_qa/20260517T070422Z/report.md`; 246/246 passing; suspicious flags 0. |
| Frontend-copy QA | `PASS` | `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`; 125/125 selected cases rendered; soft checks `480/0/0`. |
| Preview smoke | `PASS_WITH_NOTES` | `return_packages/raw-product/OPPONENT_CONFERENCE_PREVIEW_R2_SYNC_FIX_RETURN_PACKAGE.md`; supported opponent-conference checks and guardrails passed. |
| R2 data availability | `PASS` | `raw/teams/team_conference_membership.csv` verified in R2 by dry-run, sync, and `head_object`. |
| Deployment smoke | `PASS` | `outputs/deployment_smoke/opponent_conference_r2_sync_fix_preview.json`; `ok: true`, `failure_count: 0`. |
| Visual QA | `PASS_WITH_MANUAL_LIMITATION` | Latest preview `/visual-qa` loaded 15/15 cases with request errors 0; manual baseline only. |
| Handoff | `COMPLETE_WITH_NOTES` | `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`. |

## 4. Current boundary

- Supported: player summaries, team records, record-when conditions,
  without-player conditions, leaderboards, team advanced leaderboards, top
  performances, finder/count outputs, streaks, rolling stretches, splits,
  playoff history, playoff matchup history, playoff round/appearance
  leaderboards, comparisons, date/window filters, defensive/opponent-points
  aliases, and opponent-conference team-record filters for trusted seasons
  `2024-25` and `2025-26`.
- Unsupported: personal-foul leaderboards, single-team advanced-stat scalar
  summaries, rookie leaderboards, league-wide starter/bench leaderboards, team
  bench scoring, single-team playoff round records, subjective/trend queries,
  lineup or on/off surfaces without trusted coverage, team rolling-stretch
  leaderboards, minutes leaderboards, team single-game threes, divisions,
  geography phrases, and historical opponent-conference coverage outside
  trusted seasons.
- Known limitations: frontend-copy QA is selected coverage, visual QA is
  manual, opponent-conference support is trusted-season limited, existing
  frontend build/lint warnings remain non-blocking, and external NBA CDN
  image/logo request failures may occur unless they affect primary UX.

## 5. Final checklist

- Included? yes.
- Any unresolved blockers: no current release blockers. Known release notes
  remain selected frontend-copy coverage, manual visual QA, trusted-season
  opponent-conference limits, guarded unsupported boundaries, existing
  frontend build/lint warnings, and required R2 data as a future release
  blocker if missing.

## 6. Validation

- `git diff --check`: pass.
- Markdown lint: not run; `markdownlint` and `markdownlint-cli2` were not
  available on PATH.

## 7. Next recommendation

Pause/ship current release candidate.
