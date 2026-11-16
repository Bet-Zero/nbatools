# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Main `9c9f3cc0` (PR625).** The owner-approved 2023-24 package
is published, independently verified and backed up. Prior sources/work remain.

**Now answers in production:** 93 complete player/team/season cases, versus 18.
All 82 regular-season games and both with/without questions are covered for each.
Across 713 candidates, 620 remain incomplete / 20,846 player-game cells unknown.
No entire club is complete. Missing rows or season rosters never prove DNP/tenure.

Active generation: `availability-season-inactive-2023-v1-20261115`, manifest
`8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8`.
[Protected publication43801111855](https://github.com/Bet-Zero/nbatools/actions/runs/43801111855)
completed its approved write. Its original
[failed readiness receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-43801111855)
remains unchanged: 2026-27 is missing. No rollback or second publication occurred;
previous generation `availability-participation-2025-durant-v1-20261114` is retained.

**Publication verification complete:** independent
[audit43807804521](https://github.com/Bet-Zero/nbatools/actions/runs/43807804521)
passed all 1,213 bodies / 415,007,162 bytes, preservation of old cells/imports/source
authority, 38 live answers and three controls; one test passed, zero skips/errors.
The 186-query preparation proof is reused against identical data/runtime, not
claimed as new live requests. Independent checker: zero findings. Details: PR624.
[Backup43809073200](https://github.com/Bet-Zero/nbatools/actions/runs/43809073200)
passed export, durable retention and a separate secret-free restore with no
production writes. The [permanent backup](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-43809073200)
holds all seven assets, the same manifest/files and both receipts; archive
65,801,094 bytes, SHA256 `9a4dcc389a1b27c732be717b694bc30ed5f2002c0296c689ace38b2a7ce4e846`.
Do not repeat completed publication checks or backup.

**Next-season improvement, staging only:** branch `codex/season-inactive-2024`,
code/data `ba853014`; review and targeted R2 evidence belong in
[PR626](https://github.com/Bet-Zero/nbatools/pull/626). Retained 2024-25 game bodies
added nothing beyond ten already imported games. One bounded 845,487-byte public
archive capture supplies 10,847 accepted inactive rows; seven identity-name
conflicts stay quarantined with exact source replay, without aliases or facts.
The producer now accepts canonical neutral-game participants without inventing
home/away. The published 2023 derived file replays byte for byte unchanged.
Local product validation passed 138 queries: **69 complete cases versus 11**, across
23 teams. All 707 candidates are counted; 638 remain incomplete / 20,649 unknown
player-game cells. All unknowns lack both membership and participation evidence;
no full club or new tenure interval is claimed. Topic/OKC without: 68-14, all82 games;
with: genuine empty sample. Trade/no-appearance controls remain unsupported.
The retained three-file qualified overlay is usable data, not a research report.
No 2024-25 data is published. PR626 must pass independent review, targeted numerical
validation and blocking CI before merging; no extra full-suite/manual broad replay.

**Next:** prepare that same qualified 2024-25 overlay for protected publication
after PR626's gates. Verify deployed format support, preservation and exact package;
ask B only for the concrete protected activation. No rebuild/recollection, automatic
refresh, new costs, substantial historical backfill or individual-player/source hunt.
The method scales as a partial participation expansion; full historical coverage
still needs trustworthy dated membership and observations for omitted players.

**Still separate:** Core-1 remains limited acceptance (K08: 16 PASS / 26 MISSING
DATA / 4 LIVE). Davis default-season/cross-team cases and current-season readiness
remain unresolved. K12, DQ-005, 484 investigations and historical membership/PDF
research stay parked/closed. Development-security advisory remains red; preserve
all blocking gates. Additional seasons come after this bounded pilot, not in it.

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
