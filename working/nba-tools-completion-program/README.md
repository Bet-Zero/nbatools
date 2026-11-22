# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Baseline main `36d7d00a` (merged [PR633](https://github.com/Bet-Zero/nbatools/pull/633));
branch `codex/team-participation-role-boundary`.** The limited Core-1 snapshot remains closed;
full original acceptance and league-wide participation remain unfinished.
The owner separately approved a new November 22 product meaning: default team
WITH/WITHOUT records concern appearances **FOR the selected team**, including
before joining and after leaving. Opponent appearances are WITHOUT for that team.
This is a changed product requirement, not retroactive evidence for old positives.

**New qualified staging:** `team-appearances-cleveland-2024-v1` certifies all
82 Cleveland 2024-25 regular-season side lists by replaying existing retained
full-game sources. No downloads, source-body changes or publication. All 21
original Cleveland candidates support complete TEAM WITH/WITHOUT records; Curry
is an additional no-Cleveland-appearance control. Examples: without LeVert 31–13,
without Hunter 44–11, without Curry 64–18, including Curry's two GSW appearances.
WITH Curry is a known-empty sample, not 0–0. Rostered-only Cleveland coverage stays
14/21 complete, seven cases/318 unknown cells. BKN0022400199 stays uncertified;
malformed originals, quarantines and disputed observations remain intact.

**Bounded follow-up:** final unfamiliar wording exposed an explicit-opponent
translation that could retarget a retained actor and drop another. Scope now
requires one fully consumed actor/polarity/clause; mixed roles remain explicitly
unfinished. Same-team conjunctions and accepted legacy matchup pairs remain.
Focused actual-catalog and source-derived positive checks cover this correction;
exact revision, independent review and required gates are recorded in its PR.

**Shared behavior:** explicit rostered absence retains qualified membership/DNP;
opposing-player, anywhere-in-game, player-stat teammate ownership and accepted
explicit-matchup participant clauses remain distinct. Missing or ambiguous
appearance lists withhold complete records. Zero-minute/blank rows without DNP
are unqualified. Original strict filters and original 46 positive fixtures remain.
Required focused tests, independent review, authenticated targeted R2 execution
and exact-head blocking gates are recorded in the feature PR; no whole-project
release audit, publication or backup audit is repeated.

**Exactly unsupported:** the original K08 evidence ledger remains
**16 PASS /26 MISSING DATA /4 LIVE** at its original rostered-absence scope.
Davis-family original IDs1/2/3/9/10/11/12/13/14/15/17/20/21/22/27/28/29/
33/34/36/37/39/40/42/43 lack qualified complete 2025-26 Lakers evidence under
that contract; ID39 includes WITH and ID40 literal-current. ID26 keeps the entire
Celtics/Knicks union. None is automatically upgraded by the new default; complete
appearance proof for those selected 2025-26 games is still unavailable. Original
questions, controlled positives, immutable baseline and historical evidence remain.

**Separate Live:** literal-current IDs4/5/19/38/current40, current cross-club
membership/publication and 24-hour freshness/readiness; K12 cold timing. Known
2026-27 readiness503/new_season_not_loaded, original failure receipts and 484
unavailable rate values remain unchanged. DQ-005/source hunts stay parked.

**Next after the role-guard PR's gated merge:** verify only its new deployed boundary,
then preserve the proof for a future combined protected release. Source replay
took about16s cold locally against a20s query budget; hosted cold loading of the
staged proof is not yet qualified and must precede any activation. Do not activate
data, expand historical collection or begin Live without separately scoped
authority. No new costs or automatic refresh. PR633 keeps its original passing receipts; the guard PR holds its own execution.

**Preserved:** production **0abc**, its 69 complete 2024-25 plus 93 prior 2023-24
cases, verified backup/restore, Cleveland qualified v2 ZIP SHA256
`a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`,
originals/v1, all safeguards and the completed limited snapshot. No background
collection or automatic worker is running. Exact PR receipts hold code hashes,
source identities and test counts; old results stay attributed to original runs.

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
