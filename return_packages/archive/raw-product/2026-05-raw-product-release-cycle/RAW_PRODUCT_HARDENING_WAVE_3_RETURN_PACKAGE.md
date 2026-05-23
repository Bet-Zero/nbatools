# Raw Product Hardening — Wave 3 Return Package

## 1. Executive summary

- Wave executed: Wave 3 — Feedback Review Cadence, per
  `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5.
- What was produced: a new "Weekly Beta Feedback Review Cadence" section
  added at the top of `docs/operations/query_feedback_review.md`, naming
  the command, primary handoff artifact, triage worksheet, weekly cadence,
  post-event trigger, the eight triage categories from
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §5, and the explicit ownership model
  (user runs export → user sends to ChatGPT → ChatGPT triages → agents
  execute only after triage).
- Scope: docs/policy only. No production code, parser, routing, backend,
  frontend, deployment, export tool, Makefile, or feedback-endpoint
  changes.
- Release status: unchanged. Raw Product remains
  `RELEASE_CANDIDATE_WITH_NOTES` /
  `PREVIEW_READY_WITH_NOTES` /
  `FEEDBACK_READY_WITH_NOTES` /
  `PUBLIC_UI_READY_WITH_NOTES`.
- Next wave: Wave 4 — Docs/Return Package Taxonomy (target files
  `docs/index.md`, optionally `AGENTS.md`).

## 2. Files changed

| File | Change type | Why |
| --- | --- | --- |
| `docs/operations/query_feedback_review.md` | Updated runbook | Added the "Weekly Beta Feedback Review Cadence" section as the first major section after the runbook intro, ahead of the existing reference sections (Storage, Record Schema, Export Workflow, …). The new section covers: when to run (weekly + post-event + on-demand), the six-step routine, the eight triage categories, the ownership model, what a passing run looks like, and what the routine does not do. No existing section was removed, renumbered, or rewritten. |
| `return_packages/raw-product/RAW_PRODUCT_HARDENING_WAVE_3_RETURN_PACKAGE.md` | Added return package | Records what changed, files changed, acceptance-criteria check, and validation result for Wave 3. |

No other files were created, modified, moved, or deleted.

## 3. What changed (substantive content)

### 3.1 docs/operations/query_feedback_review.md — new top section

New top-level section: **Weekly Beta Feedback Review Cadence**. Inserted
between the document intro line and the existing "Storage" section so the
cadence frames the runbook before the reference material. Structure:

- Intro paragraph — names the cadence as the runbook's primary workflow;
  cross-links the working-rule chain from
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §5; positions the rest of the runbook
  as operational reference.
- **When to run.** Weekly during beta / early launch on a fixed weekday
  (small empty-handed pass preferred over skipping). Immediately after any
  larger public test, demo, or user group trial (non-negotiable
  post-event trigger). On demand for incidents or single high-priority
  reports (does not replace the next weekly run).
- **Routine — six steps.**
  1. Run the export via `make query-feedback-export` (canonical command;
     the raw `python tools/export_query_feedback.py …` invocation
     remains for filtered or alternate-source runs).
  2. Open `outputs/query_feedback_exports/<run_id>/feedback_review.md` —
     the primary handoff artifact.
  3. Send `feedback_review.md` (or key sections) to ChatGPT for product
     triage.
  4. Fill the triage worksheet
     `outputs/query_feedback_exports/<run_id>/triage_decisions_template.csv`.
  5. Classify each group into one of the eight triage categories below.
  6. Convert only reviewed, verified findings into downstream work; the
     routine itself does not modify QA, parser, frontend, data, or
     feedback artifacts.
- **Triage categories.** Eight-row table matching
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §5 verbatim in coverage:
  - `bug`
  - `support_candidate`
  - `expected_unsupported`
  - `duplicate`
  - `no_action`
  - `needs_more_data`
  - `parser_routing_risk`
  - `ui_copy_issue`
  Each row has a "When to use" definition and a "Typical follow-up" that
  links into the existing operational vocabulary (Triage Decisions, Triage
  Statuses, QA Conversion Rules, FEATURE_PROMOTION_RULES.md,
  PARSER_ROUTING_GROWTH_GUARDRAILS.md).
- **Ownership model.** Explicit four-actor split:
  - User runs `make query-feedback-export` and opens
    `feedback_review.md`.
  - User sends `feedback_review.md` (or key sections) to ChatGPT;
    redaction decisions are the user's.
  - ChatGPT helps classify and surfaces duplicates / parser-routing
    risks; does not modify any repo file; does not have final product
    judgment.
  - User records the final triage decision in
    `triage_decisions_template.csv`.
  - Agents execute follow-up work **only after triage is complete** and
    only when the worksheet row names the work via `linked_case_id` and
    `next_action`.

  Hard rule stated verbatim:

  ```text
  Triage = human + ChatGPT.
  Execution = agent.
  Agents do not triage.
  ```

- **What a passing weekly run looks like.** A run id under
  `outputs/query_feedback_exports/`, a reviewed `feedback_review.md`, a
  filled `triage_decisions_template.csv` (category + status +
  next_action per group), high-priority groups linked to a case or
  planning pointer, and any follow-up queued for a separate agent
  execution step.
- **What this routine intentionally does not do.** Lists the four hard
  non-negotiables: read-only against R2; no automatic mutation of QA
  corpora, parser, frontend, data, or feedback endpoint; no automatic
  promotion of `support_candidate` (that follows
  `FEATURE_PROMOTION_RULES.md`); no delegation of product judgment to an
  agent.

### 3.2 Existing sections — unchanged

The following existing sections of `query_feedback_review.md` were not
modified:

- Storage
- Record Schema
- Export Workflow (still contains the raw
  `tools/export_query_feedback.py` invocation for filtered runs; the new
  cadence cross-references this section as the underlying form of
  `make query-feedback-export`)
- Export Outputs
- Filter Semantics
- Smoke Exclusion Policy
- Grouping and Suggested Triage
- Triage Template Workflow
- QA Conversion Rules
- Triage Statuses
- Triage Decisions
- Privacy and Retention

The new cadence section cross-links into these sections by anchor where
the routine asks the reviewer to reach into the operational reference
(filters, smoke handling, suggested-triage signals, triage worksheet
field conventions, status vocabulary, QA conversion bar, retention).

## 4. Acceptance-criteria check

From `RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §5 Wave 3 acceptance
criteria:

| Criterion | Status | Evidence |
| --- | --- | --- |
| Runbook names `make query-feedback-export` as the command | met | Cadence step 1 names the Makefile target as the canonical command. |
| Runbook names `feedback_review.md` as the ChatGPT-handoff artifact | met | Cadence step 2 names `feedback_review.md` as the primary handoff artifact; cadence step 3 sends it (or key sections) to ChatGPT. |
| Runbook clearly distinguishes triage (human + ChatGPT) from execution (agent) | met | Ownership model section states the split explicitly and includes the verbatim hard rule. |

From the user's explicit Wave 3 task list:

| Required item | Status |
| --- | --- |
| Command: `make query-feedback-export` | met (cadence step 1) |
| Primary handoff artifact: `feedback_review.md` | met (cadence step 2 + ownership model) |
| Triage worksheet: `triage_decisions_template.csv` | met (cadence step 4) |
| Weekly beta cadence | met ("When to run" section) |
| Post-demo/public-test trigger | met ("When to run" section, second bullet) |
| Triage categories (bug, support candidate, expected unsupported, duplicate, no action, needs more data, parser/routing risk, UI/copy issue) | met (eight-row Triage categories table) |
| Ownership model (user runs export → user sends `feedback_review.md` to ChatGPT → ChatGPT triages → agents execute only after triage) | met ("Ownership model" section + verbatim hard rule) |
| Wave 3 return package created | met (this file) |
| No code/test/corpus/parser/backend/frontend/deployment changes | met |
| `git diff --check` | met (clean — see §5.1) |

Stop conditions (Wave 3):

- No change to `tools/export_query_feedback.py`: confirmed.
- No change to the Makefile target: confirmed.
- No change to the feedback endpoint: confirmed.

## 5. Validation result

### 5.1 `git diff --check`

Run: `git diff --check`.

Result: clean (no whitespace errors flagged). See §6 for the exact command.

### 5.2 Markdown lint

No repo-standard markdown linter is wired into the Makefile (per
`RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` §8). One IDE lint hint
(`MD060/table-column-style`) surfaced during editing for the eight-row
triage categories table; the table separator was normalized to the
spaced-pipe form (`| --- | --- | --- |`) to clear the hint. The
existing tables elsewhere in the runbook use the compact `|---|---|`
form and were not touched.

### 5.3 Code / test / corpus / parser / backend / frontend / deployment changes

None. This wave is docs/policy only.

## 6. Commands run for validation

```text
git diff --check
```

## 7. Scope discipline

What this wave intentionally did not do:

- Did not change `tools/export_query_feedback.py` or any other exporter
  code.
- Did not change the `query-feedback-export` Makefile target or any
  Makefile content.
- Did not change the `POST /query-feedback` endpoint or any feedback
  collection code.
- Did not change parser, routing, backend, frontend, or deployment
  behavior.
- Did not change result contracts, raw QA corpus, frontend-copy QA, or
  visual QA expectations.
- Did not change `README.md`, the active release docs, or the public UI.
- Did not move, archive, rename, or delete any file.
- Did not redeclare release status.
- Did not modify any existing section of `query_feedback_review.md`; the
  Weekly Beta Feedback Review Cadence section was inserted between the
  intro and the existing "Storage" section without rewriting any
  existing content.

## 8. Next wave

Wave 4 — Docs/Return Package Taxonomy:

- Target file: `docs/index.md` (and optionally `AGENTS.md` if it
  references return packages).
- Goal: encode the durable rules from
  `RAW_PRODUCT_POST_REVIEW_NOTES.md` §7 as a "Return Packages" subsection
  in the existing "Documentation Category Rules" section of
  `docs/index.md`: return packages are evidence not source of truth;
  durable behavior changes belong under `docs/`; archive completed wave
  packages on a regular cadence; prompts should tell agents where return
  packages belong.
- No file moves under `return_packages/`; the archive sweep is a separate
  later pass.
