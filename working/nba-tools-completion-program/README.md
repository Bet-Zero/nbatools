# NBA Tools capability-completion queue

Execution handoff updated 2026-10-02. Read `AGENTS.md` for the owner delegation
and `ROADMAP.md` for the goal. This is the single active completion queue,
replacing the stale trust-phase status narrative previously in this file.
Historical detail remains in Git history and the linked PRs; this change does
not alter old evidence or imply that unfinished features now work.

## Start here

**Next delivery unit: Q1, recent-game team records.** Reproduce its desired
questions on the current checkout, implement missing behavior, verify the
answers, and proceed through the queue. Do not start another general audit,
create another validation workflow, or ask the owner for examples or approval
to select a technical phase.

The workflow/plan change is not Q1 implementation. All delivery units below
remain open until their own acceptance evidence exists. An existing refusal
expectation is a temporary safety baseline, not a reason to leave a requested
capability unbuilt.

## Verified starting snapshot

Snapshot code: `878ab7e8611c7d7fcf387b1f8b09fc023bdd0dd6`.

- Explicit metric-selection repair: merged, [PR #295](https://github.com/Bet-Zero/nbatools/pull/295).
- Frontend check split and QA-gate integrity: merged, [#296](https://github.com/Bet-Zero/nbatools/pull/296), [#297](https://github.com/Bet-Zero/nbatools/pull/297).
- Production-monitor target repair: merged, [#298](https://github.com/Bet-Zero/nbatools/pull/298).
- Compound-event routing repair: merged, [#299](https://github.com/Bet-Zero/nbatools/pull/299), not still active.
- Advisory remediation/scoping and version work: merged, #300-303 and #308.
- Committed behavioral fixture and remote validation setup: merged, #304-305 and #309-310.
- Local-path repair for two real-data tests: merged, [#311](https://github.com/Bet-Zero/nbatools/pull/311).
- Ordinary main CI passed: [run 36988752207](https://github.com/Bet-Zero/nbatools/actions/runs/36988752207).
- Latest inspected remote data validation: [run 36983673549](https://github.com/Bet-Zero/nbatools/actions/runs/36983673549), code `4953603a2f1c73010009da03f49d7420aebd8ee1`, generation `queue-d-production-0574735-20260716`.
  The 361-case Raw QA expectation gate passed. The filter sweep reported
  98 changed answers, 337 refusals, 42 unchanged/unbadged cases, 44 untestable
  controls, zero LIED and zero ERROR. These are diagnostic classifications,
  not a product success rate. The informational real-data suite had 1000
  passes and two local-path failures repaired by #311.
- No post-#311 real-data confirmation was present in the inspected snapshot.
  Do not claim it occurred. Refresh these pointers when new evidence exists.

The generation name is not proof of data freshness. Inspect actual coverage
when freshness matters. Ordinary CI does not replace real-data verification.

## Validation already available

Use the existing manual `r2-real-data-validation.yml` and `r2-validation`
environment; credentials are already wired. Pass the exact candidate SHA as
its requested ref so all jobs read the same code, and retain the one pinned
data generation. Never print secrets or duplicate workflows/credentials.

At the next relevant integration run, confirm the #311 fix along with the
candidate. That confirmation is not a reason to stop Q1 implementation or to
repeat the full remote corpus for this documentation-only change. If remote
access requires owner approval, identify that exact access step and continue
fixture-backed implementation in the meantime.

## Q1 - Recent-game team records

State: **open; next**. This is a desired-answer task, not a refusal task.

Desired examples (fixed historical season for verification):

- `Lakers record last 10 games in 2023-24`
- `what was the Lakers record over their last 10 games in 2023-24?`
- `Celtics record last 5 games in 2023-24`

Acceptance:

- Return the correct win/loss record over the named team's most recent N
  regular-season games within that season, with the sample/time scope visible.
- Independently select/order the raw game rows and calculate wins/losses;
  compare the returned values and counts. Use fixed fixtures for deterministic
  mechanics and a pinned real generation for NBA numeric confirmation.
- Exercise another team, another N, a shortened available sample, punctuation,
  and unseen wording. Do not claim unsupported qualifier combinations work.
- Preserve ordinary season records and existing meaningful qualifiers. Inspect
  the route and shared filter helpers rather than add a string-specific path.
- Update only the relevant prior refusal expectations after correct support is
  proved; preserve separate missing-data/invalid-input safety tests.
- Verify natural input through API and the existing rendered result, update the
  query catalog, get independent semantic review, and follow merge/deploy rules.

Likely entry points: team record command, natural-query routing/finalization,
shared windows, `tests/test_filter_execution_integrity.py` and existing record
coverage. Choose exact implementation/test files from live code, not this list
alone. Use focused query/engine tests during iteration, the appropriate broad
candidate gate, relevant Raw QA, and remote verification at integration.

## Q2 - Ordinary stat wording and compound player counts

State: **open; follows Q1**. Split into coherent PRs if the causes differ.

Desired examples:

- `games played leaders in 2023-24`
- `3-pointers made leaders in 2023-24`
- `players with most games scoring 30+ and grabbing 10+ rebounds in 2023-24`
- `which players had the most 30 point and 10 rebound games in 2023-24?`

Use the established metric/aggregation semantics, making totals versus
averages explicit in the result. For occurrence rankings, count games meeting
both conditions; do not rank one condition's statistic or a season average.
Check values, ties/order, alternate names/thresholds, and untouched sibling
queries. A phrase already supported is a positive control, not work to rebuild.
Complete the same API/UI/data/regression acceptance path as Q1.

The genuinely ambiguous `players with 25 points and 10 rebounds` does not state
an operation or period. Preserve or improve clarification without pretending
it is the same request as an explicit most-games ranking. No blanket claim
that compound player questions are invalid.

## Q3 - Correct full player names across data conditions

State: **open; may run independently of Q1/Q2**.

Reproduce the wrong-name findings reported in #304. Exact full-name matching
already takes precedence when the data-backed index contains the name; do not
claim universal live failure from the reported incomplete-data case.

Desired examples: `Karl-Anthony Towns stats in 2023-24`,
`Nikola Jovic stats in 2023-24`, plus their accented/canonical variants.

Deliver actual answers for the correct named players where covered. Verify the
identity and numbers, including collisions with Carmelo Anthony and Nikola
Jokic. Under missing/incomplete coverage, prevent a partial alias from returning
another player's stats; that guard is necessary but does not replace the
positive covered-data tests. Do not fix this only by avoiding those players in
the fixture or adding one more special-case alias.

## Q4 - Complete meaningful qualifier combinations

State: **open**. Continues the unfinished work formerly labeled Phase 1C.

Inspect the existing sweep's 42 flagged cases and recorded extra-clause gaps.
Do not turn them mechanically into 42 features: a valid filter can leave the
answer unchanged, and combinations such as a team being 'a starter' may be
ill-defined. Verify intent, dataset coverage, row selection, and calculations.

For coherent desired questions, implement the missing qualifier and keep the
item open until it answers. For invalid/ambiguous combinations, use dedicated
negative/clarification tests. Use discriminating controls and independent
calculations; a changed fingerprint alone does not prove correctness.

Start with legitimate examples already recorded in the repo, such as player
stretch starter/bench scope and minimum-sample constraints where meaningful.
Check record/playoff/decade/stretch routes without treating the old route list
as a reason to ignore related concrete defects. Handle required supported
combinations at their real data grain. Do not automatically build the deferred
Phase 1D receipt framework; use existing shared mechanisms unless a specific
remaining defect makes more structure necessary.

## Q5 - Deliver remaining data-backed answer families

State: **open**. Use existing exploratory samples and documented gaps, not new
owner homework. Start independently where data is available.

Initial order: team bench scoring; team championship history and then player
ring counts with their distinct membership requirements; clutch/period queries;
lineups/on-off and other recorded supported-intent gaps. Reorder for dependency
or verified user value, recording the reason rather than seeking routine
permission. Reuse implemented rookie/sophomore and other families; do not
rebuild them simply because they appear in old plans.

For each family, add a bounded set of desired questions and concrete acceptance
checks to this queue before implementing, then carry data -> calculation ->
natural input -> output -> verification -> deployment through as one delivery
unit. Investigate sources rather than stopping at 'dataset absent'. Do not
infer player rings from a team-only champions table, infer injury status from
missed games, or claim full history from incomplete seasons.

An unavailable source, materially new cost, or access dependency is a concrete
blocker to report, not feature completion. Keep the desired question visible
and proceed with independent work. No unlimited spending or broadening of
credential access is authorized by this queue.

## Q6 - Verify the actual delivered app and operation

State: **open; targeted deployed checks also belong in every prior unit**.

Confirm the deployed revision/dataset, actual current-through coverage, source
refresh and season rollover, and representative API/browser answers. Measure
real response times and fix observed bottlenecks/timeouts; do not soften a
monitor to conceal them. Reuse the existing deployment/monitoring path.

Complete a bounded everyday-question acceptance set drawn from Q1-Q5 and the
existing product promise. Required unanswered questions cannot pass by
refusing. Preserve any open later expansion list and distinguish 'this release
batch delivered' from 'all NBA questions supported'. Naming/domain/launch
publicity decisions are not prerequisites for technical delivery.

## Recording progress without another framework

For each unit, update its state and append a compact result here or link its PR:

```text
Now answers: actual examples and capability.
Still unfinished: desired questions, dependency, and next action.
Verification: code SHA, data generation, numeric checks, API/UI checks,
              applicable tests, independent reviewer (agent or human).
Delivery: PR/merge and deployed verification, or explicitly pending.
Next: exact action; normally no owner action needed.
```

Do not invent review states in existing QA schemas. Agent review is recorded as
agent review in the PR/queue, not as historical human acceptance. Do not mark a
whole unit complete after containment or one passing parser example. Keep the
original desired examples and add representative unseen variations. Do not
remove difficult cases to improve a coverage number.

## Parked maintenance, not a serial prerequisite

Required-check enforcement and monitor retry-policy changes remain separate
maintenance decisions. Keep current blocking checks and security/privacy rules.
Batch low-value docs/version/toolchain housekeeping instead of interrupting
capability delivery. Only advance a framework/refactor task when its concrete
benefit to an active answer capability justifies it.
