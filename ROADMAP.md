# NBA Tools delivery strategy

Revised 2026-10-02 after source-and-evidence review. This replaces the delivery
order in PR #312, not its delegation of engineering work to agents. The owner's
sample-query loop was illustrative, not a prescribed methodology. Agents are
responsible for recommending and executing the engineering approach.

## Destination

An NBA statistics search product that answers ordinary, reasonably specific
questions correctly across players, teams, records, rankings, comparisons,
finders/counts, splits, streaks, stretches and historical/playoff analysis.
People should not need to learn the parser's preferred sentences. Answers must
preserve the requested meaning, expose the actual sample and statistical basis,
and use complete enough, current enough data for the claim being made.

The long-term destination includes legitimate missing statistical capabilities
and richer guided tools already described in
`docs/reference/natural_search_and_deep_tools_boundary.md`. A delivery milestone
is not a silent reduction of that destination. Salary/trade-rule engines are
not this project. Branding and launch publicity remain separate owner choices.

## Chosen approach

**Complete shared statistical capabilities, deliver them through natural search,
and develop data/operation in parallel.** Example questions are evidence and
intake; they are neither the architecture nor the entire requirements list.

Keep the shared Python query service, established calculations, result contracts,
React interface, immutable data generations and useful checks. Incrementally
consolidate duplicated sample/filter/metric behavior as real features need it.
Do not rebuild the application, design a universal query framework first, or
continue indefinitely with independent phrase patches and route allowlists.

The most useful organizing questions are:

1. Can the system select the right people, teams and games?
2. Can it apply the requested operation and statistical basis to that sample?
3. Can those abilities be combined and reached through normal language?
4. Does the necessary data exist, remain current, and reach the deployed app?
5. Does the actual user-facing answer remain correct and usable?

## Delivery sequence and dependencies

| Work | Outcome | Why this order |
| --- | --- | --- |
| A. Identity and sample selection | Correct entities, seasons, dates and last-N game samples; recent records and summaries work consistently | Every calculation depends on the right rows |
| B. Core operations and statistical basis | Counts, totals, averages, rates and rankings mean what the question asks | These operations unlock multiple answer families and compound questions |
| C. Composition across families | Meaningful filters work with summaries, records, comparisons, splits and sequence queries | Prevents rebuilding each feature/filter combination independently |
| D. Coverage and additional datasets | Historical/reference, role/bench, period/clutch, lineup/on-off and other legitimate missing answers | Build in dependency order; inspect source feasibility early |
| E. Integrated product acceptance | The required capabilities work through the deployed interface and remain operational | Proves delivered behavior, not just implementation |

A data/runtime work lane starts alongside A, not after D: inspect actual coverage,
confirm remote validation, establish season/date correctness, measure deployed
behavior, and identify source/access/cost dependencies. Each feature still has
its own deployed acceptance; E is an integrated check, not the first deployment.

There is one integration owner and at most two implementation lanes with
non-overlapping files, plus independent review. With only one execution agent,
interleave the same work rather than pretending parallel capacity exists.

The concrete work packages, seeded capability map, acceptance rules and next
action are in `working/nba-tools-completion-program/README.md`. The supporting
review is `working/nba-tools-completion-program/review-2026-10-02.md`. These are
active task artifacts, not additional sources of shipped-behavior truth.

## How progress is measured

Maintain a small capability map from the existing route inventory, product docs
and query examples. Distinguish implemented, numerically verified and deployed.
Do not create a new dashboard/framework to maintain it. Use source inspection
plus paired structured/natural queries to distinguish language gaps, computation
gaps, data gaps and display/runtime defects. Unmeasured cells remain unknown.

For each selected capability, define its meaning and acceptance before repair,
including normal variations and meaningful combinations. Use existing tests,
small independent calculations and representative real data to check it. Keep
some formulations out of the maker's tuning set for independent checking.
Required questions remain open until answered, including valid zero/empty
answers when coverage is sufficient. Clarifications and negative tests are
separate; neither contributes to desired-answer completion.

Report user-visible capabilities delivered and the remaining blockers. Test
counts, phrase counts and successful refusals are not product progress scores.
If reporting a percentage, retain the declared denominator, scope and all
required missing cases; report held-out language performance separately.

## Finishing without an endless project

The core milestone covers the named answer families using qualified game data,
ordinary statistical bases, normal language and the meaningful combinations
specified in the execution map. It does not claim that every historical or
specialized dataset already exists. Missing historical/event-data capabilities
retain their own open delivery entries and source dependencies.

A core milestone is complete only when its required acceptance cases have no
unresolved wrong, missing or unverified answers; applicable independent review
and automated checks pass; deployment is verified; and update/rollover operation
is proven for the intended coverage. Do not call the broader program complete
while required extended capabilities remain open. External blockers change
sequencing, not the definition of a finished feature.

At a milestone boundary, select the next dependency-backed capability group and
continue under the same authorization. Do not reopen the entire plan, add
unrelated governance work, or request a fresh owner query battery.

## Agent ownership and boundaries

Agents own technical choices, implementation, numerical checking, data research,
review coordination, merge readiness and continuity. Ask the owner only for
unresolved product choices, necessary account consent/access, or consequential
cost/security actions outside authorization; bring a recommendation.

Preserve the existing security/privacy boundaries and the documented fixed-plan
cost ceiling with $0 permitted metered overage. No new paid language-model
service, hosting migration, public-feedback persistence or credential expansion
is authorized merely by this strategy. Investigate and report a concrete
constraint rather than turning it into a general stop.
