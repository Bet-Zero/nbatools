# NBA Tools execution queue

This file is the project's only active queue. Rules are in `AGENTS.md`, direction
in `ROADMAP.md`. The [data-quality worklist](data-quality/README.md) holds data
exceptions only. No background worker is running.

The full previous checkpoint (to 2026-11-12, with every run ID, hash, reviewer and
receipt) is kept unchanged in
[checkpoint-history-20261112.md](checkpoint-history-20261112.md). Use it for exact
evidence; don't extend it.

## Resume checkpoint

**Lead: Codex. Application main `b041c4cc`, merged
[PR633](https://github.com/Bet-Zero/nbatools/pull/633) and
[PR634](https://github.com/Bet-Zero/nbatools/pull/634). Task complete, November 22.**
The limited Core-1 snapshot remains closed. Full original acceptance and
league-wide participation remain unfinished. No background collection runs.

**Now works:** owner-approved default team WITH/WITHOUT means appearances
**FOR the selected team**, including before joining and after leaving. Opponent
appearances are WITHOUT for that team. Explicit rostered absence retains strict
membership/DNP rules; opposing-player, anywhere-in-game and player-stat teammate
ownership remain separate. Accepted legacy matchup pairs remain supported.
A scalar explicit role must consume its actor, polarity and clause completely;
unrepresented mixed roles and unread negation return no reduced answer.

**Verified qualified staging:** `team-appearances-cleveland-2024-v1` certifies
all 82 Cleveland 2024-25 regular-season side lists from retained official sources,
with zero new collection. All 21 original pilot candidates have complete TEAM
WITH/WITHOUT answers. Examples: without LeVert 31–13, Hunter 44–11, Curry 64–18.
WITH Curry is known-empty, not 0–0. These full-season gains are **not activated**.
Proof SHA256 `fd637c6d36c4fd9ce30b9e3f769c9ba806f535b9a943dc4be3fc6314529df86a`.
Rostered-only coverage stays 14/21; seven cases/318 unknown cells. BKN0022400199,
malformed originals, disputes and ambiguous zero-minute records remain protected.

**Verification complete:** independent reviews have zero open findings; all
blocking pre/post-merge CI passed on the exact application revisions, including
all three post-merge full Python jobs. Existing development-security advisory
remains informational red. Targeted authenticated runs actually executed with
zero required skips: [qualification + Core-1 API 45081061855](https://github.com/Bet-Zero/nbatools/actions/runs/45081061855),
[role correctness 45083468571](https://github.com/Bet-Zero/nbatools/actions/runs/45083468571),
[six actual desktop/mobile checks 45081877451](https://github.com/Bet-Zero/nbatools/actions/runs/45081877451),
and [final three deployed API checks 45084724456](https://github.com/Bet-Zero/nbatools/actions/runs/45084724456).
Each remains attributed to its original revision/scope in PR633/634; no broad
manual release audit was repeated. Live app answers CLE without Curry vs GSW
2024-25 as 2–0; the game-wide version is empty; full-season LeVert stays unknown
on the published data. Exact deployed build and original readiness503/0abc
passed before/after. No production data, pointer or backup change occurred.

**Original Core-1:** K08 stays **16 PASS /26 MISSING DATA /4 LIVE** under its
original contract. The 25 Davis-family defaults and entire Tatum Celtics/Knicks
union remain unqualified as recorded in `core1-acceptance-map.json`; original
questions, controlled positives, baseline and historical evidence are preserved.
The new product meaning does not automatically upgrade any original outcome.

**Separate Live:** current-season membership/publication, 24-hour freshness,
literal-current cases and K12 cold timing. Known 2026-27 readiness
503/new_season_not_loaded, original failure receipts and 484 unavailable rate
values stay unchanged. DQ-005 and historical source hunts remain parked.

**Next:** stop this implementation and historical expansion. Preserve qualified
staging for a later combined release. Before activation, qualify hosted cold
loading (about 16s locally versus the 20s query budget), prepare the exact protected
package and obtain explicit approval. No activation, further collection/backfill,
new spending, automatic refresh or Live implementation is authorized here.

**Preserved:** active production **0abc**, its 69 qualified 2024-25 and 93 prior
2023-24 cases at their original scope, verified backup/restore, all safeguards,
and Cleveland v2 ZIP SHA256
`a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298`.

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
