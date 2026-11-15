# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 15, 2026 (Detroit). Lead: Codex.** Starting main verified at `469dc12a`
(PR622 merged). Current unit: PR623, `codex/season-inactive-pilot`. Previous work,
source originals and stopped membership investigation are preserved. No team-PDF
hunt or new membership-research infrastructure. Agent 2/DQ-005 and K12 stay parked.

**Core-1 remains limited acceptance, not league-wide completion.** K08's existing
16 PASS/26 MISSING DATA/4 LIVE view is unchanged: Davis default-season/cross-team
membership and current-season freshness/readiness remain unresolved. Older proof,
release gaps and defects stay in [checkpoint history](checkpoint-history-20261114.md).
Last recorded published snapshot remains
`availability-participation-2025-durant-v1-20261114`, manifest
`cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`.
No production data/pointer change or fresh deployed-acceptance claim.

### Useful full-season participation improvement, staged only

The bounded pilot is 2023-24, all30clubs. PR619's retained complete-game path
already supplies one additional full-season case; other retained native pairs
add no further complete case. A retained 0.86MB season CSV has 11,010 explicit
NBA SummaryV2 inactive rows for all1,230regular games. Independent checks matched
all30native comparators and found no appearance/side/duplicate contradictions.
The new strict archive-derived inactive producer/reader adds a separate dataset,
keeps old per-game/PDF rows and ledgers intact, and never fills omissions.

| Full player/team/season cases (all82games known) | Count |
| --- | ---: |
| Published before pilot | 18 |
| Including prior PR619 staging | 19 |
| Including retained season inactive batch | 93 |

That is **75 above published,74 beyond already-staged work**, across27clubs, in a
713candidate-case denominator. No entire club is complete for every candidate.
The remaining620cases include134with omissions even in processed whole-game
sources and486with gaps only outside those reports. All20,846unknown cells have
unresolved membership and participation; no membership-known/play-unknown-only
case exists. Trades/late joins stay blocked without qualified associations;
missing rows never become DNPs. No new acquisition/cost or automatic refresh.

Local product verification checked186actual season-long with/without queries,
including zero-appearance players and genuine zero-game samples. Examples:
Denver without Čančar57-25; Minnesota without Clark56-26; Houston without
Sengun12-7; Cleveland without Allen2-3. Each is explicit2023-24 scope, not a
current/deployed claim. Full-season Adams/Houston and Dinwiddie/Lakers still
refuse incomplete coverage. [Source/coverage details](source-evidence/season-inactive-pilot-20261115/README.md).

Local season integration,43focused source/boundary controls and18historical
applicability guards passed. Source count changed31/unchanged632 preserves all
663original bindings,22cases/44captures and false full-Core/fresh flags. Final
exact-head review, blocking CI and targeted R2 are required before merge; their
results belong in PR623, reusing passing PR619 evidence for unchanged code/data.

**Next:** complete PR623's focused qualification/review, then prepare its bounded
validated overlay for separately protected production approval. Published coverage
remains18until approval/activation; the93case result is isolated staging. No
additional game collection is necessary for this gain. Do not restart membership
source hunts or assume this pilot completes NBA history.

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
