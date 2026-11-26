# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 26, 2026. Lead and operations writer: Codex.** W0 landed in
[PR #645](https://github.com/Bet-Zero/nbatools/pull/645), W4A in
[PR #646](https://github.com/Bet-Zero/nbatools/pull/646), and the W2 recovery
guard in [PR #647](https://github.com/Bet-Zero/nbatools/pull/647). W2
publication safeguards landed in [PR #648](https://github.com/Bet-Zero/nbatools/pull/648),
and W1 landed in [PR #649](https://github.com/Bet-Zero/nbatools/pull/649).
PR #644 was the accepted activation artifact. Production is on `da104fbf`
from [PR #653](https://github.com/Bet-Zero/nbatools/pull/653).
The only unrelated open PR is blocked
[#462](https://github.com/Bet-Zero/nbatools/pull/462). No other writer or background
worker is active. [Execution plan](execution-plan.md)

**Cleveland is active and its historical answers and backup are verified.**
The owner approved [run 45763092143](https://github.com/Bet-Zero/nbatools/actions/runs/45763092143).
One conditional pointer write and zero snapshot uploads selected
`availability-cleveland-2024-v3-20261124`, manifest
`d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
The independent receipt records 1,461 verified objects, all 87 registered public
answers and the retained previous manifest. Cleveland's 2024-25 record without
Caris LeVert is 31–13 in 44 games. TEAM appearances cover all 21 pilot players;
rostered missed-game coverage remains 14/21. [Activation receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-45763092143)

**Recovery and proof.** The separate credential-free runner restored the 1,461
files byte-exact from the 66,763,469-byte candidate archive. The qualified restore
path checked every hash and reused source qualification. A credential-free
follow-up using the actual verified R2 reader over the restored filesystem
returned 31–13 in 44 games without LeVert. The separate checker independently
derived and recovered 44–11 in 55 games without Hunter. The public website
rendered the LeVert result through its regular query form. This exercised the loader with an
offline object transport, using the retained verified pointer and archive. The previous generation
`availability-season-inactive-2024-v1-20261116` retains its exact backup and
restore. No prospective candidate ZIP preflight or production rollback rehearsal
was found in the activation evidence. Reuse the accepted PR #643 cold proof
(5.8248 s and six follow-ups) and #644 independent review and post-merge CI.
[Candidate backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-45763092143)
· [Previous backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685)
· [PR #643](https://github.com/Bet-Zero/nbatools/pull/643)
· [PR #644](https://github.com/Bet-Zero/nbatools/pull/644)

**Live and stabilization remain open.** Public readiness reports 503 with sole
`new_season_not_loaded`, on the intended Cleveland generation. Scheduled
monitor run 45768634065 failed before its representative query. W5A logs for
the earlier unlocked deployment show Python 3.12 and uv 0.13.5, initial install from
`pyproject.toml` and subsequent build-step installs from an untracked build
`uv.lock`. The logs omit a complete installed inventory and say that Active CPU
billing ignores the configured memory value. Original K08 remains 16 PASS /
26 MISSING DATA / 4 LIVE. Full original acceptance, Live freshness, league-wide
participation, K12 timing, DQ-005 and the 484 labeled unavailable rates retain
their existing scope and authority.
[Monitor run](https://github.com/Bet-Zero/nbatools/actions/runs/45768634065)
· [Production build](https://vercel.com/zeros-projects-686e97fc/nbatools/E4SfKHXdhXx2dnKbL2qnGeSMaXN9)

**W4A.** Run-all monitoring is merged and its production build is live.
[Manual run](https://github.com/Bet-Zero/nbatools/actions/runs/45777149868)
reported snapshot passed and Live failed, with the representative scoring
query returning HTTP 200 in 2.58 s. Strict alerts still fail on the Live gap.
[Main CI](https://github.com/Bet-Zero/nbatools/actions/runs/45777118682)
passed all three Python full-suite jobs. [Scheduled run 45782818838](https://github.com/Bet-Zero/nbatools/actions/runs/45782818838)
also attempted all three checks. Its representative query returned HTTP 200
in 7.47 s and snapshot probes passed. Strict readiness still failed on the
sole Live blocker. Any alert/recovery policy change remains reserved.

**W2 recovery safeguards.** The exact guarded rollback path is merged.
[Authenticated read-only preflight](https://github.com/Bet-Zero/nbatools/actions/runs/45777409867)
passed 1/1 required tests with no skips. It checked the live pointer, previous
manifest and all 1,216 retained files without a write. The publication verifier
requires native typed readiness, health and exact pre-activation backup sizing.
On the restored Cleveland bytes it measured the same 66,763,469-byte ZIP as the
durable release. This is current proof. The previous activation's prospective
preflight timing remains unproven. If an uncertain future write actually
activated the candidate, the existing normal verifier still needs a dedicated
read-only handoff to consume that receipt and complete backup. Future writes
require separate authority.

**W1.** Request-pinned immutable identity and required-object validation
are merged. Exact-head independent review, blocking CI and
[authenticated R2](https://github.com/Bet-Zero/nbatools/actions/runs/45781851935)
passed. All 12 identity checks ran with zero required skips, and all 22 retained
API-shaped results were identical on the restored Cleveland data.
[Main CI](https://github.com/Bet-Zero/nbatools/actions/runs/45782678499) passed all
three full-suite jobs. Production `dpl_J9KedKBHdcUQKZRoFrgGmxH2ajpg` returned
31–13 in 44 Cleveland games through the natural endpoint
(`req_79f810c65bcc4d4bbdb25adb1b9723e8`) and 49 games, 680 points and 411 rebounds
for Bobby Portis Jr. through the structured endpoint
(`req_d377df6f6926481fa4836a0ae16538a7`).

**W3A.** Bounded request reads and inactive-client cleanup merged at `c4d1be10`
and deployed on `dpl_FjNusyfWTmWqGrKCVPgL3qkEH4L6`. The independent checker
passed 110 focused tests at the exact PR revision. Both offline HTTP adapters
returned the known Cleveland result from the restored archive. Production
returned typed 413 for an over-budget body (`req_3caf4ff6ea8647d3b71b60d375f13467`)
and 31–13 in 44 games for a normal question (`req_194f3cd4c2a840db90b665dd68ef7db7`,
5.330 s externally, 5.042 s in the handler). The
[blocking PR gates](https://github.com/Bet-Zero/nbatools/actions/runs/45784086988)
and [all three full main suites](https://github.com/Bet-Zero/nbatools/actions/runs/45785294622)
passed. The existing frontend development audit remained advisory and red.
The response deadline remains open. These timing samples do not establish the
effective host cutoff or near-deadline response completion.

**W3B.** The checker approved calendar runtime `9546cfa3` after 244
focused passes and independent checks of date windows and current-season ranks.
All 22 archived historical payloads matched byte for byte on the restored
Cleveland snapshot. [Authenticated R2](https://github.com/Bet-Zero/nbatools/actions/runs/45788049013)
passed all three selected raw-row checks with zero required skips. The exact
PR matrix exposed four test assertions that still specified the prior
cutoff flag or upper season boundary. The follow-up preserves the approved
runtime and updates only those calendar assertions and the checkpoint. The
independent checker approved final head `8d670d16`. All three blocking PR
matrices passed. [PR #651](https://github.com/Bet-Zero/nbatools/pull/651) merged at
`dce81e08`. [Main CI](https://github.com/Bet-Zero/nbatools/actions/runs/45790182679)
passed all three full jobs. The
[deployed revision](https://vercel.com/zeros-projects-686e97fc/nbatools/CLQbm4a4WV7QXFCyqARMJ5W5MHcb)
reported unavailable November 25 and 2026–27 coverage for the two literal
queries. The explicit LeVert record kept its 31–13 result in 44 games. The PR
records all three request IDs.

**W5.** The Python lock merged at `2615c940`. Preview and
[production](https://vercel.com/zeros-projects-686e97fc/nbatools/GGy5uCzq2sBdeLLPW3CyM5bhwBPt)
used the committed lock for the first Python 3.12 install with uv 0.13.5. The
local Python builder produced a 223,239,050-byte query bundle from the chosen
source and lock. That local artifact retains the configured 20-second value;
the effective hosted cutoff and near-deadline response timing remain unproven.
All 22 historical payloads matched under the locked dependencies, the exact
PR gates passed, and [authenticated R2](https://github.com/Bet-Zero/nbatools/actions/runs/45790777737)
passed 10 required source-row tests without skips. Production's natural and
structured queries both returned 31–13 in 44 games without LeVert. The PR holds
the request IDs and [main CI](https://github.com/Bet-Zero/nbatools/actions/runs/45791747173)
receipt. Settings remain under the owner's authority.

**W4B.** All 514 locked frontend tests, lint and build passed. Local
built desktop/mobile browsers used the public API for the verified Cleveland
example. The desktop check used the keyboard. On mobile a controlled 429
displayed its retry delay and request ID, and manual retry rendered the correct
sample with no automatic second request. The independent review identified misleading
copy for date ranges. The updated range message preserves its requested bounds.
The checker approved exact head `b0898973`. All blocking PR jobs passed.
[PR #653](https://github.com/Bet-Zero/nbatools/pull/653) merged at `da104fbf`.
[Main CI](https://github.com/Bet-Zero/nbatools/actions/runs/45795324415) passed
all blocking checks, including three full Python suites. The exact preview
built and requires SSO. The public
[production build](https://vercel.com/zeros-projects-686e97fc/nbatools/BZ9H2smKA5oU6fGX93SL5dNv1hmi)
passed fresh desktop keyboard and mobile discovery. Both rendered 31–13 in
44 games without horizontal overflow. Mobile displayed a controlled 429 and
recovered after one manual retry. The PR records both real production request IDs.

**W6A preparation.** The fresh Cleveland selector preserves the original
22 question identities and every numerical and rendered check. It binds the
immutable hosted deployment, locked build inputs and active pointer on both
sides of capture, and requires 44 fresh IDs and screenshots. The legacy gate
continues. The read-only provider lookup matched the last locked production
build's full source tree (674 files) and exact immutable URL. The restored
Cleveland preflight verified all original cases and four retained source-file
prefixes. No first-release broad capture has run.

**W3A timing.** On the locked build, Patrick Ewing's historical summary matched
all 348 games and 5,027 points. Request `req_9bda12cb015d4fbb98954b85bdff1d14`
took 13.940 s externally and 11.293 s in the handler. The metric is one successful
sample. Effective host cutoff and near-deadline completion remain open.

**Next.** Finish exact-head review and blocking CI for W6A preparation.
Bind the hosted budget and verify a useful near-deadline response before setting
the application deadline. W3C and the fresh 44 captures follow the coherent
frozen stabilization artifact and required broad checks.
No new collection, historical backfill, spending, automatic refresh or Live work is authorized for this assignment.
The checkout's existing `work` branch and the saved work below are preserved.

## Preserved scope

- **Acceptance contract:** [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md),
  byte-exact, SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`.
  Its status cells are historical; its requirements still apply, as revised only by
  the owner's recorded scope decisions, including [the November 14 decisions](https://github.com/Bet-Zero/nbatools/pull/611).
- **Bindings per group:** [K01](k01-binding.md), [K02](k02-binding.md),
  [K03](k03-binding.md), [K04](k04-binding.md), [K05](k05-binding.md),
  [K06](k06-binding.md), [K07](k07-binding.md), [K09](k09-binding.md),
  [K10](k10-binding.md), [K11](k11-binding.md), [K12](k12-binding.md). K08 uses the
  [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622).
- **Carry-forward scope:** section 8 of the baseline lists the work Core-1 does
  not complete (wider combinations, roles/context data, play-by-play/lineups,
  unattended freshness, guided tools). Use the execution plan for the current sequence.
- **Saved unreviewed work:** Tatum branch at
  `b835874e7c31dc29c38d62fcda263af404c881fe`. Don't treat it as accepted or
  overwrite it.
- **Agent 2 launch prompt**, if it's ever restarted:
  [data-quality/agent-2-prompt.md](data-quality/agent-2-prompt.md).
