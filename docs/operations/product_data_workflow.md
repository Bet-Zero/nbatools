# Independent product development and data-quality cleanup

Owner-approved operating policy, **2026-11-05**, for **Bet-Zero/nbatools only**.
This changes development sequencing, not accuracy standards. It supersedes older
readiness-only/K08-paused continuation instructions. K12 cold-start work remains
parked. The [main queue](../../working/nba-tools-completion-program/README.md)
remains the product/integration authority; the data exception worklist is subordinate.

## The two workers

**Agent 1: product and acquisition.** Build the app, identify known data needs by
source family/season/type/grain, collect bounded missing inputs through existing
approved routes, preserve originals, normalize and run initial validation. Record
failures without hiding them. Continue app work using stable data contracts and
explicitly identified inputs. Do not become the investigator of every anomalous
NBA event. An obvious bounded fix may be completed immediately; lengthy source
reconciliation belongs to the exception worklist.

**Agent 2: data quality.** Claim a coherent exception group, investigate the exact
source or calculation discrepancy, preserve evidence, independently validate a
correction, and produce a new portable data version. Group common causes rather
than launch a worker or PR for each cell. The worker can start whenever useful;
it does not have to run simultaneously with Agent 1, and app progress does not
require an empty backlog. A data worker is not automatically the independent
reviewer of its own corrections.

These are roles for real, separately launched sessions, not one agent switching
tasks and calling that concurrency. Repository text does not launch a worker,
install a scheduler or keep a stopped session running. Use existing authorized
agent capacity; do not create a new orchestration service or paid access.

## Acquisition and validation boundaries

Record four distinct states, never one undifferentiated `passed` label:

| State | Meaning | Permitted use |
| --- | --- | --- |
| Received | Original response retained with exact request, identity and byte provenance | Evidence storage only until safe parsing/contract checks pass |
| Development-usable / provisional | Safe, interpretable, correctly identified data with validation status and known failures attached | Opt-in isolated development, not a verified real-NBA answer |
| Qualified for a stated scope | All required source, numerical and completeness checks for that scope passed with review | Qualified consumers; not automatically production-published |
| Published / accepted | Separately authorized generation and its required release/live gates passed | Existing production contract |

An incorrect but readable value can be provisional. Corrupt ZIPs, unsafe paths,
ambiguous identities, incompatible schemas and unparseable inputs cannot be fed
to the app merely because transport succeeded. Preserve them outside usable data
and register the actual collection/contract blocker. A missing row or field is
not an acquired value; use a labeled fixture for development rather than fabricate
NBA facts. Report field-level status where needed instead of condemning an entire
game for one unrelated bad field.

Run the existing extensive validators; keep their real failures and original
requirements. After initial validation, route unresolved data discrepancies to the
worklist and continue independent work. Do not weaken validators, fabricate green
manifests, change required positives to skips/refusals, or repeatedly replay the
same failing corpus. A known data failure can remain open while correctly scoped
application code merges; it cannot be cited as passing data/feature acceptance.
A failing software assertion or changed verification policy still needs its normal
repair/review and mandatory gates. Select evidence by actual dependencies, not by
relabeling failures as optional.

Plan predictable requirements upfront: whole games, quarters, halves, overtime,
Advanced, events, roles and other requested families. Reuse the inventory, source
cache and existing source-family plan; do not acquire blindly or start a historical
bulk backfill. Separate known missing inputs from unexpected source contradictions.
Statistical quality failures do not halt unrelated collection. Keep existing
transport pacing, error handling, retry authorization and integrity caps unless a
separately reviewed collector change is actually needed. A laptop launch may be
necessary for blocked cloud sources; prepare one bounded reusable package, with no
owner coding or source selection. Never recollect a successful request by default.

## Development isolation and honest tests

Provisional data is explicitly allowed for development, including displaying a
source-reported 23 PPG that may later be corrected to 25. That proves the flow can
operate, not that the NBA result is verified. The engine must still calculate the
right result from the selected input rows, interpret clauses correctly and render
honestly; uncertainty in data must never excuse a software bug.

Agent 1 must prove these controls before a provisional-data demonstration:

- Explicit development-only opt-in, a pinned dataset/version/hash, and a distinct
  data root. No fallback to provisional inputs for public/production execution.
- Clearly visible UI and machine-readable API/export status, data version and
  relevant exception/coverage references. Derived outputs inherit uncertainty
  from any input they depend on. Do not silently omit flagged rows, fill nulls
  with zero or average a different sample and present it as the requested answer.
- Keep original reported, corrected and unknown values distinguishable. Do not
  restore PR582's 484 nulls merely to get numeric output. A separate labeled source
  view may exercise existing reported values; unavailable values stay unavailable.
- Verify software interpretation/arithmetic against controlled fixtures and
  already-qualified examples, separate from real-source qualification. Preserve
  independent held-out/semantic checks and exact selected sample/denominator.
- Test that opt-in cannot affect production, configuration cannot leak across
  environments, production rejects unqualified input, and strict validators still
  reject the known bad cases. No new environment flag is claimed implemented by
  this policy document alone.

Prefer local/isolated development. A hosted preview is not automatically private;
use provisional data there only after verifying existing access protection and
isolation. Do not weaken access, change Vercel configuration or expose unqualified
answers publicly to save time. No production dataset or active pointer change is
authorized. Final numerical/R2/consumer validation, 24-hour due-game requirements,
protected publication, live verification and backup remain unchanged.

## Durable exception worklist

Use [data-quality/README.md](../../working/nba-tools-completion-program/data-quality/README.md)
and its versioned entries, linked to existing exact evidence ledgers. This is a
small repository worklist, not a database, dashboard or new agent framework.
Initial entries refer to PR582's 484 unknown keys/20 groups without copying or
renumbering those scientific observations. Group tickets may share dependencies;
do not add their overlapping counts as if each were a separate failed value.

Each new failure needs a stable ID and fingerprint, dataset version/source hashes,
exact affected key/filter or immutable manifest reference, failed check and reason,
consumer impact, original/derived basis, status, required next evidence, owner/claim
and last attempt, plus resolution/reviewer/version when qualified. Deduplicate
repeat failures against the same unchanged source; link new evidence/version to
the original issue. Group by root cause when justified.

Statuses: `open`, `claimed`, `blocked_evidence`, `ready_for_review`, `resolved`, or
`superseded`. Resolution requires correction evidence, affected-vector checks,
independent review and an actual output version. Neither an agent's confidence nor
a green CI run resolves a source problem. Reopen if later source evidence or
schema/basis changes invalidate the proof; retain the original history.

Agent 1 writes intake at the point of failure. Agent 2 claims a group before
investigation and records only meaningful findings/status changes. Do not ask the
owner to maintain IDs, coordinate files or interpret NBA credit methodology.
Block evidence-only work when genuinely exhausted; do not repeatedly launch it to
produce the same blocked report. Source authority is field-specific: shared upstream
provenance is disclosed, not falsely labeled independent or treated as an automatic
rejection of every official scorer fact. PR582's reviewed decisions remain valid
unless new evidence invalidates them.

## Concurrency and correction integration

Use separate branches/worktrees and immutable read snapshots. Agent 1 owns app
code, request/loader contracts and the main checkpoint. Agent 2 owns claimed
exception entries, source evidence and correction-data candidates; its own
handoff lives in data-quality. Different hunks in a shared semantic file are not
independent ownership. If a shared validator, normalizer or schema change is
needed, make a bounded dependency for Agent 1/integration; do not edit it concurrently.

Merge against the actual current base with conflict checks. A correction records
stable row/field keys, prior source/version/basis, expected old value, new value,
justification, provenance and affected derived outputs. If upstream refresh changes
those preconditions, flag a conflict; do not replay the patch blindly or replace a
newer official correction with an older one. Regenerate affected derived outputs,
invalidate version-aware caches and run focused regressions before qualification.
Agent 1 adopts the new version at a safe test boundary, never mid-run. Only work
that truly depends on a missing contract/input waits; unrelated work continues.

Originals, normalized portable CSVs, correction/provenance records and app code
stay separate. Corrections are data, not historical player/game conditions in
application runtime. Evidence-specific investigation scripts are permitted; do not
turn them into the routine per-game acquisition architecture. Do not broadly
repackage all tools merely to achieve purity. PR582 documents existing preparation
package coupling; retain it as nonblocking technical debt unless it prevents reuse.

## Launch, stop and escalation

Launch Agent 1 now for the workflow foundation plus a real bounded app outcome.
The next implementation checkpoint must demonstrate safe provisional development
and durable deduplicated failure intake; it must not wait for all 484 unknowns.
Agent 2 can start as soon as task ownership and pinned inputs are available, before
Agent 1's app feature is finished, or later in a batch. Start one data worker for
shared dependencies, not one per anomaly. With one usable agent slot, prioritize
product work and run a data batch at a natural boundary. Keep the backlog durable.

An initial Agent 2 run may establish source feasibility once; already exhausted
external-evidence cases sleep until a concrete new source/definition is available.
No timers or automatic relaunch schedule are installed here. Use the ready launch
prompt in the data-quality directory when an actual second session is started.

Agents handle routine research, validation, implementation, review and safe merges
under standing authority. Escalate only a concrete owner-only action: necessary
login, specific permission/spend/access choice, protected publication, or unresolved
product meaning. Public-source discovery alone is not an owner decision. Report
what was tried, the exact limitation and smallest recommended action; meanwhile
continue independently authorized work. No vague "source-holder decision" that
leaves the owner to design the next technical step.

At session end state what actually ran, what was tested using fixtures versus NBA
data, what is qualified versus still provisional, the next independent action, and
whether another worker is running or stopped. Do not claim background execution
from a saved checkpoint. Finish bounded coherent outcomes, not one PR per cell;
reuse applicable evidence and avoid unnecessary full-suite repetition.
