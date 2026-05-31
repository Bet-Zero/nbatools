# Raw Product Post-Review Notes

## 1. Purpose

This is the broader working notes document for the current Raw Product review.
It captures product-level issues, risks, and follow-up ideas that are not limited
to parser/routing.

Use this document as a scratchpad while the review continues. When the review is
complete, use it to produce one or more concrete execution plans.

The current release is not being declared broken. The current state remains:

```text
Release status: RELEASE_CANDIDATE_WITH_NOTES
Preview status: PREVIEW_READY_WITH_NOTES
Feedback status: FEEDBACK_READY_WITH_NOTES
Public UI status: PUBLIC_UI_READY_WITH_NOTES
```

The point of this review is to catch structural issues now rather than relying
on future memory to revisit them.

Closure refresh — 2026-05-21:

- Raw Product Post-Review Hardening Waves 1–6 are complete.
- Follow-up AppTheming test drift is fixed; the full frontend suite is clean at
  25/25 files and 352/352 tests passing.
- No new launch blockers were identified.
- The release, preview, feedback, and public UI statuses remain unchanged:
  `RELEASE_CANDIDATE_WITH_NOTES`, `PREVIEW_READY_WITH_NOTES`,
  `FEEDBACK_READY_WITH_NOTES`, and `PUBLIC_UI_READY_WITH_NOTES`.
- Remaining notes are post-launch/deferred items: existing Vite large-chunk
  warning, existing `ReviewPage` lint warning, no screenshot automation,
  visual QA corpus expansion, admin dashboard / mutable triage overlay,
  `natural_query.py` extraction, return-package archive sweep, and
  branding/name change.

## 2. Working principle

When a potential future issue is identified, the project should not treat it as
"fine for now" and hope someone remembers later. The preferred workflow is:

```text
identify the risk
  -> write it down
  -> decide whether it needs immediate guardrails
  -> create a bounded plan
  -> execute the smallest safe hardening pass
```

This does not mean panic-rewriting working systems. It means setting up the
rules, checks, and documentation that prevent known risks from quietly becoming
large problems later.

## 3. Parser/routing growth risk

Detailed parser/routing guardrails live in:

```text
docs/operations/parser_routing_growth_guardrails.md
```

Summary:

- The current parser/routing works for the tested release boundary.
- The known risk is future growth, especially overlapping natural-language rules.
- The main failure mode is wrong-route behavior, not crashes.
- Wrong-route behavior is dangerous because it can look like a valid answer while
  answering a different question.
- The goal is to add parser-growth guardrails before more feature promotion.

Working rule:

```text
Forgive phrasing.
Do not invent meaning.
```

Future planning should consider:

- parser growth rules
- route collision checks
- accepted/rejected phrase contracts
- unsupported-boundary regression requirements
- gradual `natural_query.py` extraction
- possible bucket-first intent classification

## 4. Public answer context should be non-repetitive

The public UI should give users enough confidence to understand the answer
without repeating the same scope/details multiple times.

Important distinction:

- Do not show public chips/details merely to prove the backend parsed something.
- Do include essential scope in the answer sentence when it naturally fits.
- Use separate context only when it adds information not already clear from the
  answer.
- Keep full route/status/filter/debug proof in Details, `?debug=1`, `/review`,
  and feedback payloads.

Preferred example:

```text
The Celtics went 36-16 against Eastern Conference opponents in the 2025-26 regular season.
```

In that case, the public UI should not also need separate chips for:

```text
Opponent conference: East
Season: 2025-26
Season type: Regular Season
```

because that would be repetitive.

Separate context is useful when it adds non-obvious trust or scope information,
for example:

```text
Data through Apr. 12, 2026
Includes 15 Eastern Conference opponents
Since Jan. 1, 2026
Last 20 games
Without LeBron James
```

Working rule:

```text
Put essential scope in the answer when natural.
Show only non-obvious or trust-relevant context separately.
Do not duplicate the answer with chips.
```

## 5. Feedback review cadence and ownership

Query Feedback + Diagnostic Logging V1 is implemented and verified with notes.
The feedback review/export workflow is also implemented. The operational risk is
that collected feedback becomes a junk drawer if it is not reviewed regularly.

Recommended beta cadence:

```text
Weekly during beta/early launch:
  1. Run make query-feedback-export
  2. Open feedback_review.md
  3. Send feedback_review.md or the key sections to ChatGPT for product triage
  4. Fill triage_decisions_template.csv
  5. Classify each group:
     - bug
     - support candidate
     - expected unsupported
     - duplicate
     - no action
     - needs more data
     - parser/routing risk
     - UI/copy issue
  6. Convert only reviewed/verified findings into QA cases, planning docs, or
     product work
```

Additional trigger:

```text
Run a feedback review immediately after any larger public test, demo, or user group trial.
```

Ownership model:

- The first few feedback reviews should be product-judgment reviews, not only
  agent reviews.
- The user can run the export and send the generated `feedback_review.md` to
  ChatGPT.
- ChatGPT can help classify feedback into bugs, support candidates, expected
  unsupported behavior, duplicates, no-action items, parser/routing risks, or
  UI/copy issues.
- Agents can execute follow-up work after triage, but an agent should not be the
  only product judge during early beta.

## 6. Data/R2 deployment guardrail

The project is data-dependent. Local development can pass while deployed preview
or production fails if a required runtime data file exists locally but has not
been synced to R2.

Known risk shape:

```text
new feature needs a data file
  -> local file exists
  -> local tests pass
  -> Vercel excludes data/**
  -> deployed runtime uses R2
  -> R2 object is missing
  -> preview/prod returns no_data or fails
```

This is not an argument against R2. The issue is release process discipline.
Using R2 for deployed data is acceptable if every new runtime data dependency is
listed, synced, and smoke-tested.

Permanent rule for data-backed features:

```text
No data-backed feature is promoted until:
  1. the local data contract exists
  2. required R2 object keys are documented
  3. the data is synced to R2
  4. deployment smoke checks the feature against preview/prod data access
  5. missing data returns clean no_data/unsupported behavior, not broad fallback
```

Current example:

```text
raw/teams/team_conference_membership.csv
```

was required for opponent-conference support and must exist in R2 for deployed
runtime behavior.

## 7. Docs and return package taxonomy

Return packages exist mainly as agent-to-ChatGPT communication artifacts. Their
original purpose was to provide a copyable summary of what the agent changed
when the agent did not otherwise return enough usable information.

They remain useful as:

- handoff receipts
- evidence packets
- temporary work memory
- source material for the next prompt

But they should not be treated as durable source-of-truth product docs.

Working taxonomy:

```text
docs/
  durable product, operations, architecture, and reference docs

return_packages/
  short-lived handoff/evidence artifacts from execution waves

outputs/
  generated reports and machine/test artifacts

archive/
  old completed planning, return packages, and historical evidence when no
  longer active
```

Rules to consider:

```text
Return packages are evidence, not source of truth.
When long-term behavior changes, update durable docs under docs/.
When a release cycle or workstream is done, archive old return packages instead
of letting them compete with active planning docs.
Prompts should tell agents where return packages belong and when to archive them.
```

Open process question:

```text
Should future agent handoffs use shorter copied summaries instead of committed return package files when no long-term evidence is needed?
```

Potential answer:

```text
Keep return packages for meaningful execution waves, release evidence, and QA
checkpoints. Use shorter copied summaries for trivial changes. Archive completed
return packages on a regular cleanup cadence.
```

## 8. README/product positioning

The README should eventually be refreshed to match the product's current shape.
The current product is no longer only a CLI/API/dev workbench. It is now a
public answer-first NBA stats product with debug/review surfaces preserved.

Potential opening framing:

```text
NBA Tools is a natural-language NBA stats answer engine for stat-shaped
questions across players, teams, records, splits, streaks, leaderboards,
comparisons, and playoff history.
```

README structure to consider:

1. Product promise
2. What questions it is good at
3. What is intentionally unsupported
4. Web UI quick start
5. Developer surfaces: CLI/API/structured query
6. QA/release status pointers
7. Data/deployment notes

This does not need to block the current review, but README should not lag the
product forever.

## 9. Roadmap boundary discipline / feature promotion rules

The product already supports a broad set of query families. Future expansion
should not happen through casual parser-rule additions.

Roadmap boundary discipline is the product-level version of parser-growth
discipline.

Parser version:

```text
Do not casually add phrase rules that can collide.
```

Product/roadmap version:

```text
Do not casually promote new capabilities unless the data, route, UI, QA,
deployment, and docs are ready.
```

New support areas should follow a promotion path similar to opponent-conference
support:

```text
unsupported boundary
  -> preflight
  -> data contract
  -> route/result contract
  -> parser support
  -> raw QA cases
  -> frontend-copy/visual QA if rendering changes
  -> preview/deployment smoke
  -> release docs
```

A permanent Feature Promotion Rules doc should probably be created from this
review. It should require each new supported area to define:

- accepted phrases
- rejected/guarded phrases
- expected route
- expected no-result/unsupported behavior
- required data contract
- result contract expectations
- frontend rendering expectations
- raw QA cases
- frontend-copy cases when copy changes
- visual QA cases when UI/layout changes
- deployment/R2 checks if data-backed
- release-doc updates

The core rule:

```text
No broad fallback answers for unsupported or low-confidence queries.
```

## 10. Naming and product identity

`NBA Tools` / `nbatools` remains the working name for now.

Do not spend hardening-cycle time trying to name or brand the product. The final
name can change later. The current priority is product clarity, correctness,
parser/routing guardrails, data/deployment guardrails, and launch workflow.

Working note:

```text
The name is generic, but naming is not a current blocker.
```

## 11. Public answer product vs debug/workbench scaffolding

The intended product was always a public answer product: a user types a normal
basketball stats query and gets a clean, correct, focused answer.

The debug/workbench surfaces were necessary scaffolding to make that product
reliable, testable, and expandable. They should support the product, not define
it.

Correct framing:

```text
Public answer product was always the goal.
Debug/review/workbench surfaces are support infrastructure.
```

Product UI rule:

```text
Search box first.
Answer first.
Debug/details second.
Review/workbench surfaces for development and QA.
```

## 12. Lightweight product promise/onboarding

The product should teach users what kinds of questions work, but it should not
make the user feel like they have to read instructions before searching.

Good pattern:

- search box first
- helpful placeholder text
- strong starter query examples
- small "good at" hints below the input
- no-result suggestions that teach supported phrasing
- optional/collapsible "What can I ask?" help

Avoid:

- required category selector before search
- large tutorial before the search box
- wall of instructions
- onboarding that makes the tool feel harder to use than it is

Working rule:

```text
Teach through examples and recovery states, not through a required tutorial.
```

## 13. Open questions closure

The open questions from the review have been closed for the current release
cycle:

1. Parser/routing growth guardrails were executed in Wave 1.
2. A permanent Feature Promotion Rules doc was created in Wave 1.
3. Return-package taxonomy and archive cadence were documented in Wave 4; the
   archive sweep itself remains deferred.
4. README product positioning was refreshed in Wave 5.
5. Data-backed feature promotion now requires R2 key and deployment-smoke
   discipline through the Wave 2 checklist.
6. The public answer-context duplication audit was completed in Wave 6.
7. The weekly beta feedback-review routine and handoff were documented in
   Wave 3.
8. The lightweight homepage/product-promise pass was completed in Wave 6 without
   adding required onboarding or a required category selector.

## 14. Closure result

The working recommendation was executed as a six-wave hardening cycle:

```text
1. Parser/routing growth guardrails preflight
2. Feature Promotion Rules doc
3. Data/R2 promotion checklist hardening
4. Feedback review cadence/runbook refinement
5. Docs/return-package taxonomy cleanup
6. README/product-positioning refresh
7. Lightweight product promise/homepage pass
```

Closure evidence:

- `docs/operations/parser_routing_growth_guardrails.md`
- `docs/operations/feature_promotion_rules.md`
- `docs/operations/deployment.md`
- `docs/operations/query_feedback_review.md`
- `docs/index.md`
- `README.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`

The remaining recommendation is to proceed with launch/handoff using the
existing `*_WITH_NOTES` statuses, then handle deferred notes as post-launch work.
