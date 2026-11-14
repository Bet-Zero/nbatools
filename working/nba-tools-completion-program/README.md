# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**As of 2026-11-14, main `fab9a57` (after PR612) plus the historical publication audit.** Lead: temporary Claude Agent 1
(Codex unavailable). Agent 2 stopped. DQ-005 parked. K12 cold-start moved to Live.

### Where things stand, in plain English

- **The app works on history.** Ten of the twelve Core-1 capability groups
  (K01-K07, K09-K11) are built and numerically rechecked on a pinned candidate
  (PR595). They still need served-generation proof and the deployed
  desktop/mobile check on a frozen release candidate. K03 and K05 also need fresh
  numerical, language and rendering evidence for their paths changed since
  their bindings.
- **Participation questions (K08) are the main unfinished group.** Of the 46
  original questions, IDs 7, 8, 23-25, 30-32 and 41 pass numerically on published
  data, and also passed new-runtime desktop/mobile checks (PR605). IDs 16, 18
  and 35 pass numerically on qualified data that isn't published yet. IDs 6
  (Tatum 2024) and 44 (Durant 2007) have qualified, unpublished source data.
  A few are blocked on missing evidence, and five are "this season" questions
  that move to Live. A per-ID table for all 46 is the first next action.
- **First approved publication is live (2026-11-14).** Package
  `historical-participation-v1` adds 2023-24 Lakers participation for Davis,
  LeBron and Reaves, and 2024-25 Tatum participation. It is the active generation
  `availability-historical-participation-v1-20261114` (manifest `be094017…`,
  852 objects, 404,817,823 bytes).
  - B approved [run 43569028151](https://github.com/Bet-Zero/nbatools/actions/runs/43569028151),
    which wrote and byte-verified every object.
  - Like the LeBron publication, its verify job then failed only at the readiness
    gate, which still reports `new_season_not_loaded` (freshness, moved to Live).
  - The read-only audit `tools/audit_historical_publication.py`
    ([R2 43573241422](https://github.com/Bet-Zero/nbatools/actions/runs/43573241422),
    1/1 passed) then checked all 22 registered live answers. The pointer was
    unchanged before and after.
  - The 2025-26 LAL/BOS stages (IDs 16/18/35) and Durant 2007 (ID44) are still
    bound to the old base. They need a rebuild on this generation before their
    own packages.
- **K12 (delivery)** works functionally. Its cold-start timing checks moved to Live (B, 2026-11-14).
- **Recent fixes:** PR606 corrected P.J. Washington's rebounds (data v7). PR607
  fixed "total" questions, team-restricted double-double boards, "who led…"
  questions and a season-year bug.
- **Scope decision (B, 2026-11-11):** Core-1 is accepted on data already held
  (published history plus the fixed 123-game 2026-27 cutoff). Daily freshness and
  literal "this season" questions move to the Live milestone. They're deferred,
  not deleted.

### B's decisions (2026-11-14, "yes yes and yes")

Source: B, 2026-11-14 06:07 UTC (`cmsg_01ABTwDaHncgP7nUEgUSYNtvUp9CnT8J6gygVaXisAB7fm`),
answering the plain-language questions in `cmsg_01ABTwDaHncgP7nUEgUSYNtvP2G6Z7BrxJ6Eue7UrM1sBB`.

1. **K12 cold-start timing moves to Live.** It is no longer a Core-1 blocker.
2. **The 484 unknown USG%/TOV% values show as labeled "unavailable"** and do not
   block the release. They are never shown as numbers.
3. **Publication approved** for the already-qualified staged historical cohorts
   (LAL 16/18/35, Tatum 2024, Durant 2007, historical Davis), through the existing
   protected publication workflow only. This covers no current 2026-27 data, and
   the existing no-write validation, review and environment gates still apply.

### What's left for Core-1

| Item | Kind | What closes it |
| --- | --- | --- |
| Deployed check of K01-K12 | Release step | Served-generation proof and one desktop/mobile run on a frozen release candidate |
| K03/K05 changed paths | Software evidence | Numerical, language and rendering checks for paths changed since the bindings |
| K08 historical Davis/LeBron/Reaves 2023-24 + Tatum 2024-25 | **Published 2026-11-14** (run 43569028151; 22 live answers audited, R2 43573241422) | Map the IDs this closes in the acceptance view |
| K08 staged cohorts still to publish (2025-26 LAL/BOS for 16/18/35, 44 Durant 2007) | Approved to publish (B, 2026-11-14) | Rebuild each stage on the new base, then reviewed package, no-write validation, protected publish and audit |
| K08 Davis default-season group (incl. 12 and both 40 questions, 2025-26) | Missing data | Dated official Davis club membership, or official per-game inactive lists, for every selected 2025-26 Lakers date. Not inferred from absent rows. |
| K08 ID26 (Lakers vs Celtics and Knicks without Tatum) | Missing data | Dated Knicks-side membership or nonmembership on every selected date |
| K08 IDs 4, 5, 19, 38 and the "current" 40 | Live (B, 2026-11-11) | Need real current-season inputs |
| K08 IDs 45, 46 | Kept in controlled structured form, per the mapping | Confirm in the acceptance view |
| K12 cold-start B1/M1/H1 | Live (B, 2026-11-14) | Not a Core-1 blocker |
| 484 USG%/TOV% unknowns | Labeled unavailable (B, 2026-11-14) | Confirm they render as unavailable in the acceptance view |
| Raw QA: 13 open failures (608 pass on reuse) | Mapped | 11 are participation-coverage gaps covered by the K08 rows above. 1 is an unsafe `available = played` expectation (fix the expectation through independent review; don't implement it). 1 is an accent-format expectation. |
| Filter sweep PASS_WITH_GAPS (39 dropped, 44 no-signal) | Not yet mapped | Map each relevant gap to a K row or to carry-forward. Gaps are never counted as passes. |

### Next action

1. Build one acceptance view on the existing runners (Raw QA, the K08 shared
   cases and the deployed wrappers). It should print each K01-K12 row and each
   of the 46 K08 IDs as passing / software failure / missing data / needs
   publish / Live, from one command. No new framework.
2. Fix any software failures it shows, in shared logic, and run deployed checks
   on the existing published generation where they apply.
3. Rebuild and publish the remaining approved cohorts (2025-26 LAL/BOS, Durant
   2007) the same way as `historical-participation-v1`. Then freeze a release
   candidate and run the broad checks once.

### Carry-forward from PR607 (not Core-1 blockers unless an original case needs them)

"Mavericks games with 130 total points" drops the 130 floor. Two named teams on
an event board narrow to one. "Who led <team> in games with X and Y" returns
team grain. "25-30 points" ranges are dropped. En-dash and two-digit seasons
("15-16", "2026–27") don't parse. Season-total thresholds ("total of 2000
points") are unsupported.

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
