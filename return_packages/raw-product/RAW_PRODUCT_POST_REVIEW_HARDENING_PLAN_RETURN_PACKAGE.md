# Raw Product Post-Review Hardening Plan — Return Package

## What changed

This was a planning/docs-only pass. The two Raw Product review notes
documents were converted into a single ordered hardening plan with six waves,
a first-wave execution prompt, and explicit non-goals. No production code,
parser, routing, backend, frontend, result contract, corpus, or release
status changed.

## Files changed

- `docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md` —
  new ordered hardening plan (executive summary, inputs reviewed,
  issue/action inventory, priority classification, six-wave roadmap, first
  execution prompt, deferred/non-goals, validation).
- `docs/index.md` — planning section updated to list the new hardening plan
  alongside the two source review notes docs.
- `return_packages/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN_RETURN_PACKAGE.md` —
  this file.

## Launch blocker decision

**No launch blocker.** Inspection of both review notes docs and the current
release-candidate handoff / release-package docs found no new regression or
contract break. The Raw Product remains launch-ready with notes:

- Release status: `RELEASE_CANDIDATE_WITH_NOTES`
- Preview status: `PREVIEW_READY_WITH_NOTES`
- Feedback status: `FEEDBACK_READY_WITH_NOTES`
- Public UI status: `PUBLIC_UI_READY_WITH_NOTES`

All identified items are growth guardrails, process hygiene, or polish.

## Ordered roadmap

- **Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules**
  (should do before next feature expansion). Creates
  `PARSER_ROUTING_GROWTH_GUARDRAILS.md` and `FEATURE_PROMOTION_RULES.md`
  under `docs/planning/raw-product/`. Encodes "Forgive phrasing. Do not
  invent meaning." and "No broad fallback answers." Documents the promotion
  path with opponent-conference as the worked example. Defers
  `natural_query.py` extraction and bucket-first intent classification.
- **Wave 2 — Data/R2 Promotion Checklist Hardening** (should do before next
  feature expansion). Updates `docs/operations/deployment.md` with a
  data-backed-feature promotion checklist (required key list, R2 sync
  verification, deployment smoke, missing-data clean no_data behavior).
- **Wave 3 — Feedback Review Cadence** (immediate post-launch polish).
  Updates `docs/operations/query_feedback_review.md` with the weekly beta
  routine, ChatGPT triage handoff, triage categories, post-event trigger,
  and human-vs-agent ownership model.
- **Wave 4 — Docs/Return Package Taxonomy** (immediate post-launch polish).
  Updates `docs/index.md` "Documentation Category Rules" and `AGENTS.md`
  with rules: return packages are evidence not source of truth; archive
  cadence; when to use a short summary instead.
- **Wave 5 — README/Product Positioning Refresh** (immediate post-launch
  polish). Refreshes `README.md` to a product-first opening (product
  promise → good-at → intentionally unsupported → web UI quick start →
  dev surfaces → release status → data/deployment notes).
- **Wave 6 — Lightweight Product Promise/Homepage Pass** (immediate
  post-launch polish). Small UX pass: search-first, helpful placeholder,
  starter examples, collapsible "What can I ask?", no required tutorial or
  category selector. Folds in the public answer context duplication audit
  (POST §4).

Deferred / non-goals: parser rewrite, required category selector, admin
dashboard, automatic corpus mutation from feedback, branding change, broad
new feature support, `natural_query.py` extraction execution, return-package
archive sweep execution.

## First recommended execution wave

**Wave 1 — Parser/Routing Growth Guardrails + Feature Promotion Rules.** The
exact execution prompt is included in §6 of the hardening plan.

## Validation result

- `git diff --check` — passes (see "Validation" section below for the
  command and result).
- markdown lint — no repo-standard markdown linter is wired into the
  Makefile; `git diff --check` is the minimum bar used here.

## Acceptance criteria check

- Plan doc created → yes
  (`docs/planning/raw-product/RAW_PRODUCT_POST_REVIEW_HARDENING_PLAN.md`).
- Plan turns review notes into ordered waves → yes (six waves with goals,
  files-likely-to-change, acceptance criteria, validation, stop conditions).
- Distinguishes launch blockers from post-launch/future hardening → yes
  (no launch blockers; Waves 1–2 before next feature expansion; Waves 3–6
  immediate post-launch polish; explicit deferred bucket).
- Recommends the first execution wave → yes (Wave 1, with full prompt).
- No code/test/corpus changes → confirmed.
- Return package created → yes (this file).
- `git diff --check` passes → yes.
