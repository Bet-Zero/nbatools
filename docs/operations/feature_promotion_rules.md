# Feature Promotion Rules

## 1. Purpose

Deliver desired NBA-statistics capabilities end to end, with evidence that the
answers are correct. This policy implements the owner's 2026-10-02 direction:
a required question is unfinished until it answers correctly. Temporary safe
refusal is containment, not feature completion.

This policy does not itself change runtime behavior, data, corpus expectations,
or historical acceptance. Read [AGENTS.md](../../AGENTS.md) for delegation and
[parser guardrails](parser_routing_growth_guardrails.md) for implementation
structure. Older manual-acceptance instructions do not make the owner the
routine technical reviewer under this delegation.

## 2. Working principles

- Forgive ordinary phrasing; do not invent meaning, replace the subject/stat,
  or drop conditions.
- Separate desired-answer requirements from invalid-input, genuine ambiguity,
  explicit product-exclusion, and unavailable-data safety checks.
- Missing implementation or data for a desired question is a delivery gap,
  even when a regression test correctly preserves its temporary refusal.
- A verified zero count or empty result is an answer when coverage and the
  calculation are sound. A system error or absent dataset is not that answer.
- Complete reusable capabilities, not lists of hardcoded sentence exceptions.
- Scale the checks to the change. Reuse existing data contracts, result types,
  renderers, test runners, and evidence. No separate document, approval, or
  workflow is required for each step below.

## 3. The promotion path

```text
desired questions -> baseline and gap -> reuse/add data and calculation
-> natural input -> verified answers and regression tests
-> rendered/deployed checks -> truthful shipped documentation
```

### 3.1 Unsupported boundary

Record current behavior and the desired answer. This is a baseline, not a
mandatory refusal milestone. If a wrong answer must first be contained, record
the containment separately and continue toward implementation. Do not label an
ordinary desired question a negative input because the app currently refuses it.

### 3.2 Preflight

In the existing queue item or PR, state the examples, intended meaning, needed
data/calculation, reusable components, and acceptance checks. Agents resolve
technical choices. Ask the owner only for genuinely unresolved product intent,
necessary access, new cost, or consequential actions outside authorization.
Do not manufacture a separate planning phase for an ordinary feature.

### 3.3 Data contract

Reuse the documented source/grain/keys/coverage where possible. For new data,
define them and the consumer in [data contracts](../reference/data_contracts.md).
Keep raw/processed/derived layers distinct. Investigate a missing source; do not
stop at 'dataset absent'. Do not fabricate coverage, historical completeness,
injury status, or membership. Blocked dependencies remain open and must not stop
independent feature work.

### 3.4 Route / result contract

Use the correct computation and data grain. Keep subject, ranking operation,
event thresholds, qualifiers, and period separate. Verify every meaningful
condition reaches and affects the intended computation; a condition need not
change the numeric answer on every sample to have been applied.
Reuse result sections; extend consumers when an extension is necessary.

### 3.5 Parser support

Support the concept across full questions, fragments, shorthand, and reasonable
variations. Test adjacent-route collisions and preserve supported behavior.
A technically readable fragment is not permission to answer a different query.
Genuine ambiguity calls for clarification or explicit supported choices, not
silent invention. Follow the shared route-finalization structure in the parser
guardrails; do not launch a parser rewrite without a concrete delivery reason.

### 3.6 Raw QA cases

Use the existing corpus and runners. Add explicit positive assertions for the
capability, including independent expected values, scope and row membership or
counts where appropriate. Derive expectations from qualified data/reference
calculations, not by copying the application's current output.

Keep negative and temporary unavailable-data regressions separately identifiable.
When implementing a previously refused desired question, replace its refusal
expectation only alongside demonstrated correct support and retain appropriate
missing-data/invalid-input checks. Do not bulk-relabel old cases or weaken the
gate. Test unfamiliar variants and positive controls beyond the examples used
while implementing. `ok`, no crash, or changed output alone is not correctness.

### 3.7 Frontend-copy / visual QA when rendering changes

Inspect the real displayed answer, scope, and table. Changed layout/copy needs
relevant frontend tests and browser checks. Reused unchanged renderers need a
targeted output check, not a repeated full screenshot review or owner approval.
Rebuild served assets after frontend changes.

### 3.8 Preview / deployment smoke

Verify the capability through the actual API/browser path. For changed data,
follow [deployment operations](deployment.md#data-backed-feature-promotion-checklist):
required keys, validated immutable generation, deployed availability, feature
smoke, and honest unavailable-data handling. For unchanged data, cite/recheck
the existing applicable generation rather than publish a duplicate.
Record implementation and deployed verification separately if one is pending.
Do not count an undeployed feature as verified live behavior.

### 3.9 Release docs

Update affected verified-behavior documents, especially the query catalog.
Do not advertise examples until verified. Update the same active queue on merge
with the next action. Keep historical acceptance attached to its original
revision/artifacts rather than relabel it as current.

### 3.10 Validation and evidence conventions

Use focused tests during iteration and appropriate broader candidate checks at
integration. Run the existing failing Raw QA command for the relevant cases;
use its full corpus at meaningful query/data checkpoints, not every docs edit.
Use one exact code revision and one pinned dataset for comparisons. Disclose
skips, missing access, and unverified numeric/deployed behavior.

A checker independently examines material semantic/data changes and checks
answers against data. Record agent review as agent review, not human acceptance.
Existing Raw QA human-review states retain their literal meaning; an old
`human_review_pending` label alone is not an owner dependency or engineering
stop. Do not invent unsupported schema states or counterfeit human receipts.

## 4. Per-feature contract

Use one compact record in the existing queue item/PR:

- Desired examples and the complete meaning they must answer.
- Reused/new data and calculations; real dependencies or exclusions.
- Positive numeric/scope/output checks, unfamiliar variants, and relevant
  negative/collision regressions.
- Actual test/review results, code revision, dataset, and deployment status.
- Still-unanswered desired examples and exact continuation, if any.

A desired-answer requirement cannot pass with refusal, missing data, or a
renamed boundary. A coherent blocked feature remains open. A separate
containment PR can merge when needed without closing that feature.

## 5. Worked example - opponent-conference team record

Desired question: `Celtics record against the East`.

The capability needs the team's game results and reliable season-specific
conference membership. It must select the correct opponents and calculate
wins/losses, rather than use the overall team record. Verify selected rows and
numbers independently, ordinary phrase variants, correct displayed scope, and
deployed data availability. Reuse the existing record renderer.

A season lacking trusted membership needs honest missing-coverage behavior,
but that safety test does not implement historical coverage. Keep the desired
historical capability open while a reliable source/backfill is developed.
The [deployment runbook](deployment.md) contains the existing detailed example.

## 6. Promotion stop conditions

Stop unsafe execution, not routine delivery, when an action would fabricate
numbers/coverage, drop required meaning, leak secrets, damage data, or exceed
access/spending authorization. Resolve a technical gap or split independent
work without a new owner planning session. Scope changes must not remove
desired capabilities merely to match current passing tests.

A failed check requires diagnosis and repair. Do not soften it to declare the
capability done. Optional refactoring, additional evidence machinery, and
unrelated maintenance are not automatic blockers.

## 7. Non-goals

This policy does not require a new test platform, parser rewrite, category
selector, receipt architecture, repeated owner QA, or one preflight document
per code change. It does not enable public feedback persistence or change its
privacy/consent requirements. Task artifacts follow the
[working and archive policy](working_and_archive_policy.md).

## 8. How this doc is used

Agents apply this path to finish capabilities, not to explain why they remain
unsupported. Reviewers assess correct useful behavior and material evidence.
Owner updates lead with newly answered questions and explicit remaining work;
implementation detail stays in the change record.
