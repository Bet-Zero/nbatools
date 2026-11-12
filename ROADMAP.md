# NBA Tools roadmap

Where the project is going, in order. Current rules are in `AGENTS.md`; live
status and the next action are in the Resume checkpoint of
`working/nba-tools-completion-program/README.md`. The pre-2026-11-12 roadmap
text is in Git history (`git show 95cb705:ROADMAP.md`).

## Destination

A person asks an ordinary, reasonably specific NBA statistics question and gets
the correct answer, with the subject, conditions, sample and metric they asked
for. Natural search is the front door; the same engine serves the API and CLI.
Nobody should have to learn special wording.

Scope is 1996-97 onward, prioritizing the 21st century. The destination covers
summaries, records, finders and counts, rankings, comparisons, splits, streaks,
stretches, playoff history and qualified specialized stats. Guided builders and
profiles come later (`docs/reference/natural_search_and_deep_tools_boundary.md`).
Salary and trade-rule engines are a different project.

## Milestones

| Milestone | What "done" means | Status |
| --- | --- | --- |
| **Core-1 (snapshot release)** | The twelve K01-K12 capability groups answer correctly on the data already held: published history plus the fixed 123-game 2026-27 cutoff. Verified numerically against independent expectations and checked once on the deployed site (desktop and mobile) for a frozen release candidate. Unknown values stay unknown and are labeled. | Active. Owner scope decision 2026-11-11. |
| **Live** | Literal "this season" questions, 24-hour freshness and readiness, current cross-club membership, current-season publication, and any requirement B moves here from Core-1. | Deferred, not deleted. Needs a working refresh route, which is parked. |
| **P2 language comparison** | Compare the current parser with one bounded alternative (for example a constrained AI translator into the existing structured request) on an already verified subset, with a fixed budget and a clear stop point. | After Core-1, or earlier only if it doesn't delay it. Paid access needs B's approval. |
| **D: extend** | More combinations, source-dependent stats and later guided surfaces, picked from the carry-forward list. | After Core-1. |
| **O: runtime** | Measured latency and cost work on existing data. | Interleave when it doesn't block Core-1. |

## Rules that shape the plan

- **Core-1 is finite.** Its requirements are the twelve K01-K12 rows and the 46
  original K08 participation positives, preserved byte-for-byte in
  `working/nba-tools-completion-program/acceptance-baseline-pr582.md`. Each
  requirement ends in one of three states: passing, moved to Live by B's
  decision, or explicitly deferred with its missing evidence named. Nothing is
  silently dropped and no refusal counts as passing.
- **Four separate proofs.** A capability is complete when it is implemented,
  numerically verified (fixture versus real data stated), checked with
  unfamiliar wording, and verified on the deployed site. A green test total, a
  route, or a refusal is not any of these.
- **Fix interpretation in shared logic.** Repeated subject swaps, dropped
  clauses and reparsing are shared-meaning defects, not phrase patches. No
  universal-engine prerequisite and no rewrite.
- **Data quality runs beside product work.** Flagged data becomes a scoped
  exception record (`working/nba-tools-completion-program/data-quality/`), not a
  reason to stop unrelated work. Provisional data can exercise a feature but is
  never proof of the real NBA answer.
- **AI models never supply NBA values** or run unrestricted generated code or
  SQL. A translator may only produce validated structured requests.
