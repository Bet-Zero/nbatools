# Claude startup

Before planning or implementing work in `Bet-Zero/nbatools`, read `AGENTS.md`.
It is the shared delegation/security/verification contract. Then read
`ROADMAP.md` and `working/nba-tools-completion-program/README.md` for the current
engineering strategy, dependencies, acceptance and exact next action.

The 2026-10-02 A/B/C/D/O/E plan supersedes PR #312's Q1-Q6 sequence. The owner's
sample-query loop was an example, not a mandated method. Agents own technical
strategy and should execute the dependency-led plan rather than restart a broad
audit or ask the owner to choose a workflow. First implementation is A1 (identity),
then A2 (shared game samples); O1 (data/runtime verification) starts alongside
when capacity is available. Preserve any newer in-flight accepted work and use
the active queue if its continuation record has advanced beyond this starting
snapshot.

Desired questions must become correct answers. A safe refusal does not complete
a requested capability. Agents own diagnosis, implementation, numerical checks,
review coordination and continuation. Keep source/test provenance honest and
owner-only consent/cost/security boundaries intact. Do not make the owner grade
query batches or arbitrate implementation details. Follow live repository state
rather than an old chat handoff or historical acceptance label.

## graphify

Use the existing knowledge graph when available. Prefer scoped `graphify query`,
`graphify path`, and `graphify explain` for code navigation; use the wiki index
for broad navigation and the full report only when needed. After code changes,
refresh it with `graphify update .` when available. Graph installation/cleanup
is not a prerequisite to capability delivery.
