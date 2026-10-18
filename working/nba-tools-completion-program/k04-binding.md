# K04 ranking acceptance binding

This binds the existing K04 row in the sole completion-program README; it is
not another queue. Ten primary queries and ten independently authored held-out
wordings were frozen before interpreter execution in
[k04-independent-oracle.json](k04-independent-oracle.json), SHA256
`d1dd08d99e15886db0e2a4f3e417b1db36d9350bd5bca3a631525c58d8d20ece`.
Checker `/root/availability_checker` derived them directly from the pinned
2023-24 regular-season player rows, source SHA256
`a455e553ceb0b4e74bd4caf37aca482c0a9aab193631b6f2b383b623f861d760`,
generation `queue-d-production-0574735-20260716`. The JSON's absolute source
path records the cached derivation location, not a runner dependency.

| Cases | Required distinction |
| --- | --- |
| K04-A1/A2 | Top-five total points versus points per appearance, explicit minimum40games |
| K04-B1/B2 | Top-five three-point/free-throw percentage, ratio of summed makes/attempts, explicit floors300/200attempts and default20games |
| K04-C1/C2 | Curry's top-three scoring games versus his last-three appearances |
| K04-C3/C4 | Brunson's top-four scoring games versus his last-four appearances |
| K04-D1/D2 | Top-five counts of >=40PTS games and >=10AST/exact0TOV games, with explicit tie policy |

The oracle retains every ranked player's source keys, totals, denominators,
full-precision metric, cutoff ties and next-two rows. Last/top samples retain
ordered game/team/player keys, PTS/REB/AST sums and means. Existing ranking ties
use metric descending, total appearances descending, player name ascending;
exact-N truncates and positions are sequential. Named-player top-game ties use
newer date first, unlike the separate league-game board. That family distinction
was clarified from the existing contract before execution and frozen in the
oracle. No universal tie policy or shared tied rank is implied.

The required actual-data selector is
`tests/test_k04_ranking_real_data.py::test_k04_rankings_match_frozen_raw_oracle`:
20 selected cases (ten primary, ten held-out). Each checks the frozen source
identity/arithmetic then actual answer identities, order, requested basis,
denominators, qualifiers and exact game keys where the response exposes them.
Event-count outputs do not expose player IDs; unique canonical names and counts
are checked against independently identified source players.

Five synthetic controls in `tests/test_k04_ranking_contract.py` discriminate
ranking-total versus average, ratio-of-totals versus average-of-percentages for
two shooting metrics, inclusive attempt floors, count ties broken by games/name,
exact-N positions and top-N versus most-recent-N game sets. These reuse the
existing box-score fixture schema; they are never real NBA publication data.
Existing predecessor coverage remains in leaderboard aggregation, B1 rankings,
top-N game-list and shooting-oracle tests. No runtime/parser edits are part of
this tests-and-binding lane. Baseline execution and required actual acceptance
remain subsequent evidence; fixture passes do not close K04.

## Frozen cached baseline and implementation handoff

The single cached baseline on accepted PR481 runtime (local `33971dd`, remote
main equivalent `13272cc49384b6d47739d0089234f6cc497dfe3a`) is retained in
[k04-baseline.json](k04-baseline.json). It is not a read-only runner acceptance.
All ten primary cases passed the independently reviewed response adapter; four
held-out cases passed and six remain unmet. Five controlled fixture cases passed.
No oracle values or language cases were changed after execution.

The initial adapter incorrectly assumed finder outputs exposed `team_id`, that
last-N summary display order equaled newest-first sample selection, and that
one event metric used the same output column on two valid routes. The checker
approved reconstructing full identity from exact source-qualified team
abbreviations, testing the exact selected key set separately from chronological
summary display, and recognizing each route's event column. Named top-game
ordering, full row counts/identities, per-key values and all frozen arithmetic
remain required. Original responses and initial adapter results remain retained;
only those saved responses were re-evaluated, without rerunning the interpreter.

| Unmet held-out case | Required interpretation | Observed baseline |
| --- | --- | --- |
| A1 accumulated points /40or more games | `season_leaders`, `pts_total`, minimum40games, limit5 | `leaderboard_multiple_metrics_unsupported` |
| A2 at least40appearances /scoring averages | `season_leaders`, `pts` per-game, minimum40games, limit5 | `leaderboard_request_unclear` |
| B1 three-point accuracy /at least300attempts | `season_leaders`, `fg3_pct`, minimum300`fg3a`, default20games, limit5 | `leaderboard_request_unclear` |
| B2 floor200free-throw attempts /percentages | `season_leaders`, `ft_pct`, minimum200`fta`, default20games, limit5 | `leaderboard_request_unclear` |
| D1 five largest counts of >=40PTS games | event-count ranking, `pts>=40`, limit5; existing `season_leaders/games_40p` or equivalent occurrence route | `leaderboard_request_unclear` |
| D2 >=10AST/noTOV /leading5players | `player_occurrence_leaders`, `ast>=10 AND tov==0`, limit5 | Correct event, but returns10players |

All cases require only 2023-24 Regular Season. These coherent held-out requests
remain required positive obligations. Do not replace them with refusals, skips,
changed language or a smaller denominator. Root remains the sole shared parser
writer; this lane contains tests/binding only. The next technical step is a shared
ranking-request grammar repair for eligibility/metric/attempt/limit meaning,
followed by independent review and execution of all20actual-data cases. Deployed
rendering remains separate; this baseline does not close I/N/L/D for K04.


## Current candidate evidence

Local50da0c4 preserves the frozen baseline and repairs all20 original raw-oracle
selectors on cached qualified data. Shared games-played eligibility spans are
excluded from metric anchoring; rank limits, attempt floors and metric basis
remain separate. A frequency used as a ranking key no longer collapses a board
to a scalar count. Explicit player population wins over generic team stat aliases.
Twenty RawQA cases passed693checks; human review remains literally unreviewed.

The independently frozen [second language set](k04-unseen-review.json) and its
[original failed responses](k04-unseen-baseline.json) retain the first result on
cb84a60:9valid probes,4correct4refused1wrongaccepted, plus3separatecontrols.
The wrong answer returned zero for a three-player frequency ranking. Raw truth
is Haliburton9, McConnell7, Conley6 under existing tie policy. On50da0c4 the
checker independently verified all9 repaired results and3controls against raw
rows, including Booker game keys and cross-stat attempt ownership. These are
now regressions, not a fresh unseen-language score. New source arithmetic and
output semantics were checked; no arithmetic implementation changed.

Checker /root/availability_checker approved the bounded20numerical+20RawQA
request conditional on final correct-worktree preflight/CI. Actualrunner and
production acceptance remain pending. Preserve K04 and broader program as open.

Finalruntime09e4f3c narrows newly added inclusive event-floor grammar to scoring/
grabbing/dishing verbs, preserving the prior generic games-with route boundary.
The checker approved this regression repair;68focused tests passed. The first
correct-source preflight had8076passed1527skipped and one refusal-reason drift;
finalpreflight is pending. Earlier invocation imported the oldrootcheckout and
is discarded as wrong-code validation, not candidate acceptance.


## Summary/ranking browser verification (2026-10-18)

The existing browser harness now checks all 13 K02 and 20 K04 questions on desktop/mobile, validates payloads against frozen raw oracles, and asserts visible sample/threshold meaning plus exact ranked table order and ties. Initial local browser evidence caught an undefined opponent name, stat-ranked rows reordered by date, incorrect >100% TS/eFG display and additive percentage totals, and encoded event labels. Bounded frontend repairs preserve original API calculations. The final 66 local executions pass numerical and rendered checks, with 462 frontend tests passing. See [summary-ranking-browser-verification.json](summary-ranking-browser-verification.json) for retained before/after receipt hashes, selected screenshots and scope. Qualified local `legacy` data does not certify production readiness. Independent review, CI and the fresh deployed selector remain required for D acceptance; no owner/human acceptance is implied.
