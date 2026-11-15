# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**November 15, 2026 (Detroit). Lead: Codex.** Starting live main verified at
`a9e30710` (merged PR621; all earlier work preserved). Current branch:
`codex/bounded-membership-outcome`, documentation only. Agent 2/DQ-005 and K12
cold-start stay parked; no background data worker is running.

**Core-1 remains limited acceptance, not league-wide completion.** Earlier
acceptance, K08 gaps, release evidence and defects remain in the unchanged
[checkpoint history](checkpoint-history-20261114.md). Last recorded published
snapshot remains `availability-participation-2025-durant-v1-20261114`, manifest
`cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366`.
No production change or new active-pointer/inventory/freshness claim.

**Bounded membership attempt stopped: zero new intervals or functional coverage.**
Reused PR621 sources/code. Four discovery queries and two primary guide-body
attempts found no qualifying season-final chronology: the official Rockets
media-page guide returned403; the archived Lakers2024-25 guide exceeded the
fetch tool's size limit (129,130,463bytes). Exact URLs/results are in the PR.
No retries, alternate-host chase, new acquisition/validation infrastructure or
individual investigation followed. Hinton/Hudgins opening conflicts, Windler's
effective-date dispute and full contract-event coverage remain unresolved.
Expiry coverage is unqualified; this sample has no ten-day signing to test it.

**Actual existing coverage:** pinned manifest/relevant CSV hashes verified;
43candidate player/team identities over164team-games (160unique NBA games),
3,526exact-game membership questions, not every NBA player:

| Sample | Known member | Known nonmember | Unknown | Total |
| --- | ---: | ---: | ---: | ---: |
| Rockets2023-24 | 885 | 3 | 916 | 1,804 |
| Lakers2023-24 | 980 | 4 | 738 | 1,722 |

Total **1,872known /1,654unknown (53.1% known)**:1,747played,118explicit
nonparticipants,7same-game opponent facts. The extra125facts beyond PR621's
appearance-only census were already qualified/retained, not newly acquired.
No membership-interval file exists; date-only continuous membership stays unknown.

Existing-engine natural queries verified outside the original named cohorts:
Rockets **28-28 in56games with Jock Landale** in2023-24; Rockets **1-0 without
Cam Whitmore on November8,2023** (128-94); Lakers **0-1 without Harry GilesIII
on April9,2024** (120-134). Season-wide Rockets without Whitmore remains
unsupported. Separate checker independently reproduced every cell from source
CSVs and authenticated both native inactive lists/scores, without app calculations.
No source, dataset, parser, engine or PR619 recovery code changed; no suite/R2 run.

**Next practical direction:** stop team-PDF membership hunting. Continuous
1996-97+ coverage needs a vetted league/season bulk contract-lifecycle ledger
(join/trade/waiver/expiry/two-way changes) plus dated opening populations. The
current official feed begins July2015 and is insufficient alone. Do not claim
that missing bulk input is available or automatically start another source hunt.
Use the existing whole-game qualifier over retained originals for incremental
exact-game functionality; it does not solve omitted-player tenure. Reopen
continuous membership only with materially new bulk source evidence. No substantial
backfill, costs or automatic refresh; nothing currently needed from B.
PR621 originals/reviews remain in [source evidence](source-evidence/team-membership-20261114/README.md).

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
