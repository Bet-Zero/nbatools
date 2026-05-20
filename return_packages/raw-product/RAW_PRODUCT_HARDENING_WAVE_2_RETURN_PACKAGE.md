# Raw Product Hardening — Wave 2 Return Package

## 1. Executive summary

- Wave executed: Wave 2 — Data/R2 Promotion Checklist Hardening, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5.
- What was produced:
  - A new "Data-backed Feature Promotion Checklist" section in
    `docs/operations/deployment.md` covering: required runtime data key
    list rule, R2 sync verification rule with `head_object` evidence,
    deployment smoke rule, missing-data clean `no_data` / `unsupported`
    behavior rule, no broad fallback rule, and the
    `raw/teams/team_conference_membership.csv` worked example.
  - Cross-link tighten-up in
    `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`: four
    placeholder "Wave 2 will land later" references replaced with concrete
    pointers to the new section.
- Scope: docs/policy only. No production code, parser, routing, backend,
  frontend, test, or corpus changes. No deployment scripts, R2 sync code, or
  smoke harness changes.
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- Next wave: Wave 3 — Feedback Review Cadence (target file
  `docs/operations/query_feedback_review.md`).

## 2. Files changed

| File | Change type | Why |
|---|---|---|
| `docs/operations/deployment.md` | Updated runbook | Added the "Data-backed Feature Promotion Checklist" section between "Deployment Smoke Monitoring" and "Custom-Domain Closure Checklist". Section covers required key list rule, R2 sync verification with `head_object` evidence, deployment smoke rule, missing-data clean unsupported behavior rule, no broad fallback rule, and the opponent-conference worked example. |
| `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` | Updated cross-links | Replaced four placeholder Wave-2-pending references with concrete pointers to the new deployment.md section. Targets: §3.2 preflight bullet, §3.8 stage close-out, §5.8 worked-example close-out, and §8 "How this doc is used" bullet. |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_2_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, validation result for Wave 2. |

No other files were created, modified, moved, or deleted.

## 3. What changed (substantive content)

### 3.1 docs/operations/deployment.md — new section

New top-level section: **Data-backed Feature Promotion Checklist**. Placed
between the existing "Deployment Smoke Monitoring" section and the existing
"Custom-Domain Closure Checklist" section. The section structure:

- Intro paragraph — names this as the deployment-side gate referenced by
  `FEATURE_PROMOTION_RULES.md` §3.8; cross-links to the parser/routing
  guardrails and product-level feature promotion policy.
- Working principle — verbatim five-step rule from
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §6 (local data contract → R2 keys
  documented → data synced → deployment smoke → missing-data clean
  unsupported, no broad fallback).
- **Rule 1 — Required runtime data key list rule.** Every promotion lists
  every R2 object key the deployed runtime needs; "no new R2 objects" is a
  valid explicit entry; full bucket-relative paths only; existing keys
  listed too so smoke has a complete set.
- **Rule 2 — R2 sync verification rule (head_object evidence).** Run
  `pipeline sync-r2 --dry-run` then `pipeline sync-r2`; capture
  `head_object` evidence (Bucket, Key, ContentLength, LastModified,
  nbatools-md5) for every required key into the promotion return package;
  missing key is a deploy blocker; read-only with the same credentials the
  deployed runtime uses.
- **Rule 3 — Deployment smoke rule (pointed at the feature).** New smoke
  case in `tools/deployment_smoke.py` exercising the feature against the
  deployed runtime; asserts route, result shape, and feature-specific
  evidence; smoke report captured under `outputs/deployment_smoke/`; runs
  after rule 2; smoke alone without rule-2 evidence is not sufficient.
- **Rule 4 — Missing-data clean no_data / unsupported behavior rule.**
  Acceptable shapes: `no_data`, `filter_not_supported`,
  `conference_coverage`, or a route-specific guided unsupported response;
  the exact shape is fixed by the per-feature contract in
  `FEATURE_PROMOTION_RULES.md` §4; smoke must pin missing-data behavior
  when the feature has a realistic missing-data path; happy-path-only smoke
  is not enough at a non-trivial boundary.
- **Rule 5 — No broad fallback rule.** Restated verbatim; deployment-side
  applications (do not widen scope when an R2 object is missing; do not
  silently collapse scope filters; prefer visible failure to a
  smoke-passing broad-fallback answer).
- **Rule 6 — Worked example:
  `raw/teams/team_conference_membership.csv`.** Walks the checklist for
  opponent-conference team-record support stage by stage (6.1 required key
  list, 6.2 `head_object` evidence including the actual ContentLength/
  LastModified/nbatools-md5 values for the current release candidate, 6.3
  deployment smoke invocation and assertions, 6.4 missing-data path
  expectations, 6.5 specific broad-fallback shape this checklist prevents).
- **How this checklist is used.** Reviewer surface; return-package
  expectations (rule-1 list, rule-2 evidence, rule-3 report reference,
  rule-4 evidence when applicable); re-assertion expectations when a future
  promotion changes the required-key set.

### 3.2 docs/planning/raw-product/FEATURE_PROMOTION_RULES.md — cross-link tighten-up

Four placeholder cross-links updated to point at the new section. The
locations:

- §3.2 preflight bullet (line ~92): replaced "see §3.8 and the Wave 2
  promotion checklist" with a direct pointer to the new deployment.md
  section.
- §3.8 stage close-out (line ~176): replaced the "will live in
  `docs/operations/deployment.md` as part of Wave 2 … the runbook itself
  is the link target" paragraph with a sentence naming the new section and
  enumerating its five rules.
- §5.8 worked-example close-out (line ~317): replaced the "will live …
  the runbook itself is the link target" paragraph with a pointer to the
  new §6 worked example in deployment.md.
- §8 "How this doc is used" bullet (line ~368): replaced "added in Wave 2
  of the Raw Product post-review hardening plan" with a direct reference
  to the new section.

No other content changed in `FEATURE_PROMOTION_RULES.md`. The per-feature
contract format (§4), the promotion path stages (§3.1–§3.9), the worked
example narrative (§5.1–§5.9), the stop conditions (§6), the non-goals
(§7), and the working principles (§2) all remain as committed in Wave 1.

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 2 acceptance
criteria:

| Criterion | Status | Evidence |
|---|---|---|
| `docs/operations/deployment.md` contains a clearly labeled promotion checklist that any new data-backed feature must satisfy | met | New top-level section "Data-backed Feature Promotion Checklist". |
| The checklist uses `raw/teams/team_conference_membership.csv` as the worked example | met | Section 6 "Worked example — `raw/teams/team_conference_membership.csv`" walks the full checklist stage by stage. |
| The cross-link from Wave 1's Feature Promotion Rules doc resolves | met | Four cross-links in `FEATURE_PROMOTION_RULES.md` (§3.2, §3.8, §5.8, §8) now point to "Data-backed Feature Promotion Checklist" by name. |

From the user's explicit Wave 2 task list:

| Required item | Status |
|---|---|
| Required runtime data key list rule | met (rule 1) |
| R2 sync verification rule with `head_object` evidence | met (rule 2) |
| Deployment smoke rule | met (rule 3) |
| Missing-data clean `no_data` / `unsupported` behavior rule | met (rule 4) |
| No broad fallback rule | met (rule 5) |
| Worked example: `raw/teams/team_conference_membership.csv` | met (rule 6 + cross-links to existing release-candidate `head_object` evidence in the "Data Sync Before Preview Smoke" section) |
| Update cross-links from `FEATURE_PROMOTION_RULES.md` if needed | met (four cross-links updated) |
| Wave 2 return package created | met (this file) |
| No code/test/corpus/parser/backend/frontend changes | met |
| `git diff --check` | met (clean — see §5.1) |

Stop conditions (Wave 2):

- No change to deployment scripts, R2 sync code, or smoke harness:
  confirmed.
- No move/rename of the existing "Data Sync Before Preview Smoke" or
  "Deployment Smoke Monitoring" sections: confirmed (the new section was
  added between "Deployment Smoke Monitoring" and "Custom-Domain Closure
  Checklist"; both existing sections remain intact).

## 5. Validation result

### 5.1 `git diff --check`

Run: `git diff --check`.

Result: clean (no whitespace errors flagged). See §6 for the exact command.

### 5.2 Markdown lint

No repo-standard markdown linter is wired into the Makefile (per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §8). `git diff --check` is the
minimum bar, and it passed.

### 5.3 Code / test / corpus / parser / backend / frontend changes

None. This wave is docs/policy only.

## 6. Commands run for validation

```text
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not change `tools/deployment_smoke.py` or any deployment script.
- Did not change `src/nbatools/commands/pipeline/sync_r2.py` or any R2
  sync code.
- Did not change the smoke harness or any smoke case definitions.
- Did not change parser, routing, backend, or frontend behavior.
- Did not change result contracts, raw QA corpus, frontend-copy QA, or
  visual QA expectations.
- Did not change `README.md`, the active release docs, or the public UI.
- Did not move, archive, rename, or delete any file.
- Did not redeclare release status.
- Did not touch the existing "Data Sync Before Preview Smoke",
  "Deployment Smoke Monitoring", "Vercel Frontend Build", or "Custom-Domain
  Closure Checklist" sections of `docs/operations/deployment.md`.

## 8. Next wave

Wave 3 — Feedback Review Cadence:

- Target file: `docs/operations/query_feedback_review.md`.
- Goal: add a "Weekly Beta Review Cadence" section codifying the six-step
  routine from `RAW_PRODUCT_POST_REVIEW_NOTES.md` §5 (export → open
  `feedback_review.md` → ChatGPT triage → fill
  `triage_decisions_template.csv` → classify into triage categories →
  convert verified findings into QA cases or planning docs), the
  post-event trigger, the eight triage categories (bug, support candidate,
  expected unsupported, duplicate, no action, needs more data,
  parser/routing risk, UI/copy issue), and the ownership model (triage =
  human + ChatGPT; execution = agent).
- No change to `tools/export_query_feedback.py`, the Makefile target, or
  the feedback endpoint.
