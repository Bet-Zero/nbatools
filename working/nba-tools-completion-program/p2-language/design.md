P2 frozen comparison design (before held-out questions)

Compare the current S1-S5 interpreter with one deterministic lexical clause
normalizer feeding that same interpreter/engine. Candidate.py is frozen before
independent holdouts; no tuning on those questions. This is an experiment, not
production adoption and not a universal parser rewrite.

Denominator: 20 independently authored valid questions, four each for S1-S5,
plus eight separate ambiguity/unsupported-extra-clause controls. The checker
specifies intended identities, season/date/sample order, owned thresholds and
independent raw-row expectations, including a different entity/value, reordered
clauses and two conditions with the same number. No safety control contributes
to positive completion. Already-used maker regression examples stay separate.

Code: S5 reviewed runtime0b92117f59310ba3078bc17c6250136bcc43b52d (local6222c89
same runtime); data: queue-d-production-0574735-20260716 cached full2023/25 raw
rows plus the four independently qualified S4 reports. File hashes will be
recorded before execution. This staged overlay is not a published generation.

Run each path once cold and three times warm per case; retain every answer,
selected identity/sample and latency. Count answered-correctly, wrong accepted
answers, refusals and ambiguities separately. Compare exact sample identities,
counts, W/L, averages and meaningful labels, not just route/schema agreement.

Limits: zero paid/provider calls, zero remote writes; local CPU only. Warm p95
end-to-end <=2seconds, cold <=5seconds; candidate median overhead <=20% or100ms,
whichever is larger. These are experiment limits, not a service SLA.

Selection: no known wrong accepted answer or lost clause; no positive regression
hidden as refusal; more correct held-out answers or demonstrably simpler reliable
interpretation at comparable coverage, within limits. Otherwise retain incumbent
and record the next bounded improvement. A model translator is not evaluated
because no provider/cost authorization is available in this session.
