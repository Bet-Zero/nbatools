# Parser/Routing Growth Guardrails

## 1. Purpose and controlling policy

Revised for the owner's 2026-10-15 direction. Preserve correct supported behavior
while delivering reusable interpretation and execution, not an ever-growing set
of sentence exceptions. Read [AGENTS.md](../../AGENTS.md),
[ROADMAP.md](../../ROADMAP.md) and [Feature Promotion Rules](feature_promotion_rules.md).
These instructions do not themselves change runtime, data or test expectations.

Older requirements for routine human acceptance or preserving unsupported behavior
as a permanent feature are superseded by the owner delegation in AGENTS.md. Actual
historical human reviews remain historical. Desired missing capabilities remain
unfinished; invalid/ambiguous/unavailable-data safeguards still matter.

## 2. Principles

Forgive ordinary phrasing. Do not invent meaning. Do not answer a broader or
nearby question merely because one fragment was understood.

Preserve subject identities, record grain, time/sample ordering, condition
ownership, metric and basis, grouping and ranking through the request boundary.
A condition must not change ownership when another clause, split or comparison
is added. Played/did-not-play, injury/status and on-court presence are different
facts; missing participation cannot be silently substituted for injury.

If a meaningful requested clause cannot be resolved or executed, expose the
limitation/ambiguity rather than drop it. Clarification is for real ambiguity,
not a substitute for supporting ordinary wording. A safe temporary refusal can
contain a defect, but cannot close a desired-answer requirement.

## 3. Capability contracts, examples and collisions

Use a compact semantic contract in the existing PR/queue, not a new document per
phrase. State the intended operation and all meaningful subject/sample/condition
combinations in its bounded scope before tuning the implementation.

Include canonical examples, ordinary rewordings/order changes and shorthand,
plus positive controls from adjacent families. Use the existing Raw QA corpus
for durable representative canonical/variant/collision cases and focused tests
for further combinations. Examples specify the concept, not a hardcoded sentence
allowlist. Keep some independent checker wordings out of the maker's tuning set.

Pin intended route/kwargs where they are part of the public/compatibility contract;
more importantly assert intended meaning, execution and result. An intentional
route change must preserve or deliberately extend that contract with evidence.
Route equality alone cannot establish correctness.

Inspect relevant collision groups:

- opponent conference/division versus conference finals or geography;
- team record, independent comparison and actual head-to-head;
- player comparison versus one player's opponent/teammate condition;
- season leaders versus individual games or single-season records;
- ranking key versus event threshold, and top-N versus last-N;
- owned player/team/opponent clauses and multiple named subjects;
- ordinary metric/default wording versus subjective or undefined measures.

For ambiguous overlap, document the chosen meaning or explicit clarification.
Test the neighboring valid reading too. A global phrase rewrite or a new priority
branch must not fix one interpretation while silently changing an unrelated one.

## 4. Positive delivery and separate safety coverage

Required valid questions must remain positive delivery targets until answered
correctly. Do not reclassify them as invalid or change their desired expectations
to refusal just to pass tests. Correct zero/empty answers require sufficient
coverage and independently verified computation.

Separate invalid-input, ambiguity, unavailable-source and explicit-exclusion cases.
Keep relevant temporary refusal regressions until verified support replaces them
intentionally. When crossing a former boundary, replace the corresponding refusal
expectation with proved positive support and retain genuine safety controls.
Document the transition; do not preserve an obsolete refusal forever or erase it
without a working replacement.

A partial match must not widen a sample, substitute a player/team, choose an
invented stat, or return a plausible leaderboard for a different question. A
confidence score is not proof that every clause survived.

## 5. Shared interpretation and code placement

`natural_query.py` is the orchestration layer. Keep substantial route-family
logic, calculations and reusable sample/condition handling in focused modules.
Existing `_lineup_on_off_route_utils.py` is one established extraction pattern;
use existing helpers and adapter boundaries before adding another representation.

For touched consumers, make the requested subjects, grain, predicates, ordered
sample/window, operation and metric basis explicit. Consolidate duplicate
interpretation/capability facts rather than introduce a third registry. Metadata
or a function parameter does not prove that a condition executes.

Deliver a bounded shared path with real positive answers in the same work cycle.
A small typed internal structure is justified when it resolves an observed
ambiguity; a universal query framework is not a prerequisite. Extraction alone,
file size reduction or moving exceptions to a different file is not delivery.

Preserve behavior during pure extraction, including order, kwargs, notes, confidence
and deliberate refusals. Capability changes need explicit before/after evidence.
Keep defensive reparses/compatibility adapters until the invariants they protect
are verified on the replacement. Do not remove safeguards merely for cleaner code.

Repeated findings with the same root cause trigger a lead diagnosis of the
representation/contract, not another cosmetic phrase patch. Optional cleanup is
non-blocking. A known wrong answer never becomes acceptable because review has
already taken several rounds.

## 6. Language alternatives and replacement

A bounded deterministic interpreter or constrained AI translator may be evaluated
on already-verified engine capabilities. Finishing the entire engine first is not
required. Use the same semantic targets, code/data and independent held-out cases.
The incumbent must be measured too; neither AI adoption nor parser preservation
wins automatically.

A model may propose a validated request for the same engine. It must not invent
NBA values, override coverage, or execute unrestricted generated code/SQL. Schema
validity is not semantic correctness. Measure clause preservation, wrong accepted
answers, positive coverage, refusals/ambiguity, latency/repeatability and authorized
cost. Do not tune on holdouts and keep calling them unseen.

No paid access, new credentials or production adoption follows automatically from
an experiment. Preserve existing cost/security boundaries. Record inaccessible
alternatives as untested and continue independent work. Integrate a winning
bounded change through existing contracts/gates, not a second full engine.

## 7. Verification and promotion

Use [Feature Promotion Rules](feature_promotion_rules.md) for the end-to-end bar.
Check intended meaning before deriving expected values. Test selected record IDs,
conditions, counts/rates/denominators, order and scope labels against independent
raw aggregation or controlled fixtures. Two agreeing engine paths are not an
independent oracle. Test data is not evidence of real NBA facts.

During iteration use focused parser/query/engine tests and relevant Raw QA cases.
For high-fan-in parser changes use `make test-preflight` or the appropriate broad
suite on the stable candidate. Preserve route-priority/adjacent-family controls;
use relevant natural-query route-priority corpus cases. Run required numerical
checks against the exact candidate and immutable generation. Required skipped,
empty or informationally failing tests cannot count as acceptance.

Verify the actual API/result payload and changed rendered/deployed answer. Reuse
unchanged renderers with targeted checks; no recurring owner screenshot battery.
Independent checker evidence and machine evidence are separate; a bot invitation,
self-review or historical human field is not current independent acceptance.

Update affected query catalog, data/result contracts and verified current-state
references. Record remaining valid unanswered questions and one exact next action
in the existing active queue, reached through AGENTS.md. Do not create a parallel
phase tracker or use an old rejected-phrase list as the product destination.
