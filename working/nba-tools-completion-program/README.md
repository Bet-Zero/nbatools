# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**As of 2026-11-12, main `95cb705` (after PR609).** Lead: temporary Claude Agent 1
(Codex unavailable). Agent 2 stopped. DQ-005 and K12 cold-start chasing parked.

### Where things stand, in plain English

- **The app works on history.** Ten of the twelve Core-1 capability groups
  (K01-K07, K09-K11) are built and numerically rechecked on a pinned candidate
  (PR595). What they still need is the single deployed desktop/mobile check on a
  frozen release candidate.
- **Participation questions (K08) are the main unfinished group.** Of the 46
  original questions, IDs 7, 8, 23-25, 30-32 and 41 pass numerically on published
  data. IDs 6, 16, 18, 35 and 44 pass on qualified data that isn't published yet.
  A few are blocked on missing evidence, and five are "this season" questions
  that move to Live. A per-ID table for all 46 is the first next action.
- **K12 (delivery)** works functionally. Its cold-start timing checks are parked.
- **Recent fixes:** PR606 corrected P.J. Washington's rebounds (data v7). PR607
  fixed "total" questions, team-restricted double-double boards, "who led…"
  questions and a season-year bug.
- **Scope decision (B, 2026-11-11):** Core-1 is accepted on data already held
  (published history plus the fixed 123-game 2026-27 cutoff). Daily freshness and
  literal "this season" questions move to the Live milestone. They're deferred,
  not deleted.

### Open questions for B (yes/no, asked by Agent 1)

1. Move K12 cold-start timing out of Core-1 into Live?
2. Show the 484 unknown USG%/TOV% values as labeled "unavailable" instead of
   letting them block the release?
3. Publish the already-qualified staged historical cohorts (LAL 16/18/35,
   Tatum 2024, Durant 2007, historical Davis)? This needs B's publication approval.

### What's left for Core-1

| Item | Kind | What closes it |
| --- | --- | --- |
| Deployed check of K01-K12 | Release step | One desktop/mobile run on a frozen release candidate |
| K08 staged cohorts (16/18/35, 6 Tatum 2024, 44 Durant 2007) | Needs B approval | Publish (open question 3), then the deployed check |
| K08 Davis default-season group (incl. 12 and both 40 questions, 2025-26) | Missing data | Dated official Davis club membership, or official per-game inactive lists, for every selected 2025-26 Lakers date. Not inferred from absent rows. |
| K08 ID26 (Lakers vs Celtics and Knicks without Tatum) | Missing data | Dated Knicks-side membership or nonmembership on every selected date |
| K08 IDs 4, 5, 19, 38 and the "current" 40 | Live (B, 2026-11-11) | Need real current-season inputs |
| K08 IDs 45, 46 | Kept in controlled structured form, per the mapping | Confirm in the acceptance view |
| K12 cold-start B1/M1/H1 | Parked | Open question 1 |
| 484 USG%/TOV% unknowns | Data gap | Open question 2 |
| Raw QA: 13 open failures (608 pass on reuse) | Mapped | 11 are participation-coverage gaps covered by the K08 rows above. 1 is an unsafe `available = played` expectation (fix the expectation through independent review; don't implement it). 1 is an accent-format expectation. |
| Filter sweep PASS_WITH_GAPS (39 dropped, 44 no-signal) | Not yet mapped | Map each relevant gap to a K row or to carry-forward. Gaps are never counted as passes. |

### Next action

1. Build one acceptance view on the existing runners (Raw QA, the K08 shared
   cases and the deployed wrappers). It should print each K01-K12 row and each
   of the 46 K08 IDs as passing / software failure / missing data / needs
   publish / Live, from one command. No new framework.
2. Fix any software failures it shows, in shared logic.
3. When B answers the open questions, freeze a release candidate and run the
   broad checks once.

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
