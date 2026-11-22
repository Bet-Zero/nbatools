# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Baseline main `b5c08fb9` (PR631); branch
`codex/core1-limited-snapshot`.** Owner approved
membership expectation clarification and an explicitly **LIMITED Core-1 snapshot**
on November 22. This milestone closes with the reviewed change's required gates;
**full original Core-1 acceptance and league-wide participation remain unfinished**.
No original question, controlled positive or baseline requirement is removed.

**Complete within the limited scope:** the already verified historical identity,
season/window, summary/record, finder/count, ranking, owned-condition, comparison,
split, sequence, history/population and functional-delivery bindings, plus qualified
participation cases. Reuse PR615's 126 non-K08 checks, PR617's final desktop/mobile
runs [43602403345](https://github.com/Bet-Zero/nbatools/actions/runs/43602403345)
and [43602584850](https://github.com/Bet-Zero/nbatools/actions/runs/43602584850),
and PR618's [17 focused checks](https://github.com/Bet-Zero/nbatools/actions/runs/43658225359).
New focused API/browser checks distinguish member-DNP, verified nonmember and
unknown; shared explanation fixes stop describing unverified participation as
unavailable points or an unsupported combination. An empty eligible sample is
not a 0-0 record. Exact revision, independent review and execution are in this PR;
old results are reused at their original scopes, not claimed as fresh runs.

**Exactly unsupported:** K08 remains **16 PASS /26 MISSING DATA /4 LIVE**.
Davis-family original IDs **1/2/3/9/10/11/12/13/14/15/17/20/21/22/27/28/29/
33/34/36/37/39/40/42/43** lack qualified complete membership/participation for
2025-26 Lakers dates under the served default. Their controlled-fixture teammate
positives test software, not factual Davis tenure. Retained official transfers
(Feb2 2025 LAL→DAL; Feb5 2026 DAL→WAS) establish events, not continuous intervals.
ID39 includes a WITH/coappearance variant; ID40 includes a literal-current variant.
**ID26** retains the entire Celtics/Knicks union: dated Knicks-side nonmembership
is unqualified, so the verified Boston subset cannot stand in for it. None of
these original real-NBA outcomes is upgraded. The acceptance map now explicitly
separates member-DNP, verified nonmember and unknown; nonmembers are excluded,
never counted as absences. Missing records prove neither nonmembership nor DNP.

**Separate Live scope:** literal-current IDs4/5/19/38 and current40; 24-hour
freshness/readiness, current cross-club membership/current publication (owner
Nov11); K12 cold timing (Nov14). The 484 unknown USG%/TOV% values stay labeled
unavailable and are not snapshot blockers (Nov14). The known 2026-27 readiness
failure and original failed-publication-verification receipt remain unchanged.
Existing stale-generation/acquisition failures and the informational development
security advisory are not silently closed. DQ-005/rate source hunts stay parked.

**Next:** limited snapshot closed; stop this work. Begin Live only as a separately
scoped task: establish whether the existing route can deliver one manually
initiated current-season update, its due-game/required-source coverage and $0
limits. Then qualify it and seek exact protected publication approval. No Live
implementation, collection, automatic refresh or production change is authorized
by this checkpoint. No extra historical research or test campaign.

**Preserved:** production **0abc**, 69 complete 2024-25 cases plus 93 prior
2023-24 cases, its verified backup/restore and all safeguards. Cleveland staging
**`cleveland-full-boxscore-2024-v2`**, ZIP SHA256
`a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`,
remains 14 complete /21 cases, seven cases /318 unknown cells. Keep originals,
v1, quarantines and disputes for a later combined release; no standalone package,
publication, wider collection or spending. No background work continues.

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
