# NBA Tools execution queue

Owner-approved direction: **2026-10-15**. This remains the only active queue.
Read `AGENTS.md` and `ROADMAP.md`. The owner approved the reassessment and asked
for an immediately executable plan with durable agent-to-agent continuation.
Runtime continuation is recorded below; implementation, independent fixture evidence,
real-data acceptance and deployment remain distinct.

The old A1-first start and four-stream execution instructions are superseded.
The A/B/C/D/O/E capabilities and unfinished requirements are retained, not reset.
The full pre-revision queue and detailed PR history remain available at the
[immutable October 15 snapshot](https://github.com/Bet-Zero/nbatools/blob/ce5c0cef2f46cbd086c48535b427df142be4aa8a/working/nba-tools-completion-program/README.md).
`review-2026-10-02.md` is historical rationale, not the current sequence. Do not
require a new agent to read that history before starting the task below.

## Resume checkpoint

Replace this checkpoint as work advances; do not append another active diary.
Owner explicitly resumed normal development on 2026-10-18 (America/Detroit), accepting minimum cloud/data setup. Live main and all five pending feature heads were reconciled before changes. This is not a frozen head to reset to; check newer branch/PR evidence.

| Field | Current handoff |
| --- | --- |
| Stop marker | ACTIVE — PR517 final evidence-only CI/normalmerge pending; substantive source/UI/browser/broad gates passed. Root has a separate qualified opposing-player played candidate ready for independent checking. No owner blocker, source request or production publication. |
| Main / integration | Live main efc28c9f05dea2ef0e98c2c9263c212a82c23cb8 includes PR515 and PR516. Post-515 CI39179113242 and post-516 CI39181088285 passed all checks/full-suite backstops. Production generation availability-opening-s4-v1-20261017 is unchanged. No data publication. |
| Active candidate | codex/opponent-played, maker /root, checker /root/comparison_checker; runtime/tests6047802101bef79e8f671ad6f16e4a901cf6876c on baseefc28c9. Team records propagate explicit matchup context to played filtering at each existing stage. Shared qualified observations match exact game/date/player/side; genuine DNP evidence permits an empty played sample, unknown/conflict/ambiguous evidence cannot become a partial answer. Existing same-team default remains. Independent sourceoracle frozen before implementation SHA5a37f23e80b4799512cd336a81550260f2101e08895319cc58f356e33b3ed9d9. 75focused and6actual natural/structured tests pass. Independent heldout/source review and stablepreflight next; no R2 request yet. |
| Verified / pending | K06 current-generation numerical/QA and PR492 production gate remain accepted. K07 PR493/494 production gate39176663385 passed24 answers/48 readiness and is now closed; milestone row updated. PR516 gate39178679090 adds28 production answers/56 readiness for opponent unions, qualified pairs and scoring/window ownership. Full prior RawQA504 pass/10 absence-status failures and521-filter coverage40dropped/292refused remain unfinished; unchanged red corpus was not rerun. Bounded gates do not certify all Core-1 requirements. |
| Exact NEXT | Finish expected-head merge/postmergeCI for PR517 (final46dd5f795d12f63d002d480822cfe68c998b0814), then integrate its accepted main into this candidate without losing either worktree. Obtain independent exact-SHA review for opposing-player played filters, sourcecontrols and actualconsumerlabels; stablepreflight and boundedR2 follow. Primary source qualifies LAL vs BOS with Tatumplayed2023-24: games22300403+22300684,1–1/229PTS95REB54AST; 2025-26 bothsourceDNP gives qualifiedempty. All46 original462 positives remain open and unchanged. No fresh data, tenure/nonmembership inference or Boston17 publication needed. |
| Source preparation | K01expanded source39091056182 passed1required0skip,16CSV including sixEwing-era teamfiles; oracle freezes348coveredgames205–143/5027PTS2928REB412AST. PR482 combined no-write snapshot39091103560 (reviewed072bd3b78389d9cf27058d6bf0eb137495563bd1/requeste23a27b00ee9e9910e4d441c43c9c586f27fca89) passed1required0skip, independently accepted703objects402749125bytes,684base unchanged+18overlay+derivednames. Artifact12122218736 ZIP290778578b035bdb4df8c1594f238697fa7d40c2dea32d72586df93a67b2f801; manifest5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52. Sixconsumerchecks/Brownkeys passed; projectedbucket1167483320bytes. No production writes. |
| Pinned data | **Active production R2 generation** `availability-opening-s4-v1-20261017` (pointer switched `2026-10-18T06:15:50Z`; manifest SHA256 `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`). Prior `queue-d-production-0574735-20260716` retained unchanged; five qualified NBA participation-game sources are included but not season-wide evidence. |
| Next independent implementation | K08/#462 original13df00fb84f142a0f4803ac196ebe9ff3a1355db andall46positiveabsence obligations remain open. Exact Feb1PDF is retained at source-evidence/tatum-20260201; hash e88c222a9fa1f6a31e77d43fcfa990a28ff38e3a21592c7a1f5b6bc20c42cff9/27521B. IndependentBostonoracleSHA986622658fb005269483b23e9bbed509c3aa67f2fe9200a28f5bc7cac09ab964 qualifies17listed=12played2DNP3inactive, Tatum1628369 explicitinactive forBOSgame22500702. Scoped extension can use this existingfact; no additionalsource needed forBoston. FullMIL identityrequest remains exactexistingbackup-laptophandoff, not newcloudinvestigation. Same-date other-game/tenure/nonmembership semantics remain unaccepted. |
| Local state to preserve | Bounded recovery still cannot access `c10936b` or the old stopped-runner ports; GitHub lookup422 and known worktrees absent. Current tools cannot reopen that volume. All recoverable checkpoints/branches are retained remotely; current recovered NBA files independently hash-match durable staging. No reset, prune, force-push or historical cleanup. See `cloud-operations/preservation.json`; restoration/export of the original volume is needed only to recover its unique unpublished work. |
| Deployed verification | PR512/513/514 bounded production gate39178679090 accepted: reviewed7e6cf3e/requeste76a87542eca0cc482f09a9d65db16f8f0595d0b,1 required test,28 desktop/mobile answers,56 ready immutable current-generation checks,0 skips/errors. Artifact12155098866 ZIP6588221B SHA4ed0b23a0da316869a1408d587fa3b6008048cabe5088f0435836f40679a4eb2; receiptSHA36939ad58665700413cd4c67b15059ccae4328207756b28d00e1d47dfaee4f48. Actual assetindex-BYEKgTmU.js; stable deployment71df265/dpl_ERso1oAX1PrNWG7WpFv5Z6iuR7sA. PR493/494 earlier24-answer production gate39176663385 also accepted. Lead and checker verified underlying evidence and visuals. Free preview quota recurred; no upgrade, blind retry or production data write. |
| P2 and other unfinished findings | PR478 records the frozen comparison: both paths12/20 correct,3 wrong accepted,5 valid refusals; 8 controls separate. Do not adopt the candidate or rewrite frozen results after repairs. PR479 repairs the two lost-opponent cases; PR480 addresses final-window grammar. K03 review also retains nonzero exact equality and distinct-player grouped OR as unfinished composition gaps; new league exact-nonzero wording is contained, not delivered equality. Single-opponent prefixed question copula is repaired by merged PR511. Still open: medically-cleared language can change subject, and broader qualified entity validation. Independent heldout review also reproduced an unchanged question+true-opponent-list subject swap on main15c51bd ande5e08b7: “What was New York’s away record against Miami and Washington in2023-24?” and the equivalent opponent-prefix form answer WAS-vs-MIA. The plain subject-first list computes NYK3games2–1/340PTS123REB78AST, but final metadata incorrectly says WAS/MIA on both base and candidate; a Lakers/Celtics+Wizards opponent-split query also computes LAL rows with wrong final metadata. Merged PR512 repairs these bounded subject/list-metadata examples and ordinary team/player comparison unions with exact source checks. Still unfinished: explicit team-filter player-comparison grammar, owned OR/grouped scoring compositions, self-opponent list interpretation, and leading-list plus third-team-condition refusal labels. PR514 delivers bounded AND/window own-team and named-opponent scoring conditions; it does not close broader boolean grammar. No general grammar completion or positive demotion is claimed. PR462 originalhead13df00fb84f142a0f4803ac196ebe9ff3a1355db retains46positive obligations; local462-integration has unpushed ports,88passed1failed due to absent qualified BOS+NYK/Tatum nonmembership. Preserve those positives. |
| Publication boundary | **PUBLISHED AND VERIFIED.** On 2026-10-18 the owner authorized package `opening-s4-availability-v1`, then separately approved the protected GitHub deployment. Run [39102232398](https://github.com/Bet-Zero/nbatools/actions/runs/39102232398) `success`: `published_and_verified`, 703 immutable objects / 402,749,125 bytes, exact manifest SHA256 `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`, active pointer verified, previous generation retained, six deployed application answers verified and readiness `ready`. Durable [release receipt](https://github.com/Bet-Zero/nbatools/releases/tag/data-publication-39102232398) includes `receipt.json`. Publication environment now confirmed valid: `r2-publication` ID `24614443886`, main-only Branch, required reviewer Bet-Zero, admin bypass disabled. Earlier HTTP404 audit was from before setup and is **resolved**. No recurring publication authorization. |
| Runtime / continuation | PR515 merged a22f972 after independentde825b1 approval, R2run39178568416 (3 actual/0 skip) and finalCI39178795488. Source17CSV/import receipt/scope retained beside originalPDF; production five-game availability coverage unchanged. All46 original462 positives and other-game/tenure/nonmembership limits remain open. PR514 merged71df265 with8 actual source tests and full post-mergeCI. PR516 production acceptance is bounded to14 cases. Owned OR/grouped composition and the separately reproduced ownerless OR scope/label defect remain unfinished. No new NBA fetch, credentials, spending, publication or background worker. |

S4 source acceptance: run [39007679992](https://github.com/Bet-Zero/nbatools/actions/runs/39007679992),
reviewed `9895ee04ec9b0144e314dac3e9981e3737b6aacc`, request
`9c844e3d7a96c0be9fd040764264102b2fc97c0f`: **1 selected/executed/passed, 0 skips/failures/errors/xfails**.
Artifact12091388833 ZIP SHA256 `8f459cbbb90d7652ccb84e77cb625c416e63376cc2b1b454c5d8fb5e452573d2`.
Four official BOS-LAL PDFs: 2023-12-25, 2024-02-01, 2025-12-05, 2026-02-22.
Checker independently matched all91played names/teams/minute-seconds, all8team
240-minute totals, receipt/import hashes and both68-row season files:136listed
rows=91played+45explicitDNP. Tatum played both2023 games and explicitly did not
play both2025 games. Scores: BOS126-LAL115; LAL114-BOS105; BOS126-LAL105;
BOS111-LAL89. Initial run39007279540 failed on PDF-extracted `SCORE BYPERIOD`;
the bounded whitespace repair preserves all source/date/team/identity/total gates.
34report tests passed. These four games establish no season-wide absence claim.

S1/S2 accepted numerical scope on `queue-d-production-0574735-20260716`:
BOS home versus NYK: 2023-24 **3 games, 2–1, 356 points**; 2025-26 **2 games,
1–1, 212 points**. Curry >=25 versus POR: **2 games/58 points** and **3 games/121
points**. Curry >=25 versus LAL: **3 games/109 points** and an explicitly empty
2025-26 sample (his sole recorded appearance scored23). The positive 2024-25
LAL sample, **3 games/112 points**, must remain excluded. Exact raw IDs, PTS/REB/AST
means, labels, structured/natural splits and one-season controls passed. Fixture
suite51passed; checker held-out GSW away/NYK and Curry>=28/BOS passed. Deployed
S1/S2 verification subsequently passed in39010886782; remaining K07/S4 obligations stay open.

S3 request `248b8e245d35168e423aaa4785bc124f9e04a631` on
`r2-validation/subject-ownership-10ff2e2a` selects
`tests/test_subject_ownership_contract.py::test_s3_owned_scoring_and_venue_actual_data`.
Independent raw expectations: LAL own>=110/opponent<110/home, 2023-24,
**8 games, 8–0, 998 points**; LeBron own>=25/opponent<110/home, **8 games,
7–1, 228 points**. Tests-only candidate passed fixture and independent unfamiliar
road/entity/threshold probes; actual gate subsequently passed in39005515673 and implementation merged in PR471. Reconcile with latest main
before extending its scope. No runtime drift requires repeating already valid source
arithmetic; new acceptance must still execute.

S5 evidence: numerical artifact12091999945 ZIPe3a5494e5a8b7ea16be736f6f92277fb8d19337460ab1ed9ce33a5c286f373b3;
rawQA artifact12092762362 ZIPc8785c92975ffdb977cbed574a90b5e79c98a8609cac0f3248273afe7191295f.
BOS date+NYK3games3–0/363PTS; last10 window>=110:6games5–1/762PTS;
last10 qualifying:10games8–2/1255PTS. Curry date+LAL3games2–1/109PTS;
last10 window>=30:2games1–1/66PTS; last10 qualifying:10games6–4/364PTS.
ExactIDs/REB/AST/labels independently verified. Wider product-review fields retain
human_review_pending/missing_variants; no invented human signoff or family closure.
S5 runtime merged01c38d9130957e90bc32f38b739ff1ca396cb76d; deployed S5 passed6required actual checks in39086312677 after the rate limit cleared organically. Bounded P2 evaluation is complete in PR478; its candidate was not adopted. No paid model/provider authorized here.

S1/S2/S3 deployed numerical evidence: corrected reviewed9da2e10f7fb694274bb9c1154b598d37fb0e54f1,
request6555c70b7381945b68bc180e5848ebe385ef3a63, run39010886782 passed4/4zero skips.
Artifact12092947116 ZIPbe02a8900942baea03c17296857fdc5f648c59345661529debb5564ec60f3727.
Checker /root/availability_checker independently confirmed four API responses,
identities/labels/numbers and all eight before/after readiness checks. Generation
is bracketed as queue-d-production-0574735-20260716, not attributed per response.
Earlier39010672735 remains failed4/4: test read metadata at wrong envelope level;
corrected access retains all assertions. Test-only branch merged as PR475; post-merge CI39011702006 passed.

S4 bounded actual evidence on the same pinned base plus four qualified official
reports: games22300403/22300684 with Tatum (2023-24), Celtics1–1/115.5PPG,
Brown13.5PTS6.5REB4.5AST; games22500338/22500823 without Tatum (2025-26),
Celtics2–0/118.5PPG, Brown31PTS8REB7.5AST. Each opposite named-season bucket
is qualified empty. Natural clause orders and structured queries match exact
game/team/player IDs. This is four-game coverage, not seasonwide absence,
injury/status, permanent storage or deployed S4 acceptance. A teammate-owned
statistical condition is safely contained and remains an unfinished capability.

### First-session procedure

Inspect the repository without resetting or overwriting another agent's work:

```sh
git remote -v
git status --short --branch
git fetch origin
git log -1 --format='%H %s' origin/main
```

Read live PR metadata, changed files, discussion and check results through GitHub
or `gh`. The observed branch names above are resume leads, not proof a worker is
still running. Coordinate on the PR; preserve its author/session evidence. If its
head moved or merged, inspect that actual revision before choosing the next step.
Do not create duplicate repair PRs without explaining why the original cannot be
continued. Never force-push someone else's work to match this handoff.

On the #462 candidate, after the normal editable project installation in an agent
execution environment (not the owner's laptop):

```sh
DATA_SOURCE=local python -m pytest -q \
  tests/test_participation_coverage.py tests/test_played_season_splits.py
```

These are fixture-only checks on #462, not real NBA verification and not a
request to treat the mixed candidate as releasable. The 46 known positive
absence requirements remain open and intentionally fail its normal suite.
When extracting independent work, test the isolated candidate separately and
keep missing-source evidence and regression expectations traceable on #462.

### How to resume execution without an endless red PR

1. Check the current #462 diff/commits and the approved S1/S2 evidence. Find the
   smallest truly independent P1 delivery that does **not** rely on invented
   absences. Start its candidate from live main and carry only necessary code,
   positive tests and corpus cases. If no such slice exists, move to another
   independent package rather than refactoring the blocked P0a all night.
2. Verify that new PR with a real checker, required selected/executed/skipped
   counts on pinned R2 where applicable, broad applicable CI and actual output.
   Merge only green and correctly scoped changes; do not use the status of #462
   as a substitute for the isolated candidate's own evidence.
3. Leave #462's 46 required absence obligations open on their original candidate.
   Don't delete, mark expected failure, weaken, or disguise them as safety passes.
   Investigate source sufficiency separately. A future qualified dataset/contract
   unlocks their implementation. More unrelated P1 commits on #462 only increase
   the unmergeable backlog.
4. After a safe independent merge, publish one concise checkpoint to this same
   queue on main and update #462's PR discussion. If a Codex turn ends, its
   successor uses the latest pushed PR checkpoint and checks whether a scheduled
   thread wake-up is **actually** enabled. Do not claim invisible automation.

The aim is continuous *forward progress*, not removal of legitimate failure gates
or pretending an interactive Codex turn is an always-on service.

## 1. Preserved product and starting evidence

1996-97 onward is the working historical scope, prioritizing the 21st century.
Earlier history is optional. Do not delete existing older rows or call a partial
career complete. Salary/trade-rule work is outside this repository's purpose.

| Area | Evidence retained at the revision boundary | Implication |
| --- | --- | --- |
| Core data | O1 recorded 684 served files and 60 player/team/game season-type slices, 1996-97..2025-26; most older manifests are legacy. Coverage tests/runs are in the immutable prior queue | Reuse the qualified snapshot. This is not exhaustive independent proof of every value or current freshness |
| Identity/sample | A1/A1b and A2 implementations include id-based selection, renamed players, dates and last-N semantics; shared helpers and real-data tests exist | Do not rebuild from scratch; preserve and verify affected behavior |
| Operations/history | B1/C1/C2 delivered substantial counts, rankings, splits, conditions, streaks, franchise/series/history work, most recently #450 season lists | Implemented does not mean every combination or deployment is accepted. Old individual fixes are not the new sequence |
| Participation/period | Starter roles, period rows and schedule-context features were served only for 2024-25/2025-26; rosters and core games span the historical window | Existing-snapshot slices can proceed. Earlier role/period coverage remains an explicit dependency |
| Specialized data | Served play-by-play, clutch, lineup and on/off files were absent; awards/injury/status require qualified reference sources | Missing sources remain unfinished work; do not derive injury or simultaneous presence from participation |
| Runtime | Prior profiling found material read/index/frame costs and several useful fixes; compact name lookup publication is still to verify | Follow O's bounded measurement/metadata path before suggesting a migration |
| Product acceptance | Existing monitor checks availability and one representative route, not all numeric answers; integrated E remains open | P3 is a real interface/numeric/latency checkpoint, not a monitor screenshot or green-CI claim |

Reuse existing helpers such as `_player_identity.py`, `_condition_utils.py`,
`aggregate_metrics.py`, sample selection in `data_utils.py`, `query_service.py`
and existing route adapters. Locate exact implementations on live main first.
`route_input_metadata.py` is descriptive; accepting a kwarg is not proof it runs.

## 2. Execution order and work ownership

**P0a + P0b -> P0c integration -> P1 -> P2 -> P3**, with **O** independent or
interleaved. P0c can integrate a ready independent candidate sooner; do not wait
idle for unrelated work. P1 implementation can proceed while independent evidence
is pending, but dependent acceptance cannot bypass P0's actual correctness gates.

One lead owns this checkpoint, semantic decisions and integration. At most two
non-overlapping makers plus an independent checker. Only one active writer owns
`natural_query.py` and shared request/parser/service semantics. P0b/workflow or O
work can be a second lane if its files/dependencies truly do not overlap. File
ownership is recorded in the checkpoint, not inferred from the former streams.

P0/P1/P2/P3/O are work-package labels in THIS queue, not new projects, dashboards,
registries or parallel roadmaps. Use coherent PRs. A package may need several
PRs, but each must advance a named outcome; no quota of phrase fixes.

## 3. P0 - Secure existing work

### P0a. Participation is not injury or status

**Observed defect, not a delivered repair:** #462 maps injured/similar status
words to missing participation and healthy/available/active to playing. Its
fixture removes player rows to justify those readings. The source facts do not
support that equivalence. Inspect `docs/reference/data_contracts.md` and the
current participation contract; meaning must be checked before arithmetic.

Preserve real improvements to teammate names/pairs and valid participation
wording. Games in which a player did not play may answer did-not-play/without
questions when coverage and relevant membership are qualified. They cannot be
advertised as injured games or a cause of absence. Likewise played does not mean
healthy, and listed active/available does not prove actual minutes played.

Repair the existing candidate, not a fresh unrelated parser expansion. Status-
specific wording without a source needs honest unavailable/clarification behavior,
not a converted participation answer. Colloquial 'out' can only use a clearly
stated did-not-play meaning where unambiguous; never imply injury. Do not equate
resting/suspended/sidelined or other causes with all absences without evidence.

Acceptance: independently check one and two teammates, reordered clauses and a
stat bound beside participation; retain positive answers for another team/player.
Use discriminating fixtures with both playing and non-playing games, membership
boundaries and unavailable coverage. Explicit injury/status cases must not pass
using absent/present rows. Check selected game IDs, counts, values and scope text
through natural and structured/API paths, then targeted real data for participation
and affected deployed output. Safety for missing injury data does not complete an
injury-statistics feature. If the bug already landed, repair main via a bounded PR.

### P0b. Required numerical acceptance must actually fail when wrong

Inspect `.github/workflows/r2-real-data-validation.yml`, related harness tests,
`tests/conftest.py` and its `needs_data` skip behavior. The observed workflow sets
`continue-on-error: true` on numerical tests; targeted mode may skip other gates.
The last inspected numerical run passed, but a green workflow alone is insufficient.

Strengthen the EXISTING read-only validation path. Required tests for a feature
must be non-optional and tied to a resolved candidate SHA and one pinned generation.
Avoid a moving branch being independently checked out at different revisions by
separate jobs. If older exploratory checks need to stay informational, identify
and separate them explicitly; never reclassify a failing acceptance test merely
to keep green. Preserve the full Raw QA/filter-sweep backstop and secret-free CI.

Acceptance in a controlled test/validation context: a required assertion failure,
a typo or empty required selection, zero executed tests, all-required-skipped run,
missing required data and execution error cannot become a pass. A legitimate
unselected job in targeted mode is not the same as skipped required tests. A valid
positive selection must execute and pass. Report required selected/executed/skipped
counts and underlying job conclusions. A deliberate failure experiment is clearly
labeled, isolated from production data, and leaves no failing test in main.

Use the existing `r2-validation` environment; no credential expansion, duplicate
workflow or branch-protection change. Independent checker verifies enforcement,
not just YAML appearance. Until this lands, manually inspect required underlying
jobs/counts and block dependent merges on any real failure or unavailable evidence.

### P0c. Preserve and integrate pending work

Refresh #455 and #462. Keep the useful game-list population/owner/opponent work
and participation/composition fixes. Do not merge either solely because it is
mergeable or its PR body lists old green totals. Reconcile shared parser changes,
review the actual combined candidate and its semantics, and run applicable checks.
Do not treat an automated-review invitation as completed independent review.

Close this transition when the two trust defects are fixed/verified, useful
pending work is integrated or remains open with a specific independent dependency,
and the checkpoint names P1. Unrelated blocked work must not create an indefinite
P0 phase. No pending capability is silently discarded or marked complete.

## 4. P1 - Deliver shared interpretation, not a new engine

**Outcome:** changing a record/summary into a season split does not silently change
who, which games, whose condition, or statistical basis the question asks for.
This is the first bounded replacement/consolidation opportunity, not a demand to
migrate all routes before shipping.

Start with `team_record`, player/team summaries and `player_split_summary` /
`team_split_summary` for named-season splits. Inspect their existing shared sample
helpers and the #450 reparse guard. Reuse or extend the existing boundary so the
request has explicit subject identity, record grain, ordered time/sample selection,
owned conditions, operation, metric/basis and grouping. Structured and natural
entry points should reach the same calculation. Retain working compatibility
adapters while migrating this group. Remove a defensive reparse only when its
invariants are implemented and independently verified, not just to shrink code.

Mandatory first positive contracts (select fixture and real-data entities where
participation/coverage is actually discriminating; names are examples, not rules):

| ID | Shared behavior and required combination |
| --- | --- |
| S1 | Team record/summary and season split: home + named opponent, comparing exactly two explicit non-adjacent seasons; intermediate seasons must not appear |
| S2 | Player summary and season split: own points threshold + named opponent, on the same explicit season set; selected player-game IDs and averages agree with independent expectations |
| S3 | Team record and player summary: own-stat and opponent-stat clauses in the same request stay owned by the correct side; combine with a home/road filter |
| S4 | Team record/player summary and season split: one qualified teammate's played/did-not-play condition + named opponent survives the operation change; no injury/status inference |
| S5 | Records and summaries: explicit date range + opponent; distinguish the last N games with a condition checked inside that window from the last N qualifying games. Keep eligibility/order and labels explicit |

P1 covers these five contracts, not every permutation. For S1-S4 also retain the
corresponding one-season control. Specify behavior of an explicitly named empty
season and missing coverage separately. Do not force date/last-N combinations
into cross-season splits before their meaning and need are established.

In the P1 PR, bind S1-S5 to existing/new focused tests and corpus IDs before
repairing them; update the corresponding Core-1 cells. Expected results come
from independent raw-row selection/aggregation, not parser output. The checker
uses another entity, threshold and wording outside the maker's tuning set.
Test lost clauses, swapped subjects, scope widening, and valid zeros separately.
Assert actual API/result labels and selected IDs, not merely route equality.

Done: these positive contracts work through existing calculations and natural
input, required checks/review pass, deployment is checked, and the relevant
obsolete special handling is removed or explicitly justified. A new class or
file extraction without those answers is not completion. Other families stay
on their working paths. Then start P2; do not finish every engine feature first.

## 5. P2 - Bounded input-layer comparison

Use the P1-verified subset and freeze the candidate code/data and semantic truth
before tuning. This is one decision-sized comparison, not a provider tournament.
Reuse existing tests, structured entry point, corpora and reports; no new permanent
benchmark framework or public-input mode.

Compare the incumbent with one bounded improved interpreter. The lead chooses a
feasible deterministic redesign or a constrained AI translator under existing
access/cost authority; when feasible include the other as a small comparison,
not a prerequisite. Models propose validated requests for the same engine, not
NBA answers, missing facts, arbitrary SQL or executable code.

Bind held-out paraphrases to S1-S5 and selected Core-1 cells. The checker establishes
intended semantics independently of the candidate, including alternate word order,
unfamiliar entity names, two conditions with the same number, unsupported extra
clauses and genuine ambiguity. Keep maker examples, held-out valid questions and
safety/ambiguity controls distinguishable. Do not tune on a held-out failure and
continue reporting it as unseen; keep it as regression and add fresh holdouts.

Record denominator, answered-correctly, wrong-answer, refusal and ambiguity counts;
clause/identity/sample preservation; real end-to-end latency (including repeats
for a nondeterministic candidate); and authorized operating cost. Define the
comparison's exact cases and latency/cost limits before running it. An unrun model
alternative is 'not evaluated', not a win/loss. Without authorized model access,
complete the feasible comparison, retain that limitation, and continue core work.

Selection gate: no known wrong accepted answer or lost clause in the required
subset, no required positive regression hidden as refusal, and either more correct
held-out answers or demonstrably simpler reliable interpretation at comparable
coverage, within limits. Schema conformance alone never passes. Keep the incumbent
when the replacement does not show a verified benefit; record why and the next
bounded improvement. Do not keep it by default without measuring the problem.

The result is one short decision in this queue/PR with evidence and the exact
integration step. Integrate a winning bounded replacement behind existing contracts
and normal gates. New cost/credentials or production-model adoption require the
necessary owner decision; prepare a recommendation and continue independent work.

## 6. Core-1 acceptance scope (P3 starts during P1, closes after P2 decision)

This finite **existing-snapshot checkpoint** is not the entire original core or
whole product. The following 12 rows are its fixed capability denominator. Each
row's enumerated obligations is required; examples are not exact phrase templates.
Before tuning a row, bind the obligations to explicit test/corpus IDs and independent
expectations in its PR and the evidence column. Reuse existing tests/evidence where
applicable. Do this while building the selected row, not as a new audit-only phase.

States: **I** implemented/merged; **N** independently numerically verified (fixture
and real-data scope distinguished); **L** held-out language verified; **D** actual
API/rendered/deployed path verified. 'Unassessed' means current integrated acceptance
is not established, not that all underlying code is absent. Never infer a percentage
from PR or test counts. Each row passes only when every bound required case passes.

| ID | Required positive behavior and bounded combinations | State / evidence |
| --- | --- | --- |
| K01 | Correct player/team identity and covered scope: aliases/accent spelling, one same-name collision, one renamed player, historical franchise, partial-career label | PR483 merged;14actual numerical/14QA137checks accepted. Historical boundedD39094178858 and52combinedK01/K03 browser responses39097220860 passed; current integratedD pending. |
| K02 | Player summary/team record: explicit season, explicit date range + opponent, last-N window versus qualifying last-N with one threshold | PR486/PR490 merged;13actual numerical/13QA183checks accepted. PR508 repaired canonical opponent validation;39167992465 passed66actual responses/132readiness checks on current generation, independently accepted. |
| K03 | Find/count: two AND thresholds including exact zero, strict versus inclusive bound, grouped OR, games versus distinct-player count, qualified zero result | PR481/PR487 merged;12actual numerical/12QA61checks accepted. Historical52K01/K03 browser responses39097220860 passed; current integratedD pending. |
| K04 | Ranking: totals versus per-game, ratio-of-totals shooting with declared attempts floor, top-N versus last-N, one event-count ranking and tie policy | PR485/PR490 merged;20actual numerical/20QA693checks accepted. PR508/39167992465 passed66actual summary/ranking responses on current generation with source-oracle and independent screenshot/receipt review. |
| K05 | Cross-subject conditions: own-player/team versus opponent stat in one request, plus home/road; another entity and threshold | PR488/PR492 merged;8actual numerical/8QA242checks accepted.40combined ownership/comparison production responses39163942659 passed on current generation. Prior independent source/semantic/local review; lead inspected actual artifact. |
| K06 | Comparisons: two players with same named sample/basis; two teams' independent samples versus explicit head-to-head meetings; opponent filter retained | PR491/PR492 merged; currentgeneration39160471581 passed12numerical0skip/12QA340checks independently accepted.40combined production responses39163942659 passed with exact samples/values/labels; broader identity/status gaps retained. |
| K07 | Splits: filter before home/away split; team and player named-season splits with non-adjacent seasons; opponent + threshold or participation retained | PR493/494 merged; current-generation numerical/QA gates accepted. Production run39176663385 passed1 required test,24 desktop/mobile answers and48 ready immutable-generation checks with exact identities, buckets, values and labels; independently accepted. Bounded deployed split gate closed. |
| K08 | Participation: one and two qualified teammates played/did-not-play; add one stat bound; show membership/coverage distinction and separate injury-status safety controls | PR513 bounded pair support accepted with8 actual source tests; PR516 production gate covers pair played/DNP, player bound, qualified empty and extra-clause safety. PR515 stages17 Boston observations only. Broader integrated acceptance, all46 original absence obligations and other-game membership remain open; no season-wide or medical-status claim. |
| K09 | Sequences: team winning streak and player threshold-appearance streak; count distinct runs; best N-game stretch versus last N; excluded-game/season continuity | Prior C2; integrated acceptance unassessed |
| K10 | Playoff/history: game versus series record versus appearances; one round/series-situation filter; one franchise/title-count query with exact definition and covered span | Prior C2; integrated acceptance unassessed |
| K11 | Population/ownership: league, named team's players, rookie and broad-position game lists; named opponent stays opponent, historical roster slice and missing-roster safety | #455 pending at revision; integrated acceptance unassessed |
| K12 | Answer delivery: actual subject/sample/basis labels; count/list/split/comparison rendering; valid zero versus no-data; snapshot freshness disclosure; representative cold/warm behavior | P3/O; integrated acceptance unassessed |

For each statistical row, use controlled discriminating rows AND representative
qualified real-data numeric checks. Exercise a second entity/value and unfamiliar
wording; pairwise modifier coverage plus targeted three-way cases is enough, not
an exhaustive word/number cross-product. Positive obligations may not be replaced
by refusal expectations. Safety controls have separate IDs/results and never
inflate the positive completion rate. New siblings outside these obligations stay
in the carry-forward list rather than continually expanding Core-1 by accident.

P3 acceptance uses a fixed integration candidate and served generation, the chosen
input path, and actual desktop/mobile result rendering. Exercise reused renderers
with representative outputs and changed ones directly; no owner screenshot tour.
Run applicable CI, required real-data tests, broad Raw QA/filter sweep at integration,
plus independent numerical/meaning review. Compare source keys/coverage with the
claims; 'two paths agree' or a changed output fingerprint is not correctness.

Measure common summaries/records/rankings/comparisons and heavier history/career
requests on a declared repeatable sample. Retain goals: warm common p95 <= 3 s,
cold common <= 10 s, admitted historical <= 20 s without unhandled timeout. Report
sample size, first-request versus warm, and p95 only when measurement supports it.
Do not infer these from one monitor run or raise thresholds to claim success.
If unmet, keep K12 operational acceptance open with a specific repair/dependency.

Close Core-1 only with its full bound positive set accepted and I/N/L/D evidence,
no unresolved wrong/unverified required answer, honest coverage, and required
checks/review passed. Record remaining broader scope explicitly. Snapshot acceptance
is NOT unattended-current-data acceptance; do not rename it full release readiness.

## 7. O - Independent snapshot/runtime work

**O1: inspect compact identity metadata first.** Verify the actual served generation
and whether `metadata/player_names.csv` exists/is used. Inspect
`generation_publication.py` / `_write_player_names` and the reader. The writer can
derive this lookup from staged existing player-game rows; a fresh NBA pull is not
intrinsically needed. Do not assume it is missing or automatically beneficial.

If missing, stage the existing immutable snapshot, derive/validate metadata, compare
identity results and measured cold/warm cost, then publish only under existing
write authority and deployment safeguards. Preserve original NBA data dates,
checksums/lineage, unchanged stats and last-good rollback. A metadata-only generation
is not new coverage. Without publication access, leave that exact gate open, deliver
the validated candidate/evidence, and continue independent work; never widen a
read-only key or ask the owner to restore their laptop as a runner.

October 15 source inspection confirmed `_write_player_names` derives
`metadata/player_names.csv` solely from staged existing player-game rows, and
`_read_published_player_names` consumes it with `first_seen` ordering or falls
back to full scanning. Actual served-generation metadata/access and production
performance remain unverified; no generation was staged/published in this session.

**O2: distinguish possible work from source blockers.** Maintain in this section a
short list of stored, derivable, missing and unverified inputs with consumer and
exact next action. Existing period/role slices and derivable game/reference facts
need not wait for missing play-by-play/lineup datasets. Start one representative
qualified slice with a real consumer, not a full-history collection campaign.

**O3: measured deployment repairs.** Profile read/index construction, frame
selection/cache, computation, serialization and render time. Fix observed costs,
including generation-aware caches and bounded reads, before proposing a new DB or
host. Preserve cost/security controls; in-process counters are not evidence of a
global provider spending cap. Product acceptance is not the availability monitor.

**Parked: fresh NBA acquisition and unattended refresh.** October 4 direction remains.
Prior hosted-runner reachability failures and unavailable laptop fallback are leads,
not a reason to retry blindly or a permanent source impossibility claim. Resume
only under the applicable owner priority/access decision. Reuse the staged refresh,
validation, immutable publication and last-good path. The eventual operational gate
requires a reachable authorized runner/source, a successful update reaching the app,
a failed update preserving last-good, live/frozen-clock rollover tests and budgets.
Existing `download-generation`, `changed-files`, conditional publication and pruning
work is retained; verify actual CLI help/runbook before executing consequential steps.

## 8. Carry-forward scope (not silently completed by Core-1)

These preserve the original program and the unfinished boundary; implementation
status must be reconciled before work, not assumed from old examples. Specific
unresolved examples/evidence remain in the immutable prior queue and current PRs.

| Retained area | Next dependency-backed direction |
| --- | --- |
| Remaining A/B/C combinations | Transfer newly discovered requested combinations outside K01-K12 here with root cause; use shared request semantics, not another endless phrase stream |
| Identity/availability edge cases | Shared-name cross-filters, on/off name paths, membership timing and qualified absence; distinguish whole-game from on-court presence |
| Dates/samples and opposing metrics | Remaining selector/window, repeated-month/season, opponent-metric summary and multi-subject cases: reproduce current code first; do not preserve an old wrong-answer workaround |
| Counts, rankings and sequences | Additional compound/grouped/population/eligibility/series conditions and meaningful combinations beyond the bound checkpoint |
| Historical reference | Remaining playoff/championship membership, awards, calendar/reference facts with qualified sources; participation-based title counts are not an invented official ring roster |
| D1 roles/context | Needed pre-2024-25 starter/bench/period/context coverage, team bench outputs and reference joins; existing qualified slices may ship first |
| D2 specialized inputs | Separate period, play-by-play/clutch, lineup and on/off subpackages with exact grain, denominators, sources and representative validation; no fabricated data |
| Unattended freshness | Parked acquisition/refresh and tested rollover remain open until actual authorized operation is proved |
| Guided tools/profiles | Retained later surfaces on verified shared engine/data, not a substitute for ordinary natural search |

At Core-1 completion, the lead chooses the next coherent row by dependency and
user value, records why here, binds its acceptance and continues under existing
authority. No fresh whole-project plan or owner-written test battery is required.
A genuine new source/cost/product decision is escalated with the smallest action.

## 9. Evidence, validation and durable continuation

For each selected PR record a compact semantic contract, required case IDs,
independent expected meanings/values, base/candidate SHA, one generation, executed
checks/counts, actual checker evidence, deployed result and remaining issues.
Make every requested clause accounted for. Maintain fixture versus real-data,
implementation versus deployment, and safety versus feature-completion distinctions.

Reuse focused commands while editing, `make test-preflight` / `make test` for high
fan-in integration, and the existing targeted/full R2 workflow. CI's data-free or
all-suite selection does not mean required remote data ran. Required assertions,
missing data or all-skipped acceptance remain blockers even before P0b enforcement.
A documentation-only plan change runs `make docs-governance` / `git diff --check`,
not a new full remote NBA corpus. Do not fabricate independent or human review.

Update the Resume checkpoint at work start, review-ready, merge, actual block and
session limit. Add the active package's I/N/L/D evidence to the table or PR pointer;
replace stale next actions and owner/file claims. Preserve unresolved findings.
Minimum successor handoff:

```text
Updated date; controlling package/case IDs; next incomplete stage
Live main checked; task branch and exact candidate SHA; PR
Owner/lane and overlapping work; pushed/unpushed/dirty state
Pinned generation and relevant coverage
Tests: exact command/run, selected/executed/skipped, result and scope
Independent checker: actual session/review, findings fixed/open
Deployment: URL/revision/generation, checked or still pending
Blocker: exact dependency/access and what may proceed independently
NEXT: one concrete action/command, expected outcome, then next package
```

A PR comment may hold detail while the checkpoint points to it. Keep needed code,
tests and conclusions in tracked repo/PR state; do not depend exclusively on a
private conversation, expiring artifact or local ignored output. Do not commit
credentials or synthetic facts as real data. No new handoff subsystem is needed.

A successor verifies the checkpoint against live state, preserves newer commits,
and performs NEXT. If that action already succeeded, record evidence and advance;
if blocked, state the actual dependency and choose the named independent task.
Do not restart all audits, reconstruct old threads, or ask the owner to choose a
technical task. Report: Now answers; Still unfinished; Verification; Next; Needed
from you (normally nothing). Work continues only within an actual active session.

Opponent-clause acceptance: reviewed664b7e49ec38900eed3560304a19440d7f370340,
requeste9a59745f308effdec3bc48ff22ef343e6023742, run39012662199.
Numericalartifact12093825320 ZIP SHA256fdf839875402aeec409104bc8ab746af9d10ec8ef9abc2a4159212a7d8f808f6;
RawQAartifact12092644599 ZIP SHA256fe8d41d6b5760bfee5e8a2b0f6187a59f44835e9a8f314d2437fd34830e08030.
DEN awayUTA two games eachseason:222/258PTS; MIN homeDEN twoeach:222/226PTS.
ExactIDs/WL/REB/AST independently checked. RawQA firstquery10.826seconds includes
remote cold data access; second0.0463seconds. This is not deployed latency acceptance.

K03 final actual receipt: reviewed350d05e011ef884cba73c3690cc093b4753448db,
request9525de66a4efd45b8c87ced739000e47f2e6f9ce, run39090625877.
12selected/executed/passed0skipped/errors;12RawQA61checks passed.
Numericalartifact12122497556 ZIP7d5f3d15e615fb9bab897d059fe0b9644268b8d8b5419ed3c832bb876ca70bc7;
QA12122472545 ZIPbaea83daa123cebea8157beb81d388979be74ec6a98701bf2685e7dd2d9defd4.
League count now says20player-games;11distinctplayers remains separate. Historical
human-review fields stay unreviewed; no browser acceptance or production write.
