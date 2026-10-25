# K09 finite sequence binding

This binds the existing K09 queue row. It adds no capability registry or new queue.
Base: `2acb83fcc0839c75caab9fa47401227bb043d98e`. The independent checker
`/root/gate_checker` froze [k09-raw-oracle.json](k09-raw-oracle.json) from restored,
qualified CSVs before interpreter execution. SHA256:
`35a679ea564698c1fca4669d10d28f89da44a87d6692303b643c59e26718d414`.
All original case queries/IDs/numeric expectations were retained when three team
source hashes and player-run W/L joins were added. These are existing snapshot
rows, not new NBA acquisition or a claim of complete seasons/participation.

Generation: `availability-opening-s4-v1-20261017`; manifest:
`5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`.
The verified inventory and permanent backup retain their original dates. Player
outcomes join unique season/type/game/team keys to qualified team rows; a player
CSV has no W/L column. Team stretch margin expectations use reciprocal points,
not unchecked historical plus/minus.

| ID | Required meaning / source witness | Exact acceptance binding |
| --- | --- | --- |
| K09-T1 | Miami's longest winning run in 2012-13 is 27 observed games, Feb 3–Mar 25 | `test_k09_bound_sequences[K09-T1-query]`: exact source IDs/boundaries, length, outcomes and means |
| K09-P1 | Curry's longest 20-point appearance run in 2025-26 is 11, Dec 20–Jan 11 | `K09-P1-query`: exact appearance IDs, 20-point predicate and means; no team-game absence/health inference |
| K09-R1 | Miami has four distinct 5+ winning runs (6,6,27,8), not overlapping five-game windows | `K09-R1-query`: all maximal run IDs/lengths and count 4 |
| K09-R2 | Curry has five distinct 3+ runs of 20-point appearances in 2025-26 | `K09-R2-query` plus `synonym_control_query`: same source IDs/count 5 for appearances and games; fixture count 8 is separate synthetic evidence |
| K09-W1 | Boston's best 10-game 2023-24 window is 10–0/+20.3; last ten is 7–3/+9.9 | `K09-W1-query` and `last_n_control_query`: different exact windows, dates, outcomes and qualified margin |
| K09-W2 | Curry's best five-game 3P window in 2015-16 is 29/49=.592; last five is 24/63=.381 | `K09-W2-query` and `last_n_control_query`: exact appearance IDs and ratio of summed makes/attempts |
| K09-C1 | Curry's five 20-point appearances Jan 22–Apr 5 remain one appearance run despite absent team-game dates | `K09-C1-query`: date sample and exact five IDs; no assertion that missing rows establish injury or DNP |
| K09-C2 | Explicit 2015-16..2016-17 made-three run spans 84 appearances; one-season control is 79 | `K09-C2-query` and `single_season_control_query`: exact boundary IDs/season scope; team stretch season boundaries remain separate |

All twelve real query/control selections live in
`tests/test_k09_sequences_real_data.py`; corresponding `k09_*` Raw QA cases use
this same frozen oracle. Required real-data selections may not skip.

`tests/test_k09_sequences.py` supplies controlled discriminating witnesses:
maximal runs rather than sliding windows; a failed or missing stat ends a run;
an explicitly filtered home sample may omit road games; an absent player
appearance is not a failed stat or health fact; selected-season streaks can cross
seasons. Best-versus-last windows differ for both a team and player. The 2+2
team-game sample cannot fabricate a three-game within-season window; this is a
separate no-match safety control, not a positive completion claim. Existing
player-stretch cross-season labels/behavior are retained, not silently made equal
to team-stretch semantics.

## Confirmed repair and evidence states

The independent wording “How many times did Curry score 20 or more points in 3
straight appearances in 2025-26?” dropped the run-length/count request. Its games
synonym returned eight synthetic fixture runs, while appearances returned an
unbounded streak list. `test_player_appearance_count_preserves_run_length_and_stat_threshold`
first reproduced that failure. The bounded repair canonicalizes the appearance
unit only inside the existing streak reader; original subjects, clauses and query
text remain intact. No computation or continuity policy changes.

Implementation, qualified numeric acceptance, unfamiliar-language checking and
actual deployed rendering remain separate. Independent final review, stable
broad coverage, authenticated targeted R2/Raw QA, normal CI/landing and the existing
browser runner on the changed deployment remain required before K09 acceptance.
Fresh reviewer wording is reserved until the candidate freezes. Revealed failures
remain regressions. Core-1 and K10–K12 are not closed by this binding.

## Candidate checking, October 25

Semantic candidate `22b15a89` was independently approved by `/root/gate_checker`
after checking the frozen oracle, eight source hashes, count/continuity meaning
and original-query preservation. Fresh qualified-source Tatum/LeBron/Curry
wordings changed entity, threshold and order; exact maximal-run counts/endpoints
matched independent raw loops. Six playoff/history/non-streak appearance collision
controls were unchanged. The revealed Curry appearance failure remains a regression.

Author checks before broad validation: 163 focused cases passed; all twelve source
queries/controls passed on byte-verified restored data with zero skips; twelve Raw
QA cases passed 73 assertions with zero suspicious findings. Six frontend-hero
informational flags are not failures. The local actual API and reused unchanged
served asset `index-vEjeGbzQ.js` passed all 24 desktop/mobile answers and 48 readiness
brackets using the same frozen numerical validator, actual table values, identity
contexts, screenshot hashes and absence of errors/overflow. This is qualified
local/source evidence, not new authenticated R2 or deployed acceptance.

The browser check is `tests/test_deployed_k09_sequences_browser.py::test_deployed_k09_sequences_desktop_and_mobile`.
It uses the existing complete-bundle capture runner and all twelve source-bound
query/control selections. The K09 bundle retains the existing seven-second
admission spacing in both local and public checking. Other bundles and production
admission/timeout limits are unchanged. Current generation/asset/readiness,
subjects, count versus longest, exact source boundaries/values, displayed streak
lengths/W-L/dates and best-versus-last rates are required. Its final independent
gate review, stable broad preflight, hosted R2/QA, normal CI/landing and one changed-
deployment capture remain pending.
