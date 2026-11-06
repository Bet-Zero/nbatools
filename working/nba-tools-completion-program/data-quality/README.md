# Data-quality exception worklist

Owner-approved **2026-11-05**. This is Agent2's subordinate data backlog, not a
second app roadmap. Agent1's current direction remains in [the main checkpoint](../README.md).
Read [the workflow](../../../docs/operations/product_data_workflow.md) before acting.
A saved work item does not mean an agent is running.

## Seeded state after PR582

The portable staged snapshot has647/647historical windows and16structural passes.
Original disputed rates:953/1,365qualified,412unknown, plus72newly withheld values
= **484 unknown keys /20groups**. These exact keys stay in the existing
[remaining-dependencies ledger](../source-evidence/rollover-2026-27/official-gamebooks-20261105/remaining-dependencies.json)
at commit `fca90ab50ddb446d1247a80c8bfe4efda269e8e4`, blob
`de64df067b1b485501692f71a7f0212443f9a08a`.

These are three shared evidence tasks, not484manual fixes. Their populations
can overlap; use the authoritative key ledger for totals. All three are currently
**blocked_evidence / unclaimed** as seeded; read each entry for current status.

| Work item | Exact next evidence | Launch guidance |
| --- | --- | --- |
| [DQ-001](DQ-001.json) | Attributable exceptional FT trip/use/exposure and joint FT/turnover methodology for0091/0118/0121 | One bounded attempt at genuinely new attributable sources; stop if still unavailable. Do not restart the old method search without a specific new lead. |
| [DQ-002](DQ-002.json) | 0118Q4 incomplete-award/violation ruling | May be solved by the same method/source package asDQ-001; do not double-count affected rates. |
| [DQ-003](DQ-003.json) | 0009 EasonQ1 2:15FG/2:06FT association and credit | Preserve both clocks; require attributable evidence, not a guessed and-one. |

| [DQ-004](DQ-004.json) | Resolved: authenticated owner3article originals, finite membership chain and all eligible game IDs independently qualified | Agent1 [PR590](https://github.com/Bet-Zero/nbatools/pull/590): full-season historical staged acceptance81eligible/72played/9explicitDNP,unknown0; hosted5/5required and4stagedRawQAcases passed. Feb9date-onlyunknown preserved. No production publication or repeated download. |
| [DQ-005](DQ-005.json) | Native independent scorer bodies for both complete team vectors;4JSON originals now retained | Agent2 [PR588](https://github.com/Bet-Zero/nbatools/pull/588), evidence-only closeout; blocked_evidence/stopped and nonblocking for app development. No correction or app defect established; canonical margins already derive scores. |

**Do not reopen resolved0142,0138,0009AST or0160timing** merely because an older
handoff says blocked. PR582 accepts the relevant scorer facts and independent
numerical checks while honestly leaving independent upstream generation unproven.
New contradictory evidence can invalidate a resolution, but a process change alone
cannot. Coverage647/647at the historical107-game cutoff is not current freshness,
full numerical acceptance or permission to publish.

## How entries are used

Agent1 writes/deduplicates an entry when initial validation fails. Use stable IDs,
exact immutable keys/manifests, source/data version, failure reason and downstream
impact. A field's unverified status propagates to calculations depending on it;
unrelated fields/data/app work continue. Group shared causes; do not create one
PR or worker per value. Initial intake automation is the next Agent1 task, not
already implemented by these seed files.

Agent2 records a claim (actual session/branch, timestamp and scope) in its work-item
branch/PR before investigation. One worker owns a group. Agent1 does not edit a
claimed entry; append new intake separately and link related IDs. The integrator
merges against the current head and reconciles conflicts rather than overwriting
another worker. This small worklist does not require a new dashboard/database.

Use `open`, `claimed`, `blocked_evidence`, `ready_for_review`, `resolved`, or
`superseded`. Record failed routes and a concrete changed-evidence trigger so a
successor does not repeat blocked searches. Resolve only with attributable evidence,
full affected-input checks, independent review and a new versioned output/correction.
Retain sources and all prior attempts; a schema/range check alone is insufficient.

Corrections must be portable keyed data with source/version preconditions,
provenance and dependent-output invalidation, not app-specific runtime exceptions.
A real shared parser/loader/calculation defect goes to Agent1; Agent2 must not alter
data to compensate for broken application code. Correction adoption occurs at a
safe version boundary, not by mutating Agent1's inputs during tests.

## Timing and current worker state

**No Agent2 session is started by this documentation change.** Use
[the ready launch prompt](agent-2-prompt.md) when starting an actual separate session.
It can start as soon as snapshot/ownership are clear, including while Agent1 works
on the app, or later as a batch. There is no mandatory per-PR or daily relaunch.

Do not keep a worker spinning on evidence-blocked entries. After a bounded useful
attempt, park them with exact next evidence and resume only with a concrete new
lead, newly available source, or other actionable intake. Agent1 keeps moving.
Before full acceptance refresh actual24-hour coverage; do not reinterpret this
historical validation population as the current season's complete due set.

## Handoff fields

Record actual session/branch/revision, claimed IDs, pinned input hashes, sources
checked/added, validated corrections, affected-output checks, remaining evidence,
review status, next trigger and running/stopped state. Keep large ledgers in the
existing source-evidence packages. Agent2 updates this worklist/its PR, not Agent1's
main checkpoint. Agent1 links accepted results during normal integration.

### DQ-005 bounded investigation,2026-11-06

Agent2 `/root` claimed [DQ-005](DQ-005.json) on `codex/agent2-dq005-20261106`
from post-PR587 main`4bd2f799ddeb06544ef2223e56449ec609318dec`.
[PR588](https://github.com/Bet-Zero/nbatools/pull/588) retains the exact final
revision and [versioned investigation](../source-evidence/dq005-20261106/README.md).
Four source fields and42played-player values checked; independent checker confirms
canonical team margins already match paired scores. Raw-source field semantics/
upstream mechanism and independent native scorer corroboration remain unqualified.
No data value was corrected or published. The2PDF Actions request was rejected by
automatic approval review before execution for possible compute-cost/credential
concerns. The acquisition test is removed from active test execution; its original
reviewed implementation remains only in immutable Git history. No capture or
approval request is pending. This is an **evidence-only administrative closeout**:
DQ-005 stays **blocked_evidence and nonblocking for application development**.
Reopen only for newly available attributable scorer originals/field documentation,
or a named consumer that needs the unqualified source field/player-lineup basis
or changes the paired-score canonical contract; record exact affected keys first.
A restored capture route or elapsed time alone is insufficient. Agent2 stops after
verified landing; no background worker or Agent1 coordination is implied.
DQ001-DQ004, source statistics, canonical data and production are untouched.
