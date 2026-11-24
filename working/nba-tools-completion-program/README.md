# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex, November 24.** PR637–639 are merged. Workflow main is
`11ab5aad1db7897fec0b871e6d9dba77dd6929e3`; production runtime `997efe5d` is READY.
The limited Core-1 snapshot remains closed; full original acceptance and
league-wide participation remain unfinished.

**Candidate uploaded and independently verified, NOT ACTIVATED:** owner-approved
[run45391469130](https://github.com/Bet-Zero/nbatools/actions/runs/45391469130)
completed preparation, protected upload, separate read-only verification and
[durable receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-45391469130).
The actual receipt is `candidate_independently_verified_not_activated`, SHA256
`b49eed924b26a6c2d5ad0cd0d8c654e37a811a657b8a889548f615c38ebfbd70`.
- Package `cleveland-team-appearances-2024-v1`; publisher `564f2e05`.
- Generation `availability-cleveland-2024-v3-20261124`; manifest
  `d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034`.
- 1,461 manifest-listed files/423,517,896 bytes; upload ceiling 1,462 candidate
  PUTs and **zero pointer PUTs**. Approved conservative storage projection
  4,048,614,400 bytes is below the unchanged 10 GB limit.
- The production pointer stayed on `availability-season-inactive-2024-v1-20261116`,
  manifest `0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc`.
  Every uploaded body passed independent readback. Existing data and backups
  remain intact; candidate upload intentionally skipped production backup.
- The owner approved the existing environment gate as `Bet-Zero`; no bypass,
  broader credential or repeat upload occurred. The pending-run main freeze has
  ended. The exact packet and source lineage remain in PR637–639 and the receipt.

**Functional improvement still unavailable on the public website:** all 82
Cleveland 2024-25 side lists support TEAM WITH/WITHOUT for all 21 original pilot
candidates. Without LeVert 31–13, Hunter 44–11, Curry 64–18; WITH Curry is
known-empty, not 0–0. Rostered missed games remain 14/21 complete, seven cases /
318 cells unknown. Compatible v2 sources are included; quarantines, original
source authority and unknowns are preserved. Production has not selected this
candidate.

**Verification reused:** numerical run45375696531 actually executed/passed its
one required test with zero required skips: source preservation, 45 prior checks,
44 TEAM controls and seven rostered unknown controls. Blocking pre/post CI for
PR637/638 passed; PR639 took its passing light path. Source/deployed evidence
from PR633–635 retains its original scope. Historical failed receipts and the
informational development-security failure are preserved. No full-suite rerun
or new NBA acquisition was needed for upload verification.

**Remaining blocker — apply already approved access to this running task:**
preview-only Vercel Authentication is enabled on Hobby at $0. The owner reports
adding `*.vercel.app`, but after environment restarts the actual task still
reports enforced revision1, custom host `api.github.com` plus package managers.
A fresh Vercel connection failed at the proxy with CONNECT403. The requested
runtime change did not produce a confirmed applied grant. Do not repeat identical
requests or confuse a future-task configuration change with this instance's
policy. No candidate preview, temporary share link or cold query was created.
Chat permission for the exact upload and bounded private-preview access is
already recorded; do not ask for it again.

**Next:** once this task's settings show the approved preview-host grant applied,
create an isolated protected preview pinned to the uploaded generation and full
manifest. Qualify its actual first query/loader miss within 20 seconds; maximum
two deployments/eight queries. Reuse the uploaded bytes. Stop on failure; no
optimization campaign. Only a passing hosted qualification permits preparation
of a separate protected activation approval (one pointer CAS, zero snapshot
PUTs). **Production activation remains UNAPPROVED.** Strict readiness and
separate data/backup/restore verification remain required after any later
approved activation.

**Separate unfinished requirements:** original K08 remains 16 PASS / 26 MISSING
DATA / 4 LIVE; original questions, controlled positives and acceptance baseline
are unchanged. The new semantics do not upgrade the 26 cases. Current-season
readiness remains 503/new_season_not_loaded; Live collection/publication,
24-hour freshness, literal-current cases and K12 timing are separate. DQ-005,
484 unavailable rates and original failure receipts remain preserved. No new
collection, historical backfill, spending, automatic refresh or Live work is
authorized.

## Preserved scope

- **Acceptance contract:** [acceptance-baseline-pr582.md](acceptance-baseline-pr582.md),
  byte-exact, SHA256 `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`.
  Its status cells are historical; its requirements still apply, as revised only by
  B's scope decisions recorded above.
- **Bindings per group:** [K01](k01-binding.md), [K02](k02-binding.md),
  [K03](k03-binding.md), [K04](k04-binding.md), [K05](k05-binding.md),
  [K06](k06-binding.md), [K07](k07-binding.md), [K09](k09-binding.md),
  [K10](k10-binding.md), [K11](k11-binding.md), [K12](k12-binding.md). K08 uses the
  [46 original PR462 positives](https://github.com/Bet-Zero/nbatools/pull/462#issuecomment-6440042622).
- **Carry-forward scope:** section 8 of the baseline lists the work Core-1 does
  not complete (wider combinations, roles/context data, play-by-play/lineups,
  unattended freshness, guided tools). Pick the next task from it after Core-1.
- **Saved unreviewed work:** Tatum branch at
  `b835874e7c31dc29c38d62fcda263af404c881fe`. Don't treat it as accepted or
  overwrite it.
- **Agent 2 launch prompt**, if it's ever restarted:
  [data-quality/agent-2-prompt.md](data-quality/agent-2-prompt.md).
