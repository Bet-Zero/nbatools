# NBA Tools roadmap

Owner direction: 2026-10-02. This replaces the owner-operated ten-query review
loop. Earlier work and decisions remain in Git history; current shipped
behavior is documented separately in `docs/reference/query_catalog.md`.

## The destination

Ask an NBA statistics question in normal language and get the correct answer,
with the requested subjects, statistics, conditions, and time period intact.
The interface should show the answer clearly, explain its data coverage, and
use current data when the request calls for it.

The product covers player/team stats, records, rankings, comparisons, game
finders/counts, splits, streaks, stretches, and playoff history. Legitimate
missing questions are a build queue, not an invitation to redefine success as
refusing them. More elaborate guided research tools remain a later surface;
that distinction must not be used to exclude ordinary combinations of filters.

A refusal can prevent misinformation while implementation is incomplete. It
cannot complete the requested capability. Invalid requests and genuine
ambiguities have their own rejection/clarification tests. A verified zero or
empty answer is a valid answer, distinct from unavailable data.

## How work moves forward

```text
Collect questions we want answered.
Check what the product actually returns.
Independently verify the successful answers.
Group failures by the missing or broken capability.
Implement that capability and check new wording variations.
Save regressions, deliver it, and continue expanding.
```

Agents own that loop. The owner does not have to supply a new query battery,
read testing reports, check arithmetic, select technical phases, or relay
routine reviewer findings. Existing examples are input, not a syllabus the
owner must personally grade.

## Delivery order

**1. Complete everyday capabilities using the existing foundation.** Start
with recent-game team records, missing ordinary stat/count wording, and
correct player identity. Add concrete examples from existing exploratory
samples and recorded gaps. Reproduce first; do not rebuild working features.
Fix relevant wrong-answer risks within these delivery units rather than
waiting for another broad audit before useful work can begin.

**2. Complete combinations and data-backed gaps.** Preserve every meaningful
condition, then implement the missing calculation/data where necessary. Work
through team bench scoring, championship history, clutch/period information,
lineups/on-off, and other legitimate recorded gaps by reuse and dependency.
Some require new sources or different data grains. Those dependencies change
the implementation plan, not whether refusal counts as success.

**3. Verify the delivered experience and ongoing operation.** Test the actual
API/browser path, deployed revision and dataset, freshness, season rollover,
update operation, and practical response times. Repair observed failures.
Do not change monitoring policy merely to hide product timeouts.

The current execution order and concrete acceptance examples live in
`working/nba-tools-completion-program/README.md`. That is the temporary active
queue until this program closes, not an additional source of product truth.
Agents may reorder independent tasks to unblock delivery and must record why.

## What counts as progress and completion

Report capabilities and examples that now answer correctly. Keep desired
answers, necessary clarifications, negative tests, and open data dependencies
separate. Neither a passing test total nor a safe refusal is an answer-rate
score. If reporting coverage, name the fixed sample set and denominator; do
not remove hard desired questions or add easy negative tests to improve it.

Each delivery unit has a finite acceptance list and a clear stopping point.
Finishing one unit means that unit is done, not that every conceivable NBA
question is solved. Additional legitimate questions remain visible and are
selected for the next unit without another owner planning session.

The existing first-product capabilities must work through the actual interface
with representative combinations and unfamiliar phrasing. Required gaps stay
open; only an explicit owner product decision can remove a desired capability
from scope. No silent shrinking of the promise to match what already passes.

## Owner involvement

Bring back only unresolved product meaning, necessary account access/consent,
material new cost, or a consequential action outside authorization. Bring a
recommendation, not a technical menu. Routine implementation and verification
continue without the owner's participation.

Branding, naming, domain changes, and launch publicity remain separate owner
choices. They do not block improving and verifying the existing app.
