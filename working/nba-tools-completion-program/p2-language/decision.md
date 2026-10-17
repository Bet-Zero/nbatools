# Frozen P2 language comparison: decision and evidence

Do not adopt the lexical-normalization candidate. It adds no correct held-out
answers and retains wrong accepted answers, failing the frozen selection rule.
Keep the incumbent while repairing the demonstrated shared interpretation defects;
this is not acceptance of its known incorrect behavior or of Core-1.

| Measure | Incumbent | Candidate |
| --- | --- | --- |
| Valid independently authored questions | 20 | 20 |
| Correct, including exact sample and labels | 12 | 12 |
| Wrong accepted answers | 3 | 3 |
| Refused valid questions, still required | 5 | 5 |
| Separate controls: ambiguity / refusal / error / wrong accepted | 1 / 4 / 1 / 2 | 1 / 4 / 1 / 2 |
| Maximum cold-process execution | 0.500 s | 0.486 s |
| Warm p95 execution | 0.080 s | 0.075 s |

Both pass the frozen latency limits. No paid/provider calls, network requests,
production changes or R2 writes were made. A model translator was not evaluated;
no model quality or latency conclusion follows.

The maker froze `candidate.py` and `design.md` before checker
`/root/availability_checker` authored the 20 positives and eight controls without
reading or executing the candidate. The checker independently derived raw-row
truth, then reviewed all 224 executions (28 cases × two paths × four repetitions).
`evaluation.json` contains verdicts for every repetition, source receipt hashes,
latency details and limitations. No candidate tuning or experimental rerun took
place after seeing holdouts. Subsequent fixes use these as regression examples,
not fresh held-out evidence.

The runtime is reviewed S5 commit0b92117f59310ba3078bc17c6250136bcc43b52d
(local6222c89 has the same runtime), now merged through PR476. Data is the cached
queue-d-production-0574735-20260716 raw snapshot with the four qualified BOS-LAL
report overlay. The overlay is staged and unpublished. Source hashes and exact
expected IDs are in `holdouts.json`; no 2024-25 team truth is assumed.

Frozen candidate SHA256:
`31819d844129ffe7514cb915ce3699bac9bb41d484baef4fa6d527abe301cf6b`.
Frozen holdouts SHA256:
`d65cf93f47b03bd9263105ecb91bb3e4936e73c9bbfb5a08d2261bbab39c1027`.

## Required follow-through

- `p2_s1_1`, `p2_s1_4`: opponent clauses lost beside grouping/punctuation;
  repair shared entity-span consumption, with fresh independent review.
- `p2_s5_1`: intended team/window lost; final-eight-games meaning remains required.
- Valid refusals `p2_s1_3`, `p2_s2_3`, `p2_s2_4`, `p2_s4_3`, `p2_s5_3`
  remain positive delivery obligations. Do not turn them into negative tests.
- Control4: missing last-games count silently broadens to a 44-game subset.
- Control8: Boston record with medical clearance becomes Derrick White averages.
- Control7 refuses after an incorrect subject rewrite/unsupported win_pct;
  this does not establish correct interpretation of subjective exhaustion.
- Deployed/rendered Core-1 and permanent availability publication remain separate.

## Reproducing the assessment

`receipts.json` losslessly packs repeated answer payloads and retains every
execution's timing. Run `restore_receipts.py` to recover all 56 original files,
checking each SHA256 against `evaluation.json`, then `evaluate_comparison.py` to
recompute the decision without NBA access or executing either interpreter.
`build_holdout_oracle.py` records the raw-only derivation. `run_comparison.py`
records execution at the frozen runtime with DATA_SOURCE=local,
NBATOOLS_DATA_GENERATION=legacy and NBATOOLS_DATA_ROOT pointing at the qualified
staging root. Its recorded source paths identify the original workspace; relocating
sources must preserve and verify their bytes, not regenerate expectations from
application output. No new benchmark framework or production input mode is added.

Cold-process timing excludes Python/module startup and may use warm filesystem
cache. It measures local query execution with lightweight sample capture, not a
browser/network SLA or deployed cold start. Team/split IDs come from captured
calculation inputs; player summary IDs come from returned game logs. The finite
questions are not a population-wide language success rate.
