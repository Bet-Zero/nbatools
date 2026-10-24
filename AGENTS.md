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

Read in order:

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

Owner direction updated 2026-10-18: the backup laptop performs NBA acquisition
when necessary; Codex development, testing and analysis stay in the cloud. R2
remains central storage. Commercial source evaluation and cloud NBA access
investigations are stopped; do not request a provider key. Before data-dependent
work, follow `docs/operations/data_availability.md`, read the generated inventory
for the active generation, and distinguish production coverage from staging and
unknown completeness. Produce a bounded collection requirement for missing raw
data; do not invent values or investigate providers repeatedly. The laptop does
not run application development. Existing protected publication remains required.
The October 18 setup acceptance removed that setup dependency. Follow current
owner authorization and the Resume checkpoint's stop/resume state; historical
resumption is not permission to restart paused product work.

## Execution and session continuity

The completion-program README is the sole active queue. Its Resume checkpoint is
replaced with current state, not expanded into a diary. The roadmap keeps durable
direction when this temporary program eventually closes.

- Verify remote, live main, open PRs, current branch/dirty work, and the checkpoint
  before writing. Preserve newer work; never reset or force-push another session's
  branch to match an old snapshot. Resume an existing candidate when appropriate.
- One lead owns integration. Use at most two non-overlapping implementation lanes
  plus independent checking. One active owner handles shared parser/request/service
  changes. Separate hunks in the same semantic path are not independent lanes.
  If capacity is one agent, interleave; do not invent a running team.
- Reproduce the selected defect, define the intended meaning, then implement.
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
  checkpoint with package, actual owner/lane, branch and exact SHA, data generation,
  completed evidence, unresolved findings, and one precise next action. Commit/push
  safe WIP to its task branch where permitted; identify any unpushed work explicitly.
- Keep PR-specific detail in the PR and one short pointer in the queue. Preserve
  reproducible tests and compact durable conclusions when generated artifacts can
  expire. Do not make a private chat, local laptop or ignored output the only handoff.
- Continue authorized work after acceptance within the active session. An access
  or checker blocker stops the dependent acceptance/merge, not independent tasks.
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
Try a bounded source/qualification investigation; in parallel, branch from live
main to extract a semantically independent, reviewable improvement whose normal
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

Fresh NBA acquisition/automatic refresh remains parked under the October 4 owner
decision. Existing-snapshot features, qualified derived metadata, source research
and measured performance work may continue independently. Never relabel old data
as fresh when republishing. Unattended freshness/rollover remains open even when
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
changes. It supplies unfamiliar wording/entities/thresholds and independently
derives expectations from qualified rows or controlled fixtures. Self-review is
not independent. Record reviewer identity/session, revision, data and unresolved
findings in the PR; a bot comment or installed integration is not proof of review.
No counterfeit agent/human approval. If a checker is unavailable, leave one exact
handoff and continue independent work; do not route routine reviewer debates
through the owner. Docs-only planning changes require accurate self-review and
normal checks, not fabricated runtime/independent acceptance.

Use existing commands and runners:

- While iterating: a focused test file or `make test-parser`, `test-query`,
  `test-engine`, `test-api`, `test-output` as appropriate.
- `make test-impacted` is for small localized changes. Testmon is serial, misses
  data/environment/dynamic-import changes, and can overselect. After 60 seconds
  without useful progress, use focused tests or parallel domain/preflight tests.
- High fan-in changes need `make test-preflight` or `make test` on a stable candidate.
  Avoid repeated overlapping full runs per edit. While remote checks run, work on
  independent tasks without moving the candidate being validated.
- `make test-unit` / `test-ci-fast` exclude `needs_data` and `slow`;
  `test-preflight` excludes `slow`; `make test` selects all. Disclose executed,
  skipped and unavailable tests. `fixture_data` and `needs_data` stay separate.
- `make raw-query-answer-qa` is the failing gate, not a report-only run. Use a
  targeted R2 run for changed cases and numerical tests; use full R2/Raw QA/sweep
  at meaningful integration checkpoints. No full remote corpus for a docs edit.
- Required feature-acceptance tests must execute and pass on the candidate/data.
  Empty selections, all-skipped runs, missing required datasets, informational
  failures or a green outer workflow are not acceptance. P0b enforcement landed
  in PR464; continue inspecting underlying jobs/counts for dependent acceptance.
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

Owner updates lead with **Now answers; Still unfinished; Verification; Next;
Needed from you (normally nothing)**. Explain useful examples in basketball terms.
Separate correctness containment, completed capability and operational work.
Keep receipts and coordination in the repo instead of owner homework.

When Graphify is available, use scoped navigation before full reports and refresh
it after code changes. Its installation or expected dirty output is not a new
project dependency. Do not divert capability delivery into graph cleanup.
