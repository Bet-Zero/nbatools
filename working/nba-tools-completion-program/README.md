# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 14, 2026 (Detroit). Lead: Codex, taking over from Claude.**
Live main verified at `da6ae716` (PR618 merged). Clean starting tree preserved;
work is on `codex/league-participation-recovery`, based on that exact main.
Only old PR462 remains open; its branch and saved Tatum work are untouched.
No background data worker is running; Agent 2/DQ-005 and K12 cold-start remain parked.

### What remains true

- **Core-1 has limited acceptance on held data, not league-wide completion.**
  The existing 126 K01-K07/K09-K12 checks, acceptance view and deployed
  desktop/mobile proof remain recorded, not rerun here. Latest K08 view: 16
  PASS, 26 MISSING DATA, 4 LIVE; no software failures in that view. Its Davis
  default-season and cross-team membership gaps remain open. Literal current
  season/daily freshness and K12 cold-start moved to Live by B. The 484 unknown
  USG%/TOV% values remain labeled unavailable, never zero.
- Last recorded published snapshot:
  `availability-participation-2025-durant-v1-20261114`, manifest
  `cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`,
  1,186 objects. Both approved participation publications and their 31 audited
  answers are preserved. Publication readiness still failed only at
  `new_season_not_loaded`; no new live-pointer or full-inventory claim here.
- PR618's parser fixes and independent/targeted R2 evidence are preserved.
  Known broader replay failures and stale pinned package/deployed evidence are
  not reclassified as passes. No broad replay or full suite was rerun.
- Exact prior runs, decisions, remaining release evidence and carry-forward
  defects are preserved unchanged in
  [checkpoint-history-20261114.md](checkpoint-history-20261114.md).

### Active priority: league-wide with/without coverage

B's current direction supersedes the earlier first/last-appearance suggestion:
**no first/last or whole-season roster guesses; no missing-row-as-DNP.**
Keep the existing generalized membership/participation engine.

- Core player stats came from season appearance logs, not full box-score lists.
  Legacy starter-role extraction discarded nonplayers and did not save HTTP
  bodies. Newer retained Traditional/Summary originals do contain unused DNP
  and inactive evidence. Exact-game lists establish association and play state,
  not tenure or nonmembership for omitted players.
- PR619 adds: existing offline stager accepts a **game-grain request**
  and recovers all listed players on both teams, without naming a player target.
  Same original-source, canonical, append-only and protected-publication checks.
  Local staging recovered 278 rows (173 played/105 explicit nonparticipants)
  from eight already-retained games, preserving all 597 existing season rows.
  Independent raw tally agrees. Focused R2 [43674107752](https://github.com/Bet-Zero/nbatools/actions/runs/43674107752) passed one selected/executed required test, zero skips/errors, on code `a9895ea` via request `2c56414f`. This staging is **not published**.
- Source research independently checked opener/finale absences, Adams' trade
  despite no Houston appearances, late signings, waivers, two-way players and
  arbitrary opponent players. Older injured-list members can be omitted from
  both Traditional and Summary: acquiring every pair is not a proven exact
  1996-97+ membership solution. Season inactive archives and official team/season
  transaction chronologies are reusable leads, with explicit completeness/date
  gaps and source conflicts.
- Evidence and exact missing inputs:
  [league participation findings](source-evidence/league-participation-20261114/README.md).
  Originals, old snapshots, accepted cohorts and safeguards are preserved.

### Verification and one next action

Separate checker `/root/coverage_checker` approved `a9895ea` with zero findings:
67 focused tests, two unfamiliar omission/unknown controls, exact native rows and
prior-cell preservation. R2 numerical validation passed as above. Initial CI
caught the historical applicability seal. The checker separately approved the
offline stager/documentation reach across all 22 original cases; the companion
now binds 28 changed/635 unchanged files, preserving all 663 original bindings,
22 inputs, 44 captures and false full-Core/fresh-deployment flags. Focused guard
tests passed. Final CI/delta review must pass before merging PR619.

After landing, qualify bulk **team/season membership evidence**, especially
opening rosters plus dated NBA contract changes and older injured-list coverage.
Use the game-based recovery path for valid retained pairs first; do not replace
existing one-sided reports or claim that a complete file index proves membership. Bring exact missing
season/game bodies and bounds to B before any substantial historical backfill;
production publication, new costs and automatic refresh remain separately gated.

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
