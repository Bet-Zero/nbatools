# Raw Product Post-Review Hardening Plan

## 1. Executive summary

- Current release status: `RELEASE_CANDIDATE_WITH_NOTES` / `PREVIEW_READY_WITH_NOTES`
  / `FEEDBACK_READY_WITH_NOTES` / `PUBLIC_UI_READY_WITH_NOTES`.
- Closure status: **complete with notes.** Raw Product Post-Review Hardening
  Waves 1–6 have completed, and the follow-up AppTheming test drift fix
  resolved the pre-existing frontend-suite drift surfaced during Wave 6.
- Planning decision: the post-review notes and parser/routing growth notes were
  converted into an ordered, bounded hardening roadmap before further feature
  expansion. That roadmap has now been executed through Wave 6.
- Launch blocker? **No.** Inspection of the two review notes docs and the
  current release/handoff docs found no new launch blocker. The Raw Product
  remains launch-ready with notes as previously declared. All remaining items
  are post-launch/deferred polish, process, or maintainability notes — not
  release regressions.
- Validation refresh: full frontend tests are now clean after the AppTheming
  test drift fix: **25/25 files, 352/352 tests passing**. Frontend build still
  passes with the existing Vite large-chunk warning, and lint still passes with
  the existing `ReviewPage` `react-hooks/exhaustive-deps` warning.
- What this plan does not do:
  - It does not change parser, routing, backend, or frontend behavior.
  - It does not change result contracts or QA corpus expectations.
  - It does not add features, archive/move files, or rebrand.
  - It does not redeclare release status.

## 2. Inputs reviewed

| Input | Role |
|---|---|
| `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_NOTES.md` | Primary product-level post-review notes (sections 3–14). |
| `docs/planning/raw-product/PARSER_ROUTING_GROWTH_REVIEW_NOTES.md` | Primary parser/routing growth review notes (sections 5–13). |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md` | Confirms current release-candidate-with-notes status and evidence table. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md` | Confirms current public UI ready-with-notes status and scope statement. |
| `docs/operations/deployment.md` | Existing R2/Vercel deployment runbook — Wave 2 target for promotion-checklist hardening. |
| `docs/operations/query_feedback_review.md` | Existing feedback review runbook — Wave 3 target for cadence refinement. |
| `docs/operations/ui_guide.md` | Public UI dev guide — informs Wave 6 search-first/homepage scope. |
| `docs/reference/query_guide.md` | Full query reference — informs Wave 1 accepted/rejected phrase contract format. |
| `docs/reference/query_catalog.md` | Living catalog of supported phrasing — informs Wave 1 contract and Wave 5 README framing. |
| `docs/index.md` | Docs source-of-truth taxonomy — informs Wave 4 docs vs return_packages rules. |
| `README.md` | Top-level positioning — Wave 5 target. |
| `AGENTS.md` | Agent contract — informs Wave 4 return-package taxonomy guidance for agents. |
| `src/nbatools/commands/natural_query.py` | Identified as the parser maintainability risk in PARSER_ROUTING_GROWTH_REVIEW_NOTES §6. |
| `src/nbatools/query_service.py` | Query service surface; informs Wave 1 collision/route ordering rules. |
| `Makefile` | Hosts `make query-feedback-export` — Wave 3 cadence anchors here. |
| `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md` | Confirms Wave 1 completed: parser/routing guardrails and feature promotion rules. |
| `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` | Confirms Wave 1 completed: feature promotion rules and promotion-path contract. |
| `docs/operations/deployment.md` | Confirms Wave 2 completed: Data/R2 promotion checklist hardening. |
| `docs/operations/query_feedback_review.md` | Confirms Wave 3 completed: weekly feedback review cadence. |
| `docs/index.md` | Confirms Wave 4 completed: docs/return-package taxonomy. |
| `README.md` | Confirms Wave 5 completed: README/product positioning refresh. |
| `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md` | Confirms Wave 6 completed and records follow-up AppTheming test drift fix with clean full frontend suite: 352/352 tests passing. |

## 2.1 Closure refresh — 2026-05-21

Post-review hardening closure is recorded as follows:

- Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules:
  complete.
- Wave 2 — Data/R2 Promotion Checklist Hardening: complete.
- Wave 3 — Feedback Review Cadence: complete.
- Wave 4 — Docs/Return Package Taxonomy: complete.
- Wave 5 — README/Product Positioning Refresh: complete.
- Wave 6 — Lightweight Product Promise/Homepage Pass: complete.
- Follow-up AppTheming test drift fix: complete; full frontend suite is clean
  at 352/352 tests passing.

No new launch blockers were identified during the closure refresh. The release
classification remains:

```text
Release status: RELEASE_CANDIDATE_WITH_NOTES
Preview status: PREVIEW_READY_WITH_NOTES
Feedback status: FEEDBACK_READY_WITH_NOTES
Public UI status: PUBLIC_UI_READY_WITH_NOTES
```

Remaining notes are post-launch or explicitly deferred:

- Existing Vite large-chunk warning.
- Existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` lint
  warning.
- No screenshot automation yet.
- Visual QA corpus expansion deferred.
- Admin dashboard / mutable triage overlay deferred.
- `natural_query.py` extraction deferred.
- Return-package archive sweep deferred.
- Branding/name change deferred.

## 3. Issue/action inventory

| Concern | Category | Launch-blocking? | Recommended bucket |
|---|---|---|---|
| Parser/routing wrong-route risk as new families are added (PARSER §5, POST §3) | Parser/routing guardrails | No | Complete in Wave 1 |
| No durable Feature Promotion Rules doc (POST §9) | Process policy | No | Complete in Wave 1 |
| Accepted/rejected phrase contract per supported family (PARSER §9) | Parser policy | No | Complete in Wave 1 |
| Route collision check strategy across nearby phrase families (PARSER §10C) | Parser policy | No | Complete in Wave 1 |
| Unsupported-boundary regression requirement / no broad fallback (PARSER §9, POST §9) | Parser policy | No | Complete in Wave 1 |
| Gradual `natural_query.py` extraction plan (PARSER §6, §10D) | Maintainability plan | No | Later cleanup / deferred (documented in Wave 1; execution deferred) |
| Bucket-first intent classification investigation (PARSER §7, §10E) | Parser architecture | No | Later cleanup / deferred (Wave 1 notes only) |
| R2 promotion checklist: list/sync/smoke required runtime data (POST §6) | Deployment guardrail | No | Complete in Wave 2 |
| Missing-data clean no_data behavior rule (POST §6) | Deployment guardrail | No | Complete in Wave 2 |
| `docs/operations/deployment.md` update for the promotion checklist (POST §6) | Docs update | No | Complete in Wave 2 |
| Weekly beta feedback review cadence (POST §5) | Operational runbook | No | Complete in Wave 3 |
| ChatGPT triage handoff + triage categories (POST §5) | Operational runbook | No | Complete in Wave 3 |
| Agent vs human/ChatGPT ownership during early beta (POST §5) | Operational policy | No | Complete in Wave 3 |
| Return packages as evidence, not source of truth (POST §7) | Docs taxonomy | No | Complete in Wave 4 |
| Return-package archive cadence (POST §7) | Docs taxonomy | No | Documented in Wave 4; archive sweep deferred |
| When to use return packages vs short summaries (POST §7) | Docs taxonomy | No | Complete in Wave 4 |
| README product-first refresh (POST §8) | Positioning | No | Complete in Wave 5 |
| Lightweight homepage/product-promise pass (POST §12) | UX polish | No | Complete in Wave 6 |
| Public answer context duplication audit (POST §4) | UI polish | No | Complete in Wave 6 |
| Branding/name change (POST §10) | Identity | No | Later / deferred (non-goal for this plan) |
| Required category selector before search (POST §12, PARSER §8) | UX feature | No | Later / deferred (explicit non-goal) |
| Parser rewrite in one pass (PARSER §6, §11) | Refactor | No | Later / deferred (explicit non-goal) |
| Automatic corpus mutation from feedback (POST §5 inverse) | Automation | No | Later / deferred (explicit non-goal) |

## 4. Priority classification

### Must do before public launch

None. Closure inspection found no new launch blocker. The Raw Product remains
launch-ready with notes per the release candidate handoff and release package.

### Should do before next feature expansion

Completed:

- Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules
- Wave 2 — Data/R2 Promotion Checklist Hardening

### Immediate post-launch polish

Completed:

- Wave 3 — Feedback Review Cadence
- Wave 4 — Docs/Return Package Taxonomy
- Wave 5 — README/Product Positioning Refresh
- Wave 6 — Lightweight Product Promise/Homepage Pass (includes public answer
  context duplication audit)

### Later / deferred

- Gradual `natural_query.py` extraction execution (documented in Wave 1,
  deferred)
- Bucket-first intent classification preflight
- Optional guided UI mode experiments
- Branding/name change
- Admin dashboard / mutable triage overlay
- Automatic corpus mutation from feedback
- Return-package archive sweep

## 5. Ordered roadmap

### Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules — Complete

- Goal: create durable policy docs that constrain how new natural-language
  query support is added, so parser/routing growth cannot quietly become a
  wrong-route problem.
- Why it matters: the main failure mode is wrong route, not crash. Wrong-route
  answers look credible while answering a different question
  (PARSER §5). Both review docs name this as the first hardening work.
- Files likely to change (new or updated docs only):
  - new `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md` —
    accepted phrase requirements, rejected/guarded phrase requirements, route
    collision rule, unsupported-boundary regression rule, no-broad-fallback
    rule, QA/corpus requirements, deferred `natural_query.py` extraction note,
    deferred bucket-first preflight note.
  - new `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` — promotion
    path (unsupported boundary → preflight → data contract → route/result
    contract → parser support → raw QA cases → frontend-copy/visual QA when
    rendering changes → preview/deployment smoke → release docs), with each
    new supported area required to define the bulleted contract from PARSER §9
    / POST §9.
  - update `docs/index.md` planning section to link both new docs.
- Acceptance criteria:
  - Both new docs exist under `docs/planning/raw-product/`.
  - Both encode the "Forgive phrasing. Do not invent meaning." principle and
    the "No broad fallback answers for unsupported or low-confidence queries"
    rule.
  - The Feature Promotion Rules doc explicitly references opponent-conference
    support as the worked example of the promotion path.
  - `docs/index.md` lists both docs.
- Validation:
  - `git diff --check`
  - markdown lint if available (e.g. `markdownlint` or repo convention)
- Stop conditions:
  - Any temptation to change `src/nbatools/commands/natural_query.py` or to
    add/remove parser rules → stop; this wave is docs only.
  - Any temptation to introduce a category selector or to start the
    `natural_query.py` extraction → stop; deferred.

### Wave 2 — Data/R2 Promotion Checklist Hardening — Complete

- Goal: turn the post-review §6 rule into a permanent, checkable promotion
  checklist that prevents a data-backed feature from passing locally while
  failing in preview/prod due to missing R2 objects.
- Why it matters: the project is data-dependent; Vercel excludes `data/**`;
  deployed runtime uses R2. The opponent-conference incident already demonstrated
  the failure shape.
- Files likely to change (docs only):
  - update `docs/operations/deployment.md` — add a "Data-backed Feature
    Promotion Checklist" section: required runtime data key list rule, R2
    sync verification rule (`head_object` evidence), deployment smoke rule
    pointed at the feature, missing-data clean `no_data`/`unsupported`
    behavior rule (no broad fallback).
  - cross-link from `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md` to
    the deployment-runbook section.
- Acceptance criteria:
  - `docs/operations/deployment.md` contains a clearly labeled promotion
    checklist that any new data-backed feature must satisfy.
  - The checklist uses `raw/teams/team_conference_membership.csv` as the
    worked example.
  - The cross-link from Wave 1's Feature Promotion Rules doc resolves.
- Validation:
  - `git diff --check`
  - markdown lint if available
- Stop conditions:
  - Any change to deployment scripts, R2 sync code, or smoke harness → stop;
    this wave is docs only.

### Wave 3 — Feedback Review Cadence — Complete

- Goal: refine the existing `docs/operations/query_feedback_review.md` into a
  weekly beta runbook that names the command, the artifact, the triage
  categories, the post-event trigger, and the ownership model.
- Why it matters: feedback storage exists, the export workflow exists, but
  without a cadence the data becomes a junk drawer (POST §5).
- Files likely to change (docs only):
  - update `docs/operations/query_feedback_review.md` — add a "Weekly Beta
    Review Cadence" section with the six-step routine from POST §5, the
    post-event trigger, the triage categories (bug, support candidate,
    expected unsupported, duplicate, no action, needs more data,
    parser/routing risk, UI/copy issue), and the ownership model (early
    reviews are product-judgment with ChatGPT triage; agents execute follow-up
    only after triage).
- Acceptance criteria:
  - Runbook names `make query-feedback-export` as the command and
    `feedback_review.md` as the ChatGPT-handoff artifact.
  - Runbook clearly distinguishes triage (human + ChatGPT) from execution
    (agent).
- Validation:
  - `git diff --check`
  - markdown lint if available
- Stop conditions:
  - Any change to `tools/export_query_feedback.py`, the Makefile target, or
    the feedback endpoint → stop; this wave is docs only.

### Wave 4 — Docs/Return Package Taxonomy — Complete

- Goal: encode the durable rules from POST §7 so return packages stop
  competing with active planning docs.
- Why it matters: return packages are evidence artifacts, not source of truth;
  the `return_packages/raw-product/` directory has grown large and benefits
  from explicit archive rules.
- Files likely to change (docs only):
  - update `docs/index.md` "Documentation Category Rules" — add a
    "Return Packages" subsection with the rules: evidence not source of truth;
    durable behavior change goes under `docs/`; archive completed wave packages
    on a regular cadence; prompts should tell agents where return packages
    belong.
  - update `AGENTS.md` (if it references return packages) — add a short
    pointer to the new taxonomy section.
  - no file moves; archive cadence is described, not executed.
- Acceptance criteria:
  - `docs/index.md` has a clearly labeled return-package taxonomy section.
  - Rules cover: where return packages live, when to create them vs paste a
    short summary, archive cadence.
- Validation:
  - `git diff --check`
  - markdown lint if available
- Stop conditions:
  - Any move/delete of files in `return_packages/` → stop; archive execution
    is a separate later pass.

### Wave 5 — README/Product Positioning Refresh — Complete

- Goal: refresh `README.md` so the top of the repo describes the current
  product (public answer-first NBA stats product) rather than the historical
  CLI/dev workbench.
- Why it matters: README lags the product; new readers see a workbench framing
  instead of the answer-engine product.
- Files likely to change:
  - update `README.md` — new ordering: product promise → what questions it
    is good at → what is intentionally unsupported → web UI quick start →
    developer surfaces (CLI / API / structured query) → QA / release status
    pointers → data / deployment notes.
  - update `docs/index.md` "What NBA Tools Currently Supports" only if README
    re-framing creates a contradiction with the existing list.
- Acceptance criteria:
  - README opens with the product-first framing from POST §8.
  - README preserves accurate links to existing dev surfaces and release docs.
  - No claim that the product supports anything outside the current verified
    boundary.
- Validation:
  - `git diff --check`
  - markdown lint if available
- Stop conditions:
  - Any temptation to rebrand / rename the product → stop; explicit non-goal
    (POST §10).

### Wave 6 — Lightweight Product Promise/Homepage Pass — Complete

- Goal: a small UX pass that makes the homepage feel search-first and
  answer-first without adding a required tutorial or category selector, and
  folds in the public answer context duplication audit from POST §4.
- Why it matters: users should learn what works through examples and recovery
  states, not through forced onboarding. Public answers should not duplicate
  scope across the answer sentence and chips.
- Files likely to change:
  - frontend homepage / landing surface — small copy + placement changes for
    placeholder text, starter examples, optional/collapsible "What can I ask?"
    help, no-result suggestions.
  - public result hero — audit for duplicate scope chips that repeat scope
    already in the answer sentence.
  - relevant frontend-copy QA cases if copy changes.
- Acceptance criteria:
  - Homepage shows search box first, helpful placeholder, strong starter
    examples, and optional collapsible help only.
  - Public result hero does not duplicate scope already stated in the answer
    sentence; non-obvious trust/scope context (data freshness, filter window,
    "without LeBron James") remains visible.
  - Debug, `/review`, `/visual-qa`, and feedback payloads remain unchanged.
- Validation:
  - `git diff --check`
  - markdown lint if available
  - Frontend lint and build (existing warnings remain non-blocking).
  - Manual public-UI check on the listed homepage and a representative answer
    surface.
- Stop conditions:
  - Any addition of a required category selector or required tutorial → stop;
    explicit non-goal.
  - Any change to backend or parser behavior → stop; this wave is UI polish.

## 6. Closure status

This plan no longer has a next hardening-wave prompt. Waves 1–6 have all been
executed and recorded in `return_packages/raw-product/`, and the follow-up
AppTheming test drift fix resolved the only frontend-suite drift surfaced during
Wave 6 validation.

Closure evidence:

- `docs/planning/raw-product/PARSER_ROUTING_GROWTH_GUARDRAILS.md`
- `docs/planning/raw-product/FEATURE_PROMOTION_RULES.md`
- `docs/operations/deployment.md`
- `docs/operations/query_feedback_review.md`
- `docs/index.md`
- `README.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`

The closure refresh does not change release classification. The remaining
release notes are deferred/post-launch items, not blockers.

## 7. Deferred / non-goals

- Existing Vite large-chunk warning.
- Existing `frontend/src/ReviewPage.tsx` `react-hooks/exhaustive-deps` lint
  warning.
- Screenshot automation.
- Visual QA corpus expansion.
- Parser rewrite in one pass.
- Required query category selector before search.
- Admin dashboard or mutable triage overlay for feedback.
- Automatic corpus mutation from feedback.
- Branding / name change.
- Broad new feature support outside the current verified boundary.
- Execution of `natural_query.py` extraction (plan only in Wave 1).
- Execution of return-package archive moves (Wave 4 documents the rules; the
  archive sweep is a separate later pass).

## 8. Validation

- `git diff --check`
- markdown lint if available (no repo-standard linter is currently wired into
  the Makefile; `git diff --check` is the minimum bar)
- Latest full frontend-suite evidence is recorded in
  `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`:
  25/25 files and 352/352 tests passing after the AppTheming test drift fix.
