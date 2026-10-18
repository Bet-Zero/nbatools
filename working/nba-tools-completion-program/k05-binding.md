# K05 finite ownership and venue binding

The independent checker froze `k05-raw-oracle.json` before interpretation (SHA256 `fc372d2d5871a1bf1dd042fd1ff734bfcb538b5b16d69a239eda6853a5ba3a19`). This binds the existing K05 row; it is not another queue or whole-family acceptance. Four fresh wording probes remain withheld until the primary baseline is recorded. Runtime baseline is local `f3a9c6a`; source generation is `queue-d-production-0574735-20260716`, retained qualified 2023-24 regular-season raw player/team CSVs with the oracle's exact hashes.

| Case | Required sample | Games | W–L | PTS / REB / AST means |
|---|---|---:|---|---|
| K05-A1 | Lakers home, own points >=110, opponent points <110 | 8 | 8–0 | 124.75 / 51 / 31.625 |
| K05-A2 | LeBron home, own points >=25, opponent points <110 | 8 | 7–1 | 28.5 / 7.25 / 8.25 |
| K05-B1 | Bucks away, own points >=115, opponent points <115 | 7 | 7–0 | 124.28571428571429 / 46 / 27.571428571428573 |
| K05-B2 | Giannis away, own points >=30, opponent points <115 | 11 | 6–5 | 36.09090909090909 / 13.181818181818182 / 6.7272727272727275 |

Reuse S3's raw reciprocal opponent-team join and team-record input capture. Every condition must independently discriminate; the oracle records the exact false-predicate populations. Compare complete game/team/player keys and independently recomputed sums, means and W/L, then natural versus structured results. The two B cases add the required second entities, away venue and second thresholds without reacquiring accepted source data. Numerical, wording, fixture discrimination, browser and deployed acceptance remain separate obligations.

## Original execution and required selectors

Primary baseline `a0ddd78` preserves all four passing responses before held-out revelation. The checker then released `k05-heldout-wording.json` unchanged (SHA256 `ba9f0bd961ae14a6cae9fad03503a89fa265c965b3c3fea5b17f9cea39605851`). Its first results are preserved in `k05-heldout-baseline.json` at `39c9f66`: A2 passes; A1 drops the opponent ceiling and returns 30 games, 21–9; B1 refuses as unsupported; B2 drops the opponent ceiling and returns 25 games, 14–11. The correct populations remain those frozen above. No runtime repair preceded these artifacts.

Required numerical selector: `tests/test_k05_subject_ownership_real_data.py` (eight primary/held-out cases; each checks independent raw arithmetic and a natural/structured pair). Initial actual cached execution: five pass, three fail, zero skips. Raw QA case IDs are `k05_a1`, `k05_a2`, `k05_b1`, `k05_b2` and each `_heldout` sibling; the failing gate likewise reports five pass/three fail in `/workspace/work/k05-qa-baseline/exact-display-order`. The player log bindings use independent raw chronological order, not sorted game IDs; this matters for tournament game 22301230. Original payload baselines are unchanged. These are desired-positive tests, with no xfail, expected refusal or weakened acceptance. Root owns runtime repairs; actual runner acceptance and D remain outstanding.


Runtime repair (root e398c96): shared threshold extraction now retains explicit opponent stayed/finished score ceilings, inclusive reached-stat floors and exclusive did-not-reach ceilings with their respective owners. Away from home is one road filter. Original primary4/4 and heldout1/4 baselines remain unchanged; the heldout failures were two wrong accepted populations and one valid refusal. Repaired eight cached source-qualified natural/structured cases and8RawQA passed;127 focused owner/venue/non-point controls passed. Independentchecker verified full keys and arithmetic, then found and verified the negated-reach repair (own/opponent/team-on-player). These seen wordings are now regressions, not a new unseen generalization score. Finalpreflight8127passed1538skipped5warnings135.83s; CI, actualR2 and deployed acceptance remain required.
