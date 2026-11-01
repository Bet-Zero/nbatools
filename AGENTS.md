# AGENTS.md

Instructions for coding agents in `Bet-Zero/nbatools` (NBA Tools, not ScoutZero).

## Product and controlling direction

NBA Tools is a web-based NBA statistics search app. Ordinary basketball questions
should get correct, properly scoped answers. The same engine serves the API and
CLI. **A safe refusal is not implementation of a desired capability.**

Owner direction revised 2026-10-15: preserve the foundation; secure current
correctness/verification gaps; deliver bounded shared interpretation; evaluate
language approaches on verified capabilities; accept a finite deployed core.
The October 2 hands-off delegation and 1996-97+ scope remain. The old four-stream
execution model and indefinite phrase-patch continuation are superseded.

At session entry, read in order (do not reread unchanged material in the session):

1. This file for authority and safeguards.
2. `ROADMAP.md` for destination, sequence and milestone boundaries.
3. `working/nba-tools-completion-program/README.md`, starting at its Resume
   checkpoint, for live work, first action, acceptance and continuation.
4. Only the code, contracts, PR discussions and runbooks relevant to that action.

Current explicit owner decisions control. This file and the revised roadmap
supersede conflicting older workflow/phase instructions. Current code, data and
executed evidence establish behavior; a planning statement does not. Historical
reviews remain historical. Do not use earlier refusal boundaries as permanent
product exclusions or revive a superseded queue from an old branch.

## Owner delegation and completion policy

- The owner supplies intent and optional examples. Agents own prioritization,
  query generation, diagnosis, implementation, data research, numeric checking,
  regression coverage, review coordination and routine technical choices.
- Desired coherent questions remain unfinished when unsupported, unrouted,
  missing data, or safely refused. Record containment separately. A genuinely
  correct zero/empty answer requires sufficient coverage and a valid calculation.
- Negative tests cover invalid input, real ambiguity, unavailable data or explicit
  exclusions. A missing legitimate feature is not a bad input. Preserve safety
  regressions until verified positive support replaces them deliberately.
- Never invent metrics, silently omit clauses, swap subjects, or force special
  wording. Ordinary shorthand, punctuation and grammar variation are not invalid.
- Participation, injury/status and on-court presence are different facts. A missing
  game row does not establish injured; a played row does not establish healthy,
  available or active status. Do not encode those equivalences in code OR tests.
  Qualify absence against relevant team membership and complete participation
  coverage; pre-joining games and unknown data are not verified missed games.
- Ask the owner only for unresolved product meaning, necessary access/consent,
  material new spending, or consequential action beyond authorization. Bring a
  recommendation and minimal exact action, not routine engineering homework.

## Data availability before implementation

### Standing bounded collection and staging authority (owner, 2026-11-01)

The owner approved the reviewed 2026-27 Regular Season collection/staging request
and gave standing authorization for **routine, bounded collection and staging of
public NBA data using existing approved sources, tools, credentials and cost
limits**. Agents own source collection, validation, implementation and testing
and must continue autonomously without asking for approval for each batch.
The existing reviewed GitHub archive/source tools and targeted read-only Actions
route, and the acquisition laptop where appropriate, remain available. This
supersedes older per-batch collection approval, planning-only stops and laptop-only
restrictions for routine bounded work within these approved routes. It is not
permission to invent another access route or expand permissions.

Separate explicit approval remains required for **production publication,
substantial bulk backfills, new costs or credentials, expanded permissions,
destructive operations, or weakened safeguards**. No unattended refresh schedule,
new service or commercial provider investigation is authorized. Keep fixed-plan
limits/$0 metered overage, read-only runtime/validation credentials and the
existing protected publisher/environment approval. Collection/staging acceptance
never activates production or authorizes an active-pointer change.

Before data-dependent work, follow `docs/operations/data_availability.md` and the
active generation's generated inventory. Reuse qualified retained bytes and
accepted evidence; qualify the smallest needed new population, with source URLs,
original bodies, immutable revisions where available, hashes, capture times,
statistical scope and explicit unknowns. A source/index filename, retrieval time
or green transport test does not establish current coverage or completeness.
Do not retry a diagnosed blocked/stale source without changed evidence. Preserve
all numerical/source/clock/membership/readiness/24-hour-lag and production gates;
missing sources remain unfinished work. Do not fabricate a passed manifest or
substitute different data. Cloud development/testing stays in the cloud; the
laptop is acquisition/transfer only, not a development dependency. The single
Resume checkpoint records the bounded active scope, evidence and precise next
step, not a new approval request for each routine batch.

The historical narrow authorities below retain their original evidence and
scope. Their collection restrictions are superseded by this standing authority
where applicable; their production, correctness and cost safeguards remain.

### Narrow K08 report-acquisition exception (owner, 2026-10-27)

The October 27 owner exception authorized acquisition and staging through the proven GitHub
Actions targeted-validation route for **only** the first three official reports
in `working/nba-tools-completion-program/collection-requests/lebron-participation-2025-26.json`:
`0022500019` / `20251024_MINLAL.pdf`, `0022500113` / `20251026_LALSAC.pdf`, and
`0022500122` / `20251027_PORLAL.pdf`. This narrowly supersedes laptop-only acquisition
for those reports. That original exception did not authorize the remaining 17 or other source/identity
requests; subsequent explicit and standing bounded collection authority above now
controls. New credentials, paid services, automatic refresh and production R2
publication remain separately restricted. Reuse original retained bytes for subsequent qualification/replay;
retries need a diagnosed reason. Preserve the existing read-only workflow,
independent source qualification and separately protected publication boundary.

Own acquisition, qualification and implementation across routine PR boundaries
within the active session. A merged PR or unavailable execution route alone is
not a stop: diagnose the specific blocker and advance independent useful K08 work
where possible. Consequential changes retain independent review before merge;
prefer Claude as a separate reviewing model when available within existing access
and cost authority. If unavailable, use a genuinely separate available checker,
record its actual identity/model, reviewed revision and approval; do not invent a
Claude review, new paid access or model availability dependency. Preserve all 46
positive obligations and the participation/membership/injury distinctions.

### K08 historical participation strategy (current owner direction, 2026-10-27)

Target reliable participation coverage from 1997 onward at scale. Audit existing
NBA data first; qualify small representative structured-source samples across
late 1990s, 2000s, 2010s and recent seasons, including Traditional V3, Summary
V3 and historical archives (Summary V2 where supported). This bounded research
and development supersedes the general cloud-source investigation pause for this
assignment; it is not bulk/backfill authority. Endpoint classes, indexed files,
empty inactive lists and missing rows do not establish complete historical data.
Use official PDFs as targeted fallback/corroboration unless executed evidence
shows they are the best practical primary source. Do not expand PDF collection
while selecting the scalable strategy. Preserve the already-completed three-PDF
capture; reuse its originals rather than repeating acquisition.

Deliver and independently verify a bounded working statistical capability, not
only a research/checkpoint document. Establish observed historical coverage,
quality failures, unknowns and exact acquisition requirements before any large
backfill. Keep played, explicit DNP/inactive, qualified same-game association,
verified nonmembership and unknown distinct; do not infer tenure/nonmembership
from roster snapshots or another game on the same date. No bulk acquisition,
production R2 changes, new paid services or credential expansion is authorized.
Continue routine research/development/review/safe merges across PR and route
boundaries within this active assignment, preferring cross-model review for
consequential correctness changes when available under existing authority.

## Execution and session continuity

The completion-program README is the sole active queue. Its Resume checkpoint is
replaced with current state, not expanded into a diary. The roadmap keeps durable
direction when this temporary program eventually closes.

- Verify remote, live main, open PRs, current branch/dirty work, and the checkpoint
  before writing; establish the authorized outcome, acceptance, working revision,
  blockers and applicable prior evidence once. Read only history needed for that
  outcome. Recheck live state at consequential boundaries, possible concurrent
  writes or new uncertainty, not after every command. Preserve newer work; never
  reset or force-push another session's
  branch to match an old snapshot. Resume an existing candidate when appropriate.
- One lead owns integration. Use at most two non-overlapping implementation lanes
  plus independent checking. One active owner handles shared parser/request/service
  changes. Separate hunks in the same semantic path are not independent lanes.
  If capacity is one agent, interleave; do not invent a running team.
- Reproduce the selected defect, define the intended meaning, then implement.
  Inspect affected consumers and use focused tests while editing. Select checking
  by affected behavior and risk, not diff size: a small parser, calculation,
  security or verification-policy edit can require substantial checking.
  Do not restart a whole-project audit, create a new framework/queue, or request
  a fresh owner query battery. If already repaired, verify and advance.
- Before selecting follow-up work, record one brief justification in the existing
  PR/checkpoint: the specific agreed obligation it closes, confirmed defect it
  repairs, or necessary dependency it resolves. If it adds a capability, explain
  why it should precede a named unfinished Core-1 obligation. A category label or
  useful new combination alone is insufficient. Ordinary paraphrases and genuine
  correctness repairs remain required; do not call them enhancements to defer
  them. Keep discretionary discoveries in the queue's existing carry-forward
  section, without a new ticket or owner approval for every observation.
- Track implementation/merge, independent numerical evidence, unfamiliar-language
  evidence and deployed verification separately. Do not close a desired feature
  with a new refusal, parser registration, documentation or a green test total.
- Before a material stage transition, merge, block or session stop, update the
  checkpoint only when continuation changes, with package, actual owner/lane,
  branch and exact SHA, applicable data generation,
  completed evidence, unresolved findings, and one precise next action. Commit/push
  safe WIP to its task branch where permitted; identify any unpushed work explicitly.
- Keep PR-specific detail in the PR and one short pointer in the queue. Preserve
  reproducible tests and compact durable conclusions when generated artifacts can
  expire. Do not make a private chat, local laptop or ignored output the only handoff.
- Use a PR comment for final execution/landing receipts when another checkpoint
  commit adds no continuation value; link detailed evidence instead of duplicating
  it across documents, PR text and owner updates. No update after every test.
- Continue only within the current authorized outcome. When that outcome and its
  applicable gates are satisfied, deliver and stop; useful discoveries do not
  automatically authorize another task. An access or checker blocker stops the
  dependent acceptance/merge, not already authorized independent tasks.
  No fresh owner prompt is needed at every routine package boundary. Do not claim
  background execution without an actual running service.

### Avoid idle turns and blocked-branch deadlocks

A Codex turn, a PR comment, and GitHub Actions do not themselves provide a
continuously running coding agent. While an authorized interactive goal is active,
advance to the next independent delivery step rather than concluding after
publishing a checkpoint or seeing an expected blocked CI run. An actual scheduled
thread wake-up must be configured in Codex/ChatGPT; repo text cannot create one.
Do not claim a heartbeat, running agent, or background continuation that has not
been verified. Use one active writer for shared semantics; avoid overlapping
scheduled runs and unnecessary metered work.

When a candidate has a stable, independently confirmed unmet requirement caused
by absent qualified source data, record it once with its exact failing tests and
source dependency. Do not rerun identical broad suites, spend the next turn
re-explaining the block, or pile unrelated green features into its perpetually
red branch. Preserve every unmet positive obligation and its failing evidence.
Within existing authorization, try a bounded source/qualification investigation
or branch from live main to extract a semantically independent improvement whose normal
CI and required numerical gates actually pass. Check dependencies before
porting any code; if inseparable, choose another independent P1/O task instead.
Never change desired positives to refusal/xfail/skip, suppress a gate, or merge
a knowingly incorrect behavior just to make progress appear continuous.

A successor checks the task PR linked from main's Resume checkpoint, then live
open/recently updated PRs for a newer handoff. Read the existing README at that
pushed branch revision and reconcile its PR evidence and current owner decisions.
When stopping on an unmergeable branch, link that branch checkpoint and exact SHA
from its PR so it is discoverable without a separate documentation merge. Never
merge failing runtime to publish a handoff. At the next safe independent merge,
synchronize a compact pointer back to the sole queue on main. No second tracker.
Before any unavoidable turn end, record whether the stop was normal task
completion, missing source, checker/access/approval, runtime error, usage limit,
or actual scheduled wake-up;
name exactly what can proceed without owner intervention. Turn completion is
not project completion.

## Architecture and improvement rules

Keep the Python service, established calculations, result types, React interface,
immutable generations and useful tests. Computation, filters and interpretation
belong in the engine; UI and CLI remain thin consumers.

- Deliver shared semantics with real consumers, not an abstraction first. Preserve
  explicit subjects, record grain, sample/window ordering, condition ownership,
  metric/basis, grouping and ranking through the existing parse/execution boundary.
- Use existing fields/helpers first; add a small typed internal structure only
  when it fixes a demonstrated ambiguity. No universal QueryPlan prerequisite,
  third capability registry, whole-application rewrite or cosmetic extraction wave.
- `natural_query.py` orchestrates. Keep substantial family logic/computation in
  helpers. Extend shared conditions instead of repeated phrase-specific rewrites
  or route allowlists. Splitting files without better delivered behavior is not P1.
- Repeated review findings with the same root cause require diagnosis of the
  shared representation/contract, not a third cosmetic patch. This never permits
  merging a known wrong answer. Optional cleanup remains non-blocking.
- Read `docs/operations/parser_routing_growth_guardrails.md` and
  `docs/operations/feature_promotion_rules.md`. Preserve contracts unless extending
  them intentionally, update consumers, and align verified behavior references.
- Evaluate a bounded language alternative once the chosen engine subset is
  verified. Do not wait for every statistical feature; do not assume a model wins.
  Models cannot invent NBA values or execute unrestricted generated code/SQL.
  Paid access or production adoption still requires existing cost/access authority.

## Data, freshness and publication

Preserve raw/processed/derived layers and each dataset's grain. Every extension
needs source, row meaning, join keys, verified coverage/trust rules, storage,
consumer and honest missing-data behavior in `docs/reference/data_contracts.md`.

Use configured data sources, a fixed code revision and one immutable generation
for comparisons. Fixtures are not NBA evidence and must never be published as
real data. Existing, derivable, missing and unverified inputs are different.
Do not infer complete careers, absence, official rings or injury from incomplete
or differently scoped source facts.

Routine bounded public NBA collection/staging follows the November 1 standing
authority above; the October 4 acquisition pause is superseded within that scope.
Automatic refresh remains unapproved. Existing-snapshot features, qualified
derived metadata and measured performance work may continue independently. Never
relabel old data as fresh when republishing. Unattended freshness remains open when
the finite snapshot milestone is accepted. Follow `docs/operations/deployment.md`
for validated publication, same-base protection, last-good/rollback and deployed
checks. Runtime/validation credentials stay read-only; write authority is separate.

## Verification and independent review

Tests protect delivery; totals and expected refusals are not completion scores.
Meaning is checked before expected numbers: independent arithmetic of the wrong
sample is still the wrong answer. Check clause/subject ownership and sample row
IDs as well as values, counts, ordering, denominator, labels and actual output.
Natural/structured agreement alone is not an independent oracle.

A separate checker verifies material query, computation, data or validation-gate
changes, including changes to how verification obligations are satisfied. For
policy changes, check coverage equivalence, invalidation, safety and instruction
conflicts; do not rerun the application without an executable reason. For query
changes, it supplies unfamiliar wording/entities/thresholds and independently
derives expectations from qualified rows or controlled fixtures. Self-review is
not independent. Record reviewer identity/session, revision, data and unresolved
findings in the PR; a bot comment or installed integration is not proof of review.
No counterfeit agent/human approval. Ordinary prose/cosmetic changes need accurate
self-review and normal checks, not separate semantic review unless they affect
meaning, behavior, authority or another applicable review requirement. Unavailable
review/access blocks dependent acceptance; leave one exact handoff, never
self-approve. Avoid identical failed invocations; retry only with a reason to
expect a different result. Do not route routine reviewer debates through the owner.

The author owns focused reproduction, implementation checks and required coverage
missing from automation. CI owns the standard checks it actually executes. The
checker owns independent judgment of affected meaning, selected data, arithmetic
and other material risks. The integration lead confirms evidence applicability
and resolution of blocking findings; it does not automatically repeat checker
arithmetic, artifact inspection or test execution. Green CI alone is not review.

Before broad validation or final independent review, freeze the relevant candidate.
Use an isolated checkout/worktree if another writer or task could move it. Do not
edit, merge, rebase or switch that checkout while checks run. Independent work
must use isolated state and already be authorized; do not invent work to fill waits.
During finalization, fix actual blockers without adding optional instrumentation,
stronger acceptance or adjacent features. Retain material follow-ons in the
existing appropriate location.

Reuse existing PR/commit/run evidence only when it covers the required behavior
and assertions, relevant code/dependencies/configuration/data/execution conditions
are unchanged or demonstrably unaffected, required checks actually ran and passed,
no unresolved finding or contradiction invalidates it, and release/exact-candidate
requirements remain satisfied. Check applicability once on selection and again
when something relevant changes. Identify the original revision and why reuse
applies; never claim an old execution happened on a new head or that matching
workflow names make another PR's green result applicable.

If a repair changes reviewed semantics or risk, repeat affected checks and review
(a focused delta review where sufficient), plus required exact-head gates. No hard
limit on justified review rounds; no repeat review of unchanged material solely
for reassurance. Receipt/checkpoint-only changes do not automatically invalidate
unchanged semantic evidence or waive required final-head CI. Final acceptance
identifies the actual candidate and reused evidence.

Consume existing structured summaries for candidate/generation, checks actually
executed, selected/executed/skipped counts where needed, conclusion and unresolved
findings. Once applicable success is established, record a compact link and move
on. Open detailed logs, raw outputs or artifacts for failures, contradictions,
incomplete/untrusted summaries, specific independent-review needs or concrete
integration questions, not routinely for every passing case. Use completion
signals or appropriately spaced status checks; do not repeatedly fetch unchanged
full logs or narrate waiting. Advisory failures stay advisory unless new evidence
establishes a relevant blocking problem; report them without unrelated repairs.

Use existing commands and runners:

- While iterating: a focused test file or `make test-parser`, `test-query`,
  `test-engine`, `test-api`, `test-output` as appropriate.
- `make test-impacted` is for small localized changes. Testmon is serial, misses
  data/environment/dynamic-import changes, and can overselect. After 60 seconds
  without useful progress, use focused tests or parallel domain/preflight tests.
- High fan-in changes need broad coverage equivalent to `make test-preflight` or
  `make test` on a stable candidate. Valid hosted evidence can satisfy it; an extra
  local run is not mandatory. Compare actual selected tests, configuration,
  relevant code/dependencies, data generation and execution conditions. Fast or
  data-free CI is not automatically equivalent to preflight or authenticated
  numerical validation. Run missing required pre-merge coverage once through an
  existing suitable route; future main/nightly results cannot bypass that gate.
- `make test-unit` / `test-ci-fast` exclude `needs_data` and `slow`;
  `test-preflight` excludes `slow`; `make test` selects all. Disclose executed,
  skipped and unavailable tests. `fixture_data` and `needs_data` stay separate.
- `make raw-query-answer-qa` is the failing gate, not a report-only run. Use a
  targeted R2 run for changed cases and numerical tests; use full R2/Raw QA/sweep
  at meaningful integration checkpoints. No full remote corpus for a docs edit.
- Required feature-acceptance tests must execute and pass on the candidate/data.
  Empty selections, all-skipped runs, missing required datasets, informational
  failures or a green outer workflow are not acceptance. P0b enforcement landed
  in PR464; confirm required jobs/counts through trustworthy summaries, opening
  underlying details when needed under the result-consumption rule above.
  Never demote a failing required test to exploratory to obtain a green result.
- Frontend changes need locked install/build/lint/tests and rebuilt served assets.
  Inspect actual changed rendering; unchanged renderers need targeted output checks,
  not a fresh owner screenshot tour. Track implementation and deployment separately.
- Docs-only work: `make docs-governance` and `git diff --check`. CI's narrow
  planning-document path still runs delivery-policy tests, lint and both security
  verdicts. Other documentation, executable inputs, helpers, mixed or unknown
  changes retain application checks; do not broaden the allowlist by file suffix.

## CI, cost and merge safeguards

Preserve `.github/workflows/ci.yml` checks: lint, docs-governance, frontend-verify,
blocking production frontend-security, informational whole-tree frontend-security-dev,
test-fast on application-impacting PRs and test-full on application-impacting main
pushes; nightly/manual runs always select the full suite. Full includes fast, so
do not run both matrices on the same main/nightly candidate. Scope failure remains
blocking and conservatively selects application checks. Unselected jobs are not
new executed acceptance. Follow `CONTRIBUTING.md` for the exact selection. Do not suppress
failures, remove backstops, raise audit/latency thresholds or weaken assertions.
Dev advisories remain maintenance, not automatic unrelated feature blockers.

Ordinary CI stays secret-free. Use the existing R2 workflow and its dedicated
`r2-validation` environment. Under the owner's 2026-10-15 authorization, agents
may push a reviewed candidate plus a bounded manifest-only request commit to a
fresh `r2-validation/**` branch to start targeted validation automatically; follow
`docs/operations/deployment.md`. Manual dispatch/full validation remain available.
The request's parent/SHA checks bind source identity, not review approval: agents
must still obtain and record independent review before requesting validation.
This path does not authorize new credentials, broader permissions, duplicate
workflows, secret printing, or branch-protection changes. Keep fixed-plan limits,
$0 metered overage, disabled public query-feedback persistence and separate
publication authority. No new paid service/hosting migration by implication.

Use one PR per logical unit. Before merging, require all applicable blocking CI,
actual required numerical results and independent semantic review where needed;
GitHub's technical ability to merge is not permission to bypass them. Inspect the
current head/base and revalidate materially changed integration. Routine accepted
merges need no additional owner approval. Check post-merge CI and deployed behavior
when affected; leave unfinished verification open. A red advisory is reported as
advisory, not hidden or confused with a blocking failure.

## Documentation and owner updates

Current behavior belongs in `docs/reference/`, architecture in `docs/architecture/`,
policies/runbooks in `docs/operations/`, historical audits in `docs/audits/`. Keep the
docs index current when adding/moving durable docs. Follow
`docs/operations/working_and_archive_policy.md`; do not create another status system.
Update affected catalog/current-state descriptions from evidence, not intentions.

Raw QA human-review fields keep their literal historical meaning. Inspect relevant
product-review outputs and record agent checking in the PR; legacy
`human_review_pending` alone is not a routine engineering stop. Never invent
`human_review_complete`, a named human reviewer or a schema state. Launch/branding
remain separate owner decisions.

For product delivery, owner updates lead with **Now answers; Still unfinished;
Verification; Next; Needed from you (normally nothing)**. For bounded operational
work, lead with its outcome, verification and remaining blocker, if any. Explain
product examples in basketball terms; do not narrate each routine check or wait.
Separate correctness containment, completed capability and operational work.
Keep receipts and coordination in the repo instead of owner homework.

When Graphify is available, use scoped navigation before full reports and refresh
it after code changes. Its installation or expected dirty output is not a new
project dependency. Do not divert capability delivery into graph cleanup.
